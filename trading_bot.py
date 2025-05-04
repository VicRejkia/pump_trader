# FILE: trading_bot.py (Modified)

import argparse
import asyncio
import signal
import traceback
import inspect
import threading
import os
import time
import json
import numpy as np # <-- Add numpy import
import pandas as pd # <-- Add pandas import
from datetime import datetime, timezone, timedelta

import config as config_module
from database_handler import DatabaseClient
from trading_logic import TradingManager
from websocket_handler import WebSocketHandler
from logger import setup_logging, log_info, log_debug, log_error, log_warning, log_critical, rotate_log_file
from state_manager import GlobalState
from trade_processor import trade_worker
from sol_price_api import update_sol_price
from rugcheck_handler import Rugcheck
from socials_processor import SocialsProcessor
from utils import calculate_volatility

# --- RL Imports (add these) ---
try:
    import stable_baselines3
    # Import the specific algorithm class you trained (e.g., PPO)
    from stable_baselines3 import PPO # Or SAC, TD3, etc.
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
# Import RL config to know parameter names and observation details
import rl_config

# --- End RL Imports ---


# Define paths for communication files relative to project root
COMMAND_FILE = os.path.join('data', 'bot_command.txt')
STATUS_FILE = os.path.join('data', 'bot_status.txt')
DYNAMIC_CONFIG_FILE = os.path.join('data', 'dynamic_config.json')

class TradingBot:
    """Main class for running the trading bot."""

    # Modify __init__ to accept RL agent path
    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, rl_agent_path: str = None):
        """Initialize the TradingBot with optional cleanup, backup, GA params file, and RL agent path."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.state = GlobalState.get_instance()
        self.cleanup = cleanup
        self.backup = backup
        self.params_file = params_file # Store the GA params file path
        self.rl_agent_path = rl_agent_path # Store the RL agent path
        self.rl_agent = None # Placeholder for loaded RL agent
        self.db_client = None #DatabaseClient()
        self.ws_handler = None #WebSocketHandler(db_client=self.db_client)
        self.tasks = []

        # --- Configuration Handling ---
        self.config = {} # Holds the *active* configuration (mutable dictionary)
        self.base_config = {} # Holds the config as loaded initially from config.py
        self._load_base_config() # Load initial config into self.config and self.base_config
        # --- End Configuration Handling ---

        # Initialize trading_manager later in main after full config setup
        self.trading_manager = None
        self._write_status("INITIALIZING")
        self._last_dynamic_config_mtime = 0 # For config_updater task

    # --- Add a helper to filter non-JSON serializable types ---
    def _filter_serializable_config(self, config_dict):
        serializable_config = {}
        skipped_keys = []
        for key, value in config_dict.items():
            # Convert sets to lists for JSON serialization
            if isinstance(value, set):
                serializable_config[key] = list(value)
            elif isinstance(value, (timedelta)): # Add other types like custom classes if needed
                skipped_keys.append(key)
            else:
                serializable_config[key] = value
        if skipped_keys:
            log_debug(f"Skipped non-serializable keys when preparing config for JSON: {skipped_keys}")
        return serializable_config
    # --- End helper ---

    def _load_base_config(self):
        """Loads configuration from the config module into dictionaries."""
        try:
            loaded_config = {}
            for key in dir(config_module):
                # Load only uppercase variables that are not modules/classes/functions
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config_module, key)
                    # Check type to exclude modules etc. Be careful with complex types like timedelta
                    if not inspect.ismodule(value) and \
                       not inspect.isclass(value) and \
                       not inspect.isfunction(value):
                        loaded_config[key] = value

            self.base_config = loaded_config.copy() # Store the initial load
            self.config = loaded_config.copy() # Active config starts as base
            log_info(":gear: Base configuration loaded successfully.")
            log_debug(f"Initial Config: {self.config}") # Debug log loaded config
        except Exception as e:
            log_critical(f":x: [bold red]CRITICAL: Failed to load base configuration[/bold red]: {e}", exc_info=True)
            # Potentially raise the error or exit if config loading fails
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

    def _write_status(self, status):
        """Writes the bot's status to the status file."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                f.write(status.upper())
            log_debug(f"Status updated to: {status.upper()}")
        except IOError as e:
            log_error(f"Error writing status file {STATUS_FILE}: {e}")
        except Exception as e:
             log_error(f"Unexpected error writing status file: {e}", exc_info=True)

    #     log_info("⚙️ Dynamic config updater task shutting down.")
    async def config_updater(self):
        """Periodically checks dynamic_config.json for updates and applies them."""
        log_info(f"⚙️ Dynamic config updater started. Watching: {os.path.abspath(DYNAMIC_CONFIG_FILE)}")

        while not self.state.shutdown_event.is_set():
            await asyncio.sleep(10)  # Check every 10 seconds
            try:
                if not os.path.exists(DYNAMIC_CONFIG_FILE):
                    continue  # Nothing to do if file doesn't exist

                current_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)

                if current_mtime > self._last_dynamic_config_mtime:
                    log_info(f"Detected change in {DYNAMIC_CONFIG_FILE}. Attempting to load updates.")
                    try:
                        with open(DYNAMIC_CONFIG_FILE, 'r') as f:
                            dynamic_conf = json.load(f)

                        if not isinstance(dynamic_conf, dict):
                            log_warning(f"Invalid format in {DYNAMIC_CONFIG_FILE}: Expected JSON object. Skipping update.")
                            self._last_dynamic_config_mtime = current_mtime
                            continue

                        # Convert specific lists to sets before processing
                        set_conversions = {
                            'SOCIALS_DISALLOWED_WEBSITE_DOMAINS': set,
                            'SOCIALS_ALLOWED_NEWS_DOMAINS': set
                        }
                        for key, converter in set_conversions.items():
                            if key in dynamic_conf and isinstance(dynamic_conf[key], list):
                                dynamic_conf[key] = converter(dynamic_conf[key])

                        updated_count = 0
                        for key, value in dynamic_conf.items():
                            key_upper = key.upper()
                            if key_upper in self.config:
                                current_value = self.config[key_upper]

                                # Handle set comparisons properly
                                if isinstance(value, set) and isinstance(current_value, set):
                                    if value != current_value:
                                        self.config[key_upper] = value
                                        log_info(f"⚙️ Dynamic Config Update: '{key_upper}' changed to {value}")
                                        updated_count += 1
                                    continue

                                # Original type checking logic
                                if isinstance(value, type(current_value)) or \
                                (isinstance(value, int) and isinstance(current_value, float)):
                                    # Type conversion logic
                                    if isinstance(value, int) and isinstance(current_value, float):
                                        value_to_set = float(value)
                                    else:
                                        value_to_set = value

                                    if value_to_set != current_value:
                                        self.config[key_upper] = value_to_set
                                        log_info(f"⚙️ Dynamic Config Update: '{key_upper}' changed from {current_value} to {value_to_set}")
                                        updated_count += 1
                                else:
                                    log_warning(f"Type mismatch for '{key_upper}'. Expected {type(current_value)}, got {type(value)}. Skipping.")

                        if updated_count > 0:
                            log_info(f"Applied {updated_count} configuration updates from {DYNAMIC_CONFIG_FILE}.")
                        else:
                            log_info("No configuration values changed in dynamic config.")

                        self._last_dynamic_config_mtime = current_mtime

                    except json.JSONDecodeError as e:
                        log_error(f"JSON decode error in {DYNAMIC_CONFIG_FILE}: {e}. Skipping update.")
                    except Exception as e:
                        log_error(f"Error processing dynamic config: {e}", exc_info=True)

            except FileNotFoundError:
                if self._last_dynamic_config_mtime != 0:
                    log_info(f"{DYNAMIC_CONFIG_FILE} was removed.")
                    self._last_dynamic_config_mtime = 0
            except Exception as e:
                log_error(f"Error in config_updater loop: {e}", exc_info=True)
                await asyncio.sleep(30)

        log_info("⚙️ Dynamic config updater task shutting down.")
    # --- End config_updater task ---

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

    async def status_updater(self):
        """Periodically writes 'RUNNING' status to the status file."""
        try:
            while not self.state.shutdown_event.is_set():
                self._write_status("RUNNING")
                await asyncio.sleep(15) # Update status every 15 seconds
        except asyncio.CancelledError:
            log_info(":stop_sign: Status updater task shutting down.")
        except Exception as e:
            log_error(f":x: Error in status updater: {e}", exc_info=True)
            self._write_status("ERROR") # Write error status if updater fails
        finally:
            # Attempt to write STOPPED status when task ends, unless shutdown already happened
             if not self.state.shutdown_event.is_set():
                  self._write_status("STOPPED") # Or maybe ERROR?

    async def command_listener(self):
        """Periodically checks the command file for STOP command."""
        last_command = None
        try:
            while not self.state.shutdown_event.is_set():
                command = None
                try:
                    if os.path.exists(COMMAND_FILE):
                        with open(COMMAND_FILE, 'r') as f:
                            command = f.read().strip().upper()

                        if command == "STOP" and last_command != "STOP":
                            log_info(f":hand: Received STOP command from {COMMAND_FILE}. Initiating shutdown...")
                            self.state.trigger_shutdown() # Trigger internal shutdown
                            last_command = "STOP"
                            # Optionally delete the command file after processing
                            try:
                                os.remove(COMMAND_FILE)
                                log_debug(f"Removed command file: {COMMAND_FILE}")
                            except OSError as e:
                                log_error(f"Error removing command file {COMMAND_FILE}: {e}")
                            break # Exit listener loop once stop is triggered

                        elif command == "START" and last_command != "START":
                             log_info(f":arrow_forward: Received START command from {COMMAND_FILE}. Bot should already be starting/running.")
                             last_command = "START"
                             # Optionally delete START command file? Or leave it?
                             # If left, bot might re-log this message on restart.

                        elif command == "UNSUB_NEWTOKEN" and last_command != "UNSUB_NEWTOKEN":
                            log_info(f":no_bell: Received UNSUB_NEWTOKEN command from {COMMAND_FILE}.")
                            last_command = "UNSUB_NEWTOKEN"
                            if self.ws_handler:
                                try:
                                    await self.ws_handler.unsubscribe_new_tokens()
                                except Exception as e:
                                     log_error(f"Error calling unsubscribe_new_tokens: {e}", exc_info=True)
                            else:
                                log_warning("Cannot unsubscribe new tokens: WebSocket handler not ready.")
                            # Clear the command file after processing
                            try:
                                with open(COMMAND_FILE, 'w') as f: f.write("") # Clear file
                                log_debug(f"Cleared command file: {COMMAND_FILE}")
                            except OSError as e:
                                log_error(f"Error clearing command file {COMMAND_FILE}: {e}")

                        elif command and command not in ["START", "STOP", "UNSUB_NEWTOKEN"] and command != last_command:
                             log_warning(f"Ignoring unknown command '{command}' in {COMMAND_FILE}")
                             last_command = command # Avoid re-logging warning
                             # Clear the command file after processing unknown command
                             try:
                                 with open(COMMAND_FILE, 'w') as f: f.write("") # Clear file
                                 log_debug(f"Cleared command file: {COMMAND_FILE}")
                             except OSError as e:
                                 log_error(f"Error clearing command file {COMMAND_FILE}: {e}")

                        elif not command and last_command:
                            # If file is now empty, reset last_command to allow re-reading
                            last_command = None

                except IOError as e:
                    log_error(f"Error reading command file {COMMAND_FILE}: {e}")
                except Exception as e:
                    log_error(f"Unexpected error in command listener: {e}", exc_info=True)

                await asyncio.sleep(5) # Check command file every 5 seconds
        except asyncio.CancelledError:
            log_info(":stop_sign: Command listener task shutting down.")
        finally:
             log_debug("Command listener task finished.")

    async def shutdown(self):
        """Gracefully shut down all tasks and close resources."""
        log_info(":stop_button: [bold red]Shutdown initiated[/bold red]. Cleaning up resources...")
        self._write_status("STOPPING") # Update status during shutdown
        try:
            await asyncio.wait_for(self.ws_handler.shutdown(), timeout=60)
            log_info(":link: WebSocket shutdown complete.")
        except Exception as e:
            log_error(f":x: WebSocket shutdown error: {e}", exc_info=True)

        for task in self.tasks:
            task.cancel()
            log_debug(f":no_entry: Cancelling task: {task.get_name()}")

        # Backup creator wallets before closing the pool
        try:
            await self.db_client.backup_creator_wallets()
        except Exception as e:
            log_error(f":x: Error backing up creator wallets during shutdown: {e}", exc_info=True)

        if self.db_client and self.db_client.pool: # Check if pool exists before closing
            await self.db_client.pool.close()
            log_info(":electric_plug: Database connection closed.")
        else:
            log_info(":electric_plug: Database connection already closed or not initialized.")


        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            log_info(f"Waiting for {len(pending)} pending tasks to cancel...")
            await asyncio.gather(*pending, return_exceptions=True)
            log_info("Pending tasks cancelled.")
        else:
             log_info("No pending tasks found.")

        self._write_status("STOPPED") # Final status update
        log_info(":checkered_flag: Shutdown complete.")

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

        # --- Construct Observation Vector ---
        try:
            observation = np.array([
                norm_price_change_1, norm_price_change_5, norm_price_change_10,
                norm_volatility, norm_market_cap, norm_volume,
                norm_rugcheck, norm_socials, norm_time_creation,
                obs_data['is_holding'], norm_pos_pnl, norm_steps_held, norm_sol_balance
            ], dtype=np.float32)

            if observation.shape != (rl_config.OBSERVATION_SPACE_DIM,) or not np.all(np.isfinite(observation)):
                log_error(f"Live observation generation failed! Shape: {observation.shape}, Finite: {np.all(np.isfinite(observation))}")
                return None

            log_debug(f"Generated live observation: {observation}")
            return observation

        except Exception as e:
            log_error(f"Error constructing live observation array: {e}")
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
        """Main entry point for setting up and starting the bot."""
        self._write_status("STARTING")
        is_main_thread = threading.current_thread() is threading.main_thread()

        if is_main_thread:
            log_info("Running in main thread. Performing log rotation and registering signal handlers.")
            rotate_log_file()
        else:
             log_info("Running in a secondary thread. Skipping log rotation and signal handlers.")

        # Setup logging regardless of thread (moved from inside thread check)
        setup_logging()

        if is_main_thread:
            self.register_signal_handlers()

        # --- Load GA Parameters (if provided) ---
        if self.params_file and not self.rl_agent_path: # Only load GA if RL not specified
            log_info(f":dna: Attempting to load GA optimized parameters from: {self.params_file}")
            # ... (rest of GA param loading logic - same as before) ...
            if os.path.exists(self.params_file):
                try:
                    with open(self.params_file, 'r') as f:
                        optimized_data = json.load(f)
                    optimized_params = optimized_data.get('best_solution_parameters')
                    if optimized_params:
                        log_info(f":white_check_mark: Found {len(optimized_params)} GA optimized parameters.")
                        self.config.update(optimized_params) # Update config
                        log_info(":sparkles: Merged GA optimized parameters into configuration.")
                        overridden_keys = set(self.base_config.keys()) & set(optimized_params.keys())
                        log_debug(f"Overridden by GA: {overridden_keys}")
                    else:
                        log_warning(f":warning: 'best_solution_parameters' not found in {self.params_file}. Using base/default config.")
                except Exception as e:
                    log_error(f":x: Error loading GA parameters file {self.params_file}: {e}. Using base/default config.", exc_info=True)
            else:
                 log_warning(f":warning: GA Parameter file not found: {self.params_file}. Using base/default config.")

        # --- Load RL Agent (if provided) ---
        if self.rl_agent_path:
            if not RL_AVAILABLE:
                log_error(":x: RL Agent path specified, but Stable Baselines3 library is not installed!")
                log_error("Please install it: pip install stable-baselines3[extra]>=2.0.0a5")
                self.rl_agent_path = None # Disable RL mode
            else:
                log_info(f":brain: Attempting to load RL agent from: {self.rl_agent_path}")
                if os.path.exists(self.rl_agent_path):
                    try:
                        # Determine agent class based on config or filename convention? Assume PPO for now.
                        AgentClass = PPO # Or SAC, TD3 based on rl_config or how you save
                        self.rl_agent = AgentClass.load(self.rl_agent_path)
                        log_info(f":white_check_mark: Successfully loaded RL agent: {self.rl_agent_path}")
                        if self.params_file:
                            log_warning(":information: RL agent loaded, ignoring GA parameters file.")
                    except Exception as e:
                        log_error(f":x: Failed to load RL agent from {self.rl_agent_path}: {e}", exc_info=True)
                        self.rl_agent = None # Ensure agent is None if loading failed
                else:
                    log_warning(f":warning: RL Agent file not found: {self.rl_agent_path}. Cannot use RL agent.")
                    self.rl_agent = None

        # --- Final Config Log ---
        log_debug(f":wrench: FINAL CONFIG in use: {self.config}")
        if self.rl_agent:
             log_info(":robot: RL Agent will dynamically update parameters during runtime.")
             if self.params_file:
                log_warning(":information: RL agent loaded, ignoring GA parameters file for initial config (RL will override).")

        # --- Ensure data directory exists ---
        try:
            os.makedirs(os.path.dirname(DYNAMIC_CONFIG_FILE), exist_ok=True)
        except OSError as e:
             log_error(f"Could not create data directory '{os.path.dirname(DYNAMIC_CONFIG_FILE)}': {e}")
             # Decide if this is critical - maybe continue if dir already exists?

        # --- Write Initial Config to JSON if it doesn't exist ---
        try:
            if not os.path.exists(DYNAMIC_CONFIG_FILE):
                log_info(f"{DYNAMIC_CONFIG_FILE} not found. Writing initial configuration...")
                # Filter out non-serializable types before writing
                config_to_write = self._filter_serializable_config(self.config)
                with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    # Use indent for readability
                    json.dump(config_to_write, f, indent=4)
                log_info(f"Successfully wrote initial configuration to {DYNAMIC_CONFIG_FILE}")
                # Initialize the mtime tracker *after* writing the initial file
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
            else:
                log_info(f"Found existing {DYNAMIC_CONFIG_FILE}. Bot will use its contents for dynamic updates.")
                # Initialize the mtime tracker with the existing file's time
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)

        except (IOError, OSError, TypeError, json.JSONDecodeError) as e: # Added TypeError for json.dump issues
             log_error(f"Error handling initial dynamic config file {DYNAMIC_CONFIG_FILE}: {e}", exc_info=True)
             # Bot can likely continue, but dynamic updates might not work initially
             self._last_dynamic_config_mtime = 0 # Ensure updater tries to read later if possible
        # --- End Initial Config Write ---
        log_debug(f":wrench: FINAL INITIAL CONFIG in use: {self.config}")

        # --- Database and Services Setup ---
        try:
            self.db_client = DatabaseClient(self.config)
            await self.db_client.connect()
            await self.state.set_db_client(self.db_client)

            if self.backup:
                log_info(":floppy_disk: Starting database backup...")
                await self.db_client.backup_db(backup_flag=True)
                log_info(":white_check_mark: Database backup completed.")

            if self.cleanup:
                log_warning(":wastebasket: Starting database cleanup (dropping tables)...") # Changed to warning
                await self.db_client.cleanup_db(cleanup_flag=True)
                log_info(":white_check_mark: Database cleanup finished.")
                # No need to rotate log file again here

            log_info(":rocket: [bold]Initializing database schema...[/bold]")
            await self.db_client.init_db()
            log_info(":white_check_mark: Database schema initialized.")
            await self.db_client.restore_creator_wallets()
        except Exception as db_setup_err:
             log_critical(f"CRITICAL: Failed database setup: {db_setup_err}", exc_info=True)
             self._write_status("ERROR")
             return # Cannot continue without DB

        # --- Initialize Core Components ---
        # Initialize ws_handler here now that config is ready
        self.ws_handler = WebSocketHandler(db_client=self.db_client, config_dict=self.config, state_manager=self.state)
        await self.ws_handler.connect()
        await self.state.set_websocket_handler(self.ws_handler)

        # Pass the active self.config dictionary
        socials_proc = SocialsProcessor(state=self.state, db_client=self.db_client, config_dict=self.config)
        rugchecker = Rugcheck(state=self.state, db_client=self.db_client, websocket_handler=self.ws_handler, socials_processor=socials_proc, config_dict=self.config)
        self.trading_manager = TradingManager(db_client=self.db_client, config_dict=self.config, state=self.state) # Pass config dict


        # --- Start Background Tasks ---
        self.tasks = [
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"),
            asyncio.create_task(update_sol_price(self.state, self.db_client), name="sol_price_updater"),
            asyncio.create_task(trade_worker(), name="trade_worker"),
            rugchecker.start(),
            socials_proc.start(),
            asyncio.create_task(self.run_buy_checks(), name="buy_opportunity_checker"),
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker"),
            asyncio.create_task(self.status_updater(), name="status_updater"),
            asyncio.create_task(self.command_listener(), name="command_listener"),
            asyncio.create_task(self.config_updater(), name="config_updater")
        ]
        # Start WebSocket tasks (listen, manage_subscriptions)
        self.tasks.extend(self.ws_handler.start())

        # --- Start RL Agent Update Task (if agent loaded) ---
        if self.rl_agent:
            self.tasks.append(asyncio.create_task(self.run_rl_agent_updates(), name="rl_agent_updater"))

        self._write_status("RUNNING") # Bot is now fully running

        # # --- Main Execution Loop ---
        # try:
        #     log_info(":rocket: [bold green]Trading bot started successfully.[/bold green] Listening for market updates...")
        #     await self.state.wait_for_shutdown()
        # except Exception as e:
        #     log_error(f"Main loop encountered an error: {e}", exc_info=True)
        #     self._write_status("ERROR") # Set status to error if main loop crashes

        # --- Main Execution Loop ---
        try:
            log_info(":rocket: [bold green]Trading bot started successfully.[/bold green] Listening for market updates...")
            # Wait for any task to finish (usually the shutdown signal)
            done, pending = await asyncio.wait(self.tasks, return_when=asyncio.FIRST_COMPLETED)
            log_info(f"Primary task finished: { {t.get_name() for t in done} }. Initiating shutdown.")
            # Trigger shutdown for remaining tasks if not already triggered
            if not self.state.shutdown_event.is_set():
                 self.state.trigger_shutdown()

        except Exception as e:
            log_critical(f"CRITICAL ERROR in main loop: {e}", exc_info=True)
            self._write_status("ERROR") # Set status to error if main loop crashes
            if not self.state.shutdown_event.is_set():
                 self.state.trigger_shutdown() # Trigger shutdown on critical error

    # --- run_buy_checks / run_sell_checks (No changes needed here) ---
    async def run_buy_checks(self):
        """Continuously check for buy opportunities."""
        log_info(":chart_with_upwards_trend: [bold]Starting buy opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                # TradingManager uses self.config, which might be updated by RL agent
                await self.trading_manager.check_trading_opportunities()
                await asyncio.sleep(10) # Consider if interval needs adjusting based on RL update freq
            except asyncio.CancelledError:
                log_info(":no_entry_sign: Buy checker task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in buy checker loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def run_sell_checks(self):
        """Continuously check for sell opportunities."""
        log_info(":chart_with_downwards_trend: [bold]Starting sell opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                 # TradingManager uses self.config, which might be updated by RL agent
                await self.trading_manager.check_sell_opportunities()
                await asyncio.sleep(3) # Consider if interval needs adjusting
            except asyncio.CancelledError:
                log_info(":no_entry_sign: Sell checker task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in sell checker loop: {e}", exc_info=True)
                await asyncio.sleep(12)


# --- Modify main execution block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file containing optimized parameters from GA.")
    # Add argument for RL agent
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")

    args = parser.parse_args()

    # Set policy for Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def run_bot():
        bot = TradingBot(
            cleanup=args.cleanup,
            backup=args.backup,
            params_file=args.params_file,
            rl_agent_path=args.rl_agent_path
        )
        try:
            await bot.main()
        except (KeyboardInterrupt, SystemExit):
            log_info(":stop_button: [bold red]Interrupted by user.[/bold red] Exiting.")
        except Exception as e:
            log_error(f":x: Unexpected error: {e}", exc_info=True)
        finally:
            await bot.shutdown()

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nShutdown requested by user...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Bot shutdown complete.")