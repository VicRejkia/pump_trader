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
# Import DatabaseClient type hint
from database_handler import DatabaseClient
from logger import logger
from state_manager import GlobalState # Import GlobalState to update balance
from utils import (
    play_buy_opportunity_sound, play_sell_sl_sound_async, play_sell_tp_sound_async,
    format_buy_order_log, format_sell_order_log # Import the new sell log formatter
)
from telegram_interface import send_telegram_message # Import Telegram message function

class TradingManager:
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state: GlobalState):
        self.db = db_client # Expecting a DatabaseClient instance
        self.config = config_dict
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

            # No need for explicit connection management here, handled by DatabaseClient methods
            try:
                time_interval_minutes = self.config['DEFAULT_TIME_INTERVALL']
                # Fetch potential trading opportunities using the new DatabaseClient method
                rows = await self.db.find_trading_opportunities(
                    sol_price=sol_price,
                    volume_threshold=self.config['DEFAULT_VOLUME_THRESHOLD'],
                    marketcap_threshold=self.config['DEFAULT_MARKETCAP_THRESHOLD'],
                    rugcheck_threshold=self.config['DEFAULT_RUGCHECK_SCORE_THRESHOLD'],
                    social_score_threshold=self.config['DEFAULT_SOCIAL_SCORE_THRESHOLD'],
                    time_interval_minutes=time_interval_minutes,
                    min_volatility=self.config['MIN_VOLATILITY']
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
        """Check for sell opportunities based on SL and TP rules, using configurable price determination."""
        if self.state.shutdown_event.is_set():
            return

        sol_price_usd = await self.state.get_sol_price()  # Current SOL price in USD
        if sol_price_usd is None or sol_price_usd <= 0:
            logger.warning(f"⚠ Invalid SOL_PRICE_USD ({sol_price_usd}); skipping sell check.")
            return

        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    positions = await self.db.get_active_buy_positions(conn)
                    if not positions:
                        return

                    active_mints = list(set(p['mint'] for p in positions))
                    if not active_mints:
                        return

                    prices_to_use = {}

                    for mint_address in active_mints:
                        price_for_sell_decision = None
                        # market_cap_from_latest will store the latest market_cap if valid (positive)
                        market_cap_from_latest_valid = None

                        latest_trade_data_map = await self.db.get_latest_prices([mint_address], conn)
                        if latest_trade_data_map and mint_address in latest_trade_data_map:
                            latest_data_for_mint = latest_trade_data_map[mint_address]
                            
                            # Get market_cap; it can be None if get_latest_prices returned it as such (e.g., not positive)
                            retrieved_mc = latest_data_for_mint.get('market_cap')
                            if retrieved_mc is not None and float(retrieved_mc) > 0:
                                market_cap_from_latest_valid = float(retrieved_mc)
                            # else: market_cap_from_latest_valid remains None

                            if self.config.get('PRICE_DETERMINATION_METHOD', 'LATEST') == 'LATEST':
                                # Get price; it can be None if get_latest_prices returned it as such (e.g., not positive)
                                price_for_sell_decision = latest_data_for_mint.get('price')
                        
                        price_determination_method = self.config.get('PRICE_DETERMINATION_METHOD')
                        if price_determination_method == "VWAP":
                            price_for_sell_decision = await self.db.get_vwap_price(
                                mint_address,
                                self.config.get('PRICE_AVG_WINDOW_MINUTES', 10),
                                conn
                            )
                        elif price_determination_method == "TWAP":
                            price_for_sell_decision = await self.db.get_twap_price(
                                mint_address,
                                self.config.get('PRICE_AVG_WINDOW_MINUTES', 10),
                                self.config.get('TWAP_SUB_INTERVAL_SECONDS', 60),
                                conn
                            )

                        # Ensure price_for_sell_decision is valid before adding to prices_to_use
                        if price_for_sell_decision is not None and float(price_for_sell_decision) > 0:
                            prices_to_use[mint_address] = {
                                'price': float(price_for_sell_decision),
                                # market_cap_from_latest_valid can be None here if latest MC wasn't positive
                                'market_cap': market_cap_from_latest_valid
                            }
                        else:
                            # If price is invalid, still store market_cap if it's valid, otherwise store None for MC too.
                            # This ensures the mint is in prices_to_use if we have at least a market_cap for logging.
                            # However, sell checks requiring price will skip this position later.
                            prices_to_use[mint_address] = {
                                'price': None, # Explicitly None if price is invalid
                                'market_cap': market_cap_from_latest_valid
                            }
                            logger.warning(f"Could not determine a valid positive price for {mint_address} using method '{price_determination_method}'. Price determined: {price_for_sell_decision}. Sell checks requiring price will be skipped.")


                    for position in positions:
                        pos_id = position['id']
                        mint = position['mint']

                        if mint not in prices_to_use:
                            logger.warning(f"⚠ No price/market_cap data resolved for active position {mint} (ID: {pos_id}). Skipping sell check.")
                            continue
                        
                        position_data = prices_to_use[mint]
                        current_price_to_use = position_data.get('price') # Can be None if price determination failed
                        current_market_cap_sol_for_log = position_data.get('market_cap') # Can be None if latest MC wasn't positive

                        # If current_price_to_use is None or not positive, we cannot perform price-based SL/TP checks.
                        if current_price_to_use is None or current_price_to_use <= 0:
                            logger.warning(f"Skipping price-based sell checks for {mint} (ID: {pos_id}) due to invalid current price: {current_price_to_use}.")
                            # However, an MCap based SL might still be possible if current_market_cap_sol_for_log is valid
                            if current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                            (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                                sell_reason = "Emergency SL (MCap)"
                                sell_all = True
                                logger.info(f"🆘 Emergency SL (MCap) for {mint} (ID: {pos_id}) due to low MCap, despite invalid price for other checks. MCap_USD: {(current_market_cap_sol_for_log * sol_price_usd):.2f}, Threshold: {self.config['MIN_MARKETCAP_THRESHOLD']:.2f}")
                                # Proceed to execute_sell for MCap SL
                                trigger_values = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd), "min_mcap_threshold_config": self.config['MIN_MARKETCAP_THRESHOLD']}
                                # We need a price for execute_sell. If current_price_to_use is invalid, what should be used?
                                # This is a tricky case. Selling at an "unknown" or "stale" price is risky.
                                # For now, let's assume if MCAP SL hits, we try to sell at buy_price as a last resort if current price is bad, or simply log and not execute.
                                # For simplicity of this response, let's log and skip actual execution if price is bad.
                                # In a real scenario, you might want a different fallback price for MCap SL.
                                logger.error(f"Emergency MCap SL for {mint} (ID: {pos_id}) triggered, but current_price_to_use is invalid ({current_price_to_use}). Sell not executed by this logic path to prevent selling at unknown price.")
                                # To actually sell, you'd need to decide what price to use in execute_sell.
                                # Example (if you decide to sell at buy_price as fallback for MCap SL):
                                # profit_from_sell = await self.execute_sell(conn=conn, mint=mint, current_price=float(position['buy_price']), market_cap_sol=current_market_cap_sol_for_log, reason=sell_reason, sell_percentage=1.0, position_id_to_update=pos_id, sell_trigger_values=trigger_values)
                            continue # Skip other price-based checks if price is invalid


                        buy_price = float(position['buy_price'])
                        initial_tokens = float(position['initial_tokens'])
                        remaining_tokens = float(position['remaining_tokens'])
                        active_stop_loss_price = float(position['stop_loss_price'])
                        highest_price_since_buy = float(position['highest_price'])
                        initial_tp_price = float(position['initial_tp_price'])
                        second_tp_price = float(position['second_tp_price'])
                        first_tp_hit = position['first_tp_hit']

                        if initial_tokens <= 0:
                            continue

                        if current_price_to_use > highest_price_since_buy:
                            highest_price_since_buy = current_price_to_use
                            await self.db.update_portfolio_highest_price(pos_id, current_price_to_use, conn)

                        trailing_sl_price = 0.0
                        if first_tp_hit:
                            trailing_sl_price = highest_price_since_buy * (1 - self.config['TRAILING_STOP_LOSS_PERCENT'] / 100.0)

                        sell_reason = None
                        sell_all = False
                        sell_partial = False
                        sell_percentage_of_initial = 0.0

                        if current_price_to_use <= active_stop_loss_price:
                            sell_reason = "Stop Loss" if not first_tp_hit else "Breakeven SL"
                            sell_all = True
                            logger.info(f"🛑 {sell_reason} hit for {mint} (ID: {pos_id}) at price {current_price_to_use:.9f} (SL: {active_stop_loss_price:.9f})")
                        elif current_price_to_use >= second_tp_price:
                            sell_reason = "Second TP"
                            sell_all = True
                            logger.info(f"🚀 Second TP hit for {mint} (ID: {pos_id}) at price {current_price_to_use:.9f} (Threshold: {second_tp_price:.9f})")
                        elif not first_tp_hit and current_price_to_use >= initial_tp_price:
                            sell_reason = "First TP"
                            sell_partial = True
                            sell_percentage_of_initial = self.config['FIRST_SELL_PERCENT'] / 100.0
                            logger.info(f"🎯 First TP hit for {mint} (ID: {pos_id}) at price {current_price_to_use:.9f} (Threshold: {initial_tp_price:.9f}). Selling {sell_percentage_of_initial*100}%.")
                        elif first_tp_hit and current_price_to_use <= trailing_sl_price:
                            sell_reason = "Trailing SL"
                            sell_all = True
                            logger.info(f"📉 Trailing SL hit for {mint} (ID: {pos_id}) at price {current_price_to_use:.9f} (Trailing SL: {trailing_sl_price:.9f}, Highest: {highest_price_since_buy:.9f})")
                        elif current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                            (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                            sell_reason = "Emergency SL (MCap)"
                            sell_all = True
                            logger.info(f"🆘 Emergency SL (MCap) for {mint} (ID: {pos_id}). Current MCap_USD: {(current_market_cap_sol_for_log * sol_price_usd):.2f}, Threshold: {self.config['MIN_MARKETCAP_THRESHOLD']:.2f}")
                        elif current_market_cap_sol_for_log is None or current_market_cap_sol_for_log <= 0:
                            # This case is logged if no other price-based SL/TP was hit before it
                            if not sell_reason: # Only log if no other sell reason was found yet
                                logger.warning(f"Cannot check Emergency SL (MCap) for {mint} (ID: {pos_id}) due to invalid or zero market cap from latest trade: {current_market_cap_sol_for_log}")
                        
                        if sell_reason:
                            trigger_values = {}
                            profit_from_sell = None

                            if sell_partial:
                                trigger_values = {"first_tp_price_threshold": initial_tp_price}
                                profit_from_sell = await self.execute_sell(
                                    conn=conn, mint=mint, current_price=current_price_to_use,
                                    market_cap_sol=current_market_cap_sol_for_log if current_market_cap_sol_for_log is not None else 0.0, # Pass 0 if None for logging
                                    reason=sell_reason, sell_percentage=sell_percentage_of_initial,
                                    position_id_to_update=pos_id, sell_trigger_values=trigger_values
                                )
                                if profit_from_sell is not None:
                                    await self.db.mark_first_tp_hit_and_adjust_sl(pos_id, buy_price, conn)
                                    logger.info(f"📈 Marked First TP as hit for {mint} (ID: {pos_id}) and adjusted Stop Loss to breakeven ({buy_price:.9f}).")
                            elif sell_all:
                                if sell_reason == "Stop Loss" or sell_reason == "Breakeven SL":
                                    trigger_values = {"stop_loss_price_threshold": active_stop_loss_price}
                                elif sell_reason == "Second TP":
                                    trigger_values = {"second_tp_price_threshold": second_tp_price}
                                elif sell_reason == "Trailing SL":
                                    trigger_values = {"trailing_sl_price_threshold": trailing_sl_price, "highest_price_at_trigger": highest_price_since_buy}
                                elif sell_reason == "Emergency SL (MCap)":
                                    trigger_values = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd) if current_market_cap_sol_for_log else 0.0,
                                                    "min_mcap_threshold_config": self.config['MIN_MARKETCAP_THRESHOLD']}
                                
                                profit_from_sell = await self.execute_sell(
                                    conn=conn, mint=mint, current_price=current_price_to_use,
                                    market_cap_sol=current_market_cap_sol_for_log if current_market_cap_sol_for_log is not None else 0.0, # Pass 0 if None for logging
                                    reason=sell_reason, sell_percentage=1.0,
                                    position_id_to_update=pos_id, sell_trigger_values=trigger_values
                                )
                            if profit_from_sell is not None:
                                await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"❌ Error in check_sell_opportunities transaction block: {e}", exc_info=True)
                    raise

    async def execute_sell(self, conn, mint: str, current_price: float, market_cap_sol: float, reason: str, sell_percentage: float, position_id_to_update: int, sell_trigger_values: dict = None) -> float | None:
        """
        Execute sell simulation for a specific position within an existing transaction.
        Includes relevant settings in the portfolio record.
        Returns the calculated profit (can be negative) or None if sell failed or was skipped.
        """
        if sell_trigger_values is None:
            sell_trigger_values = {} # Initialize if not provided
        try:
            # Fetch the specific active buy entry using the new DatabaseClient method
            buy_entry = await self.db.get_portfolio_entry_for_update(position_id_to_update, conn)

            if not buy_entry:
                logger.warning(f"⚠ Could not find active buy entry for ID {position_id_to_update} ({mint}) to sell.")
                return None

            buy_price = float(buy_entry['buy_price'])
            initial_tokens = float(buy_entry['initial_tokens'])
            remaining_tokens = float(buy_entry['remaining_tokens'])
            # buy_fee = float(buy_entry['buy_fee']) # Original buy fee - not needed for new cost basis calc
            # buy_tip = float(buy_entry['buy_tip']) # Original buy tip - not needed for new cost basis calc
            total_investment_sol = float(buy_entry['total_investment_sol']) # Total SOL spent on the initial buy

            if remaining_tokens <= 0 or initial_tokens <=0: # Safety check
                logger.warning(f"⚠ Invalid token amounts for position ID {position_id_to_update} ({mint}). Remaining: {remaining_tokens}, Initial: {initial_tokens}")
                return None # Indicate nothing was sold

            # Determine amount to sell based on the reason    
            # Formula: tokens_to_sell = initial_tokens * sell_percentage (First TP)
            # Example: 1,600,000 * 0.75 = 1,200,000 tokens
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

            # Get SOL price for logging
            sol_price = await self.state.get_sol_price()

            # -- Calculate financials --
            # --- Gross SOL Calculation ---
            # Formula: gross_sol_received = tokens_to_sell * current_price
            # Example: 1,200,000 * 0.000000162 = 0.1944 SOL
            gross_sol_received = tokens_to_sell * current_price
           
            # Use the full configured sell fee and tip for every sell transaction
            # Convert config Decimals to float if they aren't already
            sell_fee = float(self.config['DEFAULT_SELL_FEE'])
            sell_tip = float(self.config['DEFAULT_SELL_TIP'])
            
            # --- Net SOL Calculation ---
            # Formula: net_sol_received = gross_sol_received - sell_fee - sell_tip
            # Example: 0.1944 - 0.001 - 0.001 = 0.1924 SOL
            net_sol_received = gross_sol_received - sell_fee - sell_tip

            # Calculate cost basis for the sold portion based on the total initial investment
            # Pro-rate the total initial investment based on the fraction of *initial* tokens being sold now
            if initial_tokens <= 0: # Avoid division by zero
                 logger.error(f"Cannot calculate cost basis for {mint} (ID: {position_id_to_update}) due to zero initial tokens.")
                 return None # Or handle error appropriately
            
            # --- Cost Basis Calculation ---
            # Formula: cost_basis = total_investment_sol * (tokens_to_sell / initial_tokens)
            # Example: (0.2 SOL) * (1,200,000 / 1,600,000) = 0.2 * 0.75 = 0.15 SOL
            cost_basis = total_investment_sol * (tokens_to_sell / initial_tokens)

            # --- Profit Calculation ---
            # Formula: profit = net_sol_received - cost_basis
            # Example: 0.1924 - 0.15 = 0.0424 SOL profit
            profit = net_sol_received - cost_basis

            # Update portfolio: Reduce remaining tokens and potentially close the original buy entry
            new_remaining = remaining_tokens - tokens_to_sell
            # Use a small tolerance for floating point comparisons
            new_status = 'closed' if new_remaining < 1e-9 else 'active'

            # Update portfolio entry using the new DatabaseClient method
            await self.db.update_portfolio_entry_after_sell(position_id_to_update, new_remaining, new_status, conn)

            # --- Prepare Settings for Sell Record ---
            sell_settings = {
                "reason": reason,
                "sell_percentage": sell_percentage * 100, # Store as percentage
                "sell_fee_config": self.config['DEFAULT_SELL_FEE'],
                "sell_tip_config": self.config['DEFAULT_SELL_TIP'],
                "trigger_price": current_price, # Price at the time of sell trigger
                **sell_trigger_values # Add specific trigger values (SL price, TP price, etc.)
            }
            if reason == "Emergency SL":
                 sell_settings["min_market_cap_config_usd"] = self.config['MIN_MARKET_CAP']
                 # sell_trigger_values should contain 'current_market_cap_usd'

            # Insert sell transaction record using the new DatabaseClient method, including settings
            await self.db.insert_portfolio_sell_record(
                mint=mint, current_price=current_price, market_cap_sol=market_cap_sol,
                net_sol_received=net_sol_received, sol_price_usd=sol_price, tokens_sold=tokens_to_sell,
                sell_fee=sell_fee, sell_tip=sell_tip, profit=profit, reason=reason,
                timestamp=datetime.now(timezone.utc), settings=sell_settings, conn=conn
            )
            # Fetch token name for logging
            # Fetch token name using the new DatabaseClient method
            token_name_row = await self.db.get_token_name(mint, conn)
            token_name = token_name_row['name'] if token_name_row else mint # Fallback to mint if name not found


            # Use the new formatted log message
            message = format_sell_order_log(
                mint=mint,
                token_name=token_name,
                market_cap_sol=market_cap_sol,
                profit=profit,
                reason=reason,
                sol_price=sol_price
            )
            logger.info(message)
            asyncio.create_task(send_telegram_message(message))
            # Removed old log message here

            # Update global SOL balance using the instance passed to the manager
            await self.state.update_sol_balance(net_sol_received) # Add received SOL

            # Play sounds (consider moving sound logic outside transaction if it causes delays/failures)
            # Use run_in_executor or similar if sounds block async loop
            if reason == "Stop Loss" and self.config['PLAY_SELL_SOUND']:
                asyncio.create_task(play_sell_sl_sound_async())
            # Updated sound logic for new reasons
            elif reason in ["First TP", "Second TP", "Trailing SL"] and self.config['PLAY_SELL_SOUND']: # Play TP sound for all profit-taking/trailing scenarios
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
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Ensure we don't buy if already active
                    existing = await self.db.has_active_buy_order(mint, conn)
                    if existing:
                        # This check might be redundant if check_trading_opportunities already filters, but good safety measure
                        logger.warning(f"⚠ Attempted to buy {mint}, but it's already active in portfolio. Skipping.")
                        return
                    sol_price = await self.state.get_sol_price() # Fetch SOL price for logging
                    sol_base_amount = self.config['SOL_TO_BUY'] # Base amount intended for token purchase
                    buy_fee = self.config['DEFAULT_BUY_FEE']
                    buy_tip = self.config['DEFAULT_BUY_TIP']
                    total_sol_investment = sol_base_amount + buy_fee + buy_tip # Total SOL deducted from balance
                    sol_for_tokens = sol_base_amount # Use the base amount to calculate tokens bought

                    if sol_for_tokens <= 0: # Check if the base amount is valid
                        logger.error(f"❌ Configured SOL_TO_BUY ({sol_base_amount}) is zero or negative for {mint}.")
                        return
                    # Check if balance is sufficient for the total investment
                    current_balance = await self.state.get_current_sol_balance() # Assuming this method exists
                    if current_balance < total_sol_investment:
                        logger.warning(f"💰 Insufficient balance ({current_balance:.4f} SOL) to execute buy for {mint} requiring {total_sol_investment:.4f} SOL.")
                        return

                    tokens_bought = sol_for_tokens / current_price

                    # --- Initial Stop Loss Calculation ---
                    # Calculate initial SL based on config percentage
                    # Formula: initial_stop_loss_price = buy_price * (1 - INITIAL_STOP_LOSS_PERCENT/100)
                    # Example: 0.000000125 * 0.5 = 0.0000000625
                    initial_stop_loss_price = current_price * (1 - self.config['INITIAL_STOP_LOSS_PERCENT'] / 100.0)

                    
                    # --- Calculate First TP Price based on covering costs and margin (Net Income approach) ---
                    # Ensure config values are floats for calculation
                    sell_fee_tp1 = float(self.config['DEFAULT_SELL_FEE'])
                    sell_tip_tp1 = float(self.config['DEFAULT_SELL_TIP'])
                    profit_margin_tp1 = float(self.config['FIRST_SELL_PROFIT_MARGIN']) / 100.0
                    sell_percent_tp1 = float(self.config['FIRST_SELL_PERCENT']) / 100.0

                    # --- First TP Price Calculation (Net Income Approach) ---
                    # Calculate the total cost base including initial investment and the TP1 sell costs
                    # Formula: total_cost_base_tp1 = sol_to_buy + buy_fee + buy_tip + sell_fee + sell_tip
                    # Example: total_cost_base = 0.2 + 0.001 + 0.001 + 0.001 + 0.001 = 0.204
                    total_cost_base_tp1 = total_sol_investment + sell_fee_tp1 + sell_tip_tp1

                    # Calculate the target NET SOL return (cost base + profit margin on cost base)
                    # Formula: target_net_sol_return_tp1 = total_cost_base_tp1 * (1 + profit_margin)
                    # Example: target_net_return = 0.204 * 1.3 = 0.2652
                    target_net_sol_return_tp1 = total_cost_base_tp1 * (1 + profit_margin_tp1)

                    # Calculate the target GROSS SOL needed from the sale to achieve the target NET return
                    # Note: This is the total gross SOL needed from the sale to achieve the target NET return
                    # This includes the sell fee and tip for the first TP sale
                    # Formula: target_gross_sol_return_tp1 = target_net_return + sell_fee + sell_tip
                    # Example: target_gross_sol_return = 0.2652 + 0.001 + 0.001 = 0.2672
                    target_gross_sol_return_tp1 = target_net_sol_return_tp1 + sell_fee_tp1 + sell_tip_tp1

                    # Calculate the number of tokens to sell at TP1 based on the target GROSS return and the percentage to sell
                    # Example: tokens_to_sell_tp1 = 1,600,000 * 0.75 = 1,200,000
                    tokens_to_sell_tp1 = tokens_bought * sell_percent_tp1

                    if tokens_to_sell_tp1 <= 1e-9: # Avoid division by zero
                         logger.error(f"❌ Cannot calculate TP1 price for {mint}: Tokens to sell at TP1 is negligible ({tokens_to_sell_tp1:.12f}). Check FIRST_SELL_PERCENT config.")
                         return # Skip buy

                    # Calculate the required price per token to achieve the target GROSS return by selling the specified percentage of tokens
                    # Formula: initial_tp_price = target_gross_return / (tokens_bought * sell_percent)
                    # Example: initial_tp_price = 0.2672 / 1,200,000 ≈ 0.0000002227
                    initial_tp_price = target_gross_sol_return_tp1 / tokens_to_sell_tp1
                    
                    # --- Second TP Price Calculation ---
                    # Formula: second_tp_price = buy_price * (1 + SECOND_TAKE_PROFIT_PERCENT/100)
                    # Example: 0.000000125 * 4 = 0.0000005
                    second_tp_price = current_price * (1 + self.config['SECOND_TAKE_PROFIT_PERCENT'] / 100.0)

                    # --- Prepare Settings for Buy Record ---
                    # Gather settings relevant to the buy decision and initial position setup
                    buy_settings = {
                        # Buy Trigger Conditions (from check_trading_opportunities)
                        "volume_threshold_usd_config": self.config['DEFAULT_VOLUME_THRESHOLD'],
                        "marketcap_threshold_usd_config": self.config['DEFAULT_MARKETCAP_THRESHOLD'],
                        "rugcheck_score_threshold_config": self.config['DEFAULT_RUGCHECK_SCORE_THRESHOLD'],
                        "social_score_threshold_config": self.config['DEFAULT_SOCIAL_SCORE_THRESHOLD'],
                        "time_interval_minutes_config": self.config['DEFAULT_TIME_INTERVALL'],
                        "min_volatility_percent_config": self.config['MIN_VOLATILITY'],
                        # Buy Execution Settings
                        "sol_to_buy_config": self.config['SOL_TO_BUY'],
                        "buy_fee_config": self.config['DEFAULT_BUY_FEE'],
                        "buy_tip_config": self.config['DEFAULT_BUY_TIP'],
                        # Initial Sell Strategy Settings
                        "initial_stop_loss_percent_config": self.config['INITIAL_STOP_LOSS_PERCENT'],
                        "first_sell_percent_config": self.config['FIRST_SELL_PERCENT'],
                        "first_sell_profit_margin_config": self.config['FIRST_SELL_PROFIT_MARGIN'],
                        "second_take_profit_percent_config": self.config['SECOND_TAKE_PROFIT_PERCENT'],
                        "trailing_stop_loss_percent_config": self.config['TRAILING_STOP_LOSS_PERCENT'], # Store for reference
                        # Calculated Values at Buy Time
                        "calculated_initial_sl_price": initial_stop_loss_price,
                        "calculated_initial_tp_price": initial_tp_price,
                        "calculated_second_tp_price": second_tp_price,
                    }

                    # Insert buy record using the new DatabaseClient method, including settings
                    await self.db.insert_portfolio_buy_record(
                        mint=mint, current_price=current_price, market_cap_sol=market_cap_sol,
                        sol_base_amount=sol_base_amount, sol_price_usd=sol_price, total_sol_investment=total_sol_investment,
                        tokens_bought=tokens_bought, buy_fee=buy_fee, buy_tip=buy_tip,
                        initial_stop_loss_price=initial_stop_loss_price,
                        initial_tp_price=initial_tp_price, second_tp_price=second_tp_price,
                        timestamp=datetime.now(timezone.utc), settings=buy_settings, conn=conn
                    )

                    # Log only if insert happened (check affected rows?) - fetchval might be better
                    # For simulation, we assume insert worked if no exception
                    token_name_row = await self.db.get_token_name(mint, conn) # Fetch token name for logging
                    token_name = token_name_row['name'] if token_name_row else mint
                    # Update log format if needed to show total_sol_investment
                    message = format_buy_order_log(
                        self.state,
                        name=token_name,
                        mint=mint,
                        price_per_token=current_price,
                        tokens_bought=tokens_bought,
                        market_cap=market_cap_sol,
                        sol_price=sol_price,
                        total_investment=total_sol_investment # Pass total investment to log formatter if it accepts it
                    )

                    logger.info(message)
                    asyncio.create_task(send_telegram_message(message))

                    # Update global SOL balance using the instance passed to the manager
                    await self.state.update_sol_balance(-total_sol_investment) # Subtract TOTAL investment

                    if self.config['PLAY_BUY_SOUND']:
                        asyncio.create_task(play_buy_opportunity_sound()) # Run sound concurrently

                except Exception as e:
                    logger.error(f"❌ Buy execution failed for {mint}: {e}", exc_info=True)
                    # Transaction will be rolled back
