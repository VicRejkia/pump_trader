# config/rl_config.py
"""
Dedicated configuration constants and settings for the Reinforcement Learning Agent.
This file centralizes all parameters related to the environment, training, rewards,
and hardware setup for the RL module.
"""
import torch as th
from datetime import datetime

# --- General RL Agent Configuration ---
USE_RL_AGENT = False  # MASTER SWITCH: Set to True to enable the RL agent for live/paper trading.

# --- Hardware & Performance Configuration ---
# Set the computation device. Options: "cuda" for GPU, "cpu" for CPU.
# The script will automatically fall back to "cpu" if cuda is not available.
DEVICE = "cuda"

# Number of parallel environments (CPU cores) to use for training.
# Set to 1 to disable multiprocessing (easier for debugging).
# Using more cores (e.g., 4, 8) can significantly speed up training.
N_CPU = 4

# --- Model & Data Paths ---
RL_MODELS_DIR = "data/rl_models"  # Directory to save trained models and reports.
RL_LOGS_DIR = "data/rl_logs"      # Directory for TensorBoard log files.
BEST_MODEL_PATH = "data/rl_models/best_model.zip"  # Path to the model used for live inference.

# --- Environment Configuration ---
# Initial SOL balance for training/evaluation environments.
ENV_INITIAL_BALANCE = 100.0

# Max number of different tokens the agent can hold a position in simultaneously.
ENV_MAX_CONCURRENT_POSITIONS = 5

# Number of top tokens (by volume) the agent should observe at each step.
ENV_NUM_TOP_TOKENS_TO_OBSERVE = 5

# Action thresholds for buy/sell signals. Action values are in [-1, 1].
ENV_ACTION_BUY_THRESHOLD = 0.2
ENV_ACTION_SELL_THRESHOLD = -0.2

# Percentage of available balance to use for a new buy position. 0.95 means 95%.
ENV_CAPITAL_PER_BUY_PERCENT = 0.95

# Normalization constant for the `time_in_position` feature (in seconds).
# Default: 4 hours = 4 * 3600 = 14400 seconds.
ENV_TIME_IN_POSITION_NORM_SECONDS = 14400.0


# --- Training & Evaluation Configuration ---
# -- Date Ranges --
# IMPORTANT: Use non-overlapping periods for training and evaluation!
TRAINING_START_DATE = "2025-06-26T00:00:00Z"
TRAINING_END_DATE = "2025-06-27T00:00:00Z"
EVAL_START_DATE = "2025-06-28T00:00:00Z"
EVAL_END_DATE = "2025-06-29T00:00:00Z"

# Minimum number of trades a token must have in the date range to be included.
MIN_TRADE_COUNT_FOR_TRAINING = 100

# -- Optuna Hyperparameter Optimization --
OPTUNA_N_TRIALS = 100  # Number of hyperparameter combinations to test.
OPTUNA_TIMEOUT_SECONDS = 3600 * 4  # Max duration for the entire study (e.g., 4 hours).
OPTUNA_PRUNER_N_WARMUP_STEPS = 5 # Number of reports before pruning can happen.
OPTUNA_PRUNER_N_MIN_TRIALS = 5  # Minimum number of trials before pruning is activated.

# -- PPO Algorithm Timesteps --
# Training steps for each Optuna trial.
PPO_TIMESTEPS_PER_TRIAL = 100_000
# Training steps for retraining the final model with the best hyperparameters.
PPO_FINAL_MODEL_TIMESTEPS = 500_000

# Frequency for evaluating the model and checking for pruning.
# Should be a multiple of the PPO `n_steps` hyperparameter.
PPO_EVAL_FREQ = 2048


# --- Reward Function Configuration ---
# Primary weight for the dense reward signal (change in portfolio value).
REWARD_DENSE_WEIGHT = 1.0

# Primary weight for the sparse reward signal (rewards on completed trades).
REWARD_SPARSE_WEIGHT = 0.2

# Component weights for the sparse reward (should ideally sum to 1.0).
REWARD_PNL_WEIGHT = 0.5
REWARD_RISK_WEIGHT = 0.2
REWARD_POSITION_MANAGEMENT_WEIGHT = 0.2
REWARD_EXECUTION_WEIGHT = 0.1

# The expected max PnL for a single trade, used for scaling the reward.
MAX_EXPECTED_PNL_PER_TRADE_SOL = 1.0