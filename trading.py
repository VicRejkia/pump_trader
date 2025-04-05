"""
Handles trading logic including buy/sell decision making, volatility calculation, 
emergency sell triggers, and portfolio management.
"""
import asyncio
import numpy as np
import json
from datetime import datetime, timezone

# Removed incorrect load_config import. Config is passed during initialization.
#rom database import get_total_supply # Keep if needed outside manager, otherwise remove
from logger import logger
from utils import (
    play_buy_opportunity_sound, play_sell_sl_sound_async, play_sell_tp_sound_async,
    format_buy_order_log # calculate_market_cap might not be needed if done in SQL/price fetch
)
# Removed unused imports like np, json, get_db, calculate_market_cap (if not used)
# Config dictionary is passed in __init__

class TradingManager:
    def __init__(self, db_pool, config, state):
        self.db = db_pool # Expecting an asyncpg Pool
        self.config = config
        self.state = state # Set state during initialization
    async def check_trading_opportunities(self):
        """Check for new trading opportunities based on configured criteria."""
        if self.state.shutdown_event.is_set():
            return

        try:
            sol_price = await self.state.get_sol_price()
            if sol_price is None or sol_price <= 0:
                logger.warning(f"⚠ Invalid SOL_PRICE ({sol_price}); skipping buy check.")
                return # Cannot proceed without valid SOL price

            async with self.db.acquire() as conn:
                # Transaction might not be needed for read-heavy check, but keep for consistency
                async with conn.transaction():
                    try:
                        time_interval_minutes = self.config['DEFAULT_TIME_INTERVALL']
                        # Fetch potential trading opportunities with refined query
                        rows = await conn.fetch("""
                            WITH LatestTradeData AS (
                                SELECT
                                    mint,
                                    price,
                                    marketCapSol,
                                    vTokensInBondingCurve,
                                    vSolInBondingCurve,
                                    timestamp,
                                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                                FROM trades
                                WHERE timestamp >= NOW() - ($6 || ' minutes')::interval -- Use interval from config
                            ),
                            RecentTrades AS (
                                SELECT
                                    mint,
                                    SUM(CASE WHEN tx_type = 'buy' THEN sol_amount ELSE 0 END) AS total_buys_recent,
                                    SUM(CASE WHEN tx_type = 'sell' THEN sol_amount ELSE 0 END) AS total_sells_recent,
                                    SUM(sol_amount) AS volume_recent,
                                    COUNT(*) as trade_count
                                FROM trades
                                WHERE timestamp >= NOW() - ($6 || ' minutes')::interval -- Use interval from config
                                GROUP BY mint
                            ),
                            VolatilityData AS (
                                -- Calculate volatility based on log returns for better stability
                                SELECT
                                    mint,
                                    -- Ensure SQRT argument is non-negative
                                    STDDEV(log_return) * SQRT(GREATEST(COUNT(*), 1)) AS volatility -- Scaled Volatility approximation
                                FROM (
                                    SELECT
                                        mint,
                                        price,
                                        LAG(price) OVER (PARTITION BY mint ORDER BY timestamp) AS prev_price,
                                        -- Avoid log(0) or log(negative)
                                        CASE
                                            WHEN price > 0 AND LAG(price) OVER (PARTITION BY mint ORDER BY timestamp) > 0
                                            THEN LN(price / LAG(price) OVER (PARTITION BY mint ORDER BY timestamp))
                                            ELSE NULL
                                        END AS log_return
                                    FROM trades
                                    WHERE timestamp >= NOW() - ($6 || ' minutes')::interval -- Use interval from config
                                ) sub
                                WHERE log_return IS NOT NULL
                                GROUP BY mint
                                HAVING COUNT(*) > 5 -- Require minimum data points for volatility calculation
                            )
                            SELECT
                                t.mint,
                                t.marketCapSol,
                                t.vTokensInBondingCurve,
                                t.vSolInBondingCurve,
                                COALESCE(ltd.marketCapSol, t.marketCapSol) AS latest_market_cap_sol, -- Use latest or initial
                                COALESCE(ltd.vTokensInBondingCurve, t.vTokensInBondingCurve) AS latest_v_tokens,
                                COALESCE(ltd.vSolInBondingCurve, t.vSolInBondingCurve) AS latest_v_sol,
                                COALESCE(ltd.price, 0) AS latest_price, -- Need latest price for buy execution
                                COALESCE(rt.volume_recent, 0) AS volume_in_interval,
                                COALESCE(vd.volatility, 0) AS volatility_in_interval,
                                r.tokenMeta_name AS name,
                                r.tokenMeta_symbol AS symbol,
                                r.score AS rugcheck_score,
                                t.socials_score
                            FROM tokens AS t
                            JOIN rugcheck AS r ON t.mint = r.mint
                            JOIN LatestTradeData AS ltd ON t.mint = ltd.mint AND ltd.rn = 1 -- Get the most recent trade data
                            LEFT JOIN RecentTrades AS rt ON t.mint = rt.mint
                            LEFT JOIN VolatilityData AS vd ON t.mint = vd.mint
                            WHERE
                                t.is_active = TRUE AND
                                r.score IS NOT NULL AND
                                t.socials_score IS NOT NULL AND
                                -- Filters based on thresholds
                                r.score < $4 AND                                           -- Rugcheck score BELOW threshold
                                t.socials_score < $5 AND                                   -- Socials score BELOW threshold
                                (COALESCE(rt.volume_recent, 0) * $1) >= $2 AND             -- Volume ABOVE threshold (USD)
                                (COALESCE(ltd.marketCapSol, t.marketCapSol, 0) * $1) >= $3 AND -- Market Cap ABOVE threshold (USD)
                                COALESCE(vd.volatility, 0) >= $7 AND              -- Volatility ABOVE threshold (Percentage)
                                -- Ensure token is not already actively held
                                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
                            ORDER BY rt.volume_recent DESC; -- Order by recent volume or another relevant metric
                        """, sol_price,                                  # $1
                            self.config['DEFAULT_VOLUME_THRESHOLD'],     # $2
                            self.config['DEFAULT_MARKETCAP_THRESHOLD'],  # $3
                            self.config['DEFAULT_RUGCHECK_SCORE_THRESHOLD'], # $4
                            self.config['DEFAULT_SOCIAL_SCORE_THRESHOLD'],   # $5
                            str(time_interval_minutes),                  # $6 (as string for interval)
                            self.config['MIN_VOLATILITY']                # $7
                        )

                        logger.debug(f"Found {len(rows)} potential trading opportunities.")
                        for row in rows:
                            mint = row['mint']
                            latest_price = float(row['latest_price'])
                            latest_market_cap_sol = float(row['latest_market_cap_sol'])
                            # volume = float(row['volume_in_interval']) # Not directly used after query
                            # volatility = float(row['volatility_in_interval']) # Not directly used after query
                            # rugcheck_score = row['rugcheck_score'] # Not directly used after query
                            # socials_score = row['socials_score'] # Not directly used after query

                            if latest_price <= 0: # Cannot buy if price is zero or negative
                                logger.warning(f"Skipping buy for {mint} due to invalid latest price: {latest_price}")
                                continue

                            # Simulate buy execution (uses its own transaction)
                            # Pass only necessary info
                            await self.execute_buy(mint, latest_price, latest_market_cap_sol)
                            # Add a small delay to avoid overwhelming APIs or DB if many opportunities found
                            await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(f"❌ Error fetching/processing trading opportunities: {e}", exc_info=True)
                        # Don't re-raise, allow loop to continue

        except Exception as e:
            logger.error(f"❌ Outer error in check_trading_opportunities: {e}", exc_info=True)
            # Avoid tight loop on persistent errors
            await asyncio.sleep(5)

    async def check_sell_opportunities(self):
        """Check for sell opportunities based on SL and TP rules."""
        if self.state.shutdown_event.is_set():
            return

        sol_price = await self.state.get_sol_price() # Needed for price conversions if any
        if sol_price is None or sol_price <= 0:
            logger.warning(f"⚠ Invalid SOL_PRICE ({sol_price}); skipping sell check.")
            return

        async with self.db.acquire() as conn:
            # Use a single transaction for checking and potentially selling multiple positions
            async with conn.transaction():
                try:
                    # Fetch active buy positions with new TP/SL fields
                    positions = await conn.fetch('''
                        SELECT id, mint, price AS buy_price, initial_tokens, remaining_tokens,
                               stop_loss_price, highest_price, initial_tp_price, second_tp_price, first_tp_hit
                        FROM portfolio
                        WHERE status = 'active' AND tx_type = 'buy' -- Only check original buy entries
                    ''')

                    if not positions:
                        # logger.debug("No active positions to check for selling.")
                        return # No active positions to check

                    # Fetch latest prices for all active mints in one go
                    active_mints = list(set(p['mint'] for p in positions)) # Unique mints
                    if not active_mints:
                        return

                    latest_prices_rows = await conn.fetch(f'''
                        WITH LatestTrades AS (
                            SELECT
                                mint,
                                price,
                                marketCapSol,
                                ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                            FROM trades
                            WHERE mint = ANY($1::text[])
                        )
                        SELECT mint, price, marketCapSol FROM LatestTrades WHERE rn = 1
                    ''', active_mints)

                    latest_prices = {row['mint']: {'price': float(row['price']), 'market_cap': float(row['marketcapsol'])}
                                     for row in latest_prices_rows if row['price'] is not None and float(row['price']) > 0}

                    for position in positions:
                        pos_id = position['id']
                        mint = position['mint']
                        buy_price = float(position['buy_price'])
                        initial_tokens = float(position['initial_tokens'])
                        remaining_tokens = float(position['remaining_tokens'])
                        active_stop_loss_price = float(position['stop_loss_price']) # The currently active SL
                        highest_price = float(position['highest_price'])
                        initial_tp_price = float(position['initial_tp_price'])
                        second_tp_price = float(position['second_tp_price'])
                        first_tp_hit = position['first_tp_hit'] # Boolean

                        if initial_tokens <= 0: # Should not happen for a buy entry, but safety check
                            continue

                        if mint not in latest_prices:
                            logger.warning(f"⚠ Could not find latest price for active position {mint} (ID: {pos_id}). Skipping sell check.")
                            continue

                        current_price = latest_prices[mint]['price']
                        current_market_cap = latest_prices[mint]['market_cap']

                        # --- Update highest price ---
                        if current_price > highest_price:
                            highest_price = current_price # Update local var for subsequent checks
                            await conn.execute('''
                                UPDATE portfolio SET highest_price = $1 WHERE id = $2
                            ''', current_price, pos_id)
                            # logger.debug(f"Updated highest price for {mint} to {current_price:.6f}")


                        # --- Calculate Trailing SL Price (only relevant if first TP was hit) ---
                        trailing_sl_price = 0 # Default
                        if first_tp_hit:
                            # Calculate trailing SL based on highest price since the buy
                            trailing_sl_price = highest_price * (1 - self.config['TRAILING_STOP_LOSS_PERCENT'] / 100.0)
                            # Note: The active SL is either the initial SL, breakeven (buy_price), or potentially this trailing_sl_price
                            # depending on the exact logic chosen after first TP hit.
                            # For now, we assume SL moves to buy_price after first TP, and trailing SL is checked separately.

                        # --- Check Sell Conditions ---
                        # --- Check Sell Conditions (Order Matters!) ---
                        sell_reason = None
                        sell_all = False
                        sell_partial = False
                        sell_percentage = 0.0

                        # 1. Initial Stop Loss / Breakeven Stop Loss
                        if current_price <= active_stop_loss_price:
                            sell_reason = "Stop Loss" if not first_tp_hit else "Breakeven SL"
                            sell_all = True
                            sell_percentage = 1.0
                            logger.info(f"🛑 {sell_reason} hit for {mint} (ID: {pos_id}) at price {current_price:.9f} (SL: {active_stop_loss_price:.9f})")

                        # 2. Second Take Profit (Sell Remaining)
                        elif current_price >= second_tp_price:
                             # Check if first TP was hit is implicit, as remaining_tokens would be < initial_tokens
                             # Sell remaining regardless of whether first TP was hit or not if price reaches this high
                            sell_reason = "Second TP"
                            sell_all = True
                            sell_percentage = 1.0 # Sell all remaining
                            logger.info(f"🚀 Second TP hit for {mint} (ID: {pos_id}) at price {current_price:.9f} (Threshold: {second_tp_price:.9f})")

                        # 3. First Take Profit (Partial Sell, only if not hit before)
                        elif not first_tp_hit and current_price >= initial_tp_price:
                            sell_reason = "First TP"
                            sell_partial = True
                            # Sell configured percentage of the *initial* amount
                            sell_percentage = self.config['INITIAL_TAKE_PROFIT_PERCENT'] / 100.0
                            logger.info(f"🎯 First TP hit for {mint} (ID: {pos_id}) at price {current_price:.9f} (Threshold: {initial_tp_price:.9f}). Selling {sell_percentage*100}%.")

                        # 4. Trailing Stop Loss (Only active *after* First TP is hit)
                        elif first_tp_hit and current_price <= trailing_sl_price:
                            sell_reason = "Trailing SL"
                            sell_all = True
                            sell_percentage = 1.0 # Sell all remaining
                            logger.info(f"📉 Trailing SL hit for {mint} (ID: {pos_id}) at price {current_price:.9f} (Trailing SL: {trailing_sl_price:.9f}, Highest: {highest_price:.9f})")


                        # --- Execute Sell ---
                        # Execute sell within the same transaction
                        if sell_partial:
                            try:
                                profit = await self.execute_sell(
                                    conn=conn, # Pass connection
                                    mint=mint,
                                    current_price=current_price,
                                    market_cap_sol=current_market_cap,
                                    reason=sell_reason,
                                    sell_percentage=sell_percentage, # Use calculated percentage
                                    position_id_to_update=pos_id
                                )
                                if profit is not None: # Check if sell was successful
                                    # --- Post-First TP Actions ---
                                    # Mark first TP as hit and adjust SL to breakeven (buy_price)
                                    await conn.execute('''
                                        UPDATE portfolio SET first_tp_hit = TRUE, stop_loss_price = $1 WHERE id = $2
                                    ''', buy_price, pos_id)
                                    logger.info(f"📈 Marked First TP as hit for {mint} (ID: {pos_id}) and adjusted Stop Loss to breakeven ({buy_price:.9f}).")
                            except Exception as e:
                                logger.error(f"Error executing partial sell for {mint} (ID: {pos_id}): {e}", exc_info=True)
                                # Allow transaction to potentially rollback or continue with other positions

                        elif sell_all:
                            try:
                                await self.execute_sell(
                                    conn=conn, # Pass connection
                                    mint=mint,
                                    current_price=current_price,
                                    market_cap_sol=current_market_cap,
                                    reason=sell_reason,
                                    sell_percentage=sell_percentage, # Should be 1.0 for SL/TP2/Trailing SL
                                    position_id_to_update=pos_id
                                )
                            except Exception as e:
                                logger.error(f"Error executing full sell for {mint} (ID: {pos_id}): {e}", exc_info=True)
                                # Allow transaction to potentially rollback or continue with other positions

                        # Add a small delay if a sell occurred to allow logs/state to settle? Optional.
                        if sell_partial or sell_all:
                            await asyncio.sleep(0.1)


                except Exception as e:
                    logger.error(f"❌ Error in check_sell_opportunities transaction block: {e}", exc_info=True)
                    # The transaction will be rolled back automatically due to the exception
                    raise # Re-raise to ensure rollback

    async def execute_sell(self, conn, mint: str, current_price: float, market_cap_sol: float, reason: str, sell_percentage: float, position_id_to_update: int) -> float | None:
        """
        Execute sell simulation for a specific position within an existing transaction.
        Returns the calculated profit (can be negative) or None if sell failed or was skipped.
        """
        try:
            # Fetch the specific active buy entry to update
            buy_entry = await conn.fetchrow('''
                SELECT price AS buy_price, initial_tokens, remaining_tokens, fee AS buy_fee, tip AS buy_tip
                FROM portfolio
                WHERE id = $1 AND status = 'active' AND tx_type = 'buy'
            ''', position_id_to_update)

            if not buy_entry:
                logger.warning(f"⚠ Could not find active buy entry for ID {position_id_to_update} ({mint}) to sell.")
                return None

            buy_price = float(buy_entry['buy_price'])
            initial_tokens = float(buy_entry['initial_tokens'])
            remaining_tokens = float(buy_entry['remaining_tokens'])
            buy_fee = float(buy_entry['buy_fee']) # Original buy fee for this position
            buy_tip = float(buy_entry['buy_tip']) # Original buy tip for this position

            if remaining_tokens <= 0 or initial_tokens <=0: # Safety check
                logger.warning(f"⚠ Invalid token amounts for position ID {position_id_to_update} ({mint}). Remaining: {remaining_tokens}, Initial: {initial_tokens}")
                return None # Indicate nothing was sold

            # Determine amount to sell based on the reason
            if reason == "First TP":
                # Sell a percentage of the *initial* amount for First TP
                tokens_to_sell = initial_tokens * sell_percentage
                # Safety check: ensure we don't try to sell more than what's remaining
                tokens_to_sell = min(tokens_to_sell, remaining_tokens)
            else:
                # Sell all remaining tokens for SL, Breakeven SL, Second TP, Trailing SL
                tokens_to_sell = remaining_tokens

            if tokens_to_sell <= 1e-9: # Avoid selling dust
                 logger.info(f"ℹ Sell amount for {mint} (ID: {position_id_to_update}, Reason: {reason}) is negligible ({tokens_to_sell:.12f}). Skipping sell execution.")
                 return None # Return None as nothing was effectively sold


            # Calculate financials
            gross_sol_received = tokens_to_sell * current_price
            # Pro-rate sell fees based on the fraction of the *initial* buy being sold now
            # Convert config Decimals to float for calculation with float token amounts
            sell_fee_share = float(self.config['DEFAULT_SELL_FEE']) * (tokens_to_sell / initial_tokens)
            sell_tip_share = float(self.config['DEFAULT_SELL_TIP']) * (tokens_to_sell / initial_tokens)
            net_sol_received = gross_sol_received - sell_fee_share - sell_tip_share

            # Calculate cost basis for the sold portion
            # Pro-rate original buy fees/tips based on the fraction of the *initial* buy being sold now
            # buy_fee and buy_tip are already floats from the DB fetch
            buy_fee_share = buy_fee * (tokens_to_sell / initial_tokens)
            buy_tip_share = buy_tip * (tokens_to_sell / initial_tokens)
            cost_basis = (buy_price * tokens_to_sell) + buy_fee_share + buy_tip_share

            profit = net_sol_received - cost_basis

            # Update portfolio: Reduce remaining tokens and potentially close the original buy entry
            new_remaining = remaining_tokens - tokens_to_sell
            # Use a small tolerance for floating point comparisons
            new_status = 'closed' if new_remaining < 1e-9 else 'active'

            await conn.execute('''
                UPDATE portfolio
                SET remaining_tokens = $1, status = $2
                WHERE id = $3
            ''', new_remaining, new_status, position_id_to_update)

            # Insert sell transaction record into portfolio
            await conn.execute('''
                INSERT INTO portfolio
                (mint, tx_type, price, market_cap, sol_amount, tokens, fee, tip, profit,
                 remaining_tokens, status, reason, timestamp, initial_tokens, stop_loss_price, highest_price)
                VALUES ($1, 'sell', $2, $3, $4, $5, $6, $7, $8, 0, 'closed', $9, $10, 0, 0, 0)
            ''', mint, current_price, market_cap_sol, net_sol_received, tokens_to_sell,
               sell_fee_share, sell_tip_share, profit, reason, datetime.now(timezone.utc))
            # Sell record has 0 remaining/initial/sl/highest

            logger.info(f"✅ Sold {tokens_to_sell:.6f} tokens of {mint} (ID: {position_id_to_update}) for {profit:.6f} SOL profit ({reason}). New status: {new_status}")

            # Play sounds (consider moving sound logic outside transaction if it causes delays/failures)
            # Use run_in_executor or similar if sounds block async loop
            if reason == "Stop Loss":
                asyncio.create_task(play_sell_sl_sound_async())
            # Updated sound logic for new reasons
            elif reason in ["First TP", "Second TP", "Trailing SL"]: # Play TP sound for all profit-taking/trailing scenarios
                asyncio.create_task(play_sell_tp_sound_async())
            # Note: "Breakeven SL" will play the SL sound as it's a stop-loss trigger.

            return profit

        except Exception as e:
            logger.error(f"❌ Sell execution failed for {mint} (ID: {position_id_to_update}, Reason: {reason}): {e}", exc_info=True)
            # Important: Re-raise to trigger transaction rollback within check_sell_opportunities
            raise e

    # Removed calculate_volatility as it's handled in the SQL query now
    async def execute_buy(self, mint: str, current_price: float, market_cap_sol: float):
        """Simulate buy order execution and record in portfolio."""
        if current_price <= 0:
            logger.error(f"❌ Attempted to buy {mint} with invalid price: {current_price}")
            return

        # Use a dedicated connection and transaction for each buy simulation
        async with self.db.acquire() as conn:
            async with conn.transaction():
                try:
                    # Ensure we don't buy if already active
                    existing = await conn.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy'", mint)
                    if existing:
                        # This check might be redundant if check_trading_opportunities already filters, but good safety measure
                        logger.warning(f"⚠ Attempted to buy {mint}, but it's already active in portfolio. Skipping.")
                        return

                    sol_to_spend = self.config['SOL_TO_BUY']
                    buy_fee = self.config['DEFAULT_BUY_FEE']
                    buy_tip = self.config['DEFAULT_BUY_TIP']
                    sol_for_tokens = sol_to_spend - buy_fee - buy_tip

                    if sol_for_tokens <= 0:
                        logger.error(f"❌ Not enough SOL ({sol_to_spend}) to buy tokens for {mint} after fees/tip ({buy_fee + buy_tip}).")
                        return

                    tokens_bought = sol_for_tokens / current_price
                    # Calculate initial SL and TP levels based on config percentages
                    initial_stop_loss_price = current_price * (1 - self.config['INITIAL_STOP_LOSS_PERCENT'] / 100.0)
                    initial_tp_price = current_price * (1 + self.config['INITIAL_TAKE_PROFIT_PERCENT'] / 100.0)
                    second_tp_price = current_price * (1 + self.config['SECOND_TAKE_PROFIT_PERCENT'] / 100.0)

                    # Assumes 'initial_tokens', 'initial_tp_price', 'second_tp_price', 'first_tp_hit' columns exist
                    await conn.execute("""
                        INSERT INTO portfolio
                            (mint, tx_type, price, market_cap, sol_amount, tokens,
                             fee, tip, remaining_tokens, stop_loss_price, highest_price,
                             initial_tp_price, second_tp_price, first_tp_hit,
                             status, timestamp, initial_tokens)
                        VALUES ($1, 'buy', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, FALSE, 'active', $13, $14)
                        -- The check before this insert prevents duplicate active buys.
                    """, mint, current_price, market_cap_sol, sol_to_spend,
                       tokens_bought, buy_fee, buy_tip, tokens_bought, # remaining_tokens = initial_tokens initially
                       initial_stop_loss_price, current_price, # highest_price = current_price initially
                       initial_tp_price, second_tp_price,
                       datetime.now(timezone.utc), tokens_bought) # Store initial_tokens

                    # Log only if insert happened (check affected rows?) - fetchval might be better
                    # For simulation, we assume insert worked if no exception
                    sol_price = await self.state.get_sol_price()
                    logger.info(format_buy_order_log(self.state, mint=mint, price_per_token=current_price, tokens_bought=tokens_bought, market_cap=market_cap_sol, sol_price=sol_price))
                    asyncio.create_task(play_buy_opportunity_sound()) # Run sound concurrently

                except Exception as e:
                    logger.error(f"❌ Buy execution failed for {mint}: {e}", exc_info=True)
                    # Transaction will be rolled back
