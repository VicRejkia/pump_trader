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
from datetime import datetime

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the new centralized config
from config import rl_config as cfg
from bot_logger import setup_logging, logger
from database_handler import DatabaseClient
from rl_tools.cache_utils import CacheManager
# --- MODIFIED: Import the centralized feature engineering function ---
from rl_tools.feature_engineering import generate_feature_rich_ohlcv


async def prepare_scout_data(start_ts: datetime, end_ts: datetime, db_client: DatabaseClient):
    """
    Main function to run the data preparation pipeline for the Scout agent.
    It now saves OHLCV data as parquet files inside the cache directory.
    """
    logger.info("--- Starting Data Preparation for RL Scout Environment ---")

    try:
        raw_data = await db_client.get_raw_data_for_rl(
            start_ts, end_ts, cfg.MIN_TRADES_FOR_TRAINING
        )
        if raw_data is None:
            logger.critical("Failed to fetch raw data. Exiting.")
            return None, None

        trades_df, rugcheck_df, token_info_df, dexscreener_df = raw_data
        
        for df in [trades_df, rugcheck_df, token_info_df, dexscreener_df]:
            if not df.empty:
                for col in df.columns:
                    if 'timestamp' in col or 'last_checked' in col or 'creation_time' in col:
                        df[col] = pd.to_datetime(df[col], utc=True, errors='coerce')
                    numeric_cols = ['price_sol', 'market_cap_sol', 'volume_usd', 'score', 'socials_score', 'liquidity_usd', 'buys_m5', 'sells_m5', 'volume_m5', 'price_change_m5']
                    if col in numeric_cols:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

        decision_points = []
        mints_to_process = trades_df['mint'].unique()
        
        # This function returns the path to the directory where OHLCV files will be saved.
        cache_manager = CacheManager('scout', db_client, start_ts, end_ts)
        ohlcv_dir = cache_manager.get_ohlcv_dir()
        os.makedirs(ohlcv_dir, exist_ok=True)
        
        for mint in tqdm(mints_to_process, desc="Processing Tokens & Generating Decision Points"):
            mint_trades = trades_df[trades_df['mint'] == mint]
            if mint_trades.empty:
                continue
            
            # Use the imported feature engineering function
            df = generate_feature_rich_ohlcv(mint, mint_trades, rugcheck_df, token_info_df)
            if df.empty or ('token_creation_time' in df.columns and pd.isna(df['token_creation_time'].iloc[0])):
                continue
            
            # Save the processed OHLCV dataframe to the cache directory
            df.to_parquet(os.path.join(ohlcv_dir, f"{mint}.parquet"))
            
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
                    'timestamp': ts, 'mint': mint,
                    'initial_market_cap_sol': df['marketCapSol'].iloc[0] if not df.empty else 0,
                    'volume_first_minute_sol': past_minute_data['Volume'].sum(),
                    'volatility_first_minute': past_minute_data['volatility'].mean(),
                    'time_since_creation_seconds': (ts - df['token_creation_time'].iloc[0]).total_seconds(),
                    'rugcheck_score': snapshot['rugcheck_score'] if pd.notna(snapshot['rugcheck_score']) else 10000,
                    'socials_score': snapshot['socials_score'] if pd.notna(snapshot['socials_score']) else 100,
                    'creator_token_count': 1 # Placeholder, can be enriched later
                }
                decision_points.append(features)

        if not decision_points:
            logger.critical("No decision points could be generated.")
            return None, None
        
        decision_df = pd.DataFrame(decision_points)
        # Ensure observation features are present, fill with 0 if not
        for feature in cfg.ScoutConfig.OBSERVATION_FEATURES:
            if feature not in decision_df.columns:
                decision_df[feature] = 0
        decision_df.fillna(0, inplace=True)

        logger.info(f"--- Scout data preparation complete. Generated {len(decision_df)} decision points. ---")
        
        return decision_df, ohlcv_dir

    except Exception as e:
        logger.error(f"Error during Scout data preparation: {e}", exc_info=True)
        return None, None

def load_prepared_scout_data(start_ts: datetime, end_ts: datetime):
    """
    Loads the processed decision dataframe and gets the OHLCV data path from the managed cache.
    """
    # Instantiate the cache manager for the specific window to get the correct paths
    cache_manager = CacheManager('scout', db_client=None, start_ts=start_ts, end_ts=end_ts)
    
    if not os.path.exists(cache_manager.manifest_path):
        logger.error(f"Processed scout data cache not found for window {start_ts.date()} - {end_ts.date()}. Please run the training pipeline first.")
        return None, None

    cached_data = cache_manager.load_cache()
    decision_df = cached_data.get('decision_df')
    ohlcv_dir = cache_manager.get_ohlcv_dir()

    if decision_df is None:
        logger.error("Decision dataframe not found in cache.")
        return None, None
    if not os.path.isdir(ohlcv_dir):
        logger.error(f"OHLCV data directory not found at expected path: {ohlcv_dir}")
        return None, None

    return decision_df, ohlcv_dir

if __name__ == "__main__":
    # Example of how to run this script standalone for debugging
    async def run_standalone():
        setup_logging(logger_name="rl_scout_data_prep_standalone")
        db = DatabaseClient()
        await db.connect()
        window = cfg.DATA_WINDOWS[cfg.DEFAULT_DATA_WINDOW]
        await prepare_scout_data(window['start'], window['end'], db)
        await db.close()
    asyncio.run(run_standalone())