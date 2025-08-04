# FILE: scripts/train.py (REVISED)

import os
from datetime import datetime
import stable_baselines3 as sb3
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_rl_agent import rl_config as cfg
# Import the new environment
from trading_rl_agent.environments.solana_decision_env import SolanaDecisionEnv
# Import the new data loader
from scripts.data_utils import load_prepared_data_for_training
from bot_logger import setup_logging, logger

def train_agent():
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
    # It is crucial to normalize observations for neural networks.
    train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.)

    eval_env_kwargs = {'df': eval_df, 'full_token_data': all_token_data}
    eval_env = make_vec_env(SolanaDecisionEnv, n_envs=1, env_kwargs=eval_env_kwargs)
    eval_env = VecNormalize(eval_env, training=False, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.obs_rms = train_env.obs_rms # Use training stats for eval normalization

    # --- Configure Agent & Callbacks ---
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"{cfg.RL_ALGORITHM}_{run_timestamp}"
    
    model = sb3.PPO(
        cfg.POLICY_NAME,
        train_env,
        verbose=1,
        tensorboard_log=cfg.TENSORBOARD_LOG_DIR,
        **cfg.PPO_HYPERPARAMS
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.join(cfg.MODEL_SAVE_DIR, f"{model_prefix}_best"),
        log_path=os.path.join(cfg.MODEL_SAVE_DIR, f"{model_prefix}_eval_logs"),
        eval_freq=max(cfg.EVAL_FREQ // cfg.N_ENVS, 1),
        n_eval_episodes=cfg.N_EVAL_EPISODES,
        deterministic=True
    )

    # --- Start Training ---
    try:
        model.learn(
            total_timesteps=cfg.TOTAL_TIMESTEPS,
            callback=eval_callback,
            tb_log_name=model_prefix
        )
    finally:
        # --- Save Final Model and Environment Statistics ---
        model.save(os.path.join(cfg.MODEL_SAVE_DIR, f"{model_prefix}_final.zip"))
        train_env.save(os.path.join(cfg.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl"))
        logger.info("--- RL Agent Training Finished ---")

if __name__ == "__main__":
    # This allows running the training script directly
    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()
    train_agent()

