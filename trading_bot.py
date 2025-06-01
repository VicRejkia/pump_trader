import argparse
import asyncio
import signal
import traceback
import inspect
import threading
import os
import time
import json # Ensure json is imported
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import httpx

# Assuming these imports are correct for your project structure
import config as config_module
from database_handler import DatabaseClient
from trading_logic import TradingManager
from websocket_handler import WebSocketHandler
from logger import setup_logging, log_info, log_debug, log_error, log_warning, log_critical, rotate_log_file
from state_manager import GlobalState # Assuming GlobalState is in state_manager.py
from trade_processor import trade_worker
from sol_price_api import update_sol_price
from rugcheck_handler import Rugcheck
from socials_processor import SocialsProcessor
from utils import calculate_volatility # Assuming this is your utility

from telegram_interface import send_telegram_message

# --- RL Imports (add these) ---
try:
    import stable_baselines3
    # Import the specific algorithm class you trained (e.g., PPO)
    from stable_baselines3 import PPO # Or SAC, TD3, etc.
    from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv # Import VecNormalize
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    # Define a dummy VecNormalize if SB3 is not available
    class VecNormalize:
        def __init__(self, *args, **kwargs):
            pass
        def normalize_obs(self, obs):
            return obs
        def load(self, *args, **kwargs):
            pass
# Import RL config to know parameter names and observation details
import rl_config
# --- End RL Imports ---

# Define paths for communication files relative to project root
# Ensure these paths are consistent with how your Flask app will find them.
# If flask_app is in 'web_app', and bot is in root, these paths are from root.
PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) # Or however you define your project root
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
# Change to JSON for structured status
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

class TradingBot:
    """Main class for running the trading bot."""

    # Modify __init__ to accept RL agent path
    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, rl_agent_path: str = None, no_log_rotate: bool = False):
        """Initialize the TradingBot with optional cleanup, backup, GA params file, and RL agent path."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.state = GlobalState.get_instance() # Bot's instance of GlobalState
        self.cleanup = cleanup
        self.backup = backup
        self.no_log_rotate = no_log_rotate # Store the flag
        self.params_file = params_file
        self.rl_agent_path = rl_agent_path
        self.rl_agent = None
        self.vec_normalize = None # Add attribute for VecNormalize
        self.db_client = None
        self.ws_handler = None
        self.tasks = []
        self.config = {}
        self.base_config = {}
        self._load_base_config()
        self.trading_manager = None
        self._last_dynamic_config_mtime = 0
        self.bot_start_time = datetime.now(timezone.utc) # For uptime calculation

        # Ensure data directory exists
        os.makedirs(DATA_DIR_BOT, exist_ok=True)

        # Initialize status file with an "INITIALIZING" state
        self._write_status({"bot_process_status": "INITIALIZING", "timestamp": datetime.now(timezone.utc).isoformat()})

    async def _fetch_initial_sol_price(self) -> bool:
        """
        Fetches the SOL price once at startup and updates state and DB.
        Returns True if successful, False otherwise.
        """
        try:
            async with httpx.AsyncClient() as client:
                log_debug(f"Fetching initial SOL price from {config_module._SOL_PRICE_API_URL}") # Use log_debug if available
                response = await client.get(config_module._SOL_PRICE_API_URL, timeout=10.0) # 10-second timeout
                
                if response.status_code == 200:
                    data = response.json()
                    new_price = data.get("solana", {}).get("usd")
                    
                    if new_price is None or not isinstance(new_price, (int, float)):
                        log_error("Invalid or missing SOL price in initial API response.") # Use log_error
                        return False

                    await self.state.set_sol_price(new_price)
                    # Ensure db_client is connected and initialized before calling this
                    await self.db_client.insert_sol_price(new_price) 
                    log_info(f"✅ Initial SOL price successfully fetched and set: {new_price} USD") # Use log_info
                    return True
                else:
                    log_error(f"⚠ Error fetching initial SOL price. Status: {response.status_code}, Response: {response.text}")
                    return False
        except httpx.TimeoutException:
            log_error("⏳ Timeout fetching initial SOL price.")
            return False
        except httpx.RequestError as req_err:
            log_error(f"❌ HTTP Request Error fetching initial SOL price: {req_err}")
            return False
        except Exception as e:
            log_error(f"❌ Exception fetching initial SOL price: {e}", exc_info=True)
            return False

    def _filter_serializable_config(self, config_dict):
        serializable_config = {}
        skipped_keys = []
        for key, value in config_dict.items():
            if isinstance(value, set):
                serializable_config[key] = list(value)
            elif isinstance(value, timedelta):
                serializable_config[key] = str(value) # Convert timedelta to string
            elif isinstance(value, (int, float, str, bool, list, dict)) or value is None:
                serializable_config[key] = value
            else:
                # For other non-standard types, convert to string or skip
                try:
                    json.dumps({key: value}) # Test serializability
                    serializable_config[key] = value
                except TypeError:
                    serializable_config[key] = str(value)
                    skipped_keys.append(f"{key} (type: {type(value).__name__} converted to str)")
        if skipped_keys:
            log_debug(f"Skipped/converted non-JSON serializable keys for status config summary: {skipped_keys}")
        return serializable_config

    def _load_base_config(self):
        try:
            loaded_config = {}
            for key in dir(config_module):
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config_module, key)
                    if not inspect.ismodule(value) and \
                       not inspect.isclass(value) and \
                       not inspect.isfunction(value):
                        loaded_config[key] = value
            self.base_config = loaded_config.copy()
            self.config = loaded_config.copy()
            log_info(":gear: Base configuration loaded successfully.")
        except Exception as e:
            log_critical(f":x: [bold red]CRITICAL: Failed to load base configuration[/bold red]: {e}", exc_info=True)
            raise ValueError("Failed to load critical base configuration.") from e
        
    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""

        def signal_handler():
            log_info(":heavy_exclamation_mark: [bold red]Signal received[/bold red], initiating shutdown...")
            self.state.trigger_shutdown()

        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, lambda *_: signal_handler())
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, lambda *_: signal_handler())

    async def config_updater(self):
        """Periodically checks dynamic_config.json for updates and applies them."""
        log_info(f"⚙️ Dynamic config updater started. Watching: {os.path.abspath(DYNAMIC_CONFIG_FILE)}")

        while not self.state.shutdown_event.is_set():
            await asyncio.sleep(10)
            try:
                if not os.path.exists(DYNAMIC_CONFIG_FILE):
                    continue

                current_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
                if current_mtime > self._last_dynamic_config_mtime:
                    log_info(f"Detected change in {DYNAMIC_CONFIG_FILE}. Attempting to load updates.")
                    try:
                        with open(DYNAMIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                            dynamic_conf = json.load(f)

                        if not isinstance(dynamic_conf, dict):
                            log_warning(f"Invalid format in {DYNAMIC_CONFIG_FILE}: Expected JSON object. Skipping.")
                            self._last_dynamic_config_mtime = current_mtime
                            continue
                        
                        # Convert lists from JSON back to sets if the base config had them as sets
                        for key_in_json, value_from_json in dynamic_conf.items():
                            key_upper = key_in_json.upper()
                            if key_upper in self.base_config and isinstance(self.base_config[key_upper], set) and isinstance(value_from_json, list):
                                dynamic_conf[key_in_json] = set(value_from_json)


                        updated_count = 0
                        changed_params = {} # For logging specific changes

                        for key, value in dynamic_conf.items():
                            key_upper = key.upper()
                            if key_upper in self.config: # Check against active config
                                current_value_active = self.config[key_upper]
                                
                                # Determine the target type from base_config if available, else from current_value_active
                                target_type = None
                                if key_upper in self.base_config:
                                    target_type = type(self.base_config[key_upper])
                                else:
                                    target_type = type(current_value_active)

                                value_to_set = value
                                try:
                                    if target_type == bool and not isinstance(value, bool): value_to_set = str(value).lower() in ['true', '1', 'yes']
                                    elif target_type == int and not isinstance(value, int): value_to_set = int(value)
                                    elif target_type == float and not isinstance(value, float): value_to_set = float(value)
                                    elif target_type == set and not isinstance(value, set):
                                        if isinstance(value, list): value_to_set = set(value)
                                        else: raise TypeError(f"Cannot convert {type(value)} to set for {key_upper}")
                                    # Add other type coercions if necessary (e.g., Decimal, timedelta from string)
                                except (ValueError, TypeError) as e:
                                    log_warning(f"Type mismatch or conversion error for '{key_upper}' in {DYNAMIC_CONFIG_FILE}. Expected compatible with {target_type}, got {type(value)} ('{value}'). Error: {e}. Skipping update for this key.")
                                    continue # Skip this key

                                if value_to_set != current_value_active:
                                    self.config[key_upper] = value_to_set
                                    changed_params[key_upper] = {"from": str(current_value_active), "to": str(value_to_set)}
                                    updated_count += 1
                            else:
                                # If key is not in current config, it's a new parameter. Add it.
                                # Type is taken directly from JSON.
                                self.config[key_upper] = value
                                changed_params[key_upper] = {"from": "N/A (new)", "to": str(value)}
                                updated_count +=1
                                log_info(f"⚙️ Dynamic Config: Added new parameter '{key_upper}' = '{value}'")


                        if updated_count > 0:
                            log_info(f"Applied {updated_count} configuration updates from {DYNAMIC_CONFIG_FILE}.")
                            for k, v_change in changed_params.items():
                                log_info(f"  - '{k}': from '{v_change['from']}' to '{v_change['to']}'")
                            # Update components that depend on self.config if necessary
                            if self.trading_manager: self.trading_manager.config = self.config
                            if self.ws_handler: self.ws_handler.config = self.config
                            if self.db_client: self.db_client.config = self.config # If DBClient uses it dynamically
                            # ... update other components like Rugcheck, SocialsProcessor if they cache config values
                        else:
                            log_info(f"No configuration values changed in {DYNAMIC_CONFIG_FILE}.")

                        self._last_dynamic_config_mtime = current_mtime
                    except FileNotFoundError:
                        log_warning(f"{DYNAMIC_CONFIG_FILE} disappeared. Skipping.")
                        self._last_dynamic_config_mtime = 0
                    except json.JSONDecodeError as e:
                        log_error(f"Error decoding JSON from {DYNAMIC_CONFIG_FILE}: {e}. Skipping.")
                    except Exception as e:
                         log_error(f"Unexpected error processing {DYNAMIC_CONFIG_FILE}: {e}", exc_info=True)
                         self._last_dynamic_config_mtime = current_mtime
            except FileNotFoundError:
                 if self._last_dynamic_config_mtime != 0:
                      log_info(f"{DYNAMIC_CONFIG_FILE} was removed.")
                      self._last_dynamic_config_mtime = 0
            except Exception as e:
                log_error(f"Error in config_updater loop: {e}", exc_info=True)
                await asyncio.sleep(30)
        log_info("⚙️ Dynamic config updater task shutting down.")

    def _write_status(self, status_data: dict):
        """Writes the bot's status dictionary to the status JSON file."""
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=4)
            # log_debug(f"Status updated to: {status_data.get('bot_process_status', 'UNKNOWN')}")
        except IOError as e:
            log_error(f"Error writing status file {STATUS_FILE}: {e}")
        except Exception as e:
             log_error(f"Unexpected error writing status file: {e}", exc_info=True)

    async def status_updater(self):
        """Periodically gathers and writes detailed bot status to bot_status.json."""
        log_info("🚀 Status updater task started.")
        current_process_status = "STARTING" # Initial status

        while not self.state.shutdown_event.is_set():
            try:
                # Determine current bot process status
                if self.state.shutdown_event.is_set(): # Check if shutdown initiated
                    current_process_status = "STOPPING"
                elif not self.tasks or any(t.done() and not t.cancelled() and t.exception() for t in self.tasks if t.get_name() not in ["command_listener", "status_updater", "config_updater", "task_monitor"]): # Check for critical task failures
                    # Exclude auxiliary tasks from causing ERROR state if they fail,
                    # focus on core tasks like ws_handlers, price_updater, workers, buy/sell checkers.
                    critical_tasks_failed = False
                    for task in self.tasks:
                        if task.done() and not task.cancelled() and task.exception():
                             # Define which tasks are critical
                            critical_task_names = ["ws_", "sol_price_updater", "trade_worker", "rugcheck_worker", "socialscheck_worker", "buy_opportunity_checker", "sell_opportunity_checker"]
                            if any(ct_name in task.get_name() for ct_name in critical_task_names):
                                log_error(f"Critical task {task.get_name()} failed: {task.exception()}. Setting status to ERROR.")
                                critical_tasks_failed = True
                                break
                    if critical_tasks_failed:
                        current_process_status = "ERROR"
                    elif current_process_status != "STOPPING": # Don't override STOPPING
                        current_process_status = "RUNNING" # If no critical failures and not stopping
                elif current_process_status != "STOPPING": # If tasks are running and not stopping
                     current_process_status = "RUNNING"


                # Gather status data points
                uptime_seconds = (datetime.now(timezone.utc) - self.bot_start_time).total_seconds()
                active_subs = await self.state.get_token_subscriptions() # This is from bot's GlobalState
                
                sol_balance = await self.state.get_current_sol_balance()
                sol_price = await self.state.get_sol_price()
                sol_balance_usd = (sol_balance * sol_price) if sol_balance is not None and sol_price is not None else 0.0

                # Example: Get counts for active tasks (excluding self and other utility tasks)
                # This is a simple count, more sophisticated tracking might be needed
                active_async_tasks = [
                    t for t in asyncio.all_tasks(loop=self.loop) 
                    if not t.done() and t is not asyncio.current_task()
                ]


                # Key configuration items to display (be selective)
                # Use self._filter_serializable_config to ensure it's JSON friendly
                config_summary = self._filter_serializable_config({
                    "SOL_TO_BUY": self.config.get("SOL_TO_BUY"),
                    "INITIAL_STOP_LOSS_PERCENT": self.config.get("INITIAL_STOP_LOSS_PERCENT"),
                    "FIRST_SELL_PERCENT": self.config.get("FIRST_SELL_PERCENT"),
                    "TRAILING_STOP_LOSS_PERCENT": self.config.get("TRAILING_STOP_LOSS_PERCENT"),
                    "DEFAULT_VOLUME_THRESHOLD": self.config.get("DEFAULT_VOLUME_THRESHOLD"),
                    "DEFAULT_MARKETCAP_THRESHOLD": self.config.get("DEFAULT_MARKETCAP_THRESHOLD"),
                    "RL_AGENT_ACTIVE": bool(self.rl_agent) # Indicate if RL agent is loaded
                })
                
                rl_status_info = "Not Loaded"
                if self.rl_agent:
                    # Placeholder: In a real scenario, you might get more detailed status from the agent
                    # For example, if your RLAgentManager has a get_status method:
                    # rl_status_info = self.rl_agent_manager.get_status() # if you have such a manager
                    rl_status_info = "Loaded & Active"


                status_data = {
                    "bot_process_status": current_process_status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": int(uptime_seconds),
                    "active_token_subscriptions_count": len(active_subs),
                    # "active_token_subscriptions_list": list(active_subs)[:20], # Example: limit list size
                    "current_sol_balance": round(sol_balance, 6) if sol_balance is not None else None,
                    "current_sol_price_usd": round(sol_price, 4) if sol_price is not None else None,
                    "current_portfolio_value_usd": round(sol_balance_usd, 2),
                    "rugcheck_queue_size": self.state.get_rugcheck_queue().qsize(),
                    "socialscheck_queue_size": self.state.get_socialscheck_queue().qsize(),
                    "asyncio_tasks_count": len(active_async_tasks), # Tasks in bot's loop
                    "config_summary": config_summary,
                    "rl_agent_status": rl_status_info,
                    # Add other fields as needed:
                    # "last_buy_check_ts": self.trading_manager.last_buy_check_ts.isoformat() if self.trading_manager and hasattr(self.trading_manager, 'last_buy_check_ts') else None,
                    # "last_sell_check_ts": self.trading_manager.last_sell_check_ts.isoformat() if self.trading_manager and hasattr(self.trading_manager, 'last_sell_check_ts') else None,
                }

                self._write_status(status_data)
                await asyncio.sleep(5) # Update status every 5 seconds

            except asyncio.CancelledError:
                log_info(":stop_sign: Status updater task shutting down.")
                break # Exit loop
            except Exception as e:
                log_error(f":x: Error in status updater: {e}", exc_info=True)
                # Write an error status if the updater itself fails critically
                self._write_status({"bot_process_status": "ERROR_IN_STATUS_UPDATER", "error_message": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
                await asyncio.sleep(15) # Wait longer on error to avoid spamming logs
        
        # Final status write on shutdown
        log_info("Status updater task finished. Writing final STOPPED status.")
        self._write_status({"bot_process_status": "STOPPED", "timestamp": datetime.now(timezone.utc).isoformat()})

    async def monitor_tasks(self):
        """Monitor and log the status of background tasks."""
        try:
            while not self.state.shutdown_event.is_set():
                try:
                    rug_queue_size = self.state.get_rugcheck_queue().qsize()
                    tokens_subscribed = list(await self.state.get_token_subscriptions())
                    task_status = [f"{task.get_name()}: {'[bold yellow]done[/bold yellow]' if task.done() else '[bold green]running[/bold green]'}\n" for task in self.tasks]
                    sol_amount = await self.state.get_current_sol_balance()

                    # Add RL agent status if loaded
                    rl_status = f"[bold cyan]│[/bold cyan] :brain: [bold]RL Agent:[/bold] {'Loaded' if self.rl_agent else 'Not Loaded'}\n"

                    log_debug(
                        f"\n"
                        f"[bold cyan]┌────────────────────────────────────[/bold cyan]\n"
                        f"[bold cyan]│[/bold cyan] :robot: [bold magenta]Task Monitor[/bold magenta]\n"
                        f"[bold cyan]│────────────────────────────────────[/bold cyan]\n"
                        f"{rl_status}" # Add RL status here
                        f"[bold cyan]│[/bold cyan] :moneybag: [bold]Actual SOL amount:[/bold] {sol_amount:.6f}\n"
                        f"[bold cyan]│[/bold cyan] :label: [bold]Subscribed tokens:[/bold] {len(tokens_subscribed)}\n"
                        f"[bold cyan]│[/bold cyan] :recycle: [bold]RugCheck Queue size:[/bold] {rug_queue_size}\n"
                        f"[bold cyan]│[/bold cyan] :gear: [bold]Active tasks:[/bold] {len([t for t in self.tasks if not t.done()])}/{len(self.tasks)}\n"
                        f"[bold cyan]│[/bold cyan] :clipboard: [bold]Tasks:[/bold]\n"
                        f"[bold cyan]├──[/bold cyan] {'[bold cyan]├──[/bold cyan] '.join(task_status)}"
                        f"[bold cyan]└────────────────────────────────────[/bold cyan]\n"
                    )
                    await asyncio.sleep(5)
                except Exception as e:
                    log_error(f":x: [bold red]Monitor task error[/bold red]: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(60) # Sleep longer if monitor loop has error
        except asyncio.CancelledError:
            log_info(":stop_sign: Monitor task shutting down")

    async def command_listener(self):
        """Periodically checks the command file for commands."""
        last_command_content = None
        try:
            while not self.state.shutdown_event.is_set():
                current_command_content = None
                try:
                    if os.path.exists(COMMAND_FILE):
                        with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                            current_command_content = f.read().strip()

                        if current_command_content and current_command_content != last_command_content:
                            log_info(f"Received command via {COMMAND_FILE}: '{current_command_content}'")
                            last_command_content = current_command_content

                            command_upper = current_command_content.upper()
                            
                            # --- Process Commands ---
                            if command_upper == "STOP":
                                log_info(":hand: STOP command processed. Initiating shutdown...")
                                self.state.trigger_shutdown()
                            elif command_upper == "STOP_BUYING":
                                log_info("🚫 STOP_BUYING command processed. No new buy orders will be placed.")
                                self.state.is_buying_enabled = False
                            elif command_upper == "START_BUYING":
                                log_info("✅ START_BUYING command processed. New buy orders are now allowed.")
                                self.state.is_buying_enabled = True
                            elif command_upper.startswith("SELL_"):
                                mint_to_sell = current_command_content[len("SELL_"):]
                                log_info(f"SELL command processed for mint: {mint_to_sell}")
                                if self.trading_manager:
                                    # Non-blocking call
                                    asyncio.create_task(self.trading_manager.execute_manual_sell(mint_to_sell))
                                else:
                                    log_warning("TradingManager not ready for SELL command.")
                            elif command_upper == "UNSUB_NEWTOKEN":
                                log_info(":no_bell: UNSUB_NEWTOKEN command processed.")
                                if self.ws_handler:
                                    asyncio.create_task(self.ws_handler.unsubscribe_new_tokens())
                                else:
                                    log_warning("WS handler not ready for UNSUB_NEWTOKEN.")
                            elif command_upper.startswith("UNSUB_TOKEN_TRADES_"):
                                mint_to_unsubscribe = current_command_content[len("UNSUB_TOKEN_TRADES_"):]
                                log_info(":no_bell: UNSUB_TOKEN_TRADES command processed.")
                                if self.ws_handler:
                                    asyncio.create_task(self.ws_handler.unsubscribe_token_trades(mint_to_unsubscribe, 'manual_unsubscribe'))
                                else:
                                    log_warning("WS handler not ready for UNSUB_NEWTOKEN.")
                            else:
                                log_warning(f"Unknown command '{current_command_content}' in {COMMAND_FILE}. Ignoring.")
                            
                            # Clear command file after processing any command
                            try:
                                with open(COMMAND_FILE, 'w', encoding='utf-8') as f_clear: f_clear.write("")
                            except OSError as e_clear: 
                                log_error(f"Error clearing command file: {e_clear}")
                            
                            if command_upper == "STOP":
                                break # Exit listener loop on STOP command

                        elif not current_command_content and last_command_content:
                            last_command_content = None

                except IOError as e:
                    log_error(f"Error reading command file {COMMAND_FILE}: {e}")
                except Exception as e:
                    log_error(f"Unexpected error in command listener: {e}", exc_info=True)

                await asyncio.sleep(5)
        except asyncio.CancelledError:
            log_info(":stop_sign: Command listener task shutting down.")
        finally:
             log_debug("Command listener task finished.")

    async def shutdown(self):
        if self.state.shutdown_event.is_set() and getattr(self, '_shutdown_called', False):
            log_debug("Shutdown already called and in progress.")
            return
        self._shutdown_called = True # Mark that shutdown has been called

        log_info(":stop_button: [bold red]Shutdown initiated[/bold red]. Cleaning up resources...")
        # Initial status write, status_updater will write final STOPPED
        self._write_status({"bot_process_status": "STOPPING", "timestamp": datetime.now(timezone.utc).isoformat()})
        self.state.trigger_shutdown()

        if self.ws_handler:
            try:
                log_info("Attempting WebSocket shutdown...")
                await asyncio.wait_for(self.ws_handler.shutdown(), timeout=15.0)
                log_info(":link: WebSocket shutdown complete.")
            except asyncio.TimeoutError:
                 log_warning("WebSocket shutdown timed out.")
            except Exception as e:
                log_error(f":x: WebSocket shutdown error: {e}", exc_info=True)
        else:
            log_info("WebSocket handler not initialized, skipping its shutdown.")

        active_tasks_before_cancel = [t for t in self.tasks if t and not t.done()]
        log_info(f"Cancelling {len(active_tasks_before_cancel)} managed tasks...")
        for task in active_tasks_before_cancel:
            task.cancel()
            log_debug(f":no_entry: Sent cancel request to task: {task.get_name()}")

        # Wait for tasks to actually cancel
        if active_tasks_before_cancel:
            results = await asyncio.gather(*active_tasks_before_cancel, return_exceptions=True)
            for i, result in enumerate(results):
                task_name = active_tasks_before_cancel[i].get_name()
                if isinstance(result, asyncio.CancelledError):
                    log_debug(f"Task {task_name} cancelled successfully.")
                elif isinstance(result, Exception):
                    log_error(f"Task {task_name} raised an exception during cancellation: {result}", exc_info=result)
                # else: log_debug(f"Task {task_name} finished with result: {result}") # If it completed normally before cancel took effect
            log_info("All managed tasks processed for cancellation.")


        if self.db_client and self.db_client.pool:
            try:
                 await self.db_client.backup_creator_wallets() # Backup before closing
            except Exception as e:
                log_error(f":x: Error backing up creator wallets: {e}", exc_info=True)
            try:
                log_info("Closing database connection pool...")
                await self.db_client.close()
                log_info(":electric_plug: Database connection pool closed.")
            except Exception as e:
                 log_error(f"Error closing database pool: {e}", exc_info=True)
        else:
            log_info("DB client not connected or pool not initialized, skipping DB cleanup.")

        # Final status is written by status_updater's finally block
        log_info(":checkered_flag: Bot shutdown sequence complete.")
        # Force exit if some non-daemon threads/tasks are stuck (use with caution)
        # os._exit(0)

    # --- RL Agent Integration Functions ---
    async def _get_live_observation(self) -> np.ndarray | None:
        """
        Gathers LIVE market and portfolio data and formats it into the
        observation format expected by the RL agent. Includes normalization.
        Returns None if essential data is missing or calculation fails.
        **NOTE:** This requires significant implementation based on live data sources.
        """
        log_debug("Attempting to generate live observation for RL agent...")
        obs_data = {} # Dictionary to hold raw feature values

        # --- Fetch Portfolio State ---
        try:
            obs_data['sol_balance'] = await self.state.get_current_sol_balance()
            active_positions = await self.db_client.get_active_buy_positions() # Assumes this returns quickly
            # Simplification: Focus observation on the *first* active position if multiple exist
            current_pos = active_positions[0] if active_positions else None
            obs_data['is_holding'] = 1.0 if current_pos else 0.0
        except Exception as e:
            log_error(f"Failed to get portfolio state for observation: {e}")
            return None

        # --- Fetch Market State (Focus on current position's mint if holding) ---
        target_mint = current_pos['mint'] if current_pos else None

        if target_mint:
            try:
                # Price, Volume, MC (Needs efficient fetching - maybe latest from DB?)
                latest_prices = await self.db_client.get_latest_prices([target_mint])
                if target_mint in latest_prices:
                    obs_data['current_price'] = latest_prices[target_mint]['price']
                    obs_data['market_cap'] = latest_prices[target_mint]['market_cap'] # Assuming SOL MC
                else:
                    log_warning(f"Could not get latest price/MC for active mint {target_mint}")
                    obs_data['current_price'] = current_pos['buy_price'] # Fallback? Risky
                    obs_data['market_cap'] = 0.0

                # --- Fetch recent trades for volume/volatility (Example DB Query) ---
                # This query needs optimization for speed in live trading
                query_recent = """
                    SELECT price, sol_amount as volume FROM trades
                    WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '10 minutes'
                    ORDER BY timestamp DESC LIMIT 100;
                """ # Adjust interval/limit as needed
                recent_trades = await self.db_client.pool.fetch(query_recent, target_mint)
                if recent_trades:
                    recent_df = pd.DataFrame(recent_trades, columns=['price', 'volume'])
                    obs_data['volume'] = recent_df['volume'].sum() # Example: sum volume
                    # Calculate volatility (needs sufficient points)
                    if len(recent_df) > 5:
                        prices_series = pd.Series(pd.to_numeric(recent_df['price'], errors='coerce'), index=pd.to_datetime(recent_df['timestamp'], errors='coerce', utc=True)).sort_index() # Create Series with time index
                        prices_series = prices_series.dropna()
                        # Use appropriate window size (e.g., matching training or a reasonable live window)
                        obs_data['volatility'] = calculate_volatility(prices_series, window=20) # Example window
                    else:
                        obs_data['volatility'] = 0.0
                else:
                    obs_data['volume'] = 0.0
                    obs_data['volatility'] = 0.0


                # Scores (Fetch latest from DB - needs dedicated functions)
                # obs_data['rugcheck_score'] = await self.db_client.get_latest_score(target_mint, 'rugcheck')
                # obs_data['socials_score'] = await self.db_client.get_latest_score(target_mint, 'socials')
                obs_data['rugcheck_score'] = 10000 # Placeholder
                obs_data['socials_score'] = 100 # Placeholder

                # Token creation time
                # token_info = await self.db_client.get_token_info(target_mint) # Needs function
                # obs_data['creation_time'] = token_info['timestamp'] if token_info else pd.NaT
                obs_data['creation_time'] = pd.NaT # Placeholder

            except Exception as e:
                log_error(f"Failed to get market state for {target_mint}: {e}")
                return None # Can't proceed without market data if holding
        else:
            # If not holding, what state to use? Average market state? Random token?
            # Simplest: return a 'neutral' state or zeros.
            log_debug("Not holding any position, generating neutral observation.")
            # Use defaults or averages if possible, otherwise zeros
            obs_data['current_price'] = 0.0
            obs_data['market_cap'] = 0.0
            obs_data['volume'] = 0.0
            obs_data['volatility'] = 0.0
            obs_data['rugcheck_score'] = 10000
            obs_data['socials_score'] = 100
            obs_data['creation_time'] = pd.NaT


        # --- Calculate Derived Features ---
        # Needs access to historical prices (e.g., stored in state_manager or queried)
        # This part is complex for live data - requires maintaining price history
        obs_data['price_change_1'] = 0.0 # Placeholder
        obs_data['price_change_5'] = 0.0 # Placeholder
        obs_data['price_change_10'] = 0.0 # Placeholder

        time_since_creation_seconds = 0
        if pd.notna(obs_data.get('creation_time')):
            time_diff = datetime.now(timezone.utc) - obs_data['creation_time'].replace(tzinfo=timezone.utc) # Ensure tz
            time_since_creation_seconds = max(0, time_diff.total_seconds())

        position_pnl_norm = 0.0
        steps_holding = 0 # How to track 'steps' live? Use time held instead.
        if obs_data['is_holding'] and current_pos:
            # Calculate PnL based on live price and DB data
            buy_price = float(current_pos['buy_price'])
            rem_tokens = float(current_pos['remaining_tokens'])
            total_investment = float(current_pos.get('total_investment_sol', 1.0) or 1.0)
            current_value = obs_data.get('current_price', buy_price) * rem_tokens
            initial_cost_for_remaining = buy_price * rem_tokens
            unrealized_pnl = current_value - initial_cost_for_remaining
            position_pnl_norm = unrealized_pnl / total_investment
            # Calculate time held instead of steps
            # time_held_seconds = (datetime.now(timezone.utc) - current_pos['timestamp'].replace(tzinfo=timezone.utc)).total_seconds()
            # steps_holding = time_held_seconds / 10 # Approximate steps if using 10s intervals

        # --- Normalization (MUST MATCH TRAINING ENV) ---
        # Apply the *exact same* normalization logic used in _get_observation
        norm_price_change_1 = np.clip(obs_data['price_change_1'] * 20, -1, 1)
        norm_price_change_5 = np.clip(obs_data['price_change_5'] * 10, -1, 1)
        norm_price_change_10 = np.clip(obs_data['price_change_10'] * 5, -1, 1)
        norm_volatility = np.clip(obs_data['volatility'] * 10, 0, 1)
        norm_market_cap = np.clip(np.log10(obs_data['market_cap'] + 1e-9) / 7, -1, 1)
        norm_volume = np.clip(np.log10(obs_data['volume'] + 1e-9) / 5, -1, 1)
        norm_rugcheck = np.clip(1.0 - (obs_data['rugcheck_score'] / 1000.0), 0, 1)
        norm_socials = np.clip(1.0 - (obs_data['socials_score'] / 100.0), 0, 1)
        norm_time_creation = np.clip(np.log10(time_since_creation_seconds + 1) / 6, 0, 1)
        norm_pos_pnl = np.clip(position_pnl_norm, -1, 1)
        norm_steps_held = np.clip(steps_holding / (rl_config.MAX_STEPS_PER_EPISODE * 0.5), 0, 1) # Or use normalized time held
        norm_sol_balance = np.clip(obs_data['sol_balance'] / (rl_config.RL_INITIAL_CAPITAL * 2.0), 0, 1)

        # --- Calculate Time Features ---
        current_timestamp = datetime.now(timezone.utc)
        # Weekday: Monday=0, Sunday=6. Normalize to [0, 1].
        weekday = current_timestamp.weekday()
        norm_weekday = weekday / 6.0 if 6.0 > 0 else 0.0 # Avoid division by zero

        # Daytime: Hour of the day (0-23). Normalize to [0, 1].
        hour = current_timestamp.hour
        norm_daytime = hour / 23.0 if 23.0 > 0 else 0.0 # Avoid division by zero

        # --- Normalize Tunable Parameters ---
        norm_tunable_params = []
        epsilon = 1e-9 # Use a small epsilon for division by zero avoidance
        for param_name, low, high, p_type in rl_config.RL_TUNABLE_PARAMETERS:
            # Get current value from bot's config, use midpoint if not found
            current_val = self.config.get(param_name.upper(), (low + high) / 2.0)

            # Ensure current_val is the correct type for normalization
            if p_type == int:
                 current_val = int(current_val)
            else:
                 current_val = float(current_val)

            # Min-Max Normalization: (value - min) / (max - min)
            if high - low > epsilon: # Avoid division by zero
                norm_val = (current_val - low) / (high - low)
            else:
                norm_val = 0.0 # Or 0.5 if min == max, depending on desired behavior

            # Clip to ensure it's within [0, 1] after normalization
            norm_tunable_params.append(np.clip(norm_val, 0.0, 1.0))


        # --- Construct Raw Observation Vector (Order MUST match rl_config.OBSERVATION_FEATURES) ---
        # Ensure the order matches the list in rl_config.py
        raw_observation_list = [
            norm_price_change_1, norm_price_change_5, norm_price_change_10,
            norm_volatility, norm_market_cap, norm_volume,
            norm_rugcheck, norm_socials, norm_time_creation,
            obs_data['is_holding'], norm_pos_pnl, norm_steps_held, norm_sol_balance,
            norm_weekday, norm_daytime # Add new time features
        ]
        # Add normalized tunable parameters
        raw_observation_list.extend(norm_tunable_params)

        try:
            raw_observation = np.array(raw_observation_list, dtype=np.float32)

            # --- Apply VecNormalize (CRITICAL for live deployment) ---
            if self.vec_normalize:
                # VecNormalize expects a batch, so reshape the single observation
                normalized_observation = self.vec_normalize.normalize_obs(raw_observation.reshape(1, -1))
                observation = normalized_observation[0] # Extract the single observation from the batch
                log_debug(f"Generated and normalized live observation: {observation}")
            else:
                log_warning("VecNormalize not loaded. Live observations will NOT be normalized.")
                observation = raw_observation # Use raw observation if normalization is not available

            # --- Final Validation ---
            if observation.shape != (rl_config.OBSERVATION_SPACE_DIM,) or not np.all(np.isfinite(observation)):
                log_error(f"Live observation generation failed after normalization! Shape: {observation.shape}, Expected: {(rl_config.OBSERVATION_SPACE_DIM,)}, Finite: {np.all(np.isfinite(observation))}")
                # Log the observation list and its length for debugging
                log_error(f"Observation list length: {len(raw_observation_list)}, Expected: {rl_config.OBSERVATION_SPACE_DIM}")
                log_error(f"Observation list content (first 20): {raw_observation_list[:20]}")
                return None

            # Clip the final observation to the defined bounds [-1, 1]
            observation = np.clip(observation, rl_config.OBSERVATION_LOW, rl_config.OBSERVATION_HIGH)


            return observation

        except Exception as e:
            log_error(f"Error constructing or normalizing live observation array: {e}", exc_info=True)
            return None

    async def run_rl_agent_updates(self):
        """Periodically query the RL agent and update trading parameters."""
        if not self.rl_agent:
            log_info("RL agent not loaded, skipping RL update task.")
            return

        log_info(":brain: Starting RL agent parameter update task...")
        while not self.state.shutdown_event.is_set():
            try:
                start_time = time.time()
                # 1. Get Live Observation
                observation = await self._get_live_observation()

                if observation is not None:
                    # 2. Predict Action (Parameters)
                    # Use deterministic=True for exploitation during live trading
                    action, _ = self.rl_agent.predict(observation, deterministic=True)
                    log_debug(f"RL Agent raw action output: {action}")

                    # 3. Apply Action (Update self.config used by TradingManager)
                    updated_params_count = 0
                    for i, (param_name, low, high, p_type) in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
                         # Clip action to ensure it's within training bounds
                        val = np.clip(action[i], low, high)
                        # Convert type if necessary (e.g., for int parameters)
                        current_val = p_type(val)
                        # Only log if value changes significantly?
                        if param_name in self.config and self.config[param_name] != current_val:
                             log_info(f"RL Agent Update: '{param_name}' changed from {self.config[param_name]} -> {current_val}")
                             self.config[param_name] = current_val # Update the shared config dictionary
                             updated_params_count += 1
                        elif param_name not in self.config:
                             log_info(f"RL Agent Update: Setting '{param_name}' -> {current_val}")
                             self.config[param_name] = current_val
                             updated_params_count += 1


                    if updated_params_count > 0:
                         log_info(f"Applied {updated_params_count} parameter updates from RL agent.")
                         # Pass the updated config to TradingManager if necessary,
                         # or ensure TradingManager reads from the updated self.config
                         if self.trading_manager:
                              self.trading_manager.config = self.config # Ensure manager uses the updated dict
                    else:
                         log_debug("RL Agent parameters did not change significantly.")

                else:
                    log_warning("Failed to get live observation for RL agent. Skipping parameter update.")

                # 4. Wait for the next interval
                end_time = time.time()
                wait_time = max(0, rl_config.AGENT_ACTION_INTERVAL_SECONDS - (end_time - start_time))
                await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                log_info(":no_entry_sign: RL agent update task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in RL agent update loop: {e}", exc_info=True)
                await asyncio.sleep(rl_config.AGENT_ACTION_INTERVAL_SECONDS) # Wait before retrying on error

    # --- End RL Agent Integration Functions ---

    async def main(self):
        self._write_status({"bot_process_status": "STARTING", "timestamp": datetime.now(timezone.utc).isoformat()})
        is_main_thread = threading.current_thread() is threading.main_thread()

        if is_main_thread:
            if not self.no_log_rotate:
                log_info("Running in main thread. Log rotation enabled. Performing log rotation...")
                rotate_log_file() # Rotate log file at the very start
            else:
                log_info("Running in main thread. Log rotation disabled by controller.")
            self.register_signal_handlers() # Register signals if in main thread
        else:
             log_info("Running in a secondary thread. Skipping log rotation and signal handlers.")
        
        
        setup_logging() # Setup logging regardless

        # --- Load GA Parameters (if provided and RL not active) ---
        if self.params_file and not self.rl_agent_path:
            log_info(f":dna: Attempting to load GA optimized parameters from: {self.params_file}")
            if os.path.exists(self.params_file):
                try:
                    with open(self.params_file, 'r') as f:
                        optimized_data = json.load(f)
                    optimized_params = optimized_data.get('best_solution_parameters')
                    if optimized_params:
                        log_info(f":white_check_mark: Found {len(optimized_params)} GA optimized parameters.")
                        for key, value in optimized_params.items():
                            key_upper = key.upper() # Ensure uppercase for consistency
                            if key_upper in self.config:
                                original_type = type(self.config[key_upper])
                                try: # Attempt type conversion
                                    self.config[key_upper] = original_type(value)
                                except (ValueError, TypeError):
                                    log_warning(f"Could not convert GA param '{key_upper}' value '{value}' to type {original_type}. Using as is.")
                                    self.config[key_upper] = value
                            else:
                                log_warning(f"GA Param '{key_upper}' not found in base config. Adding anyway.")
                                self.config[key_upper] = value
                        log_info(":sparkles: Merged GA optimized parameters into active configuration.")
                    else:
                        log_warning(f":warning: 'best_solution_parameters' not found in {self.params_file}.")
                except Exception as e:
                    log_error(f":x: Error loading GA parameters file {self.params_file}: {e}. Using base/default config.", exc_info=True)
            else:
                 log_warning(f":warning: GA Parameter file not found: {self.params_file}. Using base/default config.")

        # --- Load RL Agent and VecNormalize (if provided) ---
        if self.rl_agent_path:
            if not RL_AVAILABLE:
                log_error(":x: RL Agent path specified, but Stable Baselines3 library is not installed!")
            else:
                log_info(f":brain: Attempting to load RL agent from: {self.rl_agent_path}")
                if os.path.exists(self.rl_agent_path):
                    try:
                        AgentClass = PPO # Or determine from rl_config.RL_ALGORITHM
                        self.rl_agent = AgentClass.load(self.rl_agent_path, device='cpu') # Specify device
                        log_info(f":white_check_mark: Successfully loaded RL agent: {self.rl_agent_path}")

                        # Attempt to load corresponding VecNormalize stats
                        vec_normalize_path = self.rl_agent_path.replace('_final.zip', '_vecnormalize.pkl').replace('.zip', '_vecnormalize.pkl') # Infer path
                        if os.path.exists(vec_normalize_path):
                            try:
                                # Create a dummy environment to load stats into
                                from rl_environment import TradingEnv # Import TradingEnv
                                # Need dummy env with correct observation space shape
                                # The actual data doesn't matter, only the observation space structure
                                dummy_env = TradingEnv(historical_data_dict={'dummy_mint': pd.DataFrame(np.zeros((1, len(['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'rugcheck_score', 'socials_score', 'token_creation_time']))), columns=['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'rugcheck_score', 'socials_score', 'token_creation_time'], index=pd.DatetimeIndex([datetime.now(timezone.utc)], tz=timezone.utc))}, token_lifespans={'dummy_mint': {'start_ts': datetime.now(timezone.utc), 'end_ts': datetime.now(timezone.utc) + timedelta(days=1)}}, initial_capital=rl_config.RL_INITIAL_CAPITAL, max_steps=rl_config.MAX_STEPS_PER_EPISODE)

                                self.vec_normalize = VecNormalize.load(vec_normalize_path, venv=DummyVecEnv([lambda: dummy_env])) # Load stats into dummy VecEnv
                                self.vec_normalize.training = False # Set to evaluation mode
                                self.vec_normalize.norm_reward = False # Do not normalize rewards in live bot
                                log_info(f":white_check_mark: Successfully loaded VecNormalize stats from: {vec_normalize_path}")
                            except Exception as vn_load_err:
                                log_error(f":x: Failed to load VecNormalize stats from {vec_normalize_path}: {vn_load_err}", exc_info=True)
                                self.vec_normalize = None # Ensure it's None if loading fails
                        else:
                            log_warning(f":warning: VecNormalize stats file not found: {vec_normalize_path}. Live observations will NOT be normalized.")
                            self.vec_normalize = None

                        if self.params_file:
                            log_warning(":information_source: RL agent loaded, GA parameters file will be ignored for initial config (RL will override).")
                    except Exception as e:
                        log_error(f":x: Failed to load RL agent from {self.rl_agent_path}: {e}", exc_info=True)
                        self.rl_agent = None
                        self.vec_normalize = None # Also set VecNormalize to None if agent fails to load
                else:
                    log_warning(f":warning: RL Agent file not found: {self.rl_agent_path}. Cannot use RL agent.")
                    self.rl_agent = None
                    self.vec_normalize = None # Also set VecNormalize to None if agent file not found

        # --- Initialize DYNAMIC_CONFIG_FILE ---
        try:
            if not os.path.exists(DYNAMIC_CONFIG_FILE):
                log_info(f"{DYNAMIC_CONFIG_FILE} not found. Writing initial active configuration...")
                # Filter for JSON serializable before writing
                config_to_write = self._filter_serializable_config(self.config)
                with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config_to_write, f, indent=4)
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
            else:
                log_info(f"Found existing {DYNAMIC_CONFIG_FILE}. Bot will use its contents for dynamic updates if changed.")
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
        except Exception as e:
             log_error(f"Error handling initial dynamic config file {DYNAMIC_CONFIG_FILE}: {e}", exc_info=True)
             self._last_dynamic_config_mtime = 0

        log_debug(f":wrench: FINAL INITIAL CONFIG in use by bot: {self.config}")


        # --- Database and Services Setup ---
        try:
            # Pass the active self.config to DatabaseClient if its __init__ expects it
            self.db_client = DatabaseClient(config_dict=self.config)
            await self.db_client.connect()
            await self.state.set_db_client(self.db_client) # Store in GlobalState for other modules

            if self.backup: # From command line arg
                log_info(":floppy_disk: Starting database backup...")
                await self.db_client.backup_db(backup_flag=True)
            if self.cleanup: # From command line arg
                log_warning(":wastebasket: Starting database cleanup (dropping tables)...")
                await self.db_client.cleanup_db(cleanup_flag=True)
            
            log_info(":rocket: [bold]Initializing database schema...[/bold]")
            # await self.db_client.init_db()
            # await self.db_client.restore_creator_wallets()
            # log_info(":white_check_mark: Database schema initialized and wallets restored.")

        except Exception as db_setup_err:
            log_critical(f"CRITICAL: Failed database setup: {db_setup_err}", exc_info=True)
            self._write_status({"bot_process_status": "ERROR_DB_SETUP", "error_message": str(db_setup_err), "timestamp": datetime.now(timezone.utc).isoformat()})
            return        

        # *** ADD INITIAL SOL PRICE FETCH HERE ***
        log_info("Attempting to fetch initial SOL price before starting other tasks...")
        try:
            initial_price_fetched = await self._fetch_initial_sol_price()
            if not initial_price_fetched:
                log_critical("🔴 Failed to fetch initial SOL price. The bot will rely on the hourly updater. Some functionalities might be delayed or impacted until the price is available.")
                # Consider if you want to halt bot startup if initial price fetch fails.
                # For now, it logs a critical error and proceeds.
            else:
                log_info("🟢 Initial SOL price fetched and set.")
        except Exception as e:
            log_critical(f"💥 Error during initial SOL price fetch: {e}. The bot will rely on the hourly updater.", exc_info=True)
            # Similar consideration for halting startup.
        # *** END OF INITIAL SOL PRICE FETCH ***

        # --- Initialize Core Components (pass self.config) ---
        self.ws_handler = WebSocketHandler(db_client=self.db_client, config_dict=self.config, state_manager=self.state)
        await self.ws_handler.connect() # Connect WS
        await self.state.set_websocket_handler(self.ws_handler) # Store in GlobalState

        socials_proc = SocialsProcessor(state=self.state, db_client=self.db_client, config_dict=self.config)
        rugchecker = Rugcheck(state=self.state, db_client=self.db_client, websocket_handler=self.ws_handler, socials_processor=socials_proc, config_dict=self.config)
        self.trading_manager = TradingManager(db_client=self.db_client, config_dict=self.config, state=self.state)


        # --- Start Background Tasks ---
        self.tasks = [
            asyncio.create_task(self.status_updater(), name="status_updater"), # Writes to bot_status.json
            asyncio.create_task(self.config_updater(), name="config_updater"), # Reads dynamic_config.json
            asyncio.create_task(self.command_listener(), name="command_listener"), # Reads bot_command.txt
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"), # Internal task logging
            
            asyncio.create_task(update_sol_price(self.state, self.db_client), name="sol_price_updater"),
            asyncio.create_task(trade_worker(), name="trade_worker"), # Uses self.state.db_client
            rugchecker.start(), # Returns a task
            socials_proc.start(), # Returns a task
            
            asyncio.create_task(self.run_buy_checks(), name="buy_opportunity_checker"),
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker"),
        ]
        self.tasks.extend(self.ws_handler.start()) # Add WebSocket handler's tasks
        self.tasks.append(asyncio.create_task(self.run_heartbeat_emitter(), name="heartbeat_emitter"))

        if self.rl_agent:
            self.tasks.append(asyncio.create_task(self.run_rl_agent_updates(), name="rl_agent_updater"))
        
        # Initial status update to RUNNING after all tasks are launched
        # status_updater will take over from here.
        # self._write_status({"bot_process_status": "RUNNING", "timestamp": datetime.now(timezone.utc).isoformat()})
        # No, status_updater will set it to RUNNING on its first successful pass.

        log_info(":rocket: [bold green]Trading bot core components started.[/bold green]")
        try:
            # Wait for any task to complete (e.g., if shutdown is triggered, command_listener might exit)
            # Or if a critical task errors out.
            done, pending = await asyncio.wait(self.tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # If we are here, one of the main tasks has finished.
            # Check if it was due to an error or normal completion (like shutdown signal)
            for task in done:
                if task.exception():
                    log_critical(f"Task {task.get_name()} exited with exception: {task.exception()}", exc_info=task.exception())
                    self.state.trigger_shutdown() # Trigger shutdown if a task crashes
                else:
                    log_info(f"Task {task.get_name()} completed.")
            
            # If shutdown wasn't triggered by the completed task, wait for the shutdown event
            if not self.state.shutdown_event.is_set():
                log_info("A task completed, but shutdown not triggered. Waiting for shutdown signal...")
                await self.state.wait_for_shutdown()

        except Exception as e:
            log_critical(f"CRITICAL ERROR in bot's main execution: {e}", exc_info=True)
            self.state.trigger_shutdown() # Ensure shutdown is triggered on any main error
        finally:
            log_info("Main execution loop ended. Proceeding to full shutdown.")
            # The shutdown method will handle cancelling remaining tasks and cleanup.
            # No need to call self.shutdown() here as it's called in the final `finally` block of the script's entry point

    async def run_heartbeat_emitter(self): # Add this as a new async method in TradingBot
        log_debug("❤️ Heartbeat emitter started.")
        try:
            if self.db_client: # Ensure db_client is available
                await self.db_client.insert_heartbeat(event_type="STARTUP")
        except Exception as e:
            log_error(f"Error in heartbeat emitter: {e}", exc_info=True)
            
        HEARTBEAT_INTERVAL_SECONDS = self.config.get('HEARTBEAT_EMIT_INTERVAL_SECONDS', 60) # e.g., every 60 seconds, make configurable
        while not self.state.shutdown_event.is_set():
            try:
                if self.db_client: # Ensure db_client is available
                    await self.db_client.insert_heartbeat()
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                log_debug("❤️ Heartbeat emitter task cancelled.")
                break
            except Exception as e:
                log_error(f"Error in heartbeat emitter: {e}", exc_info=True)
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS) # Still wait before retrying

    async def run_buy_checks(self):
        log_info(":chart_with_upwards_trend: [bold]Starting buy opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: # Ensure manager is initialized
                    await self.trading_manager.check_trading_opportunities()
                else:
                    log_warning("TradingManager not initialized, buy checks skipped.")
                await asyncio.sleep(self.config.get('BUY_CHECK_INTERVAL', 10)) # Use configured interval
            except asyncio.CancelledError:
                log_info(":no_entry_sign: Buy checker task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in buy checker loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.get('BUY_CHECK_ERROR_RETRY_INTERVAL', 30))

    async def run_sell_checks(self):
        log_info(":chart_with_downwards_trend: [bold]Starting sell opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: # Ensure manager is initialized
                    await self.trading_manager.check_sell_opportunities()
                else:
                    log_warning("TradingManager not initialized, sell checks skipped.")
                await asyncio.sleep(self.config.get('SELL_CHECK_INTERVAL', 3)) # Use configured interval
            except asyncio.CancelledError:
                log_info(":no_entry_sign: Sell checker task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in sell checker loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.get('SELL_CHECK_ERROR_RETRY_INTERVAL', 12))

# --- Main Script Entry Point (if running trading_bot.py directly) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file containing optimized parameters from GA.")
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")
    parser.add_argument("--no-log-rotate", action="store_true", help="Disable log rotation on startup (used when run by a controller).")
    args = parser.parse_args()

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    bot_instance = None # Keep a reference for shutdown

    async def run_bot_async_wrapper(): # Renamed to avoid conflict
        # nonlocal bot_instance # <--- REMOVED THIS LINE
        global bot_instance # Use global if you need to modify the global bot_instance from the outer scope
                           # For this structure, direct assignment works as bot_instance is in the same scope.
                           # If run_bot_async_wrapper were truly nested inside another function
                           # that defined bot_instance, then nonlocal would be appropriate for that inner function.

        bot_instance = TradingBot(
            cleanup=args.cleanup,
            backup=args.backup,
            params_file=args.params_file,
            rl_agent_path=args.rl_agent_path,
            no_log_rotate=args.no_log_rotate # Pass the flag
        )
        try:
            await bot_instance.main()
        except (KeyboardInterrupt, SystemExit) as ki_se: # Catch explicit interrupts
            log_info(f":stop_button: [bold red]Interrupted by {type(ki_se).__name__}.[/bold red] Triggering shutdown...")
            if bot_instance and not bot_instance.state.shutdown_event.is_set():
                bot_instance.state.trigger_shutdown()
        except Exception as e: # Catch other unexpected errors from main
            log_critical(f":x: Unexpected error in bot's main execution: {e}", exc_info=True)
            if bot_instance and not bot_instance.state.shutdown_event.is_set():
                 bot_instance.state.trigger_shutdown() # Ensure shutdown is triggered
        finally:
            if bot_instance:
                log_info("Ensuring final shutdown process is called...")
                await bot_instance.shutdown() # Call the bot's shutdown method

    try:
        asyncio.run(run_bot_async_wrapper())
    except KeyboardInterrupt: # This catches interrupt if it happens outside the async wrapper's try/except
        log_info("\nTop-level KeyboardInterrupt. Bot should be shutting down.")
    except Exception as e: # Catch errors during asyncio.run itself
        log_critical(f"Fatal error during asyncio.run: {e}", exc_info=True)
    finally:
        log_info("Trading Bot script finished.")