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
from rl_agent_framework.environments.solana_management_env import SolanaManagementEnv
from rl_tools.manager_data_preparation import load_prepared_manager_data
from bot_logger import setup_logging, logger

# --- FIX START: COPIED FROM SCOUT BACKTEST FOR REALISTIC PORTFOLIO SIMULATION ---
def simulate_portfolio(trade_returns: pd.Series) -> pd.Series:
    """
    Simulates portfolio performance to generate a realistic daily return series.
    Prevents portfolio value from dropping below zero.
    """
    if trade_returns.empty:
        return pd.Series(dtype=np.float64)
    
    # Use parameters from the config file instead of hardcoded values
    initial_capital = cfg.PORTFOLIO_STARTING_CAPITAL
    capital_per_trade = cfg.PORTFOLIO_CAPITAL_PER_TRADE

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
        current_capital = max(0, current_capital + profit) # A portfolio cannot go below zero.

        if current_capital == 0:
            is_blown_up = True

    # Calculate daily returns based on the changing portfolio value
    daily_returns = portfolio_value.pct_change().fillna(0)
    daily_returns[daily_returns < -1] = -1 # Cap any numerical noise
    return daily_returns
# --- FIX END ---

# --- FIX START: RE-IMPLEMENTED BENCHMARK LOGIC FROM MANAGER DATA PREPARATION ---
def simulate_benchmark_trade(trade_data: pd.DataFrame) -> float:
    """
    Simulates a trade using the original fixed SL/TP logic to get the correct
    benchmark PnL. This logic is identical to the simulation in the Scout's
    environment and the manager's data preparation script.

    Returns:
        The final realized PnL for the benchmark strategy.
    """
    if len(trade_data) < 2:
        return -1.0  # Treat as a full loss if there's no data to trade on.

    buy_price = trade_data['Close'].iloc[0]
    if buy_price <= 0:
        return -1.0

    # Use the same simulation parameters as the Scout's environment for a fair benchmark
    stop_loss_price = buy_price * (1 - cfg.ScoutConfig.SIM_INITIAL_STOP_LOSS_PERCENT / 100.0)
    first_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_FIRST_SELL_PROFIT_MARGIN / 100.0)
    second_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_SECOND_TAKE_PROFIT_PERCENT / 100.0)
    
    highest_price = buy_price
    first_tp_hit = False
    exit_price = None

    for i in range(1, min(len(trade_data), cfg.ScoutConfig.MAX_STEPS_PER_EPISODE)):
        current_price = trade_data['Close'].iloc[i]
        highest_price = max(highest_price, current_price)

        if current_price <= stop_loss_price:
            exit_price = current_price
            break
        if current_price >= second_tp_price:
            exit_price = current_price
            break
        if not first_tp_hit and current_price >= first_tp_price:
            first_tp_hit = True
            stop_loss_price = buy_price  # Adjust SL to breakeven
        if first_tp_hit:
            trailing_sl = highest_price * (1 - cfg.ScoutConfig.SIM_TRAILING_STOP_LOSS_PERCENT / 100.0)
            if current_price <= trailing_sl:
                exit_price = current_price
                break
    
    if exit_price is None:
        # If no exit condition was met, the trade timed out at the max episode steps
        final_index = min(len(trade_data) - 1, cfg.ScoutConfig.MAX_STEPS_PER_EPISODE -1)
        exit_price = trade_data['Close'].iloc[final_index]
        
    return (exit_price - buy_price) / buy_price
# --- FIX END ---


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
    model_prefix = ""
    if 'best_model.zip' in model_filename:
        model_dir = os.path.dirname(model_path)
        model_base_dir = os.path.dirname(model_dir)
        model_prefix = os.path.basename(model_dir).replace('_best', '')
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

    # --- FIX START: Refactor simulation loop to be cleaner and correct normalization ---
    # 1. Create a single environment instance for running the simulation step-by-step.
    sim_env = SolanaManagementEnv(trade_lifecycles=test_data)

    # 2. Load the VecNormalize stats into a wrapper. We will only use this to normalize observations.
    dummy_vec_env = DummyVecEnv([lambda: sim_env])
    vec_norm_stats = VecNormalize.load(vec_normalize_path, dummy_vec_env)
    vec_norm_stats.training = False
    vec_norm_stats.norm_reward = False
    # --- FIX END ---

    agent_trade_returns = []
    benchmark_trade_returns = []

    for trade_id, trade_df in tqdm(test_data.items(), desc="Backtesting Manager Decisions"):
        entry_timestamp = trade_df.index[0]
        
        # --- Simulate Agent ---
        # Force the simulation environment to the specific trade and reset it
        sim_env.force_trade(trade_id, trade_df)
        obs, _ = sim_env.reset() # Reset returns (obs, info) from the non-vectorized env
        
        done = False
        final_reward = 0.0
        while not done:
            # Manually normalize the observation using the loaded stats
            normalized_obs = vec_norm_stats.normalize_obs(obs)
            action, _ = model.predict(normalized_obs, deterministic=True)
            
            # Step the single simulation environment forward
            obs, reward, terminated, truncated, _ = sim_env.step(action)
            final_reward = reward
            done = terminated or truncated
        
        agent_pnl = final_reward
        agent_trade_returns.append({'timestamp': entry_timestamp, 'pnl': agent_pnl})

        # --- Simulate Benchmark (Fixed Rule) ---
        benchmark_pnl = simulate_benchmark_trade(trade_df)
        benchmark_trade_returns.append({'timestamp': entry_timestamp, 'pnl': benchmark_pnl})

    agent_returns_series = pd.DataFrame(agent_trade_returns).set_index('timestamp')['pnl'].sort_index()
    benchmark_returns_series = pd.DataFrame(benchmark_trade_returns).set_index('timestamp')['pnl'].sort_index()
    
    # --- FIX: USE PORTFOLIO SIMULATION FOR CORRECT DAILY RETURNS ---
    agent_daily_returns = simulate_portfolio(agent_returns_series)
    benchmark_daily_returns = simulate_portfolio(benchmark_returns_series)

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
    
    agent_report_series = agent_daily_returns
    agent_report_series.name = "RL Manager Agent" # Set the name
    if not agent_report_series.empty and agent_report_series.index.tz is not None:
        agent_report_series.index = agent_report_series.index.tz_localize(None)

    benchmark_report_series = benchmark_daily_returns
    benchmark_report_series.name = "Benchmark (Fixed Rule)" # Set the name
    if not benchmark_report_series.empty and benchmark_report_series.index.tz is not None:
        benchmark_report_series.index = benchmark_report_series.index.tz_localize(None)
    
    qs.reports.html(agent_report_series, benchmark=benchmark_report_series, output=report_filename, title=f"RL Manager Agent vs. Benchmark")
    logger.info(f"✅ Detailed HTML report saved to: {report_filename}")

if __name__ == "__main__":
    setup_logging(logger_name="rl_manager_backtester")
    parser = argparse.ArgumentParser(description="Backtest for RL Manager Agent")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the trained .zip model file.")
    args = parser.parse_args()
    
    warnings.filterwarnings("ignore", category=UserWarning)
    run_backtest(model_path=args.model_path)