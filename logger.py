import os
from datetime import datetime
import logging
from rich.logging import RichHandler
from config import LOGGER_NAME, LOG_LEVEL, LOG_FILE

logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)

def setup_logging(debug: bool = True):
    """
    Setup logging with both file and console handlers.
    """
    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    console_handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True
    )
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def rotate_log_file():
    """Rotate current log file with timestamp and create new log"""
    logger = logging.getLogger(LOGGER_NAME)
    try:
        # Close existing file handlers
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
        
        # Rename existing log file
        if os.path.exists(LOG_FILE):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_name = f"data/sniper.{timestamp}.log"
            os.rename(LOG_FILE, new_name)
            logger.info(f"MOVED log to {new_name}")
        
        # Reinitialize logging
        setup_logging(debug=logger.level == logging.DEBUG)
        logging.getLogger(LOGGER_NAME).info("Intialized new log file after rotation")
    
    except Exception as e:
        logging.error(f"Log rotation failed: {e}", exc_info=True)