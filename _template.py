import asyncio
import signal
from logger import logger

# Global shutdown event that tasks can wait on
shutdown_event = asyncio.Event()

async def task_worker(name: str, interval: float):
    """A sample worker task that periodically does work until shutdown."""
    try:
        while not shutdown_event.is_set():
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

async def monitor_tasks(tasks):
    """Periodically logs the status of running tasks."""
    try:
        while not shutdown_event.is_set():
            statuses = [f"{t.get_name()} ({'done' if t.done() else 'running'})" for t in tasks]
            logger.debug("Task Monitor: " + ", ".join(statuses))
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("Task Monitor: Cancelled.")
        raise

def register_signal_handlers(loop):
    """Register signal handlers that set the shutdown event if supported."""
    def signal_handler():
        logger.info("Signal received, initiating shutdown...")
        shutdown_event.set()
    # On Windows with the Proactor event loop, add_signal_handler is not supported.
    # Check if it's available first.
    for sig in (signal.SIGINT, signal.SIGTERM):
        if hasattr(loop, 'add_signal_handler'):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                logger.warning(f"Signal handlers not supported for {sig} on this platform.")
        else:
            logger.warning("add_signal_handler not available on this event loop.")

async def shutdown_all_tasks(tasks):
    """Cancel and wait for all tasks to complete."""
    logger.info("Cancelling tasks...")
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

async def main():
    loop = asyncio.get_running_loop()
    register_signal_handlers(loop)

    # Create a list of tasks to run concurrently.
    tasks = [
        asyncio.create_task(task_worker("Worker-1", 2), name="Worker-1"),
        asyncio.create_task(task_worker("Worker-2", 3), name="Worker-2"),
    ]
    monitor = asyncio.create_task(monitor_tasks(tasks), name="Monitor")
    tasks.append(monitor)

    logger.info("Application started. Press CTRL+C to stop.")

    try:
        # Wait until the shutdown event is set
        await shutdown_event.wait()
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
        await shutdown_all_tasks(tasks)
        logger.info("All tasks have been shut down. Exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting.")
    except Exception:
        logger.error("Unexpected error in the main event loop:", exc_info=True)
