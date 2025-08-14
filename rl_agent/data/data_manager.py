# rl_agent/data/data_manager.py
"""
Handles fetching, caching, splitting, and providing data for the RL environment.
"""
from typing import Dict, Optional, Tuple
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split

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
    def __init__(self, db_client: DatabaseClient, start_date: datetime, end_date: datetime):
        self.db_client = db_client
        self.start_date = start_date
        self.end_date = end_date
        self.min_trade_count = rl_cfg.MIN_TRADE_COUNT_FOR_DATASET
        
        self.training_data: Optional[pd.DataFrame] = None
        self.evaluation_data: Optional[pd.DataFrame] = None
        self._current_dataset_iterator = None

        self.cache_manager = CacheManager(self.db_client, self.start_date, self.end_date)

    async def load_and_prepare_data(self) -> bool:
        """
        Loads data from cache or DB, runs feature engineering, splits the data,
        and prepares unified DataFrames for training and evaluation.
        """
        train_tokens_dict: Optional[Dict[str, pd.DataFrame]] = None
        eval_tokens_dict: Optional[Dict[str, pd.DataFrame]] = None

        if await self.cache_manager.is_cache_valid():
            cached_content = self.cache_manager.load_from_cache()
            train_tokens_dict = cached_content.get('training_set')
            eval_tokens_dict = cached_content.get('evaluation_set')
            logger.info(f"Loaded {len(train_tokens_dict)} tokens for training and {len(eval_tokens_dict)} for evaluation from cache.")
        else:
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

            # --- RANDOMIZED DATA SPLITTING ---
            logger.info("Splitting tokens into training and evaluation sets...")
            token_mints = list(all_tokens_dict.keys())
            
            # Ensure the split ratio is valid
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
            
            train_tokens_dict = {m: all_tokens_dict[m] for m in train_mints}
            eval_tokens_dict = {m: all_tokens_dict[m] for m in eval_mints}
            
            logger.info(f"Split complete: {len(train_tokens_dict)} training tokens, {len(eval_tokens_dict)} evaluation tokens.")

            # Save the split datasets to cache
            fingerprint = self.cache_manager._generate_fingerprint()
            data_to_cache = {
                'training_set': train_tokens_dict,
                'evaluation_set': eval_tokens_dict
            }
            self.cache_manager.save_to_cache(fingerprint, data_to_cache)
        
        if not train_tokens_dict:
            logger.error("No training tokens available after loading/splitting.")
            return False

        # --- Combine token DataFrames into unified timelines ---
        self.training_data = pd.concat(train_tokens_dict.values()).sort_index()
        logger.info(f"Training data prepared. Total time steps: {len(self.training_data)}")
        
        if eval_tokens_dict:
            self.evaluation_data = pd.concat(eval_tokens_dict.values()).sort_index()
            logger.info(f"Evaluation data prepared. Total time steps: {len(self.evaluation_data)}")

        # Default to providing the training dataset via iterator
        self.use_training_data()
        return True

    def use_training_data(self):
        """Sets the iterator to use the training dataset."""
        if self.training_data is not None:
            self._current_dataset_iterator = self.training_data.iterrows()
            logger.debug("DataManager is now providing TRAINING data.")
        else:
            self._current_dataset_iterator = iter([])

    def use_evaluation_data(self):
        """Sets the iterator to use the evaluation dataset."""
        if self.evaluation_data is not None:
            self._current_dataset_iterator = self.evaluation_data.iterrows()
            logger.debug("DataManager is now providing EVALUATION data.")
        else:
            self._current_dataset_iterator = iter([])

    def __iter__(self):
        # Reset the *current* iterator, whichever one is active
        self.reset()
        return self

    def __next__(self) -> Optional[Tuple[pd.Timestamp, pd.Series]]:
        try:
            return next(self._current_dataset_iterator)
        except StopIteration:
            return None

    def reset(self) -> None:
        """Resets the currently active data iterator to the beginning."""
        if self._current_dataset_iterator is not None:
            if self._current_dataset_iterator == self.training_data.iterrows():
                self.use_training_data()
            else:
                self.use_evaluation_data()