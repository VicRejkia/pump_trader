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
    {
        "name": "SOL_TO_BUY",
        "values": [round(x * 0.1, 1) for x in range(2, 11)], # 0.2 to 1.0 SOL in steps of 0.1
        "type": float
    },
    {
        "name": "INITIAL_STOP_LOSS_PERCENT",
        "values": list(range(10, 71, 5)), # 10% to 70% SL in steps of 5%
        "type": float
    },
    {
        "name": "FIRST_SELL_PERCENT",
        "values": list(range(20, 101, 10)), # 20% to 100% of initial tokens in steps of 10%
        "type": float
    },
    {
        "name": "TRAILING_STOP_LOSS_PERCENT",
        "values": list(range(5, 51, 5)), # 5% to 50% trailing SL in steps of 5% (tighter range)
        "type": float
    },
    {
        "name": "SECOND_TAKE_PROFIT_PERCENT",
        "values": list(range(100, 1001, 50)), # 100% to 1000% TP2 in steps of 50%
        "type": float
    },
    {
        "name": "FIRST_SELL_PROFIT_MARGIN",
        "values": list(range(20, 201, 20)), # 20% to 200% margin in steps of 20%
        "type": float
    },
    {
        "name": "DEFAULT_VOLUME_THRESHOLD",
        "values": list(range(5000, 50001, 2500)), # 5k to 50k USD volume in steps of 2.5k
        "type": int
    },
    {
        "name": "DEFAULT_MARKETCAP_THRESHOLD",
        "values": list(range(5000, 50001, 2500)), # 5k to 50k USD market cap in steps of 2.5k
        "type": int
    },
    {
        "name": "MIN_VOLATILITY",
        # Volatility as % change (e.g., 0.1 means 0.1%)
        "values": [round(x * 0.05, 2) for x in range(1, 11)], # 0.05% to 0.5% in steps of 0.05%
        "type": float
    },
    {
        "name": "DEFAULT_RUGCHECK_SCORE_THRESHOLD",
        "values": list(range(1, 1002, 100)), # 1 to 1001 score in steps of 100
        "type": int
    },
    {
        "name": "DEFAULT_SOCIAL_SCORE_THRESHOLD",
        "values": list(range(0, 81, 10)), # 0 to 80 score in steps of 10
        "type": int
    },
    # DEFAULT_TIME_INTERVALL is removed as optimization target - less impactful than thresholds
    # {
    #     "name": "DEFAULT_TIME_INTERVALL", # Typo kept for consistency
    #     "values": list(range(10, 61, 10)),
    #     "type": int
    # },
    # Add MIN_MARKET_CAP (emergency sell threshold) if desired
    {
        "name": "MIN_MARKET_CAP", # Emergency sell trigger USD market cap
        "values": list(range(3000, 5001, 500)), # 1k to 5k USD in steps of 500
        "type": int
    },
]

# --- GA Settings ---
POPULATION_SIZE: int = 60 # Slightly larger population
NUM_GENERATIONS: int = 100 # More generations for convergence

CROSSOVER_PROBABILITY: float = 0.8
MUTATION_PROBABILITY: float = 0.2 # Slightly higher mutation for exploration

KEEP_ELITISM: int = 3 # Keep top 3 solutions

# Parent selection method: 'sss' (steady-state), 'rws' (roulette), 'sus', 'rank', 'tournament'
PARENT_SELECTION_TYPE: str = "sss"
CROSSOVER_TYPE: str = "single_point" # 'two_points', 'uniform', 'scattered'
MUTATION_TYPE: str = "random" # 'adaptive' possible but complex

# --- Fitness Function Settings ---
# Metric from backtest results dict ('total_pnl', 'win_rate', 'max_drawdown', 'final_portfolio_value')
FITNESS_METRIC: str = "final_portfolio_value" # Focus on ending portfolio value
FITNESS_GOAL: str = "max" # Maximize the metric

# Fitness Sampling: Number of random tokens to sample from the training set for each individual's fitness evaluation.
# Set to 0 or None to use all tokens (original behavior).
GA_FITNESS_SAMPLE_SIZE: Union[int, None] = 15 # e.g., Evaluate each individual on 15 random tokens

# --- Data Settings ---
# Percentage split for training, validation, test sets (sum to 1.0)
DATA_SPLIT: Dict[str, float] = {
    "training": 0.6,    # 60% for GA training iterations
    "validation": 0.2,  # 20% for intermediate checks (optional)
    "test": 0.2         # 20% for final evaluation
}

# Overall date range for historical data fetch
# NOTE: THESE DATES ARE EXAMPLES - ADJUST TO YOUR ACTUAL DATA RANGE
HISTORICAL_DATA_START_TS: datetime = datetime(2025, 4, 19, 13, 0, 0, tzinfo=timezone.utc)
HISTORICAL_DATA_END_TS: datetime = datetime(2025, 4, 21, 15, 0, 0, tzinfo=timezone.utc) # Extended range example

# --- Backtester Settings ---
BACKTEST_INITIAL_CAPITAL: float = 10.0 # In SOL

# --- Multiprocessing Settings ---
# 'auto' lets ga_optimizer determine cores (e.g., cpu_count() - 2) or set specific number (e.g., 4)
MULTIPROCESSING_CORES: str = "auto"

# --- Results ---
RESULTS_DIR: str = "ga_optimization_results"