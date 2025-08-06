# rl_tools/manager_backtest.py
"""
Backtesting script for the Manager (Trade Management) RL Agent.

This script evaluates the performance of a trained Manager agent against the
original fixed-rule (benchmark) strategy. It loads the test set of trade
lifecycles, simulates the agent's step-by-step 'HOLD'/'SELL' decisions for each
trade, and compares the resulting profit and loss.

Performance metrics are displayed in a console table and saved to a detailed
HTML report using QuantStats.
"""

import argparse
import os
import warnings
import pandas as pd
import quantstats as qs
from rich.console import Console
from rich.table import Table
from tqdm import tqdm
import stable_baselines3 as sb3
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
import numpy as np

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import rl_config as cfg
from trading_rl_agent.environments.solana_management_env import SolanaManagementEnv
from rl_tools.manager_data_preparation import load_prepared_manager_data
from bot_logger import setup_logging, logger

def calculate_performance_metrics(daily_returns: pd.Series, title: str, all_trades: pd.Series) -> dict:
    """Calculates key performance metrics for a series of daily trade returns."""
    if daily_returns.empty or all_trades.empty:
        return {f"{title} Total Trades": 0}

    metrics = {
        f"{title} Total Trades": len(all_trades),
        f"{title} Win Rate": (all_trades > 0).mean(),
        f"{title} Average Return / Trade": all_trades.mean(),
        f"{title} Total Compounded Return": qs.stats.comp(daily_returns),
        f"{title} Sharpe Ratio": qs.stats.sharpe(daily_returns),
        f"{title} Max Drawdown": qs.stats.max_drawdown(daily_returns),
    }
    return metrics

def run_backtest(model_path: str):
    """Performs a backtest of the trained Manager agent on the test dataset."""
    logger.info(f"--- Starting Backtest for Manager Model: {model_path} ---")

    if not os.path.exists(model_path):
        logger.critical(f"Model file not found at: {model_path}")
        return

    model = sb3.PPO.load(model_path, device='cpu')

    model_base_dir = os.path.dirname(model_path)
    model_filename = os.path.basename(model_path)
    if 'best_model.zip' in model_filename:
        model_base_dir = os.path.dirname(model_base_dir)
        model_prefix = os.path.basename(os.path.dirname(model_path)).replace('_best', '')
    else:
        model_prefix = model_filename.replace('_final.zip', '')
        
    vec_normalize_path = os.path.join(model_base_dir, f"{model_prefix}_vecnormalize.pkl")

    if not os.path.exists(vec_normalize_path):
        logger.critical(f"VecNormalize stats not found at: {vec_normalize_path}")
        return

    trade_lifecycles = load_prepared_manager_data()
    if not trade_lifecycles:
        logger.critical("Could not load processed manager data. Run manager_data_preparation.py first.")
        return

    all_trade_ids = list(trade_lifecycles.keys())
    train_size = int(0.8 * len(all_trade_ids))
    test_ids = all_trade_ids[train_size:]
    test_data = {tid: trade_lifecycles[tid] for tid in test_ids}
    
    logger.info(f"Backtesting on {len(test_data)} trade lifecycles.")

    dummy_env = DummyVecEnv([lambda: SolanaManagementEnv(trade_lifecycles=test_data)])
    vec_env = VecNormalize.load(vec_normalize_path, dummy_env)
    vec_env.training = False
    vec_env.norm_reward = False

    agent_trade_returns = []
    benchmark_trade_returns = []

    for trade_id, trade_df in tqdm(test_data.items(), desc="Backtesting Manager Decisions"):
        # --- Simulate Agent ---
        obs, _ = vec_env.reset()
        # Force the environment to use the specific trade_id for this iteration
        vec_env.envs[0].unwrapped._current_trade_id = trade_id
        vec_env.envs[0].unwrapped._current_trade_data = trade_df
        obs, _ = vec_env.envs[0].unwrapped.reset() # Reset internal state with the correct trade
        
        done = False
        while not done:
            action, _ = model.predict(vec_env.normalize_obs(obs), deterministic=True)
            obs, reward, terminated, truncated, _ = vec_env.envs[0].unwrapped.step(action)
            done = terminated or truncated
        
        agent_pnl = reward # The final reward is the PnL
        entry_timestamp = trade_df.index[0]
        agent_trade_returns.append({'timestamp': entry_timestamp, 'pnl': agent_pnl})

        # --- Simulate Benchmark (Fixed Rule) ---
        buy_price = trade_df['Close'].iloc[0]
        # This simulation is simplified; it assumes the fixed rule exit is within the data.
        # A more robust benchmark would re-run the logic from `manager_data_preparation`.
        # For now, we assume the last price is the exit price for the benchmark.
        last_price = trade_df['Close'].iloc[-1]
        benchmark_pnl = (last_price - buy_price) / buy_price if buy_price > 0 else 0
        benchmark_trade_returns.append({'timestamp': entry_timestamp, 'pnl': benchmark_pnl})

    agent_returns_series = pd.DataFrame(agent_trade_returns).set_index('timestamp')['pnl'].sort_index()
    benchmark_returns_series = pd.DataFrame(benchmark_trade_returns).set_index('timestamp')['pnl'].sort_index()
    
    agent_daily_returns = agent_returns_series.resample('D').sum()
    benchmark_daily_returns = benchmark_returns_series.resample('D').sum()

    agent_metrics = calculate_performance_metrics(agent_daily_returns, "Manager Agent", agent_returns_series)
    benchmark_metrics = calculate_performance_metrics(benchmark_daily_returns, "Benchmark", benchmark_returns_series)

    console = Console()
    table = Table(title=f"Manager Backtest Results: {os.path.basename(model_path)}", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("RL Manager Agent", justify="right")
    table.add_column("Benchmark (Fixed Rule)", justify="right")

    table.add_row("Total Trades", f"{agent_metrics.get('Manager Agent Total Trades', 0)}", f"{benchmark_metrics.get('Benchmark Total Trades', 0)}")
    table.add_row("Win Rate", f"{agent_metrics.get('Manager Agent Win Rate', 0):.2%}", f"{benchmark_metrics.get('Benchmark Win Rate', 0):.2%}")
    table.add_row("Average Return / Trade", f"{agent_metrics.get('Manager Agent Average Return / Trade', 0):.4f}", f"{benchmark_metrics.get('Benchmark Average Return / Trade', 0):.4f}")
    table.add_row("Total Compounded Return", f"{agent_metrics.get('Manager Agent Total Compounded Return', 0):.2%}", f"{benchmark_metrics.get('Benchmark Total Compounded Return', 0):.2%}")
    table.add_row("Sharpe Ratio", f"{agent_metrics.get('Manager Agent Sharpe Ratio', 0):.2f}", f"{benchmark_metrics.get('Benchmark Sharpe Ratio', 0):.2f}")
    table.add_row("Max Drawdown", f"{agent_metrics.get('Manager Agent Max Drawdown', 0):.2%}", f"{benchmark_metrics.get('Benchmark Max Drawdown', 0):.2%}")
    console.print(table)

    report_filename = os.path.join(model_base_dir, f"backtest_report_{model_prefix}.html")
    
    if not agent_daily_returns.empty:
        agent_daily_returns.index = agent_daily_returns.index.tz_localize(None)
    if not benchmark_daily_returns.empty:
        benchmark_daily_returns.index = benchmark_daily_returns.index.tz_localize(None)
    
    qs.reports.html(agent_daily_returns, benchmark=benchmark_daily_returns, output=report_filename, title=f"RL Manager Agent vs. Benchmark")
    logger.info(f"✅ Detailed HTML report saved to: {report_filename}")

if __name__ == "__main__":
    setup_logging(logger_name="rl_manager_backtester")
    parser = argparse.ArgumentParser(description="Backtest for RL Manager Agent")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the trained .zip model file.")
    args = parser.parse_args()
    
    warnings.filterwarnings("ignore", category=UserWarning)
    run_backtest(model_path=args.model_path)
