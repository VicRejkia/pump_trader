# FILE: rl_config.py (Added Death Penalty)

"""
Configuration for the Reinforcement Learning (RL) agent and environment.

Defines the structure of the observation and action spaces, reward function
components, hyperparameters for the RL algorithm, training settings,
and data configurations.
"""

from datetime import datetime, timezone
import numpy as np
from typing import List, Dict, Any, Tuple, Union

# --- General Configuration ---
# NOTE: THESE DATES ARE EXAMPLES - ADJUST TO YOUR ACTUAL DATA RANGE
# Use the same extended range as GA for consistency?
RL_HISTORICAL_DATA_START_TS: datetime = datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
RL_HISTORICAL_DATA_END_TS: datetime = datetime(2025, 7, 4, 23, 59, 0, tzinfo=timezone.utc)

# --- Environment Configuration ---
DATA_SET_KEY_TRAIN: str = 'train'       # Data used for agent training episodes.
DATA_SET_KEY_EVAL: str = 'validation'   # Data used for periodic evaluation during training.

RL_INITIAL_CAPITAL: float = 100.0 # In SOL

# Max steps based on typical token lifespan (e.g., 4 hours * 12 steps/min * 60 min/hr = 2880 steps if 5s candles)
# Let's set a reasonable upper bound, actual episodes will be truncated by data end.
MAX_STEPS_PER_EPISODE: int = 2880 # Max simulation steps if token lives unusually long

# --- Observation Space Configuration ---
# Features observed at each step. Normalization is crucial.
OBSERVATION_PRICE_HISTORY_LENGTH: int = 15 # Steps of price history for features like log returns

OBSERVATION_FEATURES: List[str] = [
    # Price Change Features (Normalized Log Returns)
    'price_change_1',  # Log return over 1 step (~5s)
    'price_change_5',  # Log return over 5 steps (~25s)
    'price_change_10', # Log return over 10 steps (~50s)

    # Market Indicators (Normalized)
    'volatility',           # Rolling volatility (e.g., normalized 0-1)
    'live_market_cap_sol_norm',  # Normalized LIVE SOL market cap
    'live_market_cap_usd_norm',  # Normalized LIVE USD market cap
    'volume_sol_norm',      # Trade volume in SOL (e.g., log-normalized)
    'rugcheck_score_norm',  # RugCheck score (normalized 0-1, where 1=low risk)
    'socials_score_norm',   # Socials score (normalized 0-1, where 1=low risk)
    'time_since_creation_norm', # Time since token creation (normalized 0-1)

    # Portfolio State Features (Normalized)
    'is_holding',           # Binary flag (0 or 1)
    'position_pnl_norm',    # Unrealized PnL of current position, normalized (-1 to N)
    'time_holding_norm',    # Time the current position has been held, normalized (0-1)
    'sol_balance_norm',     # Current SOL balance, normalized (0-1 relative to initial capital * factor)

    # Time Features (Normalized)
    'weekday',              # Day of the week (e.g., normalized 0-1 or one-hot)
    'daytime'               # Time of day (e.g., normalized 0-1 or cyclical)
]
OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)

# Note: Observation normalization is handled by Stable Baselines3's VecNormalize.
# The bounds defined here are the *expected* range after normalization,
# but the Box space itself is defined by the shape only.
OBSERVATION_LOW: float = -np.inf 
OBSERVATION_HIGH: float = np.inf 

# --- Action Space Configuration (Continuous Parameter Tuning) ---
# Parameters controlled by the RL agent.
# Format: (parameter_name, low_bound, high_bound, type)
RL_TUNABLE_PARAMETERS: List[Tuple[str, float, float, type]] = [
    # Sell-side parameters
    ('INITIAL_STOP_LOSS_PERCENT', 5.0, 70.0, float),
    ('FIRST_SELL_PERCENT', 20.0, 100.0, float),
    ('TRAILING_STOP_LOSS_PERCENT', 5.0, 50.0, float),
    ('FIRST_SELL_PROFIT_MARGIN', 10.0, 200.0, float),
    ('SECOND_TAKE_PROFIT_PERCENT', 100.0, 1000.0, float),
    
    # Buy condition thresholds
    ('DEFAULT_VOLUME_THRESHOLD', 5000, 50000, int),
    ('DEFAULT_MARKETCAP_THRESHOLD', 10000, 100000, int),
    ('MIN_VOLATILITY', 0.01, 1.0, float),
    ('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 1, 1002, int),
    ('DEFAULT_SOCIAL_SCORE_THRESHOLD', 1, 100, int),
    ('SOL_TO_BUY', 0.1, 0.5, float),
    
    # Emergency & Re-buy parameters
    ('MC_DROP_THRESHOLD_RL', 5.0, 95.0, float),
    ('USE_TREND_REVERSAL_CONFIRMATION', 0.0, 1.0, float),
    ('STOP_LOSS_COOLDOWN_MINUTES', 0.0, 60.0, int),
    
    # PUMP.FUN Trend Reversal Parameters
    ('TREND_REVERSAL_RECENCY_HOURS', 0.25, 12.0, int),
    ('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 30.0, 60.0, float),
    ('INDICATOR_LOOKBACK_HOURS', 0.25, 6.0, int),
    ('RSI_PERIOD', 7.0, 28.0, int),
    ('BBANDS_PERIOD', 10.0, 30.0, int),
    ('BBANDS_STD_DEV', 1.5, 2.5, float),
    ('FAST_EMA_PERIOD', 5.0, 15.0, int),
    ('SLOW_EMA_PERIOD', 15.0, 30.0, int),

    # [NEW] DEXSCREENER Trend Reversal Parameters
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
# Weights for different reward components. Tuning is critical.

# Primary Reward: Based on realized profit/loss from completed trades (sells).
REWARD_PNL_MULTIPLIER: float = 1.0 # Scale realized PnL

# Penalty for holding a position when the token dies (end of data).
# Make this substantial, e.g., equivalent to losing the initial investment.
REWARD_DEATH_PENALTY: float = -RL_INITIAL_CAPITAL * 0.5 # Example: Penalize half the initial capital

# Reward Shaping (Optional): Intermediate rewards/penalties.
REWARD_SL_HIT_PENALTY: float = -0.5 # Penalty for hitting initial or trailing stop loss
REWARD_TP_HIT_BONUS: float = 0.5  # Bonus for hitting first or second take profit (0.2)
REWARD_HOLDING_PENALTY: float = -0.001 # Small penalty per step while holding (discourages inaction)
# REWARD_UNREALIZED_PNL_CHANGE: float = 0.05 # Small bonus for increasing unrealized PnL (optional, can be noisy)

# --- Default Simulation Parameters (Fixed for RL Env) ---
# Non-optimized parameters used during simulation. Match main config where applicable.
DEFAULT_BUY_FEE: float = 0.001
DEFAULT_BUY_TIP: float = 0.001
DEFAULT_SELL_FEE: float = 0.001
DEFAULT_SELL_TIP: float = 0.001
# DEFAULT_BUY_SOL_AMOUNT: float = 0.5 # Fixed buy amount for RL env simulation
# SECOND_TAKE_PROFIT_PERCENT: float = 550.0 # Fixed second TP target

# Fixed thresholds for the *simulated* buy decision (agent learns parameters, not timing)
# MIN_MARKET_CAP is an absolute USD threshold, used as a fallback if MC_DROP_THRESHOLD logic doesn't trigger
MIN_MARKET_CAP_USD_FALLBACK: int = 3500 # Renamed for clarity

MIN_CANDLE_DATA_FOR_INDICATORS: int = 30

VOLATILITY_WINDOW: int = 120 # Window size (steps) for volatility calculation in env

# --- RL Agent & Training Configuration (Stable Baselines3) ---
RL_ALGORITHM: str = "PPO" # PPO is robust; SAC/TD3 are alternatives

# Policy network architecture. Adjust hidden layer sizes as needed.
POLICY_KWARGS: Dict[str, Any] = dict(net_arch=dict(pi=[128, 128], vf=[128, 128]))
# For SAC/TD3: dict(net_arch=[256, 256]) might be suitable

# Total training timesteps. Needs significant increase for real training.
TOTAL_TIMESTEPS: int = 1_000_000 # Increase for more thorough training (e.g., 1M+)

# Number of parallel environments. Adjust based on CPU cores.
N_ENVS: int = 8 # Example: Use 8 parallel environments if CPU allows

TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/"
MODEL_SAVE_DIR: str = "./rl_trained_models/"

# Evaluation frequency (in total agent steps across all envs).
EVAL_FREQ: int = 50000 # Evaluate every 50k total steps

# Number of episodes for each evaluation run.
N_EVAL_EPISODES: int = 40 # More episodes for better evaluation stability

# Checkpoint saving frequency (in total agent steps).
CHECKPOINT_FREQ: int = 100000 # Save every 100k total steps

# --- Data Settings ---
# Same split as GA for consistency when reusing load_and_split_data
DATA_SPLIT_RL: Dict[str, float] = {
    "training": 0.6,
    "validation": 0.2,
    "test": 0.2
}

# --- Live Agent Configuration (for deployment) ---
# How often the live bot queries the trained agent for new parameters (seconds).
AGENT_ACTION_INTERVAL_SECONDS: int = 60 # Update parameters every minute