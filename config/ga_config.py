# FILE: ga_config.py

"""
Configuration for the Genetic Algorithm (GA) optimizer.

This module defines the parameters to be optimized by the GA,
their respective ranges (boundaries), data splitting configurations,
backtesting settings, and GA hyperparameters.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Union
import numpy as np

# --- Parameters to Optimize (Fine-Tuned Set) ---
# This set provides more focused ranges and includes all new parameters
# for both Pump.fun and DexScreener trend reversal logic.
OPTIMIZABLE_PARAMETERS: List[Dict[str, Any]] = [
    # --- Standard Trading Parameters ---
    {
        "name": "SOL_TO_BUY",
        # [FIXED] The pygad library expects a list of options for "values".
        # To fix this parameter to a single value, it must be enclosed in a list.
        "values": [0.5],
        "type": float
    },
    {
        "name": "INITIAL_STOP_LOSS_PERCENT",
        "values": list(range(4, 56, 2)),    # Range: 8, 9, 10, ..., 50
        "type": float
    },
    {
        "name": "FIRST_SELL_PERCENT",
        "values": list(range(5, 101, 5)),    # Range: 5, 10, 15, ..., 65
        "type": float
    },
    {
        "name": "TRAILING_STOP_LOSS_PERCENT",
        "values": list(range(5, 61, 5)),    # Range: 5, 10, 15, ..., 70
        "type": float
    },
    {
        "name": "SECOND_TAKE_PROFIT_PERCENT",
        "values": list(range(200, 601, 50)), # Range: 200, 250, ..., 600
        "type": float
    },
    {
        "name": "FIRST_SELL_PROFIT_MARGIN",
        "values": list(range(10, 201, 50)), # Range: 10, 60, 110, 160
        "type": float
    },

    # --- Buy Condition Thresholds ---
    {
        "name": "DEFAULT_VOLUME_THRESHOLD",
        "values": list(range(1000, 10001, 1000)), # Range: 2000, 3000, ..., 10000
        "type": int
    },
    {
        "name": "DEFAULT_MARKETCAP_THRESHOLD",
        "values": list(range(5000, 30001, 1000)), # Range: 5000, 6000, ..., 30000
        "type": int
    },
    {
        "name": "MIN_VOLATILITY",
        "values": [round(x * 0.01, 2) for x in range(10, 31)], # Range: 0.10, 0.11, ..., 0.30
        "type": float
    },
    {
        "name": "DEFAULT_RUGCHECK_SCORE_THRESHOLD",
        "values": list(range(1, 1001, 100)),   # Range: 1, 101, 201, ..., 901
        "type": int
    },
    {
        "name": "DEFAULT_SOCIAL_SCORE_THRESHOLD",
        "values": list(range(0, 101, 10)),     # Range: 0, 10, 20, ..., 100
        "type": int
    },

    # --- PUMP.FUN Trend Reversal Parameters ---
    {
        "name": "USE_TREND_REVERSAL_CONFIRMATION",
        "values": [0, 1], # Options: 0 (False) or 1 (True)
        "type": int
    },
    {
        "name": "STOP_LOSS_COOLDOWN_MINUTES",
        "values": list(range(1, 21, 2)),      # Range: 5, 10, 15, ..., 30
        "type": int
    },
    {
        "name": "TREND_REVERSAL_RECENCY_HOURS",
        # [FIXED] Python's range() only accepts integers.
        # To create a range of floats, we use numpy.arange() and convert it to a list.
        "values": list(np.arange(0.1, 2.0, 0.2)), # Range: 0.1, 0.3, ..., 1.9
        "type": float
    },
    {
        "name": "TREND_REVERSAL_RSI_NEUTRAL_LEVEL",
        "values": list(range(5, 55, 5)),      # Range: 5, 10, 15, ..., 50
        "type": float
    },
    {
        "name": "INDICATOR_LOOKBACK_HOURS",
        # [FIXED] Using numpy.arange() for float steps.
        "values": list(np.arange(0.1, 2.0, 0.1)), # Range: 0.1, 0.2, ..., 1.9
        "type": float
    },
    {
        "name": "RSI_PERIOD",
        "values": list(range(4, 15, 1)),      # Range: 8, 9, ..., 14
        "type": int
    },
    {
        "name": "BBANDS_PERIOD",
        "values": list(range(15, 23, 1)),     # Range: 15, 16, ..., 22
        "type": int
    },
    {
        "name": "BBANDS_STD_DEV",
        "values": [round(x * 0.1 + 1.5, 1) for x in range(0, 8)], # Range: 1.8, 1.9, ..., 2.5
        "type": float
    },
    {
        "name": "FAST_EMA_PERIOD",
        "values": list(range(7, 14, 1)),      # Range: 7, 8, ..., 13
        "type": int
    },
    {
        "name": "SLOW_EMA_PERIOD",
        "values": list(range(18, 26, 1)),     # Range: 18, 19, ..., 25
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
        "values": list(range(4, 8, 1)), # 2 to 5 snapshots
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

# POPULATION_SIZE
# Explanation: The number of unique strategies (individuals) tested in each generation.
# A larger population explores more diverse solutions simultaneously.
# Analogy: The number of contestants in each round of a tournament.
# Example & Effect:
#   - 50 (Smaller): Faster, narrower search. Good for quick tests but might miss optimal strategies.
#   - 200 (Larger): Slower, more comprehensive search. Less likely to get stuck on a suboptimal solution.
POPULATION_SIZE: int = 150

# NUM_GENERATIONS
# Explanation: The number of evolutionary cycles the algorithm will run. More generations
# allow the best strategies more time to refine and improve.
# Analogy: The number of rounds in your tournament.
# Example & Effect:
#   - 50 (Fewer): Finishes quickly but solutions may not be fully optimized.
#   - 1000 (Larger): A very deep search, allowing for significant improvement over time. Expect long run times.
NUM_GENERATIONS: int = 500

# CROSSOVER_PROBABILITY
# Explanation: The probability that two successful "parent" strategies will combine
# their parameters to create new "child" strategies for the next generation.
# Analogy: The likelihood that two champion athletes will have a child who inherits a mix of their best skills.
# Example & Effect:
#   - 0.6 (Lower): Preserves more successful strategies as-is, leading to slower, more stable evolution.
#   - 0.9 (Higher): Creates more new combinations, which can speed up convergence but may reduce diversity.
CROSSOVER_PROBABILITY: float = 0.8

# MUTATION_PROBABILITY
# Explanation: The probability that a single parameter ("gene") will be randomly changed.
# Mutation introduces new ideas and prevents the GA from getting stuck.
# Analogy: A "wild card" or a sudden spark of genius that discovers a new path to success.
# Example & Effect:
#   - 0.1 (Lower): A more focused search that refines existing strategies. Risks getting stuck.
#   - 0.7 (Higher): A more chaotic and exploratory search. Good for finding unique solutions but can slow down refinement.
MUTATION_PROBABILITY: float = 0.6

# KEEP_ELITISM
# Explanation: The number of the absolute best strategies from a generation that are
# guaranteed to pass to the next generation unchanged. Ensures you never lose your best result.
# Analogy: The "reigning champions" rule; winners automatically qualify for the next round.
# Example & Effect:
#   - 1: Guarantees the single best solution is never lost.
#   - 5: Preserves the top 5. Can speed up convergence but might reduce diversity if they dominate the gene pool.
KEEP_ELITISM: int = 3

# The following parameters control the specific algorithms for selection, crossover, and mutation.
# The defaults ('sss', 'single_point', 'random') are robust and well-suited for this problem.
PARENT_SELECTION_TYPE: str = "sss"
CROSSOVER_TYPE: str = "single_point"
MUTATION_TYPE: str = "random"

# --- Fitness Function Settings ---

# FITNESS_METRIC
# Explanation: Defines the goal of the optimization. The GA will try to maximize or minimize this value.
# The string must exactly match a key in the results dictionary from the backtester.
# Analogy: The scoring system for your tournament. Are you judging on total points, goal difference, or win record?
# Example & Effect:
#   - "final_portfolio_value": Aims for the highest possible ending SOL balance. Good for maximizing raw profit.
#   - "profit_factor": Aims for the best risk-to-reward ratio. Often produces more stable, consistent strategies.
FITNESS_METRIC: str = "final_portfolio_value" # Focus on ending portfolio value

# FITNESS_GOAL
# Explanation: Tells the GA whether to maximize or minimize the FITNESS_METRIC.
# Should be "max" for goals like profit and "min" for goals like drawdown.
FITNESS_GOAL: str = "max" # Maximize the metric

# GA_FITNESS_SAMPLE_SIZE
# Explanation: Instead of backtesting every solution against all training tokens,
# we test against a random sample. This dramatically speeds up the process
# and reduces memory pressure, fixing potential crashes.
# Example & Effect:
#  - 0: Disables sampling, uses all available training tokens. Most accurate but slowest.
#  - 30: Evaluates each strategy against 30 random tokens from the training set. A good balance of speed and accuracy.
GA_FITNESS_SAMPLE_SIZE: Union[int, None] = 0

# --- Data Settings ---
DATA_SPLIT: Dict[str, float] = {
    "training": 0.6,
    "validation": 0.2,
    "test": 0.2
}
HISTORICAL_DATA_START_TS: datetime = datetime(2025, 9, 20, 0, 0, 0)
HISTORICAL_DATA_END_TS: datetime = datetime(2025, 10, 5, 0, 0, 0)

# --- Backtester Settings ---
BACKTEST_INITIAL_CAPITAL: float = 100.0 # In SOL

# --- Multiprocessing Settings ---
# Explanation: The number of CPU cores to use for parallel processing.
# 'auto' is a good default, but for stability on systems with many cores,
# specifying a fixed number like "8" or "12" can prevent resource exhaustion.
MULTIPROCESSING_CORES: str = "12"

# --- Results ---
RESULTS_DIR: str = "ga_optimization_results"
DETAILED_LOG_FILENAME: str = "ga_detailed_trade_log.jsonl"