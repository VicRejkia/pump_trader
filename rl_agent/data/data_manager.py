# rl_agent/data/data_manager.py
"""
Handles fetching, caching, preprocessing, and providing data for the RL environment.
This module is the bridge between the PostgreSQL database and the simulation.
"""
from typing import Dict, Optional, Tuple
import pandas as pd
from datetime import datetime

# Project-specific imports
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from database_handler import DatabaseClient
from rl_agent.feature_engineering.features import calculate_all_features
from rl_agent.data.cache_manager import CacheManager

class DataManager:
    """
    Manages the data lifecycle for RL training and evaluation.
    - Manages caching of processed data.
    - Fetches raw data from the database for a given time period if cache is invalid.
    - Orchestrates feature engineering on a per-token basis.
    - Combines token data into a single chronological DataFrame for the Gym environment.
    """

    def __init__(self, db_client: DatabaseClient, start_date: datetime, end_date: datetime, min_trade_count: int = 100):
        self.db_client = db_client
        self.start_date = start_date
        self.end_date = end_date
        self.min_trade_count = min_trade_count
        self.full_data: Optional[pd.DataFrame] = None
        self._iterator = None
        self.cache_manager = CacheManager(self.db_client, self.start_date, self.end_date)

    async def load_and_prepare_data(self) -> bool:
        """
        Loads data from cache if valid, otherwise fetches from DB, runs feature
        engineering, saves to cache, and prepares a unified DataFrame.

        Returns:
            True if data was loaded successfully, False otherwise.
        """
        token_data_dict: Optional[Dict[str, pd.DataFrame]] = None

        if await self.cache_manager.is_cache_valid():
            cached_content = self.cache_manager.load_from_cache()
            token_data_dict = cached_content.get('token_data')
        else:
            logger.info(f"No valid cache. Fetching raw data for RL from {self.start_date} to {self.end_date}...")
            raw_data = await self.db_client.get_raw_data_for_rl(
                start_date=self.start_date,
                end_date=self.end_date,
                min_trade_count=self.min_trade_count
            )

            if raw_data is None:
                logger.error("Failed to fetch raw data from the database.")
                return False

            trades_df, rugcheck_df, token_info_df, dexscreener_df = raw_data
            
            # --- Per-Token Feature Engineering ---
            token_data_dict = await calculate_all_features(
                trades_df, rugcheck_df, token_info_df, dexscreener_df
            )
            
            if token_data_dict:
                # --- Save the newly processed data to cache ---
                fingerprint = await self.cache_manager.generate_fingerprint()
                self.cache_manager.save_to_cache(fingerprint, {'token_data': token_data_dict})
        
        if not token_data_dict:
            logger.error("Data preparation resulted in no processable tokens.")
            return False

        # --- Combine token-specific DataFrames into one, sorted by time ---
        # This unified DataFrame is what the environment will iterate over.
        logger.info(f"Combining data for {len(token_data_dict)} tokens into a single timeline...")
        self.full_data = pd.concat(token_data_dict.values(), ignore_index=False)
        self.full_data.sort_index(inplace=True)

        # Prepare the iterator for the environment
        self._iterator = self.full_data.iterrows()
        logger.info(f"Data preparation complete. Total time steps for environment: {len(self.full_data)}")
        return True

    def __iter__(self):
        self.reset()
        return self

    def __next__(self) -> Optional[Tuple[pd.Timestamp, pd.Series]]:
        try:
            return next(self._iterator)
        except StopIteration:
            return None

    def reset(self) -> None:
        """Resets the data iterator to the beginning."""
        if self.full_data is not None:
            self._iterator = self.full_data.iterrows()
        else:
            self._iterator = iter([])

    def get_full_data(self) -> pd.DataFrame:
        """Returns the entire prepared and combined DataFrame."""
        return self.full_data