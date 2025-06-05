"""
Backtesting Engine Module

Simulates trading strategies on historical data, respecting token lifespans,
cooldown periods, and implementing trend-reversal re-buy logic
to evaluate performance.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta # Added timedelta
from typing import Dict, List, Optional, Any

from bot_logger import logger
import utils # For calculate_trend_indicators
import config as config_module # To access fixed configurations like _APPLY_TREND_REVERSAL_ON_SELL_REASONS

# --- Performance Metrics Calculation ---
def calculate_performance_metrics(
    trade_history: list,
    initial_capital: float,
    final_capital: float,
    start_ts: Optional[datetime] = None,
    end_ts: Optional[datetime] = None,
    simulation_end_reason: str = "Completed"
) -> dict:
    """
    Calculates various performance metrics based on simulated trades.

    Args:
        trade_history: List of dictionaries representing simulated trades.
                       Expected keys: 'timestamp', 'type' ('buy'/'sell'), 'price',
                                      'amount_sol', 'amount_tokens', 'pnl' (for sells).
        initial_capital: Starting capital in SOL.
        final_capital: Ending capital in SOL (including value of remaining assets).
        start_ts: Timestamp of the first data point used in the simulation.
        end_ts: Timestamp of the last data point used or token death.
        simulation_end_reason: Why the simulation stopped ('Completed', 'Token Death', 'Max Steps').


    Returns:
        A dictionary containing performance metrics. Includes added metrics like
        total_return_pct, duration_minutes, simulation_end_reason.
    """
    metrics = {
        "total_pnl": 0.0,
        "total_return_pct": 0.0,
        "total_trades": 0, # Number of completed buy/sell cycles
        "winning_trades": 0,
        "losing_trades": 0,
        "total_profit_sells": 0.0, # Sum of PnL from profitable sells
        "total_loss_sells": 0.0,   # Sum of absolute PnL from losing sells
        "win_rate": 0.0,
        "avg_profit_per_win_trade": 0.0,
        "avg_loss_per_loss_trade": 0.0,
        "profit_factor": 0.0, # Total profit / Total loss
        "max_drawdown": 0.0,
        "simulation_start_ts": start_ts.isoformat() if start_ts else None,
        "simulation_end_ts": end_ts.isoformat() if end_ts else None,
        "simulation_duration_minutes": (end_ts - start_ts).total_seconds() / 60.0 if start_ts and end_ts else None,
        "simulation_end_reason": simulation_end_reason,
    }

    metrics["total_pnl"] = final_capital - initial_capital
    if initial_capital > 0:
        metrics["total_return_pct"] = (metrics["total_pnl"] / initial_capital) * 100.0

    sell_trades = [t for t in trade_history if t['type'] == 'sell' and 'pnl' in t]
    metrics["total_trades"] = len(sell_trades)

    if metrics["total_trades"] > 0:
        for trade in sell_trades:
            pnl = trade.get('pnl', 0.0)
            if pnl > 0:
                metrics["winning_trades"] += 1
                metrics["total_profit_sells"] += pnl
            elif pnl < 0:
                metrics["losing_trades"] += 1
                metrics["total_loss_sells"] += abs(pnl)

        if metrics["total_trades"] > 0: # Should be same as len(sell_trades)
             metrics["win_rate"] = (metrics["winning_trades"] / metrics["total_trades"]) * 100.0

        if metrics["winning_trades"] > 0:
             metrics["avg_profit_per_win_trade"] = metrics["total_profit_sells"] / metrics["winning_trades"]

        if metrics["losing_trades"] > 0:
             metrics["avg_loss_per_loss_trade"] = metrics["total_loss_sells"] / metrics["losing_trades"]

        if metrics["total_loss_sells"] > 0:
             metrics["profit_factor"] = metrics["total_profit_sells"] / metrics["total_loss_sells"]
        elif metrics["total_profit_sells"] > 0:
             metrics["profit_factor"] = float('inf')


    equity_curve = pd.Series(index=[], dtype=float)
    if trade_history:
        first_ts = trade_history[0]['timestamp']
        equity_curve.loc[start_ts if start_ts and start_ts < first_ts else first_ts] = initial_capital
    
    current_portfolio_value = initial_capital
    for trade in trade_history:
        trade_ts = trade['timestamp']
        if trade['type'] == 'buy':
            equity_curve.loc[trade_ts - pd.Timedelta(nanoseconds=1)] = current_portfolio_value
            current_portfolio_value -= trade.get('amount_sol', 0)
            equity_curve.loc[trade_ts] = current_portfolio_value
        elif trade['type'] == 'sell':
            equity_curve.loc[trade_ts - pd.Timedelta(nanoseconds=1)] = current_portfolio_value
            current_portfolio_value += trade.get('amount_sol', 0) # amount_sol is net SOL received for sells
            equity_curve.loc[trade_ts] = current_portfolio_value

    if end_ts:
        if not equity_curve.empty and equity_curve.index[-1] < end_ts:
             equity_curve.loc[end_ts] = final_capital
        elif equity_curve.empty:
             equity_curve.loc[start_ts if start_ts else datetime.now(timezone.utc)] = initial_capital
             equity_curve.loc[end_ts] = final_capital

    if not equity_curve.empty:
        equity_curve = equity_curve.sort_index()
        equity_curve = equity_curve[~equity_curve.index.duplicated(keep='last')]
        roll_max = equity_curve.cummax()
        drawdown = (roll_max - equity_curve) / roll_max
        max_dd = drawdown.max() if not drawdown.empty else 0.0
    else:
        max_dd = 0.0
        
    metrics["max_drawdown"] = max_dd * 100.0

    return metrics

# --- Backtesting Core Function ---
async def run_backtest(
    parameters: dict,
    ohlcv_data: pd.DataFrame,
    initial_capital: float,
    max_timestamp: Optional[datetime] = None
) -> dict:
    """
    Simulates trading with 5-second OHLCV candlestick data, respecting token lifespan,
    cooldowns, and re-buy logic.

    Args:
        parameters: Dictionary of trading parameters for this simulation run.
        ohlcv_data: DataFrame containing historical 5s OHLCV data for the token.
                    Index must be a timezone-aware UTC DatetimeIndex.
                    Expected columns: 'Open', 'High', 'Low', 'Close', 'Volume',
                                      'market_cap_calculated', 'rugcheck_score', 
                                      'socials_score', 'volatility', 'cooldown_until' (can be NaT).
        initial_capital: Starting capital in SOL.
        max_timestamp: Optional UTC timestamp indicating the end of the token's
                       life. Simulation will stop at or before this time.

    Returns:
        A dictionary containing performance metrics calculated by
        `calculate_performance_metrics`.
    """
    mint_addr = parameters.get("mint", "UNKNOWN_MINT")
    simulation_end_reason = "Completed"

    logger.debug(f"--- Entering run_backtest for Mint: {mint_addr} --- Max Timestamp: {max_timestamp}")
    if ohlcv_data.empty:
        logger.warning(f"Historical OHLCV data empty for {mint_addr}.")
        return calculate_performance_metrics([], initial_capital, initial_capital, simulation_end_reason="No Data")

    if not isinstance(ohlcv_data.index, pd.DatetimeIndex) or ohlcv_data.index.tz is None:
        logger.error(f"DataFrame index must be timezone-aware UTC DatetimeIndex for {mint_addr}.")
        try:
             ohlcv_data.index = pd.to_datetime(ohlcv_data.index, utc=True)
             logger.warning("Attempted to convert index to UTC. Review data loading.")
        except Exception:
             return calculate_performance_metrics([], initial_capital, initial_capital, simulation_end_reason="Invalid Index")

    df = ohlcv_data.copy()
    df = df.sort_index()

    start_ts_data = df.index.min()
    end_ts_data = df.index.max()
    if max_timestamp:
        if max_timestamp.tzinfo is None:
             max_timestamp = max_timestamp.replace(tzinfo=timezone.utc)
        df = df[df.index <= max_timestamp]
        end_ts_data = max_timestamp
        simulation_end_reason = "Token Death"
        if df.empty:
            logger.warning(f"No data remains for {mint_addr} after filtering up to max_timestamp {max_timestamp}.")
            return calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, simulation_end_reason)

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 
                     'volatility', 'rugcheck_score', 'socials_score', 'cooldown_until', 
                     'token_creation_time'] # Added cooldown_until and token_creation_time
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required OHLCV columns in input data for {mint_addr}: {missing_cols}")
        # Add missing columns with default NaT for timestamps, NaN for numerics, to allow processing
        for col in missing_cols:
            if col in ['cooldown_until', 'token_creation_time']:
                df[col] = pd.NaT
            else:
                df[col] = np.nan
        # return calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, "Missing OHLCV Cols")


    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Ensure timestamp columns are datetime
    df['cooldown_until'] = pd.to_datetime(df['cooldown_until'], errors='coerce', utc=True)
    df['token_creation_time'] = pd.to_datetime(df['token_creation_time'], errors='coerce', utc=True)


    price_cols = ['Open', 'High', 'Low', 'Close', 'market_cap_calculated', 'volatility']
    df[price_cols] = df[price_cols].ffill().bfill()
    df[['Volume']] = df[['Volume']].fillna(0.0)
    df[['rugcheck_score', 'socials_score']] = df[['rugcheck_score', 'socials_score']].fillna(1000.0) # Default to high (bad) scores
    # Fill NaT for cooldown_until if still needed after potential to_datetime coercion issues
    df['cooldown_until'] = df['cooldown_until'].fillna(pd.NaT)
    df['token_creation_time'] = df['token_creation_time'].ffill().bfill() # Should be static per token


    df = df[df["Close"] > 1e-12]

    if df.empty:
         logger.warning(f"No candle data remained after filtering/validation for {mint_addr}.")
         return calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, "No Candle Data")
    
    # --- Extract Standard Parameters ---
    sol_to_buy = parameters.get('SOL_TO_BUY', 0.9)
    initial_stop_loss_percent = parameters.get('INITIAL_STOP_LOSS_PERCENT', 10.0)
    first_sell_percent = parameters.get('FIRST_SELL_PERCENT', 65.0)
    trailing_stop_loss_percent = parameters.get('TRAILING_STOP_LOSS_PERCENT', 15.0)
    second_take_profit_percent = parameters.get('SECOND_TAKE_PROFIT_PERCENT', 550.0)
    first_sell_profit_margin = parameters.get('FIRST_SELL_PROFIT_MARGIN', 170.0)
    volume_threshold = parameters.get('DEFAULT_VOLUME_THRESHOLD', 19000)
    marketcap_threshold = parameters.get('DEFAULT_MARKETCAP_THRESHOLD', 10000)
    rugcheck_threshold = parameters.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 801)
    socials_threshold = parameters.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 50)
    min_volatility = parameters.get('MIN_VOLATILITY', 0.1)
    buy_fee = parameters.get('DEFAULT_BUY_FEE', 0.001)
    buy_tip = parameters.get('DEFAULT_BUY_TIP', 0.001)
    sell_fee = parameters.get('DEFAULT_SELL_FEE', 0.001)
    sell_tip = parameters.get('DEFAULT_SELL_TIP', 0.001)

    # --- Extract New Re-buy Logic Parameters ---
    use_trend_reversal = bool(parameters.get('USE_TREND_REVERSAL_CONFIRMATION', config_module.USE_TREND_REVERSAL_CONFIRMATION))
    stop_loss_cooldown_minutes_ga = parameters.get('STOP_LOSS_COOLDOWN_MINUTES', config_module.STOP_LOSS_COOLDOWN_MINUTES)
    # MIN_CANDLE_DATA_FOR_INDICATORS is structural, take from module config
    min_candle_data_for_indicators_config = config_module.MIN_CANDLE_DATA_FOR_INDICATORS
    trend_reversal_recency_hours_ga = parameters.get('TREND_REVERSAL_RECENCY_HOURS', config_module.TREND_REVERSAL_RECENCY_HOURS)
    trend_reversal_rsi_neutral_level_ga = parameters.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', config_module.TREND_REVERSAL_RSI_NEUTRAL_LEVEL)
    indicator_lookback_hours_ga = parameters.get('INDICATOR_LOOKBACK_HOURS', config_module.INDICATOR_LOOKBACK_HOURS)
    
    # Indicator periods from GA parameters (or module defaults if not in GA params)
    rsi_period_ga = parameters.get('RSI_PERIOD', config_module.RSI_PERIOD)
    bbands_period_ga = parameters.get('BBANDS_PERIOD', config_module.BBANDS_PERIOD)
    bbands_std_dev_ga = parameters.get('BBANDS_STD_DEV', config_module.BBANDS_STD_DEV)
    fast_ema_period_ga = parameters.get('FAST_EMA_PERIOD', config_module.FAST_EMA_PERIOD)
    slow_ema_period_ga = parameters.get('SLOW_EMA_PERIOD', config_module.SLOW_EMA_PERIOD)

    # This comes from the main config, not typically tuned by GA directly
    apply_trend_reversal_on_sell_reasons_config = config_module._APPLY_TREND_REVERSAL_ON_SELL_REASONS

    # --- Simulation State ---
    current_sol = initial_capital
    trade_history = []
    active_position = None
    simulated_active_cooldowns: Dict[str, datetime] = {} # Manage cooldowns occurring *during* this simulation

    simulation_indices = df.index
    total_steps = len(simulation_indices)
    log_interval = max(1, total_steps // 10)
    step_count = 0

    logger.debug(f"Starting simulation loop for {mint_addr}. Total steps: {total_steps}. Max Timestamp: {end_ts_data}")

    for timestamp in simulation_indices:
        step_count += 1
        if step_count % log_interval == 0:
             logger.debug(f"Simulating step {step_count}/{total_steps} for {mint_addr} (Timestamp: {timestamp})")

        try:
            row = df.loc[timestamp]
            price = float(row["Close"])
            volume = float(row["Volume"])
            high_price = float(row["High"])
            market_cap_sol = float(row.get("market_cap_calculated", 0.0)) # This is USD MC
            # For consistency with trading_logic.py, if 'marketCapSol' (live SOL MC from trades) is available, prefer it
            # However, the current get_historical_data_for_backtesting provides 'marketCapSol' as the OHLCV aggregated live SOL MC.
            # And market_cap_calculated is the USD one. The backtester seems to use 'market_cap_calculated' as the primary market_cap source.
            # Let's assume market_cap_sol here is the USD market cap from data for consistency with existing backtester logic.
            # If actual SOL market cap is needed for specific logic, it should be named distinctly.
            # The original uses row.get("market_cap_calculated", 0.0) for `market_cap_sol` variable.
            # The GA param `DEFAULT_MARKETCAP_THRESHOLD` is in USD.

            rugcheck_score = int(row.get("rugcheck_score", 10000))
            socials_score = int(row.get("socials_score", 100))
            volatility_val = float(row.get("volatility", 0.0)) # Renamed to avoid conflict
            
            # Get the pre-existing cooldown_until from the input data for this specific token
            # This represents a cooldown that was set *before* this backtest run started (e.g. from live trading)
            pre_existing_cooldown_until_data = pd.to_datetime(row.get('cooldown_until'), errors='coerce', utc=True)


            # --- Sell Logic ---
            if active_position:
                pos = active_position
                hp = max(pos['highest_price'], high_price)
                pos['highest_price'] = hp

                current_stop_loss_price = pos['stop_loss_price']
                initial_tp_price = pos['initial_tp_price']
                second_tp_price = pos['second_tp_price']
                first_tp_hit = pos['first_tp_hit']

                trailing_sl_price = 0.0
                if first_tp_hit:
                    trailing_sl_price = hp * (1.0 - trailing_stop_loss_percent / 100.0)

                sell_reason = None
                sell_all = False; sell_partial = False
                sell_percentage = 0.0

                if price <= current_stop_loss_price:
                    sell_reason = "🛑 Stop Loss" if not first_tp_hit else "🛡️ Breakeven SL"; sell_all = True; sell_percentage = 1.0
                elif price >= second_tp_price:
                    sell_reason = "Second TP"; sell_all = True; sell_percentage = 1.0
                elif not first_tp_hit and price >= initial_tp_price:
                    sell_reason = "First TP"; sell_partial = True; sell_percentage = first_sell_percent / 100.0
                elif first_tp_hit and price <= trailing_sl_price:
                    sell_reason = "↘️ Trailing SL"; sell_all = True; sell_percentage = 1.0
                
                # Emergency MCap SL (using the market_cap_sol which is market_cap_calculated (USD))
                # Assuming MIN_MARKET_CAP is a parameter like MIN_MARKETCAP_THRESHOLD USD
                min_emergency_mcap_usd = parameters.get('MIN_MARKET_CAP', 3000) # Fallback to a value if not in GA
                if market_cap_sol < min_emergency_mcap_usd and not sell_reason: # only if no other reason
                    sell_reason = "🆘 Emergency SL (MCap)"; sell_all = True; sell_percentage = 1.0


                if sell_reason:
                    initial_tokens = pos['initial_tokens']
                    remaining_tokens = pos['remaining_tokens']
                    total_investment = pos['total_investment_sol']
                    tokens_to_sell = 0.0

                    if sell_partial:
                        tokens_to_sell = initial_tokens * sell_percentage
                        tokens_to_sell = min(tokens_to_sell, remaining_tokens)
                    elif sell_all:
                        tokens_to_sell = remaining_tokens * sell_percentage # sell_percentage is 1.0 here

                    if tokens_to_sell > 1e-9:
                        gross_sol = tokens_to_sell * price
                        net_sol = gross_sol - sell_fee - sell_tip
                        cost_basis = total_investment * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                        pnl = net_sol - cost_basis

                        current_sol += net_sol
                        pos['remaining_tokens'] -= tokens_to_sell

                        trade_history.append({
                            'timestamp': timestamp, 'type': 'sell', 'price': price,
                            'amount_sol': net_sol, 'amount_tokens': tokens_to_sell,
                            'reason': sell_reason, 'pnl': pnl, 'mint': mint_addr
                        })

                        if sell_partial:
                            pos['first_tp_hit'] = True
                            pos['stop_loss_price'] = pos['buy_price'] # Adjust SL to breakeven

                        if pos['remaining_tokens'] < 1e-9:
                            active_position = None
                        
                        # Check if this sell reason triggers a cooldown (simulated)
                        if stop_loss_cooldown_minutes_ga > 0:
                            for cooldown_trigger_reason in apply_trend_reversal_on_sell_reasons_config:
                                if cooldown_trigger_reason in sell_reason:
                                    cooldown_end_ts = timestamp + pd.Timedelta(minutes=stop_loss_cooldown_minutes_ga)
                                    simulated_active_cooldowns[mint_addr] = cooldown_end_ts
                                    logger.debug(f"Simulated cooldown set for {mint_addr} until {cooldown_end_ts} due to sell reason: {sell_reason}")
                                    break


            # --- Buy Logic ---
            elif not active_position and current_sol >= (sol_to_buy + buy_fee + buy_tip):
                # Check against pre-existing and simulated cooldowns
                is_on_pre_existing_cooldown = pd.notna(pre_existing_cooldown_until_data) and timestamp < pre_existing_cooldown_until_data
                simulated_cooldown_end_ts = simulated_active_cooldowns.get(mint_addr)
                is_on_simulated_cooldown = simulated_cooldown_end_ts and timestamp < simulated_cooldown_end_ts

                if is_on_pre_existing_cooldown:
                    # logger.debug(f"Buy check for {mint_addr} skipped: Token is on pre-existing cooldown until {pre_existing_cooldown_until_data}.")
                    continue
                if is_on_simulated_cooldown:
                    # logger.debug(f"Buy check for {mint_addr} skipped: Token is on simulated cooldown until {simulated_cooldown_end_ts}.")
                    continue
                
                # Standard buy criteria check
                meets_standard_criteria = (
                    volume >= volume_threshold and
                    market_cap_sol >= marketcap_threshold and # market_cap_sol is USD here
                    rugcheck_score < rugcheck_threshold and
                    socials_score < socials_threshold and
                    volatility_val >= min_volatility
                )

                proceed_with_buy_attempt = False
                if not meets_standard_criteria:
                    proceed_with_buy_attempt = False
                elif use_trend_reversal:
                    # Check if a re-buy is warranted due to recent applicable sell
                    was_recently_sold_for_reversal_reason = False
                    if trade_history: # Check only if there's a history
                        for trade in reversed(trade_history):
                            if trade.get('mint') == mint_addr and trade.get('type') == 'sell':
                                time_since_last_sell = timestamp - trade['timestamp']
                                if time_since_last_sell <= pd.Timedelta(hours=trend_reversal_recency_hours_ga):
                                    last_sell_reason = trade.get('reason', '')
                                    for applicable_reason in apply_trend_reversal_on_sell_reasons_config:
                                        if applicable_reason in last_sell_reason:
                                            was_recently_sold_for_reversal_reason = True
                                            break
                                if was_recently_sold_for_reversal_reason:
                                    break # Found a recent applicable sell
                                if time_since_last_sell > pd.Timedelta(hours=trend_reversal_recency_hours_ga):
                                    break # Past recency window for this mint
                    
                    if was_recently_sold_for_reversal_reason:
                        logger.debug(f"Trend reversal check triggered for {mint_addr} at {timestamp} due to recent sell.")
                        
                        # Prepare data slice for indicators
                        # Ensure 'df' here refers to the full ohlcv_data for the current mint, sorted by time
                        current_df_index_loc = df.index.get_loc(timestamp) # df is the full data for this mint
                        
                        # Calculate how many 5s candles are in indicator_lookback_hours_ga
                        candles_for_lookback = int(indicator_lookback_hours_ga * (60 * 60 / 5))
                        start_loc_indicators = max(0, current_df_index_loc - candles_for_lookback + 1) # +1 because slice end is exclusive for iloc for length
                        
                        if (current_df_index_loc - start_loc_indicators + 1) >= min_candle_data_for_indicators_config:
                            indicator_data_slice = df.iloc[start_loc_indicators : current_df_index_loc + 1]
                            
                            indicator_config_for_utils = {
                                'MIN_CANDLE_DATA_FOR_INDICATORS': min_candle_data_for_indicators_config, # This is fixed
                                'RSI_PERIOD': rsi_period_ga,
                                'BBANDS_PERIOD': bbands_period_ga,
                                'BBANDS_STD_DEV': bbands_std_dev_ga,
                                'FAST_EMA_PERIOD': fast_ema_period_ga,
                                'SLOW_EMA_PERIOD': slow_ema_period_ga,
                            }
                            # Make sure 'utils' is imported
                            df_with_indicators = utils.calculate_trend_indicators(indicator_data_slice.copy(), indicator_config_for_utils)

                            if not df_with_indicators.empty and len(df_with_indicators) >= 2:
                                latest_ind = df_with_indicators.iloc[-1]
                                previous_ind = df_with_indicators.iloc[-2]

                                # Stage 1: Potential Bottoming/Recovery Signals
                                stage1_passed = False
                                rsi_latest = latest_ind.get('RSI', float('nan'))
                                rsi_previous = previous_ind.get('RSI', float('nan'))
                                close_latest = latest_ind.get('Close', float('nan')) # Close from indicator df
                                close_previous = previous_ind.get('Close', float('nan'))
                                bb_lower_col = f"BBL_{bbands_period_ga}_{bbands_std_dev_ga}" # Construct BB col name
                                bb_lower_latest = latest_ind.get(bb_lower_col, float('inf'))
                                bb_lower_previous = previous_ind.get(bb_lower_col, float('inf'))

                                rsi_crossed_up_30 = pd.notna(rsi_latest) and pd.notna(rsi_previous) and rsi_latest > 30 and rsi_previous <= 30
                                bb_reentered = pd.notna(close_latest) and pd.notna(close_previous) and \
                                               pd.notna(bb_lower_latest) and pd.notna(bb_lower_previous) and \
                                               close_latest > bb_lower_latest and close_previous <= bb_lower_previous
                                
                                if rsi_crossed_up_30 or bb_reentered:
                                    stage1_passed = True
                                elif pd.notna(rsi_latest) and rsi_latest > trend_reversal_rsi_neutral_level_ga:
                                    stage1_passed = True
                                
                                if stage1_passed:
                                    # Stage 2: Confirmation Filters (VWAP & EMA)
                                    vwap_latest = latest_ind.get('VWAP', float('-inf'))
                                    ema_fast_latest = latest_ind.get('EMA_fast', float('-inf'))
                                    ema_slow_latest = latest_ind.get('EMA_slow', float('inf'))

                                    trend_confirmed_vwap = pd.notna(close_latest) and pd.notna(vwap_latest) and close_latest > vwap_latest
                                    momentum_confirmed_ema = pd.notna(ema_fast_latest) and pd.notna(ema_slow_latest) and ema_fast_latest > ema_slow_latest

                                    if trend_confirmed_vwap and momentum_confirmed_ema:
                                        logger.info(f"Trend reversal confirmed for {mint_addr} at {timestamp}.")
                                        proceed_with_buy_attempt = True
                                    else:
                                        logger.debug(f"Trend reversal Stage 2 failed for {mint_addr}: VWAP={trend_confirmed_vwap}, EMA={momentum_confirmed_ema}")
                                        proceed_with_buy_attempt = False
                                else:
                                    logger.debug(f"Trend reversal Stage 1 failed for {mint_addr}.")
                                    proceed_with_buy_attempt = False
                            else:
                                logger.debug(f"Indicator calculation for trend reversal failed or insufficient data for {mint_addr}.")
                                proceed_with_buy_attempt = False # Cannot confirm
                        else:
                            logger.debug(f"Not enough candles for indicator lookback for {mint_addr}.")
                            proceed_with_buy_attempt = False # Cannot confirm
                    else: # Not recently sold for applicable reason, standard buy applies
                        proceed_with_buy_attempt = True 
                else: # use_trend_reversal is False
                    proceed_with_buy_attempt = meets_standard_criteria


                if proceed_with_buy_attempt:
                    total_investment = sol_to_buy + buy_fee + buy_tip
                    sol_for_tokens = sol_to_buy
                    tokens_bought = sol_for_tokens / price if price > 0 else 0

                    if tokens_bought > 0:
                        initial_sl_price = price * (1.0 - initial_stop_loss_percent / 100.0)
                        
                        cost_of_tp1_portion = total_investment * (first_sell_percent / 100.0)
                        desired_profit_tp1 = cost_of_tp1_portion * (first_sell_profit_margin / 100.0)
                        fees_for_tp1_sell = sell_fee + sell_tip # Assuming same fees for TP1 sell
                        gross_sol_needed_tp1 = cost_of_tp1_portion + desired_profit_tp1 + fees_for_tp1_sell
                        tokens_to_sell_tp1 = tokens_bought * (first_sell_percent / 100.0)
                        initial_tp_price_calc = (gross_sol_needed_tp1 / tokens_to_sell_tp1) if tokens_to_sell_tp1 > 1e-9 else float('inf')
                        
                        second_tp_price_calc = price * (1.0 + second_take_profit_percent / 100.0)

                        current_sol -= total_investment
                        active_position = {
                            'buy_price': price, 'initial_tokens': tokens_bought,
                            'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment,
                            'stop_loss_price': initial_sl_price, 'initial_tp_price': initial_tp_price_calc,
                            'second_tp_price': second_tp_price_calc, 'highest_price': price,
                            'first_tp_hit': False, 'entry_timestamp': timestamp
                        }
                        trade_history.append({
                            'timestamp': timestamp, 'type': 'buy', 'price': price,
                            'amount_sol': total_investment, 'amount_tokens': tokens_bought,
                            'buy_fee': buy_fee, 'buy_tip': buy_tip, 'mint': mint_addr
                        })
                        # Clear any simulated cooldown for this mint upon successful buy
                        if mint_addr in simulated_active_cooldowns:
                            del simulated_active_cooldowns[mint_addr]
                            logger.debug(f"Cleared simulated cooldown for {mint_addr} after successful buy.")


        except KeyError as ke:
            logger.error(f"KeyError accessing data at step {step_count} for {mint_addr} (Timestamp: {timestamp}): Missing key {ke}", exc_info=False)
            continue
        except ValueError as ve:
             logger.error(f"ValueError at step {step_count} for {mint_addr} (Timestamp: {timestamp}): {ve}", exc_info=False)
             continue
        except Exception as loop_err:
             logger.error(f"Error during simulation step {step_count} for {mint_addr} (Timestamp: {timestamp}): {loop_err}", exc_info=True)
             continue

    logger.debug(f"Simulation loop finished for {mint_addr} at step {step_count}.")

    final_value = current_sol
    if active_position:
        if not df.empty: # df is the filtered dataframe for the current token
            # Use the Close price from the *last available candle* in the filtered df
            # Check if the simulation ended because of token death (max_timestamp)
            # or if it simply ran out of data in df.
            last_candle_ts_to_use = df.index[-1]
            if end_ts_data and end_ts_data < df.index[-1] : # If simulation cut short by max_timestamp
                # Find the closest available candle at or before end_ts_data
                valid_ts_before_end = df.index[df.index <= end_ts_data]
                if not valid_ts_before_end.empty:
                    last_candle_ts_to_use = valid_ts_before_end[-1]
            
            last_close_price = float(df.loc[last_candle_ts_to_use]["Close"])

            remaining_tokens = active_position['remaining_tokens']
            gross_sol_final = remaining_tokens * last_close_price
            net_sol_final = gross_sol_final - sell_fee - sell_tip # Assume sell fees if liquidated
            final_value += max(0, net_sol_final) # Cannot have negative value from tokens
            logger.debug(f"Added value of remaining {remaining_tokens:.4f} tokens for {mint_addr} at final Close price {last_close_price:.9f} (Net: {net_sol_final:.6f}) from timestamp {last_candle_ts_to_use}")
        else:
             logger.warning(f"No data available to value remaining position for {mint_addr}. Using current SOL only.")


    logger.debug(f"Calculating final performance metrics for {mint_addr}")
    metrics = calculate_performance_metrics(
        trade_history,
        initial_capital,
        final_value,
        start_ts=start_ts_data, # First timestamp of actual data used
        end_ts=end_ts_data,     # Last timestamp of actual data used or token death
        simulation_end_reason=simulation_end_reason
    )
    metrics["parameters"] = parameters # Store parameters used for this run
    metrics["initial_capital"] = initial_capital
    metrics["final_portfolio_value"] = final_value

    logger.debug(f"--- Exiting run_backtest for Mint: {mint_addr} --- Final Value: {final_value:.4f}")
    return metrics


async def main_test():
    # This requires DB connection and data fetching setup similar to ga_optimizer
    # Ensure the data fetched by get_historical_data_for_backtesting is used
    from database_handler import DatabaseClient, get_token_lifespan
    from ga_config import OPTIMIZABLE_PARAMETERS, BACKTEST_INITIAL_CAPITAL, HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS
    import random
    from bot_logger import setup_logging

    setup_logging()
    db_client = DatabaseClient()
    await db_client.connect()

    test_mint = "X1dpwrtFkMwbFFr6ydAVv1t7ysuXXNCqDcoVpyMpump" # Replace with a valid mint
    start_dt = HISTORICAL_DATA_START_TS
    end_dt = HISTORICAL_DATA_END_TS

    logger.info(f"Fetching OHLCV test data for mint {test_mint} from {start_dt} to {end_dt}")
    # Use the function that returns OHLCV data
    hist_data_dict = await db_client.get_historical_data_for_backtesting([test_mint], start_dt, end_dt)
    logger.debug(f"Fetched historical data: {hist_data_dict}")

    if not hist_data_dict or test_mint not in hist_data_dict:
        logger.error(f"Could not fetch OHLCV data for test mint {test_mint}. Exiting test.")
        await db_client.close()
        return

    test_ohlcv_data = hist_data_dict[test_mint] # This should be the OHLCV DataFrame
    logger.info(f"Fetched {len(test_ohlcv_data)} OHLCV data points for {test_mint}.")

    # --- Get Token Lifespan ---
    lifespan = await get_token_lifespan(db_client, test_mint)
    max_ts = lifespan['end_ts'] if lifespan else None
    logger.info(f"Token Lifespan: Start={lifespan['start_ts']}, End={lifespan['end_ts']}")

    # --- Test Parameters ---
    #test_params = {}
    # for p in OPTIMIZABLE_PARAMETERS:
    #     if 'values' in p:
    #         test_params[p['name']] = random.choice(p['values'])
    #     elif 'low' in p and 'high' in p:
    #          if p['type'] == float: test_params[p['name']] = random.uniform(p['low'], p['high'])
    #          else: test_params[p['name']] = random.randint(p['low'], p['high'])

    # test_params['SOL_TO_BUY'] = 0.5
    # test_params['mint'] = test_mint

    test_params = {
        'SOL_TO_BUY': 0.9, 
        'INITIAL_STOP_LOSS_PERCENT': 10, 
        'FIRST_SELL_PERCENT': 65, 
        'TRAILING_STOP_LOSS_PERCENT': 15,
        'SECOND_TAKE_PROFIT_PERCENT': 550, 
        'FIRST_SELL_PROFIT_MARGIN': 170,
        'DEFAULT_VOLUME_THRESHOLD': 19000, 
        'DEFAULT_MARKETCAP_THRESHOLD': 10000, 
        'MIN_VOLATILITY': 0.1, 
        'DEFAULT_RUGCHECK_SCORE_THRESHOLD': 801, 
        'DEFAULT_SOCIAL_SCORE_THRESHOLD': 50, 
        'MIN_MARKET_CAP': 3000, 
        'DEFAULT_TIME_INTERVAL': 30, 
        'mint': 'X1dpwrtFkMwbFFr6ydAVv1t7ysuXXNCqDcoVpyMpump'
    }  
    # "{""buy_fee_config"": 0.001, ""buy_tip_config"": 0.001, ""sol_to_buy_config"": 0.9, ""first_sell_percent_config"": 65.0, ""calculated_second_tp_price"": 0.000014365116894174576, ""calculated_initial_sl_price"": 0.000001989016185347249, ""calculated_initial_tp_price"": 0.000009228430650648165,
    #  ""volume_threshold_usd_config"": 19000, ""time_interval_minutes_config"": 30, ""min_volatility_percent_config"": 0.1, ""social_score_threshold_config"": 50, ""marketcap_threshold_usd_config"": 10000,
    #  ""first_sell_profit_margin_config"": 170.0, ""rugcheck_score_threshold_config"": 801, ""initial_stop_loss_percent_config"": 10.0, ""second_take_profit_percent_config"": 550.0, ""trailing_stop_loss_percent_config"": 15.0}"

    logger.info("--- Running Backtester Test with OHLCV Data ---")
    logger.info(f"Test Parameters: {test_params}")
    logger.info(f"Initial Capital: {BACKTEST_INITIAL_CAPITAL}")
    logger.info(f"Max Timestamp (Token Death): {max_ts}")

    # Pass the OHLCV data directly
    results = await run_backtest(test_params, test_ohlcv_data, BACKTEST_INITIAL_CAPITAL, max_ts)

    logger.info("--- Backtester Test Results ---")
    import pprint
    pprint.pprint(results)

    await db_client.close()

if __name__ == "__main__":
    import asyncio
    from bot_logger import setup_logging
    setup_logging()
    asyncio.run(main_test())