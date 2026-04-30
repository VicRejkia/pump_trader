# rl_agent_module/evaluation/feature_importance.py
"""
Calculates Permutation Feature Importance and logs results to MLflow.

This script runs a backtest for multiple individual tokens to establish a baseline.
It then shuffles a feature for each token, re-runs the backtest, and averages the
performance drop across all tokens to determine the feature's importance.
Each analysis is logged as a distinct run in MLflow.
"""
import argparse
import asyncio
import json
import os
import random
import shutil

# --- Project-specific imports ---
import sys
import tempfile
from datetime import datetime, timezone

# --- MLflow Integration ---
import mlflow
import numpy as np
import pandas as pd
from mlflow.data.pandas_dataset import PandasDataset
from mlflow.tracking import MlflowClient
from stable_baselines3 import PPO
from tqdm import tqdm

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import nest_asyncio

from bot_logger import logger, setup_logging
from config.rl_config import RL_CONFIG, get_active_features, get_config_for_mode
from rl_agent_module.data.data_manager import DataManager
from rl_agent_module.environments.meme_coin_env import MemeCoinEnv
from rl_agent_module.utils.script_utils import generate_config_json  # Import the utility

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

async def run_feature_importance(model_path: str, dataset_run_id: str, n_tokens: int, model_run_id: str):
    """
    Main orchestration function for feature importance, wrapped in an MLflow run.
    """
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_ANALYSIS"])
    model_basename = os.path.splitext(os.path.basename(model_path))[0]
    run_name = f"Importance_{model_basename}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with mlflow.start_run(run_name=run_name, log_system_metrics=True) as run:
        logger.info(f"🚀 Starting Permutation Feature Importance run '{run.info.run_name}'...")
        staging_dir = os.path.abspath(f"./.rl_staging/{run.info.run_id}")
        os.makedirs(staging_dir, exist_ok=True)
        client = MlflowClient()

        try:
            # --- 1. Log Initial Parameters & Tags ---
            # *** MODIFIED: Use the new 'importance' config mode ***
            rl_config = get_config_for_mode('importance')
            features_to_analyze = get_active_features(rl_config)

            # **FIXED**: Log the persistent model URI, not the temporary path.
            model_uri = f"runs:/{model_run_id}/model"
            mlflow.log_params({
                "model_uri": model_uri,
                "n_tokens_sampled": n_tokens,
                "features_analyzed_count": len(features_to_analyze),
                "features_analyzed": features_to_analyze,
            })
            mlflow.set_tags({
                "source_model_run_id": model_run_id,
                "source_dataset_run_id": dataset_run_id
            })

            # **NEW**: Log the rl_config as an artifact, same as in train.py
            config_staging_path = os.path.join(staging_dir, "config")
            generate_config_json(rl_config, config_staging_path)

            # **NEW**: Fetch and log the parent model's training parameters
            try:
                # Use tempfile for safe download within the staging area
                param_download_path = tempfile.mkdtemp(dir=staging_dir)
                client.download_artifacts(model_run_id, "best_params.json", param_download_path)
                downloaded_params_file = os.path.join(param_download_path, "best_params.json")
                # Move it to the config staging path to be logged with other configs
                shutil.move(downloaded_params_file, os.path.join(config_staging_path, "parent_model_training_params.json"))
                logger.info("✅ Logged parent model's training parameters.")
            except Exception:
                logger.warning(f"Could not find or log 'best_params.json' from parent model run {model_run_id}.")


            # --- 2. Load Data & Log as Input ---
            logger.info(f"Loading data from dataset run '{dataset_run_id}'...")
            data_manager = DataManager(rl_config=rl_config, dataset_run_id=dataset_run_id)
            if not data_manager.load_and_prepare_data():
                raise RuntimeError("Failed to load data, aborting analysis.")

            # **NEW**: Log the evaluation dataset as an input for data lineage
            full_eval_df = data_manager.get_evaluation_data()
            if full_eval_df is None or full_eval_df.empty:
                raise RuntimeError("Evaluation data is empty. Aborting.")

            eval_dataset: PandasDataset = mlflow.data.from_pandas(full_eval_df, name="evaluation_set")
            mlflow.log_input(eval_dataset, context="evaluation_data")
            logger.info("✅ Logged evaluation dataset as an MLflow input.")

            # --- 3. Prepare Evaluation DataFrames per Token ---
            _, eval_mints_all = data_manager.get_split_token_mints()
            eval_token_dfs = {
                mint: df.copy() for mint, df in full_eval_df.groupby('mint')
                if mint in eval_mints_all and not df.empty
            }
            if not eval_token_dfs:
                raise RuntimeError("Could not prepare any valid evaluation token DataFrames.")

            # --- 4. Sample Tokens and Load Model ---
            n_tokens = min(n_tokens, len(eval_token_dfs))
            eval_sample_mints = random.sample(list(eval_token_dfs.keys()), n_tokens)
            logger.info(f"Analyzing {n_tokens} randomly sampled tokens.")
            mlflow.log_param("n_tokens_actually_used", n_tokens)

            model = PPO.load(model_path, device=rl_config.get('DEVICE', 'cpu'))
            env = MemeCoinEnv(data_manager, rl_config, silent=True)

            # --- 5. Calculate Baseline Performance ---
            logger.info(f"Calculating baseline performance across {n_tokens} tokens...")
            baseline_pnls = []
            for mint in tqdm(eval_sample_mints, desc="Baseline"):
                data_manager.use_single_token_data(eval_token_dfs[mint])
                pnl = run_single_token_episode(model, env)
                baseline_pnls.append(pnl)

            baseline_mean_pnl = np.mean(baseline_pnls)
            mlflow.log_metric("baseline_mean_pnl", baseline_mean_pnl)
            logger.info(f"✅ Baseline Mean PnL: {baseline_mean_pnl:.4f} SOL")

            # --- 6. Calculate Permutation Importance ---
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

            # --- 7. Save and Log Results Artifact ---
            results_data = {
                "metadata": { "timestamp_utc": datetime.now(timezone.utc).isoformat() },
                "baseline_mean_pnl": baseline_mean_pnl,
                "feature_importance_pnl_drop": [{"feature": f, "importance": i} for f, i in sorted_importances]
            }

            # Save the final report to the staging directory
            report_path = os.path.join(staging_dir, "feature_importance_report.json")
            with open(report_path, "w") as f:
                json.dump(results_data, f, indent=4)

            # Log all collected artifacts from the staging directory
            mlflow.log_artifacts(staging_dir, artifact_path="analysis_outputs")
            logger.info("💾 All analysis artifacts, including the report and configs, logged to MLflow.")

        except Exception as e:
            logger.error(f"An error occurred during feature analysis: {e}", exc_info=True)
            mlflow.set_tag("status", "failed")
        finally:
            # Cleanup the staging directory
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)

if __name__ == "__main__":
    setup_logging(logger_name='feature_importance')
    # --- Point to the MLflow server ---
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    #mlflow.set_tracking_uri("file:./data/rl_runs")

    parser = argparse.ArgumentParser(description="Calculate Permutation Feature Importance.")
    parser.add_argument("--model-run-id", type=str, required=True, help="MLflow run ID of the trained PPO model.")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the saved PPO model .zip file.")
    parser.add_argument("--dataset-run-id", type=str, required=True, help="MLflow run ID of the dataset to use for analysis.")
    parser.add_argument("--n-tokens", type=int, default=50, help="Number of random tokens to use for the analysis.")
    args = parser.parse_args()

    asyncio.run(run_feature_importance(
        model_path=args.model_path,
        dataset_run_id=args.dataset_run_id,
        n_tokens=args.n_tokens,
        model_run_id=args.model_run_id
    ))
