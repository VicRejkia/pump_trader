# FILE: rl_trainer.py (Modifications)

import os
import asyncio
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime

try:
    # ... (SB3 imports remain the same) ...
    import stable_baselines3
    from stable_baselines3 import PPO, SAC, TD3
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, StopTrainingOnRewardThreshold
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.env_checker import check_env
except ImportError:
    print("Stable Baselines3 not found. Please install it: pip install stable-baselines3[extra]>=2.0.0a5")
    exit()

import rl_config # RL specific configs
from logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_environment import TradingEnv # The custom environment
# --- Import the new data loading function ---
from utils import load_and_split_data, ensure_datetime

# Global variable for database client (can be removed if passed explicitly)
db_client = None

async def train_rl_agent():
    """Main function to set up and train the RL agent."""
    global db_client # Declare usage of global
    setup_logging()
    logger.info("--- Starting RL Agent Training ---")

    # --- Database Connection & Data Loading ---
    if not db_client: # Initialize if not passed (e.g., from GA run)
        db_client = DatabaseClient()
        try:
            await db_client.connect()
            logger.info("DB Client connected for RL Trainer.")
        except Exception as e:
            logger.critical(f"Failed to connect database for RL Trainer: {e}")
            return

    # --- Load Data using the outsourced function ---
    # Get dates and split config from rl_config
    start_date = rl_config.RL_HISTORICAL_DATA_START_TS
    end_date = rl_config.RL_HISTORICAL_DATA_END_TS
    data_split_config = rl_config.DATA_SPLIT_RL # Use RL specific split

    logger.info("Loading and splitting data using function from utils...")
    loaded_data_sets = await load_and_split_data(db_client, start_date, end_date, data_split_config)

    if loaded_data_sets is None:
        logger.critical("Failed to load or split data via utils function. Exiting.")
        await db_client.close()
        return

    training_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_EVAL)

    if not training_data:
        logger.critical("No training data available after loading/splitting. Exiting.")
        await db_client.close()
        return

    logger.info(f"Training data loaded for {len(training_data)} tokens.")
    if eval_data:
        logger.info(f"Evaluation data loaded for {len(eval_data)} tokens.")
    else:
        logger.warning("No evaluation data found. Evaluation callback will not function correctly.")

    # --- Environment Setup ---
    logger.info("Creating RL Environments...")

    # Create a function to instantiate the environment (needed for VecEnv)
    # Pass the loaded data directly
    def make_env(data_dict, initial_capital, max_steps):
        def _init():
            # Ensure data_dict is not empty for this instance
            valid_data = {k: v for k, v in data_dict.items() if not v.empty}
            if not valid_data:
                 # This should ideally not happen if data loading filters correctly,
                 # but handle defensively. Return a dummy/simplified env? Or raise?
                 # For now, log and raise to prevent silent failures in VecEnv.
                 logger.error("make_env called with empty or invalid data_dict!")
                 raise ValueError("Cannot create environment with empty data.")

            env = TradingEnv(historical_data_dict=valid_data, initial_capital=initial_capital, max_steps=max_steps)
            env = Monitor(env) # Wrap with Monitor
            return env
        return _init

    # Create Vectorized Environments for Training
    VecEnvClass = DummyVecEnv if rl_config.N_ENVS == 1 else SubprocVecEnv
    train_env = None
    eval_env = None
    try:
        # Pass training_data to make_env for the training environments
        train_env = make_vec_env(
            make_env(training_data, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE),
            n_envs=rl_config.N_ENVS,
            vec_env_cls=VecEnvClass
        )
        logger.info(f"Created Training VecEnv with {rl_config.N_ENVS} environments.")

        # Create evaluation environment if eval_data exists
        if eval_data:
            # Pass eval_data to make_env for the evaluation environment
            eval_env = DummyVecEnv([make_env(eval_data, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE)])
            logger.info("Created Evaluation VecEnv.")
            # Optional: Check environment compatibility
            # try:
            #     check_env(eval_env.envs[0], warn=True)
            #     logger.info("Environment check passed.")
            # except Exception as check_err:
            #      logger.warning(f"Environment check failed: {check_err}", exc_info=True)

    except Exception as e:
        logger.exception(f"Error creating vectorized environments: {e}")
        if db_client: await db_client.close() # Ensure DB connection is closed
        return

    # --- Agent Setup ---
    # ... (Agent setup logic remains the same using AgentClass, rl_config, etc.) ...
    logger.info(f"Setting up RL Agent: {rl_config.RL_ALGORITHM}")
    AgentClass = globals().get(rl_config.RL_ALGORITHM)
    if AgentClass is None:
        logger.critical(f"RL Algorithm '{rl_config.RL_ALGORITHM}' not found.")
        if train_env: train_env.close()
        if eval_env: eval_env.close()
        if db_client: await db_client.close()
        return

    os.makedirs(rl_config.TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(rl_config.MODEL_SAVE_DIR, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"{rl_config.RL_ALGORITHM}_{run_timestamp}"

    model = AgentClass(
        "MlpPolicy",
        train_env,
        policy_kwargs=rl_config.POLICY_KWARGS,
        verbose=1,
        tensorboard_log=rl_config.TENSORBOARD_LOG_DIR,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.0,
        vf_coef=0.5,
        # seed=42
    )

    # --- Callbacks ---
    # ... (Callback setup logic remains the same, using eval_env if available) ...
    logger.info("Setting up Callbacks...")
    callbacks = []
    checkpoint_callback = CheckpointCallback(
        save_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1),
        save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_checkpoints"),
        name_prefix="rl_model"
    )
    callbacks.append(checkpoint_callback)

    if eval_env:
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best"),
            log_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best"),
            eval_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1),
            n_eval_episodes=rl_config.N_EVAL_EPISODES,
            deterministic=True,
            render=False,
            verbose=1
        )
        callbacks.append(eval_callback)
    else:
        logger.warning("EvalCallback disabled as evaluation environment could not be created.")


    # --- Training ---
    # ... (Training loop and saving logic remains the same) ...
    logger.info(f"Starting training for {rl_config.TOTAL_TIMESTEPS} timesteps...")
    start_train_time = time.time()
    try:
        model.learn(
            total_timesteps=rl_config.TOTAL_TIMESTEPS,
            callback=callbacks,
            tb_log_name=model_prefix,
            reset_num_timesteps=False
        )
    except Exception as learn_err:
        logger.exception(f"Error during model.learn(): {learn_err}")
    finally:
        end_train_time = time.time()
        logger.info(f"Training loop finished after {end_train_time - start_train_time:.2f} seconds.")
        final_model_path = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
        try:
            model.save(final_model_path)
            logger.info(f"Final trained model saved to: {final_model_path}")
        except Exception as save_err:
             logger.error(f"Failed to save final model: {save_err}")

    # --- Cleanup ---
    logger.info("Closing environments...")
    try:
        if train_env: train_env.close()
        if eval_env: eval_env.close()
    except Exception as close_err:
        logger.error(f"Error closing environments: {close_err}")

    if db_client: await db_client.close()
    logger.info("--- RL Agent Training Finished ---")


if __name__ == "__main__":
    # Important: If using SubprocVecEnv (N_ENVS > 1), ensure this guard is present
    # Use asyncio.run() to execute the async main training function
    # Ensure the loop policy is compatible if using SubprocVecEnv on Windows
    # if os.name == 'nt':
    #     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(train_rl_agent())