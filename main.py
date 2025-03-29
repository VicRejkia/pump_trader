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
        while not state.shutdown_event.is_set():
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

def register_signal_handlers(loop, state: GlobalState):
    """Register signal handlers that set the shutdown event if supported."""
    def signal_handler():
        logger.info("Signal received, initiating shutdown...")
        state.trigger_shutdown()
    # On Windows with the Proactor event loop, add_signal_handler may not be supported.
    for sig in (signal.SIGINT, signal.SIGTERM):
        if hasattr(loop, 'add_signal_handler'):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                logger.warning(f"Signal handlers not supported for {sig} on this platform.")
        else:
            logger.warning("add_signal_handler not available on this event loop.")

async def shutdown_handler(state, tasks, ws_handler, loop):
    """Gracefully shuts down all running tasks and the WebSocket connection."""
    logger.info("⏹ Shutdown initiated. Cleaning up resources...")

    try:
        logger.debug("Shutting down WebSocket...")
        await asyncio.wait_for(ws_handler.shutdown(), timeout=10)
        logger.info("WebSocket shutdown complete.")
    except Exception as e:
        logger.error(f"WebSocket shutdown error: {e}", exc_info=True)

    # Cancel all tasks.
    for task in tasks:
        task.cancel()
        logger.debug(f"Cancelling task: {task.get_name()}")

    # Close database last.
    async with state.get_db_write_lock():
        logger.debug("Closing database connection...")
        pool = await get_db()
        await pool.close()
        logger.info("🔌 Database connection closed.")

    try:
        logger.debug("Waiting for tasks to complete...")
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10)
        for task, result in zip(tasks, results):
            if isinstance(result, asyncio.CancelledError):
                logger.info(f"Task {task.get_name()} cancelled successfully.")
            elif isinstance(result, Exception):
                logger.error(f"Task {task.get_name()} raised an exception: {result}", exc_info=True)
        logger.info("All tasks finished.")
    except asyncio.TimeoutError:
        logger.warning("⚠️ Some tasks refused to exit gracefully.")

    # Flush any remaining asyncio events.
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

async def main(cleanup: bool):
    """Main entry point for the bot's event loop."""
    setup_logging(debug=True)
    loop = asyncio.get_running_loop()

    # Retrieve the singleton GlobalState instance.
    state = GlobalState.get_instance()
    register_signal_handlers(loop, state)

    # Initialize database and schema.
    await init_db()

    # Optionally clean up the database before starting.
    if cleanup:
        logger.info("🗑️ Starting database cleanup...")
        await cleanup_db()
        logger.info("🔄 Rotating log file...")
        logger.handlers.clear()  # Clear existing handlers
        rotate_log_file()         # Reinitialize logging

    # Setup WebSocket handler and connect.
    ws_handler = WebSocketHandler()
    await state.set_websocket_handler(ws_handler)
    await ws_handler.connect()

    # Create primary tasks and include tasks from the WebSocket handler.
    tasks = [
        #asyncio.create_task(update_sol_price(state), name="sol_price_updater"),
        #asyncio.create_task(trade_worker(state), name="trade_worker"),
        #asyncio.create_task(refresh_rugcheck_queue(state), name="rugcheck_queue_refresher"),
        #asyncio.create_task(check_trading_opportunities(ws_handler.websocket, state), name="trading_opportunities_checker"),
        #asyncio.create_task(rugcheck_worker(state, ws_handler.websocket), name="rugcheck_worker"),
    ]
    monitor_task = asyncio.create_task(monitor_tasks(state, tasks), name="task_monitor")
    tasks.append(monitor_task)
    tasks.extend(ws_handler.start())  # Add WebSocket handler tasks

    try:
        logger.info("🚀 Trading bot started successfully. Listening for market updates...")
        # Wait until the shutdown event is triggered.
        await state.wait_for_shutdown()
    except Exception as e:
        logger.error(f"Main encountered an error: {e}")
    finally:
        logger.info("⏹ Shutdown initiated. Cleaning up resources...")
        # Ensure the shutdown event is triggered.
        state.trigger_shutdown()

        # Properly close WebSocket connections.
        # try:
        #     await ws_handler.shutdown()
        # except Exception as e:
        #     logger.error(f"WebSocket shutdown error: {e}", exc_info=True)

        # Cancel all tasks and wait for their completion.
        await shutdown_handler(state, tasks, ws_handler, loop)

def handle_signal(signum, frame):
    """Force shutdown on second CTRL-C."""
    asyncio.get_event_loop().stop()
    raise SystemExit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot.")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(main(cleanup=args.cleanup))
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏹ Interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
