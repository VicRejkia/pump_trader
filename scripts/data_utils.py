# FILE: scripts/data_utils.py

import os
import pandas as pd
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, List
import json
import numpy as np
# Add the project root to the Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# To use the existing async DatabaseClient in a sync script, we run it in an event loop.
from database_handler import DatabaseClient
from utils import load_and_split_data
from trading_rl_agent import rl_config
from bot_logger import setup_logging, logger

def get_or_create_event_loop():
    """Gets the current event loop or creates a new one."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()

async def _load_data_async():
    """Async wrapper to connect to DB and call the data loading function."""
    db_client = DatabaseClient()
    await db_client.connect()
    
    try:
        loaded_results = await load_and_split_data(
            db_client,
            rl_config.DATA_WINDOW_START_TS,
            rl_config.DATA_WINDOW_END_TS,
            {"training": 0.7, "validation": 0.3} # Define split here
        )
        return loaded_results
    finally:
        await db_client.close()

def preprocess_and_save_data():
    """
    Main function to load, preprocess, and save data for RL training.
    
    - Loads data using the existing async data loader from the bot.
    - Normalizes features.
    - Saves the processed dataframes and metadata to disk.
    """
    setup_logging(logger_name="rl_data_prep")
    logger.info("--- Starting Data Preparation for RL Training ---")

    loop = get_or_create_event_loop()
    results = loop.run_until_complete(_load_data_async())
    
    if not results:
        logger.critical("Failed to load data from the database. Exiting.")
        return

    data_sets, token_lifespans, _ = results
    
    # --- Preprocessing Step (e.g., Normalization) ---
    # In a real scenario, you'd apply robust scaling (e.g., StandardScaler)
    # fitted on the training set only. For simplicity, we'll do basic normalization.
    for key, data_map in data_sets.items():
        logger.info(f"Processing '{key}' dataset with {len(data_map)} tokens...")
        for mint, df in data_map.items():
            # Example: Normalize volume and market cap
            df['Volume'] = np.log1p(df['Volume'])
            df['marketCapSol'] = np.log1p(df['marketCapSol'])
            # Identify only the numeric columns that should be filled.
            numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
            # Apply fillna(0) ONLY to the numeric columns, leaving datetimes alone.
            df[numeric_cols] = df[numeric_cols].fillna(0)
            data_sets[key][mint] = df

    # --- Save Processed Data ---
    output_dir = rl_config.PROCESSED_DATA_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    for key, data_map in data_sets.items():
        dataset_dir = os.path.join(output_dir, key)
        os.makedirs(dataset_dir, exist_ok=True)
        for mint, df in data_map.items():
            df.to_parquet(os.path.join(dataset_dir, f"{mint}.parquet"))
    
    # Save token lifespans metadata
    lifespans_serializable = {
        mint: {'start_ts': ts['start_ts'].isoformat(), 'end_ts': ts['end_ts'].isoformat()}
        for mint, ts in token_lifespans.items()
    }
    with open(os.path.join(output_dir, "token_lifespans.json"), 'w') as f:
        json.dump(lifespans_serializable, f)
        
    logger.info(f"--- Data preparation complete. Processed data saved to '{output_dir}' ---")

def load_processed_data(dataset_key: str) -> Optional[Dict[str, pd.DataFrame]]:
    """Loads preprocessed data for a specific dataset (train/validation)."""
    dataset_dir = os.path.join(rl_config.PROCESSED_DATA_DIR, dataset_key)
    if not os.path.exists(dataset_dir):
        logger.error(f"Processed data directory not found: {dataset_dir}")
        return None
        
    data_map = {}
    for filename in os.listdir(dataset_dir):
        if filename.endswith(".parquet"):
            mint = filename.replace(".parquet", "")
            try:
                df = pd.read_parquet(os.path.join(dataset_dir, filename))
                data_map[mint] = df
            except Exception as e:
                logger.error(f"Failed to load processed data for {mint}: {e}")
    
    if not data_map:
        logger.error(f"No data loaded from '{dataset_dir}'.")
        return None
        
    return data_map


if __name__ == "__main__":
    # This allows running the data prep script directly from the command line.
    preprocess_and_save_data()