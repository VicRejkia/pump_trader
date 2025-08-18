# rl_agent/evaluation/feature_importance.py
"""
Calculates Permutation Feature Importance using a robust "episode-per-token" strategy.

This script runs a backtest for multiple individual tokens to establish a baseline.
It then shuffles a feature for each token, re-runs the backtest, and averages the
performance drop across all tokens to determine the feature's importance. This
method ensures that the shuffled data directly impacts each evaluation episode.
"""

import argparse
import asyncio
import os
import json
from datetime import datetime, timezone 
import numpy as np
import pandas as pd
import random
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

# --- Project-specific imports ---
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
import config.rl_config as rl_cfg
from rl_agent.data.data_manager import DataManager
from rl_agent.data.cache_manager import CacheManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv, FEATURE_COLUMNS

import nest_asyncio
nest_asyncio.apply()


def run_single_token_episode(model: PPO, env: MemeCoinEnv) -> float:
    """Runs one full episode on the data currently loaded in the env and returns the final reward."""
    obs, _ = env.reset()
    done = False
    total_reward = 0.0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        done = terminated or truncated
    return total_reward


async def run_feature_importance(model_path: str, start_date_str: str, end_date_str: str, n_tokens: int):
    """Main orchestration function for the feature importance evaluation process."""
    logger.info("🚀 Starting Permutation Feature Importance Analysis (Episode-per-Token Strategy)...")
    
    db_client = None
    try:
        # 1. --- Data Loading and Preparation ---
        db_client = DatabaseClient()
        await db_client.connect()
        start_ts = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        end_ts = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))

        cache_manager = CacheManager(db_client, start_ts, end_ts)
        if not await cache_manager.is_cache_valid():
            logger.info("Cache not found or invalid. Generating...")
            full_data_manager = DataManager(db_client, start_date=start_ts, end_date=end_ts)
            await full_data_manager.load_and_prepare_data()

        logger.info("Loading evaluation token data from cache...")
        cached_data = cache_manager.load_from_cache()
        eval_token_dfs = cached_data.get('evaluation_set')

        if not eval_token_dfs:
            logger.error("Could not load evaluation set from cache. Aborting.")
            return

        token_mints = list(eval_token_dfs.keys())
        if len(token_mints) < n_tokens:
            logger.warning(f"Requested {n_tokens} tokens, but only {len(token_mints)} available in evaluation set.")
            n_tokens = len(token_mints)
        
        eval_sample_mints = random.sample(token_mints, n_tokens)
        logger.info(f"Using a random sample of {n_tokens} tokens for analysis.")

        # 2. --- Load Model, Config, and create a single Env instance ---
        logger.info(f"Loading pre-trained model from {model_path}...")
        model = PPO.load(model_path, device=rl_cfg.DEVICE)
        rl_config_dict = {key: getattr(rl_cfg, key) for key in dir(rl_cfg) if key.isupper()}
        
        # Pass the already-created cache_manager to the DataManager.
        # This allows it to initialize correctly without needing a db_client.
        data_manager = DataManager(cache_manager=cache_manager)
        env = Monitor(MemeCoinEnv(data_manager, rl_config_dict, silent=True))

        # 3. --- Establish Baseline Performance ---
        logger.info(f"Calculating baseline performance across {n_tokens} tokens...")
        baseline_rewards = []
        for mint in eval_sample_mints:
            token_df = eval_token_dfs[mint]
            
            # This correctly sets the data for the next episode. The environment's reset()
            # will now use this DataFrame.
            data_manager.evaluation_data = token_df
            
            reward = run_single_token_episode(model, env)
            baseline_rewards.append(reward)
        
        baseline_mean_reward = np.mean(baseline_rewards)
        logger.info(f"✅ Baseline Mean Reward: {baseline_mean_reward:.4f}")

        # 4. --- Permutation Loop ---
        importances = {}
        for feature in FEATURE_COLUMNS:
            logger.info(f"   Shuffling feature: '{feature}'...")
            shuffled_rewards = []
            for mint in eval_sample_mints:
                original_df = eval_token_dfs[mint]
                shuffled_df = original_df.copy()
                shuffled_df[feature] = np.random.permutation(shuffled_df[feature].values)
                
                # Set the shuffled data for the next episode.
                data_manager.evaluation_data = shuffled_df

                reward = run_single_token_episode(model, env)
                shuffled_rewards.append(reward)

            shuffled_mean_reward = np.mean(shuffled_rewards)
            importances[feature] = baseline_mean_reward - shuffled_mean_reward
            logger.info(f"    ↳ Shuffled Mean Reward: {shuffled_mean_reward:.4f} | Importance (Drop): {importances[feature]:.4f}")

        # 5. --- Report Results to Console ---
        sorted_importances = sorted(importances.items(), key=lambda x: x[1], reverse=True)
        
        print("\n" + "="*60)
        logger.info("📊 Permutation Feature Importance Results 📊")
        print("="*60)
        logger.info("Features are ranked by the average drop in reward across all tested tokens.")
        logger.info("A larger, positive value indicates higher importance.\n")
        
        for feature, importance in sorted_importances:
            print(f"{feature:<25} | Importance: {importance:.4f}")
        print("="*60)

        # 6. --- NEW: Save Results to JSON File ---
        results_data = {
            "analysis_metadata": {
                "description": "Permutation feature importance results.",
                "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "model_path": model_path,
                "evaluation_settings": {
                    "n_tokens_sampled": n_tokens,
                    "data_start_date": start_date_str,
                    "data_end_date": end_date_str
                }
            },
            "baseline_mean_reward": baseline_mean_reward,
            "feature_importance_results": [
                {"feature": feature, "importance_drop": importance}
                for feature, importance in sorted_importances
            ]
        }

        # Construct a descriptive filename
        model_basename = os.path.splitext(os.path.basename(model_path))[0]
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_filename = f"feature_importance_{timestamp}_{model_basename}.json"
        output_path = os.path.join(rl_cfg.RL_MODELS_DIR, output_filename)

        os.makedirs(rl_cfg.RL_MODELS_DIR, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=4)

        logger.info(f"💾 Feature importance results saved to: {output_path}")

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if db_client:
            await db_client.close()

if __name__ == "__main__":
    setup_logging(logger_name='feature_importance')
    parser = argparse.ArgumentParser(description="Calculate Permutation Feature Importance for a trained RL agent.")
    
    parser.add_argument("--model-path", type=str, default=rl_cfg.BEST_MODEL_PATH)
    parser.add_argument("--start-date", type=str, default=rl_cfg.DATA_START_DATE)
    parser.add_argument("--end-date", type=str, default=rl_cfg.DATA_END_DATE)
    parser.add_argument("--n-tokens", type=int, default=50, help="Number of random tokens to use for the analysis.")
    args = parser.parse_args()

    asyncio.run(run_feature_importance(
        model_path=args.model_path,
        start_date_str=args.start_date,
        end_date_str=args.end_date,
        n_tokens=args.n_tokens
    ))