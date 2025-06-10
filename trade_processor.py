"""
Processes trade messages from the PumpPortal queue and writes them in batches to the database.
"""

import asyncio
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from bot_logger import logger
from state_manager import GlobalState
from utils import calculate_market_cap 
from config import _TOTAL_SUPPLY # Import TOTAL_SUPPLY from config

async def trade_worker():
    """Processes trade messages from queue and writes them in batches to the database."""
    state = GlobalState.get_instance()
    db_client = state.db_client # Get DatabaseClient from GlobalState
    websocket_handler = state.websocket_handler # Get WebSocketHandler from GlobalState
    enrichment_queue = state.get_enrichment_queue() # Get the enrichment queue from the global state

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
        batch_from_queue = []
        trade_params_to_db = []
        mints_in_batch = []

        try:
            # Collect a batch of items from the queue
            start_time = asyncio.get_event_loop().time()
            while len(batch_from_queue) < BATCH_SIZE:
                remaining_time = BATCH_TIMEOUT - (asyncio.get_event_loop().time() - start_time)
                if remaining_time <= 0:
                    break
                try:
                    trade_data = await asyncio.wait_for(trade_queue.get(), timeout=remaining_time)
                    batch_from_queue.append(trade_data)
                except asyncio.TimeoutError:
                    break

            if not batch_from_queue:
                await asyncio.sleep(0.1)
                continue

            active_subscriptions = await state.get_token_subscriptions()
            sol_price_decimal = Decimal(await state.get_sol_price() or 0)

            # Prepare the database parameters from the batch
            for data in batch_from_queue:
                mint = data.get('mint')
                if not mint or mint not in active_subscriptions:
                    # This item is invalid or for an unsubscribed token, mark it as done immediately.
                    trade_queue.task_done()
                    continue

                try:
                    token_amount = Decimal(str(data.get('tokenAmount', 0)))
                    sol_amount = Decimal(str(data.get('solAmount', 0)))
                    
                    # Skip trades with no amounts
                    if token_amount <= 0 or sol_amount <= 0:
                        trade_queue.task_done()
                        continue
                        
                    price = sol_amount / token_amount
                    market_cap_sol = Decimal(str(data.get('marketCapSol', 0)))

                    # Use a fallback for market_cap_calculated if needed
                    market_cap_calculated = market_cap_sol * sol_price_decimal

                    trade_params_to_db.append((
                        data.get('signature'), mint, None, data.get('txType'),
                        token_amount, sol_amount, price,
                        data.get('bondingCurveKey', ""),
                        Decimal(str(data.get('vTokensInBondingCurve', 0))),
                        Decimal(str(data.get('vSolInBondingCurve', 0))),
                        market_cap_sol, sol_price_decimal, market_cap_calculated,
                        data.get('received_at_timestamp', datetime.now(timezone.utc))
                    ))
                    mints_in_batch.append(mint)
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Invalid data for trade (Sig: {data.get('signature')}). Skipping. Error: {e}", exc_info=True)
                    trade_queue.task_done() # Mark invalid item as done
                except Exception as e:
                    logger.error(f"Unexpected error processing trade item (Sig: {data.get('signature')}). Error: {e}", exc_info=True)
                    trade_queue.task_done() # Mark errored item as done to prevent blockage


            # --- CRITICAL CHANGE: DB write happens BEFORE task_done ---
            if trade_params_to_db:
                try:
                    # Attempt to write the prepared batch to the database
                    await db_client.insert_trades_batch(trade_params_to_db, mints_in_batch)
                    
                    # <<< ADD THIS BLOCK TO POPULATE ENRICHMENT QUEUE >>>
                    # for sig in signatures_for_enrichment:
                    #     await enrichment_queue.put(sig)
                    # logger.debug(f"Added {len(signatures_for_enrichment)} signatures to enrichment queue.")
                    # <<< END BLOCK >>>
                    
                    # SUCCESS: The DB write was successful. Now, mark all items in the batch as done.
                    for item in batch_from_queue:
                        # We must check if the item was processed into trade_params_to_db,
                        # as some might have been skipped (e.g., unsubscribed).
                        # A simpler way is to just call task_done for every item retrieved.
                        # The ones already marked done will be ignored.
                        try:
                            trade_queue.task_done()
                        except ValueError:
                            # This can happen if a task is already marked as done, which is fine.
                            pass
                    
                    logger.debug(f"Successfully processed and saved a batch of {len(trade_params_to_db)} trades.")

                except Exception as e:
                    # FAILURE: The DB write failed. The items are still in the queue because we haven't
                    # called task_done(). They will be retried in the next loop.
                    logger.error(f"🚨 Trade worker failed during batch insert. The batch will be retried. Error: {e}", exc_info=True)
                    # We add a small sleep to prevent a tight loop if the DB is down.
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"🚨 Unexpected error in trade worker main loop: {e}", exc_info=True)
            await asyncio.sleep(5)

    logger.info("🛑 Trade worker shutting down.")