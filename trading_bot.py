import argparse
import asyncio
import signal
import traceback
import inspect
import threading
import os
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import httpx
from typing import Dict, Any, List, Optional

# Assuming these imports are correct for your project structure
import config.config as config_module
from database_handler import DatabaseClient
from trading_logic import TradingManager
from connectors.websocket_handler import WebSocketHandler
from bot_logger import setup_logging, log_info, log_debug, log_error, log_warning, log_critical, rotate_log_file
from state_manager import GlobalState
from trade_processor import trade_worker
from connectors.sol_price_api import update_sol_price
from connectors.rugcheck_handler import Rugcheck
from socials_processor import SocialsProcessor
from utils import calculate_volatility # Assuming this is your utility
from connectors.dexscreener_api import DexscreenerFetcher

from telegram_interface import send_telegram_message

from typing import Optional

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

    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, no_log_rotate: bool = False):
        """Initialize the TradingBot with optional cleanup, backup, GA params file."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.state = GlobalState.get_instance() # Bot's instance of GlobalState
        self.cleanup = cleanup
        self.backup = backup
        self.no_log_rotate = no_log_rotate # Store the flag
        self.params_file = params_file
        self.db_client = None
        self.ws_handler = None
        self.tasks = []
        self.config = {}
        self.base_config = {}
        self._load_base_config()
        self.trading_manager = None
        self._last_dynamic_config_mtime = 0
        self.bot_start_time = datetime.now(timezone.utc) # For uptime calculation
        self.dexscreener_fetcher = None

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
                    "DEFAULT_MARKETCAP_THRESHOLD": self.config.get("DEFAULT_MARKETCAP_THRESHOLD")
                })
                
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
        """Monitor and log the status of background tasks using Rich markup string."""
        try:
            while not self.state.shutdown_event.is_set():
                try:
                    # --- Gather General Bot Data ---
                    sol_amount_raw = await self.state.get_current_sol_balance()
                    sol_amount = sol_amount_raw if sol_amount_raw is not None else 0.0
                    rug_queue_size = self.state.get_rugcheck_queue().qsize()
                    socials_queue_size = self.state.get_socialscheck_queue().qsize()
                    sol_price_usd = await self.state.get_sol_price()
                    sol_price = f"[bold green]${sol_price_usd:.4f}[/bold green]" if sol_price_usd and sol_price_usd > 0 else "[bold red]N/A[/red]"
                    uptime = str(timedelta(seconds=int((datetime.now(timezone.utc) - self.bot_start_time).total_seconds())))
                    open_trades_count_str = f"[yellow]{len(await self.db_client.get_active_buy_positions())}[/yellow]" if self.db_client and self.db_client.pool else "[dim white]N/A[/dim white]"

                    # --- Build WebSocket Status Section ---
                    ws_status_lines = []
                    if self.ws_handler and hasattr(self.ws_handler, 'get_connection_summary'):
                        try:
                            ws_summary = await self.ws_handler.get_connection_summary()
                            ws_conn_status = ws_summary.get("connection_status", "Error")
                            ws_new_token_sub = "Yes" if ws_summary.get("new_token_subscribed") else "No"
                            ws_migration_sub = "Yes" if ws_summary.get("migration_subscribed") else "No"
                            ws_trades_sub_count = str(ws_summary.get("trade_subscriptions_count", "0"))
                            time_since_msg = ws_summary.get("time_since_last_message_s", -1.0)
                            
                            ws_style = "green" if "connected" in ws_conn_status.lower() else "yellow"
                            if time_since_msg != -1.0 and time_since_msg > 60:
                                ws_conn_status += f" (Stale: {time_since_msg:.0f}s)"
                                ws_style = "yellow"
                            if "error" in ws_conn_status.lower(): ws_style = "bold red"
                            
                            ws_new_token_style = "green" if ws_new_token_sub == "Yes" else "yellow"
                            ws_migration_style = "green" if ws_migration_sub == "Yes" else "yellow"

                            ws_status_lines.append(f"[bold cyan]│[/bold cyan] :electric_plug: [bold]Websocket:[/bold] [{ws_style}]{ws_conn_status}[/{ws_style}]")
                            ws_status_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]NewToken Stream:[/bold] [{ws_new_token_style}]{ws_new_token_sub}[/{ws_new_token_style}]")

                            refresher_enabled = config_module._WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED
                            
                            if refresher_enabled:
                                ws_status_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]Migration Stream:[/bold] [{ws_migration_style}]{ws_migration_sub}[/{ws_migration_style}]")
                                ws_status_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]Token Trades Subbed:[/bold] [magenta]{ws_trades_sub_count}[/magenta]")
                                
                                next_refresh_ts = await self.state.get_ws_refresh_next_run_ts()
                                timer_content = ""
                                if next_refresh_ts:
                                    remaining_seconds = (next_refresh_ts - datetime.now(timezone.utc)).total_seconds()
                                    if remaining_seconds > 0:
                                        timer_content = f"[yellow]{remaining_seconds / 60:.1f} min[/yellow]"
                                    else:
                                        timer_content = f"[yellow]Soon...[/yellow]"
                                else:
                                    timer_content = f"[green]In Progress...[/green]"
                                ws_status_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Next WS Refresh:[/bold] {timer_content}")
                            else:
                                ws_status_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]Migration Stream:[/bold] [{ws_migration_style}]{ws_migration_sub}[/{ws_migration_style}]")
                                ws_status_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Token Trades Subbed:[/bold] [magenta]{ws_trades_sub_count}[/magenta]")

                        except Exception as e_ws_sum:
                            ws_status_lines.append(f"[bold cyan]│[/bold cyan] :electric_plug: [bold]Websocket:[/bold] [bold red]Error: {e_ws_sum!r}[/bold red]")
                    
                    # --- Gather Main Bot Tasks Status ---
                    main_task_status_lines_list = []
                    active_bot_tasks_count = 0
                    for task in self.tasks:
                        task_name = task.get_name()
                        style = "green"
                        if task.done():
                            style = "red"
                            status_str = f"error ({type(task.exception()).__name__})" if task.exception() else "done"
                        else:
                            status_str = "running"
                            active_bot_tasks_count += 1
                        
                        formatted_line = f"[bold cyan]├──[/bold cyan] {task_name}: [bold {style}]{status_str}[/bold {style}]"
                        main_task_status_lines_list.append(formatted_line)
                    main_tasks_formatted_str = "\n".join(main_task_status_lines_list)

                    # --- Assemble Final Log Message ---
                    log_parts = [
                        "\n",
                        "[bold cyan]┌────────────────────────────────────[/bold cyan]",
                        "[bold cyan]│[/bold cyan] :robot: [bold magenta]Task Monitor[/bold magenta]",
                        "[bold cyan]│────────────────────────────────────[/bold cyan]",
                        f"[bold cyan]│[/bold cyan] :moneybag: [bold]SOL Balance:[/bold] {sol_amount:.4f}",
                        f"[bold cyan]│[/bold cyan] :timer_clock:  [bold]Uptime:[/bold]  {uptime}",
                        f"[bold cyan]│[/bold cyan] :heavy_dollar_sign: [bold]Actual SOL Price:[/bold] {sol_price}",
                        
                        f"[bold cyan]│[/bold cyan] :bar_chart: [bold]Open Trades:[/bold] {open_trades_count_str}",
                        f"[bold cyan]│[/bold cyan] :recycle: [bold]RugCheck Queue:[/bold] [blue]{rug_queue_size}[/blue]",
                        f"[bold cyan]│[/bold cyan] :speech_balloon: [bold]Socials Queue:[/bold] [blue]{socials_queue_size}[/blue]",
                    ]
                    log_parts.extend(ws_status_lines)
                    log_parts.extend([
                        f"[bold cyan]│[/bold cyan] :gear: [bold]Managed Tasks:[/bold] {active_bot_tasks_count}/{len(self.tasks)}",
                        f"[bold cyan]│[/bold cyan] :clipboard: [bold]Tasks:[/bold]",
                        main_tasks_formatted_str,
                        "[bold cyan]└────────────────────────────────────[/bold cyan]"
                    ])

                    log_debug("\n".join(log_parts))
                    
                except Exception as e_monitor_loop:
                    log_error(f":x: [bold red]Error in monitor_tasks formatting/display loop[/bold red]: {e_monitor_loop}", exc_info=True)
                
                monitor_interval_seconds = self.config.get('MONITOR_TASK_INTERVAL_SECONDS', 30)
                await self.state.wait_or_interrupt(timeout=monitor_interval_seconds)

        except asyncio.CancelledError:
            log_info(":stop_sign: Monitor task shutting down (cancelled).")
        except Exception as e_outer:
            log_error(f":x: [bold red]FATAL error in Monitor task outer loop[/bold red]: {e_outer}", exc_info=True)
        finally:
            log_debug("Monitor task finished.")

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
            # await self.db_client.init_db() # Ensure this is called
            #await self.db_client.restore_creator_wallets() # Ensure this is called
            log_info(":white_check_mark: Database schema initialized and wallets restored.")

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
            else:
                log_info("🟢 Initial SOL price fetched and set.")
        except Exception as e:
            log_critical(f"💥 Error during initial SOL price fetch: {e}. The bot will rely on the hourly updater.", exc_info=True)
        # *** END OF INITIAL SOL PRICE FETCH ***

        # --- Initialize Core Components (pass self.config) ---
        # Initialize WebSocketHandler first as other components might depend on state it prepares (like state_manager)
        self.ws_handler = WebSocketHandler(db_client=self.db_client, config_dict=self.config, state_manager=self.state)
        # Do not call self.ws_handler.connect() here. It will be called by start_websocket_services().
        await self.state.set_websocket_handler(self.ws_handler) # Store in GlobalState

        socials_proc = SocialsProcessor(state=self.state, db_client=self.db_client, config_dict=self.config)
        rugchecker = Rugcheck(state=self.state, db_client=self.db_client, websocket_handler=self.ws_handler, socials_processor=socials_proc, config_dict=self.config)
        self.trading_manager = TradingManager(db_client=self.db_client, config_dict=self.config, state=self.state)
        self.dexscreener_fetcher = DexscreenerFetcher(state=self.state, db_client=self.db_client)


        # --- Start Background Tasks ---
        self.tasks = [
            asyncio.create_task(self.status_updater(), name="status_updater"),
            asyncio.create_task(self.config_updater(), name="config_updater"),
            asyncio.create_task(self.command_listener(), name="command_listener"),
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"),
            asyncio.create_task(update_sol_price(self.state, self.db_client), name="sol_price_updater"),
            asyncio.create_task(trade_worker(), name="trade_worker"),
            asyncio.create_task(self.dexscreener_fetcher.run(), name="dexscreener_fetcher"),
            rugchecker.start(), # Ensure this returns a task
            socials_proc.start(), # Ensure this returns a task
            
            asyncio.create_task(self.run_buy_checks(), name="buy_opportunity_checker"),
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker"),
            asyncio.create_task(self.run_heartbeat_emitter(), name="heartbeat_emitter"),
            
            # Start the single, self-recovering WebSocket service task
            asyncio.create_task(self.ws_handler.connect_and_run(), name="websocket_services_manager")
        ]
        
        
        log_info(":rocket: [bold green]Trading bot core components started.[/bold green]")
        try:
            done, pending = await asyncio.wait(self.tasks, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                if task.exception():
                    log_critical(f"Task {task.get_name()} exited with exception: {task.exception()}", exc_info=task.exception())
                    self.state.trigger_shutdown() 
                else:
                    log_info(f"Task {task.get_name()} completed.")
            
            if not self.state.shutdown_event.is_set():
                log_info("A task completed, but shutdown not triggered. Waiting for shutdown signal...")
                await self.state.wait_for_shutdown()

        except Exception as e:
            log_critical(f"CRITICAL ERROR in bot's main execution: {e}", exc_info=True)
            self.state.trigger_shutdown() 
        finally:
            log_info("Main execution loop ended. Proceeding to full shutdown.")

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