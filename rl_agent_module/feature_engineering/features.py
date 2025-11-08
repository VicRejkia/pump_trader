# rl_agent_module/feature_engineering/features.py
"""
Contains all functions for calculating features for the RL agent's observation space.
This module transforms raw time-series data into a feature-rich DataFrame dictionary,
with one DataFrame per token.
"""
import pandas as pd
import numpy as np
import warnings
from typing import Dict, List, Tuple
from tqdm import tqdm

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from config.rl_config import FEATURE_GROUPS, get_active_features

warnings.filterwarnings(
    "ignore",
    message="The 'grouped' keyword is deprecated and will be removed in a future version of pandas.",
    category=FutureWarning
)


def _calculate_pump_features(group: pd.DataFrame) -> pd.DataFrame:
    """Calculates time-series features for a single token's OHLCV data."""
    if group.empty:
        return pd.DataFrame()

    # Cache frequently used columns and constants
    close = group['Close']
    high = group['High']
    low = group['Low']
    volume_usd = group['volume_usd']
    buy_volume_usd = group['buy_volume_usd']
    sell_volume_usd = group['sell_volume_usd']
    
    # Constants
    window_15s = pd.Timedelta(seconds=15)
    window_30s = pd.Timedelta(seconds=30)
    epsilon = 1e-10
    
    # Pre-calculate common values
    close_shift1 = close.shift(1)
    
    # --- Rolling Price Change ---
    price_15s_ago = close.rolling(window_15s, closed='left').apply(lambda x: x.iloc[0], raw=False)
    price_change_15s = (close / price_15s_ago - 1).replace([np.inf, -np.inf], np.nan)

    price_30s_ago = close.rolling(window_30s, closed='left').apply(lambda x: x.iloc[0], raw=False)
    price_change_30s = (close / price_30s_ago - 1).replace([np.inf, -np.inf], np.nan)
    
    # --- Custom Volume Change ---
    rolling_vol_sum = volume_usd.rolling(window=window_15s, closed='left').sum()
    previous_vol_sum = rolling_vol_sum.shift(1)
    volume_change_15s = np.where(
        previous_vol_sum > 0,
        (rolling_vol_sum - previous_vol_sum) / (previous_vol_sum + epsilon),
        np.where(rolling_vol_sum > 0, 1.0, 0.0)
    )

    # --- Volatility ---
    log_returns = np.log(close / close_shift1)
    volatility_15s = log_returns.rolling(window=window_15s, closed='left').std()

    # --- Shared calculations for RSI ---
    deltas = close.diff()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    
    # RSI 3-period
    ema_gains_3 = gains.ewm(span=3, adjust=False).mean()
    ema_losses_3 = losses.ewm(span=3, adjust=False).mean()
    rs_3 = ema_gains_3 / ema_losses_3
    rsi_3 = np.where(
        ema_losses_3 > 0,
        100 - 100 / (1 + rs_3),
        np.where(ema_gains_3 > 0, 100.0, 50.0)
    )
    
    # RSI 6-period
    ema_gains_6 = gains.ewm(span=6, adjust=False).mean()
    ema_losses_6 = losses.ewm(span=6, adjust=False).mean()
    rs_6 = ema_gains_6 / ema_losses_6
    rsi_6 = np.where(
        ema_losses_6 > 0,
        100 - 100 / (1 + rs_6),
        np.where(ema_gains_6 > 0, 100.0, 50.0)
    )

    # --- True Range calculation (shared for ATR and ADX) ---
    high_low = high - low
    high_close_prev = abs(high - close_shift1)
    low_close_prev = abs(low - close_shift1)
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    
    # ATR calculations
    atr_14 = tr.ewm(span=14, adjust=False).mean()
    atr_7 = tr.ewm(span=7, adjust=False).mean()
    
    # --- CCI Calculation ---
    typical_price = (high + low + close) / 3
    typical_price_sma = typical_price.rolling(window=20).mean()
    mean_deviation = typical_price.rolling(window=20).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    )
    cci_20 = (typical_price - typical_price_sma) / (0.015 * mean_deviation + epsilon)

    # --- A/D Line Calculation ---
    high_low_safe = high - low + epsilon  # Avoid division by zero
    money_flow_multiplier = ((close - low) - (high - close)) / high_low_safe
    money_flow_volume = money_flow_multiplier * volume_usd
    ad_line = money_flow_volume.cumsum()

    # --- Buy/Sell Ratios ---
    volume_usd_safe = np.where(volume_usd > 0, volume_usd, epsilon)
    buy_sell_ratio = (buy_volume_usd - sell_volume_usd) / volume_usd_safe
    buy_sell_ratio = np.where(volume_usd > 0, buy_sell_ratio, 0.0)

    # 15s rolling buy/sell volumes
    buy_vol_15s = buy_volume_usd.rolling(window=window_15s, closed='left').sum()
    sell_vol_15s = sell_volume_usd.rolling(window=window_15s, closed='left').sum()
    total_vol_15s = buy_vol_15s + sell_vol_15s
    buy_sell_ratio_15s = np.where(total_vol_15s > 0, (buy_vol_15s - sell_vol_15s) / total_vol_15s, 0.0)

    # Transaction counts
    tx_buy_count_15s = group['tx_buy_count'].rolling(window=window_15s).sum()
    tx_sell_count_15s = group['tx_sell_count'].rolling(window=window_15s).sum()
    tx_total_count_15s = tx_buy_count_15s + tx_sell_count_15s

    # --- MACD Calculation ---
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_histogram = macd - macd_signal

    # --- Bollinger Bands ---
    rolling_mean_20 = close.rolling(window=20).mean()
    rolling_std_20 = close.rolling(window=20).std()
    bollinger_upper = rolling_mean_20 + (rolling_std_20 * 2)
    bollinger_lower = rolling_mean_20 - (rolling_std_20 * 2)
    bollinger_width = (bollinger_upper - bollinger_lower) / rolling_mean_20

    # --- EMA calculations ---
    ema_short = close.ewm(span=5, adjust=False).mean()
    ema_long = close.ewm(span=20, adjust=False).mean()

    # --- ADX Calculation ---
    high_shift1 = high.shift(1)
    low_shift1 = low.shift(1)
    
    up_move = high - high_shift1
    down_move = low_shift1 - low
    
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=group.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=group.index)
    
    periods_15s = 3
    tr_smooth = tr.rolling(window=periods_15s, min_periods=1).mean()
    plus_di = 100 * plus_dm.rolling(window=periods_15s, min_periods=1).mean() / (tr_smooth + epsilon)
    minus_di = 100 * minus_dm.rolling(window=periods_15s, min_periods=1).mean() / (tr_smooth + epsilon)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + epsilon)
    adx_15s = dx.rolling(window=periods_15s, min_periods=1).mean()

    # --- On-Balance Volume ---
    price_direction = np.where(close > close_shift1, volume_usd,
                              np.where(close < close_shift1, -volume_usd, 0))
    obv = price_direction.cumsum()

    # Construct result DataFrame efficiently using dictionary
    result_data = {
        'price_change_15s': price_change_15s,
        'price_change_30s': price_change_30s,
        'volume_change_15s': volume_change_15s,
        'volatility_15s': volatility_15s,
        'buy_sell_ratio': buy_sell_ratio,
        'buy_sell_ratio_15s': buy_sell_ratio_15s,
        'rsi_3': rsi_3,
        'rsi_6': rsi_6,
        'atr_7': atr_7,
        'atr_14': atr_14,
        'cci_20': cci_20,
        'ad_line': ad_line,
        'tx_buy_count_15s': tx_buy_count_15s,
        'tx_sell_count_15s': tx_sell_count_15s,
        'tx_total_count_15s': tx_total_count_15s,
        'macd': macd,
        'macd_signal': macd_signal,
        'macd_histogram': macd_histogram,
        'bollinger_upper': bollinger_upper,
        'bollinger_lower': bollinger_lower,
        'bollinger_width': bollinger_width,
        'ema_short': ema_short,
        'ema_long': ema_long,
        'adx_15s': adx_15s,
        'obv': obv
    }
    
    return pd.DataFrame(result_data, index=group.index)


async def calculate_all_features(
    trades_df: pd.DataFrame,
    rugcheck_df: pd.DataFrame,
    token_info_df: pd.DataFrame,
    dexscreener_df: pd.DataFrame
) -> Tuple[Dict[str, Dict[str, pd.DataFrame]], List[str]]:
    """
    Main pipeline: Processes raw data and returns a nested dictionary of
    feature group DataFrames, structured as {group_name: {mint: df}}.
    """
    if trades_df.empty:
        logger.warning("Trades DataFrame is empty. Cannot perform feature engineering.")
        return {}, []

    # --- 1. Data Cleaning & Type Conversion ---
    for df, date_col in [(trades_df, 'timestamp'), (rugcheck_df, 'timestamp'), 
                         (token_info_df, 'token_creation_time'), (dexscreener_df, 'timestamp')]:
        if not df.empty and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')

    for col in ['price_sol', 'market_cap_sol', 'volume_usd', 'sol_price_usd']:
        if not trades_df.empty and col in trades_df.columns:
            trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
        
    if not trades_df.empty and 'price_sol' in trades_df.columns:
        trades_df = trades_df[trades_df['price_sol'] > 0]
    trades_df.dropna(subset=['timestamp', 'price_sol', 'volume_usd', 'mint'], inplace=True)

    trades_df['buy_volume_usd'] = trades_df.apply(lambda row: row['volume_usd'] if row['tx_type'] == 'buy' else 0, axis=1)
    trades_df['sell_volume_usd'] = trades_df.apply(lambda row: row['volume_usd'] if row['tx_type'] == 'sell' else 0, axis=1)
    trades_df['tx_buy_count'] = trades_df['tx_type'].apply(lambda x: 1 if x == 'buy' else 0)
    trades_df['tx_sell_count'] = trades_df['tx_type'].apply(lambda x: 1 if x == 'sell' else 0)

    grouped_feature_data = {group_name: {} for group_name in FEATURE_GROUPS.keys()}
    unique_mints = trades_df['mint'].unique()
    
    logger.info(f"Starting feature engineering for {len(unique_mints)} tokens...")
    all_feature_columns = set()

    for mint in tqdm(unique_mints, desc="Processing Tokens"):
        mint_trades = trades_df[trades_df['mint'] == mint].set_index('timestamp').sort_index()
        if mint_trades.empty: continue
            
        resampler = mint_trades.resample('5s')
        ohlcv = resampler['price_sol'].ohlc()
        agg_dict = {
            'volume_usd': 'sum', 'buy_volume_usd': 'sum', 'sell_volume_usd': 'sum',
            'market_cap_sol': 'last', 'tx_buy_count': 'sum', 'tx_sell_count': 'sum',
            'sol_price_usd': 'mean' 
        }
        aggregated_data = resampler.agg(agg_dict)
        
        mint_df = pd.concat([ohlcv, aggregated_data], axis=1)
        mint_df.columns = ['Open', 'High', 'Low', 'Close', 'volume_usd', 'buy_volume_usd', 'sell_volume_usd', 'market_cap_sol', 'tx_buy_count', 'tx_sell_count', 'sol_price_avg']
        
        mint_df.interpolate(method='time', inplace=True)
        mint_df[['volume_usd', 'buy_volume_usd', 'sell_volume_usd']] = mint_df[['volume_usd', 'buy_volume_usd', 'sell_volume_usd']].fillna(0)
        mint_df.dropna(subset=['Close'], inplace=True)

        if mint_df.empty or len(mint_df) < 20: continue
            
        pump_features = _calculate_pump_features(mint_df.copy())
        mint_df = mint_df.join(pump_features, how='left')

        if not rugcheck_df.empty:
            mint_rugcheck = rugcheck_df[rugcheck_df['mint'] == mint].set_index('timestamp').sort_index()
            if not mint_rugcheck.empty:
                mint_df = pd.merge_asof(mint_df, mint_rugcheck[['rugcheck_score']], left_index=True, right_index=True, direction='backward')
            else: mint_df['rugcheck_score'] = np.nan
        
        if not token_info_df.empty:
            mint_info = token_info_df[token_info_df['mint'] == mint].iloc[0] if not token_info_df[token_info_df['mint'] == mint].empty else None
            if mint_info is not None:
                mint_df['socials_score'] = mint_info['socials_score']
                mint_df['token_creation_time'] = mint_info['token_creation_time']
                mint_df['token_age_seconds'] = (mint_df.index - mint_info['token_creation_time']).total_seconds()

        final_df = mint_df.copy()
        final_df['rugcheck_score'] = final_df['rugcheck_score'].fillna(2500) / 2500.0
        final_df['socials_score'] = final_df['socials_score'].fillna(100) / 100.0
        final_df.fillna(0, inplace=True)
        
        # *** CRITICAL FIX: Add mint as a column for identification later ***
        final_df['mint'] = mint
        all_feature_columns.update(final_df.columns)

        for group_name, features in FEATURE_GROUPS.items():
            group_cols = [f for f in features if f in final_df.columns]
            group_df = final_df[group_cols].copy()
            for col in group_df.columns: 
                group_df[col] = group_df[col].astype(np.float32) if pd.api.types.is_numeric_dtype(group_df[col]) else group_df[col]
            grouped_feature_data[group_name][mint] = group_df

    logger.info(f"Finished feature engineering for {len(unique_mints)} tokens into {len(FEATURE_GROUPS)} groups.")

    # Return the full list of generated columns
    return grouped_feature_data, sorted(list(all_feature_columns))