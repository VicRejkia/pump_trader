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
RL_HISTORICAL_DATA_START_TS: datetime = datetime(2025, 4, 19, 15, 0, 0, tzinfo=timezone.utc)
RL_HISTORICAL_DATA_END_TS: datetime = datetime(2025, 4, 21, 20, 0, 0, tzinfo=timezone.utc)

# --- Environment Configuration ---
DATA_SET_KEY_TRAIN: str = 'train'       # Data used for agent training episodes.
DATA_SET_KEY_EVAL: str = 'validation'   # Data used for periodic evaluation during training.

RL_INITIAL_CAPITAL: float = 10.0 # In SOL

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
    'market_cap_sol_norm',  # Market cap in SOL (e.g., log-normalized)
    'volume_sol_norm',      # Trade volume in SOL (e.g., log-normalized)
    'rugcheck_score_norm',  # RugCheck score (normalized 0-1, where 1=low risk)
    'socials_score_norm',   # Socials score (normalized 0-1, where 1=low risk)
    'time_since_creation_norm', # Time since token creation (normalized 0-1)

    # Portfolio State Features (Normalized)
    'is_holding',           # Binary flag (0 or 1)
    'position_pnl_norm',    # Unrealized PnL of current position, normalized (-1 to N)
    'time_holding_norm',    # Time the current position has been held, normalized (0-1)
    'sol_balance_norm'      # Current SOL balance, normalized (0-1 relative to initial capital * factor)
]
OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)

# Expected bounds of the observation space *after* normalization. [-1, 1] is common.
OBSERVATION_LOW: float = -1.0
OBSERVATION_HIGH: float = 1.0

# --- Action Space Configuration (Continuous Parameter Tuning) ---
# Parameters controlled by the RL agent.
# Format: (parameter_name, low_bound, high_bound, type)
RL_TUNABLE_PARAMETERS: List[Tuple[str, float, float, type]] = [
    # Focus on sell-side parameters for initial RL experiments
    ('INITIAL_STOP_LOSS_PERCENT', 5.0, 70.0, float),    # 5% to 70% SL
    ('FIRST_SELL_PERCENT', 20.0, 100.0, float),         # 20% to 100% partial sell
    ('TRAILING_STOP_LOSS_PERCENT', 5.0, 50.0, float),   # 5% to 50% TSL
    ('FIRST_SELL_PROFIT_MARGIN', 10.0, 200.0, float),   # 10% to 200% margin for TP1
    # ('SOL_TO_BUY', 0.1, 1.0, float), # Add buy amount later if needed
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
REWARD_TP_HIT_BONUS: float = 0.2  # Bonus for hitting first or second take profit
REWARD_HOLDING_PENALTY: float = -0.001 # Small penalty per step while holding (discourages inaction)
# REWARD_UNREALIZED_PNL_CHANGE: float = 0.05 # Small bonus for increasing unrealized PnL (optional, can be noisy)

# --- Default Simulation Parameters (Fixed for RL Env) ---
# Non-optimized parameters used during simulation. Match main config where applicable.
DEFAULT_BUY_FEE: float = 0.001
DEFAULT_BUY_TIP: float = 0.001
DEFAULT_SELL_FEE: float = 0.001
DEFAULT_SELL_TIP: float = 0.001
DEFAULT_BUY_SOL_AMOUNT: float = 0.5 # Fixed buy amount for RL env simulation
SECOND_TAKE_PROFIT_PERCENT: float = 550.0 # Fixed second TP target

# Fixed thresholds for the *simulated* buy decision (agent learns parameters, not timing)
DEFAULT_VOLUME_THRESHOLD: int = 19000
DEFAULT_MARKETCAP_THRESHOLD: int = 10000
DEFAULT_RUGCHECK_SCORE_THRESHOLD: int = 801
DEFAULT_SOCIAL_SCORE_THRESHOLD: int = 50
MIN_VOLATILITY: float = 0.1
MIN_MARKET_CAP: int = 3600 # Emergency sell market cap threshold (USD)

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
N_EVAL_EPISODES: int = 10 # More episodes for better evaluation stability

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