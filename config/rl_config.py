# configuration/rl_config.py
"""
Centralized configuration for the Hierarchical Reinforcement Learning (HRL) module.
Contains settings for both the Scout Agent (trade entry) and the Manager Agent (trade management).
"""
from datetime import datetime, timezone
from typing import List

# ==============================================================================
# --- General & Data Configuration ---
# ==============================================================================
# Defines the time window from which to pull historical data for training/backtesting.
DATA_WINDOW_START_TS: datetime = datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
DATA_WINDOW_END_TS: datetime = datetime(2025, 7, 20, 23, 59, 0, tzinfo=timezone.utc)

# Minimum number of trades a token must have within the window to be included.
MIN_TRADES_FOR_TRAINING: int = 50

# Paths for storing processed data.
PROCESSED_DATA_DIR: str = "data/rl_processed_data"
SCOUT_PROCESSED_DATA_PATH: str = f"{PROCESSED_DATA_DIR}/scout_training_decisions.csv"
MANAGER_PROCESSED_DATA_PATH: str = f"{PROCESSED_DATA_DIR}/manager_trade_lifecycles.pkl"


# ==============================================================================
# --- Scout Agent (Decision Gate) Configuration ---
# ==============================================================================
class ScoutConfig:
    """Settings for the Scout Agent, responsible for making 'BUY' or 'IGNORE' decisions."""

    # --- Environment ---
    INITIAL_CAPITAL: float = 0.5  # Notional capital for reward calculation.
    MAX_STEPS_PER_EPISODE: int = 720  # Max simulation steps for a single trade lifecycle.
    DECISION_FREQUENCY: str = '5s'  # Frequency of data points in the OHLCV data.
    # Defines the moments (in minutes after creation) to generate a decision point for the agent.
    DECISION_POINTS_MINUTES: List[int] = [1, 2, 4, 8, 16, 32]

    # --- Observation Space ---
    OBSERVATION_FEATURES: list[str] = [
        'initial_market_cap_sol', 'volume_first_minute_sol', 'volatility_first_minute',
        'buy_sell_ratio_first_minute', 'time_since_creation_seconds', 'dex_liquidity_usd',
        'dex_volume_m5', 'dex_price_change_m5', 'dex_buys_m5', 'dex_sells_m5',
        'rugcheck_score', 'socials_score', 'creator_token_count', 'is_migrated',
        'rugcheck_score_is_real', 'socials_score_is_real'
    ]
    OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)

    # --- Action Space ---
    ACTION_SPACE_DIM: int = 2  # 0 = IGNORE, 1 = BUY

    # --- Reward Function ---
    TIME_PENALTY_PER_STEP: float = 0.0001

    # --- Simulation Logic (for reward calculation) ---
    SIM_INITIAL_STOP_LOSS_PERCENT: float = 40.0
    SIM_FIRST_SELL_PERCENT: float = 35.0
    SIM_FIRST_SELL_PROFIT_MARGIN: float = 70.0
    SIM_TRAILING_STOP_LOSS_PERCENT: float = 10.0
    SIM_SECOND_TAKE_PROFIT_PERCENT: float = 450.0

    # --- Training Hyperparameters ---
    TOTAL_TIMESTEPS: int = 500_000
    N_ENVS: int = 8
    EVAL_FREQ: int = 10000
    N_EVAL_EPISODES: int = 50
    RL_ALGORITHM: str = "PPO"
    POLICY_NAME: str = "MlpPolicy"
    PPO_HYPERPARAMS: dict[str, any] = {
        "n_steps": 2048, 
        "batch_size": 64, 
        "n_epochs": 10, 
        "gamma": 0.995,
        "gae_lambda": 0.95, 
        "clip_range": 0.2, 
        "ent_coef": 0.01, 
        "vf_coef": 0.5,
        "learning_rate": 3e-5, 
        "max_grad_norm": 0.5,
    }
    FINE_TUNE_LR: float = 1e-5 # Lower learning rate for fine-tuning.

    # --- I/O Paths ---
    TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/scout/"
    MODEL_SAVE_DIR: str = "./rl_models/scout/"


# ==============================================================================
# --- Manager Agent (Trade Management) Configuration ---
# ==============================================================================
class ManagerConfig:
    """Settings for the Manager Agent, responsible for deciding when to 'HOLD' or 'SELL' an open position."""

    # --- Environment ---
    MANAGER_DATA_EXTENSION_MINUTES: int = 120

    # --- Observation Space ---
    OBSERVATION_SPACE_DIM: int = 5

    # --- Action Space ---
    ACTION_SPACE_DIM: int = 2  # 0 = HOLD, 1 = SELL_NOW

    # --- Reward Function ---
    TIME_PENALTY_PER_STEP: float = -0.0001

    # --- Training Hyperparameters ---
    TOTAL_TIMESTEPS: int = 1_000_000
    N_ENVS: int = ScoutConfig.N_ENVS
    EVAL_FREQ: int = 8000
    N_EVAL_EPISODES: int = 100
    RL_ALGORITHM: str = "PPO"
    POLICY_NAME: str = "MlpPolicy"
    PPO_HYPERPARAMS: dict[str, any] = {
        "n_steps": 1024, 
        "batch_size": 64, 
        "n_epochs": 10, 
        "gamma": 0.99,
        "gae_lambda": 0.95, 
        "clip_range": 0.2, 
        "ent_coef": 0.005, 
        "vf_coef": 0.5,
        "learning_rate": 5e-4, 
        "max_grad_norm": 0.5,
    }
    FINE_TUNE_LR: float = 1e-5

    # --- I/O Paths ---
    TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/manager/"
    MODEL_SAVE_DIR: str = "./rl_models/manager/"
