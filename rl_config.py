# FILE: rl_config.py (Refactored for Aggregate State)

"""
Configuration for the Reinforcement Learning (RL) agent and environment.

Defines the structure of the observation and action spaces, reward function
components, hyperparameters for the RL algorithm, training settings,
and data configurations. This version is refactored to use an aggregate
observation space, allowing the agent to manage a portfolio of multiple,
dynamic tokens.
"""

from datetime import datetime, timezone
import numpy as np
from typing import List, Dict, Any, Tuple, Union

# --- General Configuration ---
RL_HISTORICAL_DATA_START_TS: datetime = datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
RL_HISTORICAL_DATA_END_TS: datetime = datetime(2025, 6, 26, 23, 59, 0, tzinfo=timezone.utc)

# --- Environment Configuration ---
DATA_SET_KEY_TRAIN: str = 'train'       # Data used for agent training episodes.
DATA_SET_KEY_EVAL: str = 'validation'   # Data used for periodic evaluation during training.

RL_INITIAL_CAPITAL: float = 100.0 # In SOL
MAX_STEPS_PER_EPISODE: int = 720 # e.g., 720 steps of 1 minute = 12 hours of trading simulation

# --- Observation Space Configuration (Global Aggregate State) ---
# Features observed at each step, representing the entire portfolio and market.
OBSERVATION_FEATURES: List[str] = [
    # Portfolio State Features
    'sol_balance_norm',             # Current SOL balance, normalized (0-1 relative to initial capital * factor)
    'portfolio_pnl_unrealized_total', # Sum of unrealized PnL for all open positions, normalized
    'num_active_positions',         # Raw count of open trades
    'avg_time_holding_norm',        # Average holding duration for open positions, normalized
    'portfolio_value_norm',         # Total portfolio value (SOL balance + value of holdings), normalized

    # Aggregate Market Features (Normalized)
    'market_volatility_avg',        # Average volatility of actively traded tokens
    'market_volume_sol_avg',        # Average volume in SOL of actively traded tokens
    'new_tokens_last_hour',         # Count of new tokens created in the last simulated hour
    'active_tokens_rug_score_avg',  # Average rugcheck score of tokens with recent activity
    'active_tokens_social_score_avg',# Average socials score of tokens with recent activity

    # Time Features (Normalized)
    'weekday',                      # Day of the week (e.g., normalized 0-1 or one-hot)
    'daytime'                       # Time of day (e.g., normalized 0-1 or cyclical)
]
OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)
OBSERVATION_LOW: float = -np.inf
OBSERVATION_HIGH: float = np.inf

# --- Action Space Configuration (Parameter Tuning) ---
# These are the parameters the RL agent will dynamically tune for the bot's trading logic.
RL_TUNABLE_PARAMETERS: List[Tuple[str, float, float, type]] = [
    # Sell-side parameters
    ('INITIAL_STOP_LOSS_PERCENT', 5.0, 70.0, float),
    ('FIRST_SELL_PERCENT', 20.0, 100.0, float),
    ('TRAILING_STOP_LOSS_PERCENT', 5.0, 50.0, float),
    ('FIRST_SELL_PROFIT_MARGIN', 10.0, 200.0, float),
    ('SECOND_TAKE_PROFIT_PERCENT', 100.0, 1000.0, float),

    # Buy condition thresholds
    ('DEFAULT_VOLUME_THRESHOLD', 1000, 50000, int),
    ('DEFAULT_MARKETCAP_THRESHOLD', 10000, 100000, int),
    ('MIN_VOLATILITY', 0.01, 3.0, float),
    ('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 1, 1002, int),
    ('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100, 100, int), # Note: max is 100, so this is fixed
    ('SOL_TO_BUY', 0.1, 0.5, float),

    # Emergency & Re-buy parameters
    ('MC_DROP_THRESHOLD', 1.0, 20.0, float), # Note: Renamed from MC_DROP_THRESHOLD_RL for consistency
    ('USE_TREND_REVERSAL_CONFIRMATION', 0.0, 1.0, float), # Interpreted as bool ( > 0.5)
    ('STOP_LOSS_COOLDOWN_MINUTES', 0.0, 60.0, float), # Use float for continuous action space

    # PUMP.FUN Trend Reversal Parameters
    ('TREND_REVERSAL_RECENCY_HOURS', 0.25, 12.0, float),
    ('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 30.0, 60.0, float),
    ('INDICATOR_LOOKBACK_HOURS', 0.25, 6.0, float),
    ('RSI_PERIOD', 4.0, 50.0, int),
    ('BBANDS_PERIOD', 10.0, 30.0, int),
    ('BBANDS_STD_DEV', 1.0, 2.5, float),
    ('FAST_EMA_PERIOD', 5.0, 20.0, int),
    ('SLOW_EMA_PERIOD', 15.0, 80.0, int),

    # DEXSCREENER Trend Reversal Parameters
    ('DEX_REVERSAL_LOOKBACK_MINUTES', 15.0, 60.0, int),
    ('DEX_REVERSAL_MIN_SNAPSHOTS', 3.0, 10.0, int),
    ('DEX_REVERSAL_MIN_LIQUIDITY_USD', 1000.0, 10000.0, int),
    ('DEX_REVERSAL_MIN_BUY_SELL_RATIO', 1.1, 3.0, float),
    ('DEX_REVERSAL_MIN_CONFIRMATIONS', 1.0, 5.0, int),
]
ACTION_SPACE_DIM: int = len(RL_TUNABLE_PARAMETERS)
ACTION_LOW: np.ndarray = np.array([p[1] for p in RL_TUNABLE_PARAMETERS], dtype=np.float32)
ACTION_HIGH: np.ndarray = np.array([p[2] for p in RL_TUNABLE_PARAMETERS], dtype=np.float32)

# --- Reward Function Configuration ---
REWARD_PNL_MULTIPLIER: float = 1.0  # Scale realized PnL from completed trades
REWARD_DEATH_PENALTY: float = -RL_INITIAL_CAPITAL * 0.1 # Penalty for holding a token when its data ends
REWARD_HOLDING_PENALTY: float = -0.0001 # Small penalty per step per open position to discourage inaction

# --- Training Configuration ---
TOTAL_TIMESTEPS: int = 1_000_000
N_ENVS: int = 8
TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/"
MODEL_SAVE_DIR: str = "./rl_trained_models/"
EVAL_FREQ: int = 50000
N_EVAL_EPISODES: int = 20
CHECKPOINT_FREQ: int = 100000

# --- Data Settings ---
DATA_SPLIT_RL: Dict[str, float] = {"training": 0.7, "validation": 0.3, "test": 0.0}

# --- PPO Hyperparameters ---
RL_ALGORITHM: str = "PPO"
POLICY_KWARGS: Dict[str, Any] = dict(net_arch=dict(pi=[128, 128], vf=[128, 128]))
PPO_HYPERPARAMS: Dict[str, Any] = {
    "n_steps": 2048,
    "n_epochs": 10,
    "batch_size": 64,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "learning_rate": 3e-4,
    "max_grad_norm": 0.5,
    "use_sde": False
}

# --- Live Agent Configuration ---
AGENT_ACTION_INTERVAL_SECONDS: int = 60 # How often the live bot queries the agent for new parameters