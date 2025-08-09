# rl_tools/manager_backtest.py
"""
Backtesting script for the Manager (Trade Management) RL Agent.
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
from rl_tools.backtesting_utils import calculate_performance_metrics, simulate_portfolio

def simulate_benchmark_trade(trade_data: pd.DataFrame) -> float:
    """
    Simulates a trade using the original fixed SL/TP logic to get the correct
    benchmark PnL. This logic is identical to the simulation in the Scout's
    environment and the manager's data preparation script.
    """
    if len(trade_data) < 2: return -1.0
    buy_price = trade_data['Close'].iloc[0]
    if buy_price <= 0: return -1.0

    stop_loss_price = buy_price * (1 - cfg.ScoutConfig.SIM_INITIAL_STOP_LOSS_PERCENT / 100.0)
    first_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_FIRST_SELL_PROFIT_MARGIN / 100.0)
    second_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_SECOND_TAKE_PROFIT_PERCENT / 100.0)
    
    highest_price, first_tp_hit, exit_price = buy_price, False, None

    for i in range(1, min(len(trade_data), cfg.ScoutConfig.MAX_STEPS_PER_EPISODE)):
        current_price = trade_data['Close'].iloc[i]
        highest_price = max(highest_price, current_price)
        if current_price <= stop_loss_price: exit_price = current_price; break
        if current_price >= second_tp_price: exit_price = current_price; break
        if not first_tp_hit and current_price >= first_tp_price:
            first_tp_hit = True; stop_loss_price = buy_price
        if first_tp_hit:
            trailing_sl = highest_price * (1 - cfg.ScoutConfig.SIM_TRAILING_STOP_LOSS_PERCENT / 100.0)
            if current_price <= trailing_sl: exit_price = current_price; break
    
    if exit_price is None:
        final_index = min(len(trade_data) - 1, cfg.ScoutConfig.MAX_STEPS_PER_EPISODE -1)
        exit_price = trade_data['Close'].iloc[final_index]
        
    return (exit_price - buy_price) / buy_price

def run_backtest(model_path: str, data_window: str):
    """
    Performs a backtest of the trained Manager agent on the test dataset.
    
    Args:
        model_path (str): Path to the trained .zip model file.
        data_window (str): The data window to use for backtesting (e.g., 'full').
    """
    logger.info(f"--- Starting Backtest for Manager Model: {model_path} on '{data_window}' data ---")

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

    trade_lifecycles = load_prepared_manager_data(window['start'], window['end'])
    if not trade_lifecycles:
        logger.critical("Could not load processed manager data. Run data preparation first."); return

    all_trade_ids = sorted(list(trade_lifecycles.keys()))
    train_size = int(0.8 * len(all_trade_ids))
    test_ids = all_trade_ids[train_size:]
    test_data = {tid: trade_lifecycles[tid] for tid in test_ids}
    logger.info(f"Backtesting on {len(test_data)} trade lifecycles from the '{data_window}' data window.")

    sim_env = SolanaManagementEnv(trade_lifecycles=test_data)
    dummy_vec_env = DummyVecEnv([lambda: sim_env])
    vec_norm_stats = VecNormalize.load(vec_normalize_path, dummy_vec_env)
    vec_norm_stats.training = False
    vec_norm_stats.norm_reward = False

    agent_trade_returns, benchmark_trade_returns = [], []

    for trade_id, trade_df in tqdm(test_data.items(), desc="Backtesting Manager Decisions"):
        entry_timestamp = trade_df.index[0]
        
        sim_env.force_trade(trade_id, trade_df)
        obs, _ = sim_env.reset()
        done, final_reward = False, 0.0
        while not done:
            normalized_obs = vec_norm_stats.normalize_obs(obs)
            action, _ = model.predict(normalized_obs, deterministic=True)
            obs, reward, terminated, truncated, _ = sim_env.step(action)
            final_reward = reward
            done = terminated or truncated
        
        agent_trade_returns.append({'timestamp': entry_timestamp, 'pnl': final_reward})
        benchmark_trade_returns.append({'timestamp': entry_timestamp, 'pnl': simulate_benchmark_trade(trade_df)})

    agent_returns_series = pd.DataFrame(agent_trade_returns).set_index('timestamp')['pnl'].sort_index()
    benchmark_returns_series = pd.DataFrame(benchmark_trade_returns).set_index('timestamp')['pnl'].sort_index()
    
    agent_daily_returns = simulate_portfolio(agent_returns_series)
    benchmark_daily_returns = simulate_portfolio(benchmark_returns_series)
    agent_metrics = calculate_performance_metrics(agent_daily_returns, "Manager Agent", agent_returns_series)
    benchmark_metrics = calculate_performance_metrics(benchmark_daily_returns, "Benchmark", benchmark_returns_series)

    console = Console()
    table = Table(title=f"Manager Backtest Results: {os.path.basename(model_path)} on '{data_window}' data", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan"); table.add_column("RL Manager Agent", justify="right"); table.add_column("Benchmark (Fixed Rule)", justify="right")
    table.add_row("Total Trades", f"{agent_metrics.get('Manager Agent Total Trades', 0)}", f"{benchmark_metrics.get('Benchmark Total Trades', 0)}")
    table.add_row("Win Rate", f"{agent_metrics.get('Manager Agent Win Rate', 0):.2%}", f"{benchmark_metrics.get('Benchmark Win Rate', 0):.2%}")
    table.add_row("Average Return / Trade", f"{agent_metrics.get('Manager Agent Average Return / Trade', 0):.4f}", f"{benchmark_metrics.get('Benchmark Average Return / Trade', 0):.4f}")
    table.add_row("Total Compounded Return", f"{agent_metrics.get('Manager Agent Total Compounded Return', 0):.2%}", f"{benchmark_metrics.get('Benchmark Total Compounded Return', 0):.2%}")
    table.add_row("Sharpe Ratio", f"{agent_metrics.get('Manager Agent Sharpe Ratio', 0):.2f}", f"{benchmark_metrics.get('Benchmark Sharpe Ratio', 0):.2f}")
    table.add_row("Max Drawdown", f"{agent_metrics.get('Manager Agent Max Drawdown', 0):.2%}", f"{benchmark_metrics.get('Benchmark Max Drawdown', 0):.2%}")
    console.print(table)

    report_filename = os.path.join(model_base_dir, f"backtest_report_{model_prefix}.html")
    agent_report_series = agent_daily_returns; agent_report_series.name = "RL Manager Agent"
    if not agent_report_series.empty and agent_report_series.index.tz is not None: agent_report_series.index = agent_report_series.index.tz_localize(None)
    benchmark_report_series = benchmark_daily_returns; benchmark_report_series.name = "Benchmark (Fixed Rule)"
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
                title=f"RL Manager Agent vs. Benchmark"
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
    parser = argparse.ArgumentParser(description="Backtest for Manager RL Trading Agent")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the trained .zip model file.")
    parser.add_argument(
        "--data-window", type=str, default=cfg.DEFAULT_DATA_WINDOW,
        choices=cfg.DATA_WINDOWS.keys(),
        help="The data window to use for backtesting."
    )
    args = parser.parse_args()

    setup_logging(logger_name="rl_manager_backtester")
    warnings.filterwarnings("ignore", category=UserWarning)
    
    run_backtest(model_path=args.model_path, data_window=args.data_window)