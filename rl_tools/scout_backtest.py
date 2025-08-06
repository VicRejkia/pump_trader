# rl_tools/scout_backtest.py
"""
Backtesting script for the Scout (Decision Gate) RL Agent.

This script evaluates the performance of a trained Scout agent against a
benchmark strategy ("Buy All"). It loads the test dataset (data the agent has
never seen), runs the agent's decisions against it, and calculates key
performance metrics like Win Rate, Sharpe Ratio, and Max Drawdown.

The results are displayed in a console table and saved as a detailed
HTML report using the QuantStats library.
"""

import argparse
import os
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
from rl_agent_framework.environments.solana_scout_env import SolanaDecisionEnv
from rl_tools.scout_data_preparation import load_prepared_scout_data
from bot_logger import setup_logging, logger

def calculate_performance_metrics(daily_returns: pd.Series, title: str, all_trades: pd.Series) -> dict:
    """Calculates key performance metrics for a series of daily trade returns."""
    if daily_returns.empty or all_trades.empty:
        return {f"{title} Total Trades": 0}

    # Ensure there are no NaN values before passing to quantstats
    daily_returns = daily_returns.fillna(0)

    metrics = {
        f"{title} Total Trades": len(all_trades),
        f"{title} Win Rate": (all_trades > 0).mean(),
        f"{title} Average Return / Trade": all_trades.mean(),
        f"{title} Total Compounded Return": qs.stats.comp(daily_returns),
        f"{title} Sharpe Ratio": qs.stats.sharpe(daily_returns),
        f"{title} Max Drawdown": qs.stats.max_drawdown(daily_returns),
    }
    return metrics

def simulate_portfolio(trade_returns: pd.Series, initial_capital: float = 10000.0, capital_per_trade: float = 100.0) -> pd.Series:
    """
    Simulates portfolio performance to generate a realistic daily return series.
    Prevents portfolio value from dropping below zero.
    """
    if trade_returns.empty:
        return pd.Series(dtype=np.float64)

    # Assume a fixed capital allocation for each trade to calculate profit in dollars
    daily_profit = (trade_returns * capital_per_trade).resample('D').sum()

    # Create a full date range to ensure we have a value for every day
    full_date_range = pd.date_range(start=daily_profit.index.min(), end=daily_profit.index.max(), freq='D')
    daily_profit = daily_profit.reindex(full_date_range, fill_value=0)

    portfolio_value = pd.Series(index=daily_profit.index, dtype=np.float64)
    current_capital = initial_capital
    is_blown_up = False

    for day, profit in daily_profit.items():
        if is_blown_up:
            portfolio_value[day] = 0
            continue

        portfolio_value[day] = current_capital
        # A portfolio cannot go below zero.
        current_capital = max(0, current_capital + profit)

        if current_capital == 0:
            is_blown_up = True

    # Calculate daily returns based on the changing portfolio value
    daily_returns = portfolio_value.pct_change().fillna(0)
    
    # The pct_change from a positive number to 0 is -1. Cap any numerical noise.
    daily_returns[daily_returns < -1] = -1

    return daily_returns


def run_backtest(model_path: str):
    """Performs a backtest of the trained Scout agent on the test dataset."""
    logger.info(f"--- Starting Backtest for Scout Model: {model_path} ---")
    
    if not os.path.exists(model_path):
        logger.critical(f"Model file not found at: {model_path}")
        return

    model = sb3.PPO.load(model_path, device='cpu')
    
    model_base_dir = ""
    model_prefix = ""
    if 'best_model.zip' in model_path:
        model_dir = os.path.dirname(model_path)
        model_base_dir = os.path.dirname(model_dir)
        model_prefix = os.path.basename(model_dir).replace('_best', '')
    else:
        model_base_dir = os.path.dirname(model_path)
        model_filename = os.path.basename(model_path)
        model_prefix = model_filename.replace('_final.zip', '')
    
    vec_normalize_path = os.path.join(model_base_dir, f"{model_prefix}_vecnormalize.pkl")

    if not os.path.exists(vec_normalize_path):
        logger.critical(f"VecNormalize stats not found at: {vec_normalize_path}")
        return

    decision_df, all_token_data = load_prepared_scout_data()
    if decision_df is None or not all_token_data:
        logger.critical("Could not load processed data. Run scout_data_preparation.py first.")
        return
        
    train_df = decision_df.sample(frac=0.8, random_state=42)
    test_df = decision_df.drop(train_df.index).reset_index(drop=True)
    
    logger.info(f"Backtesting on {len(test_df)} decision points.")

    dummy_env = DummyVecEnv([lambda: SolanaDecisionEnv(df=test_df, full_token_data=all_token_data)])
    vec_env = VecNormalize.load(vec_normalize_path, dummy_env)
    vec_env.training = False
    vec_env.norm_reward = False

    agent_trade_returns = []
    benchmark_trade_returns = []
    
    sim_env = SolanaDecisionEnv(df=test_df, full_token_data=all_token_data)

    for i in tqdm(range(len(test_df)), desc="Backtesting Agent Decisions"):
        sim_env.reset()
        sim_env._current_decision_idx = i
        sim_env.current_decision_info = test_df.iloc[i]
        mint = sim_env.current_decision_info['mint']
        sim_env._token_ohlcv = all_token_data.get(mint)

        obs = sim_env._get_observation()
        normalized_obs = vec_env.normalize_obs(obs)
        action, _ = model.predict(normalized_obs, deterministic=True)
        
        benchmark_pnl = sim_env._simulate_trade()
        benchmark_trade_returns.append({'timestamp': test_df.iloc[i]['timestamp'], 'pnl': benchmark_pnl})
        
        if action == 1:
            agent_trade_returns.append({'timestamp': test_df.iloc[i]['timestamp'], 'pnl': benchmark_pnl})

    agent_returns_series = pd.DataFrame(agent_trade_returns).set_index('timestamp')['pnl'].sort_index()
    benchmark_returns_series = pd.DataFrame(benchmark_trade_returns).set_index('timestamp')['pnl'].sort_index()

    agent_daily_returns = simulate_portfolio(agent_returns_series, initial_capital=cfg.PORTFOLIO_STARTING_CAPITAL, capital_per_trade=cfg.PORTFOLIO_CAPITAL_PER_TRADE)
    benchmark_daily_returns = simulate_portfolio(benchmark_returns_series, initial_capital=cfg.PORTFOLIO_STARTING_CAPITAL, capital_per_trade=cfg.PORTFOLIO_CAPITAL_PER_TRADE)

    agent_metrics = calculate_performance_metrics(agent_daily_returns, "Agent", agent_returns_series)
    benchmark_metrics = calculate_performance_metrics(benchmark_daily_returns, "Benchmark", benchmark_returns_series)

    console = Console()
    table = Table(title=f"Scout Backtest Results: {os.path.basename(model_path)}", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("RL Agent", justify="right")
    table.add_column("Benchmark (Buy All)", justify="right")

    table.add_row("Total Trades", f"{agent_metrics.get('Agent Total Trades', 0)}", f"{benchmark_metrics.get('Benchmark Total Trades', 0)}")
    table.add_row("Win Rate", f"{agent_metrics.get('Agent Win Rate', 0):.2%}", f"{benchmark_metrics.get('Benchmark Win Rate', 0):.2%}")
    table.add_row("Average Return / Trade", f"{agent_metrics.get('Agent Average Return / Trade', 0):.4f}", f"{benchmark_metrics.get('Benchmark Average Return / Trade', 0):.4f}")
    table.add_row("Total Compounded Return", f"{agent_metrics.get('Agent Total Compounded Return', 0):.2%}", f"{benchmark_metrics.get('Benchmark Total Compounded Return', 0):.2%}")
    table.add_row("Sharpe Ratio", f"{agent_metrics.get('Agent Sharpe Ratio', 0):.2f}", f"{benchmark_metrics.get('Benchmark Sharpe Ratio', 0):.2f}")
    table.add_row("Max Drawdown", f"{agent_metrics.get('Agent Max Drawdown', 0):.2%}", f"{benchmark_metrics.get('Benchmark Max Drawdown', 0):.2%}")
    console.print(table)

    report_filename = os.path.join(model_base_dir, f"backtest_report_{model_prefix}.html")
    
    agent_report_series = agent_daily_returns
    agent_report_series.name = "RL Agent" # Set the name for the report title
    if not agent_report_series.empty:
        agent_report_series.index = agent_report_series.index.tz_localize(None)

    benchmark_report_series = benchmark_daily_returns
    benchmark_report_series.name = "Benchmark (Buy All)" # Set the name for the report title
    if not benchmark_report_series.empty:
        benchmark_report_series.index = benchmark_report_series.index.tz_localize(None)
    # --- FIX END ---
    
    # Conditionally generate the report based on whether benchmark data exists.
    if not benchmark_report_series.empty:
        qs.reports.html(agent_report_series, benchmark=benchmark_report_series, output=report_filename, title=f"RL Scout Agent vs. Benchmark")
    else:
        logger.warning("Benchmark strategy resulted in no trades. Generating report for Agent only.")
        qs.reports.html(agent_report_series, benchmark=None, output=report_filename, title=f"RL Scout Agent Performance")
    
    logger.info(f"✅ Detailed HTML report saved to: {report_filename}")

if __name__ == "__main__":
    setup_logging(logger_name="rl_scout_backtester")
    parser = argparse.ArgumentParser(description="Backtest for Scout RL Trading Agent")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the trained .zip model file.")
    args = parser.parse_args()
    
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    run_backtest(model_path=args.model_path)
