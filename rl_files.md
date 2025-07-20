# `PUMP_T~1` Project Files

📅 Generated on: 2025-07-20 20:52

📂 Project root: `C:\USERS\SASCHA\DOCUME~1\PROJECTS\PYTHON\CRYPTO\PUMP_T~1`

---

### 📄 rl_config.py

```python
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
RL_HISTORICAL_DATA_END_TS: datetime = datetime(2025, 6, 26, 23, 59, 0, tzinfo=timezone.utc)

# --- Environment Configuration ---
DATA_SET_KEY_TRAIN: str = 'train'       # Data used for agent training episodes.
DATA_SET_KEY_EVAL: str = 'validation'   # Data used for periodic evaluation during training.

RL_INITIAL_CAPITAL: float = 100.0 # In SOL

# --- START: Modified MAX_STEPS_PER_EPISODE ---
# This value is now calculated dynamically in rl_trainer.py based on the
# percentile of token lifespans in the training dataset.
# A fallback value can be set here if the calculation fails.
MAX_STEPS_PER_EPISODE: Union[int, None] = None # Set to None to indicate dynamic calculation
MAX_STEPS_PERCENTILE: float = 95.0 # The percentile of token lifespans to use as the max step limit.
MAX_STEPS_PER_EPISODE_FALLBACK: int = 2880 # Fallback if dynamic calculation fails or None is passed
# --- END: Modified MAX_STEPS_PER_EPISODE ---

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
    ('DEFAULT_VOLUME_THRESHOLD', 1000, 50000, int),
    ('DEFAULT_MARKETCAP_THRESHOLD', 10000, 100000, int),
    ('MIN_VOLATILITY', 0.01, 3.0, float),
    ('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 1, 1002, int),
    ('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100, 100, int),
    ('SOL_TO_BUY', 0.1, 0.5, float),
    
    # Emergency & Re-buy parameters
    ('MC_DROP_THRESHOLD_RL', 1.0, 20.0, float),
    ('USE_TREND_REVERSAL_CONFIRMATION', 0.0, 1.0, float),
    ('STOP_LOSS_COOLDOWN_MINUTES', 0.0, 60.0, int),
    
    # PUMP.FUN Trend Reversal Parameters
    ('TREND_REVERSAL_RECENCY_HOURS', 0.25, 12.0, int),
    ('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 30.0, 60.0, float),
    ('INDICATOR_LOOKBACK_HOURS', 0.25, 6.0, int),
    ('RSI_PERIOD', 4.0, 50.0, int),
    ('BBANDS_PERIOD', 10.0, 30.0, int),
    ('BBANDS_STD_DEV', 1.0, 2.5, float),
    ('FAST_EMA_PERIOD', 5.0, 20.0, int),
    ('SLOW_EMA_PERIOD', 15.0, 80.0, int),

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

MIN_MARKET_CAP_USD_FALLBACK: int = 4000

MIN_CANDLE_DATA_FOR_INDICATORS: int = 30
APPLY_TREND_REVERSAL_ON_SELL_REASONS = ["🛑 Stop Loss", "🆘 Emergency SL (MCap)", "↘️ Trailing SL", "🛡️ Breakeven SL", "manual_override"]

VOLATILITY_WINDOW: int = 120 # Window size (steps) for volatility calculation in env

# Total training timesteps. Needs significant increase for real training.
TOTAL_TIMESTEPS: int = 10_000_000 #1_000_000 # Increase for more thorough training (e.g., 1M+)

# Number of parallel environments. Adjust based on CPU cores.
N_ENVS: int = 8 # Example: Use 8 parallel environments if CPU allows

TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/"
MODEL_SAVE_DIR: str = "./rl_trained_models/"

# Evaluation frequency (in total agent steps across all envs).
EVAL_FREQ: int = 100000 #50000 # Evaluate every 50k total steps

# Number of episodes for each evaluation run.
N_EVAL_EPISODES: int = 120 #60 # More episodes for better evaluation stability

# Checkpoint saving frequency (in total agent steps).
CHECKPOINT_FREQ: int = 500000 # Save every 100k total steps

# --- Data Settings ---
# Same split as GA for consistency when reusing load_and_split_data
DATA_SPLIT_RL: Dict[str, float] = {
    "training": 0.6,
    "validation": 0.2,
    "test": 0.2
}

# --- START: Centralized PPO Hyperparameters ---

# --- RL Agent & Training Configuration (Stable Baselines3) ---
RL_ALGORITHM: str = "PPO" # PPO is robust; SAC/TD3 are alternatives

# Defines the neural network architecture.
# CHANGEABLE FOR: New models only. Cannot be changed when fine-tuning.
POLICY_KWARGS: Dict[str, Any] = dict(net_arch=dict(pi=[128, 128], vf=[128, 128]))

# PPO-specific hyperparameters.
PPO_HYPERPARAMS: Dict[str, Any] = {
    # Number of steps to run for each environment per update.
    # CHANGEABLE FOR: New models only.
    "n_steps": 2048,
    
    # The number of training epochs to run per update.
    # CHANGEABLE FOR: New models and fine-tuning.
    "n_epochs": 10,

    # Minibatch size for each epoch.
    # CHANGEABLE FOR: New models only.
    "batch_size": 64,

    # Discount factor for future rewards.
    # CHANGEABLE FOR: New models and fine-tuning.
    "gamma": 0.99,

    # Factor for trade-off of bias vs. variance in Advantage function.
    # Recommendation: Lower to 0.9 for less variance and more focus on immediate rewards.
    # CHANGEABLE FOR: New models and fine-tuning.
    "gae_lambda": 0.9,

    # Clipping parameter for the policy update.
    # Recommendation: Lower to 0.15 for more stable, smaller policy updates.
    # CHANGEABLE FOR: New models and fine-tuning.
    "clip_range": 0.15,

    # Entropy coefficient to encourage exploration.
    # Recommendation: 0.005 to encourage slight exploration around the learned policy.
    # CHANGEABLE FOR: New models and fine-tuning.
    "ent_coef": 0.01,

    # Value function coefficient for the loss calculation.
    # CHANGEABLE FOR: New models and fine-tuning.
    "vf_coef": 0.7,

    # The learning rate for the Adam optimizer.
    # CHANGEABLE FOR: New models only. Changing this during fine-tuning is not recommended.
    "learning_rate": 3e-5,

    # The maximum value for the gradient clipping.
    # CHANGEABLE FOR: New models and fine-tuning.
    "max_grad_norm": 0.5,

    # Whether to use State-Dependent Exploration (SDE).
    # CHANGEABLE FOR: New models only.
    "use_sde": False,
    "sde_sample_freq": -1,
}
# --- END: Centralized PPO Hyperparameters ---


# --- Live Agent Configuration (for deployment) ---
# How often the live bot queries the trained agent for new parameters (seconds).
AGENT_ACTION_INTERVAL_SECONDS: int = 15 # Update parameters every minute
```

---

### 📄 rl_environment.py

```python
# FILE: rl_environment.py (OHLCV Adapted & Refinements)

"""
Custom Gymnasium Environment for Training a Solana Pump.fun Trading Bot RL Agent.

This environment simulates the trading process based on historical OHLCV data, including
handling for token death and applying appropriate rewards/penalties.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import random
from collections import deque
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import timezone, datetime, timedelta

# --- Project Modules ---
from bot_logger import logger
import rl_config # Import RL specific configurations
from utils import calculate_volatility, calculate_trend_indicators # Keep utility for potential recalculation

# --- Environment Class ---

class TradingEnv(gym.Env):
    """
    Custom Gymnasium Environment for Solana Pump Trading Simulation using OHLCV data.

    Action Space (Continuous):
        Box space representing tunable trading parameters (rl_config.RL_TUNABLE_PARAMETERS).

    Observation Space (Continuous):
        Box space representing market state and portfolio status from OHLCV data, normalized
        (rl_config.OBSERVATION_FEATURES).

    Reward:
        Combination of realized PnL, shaping rewards/penalties, and death penalty.
    """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}

    def __init__(
        self,
        historical_data_dict: Dict[str, pd.DataFrame], # Expects OHLCV data per mint
        token_lifespans: Dict[str, Dict[str, datetime]],
        dexscreener_snapshot_data: Dict[str, pd.DataFrame],
        initial_capital: float = rl_config.RL_INITIAL_CAPITAL,
        max_steps: Optional[int] = None,
        render_mode: Optional[str] = None
    ):
        """
        Initializes the Trading Environment with OHLCV data.

        Args:
            historical_data_dict: Dictionary mapping mints to their historical 5s OHLCV DataFrames.
                                  Indices MUST be timezone-aware UTC DatetimeIndex.
                                  Expected columns: 'Open', 'High', 'Low', 'Close', 'Volume',
                                                    'market_cap_calculated', 'rugcheck_score', 'socials_score',
                                                    'token_creation_time'.
                                  Note: Assumes a fixed step interval (e.g., 5 seconds) based on data frequency.
            token_lifespans: Dictionary mapping mints to their {'start_ts', 'end_ts'} (UTC).
            initial_capital: Starting SOL balance for each episode.
            max_steps: Maximum number of steps allowed per episode (truncation).
        """
        super().__init__()

        if not historical_data_dict:
            raise ValueError("Historical OHLCV data dictionary cannot be empty.")
        if not token_lifespans:
            raise ValueError("Token lifespans dictionary cannot be empty.")

        # --- Validate and Store OHLCV Data ---
        self.historical_data_dict = {}
        self.token_lifespans = {}

        # These are the columns expected in the DataFrame for each mint
        required_cols = [
            'Open', 'High', 'Low', 'Close', 'Volume',
            'market_cap_calculated',     # Live USD MC
            'marketCapSol',              # Live SOL MC
            'creation_init_market_cap_sol', # Creation-time SOL MC
            'volatility', 'rugcheck_score', 'socials_score',
            'token_creation_time'
        ]

        for mint, df in historical_data_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty and isinstance(df.index, pd.DatetimeIndex):
                 if df.index.tz is None or str(df.index.tz).upper() != 'UTC':
                     logger.error(f"DataFrame index for mint {mint} is not timezone-aware UTC! Skipping.")
                     continue
                 if mint not in token_lifespans:
                      logger.warning(f"Lifespan info missing for mint {mint}. Skipping.")
                      continue
                 missing_cols_check = [col for col in required_cols if col not in df.columns]
                 if missing_cols_check:
                     logger.error(f"Missing required OHLCV columns in data for mint {mint}: {missing_cols_check}. Skipping.")
                     continue
                 if df[required_cols].isnull().values.any():
                      logger.warning(f"NaN values found in required columns for mint {mint}. Will attempt fill/clip later.")
                 self.historical_data_dict[mint] = df
                 self.token_lifespans[mint] = token_lifespans[mint]
            else:
                 logger.warning(f"Skipping invalid/empty DataFrame for mint: {mint}")

        # Store the snapshot data
        self.dexscreener_snapshot_data = dexscreener_snapshot_data

        self.available_mints = list(self.historical_data_dict.keys())
        if not self.available_mints:
            raise ValueError("No valid OHLCV DataFrames found after validation.")

        self.initial_capital = initial_capital
        
        # Defensively handle the case where max_steps might be None.
        if max_steps is None:
            logger.warning(
                f"max_steps was not provided to TradingEnv constructor. "
                f"Using fallback value from rl_config: {rl_config.MAX_STEPS_PER_EPISODE_FALLBACK}."
            )
            self._max_episode_steps = rl_config.MAX_STEPS_PER_EPISODE_FALLBACK
        else:
            self._max_episode_steps = max_steps


        self.action_space = spaces.Box(
            low=rl_config.ACTION_LOW,
            high=rl_config.ACTION_HIGH,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        self._action_param_names = [p[0] for p in rl_config.RL_TUNABLE_PARAMETERS]

        self.observation_space = spaces.Box(
            low=rl_config.OBSERVATION_LOW, # Using -np.inf
            high=rl_config.OBSERVATION_HIGH, # Using np.inf
            shape=(rl_config.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        self.current_step: int = 0
        self.current_sol: float = 0.0
        self.current_data_df: Optional[pd.DataFrame] = None
        self.current_mint: Optional[str] = None
        self.current_token_end_ts: Optional[datetime] = None
        self.initial_creation_market_cap_sol: Optional[float] = None # For MC drop %
        self.active_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {}
        self.last_observation: np.ndarray = np.zeros(self.observation_space.shape, dtype=np.float32)
        self._price_history: deque = deque(maxlen=rl_config.OBSERVATION_PRICE_HISTORY_LENGTH)
        self._previous_unrealized_pnl: float = 0.0
        self._last_step_processed_index = -1
        self.current_snapshot_df: Optional[pd.DataFrame] = None # Add state for current snapshot df

        logger.info(f"TradingEnv (OHLCV) initialized. Observation space dim: {rl_config.OBSERVATION_SPACE_DIM}, Action space dim: {rl_config.ACTION_SPACE_DIM}")


    def _get_observation(self) -> np.ndarray:
        default_obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        if self.current_data_df is None or self._last_step_processed_index < 0 or self._last_step_processed_index >= len(self.current_data_df):
            return default_obs
        try:
            current_row = self.current_data_df.iloc[self._last_step_processed_index]
            current_timestamp = self.current_data_df.index[self._last_step_processed_index]
        except IndexError: return default_obs

        current_price = current_row.get('Close', 0.0)
        self._price_history.append(float(current_price) if pd.notna(current_price) and isinstance(current_price, (int, float)) else (self._price_history[-1] if self._price_history else 0.0))

        try:
            live_usd_market_cap = float(current_row.get('market_cap_calculated', 0.0))
            live_sol_market_cap = float(current_row.get('marketCapSol', 0.0)) # Live SOL MC
            volume = float(current_row.get('Volume', 0.0))
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            creation_time_ts = current_row.get('token_creation_time', pd.NaT)
            volatility = float(current_row.get('volatility', 0.0))

            live_usd_market_cap = 0.0 if pd.isna(live_usd_market_cap) else live_usd_market_cap
            live_sol_market_cap = 0.0 if pd.isna(live_sol_market_cap) else live_sol_market_cap
            volume = 0.0 if pd.isna(volume) else volume
            rugcheck_score = 10000 if pd.isna(rugcheck_score) else int(rugcheck_score)
            socials_score = 100 if pd.isna(socials_score) else int(socials_score)
            volatility = 0.0 if pd.isna(volatility) else volatility

        except (KeyError, ValueError, TypeError) as e: return default_obs

        prices_arr = np.array(self._price_history, dtype=np.float32)
        safe_prices = prices_arr[prices_arr > 1e-12]
        price_change_1 = np.log(safe_prices[-1] / safe_prices[-2]) if len(safe_prices) >= 2 else 0.0
        price_change_5 = np.log(safe_prices[-1] / safe_prices[-6]) if len(safe_prices) >= 6 else 0.0
        price_change_10 = np.log(safe_prices[-1] / safe_prices[-11]) if len(safe_prices) >= 11 else 0.0

        time_since_creation_seconds = 0.0
        if pd.notna(creation_time_ts) and isinstance(current_timestamp, pd.Timestamp):
            ct_ts_aware = creation_time_ts.tz_localize('UTC') if creation_time_ts.tzinfo is None else creation_time_ts.astimezone(timezone.utc)
            time_diff = current_timestamp - ct_ts_aware
            time_since_creation_seconds = max(0.0, time_diff.total_seconds())

        is_holding = 1.0 if self.active_position else 0.0
        position_pnl_current_unrealized = 0.0
        time_holding_seconds = 0.0
        if self.active_position:
            buy_p = self.active_position['buy_price']
            rem_t = self.active_position['remaining_tokens']
            total_inv = self.active_position.get('total_investment_sol', 1.0)
            last_p = prices_arr[-1] if prices_arr.size > 0 else buy_p
            curr_val = last_p * rem_t
            init_t = self.active_position.get('initial_tokens', rem_t)
            cost_frac = rem_t / init_t if init_t > 0 else 1.0
            cost_basis_rem = total_inv * cost_frac
            position_pnl_current_unrealized = curr_val - cost_basis_rem
            entry_ts = self.active_position.get('entry_timestamp')
            if entry_ts: time_holding_seconds = max(0.0, (current_timestamp - entry_ts).total_seconds())
        
        weekday = float(current_timestamp.weekday())
        hour = float(current_timestamp.hour)

        # These are raw values; VecNormalize will handle scaling
        observation_list = [
            price_change_1, price_change_5, price_change_10,
            volatility,
            live_sol_market_cap,    # For 'live_market_cap_sol_norm'
            live_usd_market_cap,    # For 'live_market_cap_usd_norm'
            volume,
            float(rugcheck_score), 
            float(socials_score), 
            time_since_creation_seconds,
            is_holding, 
            position_pnl_current_unrealized, 
            time_holding_seconds, 
            self.current_sol,
            weekday, 
            hour
        ]
        
        observation = np.array(observation_list, dtype=np.float32)
        if not np.all(np.isfinite(observation)): observation = default_obs
        elif observation.shape != self.observation_space.shape: observation = default_obs
        
        self.last_observation = observation
        self._previous_unrealized_pnl = position_pnl_current_unrealized
        return observation

    def _apply_action(self, action: np.ndarray):
        new_params = {}
        clipped_action = np.clip(action, rl_config.ACTION_LOW, rl_config.ACTION_HIGH)
        for i, param_config in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            param_name, _, _, p_type = param_config
            val = clipped_action[i]
            if param_name == "USE_TREND_REVERSAL_CONFIRMATION":
                # Convert float action (0.0-1.0) to boolean for this parameter
                new_params[param_name] = bool(val > 0.5)
            else:
                new_params[param_name] = p_type(np.round(val)) if p_type == int else float(val)
        self.current_parameters = new_params

    def _run_trading_logic_step(self) -> Tuple[float, float]:
        """
        [REWRITTEN] Simulates one step of the trading logic using OHLCV data.
        This now includes the complete, source-aware trend reversal logic to match the backtester.
        Returns realized PnL and any shaping bonuses/penalties for the step.
        """
        realized_pnl_this_step = 0.0
        reward_bonus_penalty = 0.0

        current_data_index = self.current_step
        self._last_step_processed_index = current_data_index

        if self.current_data_df is None or current_data_index >= len(self.current_data_df):
            return realized_pnl_this_step, reward_bonus_penalty

        try:
            current_row = self.current_data_df.iloc[current_data_index]
            current_timestamp = self.current_data_df.index[current_data_index]
            
            price = float(current_row.get('Close', 0.0))
            volume_ohlcv = float(current_row.get('Volume', 0.0))
            high_price = float(current_row.get('High', 0.0))
            current_live_usd_mc = float(current_row.get('market_cap_calculated', 0.0))
            rugcheck_val = int(current_row.get('rugcheck_score', 10000))
            socials_val = int(current_row.get('socials_score', 100))
            volatility_val = float(current_row.get('volatility', 0.0))

            if price <= 1e-12:
                return realized_pnl_this_step, reward_bonus_penalty

            agent_params = self.current_parameters
            initial_sl_percent = agent_params.get('INITIAL_STOP_LOSS_PERCENT', 40.0)
            first_sell_percent = agent_params.get('FIRST_SELL_PERCENT', 35.0)
            trailing_sl_percent = agent_params.get('TRAILING_STOP_LOSS_PERCENT', 15.0)
            first_sell_profit_margin = agent_params.get('FIRST_SELL_PROFIT_MARGIN', 70.0)
            second_take_profit_percent = agent_params.get('SECOND_TAKE_PROFIT_PERCENT', 450.0)
            
            volume_thresh_usd = agent_params.get('DEFAULT_VOLUME_THRESHOLD', 40000)
            mcap_thresh_buy_usd = agent_params.get('DEFAULT_MARKETCAP_THRESHOLD', 20000)
            rug_thresh_agent = agent_params.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 401)
            social_thresh_agent = agent_params.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100)
            volatility_thresh_agent = agent_params.get('MIN_VOLATILITY', 0.18)
            buy_amount_sol_agent = agent_params.get('SOL_TO_BUY', 0.5)
            use_trend_reversal = agent_params.get('USE_TREND_REVERSAL_CONFIRMATION', False)

            buy_fee = rl_config.DEFAULT_BUY_FEE
            buy_tip = rl_config.DEFAULT_BUY_TIP
            sell_fee = rl_config.DEFAULT_SELL_FEE
            sell_tip = rl_config.DEFAULT_SELL_TIP
            min_mcap_usd_fallback = rl_config.MIN_MARKET_CAP_USD_FALLBACK

        except (KeyError, ValueError, TypeError, IndexError) as e:
            logger.error(f"RL Env: Error getting data/params at step {self.current_step}: {e}", exc_info=False)
            return realized_pnl_this_step, reward_bonus_penalty
        
        if self.active_position:
            pos = self.active_position
            pos['highest_price'] = max(pos['highest_price'], high_price)
            
            sell_reason = None
            if price <= pos['stop_loss_price']:
                sell_reason = "Stop Loss" if not pos['first_tp_hit'] else "Breakeven SL"
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif price >= pos['second_tp_price']:
                sell_reason = "Second TP"
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif not pos['first_tp_hit'] and price >= pos['initial_tp_price']:
                sell_reason = "First TP"
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif pos['first_tp_hit']:
                trailing_sl_price = pos['highest_price'] * (1.0 - trailing_sl_percent / 100.0)
                if trailing_sl_price > 0 and price <= trailing_sl_price:
                    sell_reason = "Trailing SL"
                    reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            
            if current_live_usd_mc > 0 and current_live_usd_mc < min_mcap_usd_fallback and not sell_reason:
                 sell_reason = f"Emergency SL (Abs USD MCap < {min_mcap_usd_fallback})"
                 reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            
            if sell_reason:
                initial_tokens = pos['initial_tokens']
                remaining_tokens = pos['remaining_tokens']
                
                tokens_to_sell = remaining_tokens
                if sell_reason == "First TP":
                    tokens_to_sell = min(initial_tokens * (first_sell_percent / 100.0), remaining_tokens)
                
                if tokens_to_sell > 1e-9:
                    gross_sol_recv = tokens_to_sell * price
                    net_sol_recv = gross_sol_recv - sell_fee - sell_tip
                    cost_basis_sold = pos['total_investment_sol'] * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                    pnl = net_sol_recv - cost_basis_sold
                    realized_pnl_this_step += pnl
                    self.current_sol += net_sol_recv
                    pos['remaining_tokens'] -= tokens_to_sell
                    self.trade_history.append({'step': self.current_step, 'type': 'sell', 'price': price, 'tokens': tokens_to_sell, 'pnl': pnl, 'reason': sell_reason})
                    
                    if sell_reason == "First TP":
                        pos['first_tp_hit'] = True
                        pos['stop_loss_price'] = pos['buy_price'] # Breakeven
                    
                    if pos['remaining_tokens'] < 1e-9:
                        self.active_position = None
        
        if not self.active_position and self.current_sol >= (buy_amount_sol_agent + buy_fee + buy_tip):
            meets_standard_criteria = (
                volume_ohlcv >= volume_thresh_usd and
                current_live_usd_mc >= mcap_thresh_buy_usd and
                rugcheck_val < rug_thresh_agent and
                socials_val < social_thresh_agent and
                volatility_val >= volatility_thresh_agent
            )

            proceed_with_buy_attempt = False
            if not meets_standard_criteria:
                proceed_with_buy_attempt = False
            elif use_trend_reversal:
                recency_hours = agent_params.get('TREND_REVERSAL_RECENCY_HOURS', 6)
                applicable_reasons = rl_config.APPLY_TREND_REVERSAL_ON_SELL_REASONS
                was_recently_sold = False
                if self.trade_history:
                    last_sell = next((t for t in reversed(self.trade_history) if t['type'] == 'sell'), None)
                    if last_sell:
                        time_since_sell = current_timestamp - self.current_data_df.index[last_sell['step']]
                        if time_since_sell <= timedelta(hours=recency_hours) and any(r in last_sell.get('reason','') for r in applicable_reasons):
                            was_recently_sold = True

                if was_recently_sold:
                    is_migrated = self.current_snapshot_df is not None and not self.current_snapshot_df.empty
                    
                    if is_migrated:
                        lookback_minutes = agent_params.get('DEX_REVERSAL_LOOKBACK_MINUTES', 15)
                        min_snapshots = agent_params.get('DEX_REVERSAL_MIN_SNAPSHOTS', 3)
                        min_liquidity = agent_params.get('DEX_REVERSAL_MIN_LIQUIDITY_USD', 5000)
                        min_ratio = agent_params.get('DEX_REVERSAL_MIN_BUY_SELL_RATIO', 1.5)
                        min_confirmations = agent_params.get('DEX_REVERSAL_MIN_CONFIRMATIONS', 2)

                        time_filter_start = current_timestamp - timedelta(minutes=lookback_minutes)
                        snapshots = self.current_snapshot_df.loc[(self.current_snapshot_df.index > time_filter_start) & (self.current_snapshot_df.index <= current_timestamp)]

                        if len(snapshots) < min_snapshots or float(snapshots.iloc[-1]['liquidity_usd']) < min_liquidity:
                            proceed_with_buy_attempt = False
                        else:
                            count = sum(1 for _, s in snapshots.iterrows() if s.get('buys_m5', 0) > 0 and (s.get('sells_m5', 0) == 0 or (s.get('buys_m5') / s.get('sells_m5')) >= min_ratio))
                            proceed_with_buy_attempt = count >= min_confirmations
                    else: # PUMP.FUN Logic
                        lookback_h = agent_params.get('INDICATOR_LOOKBACK_HOURS', 1)
                        candles_needed = int(lookback_h * 3600 / 5)
                        start_idx = max(0, self.current_step - candles_needed + 1)
                        
                        if (self.current_step - start_idx + 1) >= rl_config.MIN_CANDLE_DATA_FOR_INDICATORS:
                            indicator_config = {
                                'MIN_CANDLE_DATA_FOR_INDICATORS': rl_config.MIN_CANDLE_DATA_FOR_INDICATORS,
                                **{k: agent_params.get(k, v) for k, v in {
                                    'RSI_PERIOD': 14, 'BBANDS_PERIOD': 20, 'BBANDS_STD_DEV': 2.0, 
                                    'FAST_EMA_PERIOD': 9, 'SLOW_EMA_PERIOD': 21
                                }.items()}
                            }
                            df_inds = calculate_trend_indicators(self.current_data_df.iloc[start_idx : self.current_step + 1].copy(), indicator_config)

                            if not df_inds.empty and len(df_inds) >= 2:
                                latest = df_inds.iloc[-1]; prev = df_inds.iloc[-2]
                                rsi_neutral = agent_params.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 45)
                                bbl_col = f"BBL_{indicator_config['BBANDS_PERIOD']}_{indicator_config['BBANDS_STD_DEV']}"
                                stage1 = (latest.get('RSI', 50) > 30 and prev.get('RSI', 50) <= 30) or \
                                         (latest.get('Close', 0) > latest.get(bbl_col, float('inf')) and prev.get('Close', 0) <= prev.get(bbl_col, float('inf'))) or \
                                         (latest.get('RSI', 0) > rsi_neutral)
                                stage2 = (latest.get('Close', 0) > latest.get('VWAP', float('-inf'))) and (latest.get('EMA_fast', 0) > latest.get('EMA_slow', float('inf')))
                                proceed_with_buy_attempt = stage1 and stage2
                            else:
                                proceed_with_buy_attempt = False
                        else:
                            proceed_with_buy_attempt = False
                else:
                    proceed_with_buy_attempt = meets_standard_criteria
            else:
                proceed_with_buy_attempt = meets_standard_criteria

            if proceed_with_buy_attempt:
                total_investment = buy_amount_sol_agent + buy_fee + buy_tip
                tokens_bought = buy_amount_sol_agent / price
                self.current_sol -= total_investment
                sl_price = price * (1.0 - initial_sl_percent / 100.0)
                
                cost_of_tp1_portion = total_investment * (first_sell_percent / 100.0)
                desired_profit_tp1 = cost_of_tp1_portion * (first_sell_profit_margin / 100.0)
                fees_tp1_sell = sell_fee + sell_tip
                gross_sol_tp1 = cost_of_tp1_portion + desired_profit_tp1 + fees_tp1_sell
                tokens_tp1 = tokens_bought * (first_sell_percent / 100.0)
                tp1_price = gross_sol_tp1 / tokens_tp1 if tokens_tp1 > 1e-9 else float('inf')
                tp2_price = price * (1.0 + second_take_profit_percent / 100.0)

                self.active_position = {'buy_price': price, 'initial_tokens': tokens_bought, 'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment, 'stop_loss_price': sl_price, 'initial_tp_price': tp1_price, 'second_tp_price': tp2_price, 'highest_price': price, 'first_tp_hit': False, 'entry_timestamp': current_timestamp}
                self.trade_history.append({'step': self.current_step, 'type': 'buy', 'price': price, 'tokens': tokens_bought})
        
        if self.active_position:
            reward_bonus_penalty += rl_config.REWARD_HOLDING_PENALTY
            
        return realized_pnl_this_step, reward_bonus_penalty


    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        if self.current_data_df is None:
            obs = np.zeros(self.observation_space.shape, dtype=np.float32)
            return obs, 0.0, True, False, {"error": "Environment not reset"}

        self._apply_action(action)
        realized_pnl, bonus_penalty = self._run_trading_logic_step()
        
        terminated = self.current_sol <= 0
        
        current_data_idx_for_check = self.current_step 
        end_of_data = current_data_idx_for_check >= len(self.current_data_df) - 1
        
        token_died_this_step = False
        if self.current_token_end_ts and current_data_idx_for_check < len(self.current_data_df):
            current_candle_timestamp = self.current_data_df.index[current_data_idx_for_check]
            if current_candle_timestamp >= self.current_token_end_ts:
                token_died_this_step = True
        
        max_steps_reached = (self.current_step + 1) >= self._max_episode_steps
        truncated = max_steps_reached or end_of_data or token_died_this_step
        is_token_death_event_for_reward = end_of_data or token_died_this_step

        reward = self._calculate_reward(realized_pnl, bonus_penalty, is_token_death_event_for_reward)
        
        self.current_step += 1

        if not (terminated or truncated):
             self._last_step_processed_index = self.current_step
        else:
             self._last_step_processed_index = min(self.current_step, len(self.current_data_df) - 1) if len(self.current_data_df) > 0 else -1

        observation = self._get_observation()

        info = {
            'mint': self.current_mint, 'step': self.current_step - 1,
            'sol_balance': self.current_sol, 'realized_pnl_step': realized_pnl,
            'is_holding': 1 if self.active_position else 0, 'raw_reward': reward
        }
        if terminated or truncated:
            final_val = self.current_sol
            if self.active_position and self._price_history:
                final_val += self.active_position['remaining_tokens'] * self._price_history[-1]
            info['final_portfolio_value'] = final_val
            info['total_steps_taken'] = self.current_step
            if terminated: info['episode_end_reason'] = "terminated (bankrupt)"
            elif token_died_this_step: info['episode_end_reason'] = "truncated (token_death)"
            elif end_of_data: info['episode_end_reason'] = "truncated (end_of_data)"
            elif max_steps_reached: info['episode_end_reason'] = "truncated (max_steps)"
            else: info['episode_end_reason'] = "truncated (unknown)"
            
        return observation, reward, terminated, truncated, info

    def _calculate_reward(self, realized_pnl: float, bonus_penalty: float, is_token_death_event: bool) -> float:
        reward = realized_pnl * rl_config.REWARD_PNL_MULTIPLIER
        reward += bonus_penalty
        if is_token_death_event and self.active_position:
            reward += rl_config.REWARD_DEATH_PENALTY
        return reward

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)

        self.current_mint = random.choice(self.available_mints)
        self.current_data_df = self.historical_data_dict[self.current_mint].copy()
        self.current_snapshot_df = self.dexscreener_snapshot_data.get(self.current_mint)
        
        lifespan = self.token_lifespans.get(self.current_mint)
        if not lifespan:
             raise RuntimeError(f"Lifespan info missing for selected mint {self.current_mint} during reset.")
        self.current_token_end_ts = lifespan['end_ts']

        self.initial_creation_market_cap_sol = None 
        if not self.current_data_df.empty and 'creation_init_market_cap_sol' in self.current_data_df.columns:
            val_series = pd.to_numeric(self.current_data_df['creation_init_market_cap_sol'], errors='coerce')
            first_valid_val = val_series.dropna().iloc[0] if not val_series.dropna().empty else np.nan
            if pd.notna(first_valid_val) and first_valid_val > 0:
                self.initial_creation_market_cap_sol = float(first_valid_val)
        
        if 'volatility' not in self.current_data_df.columns or self.current_data_df['volatility'].isnull().all():
             prices = pd.to_numeric(self.current_data_df.get('Close'), errors='coerce').ffill().bfill().fillna(0.0)
             self.current_data_df['volatility'] = calculate_volatility(prices, window=rl_config.VOLATILITY_WINDOW).fillna(0.0) if len(prices) > 1 else 0.0
        else:
             self.current_data_df['volatility'] = self.current_data_df['volatility'].fillna(0.0)
        
        self.current_step = 0
        self._last_step_processed_index = -1
        self.current_sol = self.initial_capital
        self.active_position = None
        self.trade_history = []
        self.current_parameters = {}
        self._price_history.clear()
        self._previous_unrealized_pnl = 0.0
        self.last_observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        initial_steps_to_fill = min(len(self.current_data_df), self._price_history.maxlen)
        for i in range(initial_steps_to_fill):
            try:
                price = float(self.current_data_df.iloc[i].get('Close', 0.0))
                self._price_history.append(price if pd.notna(price) else 0.0)
            except (IndexError, ValueError, TypeError): self._price_history.append(0.0)

        if len(self.current_data_df) > 0:
            self._last_step_processed_index = 0
            observation = self._get_observation()
            self._last_step_processed_index = -1 
        else:
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)
        return observation, {}

    def render(self, mode='human'):
        if mode == 'ansi':
            output = f"--- Step: {self.current_step}/{self._max_episode_steps} (Data Index: {self._last_step_processed_index}) ---\n"
            output += f"Mint: {self.current_mint}\n"
            output += f"SOL Balance: {self.current_sol:.4f}\n"
            if self.active_position:
                pos = self.active_position
                output += f"Holding: {pos['remaining_tokens']:.4f} tokens (Bought @ {pos['buy_price']:.9f})\n"
            else:
                output += "Holding: None\n"
            last_close = self._price_history[-1] if self._price_history else 'N/A'
            output += f"Last Close Price: {last_close}\n"
            return output
        elif mode == 'human':
            print(self.render(mode='ansi'))

    def close(self):
        pass

    def set_render_mode(self, render_mode: Optional[str]):
        self.render_mode = render_mode

```

---

### 📄 rl_trainer.py

```python
# FILE: rl_trainer.py (Updated Env Initialization)

"""
Reinforcement Learning Agent Training Script.

This module orchestrates the training process for a Reinforcement Learning (RL) agent 
using Stable Baselines3 to learn optimal trading parameters within a custom TradingEnv environment.

Key Features:
- Trains an RL agent for trading strategy optimization
- Supports visualization of training progress via TensorBoard
- Configurable environment and agent parameters

TensorBoard Visualization:
To monitor training details, run:
    tensorboard --logdir ./rl_tensorboard_logs/ --port 6006
"""

import os
import asyncio
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime
import argparse # Import argparse
from typing import Dict, Optional, Union, Tuple, Callable # Import Callable
import warnings

# --- Stable Baselines3 Imports ---
try:
    import stable_baselines3
    from stable_baselines3 import PPO, SAC, TD3
    from stable_baselines3.common.env_util import make_vec_env
    # Import VecEnv types explicitly
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv, VecNormalize
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.env_checker import check_env
    from stable_baselines3.common.logger import configure as sb3_configure_logger
    RL_AVAILABLE = True
except ImportError:
    print("Stable Baselines3 library not found or has issues. RL training is unavailable.")
    print("Please install it: pip install stable-baselines3[extra]>=2.0.0a5")
    RL_AVAILABLE = False
    class DummyAlgorithm: pass
    PPO = SAC = TD3 = DummyAlgorithm
    class BaseCallback: pass
    class VecEnv: pass # Dummy VecEnv base class
    class DummyVecEnv(VecEnv): pass
    class SubprocVecEnv(VecEnv): pass
    class VecNormalize(VecEnv): pass

import shap
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt

# --- Project Modules ---
import rl_config
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_environment import TradingEnv # Ensure TradingEnv takes lifespan info
from utils import load_and_split_data, calculate_volatility, export_to_csv, NpEncoder # Import NpEncoder for saving

# --- Global Variables ---
db_client_global: Optional[DatabaseClient] = None

# --- Helper function for hyperparameter schedules ---
def get_schedule_fn(value: Union[float, int]) -> Callable[[float], Union[float, int]]:
    """
    Returns a schedule function that returns a constant value.
    This is used to wrap fixed hyperparameter values so they can be
    treated as a callable schedule by Stable Baselines3.
    """
    def func(_progress_remaining: float) -> Union[float, int]:
        return value
    return func

# --- Custom Callback ---
class TensorboardCallback(BaseCallback):
    """Logs additional custom values to TensorBoard."""
    def __init__(self, verbose=0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        # Log average final portfolio value from completed episodes
        final_values = [ep_info.get('final_portfolio_value') for ep_info in self.model.ep_info_buffer if 'final_portfolio_value' in ep_info]
        if final_values:
            avg_final_value = np.mean(final_values)
            self.logger.record('rollout/ep_final_value_mean', avg_final_value)

        # Log average SOL balance at episode end
        sol_balances = [ep_info.get('sol_balance') for ep_info in self.model.ep_info_buffer if 'sol_balance' in ep_info and ep_info.get('terminated', False) or ep_info.get('truncated', False)]
        if sol_balances:
             avg_sol_balance = np.mean(sol_balances)
             self.logger.record('rollout/ep_sol_balance_mean', avg_sol_balance)
        return True

# Add this class after the TensorboardCallback class
class SaveVecNormalizeCallback(BaseCallback):
    """Callback to save VecNormalize statistics when a new best model is found."""
    def __init__(self, save_path: str, verbose=0):
        super().__init__(verbose)
        self.save_path = save_path

    def _on_step(self) -> bool:
        vec_normalize = self.model.get_vec_normalize_env()
        if vec_normalize is not None:
            vec_normalize.save(self.save_path)
        return True

def analyze_feature_importance(model, env, num_samples=1000):
    """Analyzes feature importance using SHAP and Permutation Importance."""
    # Generate properly structured samples
    samples = np.array([env.observation_space.sample() for _ in range(num_samples)])

    # Create a simple wrapper class for the model to be used as an estimator
    class ModelPredictor:
        def __init__(self, model):
            self.model = model

        def predict(self, X):
            # Ensure the input X is treated as a batch for prediction
            # Stable Baselines3 returns (action, state) tuple
            return np.array([self.model.predict(sample)[0] for sample in X])

        # Add a dummy fit method to satisfy permutation_importance's check
        def fit(self, X, y=None):
            return self

    model_predictor = ModelPredictor(model)

    # SHAP Analysis
    # Use the ModelPredictor instance as the model for SHAP
    explainer = shap.Explainer(
        model_predictor.predict, # Pass the predict method
        samples,
        feature_names=rl_config.OBSERVATION_FEATURES
    )

    # Calculate SHAP values
    # Use a reasonable subset of samples for SHAP to manage memory and computation
    shap_samples = samples[:500] # Increased samples for SHAP
    shap_values = explainer(shap_samples)

    # Plot summary
    plt.figure()
    shap.summary_plot(shap_values, shap_samples, show=False, feature_names=rl_config.OBSERVATION_FEATURES) # Pass feature_names explicitly
    plt.savefig(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_shap.png"))
    plt.close()

    # Permutation Importance
    # Use a reasonable subset of samples for permutation importance
    perm_samples = samples[:500] # Increased samples for permutation importance

    # Define a scoring function for permutation_importance that accepts X and y but only uses X
    def mean_prediction_magnitude_score(estimator, X, y):
        # Estimator here is our ModelPredictor instance
        predictions = estimator.predict(X)
        # For a continuous action space, predictions is an array of actions.
        # We can take the mean of the sum of squares of actions to measure the magnitude.
        # Use negative because permutation_importance expects a score where higher is better,
        # and we want features that *decrease* the score (change the prediction) to be important.
        return -np.mean(np.sum(predictions**2, axis=-1))

    # --- START: Fix for FutureWarning ---
    # Create a modern NumPy random number generator instance for reproducibility.
    # This avoids the deprecated global `np.random.seed`.
    rng = np.random.default_rng(42)
    # --- END: Fix for FutureWarning ---

    result = permutation_importance(
        model_predictor, # Pass the ModelPredictor instance as the estimator
        perm_samples, # This is X
        y=None, # Explicitly pass y=None
        scoring=mean_prediction_magnitude_score, # Provide custom scoring
        n_repeats=5,
        random_state=rng, # FIX: Pass the generator instance instead of an integer seed
        n_jobs=1
    )

    # Save results
    importance_df = pd.DataFrame({
        'feature': rl_config.OBSERVATION_FEATURES,
        'importance_mean': result.importances_mean, # Access mean directly
        'importance_std': result.importances_std # Access std directly
    }).sort_values('importance_mean', ascending=False)

    importance_df.to_csv(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_permutation.csv"), index=False)

    logger.info("Feature importance analysis completed")

# --- Environment Creation Helper ---
def make_env_func(
    data_dict: Dict[str, pd.DataFrame],
    lifespan_dict: Dict[str, Dict[str, datetime]], # Add lifespans
    snapshot_dict: Dict[str, pd.DataFrame],
    initial_capital: float,
    max_steps: int,
    rank: int = 0,
    seed: int = 0,
    render_mode: Optional[str] = None # Added render_mode parameter
):
    """
    Utility function for creating and wrapping the environment for VecEnv.

    Args:
        data_dict: Historical data for this environment instance.
        lifespan_dict: Token lifespan data for this environment instance.
        initial_capital: Starting capital.
        max_steps: Max steps per episode.
        rank: Unique identifier for the environment instance.
        seed: Base random seed.

    Returns:
        A function that initializes and returns the wrapped environment.
    """
    def _init():
        # Filter data to only include mints present in lifespan_dict
        valid_data = {
            k: v for k, v in data_dict.items()
            if isinstance(v, pd.DataFrame) and not v.empty and k in lifespan_dict
        }
        valid_lifespans = {k: v for k, v in lifespan_dict.items() if k in valid_data}
        # Filter snapshots to only include those for valid mints
        valid_snapshots = {k: v for k, v in snapshot_dict.items() if k in valid_data}


        if not valid_data or not valid_lifespans:
            logger.error(f"make_env_func (rank {rank}) received empty/invalid data or missing lifespans!")
            raise ValueError(f"Cannot create environment for rank {rank} with empty data or missing lifespans.")

        env = TradingEnv(
            historical_data_dict=valid_data,
            token_lifespans=valid_lifespans, # Pass lifespans
            dexscreener_snapshot_data=valid_snapshots,
            initial_capital=initial_capital,
            max_steps=max_steps,
            render_mode=render_mode # Pass render_mode to TradingEnv
        )
        env.reset(seed=seed + rank) # Seed the environment
        log_dir_monitor = os.path.join(rl_config.MODEL_SAVE_DIR, f"monitor_logs_{rank}")
        os.makedirs(log_dir_monitor, exist_ok=True)
        env = Monitor(env, filename=log_dir_monitor)
        return env
    return _init

# --- Main Training Function ---
async def train_rl_agent(render_mode: Optional[str] = None, continue_from_model: Optional[str] = None):
    """
    Sets up the RL environment, agent, callbacks, and starts training.

    Args:
        render_mode: The render mode for the training environment.
        continue_from_model: Path to a saved model to continue training from.
    """
    global db_client_global
    setup_logging(logger_name="rl_trainer") # Initialize logger for this module
    logger.info("--- Starting RL Agent Training ---")

    if not RL_AVAILABLE:
        logger.critical("Stable Baselines3 is not available. Cannot start RL training.")
        return

    # --- Database Connection ---
    if not db_client_global:
        db_client_global = DatabaseClient()
        try:
            await db_client_global.connect()
            logger.info("DB Client connected for RL Trainer.")
        except Exception as e:
            logger.critical(f"Failed to connect database for RL Trainer: {e}")
            return

    # --- Load and Prepare Data ---
    start_date = rl_config.RL_HISTORICAL_DATA_START_TS
    end_date = rl_config.RL_HISTORICAL_DATA_END_TS
    data_split_config = rl_config.DATA_SPLIT_RL

    logger.info(f"Loading and splitting data from {start_date.isoformat()} to {end_date.isoformat()}...")
    loaded_results: Optional[Tuple[Dict, Dict, Dict]] = await load_and_split_data(
        db_client_global, start_date, end_date, data_split_config
    )

    if not loaded_results:
        logger.critical("Failed to load or split data. Exiting.")
        await db_client_global.close() if db_client_global else None
        return

    loaded_data_sets, token_lifespans, dexscreener_snapshots  = loaded_results

    training_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_EVAL)

    train_lifespans = {k: v for k, v in token_lifespans.items() if k in training_data} if training_data else {}
    eval_lifespans = {k: v for k, v in token_lifespans.items() if k in eval_data} if eval_data else {}

    # Filter snapshots for each data split
    train_snapshots = {k: v for k, v in dexscreener_snapshots.items() if k in training_data} if training_data else {}
    eval_snapshots = {k: v for k, v in dexscreener_snapshots.items() if k in eval_data} if eval_data else {}


    if not training_data or not train_lifespans:
        logger.critical("No training data or corresponding lifespans available. Exiting.")
        await db_client_global.close() if db_client_global else None
        return

    logger.info(f"Training data loaded for {len(training_data)} tokens with lifespan info.")
    if eval_data and eval_lifespans:
        logger.info(f"Evaluation data loaded for {len(eval_data)} tokens with lifespan info.")
    else:
        logger.warning("No evaluation data/lifespans found. Evaluation callback will not function correctly.")
        eval_data = None
        eval_lifespans = {}

    # --- START: Dynamic MAX_STEPS_PER_EPISODE Calculation ---
    if train_lifespans:
        lifespan_durations_seconds = [
            (v['end_ts'] - v['start_ts']).total_seconds()
            for v in train_lifespans.values()
            if v['end_ts'] and v['start_ts']
        ]
        if lifespan_durations_seconds:
            # Use the percentile from the config file
            percentile_value = rl_config.MAX_STEPS_PERCENTILE
            percentile_duration = np.percentile(lifespan_durations_seconds, percentile_value)
            
            # Assuming 5-second candles (steps)
            CANDLE_INTERVAL_SECONDS = 5
            max_steps_calculated = int(percentile_duration / CANDLE_INTERVAL_SECONDS)
            
            # Ensure a minimum number of steps
            max_steps = max(max_steps_calculated, 100) # e.g., minimum 100 steps
            
            logger.info(f"Dynamically calculated MAX_STEPS_PER_EPISODE based on {percentile_value}th percentile of training data lifespans: {max_steps} steps.")
        else:
            logger.warning("Could not calculate token lifespans from training data. Using fallback MAX_STEPS_PER_EPISODE.")
            max_steps = rl_config.MAX_STEPS_PER_EPISODE_FALLBACK
    else:
        logger.error("No training lifespans available to calculate MAX_STEPS_PER_EPISODE. Using fallback.")
        max_steps = rl_config.MAX_STEPS_PER_EPISODE_FALLBACK
    # --- END: Dynamic Calculation ---

    # --- Create Vectorized Environments ---
    logger.info("Creating RL Vectorized Environments...")
    train_env_raw: Optional[VecEnv] = None
    eval_env_raw: Optional[VecEnv] = None
    train_env: Optional[VecNormalize] = None
    eval_env: Optional[VecNormalize] = None


    try:
        VecEnvClass = SubprocVecEnv if rl_config.N_ENVS > 1 else DummyVecEnv

        # Create training environments, passing the dynamically calculated max_steps
        env_fns = [
            make_env_func(
                data_dict=training_data, 
                lifespan_dict=train_lifespans,
                snapshot_dict=train_snapshots,
                initial_capital=rl_config.RL_INITIAL_CAPITAL, 
                max_steps=max_steps, # Use the calculated value
                rank=i, 
                render_mode=render_mode
            ) for i in range(rl_config.N_ENVS)
        ]
        train_env_raw = VecEnvClass(env_fns)
        if render_mode is not None:
             train_env_raw.render_mode = render_mode
        logger.info(f"Created Training VecEnv ({VecEnvClass.__name__}) with {rl_config.N_ENVS} environments.")

        # Create evaluation environment with the same max_steps
        if eval_data and eval_lifespans:
            eval_env_fn = make_env_func(
                data_dict=eval_data, 
                lifespan_dict=eval_lifespans,
                snapshot_dict=eval_snapshots,
                initial_capital=rl_config.RL_INITIAL_CAPITAL, 
                max_steps=max_steps, # Use the same calculated value
                rank=100
            )
            eval_env_raw = DummyVecEnv([eval_env_fn])
            if render_mode is not None:
                 eval_env_raw.render_mode = render_mode
            logger.info("Created Evaluation VecEnv (DummyVecEnv).")
        else:
             eval_env_raw = None

        # --- Apply VecNormalize ---
        # If continuing, load stats. Otherwise, create new.
        if continue_from_model:
            vec_normalize_path = continue_from_model.replace(".zip", "_vecnormalize.pkl")
            if not os.path.exists(vec_normalize_path):
                 # Handle case where best model is in a subdirectory
                 base_dir = os.path.dirname(continue_from_model)
                 vec_normalize_path = os.path.join(base_dir, "best_vecnormalize.pkl")

            if os.path.exists(vec_normalize_path):
                logger.info(f"Loading VecNormalize stats from {vec_normalize_path}")
                train_env = VecNormalize.load(vec_normalize_path, train_env_raw)
            else:
                logger.warning(f"VecNormalize stats not found at {vec_normalize_path}. Creating new stats.")
                train_env = VecNormalize(train_env_raw, norm_obs=True, norm_reward=False, gamma=0.99)
        else:
            train_env = VecNormalize(train_env_raw, norm_obs=True, norm_reward=False, gamma=0.99)
        
        logger.info("Applied VecNormalize to training environment.")

        if eval_env_raw:
            eval_env = VecNormalize(eval_env_raw, training=False, norm_obs=True, norm_reward=False, gamma=0.99)
            eval_env.obs_rms = train_env.obs_rms
            eval_env.ret_rms = train_env.ret_rms
            eval_env.clip_obs = train_env.clip_obs
            eval_env.clip_reward = train_env.clip_reward
            logger.info("Applied VecNormalize to evaluation environment using training stats.")
        else:
            eval_env = None

    except Exception as e:
        logger.exception(f"Error creating vectorized environments: {e}")
        if train_env: train_env.close()
        elif train_env_raw: train_env_raw.close()
        if eval_env: eval_env.close()
        elif eval_env_raw: eval_env_raw.close()
        if db_client_global: await db_client_global.close()
        return

    # --- Configure Agent ---
    logger.info(f"Setting up RL Agent: {rl_config.RL_ALGORITHM}")
    algo_map = {"PPO": PPO, "SAC": SAC, "TD3": TD3}
    AgentClass = algo_map.get(rl_config.RL_ALGORITHM)

    if AgentClass is None:
        logger.critical(f"RL Algorithm '{rl_config.RL_ALGORITHM}' not supported.")
        if train_env: train_env.close()
        if eval_env: eval_env.close()
        if db_client_global: await db_client_global.close()
        return

    os.makedirs(rl_config.TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(rl_config.MODEL_SAVE_DIR, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"{rl_config.RL_ALGORITHM}_{run_timestamp}"
    log_path_tb = os.path.join(rl_config.TENSORBOARD_LOG_DIR, model_prefix)
    save_path_model = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
    save_path_vecnormalize = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl")
    best_model_save_dir = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best")

    sb3_file_logger = sb3_configure_logger(log_path_tb, ["stdout", "csv", "tensorboard"])

    device = 'cpu'
    logger.info(f"Using device: {device}")

    # --- Load or Create Model ---
    if continue_from_model:
        logger.info(f"Continuing training from model: {continue_from_model}")
        model = AgentClass.load(
            continue_from_model,
            env=train_env,
            device=device
        )
        
        # --- START: APPLY FINE-TUNING HYPERPARAMETERS TO LOADED MODEL ---
        # Get hyperparameters from the config file
        params = rl_config.PPO_HYPERPARAMS
        
        # Wrap tunable parameters in schedule functions to prevent 'float is not callable' TypeError
        model.learning_rate = get_schedule_fn(params["learning_rate"])
        model.clip_range = get_schedule_fn(params["clip_range"])
        
        # Directly set other tunable parameters
        model.gae_lambda = params["gae_lambda"]
        model.gamma = params["gamma"]
        model.ent_coef = params["ent_coef"]
        model.vf_coef = params["vf_coef"]
        model.max_grad_norm = params["max_grad_norm"]
        
        logger.info(f"Applied fine-tuning parameters to loaded model (gae_lambda={model.gae_lambda}, clip_range={params['clip_range']}, etc.).")
        # --- END: APPLY FINE-TUNING ---

    else:
        logger.info("Creating a new model for training.")
        # Combine base parameters with PPO-specific hyperparameters from config
        agent_params = {
            "policy": "MlpPolicy",
            "env": train_env,
            "policy_kwargs": rl_config.POLICY_KWARGS, # Use from config
            "verbose": 1,
            "device": device,
            "seed": 42,
            **rl_config.PPO_HYPERPARAMS # Unpack all PPO hyperparameters
        }
        model = AgentClass(**agent_params)
    
    model.set_logger(sb3_file_logger)

    # --- Setup Callbacks ---
    logger.info("Setting up Callbacks...")
    callbacks = []
    checkpoint_callback = CheckpointCallback(
        save_freq=max(rl_config.CHECKPOINT_FREQ // rl_config.N_ENVS, 1),
        save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_checkpoints"),
        name_prefix="rl_model",
        save_replay_buffer=True if rl_config.RL_ALGORITHM in ["SAC", "TD3"] else False,
        save_vecnormalize=True
    )
    callbacks.append(checkpoint_callback)

    if eval_env:
        save_vec_normalize_callback = SaveVecNormalizeCallback(
            save_path=os.path.join(best_model_save_dir, "best_vecnormalize.pkl")
        )
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=best_model_save_dir,
            log_path=best_model_save_dir,
            eval_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1),
            n_eval_episodes=rl_config.N_EVAL_EPISODES,
            deterministic=True,
            render=False, # Disable render during eval to speed it up
            verbose=1,
            callback_on_new_best=save_vec_normalize_callback
        )
        callbacks.append(eval_callback)
    else:
        logger.warning("EvalCallback disabled as evaluation environment is not available.")

    callbacks.append(TensorboardCallback())

    # --- Start Training ---
    logger.info(f"--- Starting RL Training ({rl_config.RL_ALGORITHM}) for {rl_config.TOTAL_TIMESTEPS} timesteps ---")
    start_train_time = time.time()
    training_successful = False
    try:
        model.learn(
            total_timesteps=rl_config.TOTAL_TIMESTEPS,
            callback=callbacks,
            log_interval=10,
            reset_num_timesteps=False if continue_from_model else True # Continue timestep count if loading model
        )
        training_successful = True
    except KeyboardInterrupt:
         logger.warning("Training interrupted by user (KeyboardInterrupt). Saving current model.")
    except Exception as learn_err:
        logger.exception(f"Error during model.learn(): {learn_err}")
    finally:
        # --- Save Final Model and Environment Statistics ---
        end_train_time = time.time()
        logger.info(f"--- Training loop finished. Duration: {end_train_time - start_train_time:.2f} seconds ---")

        try:
            model.save(save_path_model)
            logger.info(f"Final trained model saved to: {save_path_model}")

            if isinstance(train_env, VecNormalize):
                train_env.save(save_path_vecnormalize)
                logger.info(f"Final VecNormalize statistics saved to: {save_path_vecnormalize}")

            best_model_path = os.path.join(best_model_save_dir, "best_model.zip")
            best_vecnorm_path = os.path.join(best_model_save_dir, "best_vecnormalize.pkl")
            if eval_env and os.path.exists(best_model_path) and training_successful:
                logger.info(f"Best model saved during evaluation: {best_model_path}")
                if os.path.exists(best_vecnorm_path):
                    logger.info(f"Corresponding VecNormalize stats saved: {best_vecnorm_path}")
                else:
                    logger.warning(f"Best model saved, but VecNormalize stats file missing: {best_vecnorm_path}")

        except Exception as save_err:
             logger.error(f"Failed to save final model or VecNormalize stats: {save_err}")

        if training_successful and not continue_from_model: # Only run on a full new run
            logger.info("Performing post-training feature importance analysis...")
            analyze_feature_importance(model, train_env)

        # --- Cleanup ---
        logger.info("Closing environments...")
        try:
            if train_env: train_env.close()
            if eval_env: eval_env.close()
        except Exception as close_err:
            logger.error(f"Error closing environments: {close_err}")

        if db_client_global: await db_client_global.close()
        logger.info("--- RL Agent Training Finished ---")


# --- Entry Point Guard ---
if __name__ == "__main__":
    # --- Add Argument Parser ---
    parser = argparse.ArgumentParser(description="RL Agent Trainer")
    parser.add_argument(
        "--continue-from-model",
        type=str,
        default=None,
        help="Path to a saved .zip model file to continue training from."
    )
    args = parser.parse_args()
    # --- End Argument Parser ---

    if os.name == 'nt':
         from multiprocessing import freeze_support
         freeze_support()

    try:
        asyncio.run(train_rl_agent(render_mode=None, continue_from_model=args.continue_from_model))
    except Exception as main_err:
         logger.critical(f"Critical error in RL trainer entry point: {main_err}", exc_info=True)

```

---

