import argparse
import asyncio
import signal
import traceback
import inspect
import threading # Import threading module
import os # Import os module
import time # Import time module
import config
from database_handler import DatabaseClient
from trading_logic import TradingManager
from websocket_handler import WebSocketHandler
from logger import setup_logging, log_info, log_debug, log_error, rotate_log_file
from state_manager import GlobalState
from trade_processor import trade_worker
from sol_price_api import update_sol_price
from rugcheck_handler import Rugcheck
from socials_processor import SocialsProcessor
# Define paths for communication files relative to project root
# Assuming this script is run from the project root via main.py
COMMAND_FILE = os.path.join('data', 'bot_command.txt')
STATUS_FILE = os.path.join('data', 'bot_status.txt')


class TradingBot:
    """Main class for running the trading bot."""

    def __init__(self, cleanup: bool = False, backup: bool = False):
        """Initialize the TradingBot with optional cleanup and backup flags."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.state = GlobalState.get_instance()
        self.cleanup = cleanup
        self.backup = backup
        self.db_client = DatabaseClient()
        self.ws_handler = WebSocketHandler(db_client=self.db_client)
        self.tasks = []
        self.config = {}
        self.trading_manager = None
        self._write_status("INITIALIZING") # Initial status before main loop starts

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

                    log_debug(
                        f"\n"
                        f"[bold cyan]┌────────────────────────────────────[/bold cyan]\n"
                        f"[bold cyan]│[/bold cyan] :robot: [bold magenta]Task Monitor[/bold magenta]\n"
                        f"[bold cyan]│────────────────────────────────────[/bold cyan]\n"
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
                await asyncio.sleep(60)
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

        await self.db_client.pool.close()
        log_info(":electric_plug: Database connection closed.")

        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        self._write_status("STOPPED") # Final status update
        log_info(":checkered_flag: Shutdown complete.")
        # Clean up command/status files on clean exit? Optional.
        # try:
        #     if os.path.exists(COMMAND_FILE): os.remove(COMMAND_FILE)
        #     if os.path.exists(STATUS_FILE): os.remove(STATUS_FILE)
        # except OSError as e:
        #     log_error(f"Error cleaning up flag files: {e}")

    async def main(self):
        """Main entry point for setting up and starting the bot."""
        self._write_status("STARTING") # Indicate startup process
        is_main_thread = threading.current_thread() is threading.main_thread()

        if is_main_thread:
            log_info("Running in main thread. Performing log rotation and registering signal handlers.")
            rotate_log_file() # Only rotate logs if running as main script
        else:
             log_info("Running in a secondary thread (likely Flask). Skipping log rotation and signal handlers.")

        # Setup logging regardless of thread
        setup_logging()

        if is_main_thread:
            self.register_signal_handlers() # Only register signals if running as main script

        try:
            config_vars = {}
            for key in dir(config):
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config, key)
                    if not inspect.ismodule(value) and not inspect.isclass(value) and not inspect.isfunction(value):
                        config_vars[key] = value

            critical_vars = ['SOL_TO_BUY', 'WS_HOST']
            missing_critical = [var for var in critical_vars if var not in config_vars]
            if missing_critical:
                log_error(f":x: [bold red]Missing critical configuration variables[/bold red]: {missing_critical}")
                return

            self.config = config_vars
            log_info(":gear: [bold green]Configuration loaded successfully.[/bold green]")

        except Exception as e:
            log_error(f":x: [bold red]Failed to load configuration[/bold red]: {e}", exc_info=True)
            return

        log_debug(f":wrench: CONFIG: {self.config}")

        await self.db_client.connect()
        await self.state.set_db_client(self.db_client)

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

        # Restore creator wallets after schema initialization
        await self.db_client.restore_creator_wallets()

        await self.ws_handler.connect()
        await self.state.set_websocket_handler(self.ws_handler)
        socials_proc = SocialsProcessor(self.state, self.db_client, self.config)
        rugchecker = Rugcheck(self.state, self.db_client, self.ws_handler, socials_proc)
        # Pass the DatabaseClient instance, not just the pool
        self.trading_manager = TradingManager(self.db_client, self.config, self.state)

        self.tasks = [
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"),
            asyncio.create_task(update_sol_price(self.state), name="sol_price_updater"),
            asyncio.create_task(trade_worker(), name="trade_worker"),
            rugchecker.start(),
            socials_proc.start(),
            asyncio.create_task(self.run_buy_checks(), name="buy_opportunity_checker"),
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker"),
            # Add new tasks for status and command handling
            asyncio.create_task(self.status_updater(), name="status_updater"),
            asyncio.create_task(self.command_listener(), name="command_listener")
        ]
        self.tasks.extend(self.ws_handler.start())
        self._write_status("RUNNING") # Bot is now fully running

        try:
            log_info(":rocket: [bold green]Trading bot started successfully.[/bold green] Listening for market updates...")
            await self.state.wait_for_shutdown()
        except Exception as e:
            log_error(f"Main encountered an error: {e}", exc_info=True)

    async def run_buy_checks(self):
        """Continuously check for buy opportunities."""
        log_info(":chart_with_upwards_trend: [bold]Starting buy opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                await self.trading_manager.check_trading_opportunities()
                await asyncio.sleep(10)
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
                await self.trading_manager.check_sell_opportunities()
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                log_info(":no_entry_sign: Sell checker task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in sell checker loop: {e}", exc_info=True)
                await asyncio.sleep(12)