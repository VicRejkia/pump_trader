# scripts/manager_train.py
"""
Training script for the Manager (Trade Management) RL Agent.
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

from bot_logger import setup_logging, logger
from config import rl_config_old as cfg
from rl_agent_framework.environments.solana_management_env import SolanaManagementEnv
from rl_tools.manager_data_preparation import load_prepared_manager_data

def train_manager_agent(data_window: str, continue_from_model: str = None, fine_tune: bool = False):
    """
    Main function to train the Manager RL agent.

    Args:
        data_window (str): The key for the data window to use from rl_config.py.
        continue_from_model (str, optional): Path to a .zip model file to continue training from.
        fine_tune (bool): If True and continuing, uses fine-tuning hyperparameters.
    """
    setup_logging(logger_name="rl_manager_trainer")
    logger.info(f"--- Starting RL Agent Training (Manager Agent) on '{data_window}' data ---")

    try:
        window = cfg.DATA_WINDOWS[data_window]
    except KeyError:
        logger.critical(f"Data window '{data_window}' not found in rl_config.py. Exiting.")
        return
        
    trade_lifecycles = load_prepared_manager_data(window['start'], window['end'])
    if not trade_lifecycles:
        logger.critical("No training data found for Manager agent. Run the data preparation pipeline first. Exiting.")
        return

    all_trade_ids = sorted(list(trade_lifecycles.keys()))
    train_size = int(0.8 * len(all_trade_ids))
    train_ids = all_trade_ids[:train_size]
    eval_ids = all_trade_ids[train_size:]

    train_data = {tid: trade_lifecycles[tid] for tid in train_ids}
    eval_data = {tid: trade_lifecycles[tid] for tid in eval_ids}

    logger.info(f"Data split: {len(train_data)} trades for training, {len(eval_data)} for evaluation.")

    train_env_kwargs = {'trade_lifecycles': train_data}
    eval_env_kwargs = {'trade_lifecycles': eval_data}
    
    train_env_raw = make_vec_env(
        SolanaManagementEnv, n_envs=cfg.ManagerConfig.N_ENVS,
        env_kwargs=train_env_kwargs,
        vec_env_cls=SubprocVecEnv if cfg.ManagerConfig.N_ENVS > 1 and os.name != 'nt' else DummyVecEnv
    )
    eval_env_raw = make_vec_env(SolanaManagementEnv, n_envs=1, env_kwargs=eval_env_kwargs)
    
    model = None
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hyperparams = cfg.ManagerConfig.PPO_FINETUNE_HYPERPARAMS if fine_tune else cfg.ManagerConfig.PPO_HYPERPARAMS
    
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
            logger.critical(f"VecNormalize stats file not found at {stats_path}. Cannot continue.")
            return

        train_env = VecNormalize.load(stats_path, train_env_raw)
        train_env.training = True
        train_env.norm_reward = True
        
        model = sb3.PPO.load(
            continue_from_model, env=train_env,
            tensorboard_log=cfg.ManagerConfig.TENSORBOARD_LOG_DIR,
            device='cpu',
            **hyperparams['model_params']
        )
        logger.info(f"Successfully loaded model and stats. Using learning rate: {model.learning_rate}")
        run_timestamp = f"continued_{run_timestamp}"
    else:
        logger.info("--- STARTING NEW training session ---")
        train_env = VecNormalize(train_env_raw, norm_obs=True, norm_reward=True, clip_obs=10.)
        model = sb3.PPO(
            cfg.ManagerConfig.POLICY_NAME, train_env, verbose=1,
            tensorboard_log=cfg.ManagerConfig.TENSORBOARD_LOG_DIR,
            device='cpu',
            **hyperparams['model_params']
        )

    eval_env = VecNormalize(eval_env_raw, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.obs_rms = train_env.obs_rms

    model_prefix = f"{cfg.ManagerConfig.RL_ALGORITHM}_Manager_{run_timestamp}"
    model_save_dir = os.path.join(cfg.ManagerConfig.MODEL_SAVE_DIR, model_prefix)
    
    eval_callback = EvalCallback(
        eval_env, best_model_save_path=model_save_dir,
        log_path=model_save_dir,
        eval_freq=max(hyperparams['learn_params']['eval_freq'] // cfg.ManagerConfig.N_ENVS, 1),
        n_eval_episodes=cfg.ManagerConfig.N_EVAL_EPISODES,
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
        
        logger.info(f"Final Manager model saved to: {final_model_path}")
        logger.info(f"Normalization stats saved to: {stats_path}")
        logger.info("--- RL Manager Agent Training Finished ---")

if __name__ == "__main__":
    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()
    
    parser = argparse.ArgumentParser(description="Train the Manager RL Agent.")
    parser.add_argument(
        "--data-window", type=str, default=cfg.DEFAULT_DATA_WINDOW,
        choices=cfg.DATA_WINDOWS.keys(),
        help="The data window to use for training."
    )
    parser.add_argument(
        "--continue-from-model", type=str, 
        help="Path to the .zip model file to continue training from."
    )
    parser.add_argument(
        "--fine-tune", action="store_true",
        help="Use fine-tuning hyperparameters when continuing from a model."
    )
    args = parser.parse_args()

    train_manager_agent(data_window=args.data_window, continue_from_model=args.continue_from_model, fine_tune=args.fine_tune)