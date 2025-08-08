# rl_tools/scout_train.py
"""
Training script for the Scout (Decision Gate) RL Agent.
...
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

def train_scout_agent(data_window: str, continue_from_model: str = None, fine_tune: bool = False):
    """
    Main function to train the Scout RL agent.

    Args:
        data_window (str): The key for the data window to use from rl_config.py (e.g., 'test', 'full').
        continue_from_model (str, optional): Path to a .zip model file to continue training from.
        fine_tune (bool): If True and continuing, uses fine-tuning hyperparameters.
    """
    setup_logging(logger_name="rl_scout_trainer")
    logger.info(f"--- Starting RL Agent Training (Scout Agent) on '{data_window}' data ---")
    
    try:
        window = cfg.DATA_WINDOWS[data_window]
    except KeyError:
        logger.critical(f"Data window '{data_window}' not found in rl_config.py. Exiting.")
        return
        
    decision_df, ohlcv_dir = load_prepared_scout_data(window['start'], window['end'])
    if decision_df is None or ohlcv_dir is None:
        logger.critical("No training data found. Run the data preparation pipeline first. Exiting.")
        return

    train_df = decision_df.sample(frac=0.8, random_state=42)
    eval_df = decision_df.drop(train_df.index)

    logger.info(f"Data split: {len(train_df)} decisions for training, {len(eval_df)} for evaluation.")

    train_env_kwargs = {'df': train_df, 'ohlcv_data_dir': ohlcv_dir}
    train_env_raw = make_vec_env(
        SolanaDecisionEnv, n_envs=cfg.ScoutConfig.N_ENVS,
        env_kwargs=train_env_kwargs,
        vec_env_cls=SubprocVecEnv if cfg.ScoutConfig.N_ENVS > 1 and os.name != 'nt' else DummyVecEnv
    )
    
    eval_env_kwargs = {'df': eval_df, 'ohlcv_data_dir': ohlcv_dir}
    eval_env_raw = make_vec_env(SolanaDecisionEnv, n_envs=1, env_kwargs=eval_env_kwargs)

    model = None
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hyperparams = cfg.ScoutConfig.PPO_FINETUNE_HYPERPARAMS if fine_tune else cfg.ScoutConfig.PPO_HYPERPARAMS

    if continue_from_model:
        continue_from_model = os.path.abspath(continue_from_model)
        mode = "FINE-TUNING" if fine_tune else "CONTINUING TRAINING"
        logger.info(f"--- {mode} from model: {continue_from_model} ---")
        
        # --- MODIFIED: Simplified and corrected path derivation logic ---
        # The base directory is simply the directory containing the selected model file.
        model_base_dir = os.path.dirname(continue_from_model)
        
        # The prefix is the name of that directory.
        model_prefix = os.path.basename(model_base_dir)
        stats_path = os.path.join(model_base_dir, f"{model_prefix}_vecnormalize.pkl")
        # --- END MODIFICATION ---

        if not os.path.exists(stats_path):
            logger.critical(f"VecNormalize stats file not found at {stats_path}. Cannot continue training.")
            return

        train_env = VecNormalize.load(stats_path, train_env_raw)
        train_env.training = True
        train_env.norm_reward = True
        
        model = sb3.PPO.load(
            continue_from_model, env=train_env,
            tensorboard_log=cfg.ScoutConfig.TENSORBOARD_LOG_DIR,
            device='cpu',
            **hyperparams['model_params']
        )
        logger.info(f"Successfully loaded model and stats. Using learning rate: {model.learning_rate}")
        run_timestamp = f"continued_{run_timestamp}"

    else:
        logger.info("--- STARTING NEW training session ---")
        train_env = VecNormalize(train_env_raw, norm_obs=True, norm_reward=True, clip_obs=10.)
        model = sb3.PPO(
            cfg.ScoutConfig.POLICY_NAME, train_env, verbose=1,
            tensorboard_log=cfg.ScoutConfig.TENSORBOARD_LOG_DIR,
            device='cpu',
            **hyperparams['model_params']
        )

    eval_env = VecNormalize(eval_env_raw, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.obs_rms = train_env.obs_rms

    model_prefix = f"{cfg.ScoutConfig.RL_ALGORITHM}_Scout_{run_timestamp}"
    model_save_dir = os.path.join(cfg.ScoutConfig.MODEL_SAVE_DIR, model_prefix)
    
    eval_callback = EvalCallback(
        eval_env, best_model_save_path=model_save_dir,
        log_path=model_save_dir,
        eval_freq=max(hyperparams['learn_params']['eval_freq'] // cfg.ScoutConfig.N_ENVS, 1),
        n_eval_episodes=cfg.ScoutConfig.N_EVAL_EPISODES,
        deterministic=True
    )

    try:
        model.learn(
            total_timesteps=hyperparams['learn_params']['total_timesteps'],
            callback=eval_callback,
            tb_log_name=model_prefix,
            reset_num_timesteps=not continue_from_model
        )
    finally:
        os.makedirs(model_save_dir, exist_ok=True)
        final_model_path = os.path.join(model_save_dir, f"{model_prefix}_final.zip")
        stats_path = os.path.join(model_save_dir, f"{model_prefix}_vecnormalize.pkl")
        
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
    parser.add_argument(
        "--data-window", type=str, default=cfg.DEFAULT_DATA_WINDOW,
        choices=cfg.DATA_WINDOWS.keys(),
        help="The data window to use for training."
    )
    parser.add_argument("--continue-from-model", type=str, help="Path to the .zip model file to continue training from.")
    parser.add_argument("--fine-tune", action="store_true", help="Use fine-tuning hyperparameters when continuing from a model.")
    args = parser.parse_args()

    train_scout_agent(data_window=args.data_window, continue_from_model=args.continue_from_model, fine_tune=args.fine_tune)