import argparse
import asyncio
import signal
import traceback
import inspect
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

    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""

        def signal_handler():
            log_info(":heavy_exclamation_mark: [bold red]Signal received[/bold red], initiating shutdown...")
            self.state.trigger_shutdown()

        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, lambda *_: signal_handler())
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, lambda *_: signal_handler())

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

    async def shutdown(self):
        """Gracefully shut down all tasks and close resources."""
        log_info(":stop_button: [bold red]Shutdown initiated[/bold red]. Cleaning up resources...")
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
        log_info(":checkered_flag: Shutdown complete.")

    async def main(self):
        """Main entry point for setting up and starting the bot."""
        rotate_log_file()
        setup_logging()
        self.register_signal_handlers()

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
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker")
        ]
        self.tasks.extend(self.ws_handler.start())

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    args = parser.parse_args()

    bot = TradingBot(cleanup=args.cleanup, backup=args.backup)
    try:
        bot.loop.run_until_complete(bot.main())
    except (KeyboardInterrupt, SystemExit):
        log_info(":stop_button: [bold red]Interrupted by user.[/bold red] Exiting.")
    except Exception as e:
        log_error(f":x: Unexpected error: {e}", exc_info=True)
    finally:
        bot.loop.run_until_complete(bot.shutdown())
        bot.loop.close()
