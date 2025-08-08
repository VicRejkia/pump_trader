# configuration/rl_config.py
"""
Centralized configuration for the Hierarchical Reinforcement Learning (HRL) module.
Contains settings for both the Scout Agent (trade entry) and the Manager Agent (trade management).
"""
from datetime import datetime, timezone
from typing import List, Dict, Any

# ==============================================================================
# --- General & Data Configuration ---
# ==============================================================================
# Defines the available time windows for pulling historical data. 
# The `train_agents.py` script can be run with `--data-window test` or `--data-window full`.
DATA_WINDOWS: Dict[str, Dict[str, datetime]] = {
    "test": {
        "start": datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc),
        "end": datetime(2025, 6, 27, 23, 59, 0, tzinfo=timezone.utc),
    },
    "full": {
        "start": datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc),
        "end": datetime(2025, 7, 19, 23, 59, 0, tzinfo=timezone.utc),
    }
}
DEFAULT_DATA_WINDOW: str = "full" # The window to use if none is specified.

# Minimum number of trades a token must have within the window to be included.
MIN_TRADES_FOR_TRAINING: int = 25

# Paths for storing processed data.
PROCESSED_DATA_DIR: str = "data/rl_processed_data"
# The specific cache paths are now managed by the CacheManager based on the data window.

# ==============================================================================
# --- Backtest Portfolio Configuration ---
# ==============================================================================
# These settings exclusively control the backtester's portfolio simulation.
PORTFOLIO_STARTING_CAPITAL: float = 1000.0 # The total starting bankroll for a backtest.
PORTFOLIO_CAPITAL_PER_TRADE: float = 50.0  # The fixed dollar amount allocated to each trade.


# ==============================================================================
# --- Scout Agent (Decision Gate) Configuration ---
# ==============================================================================
class ScoutConfig:
    """Settings for the Scout Agent, responsible for making 'BUY' or 'IGNORE' decisions."""

    # --- Environment ---
    SIMULATION_FAILURE_PENALTY: float = 1.0
    MAX_STEPS_PER_EPISODE: int = 720
    DECISION_FREQUENCY: str = '5s'
    DECISION_POINTS_MINUTES: List[int] = [1, 2, 4, 8, 16, 32]

    # --- Observation Space ---
    OBSERVATION_FEATURES: list[str] = [
        'initial_market_cap_sol', 
        'volume_first_minute_sol', 
        'volatility_first_minute',
        'time_since_creation_seconds',
        'rugcheck_score', 
        'socials_score',
        'creator_token_count'
    ]
    OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)

    # --- Action Space ---
    ACTION_SPACE_DIM: int = 2  # 0 = IGNORE, 1 = BUY

    # --- Reward Function ---
    TIME_PENALTY_PER_STEP: float = 0.0001

    # --- Simulation Logic (for reward calculation) ---
    SIM_INITIAL_STOP_LOSS_PERCENT: float = 50.0
    SIM_FIRST_SELL_PERCENT: float = 25.0
    SIM_FIRST_SELL_PROFIT_MARGIN: float = 100.0
    SIM_TRAILING_STOP_LOSS_PERCENT: float = 50.0
    SIM_SECOND_TAKE_PROFIT_PERCENT: float = 500.0

    # --- Training Hyperparameters ---
    RL_ALGORITHM: str = "PPO"
    POLICY_NAME: str = "MlpPolicy"
    N_ENVS: int = 24
    N_EVAL_EPISODES: int = 50

    # --- MODIFIED: Restructured Hyperparameters ---
    # Hyperparameters for initial training
    PPO_HYPERPARAMS: Dict[str, Any] = {
        "learn_params": {
            "total_timesteps": 7_000,
            "eval_freq": 10000,
        },
        "model_params": {
            "n_steps": 4096, 
            "batch_size": 128, 
            "n_epochs": 20, 
            "gamma": 0.99,
            "gae_lambda": 0.95, 
            "clip_range": 0.2, 
            "ent_coef": 0.01, 
            "vf_coef": 0.5,
            "learning_rate": 3e-4, 
            "max_grad_norm": 0.5,
        }
    }

    # Hyperparameters for fine-tuning an existing model
    PPO_FINETUNE_HYPERPARAMS: Dict[str, Any] = {
        "learn_params": {
            "total_timesteps": 2_000, # Shorter run for fine-tuning
            "eval_freq": 5000,
        },
        "model_params": {
            "n_steps": 4096, 
            "batch_size": 128, 
            "n_epochs": 10, # Fewer epochs
            "gamma": 0.995,
            "gae_lambda": 0.95, 
            "clip_range": 0.2, 
            "ent_coef": 0.01, 
            "vf_coef": 0.5,
            "learning_rate": 1e-5, # Lower learning rate
            "max_grad_norm": 0.5,
        }
    }
    # --- END MODIFICATION ---

    # --- I/O Paths ---
    TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/scout/"
    MODEL_SAVE_DIR: str = "./rl_models/scout/"


# ==============================================================================
# --- Manager Agent (Trade Management) Configuration ---
# ==============================================================================
class ManagerConfig:
    """Settings for the Manager Agent, responsible for deciding when to 'HOLD' or 'SELL' an open position."""

    # --- Environment ---
    MANAGER_DATA_EXTENSION_MINUTES: int = 180

    # --- Observation Space ---
    OBSERVATION_SPACE_DIM: int = 5

    # --- Action Space ---
    ACTION_SPACE_DIM: int = 2  # 0 = HOLD, 1 = SELL_NOW

    # --- Reward Function ---
    TIME_PENALTY_PER_STEP: float = -0.0001

    # --- Training Hyperparameters ---
    RL_ALGORITHM: str = "PPO"
    POLICY_NAME: str = "MlpPolicy"
    N_ENVS: int = ScoutConfig.N_ENVS
    N_EVAL_EPISODES: int = 100

    # --- MODIFIED: Restructured Hyperparameters ---
    # Hyperparameters for initial training
    PPO_HYPERPARAMS: Dict[str, Any] = {
        "learn_params": {
            "total_timesteps": 7_000,
            "eval_freq": 8000,
        },
        "model_params": {
            "n_steps": 1024, 
            "batch_size": 64, 
            "n_epochs": 10, 
            "gamma": 0.99,
            "gae_lambda": 0.95, 
            "clip_range": 0.2, 
            "ent_coef": 0.005, 
            "vf_coef": 0.5,
            "learning_rate": 3e-4, 
            "max_grad_norm": 0.5,
        }
    }

    # Hyperparameters for fine-tuning an existing model
    PPO_FINETUNE_HYPERPARAMS: Dict[str, Any] = {
        "learn_params": {
            "total_timesteps": 2_000, # Shorter run for fine-tuning
            "eval_freq": 4000,
        },
        "model_params": {
            "n_steps": 1024, 
            "batch_size": 64, 
            "n_epochs": 5, # Fewer epochs
            "gamma": 0.995,
            "gae_lambda": 0.95, 
            "clip_range": 0.2, 
            "ent_coef": 0.005, 
            "vf_coef": 0.5,
            "learning_rate": 1e-5, # Lower learning rate
            "max_grad_norm": 0.5,
        }
    }
    # --- END MODIFICATION ---

    # --- I/O Paths ---
    TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/manager/"
    MODEL_SAVE_DIR: str = "./rl_models/manager/"