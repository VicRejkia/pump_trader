"""
Processes trade messages from the PumpPortal queue and writes them in batches to the database.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from bot_logger import logger
from config.config import _TOTAL_SUPPLY
from state_manager import GlobalState
from utils import calculate_market_cap


async def trade_worker(trade_queue: asyncio.Queue):
    """
    Processes trade messages from the provided queue and writes them in batches to the database.
    """
    state = GlobalState.get_instance()
    db_client = state.db_client

    if not db_client:
        logger.error(":police_car_light: Trade worker cannot start: DatabaseClient not initialized in GlobalState.")
        return

    BATCH_SIZE = 100
    BATCH_TIMEOUT = 5

    logger.info(":rocket: Trade worker started.")

    while not state.shutdown_event.is_set():
        batch_from_queue = []
        trade_params_to_db = []
        mints_in_batch = []

        try:
            # Collect trades for a batch until BATCH_SIZE is reached or BATCH_TIMEOUT expires
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
                await asyncio.sleep(0.1) # Prevent busy-waiting if queue is empty
                continue

            active_subscriptions = await state.get_token_subscriptions()
            sol_price = await state.get_sol_price()
            sol_price_decimal = Decimal(sol_price) if sol_price is not None else Decimal('0')


            for data in batch_from_queue:
                mint = data.get('mint')
                # Process only if the token is actively subscribed
                if not mint or mint not in active_subscriptions:
                    trade_queue.task_done()
                    continue

                try:
                    # Safely convert API data to Decimal
                    token_amount_raw = data.get('tokenAmount')
                    sol_amount_raw = data.get('solAmount')

                    token_amount = Decimal(str(token_amount_raw)) if token_amount_raw else Decimal('0')
                    sol_amount = Decimal(str(sol_amount_raw)) if sol_amount_raw else Decimal('0')

                    # Skip trades with invalid amounts
                    if token_amount <= 0 or sol_amount <= 0:
                        trade_queue.task_done()
                        continue

                    price = sol_amount / token_amount
                    market_cap_sol = Decimal(str(data.get('marketCapSol'))) if data.get('marketCapSol') else Decimal('0')
                    v_tokens_in_bc = Decimal(str(data.get('vTokensInBondingCurve'))) if data.get('vTokensInBondingCurve') else Decimal('0')
                    v_sol_in_bc = Decimal(str(data.get('vSolInBondingCurve'))) if data.get('vSolInBondingCurve') else Decimal('0')

                    market_cap_calculated = market_cap_sol * sol_price_decimal

                    trade_params_to_db.append((
                        data.get('signature'), mint, data.get('traderPublicKey'), data.get('txType'),
                        token_amount, sol_amount, price,
                        data.get('bondingCurveKey', ""),
                        v_tokens_in_bc, v_sol_in_bc,
                        market_cap_sol, sol_price_decimal, market_cap_calculated,
                        datetime.now(timezone.utc) # Use current time as fallback for timestamp
                    ))
                    mints_in_batch.append(mint)
                except (InvalidOperation, TypeError) as e:
                    logger.error(f":police_car_light: Invalid data for trade (Sig: {data.get('signature')}). Skipping. Error: {e}")
                    trade_queue.task_done()
                except Exception as e:
                    logger.error(f":police_car_light: Unexpected error processing trade item (Sig: {data.get('signature')}). Error: {e}", exc_info=True)
                    trade_queue.task_done()

            if trade_params_to_db:
                try:
                    await db_client.insert_trades_batch(trade_params_to_db, mints_in_batch)

                    # Mark all items in the processed batch as done
                    for _ in batch_from_queue:
                        try:
                            trade_queue.task_done()
                        except ValueError:
                            pass # Can happen if queue is manipulated elsewhere, safe to ignore

                    logger.debug(f":bank: Successfully processed and saved a batch of {len(trade_params_to_db)} trades.")

                except Exception as e:
                    logger.error(f":police_car_light: Trade worker failed during batch insert. Error: {e}", exc_info=True)
                    # Note: In case of DB failure, items remain in queue and will be re-processed, which is the desired behavior.
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info(":stop_sign: Trade worker task cancelled.")
            break
        except Exception as e:
            logger.error(f"🚨 Unexpected error in trade worker main loop: {e}", exc_info=True)
            await asyncio.sleep(5)

    logger.info(":stop_sign: Trade worker shutting down.")
