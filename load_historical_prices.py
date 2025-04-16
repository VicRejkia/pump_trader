import json
from datetime import datetime, timezone
import asyncio
from typing import List, Dict
from logger import logger  # Assuming you have a logger configured
from database_handler import DatabaseClient  # Import your existing DatabaseClient


async def load_and_insert_historical_prices(json_file_path: str, db_client: DatabaseClient):
    """
    Load historical OHLCV data from a JSON file, calculate the mean price for each hour,
    and insert it into the sol_price_usd table.
    """
    logger.info("🚀 Starting historical SOL price insertion task...")

    try:
        # Load the JSON file
        with open(json_file_path, 'r') as f:
            ohlcv_data: List[Dict] = json.load(f)

        if not ohlcv_data:
            logger.error("JSON file is empty or invalid.")
            return

        logger.info(f"Loaded {len(ohlcv_data)} OHLCV records from the JSON file.")

        # Process each record
        for record in ohlcv_data:
            try:
                # Extract relevant fields
                time_ms = record.get("time")
                open_price = record.get("open")
                high_price = record.get("high")
                low_price = record.get("low")
                close_price = record.get("close")

                # Validate the data
                if None in (time_ms, open_price, high_price, low_price, close_price):
                    logger.warning(f"Skipping invalid record: {record}")
                    continue

                # Calculate the mean price
                mean_price = (open_price + high_price + low_price + close_price) / 4

                # Convert the timestamp to a Python datetime object
                timestamp = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)

                # Insert the mean price and timestamp into the database
                await db_client.insert_sol_price(mean_price, timestamp)
                logger.debug(f"Inserted SOL price: {mean_price} USD at {timestamp}")

            except Exception as e:
                logger.error(f"Error processing record {record}: {e}", exc_info=True)

        logger.info("✅ Historical SOL price insertion completed successfully.")

    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR during historical SOL price insertion: {e}", exc_info=True)


# Example usage
if __name__ == "__main__":
    # Path to the JSON file containing OHLCV data
    JSON_FILE_PATH = "data/hour_CryptoCompare_Index_SOL_USD_387_11744737723806.json"

    # Initialize the database client
    db_client = DatabaseClient()

    async def main():
        try:
            # Connect to the database
            await db_client.connect()
            
            # Load and insert historical prices
            await load_and_insert_historical_prices(JSON_FILE_PATH, db_client)
        finally:
            # Close the database connection pool
            if db_client.pool:
                await db_client.pool.close()

    # Run the script
    asyncio.run(main())