# scripts/scout_data_preparation.py
"""
Data preparation script for the Scout (Decision Gate) RL Agent.

This script fetches raw trade, rugcheck, and token info data from the database,
processes it into a feature-rich OHLCV format, generates potential decision points
(e.g., at 1, 2, and 5 minutes after token creation), and saves the processed
dataframes for the training environment.
"""

import os
import pandas as pd
import numpy as np
import asyncio
from tqdm import tqdm

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the new centralized config
from config import rl_config as cfg
from bot_logger import setup_logging, logger
from database_handler import DatabaseClient

async def generate_feature_rich_ohlcv(
    mint: str,
    mint_trades: pd.DataFrame,
    rugcheck_df: pd.DataFrame,
    token_info_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Takes raw data for a SINGLE token and processes it into a feature-rich
    OHLCV format, correctly handling time-aware joins.
    """
    mint_trades = mint_trades.set_index('timestamp').sort_index()

    # Resample to 5s OHLCV
    resampler = mint_trades.resample('5s')
    ohlc = resampler['price_sol'].ohlc()
    volume = resampler['volume_usd'].sum()
    market_cap = resampler['market_cap_sol'].last()
    
    df = pd.concat([ohlc, volume, market_cap], axis=1)
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'marketCapSol']
    
    # Using modern assignment to avoid SettingWithCopyWarning
    df = df.interpolate(method='time')
    df.loc[:, 'Volume'] = df['Volume'].fillna(0)
    df.dropna(subset=['Close'], inplace=True)

    # Calculate Volatility
    log_returns = np.log(df['Close'] / df['Close'].shift(1))
    df['volatility'] = log_returns.rolling(window=12*5, min_periods=12).std() * np.sqrt(12*5)
    df['volatility'] = df['volatility'].fillna(0)

    # Time-aware merge for scores
    mint_rugcheck = rugcheck_df[rugcheck_df['mint'] == mint].set_index('timestamp').sort_index().drop_duplicates()
    if not mint_rugcheck.empty:
        df = pd.merge_asof(df, mint_rugcheck[['rugcheck_score']], left_index=True, right_index=True, direction='backward')
    else:
        df['rugcheck_score'] = np.nan

    mint_info = token_info_df[token_info_df['mint'] == mint]
    if not mint_info.empty and 'socials_last_checked' in mint_info.columns and pd.notna(mint_info['socials_last_checked'].iloc[0]):
        socials_event = pd.DataFrame({'socials_score': [mint_info['socials_score'].iloc[0]]}, index=[mint_info['socials_last_checked'].iloc[0]])
        df = pd.merge_asof(df, socials_event, left_index=True, right_index=True, direction='backward')
    else:
        df['socials_score'] = np.nan
        
    if not mint_info.empty and 'token_creation_time' in mint_info.columns:
        df['token_creation_time'] = mint_info['token_creation_time'].iloc[0]
    else:
        df['token_creation_time'] = df.index.min()

    return df

async def prepare_scout_data():
    """Main function to run the data preparation pipeline for the Scout agent."""
    setup_logging(logger_name="rl_scout_data_prep")
    logger.info("--- Starting Data Preparation for RL Scout Environment ---")
    
    db_client = DatabaseClient()
    await db_client.connect()

    try:
        raw_data = await db_client.get_raw_data_for_rl(
            cfg.DATA_WINDOW_START_TS, cfg.DATA_WINDOW_END_TS, cfg.MIN_TRADES_FOR_TRAINING
        )
        if raw_data is None:
            logger.critical("Failed to fetch raw data. Exiting.")
            return

        trades_df, rugcheck_df, token_info_df, dexscreener_df = raw_data
        
        # Convert data types for all DFs immediately after loading
        for df in [trades_df, rugcheck_df, token_info_df, dexscreener_df]:
            if not df.empty:
                for col in df.columns:
                    if 'timestamp' in col or 'last_checked' in col or 'creation_time' in col:
                        df[col] = pd.to_datetime(df[col], utc=True, errors='coerce')
                    numeric_cols = ['price_sol', 'market_cap_sol', 'volume_usd', 'score', 'socials_score', 'liquidity_usd', 'buys_m5', 'sells_m5', 'volume_m5', 'price_change_m5']
                    if col in numeric_cols:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

        all_feature_rich_data = {}
        mints_to_process = trades_df['mint'].unique()
        
        # Process tokens one by one to keep memory usage low
        for mint in tqdm(mints_to_process, desc="Processing Tokens"):
            mint_trades = trades_df[trades_df['mint'] == mint]
            if mint_trades.empty:
                continue
            processed_df = await generate_feature_rich_ohlcv(mint, mint_trades, rugcheck_df, token_info_df)
            all_feature_rich_data[mint] = processed_df

        decision_points = []
        for mint, df in tqdm(all_feature_rich_data.items(), desc="Generating Decision Points"):
            if df.empty or pd.isna(df['token_creation_time'].iloc[0]):
                continue

            # Generate Pump.fun launch decision points
            first_trade_ts = df.index.min()
            for minutes in cfg.ScoutConfig.DECISION_POINTS_MINUTES:
                ts = df['token_creation_time'].iloc[0] + pd.Timedelta(minutes=minutes)
                
                if ts < first_trade_ts or ts > df.index.max():
                    continue
                
                snapshot_ts = df.index.asof(ts)
                if pd.isna(snapshot_ts): continue
                snapshot = df.loc[snapshot_ts]
                past_minute_data = df.loc[ts - pd.Timedelta(minutes=1):ts]
                
                features = {
                    'timestamp': ts, 'mint': mint, 'is_migrated': 0,
                    'initial_market_cap_sol': df['marketCapSol'].iloc[0],
                    'volume_first_minute_sol': past_minute_data['Volume'].sum(),
                    'volatility_first_minute': past_minute_data['volatility'].mean(),
                    'buy_sell_ratio_first_minute': 1.0,
                    'time_since_creation_seconds': (ts - df['token_creation_time'].iloc[0]).total_seconds(),
                    'dex_liquidity_usd': 0, 'dex_volume_m5': 0, 'dex_price_change_m5': 0, 'dex_buys_m5': 0, 'dex_sells_m5': 0,
                    'rugcheck_score_is_real': 0 if pd.isna(snapshot['rugcheck_score']) else 1,
                    'socials_score_is_real': 0 if pd.isna(snapshot['socials_score']) else 1,
                    'rugcheck_score': snapshot['rugcheck_score'] if pd.notna(snapshot['rugcheck_score']) else 10000,
                    'socials_score': snapshot['socials_score'] if pd.notna(snapshot['socials_score']) else 100,
                    'creator_token_count': 1
                }
                decision_points.append(features)

            # Generate DexScreener breakout points
            mint_dex_data = dexscreener_df[dexscreener_df['mint'] == mint]
            if not mint_dex_data.empty:
                high_vol_timestamps = mint_dex_data[mint_dex_data['volume_m5'] > 10000]['timestamp']
                for ts in high_vol_timestamps:
                    if ts in df.index:
                        dex_snapshot = mint_dex_data.set_index('timestamp').asof(ts)
                        ohlcv_snapshot = df.asof(ts)
                        features = {
                            'timestamp': ts, 'mint': mint, 'is_migrated': 1,
                            'initial_market_cap_sol': 0, 'volume_first_minute_sol': 0, 'volatility_first_minute': 0, 'buy_sell_ratio_first_minute': 0,
                            'time_since_creation_seconds': (ts - ohlcv_snapshot['token_creation_time']).total_seconds(),
                            'dex_liquidity_usd': dex_snapshot['liquidity_usd'], 'dex_volume_m5': dex_snapshot['volume_m5'],
                            'dex_price_change_m5': dex_snapshot['price_change_m5'], 'dex_buys_m5': dex_snapshot['buys_m5'], 'dex_sells_m5': dex_snapshot['sells_m5'],
                            'rugcheck_score_is_real': 0 if pd.isna(ohlcv_snapshot['rugcheck_score']) else 1,
                            'socials_score_is_real': 0 if pd.isna(ohlcv_snapshot['socials_score']) else 1,
                            'rugcheck_score': ohlcv_snapshot['rugcheck_score'] if pd.notna(ohlcv_snapshot['rugcheck_score']) else 10000,
                            'socials_score': ohlcv_snapshot['socials_score'] if pd.notna(ohlcv_snapshot['socials_score']) else 100,
                            'creator_token_count': 1
                        }
                        decision_points.append(features)

        if not decision_points:
            logger.critical("No decision points could be generated.")
            return
        
        decision_df = pd.DataFrame(decision_points)
        os.makedirs(os.path.dirname(cfg.SCOUT_PROCESSED_DATA_PATH), exist_ok=True)
        decision_df.to_csv(cfg.SCOUT_PROCESSED_DATA_PATH, index=False)
        
        ohlcv_dir = os.path.join(os.path.dirname(cfg.SCOUT_PROCESSED_DATA_PATH), "ohlcv_data")
        os.makedirs(ohlcv_dir, exist_ok=True)
        for mint, df in all_feature_rich_data.items():
            df.to_parquet(os.path.join(ohlcv_dir, f"{mint}.parquet"))

        logger.info(f"--- Scout data preparation complete. Generated {len(decision_df)} decision points. ---")

    finally:
        await db_client.close()

def load_prepared_scout_data():
    """Loads the processed decision data and OHLCV files for Scout training."""
    if not os.path.exists(cfg.SCOUT_PROCESSED_DATA_PATH):
        logger.error(f"Processed data file not found: {cfg.SCOUT_PROCESSED_DATA_PATH}")
        return None, None
        
    decision_df = pd.read_csv(cfg.SCOUT_PROCESSED_DATA_PATH, parse_dates=['timestamp'])
    
    ohlcv_dir = os.path.join(os.path.dirname(cfg.SCOUT_PROCESSED_DATA_PATH), "ohlcv_data")
    all_token_data = {}
    if os.path.exists(ohlcv_dir):
        for filename in tqdm(os.listdir(ohlcv_dir), desc="Loading OHLCV Data"):
            if filename.endswith(".parquet"):
                mint = filename.replace(".parquet", "")
                all_token_data[mint] = pd.read_parquet(os.path.join(ohlcv_dir, filename))
            
    return decision_df, all_token_data

if __name__ == "__main__":
    asyncio.run(prepare_scout_data())
