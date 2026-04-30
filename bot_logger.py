# bot_logger.py
import inspect
import logging
import os
import queue
from datetime import datetime
from functools import wraps

import rich.align
import rich.box as _rich_box_module
import rich.console

# --- RICH COMPONENT IMPORTS AND RE-EXPORTS ---
import rich.panel
import rich.table
import rich.text
from rich.console import Console
from rich.logging import RichHandler

from config.config import _LOG_LEVEL_CONSOLE, _LOG_LEVEL_FILE, _LOG_STORAGE_PATH, _LOGGER_NAME

Panel = rich.panel.Panel
Table = rich.table.Table
Text = rich.text.Text
Align = rich.align.Align
Group = rich.console.Group
rich_box = _rich_box_module
# --- END RICH RE-EXPORTS ---

logger = logging.getLogger(name=_LOGGER_NAME)
log_queue = queue.Queue()
console_for_queue_capture = Console() # Define a console instance for capturing

# --- ADD THIS CUSTOM HANDLER ---
class DebugRichHandler(RichHandler):
    def emit(self, record: logging.LogRecord) -> None:
        # Log what RichHandler's emit method receives as record.msg
        is_rich_in_emit = hasattr(record.msg, "__rich_console__") or hasattr(record.msg, "__rich__")
        print(f"DEBUG_HANDLER_EMIT: Type of record.msg: {type(record.msg)}")
        print(f"DEBUG_HANDLER_EMIT: Is Panel instance: {isinstance(record.msg, Panel)}") # Use your re-exported Panel
        print(f"DEBUG_HANDLER_EMIT: Has __rich_console__ in emit: {hasattr(record.msg, '__rich_console__')}")
        print(f"DEBUG_HANDLER_EMIT: Has __rich__ in emit: {hasattr(record.msg, '__rich__')}")
        print(f"DEBUG_HANDLER_EMIT: String of record.msg: {str(record.msg)[:150]}...") # First 150 chars

        # Original RichHandler emit logic follows
        try:
            super().emit(record)
        except Exception as e:
            # This will catch errors happening *during* RichHandler's own processing
            print(f"DEBUG_HANDLER_EMIT: Error during super().emit(): {e}")
            # Fallback to basic printing if super().emit fails
            log_message = self.format(record) # Get the string formatted by the handler
            self.console.print(log_message, overflow="ignore", no_wrap=True) # Basic print
# --- END CUSTOM HANDLER ---


def setup_logging(logger_name=_LOGGER_NAME):
    """
    Setup logging with both file and console handlers using config-defined levels.
    """
    logger.setLevel(logging.DEBUG)
    if logger.hasHandlers():
        logger.handlers.clear()

    os.makedirs(_LOG_STORAGE_PATH, exist_ok=True)

    # File Handler
    try:
        file_handler = logging.FileHandler(
            f"{_LOG_STORAGE_PATH}/{logger_name}.log", encoding="utf-8"
        )
        file_level = logging.getLevelName(_LOG_LEVEL_FILE)
        file_handler.setLevel(file_level)

        file_formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(funcName)s() - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
    except Exception as e:
        logging.error(f"Failed to create file handler: {e}")
        file_handler = None

    console_handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        # Ensure RichHandler can handle renderables by not trying to stringify them too early
        # The default behavior should be fine.
    )
    console_level = logging.getLevelName(_LOG_LEVEL_CONSOLE)
    console_handler.setLevel(console_level)

    if file_handler:
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.propagate = False

    logger.debug(":writing_hand: [green]Logging system initialized with level:[/green] [bold red]%s[/bold red]", logging.getLevelName(logger.level))

    def log_to_queue(record):
        # Check if the message is already a Rich renderable object
        if hasattr(record.msg, '__rich_console__'):
            # Render the Rich object to a string for the queue
            with console_for_queue_capture.capture() as capture:
                console_for_queue_capture.print(record.msg)
            log_queue.put(capture.get().strip()) # Put stringified version
        else:
            log_queue.put(record.getMessage()) # Standard string message

    log_handler = logging.StreamHandler()
    # log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')) # Formatter might interfere with Rich renderables if not careful
    log_handler.emit = log_to_queue # type: ignore
    # logger.addHandler(log_handler) # Decide if this queue logging is still needed with Rich. For simplicity, can be commented out if not strictly used.


def rotate_log_file(logger_name=_LOGGER_NAME):
    """Rotate current log file with timestamp and create new log"""
    try:
        handlers = logger.handlers.copy()
        for handler in handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
                handler.close()
                logger.removeHandler(handler)

        log_path = f"{_LOG_STORAGE_PATH}/{logger_name}.log"
        if os.path.exists(log_path):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_name = f"{_LOG_STORAGE_PATH}/{_LOGGER_NAME}.{timestamp}.log"
            os.rename(log_path, new_name)
            logger.info(f"Log rotated to: {new_name}")

        setup_logging() # This re-initializes handlers, including RichHandler
        logger.info(":newspaper: Initialized new log file after rotation")

    except Exception as e:
        logger.error(f":exclamation: Log rotation failed: {str(e)}", exc_info=True)


# -------------------------------
# 🚀 Contextual Logging Functions
# -------------------------------

def _get_caller_context():
    frame = inspect.currentframe()
    # Go up the stack to find the caller outside of logger.py
    while frame and frame.f_code.co_filename == __file__:
        frame = frame.f_back # type: ignore
    if not frame: # Should not happen in normal use
        return "[unknown_context]"

    func_name = frame.f_code.co_name
    cls = frame.f_locals.get("self", None)
    class_name = cls.__class__.__name__ if cls else None
    return f"[{class_name}.{func_name}]" if class_name else f"[{func_name}]"


def log_with_context(level, msg, *args, **kwargs):
    # If msg is a Rich renderable, it's passed directly to logger.log.
    # Otherwise, context is prepended.
    if not hasattr(msg, '__rich_console__'): # Check if msg is NOT a Rich renderable
        context = _get_caller_context()
        logger.log(level, f"{context} {msg}", *args, **kwargs) # msg becomes part of an f-string -> str(msg)
    else: # msg IS a Rich renderable (like your Panel)
        logger.log(level, msg, *args, **kwargs) # msg is passed AS IS (the Panel object)


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
        func_name_for_log = func.__name__ # Get func name at decoration time

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # For decorators, explicitly construct the context string
            cls = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
            context = f"[{cls}.{func_name_for_log}]" if cls else f"[{func_name_for_log}]"

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
            cls = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
            context = f"[{cls}.{func_name_for_log}]" if cls else f"[{func_name_for_log}]"

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
