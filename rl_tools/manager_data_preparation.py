# scripts/manager_data_preparation.py
"""
Data preparation script for the Manager (Trade Management) RL Agent.

This script leverages the data prepared for the Scout agent. It works by:
1. Loading the Scout's potential trade entry points and the full OHLCV data.
2. Simulating every potential trade using the bot's original fixed stop-loss/take-profit logic
   to determine a baseline entry and exit point for each trade.
3. Extracting the time-series data (the "lifecycle") for each of these simulated trades.
4. Optionally extending this data beyond the fixed-rule exit point to allow the Manager
   agent to learn potentially better, more dynamic exit strategies.
5. Saving the collection of these trade lifecycles to be used by the Manager's training environment.
"""

import os
import pandas as pd
import asyncio
from tqdm import tqdm
import pickle
from datetime import timedelta
from typing import Dict, List

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_logger import setup_logging, logger
# Import from the new centralized config
from config import rl_config as cfg
# Import the Scout's data loader to get the full OHLCV data
from rl_tools.scout_data_preparation import load_prepared_scout_data
from rl_tools.cache_utils import CacheManager

def simulate_scout_trades(decision_df: pd.DataFrame, all_token_data: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    Simulates the fixed SL/TP logic for every potential trade identified by the Scout.
    This is based on the logic from the Scout's backtest and environment simulation.

    Returns:
        A list of dictionaries, where each dictionary represents a completed trade
        with its entry and exit details.
    """
    completed_trades = []
    
    for i in tqdm(range(len(decision_df)), desc="Simulating Scout's Fixed-Rule Trades"):
        decision_info = decision_df.iloc[i]
        mint = decision_info['mint']
        token_ohlcv = all_token_data.get(mint)

        if token_ohlcv is None or token_ohlcv.empty:
            continue

        decision_timestamp = decision_info['timestamp']
        trade_data = token_ohlcv[token_ohlcv.index >= decision_timestamp]

        if len(trade_data) < 2:
            continue

        buy_price = trade_data['Close'].iloc[0]
        if buy_price <= 0:
            continue

        # Use simulation parameters from the Scout's configuration
        stop_loss_price = buy_price * (1 - cfg.ScoutConfig.SIM_INITIAL_STOP_LOSS_PERCENT / 100.0)
        first_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_FIRST_SELL_PROFIT_MARGIN / 100.0)
        second_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_SECOND_TAKE_PROFIT_PERCENT / 100.0)
        
        highest_price = buy_price
        first_tp_hit = False
        exit_timestamp = None
        exit_reason = "Timeout"

        # Simulate the trade lifecycle
        for j in range(1, min(len(trade_data), cfg.ScoutConfig.MAX_STEPS_PER_EPISODE)):
            current_price = trade_data['Close'].iloc[j]
            highest_price = max(highest_price, current_price)

            if current_price <= stop_loss_price:
                exit_reason = "Stop Loss"
                exit_timestamp = trade_data.index[j]
                break
            if current_price >= second_tp_price:
                exit_reason = "Second TP"
                exit_timestamp = trade_data.index[j]
                break
            if not first_tp_hit and current_price >= first_tp_price:
                first_tp_hit = True
                stop_loss_price = buy_price # Adjust SL to breakeven
            if first_tp_hit:
                trailing_sl = highest_price * (1 - cfg.ScoutConfig.SIM_TRAILING_STOP_LOSS_PERCENT / 100.0)
                if current_price <= trailing_sl:
                    exit_reason = "Trailing SL"
                    exit_timestamp = trade_data.index[j]
                    break
        
        if exit_timestamp is None:
            exit_timestamp = trade_data.index[-1]

        completed_trades.append({
            "mint": mint,
            "entry_timestamp": decision_timestamp,
            "exit_timestamp_fixed_rule": exit_timestamp,
            "entry_price": buy_price,
            "exit_reason": exit_reason
        })
        
    return completed_trades

async def prepare_manager_data():
    """
    Main function to run the data preparation pipeline for the Manager agent.
    Returns the processed data instead of saving it directly.
    """
    setup_logging(logger_name="rl_manager_data_prep")
    logger.info("--- Starting Data Preparation for RL Manager Environment ---")

    logger.info("Loading Scout agent's processed decision and OHLCV data...")
    decision_df, all_token_data = load_prepared_scout_data()
    if decision_df is None or not all_token_data:
        logger.critical("Could not load Scout's processed data. Run scout_data_preparation.py first.")
        return None

    logger.info(f"Found {len(decision_df)} potential trade entry points from Scout's data.")

    scout_trades = simulate_scout_trades(decision_df, all_token_data)
    logger.info(f"Simulated {len(scout_trades)} trade lifecycles based on Scout's fixed rules.")

    trade_lifecycles_data = {}
    for i, trade in enumerate(tqdm(scout_trades, desc="Extracting Trade Lifecycles")):
        mint = trade['mint']
        entry_ts = trade['entry_timestamp']
        fixed_rule_exit_ts = trade['exit_timestamp_fixed_rule']
        
        if mint in all_token_data:
            token_df = all_token_data[mint]
            
            extended_exit_ts = fixed_rule_exit_ts + timedelta(minutes=cfg.ManagerConfig.MANAGER_DATA_EXTENSION_MINUTES)
            final_exit_ts = min(extended_exit_ts, token_df.index[-1])
            
            lifecycle_df = token_df.loc[entry_ts:final_exit_ts]
            
            if not lifecycle_df.empty and len(lifecycle_df) > 1:
                trade_id = f"{mint}_{entry_ts.strftime('%Y%m%d%H%M%S')}"
                trade_lifecycles_data[trade_id] = lifecycle_df
    
    logger.info(f"Successfully extracted {len(trade_lifecycles_data)} valid trade lifecycles for Manager training.")
    if cfg.ManagerConfig.MANAGER_DATA_EXTENSION_MINUTES > 0:
        logger.info(f"Data was extended by up to {cfg.ManagerConfig.MANAGER_DATA_EXTENSION_MINUTES} minutes per trade.")

    # Return the processed data ---
    return trade_lifecycles_data

def load_prepared_manager_data():
    """Loads the processed trade lifecycle data for the Manager agent from the cache."""
    # --- MODIFICATION: Use CacheManager to load data ---
    cache_manager = CacheManager('manager', db_client=None)
    
    if not os.path.exists(cache_manager.manifest_path):
        logger.error(f"Processed manager data cache not found. Please run the training pipeline first.")
        return None
        
    cached_data = cache_manager.load_cache()
    return cached_data.get('trade_lifecycles')

if __name__ == "__main__":
    asyncio.run(prepare_manager_data())
