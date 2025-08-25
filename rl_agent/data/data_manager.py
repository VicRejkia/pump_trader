# rl_agent/data/data_manager.py
"""
Handles assembling feature data from a pre-computed Parquet feature store
for the RL environment.
"""
import os
import sys
from typing import Dict, Optional, Tuple, List
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from tqdm import tqdm

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from config.rl_config import FEATURE_GROUPS, RL_FEATURE_STORE_PATH, RL_FEATURE_STORE_VERSION

# Dynamically create the reverse mapping from the config to avoid redundancy
FEATURE_TO_GROUP_MAP = {
    feature: group_name
    for group_name, features in FEATURE_GROUPS.items()
    for feature in features
}

class DataManager:
    """
    Assembles feature data for RL training by reading from a partitioned Parquet store.
    - Determines which feature groups to load based on the active features.
    - Loads and merges data for a specified list of tokens and a date range.
    - Splits available tokens into training and evaluation sets.
    - Combines token data into chronological DataFrames for the Gym environment.
    """
    def __init__(self, rl_config: dict):
        self.rl_config = rl_config
        self.feature_store_path = os.path.join(project_root, RL_FEATURE_STORE_PATH, f"v{RL_FEATURE_STORE_VERSION}")
        
        self.training_data: Optional[pd.DataFrame] = None
        self.evaluation_data: Optional[pd.DataFrame] = None
        self.training_set_mints: List[str] = []
        self.evaluation_set_mints: List[str] = []

        self._current_dataset_iterator = None
        self._columns = None

    def get_training_data(self) -> Optional[pd.DataFrame]: return self.training_data
    def get_evaluation_data(self) -> Optional[pd.DataFrame]: return self.evaluation_data
    def get_split_token_mints(self) -> Tuple[List[str], List[str]]: return self.training_set_mints, self.evaluation_set_mints

    def _load_data_for_mints(
        self,
        mints_to_load: List[str],
        start_date: datetime,
        end_date: datetime,
        active_features: List[str],
        verbose: bool = True
    ) -> Optional[Dict[str, pd.DataFrame]]:
        if not mints_to_load: return {}

        groups_to_load = {'base_ohlcv'}
        for feature in active_features:
            if feature in FEATURE_TO_GROUP_MAP:
                groups_to_load.add(FEATURE_TO_GROUP_MAP[feature])
            elif feature not in FEATURE_GROUPS['base_ohlcv']:
                logger.warning(f"Feature '{feature}' not mapped to a group and will be ignored.")
        if verbose: logger.info(f"Required feature groups: {sorted(list(groups_to_load))}")

        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        all_mint_data = {mint: [] for mint in mints_to_load}

        for group in groups_to_load:
            for day in date_range:
                group_path = os.path.join(self.feature_store_path, f"group={group}", f"date={day.strftime('%Y-%m-%d')}")
                if not os.path.isdir(group_path): continue
                for mint in mints_to_load:
                    file_path = os.path.join(group_path, f"{mint}.parquet")
                    if os.path.exists(file_path):
                        try:
                            all_mint_data[mint].append(pd.read_parquet(file_path))
                        except Exception as e:
                            if verbose: logger.warning(f"Could not read {file_path}: {e}")

        assembled_dfs = {}
        for mint, df_list in tqdm(all_mint_data.items(), desc="Assembling mint dataframes", disable=not verbose):
            if df_list:
                full_df = pd.concat(df_list).sort_index()
                assembled_dfs[mint] = full_df.loc[~full_df.index.duplicated(keep='first')]
            
        return assembled_dfs

    def load_and_prepare_data(self, mints_to_load: Optional[List[str]] = None, verbose: bool = True) -> bool:
        start_date = datetime.fromisoformat(self.rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(self.rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
        active_features = [f for f, is_active in self.rl_config['FEATURES_CONFIG'].items() if is_active]

        if not os.path.isdir(self.feature_store_path):
            logger.error(f"Feature store not found at: {self.feature_store_path}")
            logger.error("Please run `rl_agent/etl/prepare_rl_dataset.py` first.")
            return False

        if not mints_to_load and not (self.training_set_mints or self.evaluation_set_mints):
            logger.info("Discovering available tokens in the feature store...")
            base_path = os.path.join(self.feature_store_path, "group=base_ohlcv")
            available_mints = set(os.path.splitext(f)[0] for root, _, files in os.walk(base_path) for f in files if f.endswith(".parquet"))
            
            if not available_mints:
                logger.error("No token data found in the feature store. Aborting.")
                return False

            logger.info(f"Found {len(available_mints)} unique tokens. Splitting into train/eval sets.")
            train_ratio, eval_ratio = self.rl_config.get('DATA_SPLIT_RATIO')
            self.training_set_mints, self.evaluation_set_mints = train_test_split(
                list(available_mints), train_size=train_ratio, test_size=eval_ratio,
                random_state=self.rl_config.get('DATA_SPLIT_RANDOM_SEED'), shuffle=True
            )
        
        mints_for_training = mints_to_load or self.training_set_mints
        mints_for_evaluation = [] if mints_to_load else self.evaluation_set_mints

        training_dict = self._load_data_for_mints(mints_for_training, start_date, end_date, active_features, verbose)
        if training_dict:
            self.training_data = pd.concat(training_dict.values()).sort_index()
            if verbose: logger.info(f"Training data prepared. Total steps: {len(self.training_data)}")
        
        if mints_for_evaluation:
            eval_dict = self._load_data_for_mints(mints_for_evaluation, start_date, end_date, active_features, verbose)
            if eval_dict:
                self.evaluation_data = pd.concat(eval_dict.values()).sort_index()
                if verbose: logger.info(f"Evaluation data prepared. Total steps: {len(self.evaluation_data)}")
        
        self.use_training_data()
        return True

    def use_training_data(self):
        if self.training_data is not None:
            self._current_dataset_iterator, self._columns = self.training_data.itertuples(), self.training_data.columns
        else: self._current_dataset_iterator = iter([])

    def use_evaluation_data(self):
        if self.evaluation_data is not None:
            self._current_dataset_iterator, self._columns = self.evaluation_data.itertuples(), self.evaluation_data.columns
        else: self._current_dataset_iterator = iter([])
            
    def use_single_token_data(self, token_df: pd.DataFrame):
        if token_df is not None and not token_df.empty:
            self._current_dataset_iterator, self._columns = token_df.itertuples(), token_df.columns
        else: self._current_dataset_iterator = iter([])

    def __iter__(self):
        self.reset(); return self

    def __next__(self) -> Optional[Tuple[pd.Timestamp, pd.Series]]:
        if self._current_dataset_iterator is None: return None
        try:
            row_tuple = next(self._current_dataset_iterator)
            timestamp = row_tuple[0]
            return timestamp, pd.Series(row_tuple[1:], index=self._columns, name=timestamp)
        except StopIteration: return None

    def reset(self) -> None: self.use_training_data()