# rl_tools/train_agents.py
"""
Unified training script for the Hierarchical Reinforcement Learning (HRL) module.

This script orchestrates the entire training pipeline for both the Scout and Manager agents.
It runs the data preparation and training for each agent sequentially.

Usage:
    - Train both agents from scratch:
      python rl_tools/train_agents.py

    - Train only the Scout agent:
      python rl_tools/train_agents.py --agent scout

    - Continue training a Scout agent from a saved model:
      python rl_tools/train_agents.py --agent scout --continue-from-model /path/to/scout_model.zip

    - Fine-tune a Manager agent from a saved model:
      python rl_tools/train_agents.py --agent manager --continue-from-model /path/to/manager_model.zip --fine-tune
"""

import asyncio
import argparse
import os

# Add project root to Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_logger import setup_logging, logger
from rl_tools.cache_utils import CacheManager
from database_handler import DatabaseClient
from rl_tools.scout_data_preparation import prepare_scout_data
from rl_tools.scout_train import train_scout_agent
from rl_tools.manager_data_preparation import prepare_manager_data
from rl_tools.manager_train import train_manager_agent

async def main():
    """Asynchronous main function to run the training pipeline."""
    parser = argparse.ArgumentParser(description="Unified Trainer for HRL Agents")
    parser.add_argument(
        "--agent",
        type=str,
        choices=['scout', 'manager', 'all'],
        default='all',
        help="Which agent to train: 'scout', 'manager', or 'all'."
    )
    parser.add_argument(
        "--continue-from-model",
        type=str,
        help="Path to a .zip model file to continue training from. Only applicable when training a single agent."
    )
    parser.add_argument(
        "--fine-tune",
        action="store_true",
        help="Use a lower learning rate when continuing training. Applies to both agents."
    )
    args = parser.parse_args()

    setup_logging(logger_name="rl_unified_trainer")

    # Initialize DB Client for Cache Manager ---
    db_client = DatabaseClient()
    await db_client.connect()

    try:
        # --- Step 1: Train Scout Agent ---
        if args.agent in ['scout', 'all']:
            logger.info("="*80)
            logger.info("=== Starting Scout Agent Training Pipeline ===")
            logger.info("="*80)

            # --- MODIFICATION: Full robust caching workflow ---
            scout_cache = CacheManager('scout', db_client)
            if not await scout_cache.is_cache_valid():
                logger.info("--- Running Scout Data Preparation ---")
                decision_df, all_token_data = await prepare_scout_data()
                
                if decision_df is not None and all_token_data:
                    fingerprint = await scout_cache.generate_fingerprint()
                    scout_cache.save_cache(
                        fingerprint,
                        decision_df=decision_df,
                        all_token_data=all_token_data
                    )
                    logger.info("--- Scout Data Preparation Finished & Cached ---")
                else:
                    logger.critical("Scout data preparation failed. Aborting pipeline.")
                    return
            # --- END MODIFICATION ---

            logger.info("--- Running Scout Agent Training ---")
            train_scout_agent(
                continue_from_model=args.continue_from_model if args.agent == 'scout' else None,
                fine_tune=args.fine_tune if args.agent == 'scout' else False
            )
            logger.info("--- Scout Agent Training Finished ---")

        # --- Step 2: Train Manager Agent ---
        if args.agent in ['manager', 'all']:
            logger.info("="*80)
            logger.info("=== Starting Manager Agent Training Pipeline ===")
            logger.info("="*80)

            # --- MODIFICATION: Full robust caching workflow ---
            manager_cache = CacheManager('manager', db_client)
            if not await manager_cache.is_cache_valid():
                logger.info("--- Running Manager Data Preparation ---")
                trade_lifecycles = await prepare_manager_data()
                
                if trade_lifecycles is not None:
                    fingerprint = await manager_cache.generate_fingerprint()
                    manager_cache.save_cache(
                        fingerprint,
                        trade_lifecycles=trade_lifecycles
                    )
                    logger.info("--- Manager Data Preparation Finished & Cached ---")
                else:
                    logger.critical("Manager data preparation failed. Aborting.")
                    return
            # --- END MODIFICATION ---

            logger.info("--- Running Manager Agent Training ---")
            train_manager_agent(
                continue_from_model=args.continue_from_model if args.agent == 'manager' else None,
                fine_tune=args.fine_tune if args.agent == 'manager' else False
            )
            logger.info("--- Manager Agent Training Finished ---")

        logger.info("="*80)
        logger.info("=== HRL Training Pipeline Complete ===")
        logger.info("="*80)

    finally:
        await db_client.close()

if __name__ == "__main__":
    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()
    asyncio.run(main())
