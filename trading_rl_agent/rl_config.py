# FILE: trading_rl_agent/rl_config.py

"""
Configuration for the Hierarchical Reinforcement Learning (HRL) agent and 
the portfolio management environment.

This configuration defines the structure of the observation and action spaces
for the high-level Meta-Controller, reward function components, hyperparameters
for the PPO algorithm, and training settings. The design supports a dynamic
universe of multiple tokens.
"""

from datetime import datetime, timezone
import numpy as np
from typing import List, Dict, Any, Tuple

# --- General & Data Configuration ---
# This time range is used by the data loading script to identify tokens that were active.
# The training process will then use the *full* history of those identified tokens.
DATA_WINDOW_START_TS: datetime = datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
DATA_WINDOW_END_TS: datetime = datetime(2025, 7, 19, 23, 59, 0, tzinfo=timezone.utc)
PROCESSED_DATA_DIR: str = "data/rl_processed_data" # Directory to save/load preprocessed dataframes

# --- Environment Configuration ---
DATA_SET_KEY_TRAIN: str = 'train'
DATA_SET_KEY_EVAL: str = 'validation'

# Initial capital for each training/evaluation episode in SOL.
INITIAL_CAPITAL: float = 100.0
# Max number of decision steps per episode (e.g., 288 steps of 5 mins = 1 day).
MAX_STEPS_PER_EPISODE: int = 1000 # 288 
# The frequency of the Meta-Controller's decisions.
DECISION_FREQUENCY: str = '2min'

# --- Observation Space (Meta-Controller) ---
# Defines what the high-level agent sees at each step.

# Part 1: Per-Token Features (a time-series for each token)
# These features are extracted from the historical data (e.g., resampled to 5-min intervals).
# The shape will be (MAX_TOKENS_IN_UNIVERSE, HISTORY_LENGTH, NUM_TOKEN_FEATURES).
TOKEN_HISTORY_LENGTH: int = 60 # e.g., 60 steps of 5-min data = 5 hours of context
TOKEN_FEATURES: List[str] = [
    'Close', 'Volume', 'marketCapSol', 'volatility', 
    'rugcheck_score', 'socials_score'
]
NUM_TOKEN_FEATURES: int = len(TOKEN_FEATURES)

# Part 2: Global Portfolio & Market Features (a single vector)
GLOBAL_FEATURES: List[str] = [
    'sol_balance_norm',             # Current SOL balance, normalized (e.g., 0-1)
    'portfolio_value_norm',         # Total portfolio value (SOL + holdings), normalized
    'unrealized_pnl',               # Total unrealized profit/loss across all positions
    'num_active_positions',         # Raw count of tokens currently held
    'avg_holding_period',           # Average time (in steps) positions have been held
    'market_trend',                 # A simple metric for recent market trend (e.g., avg % change)
    'market_volatility_avg'         # Average volatility across all active tokens
]
NUM_GLOBAL_FEATURES: int = len(GLOBAL_FEATURES)

# Maximum number of tokens the agent can manage at once. This defines the static
# size of the observation and action spaces.
MAX_TOKENS_IN_UNIVERSE: int = 20

# --- Action Space (Meta-Controller) ---
# The action is a vector of target portfolio weights.
# The size is MAX_TOKENS_IN_UNIVERSE + 1 (for the SOL/cash position).
ACTION_SPACE_DIM: int = MAX_TOKENS_IN_UNIVERSE + 1

# --- Reward Function Configuration ---
# Weights for the composite reward function.
REWARD_PNL_WEIGHT: float = 1.0          # For realized profit/loss from sells
REWARD_SHARPE_WEIGHT: float = 0.20      # For risk-adjusted returns (encourages smooth equity curve)
REWARD_DRAWDOWN_PENALTY: float = 0.3    # Penalty for peak-to-trough losses
REWARD_TURNOVER_PENALTY: float = 0.01   # Penalty for excessive trading (to control transaction costs)
REWARD_HOLDING_PENALTY: float = 0.001   # Small penalty for holding positions to encourage closing them eventually

# --- Training Configuration ---
TOTAL_TIMESTEPS: int = 1_000_000
N_ENVS: int = 6 # Number of parallel environments for training
TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/"
MODEL_SAVE_DIR: str = "./rl_models/"
EVAL_FREQ: int = 20000
N_EVAL_EPISODES: int = 10

# --- PPO Hyperparameters ---
# Tuned for financial applications and complex observation spaces.
RL_ALGORITHM: str = "PPO"
POLICY_NAME: str = "MultiInputPolicy" # Required for Dict observation spaces in SB3
POLICY_KWARGS: Dict[str, Any] = dict(
    net_arch=dict(pi=[256, 128], vf=[256, 128]),
    # Configuration for the custom feature extractor
    features_extractor_kwargs=dict(
        token_features_dim=NUM_TOKEN_FEATURES,
        global_features_dim=NUM_GLOBAL_FEATURES,
        lstm_hidden_size=128, # Hidden size of the LSTM for processing token histories
        combined_features_dim=256 # Size of the final combined feature vector
    )
)
PPO_HYPERPARAMS: Dict[str, Any] = {
    "n_steps": 1024,
    "batch_size": 128,
    "n_epochs": 10,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.3,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "learning_rate": 1e-4, # Lower learning rate for more stable learning
    "max_grad_norm": 0.5,
    "use_sde": True # State-Dependent Exploration, can be useful but start with False
}

# --- Live Agent Configuration ---
# How often the live bot queries the RL agent for new target portfolio allocations.
AGENT_ACTION_INTERVAL_SECONDS: int = 300 # 5 minutes, matching the decision frequency