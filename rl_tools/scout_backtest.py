# rl_tools/scout_backtest.py
"""
Backtesting script for the Scout (Decision Gate) RL Agent.
...
"""

import argparse
import os
import pandas as pd
import quantstats as qs
from rich.console import Console
from rich.table import Table
from tqdm import tqdm
import warnings

import stable_baselines3 as sb3
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
import numpy as np

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import rl_config_old as cfg
from rl_agent_framework.environments.solana_scout_env import SolanaDecisionEnv
from rl_tools.scout_data_preparation import load_prepared_scout_data
from rl_tools.backtesting_utils import calculate_performance_metrics, simulate_portfolio
from bot_logger import setup_logging, logger


def run_backtest(model_path: str, data_window: str):
    """
    Performs a backtest of the trained Scout agent on the test dataset.
    
    Args:
        model_path (str): Path to the trained .zip model file.
        data_window (str): The data window to use for backtesting (e.g., 'full').
    """
    logger.info(f"--- Starting Backtest for Scout Model: {model_path} on '{data_window}' data ---")
    
    if not os.path.exists(model_path):
        logger.critical(f"Model file not found at: {model_path}"); return

    model = sb3.PPO.load(model_path, device='cpu')
    
    # The base directory is the directory containing the selected model file.
    model_base_dir = os.path.dirname(model_path)
    # The prefix is the name of that directory.
    model_prefix = os.path.basename(model_base_dir)
    vec_normalize_path = os.path.join(model_base_dir, f"{model_prefix}_vecnormalize.pkl")
    
    if not os.path.exists(vec_normalize_path):
        logger.critical(f"VecNormalize stats not found at: {vec_normalize_path}"); return

    try:
        window = cfg.DATA_WINDOWS[data_window]
    except KeyError:
        logger.critical(f"Data window '{data_window}' not found in rl_config.py. Exiting."); return
        
    decision_df, ohlcv_dir = load_prepared_scout_data(window['start'], window['end'])
    if decision_df is None or ohlcv_dir is None:
        logger.critical("Could not load processed decision data. Run data preparation first."); return
        
    train_df = decision_df.sample(frac=0.8, random_state=42)
    test_df = decision_df.drop(train_df.index).reset_index(drop=True)
    
    logger.info(f"Backtesting on {len(test_df)} unseen decision points.")

    if not os.path.isdir(ohlcv_dir):
        logger.critical(f"OHLCV data directory not found at: {ohlcv_dir}. Aborting."); return

    sim_env = SolanaDecisionEnv(df=test_df, ohlcv_data_dir=ohlcv_dir)
    dummy_vec_env = DummyVecEnv([lambda: SolanaDecisionEnv(df=test_df, ohlcv_data_dir=ohlcv_dir)])
    vec_env_stats = VecNormalize.load(vec_normalize_path, dummy_vec_env)
    vec_env_stats.training = False
    vec_env_stats.norm_reward = False

    agent_trade_returns = []
    benchmark_trade_returns = []
    
    for i in tqdm(range(len(test_df)), desc="Backtesting Agent Decisions"):
        sim_env._current_decision_idx = i
        obs, _ = sim_env.reset()
        
        normalized_obs = vec_env_stats.normalize_obs(obs)
        action, _ = model.predict(normalized_obs, deterministic=True)
        
        benchmark_pnl = sim_env._simulate_trade()
        benchmark_trade_returns.append({'timestamp': test_df.iloc[i]['timestamp'], 'pnl': benchmark_pnl})
        
        if action == 1:
            agent_trade_returns.append({'timestamp': test_df.iloc[i]['timestamp'], 'pnl': benchmark_pnl})

    agent_returns_series = pd.DataFrame(agent_trade_returns).set_index('timestamp')['pnl'].sort_index()
    benchmark_returns_series = pd.DataFrame(benchmark_trade_returns).set_index('timestamp')['pnl'].sort_index()

    agent_daily_returns = simulate_portfolio(agent_returns_series)
    benchmark_daily_returns = simulate_portfolio(benchmark_returns_series)

    agent_metrics = calculate_performance_metrics(agent_daily_returns, "Agent", agent_returns_series)
    benchmark_metrics = calculate_performance_metrics(benchmark_daily_returns, "Benchmark", benchmark_returns_series)

    console = Console()
    table = Table(title=f"Scout Backtest Results: {os.path.basename(model_path)} on '{data_window}' data", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan"); table.add_column("RL Agent", justify="right"); table.add_column("Benchmark (Buy All)", justify="right")
    table.add_row("Total Trades", f"{agent_metrics.get('Agent Total Trades', 0)}", f"{benchmark_metrics.get('Benchmark Total Trades', 0)}")
    table.add_row("Win Rate", f"{agent_metrics.get('Agent Win Rate', 0):.2%}", f"{benchmark_metrics.get('Benchmark Win Rate', 0):.2%}")
    table.add_row("Average Return / Trade", f"{agent_metrics.get('Agent Average Return / Trade', 0):.4f}", f"{benchmark_metrics.get('Benchmark Average Return / Trade', 0):.4f}")
    table.add_row("Total Compounded Return", f"{agent_metrics.get('Agent Total Compounded Return', 0):.2%}", f"{benchmark_metrics.get('Benchmark Total Compounded Return', 0):.2%}")
    table.add_row("Sharpe Ratio", f"{agent_metrics.get('Agent Sharpe Ratio', 0):.2f}", f"{benchmark_metrics.get('Benchmark Sharpe Ratio', 0):.2f}")
    table.add_row("Max Drawdown", f"{agent_metrics.get('Agent Max Drawdown', 0):.2%}", f"{benchmark_metrics.get('Benchmark Max Drawdown', 0):.2%}")
    console.print(table)

    report_filename = os.path.join(model_base_dir, f"backtest_report_{model_prefix}.html")
    
    agent_report_series = agent_daily_returns; agent_report_series.name = "RL Agent"
    if not agent_report_series.empty and agent_report_series.index.tz is not None: agent_report_series.index = agent_report_series.index.tz_localize(None)
    benchmark_report_series = benchmark_daily_returns; benchmark_report_series.name = "Benchmark (Buy All)"
    if not benchmark_report_series.empty and benchmark_report_series.index.tz is not None: benchmark_report_series.index = benchmark_report_series.index.tz_localize(None)
    
    # --- FINAL FIX: Explicitly check for zero variance to provide a better message ---
    # and use a try/except block as a final safeguard.
    
    # Check for the condition that causes both warnings and the final crash.
    agent_has_variance = len(agent_report_series.index) > 1 and agent_report_series.std() > 0
    benchmark_has_variance = len(benchmark_report_series.index) > 1 and benchmark_report_series.std() > 0

    if agent_has_variance and benchmark_has_variance:
        try:
            # If data looks good, attempt to generate the full report.
            qs.reports.html(
                agent_report_series,
                benchmark=benchmark_report_series,
                output=report_filename,
                title=f"RL Scout Agent vs. Benchmark"
            )
            logger.info(f"✅ Detailed HTML report saved to: {report_filename}")

        except np.linalg.LinAlgError:
            # This is a fallback for any other unexpected numerical issue within the library.
            logger.error(
                "🔴 Failed to generate HTML report due to a numerical error in the plotting library. "
                "The script will continue without the report."
            )
        except Exception as e:
            logger.error(f"🔴 An unexpected error occurred during report generation: {e}")
    else:
        # If there is no variance, provide a clear, user-friendly message instead of warnings.
        logger.warning(
            "⚠️ Portfolio value may have been completely wiped out (-100% return), resulting in zero variance in daily returns."
        )
        logger.warning(
            "   Advanced statistical plots cannot be generated under this condition. Skipping HTML report."
        )
    # --- END FINAL FIX ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest for Scout RL Trading Agent")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the trained .zip model file.")
    parser.add_argument(
        "--data-window", type=str, default=cfg.DEFAULT_DATA_WINDOW,
        choices=cfg.DATA_WINDOWS.keys(),
        help="The data window to use for backtesting."
    )
    args = parser.parse_args()
    
    setup_logging(logger_name="rl_scout_backtester")
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    run_backtest(model_path=args.model_path, data_window=args.data_window)