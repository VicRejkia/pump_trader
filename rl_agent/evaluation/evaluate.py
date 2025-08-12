# rl_agent/evaluation/evaluate.py
"""
Standalone script for evaluating a trained RL agent's performance.

This script runs a backtest of a saved agent model on a specified
historical data period and generates a detailed performance report
using the quantstats library.
"""

import argparse
import asyncio
import os
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import quantstats as qs
from stable_baselines3 import PPO

# Project-specific imports
import config.config as config_module

import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from state_manager import GlobalState
from rl_agent.data.data_manager import DataManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv


def _run_backtest(model: PPO, env: MemeCoinEnv) -> pd.Series:
    """
    Runs the agent through the environment and records portfolio value over time.

    Args:
        model: The trained Stable Baselines 3 agent.
        env: The initialized MemeCoinEnv with the evaluation data.

    Returns:
        A pandas Series of the portfolio value, indexed by timestamp.
    """
    logger.info("Starting backtest simulation...")
    obs = env.reset()
    done = False
    portfolio_history = {}

    while not done:
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        
        # Store portfolio value at each step using the environment's timestamp
        portfolio_history[env.current_timestamp] = env.portfolio_value
        
        if done:
            logger.info("Backtest simulation finished.")
            break
            
    if not portfolio_history:
        logger.warning("Backtest resulted in no portfolio history. Cannot generate report.")
        return pd.Series(dtype=float)

    return pd.Series(portfolio_history)


def _generate_quantstats_report(
    portfolio_history: pd.Series,
    output_dir: str,
    config: Dict[str, Any]
):
    """
    Processes the portfolio history and generates a quantstats report.

    Args:
        portfolio_history: A pandas Series of portfolio values over time.
        output_dir: The directory to save the HTML report.
        config: The bot's configuration dictionary.
    """
    if portfolio_history.empty or portfolio_history.isnull().all():
        logger.error("Portfolio history is empty. Cannot generate Quantstats report.")
        return

    logger.info("Generating Quantstats performance report...")
    
    # Ensure the index is a DatetimeIndex
    portfolio_history.index = pd.to_datetime(portfolio_history.index, utc=True)
    
    # Convert absolute portfolio values to percentage returns
    returns = portfolio_history.pct_change().fillna(0)
    
    report_filename = os.path.join(output_dir, "rl_agent_performance_report.html")
    
    try:
        # Use Quantstats to generate a comprehensive HTML report
        qs.reports.html(
            returns,
            benchmark=None,  # No benchmark for now, could add SOL price later
            output=report_filename,
            title=f"RL Agent Performance ({config.get('EVAL_START_DATE')} to {config.get('EVAL_END_DATE')})",
            download_filename=report_filename
        )
        logger.info(f"✅ Quantstats report successfully saved to: {report_filename}")
    except Exception as e:
        logger.error(f"Failed to generate Quantstats report: {e}", exc_info=True)


async def run_evaluation(model_path: str, start_date_str: str, end_date_str: str, output_dir: str):
    """
    Main orchestration function for the evaluation process.

    Args:
        model_path: Path to the saved RL model .zip file.
        start_date_str: Start date for the evaluation period (YYYY-MM-DD).
        end_date_str: End date for the evaluation period (YYYY-MM-DD).
        output_dir: Directory to save the evaluation report.
    """
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
            end_date=datetime.fromisoformat(end_date_str),
            min_trade_count=config.get('MIN_TRADE_COUNT_FOR_EVAL', 50)
        )
        if not await data_manager.load_and_prepare_data():
            logger.error("Failed to load and prepare evaluation data. Aborting.")
            return

        # 5. Create Environment
        env = MemeCoinEnv(
            data_manager,
            config,
            initial_balance=config.get('RL_INITIAL_BALANCE', 100.0)
        )

        # 6. Run Backtest
        portfolio_history = _run_backtest(model, env)

        # 7. Generate Report
        if not portfolio_history.empty:
            _generate_quantstats_report(portfolio_history, output_dir, config)

    except Exception as e:
        logger.error(f"An error occurred during the evaluation process: {e}", exc_info=True)
    finally:
        if db_client:
            await db_client.close()
            logger.info("Database connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a trained RL trading agent.")
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the saved PPO model .zip file."
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date for the backtest period in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date for the backtest period in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/evaluation_reports",
        help="Directory to save the performance report."
    )
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