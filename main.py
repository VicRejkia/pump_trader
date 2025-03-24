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
from state import GlobalState

async def monitor_tasks(state, tasks):
    """Enhanced task monitor with queue metrics and detailed statuses"""
    while not await state.get_shutdown():
        try:
            queue = state.get_rugcheck_queue()
            queue_size = queue.qsize()
            
            task_status = []
            for task in tasks:
                if task.done():
                    if task.cancelled():
                        status = "cancelled"
                    else:
                        try:
                            result = task.result()
                            status = f"done ({result})"
                        except Exception as e:
                            status = f"failed ({str(e)})"
                else:
                    status = "running"
                task_status.append(f"{task.get_name()}:{status}")
            
            logger.debug(
                f"**Task Monitor**\n"
                f"│ Queue size: {queue_size}\n"
                f"│ Active tasks: {len([t for t in tasks if not t.done()])}/{len(tasks)}\n"
                f"│ Tasks: {', '.join(task_status)}"
            )
        except Exception as e:
            logger.error(f"Monitor task error: {e}")
        
        await asyncio.sleep(30)

async def main(cleanup: bool):
    """Main entry point for the bot's event loop."""
    setup_logging(debug=True)

    # Instantiate state within the event loop
    state = await GlobalState.get_instance()

    # Initialize connection pool and database schema
    await init_db()

    # Optionally clean up the database before starting.
    if cleanup:
        logger.info("🗑️ Starting database cleanup...")
        await cleanup_db()

    ws_handler = WebSocketHandler(state)
    await ws_handler.connect()

    tasks = [
        asyncio.create_task(update_sol_price(state), name="sol_price_updater"),
        asyncio.create_task(refresh_rugcheck_queue(state), name="rugcheck_queue_refresher"),
        asyncio.create_task(check_trading_opportunities(ws_handler.websocket, state), name="trading_opportunities_checker"),
        asyncio.create_task(rugcheck_worker(state), name="rugcheck_worker"),
        asyncio.create_task(check_missing_rugcheck_data(state), name="missing_rugcheck_data_checker")
    ]
    monitor_task = asyncio.create_task(monitor_tasks(state, tasks), name="task_monitor")
    tasks.append(monitor_task)
    tasks.extend(ws_handler.start())  # Add WebSocket handler tasks

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
