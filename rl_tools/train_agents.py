# rl_tools/train_agents.py
"""
Unified training script for the Hierarchical Reinforcement Learning (HRL) module.

This script orchestrates the entire training pipeline for both the Scout and Manager agents.
It runs the data preparation and training for each agent sequentially.

Usage:
  - Interactive Mode (recommended):
    python rl_tools/train_agents.py

  - Non-Interactive (for automation/scripts):
    - Train both agents from scratch on the 'full' dataset:
      python rl_tools/train_agents.py --train-all-from-scratch --data-window full
    - Train only the Scout agent from scratch on the 'test' dataset:
      python rl_tools/train_agents.py --agent scout --data-window test
    - Continue training a Scout agent:
      python rl_tools/train_agents.py --agent scout --data-window full --continue-from-model /path/to/scout_model.zip
    - Fine-tune a Manager agent:
      python rl_tools/train_agents.py --agent manager --data-window full --continue-from-model /path/to/manager_model.zip --fine-tune
"""

import asyncio
import argparse
import os
from typing import List

# Add project root to Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_logger import setup_logging, logger
from config import rl_config_old as cfg
from rl_tools.cache_utils import CacheManager
from database_handler import DatabaseClient
# --- MODIFIED: Import window-aware functions ---
from rl_tools.scout_data_preparation import prepare_scout_data
from rl_tools.scout_train import train_scout_agent
from rl_tools.manager_data_preparation import prepare_manager_data
from rl_tools.manager_train import train_manager_agent

def find_saved_models(agent: str) -> List[str]:
    """Scans the model directory for a given agent and returns a list of .zip model files."""
    if agent not in ['scout', 'manager']:
        return []
    
    model_dir = cfg.ScoutConfig.MODEL_SAVE_DIR if agent == 'scout' else cfg.ManagerConfig.MODEL_SAVE_DIR
    found_models = []
    if os.path.exists(model_dir):
        for root, _, files in os.walk(model_dir):
            for file in files:
                if file.endswith(("_final.zip", "best_model.zip")):
                    full_path = os.path.join(root, file)
                    # Get relative path for cleaner display
                    relative_path = os.path.relpath(full_path, os.path.join(os.path.dirname(__file__), '..'))
                    found_models.append(relative_path.replace('\\', '/'))
    return sorted(found_models, reverse=True) # Show newest first

def get_user_choice(prompt: str, options: List[str]) -> str:
    """Displays a list of options and gets a valid choice from the user."""
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    print(f"  [q] Quit")
    
    while True:
        choice = input("> ").strip().lower()
        if choice == 'q':
            sys.exit("Operation cancelled by user.")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Invalid choice. Please try again.")

def get_model_selection(agent: str) -> str:
    """Displays saved models for an agent and lets the user pick one."""
    models = find_saved_models(agent)
    if not models:
        print(f"No saved models found for the {agent} agent.")
        return None
    
    return get_user_choice(f"Please select a model for the {agent} agent", models)

async def run_scout_pipeline(data_window: str, continue_from: str = None, fine_tune: bool = False):
    """Runs the full data prep and training pipeline for the Scout."""
    logger.info("="*80)
    logger.info(f"=== Starting Scout Agent Pipeline (Window: {data_window}) ===")
    logger.info("="*80)
    
    try:
        window = cfg.DATA_WINDOWS[data_window]
    except KeyError:
        logger.critical(f"Data window '{data_window}' not defined in config. Aborting."); return False

    db_client_scout = DatabaseClient()
    await db_client_scout.connect()
    try:
        scout_cache = CacheManager('scout', db_client_scout, window['start'], window['end'])
        if not await scout_cache.is_cache_valid():
            logger.info("--- Running Scout Data Preparation ---")
            decision_df, _ = await prepare_scout_data(window['start'], window['end'], db_client_scout)
            
            if decision_df is not None:
                fingerprint = await scout_cache.generate_fingerprint()
                scout_cache.save_cache(fingerprint, decision_df=decision_df)
                logger.info("--- Scout Data Preparation Finished & Cached ---")
            else:
                logger.critical("Scout data preparation failed. Aborting pipeline.")
                return False
    finally:
        await db_client_scout.close()

    logger.info("--- Running Scout Agent Training ---")
    train_scout_agent(data_window=data_window, continue_from_model=continue_from, fine_tune=fine_tune)
    logger.info("--- Scout Agent Pipeline Finished ---")
    return True

async def run_manager_pipeline(data_window: str, continue_from: str = None, fine_tune: bool = False):
    """Runs the full data prep and training pipeline for the Manager."""
    logger.info("="*80)
    logger.info(f"=== Starting Manager Agent Pipeline (Window: {data_window}) ===")
    logger.info("="*80)

    try:
        window = cfg.DATA_WINDOWS[data_window]
    except KeyError:
        logger.critical(f"Data window '{data_window}' not defined in config. Aborting."); return False

    db_client_manager = DatabaseClient()
    await db_client_manager.connect()
    try:
        manager_cache = CacheManager('manager', db_client_manager, window['start'], window['end'])
        if not await manager_cache.is_cache_valid():
            logger.info("--- Running Manager Data Preparation ---")
            trade_lifecycles = await prepare_manager_data(window['start'], window['end'])
            if trade_lifecycles is not None:
                fingerprint = await manager_cache.generate_fingerprint()
                manager_cache.save_cache(fingerprint, trade_lifecycles=trade_lifecycles)
                logger.info("--- Manager Data Preparation Finished & Cached ---")
            else:
                logger.critical("Manager data preparation failed. Aborting pipeline.")
                return False
    finally:
        await db_client_manager.close()

    logger.info("--- Running Manager Agent Training ---")
    train_manager_agent(data_window=data_window, continue_from_model=continue_from, fine_tune=fine_tune)
    logger.info("--- Manager Agent Pipeline Finished ---")
    return True

async def run_interactive_menu():
    """Guides the user through training options via the console."""
    main_menu_options = ["Train both agents from scratch", "Train a single agent from scratch", "Continue training an existing agent", "Fine-tune an existing agent"]
    agent_menu_options = ["Scout", "Manager"]
    data_window_options = list(cfg.DATA_WINDOWS.keys())

    choice = get_user_choice("What would you like to do?", main_menu_options)
    data_window_choice = get_user_choice("Which data window should be used?", data_window_options)

    if choice == "Train both agents from scratch":
        if await run_scout_pipeline(data_window=data_window_choice):
            await run_manager_pipeline(data_window=data_window_choice)

    elif choice == "Train a single agent from scratch":
        agent_choice = get_user_choice("Which agent would you like to train?", agent_menu_options)
        if agent_choice == "Scout":
            await run_scout_pipeline(data_window=data_window_choice)
        elif agent_choice == "Manager":
            await run_manager_pipeline(data_window=data_window_choice)

    elif choice in ["Continue training an existing agent", "Fine-tune an existing agent"]:
        is_fine_tuning = choice.startswith("Fine-tune")
        action_word = "fine-tune" if is_fine_tuning else "continue training"
        
        agent_choice = get_user_choice(f"Which agent do you want to {action_word}?", agent_menu_options)
        agent_key = agent_choice.lower()
        
        model_to_continue = get_model_selection(agent_key)
        if model_to_continue:
            if agent_key == "scout":
                await run_scout_pipeline(data_window=data_window_choice, continue_from=model_to_continue, fine_tune=is_fine_tuning)
            elif agent_key == "manager":
                await run_manager_pipeline(data_window=data_window_choice, continue_from=model_to_continue, fine_tune=is_fine_tuning)

async def main():
    """Asynchronous main function to run the training pipeline."""
    parser = argparse.ArgumentParser(description="Unified Trainer for HRL Agents", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--agent", type=str, choices=['scout', 'manager'], help="Which agent to train: 'scout' or 'manager'.")
    parser.add_argument("--train-all-from-scratch", action="store_true", help="Train both agents from scratch without interactive prompts.")
    parser.add_argument("--data-window", type=str, default=cfg.DEFAULT_DATA_WINDOW, choices=cfg.DATA_WINDOWS.keys(), help="The data window from config to use for preparation and training.")
    parser.add_argument("--continue-from-model", type=str, help="Path to a .zip model file to continue training from. Requires --agent.")
    parser.add_argument("--fine-tune", action="store_true", help="Use fine-tuning hyperparameters when continuing training. Requires --agent and --continue-from-model.")
    
    if len(sys.argv) == 1:
        setup_logging(logger_name="rl_interactive_trainer")
        await run_interactive_menu()
        return

    args = parser.parse_args()
    setup_logging(logger_name="rl_unified_trainer")

    if args.train_all_from_scratch:
        if await run_scout_pipeline(data_window=args.data_window):
            await run_manager_pipeline(data_window=args.data_window)
    elif args.agent == 'scout':
        await run_scout_pipeline(data_window=args.data_window, continue_from=args.continue_from_model, fine_tune=args.fine_tune)
    elif args.agent == 'manager':
        await run_manager_pipeline(data_window=args.data_window, continue_from=args.continue_from_model, fine_tune=args.fine_tune)
    else:
        print("Invalid combination of arguments. Use --help for more information or run without arguments for the interactive menu.")

if __name__ == "__main__":
    if os.name == 'nt':
        from multiprocessing import freeze_support
        freeze_support()
    asyncio.run(main())