# scripts/manager_train.py
"""
Training script for the Manager (Trade Management) RL Agent.

This script trains the PPO agent responsible for making the 'HOLD' or 'SELL'
decision for an open trade. It loads the pre-processed trade lifecycle data,
sets up the training and evaluation environments, configures the agent, and
manages the training loop and model saving.
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
# Import from the new centralized config
from config import rl_config as cfg
from rl_agent_framework.environments.solana_management_env import SolanaManagementEnv
from rl_tools.manager_data_preparation import load_prepared_manager_data

def train_manager_agent(continue_from_model: str = None, fine_tune: bool = False):
    """
    Main function to train the Manager RL agent.

    Args:
        continue_from_model (str, optional): Path to a .zip model file to continue training from.
        fine_tune (bool): If True and continuing, uses a lower learning rate.
    """
    setup_logging(logger_name="rl_manager_trainer")
    logger.info("--- Starting RL Agent Training (Manager Agent) ---")

    # --- Load Data ---
    trade_lifecycles = load_prepared_manager_data()
    if not trade_lifecycles:
        logger.critical("No training data found for Manager agent. Run manager_data_preparation.py first. Exiting.")
        return

    all_trade_ids = list(trade_lifecycles.keys())
    train_size = int(0.8 * len(all_trade_ids))
    train_ids = all_trade_ids[:train_size]
    eval_ids = all_trade_ids[train_size:]

    train_data = {tid: trade_lifecycles[tid] for tid in train_ids}
    eval_data = {tid: trade_lifecycles[tid] for tid in eval_ids}

    logger.info(f"Data split: {len(train_data)} trades for training, {len(eval_data)} for evaluation.")

    # --- Create Vectorized Environments ---
    train_env_kwargs = {'trade_lifecycles': train_data}
    eval_env_kwargs = {'trade_lifecycles': eval_data}
    
    train_env_raw = make_vec_env(
        SolanaManagementEnv, n_envs=cfg.ManagerConfig.N_ENVS,
        env_kwargs=train_env_kwargs,
        vec_env_cls=SubprocVecEnv if cfg.ManagerConfig.N_ENVS > 1 else DummyVecEnv
    )
    eval_env_raw = make_vec_env(SolanaManagementEnv, n_envs=1, env_kwargs=eval_env_kwargs)

    # --- Configure Agent, Callbacks, and Normalization ---
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
            logger.critical(f"VecNormalize stats file not found at {stats_path}. Cannot continue.")
            return

        train_env = VecNormalize.load(stats_path, train_env_raw)
        learning_rate = cfg.ManagerConfig.FINE_TUNE_LR if fine_tune else cfg.ManagerConfig.PPO_HYPERPARAMS["learning_rate"]
        
        model = sb3.PPO.load(
            continue_from_model,
            env=train_env,
            tensorboard_log=cfg.ManagerConfig.TENSORBOARD_LOG_DIR,
            learning_rate=learning_rate,
            device='cpu'
        )
        logger.info(f"Successfully loaded model and stats. New learning rate: {learning_rate}")
        run_timestamp = f"continued_{run_timestamp}"
    else:
        logger.info("--- STARTING NEW training session ---")
        train_env = VecNormalize(train_env_raw, norm_obs=True, norm_reward=True, clip_obs=10.)
        model = sb3.PPO(
            cfg.ManagerConfig.POLICY_NAME, train_env, verbose=1,
            tensorboard_log=cfg.ManagerConfig.TENSORBOARD_LOG_DIR,
            device='cpu',
            **cfg.ManagerConfig.PPO_HYPERPARAMS
        )

    eval_env = VecNormalize(eval_env_raw, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.obs_rms = train_env.obs_rms

    model_prefix = f"{cfg.ManagerConfig.RL_ALGORITHM}_Manager_{run_timestamp}"
    best_model_save_path = os.path.join(cfg.ManagerConfig.MODEL_SAVE_DIR, f"{model_prefix}_best")
    
    eval_callback = EvalCallback(
        eval_env, best_model_save_path=best_model_save_path,
        log_path=os.path.join(best_model_save_path, "eval_logs"),
        eval_freq=max(cfg.ManagerConfig.EVAL_FREQ // cfg.ManagerConfig.N_ENVS, 1),
        n_eval_episodes=cfg.ManagerConfig.N_EVAL_EPISODES,
        deterministic=True
    )

    # --- Start Training ---
    try:
        model.learn(
            total_timesteps=cfg.ManagerConfig.TOTAL_TIMESTEPS,
            callback=eval_callback,
            tb_log_name=model_prefix,
            reset_num_timesteps=not continue_from_model
        )
    finally:
        os.makedirs(cfg.ManagerConfig.MODEL_SAVE_DIR, exist_ok=True)
        final_model_path = os.path.join(cfg.ManagerConfig.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
        stats_path = os.path.join(cfg.ManagerConfig.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl")
        
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
        "--continue-from-model", type=str, 
        help="Path to the .zip model file to continue training from."
    )
    parser.add_argument(
        "--fine-tune", action="store_true",
        help="Use a lower learning rate when continuing from a model."
    )
    args = parser.parse_args()

    train_manager_agent(continue_from_model=args.continue_from_model, fine_tune=args.fine_tune)
