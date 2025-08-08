# scripts/manager_data_preparation.py
"""
Data preparation script for the Manager (Trade Management) RL Agent.
...
"""

import os
import pandas as pd
import asyncio
from tqdm import tqdm
import pickle
from datetime import timedelta, datetime
from typing import Dict, List

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_logger import setup_logging, logger
from config import rl_config as cfg
# --- MODIFIED: Import the window-aware loading function ---
from rl_tools.scout_data_preparation import load_prepared_scout_data
from rl_tools.cache_utils import CacheManager

def simulate_scout_trades(decision_df: pd.DataFrame, ohlcv_data_dir: str) -> List[Dict]:
    """
    Simulates the fixed SL/TP logic for every potential trade identified by the Scout.
    It loads token OHLCV data from the specified parquet directory.

    Returns:
        A list of dictionaries, where each dictionary represents a completed trade
        with its entry and exit details.
    """
    completed_trades = []
    ohlcv_local_cache = {} # Cache to avoid re-reading files for the same token
    
    for i in tqdm(range(len(decision_df)), desc="Simulating Scout's Fixed-Rule Trades"):
        decision_info = decision_df.iloc[i]
        mint = decision_info['mint']
        
        # Load token OHLCV data from parquet file on demand
        if mint in ohlcv_local_cache:
            token_ohlcv = ohlcv_local_cache[mint]
        else:
            try:
                token_ohlcv_path = os.path.join(ohlcv_data_dir, f"{mint}.parquet")
                token_ohlcv = pd.read_parquet(token_ohlcv_path)
                ohlcv_local_cache[mint] = token_ohlcv
            except FileNotFoundError:
                logger.debug(f"OHLCV file for mint {mint} not found. Skipping trade simulation.")
                continue

        decision_timestamp = decision_info['timestamp']
        trade_data = token_ohlcv[token_ohlcv.index >= decision_timestamp]

        if len(trade_data) < 2:
            continue

        buy_price = trade_data['Close'].iloc[0]
        if buy_price <= 0:
            continue

        stop_loss_price = buy_price * (1 - cfg.ScoutConfig.SIM_INITIAL_STOP_LOSS_PERCENT / 100.0)
        first_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_FIRST_SELL_PROFIT_MARGIN / 100.0)
        second_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_SECOND_TAKE_PROFIT_PERCENT / 100.0)
        
        highest_price = buy_price
        first_tp_hit = False
        exit_timestamp = None
        exit_reason = "Timeout"

        for j in range(1, min(len(trade_data), cfg.ScoutConfig.MAX_STEPS_PER_EPISODE)):
            current_price = trade_data['Close'].iloc[j]
            highest_price = max(highest_price, current_price)

            if current_price <= stop_loss_price:
                exit_reason = "Stop Loss"; exit_timestamp = trade_data.index[j]; break
            if current_price >= second_tp_price:
                exit_reason = "Second TP"; exit_timestamp = trade_data.index[j]; break
            if not first_tp_hit and current_price >= first_tp_price:
                first_tp_hit = True; stop_loss_price = buy_price # Breakeven
            if first_tp_hit:
                trailing_sl = highest_price * (1 - cfg.ScoutConfig.SIM_TRAILING_STOP_LOSS_PERCENT / 100.0)
                if current_price <= trailing_sl:
                    exit_reason = "Trailing SL"; exit_timestamp = trade_data.index[j]; break
        
        if exit_timestamp is None: exit_timestamp = trade_data.index[min(len(trade_data)-1, cfg.ScoutConfig.MAX_STEPS_PER_EPISODE-1)]

        completed_trades.append({
            "mint": mint, "entry_timestamp": decision_timestamp,
            "exit_timestamp_fixed_rule": exit_timestamp,
            "entry_price": buy_price, "exit_reason": exit_reason
        })
        
    return completed_trades

async def prepare_manager_data(start_ts: datetime, end_ts: datetime):
    """
    Main function to run the data preparation pipeline for the Manager agent.
    Returns the processed data instead of saving it directly.
    """
    setup_logging(logger_name="rl_manager_data_prep")
    logger.info("--- Starting Data Preparation for RL Manager Environment ---")

    logger.info("Loading Scout agent's processed decision data...")
    # --- MODIFIED: Load data for the specified window ---
    decision_df, ohlcv_dir = load_prepared_scout_data(start_ts, end_ts)
    if decision_df is None or ohlcv_dir is None:
        logger.critical("Could not load Scout's processed data. Run scout_data_preparation.py first.")
        return None

    logger.info(f"Found {len(decision_df)} potential trade entry points from Scout's data.")
    
    if not os.path.isdir(ohlcv_dir):
        logger.critical(f"Scout's OHLCV cache directory not found at {ohlcv_dir}. Aborting.")
        return None

    scout_trades = simulate_scout_trades(decision_df, ohlcv_dir)
    logger.info(f"Simulated {len(scout_trades)} trade lifecycles based on Scout's fixed rules.")

    trade_lifecycles_data = {}
    ohlcv_local_cache = {} # Cache to avoid re-reading files
    for trade in tqdm(scout_trades, desc="Extracting Trade Lifecycles"):
        mint = trade['mint']
        entry_ts = trade['entry_timestamp']
        fixed_rule_exit_ts = trade['exit_timestamp_fixed_rule']
        
        # Load from parquet file if not in local cache
        if mint in ohlcv_local_cache:
            token_df = ohlcv_local_cache[mint]
        else:
            try:
                token_df_path = os.path.join(ohlcv_dir, f"{mint}.parquet")
                token_df = pd.read_parquet(token_df_path)
                ohlcv_local_cache[mint] = token_df
            except FileNotFoundError:
                continue
            
        extended_exit_ts = fixed_rule_exit_ts + timedelta(minutes=cfg.ManagerConfig.MANAGER_DATA_EXTENSION_MINUTES)
        final_exit_ts = min(extended_exit_ts, token_df.index[-1])
        
        lifecycle_df = token_df.loc[entry_ts:final_exit_ts]
        
        if not lifecycle_df.empty and len(lifecycle_df) > 1:
            trade_id = f"{mint}_{pd.to_datetime(entry_ts).strftime('%Y%m%d%H%M%S')}"
            trade_lifecycles_data[trade_id] = lifecycle_df
    
    logger.info(f"Successfully extracted {len(trade_lifecycles_data)} valid trade lifecycles for Manager training.")
    if cfg.ManagerConfig.MANAGER_DATA_EXTENSION_MINUTES > 0:
        logger.info(f"Data was extended by up to {cfg.ManagerConfig.MANAGER_DATA_EXTENSION_MINUTES} minutes per trade.")

    return trade_lifecycles_data

def load_prepared_manager_data(start_ts: datetime, end_ts: datetime):
    """Loads the processed trade lifecycle data for the Manager agent from the cache for a specific window."""
    # --- MODIFIED: Instantiate cache manager for the specific window ---
    cache_manager = CacheManager('manager', db_client=None, start_ts=start_ts, end_ts=end_ts)
    
    if not os.path.exists(cache_manager.manifest_path):
        logger.error(f"Processed manager data cache not found for window {start_ts.date()} - {end_ts.date()}. Please run the training pipeline first.")
        return None
        
    cached_data = cache_manager.load_cache()
    return cached_data.get('trade_lifecycles')

if __name__ == "__main__":
    # Example of how to run this script standalone for debugging
    async def run_standalone():
        window = cfg.DATA_WINDOWS[cfg.DEFAULT_DATA_WINDOW]
        await prepare_manager_data(window['start'], window['end'])
    asyncio.run(run_standalone())