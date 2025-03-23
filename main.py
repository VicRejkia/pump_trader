"""
Entry point for the trading bot.
Initializes the database, starts SOL price updates, WebSocket communication,
and trading tasks.
"""
import argparse
import asyncio
from database import init_db, get_db, cleanup_db
from api import update_sol_price, rugcheck_worker, check_missing_rugcheck_data, refresh_rugcheck_queue
from trading import check_trading_opportunities
from websocket_handler import WebSocketHandler
from logger import setup_logging, logger
from state import state  # Singleton state management

async def monitor_tasks(tasks):
    while not await state.get_shutdown():
        logger.debug("Task monitor: " + ", ".join([f"{t.get_name()}:{'done' if t.done() else 'running'}" for t in tasks]))
        await asyncio.sleep(30)

async def main(cleanup: bool):
    """Main entry point for the bot's event loop."""
    setup_logging(debug=True)
    await init_db()  # Initialize connection pool and database schema

    # Optionally clean up the database before starting.
    if cleanup:
        logger.info("🗑️ Starting database cleanup...")
        await cleanup_db()

    ws_handler = WebSocketHandler()
    await ws_handler.connect()

    tasks = [
        asyncio.create_task(update_sol_price()),
        asyncio.create_task(refresh_rugcheck_queue()),
        asyncio.create_task(check_trading_opportunities(ws_handler.websocket)),
        asyncio.create_task(rugcheck_worker()),
        asyncio.create_task(check_missing_rugcheck_data())
    ]
    tasks.extend(ws_handler.start())  # Add WebSocket handler tasks
    tasks.append(asyncio.create_task(monitor_tasks(tasks)))

    try:
        logger.info("🚀 Trading bot started successfully. Listening for market updates...")
        await asyncio.gather(*tasks, return_exceptions=True)

    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("⏹ Shutdown initiated. Cleaning up resources...")

        # 🚀 Wake up all sleeping tasks so they stop immediately
        await state.set_shutdown(True)  
        
        # Properly close WebSocket connections
        await ws_handler.shutdown()

        # Cancel all running tasks
        for task in tasks:
            task.cancel()
        
        # Wait for all tasks to finish
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        # Ensure database connections are properly closed
        async with state.get_db_write_lock():
            pool = await get_db()
            await pool.close()
            logger.info("🔌 Database connection pool closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up (empty) the database before starting the bot.")
    args = parser.parse_args()

    try:
        asyncio.run(main(cleanup=args.cleanup))
    except KeyboardInterrupt:
        logger.info("⏹ Bot manually interrupted. Exiting.")
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")
