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
from tqdm import tqdm

# --- MLflow Integration ---
import mlflow

# --- Project-specific imports ---
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from config.rl_config import get_config_for_mode, get_active_features
from rl_agent.data.data_manager import DataManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv

import nest_asyncio
nest_asyncio.apply()

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
        done = terminated or truncated
    final_pnl = env.portfolio_value - initial_value
    return final_pnl

async def run_feature_importance(model_path: str, dataset_run_id: str, n_tokens: int):
    """
    Main orchestration function for feature importance, wrapped in an MLflow run.
    """
    mlflow.set_experiment("PumpTrader.RL Feature Analysis")
    model_basename = os.path.splitext(os.path.basename(model_path))[0]
    run_name = f"Importance_{model_basename}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with mlflow.start_run(run_name=run_name, log_system_metrics=True) as run:
        logger.info(f"🚀 Starting Permutation Feature Importance run '{run.info.run_name}'...")
        rl_config = get_config_for_mode('train') # Use train config for feature list
        features_to_analyze = get_active_features(rl_config)
        
        mlflow.log_params({
            "model_path": model_path,
            "n_tokens_sampled": n_tokens,
            "features_analyzed_count": len(features_to_analyze),
        })
        mlflow.set_tag("source_dataset_run_id", dataset_run_id)

        try:
            # --- 1. Load Data using the new DataManager ---
            logger.info(f"Loading data from dataset run '{dataset_run_id}'...")
            data_manager = DataManager(rl_config=rl_config, dataset_run_id=dataset_run_id)
            if not data_manager.load_and_prepare_data():
                logger.error("Failed to load data, aborting analysis.")
                return

            # --- 2. Prepare Evaluation DataFrames per Token ---
            _, eval_mints_all = data_manager.get_split_token_mints()
            full_eval_df = data_manager.get_evaluation_data()
            if full_eval_df is None or full_eval_df.empty:
                logger.error("Evaluation data is empty. Aborting.")
                return
            
            # Create a dictionary of {mint: DataFrame} for easy access
            eval_token_dfs = {
                mint: df.copy() for mint, df in full_eval_df.groupby('mint') 
                if mint in eval_mints_all and not df.empty
            }

            if not eval_token_dfs:
                logger.error("Could not prepare any valid evaluation token DataFrames. Aborting.")
                return

            # --- 3. Sample Tokens and Load Model ---
            token_mints = list(eval_token_dfs.keys())
            n_tokens = min(n_tokens, len(token_mints))
            eval_sample_mints = random.sample(token_mints, n_tokens)
            logger.info(f"Analyzing {n_tokens} randomly sampled tokens.")
            mlflow.log_param("n_tokens_actually_used", n_tokens)

            model = PPO.load(model_path, device=rl_config.get('DEVICE', 'cpu'))
            env = MemeCoinEnv(data_manager, rl_config, silent=True)

            # --- 4. Calculate Baseline Performance ---
            logger.info(f"Calculating baseline performance across {n_tokens} tokens...")
            baseline_pnls = []
            for mint in tqdm(eval_sample_mints, desc="Baseline"):
                data_manager.use_single_token_data(eval_token_dfs[mint])
                pnl = run_single_token_episode(model, env)
                baseline_pnls.append(pnl)

            baseline_mean_pnl = np.mean(baseline_pnls)
            mlflow.log_metric("baseline_mean_pnl", baseline_mean_pnl)
            logger.info(f"✅ Baseline Mean PnL: {baseline_mean_pnl:.4f} SOL")

            # --- 5. Calculate Permutation Importance ---
            importances = {}
            pbar = tqdm(features_to_analyze, desc="Shuffling Features")
            for feature in pbar:
                pbar.set_postfix_str(f"Feature: {feature}")
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
            
            logger.info("Finished calculating all feature importances.")
            sorted_importances = sorted(importances.items(), key=lambda x: x[1], reverse=True)

            # --- 6. Log Results to MLflow ---
            results_data = {
                "metadata": { "timestamp_utc": datetime.now(timezone.utc).isoformat() },
                "baseline_mean_pnl": baseline_mean_pnl,
                "feature_importance_pnl_drop": [{"feature": f, "importance": i} for f, i in sorted_importances]
            }

            with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmp_dir:
                tmp_file = os.path.join(tmp_dir, "feature_importance_report.json")
                with open(tmp_file, "w") as f:
                    json.dump(results_data, f, indent=4)            
                try:
                    mlflow.log_artifact(tmp_file, ".")
                    logger.info("💾 Feature importance report logged to MLflow.")
                finally:
                    os.remove(tmp_dir)

        except Exception as e:
            logger.error(f"An error occurred during feature analysis: {e}", exc_info=True)
            mlflow.set_tag("status", "failed")

if __name__ == "__main__":
    setup_logging(logger_name='feature_importance')
    mlflow.set_tracking_uri("file:./data/rl_runs")
    
    parser = argparse.ArgumentParser(description="Calculate Permutation Feature Importance.")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the saved PPO model .zip file.")
    parser.add_argument("--dataset-run-id", type=str, required=True, help="MLflow run ID of the dataset to use for analysis.")
    parser.add_argument("--n-tokens", type=int, default=50, help="Number of random tokens to use for the analysis.")
    args = parser.parse_args()

    asyncio.run(run_feature_importance(
        model_path=args.model_path,
        dataset_run_id=args.dataset_run_id,
        n_tokens=args.n_tokens
    ))