"""
Handles trading logic including buy/sell decision making,
emergency sell triggers, and portfolio management, supporting multiple trading modes.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json # Added for settings

# Assuming these are in your project structure
from database_handler import DatabaseClient # Type hint
from logger import logger
from state_manager import GlobalState
from utils import (
    play_buy_opportunity_sound, play_sell_sl_sound_async, play_sell_tp_sound_async,
    format_buy_order_log, format_sell_order_log, calculate_trend_indicators
)
from live_trader_pumpportal import execute_live_pumpportal_trade # Import the live trading function
from telegram_interface import send_telegram_message # If you use it

class TradingManager:
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state: GlobalState):
        self.db = db_client
        self.config = config_dict # This is the active config from TradingBot
        self.state = state

    async def _is_trend_reversal_confirmed(self, mint: str) -> bool:
        """
        Checks if a token that was recently stopped out shows signs of trend reversal.
        """
        if not self.config.get('USE_TREND_REVERSAL_CONFIRMATION', False):
            return True # If disabled, always "confirm"

        logger.debug(f"Performing trend reversal confirmation for {mint}...")
        
        apply_reversal_on_configured_reasons = self.config.get('_APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
        recency_hours = self.config.get('TREND_REVERSAL_RECENCY_HOURS', 6)
        rsi_neutral_level_config = self.config.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 45)

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
        
        if not requires_reversal_check:
            logger.debug(f"Trend reversal check not required for {mint} based on last sell reason or recency.")
            return True # No specific sell reason that needs reversal confirmation

        logger.info(f"Token {mint} recently sold (within {recency_hours}h) due to '{last_sell_reason_for_check}'. Performing trend reversal confirmation...")
        
        start_date_hist = datetime.now(timezone.utc) - timedelta(hours=self.config.get('INDICATOR_LOOKBACK_HOURS', 1))
        end_date_hist = datetime.now(timezone.utc)
        historical_data = await self.db.get_historical_data_for_backtesting([mint], start_date_hist, end_date_hist)

        if not historical_data or mint not in historical_data:
            logger.warning(f"Could not fetch historical data for {mint} for trend reversal. Skipping buy for now.")
            return False
        
        df = historical_data[mint]
        df_with_indicators = calculate_trend_indicators(df, self.config) 

        if df_with_indicators.empty or len(df_with_indicators) < self.config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30): 
            logger.warning(f"Indicator calculation failed or returned insufficient data for {mint} (rows: {len(df_with_indicators)}). Cannot confirm trend.")
            return False
        
        latest = df_with_indicators.iloc[-1]
        previous = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else latest 

        # STAGE 1: Potential Bottoming/Recovery Signals
        stage1_passed = False
        rsi_latest_val = latest.get('RSI', float('nan'))
        rsi_previous_val = previous.get('RSI', float('nan'))
        close_latest_val = latest.get('Close', float('nan'))
        close_previous_val = previous.get('Close', float('nan'))
        bb_lower_band_col = f"BBL_{self.config.get('BBANDS_PERIOD', 20)}_{self.config.get('BBANDS_STD_DEV', 2.0)}"
        bb_lower_latest_val = latest.get(bb_lower_band_col, float('inf'))
        bb_lower_previous_val = previous.get(bb_lower_band_col, float('inf'))

        rsi_just_crossed_up = rsi_latest_val > 30 and rsi_previous_val <= 30
        bb_price_reentered = close_latest_val > bb_lower_latest_val and close_previous_val <= bb_lower_previous_val
        
        if rsi_just_crossed_up or bb_price_reentered:
            stage1_passed = True
            logger.info(f"Stage 1 for {mint} PASSED (Crossover): RSI_Cross={rsi_just_crossed_up}, BB_Reentry={bb_price_reentered}")
        else:
            if rsi_latest_val > rsi_neutral_level_config:
                stage1_passed = True
                logger.info(f"Stage 1 for {mint} PASSED (Alternative): RSI ({rsi_latest_val:.2f}) > Neutral Level ({rsi_neutral_level_config}).")
            else:
                logger.info(f"Stage 1 for {mint} FAILED: No crossover and RSI ({rsi_latest_val:.2f}) not above neutral level ({rsi_neutral_level_config}).")

        if not stage1_passed:
            return False
        
        # STAGE 2: Confirmation Filters (VWAP & EMA)
        trend_confirmed_vwap = close_latest_val > latest.get('VWAP', float('-inf'))
        momentum_confirmed_ema = latest.get('EMA_fast', float('-inf')) > latest.get('EMA_slow', float('inf'))

        if not (trend_confirmed_vwap and momentum_confirmed_ema):
            logger.info(f"Re-buy for {mint} skipped: Stage 2 (Confirmation) FAILED. VWAP: {trend_confirmed_vwap}, EMA: {momentum_confirmed_ema}.")
            return False
        
        logger.info(f"🚀 Trend Reversal Fully Confirmed for {mint} (Stage 2 Passed)! VWAP: {trend_confirmed_vwap}, EMA: {momentum_confirmed_ema}.")
        return True

    async def check_trading_opportunities(self):
        """✅ Check for new trading opportunities based on configured criteria."""
        if self.state.shutdown_event.is_set():
            return

        if not self.state.is_buying_enabled: # Global bot state flag
            logger.debug("Buying is currently disabled by command. Skipping buy checks.")
            return

        try:
            sol_price_usd = await self.state.get_sol_price()
            if sol_price_usd is None or sol_price_usd <= 0:
                logger.warning(f"⚠️ Invalid SOL_PRICE_USD ({sol_price_usd}); skipping buy check.")
                return

            rows = await self.db.find_trading_opportunities(
                sol_price=sol_price_usd,
                volume_threshold=self.config['DEFAULT_VOLUME_THRESHOLD'],
                marketcap_threshold=self.config['DEFAULT_MARKETCAP_THRESHOLD'],
                rugcheck_threshold=self.config['DEFAULT_RUGCHECK_SCORE_THRESHOLD'],
                social_score_threshold=self.config['DEFAULT_SOCIAL_SCORE_THRESHOLD'],
                time_interval_minutes=self.config['DEFAULT_TIME_INTERVALL'],
                min_volatility=self.config['MIN_VOLATILITY']
            )

            logger.debug(f"Found {len(rows)} potential trading opportunities after initial DB filter.")

            for row in rows:
                mint = row['mint']
                opportunity_price = float(row['latest_price'])
                opportunity_market_cap_sol = float(row['latest_market_cap_sol'])

                if opportunity_price <= 0:
                    logger.warning(f"Skipping buy for {mint} due to invalid opportunity price: {opportunity_price}")
                    continue

                if self.config.get('USE_TREND_REVERSAL_CONFIRMATION', False):
                    if not await self._is_trend_reversal_confirmed(mint):
                        logger.debug(f"Trend reversal not confirmed for {mint}. Skipping buy opportunity.")
                        continue
                
                await self.execute_buy(mint, opportunity_price, opportunity_market_cap_sol)
                await asyncio.sleep(0.1) 

        except Exception as e:
            logger.error(f"❌ Error in check_trading_opportunities: {e}", exc_info=True)
            await asyncio.sleep(5) 

    async def execute_buy(self, mint: str, trigger_price: float, market_cap_sol_at_trigger: float):
        """🛒 Dispatches buy execution based on TRADING_MODE."""
        trading_mode = self.config['TRADING_MODE'].lower()

        if trigger_price <= 0:
            logger.error(f"❌ [{trading_mode.upper()}] Attempted to buy {mint} with invalid trigger price: {trigger_price}")
            return

        async with self.db.pool.acquire() as conn:
            async with conn.transaction(): 
                already_active = await self.db.has_active_buy_order(mint, conn)
                if already_active:
                    logger.debug(f"⚠️ [{trading_mode.upper()}] Attempted to buy {mint}, but it's already active in portfolio. Skipping.")
                    return

                sol_price_usd = await self.state.get_sol_price()
                if sol_price_usd is None or sol_price_usd <=0: 
                    logger.warning(f"⚠️ [{trading_mode.upper()}] Invalid SOL_PRICE_USD ({sol_price_usd}) for buy of {mint}.")

                sol_to_spend_on_tokens = float(self.config['SOL_TO_BUY']) 
                sim_buy_fee = float(self.config['DEFAULT_BUY_FEE'])
                sim_buy_tip = float(self.config['DEFAULT_BUY_TIP'])
                sim_total_investment = sol_to_spend_on_tokens + sim_buy_fee + sim_buy_tip
                
                current_sol_balance = await self.state.get_current_sol_balance()

                if trading_mode == "simulate":
                    if current_sol_balance < sim_total_investment:
                        logger.warning(f"💰 [SIMULATE] Insufficient balance ({current_sol_balance:.4f} SOL) for buy of {mint} requiring ~{sim_total_investment:.4f} SOL.")
                        return
                elif trading_mode in ["paper_trading", "live"]:
                    priority_fee_for_api = float(self.config['DEFAULT_BUY_TIP']) 
                    required_for_api_call = sol_to_spend_on_tokens + priority_fee_for_api
                    if current_sol_balance < required_for_api_call:
                        logger.warning(f"💰 [{trading_mode.upper()}] Insufficient balance ({current_sol_balance:.4f} SOL) for buy of {mint} requiring {sol_to_spend_on_tokens:.4f} SOL (base) + {priority_fee_for_api:.6f} SOL (priority).")
                        return
        
        if trading_mode == "simulate":
            logger.info(f"[SIMULATE MODE] Executing simulated buy for {mint} at {trigger_price:.9f} SOL")
            async with self.db.pool.acquire() as conn_sim: 
                async with conn_sim.transaction():
                    try:
                        tokens_bought_calculated = sol_to_spend_on_tokens / trigger_price
                        initial_sl_price_calc = trigger_price * (1 - float(self.config['INITIAL_STOP_LOSS_PERCENT']) / 100.0)
                        
                        sim_sell_fee_tp1 = float(self.config['DEFAULT_SELL_FEE'])
                        sim_sell_tip_tp1 = float(self.config['DEFAULT_SELL_TIP'])
                        sim_fees_for_tp1_sell = sim_sell_fee_tp1 + sim_sell_tip_tp1
                        sim_profit_margin_tp1_frac = float(self.config['FIRST_SELL_PROFIT_MARGIN']) / 100.0
                        sim_sell_percent_tp1_frac = float(self.config['FIRST_SELL_PERCENT']) / 100.0
                        
                        sim_tokens_to_sell_tp1 = tokens_bought_calculated * sim_sell_percent_tp1_frac
                        initial_tp1_price_calc = float('inf') 
                        if sim_tokens_to_sell_tp1 > 1e-9:
                            sim_cost_of_tp1_tokens = sim_total_investment * sim_sell_percent_tp1_frac
                            sim_desired_profit_tp1 = sim_cost_of_tp1_tokens * sim_profit_margin_tp1_frac
                            sim_gross_sol_needed_tp1 = sim_cost_of_tp1_tokens + sim_desired_profit_tp1 + sim_fees_for_tp1_sell
                            initial_tp1_price_calc = sim_gross_sol_needed_tp1 / sim_tokens_to_sell_tp1
                        else:
                            logger.warning(f"[SIMULATE] Tokens to sell at TP1 for {mint} is negligible. TP1 price set to infinity.")

                        second_tp_price_calc = trigger_price * (1 + float(self.config['SECOND_TAKE_PROFIT_PERCENT']) / 100.0)
                        
                        sim_buy_settings = {
                            "mode": "simulate", "simulated_price": trigger_price,
                            "sol_to_buy_config": self.config['SOL_TO_BUY'],
                            "initial_stop_loss_percent_config": self.config['INITIAL_STOP_LOSS_PERCENT'],
                            "first_sell_percent_config": self.config['FIRST_SELL_PERCENT'],
                            "first_sell_profit_margin_config": self.config['FIRST_SELL_PROFIT_MARGIN'],
                            "second_take_profit_percent_config": self.config['SECOND_TAKE_PROFIT_PERCENT'],
                            "trailing_stop_loss_percent_config": self.config['TRAILING_STOP_LOSS_PERCENT'],
                            "calculated_initial_sl_price": initial_sl_price_calc,
                            "calculated_initial_tp_price": initial_tp1_price_calc,
                            "calculated_second_tp_price": second_tp_price_calc,
                             "price_determination_method_at_buy_opportunity": self.config.get('PRICE_DETERMINATION_METHOD')
                        }
                        await self.db.insert_portfolio_buy_record(
                            mint=mint, current_price=trigger_price, market_cap_sol=market_cap_sol_at_trigger,
                            sol_base_amount=sol_to_spend_on_tokens, sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                            total_sol_investment=sim_total_investment, tokens_bought=tokens_bought_calculated,
                            buy_fee=sim_buy_fee, buy_tip=sim_buy_tip,
                            initial_stop_loss_price=initial_sl_price_calc,
                            initial_tp_price=initial_tp1_price_calc, second_tp_price=second_tp_price_calc,
                            timestamp=datetime.now(timezone.utc), settings=sim_buy_settings, conn=conn_sim
                        )
                        await self.state.update_sol_balance(-sim_total_investment)
                        
                        token_name_row = await self.db.get_token_name(mint, conn_sim)
                        token_name = token_name_row['name'] if token_name_row else mint
                        log_msg = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=trigger_price, tokens_bought=tokens_bought_calculated, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sim_total_investment)
                        logger.info(log_msg)
                        if self.config.get('PLAY_BUY_SOUND'): asyncio.create_task(play_buy_opportunity_sound())
                        if self.config.get('TELEGRAM_INTERACTION'):
                            telegram_msg  = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=trigger_price, tokens_bought=tokens_bought_calculated, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sim_total_investment, for_telegram=True)
                            asyncio.create_task(send_telegram_message(telegram_msg))
                    except Exception as e_sim:
                        logger.error(f"[SIMULATE MODE] Buy DB operation failed for {mint}: {e_sim}", exc_info=True)

        elif trading_mode in ["paper_trading", "live"]:
            api_amount_str = f"{sol_to_spend_on_tokens:.9f}" 
            api_priority_fee = float(self.config['DEFAULT_BUY_TIP']) 
            api_slippage = int(self.config.get('DEFAULT_SLIPPAGE_PERCENT', 25))
            api_pool = self.config.get('DEFAULT_BUY_POOL', "auto")

            logger.info(f"[{trading_mode.upper()} MODE] Initiating buy for {mint} with {api_amount_str} SOL (Priority: {api_priority_fee} SOL) via PumpPortal API.")

            trade_result = await execute_live_pumpportal_trade(
                trigger_price=trigger_price, action="buy", mint_address=mint,
                amount_str=api_amount_str, denominated_in_sol=True,
                slippage_percent=api_slippage, priority_fee_sol=api_priority_fee, pool=api_pool
            )

            if trade_result and trade_result.get("success"):
                signature = trade_result.get("signature", "N/A")
                executed_price = trade_result.get("executed_price", trigger_price) 
                tokens_bought_actual = trade_result.get("quantity_exchanged", 0.0) 

                if tokens_bought_actual <= 0 or executed_price <= 0:
                    logger.error(f"[{trading_mode.upper()} MODE] Trade for {mint} reported success but returned invalid executed price/quantity. Sig: {signature}")
                    return

                logger.info(f"[{trading_mode.upper()} MODE] Buy for {mint} successful. Sig: {signature}, Executed Price (approx): {executed_price:.9f}, Tokens (approx): {tokens_bought_actual:.4f}")
                
                async with self.db.pool.acquire() as conn_live: 
                    async with conn_live.transaction():
                        total_sol_outflow_for_pnl = sol_to_spend_on_tokens + api_priority_fee 

                        initial_sl_price_live = executed_price * (1 - float(self.config['INITIAL_STOP_LOSS_PERCENT']) / 100.0)
                        
                        live_sell_fee_tp1 = float(self.config.get('DEFAULT_SELL_FEE_LIVE', self.config['DEFAULT_SELL_FEE']))
                        live_sell_tip_tp1 = float(self.config.get('DEFAULT_SELL_TIP_LIVE', self.config['DEFAULT_SELL_TIP'])) 
                        live_fees_for_tp1_sell = live_sell_fee_tp1 + live_sell_tip_tp1
                        live_profit_margin_tp1_frac = float(self.config['FIRST_SELL_PROFIT_MARGIN']) / 100.0
                        live_sell_percent_tp1_frac = float(self.config['FIRST_SELL_PERCENT']) / 100.0
                        
                        live_cost_of_all_tokens = sol_to_spend_on_tokens

                        live_tokens_to_sell_tp1 = tokens_bought_actual * live_sell_percent_tp1_frac
                        initial_tp1_price_live = float('inf')
                        if live_tokens_to_sell_tp1 > 1e-9:
                            live_cost_of_tp1_tokens = live_cost_of_all_tokens * live_sell_percent_tp1_frac
                            live_desired_profit_tp1 = live_cost_of_tp1_tokens * live_profit_margin_tp1_frac
                            live_gross_sol_needed_tp1 = live_cost_of_tp1_tokens + live_desired_profit_tp1 + live_fees_for_tp1_sell
                            initial_tp1_price_live = live_gross_sol_needed_tp1 / live_tokens_to_sell_tp1
                        else:
                            logger.warning(f"[{trading_mode.upper()}] Tokens to sell at TP1 for {mint} is negligible. TP1 price set to infinity.")

                        second_tp_price_live = executed_price * (1 + float(self.config['SECOND_TAKE_PROFIT_PERCENT']) / 100.0)

                        live_buy_settings = {
                            "mode": trading_mode, "signature": signature,
                            "api_executed_price": executed_price, "api_tokens_bought": tokens_bought_actual,
                            "api_priority_fee_sent": api_priority_fee, "api_slippage_sent": api_slippage,
                            "sol_to_buy_config": self.config['SOL_TO_BUY'],
                            "initial_stop_loss_percent_config": self.config['INITIAL_STOP_LOSS_PERCENT'],
                            "first_sell_percent_config": self.config['FIRST_SELL_PERCENT'],
                            "first_sell_profit_margin_config": self.config['FIRST_SELL_PROFIT_MARGIN'],
                            "second_take_profit_percent_config": self.config['SECOND_TAKE_PROFIT_PERCENT'],
                            "trailing_stop_loss_percent_config": self.config['TRAILING_STOP_LOSS_PERCENT'],
                             "calculated_initial_sl_price": initial_sl_price_live,
                            "calculated_initial_tp_price": initial_tp1_price_live,
                            "calculated_second_tp_price": second_tp_price_live,
                            "price_determination_method_at_buy_opportunity": self.config.get('PRICE_DETERMINATION_METHOD')
                        }
                        await self.db.insert_portfolio_buy_record(
                            mint=mint, current_price=executed_price, market_cap_sol=market_cap_sol_at_trigger,
                            sol_base_amount=sol_to_spend_on_tokens, sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                            total_investment_sol=total_sol_outflow_for_pnl, 
                            tokens_bought=tokens_bought_actual,
                            buy_fee=0, buy_tip=api_priority_fee, 
                            initial_stop_loss_price=initial_sl_price_live,
                            initial_tp_price=initial_tp1_price_live, second_tp_price=second_tp_price_live,
                            timestamp=datetime.now(timezone.utc), settings=live_buy_settings, conn=conn_live
                        )
                        await self.state.update_sol_balance(-total_sol_outflow_for_pnl)
                        
                        token_name_row = await self.db.get_token_name(mint, conn_live)
                        token_name = token_name_row['name'] if token_name_row else mint
                        log_msg = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=executed_price, tokens_bought=tokens_bought_actual, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sol_to_spend_on_tokens)
                        logger.info(f"[{trading_mode.upper()}] {log_msg}")
                        if self.config.get('PLAY_BUY_SOUND'): asyncio.create_task(play_buy_opportunity_sound())
                        if self.config.get('TELEGRAM_INTERACTION'):
                            telegram_msg  = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=executed_price, tokens_bought=tokens_bought_actual, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sol_to_spend_on_tokens, for_telegram=True)
                            telegram_msg += f"\nMode: {trading_mode.upper()}\nSignature: {signature}"
                            asyncio.create_task(send_telegram_message(telegram_msg))
            else:
                logger.error(f"[{trading_mode.upper()} MODE] Buy failed for {mint}. API Error: {trade_result.get('error', 'Unknown') if trade_result else 'No API result'}")
        else:
            logger.error(f"Unknown TRADING_MODE: '{trading_mode}' in execute_buy for {mint}.")

    async def execute_sell(self, conn, mint: str, trigger_price: float, market_cap_sol_at_trigger: float, reason: str, sell_percentage: float, position_id_to_update: int, sell_trigger_values: dict = None):
        """💸 Dispatches sell execution based on TRADING_MODE. `conn` is for the initial portfolio fetch and simulate mode DB writes."""
        trading_mode = self.config['TRADING_MODE'].lower()
        if sell_trigger_values is None: sell_trigger_values = {}
        
        sol_price_usd = await self.state.get_sol_price() 

        try:
            buy_entry = await self.db.get_portfolio_entry_for_update(position_id_to_update, conn)
            if not buy_entry:
                logger.warning(f"⚠️ [{trading_mode.upper()}] Could not find active buy entry for ID {position_id_to_update} ({mint}) to sell.")
                return None

            remaining_tokens_portfolio = float(buy_entry['remaining_tokens'])
            initial_tokens_portfolio = float(buy_entry['initial_tokens'])
            total_investment_sol_at_buy_portfolio = float(buy_entry['total_investment_sol']) 

            if remaining_tokens_portfolio <= 1e-9: 
                logger.info(f"ℹ️ [{trading_mode.upper()}] No remaining tokens for pos ID {position_id_to_update} ({mint}). Skipping sell.")
                return None

            tokens_to_sell_on_trigger: float
            if reason == "🥇 First TP": 
                tokens_to_sell_on_trigger = initial_tokens_portfolio * sell_percentage
                tokens_to_sell_on_trigger = min(tokens_to_sell_on_trigger, remaining_tokens_portfolio)
            else: 
                tokens_to_sell_on_trigger = remaining_tokens_portfolio * sell_percentage

            if tokens_to_sell_on_trigger <= 1e-9:
                logger.info(f"ℹ️ [{trading_mode.upper()}] Sell amount for {mint} (Reason: {reason}) is negligible ({tokens_to_sell_on_trigger:.12f}). Skipping.")
                return None

            if trading_mode == "simulate":
                logger.info(f"[SIMULATE MODE] Executing simulated sell for {tokens_to_sell_on_trigger:.4f} of {mint} at {trigger_price:.9f} (Reason: {reason})")
                
                sim_gross_sol_received = tokens_to_sell_on_trigger * trigger_price
                sim_sell_fee = float(self.config['DEFAULT_SELL_FEE'])
                sim_sell_tip = float(self.config['DEFAULT_SELL_TIP'])
                sim_net_sol_received = sim_gross_sol_received - sim_sell_fee - sim_sell_tip

                sim_cost_basis_sold_portion = total_investment_sol_at_buy_portfolio * (tokens_to_sell_on_trigger / initial_tokens_portfolio) if initial_tokens_portfolio > 0 else 0
                sim_profit = sim_net_sol_received - sim_cost_basis_sold_portion

                sim_new_remaining_tokens = remaining_tokens_portfolio - tokens_to_sell_on_trigger
                sim_new_status = 'closed' if sim_new_remaining_tokens < 1e-9 else 'active'

                await self.db.update_portfolio_entry_after_sell(position_id_to_update, sim_new_remaining_tokens, sim_new_status, conn)
                sim_sell_settings = {
                    "mode": "simulate", "reason": reason, **sell_trigger_values,
                    "sell_percentage_of_initial_request": sell_percentage * 100 if reason == "🥇 First TP" else (sell_percentage * 100.0 if reason in ["🛑 Stop Loss", "🛡️ Breakeven SL", "🎯 Second TP", "↘️ Trailing SL", "🆘 Emergency SL (MCap)", "manual_override"] else 0.0),
                    "actual_tokens_sold_as_fraction_of_remaining_at_sell_time": (tokens_to_sell_on_trigger / remaining_tokens_portfolio) if remaining_tokens_portfolio > 0 else 0,
                    "sell_fee_config": self.config['DEFAULT_SELL_FEE'],
                    "sell_tip_config": self.config['DEFAULT_SELL_TIP'],
                    "price_determination_method_used": self.config.get('PRICE_DETERMINATION_METHOD'),
                    "trigger_price_at_sell": trigger_price
                }
                if market_cap_sol_at_trigger is not None: sim_sell_settings["market_cap_sol_at_sell"] = market_cap_sol_at_trigger

                await self.db.insert_portfolio_sell_record(
                    mint=mint, current_price=trigger_price, market_cap_sol=market_cap_sol_at_trigger,
                    net_sol_received=sim_net_sol_received, sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                    tokens_sold=tokens_to_sell_on_trigger, sell_fee=sim_sell_fee, sell_tip=sim_sell_tip, profit=sim_profit,
                    reason=reason, timestamp=datetime.now(timezone.utc), settings=sim_sell_settings, conn=conn
                )
                await self.state.update_sol_balance(sim_net_sol_received)
                
                token_name_row = await self.db.get_token_name(mint, conn)
                token_name = token_name_row['name'] if token_name_row else mint
                log_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=sim_profit, reason=reason, sol_price=sol_price_usd)
                logger.info(log_msg)
                if self.config.get('PLAY_SELL_SOUND'):
                    if reason in ["🛑 Stop Loss", "🛡️ Breakeven SL", "🆘 Emergency SL (MCap)", "manual_override"]: asyncio.create_task(play_sell_sl_sound_async())
                    elif reason in ["🥇 First TP", "🎯 Second TP", "↘️ Trailing SL"]: asyncio.create_task(play_sell_tp_sound_async())
                if self.config.get('TELEGRAM_INTERACTION'):
                    telegram_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=sim_profit, reason=reason, sol_price=sol_price_usd, for_telegram=True)
                    asyncio.create_task(send_telegram_message(telegram_msg))
                
                sell_reasons_triggering_hard_cooldown = self.config.get('_APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
                if any(configured_reason in reason for configured_reason in sell_reasons_triggering_hard_cooldown):
                    cooldown_minutes = self.config.get('STOP_LOSS_COOLDOWN_MINUTES', 0)
                    if cooldown_minutes > 0:
                        await self.db.set_token_cooldown(mint, cooldown_minutes) 
                return sim_profit

            elif trading_mode in ["paper_trading", "live"]:
                api_amount_tokens_str = f"{tokens_to_sell_on_trigger:.9f}" 
                api_priority_fee = float(self.config['DEFAULT_SELL_TIP']) 
                api_slippage = int(self.config.get('DEFAULT_SLIPPAGE_PERCENT', 25))
                api_pool = self.config.get('DEFAULT_SELL_POOL', "auto") 

                logger.info(f"[{trading_mode.upper()} MODE] Initiating sell of {api_amount_tokens_str} {mint} (Reason: {reason}, Priority: {api_priority_fee} SOL) via PumpPortal API.")

                trade_result = await execute_live_pumpportal_trade(
                    trigger_price=trigger_price, action="sell", mint_address=mint,
                    amount_str=api_amount_tokens_str, denominated_in_sol=False, 
                    slippage_percent=api_slippage, priority_fee_sol=api_priority_fee, pool=api_pool
                )

                if trade_result and trade_result.get("success"):
                    signature = trade_result.get("signature", "N/A")
                    executed_price_live = trade_result.get("executed_price", trigger_price)
                    sol_received_from_api = trade_result.get("quantity_exchanged", 0.0)

                    if sol_received_from_api <= 0 and executed_price_live > 0:
                        sol_received_from_api = tokens_to_sell_on_trigger * executed_price_live
                    
                    logger.info(f"[{trading_mode.upper()} MODE] Sell for {mint} successful. Sig: {signature}, Executed Price (approx): {executed_price_live:.9f}, SOL Received (approx gross): {sol_received_from_api:.9f}")

                    async with self.db.pool.acquire() as conn_live_sell:
                        async with conn_live_sell.transaction():
                            cost_basis_sold_portion_live = total_investment_sol_at_buy_portfolio * (tokens_to_sell_on_trigger / initial_tokens_portfolio) if initial_tokens_portfolio > 0 else 0
                            profit_live = sol_received_from_api - cost_basis_sold_portion_live

                            new_remaining_tokens_live = remaining_tokens_portfolio - tokens_to_sell_on_trigger
                            new_status_live = 'closed' if new_remaining_tokens_live < 1e-9 else 'active'

                            await self.db.update_portfolio_entry_after_sell(position_id_to_update, new_remaining_tokens_live, new_status_live, conn_live_sell)
                            
                            live_sell_settings = {
                                "mode": trading_mode, "signature": signature, "reason": reason,
                                "api_executed_price": executed_price_live, "api_sol_received": sol_received_from_api,
                                "api_priority_fee_sent": api_priority_fee, "api_slippage_sent": api_slippage,
                                **sell_trigger_values,
                                "sell_percentage_of_initial_request": sell_percentage * 100 if reason == "🥇 First TP" else (sell_percentage * 100.0 if reason in ["🛑 Stop Loss", "🛡️ Breakeven SL", "🎯 Second TP", "↘️ Trailing SL", "🆘 Emergency SL (MCap)", "manual_override"] else 0.0),
                                "actual_tokens_sold_as_fraction_of_remaining_at_sell_time": (tokens_to_sell_on_trigger / remaining_tokens_portfolio) if remaining_tokens_portfolio > 0 else 0,
                                "sell_fee_config": self.config['DEFAULT_SELL_FEE'], # For reference
                                "sell_tip_config": self.config['DEFAULT_SELL_TIP'], # For reference
                                "price_determination_method_used": self.config.get('PRICE_DETERMINATION_METHOD'),
                                "trigger_price_at_sell": trigger_price
                            }
                            if market_cap_sol_at_trigger is not None: live_sell_settings["market_cap_sol_at_sell"] = market_cap_sol_at_trigger

                            await self.db.insert_portfolio_sell_record(
                                mint=mint, current_price=executed_price_live, market_cap_sol=market_cap_sol_at_trigger,
                                net_sol_received=sol_received_from_api, 
                                sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                                tokens_sold=tokens_to_sell_on_trigger,
                                sell_fee=0, sell_tip=api_priority_fee, 
                                profit=profit_live,
                                reason=reason, timestamp=datetime.now(timezone.utc), settings=live_sell_settings, conn=conn_live_sell
                            )
                            await self.state.update_sol_balance(sol_received_from_api)
                            
                            token_name_row = await self.db.get_token_name(mint, conn_live_sell)
                            token_name = token_name_row['name'] if token_name_row else mint
                            log_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=profit_live, reason=reason, sol_price=sol_price_usd)
                            logger.info(f"[{trading_mode.upper()}] {log_msg}")
                            if self.config.get('PLAY_SELL_SOUND'):
                                if reason in ["🛑 Stop Loss", "🛡️ Breakeven SL", "🆘 Emergency SL (MCap)", "manual_override"]: asyncio.create_task(play_sell_sl_sound_async())
                                elif reason in ["🥇 First TP", "🎯 Second TP", "↘️ Trailing SL"]: asyncio.create_task(play_sell_tp_sound_async())
                            if self.config.get('TELEGRAM_INTERACTION'):
                                telegram_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=profit_live, reason=reason, sol_price=sol_price_usd, for_telegram=True)
                                telegram_msg += f"\nMode: {trading_mode.upper()}\nSignature: {signature}"
                                asyncio.create_task(send_telegram_message(telegram_msg))
                    
                    sell_reasons_triggering_hard_cooldown = self.config.get('_APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
                    if any(configured_reason in reason for configured_reason in sell_reasons_triggering_hard_cooldown):
                        cooldown_minutes = self.config.get('STOP_LOSS_COOLDOWN_MINUTES', 0)
                        if cooldown_minutes > 0:
                            await self.db.set_token_cooldown(mint, cooldown_minutes) 
                    return profit_live
                else:
                    logger.error(f"[{trading_mode.upper()} MODE] Sell failed for {mint}. API Error: {trade_result.get('error', 'Unknown error') if trade_result else 'No API result'}")
                    return None
            else:
                logger.error(f"Unknown TRADING_MODE: '{trading_mode}' in execute_sell for {mint}.")
                return None

        except Exception as e:
            logger.error(f"❌ [{trading_mode.upper()}] Overall error in execute_sell for {mint} (PosID: {position_id_to_update}, Reason: {reason}): {e}", exc_info=True)
            if trading_mode == "simulate": raise 
            return None 

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

        async with self.db.pool.acquire() as conn:
            async with conn.transaction(): 
                try:
                    positions = await self.db.get_active_buy_positions(conn)
                    if not positions:
                        return

                    for position in positions:
                        pos_id = position['id']
                        mint = position['mint']

                        price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn)
                        current_price_to_use = price_data.get('price')
                        current_market_cap_sol_for_log = price_data.get('market_cap')

                        if isinstance(current_market_cap_sol_for_log, str): 
                            try: current_market_cap_sol_for_log = float(current_market_cap_sol_for_log)
                            except ValueError: current_market_cap_sol_for_log = None
                        
                        if current_price_to_use is None or current_price_to_use <= 0:
                            logger.warning(f"Skipping price-based sell checks for {mint} (ID: {pos_id}) due to invalid current price: {current_price_to_use} by method '{self.config.get('PRICE_DETERMINATION_METHOD')}'.")
                            if current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                               (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                                sell_reason_mc = "🆘 Emergency SL (MCap)"
                                logger.info(f"{sell_reason_mc} for {mint} (ID: {pos_id}) due to low MCap. MCap_USD: {(current_market_cap_sol_for_log * sol_price_usd):.2f}")
                                trigger_val_mc = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd)}
                                fallback_price_for_mcap_sl = float(position['buy_price']) 
                                await self.execute_sell(conn, mint, fallback_price_for_mcap_sl, current_market_cap_sol_for_log, sell_reason_mc, 1.0, pos_id, trigger_val_mc)
                            continue 

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
                        if first_tp_hit:
                            trailing_sl_price = highest_price_since_buy * (1 - self.config['TRAILING_STOP_LOSS_PERCENT'] / 100.0)

                        sell_reason = None
                        sell_all = False
                        sell_partial = False
                        sell_percentage_of_initial = 0.0 
                        trigger_values_for_log = {}

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
                        elif first_tp_hit and trailing_sl_price > 0 and current_price_to_use <= trailing_sl_price:
                            sell_reason = "↘️ Trailing SL"
                            sell_all = True
                            trigger_values_for_log = {"trailing_sl_price_threshold": trailing_sl_price, "highest_price_at_trigger": highest_price_since_buy}
                        elif current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                           (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                            sell_reason = "🆘 Emergency SL (MCap)"
                            sell_all = True
                            trigger_values_for_log = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd), "min_mcap_threshold_config": self.config['MIN_MARKETCAP_THRESHOLD']}
                        elif current_market_cap_sol_for_log is None and not sell_reason : 
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
                            percentage_to_sell_api = 0.0
                            if sell_partial: 
                                percentage_to_sell_api = sell_percentage_of_initial 
                            elif sell_all:
                                percentage_to_sell_api = 1.0 

                            profit_from_sell = await self.execute_sell(
                                conn, mint, current_price_to_use, 
                                current_market_cap_sol_for_log if current_market_cap_sol_for_log is not None else 0.0,
                                sell_reason, percentage_to_sell_api, 
                                pos_id, trigger_values_for_log
                            )
                            
                            if profit_from_sell is not None and sell_reason == "🥇 First TP":
                                await self.db.mark_first_tp_hit_and_adjust_sl(pos_id, buy_price, conn)
                                logger.info(f"📈 Marked First TP as hit for {mint} (ID: {pos_id}) and SL adjusted to breakeven ({buy_price:.9f}).")
                            
                            if profit_from_sell is not None: 
                                await asyncio.sleep(0.1) 
                except Exception as e:
                    logger.error(f"❌ Error in check_sell_opportunities transaction block: {e}", exc_info=True)

    async def execute_manual_sell(self, mint: str):
        """Executes a manual sell for all holdings of a specific token, respecting TRADING_MODE."""
        trading_mode = self.config['TRADING_MODE'].lower()
        logger.info(f"[{trading_mode.upper()} MODE] Attempting manual sell for all holdings of token: {mint}")
        
        position_id_to_sell = None
        trigger_price_for_manual_sell = None
        market_cap_for_manual_sell = 0.0

        async with self.db.pool.acquire() as conn_manual_fetch:
            position_data = await conn_manual_fetch.fetchrow(
                "SELECT id, price AS buy_price, remaining_tokens FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' ORDER BY timestamp DESC LIMIT 1",
                mint
            )
            if not position_data:
                logger.warning(f"[{trading_mode.upper()}] No active buy position found for mint {mint} to execute manual sell.")
                await send_telegram_message(f"⚠️ Manual Sell Error: No active position for {mint}.")
                return
            
            if float(position_data['remaining_tokens']) <= 1e-9:
                logger.info(f"[{trading_mode.upper()}] No remaining tokens for active position of {mint}. Manual sell skipped.")
                await send_telegram_message(f"ℹ️ Manual Sell Info: No remaining tokens for {mint}.")
                return

            position_id_to_sell = position_data['id']
            
            price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn_manual_fetch)
            trigger_price_for_manual_sell = price_data.get('price')
            market_cap_for_manual_sell = price_data.get('market_cap') if price_data.get('market_cap') is not None else 0.0

            if trigger_price_for_manual_sell is None or trigger_price_for_manual_sell <= 0:
                logger.error(f"[{trading_mode.upper()}] Cannot execute manual sell for {mint}: Invalid current price ({trigger_price_for_manual_sell}) for execution.")
                await send_telegram_message(f"⚠️ Manual Sell Error for {mint}: Could not determine a valid current price.")
                return

        logger.info(f"[{trading_mode.upper()} MODE] Proceeding with manual sell for {mint} (Pos ID: {position_id_to_sell}) at price {trigger_price_for_manual_sell:.9f}")

        async with self.db.pool.acquire() as conn_for_execute_sell: 
             await self.execute_sell(
                conn=conn_for_execute_sell, 
                mint=mint,
                trigger_price=trigger_price_for_manual_sell, # Changed from current_price
                market_cap_sol_at_trigger=market_cap_for_manual_sell, # Changed from market_cap_sol
                reason="manual_override",
                sell_percentage=1.0,  
                position_id_to_update=position_id_to_sell,
                sell_trigger_values={"command": f"SELL_{mint}", "manual_override_timestamp": datetime.now(timezone.utc).isoformat()}
            )