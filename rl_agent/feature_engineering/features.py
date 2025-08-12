# rl_agent/feature_engineering/features.py
"""
Contains all functions for calculating features for the RL agent's observation space.
This module transforms raw time-series data into a feature-rich DataFrame dictionary,
with one DataFrame per token.
"""
import pandas as pd
import numpy as np
import warnings
import pandas_ta as ta
from typing import Dict
from tqdm import tqdm

# Project-specific imports
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger

# Suppress known pandas warning
warnings.filterwarnings(
    "ignore",
    message="The 'grouped' keyword is deprecated and will be removed in a future version of pandas.",
    category=FutureWarning
)


def _calculate_pump_features(group: pd.DataFrame) -> pd.DataFrame:
    """Calculates time-series features for a single token's OHLCV data."""
    if group.empty:
        return pd.DataFrame()

    # Use 'Close' price from OHLCV for calculations
    price_col = 'Close'
    
    # --- Time-based windows ---
    window_15s = pd.Timedelta(seconds=15)
    window_30s = pd.Timedelta(seconds=30)
    
    # --- Rolling Price Change ---
    price_15s_ago = group[price_col].rolling(window_15s, closed='left').apply(lambda x: x.iloc[0], raw=False)
    group['price_change_15s'] = (group[price_col] / price_15s_ago - 1).replace([np.inf, -np.inf], np.nan)

    price_30s_ago = group[price_col].rolling(window_30s, closed='left').apply(lambda x: x.iloc[0], raw=False)
    group['price_change_30s'] = (group[price_col] / price_30s_ago - 1).replace([np.inf, -np.inf], np.nan)
    
    # --- Custom Volume Change ---
    rolling_vol_sum = group['volume_usd'].rolling(window=window_15s, closed='left').sum()
    previous_vol_sum = rolling_vol_sum.shift(1)
    epsilon = 1e-10  # Small constant to avoid division by zero
    group['volume_change_15s'] = np.where(
        previous_vol_sum > 0,
        (rolling_vol_sum - previous_vol_sum) / (previous_vol_sum + epsilon),
        np.where(rolling_vol_sum > 0, 1.0, 0.0)  # If previous=0 and current>0, set to 1.0; if both=0, set to 0.0
    )

    # --- Volatility ---
    log_returns = np.log(group[price_col] / group[price_col].shift(1))
    group['volatility_15s'] = log_returns.rolling(window=window_15s, closed='left').std()

    # --- Custom RSI Calculation (length=5) ---
    rsi_length = 5
    deltas = group[price_col].diff()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    ema_gains = gains.ewm(span=rsi_length, adjust=False).mean()
    ema_losses = losses.ewm(span=rsi_length, adjust=False).mean()
    rs = ema_gains / ema_losses
    group['short_term_rsi'] = np.where(
        ema_losses > 0,
        100 - 100 / (1 + rs),
        np.where(ema_gains > 0, 100.0, 50.0)  # If losses=0 and gains>0, RSI=100; if both=0, RSI=50 (neutral)
    )
    
    # --- Buy/Sell Ratio from -1.0 - 1.0 ---
    group['buy_sell_ratio'] = np.where(group['volume_usd'] > 0, (group['buy_volume_usd'] - group['sell_volume_usd']) / group['volume_usd'], 0.0)

    # Calculate buy and sell volume over the last 15 seconds
    buy_vol_15s = group['buy_volume_usd'].rolling(window=window_15s, closed='left').sum()
    sell_vol_15s = group['sell_volume_usd'].rolling(window=window_15s, closed='left').sum()
    total_vol_15s = buy_vol_15s + sell_vol_15s
    group['buy_sell_ratio_15s'] = np.where(total_vol_15s > 0, (buy_vol_15s - sell_vol_15s) / total_vol_15s, 0.0)

    # Sum tx_buy_count and tx_sell_count over 15s rolling window
    group['tx_buy_count_15s'] = group['tx_buy_count'].rolling(window=window_15s).sum()
    group['tx_sell_count_15s'] = group['tx_sell_count'].rolling(window=window_15s).sum()
    group['tx_total_count_15s'] = group['tx_buy_count_15s'] + group['tx_sell_count_15s']

    # --- MACD Calculation ---
    ema_fast = group[price_col].ewm(span=12, adjust=False).mean()
    ema_slow = group[price_col].ewm(span=26, adjust=False).mean()
    group['macd'] = ema_fast - ema_slow
    group['macd_signal'] = group['macd'].ewm(span=9, adjust=False).mean()
    group['macd_histogram'] = group['macd'] - group['macd_signal']

    # --- Bollinger Bands Calculation (20-period, 2 std) ---
    bb_window = 20
    rolling_mean = group[price_col].rolling(window=bb_window).mean()
    rolling_std = group[price_col].rolling(window=bb_window).std()
    group['bollinger_upper'] = rolling_mean + (rolling_std * 2)
    group['bollinger_lower'] = rolling_mean - (rolling_std * 2)
    group['bollinger_width'] = (group['bollinger_upper'] - group['bollinger_lower']) / rolling_mean

    # --- EMA Short (5-period) and Long (20-period) ---
    group['ema_short'] = group[price_col].ewm(span=5, adjust=False).mean()
    group['ema_long'] = group[price_col].ewm(span=20, adjust=False).mean()

    # --- ADX Calculation (15s window) ---
    # Calculate True Range (TR)
    high_low = group['High'] - group['Low']
    high_close_prev = abs(group['High'] - group['Close'].shift(1))
    low_close_prev = abs(group['Low'] - group['Close'].shift(1))
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    
    # Calculate Directional Movement (DM)
    up_move = group['High'] - group['High'].shift(1)
    down_move = group['Low'].shift(1) - group['Low']
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=group.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=group.index)
    
    # Smooth TR and DM over 15s window (convert time window to number of periods)
    freq = pd.infer_freq(group.index) or '1S'  # Default to 1-second if frequency inference fails
    periods_15s = int(window_15s / pd.Timedelta(freq))
    
    tr_smooth = tr.rolling(window=periods_15s, min_periods=1).mean()
    plus_di = 100 * plus_dm.rolling(window=periods_15s, min_periods=1).mean() / (tr_smooth + epsilon)
    minus_di = 100 * minus_dm.rolling(window=periods_15s, min_periods=1).mean() / (tr_smooth + epsilon)
    
    # Calculate DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + epsilon)
    group['adx_15s'] = dx.rolling(window=periods_15s, min_periods=1).mean()

    # --- On-Balance Volume (OBV) ---
    group['obv'] = np.where(
        group[price_col] > group[price_col].shift(1), group['volume_usd'],
        np.where(group[price_col] < group[price_col].shift(1), -group['volume_usd'], 0)
    ).cumsum()

    # Update feature columns to include new indicators
    feature_cols = [
        'price_change_15s', 'price_change_30s', 'volume_change_15s',
        'volatility_15s', 'buy_sell_ratio', 'buy_sell_ratio_15s', 'short_term_rsi',
        'tx_buy_count_15s', 'tx_sell_count_15s', 'tx_total_count_15s',
        'macd', 'macd_signal', 'macd_histogram',
        'bollinger_upper', 'bollinger_lower', 'bollinger_width',
        'ema_short', 'ema_long', 'adx_15s', 'obv'
    ]
    return group[feature_cols]


async def calculate_all_features(
    trades_df: pd.DataFrame,
    rugcheck_df: pd.DataFrame,
    token_info_df: pd.DataFrame,
    dexscreener_df: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """
    Main pipeline: Processes raw data into a dictionary of feature-rich
    DataFrames, one for each token (mint).
    """
    if trades_df.empty:
        logger.warning("Trades DataFrame is empty. Cannot perform feature engineering.")
        return {}

    # --- 1. Data Cleaning & Type Conversion ---
    for df, date_col in [(trades_df, 'timestamp'), (rugcheck_df, 'timestamp'), 
                         (token_info_df, 'token_creation_time'), (dexscreener_df, 'timestamp')]:
        if not df.empty and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')

    for col in ['price_sol', 'market_cap_sol', 'volume_usd', 'sol_price_usd']:
        if not trades_df.empty and col in trades_df.columns:
            trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')

    trades_df.dropna(subset=['timestamp', 'price_sol', 'volume_usd', 'mint'], inplace=True)

    # --- Create separate columns for buy and sell volume before aggregation ---
    trades_df['buy_volume_usd'] = trades_df.apply(lambda row: row['volume_usd'] if row['tx_type'] == 'buy' else 0, axis=1)
    trades_df['sell_volume_usd'] = trades_df.apply(lambda row: row['volume_usd'] if row['tx_type'] == 'sell' else 0, axis=1)

    trades_df['tx_buy_count'] = trades_df['tx_type'].apply(lambda x: 1 if x == 'buy' else 0)
    trades_df['tx_sell_count'] = trades_df['tx_type'].apply(lambda x: 1 if x == 'sell' else 0)

    processed_token_data = {}
    unique_mints = trades_df['mint'].unique()
    
    logger.info(f"Starting feature engineering for {len(unique_mints)} tokens...")

    for mint in tqdm(unique_mints, desc="Processing Tokens"):
        # --- 2. Isolate Data for a Single Token ---
        mint_trades = trades_df[trades_df['mint'] == mint].set_index('timestamp').sort_index()
        if mint_trades.empty:
            continue
            
        # --- 3. Resample to 5-Second OHLCV ---
        resampler = mint_trades.resample('5s')
        ohlcv = resampler['price_sol'].ohlc()
        # Sum total volume AND separated buy/sell volumes
        agg_dict = {
            'volume_usd': 'sum',
            'buy_volume_usd': 'sum',
            'sell_volume_usd': 'sum',
            'market_cap_sol': 'last',
            'tx_buy_count': 'sum', 
            'tx_sell_count': 'sum',
            'sol_price_usd': 'mean' 
        }
        aggregated_data = resampler.agg(agg_dict)
        
        mint_df = pd.concat([ohlcv, aggregated_data], axis=1)
        mint_df.columns = ['Open', 'High', 'Low', 'Close', 'volume_usd', 'buy_volume_usd', 'sell_volume_usd', 'market_cap_sol', 'tx_buy_count', 'tx_sell_count', 'sol_price_avg']
        
        mint_df.interpolate(method='time', inplace=True)
        mint_df[['volume_usd', 'buy_volume_usd', 'sell_volume_usd']] = mint_df[['volume_usd', 'buy_volume_usd', 'sell_volume_usd']].fillna(0)
        mint_df.dropna(subset=['Close'], inplace=True)

        if mint_df.empty:
            continue
            
        # --- 4. Calculate Time-Based Features ---
        pump_features = _calculate_pump_features(mint_df.copy())
        mint_df = mint_df.join(pump_features, how='left')

        # --- 5. Merge Time-Aware Rugcheck & Socials ---
        if not rugcheck_df.empty:
            mint_rugcheck = rugcheck_df[rugcheck_df['mint'] == mint].set_index('timestamp').sort_index()
            if not mint_rugcheck.empty:
                mint_df = pd.merge_asof(mint_df, mint_rugcheck[['rugcheck_score']], left_index=True, right_index=True, direction='backward')
            else:
                mint_df['rugcheck_score'] = np.nan
        
        # --- 6. Merge Static Info & Calculate Age ---
        if not token_info_df.empty:
            mint_info = token_info_df[token_info_df['mint'] == mint].iloc[0] if not token_info_df[token_info_df['mint'] == mint].empty else None
            if mint_info is not None:
                mint_df['socials_score'] = mint_info['socials_score']
                mint_df['token_creation_time'] = mint_info['token_creation_time']
                mint_df['token_age_seconds'] = (mint_df.index - mint_info['token_creation_time']).total_seconds()

        # --- 7. Final Cleanup and Normalization ---
        final_df = mint_df.copy()
        final_df['mint'] = mint
        
        # Fill NaNs and normalize scores
        final_df['rugcheck_score'] = final_df['rugcheck_score'].fillna(2500)
        final_df['socials_score'] = final_df['socials_score'].fillna(100)
        final_df.fillna(0, inplace=True)

        final_df['rugcheck_score'] = final_df['rugcheck_score'] / 2500.0
        final_df['socials_score'] = final_df['socials_score'] / 100.0

        processed_token_data[mint] = final_df

    logger.info(f"Finished feature engineering. Processed data for {len(processed_token_data)} tokens.")
    return processed_token_data