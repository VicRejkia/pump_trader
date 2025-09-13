# rl_agent/evaluation/evaluate.py
"""
Standalone script for evaluating a trained RL agent's performance using a pre-generated dataset.

This script runs a backtest of a saved agent model on the evaluation split
of a specified MLflow dataset run. It logs parameters, key performance metrics, and a
detailed quantstats report to MLflow for tracking and comparison.
"""

import argparse
import asyncio
import os
from datetime import datetime
from typing import Dict, Any

import numpy as np
import pandas as pd
import quantstats as qs
from stable_baselines3 import PPO

# --- MLflow Integration ---
import mlflow

# Project-specific imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from rl_agent.data.data_manager import DataManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv
from config.rl_config import get_config_for_mode, RL_CONFIG


def _run_backtest(model: PPO, env: MemeCoinEnv) -> pd.Series:
    """
    Runs the agent through the environment and records portfolio value over time.
    """
    logger.info("Starting backtest simulation...")
    obs, _ = env.reset()
    done = False
    truncated = False
    portfolio_history = {}

    while not (done or truncated):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, truncated, info = env.step(action)
        
        # Store portfolio value at each step using the environment's timestamp
        if env.current_timestamp:
            portfolio_history[env.current_timestamp] = env.portfolio_value
        
        if done or truncated:
            logger.info("Backtest simulation finished.")
            break
            
    if not portfolio_history:
        logger.warning("Backtest resulted in no portfolio history. Cannot generate report.")
        return pd.Series(dtype=float)

    return pd.Series(portfolio_history)


def _generate_quantstats_report(
    portfolio_history: pd.Series,
    report_filename: str,
    run_name: str
) -> pd.Series:
    """
    Processes the portfolio history, generates a quantstats report, and returns key metrics.
    """
    if portfolio_history.empty or portfolio_history.isnull().all():
        logger.error("Portfolio history is empty. Cannot generate Quantstats report.")
        return pd.Series(dtype=float)

    logger.info("Generating Quantstats performance report...")
    
    portfolio_history.index = pd.to_datetime(portfolio_history.index, utc=True)
    portfolio_history = portfolio_history.loc[~portfolio_history.index.duplicated(keep='last')]
    returns = portfolio_history.pct_change().fillna(0)

    # --- FIX: Check if there were any non-zero returns ---
    # If the portfolio value never changed, returns.abs().sum() will be 0.
    if returns.abs().sum() == 0:
        logger.warning("⚠️ No trades were made, so no performance metrics can be calculated.")
        logger.warning("Quantstats report will be skipped.")
        # Return an empty Series to indicate no metrics were generated.
        return pd.Series(dtype=float)
    # --- END FIX ---
    
    try:
        title = f"RL Agent Performance ({run_name})"
        qs.reports.html(
            returns,
            benchmark=None,
            output=report_filename,
            title=title
        )
        logger.info(f"✅ Quantstats report successfully saved to: {report_filename}")
        return qs.reports.metrics(returns, display=False)
    except Exception as e:
        logger.error(f"Failed to generate Quantstats report: {e}", exc_info=True)
        return pd.Series(dtype=float)


async def run_evaluation(model_path: str, dataset_run_id: str, output_dir: str):
    """
    Main orchestration function for the evaluation process, wrapped in an MLflow run.
    """
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_BACKTESTING"])
    model_basename = os.path.splitext(os.path.basename(model_path))[0]
    run_name = f"Backtest_{model_basename}_on_DS_{dataset_run_id[:8]}"

    with mlflow.start_run(run_name=run_name) as run:
        logger.info(f"Starting evaluation run: {run.info.run_name}")

        mlflow.log_param("model_path", model_path)
        mlflow.log_param("source_dataset_run_id", dataset_run_id)
        
        setup_logging()
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at: {model_path}")
            return

        # Use a generic config mode to get environment parameters
        rl_config = get_config_for_mode('train') 

        try:
            logger.info(f"Loading pre-trained model from {model_path}...")
            model = PPO.load(model_path, device=rl_config.get("DEVICE", "cpu"))

            logger.info(f"Loading data from dataset run: {dataset_run_id}")
            data_manager = DataManager(
                rl_config=rl_config,
                dataset_run_id=dataset_run_id
            )
            if not data_manager.load_and_prepare_data():
                logger.error("Failed to load and prepare evaluation data. Aborting.")
                return
            
            data_manager.use_evaluation_data()
            evaluation_df = data_manager.get_evaluation_data()

            if evaluation_df is not None and not evaluation_df.empty:
                eval_dataset = mlflow.data.from_pandas(evaluation_df, name="evaluation_set")
                mlflow.log_input(eval_dataset, context="evaluation")
            else:
                logger.warning("Evaluation data split is empty, cannot run backtest.")
                return

            env = MemeCoinEnv(data_manager, rl_config=rl_config, silent=False)
            portfolio_history = _run_backtest(model, env)

            if not portfolio_history.empty:
                report_filename = os.path.join(output_dir, f"report_{run.info.run_id}.html")
                metrics = _generate_quantstats_report(portfolio_history, report_filename, run.info.run_name)
                
                if not metrics.empty:
                    mlflow.log_artifact(report_filename, "quantstats_report")
                    logger.info("✅ Quantstats report logged to MLflow as an artifact.")

                    key_metrics_dict = {
                        "sharpe_ratio": metrics.loc['Sharpe'],
                        "sortino_ratio": metrics.loc['Sortino'],
                        "max_drawdown_pct": metrics.loc['Max Drawdown'],
                        "cumulative_return_pct": metrics.loc['Cumulative Return'],
                        "win_rate_pct": metrics.loc['Win Rate']
                    }
                    cleaned_metrics = {k: float(v) for k, v in key_metrics_dict.items() if np.isfinite(v)}
                    mlflow.log_metrics(cleaned_metrics)
                    logger.info("✅ Key performance metrics logged to MLflow.")

        except Exception as e:
            logger.error(f"An error occurred during the evaluation process: {e}", exc_info=True)
        finally:
            logger.info("Evaluation finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a trained RL trading agent on a prepared dataset.")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the saved PPO model .zip file.")
    parser.add_argument("--dataset-run-id", type=str, required=True, help="MLflow run ID of the prepared dataset to use for the backtest.")
    parser.add_argument("--output-dir", type=str, default="data/evaluation_reports", help="Directory to save the performance report.")
    args = parser.parse_args()

    asyncio.run(run_evaluation(
        model_path=args.model_path,
        dataset_run_id=args.dataset_run_id,
        output_dir=args.output_dir
    ))