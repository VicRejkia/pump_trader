# rl_agent/data/cache_manager.py
"""
Utility for managing cached data preparation assets to avoid re-computation.
The cache is aware of the data window (start/end dates) and can use
different storage strategies (single pickle vs. multi-file parquet).
"""
import os
import hashlib
import json
import pickle
import time
import pandas as pd
from typing import Dict, Any
from datetime import datetime, timezone
from tqdm import tqdm 

# Project-specific imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from database_handler import DatabaseClient
import config.rl_config as rl_cfg

class CacheManager:
    """
    Handles creation, validation, and loading of cached data using a configurable strategy.
    It measures performance and storage usage for comparison.
    """
    def __init__(self, db_client: DatabaseClient, start_ts: datetime, end_ts: datetime, verbose: bool = True):
        self.db_client = db_client
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.strategy = rl_cfg.CACHE_STRATEGY.lower() # 'pickle' or 'parquet'

        date_str = f"{self.start_ts.strftime('%Y%m%d')}_{self.end_ts.strftime('%Y%m%d')}"
        self.cache_dir = os.path.join(project_root, "rl_agent", "data", "cache", date_str)
        self.manifest_path = os.path.join(self.cache_dir, "manifest.json")

        self.verbose = verbose
        
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _generate_fingerprint(self) -> str:
        """Generates a hash from relevant config params to detect changes."""
        config_params = {
            'DATA_START_DATE': rl_cfg.DATA_START_DATE,
            'DATA_END_DATE': rl_cfg.DATA_END_DATE,
            'MIN_TRADE_COUNT_FOR_DATASET': rl_cfg.MIN_TRADE_COUNT_FOR_DATASET,
            'DATA_SPLIT_RATIO': rl_cfg.DATA_SPLIT_RATIO,
            'DATA_SPLIT_RANDOM_SEED': rl_cfg.DATA_SPLIT_RANDOM_SEED,
        }
        config_str = json.dumps(config_params, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    async def is_cache_valid(self, verbose: bool = True) -> bool:
        """Checks if a valid cache exists by comparing fingerprints."""
        if not os.path.exists(self.manifest_path):
            if (verbose + self.verbose) == 2:
                logger.info(f"No cache manifest found for window. Preparation is required.")
            return False

        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            
            stored_fingerprint = manifest.get('fingerprint')
            current_fingerprint = self._generate_fingerprint()

            stored_strategy = manifest.get('strategy', 'pickle')
            if stored_strategy != self.strategy:
                if (verbose + self.verbose) == 2:
                    logger.info(f"Cache strategy changed from '{stored_strategy}' to '{self.strategy}'. Re-caching is required.")
                return False

            if stored_fingerprint == current_fingerprint:
                if (verbose + self.verbose) == 2:
                    logger.info(f"Cache is valid (Strategy: {self.strategy}). Skipping data preparation.")
                return True
            else:
                if (verbose + self.verbose) == 2:
                    logger.info("Config fingerprint mismatch. Cache is stale. Re-running data preparation.")
                return False
        except Exception as e:
            if (verbose + self.verbose) == 2:
                logger.warning(f"Could not validate cache manifest: {e}. Re-running data preparation.")
            return False

    def save_to_cache(self, fingerprint: str, data_to_cache: Dict[str, Any], verbose: bool = True):
        """Saves the processed dataframes and manifest using the configured strategy."""
        if (verbose + self.verbose) == 2:
            logger.info(f"Saving data to cache using '{self.strategy}' strategy...")
        start_time = time.time()

        if self.strategy == 'pickle':
            self._save_as_pickle(data_to_cache, verbose)
        elif self.strategy == 'parquet':
            self._save_as_parquet(data_to_cache, verbose=verbose)
        else:
            raise ValueError(f"Unknown cache strategy: {self.strategy}")

        end_time = time.time()
        if (verbose + self.verbose) == 2:
            logger.info(f"Cache save operation took {end_time - start_time:.2f} seconds.")

        manifest = {
            'fingerprint': fingerprint,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'strategy': self.strategy,
            'file_keys': list(data_to_cache.keys())
        }
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)

    def load_from_cache(self, verbose: bool = True) -> Dict[str, Any]:
        """Loads data from the cache using the configured strategy."""
        if (verbose + self.verbose) == 2:
            logger.info(f"Loading data from cache using '{self.strategy}' strategy...")
        start_time = time.time()
        
        cached_data = {}
        if self.strategy == 'pickle':
            cached_data = self._load_from_pickle(verbose)
        elif self.strategy == 'parquet':
            cached_data = self._load_from_parquet(verbose=verbose)
        else:
            raise ValueError(f"Unknown cache strategy: {self.strategy}")

        end_time = time.time()
        if (verbose + self.verbose) == 2:
            logger.info(f"Cache load operation took {end_time - start_time:.2f} seconds.")
        return cached_data

    def _save_as_pickle(self, data: Dict[str, Any], verbose: bool = True):
        total_size_mb = 0
        for key, content in data.items():
            file_path = os.path.join(self.cache_dir, f"{key}.pkl")
            with open(file_path, 'wb') as f:
                pickle.dump(content, f)
            total_size_mb += os.path.getsize(file_path) / (1024 * 1024)
        if (verbose + self.verbose) == 2:
            logger.info(f"💾 Pickle Strategy: Saved {len(data)} key(s). Total size: {total_size_mb:.2f} MB")

    def _load_from_pickle(self, verbose: bool = True) -> Dict[str, Any]:
        loaded_data = {}
        with open(self.manifest_path, 'r') as f:
            keys = json.load(f)['file_keys']
        for key in keys:
            file_path = os.path.join(self.cache_dir, f"{key}.pkl")
            with open(file_path, 'rb') as f:
                loaded_data[key] = pickle.load(f)
        return loaded_data

    def _save_as_parquet(self, data: Dict[str, Any], verbose: bool = True):
        total_size_mb = 0
        for key, content in data.items():
            if isinstance(content, dict) and all(isinstance(df, pd.DataFrame) for df in content.values()):
                key_dir = os.path.join(self.cache_dir, key)
                os.makedirs(key_dir, exist_ok=True)
                
                desc = f"Saving '{key}' to Parquet"
                iterable = tqdm(content.items(), desc=desc, disable=not verbose)

                for mint, df in iterable:
                    safe_mint = mint.replace('/', '_').replace('\\', '_')
                    file_path = os.path.join(key_dir, f"{safe_mint}.parquet")
                    df.to_parquet(file_path)
                    total_size_mb += os.path.getsize(file_path) / (1024 * 1024)
            else:
                if (verbose + self.verbose) == 2:
                    logger.warning(f"Content for key '{key}' is not a DataFrame dict. Falling back to pickle.")
                self._save_as_pickle({key: content}, verbose)
        
        if (verbose + self.verbose) == 2:
            logger.info(f"💾 Parquet Strategy: Save complete. Total size: {total_size_mb:.2f} MB")

    def _load_from_parquet(self, verbose: bool = True) -> Dict[str, Any]:
        loaded_data = {}
        with open(self.manifest_path, 'r') as f:
            keys = json.load(f)['file_keys']

        for key in keys:
            key_dir = os.path.join(self.cache_dir, key)
            if os.path.isdir(key_dir):
                data_dict = {}
                parquet_files = [f for f in os.listdir(key_dir) if f.endswith('.parquet')]
                
                desc = f"Loading '{key}' from Parquet"
                iterable = tqdm(parquet_files, desc=desc, disable=not verbose)
                
                for filename in iterable:
                    mint = os.path.splitext(filename)[0]
                    file_path = os.path.join(key_dir, filename)
                    data_dict[mint] = pd.read_parquet(file_path)
                loaded_data[key] = data_dict
            else:
                if (verbose + self.verbose) == 2:
                    logger.warning(f"Directory for key '{key}' not found. Attempting to load as pickle.")
                file_path = os.path.join(self.cache_dir, f"{key}.pkl")
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        loaded_data[key] = pickle.load(f)
        return loaded_data