import argparse
import asyncio
import signal
from logger import logger, setup_logging, rotate_log_file
import traceback
from state import GlobalState
from database import init_db, cleanup_db
from websocket_handler import WebSocketHandler

async def task_worker(name: str, interval: float, state: GlobalState):
    """A sample worker task that periodically does work until shutdown."""
    try:
        while not state.shutdown_event.is_set():
            logger.info(f"{name}: Working...")
            # Simulate work with an interruptible sleep
            try:
                await asyncio.wait_for(asyncio.sleep(interval), timeout=interval + 1)
            except asyncio.TimeoutError:
                pass
    except asyncio.CancelledError:
        logger.info(f"{name}: Cancelled.")
        raise
    finally:
        logger.info(f"{name}: Exiting gracefully.")

async def monitor_tasks(tasks, state: GlobalState):
    """Periodically logs the status of running tasks."""
    try:
        while not state.shutdown_event.is_set():

            # rugcheck queuesize
            rug_queue = state.get_rugcheck_queue() 
            rug_queue_size = rug_queue.qsize()

            # token subscriptions
            tokens_subscribed = list(await state.get_subscriptions())

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
                task_status.append(f"{task.get_name()}:{status}\n")

            logger.debug(
                f"\n"
                f"┌────────────────────────────────────\n"
                f"│📟 Task Monitor 📟\n"
                f"│────────────────────────────────────\n"
                f"│ Subscibed tokens: {len(tokens_subscribed)}\n"
                f"│ RugCheck Queue size: {rug_queue_size}\n"
                f"│ Active tasks: {len([t for t in tasks if not t.done()])}/{len(tasks)}\n"
                f"│ Tasks:\n"
                f"├── {'├── '.join(task_status)}"
                f"└────────────────────────────────────\n"
            )
            
            # Optionally check for stalled tasks
            for task in tasks:
                if not task.done() and task.get_name() in ["check_trading_opportunities", "rugcheck_worker"]:
                    logger.debug(f"🔍 Checking if task {task.get_name()} is stuck...")

            await asyncio.sleep(30)
    except asyncio.CancelledError:
        logger.info("Task Monitor: Cancelled.")
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

async def shutdown_all_tasks(tasks: list, ws_handler: WebSocketHandler, state: GlobalState):
    """Cancel and wait for all tasks to complete."""
    try:
        logger.debug("Shutting down WebSocket...")
        tokens_subscribed = list(await state.get_subscriptions())
        min_timout = len(tokens_subscribed) * 15
        await asyncio.wait_for(ws_handler.shutdown(), timeout=min_timout)
    except Exception as e:
        logger.error(f"WebSocket shutdown error: {e}", exc_info=True)
    
    for task in tasks:
        task.cancel()
    # Wait briefly to let tasks process cancellation
    await asyncio.sleep(0.1)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for task, result in zip(tasks, results):
        if isinstance(result, asyncio.CancelledError):
            logger.info(f"Task {task.get_name()} cancelled successfully.")
        elif isinstance(result, Exception):
            logger.error(f"Task {task.get_name()} raised an exception: {result}", exc_info=True)

async def main(cleanup: bool):
    setup_logging(debug=True)
    loop = asyncio.get_running_loop()
    # Get the singleton global state
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

    tasks = []

    # Setup WebSocket handler and connect.
    ws_handler = WebSocketHandler()
    await state.set_websocket_handler(ws_handler)
    await ws_handler.connect()
    tasks.extend(ws_handler.start(), name="WebSocket") 

    # Create a list of tasks to run concurrently.
    asyncio.create_task(task_worker("Worker-1", 2, state), name="Worker-1"),
    asyncio.create_task(task_worker("Worker-2", 3, state), name="Worker-2"),

    monitor = asyncio.create_task(monitor_tasks(tasks, state), name="Monitor")
    tasks.append(monitor)

    logger.info("Application started. Press CTRL+C to stop.")

    try:
        # Wait until the shutdown event is set
        await state.wait_for_shutdown()
    except Exception as e:
        logger.error("Main encountered an error: " + str(e))
    finally:
        logger.info("Shutdown signal received. Cancelling tasks...")
        # Optionally remove signal handlers (if they were added)
        for sig in (signal.SIGINT, signal.SIGTERM):
            if hasattr(loop, 'remove_signal_handler'):
                try:
                    loop.remove_signal_handler(sig)
                except Exception:
                    pass
        await shutdown_all_tasks(tasks, ws_handler, state)
        logger.info("All tasks have been shut down. Exiting.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot.")
    args = parser.parse_args()

    try:
        asyncio.run(main(cleanup=args.cleanup))
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting.")
    except Exception:
        logger.error("Unexpected error in the main event loop:", exc_info=True)
