"""
Processes trade messages from the PumpPortal queue and writes them in batches to the database.
"""

import asyncio
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from bot_logger import logger
from state_manager import GlobalState
from utils import calculate_market_cap 
from config.config import _TOTAL_SUPPLY # Import TOTAL_SUPPLY from config

async def trade_worker():
    """Processes trade messages from queue and writes them in batches to the database."""
    state = GlobalState.get_instance()
    db_client = state.db_client

    if not db_client:
        logger.error("Trade worker cannot start: DatabaseClient not initialized in GlobalState.")
        return

    # Wait for the single, persistent WebSocketHandler instance to be available.
    websocket_handler = None
    while not state.shutdown_event.is_set():
        websocket_handler = state.websocket_handler
        if websocket_handler:
            logger.info("Trade worker has acquired stable WebSocketHandler instance. Proceeding.")
            break
        logger.info("Trade worker is waiting for WebSocketHandler to become available...")
        await state.wait_or_interrupt(timeout=2)
    
    if not websocket_handler:
        logger.warning("Trade worker exiting as shutdown was signaled while waiting for WebSocketHandler.")
        return

    # The trade_queue reference is now stable and will never change.
    trade_queue = websocket_handler.trade_queue

    trade_queue = websocket_handler.trade_queue
    BATCH_SIZE = 100
    BATCH_TIMEOUT = 5

    logger.info("🚀 Trade worker started.")

    while not state.shutdown_event.is_set():
        # The complex logic to re-check the handler instance is no longer needed.
        batch_from_queue = []
        trade_params_to_db = []
        mints_in_batch = []

        try:
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

            for data in batch_from_queue:
                mint = data.get('mint')
                if not mint or mint not in active_subscriptions:
                    trade_queue.task_done()
                    continue

                try:
                    # --- START OF FIX ---
                    # Safely convert potentially malformed API data to Decimal.
                    # This handles cases where the API sends None, empty strings, or other non-numeric values.
                    raw_token_amount = data.get('tokenAmount')
                    raw_sol_amount = data.get('solAmount')
                    raw_market_cap_sol = data.get('marketCapSol')
                    raw_v_tokens = data.get('vTokensInBondingCurve')
                    raw_v_sol = data.get('vSolInBondingCurve')

                    token_amount = Decimal(str(raw_token_amount)) if raw_token_amount else Decimal('0')
                    sol_amount = Decimal(str(raw_sol_amount)) if raw_sol_amount else Decimal('0')
                    # --- END OF FIX ---
                    
                    if token_amount <= 0 or sol_amount <= 0:
                        trade_queue.task_done()
                        continue
                        
                    price = sol_amount / token_amount
                    # --- START OF FIX (Continued) ---
                    market_cap_sol = Decimal(str(raw_market_cap_sol)) if raw_market_cap_sol else Decimal('0')
                    v_tokens_in_bc = Decimal(str(raw_v_tokens)) if raw_v_tokens else Decimal('0')
                    v_sol_in_bc = Decimal(str(raw_v_sol)) if raw_v_sol else Decimal('0')
                    # --- END OF FIX (Continued) ---

                    market_cap_calculated = market_cap_sol * sol_price_decimal

                    trade_params_to_db.append((
                        data.get('signature'), mint, None, data.get('txType'),
                        token_amount, sol_amount, price,
                        data.get('bondingCurveKey', ""),
                        v_tokens_in_bc,
                        v_sol_in_bc,
                        market_cap_sol, sol_price_decimal, market_cap_calculated,
                        data.get('received_at_timestamp', datetime.now(timezone.utc))
                    ))
                    mints_in_batch.append(mint)
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Invalid data for trade (Sig: {data.get('signature')}). Skipping. Error: {e}", exc_info=True)
                    trade_queue.task_done()
                except Exception as e:
                    logger.error(f"Unexpected error processing trade item (Sig: {data.get('signature')}). Error: {e}", exc_info=True)
                    trade_queue.task_done()

            if trade_params_to_db:
                try:
                    await db_client.insert_trades_batch(trade_params_to_db, mints_in_batch)
                    
                    for item in batch_from_queue:
                        try:
                            trade_queue.task_done()
                        except ValueError:
                            pass
                    
                    logger.debug(f"Successfully processed and saved a batch of {len(trade_params_to_db)} trades.")

                except Exception as e:
                    logger.error(f"🚨 Trade worker failed during batch insert. The batch will be retried. Error: {e}", exc_info=True)
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"🚨 Unexpected error in trade worker main loop: {e}", exc_info=True)
            await asyncio.sleep(5)

    logger.info("🛑 Trade worker shutting down.")