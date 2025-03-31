import os
from datetime import datetime
import logging
from rich.logging import RichHandler
from config import LOGGER_NAME, LOG_LEVEL_CONSOLE, LOG_LEVEL_FILE, LOG_STORAGE_PATH

logger = logging.getLogger(LOGGER_NAME)

def setup_logging():
    """
    Setup logging with both file and console handlers using config-defined levels.
    """
    logger.setLevel(logging.DEBUG)  # Set logger level to lowest threshold
    if logger.hasHandlers():
        logger.handlers.clear()

    # Ensure log directory exists
    os.makedirs(LOG_STORAGE_PATH, exist_ok=True)

    # Configure File Handler
    try:
        file_handler = logging.FileHandler(
            f"{LOG_STORAGE_PATH}/{LOGGER_NAME}.log",
            encoding="utf-8"
        )
        file_level = logging.getLevelName(LOG_LEVEL_FILE)
        file_handler.setLevel(file_level)
        
        file_formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
    except Exception as e:
        logging.error(f"Failed to create file handler: {e}")
        file_handler = None

    # Configure Console Handler
    console_handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True
    )
    console_level = logging.getLevelName(LOG_LEVEL_CONSOLE)
    console_handler.setLevel(console_level)

    # Add handlers to logger
    if file_handler:
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.debug("Logging system initialized with level: %s", logging.getLevelName(logger.level))

def rotate_log_file():
    """Rotate current log file with timestamp and create new log"""
    try:
        # Close and remove existing file handlers
        logger_handlers = logger.handlers.copy()
        for handler in logger_handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
        
        # Rename existing log file with timestamp
        log_path = f"{LOG_STORAGE_PATH}/{LOGGER_NAME}.log"
        if os.path.exists(log_path):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_name = f"{LOG_STORAGE_PATH}/{LOGGER_NAME}.{timestamp}.log"
            os.rename(log_path, new_name)
            logger.info(f"Log rotated to: {new_name}")
        
        # Reinitialize logging configuration
        setup_logging()
        logger.info("Intialized new log file after rotation")
    
    except Exception as e:
        logger.error(f"Log rotation failed: {str(e)}", exc_info=True)