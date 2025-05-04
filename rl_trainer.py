# FILE: rl_trainer.py (Updated Env Initialization)

"""
Reinforcement Learning Agent Training Script.

Orchestrates the training process for an RL agent using Stable Baselines3
to learn optimal trading parameters for the custom TradingEnv environment.

to see training details use:
tensorboard --logdir ./rl_tensorboard_logs/ --port 6006      
"""

import os
import asyncio
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Union, Tuple
import warnings

# --- Stable Baselines3 Imports ---
try:
    import stable_baselines3
    from stable_baselines3 import PPO, SAC, TD3
    from stable_baselines3.common.env_util import make_vec_env
    # Import VecEnv types explicitly
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv, VecNormalize
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.env_checker import check_env
    from stable_baselines3.common.logger import configure as sb3_configure_logger
    RL_AVAILABLE = True
except ImportError:
    print("Stable Baselines3 library not found or has issues. RL training is unavailable.")
    print("Please install it: pip install stable-baselines3[extra]>=2.0.0a5")
    RL_AVAILABLE = False
    class DummyAlgorithm: pass
    PPO = SAC = TD3 = DummyAlgorithm
    class BaseCallback: pass
    class VecEnv: pass # Dummy VecEnv base class
    class DummyVecEnv(VecEnv): pass
    class SubprocVecEnv(VecEnv): pass
    class VecNormalize(VecEnv): pass

import shap
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt

# --- Project Modules ---
import rl_config
from logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_environment import TradingEnv # Ensure TradingEnv takes lifespan info
from utils import load_and_split_data, calculate_volatility, export_to_csv, NpEncoder # Import NpEncoder for saving

# --- Global Variables ---
db_client_global: Optional[DatabaseClient] = None


# --- Custom Callback ---
class TensorboardCallback(BaseCallback):
    """Logs additional custom values to TensorBoard."""
    def __init__(self, verbose=0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        # Log average final portfolio value from completed episodes
        final_values = [ep_info.get('final_portfolio_value') for ep_info in self.model.ep_info_buffer if 'final_portfolio_value' in ep_info]
        if final_values:
            avg_final_value = np.mean(final_values)
            self.logger.record('rollout/ep_final_value_mean', avg_final_value)

        # Log average SOL balance at episode end
        sol_balances = [ep_info.get('sol_balance') for ep_info in self.model.ep_info_buffer if 'sol_balance' in ep_info and ep_info.get('terminated', False) or ep_info.get('truncated', False)]
        if sol_balances:
             avg_sol_balance = np.mean(sol_balances)
             self.logger.record('rollout/ep_sol_balance_mean', avg_sol_balance)
        return True

# Add this class after the TensorboardCallback class
class SaveVecNormalizeCallback(BaseCallback):
    """Callback to save VecNormalize statistics when a new best model is found."""
    def __init__(self, save_path: str, verbose=0):
        super().__init__(verbose)
        self.save_path = save_path

    def _on_step(self) -> bool:
        vec_normalize = self.model.get_vec_normalize_env()
        if vec_normalize is not None:
            vec_normalize.save(self.save_path)
        return True

def analyze_feature_importance(model, env, num_samples=1000):
    """Analyzes feature importance using SHAP with proper output handling."""
    # Generate properly structured samples
    samples = np.array([env.observation_space.sample() for _ in range(num_samples)])
    
    # Create wrapper function that returns proper numpy array
    def model_predict_wrapper(x):
        # Stable Baselines3 returns (action, state) tuple
        return np.array([model.predict(sample)[0] for sample in x])

    # SHAP Analysis
    explainer = shap.Explainer(
        model_predict_wrapper, 
        samples,
        feature_names=rl_config.OBSERVATION_FEATURES
    )
    
    # Calculate SHAP values in batches to manage memory
    shap_values = explainer(samples[:100])  # Use smaller subset for demonstration
    
    # Plot summary
    plt.figure()
    shap.summary_plot(shap_values, samples[:100], show=False)
    plt.savefig(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_shap.png"))
    plt.close()

    # Permutation Importance
    # def score_fn(X):
    #     return np.array([model.predict(x)[0] for x in X])

    # result = permutation_importance(
    #     score_fn, 
    #     samples[:100], 
    #     n_repeats=5, 
    #     random_state=42,
    #     n_jobs=-1
    # )
    
    # # Save results
    # importance_df = pd.DataFrame({
    #     'feature': rl_config.OBSERVATION_FEATURES,
    #     'importance_mean': result.importances_mean(axis=1),
    #     'importance_std': result.importances_std(axis=1)
    # }).sort_values('importance_mean', ascending=False)
    
    # importance_df.to_csv(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_permutation.csv"), index=False)
    
    logger.info("Feature importance analysis completed")

# --- Environment Creation Helper ---
def make_env_func(
    data_dict: Dict[str, pd.DataFrame],
    lifespan_dict: Dict[str, Dict[str, datetime]], # Add lifespans
    initial_capital: float,
    max_steps: int,
    rank: int = 0,
    seed: int = 0
):
    """
    Utility function for creating and wrapping the environment for VecEnv.

    Args:
        data_dict: Historical data for this environment instance.
        lifespan_dict: Token lifespan data for this environment instance.
        initial_capital: Starting capital.
        max_steps: Max steps per episode.
        rank: Unique identifier for the environment instance.
        seed: Base random seed.

    Returns:
        A function that initializes and returns the wrapped environment.
    """
    def _init():
        # Filter data to only include mints present in lifespan_dict
        valid_data = {
            k: v for k, v in data_dict.items()
            if isinstance(v, pd.DataFrame) and not v.empty and k in lifespan_dict
        }
        valid_lifespans = {k: v for k, v in lifespan_dict.items() if k in valid_data}

        if not valid_data or not valid_lifespans:
            logger.error(f"make_env_func (rank {rank}) received empty/invalid data or missing lifespans!")
            raise ValueError(f"Cannot create environment for rank {rank} with empty data or missing lifespans.")

        env = TradingEnv(
            historical_data_dict=valid_data,
            token_lifespans=valid_lifespans, # Pass lifespans
            initial_capital=initial_capital,
            max_steps=max_steps
        )
        env.reset(seed=seed + rank) # Seed the environment
        log_dir_monitor = os.path.join(rl_config.MODEL_SAVE_DIR, f"monitor_logs_{rank}")
        os.makedirs(log_dir_monitor, exist_ok=True)
        env = Monitor(env, filename=log_dir_monitor)
        return env
    return _init

# --- Main Training Function ---
async def train_rl_agent():
    """Sets up the RL environment, agent, callbacks, and starts training."""
    global db_client_global
    setup_logging(logger_name="rl_trainer") # Initialize logger for this module
    logger.info("--- Starting RL Agent Training ---")

    if not RL_AVAILABLE:
        logger.critical("Stable Baselines3 is not available. Cannot start RL training.")
        return

    # --- Database Connection ---
    # (Connect DB - same as before)
    if not db_client_global:
        db_client_global = DatabaseClient()
        try:
            await db_client_global.connect()
            logger.info("DB Client connected for RL Trainer.")
        except Exception as e:
            logger.critical(f"Failed to connect database for RL Trainer: {e}")
            return

    # --- Load and Prepare Data (Receives data AND lifespans) ---
    start_date = rl_config.RL_HISTORICAL_DATA_START_TS
    end_date = rl_config.RL_HISTORICAL_DATA_END_TS
    data_split_config = rl_config.DATA_SPLIT_RL

    logger.info(f"Loading and splitting data from {start_date.isoformat()} to {end_date.isoformat()}...")
    loaded_results: Optional[Tuple[Dict, Dict]] = await load_and_split_data(db_client_global, start_date, end_date, data_split_config)

    if loaded_results is None:
        logger.critical("Failed to load or split data. Exiting.")
        if db_client_global: await db_client_global.close()
        return

    loaded_data_sets, token_lifespans = loaded_results # Unpack

    # Create an output directory for the datasets
    # output_dir = os.path.join("data", "exported_datasets", datetime.now().strftime("%Y%m%d_%H%M%S"))

    # # Export the datasets and token lifespans
    # export_to_csv(loaded_data_sets, output_dir, token_lifespans)
    # logger.info(f"Exported datasets and token lifespans to {output_dir}")

    training_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_EVAL)
    # Filter lifespans to match the data splits
    train_lifespans = {k: v for k, v in token_lifespans.items() if k in training_data} if training_data else {}
    eval_lifespans = {k: v for k, v in token_lifespans.items() if k in eval_data} if eval_data else {}


    if not training_data or not train_lifespans:
        logger.critical("No training data or corresponding lifespans available after loading/splitting. Exiting.")
        if db_client_global: await db_client_global.close()
        return

    logger.info(f"Training data loaded for {len(training_data)} tokens with lifespan info.")
    if eval_data and eval_lifespans:
        logger.info(f"Evaluation data loaded for {len(eval_data)} tokens with lifespan info.")
    else:
        logger.warning("No evaluation data/lifespans found. Evaluation callback will not function correctly.")
        eval_data = None # Ensure eval_data is None if lifespans are missing
        eval_lifespans = {}

    # --- Create Vectorized Environments ---
    logger.info("Creating RL Vectorized Environments...")
    train_env_raw: Optional[VecEnv] = None
    eval_env_raw: Optional[VecEnv] = None
    train_env: Optional[VecNormalize] = None
    eval_env: Optional[VecNormalize] = None


    try:
        VecEnvClass = SubprocVecEnv if rl_config.N_ENVS > 1 else DummyVecEnv

        # Create training environments, passing lifespans
        env_fns = [make_env_func(training_data, train_lifespans, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE, rank=i)
                   for i in range(rl_config.N_ENVS)]
        train_env_raw = VecEnvClass(env_fns)
        logger.info(f"Created Training VecEnv ({VecEnvClass.__name__}) with {rl_config.N_ENVS} environments.")

        # --- Environment Checker ---
        # try:
        #     logger.info("Running environment checker...")
        #     # Pass lifespans to the check env func too
        #     sample_env_fn = make_env_func(training_data, train_lifespans, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE, rank=99)
        #     check_env(sample_env_fn(), warn=True) # Create and check one instance
        #     logger.info("Environment check passed.")
        # except Exception as check_err:
        #     logger.error(f"Environment check failed: {check_err}", exc_info=True)
        #     # return # Exit if check fails

        # Create evaluation environment
        if eval_data and eval_lifespans:
            eval_env_fn = make_env_func(eval_data, eval_lifespans, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE, rank=100)
            eval_env_raw = DummyVecEnv([eval_env_fn])
            logger.info("Created Evaluation VecEnv (DummyVecEnv).")
        else:
             eval_env_raw = None

        # --- Apply VecNormalize ---
        normalize_kwargs = {'norm_obs': True, 'norm_reward': False, 'gamma': 0.99}
        train_env = VecNormalize(train_env_raw, **normalize_kwargs)
        logger.info("Applied VecNormalize to training environment.")
        if eval_env_raw:
            eval_env = VecNormalize(eval_env_raw, training=False, **normalize_kwargs)
            # Load the SAME stats as the training env for consistent evaluation
            eval_env.obs_rms = train_env.obs_rms
            eval_env.ret_rms = train_env.ret_rms # If normalizing rewards (norm_reward=True)
            eval_env.clip_obs = train_env.clip_obs
            eval_env.clip_reward = train_env.clip_reward
            logger.info("Applied VecNormalize to evaluation environment using training stats.")
        else:
            eval_env = None

    except Exception as e:
        logger.exception(f"Error creating vectorized environments: {e}")
        # Clean up any created envs
        if train_env: train_env.close()
        elif train_env_raw: train_env_raw.close() # Close raw if wrapper failed
        if eval_env: eval_env.close()
        elif eval_env_raw: eval_env_raw.close()
        if db_client_global: await db_client_global.close()
        return

    # --- Configure Agent ---
    # (Agent selection, path setup, SB3 logger setup - same as before)
    logger.info(f"Setting up RL Agent: {rl_config.RL_ALGORITHM}")
    algo_map = {"PPO": PPO, "SAC": SAC, "TD3": TD3}
    AgentClass = algo_map.get(rl_config.RL_ALGORITHM)

    if AgentClass is None:
        logger.critical(f"RL Algorithm '{rl_config.RL_ALGORITHM}' not supported.")
        # Cleanup envs before exiting
        if train_env: train_env.close()
        if eval_env: eval_env.close()
        if db_client_global: await db_client_global.close()
        return

    os.makedirs(rl_config.TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(rl_config.MODEL_SAVE_DIR, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"{rl_config.RL_ALGORITHM}_{run_timestamp}"
    log_path_tb = os.path.join(rl_config.TENSORBOARD_LOG_DIR, model_prefix)
    save_path_model = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
    save_path_vecnormalize = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl")
    best_model_save_dir = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best")

    # Configure SB3 logger to output to tensorboard, csv, and stdout
    sb3_file_logger = sb3_configure_logger(log_path_tb, ["stdout", "csv", "tensorboard"])

    device = 'cpu' #"auto"
    logger.info(f"Using device: {device}")

    # Define agent parameters
    agent_params = dict(
        policy="MlpPolicy",
        env=train_env, # Use the normalized env
        policy_kwargs={
            "net_arch": {
                "pi": [64, 64],  # Policy network architecture
                "vf": [64, 64]   # Value function network architecture
            }
        },
        verbose=1,
        device=device,
        seed=42
    )
    # Algorithm-specific hyperparameters
    if rl_config.RL_ALGORITHM == "PPO":
        agent_params.update(dict(
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.1,  # Slightly increased for better exploration
            vf_coef=0.5,
            learning_rate=3e-4,
            max_grad_norm=0.5,  # Added to prevent explosive gradients
            use_sde=False,     # Added explicit SDE setting
            sde_sample_freq=-1
        ))
    # Add SAC/TD3 params if needed

    model = AgentClass(**agent_params)
    model.set_logger(sb3_file_logger) # Assign the configured logger

    # --- Setup Callbacks ---
    logger.info("Setting up Callbacks...")
    callbacks = []
    # Checkpoint callback
    checkpoint_callback = CheckpointCallback(
        save_freq=max(rl_config.CHECKPOINT_FREQ // rl_config.N_ENVS, 1), # Adjust freq by n_envs
        save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_checkpoints"),
        name_prefix="rl_model",
        save_replay_buffer=True if rl_config.RL_ALGORITHM in ["SAC", "TD3"] else False,
        save_vecnormalize=True # IMPORTANT: Save VecNormalize stats with checkpoints
    )
    callbacks.append(checkpoint_callback)

    # Evaluation callback
    if eval_env:
        save_vec_normalize_callback = SaveVecNormalizeCallback(
            save_path=os.path.join(best_model_save_dir, "best_vecnormalize.pkl")
        )
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=best_model_save_dir,
            log_path=best_model_save_dir,
            eval_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1),
            n_eval_episodes=rl_config.N_EVAL_EPISODES,
            deterministic=True,
            render=False,
            verbose=1,
            callback_on_new_best=save_vec_normalize_callback  # Use the new callback class
        )
        callbacks.append(eval_callback)
    else:
        logger.warning("EvalCallback disabled as evaluation environment is not available.")

    # Custom TensorBoard callback
    callbacks.append(TensorboardCallback())

    # --- Start Training ---
    logger.info(f"--- Starting RL Training ({rl_config.RL_ALGORITHM}) for {rl_config.TOTAL_TIMESTEPS} timesteps ---")
    start_train_time = time.time()
    training_successful = False
    try:
        model.learn(
            total_timesteps=rl_config.TOTAL_TIMESTEPS,
            callback=callbacks,
            log_interval=10, # Log stats every 10 updates (can adjust)
            reset_num_timesteps=True
        )
        training_successful = True
    except KeyboardInterrupt:
         logger.warning("Training interrupted by user (KeyboardInterrupt). Saving current model.")
    except Exception as learn_err:
        logger.exception(f"Error during model.learn(): {learn_err}")
    finally:
        # --- Save Final Model and Environment Statistics ---
        end_train_time = time.time()
        logger.info(f"--- Training loop finished. Duration: {end_train_time - start_train_time:.2f} seconds ---")

        try:
            # Save the final agent model
            model.save(save_path_model)
            logger.info(f"Final trained model saved to: {save_path_model}")

            # Save the VecNormalize statistics from the training environment
            if isinstance(train_env, VecNormalize):
                train_env.save(save_path_vecnormalize)
                logger.info(f"Final VecNormalize statistics saved to: {save_path_vecnormalize}")

            # Check if a best model was saved and report
            best_model_path = os.path.join(best_model_save_dir, "best_model.zip")
            best_vecnorm_path = os.path.join(best_model_save_dir, "best_vecnormalize.pkl")
            if eval_env and os.path.exists(best_model_path) and training_successful:
                logger.info(f"Best model saved during evaluation: {best_model_path}")
                if os.path.exists(best_vecnorm_path):
                    logger.info(f"Corresponding VecNormalize stats saved: {best_vecnorm_path}")
                else:
                    logger.warning(f"Best model saved, but VecNormalize stats file missing: {best_vecnorm_path}")

        except Exception as save_err:
             logger.error(f"Failed to save final model or VecNormalize stats: {save_err}")

        if training_successful:
            logger.info("Performing post-training feature importance analysis...")
            analyze_feature_importance(model, train_env)

        # --- Cleanup ---
        logger.info("Closing environments...")
        try:
            # Close VecNormalize wrappers first, then underlying VecEnvs
            if train_env: train_env.close()
            if eval_env: eval_env.close()
            # No need to explicitly close train_env_raw/eval_env_raw if wrappers were created
        except Exception as close_err:
            logger.error(f"Error closing environments: {close_err}")

        if db_client_global: await db_client_global.close()
        logger.info("--- RL Agent Training Finished ---")


# --- Entry Point Guard ---
if __name__ == "__main__":
    if os.name == 'nt':
         from multiprocessing import freeze_support
         freeze_support()

    try:
        asyncio.run(train_rl_agent())
    except Exception as main_err:
         logger.critical(f"Critical error in RL trainer entry point: {main_err}", exc_info=True)