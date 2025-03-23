import logging
from rich.logging import RichHandler

logger = logging.getLogger("TradingBot")
logger.setLevel(logging.DEBUG)

def setup_logging(debug: bool = True):
    """
    Setup logging with both file and console handlers.
    """
    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler("data/sniper.log", encoding="utf-8")
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
