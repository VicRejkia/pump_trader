# path: trading_logic.py

"""
Handles trading logic including buy/sell decision making,
emergency sell triggers, and portfolio management, supporting multiple trading modes.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
from typing import Optional, Dict, Any

from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState
from utils import (
    play_buy_opportunity_sound, play_sell_sl_sound_async, play_sell_tp_sound_async,
    format_buy_order_log, format_sell_order_log, calculate_trend_indicators
)
from connectors.live_trader_pumpportal import execute_live_pumpportal_trade
from telegram_interface import send_telegram_message

# --- ADD THIS IMPORT ---
from ai_decision_module.ai_decision_maker import AIDecisionMaker

# --- HELPER FUNCTIONS FOR LOGGING (Unchanged) ---
def format_price_for_log(price):
    if price is None: return "N/A"
    if price == 0: return "0.0"
    if abs(price) < 1e-4 or abs(price) >= 1e6: return f"{price:.2e}"
    else: return f"{price:.9f}".rstrip('0').rstrip('.')

def format_pnl_value(value):
    if value < 0: return f"[red]{value:+.4f} SOL[/red]"
    else: return f"{value:+.4f} SOL"

def format_profit_pct(pct):
    if pct < 0: return f"[red]({pct:+.2f}%)[/red]"
    else: return f"({pct:+.2f}%)"
# --- END HELPER FUNCTIONS ---

class TradingManager:
    # --- MODIFIED __init__ ---
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state: GlobalState, ai_decision_maker: Optional[AIDecisionMaker] = None):
        self.db = db_client
        self.config = config_dict
        self.state = state
        # --- ADD THIS LINE ---
        self.ai_decision_maker = ai_decision_maker
    # --- END MODIFICATION ---

    def get_adaptive_atr_multiplier(self, rsi_value: float) -> float:
        """ Returns an ATR multiplier based on the current RSI momentum. (Unchanged) """
        if rsi_value >= self.config['ADAPTIVE_RSI_EXTREME_LEVEL']:
            return self.config['ADAPTIVE_ATR_EXTREME_MULTIPLIER']
        elif rsi_value >= self.config['ADAPTIVE_RSI_STRONG_LEVEL']:
            return self.config['ADAPTIVE_ATR_STRONG_MULTIPLIER']
        else:
            return self.config['ADAPTIVE_ATR_BASE_MULTIPLIER']

    async def _is_trend_reversal_confirmed(self, mint: str) -> bool:
        """
        Checks if a token that was recently stopped out shows signs of a trend reversal. (Unchanged)
        """
        if not self.config.get('USE_TREND_REVERSAL_CONFIRMATION', False):
            return True

        async with self.db.pool.acquire() as conn:
            token_record = await conn.fetchrow("""
                SELECT t.data_source, p.reason, p.timestamp
                FROM tokens t
                LEFT JOIN (
                    SELECT mint, reason, timestamp, ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                    FROM portfolio WHERE tx_type = 'sell'
                ) p ON t.mint = p.mint AND p.rn = 1
                WHERE t.mint = $1;
            """, mint)

        if not token_record:
            logger.warning(f":triangular_flag: Could not find token record for {mint} during trend reversal check.")
            return True

        last_sell_reason = token_record['reason']
        last_sell_timestamp = token_record['timestamp']

        if not last_sell_reason or not last_sell_timestamp:
            return True

        apply_reversal_on_reasons = self.config.get('APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
        recency_hours = self.config.get('TREND_REVERSAL_RECENCY_HOURS', 6)

        is_relevant_reason = any(reason_str in last_sell_reason for reason_str in apply_reversal_on_reasons)
        is_recent = (datetime.now(timezone.utc) - last_sell_timestamp.astimezone(timezone.utc)) < timedelta(hours=recency_hours)

        if not (is_relevant_reason and is_recent):
            logger.debug(f":thumbs_up: Trend reversal check not required for {mint} (Reason: '{last_sell_reason}', IsRecent: {is_recent}).")
            return True

        data_source = token_record['data_source']

        if data_source == 'DEXSCREENER':
            logger.info(f"Token {mint} is migrated. Performing DexScreener snapshot-based trend reversal check...")
            async with self.db.pool.acquire() as conn:
                snapshots = await self.db.analyze_dexscreener_trend(
                    mint,
                    self.config['DEX_REVERSAL_LOOKBACK_MINUTES'],
                    conn
                )

            if len(snapshots) < self.config['DEX_REVERSAL_MIN_SNAPSHOTS']:
                logger.info(f":triangular_flag: DEX Reversal FAILED for {mint}: Not enough recent data points (have {len(snapshots)}, need {self.config['DEX_REVERSAL_MIN_SNAPSHOTS']}).")
                return False

            latest_snapshot = snapshots[0]
            min_liquidity_usd = self.config['DEX_REVERSAL_MIN_LIQUIDITY_USD']
            if float(latest_snapshot['liquidity_usd']) < min_liquidity_usd:
                logger.info(f":thumbs_down: DEX Reversal FAILED for {mint}: Liquidity (${latest_snapshot['liquidity_usd']:.2f}) is below threshold (${min_liquidity_usd:.2f}).")
                return False

            strong_buy_pressure_count = 0
            for snap in snapshots:
                buys = snap['buys_m5']
                sells = snap['sells_m5']
                if buys > 0 and (sells == 0 or (buys / sells) >= self.config['DEX_REVERSAL_MIN_BUY_SELL_RATIO']):
                    strong_buy_pressure_count += 1

            logger.debug(f":bookmark: DEX Reversal analysis for {mint}: Strong Buy Pressure Signals={strong_buy_pressure_count} found in the last {len(snapshots)} snapshots.")

            min_confirmations = self.config['DEX_REVERSAL_MIN_CONFIRMATIONS']
            if strong_buy_pressure_count >= min_confirmations:
                logger.info(f":bookmark: DEXScreener Trend Reversal CONFIRMED for {mint}. Strong buy pressure found in {strong_buy_pressure_count}/{len(snapshots)} recent snapshots.")
                return True
            else:
                logger.info(f":thumbs_down: DEX Reversal FAILED for {mint}: Not enough confirmations of strong buying pressure (have {strong_buy_pressure_count}, need {min_confirmations}).")
                return False

        elif data_source == 'PUMP':
            logger.info(f"Token {mint} is on Pump.fun. Performing indicator-based trend reversal check...")
            start_date_hist = datetime.now(timezone.utc) - timedelta(hours=self.config.get('INDICATOR_LOOKBACK_HOURS', 1))
            end_date_hist = datetime.now(timezone.utc)
            historical_data = await self.db.get_historical_data_for_backtesting([mint], start_date_hist, end_date_hist)

            if not historical_data or mint not in historical_data:
                return False

            df = historical_data[mint]
            df_with_indicators = calculate_trend_indicators(df, self.config)

            if df_with_indicators.empty or len(df_with_indicators) < self.config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30):
                return False

            latest = df_with_indicators.iloc[-1]
            previous = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else latest

            stage1_passed = False
            rsi_neutral_level = self.config.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 45)
            rsi_val = latest.get('RSI', float('nan'))
            bb_lower_band = latest.get(f"BBL_{self.config['BBANDS_PERIOD']}_{self.config['BBANDS_STD_DEV']}", float('inf'))

            if (rsi_val > 30 and previous.get('RSI', float('nan')) <= 30) or \
            (latest.get('Close', 0) > bb_lower_band and previous.get('Close', 0) <= previous.get(f"BBL_{self.config['BBANDS_PERIOD']}_{self.config['BBANDS_STD_DEV']}", float('inf'))):
                stage1_passed = True
            elif rsi_val > rsi_neutral_level:
                stage1_passed = True

            if not stage1_passed:
                return False

            is_above_vwap = latest.get('Close', 0) > latest.get('VWAP', float('-inf'))
            is_ema_bullish = latest.get('EMA_fast', float('-inf')) > latest.get('EMA_slow', float('inf'))

            if is_above_vwap and is_ema_bullish:
                logger.info(f":thumbs_up: Pump.fun Trend Reversal Fully Confirmed for {mint}!")
                return True
            else:
                return False
                
        else:
            logger.warning(f":triangular_flag: Unknown data_source '{data_source}' for {mint} in trend reversal check.")
            return False

    async def check_trading_opportunities(self):
        """✅ Check for new trading opportunities, incorporating AI advice. (Unchanged)"""
        if self.state.shutdown_event.is_set():
            return

        if not self.state.is_buying_enabled:
            logger.debug(":closed_lock_with_key: Buying is currently disabled by command. Skipping buy checks.")
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
                time_interval_minutes=self.config['DEFAULT_TIME_INTERVAL'],
                min_volatility=self.config['MIN_VOLATILITY']
            )

            logger.debug(f":magnifying_glass_tilted_right: Found {len(rows)} potential trading opportunities after initial DB filter.")

            for row in rows:
                mint = row['mint']
                opportunity_price = float(row['latest_price'])
                opportunity_market_cap_sol = float(row['latest_market_cap_sol'])

                if opportunity_price <= 0:
                    logger.warning(f"Skipping buy for {mint} due to invalid opportunity price: {opportunity_price}")
                    continue

                ai_advice_used = None
                if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_decision_maker:
                    async with self.db.pool.acquire() as conn_ai:
                        ai_decision_record = await self.db.get_latest_ai_decision(mint, conn_ai)

                    if ai_decision_record:
                        ai_decision = ai_decision_record['decision']
                        ai_confidence = ai_decision_record['confidence']
                        ai_timestamp = ai_decision_record['evaluation_timestamp']
                        advice_age = datetime.now(timezone.utc) - ai_timestamp
                        max_staleness = timedelta(minutes=self.config.get('AI_ADVICE_MAX_STALENESS_MINUTES', 20))

                        if advice_age <= max_staleness:
                            ai_advice_used = {'decision': ai_decision, 'confidence': ai_confidence, 'timestamp': ai_timestamp.isoformat()}
                            logger.debug(f"🤖 AI Advice ({mint}): {ai_decision} ({ai_confidence}%) - Age: {advice_age.total_seconds():.0f}s")
                            hold_veto_threshold = self.config.get('AI_BUY_HOLD_CONFIDENCE_THRESHOLD', 60)
                            if ai_decision == 'HOLD' and ai_confidence >= hold_veto_threshold:
                                logger.info(f"🤖 AI advised HOLD (Confidence: {ai_confidence} >= {hold_veto_threshold}) for potential buy of {mint}. Deferring purchase.")
                                continue 
                            if ai_decision == 'BUY':
                                logger.debug(f"🤖 AI confirmed potential BUY for {mint} (Confidence: {ai_confidence}).")
                        else:
                            logger.debug(f"🤖 AI advice for {mint} is stale (Age: {advice_age.total_seconds():.0f}s > {max_staleness.total_seconds():.0f}s). Ignoring.")
                    else:
                        logger.debug(f"🤖 AI advice for {mint} buy check unavailable. Using rule-based logic only.")
                
                if self.config.get('USE_TREND_REVERSAL_CONFIRMATION', False):
                    if not await self._is_trend_reversal_confirmed(mint):
                        logger.debug(f"Trend reversal not confirmed for {mint}. Skipping buy opportunity.")
                        continue
                
                await self.execute_buy(mint, opportunity_price, opportunity_market_cap_sol, ai_advice_used)
                await asyncio.sleep(0.1) 

        except Exception as e:
            logger.error(f"❌ Error in check_trading_opportunities: {e}", exc_info=True)
            await asyncio.sleep(5) 

    async def execute_buy(self, mint: str, trigger_price: float, market_cap_sol_at_trigger: float, ai_context: Optional[dict] = None):
        """🛒 Dispatches buy execution based on TRADING_MODE. (Unchanged)"""
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
                            timestamp=datetime.now(timezone.utc), settings=sim_buy_settings, ai_context=ai_context, conn=conn_sim
                        )
                        await self.db.log_completed_trade(
                            token_address=mint,
                            side='buy',
                            amount_in_sol=sol_to_spend_on_tokens,
                            amount_out_tokens=tokens_bought_calculated,
                            fill_price=trigger_price,
                            market_cap_at_trade=market_cap_sol_at_trigger,
                            tx_fee_sol=sim_buy_fee,
                            tip_sol=sim_buy_tip,
                            slippage_percent=0,
                            trade_context={**sim_buy_settings, "ai_advice_at_buy": ai_context} if ai_context else sim_buy_settings
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
                            total_sol_investment=total_sol_outflow_for_pnl, 
                            tokens_bought=tokens_bought_actual,
                            buy_fee=0, buy_tip=api_priority_fee, 
                            initial_stop_loss_price=initial_sl_price_live,
                            initial_tp_price=initial_tp1_price_live, second_tp_price=second_tp_price_live,
                            timestamp=datetime.now(timezone.utc), settings=live_buy_settings, ai_context=ai_context, conn=conn_live
                        )
                        await self.db.log_completed_trade(
                            token_address=mint,
                            side='buy',
                            amount_in_sol=sol_to_spend_on_tokens,
                            amount_out_tokens=tokens_bought_actual,
                            fill_price=executed_price,
                            market_cap_at_trade=market_cap_sol_at_trigger,
                            tx_fee_sol=0,
                            tip_sol=api_priority_fee,
                            slippage_percent=trade_result.get("slippage"),
                            trade_context={**live_buy_settings, "ai_advice_at_buy": ai_context} if ai_context else live_buy_settings,
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
    
    # --- MODIFIED execute_sell ---
    async def execute_sell(self, conn, mint: str, trigger_price: float, market_cap_sol_at_trigger: float, reason: str, sell_percentage: float, position_id_to_update: int, sell_trigger_values: dict = None, ai_context: Optional[dict] = None):
        """
        💸 Dispatches sell execution based on TRADING_MODE.
        NOW ALSO logs the sell event to the AI RAG memory for feedback.
        """
        trading_mode = self.config['TRADING_MODE'].lower()
        if sell_trigger_values is None: sell_trigger_values = {}
        
        sol_price_usd = await self.state.get_sol_price() 
        profit_from_sell = None # Initialize profit variable

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
            if reason == "First TP": 
                tokens_to_sell_on_trigger = initial_tokens_portfolio * sell_percentage
                tokens_to_sell_on_trigger = min(tokens_to_sell_on_trigger, remaining_tokens_portfolio)
            else: 
                tokens_to_sell_on_trigger = remaining_tokens_portfolio * sell_percentage

            if tokens_to_sell_on_trigger <= 1e-9:
                logger.info(f"ℹ️ [{trading_mode.upper()}] Sell amount for {mint} (Reason: {reason}) is negligible ({tokens_to_sell_on_trigger:.12f}). Skipping.")
                return None
            
            # --- Initialize variables for RAG logging ---
            final_executed_price = trigger_price # Default to trigger price
            final_profit_sol = 0.0
            final_net_sol_received = 0.0
            final_market_cap_sol = market_cap_sol_at_trigger
            final_sell_settings = {}
            # ---

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
                    "sell_percentage_of_initial_request": sell_percentage * 100 if reason == "First TP" else (sell_percentage * 100.0 if reason in ["Stop Loss", "Breakeven SL", "Second TP", "Trailing SL", "Emergency SL (MCap)", "manual_override"] else 0.0),
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
                    reason=reason, timestamp=datetime.now(timezone.utc), settings=sim_sell_settings, ai_context=ai_context, conn=conn
                )
                await self.db.log_completed_trade(
                    token_address=mint, side='sell',
                    amount_in_sol=sim_net_sol_received, amount_out_tokens=tokens_to_sell_on_trigger,
                    fill_price=trigger_price, market_cap_at_trade=market_cap_sol_at_trigger,
                    tx_fee_sol=sim_sell_fee, tip_sol=sim_sell_tip, slippage_percent=0,
                    trade_context={**sim_sell_settings, "ai_advice_at_sell": ai_context} if ai_context else sim_sell_settings,
                )
                await self.state.update_sol_balance(sim_net_sol_received)
                
                # Set variables for RAG logging
                profit_from_sell = sim_profit
                final_profit_sol = sim_profit
                final_net_sol_received = sim_net_sol_received
                final_sell_settings = sim_sell_settings

            elif trading_mode in ["paper_trading", "live"]:
                api_pool = self.config.get('DEFAULT_SELL_POOL', "auto")
                
                token_record = await conn.fetchrow("SELECT data_source FROM tokens WHERE mint = $1", mint)
                if token_record and token_record['data_source'] == 'DEXSCREENER':
                    logger.debug(f"Token {mint} is migrated. Attempting to find primary DEX ID for selling.")
                    dex_id = await self.db.get_primary_dex_id_for_migrated_token(mint, conn)
                    if dex_id:
                        api_pool = dex_id
                        logger.info(f"Using dynamically determined pool '{api_pool}' for migrated token {mint}.")
                    else:
                        logger.warning(f"Could not determine specific DEX ID for migrated token {mint}. Falling back to default pool '{api_pool}'.")
                
                api_amount_tokens_str = f"{tokens_to_sell_on_trigger:.9f}" 
                api_priority_fee = float(self.config['DEFAULT_SELL_TIP']) 
                api_slippage = int(self.config.get('DEFAULT_SLIPPAGE_PERCENT', 25))

                logger.info(f"[{trading_mode.upper()} MODE] Initiating sell of {api_amount_tokens_str} {mint} on pool '{api_pool}' (Reason: {reason}, Priority: {api_priority_fee} SOL)")

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

                    # --- This transaction is now inside the outer `execute_sell` transaction ---
                    cost_basis_sold_portion_live = total_investment_sol_at_buy_portfolio * (tokens_to_sell_on_trigger / initial_tokens_portfolio) if initial_tokens_portfolio > 0 else 0
                    profit_live = sol_received_from_api - cost_basis_sold_portion_live

                    new_remaining_tokens_live = remaining_tokens_portfolio - tokens_to_sell_on_trigger
                    new_status_live = 'closed' if new_remaining_tokens_live < 1e-9 else 'active'

                    await self.db.update_portfolio_entry_after_sell(position_id_to_update, new_remaining_tokens_live, new_status_live, conn)
                    
                    live_sell_settings = {
                        "mode": trading_mode, "signature": signature, "reason": reason,
                        "api_pool_used": api_pool,
                        "api_executed_price": executed_price_live, "api_sol_received": sol_received_from_api,
                        "api_priority_fee_sent": api_priority_fee, "api_slippage_sent": api_slippage,
                        **sell_trigger_values,
                        "sell_percentage_of_initial_request": sell_percentage * 100 if reason == "First TP" else (sell_percentage * 100.0 if reason in ["Stop Loss", "Breakeven SL", "Second TP", "Trailing SL", "Emergency SL (MCap)", "manual_override"] else 0.0),
                        "actual_tokens_sold_as_fraction_of_remaining_at_sell_time": (tokens_to_sell_on_trigger / remaining_tokens_portfolio) if remaining_tokens_portfolio > 0 else 0,
                        "sell_fee_config": self.config['DEFAULT_SELL_FEE'],
                        "sell_tip_config": self.config['DEFAULT_SELL_TIP'],
                        "price_determination_method_used": self.config.get('PRICE_DETERMINATION_METHOD'),
                        "trigger_price_at_sell": trigger_price
                    }
                    if market_cap_sol_at_trigger is not None: live_sell_settings["market_cap_sol_at_sell"] = market_cap_sol_at_trigger

                    await self.db.insert_portfolio_sell_record(
                        mint=mint, current_price=executed_price_live, market_cap_sol=market_cap_sol_at_trigger,
                        net_sol_received=sol_received_from_api, 
                        sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                        tokens_sold=tokens_to_sell_on_trigger,
                        sell_fee=0, tip_sol=api_priority_fee, 
                        profit=profit_live,
                        reason=reason, timestamp=datetime.now(timezone.utc), settings=live_sell_settings, ai_context=ai_context, conn=conn
                    )
                    await self.db.log_completed_trade(
                        token_address=mint,
                        side='sell',
                        amount_in_sol=sol_received_from_api,
                        amount_out_tokens=tokens_to_sell_on_trigger,
                        fill_price=executed_price_live,
                        market_cap_at_trade=market_cap_sol_at_trigger,
                        tx_fee_sol=0,
                        tip_sol=api_priority_fee,
                        slippage_percent=trade_result.get("slippage"),
                        trade_context={**live_sell_settings, "ai_advice_at_sell": ai_context} if ai_context else live_sell_settings,
                    )
                    await self.state.update_sol_balance(sol_received_from_api)

                    # Set variables for RAG logging
                    profit_from_sell = profit_live
                    final_executed_price = executed_price_live
                    final_profit_sol = profit_live
                    final_net_sol_received = sol_received_from_api
                    final_sell_settings = live_sell_settings

                else:
                    logger.error(f"[{trading_mode.upper()} MODE] Sell failed for {mint}. API Error: {trade_result.get('error', 'Unknown error') if trade_result else 'No API result'}")
                    return None
            else:
                logger.error(f"Unknown TRADING_MODE: '{trading_mode}' in execute_sell for {mint}.")
                return None
            
            # --- RAG FEEDBACK LOOP & LOGGING ---
            # This block runs for *both* SIMULATE and LIVE modes if profit_from_sell is not None
            if profit_from_sell is not None:
                token_name_row = await self.db.get_token_name(mint, conn)
                token_name = token_name_row['name'] if token_name_row else mint
                log_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=profit_from_sell, reason=reason, sol_price=sol_price_usd)
                logger.info(log_msg)
                
                # --- NEW: Log Outcome to RAG Memory ---
                if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_decision_maker:
                    # Create a "snapshot" of the sell event
                    sell_snapshot_data = {
                        "mint": mint,
                        "source": (await conn.fetchval("SELECT data_source FROM tokens WHERE mint = $1", mint)) or "PUMP",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "decision_context": "SELL_EVENT_OUTCOME", # Special context
                        "market_cap": (final_market_cap_sol * sol_price_usd) if final_market_cap_sol and sol_price_usd else 0,
                        "volatility": 0, # Volatility at sell time isn't as relevant as the reason
                        "token_age_minutes": (datetime.now(timezone.utc) - (await conn.fetchval("SELECT timestamp FROM tokens WHERE mint = $1", mint))).total_seconds() / 60,
                        "is_prolific_creator": False, # Not relevant for sell event
                        "uri_status": "N/A", # Not relevant
                        "market_dynamics_summary_str": f"Sell executed at {final_executed_price:.9f} SOL",
                        "trade_history_summary": "N/A" # Not relevant, outcome is what matters
                    }
                    # Create the "decision" (outcome) info
                    sell_decision_info = {
                        "decision": f"SELL_OUTCOME: {reason}",
                        "confidence": 100, # This was an actual event
                        "explanation": f"Sell of {tokens_to_sell_on_trigger:.4f} tokens executed.\nReason: {reason}\nProfit: {final_profit_sol:+.6f} SOL\nNet SOL Received: {final_net_sol_received:+.6f} SOL"
                    }
                    
                    # Asynchronously add this to RAG memory, don't block the sell logic
                    asyncio.create_task(
                        self.ai_decision_maker.add_decision_snapshot_to_memory(sell_snapshot_data, sell_decision_info)
                    )
                    logger.debug(f"🤖 AI Feedback: Queued sell outcome for {mint} (Reason: {reason}) to RAG memory.")
                # --- END RAG FEEDBACK LOOP ---

                if self.config.get('PLAY_SELL_SOUND'):
                    if any(sl_reason in reason for sl_reason in ["Stop Loss", "Breakeven SL", "Emergency SL", "manual_override"]): asyncio.create_task(play_sell_sl_sound_async())
                    elif any(tp_reason in reason for tp_reason in ["First TP", "Second TP", "Trailing SL"]): asyncio.create_task(play_sell_tp_sound_async())
                if self.config.get('TELEGRAM_INTERACTION'):
                    telegram_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=profit_from_sell, reason=reason, sol_price=sol_price_usd, for_telegram=True)
                    if trading_mode in ["paper_trading", "live"]:
                        telegram_msg += f"\nMode: {trading_mode.upper()}\nSignature: {final_sell_settings.get('signature', 'N/A')}"
                    asyncio.create_task(send_telegram_message(telegram_msg))
                
                sell_reasons_triggering_hard_cooldown = self.config.get('APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
                if any(configured_reason in reason for configured_reason in sell_reasons_triggering_hard_cooldown):
                    cooldown_minutes = self.config.get('STOP_LOSS_COOLDOWN_MINUTES', 0)
                    if cooldown_minutes > 0:
                        await self.db.set_token_cooldown(mint, cooldown_minutes) 
                return profit_from_sell
            
            # This return is for cases where the trade_result failed
            return None

        except Exception as e:
            logger.error(f"❌ [{trading_mode.upper()}] Overall error in execute_sell for {mint} (PosID: {position_id_to_update}, Reason: {reason}): {e}", exc_info=True)
            if trading_mode == "simulate": raise 
            return None
    
    async def check_sell_opportunities(self):
        """
        [REFACTORED v3] Checks for sell opportunities with combined post-TP1 logic. (Unchanged)
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
                        pos_id, mint, token_data_source, volume_stale_since = position['id'], position['mint'], position['data_source'], position['volume_stale_since']
                        
                        price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn)
                        current_price_to_use = price_data.get('price')
                        current_market_cap_sol_for_log = price_data.get('market_cap')
                        
                        if token_data_source == 'DEXSCREENER':
                            if current_price_to_use is None:
                                min_mcap_threshold_usd = self.config['MIN_MARKETCAP_THRESHOLD']
                                if current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0:
                                    current_mcap_usd = current_market_cap_sol_for_log * sol_price_usd
                                    if current_mcap_usd < min_mcap_threshold_usd:
                                        sell_reason = "Emergency SL (MCap during stale volume)"
                                        logger.info(f"🚨 {sell_reason} for {mint} (ID: {pos_id}). MC crashed to ${current_mcap_usd:,.2f} while volume was stale. Overriding patience timer.")
                                        await self.execute_sell(
                                            conn, mint, float(position['buy_price']), current_market_cap_sol_for_log,
                                            sell_reason, 1.0, pos_id, {"reason": "MCap crash during stale period"}
                                        )
                                        continue

                                if volume_stale_since is None:
                                    logger.warning(f"Token {mint} (ID: {pos_id}) has stale volume. Starting patience timer.")
                                    await conn.execute("UPDATE portfolio SET volume_stale_since = NOW() WHERE id = $1", pos_id)
                                    continue
                                else:
                                    time_since_stale = datetime.now(timezone.utc) - volume_stale_since
                                    patience_delay = timedelta(minutes=self.config.get('DEXSCREENER_STALE_VOLUME_SELL_DELAY_MINUTES', 120))
                                    if time_since_stale >= patience_delay:
                                        sell_reason = "Emergency SL (No Volume)"
                                        logger.info(f"🆘 {sell_reason} for {mint} (ID: {pos_id}) after waiting {time_since_stale.total_seconds() / 60:.1f} minutes.")
                                        await self.execute_sell(
                                            conn, mint, float(position['buy_price']), current_market_cap_sol_for_log or 0,
                                            sell_reason, 1.0, pos_id, {"reason": "Stale volume patience timer expired"}
                                        )
                                        continue
                                    else:
                                        wait_time = (patience_delay - time_since_stale).total_seconds() / 60
                                        logger.debug(f"Token {mint} (ID: {pos_id}) is within stale patience window. MCap is OK. Waiting for another {wait_time:.1f} mins.")
                                        continue
                            elif volume_stale_since is not None:
                                logger.info(f"✅ Token {mint} (ID: {pos_id}) has recovered volume. Resetting stale timer.")
                                await conn.execute("UPDATE portfolio SET volume_stale_since = NULL WHERE id = $1", pos_id)
                        
                        safe_price = format_price_for_log(current_price_to_use)
                        safe_mcap = f"{current_market_cap_sol_for_log:,.2f}" if current_market_cap_sol_for_log is not None else "N/A"
                        pnl_emoji, unrealized_pnl_str = "❓", "\tPnL: N/A"

                        if current_price_to_use is not None and current_price_to_use > 0:
                            try:
                                remaining_tokens, initial_tokens, total_investment_sol = float(position['remaining_tokens']), float(position['initial_tokens']), float(position['total_investment_sol'])
                                if initial_tokens > 1e-9 and remaining_tokens > 1e-9:
                                    cost_basis_remaining = (total_investment_sol / initial_tokens) * remaining_tokens
                                    unrealized_pnl_sol = (remaining_tokens * current_price_to_use) - cost_basis_remaining
                                    profit_percentage = (unrealized_pnl_sol / cost_basis_remaining) * 100 if cost_basis_remaining > 1e-9 else 0.0
                                    pnl_emoji = "📈" if unrealized_pnl_sol >= 0 else "📉"
                                    unrealized_pnl_str = f"\tPnL: {str(format_pnl_value(unrealized_pnl_sol))} {str(format_profit_pct(profit_percentage))}"
                            except (TypeError, ValueError, ZeroDivisionError):
                                unrealized_pnl_str, pnl_emoji = "\tPnL: [bold yellow]error[/bold yellow]", "⚠️"

                        logger.debug(f":abacus: Checking sell for {mint:<44} (ID: {pos_id:<4}) {pnl_emoji} ({token_data_source[:4]}) - Price: {safe_price:<12} MCap: {safe_mcap:<10} SOL {unrealized_pnl_str}")

                        ai_advice_used = None
                        ai_decision = None
                        ai_confidence = 0
                        is_ai_advice_valid = False 

                        if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_decision_maker:
                            ai_decision_record = await self.db.get_latest_ai_decision(mint, conn)
                            if ai_decision_record:
                                ai_timestamp = ai_decision_record['evaluation_timestamp']
                                advice_age = datetime.now(timezone.utc) - ai_timestamp
                                max_staleness = timedelta(minutes=self.config.get('AI_ADVICE_MAX_STALENESS_MINUTES', 20))

                                if advice_age <= max_staleness:
                                    is_ai_advice_valid = True
                                    ai_decision = ai_decision_record['decision']
                                    ai_confidence = ai_decision_record['confidence']
                                    ai_advice_used = {'decision': ai_decision, 'confidence': ai_confidence, 'timestamp': ai_timestamp.isoformat()}
                                    logger.debug(f"🤖 AI Advice ({mint}): {ai_decision} ({ai_confidence}%) - Age: {advice_age.total_seconds():.0f}s")
                                else:
                                    logger.debug(f"🤖 AI advice for {mint} is stale (Age: {advice_age.total_seconds():.0f}s > {max_staleness.total_seconds():.0f}s). Ignoring.")
                            else:
                                logger.debug(f"🤖 AI advice for {mint} sell check unavailable. Using rule-based logic only.")
                        
                        if current_price_to_use is None or current_price_to_use <= 0:
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

                        sell_reason = None
                        rule_based_sell_triggered = False 
                        rule_reason = None 
                        trigger_values_for_log = {}

                        if not first_tp_hit:
                            if current_price_to_use <= active_stop_loss_price: rule_based_sell_triggered=True; rule_reason="Stop Loss"; trigger_values_for_log = {"stop_loss_price_threshold": active_stop_loss_price}
                            elif current_price_to_use >= second_tp_price: rule_based_sell_triggered=True; rule_reason="Second TP"; trigger_values_for_log = {"second_tp_price_threshold": second_tp_price}
                            elif current_price_to_use >= initial_tp_price: rule_based_sell_triggered=True; rule_reason="First TP"; trigger_values_for_log = {"first_tp_price_threshold": initial_tp_price}
                        else:
                            lookback_hours = self.config.get('INDICATOR_LOOKBACK_HOURS', 2.0)
                            start_date = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
                            historical_data = await self.db.get_historical_data_for_backtesting([mint], start_date, None)
                            
                            df_indicators = pd.DataFrame() 
                            if historical_data and mint in historical_data:
                                if len(historical_data[mint]) >= self.config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30):
                                    loop = asyncio.get_running_loop()
                                    df_indicators = await loop.run_in_executor(None, calculate_trend_indicators, historical_data[mint], self.config)
                                else:
                                    logger.debug(f"Not enough historical data for {mint} ({len(historical_data[mint])} points) to calculate indicators for sell logic.")

                            if not df_indicators.empty and len(df_indicators) >= 2:
                                latest = df_indicators.iloc[-1]
                                previous = df_indicators.iloc[-2]
                                if latest.get('EMA_fast') < latest.get('EMA_slow') and previous.get('EMA_fast') >= previous.get('EMA_slow'):
                                    rule_based_sell_triggered=True; rule_reason="Trend Reversal (EMA Cross)"; trigger_values_for_log = {"ema_fast": latest.get('EMA_fast'), "ema_slow": latest.get('EMA_slow')}
                                    logger.info(f" EMA cross-down detected for {mint}. Fast EMA: {latest.get('EMA_fast'):.9f}, Slow EMA: {latest.get('EMA_slow'):.9f}")

                            if not rule_based_sell_triggered:
                                effective_sl_price = active_stop_loss_price
                                simple_trailing_sl = highest_price_since_buy * (1 - self.config['TRAILING_STOP_LOSS_PERCENT'] / 100.0)
                                effective_sl_price = max(effective_sl_price, simple_trailing_sl)
                                
                                if self.config['USE_DYNAMIC_SECOND_TP'] and not df_indicators.empty:
                                    latest = df_indicators.iloc[-1]
                                    atr_col = f"ATRr_{self.config['ADAPTIVE_ATR_PERIOD']}"
                                    rsi_col = f"RSI_{self.config['RSI_PERIOD']}"
                                    
                                    if atr_col in latest and rsi_col in latest and pd.notna(latest[atr_col]) and pd.notna(latest[rsi_col]):
                                        multiplier = self.get_adaptive_atr_multiplier(latest[rsi_col])
                                        chandelier_exit = highest_price_since_buy - (multiplier * latest[atr_col])
                                        effective_sl_price = max(effective_sl_price, chandelier_exit)
                                        logger.debug(f"Dynamic SL for {mint}: Breakeven={active_stop_loss_price:.9f}, SimpleTrail={simple_trailing_sl:.9f}, Chandelier={chandelier_exit:.9f} -> Effective SL={effective_sl_price:.9f}")

                                if current_price_to_use <= effective_sl_price:
                                    rule_based_sell_triggered=True
                                    rule_reason="Trailing SL Hybrid"
                                    trigger_values_for_log = {
                                        "effective_sl_price": effective_sl_price, 
                                        "highest_price": highest_price_since_buy,
                                        "breakeven_price": active_stop_loss_price,
                                        "simple_trail_price": simple_trailing_sl
                                    }
                        
                        if not rule_based_sell_triggered:
                            if current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                               (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                                rule_based_sell_triggered=True
                                rule_reason="Emergency SL (MCap)"
                                sell_trigger_values = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd), "min_mcap_threshold_config": self.config['MIN_MARKETCAP_THRESHOLD']}

                        if is_ai_advice_valid:
                            if rule_based_sell_triggered:
                                if ai_decision == 'SELL':
                                    logger.debug(f"🤖 AI confirmed rule-based SELL trigger ({rule_reason}) for {mint} (Confidence: {ai_confidence}).")
                                    sell_reason = rule_reason
                                elif ai_decision == 'HOLD':
                                    override_threshold = self.config.get('AI_HOLD_OVERRIDE_CONFIDENCE_THRESHOLD', 85)
                                    can_override = rule_reason not in ["Stop Loss", "Emergency SL (MCap)", "Emergency SL (No Volume)"]
                                    if can_override and ai_confidence >= override_threshold:
                                        logger.warning(f"🤖 AI advised HOLD (Confidence: {ai_confidence} >= {override_threshold}), overriding rule-based sell trigger ({rule_reason}) for {mint} this cycle.")
                                        continue 
                                    else:
                                        logger.debug(f"🤖 AI advised HOLD (Confidence: {ai_confidence}) but rule ({rule_reason}) is critical or confidence too low. Proceeding with rule-based sell.")
                                        sell_reason = rule_reason
                            else:
                                if ai_decision == 'SELL':
                                    trigger_threshold = self.config.get('AI_SELL_TRIGGER_CONFIDENCE_THRESHOLD', 75)
                                    if ai_confidence >= trigger_threshold:
                                        logger.info(f"🤖 AI advised SELL (Confidence: {ai_confidence} >= {trigger_threshold}) for {mint}, triggering early sell despite no rule match.")
                                        sell_reason = "AI Triggered Sell"
                                        trigger_values_for_log = {"ai_confidence_threshold": trigger_threshold}
                                    else:
                                         logger.debug(f"🤖 AI advised SELL but confidence ({ai_confidence}) is below threshold ({trigger_threshold}). Holding based on rules.")
                                elif ai_decision == 'HOLD':
                                    logger.debug(f"🤖 AI confirmed HOLD for {mint} (Confidence: {ai_confidence}), aligning with rules.")
                        elif rule_based_sell_triggered:
                            sell_reason = rule_reason


                        if sell_reason:
                            sell_percentage_of_initial = 0.0 
                            if sell_reason == "First TP":
                                sell_percentage_of_initial = self.config['FIRST_SELL_PERCENT'] / 100.0
                            else:
                                sell_percentage_of_initial = 1.0 
                            
                            log_message_sell_trigger = (f"Trigger for {mint} (ID: {pos_id}): Reason='{sell_reason}', PriceToUse={current_price_to_use:.9f}")
                            logger.info(log_message_sell_trigger)
                            
                            profit_from_sell = await self.execute_sell(
                                conn, mint, current_price_to_use, 
                                current_market_cap_sol_for_log if current_market_cap_sol_for_log is not None else 0.0,
                                sell_reason, sell_percentage_of_initial, 
                                pos_id, trigger_values_for_log, ai_advice_used
                            )
                            
                            if profit_from_sell is not None and sell_reason == "First TP":
                                await self.db.mark_first_tp_hit_and_adjust_sl(pos_id, buy_price, conn)
                                logger.info(f"📈 Marked First TP as hit for {mint} (ID: {pos_id}) and SL adjusted to breakeven ({buy_price:.9f}).")
                            
                            if profit_from_sell is not None: 
                                await asyncio.sleep(0.1) 
                except Exception as e:
                    logger.error(f"❌ Error in check_sell_opportunities transaction block: {e}", exc_info=True)
    
    async def execute_manual_sell_all(self):
        """Executes a manual sell for ALL active positions. (Unchanged)"""
        trading_mode = self.config['TRADING_MODE'].lower()
        logger.info(f"[{trading_mode.upper()} MODE] Received command to sell ALL active positions.")
        
        positions_to_sell = []
        async with self.db.pool.acquire() as conn_fetch:
            positions_to_sell = await self.db.get_active_buy_positions(conn_fetch)

        if not positions_to_sell:
            logger.info("No active positions found to sell.")
            await send_telegram_message("ℹ️ Sell All Command: No active positions found to sell.")
            return

        logger.info(f"Found {len(positions_to_sell)} active positions to sell.")
        await send_telegram_message(f"🚨 Executing SELL ALL command for {len(positions_to_sell)} positions...")

        for position in positions_to_sell:
            mint = position['mint']
            pos_id = position['id']
            try:
                # --- Must use a NEW connection for each sell's transaction ---
                async with self.db.pool.acquire() as conn_sell:
                    price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn_sell)
                    trigger_price = price_data.get('price')
                    market_cap = price_data.get('market_cap', 0.0)

                    if trigger_price is None or trigger_price <= 0:
                        logger.error(f"[{trading_mode.upper()}] Cannot execute sell for {mint} (part of SELL ALL): Invalid current price ({trigger_price}).")
                        continue

                    logger.info(f"[{trading_mode.upper()}] Selling {mint} (Pos ID: {pos_id}) at price {trigger_price:.9f}...")
                    # --- Pass the new connection to execute_sell ---
                    await self.execute_sell(
                        conn=conn_sell,
                        mint=mint,
                        trigger_price=trigger_price,
                        market_cap_sol_at_trigger=market_cap,
                        reason="manual_override_all",
                        sell_percentage=1.0,
                        position_id_to_update=pos_id,
                        sell_trigger_values={"command": "SELL_ALL_IMMEDIATELY"}
                    )
            except Exception as e:
                logger.error(f"Failed to sell {mint} (Pos ID: {pos_id}) during SELL ALL operation: {e}", exc_info=True)
        
        logger.info("SELL ALL operation completed.")
        await send_telegram_message("✅ SELL ALL operation completed.")
        
    async def execute_manual_sell(self, mint: str):
        """Executes a manual sell for all holdings of a specific token. (Unchanged)"""
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

        # --- This must also acquire its own connection for the transaction ---
        async with self.db.pool.acquire() as conn_for_execute_sell: 
             await self.execute_sell(
                conn=conn_for_execute_sell, 
                mint=mint,
                trigger_price=trigger_price_for_manual_sell,
                market_cap_sol_at_trigger=market_cap_for_manual_sell,
                reason="manual_override",
                sell_percentage=1.0,  
                position_id_to_update=position_id_to_sell,
                sell_trigger_values={"command": f"SELL_{mint}", "manual_override_timestamp": datetime.now(timezone.utc).isoformat()}
            )