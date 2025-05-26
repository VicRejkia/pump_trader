"""
Handles trading logic including buy/sell decision making, volatility calculation,
emergency sell triggers, and portfolio management.
"""
import asyncio
import numpy as np # Keep if other parts of your TradingManager might use it
import json
from datetime import datetime, timezone, timedelta

from database_handler import DatabaseClient # Type hint
from logger import logger
from state_manager import GlobalState
from utils import (
    play_buy_opportunity_sound, play_sell_sl_sound_async, play_sell_tp_sound_async,
    format_buy_order_log, format_sell_order_log, calculate_trend_indicators 
)
from telegram_interface import send_telegram_message

class TradingManager:
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state: GlobalState):
        self.db = db_client
        self.config = config_dict # config_dict is the active config from TradingBot
        self.state = state

    async def _is_trend_reversal_confirmed(self, mint: str) -> bool:
        """
        Checks if a token that was recently stopped out shows strong signs of trend reversal.
        """
        # logger.debug(f"Performing trend reversal confirmation for {mint}...")
        
        # # 1. Fetch recent data. Let's look at the last 3 hours of data to have enough for indicators.
        # start_date = datetime.now(timezone.utc) - timedelta(hours=3)
        # end_date = datetime.now(timezone.utc)

        # # Use the existing function to get data. It returns a dictionary.
        # historical_data = await self.db.get_historical_data_for_backtesting([mint], start_date, end_date)

        # if not historical_data or mint not in historical_data:
        #     logger.warning(f"Could not fetch historical data for {mint} to check trend reversal.")
        #     return False

        # df = historical_data[mint]
        
        # # 2. Calculate indicators using our new utility function
        # df_with_indicators = calculate_trend_indicators(df, self.config)

        # if df_with_indicators.empty:
        #     logger.warning(f"Indicator calculation failed or returned no data for {mint}. Cannot confirm trend.")
        #     return False

        # # 3. Get the latest data point for our checks
        # latest = df_with_indicators.iloc[-1]
        # previous = df_with_indicators.iloc[-2] # Also get the second-to-last for crossover detection

        # # 4. Implement the two-stage confirmation logic
        
        # # --- Stage 1: Potential Bottom Triggers ---
        # rsi_triggered = latest['RSI'] > 30 and previous['RSI'] <= 30
        # bb_triggered = latest['Close'] > latest['BBL_20_2.0'] and previous['Close'] <= previous['BBL_20_2.0']

        # if not (rsi_triggered or bb_triggered):
        #     logger.debug(f"Re-buy for {mint} skipped: No bottom trigger. RSI cross: {rsi_triggered}, BB cross: {bb_triggered}.")
        #     return False
        
        # logger.info(f"✅ Bottom trigger confirmed for {mint}. RSI cross: {rsi_triggered}, BB cross: {bb_triggered}. Checking filters...")

        # # --- Stage 2: Trend and Volume Filters ---
        # trend_confirmed = latest['Close'] > latest['VWAP']
        # momentum_confirmed = latest['EMA_fast'] > latest['EMA_slow']
        
        # if not (trend_confirmed and momentum_confirmed):
        #     logger.debug(f"Re-buy for {mint} skipped: Trend/Momentum filter failed. Above VWAP: {trend_confirmed}, EMA Cross: {momentum_confirmed}.")
        #     return False
            
        # logger.info(f"✅ Trend & Momentum filters passed for {mint}. Above VWAP: {trend_confirmed}, EMA Cross: {momentum_confirmed}.")
        
        # # If we reach here, all conditions are met
        # logger.info(f"🚀 Trend Reversal Confirmed for {mint}! Proceeding with buy opportunity.")
        # return True
        pass

    async def check_trading_opportunities(self):
        """✅ Check for new trading opportunities based on configured criteria."""
        if self.state.shutdown_event.is_set():
            return

        if not self.state.is_buying_enabled:
            logger.debug("Buying is currently disabled by command. Skipping buy checks.")
            return

        try:
            sol_price = await self.state.get_sol_price()
            if sol_price is None or sol_price <= 0:
                logger.warning(f"⚠️ Invalid SOL_PRICE ({sol_price}); skipping buy check.")
                return

            rows = await self.db.find_trading_opportunities(
                sol_price=sol_price,
                volume_threshold=self.config['DEFAULT_VOLUME_THRESHOLD'],
                marketcap_threshold=self.config['DEFAULT_MARKETCAP_THRESHOLD'],
                rugcheck_threshold=self.config['DEFAULT_RUGCHECK_SCORE_THRESHOLD'],
                social_score_threshold=self.config['DEFAULT_SOCIAL_SCORE_THRESHOLD'],
                time_interval_minutes=self.config['DEFAULT_TIME_INTERVALL'],
                min_volatility=self.config['MIN_VOLATILITY']
            )

            logger.debug(f"Found {len(rows)} potential trading opportunities after initial DB filter (incl. hard cooldown).")

            for row in rows:
                mint = row['mint']
                
                proceed_to_buy = True # Assume true unless a check fails

                # --- Trend Reversal Confirmation Logic (Revised with two-pronged Stage 1) ---
                if self.config.get('USE_TREND_REVERSAL_CONFIRMATION', False):
                    apply_reversal_on_configured_reasons = self.config.get('APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
                    recency_hours = self.config.get('TREND_REVERSAL_RECENCY_HOURS', 6) 
                    rsi_neutral_level_config = self.config.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 45) # New config

                    last_sell_reason_for_check = None 
                    requires_reversal_check = False

                    async with self.db.pool.acquire() as conn:
                        last_sell_record = await conn.fetchrow(
                            """SELECT reason, timestamp FROM portfolio 
                               WHERE mint = $1 AND tx_type = 'sell' 
                               ORDER BY timestamp DESC LIMIT 1""",
                            mint
                        )
                    
                    if last_sell_record:
                        reason_from_portfolio = last_sell_record['reason']
                        timestamp_from_portfolio = last_sell_record['timestamp']
                        if timestamp_from_portfolio.tzinfo is None:
                            timestamp_from_portfolio = timestamp_from_portfolio.replace(tzinfo=timezone.utc)
                        
                        is_recent_sell = (datetime.now(timezone.utc) - timestamp_from_portfolio) < timedelta(hours=recency_hours)

                        if reason_from_portfolio and is_recent_sell:
                            for configured_reason_substring in apply_reversal_on_configured_reasons:
                                if configured_reason_substring in reason_from_portfolio:
                                    requires_reversal_check = True
                                    last_sell_reason_for_check = reason_from_portfolio
                                    break
                    
                    if requires_reversal_check:
                        logger.info(f"Token {mint} recently sold (within {recency_hours}h) due to '{last_sell_reason_for_check}'. Performing trend reversal confirmation...")
                        
                        # Fetch historical data for indicators
                        start_date_hist = datetime.now(timezone.utc) - timedelta(hours=self.config.get('INDICATOR_LOOKBACK_HOURS', 1)) # Configurable lookback
                        end_date_hist = datetime.now(timezone.utc)
                        historical_data = await self.db.get_historical_data_for_backtesting([mint], start_date_hist, end_date_hist)

                        if not historical_data or mint not in historical_data:
                            logger.warning(f"Could not fetch historical data for {mint} for trend reversal. Skipping buy for now.")
                            proceed_to_buy = False
                        
                        if proceed_to_buy:
                            df = historical_data[mint]
                            df_with_indicators = calculate_trend_indicators(df, self.config) # from utils.py

                            if df_with_indicators.empty or len(df_with_indicators) < 2:
                                logger.warning(f"Indicator calculation failed or returned insufficient data for {mint} (rows: {len(df_with_indicators)}). Skipping buy for now.")
                                proceed_to_buy = False
                            
                            if proceed_to_buy:
                                latest = df_with_indicators.iloc[-1]
                                previous = df_with_indicators.iloc[-2]

                                # STAGE 1: Potential Bottoming/Recovery Signals
                                stage1_passed = False
                                rsi_latest_val = latest.get('RSI', float('nan'))
                                rsi_previous_val = previous.get('RSI', float('nan'))
                                close_latest_val = latest.get('Close', float('nan'))
                                close_previous_val = previous.get('Close', float('nan'))
                                bb_lower_band_col = f"BBL_{self.config.get('BBANDS_PERIOD', 20)}_{self.config.get('BBANDS_STD_DEV', 2.0)}"
                                bb_lower_latest_val = latest.get(bb_lower_band_col, float('inf'))
                                bb_lower_previous_val = previous.get(bb_lower_band_col, float('inf'))

                                # Primary Trigger: Crossovers
                                rsi_just_crossed_up = rsi_latest_val > 30 and rsi_previous_val <= 30
                                bb_price_reentered = close_latest_val > bb_lower_latest_val and close_previous_val <= bb_lower_previous_val
                                
                                if rsi_just_crossed_up or bb_price_reentered:
                                    stage1_passed = True
                                    logger.info(f"Stage 1 for {mint} PASSED (Crossover): RSI_Cross={rsi_just_crossed_up}, BB_Reentry={bb_price_reentered}")
                                else:
                                    # Secondary Trigger: If crossover missed, check if RSI is showing some baseline strength
                                    if rsi_latest_val > rsi_neutral_level_config:
                                        stage1_passed = True
                                        logger.info(f"Stage 1 for {mint} PASSED (Alternative): RSI ({rsi_latest_val:.2f}) > Neutral Level ({rsi_neutral_level_config}).")
                                    else:
                                        logger.info(f"Stage 1 for {mint} FAILED: No crossover and RSI ({rsi_latest_val:.2f}) not above neutral level ({rsi_neutral_level_config}).")

                                if not stage1_passed:
                                    proceed_to_buy = False
                                else:
                                    # STAGE 2: Confirmation Filters (VWAP & EMA)
                                    trend_confirmed_vwap = close_latest_val > latest.get('VWAP', float('-inf')) # Treat missing VWAP as price not being above it
                                    momentum_confirmed_ema = latest.get('EMA_fast', float('-inf')) > latest.get('EMA_slow', float('inf'))

                                    if not (trend_confirmed_vwap and momentum_confirmed_ema):
                                        logger.info(f"Skipping re-buy for {mint}: Stage 2 (Confirmation) FAILED. VWAP: {trend_confirmed_vwap}, EMA: {momentum_confirmed_ema}.")
                                        proceed_to_buy = False
                                    else:
                                        logger.info(f"🚀 Trend Reversal Fully Confirmed for {mint} (Stage 2 Passed)! VWAP: {trend_confirmed_vwap}, EMA: {momentum_confirmed_ema}.")
                
                if not proceed_to_buy:
                    continue # Skip to the next token in the opportunity list

                # --- Original Buy Logic (if all checks passed or not applicable) ---
                latest_price = float(row['latest_price'])
                latest_market_cap_sol = float(row['latest_market_cap_sol'])

                if latest_price <= 0:
                    logger.warning(f"Skipping buy for {mint} due to invalid latest price: {latest_price}")
                    continue
                
                await self.execute_buy(mint, latest_price, latest_market_cap_sol)
                await asyncio.sleep(0.1) 

        except Exception as e:
            logger.error(f"❌ Error in check_trading_opportunities: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def check_sell_opportunities(self):
        """
        🧐 Check for sell opportunities based on SL and TP rules,
        using the centralized price determination logic.
        """
        if self.state.shutdown_event.is_set():
            return

        sol_price_usd = await self.state.get_sol_price()
        if sol_price_usd is None or sol_price_usd <= 0:
            logger.warning(f"⚠️ Invalid SOL_PRICE_USD ({sol_price_usd}); skipping sell check.")
            return

        async with self.db.pool.acquire() as conn: # Acquire connection for the whole sell check cycle
            async with conn.transaction(): # Start a transaction for this cycle
                try:
                    positions = await self.db.get_active_buy_positions(conn)
                    if not positions:
                        return

                    for position in positions:
                        pos_id = position['id']
                        mint = position['mint']

                        # Use the new centralized function to get decision price and market cap
                        price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn)
                        current_price_to_use = price_data.get('price')
                        current_market_cap_sol_for_log = price_data.get('market_cap')

                        # Ensure current_market_cap_sol_for_log is float or None for calculations
                        if isinstance(current_market_cap_sol_for_log, str):
                            try:
                                current_market_cap_sol_for_log = float(current_market_cap_sol_for_log)
                            except ValueError:
                                logger.warning(f"Could not convert market_cap_sol '{current_market_cap_sol_for_log}' to float for {mint}. Setting to None.")
                                current_market_cap_sol_for_log = None


                        # --- Start of Sell Logic (mostly same as before, but uses new price/mc sources) ---
                        if current_price_to_use is None or current_price_to_use <= 0:
                            logger.warning(f"Skipping price-based sell checks for {mint} (ID: {pos_id}) due to invalid current price: {current_price_to_use} determined by method '{self.config.get('PRICE_DETERMINATION_METHOD')}'.")
                            # Market Cap Emergency SL (can still trigger if MC is valid, even if price is not)
                            if current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                               (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                                sell_reason_mc = "Emergency SL (MCap)"
                                logger.info(f"🆘 {sell_reason_mc} for {mint} (ID: {pos_id}) due to low MCap. MCap_USD: {(current_market_cap_sol_for_log * sol_price_usd):.2f}, Threshold: {self.config['MIN_MARKETCAP_THRESHOLD']:.2f}")
                                trigger_val_mc = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd), "min_mcap_threshold_config": self.config['MIN_MARKETCAP_THRESHOLD']}
                                logger.error(f"Emergency MCap SL for {mint} (ID: {pos_id}) triggered, but price for execution is invalid ({current_price_to_use}). Sell action deferred by this logic path to prevent selling at unknown/stale price if primary price determination failed.")

                            continue # Skip further price-based checks

                        buy_price = float(position['buy_price'])
                        initial_tokens = float(position['initial_tokens'])
                        active_stop_loss_price = float(position['stop_loss_price'])
                        highest_price_since_buy = float(position['highest_price'])
                        initial_tp_price = float(position['initial_tp_price'])
                        second_tp_price = float(position['second_tp_price'])
                        first_tp_hit = position['first_tp_hit']

                        if initial_tokens <= 0: continue

                        if current_price_to_use > highest_price_since_buy:
                            highest_price_since_buy = current_price_to_use
                            await self.db.update_portfolio_highest_price(pos_id, current_price_to_use, conn)

                        trailing_sl_price = 0.0
                        if first_tp_hit: # Trailing SL is active only AFTER first TP
                            trailing_sl_price = highest_price_since_buy * (1 - self.config['TRAILING_STOP_LOSS_PERCENT'] / 100.0)

                        sell_reason = None
                        sell_all = False
                        sell_partial = False
                        sell_percentage_of_initial = 0.0
                        trigger_values_for_log = {}


                        # Order of checks: SL > Second TP > First TP > Trailing SL > MCap SL
                        if current_price_to_use <= active_stop_loss_price:
                            sell_reason = "🛑 Stop Loss" if not first_tp_hit else "🛡️ Breakeven SL"
                            sell_all = True
                            trigger_values_for_log = {"stop_loss_price_threshold": active_stop_loss_price}
                        elif current_price_to_use >= second_tp_price:
                            sell_reason = "🎯 Second TP"
                            sell_all = True
                            trigger_values_for_log = {"second_tp_price_threshold": second_tp_price}
                        elif not first_tp_hit and current_price_to_use >= initial_tp_price:
                            sell_reason = "🥇 First TP"
                            sell_partial = True
                            sell_percentage_of_initial = self.config['FIRST_SELL_PERCENT'] / 100.0
                            trigger_values_for_log = {"first_tp_price_threshold": initial_tp_price}
                        elif first_tp_hit and current_price_to_use <= trailing_sl_price: # Trailing SL checked only if first TP hit
                            sell_reason = "↘️ Trailing SL"
                            sell_all = True
                            trigger_values_for_log = {"trailing_sl_price_threshold": trailing_sl_price, "highest_price_at_trigger": highest_price_since_buy}
                        elif current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                           (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                            sell_reason = "🆘 Emergency SL (MCap)"
                            sell_all = True # MCap SL sells all
                            trigger_values_for_log = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd), "min_mcap_threshold_config": self.config['MIN_MARKETCAP_THRESHOLD']}
                        elif current_market_cap_sol_for_log is None and not sell_reason : # Log if MC is None and no other reason found
                             logger.warning(f"Cannot check Emergency SL (MCap) for {mint} (ID: {pos_id}) due to invalid market cap: {current_market_cap_sol_for_log}")


                        if sell_reason:
                            trailing_sl_price_display = f"{trailing_sl_price:.9f}" if first_tp_hit else "N/A"
                            log_message_sell_trigger = (
                                f"Trigger for {mint} (ID: {pos_id}): Reason='{sell_reason}', "
                                f"PriceToUse={current_price_to_use:.9f} (Method: {self.config.get('PRICE_DETERMINATION_METHOD')}), "
                                f"BuyPrice={buy_price:.9f}, ActiveSL={active_stop_loss_price:.9f}, "
                                f"InitialTP={initial_tp_price:.9f}, SecondTP={second_tp_price:.9f}, "
                                f"Highest={highest_price_since_buy:.9f}, TrailingSLPrice={trailing_sl_price_display}, "
                                f"FirstTPHit={first_tp_hit}, MarketCapSOL={current_market_cap_sol_for_log}"
                            )
                            logger.info(log_message_sell_trigger)

                            profit_from_sell = None
                            if sell_partial:
                                profit_from_sell = await self.execute_sell(
                                    conn=conn, mint=mint, current_price=current_price_to_use,
                                    market_cap_sol=current_market_cap_sol_for_log if current_market_cap_sol_for_log is not None else 0.0,
                                    reason=sell_reason, sell_percentage=sell_percentage_of_initial,
                                    position_id_to_update=pos_id, sell_trigger_values=trigger_values_for_log
                                )
                                if profit_from_sell is not None: # If sell was successful
                                    await self.db.mark_first_tp_hit_and_adjust_sl(pos_id, buy_price, conn) # Adjust SL to breakeven
                                    logger.info(f"📈 Marked First TP as hit for {mint} (ID: {pos_id}) and adjusted Stop Loss to breakeven ({buy_price:.9f}).")
                            elif sell_all:
                                profit_from_sell = await self.execute_sell(
                                    conn=conn, mint=mint, current_price=current_price_to_use,
                                    market_cap_sol=current_market_cap_sol_for_log if current_market_cap_sol_for_log is not None else 0.0,
                                    reason=sell_reason, sell_percentage=1.0, # Sell 100%
                                    position_id_to_update=pos_id, sell_trigger_values=trigger_values_for_log
                                )
                            # Optional: small delay after a sell execution
                            if profit_from_sell is not None:
                                await asyncio.sleep(0.1)
                        # --- End of Sell Logic ---

                except Exception as e:
                    logger.error(f"❌ Error in check_sell_opportunities transaction block: {e}", exc_info=True)

    async def execute_manual_sell(self, mint: str):
        """Executes a manual sell for all holdings of a specific token."""
        logger.info(f"Attempting manual sell for all holdings of token: {mint}")
        
        async with self.db.pool.acquire() as conn:
            # Find the active buy position for the given mint
            position = await conn.fetchrow(
                "SELECT id FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' ORDER BY timestamp DESC LIMIT 1",
                mint
            )

            if not position:
                logger.warning(f"No active buy position found for mint {mint} to execute manual sell.")
                return

            pos_id = position['id']
            
            # Get the current price and market cap
            price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn)
            current_price = price_data.get('price')
            market_cap_sol = price_data.get('market_cap')

            if current_price is None or current_price <= 0:
                logger.error(f"Cannot execute manual sell for {mint}: Invalid current price ({current_price}).")
                return

            logger.info(f"Executing manual sell for {mint} (Position ID: {pos_id}) at price {current_price:.9f}")

            async with conn.transaction():
                await self.execute_sell(
                    conn=conn,
                    mint=mint,
                    current_price=current_price,
                    market_cap_sol=market_cap_sol if market_cap_sol is not None else 0.0,
                    reason="manual_override",
                    sell_percentage=1.0,  # Sell 100%
                    position_id_to_update=pos_id,
                    sell_trigger_values={"command": "SELL_" + mint}
                )

    async def execute_sell(self, conn, mint: str, current_price: float, market_cap_sol: float, reason: str, sell_percentage: float, position_id_to_update: int, sell_trigger_values: dict = None) -> float | None:
        """
        💸 Execute sell simulation for a specific position within an existing transaction.
        Includes relevant settings in the portfolio record.
        Returns the calculated profit (can be negative) or None if sell failed or was skipped.
        """
        if sell_trigger_values is None: sell_trigger_values = {}
        try:
            buy_entry = await self.db.get_portfolio_entry_for_update(position_id_to_update, conn)
            if not buy_entry:
                logger.warning(f"⚠️ Could not find active buy entry for ID {position_id_to_update} ({mint}) to sell.")
                return None

            if current_price is None or current_price <= 0:
                if reason == "🆘 Emergency SL (MCap)":
                    current_price = float(buy_entry['buy_price']) # Fallback to buy_price for MCap SL execution
                    logger.warning(f"Emergency SL (MCap) for {mint} using buy_price {current_price} as fallback due to invalid determined sell price.")
                else: # For other sell reasons, a valid current_price is essential
                    logger.error(f"Invalid current_price ({current_price}) for sell execution of {mint} (Reason: {reason}). Aborting sell.")
                    return None


            buy_price = float(buy_entry['buy_price'])
            initial_tokens = float(buy_entry['initial_tokens'])
            remaining_tokens = float(buy_entry['remaining_tokens'])
            total_investment_sol = float(buy_entry['total_investment_sol']) # SOL spent on initial buy including fees/tip

            if remaining_tokens <= 0 or initial_tokens <= 0:
                logger.warning(f"⚠️ Invalid token amounts for position ID {position_id_to_update} ({mint}). Remaining: {remaining_tokens}, Initial: {initial_tokens}")
                return None

            tokens_to_sell: float
            if reason == "🥇 First TP":
                tokens_to_sell = initial_tokens * sell_percentage
                tokens_to_sell = min(tokens_to_sell, remaining_tokens) # Cannot sell more than remaining
            else: # SL, Second TP, Trailing SL, MCap SL - sell all *remaining* tokens
                tokens_to_sell = remaining_tokens * sell_percentage # effectively remaining_tokens * 1.0

            if tokens_to_sell <= 1e-9: # Avoid selling dust
                 logger.info(f"ℹ️ Sell amount for {mint} (ID: {position_id_to_update}, Reason: {reason}) is negligible ({tokens_to_sell:.12f}). Skipping sell execution.")
                 return None

            sol_price_usd_for_log = await self.state.get_sol_price() # For logging USD values

            gross_sol_received = tokens_to_sell * current_price
            sell_fee = float(self.config['DEFAULT_SELL_FEE'])
            sell_tip = float(self.config['DEFAULT_SELL_TIP'])
            net_sol_received = gross_sol_received - sell_fee - sell_tip

            cost_basis_of_sold_portion = total_investment_sol * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
            profit = net_sol_received - cost_basis_of_sold_portion

            new_remaining_tokens = remaining_tokens - tokens_to_sell
            new_status = 'closed' if new_remaining_tokens < 1e-9 else 'active' # Close if effectively zero tokens left

            await self.db.update_portfolio_entry_after_sell(position_id_to_update, new_remaining_tokens, new_status, conn)

            sell_settings = {
                "reason": reason,
                "sell_percentage_of_initial_request": sell_percentage * 100 if reason == "🥇 First TP" else (sell_percentage * 100.0 if reason in ["🛑 Stop Loss", "🛡️ Breakeven SL", "🎯 Second TP", "↘️ Trailing SL", "🆘 Emergency SL (MCap)", "manual_override"] else 0.0),
                "actual_tokens_sold_as_fraction_of_remaining_at_sell_time": (tokens_to_sell / remaining_tokens) if remaining_tokens > 0 else 0,
                "sell_fee_config": self.config['DEFAULT_SELL_FEE'],
                "sell_tip_config": self.config['DEFAULT_SELL_TIP'],
                "price_determination_method_used": self.config.get('PRICE_DETERMINATION_METHOD'),
                "trigger_price_at_sell": current_price,
                **sell_trigger_values # Add SL price, TP price etc. that triggered it
            }
            if market_cap_sol is not None: sell_settings["market_cap_sol_at_sell"] = market_cap_sol


            await self.db.insert_portfolio_sell_record(
                mint=mint, current_price=current_price, market_cap_sol=market_cap_sol if market_cap_sol is not None else 0.0,
                net_sol_received=net_sol_received, sol_price_usd=sol_price_usd_for_log if sol_price_usd_for_log else 0.0,
                tokens_sold=tokens_to_sell, sell_fee=sell_fee, sell_tip=sell_tip, profit=profit,
                reason=reason, timestamp=datetime.now(timezone.utc), settings=sell_settings, conn=conn
            )

            # Determine if a hard cooldown should be set
            sell_reasons_triggering_hard_cooldown = self.config.get('APPLY_TREND_REVERSAL_ON_SELL_REASONS', []) # Using the same list
            trigger_hard_cooldown = False
            for configured_reason_substring in sell_reasons_triggering_hard_cooldown:
                if configured_reason_substring in reason: # 'reason' is the sell_reason string passed to execute_sell
                    trigger_hard_cooldown = True
                    break

            if trigger_hard_cooldown:
                # Use the existing STOP_LOSS_COOLDOWN_MINUTES or a more generic config if you rename it
                cooldown_minutes = self.config.get('STOP_LOSS_COOLDOWN_MINUTES', 0) 
                if cooldown_minutes > 0:
                    # Call the simplified set_token_cooldown (assuming you've removed last_cooldown_reason from it)
                    await self.db.set_token_cooldown(mint, cooldown_minutes) 
                    logger.info(f"Hard cooldown of {cooldown_minutes} min set for {mint} due to sell reason: {reason}")


            token_name_row = await self.db.get_token_name(mint, conn)
            token_name = token_name_row['name'] if token_name_row else mint

            log_msg = format_sell_order_log(
                mint=mint, token_name=token_name,
                market_cap_sol=market_cap_sol if market_cap_sol is not None else 0.0,
                profit=profit, reason=reason, sol_price=sol_price_usd_for_log
            )
            logger.info(log_msg)

            if self.config['TELEGRAM_INTERACTION']:
                telegram_msg = format_sell_order_log(
                    mint=mint, token_name=token_name,
                    market_cap_sol=market_cap_sol if market_cap_sol is not None else 0.0,
                    profit=profit, reason=reason, sol_price=sol_price_usd_for_log, for_telegram=True
                )
                asyncio.create_task(send_telegram_message(telegram_msg))

            await self.state.update_sol_balance(net_sol_received) # Add net SOL received to balance

            if self.config['PLAY_SELL_SOUND']:
                if reason in ["🛑 Stop Loss", "🛡️ Breakeven SL", "🆘 Emergency SL (MCap)", "manual_override"]:
                    asyncio.create_task(play_sell_sl_sound_async())
                elif reason in ["🥇 First TP", "🎯 Second TP", "↘️ Trailing SL"]:
                    asyncio.create_task(play_sell_tp_sound_async())
            return profit
        except Exception as e:
            logger.error(f"❌ Sell execution failed for {mint} (ID: {position_id_to_update}, Reason: {reason}): {e}", exc_info=True)
            raise # Re-raise to ensure transaction rollback if this is part of a larger transaction

    async def execute_buy(self, mint: str, current_price: float, market_cap_sol: float):
        """🛒 Simulate buy order execution and record in portfolio."""
        if current_price <= 0:
            logger.error(f"❌ Attempted to buy {mint} with invalid price: {current_price}")
            return

        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    existing = await self.db.has_active_buy_order(mint, conn)
                    if existing:
                        logger.debug(f"⚠️ Attempted to buy {mint}, but it's already active in portfolio. Skipping.")
                        return

                    sol_price_usd_for_log = await self.state.get_sol_price()
                    sol_base_amount = float(self.config['SOL_TO_BUY'])         # e.g., 0.5 SOL
                    buy_fee = float(self.config['DEFAULT_BUY_FEE'])           # e.g., 0.01 SOL
                    buy_tip = float(self.config['DEFAULT_BUY_TIP'])           # e.g., 0.01 SOL
                    total_sol_investment = sol_base_amount + buy_fee + buy_tip # e.g., 0.5 + 0.01 + 0.01 = 0.52 SOL

                    current_balance = await self.state.get_current_sol_balance()
                    if current_balance < total_sol_investment:
                        logger.warning(f"💰 Insufficient balance ({current_balance:.4f} SOL) to execute buy for {mint} requiring {total_sol_investment:.4f} SOL.")
                        return

                    # Tokens bought calculation
                    # Example: current_price = 0.0001 SOL/token
                    # tokens_bought = 0.5 SOL / 0.0001 SOL/token = 5000 tokens
                    tokens_bought = sol_base_amount / current_price

                    # Initial Stop Loss Price Calculation
                    # Example: current_price = 0.0001, INITIAL_STOP_LOSS_PERCENT = 40.0
                    # initial_stop_loss_price = 0.0001 * (1 - 40.0 / 100.0)
                    #                         = 0.0001 * (1 - 0.4)
                    #                         = 0.0001 * 0.6 = 0.00006
                    initial_stop_loss_price = current_price * (1 - float(self.config['INITIAL_STOP_LOSS_PERCENT']) / 100.0)


                    # First Take Profit (TP1) Price Calculation (Net Income Approach)
                    # Goal: The SOL received from selling FIRST_SELL_PERCENT of initial tokens at TP1 price
                    #       should cover the pro-rata cost of those tokens PLUS the desired PROFIT_MARGIN on that pro-rata cost,
                    #       PLUS the fees for this TP1 sell transaction.
                    #
                    # Example:
                    #   SOL_TO_BUY = 0.5
                    #   DEFAULT_BUY_FEE = 0.01, DEFAULT_BUY_TIP = 0.01
                    #   total_sol_investment (cost_of_all_tokens) = 0.5 + 0.01 + 0.01 = 0.52 SOL
                    #   tokens_bought = 5000 (from above example, assuming current_price was 0.0001)
                    #
                    #   FIRST_SELL_PERCENT = 35.0 (so 0.35 as fraction)
                    #   tokens_to_sell_tp1 = 5000 * 0.35 = 1750 tokens
                    #
                    #   Pro-rata cost of tokens being sold at TP1:
                    #   This is the portion of the total_sol_investment that corresponds to the tokens_to_sell_tp1.
                    #   cost_of_tp1_tokens_sold = total_sol_investment * (tokens_to_sell_tp1 / tokens_bought)
                    #                           = total_sol_investment * sell_percent_tp1_fraction
                    #                           = 0.52 * 0.35 = 0.182 SOL
                    #
                    #   FIRST_SELL_PROFIT_MARGIN = 70.0 (so 0.70 as fraction)
                    #   Desired profit ON THESE TP1 TOKENS = cost_of_tp1_tokens_sold * FIRST_SELL_PROFIT_MARGIN
                    #                                      = 0.182 * 0.70 = 0.1274 SOL
                    #
                    #   DEFAULT_SELL_FEE (for TP1) = 0.01, DEFAULT_SELL_TIP (for TP1) = 0.01
                    #   fees_for_tp1_sell = 0.01 + 0.01 = 0.02 SOL
                    #
                    #   Total SOL that needs to be received from TP1 sale (Gross SOL from sale):
                    #   This is what the sale of tokens_to_sell_tp1 must yield to cover their cost, desired profit, and the TP1 sell fees.
                    #   gross_sol_needed_from_tp1_sale = cost_of_tp1_tokens_sold + desired_profit_on_tp1_tokens + fees_for_tp1_sell
                    #                                  = 0.182 + 0.1274 + 0.02 = 0.3294 SOL
                    #
                    #   TP1 Price = gross_sol_needed_from_tp1_sale / tokens_to_sell_tp1
                    #             = 0.3294 SOL / 1750 tokens = 0.000188228... SOL/token
                    #
                    #   Verification:
                    #   If price hits 0.000188228..., and we sell 1750 tokens:
                    #   Gross SOL received = 1750 * 0.000188228... = 0.3294 SOL
                    #   Net SOL after TP1 sell fees = 0.3294 - 0.02 (fees_for_tp1_sell) = 0.3094 SOL
                    #   Profit from this portion = Net SOL received from TP1 sale - Cost of this portion
                    #                            = 0.3094 - 0.182 = 0.1274 SOL
                    #   Profit margin check = Profit from this portion / Cost of this portion
                    #                       = 0.1274 / 0.182 = 0.70 (70%), which matches the configured FIRST_SELL_PROFIT_MARGIN.

                    sell_fee_tp1 = float(self.config['DEFAULT_SELL_FEE'])
                    sell_tip_tp1 = float(self.config['DEFAULT_SELL_TIP'])
                    fees_for_tp1_sell = sell_fee_tp1 + sell_tip_tp1

                    profit_margin_tp1_fraction = float(self.config['FIRST_SELL_PROFIT_MARGIN']) / 100.0
                    sell_percent_tp1_fraction = float(self.config['FIRST_SELL_PERCENT']) / 100.0

                    tokens_to_sell_tp1 = tokens_bought * sell_percent_tp1_fraction
                    if tokens_to_sell_tp1 <= 1e-9: # Avoid division by zero if FIRST_SELL_PERCENT is ~0
                         logger.error(f"❌ Cannot calculate TP1 price for {mint}: Tokens to sell at TP1 ({tokens_to_sell_tp1}) is negligible. Check FIRST_SELL_PERCENT config.")
                         return # Or handle differently, e.g., by not setting TP1 or setting it very high

                    cost_of_tp1_tokens_sold = total_sol_investment * sell_percent_tp1_fraction
                    desired_profit_on_tp1_tokens = cost_of_tp1_tokens_sold * profit_margin_tp1_fraction
                    gross_sol_needed_from_tp1_sale = cost_of_tp1_tokens_sold + desired_profit_on_tp1_tokens + fees_for_tp1_sell

                    initial_tp_price = gross_sol_needed_from_tp1_sale / tokens_to_sell_tp1

                    # Second Take Profit Price Calculation
                    # Example: current_price = 0.0001, SECOND_TAKE_PROFIT_PERCENT = 150.0
                    # second_tp_price = 0.0001 * (1 + 150.0 / 100.0)
                    #                 = 0.0001 * (1 + 1.5)
                    #                 = 0.0001 * 2.5 = 0.00025
                    second_tp_price = current_price * (1 + float(self.config['SECOND_TAKE_PROFIT_PERCENT']) / 100.0)


                    buy_settings = {
                        "volume_threshold_usd_config": self.config['DEFAULT_VOLUME_THRESHOLD'],
                        "marketcap_threshold_usd_config": self.config['DEFAULT_MARKETCAP_THRESHOLD'],
                        "rugcheck_score_threshold_config": self.config['DEFAULT_RUGCHECK_SCORE_THRESHOLD'],
                        "social_score_threshold_config": self.config['DEFAULT_SOCIAL_SCORE_THRESHOLD'],
                        "sol_to_buy_config": self.config['SOL_TO_BUY'], "buy_fee_config": self.config['DEFAULT_BUY_FEE'],
                        "buy_tip_config": self.config['DEFAULT_BUY_TIP'],
                        "initial_stop_loss_percent_config": self.config['INITIAL_STOP_LOSS_PERCENT'],
                        "first_sell_percent_config": self.config['FIRST_SELL_PERCENT'],
                        "first_sell_profit_margin_config": self.config['FIRST_SELL_PROFIT_MARGIN'],
                        "second_take_profit_percent_config": self.config['SECOND_TAKE_PROFIT_PERCENT'],
                        "trailing_stop_loss_percent_config": self.config['TRAILING_STOP_LOSS_PERCENT'],
                        "calculated_initial_sl_price": initial_stop_loss_price,
                        "calculated_initial_tp_price": initial_tp_price,
                        "calculated_second_tp_price": second_tp_price,
                        "price_determination_method_at_buy_opportunity": self.config.get('PRICE_DETERMINATION_METHOD')
                    }

                    await self.db.insert_portfolio_buy_record(
                        mint=mint, current_price=current_price, market_cap_sol=market_cap_sol,
                        sol_base_amount=sol_base_amount, sol_price_usd=sol_price_usd_for_log if sol_price_usd_for_log else 0.0,
                        total_sol_investment=total_sol_investment, tokens_bought=tokens_bought,
                        buy_fee=buy_fee, buy_tip=buy_tip,
                        initial_stop_loss_price=initial_stop_loss_price,
                        initial_tp_price=initial_tp_price, second_tp_price=second_tp_price,
                        timestamp=datetime.now(timezone.utc), settings=buy_settings, conn=conn
                    )

                    token_name_row = await self.db.get_token_name(mint, conn)
                    token_name = token_name_row['name'] if token_name_row else mint
                    log_msg = format_buy_order_log(
                        self.state, name=token_name, mint=mint, price_per_token=current_price,
                        tokens_bought=tokens_bought, market_cap=market_cap_sol,
                        sol_price=sol_price_usd_for_log, total_investment=total_sol_investment
                    )
                    logger.info(log_msg)

                    if self.config['TELEGRAM_INTERACTION']:
                        telegram_msg  = format_buy_order_log(
                            self.state, name=token_name, mint=mint, price_per_token=current_price,
                            tokens_bought=tokens_bought, market_cap=market_cap_sol,
                            sol_price=sol_price_usd_for_log, total_investment=total_sol_investment, for_telegram=True
                        )
                        asyncio.create_task(send_telegram_message(telegram_msg))

                    await self.state.update_sol_balance(-total_sol_investment)

                    if self.config['PLAY_BUY_SOUND']:
                        asyncio.create_task(play_buy_opportunity_sound())
                except Exception as e:
                    logger.error(f"❌ Buy execution failed for {mint}: {e}", exc_info=True)