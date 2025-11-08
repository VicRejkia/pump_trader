# rl_agent_module/data/data_manager.py
"""
Handles assembling feature data by directly accessing the MLflow artifact store path.
NOTE: This approach is optimized for a local 'file://' MLflow backend.
"""
import os
import sys
from typing import Dict, Optional, Tuple, List
import pandas as pd
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import mlflow
from mlflow.tracking import MlflowClient
from urllib.parse import urlparse
import platform

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from config.rl_config import FEATURE_GROUPS, get_active_features

# Dynamically create the reverse mapping from the config
FEATURE_TO_GROUP_MAP = {
    feature: group_name
    for group_name, features in FEATURE_GROUPS.items()
    for feature in features
}

class DataManager:
    """
    Manages RL feature data by linking to a versioned dataset in MLflow.
    - Determines the direct local path to the artifact store for a given run.
    - Loads and merges data for specified tokens from the Parquet store.
    - Splits available tokens into training and evaluation sets.
    """
    def __init__(self, rl_config: dict, dataset_run_id: str):
        self.rl_config = rl_config
        self.dataset_run_id = dataset_run_id
        
        # The path will be populated dynamically by resolving the artifact URI.
        self.feature_store_path: Optional[str] = None

        self.training_data: Optional[pd.DataFrame] = None
        self.evaluation_data: Optional[pd.DataFrame] = None
        self.training_set_mints: List[str] = []
        self.evaluation_set_mints: List[str] = []

        self._current_dataset_iterator = None
        self._columns = None

        self.verbose = True

    def get_training_data(self) -> Optional[pd.DataFrame]: return self.training_data
    def get_evaluation_data(self) -> Optional[pd.DataFrame]: return self.evaluation_data
    def get_split_token_mints(self) -> Tuple[List[str], List[str]]: return self.training_set_mints, self.evaluation_set_mints

    def _resolve_artifact_path(self) -> bool:
        """
        Gets the direct, local filesystem path to the 'feature_store' artifact.
        This method is suitable for 'file://' MLflow backends.
        """
        try:
            if self.verbose:
                logger.info(f"Resolving direct artifact path for run '{self.dataset_run_id}'...")
            client = MlflowClient()
            run = client.get_run(self.dataset_run_id)
            artifact_uri = run.info.artifact_uri
            
            # The artifact_uri is the root of the artifacts for the run.
            # We need to append our specific artifact's path.
            parsed_uri = urlparse(artifact_uri)
            
            # For local file URIs (e.g., 'file:///C:/path'), extract the path correctly.
            if parsed_uri.scheme == 'file':
                # On Windows, urlparse might add an extra leading '/' (e.g., /C:/...).
                # We need to remove it.
                local_artifact_root = parsed_uri.path
                if platform.system() == "Windows" and local_artifact_root.startswith('/'):
                    local_artifact_root = local_artifact_root[1:]
                
                self.feature_store_path = os.path.join(local_artifact_root, "feature_store")
                if self.verbose:
                    logger.info(f"✅ Resolved artifact path to: {self.feature_store_path}")
                return True
            else:
                logger.error(f"Cannot resolve direct path for non-file URI: {artifact_uri}. This method only works for local MLflow stores.")
                return False

        except Exception as e:
            logger.error(f"Failed to resolve artifact path for run '{self.dataset_run_id}': {e}", exc_info=True)
            return False

    def _load_data_for_mints(
        self,
        mints_to_load: List[str],
        active_features: List[str],
        verbose: bool = True
    ) -> Dict[str, pd.DataFrame]:
        if not mints_to_load or self.feature_store_path is None: return {}

        groups_to_load = {'base_ohlcv'}
        for feature in active_features:
            if feature in FEATURE_TO_GROUP_MAP:
                groups_to_load.add(FEATURE_TO_GROUP_MAP[feature])
        if verbose: logger.info(f"Required feature groups: {sorted(list(groups_to_load))}")

        all_mint_data = {mint: [] for mint in mints_to_load}
        for group in groups_to_load:
            group_root_path = os.path.join(self.feature_store_path, f"group={group}")
            if not os.path.isdir(group_root_path): continue

            for date_dir in os.listdir(group_root_path):
                date_path = os.path.join(group_root_path, date_dir)
                if not os.path.isdir(date_path): continue
                for mint in mints_to_load:
                    file_path = os.path.join(date_path, f"{mint}.parquet")
                    if os.path.exists(file_path):
                        try:
                            all_mint_data[mint].append(pd.read_parquet(file_path))
                        except Exception as e:
                            if verbose: logger.warning(f"Could not read {file_path}: {e}")

        assembled_dfs = {}
        desc = "Assembling mint dataframes"
        for mint, df_list in tqdm(all_mint_data.items(), desc=desc, disable=not verbose):
            if df_list:
                full_df = pd.concat(df_list).sort_index()
                full_df = full_df.loc[~full_df.index.duplicated(keep='first')]
                assembled_dfs[mint] = full_df
            
        return assembled_dfs

    def load_and_prepare_data(self, mints_to_load: Optional[List[str]] = None, verbose: bool = True) -> bool:
        if self.feature_store_path is None:
            if not self._resolve_artifact_path():
                return False
        
        active_features = get_active_features(self.rl_config)
        active_features_with_mint = active_features + ['mint']

        if not mints_to_load and not (self.training_set_mints or self.evaluation_set_mints):
            if verbose: logger.info("Discovering available tokens in the feature store...")
            base_path = os.path.join(self.feature_store_path, "group=base_ohlcv")
            
            if not os.path.isdir(base_path):
                 logger.error(f"Critical error: 'group=base_ohlcv' not found at path {base_path}")
                 return False

            available_mints = set(os.path.splitext(f)[0] for root, _, files in os.walk(base_path) for f in files if f.endswith(".parquet"))
            
            if not available_mints:
                logger.error("No token data found in the feature store. Aborting.")
                return False

            if verbose: logger.info(f"Found {len(available_mints)} unique tokens. Splitting into train/eval sets.")
            train_ratio = self.rl_config.get('DATA_SPLIT_RATIO')[0]
            self.training_set_mints, self.evaluation_set_mints = train_test_split(
                list(available_mints), train_size=train_ratio,
                random_state=self.rl_config.get('DATA_SPLIT_RANDOM_SEED'), shuffle=True
            )
        
        mints_for_training = mints_to_load or self.training_set_mints
        mints_for_evaluation = [] if mints_to_load else self.evaluation_set_mints

        training_dict = self._load_data_for_mints(mints_for_training, active_features_with_mint, verbose)
        if training_dict:
            self.training_data = pd.concat(training_dict.values()).sort_index()
            if verbose: logger.info(f"Training data prepared. Total steps: {len(self.training_data)}")
        
        if mints_for_evaluation:
            eval_dict = self._load_data_for_mints(mints_for_evaluation, active_features_with_mint, verbose)
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