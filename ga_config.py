# FILE: ga_config.py

"""
Configuration for the Genetic Algorithm (GA) optimizer.

This module defines the parameters to be optimized by the GA,
their respective ranges (boundaries), data splitting configurations,
backtesting settings, and GA hyperparameters.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Union

# --- Parameters to Optimize ---
# Define the parameters from the main config that the GA will tune.
# Each parameter is a dictionary with 'name', 'values' (for discrete choices)
# or 'low'/'high' (for continuous ranges), and 'type' (int or float).
# Ensure 'name' matches the exact key used in the trading logic/backtester.
# Using discrete values simplifies the search space initially.

OPTIMIZABLE_PARAMETERS: List[Dict[str, Any]] = [
    # --- Standard Trading Parameters ---
    {
        "name": "SOL_TO_BUY",
        "values": [round(x * 0.1, 1) for x in range(1, 6)], # 0.1 to 0.5 SOL
        "type": float
    },
    {
        "name": "INITIAL_STOP_LOSS_PERCENT",
        "values": list(range(10, 71, 5)), # 10% to 70% SL
        "type": float
    },
    {
        "name": "FIRST_SELL_PERCENT",
        "values": list(range(20, 101, 10)), # 20% to 100% of initial tokens
        "type": float
    },
    {
        "name": "TRAILING_STOP_LOSS_PERCENT",
        "values": list(range(5, 41, 5)), # 5% to 40% trailing SL
        "type": float
    },
    {
        "name": "SECOND_TAKE_PROFIT_PERCENT",
        "values": list(range(100, 1001, 50)), # 100% to 1000% TP2
        "type": float
    },
    {
        "name": "FIRST_SELL_PROFIT_MARGIN",
        "values": list(range(20, 201, 20)), # 20% to 200% margin
        "type": float
    },
    
    # --- Buy Condition Thresholds ---
    {
        "name": "DEFAULT_VOLUME_THRESHOLD",
        "values": list(range(5000, 50001, 2500)), # 5k to 50k USD volume
        "type": int
    },
    {
        "name": "DEFAULT_MARKETCAP_THRESHOLD",
        "values": list(range(5000, 50001, 2500)), # 5k to 50k USD market cap
        "type": int
    },
    {
        "name": "MIN_VOLATILITY",
        "values": [round(x * 0.05, 2) for x in range(1, 11)], # 0.05% to 0.5%
        "type": float
    },
    {
        "name": "DEFAULT_RUGCHECK_SCORE_THRESHOLD",
        "values": list(range(201, 1002, 100)), # 201 to 1001 score
        "type": int
    },
    {
        "name": "DEFAULT_SOCIAL_SCORE_THRESHOLD",
        "values": list(range(100, 100, 1)), # 10 to 80 score
        "type": int
    },
    
    # --- PUMP.FUN Trend Reversal Parameters ---
    {
        "name": "USE_TREND_REVERSAL_CONFIRMATION",
        "values": [0, 1], # 0 for False, 1 for True
        "type": int 
    },
    {
        "name": "STOP_LOSS_COOLDOWN_MINUTES",
        "values": list(range(0, 61, 5)), # 0 to 60 minutes
        "type": int
    },
    {
        "name": "TREND_REVERSAL_RECENCY_HOURS",
        "values": list(range(1, 13, 1)), # 1 to 12 hours
        "type": int
    },
    {
        "name": "TREND_REVERSAL_RSI_NEUTRAL_LEVEL",
        "values": [round(x * 2.5 + 30, 1) for x in range(0, 13)], # 30.0 to 60.0
        "type": float
    },
    {
        "name": "INDICATOR_LOOKBACK_HOURS",
        "values": list(range(1, 7, 1)), # 1 to 6 hours
        "type": int
    },
    {
        "name": "RSI_PERIOD",
        "values": list(range(7, 29, 1)), # 7 to 28
        "type": int
    },
    {
        "name": "BBANDS_PERIOD",
        "values": list(range(10, 31, 2)), # 10 to 30
        "type": int
    },
    {
        "name": "BBANDS_STD_DEV",
        "values": [round(x * 0.1 + 1.5, 1) for x in range(0, 11)], # 1.5 to 2.5
        "type": float
    },
    {
        "name": "FAST_EMA_PERIOD",
        "values": list(range(5, 16, 1)), # 5 to 15
        "type": int
    },
    {
        "name": "SLOW_EMA_PERIOD",
        "values": list(range(15, 31, 1)), # 15 to 30
        "type": int
    },

    # --- [NEW] DEXSCREENER Trend Reversal Parameters ---
    {
        "name": "DEX_REVERSAL_LOOKBACK_MINUTES",
        "values": list(range(15, 61, 5)), # 15 to 60 minutes
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_SNAPSHOTS",
        "values": list(range(3, 11, 1)), # 3 to 10 snapshots
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_LIQUIDITY_USD",
        "values": list(range(1000, 10001, 1000)), # 1k to 10k USD
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_BUY_SELL_RATIO",
        "values": [round(x * 0.1 + 1.1, 1) for x in range(0, 20)], # 1.1 to 3.0
        "type": float
    },
    {
        "name": "DEX_REVERSAL_MIN_CONFIRMATIONS",
        "values": list(range(1, 6, 1)), # 1 to 5 confirmations
        "type": int
    },
]

# --- GA Settings ---
POPULATION_SIZE: int = 60 # Slightly larger population
NUM_GENERATIONS: int = 100 # More generations for convergence

# Crossover and mutation rates: Higher rates for exploration
CROSSOVER_PROBABILITY: float = 0.8 # Higher crossover probability for exploration
# Mutation probability: 0.5 is a good starting point for exploration
MUTATION_PROBABILITY: float = 0.5 # Slightly higher mutation for exploration

KEEP_ELITISM: int = 3 # Keep top 3 solutions

# Parent selection method: 'sss' (steady-state), 'rws' (roulette), 'sus', 'rank', 'tournament'
# 'sss' is a steady-state selection method that maintains diversity
# 'rws' is roulette wheel selection, 'sus' is stochastic universal sampling
# 'rank' is rank-based selection, 'tournament' is tournament selection
# 'sss' is generally more stable and maintains diversity in the population
PARENT_SELECTION_TYPE: str = "sss"


# 'single_point' is a good starting point for exploration
# 'two_points' is more complex but can be beneficial in some cases
# 'uniform' is a more complex crossover method that can be beneficial in some cases
# 'scattered' is a more complex crossover method that can be beneficial in some cases
CROSSOVER_TYPE: str = "single_point" # 'two_points', 'uniform', 'scattered'

# 'random' mutation is a good starting point for exploration
# 'adaptive' mutation is more complex and can be beneficial in some cases
MUTATION_TYPE: str = "random" # 'adaptive' possible but complex


# --- Fitness Function Settings ---
# Metric from backtest results dict ('total_pnl', 'win_rate', 'max_drawdown', 'final_portfolio_value')
FITNESS_METRIC: str = "final_portfolio_value" # Focus on ending portfolio value
FITNESS_GOAL: str = "max" # Maximize the metric

# Fitness Sampling: Number of random tokens to sample from the training set for each individual's fitness evaluation.
# Set to 0 or None to use all tokens (original behavior).
GA_FITNESS_SAMPLE_SIZE: Union[int, None] = 0 # e.g., Evaluate each individual on 15 random tokens

# --- Data Settings ---
# Percentage split for training, validation, test sets (sum to 1.0)
DATA_SPLIT: Dict[str, float] = {
    "training": 0.6,    # 60% for GA training iterations
    "validation": 0.2,  # 20% for intermediate checks (optional)
    "test": 0.2         # 20% for final evaluation
}

# Overall date range for historical data fetch
# NOTE: THESE DATES ARE EXAMPLES - ADJUST TO YOUR ACTUAL DATA RANGE
HISTORICAL_DATA_START_TS: datetime = datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
HISTORICAL_DATA_END_TS: datetime = datetime(2025, 7, 5, 23, 59, 0, tzinfo=timezone.utc) # Extended range example

# --- Backtester Settings ---
BACKTEST_INITIAL_CAPITAL: float = 100.0 # In SOL

# --- Multiprocessing Settings ---
# 'auto' lets ga_optimizer determine cores (e.g., cpu_count() - 2) or set specific number (e.g., 4)
MULTIPROCESSING_CORES: str = "auto"

# --- Results ---
RESULTS_DIR: str = "ga_optimization_results"