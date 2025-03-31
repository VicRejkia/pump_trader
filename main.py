import argparse
import asyncio
import signal
import traceback
import config
from database import DatabaseClient
# from api import update_sol_price, rugcheck_worker, refresh_rugcheck_queue
# from trading import check_trading_opportunities
from websocket_handler import WebSocketHandler
from logger import setup_logging, logger, rotate_log_file
from state import GlobalState
from trade_processor import trade_worker # Import the trade worker

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
                    queue_size = self.state.get_rugcheck_queue().qsize()
                    task_status = [f"{task.get_name()}: {'done' if task.done() else 'running'}" for task in self.tasks]
                    logger.debug(f"📟 Task Monitor: Queue size: {queue_size}, Tasks: {', '.join(task_status)}")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Monitor task error: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(15)
        except asyncio.CancelledError:
            logger.info("Monitor task shutting down")

    async def shutdown(self):
        """Gracefully shuts down all running tasks and connections."""
        logger.info("⏹ Shutdown initiated. Cleaning up resources...")
        try:
            await asyncio.wait_for(self.ws_handler.shutdown(), timeout=60)
            logger.info("WebSocket shutdown complete.")
        except Exception as e:
            logger.error(f"WebSocket shutdown error: {e}", exc_info=True)
        
        for task in self.tasks:
            task.cancel()
            logger.debug(f"Cancelling task: {task.get_name()}")

        await self.db_client.pool.close()
        logger.info("🔌 Database connection closed.")

        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        logger.info("Shutdown complete.")

    async def main(self):
        """Main execution loop of the bot."""
        setup_logging()
        self.register_signal_handlers()
        await self.db_client.connect()
        await self.state.set_db_client(self.db_client) # Store db_client in GlobalState
        
        if self.cleanup:
            logger.info("🗑️ Starting database cleanup...")
            await self.db_client.cleanup_db(cleanup_flag=True)
            logger.info("🔄 Rotating log file...")
            logger.handlers.clear()
            rotate_log_file()
        
        await self.ws_handler.connect()
        await self.state.set_websocket_handler(self.ws_handler)
        
        self.tasks = [
            asyncio.create_task(self.monitor_tasks(), name="task_monitor")
        ]
        self.tasks.extend(self.ws_handler.start())
        self.tasks.append(asyncio.create_task(trade_worker(), name="trade_worker")) # Start the trade worker
        
        try:
            logger.info("🚀 Trading bot started successfully. Listening for market updates...")
            await self.state.wait_for_shutdown()
        except Exception as e:
            logger.error(f"Main encountered an error: {e}")
        finally:
            await self.shutdown()

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
