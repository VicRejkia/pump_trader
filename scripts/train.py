import os
import argparse
from datetime import datetime
import stable_baselines3 as sb3
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_rl_agent import rl_config as cfg
from trading_rl_agent.environments.solana_decision_env import SolanaDecisionEnv
from scripts.data_utils import load_prepared_data_for_training
from bot_logger import setup_logging, logger

def train_agent(continue_from_model: str = None):
    """
    Main function to train the RL agent.

    Args:
        continue_from_model (str, optional): Path to a .zip model file to continue training from.
    """
    setup_logging(logger_name="rl_trainer")
    logger.info("--- Starting RL Agent Training (Decision Gate Mode) ---")

    # --- Load Data ---
    decision_df, all_token_data = load_prepared_data_for_training()
    if decision_df is None or not all_token_data:
        logger.critical("No training data found. Run data_utils.py first. Exiting.")
        return

    # Split decision_df for training and evaluation
    train_df = decision_df.sample(frac=0.8, random_state=42)
    eval_df = decision_df.drop(train_df.index)

    # --- Create Vectorized Environments ---
    train_env_kwargs = {'df': train_df, 'full_token_data': all_token_data}
    train_env = make_vec_env(
        SolanaDecisionEnv,
        n_envs=cfg.N_ENVS,
        env_kwargs=train_env_kwargs,
        vec_env_cls=SubprocVecEnv if cfg.N_ENVS > 1 else DummyVecEnv
    )
    # VecNormalize is applied differently depending on whether we are starting fresh or continuing
    
    eval_env_kwargs = {'df': eval_df, 'full_token_data': all_token_data}
    eval_env_raw = make_vec_env(SolanaDecisionEnv, n_envs=1, env_kwargs=eval_env_kwargs)

    # --- Configure Agent & Callbacks ---
    model = None
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if continue_from_model:
        logger.info(f"--- CONTINUING TRAINING from model: {continue_from_model} ---")
        
        # Construct path to the normalization stats file
        model_base_dir = ""
        model_prefix = ""
        if 'best_model.zip' in continue_from_model:
            # Path is like .../rl_models/PPO_..._best/best_model.zip
            # The stats file is in the parent directory of the model's directory
            model_dir = os.path.dirname(continue_from_model)
            model_base_dir = os.path.dirname(model_dir)
            model_prefix = os.path.basename(model_dir).replace('_best', '')
        else:
            # Path is like .../rl_models/PPO_..._final.zip
            # The stats file is in the same directory as the model
            model_base_dir = os.path.dirname(continue_from_model)
            model_filename = os.path.basename(continue_from_model)
            model_prefix = model_filename.replace('_final.zip', '')

        stats_path = os.path.join(model_base_dir, f"{model_prefix}_vecnormalize.pkl")

        if not os.path.exists(stats_path):
            logger.critical(f"VecNormalize stats file not found at {stats_path}. Cannot continue training.")
            return

        # Load the normalization stats into the new training environment
        train_env = VecNormalize.load(stats_path, train_env)
        
        # Load the model, associating it with the new (normalized) environment
        model = sb3.PPO.load(
            continue_from_model,
            env=train_env,
            tensorboard_log=cfg.TENSORBOARD_LOG_DIR,
            # You can optionally set a new, lower learning rate for fine-tuning
            learning_rate=cfg.PPO_HYPERPARAMS.get("learning_rate", 3e-4) 
        )
        logger.info("Successfully loaded model and normalization stats for fine-tuning.")
        run_timestamp = f"continued_{run_timestamp}"

    else:
        logger.info("--- STARTING NEW training session ---")
        # If starting fresh, create a new VecNormalize wrapper
        train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.)
        
        model = sb3.PPO(
            cfg.POLICY_NAME,
            train_env,
            verbose=1,
            tensorboard_log=cfg.TENSORBOARD_LOG_DIR,
            **cfg.PPO_HYPERPARAMS
        )

    # Setup evaluation environment with the correct normalization stats
    eval_env = VecNormalize(eval_env_raw, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.obs_rms = train_env.obs_rms # Use the training environment's running mean and std

    model_prefix = f"{cfg.RL_ALGORITHM}_{run_timestamp}"
    # Corrected save path for best model to be inside its own folder
    best_model_save_path = os.path.join(cfg.MODEL_SAVE_DIR, f"{model_prefix}_best")
    
    # --- THIS IS THE FIX: Removed the unsupported 'name_prefix' argument ---
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=best_model_save_path,
        log_path=os.path.join(best_model_save_path, "eval_logs"), # Log inside the best model folder
        eval_freq=max(cfg.EVAL_FREQ // cfg.N_ENVS, 1),
        n_eval_episodes=cfg.N_EVAL_EPISODES,
        deterministic=True
    )

    # --- Start Training ---
    try:
        model.learn(
            total_timesteps=cfg.TOTAL_TIMESTEPS,
            callback=eval_callback,
            tb_log_name=model_prefix,
            reset_num_timesteps=not continue_from_model # Don't reset counter if continuing
        )
    finally:
        # --- Save Final Model and Environment Statistics ---
        final_model_path = os.path.join(cfg.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
        stats_path = os.path.join(cfg.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl")
        
        model.save(final_model_path)
        train_env.save(stats_path)
        
        logger.info(f"Final model saved to: {final_model_path}")
        logger.info(f"Normalization stats saved to: {stats_path}")
        logger.info("--- RL Agent Training Finished ---")

if __name__ == "__main__":
    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()
    
    # Add command-line argument parsing
    parser = argparse.ArgumentParser(description="Train an RL Agent for Solana Trading.")
    parser.add_argument(
        "--continue-from-model", 
        type=str, 
        help="Path to the .zip model file to continue training from."
    )
    args = parser.parse_args()

    train_agent(continue_from_model=args.continue_from_model)
