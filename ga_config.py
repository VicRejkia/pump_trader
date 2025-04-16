"""
Configuration for the Genetic Algorithm (GA) optimizer.

This file defines the parameters to be optimized by the GA,
their respective ranges (boundaries), and other GA settings.
"""

# --- Parameters to Optimize ---
# Define the parameters from config.py that the GA will tune.
# Each parameter is a dictionary with 'name', 'low', 'high', and 'type' (int or float).
OPTIMIZABLE_PARAMETERS = [
    {
        "name": "SOL_TO_BUY",
        "low": 0.1,
        "high": 1.0,
        "type": float
    },
    {
        "name": "INITIAL_STOP_LOSS_PERCENT",
        "low": 20.0,
        "high": 95.0,
        "type": float
    },
    {
        "name": "FIRST_SELL_PERCENT",
        "low": 25.0,
        "high": 100.0,
        "type": float
    },
    {
        "name": "TRAILING_STOP_LOSS_PERCENT",
        "low": 5.0,
        "high": 100.0,
        "type": float
    },
    {
        "name": "SECOND_TAKE_PROFIT_PERCENT",
        "low": 100.0,
        "high": 1000.0,
        "type": float
    },
    {
        "name": "FIRST_SELL_PROFIT_MARGIN",
        "low": 5.0,
        "high": 100.0,
        "type": float
    },
    {
        "name": "DEFAULT_VOLUME_THRESHOLD",
        "low": 4000,
        "high": 50000,
        "type": int # Assuming volume is treated as integer USD
    },
    {
        "name": "DEFAULT_MARKETCAP_THRESHOLD", # For buying
        "low": 1000,
        "high": 50000,
        "type": int # Assuming market cap is treated as integer USD
    },
    {
        "name": "MIN_VOLATILITY",
        "low": 0.1,
        "high": 5.0,
        "type": float
    },
    {
        "name": "DEFAULT_RUGCHECK_SCORE_THRESHOLD",
        "low": 1,
        "high": 1000,
        "type": int
    },
    {
        "name": "DEFAULT_SOCIAL_SCORE_THRESHOLD",
        "low": 30,
        "high": 90,
        "type": int
    },
    {
        "name": "DEFAULT_TIME_INTERVALL", # In minutes
        "low": 1,
        "high": 60,
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
# Example: "YYYY-MM-DD" (These should be set based on available data)
HISTORICAL_DATA_START_DATE = "2025-04-09"
HISTORICAL_DATA_END_DATE = "2025-04-15"

# --- Backtester Settings ---
# Initial capital for backtesting simulations (can be different from live)
BACKTEST_INITIAL_CAPITAL = 10.0 # In SOL