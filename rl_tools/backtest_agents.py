# rl_tools/backtest_agents.py
"""
Unified backtesting script for the Hierarchical Reinforcement Learning (HRL) module.

This script allows you to run a backtest for either the Scout or the Manager agent
by specifying the agent and the path to its trained model.

Usage:
    - Backtest a Scout agent:
      python rl_tools/backtest_agents.py --agent scout --model-path /path/to/scout_model.zip

    - Backtest a Manager agent:
      python rl_tools/backtest_agents.py --agent manager --model-path /path/to/manager_model.zip
"""
import argparse
import os
import warnings

# Add project root to Python path to resolve imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_logger import setup_logging, logger
from rl_tools.scout_backtest import run_backtest as run_scout_backtest
from rl_tools.manager_backtest import run_backtest as run_manager_backtest

def main():
    """Parses arguments and calls the appropriate backtesting function."""
    parser = argparse.ArgumentParser(description="Unified Backtester for HRL Agents")
    parser.add_argument(
        "--agent",
        type=str,
        choices=['scout', 'manager'],
        required=True,
        help="Which agent to backtest: 'scout' or 'manager'."
    )
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the trained .zip model file for the specified agent."
    )
    args = parser.parse_args()

    setup_logging(logger_name=f"rl_{args.agent}_backtester")
    warnings.filterwarnings("ignore", category=UserWarning)

    if args.agent == 'scout':
        logger.info(f"Initiating backtest for Scout agent with model: {args.model_path}")
        run_scout_backtest(model_path=args.model_path)
    elif args.agent == 'manager':
        logger.info(f"Initiating backtest for Manager agent with model: {args.model_path}")
        run_manager_backtest(model_path=args.model_path)

if __name__ == "__main__":
    main()
