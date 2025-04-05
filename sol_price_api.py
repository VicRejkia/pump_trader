
import asyncio
import httpx
import json
from config import SOL_PRICE_API_URL
from logger import logger


async def update_sol_price(state):
    """Periodically fetches and updates the global SOL price from an external API."""
    logger.info("🚀 Starting update_sol_price task...") # Add log here
    try:
        while not state.shutdown_event.is_set():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(SOL_PRICE_API_URL)
                    if response.status_code == 200:
                        data = response.json()
                        new_price = data.get("solana", {}).get("usd")
                        await state.set_sol_price(new_price)
                        logger.info(f"✅ Updated Solana price: {new_price} USD")
                    else:
                        logger.error(f"⚠ Error fetching Solana price: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Exception fetching Solana price: {e}", exc_info=True)
            
            if not state.shutdown_event.is_set():
                logger.debug("⏳ update_sol_price sleeping for 1 hour...") # Add log before sleep
                # 🚀 Sleep interruptibly
                await state.wait_or_interrupt(timeout=3600) # 1 hour
    except asyncio.CancelledError:
        logger.info("⏹ update_sol_price task cancelled.")
        # No need to raise CancelledError again, it's handled by the caller (main.py shutdown)
    except Exception as e: # Catch any other unexpected error
        logger.error(f"💥 UNEXPECTED ERROR in update_sol_price task: {e}", exc_info=True)
    logger.info("🛑 update_sol_price task finished.") # Add log at the end
