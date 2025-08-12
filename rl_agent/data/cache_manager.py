# rl_agent/data/cache_manager.py
"""
Utility for managing cached data preparation assets to avoid re-computation.
The cache is aware of the data window (start/end dates) to allow for
persistent, separate caches for different time periods.
"""
import os
import hashlib
import json
import pickle
import pandas as pd
from typing import Dict, Any
from datetime import datetime, timezone

# Project-specific imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from database_handler import DatabaseClient
import config.config as cfg

class CacheManager:
    """
    Handles the creation, validation, and loading of cached, feature-engineered
    token DataFrames for a specific data window.
    """
    def __init__(self, db_client: DatabaseClient, start_ts: datetime, end_ts: datetime):
        self.db_client = db_client
        self.start_ts = start_ts
        self.end_ts = end_ts

        # Create a unique directory name based on the date range
        date_str = f"{self.start_ts.strftime('%Y%m%d')}_{self.end_ts.strftime('%Y%m%d')}"
        # Store cache within the rl_agent/data directory
        self.cache_dir = os.path.join(project_root, "rl_agent", "data", "cache", date_str)
        
        self.manifest_path = os.path.join(self.cache_dir, "manifest.json")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _generate_config_fingerprint(self) -> str:
        """Generates a hash from the relevant rl_config parameters and the date window."""
        config_params = {
            'DATA_WINDOW_START_TS': str(self.start_ts),
            'DATA_WINDOW_END_TS': str(self.end_ts),
            # Add any other config parameters that affect data preparation
            'PRICE_SOURCE_METHOD': cfg.PRICE_SOURCE_METHOD,
            'PRICE_WINDOW_TYPE': cfg.PRICE_WINDOW_TYPE,
            'PRICE_AVG_TRADE_COUNT': cfg.PRICE_AVG_TRADE_COUNT,
        }
        
        config_str = json.dumps(config_params, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    async def _generate_db_state_fingerprint(self) -> str:
        """
        Generates a hash based on the metadata of relevant database tables
        within the configured date range.
        """
        if not self.db_client or not self.db_client.pool:
            logger.error("Database client not available for DB state fingerprinting.")
            return "db_error"

        # Check a representative view that combines underlying data sources
        table_to_check = 'v_unified_market_ticks_historical'
        metadata = {}
        
        async with self.db_client.pool.acquire() as conn:
            query = f"""
                SELECT COUNT(*) as row_count, MAX(timestamp) as max_ts
                FROM {table_to_check} WHERE timestamp >= $1 AND timestamp < $2
            """
            try:
                stats = await conn.fetchrow(query, self.start_ts, self.end_ts)
                metadata[table_to_check] = {'row_count': stats['row_count'], 'max_ts': str(stats['max_ts'])}
            except Exception as e:
                logger.warning(f"Could not get metadata for table {table_to_check}: {e}")
                metadata[table_to_check] = {}

        metadata_str = json.dumps(metadata, sort_keys=True)
        return hashlib.sha256(metadata_str.encode()).hexdigest()

    async def generate_fingerprint(self) -> str:
        """Combines config and DB fingerprints into a single master hash."""
        config_hash = self._generate_config_fingerprint()
        db_hash = await self._generate_db_state_fingerprint()
        combined = f"{config_hash}-{db_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def is_cache_valid(self) -> bool:
        """
        Checks if a valid cache exists by comparing fingerprints.
        """
        if not os.path.exists(self.manifest_path):
            logger.info(f"No cache manifest found for window {self.start_ts.date()} to {self.end_ts.date()}. Preparation is required.")
            return False

        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            
            stored_fingerprint = manifest.get('fingerprint')
            current_fingerprint = await self.generate_fingerprint()

            if stored_fingerprint == current_fingerprint:
                logger.info(f"Cache is valid for window {self.start_ts.date()} to {self.end_ts.date()}. Skipping data preparation.")
                return True
            else:
                logger.info(f"Cache is stale for window {self.start_ts.date()} to {self.end_ts.date()}. Re-running data preparation.")
                return False
        except Exception as e:
            logger.warning(f"Could not validate cache manifest: {e}. Re-running data preparation.")
            return False

    def save_to_cache(self, fingerprint: str, data_to_cache: Dict[str, Any]):
        """Saves the processed dataframes and the manifest file to the cache."""
        logger.info(f"Saving processed data to cache at {self.cache_dir}...")

        # --- FIX: Extract the actual data dictionary to save ---
        token_data_to_save = data_to_cache.get('token_data')
        if token_data_to_save is None:
            logger.error("Data to cache is missing the 'token_data' key. Aborting cache save.")
            return
        
        file_path = os.path.join(self.cache_dir, "token_data.pkl")
        with open(file_path, 'wb') as f:
            # --- FIX: Save only the dictionary of token DataFrames ---
            pickle.dump(token_data_to_save, f)
        
        manifest = {
            'fingerprint': fingerprint,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'file_keys': ['token_data'] # The key for the main data dictionary
        }
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)
        logger.info("Cache saved successfully.")

    def load_from_cache(self) -> Dict[str, Any]:
        """Loads all specified data from the cache."""
        logger.info(f"Loading data from cache at {self.cache_dir}...")
        try:
            file_path = os.path.join(self.cache_dir, "token_data.pkl")
            with open(file_path, 'rb') as f:
                # --- FIX: Load the pickled object directly ---
                loaded_token_data = pickle.load(f)
            
            # --- FIX: Wrap the loaded data in the expected dictionary structure ---
            cached_data = {'token_data': loaded_token_data}

            logger.info(f"Successfully loaded {len(cached_data.get('token_data', {}))} tokens from cache.")
            return cached_data
        except Exception as e:
            logger.error(f"Failed to load data from cache: {e}", exc_info=True)
            return {}