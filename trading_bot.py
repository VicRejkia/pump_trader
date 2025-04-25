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
from datetime import datetime, timezone

import config # Base config
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
        self.db_client = DatabaseClient()
        self.ws_handler = WebSocketHandler(db_client=self.db_client)
        self.tasks = []
        self.config = {} # This will hold the final config (base, GA, or updated by RL)
        self.base_config = {} # Store the initial config loaded from file/defaults
        self.trading_manager = None
        self._write_status("INITIALIZING")


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
                            # try:
                            #     os.remove(COMMAND_FILE)
                            #     log_debug(f"Removed command file: {COMMAND_FILE}")
                            # except OSError as e:
                            #     log_error(f"Error removing command file {COMMAND_FILE}: {e}")
                            break # Exit listener loop once stop is triggered
                        elif command == "START" and last_command != "START":
                             log_info(f":arrow_forward: Received START command from {COMMAND_FILE}. Bot should already be starting/running.")
                             last_command = "START"
                             # Optionally delete START command file? Or leave it?
                             # If left, bot might re-log this message on restart.
                        elif command not in ["START", "STOP"]:
                             log_warning(f"Ignoring unknown command '{command}' in {COMMAND_FILE}")
                             last_command = command # Avoid re-logging warning

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

        # --- Load Base Configuration ---
        try:
            loaded_config = {}
            for key in dir(config):
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config, key)
                    if not inspect.ismodule(value) and not inspect.isclass(value) and not inspect.isfunction(value):
                        loaded_config[key] = value
            self.base_config = loaded_config # Store base config
            self.config = self.base_config.copy() # Start with base config
            log_info(":gear: Base configuration loaded successfully.")
        except Exception as e:
            log_error(f":x: [bold red]Failed to load base configuration[/bold red]: {e}", exc_info=True)
            self._write_status("ERROR")
            return

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

        # --- Database and Services Setup ---
        await self.db_client.connect()
        await self.state.set_db_client(self.db_client)

        # ... (database backup/cleanup/init - no changes needed) ...
        if self.backup:
            log_info(":floppy_disk: Starting database backup...")
            await self.db_client.backup_db(backup_flag=True)
            log_info(":white_check_mark: Database backup completed.")

        if self.cleanup:
            log_info(":wastebasket: Starting database cleanup (dropping tables)...")
            await self.db_client.cleanup_db(cleanup_flag=True)
            log_info(":arrows_counterclockwise: Rotating log file...")

        log_info(":rocket: [bold]Initializing database schema...[/bold]")
        await self.db_client.init_db()
        log_info(":white_check_mark: Database schema initialized.")
        await self.db_client.restore_creator_wallets()


        # --- Initialize Core Components ---
        await self.ws_handler.connect()
        await self.state.set_websocket_handler(self.ws_handler)
        socials_proc = SocialsProcessor(self.state, self.db_client, self.config) # Pass final config
        rugchecker = Rugcheck(self.state, self.db_client, self.ws_handler, socials_proc)
        # Pass the final config (potentially updated by GA)
        self.trading_manager = TradingManager(self.db_client, self.config, self.state)

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
            asyncio.create_task(self.command_listener(), name="command_listener")
        ]
        self.tasks.extend(self.ws_handler.start())

        # --- Start RL Agent Update Task (if agent loaded) ---
        if self.rl_agent:
            self.tasks.append(asyncio.create_task(self.run_rl_agent_updates(), name="rl_agent_updater"))

        self._write_status("RUNNING") # Bot is now fully running

        # --- Main Execution Loop ---
        try:
            log_info(":rocket: [bold green]Trading bot started successfully.[/bold green] Listening for market updates...")
            await self.state.wait_for_shutdown()
        except Exception as e:
            log_error(f"Main loop encountered an error: {e}", exc_info=True)
            self._write_status("ERROR") # Set status to error if main loop crashes

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

    # Pass the new argument to TradingBot constructor
    bot = TradingBot(
        cleanup=args.cleanup,
        backup=args.backup,
        params_file=args.params_file,
        rl_agent_path=args.rl_agent_path # Pass RL agent path
    )
    try:
        bot.loop.run_until_complete(bot.main())
    except (KeyboardInterrupt, SystemExit):
        log_info(":stop_button: [bold red]Interrupted by user.[/bold red] Exiting.")
    except Exception as e:
        log_error(f":x: Unexpected error: {e}", exc_info=True)
        # Attempt graceful shutdown even on unexpected error
        if bot.state and not bot.state.shutdown_event.is_set():
            bot.state.trigger_shutdown()
    finally:
        # Ensure shutdown runs
        if bot.loop.is_running():
             bot.loop.run_until_complete(bot.shutdown())
        else:
             # If loop closed unexpectedly, try running shutdown in a new temp loop
             try:
                 asyncio.run(bot.shutdown())
             except Exception as final_shutdown_err:
                  log_error(f"Error during final shutdown attempt: {final_shutdown_err}")

        if not bot.loop.is_closed():
             bot.loop.close()
             log_info("Asyncio loop closed.")