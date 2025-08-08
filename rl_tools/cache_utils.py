# rl_tools/cache_utils.py
"""
Utility for managing cached data preparation assets to avoid re-computation.
The cache is now aware of the data window (start/end dates) to allow for
persistent, separate caches for different time periods (e.g., test vs. full).
"""
import os
import hashlib
import json
import pickle
import pandas as pd
from typing import Dict, Any
from datetime import datetime, timezone

from bot_logger import logger
from database_handler import DatabaseClient
from config import rl_config as cfg

class CacheManager:
    """
    Handles the creation, validation, and loading of cached data preparation steps
    for a specific data window.
    """
    def __init__(self, cache_name: str, db_client: DatabaseClient, start_ts: datetime, end_ts: datetime):
        self.cache_name = cache_name
        self.db_client = db_client
        self.start_ts = start_ts
        self.end_ts = end_ts
        
        # Create a unique directory name based on the date range
        date_str = f"{self.start_ts.strftime('%Y%m%d')}_{self.end_ts.strftime('%Y%m%d')}"
        self.cache_dir = os.path.join(cfg.PROCESSED_DATA_DIR, f"{cache_name}_cache", date_str)
        
        self.manifest_path = os.path.join(self.cache_dir, "manifest.json")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_ohlcv_dir(self):
        """Returns the specific directory for storing/finding OHLCV parquet files."""
        return os.path.join(self.cache_dir, "ohlcv_data")

    def _generate_config_fingerprint(self) -> str:
        """Generates a hash from the relevant rl_config parameters and the date window."""
        config_params = {
            # --- FIX: Fingerprint now includes the specific dates used ---
            'DATA_WINDOW_START_TS': str(self.start_ts),
            'DATA_WINDOW_END_TS': str(self.end_ts),
            # --- END FIX ---
            'MIN_TRADES_FOR_TRAINING': cfg.MIN_TRADES_FOR_TRAINING
        }
        if self.cache_name == 'scout':
            config_params['DECISION_POINTS_MINUTES'] = cfg.ScoutConfig.DECISION_POINTS_MINUTES
        elif self.cache_name == 'manager':
            config_params['SIM_INITIAL_STOP_LOSS_PERCENT'] = cfg.ScoutConfig.SIM_INITIAL_STOP_LOSS_PERCENT
            config_params['SIM_FIRST_SELL_PROFIT_MARGIN'] = cfg.ScoutConfig.SIM_FIRST_SELL_PROFIT_MARGIN
            config_params['MANAGER_DATA_EXTENSION_MINUTES'] = cfg.ManagerConfig.MANAGER_DATA_EXTENSION_MINUTES
        
        config_str = json.dumps(config_params, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    async def _generate_db_state_fingerprint(self) -> str:
        """
        Generates a hash based on the metadata of relevant database tables
        within the configured date range.
        """
        tables_to_check = ['v_trades', 'v_tokens', 'v_rugcheck', 'v_dexscreener_data']
        metadata = {}
        
        if not self.db_client or not self.db_client.pool:
            logger.error("Database client not available for DB state fingerprinting.")
            return "db_error"

        async with self.db_client.pool.acquire() as conn:
            for table in tables_to_check:
                ts_col = 'timestamp'
                # --- FIX: Query now uses the instance's specific start and end dates ---
                query = f"""
                    SELECT COUNT(*) as row_count, MAX({ts_col}) as max_ts
                    FROM {table} WHERE {ts_col} >= $1 AND {ts_col} < $2
                """
                try:
                    stats = await conn.fetchrow(query, self.start_ts, self.end_ts)
                    metadata[table] = {'row_count': stats['row_count'], 'max_ts': str(stats['max_ts'])}
                except Exception as e:
                    logger.warning(f"Could not get metadata for table {table}: {e}")
                    metadata[table] = {}
        # --- END FIX ---
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
        Checks if a valid cache exists for the specific data window by comparing
        the current fingerprint with the one stored in the manifest.
        """
        if not os.path.exists(self.manifest_path):
            logger.info(f"[{self.cache_name.upper()}] No cache manifest found for window {self.start_ts.date()} to {self.end_ts.date()}. Preparation is required.")
            return False

        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            
            stored_fingerprint = manifest.get('fingerprint')
            current_fingerprint = await self.generate_fingerprint()

            if stored_fingerprint == current_fingerprint:
                logger.info(f"[{self.cache_name.upper()}] Cache is valid for window {self.start_ts.date()} to {self.end_ts.date()}. Skipping data preparation.")
                return True
            else:
                logger.info(f"[{self.cache_name.upper()}] Cache is stale for window {self.start_ts.date()} to {self.end_ts.date()}. Re-running data preparation.")
                return False
        except Exception as e:
            logger.warning(f"[{self.cache_name.upper()}] Could not validate cache manifest: {e}. Re-running data preparation.")
            return False

    def save_cache(self, fingerprint: str, **kwargs: Any):
        """Saves the processed dataframes and the manifest file to the date-specific cache."""
        logger.info(f"[{self.cache_name.upper()}] Saving processed data to cache at {self.cache_dir}...")
        for name, data in kwargs.items():
            file_path = os.path.join(self.cache_dir, f"{name}.pkl")
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
        
        manifest = {
            'fingerprint': fingerprint,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'file_keys': list(kwargs.keys())
        }
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)
        logger.info(f"[{self.cache_name.upper()}] Cache saved successfully.")

    def load_cache(self) -> Dict[str, Any]:
        """Loads all specified data from the date-specific cache."""
        logger.info(f"[{self.cache_name.upper()}] Loading data from cache at {self.cache_dir}...")
        cached_data = {}
        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            
            file_keys = manifest.get('file_keys', [])
            for key in file_keys:
                file_path = os.path.join(self.cache_dir, f"{key}.pkl")
                with open(file_path, 'rb') as f:
                    cached_data[key] = pickle.load(f)
            
            logger.info(f"[{self.cache_name.upper()}] Successfully loaded {len(cached_data)} files from cache.")
            return cached_data
        except Exception as e:
            logger.error(f"[{self.cache_name.upper()}] Failed to load data from cache: {e}", exc_info=True)
            return {}