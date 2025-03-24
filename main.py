"""
Entry point for the trading bot.
Initializes the database, starts SOL price updates, WebSocket communication,
and trading tasks.
"""
import argparse
import asyncio
from database import init_db, get_db, cleanup_db, trade_worker
from api import update_sol_price, rugcheck_worker, refresh_rugcheck_queue
from trading import check_trading_opportunities
from websocket_handler import WebSocketHandler
from logger import setup_logging, logger
from state import GlobalState
import sys
import traceback

async def monitor_tasks(state, tasks):
    """Enhanced task monitor with queue metrics and detailed statuses"""
    while not await state.get_shutdown():
        try:
            queue = state.get_rugcheck_queue()
            queue_size = queue.qsize()
            
            task_status = []
            for task in tasks:
                if task.done():
                    logger.warning(f"Task {task.get_name()} exited unexpectedly!")
                    if task.cancelled():
                        status = "cancelled"
                    else:
                        try:
                            result = task.result()
                            status = f"done ({result})"
                        except Exception as e:
                            logger.error(f"🚨 Task {task.get_name()} failed: {e}\n{traceback.format_exc()}")
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

            # 🚀 Check for stalled tasks
            for task in tasks:
                if not task.done() and task.get_name() in ["check_trading_opportunities", "rugcheck_worker"]:
                    logger.debug(f"🔍 Checking if task {task.get_name()} is stuck...")

            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Monitor task error: {e}\n{traceback.format_exc()}")
        
        await asyncio.sleep(30)

async def main(cleanup: bool):
    """Main entry point for the bot's event loop."""
    setup_logging(debug=True)

    loop = asyncio.get_running_loop()

    def handle_exception(loop, context):
        logger.error(f"Unhandled exception: {context.get('exception', context['message'])}")
    
    loop.set_exception_handler(handle_exception)

    # Instantiate state within the event loop
    state = await GlobalState.get_instance()

    # Initialize connection pool and database schema
    await init_db()

    # Optionally clean up the database before starting.
    if cleanup:
        logger.info("🗑️ Starting database cleanup...")
        await cleanup_db()

    ws_handler = WebSocketHandler(state)
    await state.set_websocket_handler(ws_handler)  # 🚀 Store WebSocketHandler referenc
    await ws_handler.connect()

    tasks = [
        asyncio.create_task(update_sol_price(state), name="sol_price_updater"),
        asyncio.create_task(trade_worker(state), name="trade_worker"),
        asyncio.create_task(refresh_rugcheck_queue(state), name="rugcheck_queue_refresher"),
        asyncio.create_task(check_trading_opportunities(ws_handler.websocket, state), name="trading_opportunities_checker"),
        asyncio.create_task(rugcheck_worker(state), name="rugcheck_worker"),
    ]

    monitor_task = asyncio.create_task(monitor_tasks(state, tasks), name="task_monitor")
    tasks.append(monitor_task)
    tasks.extend(ws_handler.start())  # Add WebSocket handler tasks

    for task in tasks:
        task.add_done_callback(lambda t: logger.error(f"🚨 Task {t.get_name()} crashed: {t.exception()}") if t.exception() else None)


    try:
        logger.info("🚀 Trading bot started successfully. Listening for market updates...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"🚨 Task {tasks[i].get_name()} failed with error: {result}")

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
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"🚨 Task {tasks[i].get_name()} failed with error: {result}")
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
        def log_unhandled_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logger.error("Unhandled Exception:", exc_info=(exc_type, exc_value, exc_traceback))

        sys.excepthook = log_unhandled_exception
        asyncio.run(main(cleanup=args.cleanup))
    except KeyboardInterrupt:
        logger.info("⏹ Bot manually interrupted. Exiting.")
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")
