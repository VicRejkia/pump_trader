import os

import uvicorn

from bot_logger import logger, setup_logging

# Set up logging immediately
setup_logging(logger_name="pump_trader_v3")

# Import the main FastAPI app
try:
    from api.main import app
except ImportError as e:
    logger.critical(f"Failed to import FastAPI app: {e}")
    logger.critical("Please ensure all dependencies from requirements.txt are installed.")
    exit(1)

# Define host and port (can be moved to config/app.yaml later)
APP_HOST = os.getenv("PUMP_TRADER_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("PUMP_TRADER_PORT", 8000))

if __name__ == "__main__":
    logger.info(f"🚀 Starting PumpTrader v3.0 C&C Hub at http://{APP_HOST}:{APP_PORT}")

    # uvicorn.run expects the import string "api.main:app"
    # This allows for hot-reloading when run with --reload
    uvicorn.run(
        "api.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=True, # Set to False in production
        log_level="info"
    )
