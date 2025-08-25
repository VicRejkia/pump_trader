# rl_agent/evaluation/feature_importance.py
"""
Calculates Permutation Feature Importance and logs results to MLflow.

This script runs a backtest for multiple individual tokens to establish a baseline.
It then shuffles a feature for each token, re-runs the backtest, and averages the
performance drop across all tokens to determine the feature's importance.
Each analysis is logged as a distinct run in MLflow.
"""

import argparse
import asyncio
import os
import json
import tempfile
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import random
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

# --- MLflow Integration ---
import mlflow

# --- Project-specific imports ---
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from config.rl_config import get_config_for_mode, get_active_features
from rl_agent.data.data_manager import DataManager
from rl_agent.data.cache_manager import CacheManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv

import nest_asyncio
nest_asyncio.apply()


def json_serializable_converter(o):
    """Converts non-serializable objects to serializable types."""
    if isinstance(o, set):
        return list(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

def run_single_token_episode(model: PPO, env: MemeCoinEnv) -> float:
    """
    Runs one full episode on the data currently loaded in the env and returns the final PnL.
    """
    obs, _ = env.reset()
    done = False
    truncated = False
    initial_value = env.initial_balance
    while not (done or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated
    final_pnl = env.portfolio_value - initial_value
    return final_pnl


async def run_feature_importance(model_path: str, start_date_str: str, end_date_str: str, n_tokens: int):
    """
    Main orchestration function for feature importance, wrapped in an MLflow run.
    """
    mlflow.set_experiment("PumpTrader.RL Feature Analysis")
    model_basename = os.path.splitext(os.path.basename(model_path))[0]
    run_name = f"Importance_{model_basename}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with mlflow.start_run(run_name=run_name):
        logger.info(f"🚀 Starting Permutation Feature Importance with MLflow run '{run_name}'...")
        rl_config = get_config_for_mode('train')

        features_to_analyze = get_active_features(rl_config)
        mlflow.log_param("features_analyzed", features_to_analyze)
        mlflow.log_param("model_path", model_path)

        db_client = None
        try:
            db_client = DatabaseClient()
            await db_client.connect()
            start_ts = datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
            end_ts = datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))

            cache_manager = CacheManager(db_client, start_ts, end_ts, rl_config=rl_config)
            if not await cache_manager.is_cache_valid():
                logger.info("Cache not found or invalid. Generating...")
                full_data_manager = DataManager(rl_config, db_client, start_date=start_ts, end_date=end_ts)
                await full_data_manager.load_and_prepare_data()

            logger.info("Loading evaluation token data from cache...")
            cached_data = cache_manager.load_from_cache()
            eval_token_dfs = cached_data.get('evaluation_set')

            if eval_token_dfs is not None and not eval_token_dfs.empty:
                # FIX: Use the actual directory path as the source
                input_data_eval = mlflow.data.from_pandas(eval_token_dfs)
                mlflow.log_input(input_data_eval, context="evaluation")
            else:
                logger.warning("Evaluation data is empty, skipping MLflow input logging.")

            if not eval_token_dfs:
                logger.error("Could not load evaluation set from cache. Aborting.")
                return

            token_mints = list(eval_token_dfs.keys())
            if len(token_mints) < n_tokens:
                n_tokens = len(token_mints)
            eval_sample_mints = random.sample(token_mints, n_tokens)

            model = PPO.load(model_path, device=rl_config['DEVICE'])
            data_manager = DataManager(rl_config=rl_config, cache_manager=cache_manager)
            # We wrap with Monitor to ensure episode stats are available, but not inside the env itself
            env = MemeCoinEnv(data_manager, rl_config, silent=True)


            logger.info(f"Calculating baseline performance across {n_tokens} tokens...")
            baseline_pnls = []
            for mint in eval_sample_mints:
                data_manager.use_single_token_data(eval_token_dfs[mint])
                pnl = run_single_token_episode(model, env)
                baseline_pnls.append(pnl)

            baseline_mean_pnl = np.mean(baseline_pnls)
            mlflow.log_metric("baseline_mean_pnl", baseline_mean_pnl)
            logger.info(f"✅ Baseline Mean PnL: {baseline_mean_pnl:.4f} SOL")

            importances = {}
            for feature in features_to_analyze:
                logger.info(f"   Shuffling feature: '{feature}'...")
                shuffled_pnls = []
                for mint in eval_sample_mints:
                    original_df = eval_token_dfs[mint]
                    shuffled_df = original_df.copy()
                    shuffled_df[feature] = np.random.permutation(shuffled_df[feature].values)
                    data_manager.use_single_token_data(shuffled_df)
                    pnl = run_single_token_episode(model, env)
                    shuffled_pnls.append(pnl)

                shuffled_mean_pnl = np.mean(shuffled_pnls)
                importances[feature] = baseline_mean_pnl - shuffled_mean_pnl
                logger.info(f"    ↳ Shuffled Mean PnL: {shuffled_mean_pnl:.4f} | Importance (Drop): {importances[feature]:.4f}")

            sorted_importances = sorted(importances.items(), key=lambda x: x[1], reverse=True)

            results_data = {
                "analysis_metadata": {
                    "model_path": model_path,
                    "n_tokens_sampled": n_tokens,
                    "data_start_date": start_date_str,
                    "data_end_date": end_date_str,
                    "features_analyzed": features_to_analyze,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
                "baseline_mean_pnl": baseline_mean_pnl,
                "feature_importance_results": [
                    {"feature": f, "importance_pnl_drop": i} for f, i in sorted_importances
                ]
            }

            staging_dir = os.path.abspath("./.rl_staging") # Define staging dir
            os.makedirs(staging_dir, exist_ok=True)      # Ensure it exists
            with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False, dir=staging_dir) as tmp:
                json.dump(results_data, tmp, indent=4, default=json_serializable_converter)
                tmp_path = tmp.name

            try:
                mlflow.log_artifact(tmp_path, "feature_importance_report.json")
                logger.info(f"💾 Feature importance results logged to MLflow as 'feature_importance_report.json'.")
            finally:
                os.remove(tmp_path)

        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            if db_client:
                await db_client.close()

if __name__ == "__main__":
    setup_logging(logger_name='feature_importance')
    temp_config = get_config_for_mode('train')

    parser = argparse.ArgumentParser(description="Calculate Permutation Feature Importance for a trained RL agent.")
    parser.add_argument("--model-path", type=str, default=temp_config['BEST_MODEL_PATH'])
    parser.add_argument("--start-date", type=str, default=temp_config['DATA_START_DATE'])
    parser.add_argument("--end-date", type=str, default=temp_config['DATA_END_DATE'])
    parser.add_argument("--n-tokens", type=int, default=50, help="Number of random tokens to use for the analysis.")
    args = parser.parse_args()

    asyncio.run(run_feature_importance(
        model_path=args.model_path,
        start_date_str=args.start_date,
        end_date_str=args.end_date,
        n_tokens=args.n_tokens
    ))
