import argparse
import asyncio
import signal
import traceback
import config
from database import DatabaseClient
# Old rugcheck imports removed
# from trading import check_trading_opportunities
from websocket_handler import WebSocketHandler
from logger import setup_logging, logger, rotate_log_file
from state import GlobalState
from trade_processor import trade_worker # Import the trade worker
from sol_price_api import update_sol_price # Corrected import for SOL price fetcher
from rugcheck import Rugcheck # Import the Rugcheck class
from socials_processor import SocialsProcessor # Import the SocialsProcessor class

class TradingBot:
    def __init__(self, cleanup: bool = False):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.state = GlobalState.get_instance()
        self.cleanup = cleanup
        self.db_client = DatabaseClient()
        self.ws_handler = WebSocketHandler(db_client=self.db_client)
        self.tasks = []

    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def signal_handler():
            logger.info("Signal received, initiating shutdown...")
            self.state.trigger_shutdown()

        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, lambda *_: signal_handler())
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, lambda *_: signal_handler())

    async def monitor_tasks(self):
        """Monitor running tasks and log their status."""
        try:
            while not self.state.shutdown_event.is_set():
                try:
                    rug_queue_size = self.state.get_rugcheck_queue().qsize()
                    tokens_subscribed = list(await self.state.get_token_subscriptions())
                    task_status = [f"{task.get_name()}: {'done' if task.done() else 'running'}\n" for task in self.tasks]
                    #logger.debug(f"📟 Task Monitor: Queue size: {rug_queue_size}, Tasks: {', '.join(task_status)}")

                    logger.debug(
                        f"\n"
                        f"┌────────────────────────────────────\n"
                        f"│📟 Task Monitor 📟\n"
                        f"│────────────────────────────────────\n"
                        f"│ Subscibed tokens: {len(tokens_subscribed)}\n"
                        f"│ RugCheck Queue size: {rug_queue_size}\n"
                        f"│ Active tasks: {len([t for t in self.tasks if not t.done()])}/{len(self.tasks)}\n"
                        f"│ Tasks:\n"
                        f"├── {'├── '.join(task_status)}"
                        f"└────────────────────────────────────\n"
                    )
            


                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Monitor task error: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Monitor task shutting down")

    async def shutdown(self):
        """Gracefully shuts down all running tasks and connections."""
        logger.info("⏹ Shutdown initiated. Cleaning up resources...")
        try:
            await asyncio.wait_for(self.ws_handler.shutdown(), timeout=60)
            logger.info("🛑 WebSocket shutdown complete.")
        except Exception as e:
            logger.error(f"WebSocket shutdown error: {e}", exc_info=True)
        
        for task in self.tasks:
            task.cancel()
            logger.debug(f"🛑 Cancelling task: {task.get_name()}")

        await self.db_client.pool.close()
        logger.info("🔌 Database connection closed.")

        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        logger.info("🛑 Shutdown complete.")

    async def main(self):
        """Main execution loop of the bot."""
        setup_logging()
        self.register_signal_handlers()
        await self.db_client.connect()
        await self.state.set_db_client(self.db_client) # Store db_client in GlobalState
        await self.db_client.init_db()
        
        if self.cleanup:
            logger.info("🗑️ Starting database cleanup...")
            await self.db_client.cleanup_db(cleanup_flag=True)
            logger.info("🔄 Rotating log file...")
            logger.handlers.clear()
            rotate_log_file()
        
        await self.ws_handler.connect()
        await self.state.set_websocket_handler(self.ws_handler) # Store ws_handler in GlobalState

        # Instantiate Processors after dependencies are ready
        socials_proc = SocialsProcessor(self.state, self.db_client)
        # Pass socials_proc to Rugcheck constructor (will require updating Rugcheck.__init__)
        rugchecker = Rugcheck(self.state, self.db_client, self.ws_handler, socials_proc)

        # Start background tasks
        self.tasks = [
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"),
            asyncio.create_task(update_sol_price(self.state), name="sol_price_updater"),
            asyncio.create_task(trade_worker(), name="trade_worker"),
            rugchecker.start() # Start the rugcheck worker task
        ]
        self.tasks.extend(self.ws_handler.start()) # Start WebSocket handler tasks
        
        try:
            logger.info("🚀 Trading bot started successfully. Listening for market updates...")
            await self.state.wait_for_shutdown()
        except Exception as e:
            logger.error(f"Main encountered an error: {e}", exc_info=True) # Added exc_info for better debugging
        # Removed await self.shutdown() from here - it's handled in the main execution block's finally clause

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot.")
    args = parser.parse_args()

    bot = TradingBot(cleanup=args.cleanup)
    try:
        bot.loop.run_until_complete(bot.main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏹ Interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
    finally:
        bot.loop.run_until_complete(bot.shutdown())
        bot.loop.close()
