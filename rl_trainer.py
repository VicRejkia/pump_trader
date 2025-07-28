# FILE: rl_trainer.py (Adapted for Portfolio Env & Offline Pre-training Placeholder)

"""
Reinforcement Learning Agent Training Script for Parameter Optimization.

This module orchestrates the training of an RL agent to find optimal trading
parameters for the bot's logic by simulating its portfolio performance over
historical data.
"""

import os
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
import argparse
from typing import Dict, Optional, Tuple, Callable

# --- Stable Baselines3 Imports ---
try:
    import stable_baselines3
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv, VecNormalize
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback
    from stable_baselines3.common.monitor import Monitor
    RL_AVAILABLE = True
except ImportError:
    print("Stable Baselines3 not found. RL training is unavailable.")
    RL_AVAILABLE = False
    # Dummy classes for type hinting
    class PPO: pass
    class BaseCallback: pass
    class VecNormalize: pass

# --- Project Modules ---
import rl_config
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_environment import TradingEnv # Import the refactored environment
from utils import load_and_split_data

# --- Global Variables ---
db_client_global: Optional[DatabaseClient] = None

# --- Custom Callback ---
class TensorboardCallback(BaseCallback):
    """Logs additional custom values to TensorBoard."""
    def _on_step(self) -> bool:
        final_values = [ep_info.get('final_portfolio_value') for ep_info in self.model.ep_info_buffer if 'final_portfolio_value' in ep_info]
        if final_values:
            self.logger.record('rollout/ep_final_portfolio_mean', np.mean(final_values))
        return True

def pretrain_agent_offline(offline_dataset_path: str, model: PPO) -> PPO:
    """
    Placeholder for offline pre-training logic.
    In a real implementation, this function would load a dataset of
    (state, action, reward, next_state) tuples from the `completed_trades`
    table history and use an offline RL algorithm (e.g., Behavioral Cloning,
    CQL, IQL) to pre-train the agent's policy network. This provides the agent
    with a strong baseline before online fine-tuning.

    Args:
        offline_dataset_path (str): Path to the offline dataset (e.g., CSV or parquet).
        model (PPO): The PPO agent instance to be pre-trained.

    Returns:
        PPO: The pre-trained PPO agent.
    """
    logger.info(f"--- Starting Offline Pre-training Stage (Placeholder) ---")
    logger.warning("Offline pre-training is a conceptual step. This function is a placeholder.")
    logger.info("In a full implementation, you would:")
    logger.info("1. Load a dataset prepared from production `completed_trades` logs.")
    logger.info("2. Implement an offline RL algorithm (e.g., Behavioral Cloning for policy initialization).")
    logger.info("3. Train the policy/value networks on the offline data.")
    logger.info(f"--- Offline Pre-training Stage Finished ---")
    # This function currently does nothing but return the model as is.
    return model


# --- Environment Creation Helper ---
def make_env_func(
    data_dict: Dict[str, pd.DataFrame],
    lifespan_dict: Dict[str, Dict[str, datetime]],
    initial_capital: float,
    max_steps: int,
    rank: int = 0,
    seed: int = 0,
):
    """Utility function for creating and wrapping the environment for VecEnv."""
    def _init():
        env = TradingEnv(
            historical_data_dict=data_dict,
            token_lifespans=lifespan_dict,
            initial_capital=initial_capital,
            max_steps=max_steps,
        )
        env = Monitor(env) # Wrap with Monitor to track episode stats
        env.reset(seed=seed + rank)
        return env
    return _init

# --- Main Training Function ---
async def train_rl_agent(continue_from_model: Optional[str] = None):
    """Sets up the RL environment, agent, callbacks, and starts training."""
    global db_client_global
    setup_logging(logger_name="rl_trainer")
    logger.info("--- Starting RL Agent Training (Portfolio Simulation) ---")

    if not RL_AVAILABLE:
        logger.critical("Stable Baselines3 is not available. Cannot start RL training.")
        return

    # --- Database Connection ---
    if not db_client_global:
        db_client_global = DatabaseClient()
        await db_client_global.connect()

    # --- Load and Prepare Data ---
    loaded_results = await load_and_split_data(
        db_client_global,
        rl_config.RL_HISTORICAL_DATA_START_TS,
        rl_config.RL_HISTORICAL_DATA_END_TS,
        rl_config.DATA_SPLIT_RL
    )
    if not loaded_results:
        logger.critical("Failed to load or split data. Exiting.")
        await db_client_global.close()
        return

    loaded_data_sets, token_lifespans, _ = loaded_results
    training_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_EVAL)

    train_lifespans = {k: v for k, v in token_lifespans.items() if k in training_data}
    eval_lifespans = {k: v for k, v in token_lifespans.items() if k in eval_data}

    if not training_data:
        logger.critical("No training data available. Exiting.")
        await db_client_global.close()
        return

    # --- Create Vectorized Environments ---
    train_env = make_vec_env(
        make_env_func(
            data_dict=training_data,
            lifespan_dict=train_lifespans,
            initial_capital=rl_config.RL_INITIAL_CAPITAL,
            max_steps=rl_config.MAX_STEPS_PER_EPISODE
        ),
        n_envs=rl_config.N_ENVS,
        vec_env_cls=SubprocVecEnv if rl_config.N_ENVS > 1 else DummyVecEnv
    )
    train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.)

    eval_env_instance = None
    if eval_data:
        eval_env_vec = make_vec_env(
            make_env_func(
                data_dict=eval_data,
                lifespan_dict=eval_lifespans,
                initial_capital=rl_config.RL_INITIAL_CAPITAL,
                max_steps=rl_config.MAX_STEPS_PER_EPISODE
            ),
            n_envs=1,
            vec_env_cls=DummyVecEnv
        )
        eval_env_instance = VecNormalize(eval_env_vec, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)


    # --- Configure Agent ---
    os.makedirs(rl_config.TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(rl_config.MODEL_SAVE_DIR, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"{rl_config.RL_ALGORITHM}_{run_timestamp}"

    if continue_from_model:
        logger.info(f"Continuing training from model: {continue_from_model}")
        model = PPO.load(continue_from_model, env=train_env)
    else:
        logger.info("Creating a new model for training.")
        model = PPO(
            "MlpPolicy",
            train_env,
            policy_kwargs=rl_config.POLICY_KWARGS,
            verbose=1,
            tensorboard_log=rl_config.TENSORBOARD_LOG_DIR,
            **rl_config.PPO_HYPERPARAMS
        )

    # --- Offline Pre-training Step (Placeholder) ---
    # In a real scenario, you might have a path to an offline dataset.
    # If a model is not being continued, you could pre-train it here.
    if not continue_from_model:
        model = pretrain_agent_offline(offline_dataset_path="path/to/offline_data.csv", model=model)


    # --- Setup Callbacks ---
    callbacks = [TensorboardCallback()]
    if eval_env_instance:
        eval_callback = EvalCallback(
            eval_env_instance,
            best_model_save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best"),
            log_path=rl_config.MODEL_SAVE_DIR,
            eval_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1),
            n_eval_episodes=rl_config.N_EVAL_EPISODES,
            deterministic=True,
            render=False
        )
        callbacks.append(eval_callback)

    # --- Start Training ---
    try:
        model.learn(
            total_timesteps=rl_config.TOTAL_TIMESTEPS,
            callback=callbacks,
            tb_log_name=model_prefix,
            reset_num_timesteps=False if continue_from_model else True
        )
    except KeyboardInterrupt:
        logger.warning("Training interrupted by user.")
    finally:
        # --- Save Final Model and Environment Statistics ---
        final_model_path = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
        model.save(final_model_path)
        train_env.save(os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl"))
        logger.info(f"Final model saved to: {final_model_path}")

        # --- Cleanup ---
        train_env.close()
        if eval_env_instance:
            eval_env_instance.close()
        await db_client_global.close()
        logger.info("--- RL Agent Training Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Agent Trainer")
    parser.add_argument("--continue-from-model", type=str, help="Path to a saved model to continue training from.")
    args = parser.parse_args()

    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()

    asyncio.run(train_rl_agent(continue_from_model=args.continue_from_model))