# FILE: scripts/backtest.py (REFACTORED)

import argparse
import os
import pandas as pd
import numpy as np
import quantstats as qs
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

import stable_baselines3 as sb3
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# Add the project root to the Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_rl_agent import rl_config as cfg
# Import the new environment, which contains the simulation logic we need
from trading_rl_agent.environments.solana_decision_env import SolanaDecisionEnv
from scripts.data_utils import load_prepared_data_for_training
from bot_logger import setup_logging, logger

def calculate_performance_metrics(daily_returns: pd.Series, title: str, all_trades: pd.Series) -> dict:
    """
    Calculates key performance metrics for a series of daily trade returns,
    plus metrics from the raw trade data.
    """
    if daily_returns.empty or all_trades.empty:
        return {f"{title} Total Trades": 0}

    metrics = {
        f"{title} Total Trades": len(all_trades),
        f"{title} Win Rate": (all_trades > 0).mean(),
        f"{title} Average Return / Trade": all_trades.mean(),
        f"{title} Total Return": qs.stats.comp(daily_returns),
        f"{title} Sharpe Ratio": qs.stats.sharpe(daily_returns),
        f"{title} Max Drawdown": qs.stats.max_drawdown(daily_returns),
    }
    return metrics

def run_backtest(model_path: str):
    """
    Performs a backtest of the trained 'Decision Gate' agent on the test dataset.
    """
    logger.info(f"--- Starting Backtest for Model: {model_path} ---")
    
    # --- Load Model and Normalization Stats ---
    if not os.path.exists(model_path):
        logger.critical(f"Model file not found at: {model_path}")
        return

    model = sb3.PPO.load(model_path, device='cpu')
    
    # Robustly find the vec_normalize stats path
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
        logger.critical(f"VecNormalize stats not found at: {vec_normalize_path}. Cannot run backtest.")
        return

    # --- Load Test Data ---
    decision_df, all_token_data = load_prepared_data_for_training()
    if decision_df is None or not all_token_data:
        logger.critical("Could not load processed data. Run data_utils.py first.")
        return
        
    # Create the test set (the 20% of data the agent has never seen)
    train_df = decision_df.sample(frac=0.8, random_state=42)
    test_df = decision_df.drop(train_df.index).reset_index(drop=True)
    
    logger.info(f"Backtesting on {len(test_df)} decision points.")

    # --- Create a Dummy Environment to load normalization stats ---
    dummy_env = DummyVecEnv([lambda: SolanaDecisionEnv(df=test_df, full_token_data=all_token_data)])
    vec_env = VecNormalize.load(vec_normalize_path, dummy_env)
    vec_env.training = False
    vec_env.norm_reward = False

    # --- Backtesting Loop ---
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

    # --- Aggregate Results & Generate Report ---
    agent_returns_series = pd.DataFrame(agent_trade_returns).set_index('timestamp')['pnl'].sort_index()
    benchmark_returns_series = pd.DataFrame(benchmark_trade_returns).set_index('timestamp')['pnl'].sort_index()

    # --- THIS IS THE FIX: Resample to daily returns for stable metrics ---
    agent_daily_returns = agent_returns_series.resample('D').sum()
    benchmark_daily_returns = benchmark_returns_series.resample('D').sum()
    # --- END OF FIX ---

    agent_metrics = calculate_performance_metrics(agent_daily_returns, "Agent", agent_returns_series)
    benchmark_metrics = calculate_performance_metrics(benchmark_daily_returns, "Benchmark", benchmark_returns_series)

    # --- Display Rich Table in Console ---
    console = Console()
    table = Table(title=f"Backtest Results: {os.path.basename(model_path)}", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("RL Agent", justify="right")
    table.add_column("Benchmark (Buy All)", justify="right")

    table.add_row("Total Trades", f"{agent_metrics.get('Agent Total Trades', 0)}", f"{benchmark_metrics.get('Benchmark Total Trades', 0)}")
    table.add_row("Win Rate", f"{agent_metrics.get('Agent Win Rate', 0):.2%}", f"{benchmark_metrics.get('Benchmark Win Rate', 0):.2%}")
    table.add_row("Average Return / Trade", f"{agent_metrics.get('Agent Average Return', 0):.4f}", f"{benchmark_metrics.get('Benchmark Average Return', 0):.4f}")
    table.add_row("Total Compounded Return", f"{agent_metrics.get('Agent Total Return', 0):.2%}", f"{benchmark_metrics.get('Benchmark Total Return', 0):.2%}")
    table.add_row("Sharpe Ratio", f"{agent_metrics.get('Agent Sharpe Ratio', 0):.2f}", f"{benchmark_metrics.get('Benchmark Sharpe Ratio', 0):.2f}")
    table.add_row("Max Drawdown", f"{agent_metrics.get('Agent Max Drawdown', 0):.2%}", f"{benchmark_metrics.get('Benchmark Max Drawdown', 0):.2%}")
    console.print(table)

    # --- Save QuantStats HTML Report ---
    report_filename = os.path.join(model_base_dir, f"backtest_report_{model_prefix}.html")
    
    # Convert timezone-aware index to timezone-naive before passing to quantstats
    if not agent_daily_returns.empty:
        agent_daily_returns.index = agent_daily_returns.index.tz_localize(None)
    if not benchmark_daily_returns.empty:
        benchmark_daily_returns.index = benchmark_daily_returns.index.tz_localize(None)
    
    qs.reports.html(agent_daily_returns, benchmark=benchmark_daily_returns, output=report_filename, title=f"RL Agent vs. Benchmark")
    logger.info(f"✅ Detailed HTML report saved to: {report_filename}")

if __name__ == "__main__":
    setup_logging(logger_name="rl_backtester")
    parser = argparse.ArgumentParser(description="Backtest for RL Trading Agent")
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the trained .zip model file (e.g., best_model.zip)."
    )
    args = parser.parse_args()
    
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)

    run_backtest(model_path=args.model_path)
