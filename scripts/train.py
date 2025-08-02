# FILE: scripts/train.py

import os
import argparse
from datetime import datetime
import stable_baselines3 as sb3
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback

# Add the project root to the Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_rl_agent import rl_config
from trading_rl_agent.environments.solana_env import SolanaPortfolioEnv
from trading_rl_agent.policies.custom_nets import CustomCombinedExtractor
from scripts.data_utils import load_processed_data
from bot_logger import setup_logging, logger

def train_agent(continue_from_id: str = None):
    """
    Main function to set up and run the RL agent training process.
    """
    setup_logging(logger_name="rl_trainer")
    logger.info("--- Starting RL Agent Training ---")

    # --- Load Data ---
    training_data = load_processed_data(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = load_processed_data(rl_config.DATA_SET_KEY_EVAL)
    
    if not training_data:
        logger.critical("No training data found. Run data_utils.py first. Exiting.")
        return
    if not eval_data:
        logger.warning("No evaluation data found. Evaluation callback will be disabled.")

    # --- Create Vectorized Environments ---
    # Training environment
    train_env_kwargs = {'token_data_map': training_data}
    train_env = make_vec_env(
        SolanaPortfolioEnv,
        n_envs=rl_config.N_ENVS,
        env_kwargs=train_env_kwargs,
        vec_env_cls=SubprocVecEnv if rl_config.N_ENVS > 1 else DummyVecEnv
    )
    # It is crucial to normalize observations for neural networks.
    train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.)

    # Evaluation environment
    eval_env_instance = None
    if eval_data:
        eval_env_kwargs = {'token_data_map': eval_data}
        eval_env = make_vec_env(SolanaPortfolioEnv, n_envs=1, env_kwargs=eval_env_kwargs)
        # Use the stats from the training environment for normalization
        eval_env_instance = VecNormalize(eval_env, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)

    # --- Configure Agent & Callbacks ---
    os.makedirs(rl_config.TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(rl_config.MODEL_SAVE_DIR, exist_ok=True)

    model = None

    # Loading logic based on the ID
    if continue_from_id:
        logger.info(f"--- Attempting to continue training from ID: {continue_from_id} ---")
        
        # Construct paths automatically
        model_path = os.path.join(rl_config.MODEL_SAVE_DIR, f"{continue_from_id}_final.zip")
        stats_path = os.path.join(rl_config.MODEL_SAVE_DIR, f"{continue_from_id}_vecnormalize.pkl")

        # Verify that both required files exist
        if not os.path.exists(model_path) or not os.path.exists(stats_path):
            logger.critical(f"Could not find model/stats files for ID '{continue_from_id}'. Searched for:")
            logger.critical(f"  - Model: {model_path}")
            logger.critical(f"  - Stats: {stats_path}")
            return
        
        # Load the existing model, pointing it to the correct environment
        model = sb3.PPO.load(
            model_path,
            env=train_env,
            tensorboard_log=rl_config.TENSORBOARD_LOG_DIR,
            learning_rate=rl_config.PPO_HYPERPARAMS.get("learning_rate") # Use new LR from config
        )
        
        # Load and apply the normalization stats to the environment
        train_env = VecNormalize.load(stats_path, train_env)
        logger.info("Successfully loaded model and normalization stats.")
        
        run_timestamp = f"continued_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    else:
        logger.info("--- Starting New Training Session ---")
        policy_kwargs = rl_config.POLICY_KWARGS
        policy_kwargs['features_extractor_class'] = CustomCombinedExtractor
        
        model = sb3.PPO(
            rl_config.POLICY_NAME,
            train_env,
            policy_kwargs=policy_kwargs,
            verbose=1,
            tensorboard_log=rl_config.TENSORBOARD_LOG_DIR,
            **rl_config.PPO_HYPERPARAMS
        )
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    model_prefix = f"{rl_config.RL_ALGORITHM}_{run_timestamp}"
        
    callbacks = []
    if eval_env_instance:
        eval_callback = EvalCallback(
            eval_env_instance,
            best_model_save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best"),
            log_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_eval_logs"),
            eval_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1),
            n_eval_episodes=rl_config.N_EVAL_EPISODES,
            deterministic=True
        )
        callbacks.append(eval_callback)

    # --- Start Training ---
    try:
        model.learn(
            total_timesteps=rl_config.TOTAL_TIMESTEPS,
            callback=callbacks,
            tb_log_name=model_prefix
        )
    except KeyboardInterrupt:
        logger.warning("Training interrupted by user.")
    finally:
        # --- Save Final Model and Environment Statistics ---
        final_model_path = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
        model.save(final_model_path)
        
        # Save the normalization statistics
        vec_normalize_stats_path = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl")
        train_env.save(vec_normalize_stats_path)
        
        logger.info(f"Final model saved to: {final_model_path}")
        logger.info(f"Normalization stats saved to: {vec_normalize_stats_path}")
        
        train_env.close()
        if eval_env_instance:
            eval_env_instance.close()
            
        logger.info("--- RL Agent Training Finished ---")

if __name__ == "__main__":
    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()
    
    # 4. Update the parser to use the new, simpler argument
    parser = argparse.ArgumentParser(description="Train an RL Agent.")
    parser.add_argument(
        "--continue-from-id", 
        type=str, 
        help="The ID (prefix) of the model to continue training from (e.g., 'PPO_20250801_153000')."
    )
    args = parser.parse_args()

    train_agent(continue_from_id=args.continue_from_id)