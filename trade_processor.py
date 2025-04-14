"""
Processes trade messages from the PumpPortal queue and writes them in batches to the database.
"""

import asyncio
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from logger import logger
from state_manager import GlobalState
from utils import calculate_market_cap 
from config import TOTAL_SUPPLY # Import TOTAL_SUPPLY from config

async def trade_worker():
    """Processes trade messages from queue and writes them in batches to the database."""
    state = GlobalState.get_instance()
    db_client = state.db_client # Get DatabaseClient from GlobalState
    websocket_handler = state.websocket_handler # Get WebSocketHandler from GlobalState

    # Add check for db_client
    if not db_client:
        logger.error("Trade worker cannot start: DatabaseClient not initialized in GlobalState.")
        return # Exit if db_client is not ready

    if not websocket_handler:
        logger.error("Trade worker cannot start: WebSocketHandler not initialized in GlobalState.")
        return # Exit if websocket_handler is not ready

    trade_queue = websocket_handler.trade_queue # Get trade queue
    logger.debug(f"Trade queue: {trade_queue}")

    BATCH_SIZE = 100  # Number of trades per batch
    BATCH_TIMEOUT = 5 # Seconds to wait for new trades before processing batch

    logger.info("🚀 Trade worker started.")

    while not state.shutdown_event.is_set():
        batch = []
        mints_in_batch = []
        trade_params = []

        try:
            # Collect batch with timeout
            start_time = asyncio.get_event_loop().time()
            while len(batch) < BATCH_SIZE:
                try:
                    # Calculate remaining time for the batch timeout
                    remaining_time = BATCH_TIMEOUT - (asyncio.get_event_loop().time() - start_time)
                    if remaining_time <= 0:
                        break # Timeout reached

                    trade_data = await asyncio.wait_for(trade_queue.get(), timeout=remaining_time)
                    batch.append(trade_data)
                except asyncio.TimeoutError:
                    break # No more trades available within the timeout

            if not batch:
                # If no trades were collected (even after timeout), sleep briefly and continue
                await asyncio.sleep(0.1)
                continue

            # Prepare parameters for batch insert
            active_subscriptions = await state.get_token_subscriptions() # Get current subscriptions

            for data in batch:
                mint = data.get('mint')
                signature = data.get('signature')

                if not mint or not signature:
                    logger.warning(f"Skipping trade with missing mint or signature: {data}")
                    trade_queue.task_done() # Mark invalid item as done
                    continue

                if mint not in active_subscriptions:
                    # logger.debug(f"Skipping trade for unsubscribed token {mint} (Sig: {signature})")
                    trade_queue.task_done() # Mark skipped item as done
                    continue

                try:
                    # Safely convert to Decimal, handle potential errors
                    token_amount = Decimal(str(data.get('tokenAmount', 0)))
                    sol_amount = Decimal(str(data.get('solAmount', 0)))
                    v_tokens = Decimal(str(data.get('vTokensInBondingCurve', 0)))
                    v_sol = Decimal(str(data.get('vSolInBondingCurve', 0)))
                    market_cap_sol = Decimal(str(data.get('marketCapSol', 0)))

                    # Calculate price safely
                    price = (sol_amount / token_amount) if token_amount else Decimal(0)

                    # Calculate market cap
                    market_cap_calculated = calculate_market_cap(
                        v_tokens,
                        v_sol,
                        Decimal(str(data.get('totalSupply', TOTAL_SUPPLY))) # Use TOTAL_SUPPLY from config
                    )

                    trade_params.append((
                        signature,
                        mint,
                        data.get('txType'),
                        token_amount,
                        sol_amount,
                        price,
                        data.get('bondingCurveKey', ""),
                        v_tokens,
                        v_sol,
                        market_cap_sol,
                        market_cap_calculated,
                        datetime.now(timezone.utc) # Use current UTC time for timestamp
                    ))
                    mints_in_batch.append(mint)

                except InvalidOperation as e:
                    logger.error(f"Invalid decimal conversion for trade {signature} (Mint: {mint}): {e}. Data: {data}", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to process trade {signature} (Mint: {mint}): {e}. Data: {data}", exc_info=True)
                finally:
                    trade_queue.task_done() # Ensure task_done is called once per item

            # Batch insert trades (if any valid trades were processed)
            if trade_params:
                try:
                    await db_client.insert_trades_batch(trade_params, mints_in_batch)
                    # Logger message is now inside insert_trades_batch
                except Exception as e:
                    # Error is logged within insert_trades_batch, but we log here too for context
                    logger.error(f"🚨 Trade worker failed during batch insert: {e}", exc_info=True)
                    # Note: If insert_trades_batch fails, the transaction should roll back.
                    # Items remain in the queue implicitly due to task_done() not being called on failure within the loop.
                    # Consider adding retry logic or moving failed items to a dead-letter queue if needed.

        except Exception as e:
            logger.error(f"🚨 Unexpected error in trade worker loop: {e}", exc_info=True)
            # Avoid busy-looping on persistent errors
            await asyncio.sleep(5)

    logger.info("🛑 Trade worker shutting down.")