# rl_agent/evaluation/evaluate.py
"""
Standalone script for evaluating a trained RL agent's performance with MLflow logging.

This script runs a backtest of a saved agent model on a specified
historical data period. It logs parameters, key performance metrics, and a
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

import config.config as config_module
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from state_manager import GlobalState
from rl_agent.data.data_manager import DataManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv
from config.rl_config import RL_CONFIG


def _run_backtest(model: PPO, env: MemeCoinEnv) -> pd.Series:
    """
    Runs the agent through the environment and records portfolio value over time.
    (This function remains unchanged.)
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
    config: Dict[str, Any]
) -> pd.Series:
    """
    Processes the portfolio history, generates a quantstats report, and returns key metrics.
    """
    if portfolio_history.empty or portfolio_history.isnull().all():
        logger.error("Portfolio history is empty. Cannot generate Quantstats report.")
        return pd.Series(dtype=float)

    logger.info("Generating Quantstats performance report...")
    
    # Ensure the index is a DatetimeIndex and handle potential duplicates
    portfolio_history.index = pd.to_datetime(portfolio_history.index, utc=True)
    portfolio_history = portfolio_history.loc[~portfolio_history.index.duplicated(keep='last')]

    # Convert absolute portfolio values to percentage returns
    returns = portfolio_history.pct_change().fillna(0)
    
    try:
        # Use Quantstats to generate a comprehensive HTML report
        title = f"RL Agent Performance ({config.get('EVAL_START_DATE')} to {config.get('EVAL_END_DATE')})"
        qs.reports.html(
            returns,
            benchmark=None,
            output=report_filename,
            title=title
        )
        logger.info(f"✅ Quantstats report successfully saved to: {report_filename}")
        # Return key metrics for MLflow logging
        return qs.reports.metrics(returns, display=False)
    except Exception as e:
        logger.error(f"Failed to generate Quantstats report: {e}", exc_info=True)
        return pd.Series(dtype=float)


async def run_evaluation(model_path: str, start_date_str: str, end_date_str: str, output_dir: str):
    """
    Main orchestration function for the evaluation process, wrapped in an MLflow run.
    """
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_BACKTESTING"])
    run_name = f"Eval_{os.path.basename(model_path)}_{start_date_str}_to_{end_date_str}"

    with mlflow.start_run(run_name=run_name):
        logger.info(f"Starting evaluation run: {run_name}")

        # --- Log parameters to MLflow ---
        mlflow.log_param("model_path", model_path)

        # If a registered model URI like models:/Name/Version is passed, record linkage
        if model_path.startswith("models:/"):
            parts = model_path.split("/")
            if len(parts) >= 3:
                mlflow.set_tags({
                    "registered_model_name": parts[1],
                    "registered_model_version": parts[2],
                })
                
        mlflow.log_param("start_date", start_date_str)
        mlflow.log_param("end_date", end_date_str)

        # 1. Initial Setup
        setup_logging()
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at: {model_path}")
            return

        state = GlobalState.get_instance()
        config = {key: getattr(config_module, key) for key in dir(config_module) if key.isupper()}
        config['EVAL_START_DATE'] = start_date_str
        config['EVAL_END_DATE'] = end_date_str

        db_client = None
        try:
            # 2. Database Connection
            db_client = DatabaseClient(config_dict=config)
            await db_client.connect()
            state.set_db_client(db_client)

            # 3. Load Model
            logger.info(f"Loading pre-trained model from {model_path}...")
            model = PPO.load(model_path)

            # 4. Load Data
            data_manager = DataManager(
                db_client,
                start_date=datetime.fromisoformat(start_date_str),
                end_date=datetime.fromisoformat(end_date_str)
            )
            if not await data_manager.load_and_prepare_data():
                logger.error("Failed to load and prepare evaluation data. Aborting.")
                return
            
            # Switch data_manager to use the evaluation set for the backtest
            data_manager.use_evaluation_data()
            evaluation_df = data_manager.get_evaluation_data()

            if evaluation_df is not None and not evaluation_df.empty:
                # FIX: Use the actual directory path as the source
                input_data_eval = mlflow.data.from_pandas(evaluation_df)
                mlflow.log_input(input_data_eval, context="evaluation")
            else:
                logger.warning("Evaluation data is empty, skipping MLflow input logging.")
            

            # 5. Create Environment
            env = MemeCoinEnv(
                data_manager,
                rl_config=vars(config_module) # Pass the module's vars as a dict
            )

            # 6. Run Backtest
            portfolio_history = _run_backtest(model, env)

            # 7. Generate Report and Log to MLflow
            if not portfolio_history.empty:
                report_filename = os.path.join(output_dir, f"report_{mlflow.active_run().info.run_id}.html")
                metrics = _generate_quantstats_report(portfolio_history, report_filename, config)
                
                if not metrics.empty:
                    # Log the full HTML report as an artifact
                    mlflow.log_artifact(report_filename, "quantstats_report")
                    logger.info("✅ Quantstats report logged to MLflow as an artifact.")

                    # Log key metrics to MLflow
                    key_metrics_dict = {
                        "sharpe_ratio": metrics.loc['Sharpe'],
                        "sortino_ratio": metrics.loc['Sortino'],
                        "max_drawdown_pct": metrics.loc['Max Drawdown'],
                        "cumulative_return_pct": metrics.loc['Cumulative Return'],
                        "win_rate_pct": metrics.loc['Win Rate']
                    }
                    # Clean up NaN or Inf values before logging
                    cleaned_metrics = {k: float(v) for k, v in key_metrics_dict.items() if np.isfinite(v)}
                    mlflow.log_metrics(cleaned_metrics)
                    logger.info("✅ Key performance metrics logged to MLflow.")

        except Exception as e:
            logger.error(f"An error occurred during the evaluation process: {e}", exc_info=True)
        finally:
            if db_client:
                await db_client.close()
                logger.info("Database connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a trained RL trading agent.")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the saved PPO model .zip file.")
    parser.add_argument("--start-date", type=str, required=True, help="Start date for the backtest period in YYYY-MM-DD format.")
    parser.add_argument("--end-date", type=str, required=True, help="End date for the backtest period in YYYY-MM-DD format.")
    parser.add_argument("--output-dir", type=str, default="data/evaluation_reports", help="Directory to save the performance report.")
    args = parser.parse_args()

    try:
        asyncio.run(run_evaluation(
            model_path=args.model_path,
            start_date_str=args.start_date,
            end_date_str=args.end_date,
            output_dir=args.output_dir
        ))
    except KeyboardInterrupt:
        logger.info("Evaluation process interrupted by user.")