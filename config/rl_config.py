# config/rl_config.py
"""
Dedicated configuration constants and settings for the Reinforcement Learning Agent.
This file centralizes all parameters into a structured dictionary for different
operational modes like tuning, training, and fine-tuning.
"""
import torch as th

# --- NEW: Feature Store Configuration ---
# Defines the location and version of the pre-computed Parquet feature data lake.
RL_FEATURE_STORE_PATH = "data/rl_feature_store"
RL_FEATURE_STORE_VERSION = "0.1"

# --- NEW: Feature Group Definitions ---
# Logically groups features for modular storage and loading in the ETL pipeline.
# This dictionary drives how data is partitioned in the feature store.
FEATURE_GROUPS = {
    'base_ohlcv': [
        'Open', 'High', 'Low', 'Close', 'volume_usd', 'buy_volume_usd',
        'sell_volume_usd', 'market_cap_sol', 'tx_buy_count', 'tx_sell_count', 'sol_price_avg'
    ],
    'static_and_age': [
        'rugcheck_score', 'socials_score', 'token_age_seconds'
    ],
    'price_change_and_volatility': [
        'price_change_15s', 'price_change_30s', 'volatility_15s',
        'atr_7', 'atr_14', 'bollinger_width'
    ],
    'momentum_indicators': [
        'rsi_3', 'rsi_6', 'cci_20', 'macd', 'macd_signal',
        'macd_histogram', 'adx_15s'
    ],
    'volume_and_flow': [
        'volume_change_15s', 'buy_sell_ratio', 'buy_sell_ratio_15s',
        'tx_buy_count_15s', 'tx_sell_count_15s', 'tx_total_count_15s',
        'ad_line', 'obv'
    ],
    'bollinger_bands': [
        'bollinger_upper', 'bollinger_lower'
    ],
    'emas': [
        'ema_short', 'ema_long'
    ]
}

# --- Central Configuration Dictionary ---
RL_CONFIG = {
    "common": {
        # --- Hardware & Performance ---
        "DEVICE": "cuda" if th.cuda.is_available() else "cpu",

        # --- Training Data Configuration ---
        "DATA_START_DATE": "2025-06-26T00:00:00Z",
        "DATA_END_DATE": "2025-07-20T00:00:00Z",
        "MIN_TRADE_COUNT_FOR_DATASET": 50,

        # --- Caching and Data Splitting ---
        "CACHE_STRATEGY": "parquet",
        "DATA_SPLIT_RATIO": [0.8, 0.2],
        "DATA_SPLIT_RANDOM_SEED": 42,

        # --- Environment Configuration ---
        "ENV_INITIAL_BALANCE": 100.0,
        "ENV_MAX_CONCURRENT_POSITIONS": 5,
        "ENV_NUM_TOP_TOKENS_TO_OBSERVE": 10,
        "ENV_ACTION_BUY_THRESHOLD": 0.2,
        "ENV_ACTION_SELL_THRESHOLD": -0.2,
        "ENV_CAPITAL_PER_BUY_PERCENT": 0.95,
        "ENV_TIME_IN_POSITION_NORM_SECONDS": 28800.0, # 8 hours
        "ENV_EPS": 1e-9,  # Epsilon for safe division
        "ENV_MAX_STEPS_PER_EPISODE": 5000,
        "ENV_WARMUP_STEPS": 200,

        # --- Reward Function Configuration ---
        "REWARD_DENSE_WEIGHT": 1.0,
        "REWARD_SPARSE_WEIGHT": 0.2,
        "REWARD_PNL_WEIGHT": 0.5,
        "REWARD_RISK_WEIGHT": 0.2,
        "REWARD_POSITION_MANAGEMENT_WEIGHT": 0.2,
        "REWARD_EXECUTION_WEIGHT": 0.1,
        "MAX_EXPECTED_PNL_PER_TRADE_SOL": 1.0,

        # --- Feature Management ---
        "FEATURES_CONFIG": {
            'tx_sell_count': True,
            'market_cap_sol': True,
            'sol_price_avg': True,
            'price_change_15s': True,
            'price_change_30s': True,
            'volume_usd': True,
            'volume_change_15s': True,
            'volatility_15s': True,
            'buy_sell_ratio': True,
            'buy_sell_ratio_15s': True,
            'buy_volume_usd': True,
            'sell_volume_usd': True,
            'tx_buy_count_15s': True,
            'tx_sell_count_15s': True,
            'tx_total_count_15s': True,
            'rsi_3': True,
            'rsi_6': True,
            'atr_7': True,
            'atr_14': True,
            'cci_20': True,
            'ad_line': True,
            'macd': True,
            'macd_signal': True,
            'macd_histogram': True,
            'bollinger_upper': True,
            'bollinger_lower': True,
            'bollinger_width': True,
            'ema_short': True,
            'ema_long': True,
            'adx_15s': True,
            'obv': True,
            'rugcheck_score': True,
            'socials_score': True,
            'token_age_seconds': True
        }
    },
    "tune": {
        "N_CPU": 1,
        "DEVICE": "cuda",
        "PPO_TIMESTEPS_PER_TRIAL": 500_000,
        "OPTUNA_N_TRIALS": 30,
        "OPTUNA_TIMEOUT_SECONDS": 14400, # 4 hours
        "OPTUNA_PRUNER_N_WARMUP_STEPS": 5,
        "OPTUNA_PRUNER_N_MIN_TRIALS": 5,
    },
    "train": {
        "N_CPU": 3,
        "DEVICE": "cpu",
        "PPO_FINAL_MODEL_TIMESTEPS": 2_000_000,
        "PPO_EVAL_FREQ": 2048,
    },
    "finetune": {
        "N_CPU": 3,
        "DEVICE": "cpu",
        "PPO_FINAL_MODEL_TIMESTEPS": 500_000, # Shorter duration for fine-tuning
        "PPO_EVAL_FREQ": 2048,
    },
    "continue": {
        "N_CPU": 3,
        "DEVICE": "cpu",
        "PPO_FINAL_MODEL_TIMESTEPS": 1_000_000,
        "PPO_EVAL_FREQ": 2048,
    }
}

def get_config_for_mode(mode: str) -> dict:
    """Merges common config with mode-specific config."""
    if mode not in RL_CONFIG:
        raise ValueError(f"Unknown configuration mode: '{mode}'. Must be one of {list(RL_CONFIG.keys())}")

    # Start with a copy of the common configuration
    config = RL_CONFIG['common'].copy()
    # Update it with the mode-specific settings, overriding common ones if necessary
    config.update(RL_CONFIG[mode])
    return config

def get_active_features(config: dict) -> list[str]:
    """
    Reads the FEATURES_CONFIG dictionary from a given config
    and returns a list of feature names that are set to True.
    """
    features_config = config.get("FEATURES_CONFIG", {})
    return [feature for feature, is_active in features_config.items() if is_active]
