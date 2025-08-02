# FILE: scripts/backtest.py

import argparse
import os
import pandas as pd
import numpy as np
import quantstats as qs
from rich.console import Console
from rich.table import Table

import stable_baselines3 as sb3
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# Add the project root to the Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_rl_agent import rl_config
from trading_rl_agent.environments.solana_env import SolanaPortfolioEnv
from trading_rl_agent.policies.custom_nets import CustomCombinedExtractor
from scripts.data_utils import load_processed_data
from bot_logger import setup_logging, logger

def calculate_performance_metrics(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> dict:
    """Calculates key performance metrics using quantstats."""
    metrics = {
        "Cumulative Return": qs.stats.comp(portfolio_returns),
        "Annualized Return": qs.stats.avg_return(portfolio_returns),
        "Annualized Volatility": qs.stats.volatility(portfolio_returns),
        "Sharpe Ratio": qs.stats.sharpe(portfolio_returns),
        "Sortino Ratio": qs.stats.sortino(portfolio_returns),
        "Max Drawdown": qs.stats.max_drawdown(portfolio_returns),
        "Calmar Ratio": qs.stats.calmar(portfolio_returns),
    }

    benchmark_metrics = {
        "Benchmark Cumulative Return": qs.stats.comp(benchmark_returns),
        "Benchmark Annualized Return": qs.stats.avg_return(benchmark_returns),
        "Benchmark Volatility": qs.stats.volatility(benchmark_returns),
        "Benchmark Sharpe Ratio": qs.stats.sharpe(benchmark_returns),
    }
    
    metrics.update(benchmark_metrics)
    return metrics

def run_episode(env, model) -> pd.Series:
    """Runs a single episode in the environment and returns portfolio values."""
    obs = env.reset()
    if not isinstance(obs, dict):
        error_msg = f"env.reset() returned an object of type {type(obs)}, but a dictionary was expected. Value: {obs}"
        logger.critical(error_msg)
        raise TypeError(error_msg)
        
    is_done = False
    portfolio_values = [env.get_attr('portfolio_value')[0]]
    
    while not is_done:
        unbatched_obs = {key: value[0] for key, value in obs.items()}
        action, _ = model.predict(unbatched_obs, deterministic=True)
        
        action = action.reshape(1, -1)
        
        obs, reward, done, info = env.step(action)
        
        is_done = done[0]
        portfolio_values.append(info[0]['portfolio_value'])
        
    start_time = env.get_attr('min_ts')[0]
    freq = env.get_attr('decision_freq')[0]
    index = pd.to_datetime([start_time + i * freq for i in range(len(portfolio_values))])
    
    portfolio_series = pd.Series(portfolio_values, index=index)
    
    # Remove duplicate timestamps before returning
    portfolio_series = portfolio_series.loc[~portfolio_series.index.duplicated(keep='last')]
    
    return portfolio_series

def run_backtest(model_path: str, n_splits: int = 4):
    """
    Performs walk-forward validation on a trained RL agent.
    """
    logger.info(f"--- Starting Backtest for Model: {model_path} ---")
    
    # --- Load Model and Normalization Stats ---
    if not os.path.exists(model_path):
        logger.critical(f"Model file not found at: {model_path}")
        return

    model = sb3.PPO.load(model_path, device='cpu')
    
    model_dir = ""
    vec_normalize_path = ""
    
    if os.path.basename(model_path) == 'best_model.zip':
        model_dir = os.path.dirname(model_path)
        parent_dir = os.path.dirname(model_dir)
        model_prefix = os.path.basename(model_dir).replace('_best', '')
        vec_normalize_path = os.path.join(parent_dir, f"{model_prefix}_vecnormalize.pkl")
    else:
        model_dir = os.path.dirname(model_path)
        model_filename = os.path.basename(model_path)
        model_prefix = os.path.splitext(model_filename)[0].replace('_final', '')
        vec_normalize_path = os.path.join(parent_dir, f"{model_prefix}_vecnormalize.pkl")

    if not os.path.exists(vec_normalize_path):
        logger.critical(f"VecNormalize stats not found. Constructed path was: {vec_normalize_path}")
        return

    # --- Load and Combine All Available Data for Splitting ---
    train_data = load_processed_data('train')
    val_data = load_processed_data('validation')
    if not train_data or not val_data:
        logger.critical("Could not load processed train/validation data.")
        return
        
    all_data = {**train_data, **val_data}
    sorted_mints = sorted(all_data.keys(), key=lambda m: all_data[m].index.min())

    # --- Walk-Forward Validation Loop ---
    max_tokens_per_split = rl_config.MAX_TOKENS_IN_UNIVERSE
    n_splits = len(sorted_mints) // max_tokens_per_split
    if n_splits == 0:
        n_splits = 1 

    logger.info(f"Adjusting to {n_splits} splits to respect MAX_TOKENS_IN_UNIVERSE ({max_tokens_per_split}).")
    split_size = len(sorted_mints) // n_splits

    all_portfolio_returns = []
    all_benchmark_returns = []

    for i in range(n_splits):
        logger.info(f"\n--- Running Walk-Forward Split {i+1}/{n_splits} ---")
        test_start_index = i * split_size
        test_end_index = (i + 1) * split_size
        test_mints = sorted_mints[test_start_index:test_end_index]
        
        if not test_mints:
            logger.warning(f"No tokens for split {i+1}, skipping.")
            continue
            
        test_data_map = {m: all_data[m] for m in test_mints}
        
        # --- Create Test Environment ---
        env_kwargs = {'token_data_map': test_data_map}
        test_env = make_vec_env(SolanaPortfolioEnv, n_envs=1, env_kwargs=env_kwargs)
        test_env = VecNormalize.load(vec_normalize_path, test_env)
        test_env.training = False
        test_env.norm_reward = False

        # --- Run Agent Episode ---
        portfolio_values = run_episode(test_env, model)
        agent_returns = portfolio_values.pct_change().dropna()
        all_portfolio_returns.append(agent_returns)
        logger.info(f"Agent finished split {i+1}. Final Portfolio Value: {portfolio_values.iloc[-1]:.2f} SOL")

        # --- Run Benchmark (Equal-Weight Buy & Hold) ---
        combined_returns_for_split = pd.concat(
            [df['Close'].pct_change().dropna() for df in test_data_map.values()]
        )
        benchmark_returns = combined_returns_for_split.groupby(combined_returns_for_split.index).mean()
        all_benchmark_returns.append(benchmark_returns)
        
        test_env.close()

    if not all_portfolio_returns:
        logger.error("Backtest failed to produce any results.")
        return

    # - Aggregate Results & Generate Report -
    final_agent_returns = pd.concat(all_portfolio_returns).sort_index()
    combined_benchmark_returns = pd.concat(all_benchmark_returns).sort_index()

    # CRITICAL FIX: Handle timestamp precision issues and ensure uniqueness
    # 1. Round timestamps to the nearest minute (or your data frequency)
    final_agent_returns.index = final_agent_returns.index.floor('min')
    combined_benchmark_returns.index = combined_benchmark_returns.index.floor('min')

    # 2. Properly de-duplicate using groupby (more reliable than duplicated())
    final_agent_returns = final_agent_returns.groupby(final_agent_returns.index).last()
    final_benchmark_returns = combined_benchmark_returns.groupby(combined_benchmark_returns.index).mean()

    # 3. Ensure timezone-naive indices (completing the previous fix)
    if hasattr(final_agent_returns.index, 'tz') and final_agent_returns.index.tz is not None:
        final_agent_returns.index = final_agent_returns.index.tz_localize(None)
    if hasattr(final_benchmark_returns.index, 'tz') and final_benchmark_returns.index.tz is not None:
        final_benchmark_returns.index = final_benchmark_returns.index.tz_localize(None)

    # 4. Align the indices
    common_index = final_agent_returns.index.intersection(final_benchmark_returns.index)
    aligned_agent = final_agent_returns.loc[common_index]
    aligned_benchmark = final_benchmark_returns.loc[common_index]

    # 5. Reindex the benchmark to the agent's timeline
    aligned_benchmark = aligned_benchmark.reindex(aligned_agent.index, method='ffill').fillna(0)

    # 6. CRITICAL: Verify uniqueness before passing to quantstats
    if aligned_agent.index.has_duplicates:
        logger.warning("Agent returns still have duplicate timestamps after cleanup!")
        aligned_agent = aligned_agent[~aligned_agent.index.duplicated(keep='last')]
    if aligned_benchmark.index.has_duplicates:
        logger.warning("Benchmark returns still have duplicate timestamps after cleanup!")
        aligned_benchmark = aligned_benchmark[~aligned_benchmark.index.duplicated(keep='last')]

    # 7. Final sanity check
    assert not aligned_agent.index.has_duplicates, "Agent returns still have duplicate timestamps"
    assert not aligned_benchmark.index.has_duplicates, "Benchmark returns still have duplicate timestamps"

    metrics = calculate_performance_metrics(aligned_agent, aligned_benchmark)

    # --- Display Rich Table in Console ---
    console = Console()
    table = Table(title=f"Walk-Forward Backtest Results: {os.path.basename(model_path)}", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("RL Agent", justify="right")
    table.add_column("Benchmark (Equal B&H)", justify="right")

    table.add_row("Cumulative Return", f"{metrics['Cumulative Return']:.2%}", f"{metrics['Benchmark Cumulative Return']:.2%}")
    table.add_row("Annualized Return", f"{metrics['Annualized Return']:.2%}", f"{metrics['Benchmark Annualized Return']:.2%}")
    table.add_row("Annualized Volatility", f"{metrics['Annualized Volatility']:.2%}", f"{metrics['Benchmark Volatility']:.2%}")
    table.add_row("Sharpe Ratio", f"{metrics['Sharpe Ratio']:.2f}", f"{metrics['Benchmark Sharpe Ratio']:.2f}")
    table.add_row("Sortino Ratio", f"{metrics['Sortino Ratio']:.2f}", "-")
    table.add_row("Max Drawdown", f"{metrics['Max Drawdown']:.2%}", "-")
    table.add_row("Calmar Ratio", f"{metrics['Calmar Ratio']:.2f}", "-")
    console.print(table)

    # --- Save QuantStats HTML Report ---
    report_filename = f"tensorboard_logs/backtest_report_{os.path.basename(model_dir)}.html"
    qs.reports.html(aligned_agent, benchmark=aligned_benchmark, output=report_filename, title=f"RL Agent vs. Benchmark")
    logger.info(f"✅ Detailed HTML report saved to: {report_filename}")

if __name__ == "__main__":
    setup_logging(logger_name="rl_backtester")
    parser = argparse.ArgumentParser(description="Walk-Forward Backtest for RL Trading Agent")
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the trained .zip model file."
    )
    args = parser.parse_args()
    
    # Suppress UserWarning from pandas_ta in quantstats
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)

    run_backtest(model_path=args.model_path)