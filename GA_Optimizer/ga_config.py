# FILE: ga_config.py

"""
Configuration for the Genetic Algorithm (GA) optimizer.

This module defines the parameters to be optimized by the GA,
their respective ranges (boundaries), data splitting configurations,
backtesting settings, and GA hyperparameters.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Union

# --- Parameters to Optimize (Fine-Tuned Set) ---
OPTIMIZABLE_PARAMETERS: List[Dict[str, Any]] = [
    # --- Standard Trading Parameters ---
    {
        "name": "SOL_TO_BUY",
        "values": [round(x * 0.05, 2) for x in range(6, 11)],  # 0.3 to 0.5 SOL
        "type": float
    },
    {
        "name": "INITIAL_STOP_LOSS_PERCENT",
        "values": list(range(8, 16, 1)),  # 8% to 15%
        "type": float
    },
    {
        "name": "FIRST_SELL_PERCENT",
        "values": list(range(15, 36, 5)), # 15% to 35%
        "type": float
    },
    {
        "name": "TRAILING_STOP_LOSS_PERCENT",
        "values": list(range(12, 19, 1)), # 12% to 18%
        "type": float
    },
    {
        "name": "SECOND_TAKE_PROFIT_PERCENT",
        "values": list(range(200, 351, 25)), # 200% to 350%
        "type": float
    },
    {
        "name": "FIRST_SELL_PROFIT_MARGIN",
        "values": list(range(20, 101, 10)), # 20% to 100% margin
        "type": float
    },

    # --- Buy Condition Thresholds ---
    {
        "name": "DEFAULT_VOLUME_THRESHOLD",
        "values": list(range(3000, 8001, 1000)), # 3k to 8k USD volume
        "type": int
    },
    {
        "name": "DEFAULT_MARKETCAP_THRESHOLD",
        "values": list(range(5000, 10001, 1000)), # 5k to 10k USD market cap
        "type": int
    },
    {
        "name": "MIN_VOLATILITY",
        "values": [round(x * 0.01, 2) for x in range(20, 31)], # 0.20 to 0.30
        "type": float
    },
    {
        "name": "DEFAULT_RUGCHECK_SCORE_THRESHOLD",
        "values": list(range(850, 1001, 10)), # 850 to 1000
        "type": int
    },
    {
        "name": "DEFAULT_SOCIAL_SCORE_THRESHOLD",
        "values": list(range(60, 81, 2)), # 60 to 80
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
        "values": list(range(15, 31, 5)), # 15 to 30 minutes
        "type": int
    },
    {
        "name": "TREND_REVERSAL_RECENCY_HOURS",
        "values": list(range(6, 11, 1)), # 6 to 10 hours
        "type": int
    },
    {
        "name": "TREND_REVERSAL_RSI_NEUTRAL_LEVEL",
        "values": [round(x * 1.0 + 40, 1) for x in range(0, 11)], # 40.0 to 50.0
        "type": float
    },
    {
        "name": "INDICATOR_LOOKBACK_HOURS",
        "values": list(range(3, 7, 1)), # 3 to 6 hours
        "type": int
    },
    {
        "name": "RSI_PERIOD",
        "values": list(range(8, 15, 1)), # 8 to 14
        "type": int
    },
    {
        "name": "BBANDS_PERIOD",
        "values": list(range(15, 23, 1)), # 15 to 22
        "type": int
    },
    {
        "name": "BBANDS_STD_DEV",
        "values": [round(x * 0.1 + 1.8, 1) for x in range(0, 8)], # 1.8 to 2.5
        "type": float
    },
    {
        "name": "FAST_EMA_PERIOD",
        "values": list(range(7, 14, 1)), # 7 to 13
        "type": int
    },
    {
        "name": "SLOW_EMA_PERIOD",
        "values": list(range(18, 26, 1)), # 18 to 25
        "type": int
    },

    # --- DEXSCREENER Trend Reversal Parameters ---
    {
        "name": "DEX_REVERSAL_LOOKBACK_MINUTES",
        "values": list(range(15, 31, 5)), # 15 to 30 minutes
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_SNAPSHOTS",
        "values": list(range(2, 6, 1)), # 2 to 5 snapshots
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_LIQUIDITY_USD",
        "values": list(range(500, 4001, 500)), # 500 to 4k USD
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_BUY_SELL_RATIO",
        "values": [round(x * 0.2 + 1.2, 1) for x in range(0, 10)], # 1.2 to 3.0
        "type": float
    },
    {
        "name": "DEX_REVERSAL_MIN_CONFIRMATIONS",
        "values": list(range(1, 4, 1)), # 1 to 3 confirmations
        "type": int
    },
]

# --- GA Settings ---
POPULATION_SIZE: int = 60
NUM_GENERATIONS: int = 100
CROSSOVER_PROBABILITY: float = 0.8
MUTATION_PROBABILITY: float = 0.5
KEEP_ELITISM: int = 3
PARENT_SELECTION_TYPE: str = "sss"
CROSSOVER_TYPE: str = "single_point"
MUTATION_TYPE: str = "random"

# --- Fitness Function Settings ---
FITNESS_METRIC: str = "final_portfolio_value" # Focus on ending portfolio value
FITNESS_GOAL: str = "max" # Maximize the metric

# --- [FIX & OPTIMIZATION] ---
# Instead of backtesting every solution against all ~1700 training tokens,
# we test against a random sample. This dramatically speeds up the process
# and reduces memory pressure, fixing the crash. A sample size of 30-50
# is usually sufficient. Set to 0 to disable and use all tokens.
GA_FITNESS_SAMPLE_SIZE: Union[int, None] = 0

# --- Data Settings ---
DATA_SPLIT: Dict[str, float] = {
    "training": 0.6,
    "validation": 0.2,
    "test": 0.2
}
HISTORICAL_DATA_START_TS: datetime = datetime(2025, 9, 20, 0, 0, 0)
HISTORICAL_DATA_END_TS: datetime = datetime(2025, 9, 26, 0, 0, 0)

# --- Backtester Settings ---
BACKTEST_INITIAL_CAPITAL: float = 100.0 # In SOL

# --- [FIX] Multiprocessing Settings ---
# Running 30 processes with a large dataset causes resource exhaustion.
# Reducing this to a more reasonable number like 8, 12, or half your CPU cores
# is crucial for stability on Windows.
MULTIPROCESSING_CORES: str = "12"

# --- Results ---
RESULTS_DIR: str = "ga_optimization_results"