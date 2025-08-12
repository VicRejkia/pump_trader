# rl_agent/training/train.py
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import optuna
import torch as th
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

import config.config as config_module
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from state_manager import GlobalState
from rl_agent.agents.ppo_agent import create_ppo_agent
from rl_agent.data.data_manager import DataManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv
from utils import NpEncoder


class TrialEvaluationCallback(BaseCallback):
    """
    A Stable Baselines 3 callback to monitor training progress and prune
    unpromising Optuna trials early.
    """
    def __init__(self, trial: optuna.trial.Trial, eval_freq: int, verbose: int = 0):
        super().__init__(verbose)
        self.trial = trial
        self.eval_freq = eval_freq
        self.best_mean_reward = -float('inf')

    def _on_step(self) -> bool:
        if self.n_calls % self.eval_freq == 0:
            ep_info_buffer = self.model.ep_info_buffer
            if ep_info_buffer and len(ep_info_buffer) > 0:
                # Correctly access reward 'r' and length 'l'
                mean_reward = safe_mean([ep_info['r'] for ep_info in ep_info_buffer])
                self.trial.report(mean_reward, self.num_timesteps)
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                if self.trial.should_prune():
                    logger.info(f"Pruning trial {self.trial.number} with mean reward {mean_reward}.")
                    raise optuna.exceptions.TrialPruned()
        return True

async def _objective_async(trial: optuna.trial.Trial, config: Dict[str, Any], state: GlobalState) -> float:
    """
    Asynchronous version of the objective function.
    This function is now self-contained and manages its own DB connection.
    """
    db_client_trial = None  # Each trial gets its own DB client
    try:
        # 1. Setup Trial-Specific DB Connection
        db_client_trial = DatabaseClient(config_dict=config)
        await db_client_trial.connect()

        # 2. Setup Environment
        data_manager = DataManager(
            db_client_trial,
            start_date=datetime.fromisoformat(config['TRAINING_START_DATE'].replace("Z", "+00:00")),
            end_date=datetime.fromisoformat(config['TRAINING_END_DATE'].replace("Z", "+00:00")),
            min_trade_count=config.get('MIN_TRADE_COUNT_FOR_TRAINING', 100)
        )
        if not await data_manager.load_and_prepare_data():
            logger.warning("Failed to load or process data for this trial.")
            raise optuna.exceptions.TrialPruned("Failed to load or process data.")
        
        # --- CRITICAL BUG FIX: Removed sys.exit() ---
        # sys.exit() # This line was incorrectly stopping the training.

        env = MemeCoinEnv(data_manager, config, initial_balance=config.get('RL_INITIAL_BALANCE', 100.0))
        env = Monitor(env) # Wrap env in Monitor for SB3 callbacks

        # 3. Create Agent
        device = 'cuda' if th.cuda.is_available() else 'cpu'
        model = create_ppo_agent(env, trial, device=device)

        # 4. Train Agent
        eval_freq = config.get('RL_EVAL_FREQ', 2048)
        total_timesteps = config.get('RL_TOTAL_TIMESTEPS_PER_TRIAL', 100_000)
        callback = TrialEvaluationCallback(trial, eval_freq)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: model.learn(total_timesteps=total_timesteps, callback=callback)
        )

        # After learning, use the episode info buffer for the final reward
        final_mean_reward = safe_mean([ep_info['r'] for ep_info in model.ep_info_buffer])
        return final_mean_reward if final_mean_reward != 0 else -float('inf')


    except optuna.exceptions.TrialPruned as e:
        raise e # Re-raise to let Optuna handle it
    except Exception as e:
        logger.error(f"Error in Optuna trial #{trial.number}: {e}", exc_info=True)
        return -float('inf') # Return a very bad score on other errors
    finally:
        # 5. Ensure trial-specific DB connection is always closed
        if db_client_trial:
            await db_client_trial.close()

def objective(
    trial: optuna.trial.Trial,
    config: Dict[str, Any],
    state: GlobalState
) -> float:
    """
    Synchronous wrapper for the Optuna objective function.
    It creates a new event loop to run the async trial logic.
    """
    try:
        logger.info(f"🚀 Starting Optuna Trial #{trial.number}...")
        return asyncio.run(_objective_async(trial, config, state))
    except optuna.exceptions.TrialPruned:
        raise
    except Exception as e:
        logger.error(f"Error in Optuna trial #{trial.number}: {e}", exc_info=True)
        return -float('inf')

async def run_training(db_client: DatabaseClient, config: Dict[str, Any], state: GlobalState):
    """
    Main async function to orchestrate the RL training process.
    """
    session_id = uuid.uuid4()
    start_time = datetime.now(timezone.utc)
    n_trials = config.get('RL_OPTUNA_N_TRIALS', 100)
    models_dir = config.get('RL_MODELS_DIR', 'data/rl_models')
    os.makedirs(models_dir, exist_ok=True)

    logger.info(f"Starting RL training session {session_id} with {n_trials} trials.")

    study = optuna.create_study(
        direction="maximize",
        pruner=optuna.pruners.MedianPruner(n_warmup_steps=5, n_min_trials=5)
    )

    try:
        objective_func = lambda trial: objective(trial, config, state)
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: study.optimize(
                objective_func, 
                n_trials=n_trials, 
                timeout=config.get('RL_OPTUNA_TIMEOUT_SECONDS', 3600 * 4) # 4 hours timeout
            )
        )
    except Exception as e:
        logger.error(f"Optuna study failed: {e}", exc_info=True)
        return

    best_trial = study.best_trial
    logger.info("=" * 60)
    logger.info(f"Optuna study complete. Best Trial: #{best_trial.number}")
    logger.info(f"  Value (Best Mean Reward): {best_trial.value:.4f}")
    logger.info("  Best Hyperparameters:")
    for key, value in best_trial.params.items():
        logger.info(f"    {key}: {value}")
    logger.info("=" * 60)
    
    final_model_path = os.path.join(models_dir, f"ppo_model_final_{session_id}.zip")
    logger.info("The next step would be to retrain the final model and save it to:")
    logger.info(f"--> {final_model_path}")


def safe_mean(arr: list) -> float:
    """Calculates the mean of a list, returning 0.0 if the list is empty."""
    return float(sum(arr) / len(arr)) if len(arr) > 0 else 0.0


if __name__ == "__main__":
    setup_logging(logger_name='rl_training')

    async def main():
        state = GlobalState.get_instance()
        config = {key: getattr(config_module, key) for key in dir(config_module) if key.isupper()}
        
        db_check_client = None
        try:
            logger.info("Checking database connectivity before starting training...")
            db_check_client = DatabaseClient(config_dict=config)
            await db_check_client.connect()
            logger.info("Database connection check successful.")
            await run_training(db_check_client, config, state)
        except Exception as e:
            logger.error(f"A critical error occurred: {e}", exc_info=True)
        finally:
            if db_check_client:
                await db_check_client.close()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Training process interrupted by user.")