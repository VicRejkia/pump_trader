from datetime import datetime, timezone

# --- General & Data Configuration ---
DATA_WINDOW_START_TS: datetime = datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
DATA_WINDOW_END_TS: datetime = datetime(2025, 7, 19, 23, 59, 0, tzinfo=timezone.utc)
MIN_TRADES_FOR_TRAINING: int = 20
PROCESSED_DATA_PATH: str = "data/rl_processed_data/training_decisions.csv"

# --- Environment Configuration ---
INITIAL_CAPITAL: float = 0.5
MAX_STEPS_PER_EPISODE: int = 720
DECISION_FREQUENCY: str = '5s'

# --- Observation Space (Now includes flags for data availability) ---
OBSERVATION_FEATURES: list[str] = [
    # Pump.fun Launch Features
    'initial_market_cap_sol',
    'volume_first_minute_sol',
    'volatility_first_minute',
    'buy_sell_ratio_first_minute',
    'time_since_creation_seconds',
    
    # DexScreener Breakout Features
    'dex_liquidity_usd',
    'dex_volume_m5',
    'dex_price_change_m5',
    'dex_buys_m5',
    'dex_sells_m5',
    
    # Common Features
    'rugcheck_score',
    'socials_score',
    'creator_token_count',
    'is_migrated',
    
    # NEW: Flags to indicate if the scores are real or default penalties
    'rugcheck_score_is_real',
    'socials_score_is_real'
]
OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)

# --- Action Space ---
ACTION_SPACE_DIM: int = 2 # 0 = IGNORE, 1 = BUY

# --- Reward Function ---
TIME_PENALTY_PER_STEP: float = 0.0001

# --- Simulation Logic ---
SIM_INITIAL_STOP_LOSS_PERCENT: float = 40.0
SIM_FIRST_SELL_PERCENT: float = 35.0
SIM_FIRST_SELL_PROFIT_MARGIN: float = 70.0
SIM_TRAILING_STOP_LOSS_PERCENT: float = 10.0
SIM_SECOND_TAKE_PROFIT_PERCENT: float = 450.0

# --- Training Configuration ---
TOTAL_TIMESTEPS: int = 500_000
N_ENVS: int = 8
TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/"
MODEL_SAVE_DIR: str = "./rl_models/"
EVAL_FREQ: int = 10000
N_EVAL_EPISODES: int = 50

# --- PPO Hyperparameters ---
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
