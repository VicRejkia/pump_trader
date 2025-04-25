"""
Configuration for the Genetic Algorithm (GA) optimizer.

This file defines the parameters to be optimized by the GA,
their respective ranges (boundaries), and other GA settings.
"""
from datetime import datetime, timezone

# --- Parameters to Optimize ---
# Define the parameters from config.py that the GA will tune.
# Each parameter is a dictionary with 'name', 'low', 'high', and 'type' (int or float).
OPTIMIZABLE_PARAMETERS = [
    {
        "name": "SOL_TO_BUY",
        "values": [round(x * 0.2, 1) for x in range(1, 6)],  # 0.1 to 1.0 in steps of 0.1
        "type": float
    },
    {
        "name": "INITIAL_STOP_LOSS_PERCENT",
        "values": list(range(30, 71, 5)),  # 10% to 100%
        "type": float
    },
    {
        "name": "FIRST_SELL_PERCENT",
        "values": list(range(30, 101, 10)),  # 25% to 100%
        "type": float
    },
    {
        "name": "TRAILING_STOP_LOSS_PERCENT",
        "values": list(range(30, 101, 10)),  # 10% to 100%
        "type": float
    },
    {
        "name": "SECOND_TAKE_PROFIT_PERCENT",
        "values": list(range(100, 1001, 100)),  # 50% to 1000%
        "type": float
    },
    {
        "name": "FIRST_SELL_PROFIT_MARGIN",
        "values": list(range(10, 201, 20)),  # 10% to 200%
        "type": float
    },
    {
        "name": "DEFAULT_VOLUME_THRESHOLD",
        "values": list(range(5000, 50001, 5000)),  # 1k to 50k
        "type": int # Assuming volume is treated as integer USD
    },
    {
        "name": "DEFAULT_MARKETCAP_THRESHOLD", # For buying
        "values": list(range(5000, 50001, 2500)),  # 1k to 50k
        "type": int # Assuming market cap is treated as integer USD
    },
    {
        "name": "MIN_VOLATILITY",
        "values": [round(x * 0.1, 2) for x in range(1, 11, 2)],  # 0.05 to 0.5
        "type": float
    },
    {
        "name": "DEFAULT_RUGCHECK_SCORE_THRESHOLD",
        "values": list(range(1, 1001, 50)),  # Lower = safer
        "type": int
    },
    {
        "name": "DEFAULT_SOCIAL_SCORE_THRESHOLD",
        "values": list(range(0, 101, 10)),  # 0 to 100
        "type": int
    },
    {
        "name": "DEFAULT_TIME_INTERVALL", # In minutes
        "values": list(range(0, 61, 10)),  # 1 to 60 minutes
        "type": int
    },
    # Add more parameters here if needed
]

# --- GA Settings ---
POPULATION_SIZE = 50
NUM_GENERATIONS = 100
# Mating probability (crossover)
CROSSOVER_PROBABILITY = 0.8
# Mutation probability
MUTATION_PROBABILITY = 0.15

# --- Fitness Function Settings ---
# The primary metric from the backtest results to maximize/minimize
FITNESS_METRIC = "total_pnl" # e.g., 'total_pnl', 'sharpe_ratio'
# Set to 'max' if higher fitness is better, 'min' if lower is better
FITNESS_GOAL = "max"

# --- Data Settings ---
# Define the percentage split for training, validation, and test data
# Ensure these sum to 1.0
DATA_SPLIT = {
    "training": 0.6,
    "validation": 0.2,
    "test": 0.2
}

# Define the overall date range for historical data to be used
HISTORICAL_DATA_START_TS = datetime(2025, 4, 19, 15, 0, 0, tzinfo=timezone.utc)  # <-- adjust here
HISTORICAL_DATA_END_TS   = datetime(2025, 4, 19, 20, 59, 59, tzinfo=timezone.utc)

# --- Backtester Settings ---
# Initial capital for backtesting simulations (can be different from live)
BACKTEST_INITIAL_CAPITAL = 10.0 # In SOL