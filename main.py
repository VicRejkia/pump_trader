import argparse
import asyncio
import os
import sys
import subprocess
import time
import json
from datetime import datetime, timezone
from logger import setup_logging, log_info, log_debug, log_error, log_warning, log_critical
from config import TELEGRAM_INTERACTION

# --- Project Setup ---
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = CURRENT_SCRIPT_DIR  # Assuming main.py is in the project root

# --- File Paths ---
DATA_DIR = os.path.join(PROJECT_ROOT_DIR, 'data')
STATUS_FILE = os.path.join(DATA_DIR, 'bot_status.json')
TELEGRAM_SCRIPT_PATH = os.path.join(PROJECT_ROOT_DIR, 'telegram_interface.py')
TRADING_BOT_SCRIPT_PATH = os.path.join(PROJECT_ROOT_DIR, 'trading_bot.py')

# --- Configuration ---
BOT_INITIAL_WARMUP_SECONDS = 40  # Wait this long after starting the bot before the first check
BOT_CHECK_INTERVAL_SECONDS = 15  # How often to check if the TradingBot is running after warmup
PYTHON_EXECUTABLE = sys.executable
MAX_RESTART_ATTEMPTS = 5 # Maximum number of consecutive restart attempts before giving up for a while
RESTART_COOLDOWN_SECONDS = 300 # Wait this long after max restart attempts

# --- Helper Functions ---
def is_process_running(process_handle):
    """Checks if the given subprocess.Popen handle is still running."""
    if process_handle is None:
        return False
    return process_handle.poll() is None

def get_trading_bot_status_from_file() -> str:
    """
    Reads the TradingBot status from the bot_status.json file.
    Returns 'RUNNING', 'STARTING', 'STOPPED', 'STALE', or 'ERROR_READING_STATUS'.
    """
    try:
        if not os.path.exists(STATUS_FILE):
            return "STOPPED"
        with open(STATUS_FILE, 'r') as f:
            status_data = json.load(f)

        bot_process_status = status_data.get("bot_process_status", "UNKNOWN").upper()
        timestamp_str = status_data.get("timestamp")

        if not timestamp_str:
            return "STALE" if bot_process_status == "RUNNING" else bot_process_status

        status_dt = datetime.fromisoformat(timestamp_str)
        # Ensure status_dt is offset-aware for correct comparison with offset-aware datetime.now(timezone.utc)
        if status_dt.tzinfo is None:
            status_dt = status_dt.replace(tzinfo=timezone.utc) # Assume UTC if naive
        else:
            status_dt = status_dt.astimezone(timezone.utc) # Convert to UTC if already aware

        age_seconds = (datetime.now(timezone.utc) - status_dt).total_seconds()

        # Check for stale status specifically
        # Stale if status is RUNNING/STARTING but timestamp is too old
        stale_threshold = BOT_CHECK_INTERVAL_SECONDS * 2.5 # Increased threshold slightly
        if bot_process_status in ["RUNNING", "STARTING"] and age_seconds > stale_threshold:
            log_warning(f"Status file is STALE. Status: {bot_process_status}, Age: {age_seconds:.2f}s, Threshold: {stale_threshold}s")
            return "STALE"
        
        if bot_process_status in ["RUNNING", "STARTING"]: # STARTING is also a valid running state initially
            return bot_process_status
        
        # Covers "STOPPED", "ERROR_IN_STATUS_UPDATER", "CRASHED", "ERROR_DB_SETUP", etc.
        return "STOPPED"

    except (IOError, json.JSONDecodeError, ValueError) as e:
        log_error(f"Error reading bot_status.json: {e}")
        return "ERROR_READING_STATUS"
    except Exception as e:
        log_error(f"Unexpected error in get_trading_bot_status_from_file: {e}")
        return "ERROR_READING_STATUS"

def start_script_in_new_console(script_path: str, cwd: str, args: list = None) -> subprocess.Popen:
    """Starts a Python script in a new console window."""
    if not os.path.exists(script_path):
        log_error(f"Script not found: {script_path}")
        raise FileNotFoundError(f"Script not found: {script_path}")

    command = [PYTHON_EXECUTABLE, script_path]
    if args:
        command.extend(args)

    log_info(f"Starting script: {' '.join(command)} in CWD: {cwd}")
    creation_flags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    try:
        process = subprocess.Popen(command, cwd=cwd, creationflags=creation_flags)
        log_info(f"Successfully started {os.path.basename(script_path)} with PID: {process.pid}")
        return process
    except Exception as e:
        log_error(f"Failed to Popen {os.path.basename(script_path)}: {e}")
        return None


async def ensure_process_terminated(process_handle: subprocess.Popen, process_name: str):
    """Ensures a process is terminated."""
    if process_handle and is_process_running(process_handle):
        log_info(f"Terminating {process_name} process (PID: {process_handle.pid})...")
        process_handle.terminate()
        try:
            process_handle.wait(timeout=10)
            log_info(f"{process_name} process terminated gracefully.")
        except subprocess.TimeoutExpired:
            log_warning(f"{process_name} process did not terminate gracefully, killing (PID: {process_handle.pid}).")
            process_handle.kill()
            try:
                process_handle.wait(timeout=5) # Wait for kill to take effect
            except subprocess.TimeoutExpired:
                log_error(f"Failed to kill {process_name} process (PID: {process_handle.pid}).")

async def main_controller(args):
    setup_logging()
    log_info("--- Main Controller Started ---")

    trading_bot_process = None
    telegram_interface_process = None
    restart_attempts = 0

    try:
        # 1. Start the Telegram Interface
        try:
            log_info("Attempting to start Telegram Interface...")
            if TELEGRAM_INTERACTION:
                telegram_interface_process = start_script_in_new_console(TELEGRAM_SCRIPT_PATH, PROJECT_ROOT_DIR)
                if not telegram_interface_process:
                    log_warning("Failed to start Telegram Interface, but controller will continue.")
        except Exception as e:
            log_error(f"Error during Telegram Interface startup: {e}")

        # Function to start the trading bot
        async def start_trading_bot(pass_args):
            nonlocal trading_bot_process # To modify the outer scope variable
            await ensure_process_terminated(trading_bot_process, "Trading Bot") # Ensure old instance is gone
            log_info("Attempting to start Trading Bot...")
            trading_bot_process = start_script_in_new_console(TRADING_BOT_SCRIPT_PATH, PROJECT_ROOT_DIR, pass_args)
            if trading_bot_process:
                log_info(f"Trading Bot started. Waiting {BOT_INITIAL_WARMUP_SECONDS}s for warmup...")
                await asyncio.sleep(BOT_INITIAL_WARMUP_SECONDS)
                return True
            else:
                log_error("Failed to start Trading Bot process.")
                return False

        # 2. Initial Trading Bot Start
        trading_bot_cli_args = []
        if args.cleanup: trading_bot_cli_args.append("--cleanup")
        if args.backup: trading_bot_cli_args.append("--backup")
        if args.params_file: trading_bot_cli_args.extend(["--params-file", args.params_file])
        if args.rl_agent_path: trading_bot_cli_args.extend(["--rl-agent-path", args.rl_agent_path])

        if not await start_trading_bot(trading_bot_cli_args):
            log_critical("Trading Bot could not be started initially. Exiting controller.")
            return

        # 3. Monitor the Trading Bot
        while True:
            await asyncio.sleep(BOT_CHECK_INTERVAL_SECONDS)
            bot_needs_restart = False

            # Check 1: Subprocess handle
            if not is_process_running(trading_bot_process):
                log_warning("Trading Bot process is no longer running (detected by process handle).")
                bot_needs_restart = True
            else:
                # Check 2: Status file (only if process handle seems okay)
                bot_status_from_file = get_trading_bot_status_from_file()
                log_debug(f"Trading Bot status from file: {bot_status_from_file}")

                if bot_status_from_file in ["STALE", "STOPPED", "ERROR_READING_STATUS"]:
                    log_warning(f"Trading Bot status from file indicates an issue: {bot_status_from_file}.")
                    # If process *is* running but status is bad, it might be stuck.
                    # Let's try to restart it.
                    bot_needs_restart = True

            if bot_needs_restart:
                if restart_attempts < MAX_RESTART_ATTEMPTS:
                    restart_attempts += 1
                    log_info(f"Attempting to restart Trading Bot (Attempt {restart_attempts}/{MAX_RESTART_ATTEMPTS})...")
                    if not await start_trading_bot(trading_bot_cli_args):
                        log_error(f"Failed to restart Trading Bot on attempt {restart_attempts}. Will retry after interval.")
                    else:
                        log_info("Trading Bot restarted successfully.")
                        # restart_attempts = 0 # Reset attempts on successful explicit restart
                                                # Let's keep incrementing to see if it stabilizes.
                                                # If it stabilizes, next check will not trigger restart, then we can reset.
                else:
                    log_error(f"Maximum restart attempts ({MAX_RESTART_ATTEMPTS}) reached for Trading Bot. Cooling down for {RESTART_COOLDOWN_SECONDS}s.")
                    await asyncio.sleep(RESTART_COOLDOWN_SECONDS)
                    restart_attempts = 0 # Reset attempts after cooldown
                    log_info("Cooldown finished. Will attempt to start Trading Bot on next cycle if needed.")
                    # No immediate restart here, will be caught in the next loop iteration if still needed
            else:
                # If bot is running fine, reset restart_attempts
                if restart_attempts > 0:
                    log_info("Trading Bot is running stable. Resetting restart attempt counter.")
                    restart_attempts = 0


            # Monitor Telegram Interface (optional)
            if telegram_interface_process and not is_process_running(telegram_interface_process):
                log_warning("Telegram Interface process is no longer running. Attempting to restart...")
                try:
                    await ensure_process_terminated(telegram_interface_process, "Telegram Interface")
                    telegram_interface_process = start_script_in_new_console(TELEGRAM_SCRIPT_PATH, PROJECT_ROOT_DIR)
                    if not telegram_interface_process:
                         log_error("Failed to restart Telegram Interface.")
                except Exception as e:
                    log_error(f"Error restarting Telegram Interface: {e}")


    except KeyboardInterrupt:
        log_info("KeyboardInterrupt received in Main Controller. Shutting down...")
    except Exception as e:
        log_error(f"An unexpected error occurred in Main Controller: {e}", exc_info=True)
    finally:
        log_info("--- Main Controller Shutting Down ---")
        await ensure_process_terminated(trading_bot_process, "Trading Bot")
        await ensure_process_terminated(telegram_interface_process, "Telegram Interface")
        log_info("Main Controller shutdown complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot Controller")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file containing optimized parameters from GA.")
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")

    cmd_args = parser.parse_args()

    # Ensure data directory exists for status files etc.
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created data directory: {DATA_DIR}")

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main_controller(cmd_args))
    except KeyboardInterrupt:
        print("\nMain Controller interrupted by user. Exiting.")
    except Exception as e:
        print(f"Fatal error in controller startup: {e}")