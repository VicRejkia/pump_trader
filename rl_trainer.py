# FILE: rl_trainer.py

"""
Reinforcement Learning Agent Trainer

Loads data, sets up the RL environment, configures and trains
an RL agent (e.g., PPO from Stable Baselines3), and saves the result.
"""
import os
import asyncio
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Select RL framework - Stable Baselines3
try:
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
# Need a way to load the split data - reuse GA's or create new logic
# Assuming ga_optimizer structure can be adapted or reused
try:
     from ga_optimizer import load_and_split_data, historical_data_sets, db_client as ga_db_client
     db_client = ga_db_client # Share the client if running together potentially
except ImportError:
     logger.warning("Could not import from ga_optimizer. Need separate data loading logic for RL.")
     historical_data_sets = {} # Ensure it's defined
     db_client = None # Ensure it's defined


async def train_rl_agent():
    """Main function to set up and train the RL agent."""
    global db_client, historical_data_sets
    setup_logging()
    logger.info("--- Starting RL Agent Training ---")

    # --- Database Connection & Data Loading ---
    if not db_client:
        db_client = DatabaseClient()
        try:
            await db_client.connect()
            logger.info("DB Client connected for RL Trainer.")
        except Exception as e:
            logger.critical(f"Failed to connect database for RL Trainer: {e}")
            return

    # Load and split data using the date range from rl_config
    start_date_str = rl_config.RL_HISTORICAL_DATA_START_TS.strftime('%Y-%m-%d')
    end_date_str = rl_config.RL_HISTORICAL_DATA_END_TS.strftime('%Y-%m-%d')

    logger.info(f"Loading data from {start_date_str} to {end_date_str} using RL config dates.")
    # Use the load_and_split_data function (ensure it uses rl_config splits if different)
    # We might need to adapt load_and_split_data or create a specific one for RL splits
    if not await load_and_split_data(start_date_str, end_date_str): # Assumes this uses DATA_SPLIT_RL internally now or needs modification
        logger.critical("Failed to load or split data for RL training. Exiting.")
        await db_client.close()
        return

    training_data = historical_data_sets.get(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = historical_data_sets.get(rl_config.DATA_SET_KEY_EVAL)

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
    def make_env(data_dict, initial_capital, max_steps):
        def _init():
            env = TradingEnv(historical_data_dict=data_dict, initial_capital=initial_capital, max_steps=max_steps)
            # IMPORTANT: Wrap the env with Monitor for SB3 logging/evaluation
            env = Monitor(env)
            return env
        return _init

    # Create Vectorized Environments for Training
    # Use DummyVecEnv for debugging, SubprocVecEnv for performance (requires __main__ guard)
    VecEnvClass = DummyVecEnv if rl_config.N_ENVS == 1 else SubprocVecEnv
    try:
        train_env = make_vec_env(
            make_env(training_data, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE),
            n_envs=rl_config.N_ENVS,
            vec_env_cls=VecEnvClass
        )
        logger.info(f"Created Training VecEnv with {rl_config.N_ENVS} environments.")
    except Exception as e:
        logger.exception(f"Error creating training vectorized environment: {e}")
        await db_client.close()
        return

    # Create a separate environment for evaluation
    eval_env = None
    if eval_data:
        try:
            # Evaluation usually runs on a single environment
            eval_env = DummyVecEnv([make_env(eval_data, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE)])
            logger.info("Created Evaluation VecEnv.")

            # Optional: Check the custom environment compatibility with SB3
            # logger.info("Checking environment compatibility...")
            # check_env(eval_env.envs[0], warn=True) # Check the underlying single env
            # logger.info("Environment check passed.")

        except Exception as e:
            logger.exception(f"Error creating evaluation environment: {e}")
            # Continue without eval_env if creation fails


    # --- Agent Setup ---
    logger.info(f"Setting up RL Agent: {rl_config.RL_ALGORITHM}")
    AgentClass = globals().get(rl_config.RL_ALGORITHM) # Get class from globals() e.g., PPO
    if AgentClass is None:
        logger.critical(f"RL Algorithm '{rl_config.RL_ALGORITHM}' not found in Stable Baselines3.")
        await db_client.close()
        return

    os.makedirs(rl_config.TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(rl_config.MODEL_SAVE_DIR, exist_ok=True)

    # Define file prefix for saved models/logs
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"{rl_config.RL_ALGORITHM}_{run_timestamp}"

    model = AgentClass(
        "MlpPolicy", # Assuming Multi-Layer Perceptron policy
        train_env,
        policy_kwargs=rl_config.POLICY_KWARGS,
        verbose=1,
        tensorboard_log=rl_config.TENSORBOARD_LOG_DIR,
        # Add other hyperparameters specific to the chosen algorithm here
        # e.g., for PPO: n_steps=2048, batch_size=64, n_epochs=10, gamma=0.99, gae_lambda=0.95, ...
        n_steps=2048, # Common default for PPO
        batch_size=64, # Common default for PPO
        n_epochs=10, # Common default for PPO
        gamma=0.99, # Discount factor
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.0, # Entropy coefficient (can regularize exploration)
        vf_coef=0.5, # Value function coefficient
        # seed=42 # Optional: for reproducibility
    )

    # --- Callbacks ---
    logger.info("Setting up Callbacks...")
    callbacks = []

    # Checkpoint callback to save model periodically
    checkpoint_callback = CheckpointCallback(
        save_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1), # Adjust save freq based on n_envs
        save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_checkpoints"),
        name_prefix="rl_model"
    )
    callbacks.append(checkpoint_callback)

    # Evaluation callback
    if eval_env:
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best"),
            log_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best"),
            eval_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1), # Adjust eval freq based on n_envs
            n_eval_episodes=rl_config.N_EVAL_EPISODES,
            deterministic=True,
            render=False,
            verbose=1
        )
        callbacks.append(eval_callback)
    else:
        logger.warning("EvalCallback disabled as evaluation environment could not be created.")

    # Example: Stop training if average reward reaches a threshold
    # reward_threshold_callback = StopTrainingOnRewardThreshold(reward_threshold=10.0, verbose=1) # Adjust threshold
    # callbacks.append(reward_threshold_callback)


    # --- Training ---
    logger.info(f"Starting training for {rl_config.TOTAL_TIMESTEPS} timesteps...")
    start_train_time = time.time()
    try:
        model.learn(
            total_timesteps=rl_config.TOTAL_TIMESTEPS,
            callback=callbacks,
            tb_log_name=model_prefix, # Log under a specific name in TensorBoard
            reset_num_timesteps=False # Set to True if continuing training
        )
    except Exception as learn_err:
        logger.exception(f"Error during model.learn(): {learn_err}")
    finally:
        end_train_time = time.time()
        logger.info(f"Training loop finished after {end_train_time - start_train_time:.2f} seconds.")

        # --- Save Final Model ---
        final_model_path = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
        try:
            model.save(final_model_path)
            logger.info(f"Final trained model saved to: {final_model_path}")
        except Exception as save_err:
             logger.error(f"Failed to save final model: {save_err}")


    # --- Cleanup ---
    logger.info("Closing environments...")
    try:
        train_env.close()
        if eval_env:
            eval_env.close()
    except Exception as close_err:
        logger.error(f"Error closing environments: {close_err}")

    await db_client.close()
    logger.info("--- RL Agent Training Finished ---")


if __name__ == "__main__":
    # Important: If using SubprocVecEnv (N_ENVS > 1), the training
    # needs to be run inside this __main__ guard for multiprocessing safety.
    # Use asyncio.run() to execute the async main training function
    asyncio.run(train_rl_agent())