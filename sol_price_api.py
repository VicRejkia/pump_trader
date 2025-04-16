
import asyncio
import httpx
import json
from config import SOL_PRICE_API_URL
from logger import logger
from database_handler import DatabaseClient


async def update_sol_price(state, db_client: DatabaseClient):
    """Periodically fetches and updates the global SOL price from an external API."""
    logger.info("🚀 Starting update_sol_price task...")

    try:
        while True:
            if state.shutdown_event.is_set():
                logger.info("Shutdown event detected. Exiting update_sol_price task.")
                break

            try:
                # Fetch the SOL price from an external API
                async with httpx.AsyncClient() as client:
                    response = await client.get(SOL_PRICE_API_URL)
                    if response.status_code == 200:
                        data = response.json()
                        new_price = data.get("solana", {}).get("usd")
                        if new_price is None or not isinstance(new_price, (int, float)):
                            logger.error("Invalid or missing SOL price in API response.")
                            continue

                        # Update the in-memory state and database
                        #async with state.lock:
                        await state.set_sol_price(new_price)
                        await db_client.insert_sol_price(new_price)

                        logger.info(f"✅ Updated Solana price: {new_price} USD")
                    else:
                        logger.error(f"⚠ Error fetching Solana price. Status code: {response.status_code}, Response: {response.text}")
            except Exception as e:
                logger.error(f"❌ Exception in update_sol_price task: {e}", exc_info=True)

            logger.debug("⏳ Sleeping for 1 hour...")
            await state.wait_or_interrupt(timeout=3600)

    except asyncio.CancelledError:
        logger.info("⏹ update_sol_price task cancelled.")
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in update_sol_price task: {e}", exc_info=True)
    finally:
        logger.info("🛑 update_sol_price task finished.")
