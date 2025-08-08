# rl_tools/backtest_agents.py
"""
Unified backtesting script for the Hierarchical Reinforcement Learning (HRL) module.

This script allows you to run a backtest for either the Scout or the Manager agent
by specifying the agent and the path to its trained model.

Usage:
  - Interactive Mode (recommended):
    python rl_tools/backtest_agents.py

  - Non-Interactive (for automation/scripts):
    - Backtest a Scout agent:
      python rl_tools/backtest_agents.py --agent scout --model-path /path/to/scout_model.zip --data-window full
    - Backtest a Manager agent:
      python rl_tools/backtest_agents.py --agent manager --model-path /path/to/manager_model.zip --data-window test
"""
import argparse
import os
import warnings
from typing import List

# Add project root to Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_logger import setup_logging, logger
from config import rl_config as cfg
from rl_tools.scout_backtest import run_backtest as run_scout_backtest
from rl_tools.manager_backtest import run_backtest as run_manager_backtest

# --- START: Interactive Menu Helper Functions ---

def find_saved_models(agent: str) -> List[str]:
    """Scans the model directory for a given agent and returns a list of .zip model files."""
    if agent not in ['scout', 'manager']:
        return []
    
    model_dir = cfg.ScoutConfig.MODEL_SAVE_DIR if agent == 'scout' else cfg.ManagerConfig.MODEL_SAVE_DIR
    found_models = []
    if os.path.exists(model_dir):
        for root, _, files in os.walk(model_dir):
            for file in files:
                if file.endswith((".zip")): # Find any .zip file
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, os.path.join(os.path.dirname(__file__), '..'))
                    found_models.append(relative_path.replace('\\', '/'))
    return sorted(found_models, reverse=True)

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
        print(f"No saved models found for the {agent} agent. Cannot proceed with backtest.")
        return None
    
    return get_user_choice(f"Please select a model to backtest for the {agent} agent:", models)

def run_interactive_backtest_menu():
    """Guides the user through backtesting options via the console."""
    agent_choice = get_user_choice("Which agent would you like to backtest?", ["Scout", "Manager"])
    agent_key = agent_choice.lower()
    
    model_to_backtest = get_model_selection(agent_key)
    
    if model_to_backtest:
        # --- MODIFIED: Ask for the data window ---
        data_window_options = list(cfg.DATA_WINDOWS.keys())
        data_window_choice = get_user_choice("Which data window should be used for the backtest?", data_window_options)
        
        if agent_key == 'scout':
            logger.info(f"Initiating backtest for Scout agent with model: {model_to_backtest}")
            # --- MODIFIED: Pass the chosen data window ---
            run_scout_backtest(model_path=model_to_backtest, data_window=data_window_choice)
        elif agent_key == 'manager':
            logger.info(f"Initiating backtest for Manager agent with model: {model_to_backtest}")
            # --- MODIFIED: Pass the chosen data window ---
            run_manager_backtest(model_path=model_to_backtest, data_window=data_window_choice)

# --- END: Interactive Menu Helper Functions ---

def main():
    """Parses arguments and calls the appropriate backtesting function."""
    
    if len(sys.argv) == 1:
        setup_logging(logger_name="rl_interactive_backtester")
        warnings.filterwarnings("ignore", category=UserWarning)
        run_interactive_backtest_menu()
        return

    parser = argparse.ArgumentParser(description="Unified Backtester for HRL Agents")
    parser.add_argument(
        "--agent", type=str, choices=['scout', 'manager'], required=True,
        help="Which agent to backtest: 'scout' or 'manager'."
    )
    parser.add_argument(
        "--model-path", type=str, required=True,
        help="Path to the trained .zip model file for the specified agent."
    )
    # --- MODIFIED: Add data-window argument for non-interactive mode ---
    parser.add_argument(
        "--data-window", type=str, default=cfg.DEFAULT_DATA_WINDOW,
        choices=cfg.DATA_WINDOWS.keys(),
        help="The data window to use for backtesting."
    )
    args = parser.parse_args()

    setup_logging(logger_name=f"rl_{args.agent}_backtester")
    warnings.filterwarnings("ignore", category=UserWarning)

    if args.agent == 'scout':
        logger.info(f"Initiating backtest for Scout agent with model: {args.model_path}")
        # --- MODIFIED: Pass the data_window argument ---
        run_scout_backtest(model_path=args.model_path, data_window=args.data_window)
    elif args.agent == 'manager':
        logger.info(f"Initiating backtest for Manager agent with model: {args.model_path}")
        # --- MODIFIED: Pass the data_window argument ---
        run_manager_backtest(model_path=args.model_path, data_window=args.data_window)

if __name__ == "__main__":
    main()