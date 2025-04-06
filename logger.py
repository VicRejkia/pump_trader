import os
import inspect
from datetime import datetime
import logging
from functools import wraps
from rich.logging import RichHandler
from rich.console import Console
from config import LOGGER_NAME, LOG_LEVEL_CONSOLE, LOG_LEVEL_FILE, LOG_STORAGE_PATH

logger = logging.getLogger(LOGGER_NAME)
console = Console()

def setup_logging():
    """
    Setup logging with both file and console handlers using config-defined levels.
    """
    logger.setLevel(logging.DEBUG)
    if logger.hasHandlers():
        logger.handlers.clear()

    os.makedirs(LOG_STORAGE_PATH, exist_ok=True)

    # File Handler
    try:
        file_handler = logging.FileHandler(
            f"{LOG_STORAGE_PATH}/{LOGGER_NAME}.log", encoding="utf-8"
        )
        file_level = logging.getLevelName(LOG_LEVEL_FILE)
        file_handler.setLevel(file_level)

        file_formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(funcName)s() - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
    except Exception as e:
        logging.error(f"Failed to create file handler: {e}")
        file_handler = None

    # Console Handler (Rich)
    console_handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
    )
    console_level = logging.getLevelName(LOG_LEVEL_CONSOLE)
    console_handler.setLevel(console_level)

    if file_handler:
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.debug(":writing_hand: [green]Logging system initialized with level:[/green] [bold red]%s[/bold red]", logging.getLevelName(logger.level))


def rotate_log_file():
    """Rotate current log file with timestamp and create new log"""
    try:
        handlers = logger.handlers.copy()
        for handler in handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
                handler.close()
                logger.removeHandler(handler)

        log_path = f"{LOG_STORAGE_PATH}/{LOGGER_NAME}.log"
        if os.path.exists(log_path):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_name = f"{LOG_STORAGE_PATH}/{LOGGER_NAME}.{timestamp}.log"
            os.rename(log_path, new_name)
            logger.info(f"Log rotated to: {new_name}")

        setup_logging()
        logger.info("Initialized new log file after rotation")

    except Exception as e:
        logger.error(f"Log rotation failed: {str(e)}", exc_info=True)


# -------------------------------
# 🚀 Contextual Logging Functions
# -------------------------------

def _get_caller_context():
    frame = inspect.currentframe().f_back.f_back
    func_name = frame.f_code.co_name
    cls = frame.f_locals.get("self", None)
    class_name = cls.__class__.__name__ if cls else None
    return f"[{class_name}.{func_name}]" if class_name else f"[{func_name}]"


def log_with_context(level, msg, *args, **kwargs):
    context = _get_caller_context()
    logger.log(level, f"{context} {msg}", *args, **kwargs)


def log_debug(msg, *args, **kwargs):
    log_with_context(logging.DEBUG, msg, *args, **kwargs)

def log_info(msg, *args, **kwargs):
    log_with_context(logging.INFO, msg, *args, **kwargs)

def log_warning(msg, *args, **kwargs):
    log_with_context(logging.WARNING, msg, *args, **kwargs)

def log_error(msg, *args, **kwargs):
    log_with_context(logging.ERROR, msg, *args, **kwargs)

def log_critical(msg, *args, **kwargs):
    log_with_context(logging.CRITICAL, msg, *args, **kwargs)

# -------------------------------------
# 🧙 Decorators: Auto Entry/Exit Logging
# -------------------------------------

def log_calls(level=logging.DEBUG):
    """
    Decorator to automatically log entry and exit of a function.
    Supports both sync and async functions.
    """
    def decorator(func):
        is_coroutine = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = _get_caller_context()
            logger.log(level, f"{context} → Entered")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"{context} ← Exited")
                return result
            except Exception as e:
                logger.exception(f"{context} ❌ Exception: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = _get_caller_context()
            logger.log(level, f"{context} → Entered")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{context} ← Exited")
                return result
            except Exception as e:
                logger.exception(f"{context} ❌ Exception: {e}")
                raise

        return async_wrapper if is_coroutine else sync_wrapper

    return decorator
