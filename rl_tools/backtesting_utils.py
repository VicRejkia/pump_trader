# rl_tools/backtesting_utils.py
"""
Shared utility functions for the RL backtesting scripts.
This avoids code duplication and ensures consistent performance evaluation.
"""
import pandas as pd
import quantstats as qs
import numpy as np

from config import rl_config as cfg

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
    # Ensure index is datetime before resampling
    if not isinstance(trade_returns.index, pd.DatetimeIndex):
        raise TypeError("trade_returns Series must have a DatetimeIndex.")
        
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