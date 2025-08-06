# rl_tools/scout_train.py
"""
Training script for the Scout (Decision Gate) RL Agent.

This script orchestrates the training process for the PPO agent responsible for
making the initial 'BUY' or 'IGNORE' decision on a new token opportunity.
It loads the prepared data, sets up the vectorized training and evaluation
environments, configures the agent with specified hyperparameters, and handles
the training loop, including callbacks for saving the best model.
"""

import os
import argparse
from datetime import datetime
import stable_baselines3 as sb3
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import rl_config as cfg
from rl_agent_framework.environments.solana_scout_env import SolanaDecisionEnv
from rl_tools.scout_data_preparation import load_prepared_scout_data
from bot_logger import setup_logging, logger

def train_scout_agent(continue_from_model: str = None, fine_tune: bool = False):
    """
    Main function to train the Scout RL agent.

    Args:
        continue_from_model (str, optional): Path to a .zip model file to continue training from.
        fine_tune (bool): If True and continuing, uses a lower learning rate.
    """
    setup_logging(logger_name="rl_scout_trainer")
    logger.info("--- Starting RL Agent Training (Scout Agent) ---")

    decision_df, all_token_data = load_prepared_scout_data()
    if decision_df is None or not all_token_data:
        logger.critical("No training data found. Run scout_data_preparation.py first. Exiting.")
        return

    train_df = decision_df.sample(frac=0.8, random_state=42)
    eval_df = decision_df.drop(train_df.index)

    train_env_kwargs = {'df': train_df, 'full_token_data': all_token_data}
    train_env = make_vec_env(
        SolanaDecisionEnv, n_envs=cfg.ScoutConfig.N_ENVS,
        env_kwargs=train_env_kwargs,
        vec_env_cls=SubprocVecEnv if cfg.ScoutConfig.N_ENVS > 1 else DummyVecEnv
    )
    
    eval_env_kwargs = {'df': eval_df, 'full_token_data': all_token_data}
    eval_env_raw = make_vec_env(SolanaDecisionEnv, n_envs=1, env_kwargs=eval_env_kwargs)

    model = None
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if continue_from_model:
        mode = "FINE-TUNING" if fine_tune else "CONTINUING TRAINING"
        logger.info(f"--- {mode} from model: {continue_from_model} ---")
        
        model_base_dir = os.path.dirname(continue_from_model)
        model_filename = os.path.basename(continue_from_model)
        if 'best_model.zip' in model_filename:
            model_base_dir = os.path.dirname(model_base_dir)
            model_prefix = os.path.basename(os.path.dirname(continue_from_model)).replace('_best', '')
        else:
            model_prefix = model_filename.replace('_final.zip', '')
            
        stats_path = os.path.join(model_base_dir, f"{model_prefix}_vecnormalize.pkl")

        if not os.path.exists(stats_path):
            logger.critical(f"VecNormalize stats file not found at {stats_path}. Cannot continue training.")
            return

        train_env = VecNormalize.load(stats_path, train_env)
        learning_rate = cfg.ScoutConfig.FINE_TUNE_LR if fine_tune else cfg.ScoutConfig.PPO_HYPERPARAMS["learning_rate"]
        
        model = sb3.PPO.load(
            continue_from_model, env=train_env,
            tensorboard_log=cfg.ScoutConfig.TENSORBOARD_LOG_DIR,
            learning_rate=learning_rate,
            device='cpu'
        )
        logger.info(f"Successfully loaded model and stats. New learning rate: {learning_rate}")
        run_timestamp = f"continued_{run_timestamp}"

    else:
        logger.info("--- STARTING NEW training session ---")
        train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.)
        model = sb3.PPO(
            cfg.ScoutConfig.POLICY_NAME, train_env, verbose=1,
            tensorboard_log=cfg.ScoutConfig.TENSORBOARD_LOG_DIR,
            device='cpu',
            **cfg.ScoutConfig.PPO_HYPERPARAMS
        )

    eval_env = VecNormalize(eval_env_raw, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.obs_rms = train_env.obs_rms

    model_prefix = f"{cfg.ScoutConfig.RL_ALGORITHM}_Scout_{run_timestamp}"
    best_model_save_path = os.path.join(cfg.ScoutConfig.MODEL_SAVE_DIR, f"{model_prefix}_best")
    
    eval_callback = EvalCallback(
        eval_env, best_model_save_path=best_model_save_path,
        log_path=os.path.join(best_model_save_path, "eval_logs"),
        eval_freq=max(cfg.ScoutConfig.EVAL_FREQ // cfg.ScoutConfig.N_ENVS, 1),
        n_eval_episodes=cfg.ScoutConfig.N_EVAL_EPISODES,
        deterministic=True
    )

    try:
        model.learn(
            total_timesteps=cfg.ScoutConfig.TOTAL_TIMESTEPS,
            callback=eval_callback,
            tb_log_name=model_prefix,
            reset_num_timesteps=not continue_from_model
        )
    finally:
        os.makedirs(cfg.ScoutConfig.MODEL_SAVE_DIR, exist_ok=True)
        final_model_path = os.path.join(cfg.ScoutConfig.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
        stats_path = os.path.join(cfg.ScoutConfig.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl")
        
        model.save(final_model_path)
        train_env.save(stats_path)
        
        logger.info(f"Final model saved to: {final_model_path}")
        logger.info(f"Normalization stats saved to: {stats_path}")
        logger.info("--- RL Scout Agent Training Finished ---")

if __name__ == "__main__":
    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()
    
    parser = argparse.ArgumentParser(description="Train the Scout RL Agent.")
    parser.add_argument("--continue-from-model", type=str, help="Path to the .zip model file to continue training from.")
    parser.add_argument("--fine-tune", action="store_true", help="Use a lower learning rate when continuing from a model.")
    args = parser.parse_args()

    train_scout_agent(continue_from_model=args.continue_from_model, fine_tune=args.fine_tune)
