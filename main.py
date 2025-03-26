import argparse
import asyncio
import signal
import traceback
from database import init_db, get_db, cleanup_db, trade_worker
from api import update_sol_price, rugcheck_worker, refresh_rugcheck_queue
from trading import check_trading_opportunities
from websocket_handler import WebSocketHandler
from logger import setup_logging, logger, rotate_log_file
from state import GlobalState

async def monitor_tasks(state, tasks):
    """Enhanced task monitor with queue metrics and detailed statuses."""
    try:
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
                    f"📟 Task Monitor 📟\n"
                    f"│ Queue size: {queue_size}\n"
                    f"│ Active tasks: {len([t for t in tasks if not t.done()])}/{len(tasks)}\n"
                    f"│ Tasks: {', '.join(task_status)}"
                )
                
                # Optionally check for stalled tasks
                for task in tasks:
                    if not task.done() and task.get_name() in ["check_trading_opportunities", "rugcheck_worker"]:
                        logger.debug(f"🔍 Checking if task {task.get_name()} is stuck...")
    
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Monitor task error: {e}\n{traceback.format_exc()}")
            await asyncio.sleep(15)
    except asyncio.CancelledError:
        logger.info("Monitor task shutting down")
        raise

async def shutdown_handler(state, tasks, ws_handler, loop):
    """Gracefully shuts down all running tasks and the WebSocket connection."""
    logger.info("⏹ Shutdown initiated. Cleaning up resources...")

    # Set shutdown flag and wake up tasks waiting on state.shutdown_event
    await state.set_shutdown(True)

    # Attempt graceful WebSocket shutdown
    try:
        await ws_handler.shutdown()
    except Exception as e:
        logger.error(f"❌ WebSocket shutdown error: {e}", exc_info=True)

    # Cancel all tasks
    for task in tasks:
        task.cancel()

    # Remove signal handlers to avoid further signals during shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.remove_signal_handler(sig)
        except Exception:
            pass

    # Allow tasks a moment to process cancellation (increase to 1 second)
    await asyncio.sleep(1)

    # Wait for tasks to finish
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for idx, result in enumerate(results):
        if isinstance(result, asyncio.CancelledError):
            logger.info(f"Task {tasks[idx].get_name()} cancelled successfully.")
        elif isinstance(result, Exception):
            logger.error(f"Task {tasks[idx].get_name()} raised an exception: {result}", exc_info=True)

    # Ensure the database connection pool is properly closed
    async with state.get_db_write_lock():
        pool = await get_db()
        await pool.close()
        logger.info("🔌 Database connection closed.")

async def main(cleanup: bool):
    """Main entry point for the bot's event loop."""
    setup_logging(debug=True)
    loop = asyncio.get_running_loop()

    # Instantiate global state
    state = await GlobalState.get_instance()

    # Initialize database and schema
    await init_db()

    # Optionally clean up the database before starting.
    if cleanup:
        logger.info("🗑️ Starting database cleanup...")
        await cleanup_db()
        # Rotate logs after cleanup
        logger.info("🔄 Rotating log file...")
        logger.handlers.clear()  # Clear existing handlers
        rotate_log_file()  # Reinitialize logging

    # Setup WebSocket handler and connect
    ws_handler = WebSocketHandler(state)
    await state.set_websocket_handler(ws_handler)
    await ws_handler.connect()

    # Create primary tasks and include tasks from the WebSocket handler
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

    # Setup signal handling to trigger shutdown
    stop_event = asyncio.Event()

    def handle_signal():
        stop_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    logger.info("🚀 Bot started. Press CTRL+C to stop.")

    try:
        await stop_event.wait()
    finally:
        await shutdown_handler(state, tasks, ws_handler, loop)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot.")
    args = parser.parse_args()

    try:
        asyncio.run(main(cleanup=args.cleanup))
    except KeyboardInterrupt:
        logger.info("⏹ Interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
