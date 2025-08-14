# rl_agent/data/data_manager.py
"""
Handles fetching, caching, splitting, and providing data for the RL environment.
"""
from typing import Dict, Optional, Tuple, List # Add List
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from tqdm import tqdm

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
import config.rl_config as rl_cfg

class DataManager:
    """
    Manages the data lifecycle for RL training and evaluation.
    - Manages caching of processed data.
    - Fetches raw data if cache is invalid.
    - Orchestrates feature engineering.
    - Splits tokens randomly into training and evaluation sets.
    - Combines token data into chronological DataFrames for the Gym environment.
    """
    # --- MODIFICATION START ---
    # Allow initialization with just one of db_client or cache_manager
    def __init__(self, db_client: Optional[DatabaseClient] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, training_df: Optional[pd.DataFrame] = None, evaluation_df: Optional[pd.DataFrame] = None, cache_manager: Optional[CacheManager] = None):
    # --- MODIFICATION END ---
        # Allow for initialization with pre-loaded data
        if training_df is not None:
            self.db_client = None
            self.training_data = training_df
            self.evaluation_data = evaluation_df
            self.use_training_data() # Default to providing training data
            self._is_preloaded = True
            self.cache_manager = None
        else:
            # MODIFICATION: Allow either db_client or cache_manager to be None initially
            if not db_client and not cache_manager and not (start_date and end_date):
                 raise ValueError("For non-preloaded data, cache_manager or db_client must be provided.")

            self.db_client = db_client
            self.start_date = start_date
            self.end_date = end_date
            self.min_trade_count = rl_cfg.MIN_TRADE_COUNT_FOR_DATASET
            self.training_data: Optional[pd.DataFrame] = None
            self.evaluation_data: Optional[pd.DataFrame] = None

            if cache_manager is not None:
                self.cache_manager = cache_manager
            elif db_client is not None and start_date is not None and end_date is not None:
                self.cache_manager = CacheManager(self.db_client, self.start_date, self.end_date)
            else:
                # This will be the case for child processes that create their own manager
                self.cache_manager = None


            self._is_preloaded = False

        self._current_dataset_iterator = None

    # --- NEW METHOD ---
    def get_split_token_mints(self, verbose: bool = True) -> Optional[Tuple[List[str], List[str]]]:
        """
        Loads the cached token sets and returns only the lists of mints for training and evaluation.
        This avoids loading the full dataframes into memory.
        """
        if self.cache_manager.strategy != 'parquet':
            logger.error("get_split_token_mints requires 'parquet' cache strategy.")
            return None

        # --- MODIFICATION: Pass verbose flag ---
        if verbose:
            logger.info("Loading token mint lists from cache...")
        cached_content = self.cache_manager.load_from_cache(verbose=verbose)
        train_set = cached_content.get('training_set')
        eval_set = cached_content.get('evaluation_set')

        if not train_set or not eval_set:
            logger.error("Cache does not contain 'training_set' and 'evaluation_set'. Please regenerate the cache.")
            return None

        train_mints = list(train_set.keys())
        eval_mints = list(eval_set.keys())
        
        if verbose:
            logger.info(f"Found {len(train_mints)} training mints and {len(eval_mints)} evaluation mints.")
        return train_mints, eval_mints

    async def load_and_prepare_data(self, mints_to_load: Optional[List[str]] = None, verbose: bool = True) -> bool:
        """
        [MODIFIED] Loads data from cache or DB. If mints_to_load is provided,
        it only loads and concatenates data for those specific mints, enabling lazy loading.
        """
        if self._is_preloaded:
            if verbose:
                logger.info("DataManager is using pre-loaded data. Skipping DB/cache operations.")
            return True
        
        # MODIFICATION: If cache manager was not provided at init, create it now.
        if self.cache_manager is None:
            self.cache_manager = CacheManager(self.db_client, self.start_date, self.end_date, verbose=verbose)


        train_tokens_dict: Optional[Dict[str, pd.DataFrame]] = None
        eval_tokens_dict: Optional[Dict[str, pd.DataFrame]] = None

        if await self.cache_manager.is_cache_valid(verbose=verbose):
            # --- MODIFICATION: Pass verbose flag ---
            cached_content = self.cache_manager.load_from_cache(verbose=verbose)
            train_tokens_dict = cached_content.get('training_set')
            eval_tokens_dict = cached_content.get('evaluation_set')
            if not train_tokens_dict:
                logger.error("Could not load training set from cache.")
                return False
            if verbose:
                logger.info(f"Loaded {len(train_tokens_dict)} tokens for training and {len(eval_tokens_dict)} for evaluation from cache.")
        else:
            # (The data generation part remains the same)
            logger.info(f"Fetching raw data from {self.start_date} to {self.end_date}...")
            raw_data = await self.db_client.get_raw_data_for_rl(
                start_date=self.start_date,
                end_date=self.end_date,
                min_trade_count=self.min_trade_count
            )

            if raw_data is None: return False
            trades_df, rugcheck_df, token_info_df, dexscreener_df = raw_data
            
            all_tokens_dict = await calculate_all_features(
                trades_df, rugcheck_df, token_info_df, dexscreener_df
            )
            
            if not all_tokens_dict:
                logger.error("Data preparation resulted in no processable tokens.")
                return False

            logger.info("Splitting tokens into training and evaluation sets...")
            token_mints = list(all_tokens_dict.keys())
            
            train_ratio, eval_ratio = rl_cfg.DATA_SPLIT_RATIO
            if not (train_ratio + eval_ratio == 1.0):
                    raise ValueError("DATA_SPLIT_RATIO must sum to 1.0")

            train_mints, eval_mints = train_test_split(
                token_mints,
                train_size=train_ratio,
                test_size=eval_ratio,
                random_state=rl_cfg.DATA_SPLIT_RANDOM_SEED,
                shuffle=True
            )
            
            train_tokens_dict = {m: all_tokens_dict[m] for m in tqdm(train_mints, desc="Building Training Set")}
            eval_tokens_dict = {m: all_tokens_dict[m] for m in tqdm(eval_mints, desc="Building Evaluation Set")}
            
            logger.info(f"Split complete: {len(train_tokens_dict)} training tokens, {len(eval_tokens_dict)} evaluation tokens.")

            fingerprint = self.cache_manager._generate_fingerprint()
            data_to_cache = {
                'training_set': train_tokens_dict,
                'evaluation_set': eval_tokens_dict
            }
            self.cache_manager.save_to_cache(fingerprint, data_to_cache)
        
        # --- LAZY LOADING LOGIC ---
        if mints_to_load:
            if verbose:
                logger.info(f"Lazy loading data for {len(mints_to_load)} specific mints.")
            # We assume we are loading a subset for a single dataset (e.g., training)
            self.training_data = pd.concat([train_tokens_dict[m] for m in mints_to_load if m in train_tokens_dict]).sort_index()
            # For evaluation, you might do the same with an eval_mints list
            self.evaluation_data = None # Or load a subset of eval tokens if needed
            if verbose:
                logger.info(f"Lazy load complete. Total steps: {len(self.training_data)}")
        else:
            # Original behavior: load everything
            logger.info("Combining all training dataframes...")
            self.training_data = pd.concat(tqdm(train_tokens_dict.values(), desc="Combining Training DataFrames", total=len(train_tokens_dict))).sort_index()
            logger.info(f"Training data prepared. Total time steps: {len(self.training_data)}")
            
            if eval_tokens_dict:
                logger.info("Combining all evaluation dataframes...")
                self.evaluation_data = pd.concat(tqdm(eval_tokens_dict.values(), desc="Combining Evaluation DataFrames", total=len(eval_tokens_dict))).sort_index()
                logger.info(f"Evaluation data prepared. Total time steps: {len(self.evaluation_data)}")

        self.use_training_data()
        return True

    def use_training_data(self):
        if self.training_data is not None:
            self._current_dataset_iterator = self.training_data.iterrows()
        else:
            self._current_dataset_iterator = iter([])

    def use_evaluation_data(self):
        if self.evaluation_data is not None:
            self._current_dataset_iterator = self.evaluation_data.iterrows()
        else:
            self._current_dataset_iterator = iter([])

    def __iter__(self):
        self.reset()
        return self

    def __next__(self) -> Optional[Tuple[pd.Timestamp, pd.Series]]:
        try:
            return next(self._current_dataset_iterator)
        except StopIteration:
            return None

    def reset(self) -> None:
        if self.training_data is not None:
            self.use_training_data()
        elif self.evaluation_data is not None:
            self.use_evaluation_data()