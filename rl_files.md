# `PUMP_T~1` Project Files

📅 Generated on: 2025-07-14 01:58

📂 Project root: `C:\USERS\SASCHA\DOCUME~1\PROJECTS\PYTHON\CRYPTO\PUMP_T~1`

---

### 📄 backtester.py

```python
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
import config as config_module # To access fixed configurations like APPLY_TREND_REVERSAL_ON_SELL_REASONS

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
    max_timestamp: Optional[datetime] = None,
    dexscreener_snapshot_data: Optional[pd.DataFrame] = None
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
    apply_trend_reversal_on_sell_reasons_config = config_module.APPLY_TREND_REVERSAL_ON_SELL_REASONS

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

                        is_migrated_token = dexscreener_snapshot_data is not None and not dexscreener_snapshot_data.empty
                        
                        if is_migrated_token:
                            # --- DEXSCREENER REVERSAL LOGIC ---
                            logger.debug(f"Token {mint_addr} is migrated. Performing DexScreener snapshot-based check.")
                            
                            # Filter snapshots up to the current simulation time
                            lookback_minutes = parameters.get('DEX_REVERSAL_LOOKBACK_MINUTES', 15)
                            snapshots = dexscreener_snapshot_data[dexscreener_snapshot_data.index <= timestamp]
                            snapshots = snapshots.last(f'{lookback_minutes}min')

                            min_snapshots_needed = parameters.get('DEX_REVERSAL_MIN_SNAPSHOTS', 3)
                            if len(snapshots) < min_snapshots_needed:
                                logger.debug(f"DEX Reversal FAILED for {mint_addr}: Not enough recent snapshots (have {len(snapshots)}, need {min_snapshots_needed}).")
                                proceed_with_buy_attempt = False
                            else:
                                latest_snapshot = snapshots.iloc[-1]
                                min_liquidity_usd = parameters.get('DEX_REVERSAL_MIN_LIQUIDITY_USD', 5000)
                                if float(latest_snapshot['liquidity_usd']) < min_liquidity_usd:
                                    logger.debug(f"DEX Reversal FAILED for {mint_addr}: Liquidity (${latest_snapshot['liquidity_usd']:.2f}) is below threshold (${min_liquidity_usd:.2f}).")
                                    proceed_with_buy_attempt = False
                                else:
                                    strong_buy_pressure_count = 0
                                    min_buy_sell_ratio = parameters.get('DEX_REVERSAL_MIN_BUY_SELL_RATIO', 1.5)
                                    for _, snap in snapshots.iterrows():
                                        buys = snap.get('buys_m5', 0)
                                        sells = snap.get('sells_m5', 0)
                                        if buys > 0 and (sells == 0 or (buys / sells) >= min_buy_sell_ratio):
                                            strong_buy_pressure_count += 1
                                    
                                    min_confirmations = parameters.get('DEX_REVERSAL_MIN_CONFIRMATIONS', 2)
                                    if strong_buy_pressure_count >= min_confirmations:
                                        logger.info(f"🚀 DEXScreener Trend Reversal CONFIRMED for {mint_addr} in backtest.")
                                        proceed_with_buy_attempt = True
                                    else:
                                        logger.debug(f"DEX Reversal FAILED for {mint_addr}: Not enough confirmations (have {strong_buy_pressure_count}, need {min_confirmations}).")
                                        proceed_with_buy_attempt = False
                                        
                        else:
                            # --- PUMP.FUN REVERSAL LOGIC (existing logic) ---
                            logger.debug(f"Token {mint_addr} is on Pump.fun. Performing indicator-based check.")
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
```

---

### 📄 database_handler.py

```python
"""
Database module.
Handles PostgreSQL connections and CRUD operations.
"""

import os
import io
import csv
import glob
from datetime import datetime, timezone,timedelta
import asyncio
import asyncpg
import aiofiles
import json
import pandas as pd
from dotenv import load_dotenv
from bot_logger import logger
from config import _TOTAL_SUPPLY
import config as base_config_module
from state_manager import GlobalState
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from utils import calculate_volatility
import inspect 
from typing import Optional
import statistics 
from decimal import Decimal

# Load environment variables from .env file
load_dotenv()

# Construct the database URL from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?options=-c%20timezone%3Dutc"

# --- Helper Function to Convert Module to Dict ---
# (Place this helper function outside the class, near the imports)
def _config_module_to_dict(module) -> dict:
    """Converts public, uppercase attributes of a module into a dictionary."""
    config_dict = {}
    for key in dir(module):
        # Load only uppercase variables that are not modules/classes/functions/private
        if key.isupper() and not key.startswith('_'):
            value = getattr(module, key)
            # Check type to exclude modules etc.
            if not inspect.ismodule(value) and \
               not inspect.isclass(value) and \
               not inspect.isfunction(value):
                config_dict[key] = value
    logger.debug(f"Converted config module to dict: {list(config_dict.keys())}")
    return config_dict

# --- Helper Function to Sanitize Strings ---
def _sanitize_string(value: Any) -> Optional[str]:
    """Removes null bytes from strings and ensures the value is a string or None."""
    if isinstance(value, str):
        return value.replace('\x00', '')
    return None if value is None else str(value) # Convert other types to string, handle None
class DatabaseClient:
    """Client to manage database connections and operations."""
 
    _DEFAULT_CONFIG = _config_module_to_dict(base_config_module)
    
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict
        self.pool = None
        self.state = GlobalState.get_instance()

        # Use the provided config_dict if available, otherwise use the class default
        if config_dict is not None:
            self.config = config_dict
            logger.debug("DatabaseClient initialized with provided config_dict.")
        else:
            # Use a copy of the default to prevent modifications affecting others
            self.config = self._DEFAULT_CONFIG.copy()
            logger.debug("DatabaseClient initialized with default config from config.py.")

        # Ensure self.config is always a dictionary
        if not isinstance(self.config, dict):
             logger.error(f"DatabaseClient self.config is not a dict! Type: {type(self.config)}. Falling back to default.")
             self.config = self._DEFAULT_CONFIG.copy() # Fallback just in case

    async def connect(self):
        """Establish a connection pool to the PostgreSQL database."""
        try:
            # Use the DB_URL constructed from environment variables
            self.pool = await asyncpg.create_pool(dsn=DB_URL)
            logger.info("Connected to the database successfully.")
        except Exception as e:
            logger.exception("Error connecting to the database: %s", e)
            raise

    async def init_db(self):
        """
        Initialize the database schema by reading and executing all SQL files 
        from the 'sql' subfolder. Additionally, restore the creator_wallets 
        table from the backup file if necessary.
        """
        sql_folder = os.path.join(os.path.dirname(__file__), "sql")
        sql_files = sorted(glob.glob(os.path.join(sql_folder, "*.sql")))
        
        async with self.pool.acquire() as conn:
            # Execute schema SQL files
            for file_path in sql_files:
                try:
                    with open(file_path, "r") as f:
                        sql = f.read()
                    await conn.execute(sql)
                    logger.info("Executed SQL file: %s", os.path.basename(file_path))
                except Exception as e:
                    logger.exception("Error executing SQL file %s: %s", os.path.basename(file_path), e)
                    raise

    async def insert_sol_price(self, price: float, timestamp: datetime = datetime.now(timezone.utc)):
        """Insert a new SOL price into the database."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO sol_price_usd (price, timestamp) VALUES ($1, $2)", price, timestamp)
        except Exception as e:
            logger.exception("Error inserting SOL price into the database: %s", e)
            raise

    async def insert_token(self, data: dict):
        """Checks if the token is valid and stores it if conditions are met."""
        async with self.pool.acquire() as conn:
            mint = data.get('mint')
            if not mint:
                logger.warning("Mint address is missing in the token data.")
                return False
            try:
                async with conn.transaction():
                    # 1. Check if token already exists in tokens or tokens_backup
                    token_exists = await conn.fetchval("""
                        SELECT 1 FROM tokens WHERE mint = $1
                        UNION
                        SELECT 1 FROM tokens_backup WHERE mint = $1
                    """, mint)
                    if token_exists:
                        logger.info(f"Token {mint} is already stored. Skipping.")
                        return False  # Token already exists, no need to insert

                    # 2. Check how many tokens the creator has recently created
                    creator = data.get('traderPublicKey')
                    now = datetime.now(timezone.utc)
                    row = await conn.fetchrow(
                        "SELECT token_count, last_token_time FROM creator_wallets WHERE wallet_address = $1",
                        creator
                    )
                    
                    token_count = 1
                    if row:
                        token_count, last_token_time = row
                        if last_token_time and (now - last_token_time).total_seconds() < 604800:
                            token_count += 1

                        await conn.execute(
                            "UPDATE creator_wallets SET token_count = $1, last_token_time = $2 WHERE wallet_address = $3",
                            token_count, now, creator
                        )
                    else:
                        await conn.execute(
                            "INSERT INTO creator_wallets (wallet_address, token_count, last_token_time) VALUES ($1, $2, $3)",
                            creator, token_count, now
                        )

                    if token_count > self.config.get('MAX_TOKEN_COUNT_PER_CREATOR', 10):
                            logger.debug(f"🤬 [bold red]Suspicious creator[/bold red] %s for token %s with %s tokens in 7 days", creator, data['mint'], token_count)
                            return False

                    sol_price = await self.state.get_sol_price()
                    if sol_price is None or sol_price <= 0:
                        logger.warning(f"⚠ Invalid SOL_PRICE ({sol_price}); skipping insert token operation.")
                        return False # Cannot proceed without valid SOL price
                    
                    # 3. Insert/update token
                    await conn.execute("""
                        INSERT INTO tokens(mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, 
                            vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri, sol_price_usd,
                            is_active, timestamp)
                        VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, True, NOW());
                        """, 
                        data.get('mint'), 
                        data.get('traderPublicKey'), 
                        data.get('initialBuy'), 
                        data.get('solAmount'), 
                        data.get('bondingCurveKey'), 
                        data.get('vTokensInBondingCurve'),
                        data.get('vSolInBondingCurve'), 
                        data.get('marketCapSol'), 
                        _sanitize_string(data.get('name')),
                        _sanitize_string(data.get('symbol')), 
                        _sanitize_string(data.get('uri')),
                        sol_price
                    )
                    logger.debug("Inserted/Updated token %s", data.get('mint'))
                    return True
            except Exception as e:
                logger.exception("Error inserting token data: %s", e)
                raise

    async def insert_migration(self, data: dict):
        """Batch-insert trade data into trades table."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                            INSERT INTO migrations (signature, mint, txType, pool)
                            VALUES ($1, $2, $3, $4)
                        ''',data["signature"], data["mint"], data["txType"], data["pool"])

                        logger.debug(f"Stored migration event for token {data['mint']}")
                    except Exception as e:
                        logger.error(f"❌ Storing migration for {data['mint']} failed: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f"🚨 Error on storing migration: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def insert_trades_batch(self, trade_params: list, mints: list):
        """
        Inserts a batch of trades into the database and updates the last_trade timestamp for the tokens.
        """
        if not trade_params:
            return

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Batch insert trades
                    await conn.executemany('''
                        INSERT INTO trades (
                            signature, mint, trader_pubkey, tx_type, token_amount, sol_amount, price,
                            bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
                            marketCapSol,sol_price_usd, market_cap_calculated, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        ON CONFLICT (signature) DO NOTHING
                    ''', trade_params)

                    # Batch update last_trade timestamps
                    if mints:
                        # Ensure mints are unique before updating
                        unique_mints = list(set(mints))
                        await conn.execute('''
                            UPDATE tokens
                            SET last_trade = NOW()
                            WHERE mint = ANY($1::text[])
                        ''', unique_mints)

                    logger.debug(f"✅ Processed {len(trade_params)} trades in batch")

                except Exception as e:
                    logger.error(f"🚨 Error during batch trade insert: {e}", exc_info=True)
                    # The transaction will be rolled back automatically
                    raise # Re-raise the exception so the caller knows about the failure

    async def get_tokens_to_unsubscribe(self, mc_drop_threshold, inactivity_period, min_token_age):
        """Fetch tokens to unsubscribe based on market cap drop and inactivity."""
        query = """
            SELECT t.mint
            FROM tokens t
            LEFT JOIN (
                -- Subquery to find the very latest trade tick for each token
                SELECT mint, market_cap_sol, timestamp,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM v_unified_market_ticks_live
            ) latest ON t.mint = latest.mint AND latest.rn = 1
            WHERE
                -- Condition 1: The token must be older than the minimum age.
                t.timestamp <= NOW() - (INTERVAL '1 minute' * $3) -- $3 = min_token_age
                
                -- Condition 2: The token must not have an active position in the portfolio.
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
                
                -- Condition 3: The token must meet one of the "dead" criteria.
                AND (
                    -- Criteria A: The token HAS trades but is inactive or has crashed.
                    (
                        latest.mint IS NOT NULL AND (
                            -- Market cap has dropped below the threshold.
                            (latest.market_cap_sol * 100.0 / t.marketCapSol) < (100 - $1) -- $1 = mc_drop_threshold
                            OR
                            -- The last trade was longer ago than the inactivity period.
                            latest.timestamp <= NOW() - (INTERVAL '1 minute' * $2) -- $2 = inactivity_period
                        )
                    )
                    OR
                    -- Criteria B: The token has NO trades at all.
                    (latest.mint IS NULL)
                )
            ORDER BY t.timestamp DESC;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, mc_drop_threshold, inactivity_period, min_token_age)

    async def get_active_tokens(self, limit: int = 20000):
        """Fetch active tokens from the database."""
        query = """
            SELECT mint FROM tokens WHERE is_active = True
            ORDER BY timestamp DESC LIMIT $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, limit)
        
    async def is_suspicious_creator(self, creator: str):
        """Check if a creator is suspicious based on the number of tokens created."""
        query = """
            SELECT token_count FROM creator_wallets WHERE wallet_address = $1
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, creator)
            if row and row['token_count'] > 2:
                return True
            return False

    async def fetch_tokens_by_creator(self, creator: str, respect_portfolio: bool = False):
        if respect_portfolio:
            query = """
                SELECT mint FROM tokens 
                WHERE traderpublickey = $1
                    AND mint NOT IN (SELECT mint FROM portfolio)
            """
        else:
            query = """
                SELECT mint FROM tokens 
                WHERE traderpublickey = $1
            """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, creator)
        
    async def has_active_buy_order(self, mint: str):
        query = """
            SELECT 1 FROM portfolio WHERE mint = $1 AND tx_type = 'buy' AND status = 'active'
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, mint)
            return result is not None
        
    async def get_total_supply(self, mint: str): #
        """Fetch the total supply of a token (RAW units) from rugcheck table.
           NOTE: For price calculations, use _get_latest_token_info which also gets decimals.
        """
        query = "SELECT token_supply FROM rugcheck WHERE mint = $1" #
        async with self.pool.acquire() as conn: #
            result = await conn.fetchrow(query, mint) #
            # Ensure _TOTAL_SUPPLY is fetched from self.config
            default_supply = self.config.get('_TOTAL_SUPPLY', 1_000_000_000) #
            return result['token_supply'] if result and result['token_supply'] is not None else default_supply #

    async def find_trading_opportunities(self, sol_price: float, volume_threshold: float, marketcap_threshold: float, rugcheck_threshold: int, social_score_threshold: int, time_interval_minutes: int, min_volatility: float): 
        """
        Identifies potential token buy opportunities.
        - Volume Calculation is source-aware:
            - PUMP: SUMs all individual trade sol_amounts.
            - DEXSCREENER: Takes only the SINGLE LATEST volume snapshot to prevent duplicate counting.
        - Volatility is calculated ONLY from high-frequency PUMP trades for accuracy.
        """
        
        query = """
            WITH LatestTickData AS (
                -- This correctly gets the latest price/MC from either source
                SELECT
                    mint,
                    price_sol,
                    market_cap_sol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM v_unified_market_ticks_live -- Uses LIVE view, which is correct
                WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
            ),
            RecentMetrics AS (
                -- THIS CTE IS NOW SOURCE-AWARE TO PREVENT DOUBLE-COUNTING VOLUME
                SELECT
                    mint,
                    SUM(calculated_volume) AS volume_recent_sol
                FROM (
                    -- 1. Sum up all individual Pump.fun trades from the 'trades' table
                    SELECT
                        mint,
                        sol_amount AS calculated_volume
                    FROM trades -- Use base table for PUMP data
                    WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval

                    UNION ALL

                    -- 2. Get only the LATEST 5-minute volume for migrated tokens
                    SELECT
                        mint_address AS mint,
                        (volume_m5 / sol_price_usd) AS calculated_volume
                    FROM (
                        SELECT
                            mint_address,
                            volume_m5,
                            sol_price_usd,
                            ROW_NUMBER() OVER(PARTITION BY mint_address ORDER BY timestamp DESC) as rn
                        FROM dexscreener_data -- Use base table for DEXSCREENER data
                        WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
                          AND sol_price_usd > 0 -- Avoid division by zero
                    ) AS ranked_dex
                    WHERE rn = 1
                ) AS combined_volume_sources
                GROUP BY mint
            ),
            VolatilityData AS (
                -- THIS CTE IS NOW MODIFIED TO ONLY USE PUMP.FUN TRADES FOR RELIABLE CALCULATION
                SELECT
                    mint,
                    -- The volatility formula remains the same
                    STDDEV(log_return) * SQRT(GREATEST(COUNT(*), 1)) AS volatility
                FROM (
                    SELECT
                        mint,
                        -- Use price_sol from the unified view
                        LN(price_sol / LAG(price_sol) OVER (PARTITION BY mint ORDER BY timestamp)) AS log_return
                    -- <<< CHANGE: Use 'v_unified_market_ticks_historical' view instead of 'trades'
                    FROM v_unified_market_ticks_live
                    WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
                      -- <<< CHANGE: Use 'price_sol' column from the view
                      AND price_sol > 0
                ) sub
                WHERE log_return IS NOT NULL
                    AND log_return > '-Infinity'::double precision
                    AND log_return < 'Infinity'::double precision
                GROUP BY mint
                HAVING COUNT(*) > 5
            )
            SELECT
                t.mint, ltd.price_sol AS latest_price, ltd.market_cap_sol AS latest_market_cap_sol,
                COALESCE(rm.volume_recent_sol, 0) AS volume_in_interval,
                COALESCE(vd.volatility, 0) AS volatility_in_interval,
                rc.tokenMeta_name AS name, rc.tokenMeta_symbol AS symbol,
                rc.score AS rugcheck_score, t.socials_score
            FROM tokens AS t
            INNER JOIN rugcheck AS rc ON t.mint = rc.mint
            INNER JOIN LatestTickData AS ltd ON t.mint = ltd.mint AND ltd.rn = 1
            LEFT JOIN RecentMetrics AS rm ON t.mint = rm.mint
            LEFT JOIN VolatilityData AS vd ON t.mint = vd.mint
            WHERE
                t.is_active = TRUE AND
                rc.score IS NOT NULL AND rc.score < $4 AND
                t.socials_score IS NOT NULL AND t.socials_score < $5 AND
                (COALESCE(rm.volume_recent_sol, 0) * $1) >= $2 AND
                (ltd.market_cap_sol * $1) >= $3 AND
                COALESCE(vd.volatility, 0) >= $7 AND
                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') AND
                (t.cooldown_until IS NULL OR t.cooldown_until < NOW())
            ORDER BY rm.volume_recent_sol DESC;
        """
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch(query, sol_price, volume_threshold, marketcap_threshold, rugcheck_threshold, social_score_threshold, str(time_interval_minutes), min_volatility)
            except Exception as e:
                logger.error(f"Error finding trading opportunities: {e}", exc_info=True)
                return []

    async def get_active_buy_positions(self, conn=None):
        """Fetches active buy positions from the portfolio."""
        query = '''
            SELECT p.id, p.mint, p.price AS buy_price, p.initial_tokens, p.remaining_tokens, p.total_investment_sol,
                p.stop_loss_price, p.highest_price, p.initial_tp_price, p.second_tp_price, p.first_tp_hit,
                t.marketCapSol as initial_market_cap_sol, t.data_source,
                p.timestamp
            FROM portfolio p
            JOIN tokens t ON p.mint = t.mint
            WHERE p.status = 'active' AND p.tx_type = 'buy'
        '''
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetch(query)
        finally:
            if not conn and connection: # Release connection only if it was acquired here
                await self.pool.release(connection)

    async def get_latest_prices(self, mints: list[str], conn=None):
        """Fetches the latest price and market cap for a list of mints."""
        if not mints:
            return {}
        query = f'''
            WITH LatestTrades AS (
                SELECT
                    mint,
                    price_sol AS price,
                    market_cap_sol AS marketCapSol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                FROM v_unified_market_ticks_live
                WHERE mint = ANY($1::text[])
            )
            SELECT mint, price, marketCapSol FROM LatestTrades WHERE rn = 1
        '''
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, mints)
            results = {}
            for row in rows:
                mint = row['mint']
                price_val = float(row['price']) if row['price'] is not None else None
                market_cap_val = float(row['marketcapsol']) if row['marketcapsol'] is not None else None # Ensure marketcapsol from DB

                # Store market cap if it's valid, regardless of price for now
                # Store price only if it's valid and positive
                current_data = {'price': None, 'market_cap': None}

                if market_cap_val is not None and market_cap_val > 0: # Require positive MC
                    current_data['market_cap'] = market_cap_val
                
                if price_val is not None and price_val > 0:
                    current_data['price'] = price_val
                
                # Only add to results if we have at least a valid market_cap or a valid price
                if current_data['market_cap'] is not None or current_data['price'] is not None:
                    results[mint] = current_data
                else:
                    logger.warning(f"For mint {mint}, latest trade had invalid price ({row['price']}) AND invalid marketcap ({row['marketcapsol']}). Not returning data.")
            return results
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_primary_dex_id_for_migrated_token(self, mint: str, conn=None) -> str | None:
        """
        Fetches the dexId of the highest-liquidity pair for a migrated token
        from the most recent dexscreener_data entry.
        """
        query = """
            SELECT full_response
            FROM dexscreener_data
            WHERE mint_address = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            latest_record = await connection.fetchrow(query, mint)
            if latest_record and latest_record['full_response']:
                try:
                    # The full_response is stored as a JSON string, so we load it
                    pair_data = json.loads(latest_record['full_response'])
                    dex_id = pair_data.get('dexId')
                    if dex_id:
                        logger.debug(f"Found primary dexId '{dex_id}' for migrated token {mint}.")
                        return dex_id
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse dexId from full_response for {mint}: {e}")
            return None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def update_portfolio_highest_price(self, position_id: int, price: float, conn=None):
        """Updates the highest price for a given portfolio position."""
        query = 'UPDATE portfolio SET highest_price = $1 WHERE id = $2'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, price, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def mark_first_tp_hit_and_adjust_sl(self, position_id: int, buy_price: float, conn=None):
        """Marks the first TP as hit and adjusts the stop loss to breakeven."""
        query = 'UPDATE portfolio SET first_tp_hit = TRUE, stop_loss_price = $1 WHERE id = $2'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, buy_price, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_portfolio_entry_for_update(self, position_id: int, conn=None):
        """Fetches a specific portfolio buy entry needed for sell calculations."""
        query = '''
            SELECT price AS buy_price, initial_tokens, remaining_tokens, total_investment_sol, fee AS buy_fee, tip AS buy_tip
            FROM portfolio
            WHERE id = $1 AND status = 'active' AND tx_type = 'buy'
        '''
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def update_portfolio_entry_after_sell(self, position_id: int, new_remaining_tokens: float, new_status: str, conn=None):
        """Updates remaining tokens and status of a portfolio entry after a sell."""
        query = 'UPDATE portfolio SET remaining_tokens = $1, status = $2 WHERE id = $3'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, new_remaining_tokens, new_status, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def insert_portfolio_sell_record(self, mint: str, current_price: float, market_cap_sol: float, net_sol_received: float, sol_price_usd: float, tokens_sold: float, sell_fee: float, sell_tip: float, profit: float, reason: str, timestamp: datetime, settings: dict, conn=None):
        """Inserts a sell transaction record into the portfolio, including settings."""
        query = '''
            INSERT INTO portfolio
            (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, tokens, fee, tip, profit, total_investment_sol,
             remaining_tokens, status, reason, timestamp, initial_tokens, stop_loss_price, highest_price, settings)
            VALUES ($1, 'sell', $2, $3, $4, $5, $6, $7, $8, $9, 0, 0, 'closed', $10, $11, 0, 0, 0, $12)
        '''
        connection = conn or await self.pool.acquire()
        try:
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, net_sol_received, sol_price_usd, tokens_sold,
                                   sell_fee, sell_tip, profit, reason, timestamp, settings_json)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_token_name(self, mint: str, conn=None):
        """Fetches the name of a token given its mint address."""
        query = "SELECT name FROM tokens WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, mint)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def insert_portfolio_buy_record(self, mint: str, current_price: float, market_cap_sol: float, sol_base_amount: float, sol_price_usd: float, total_sol_investment: float, tokens_bought: float, buy_fee: float, buy_tip: float, initial_stop_loss_price: float, initial_tp_price: float, second_tp_price: float, timestamp: datetime, settings: dict, conn=None):
        """Inserts a buy transaction record into the portfolio, including settings."""
        query = """
            INSERT INTO portfolio
                (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, total_investment_sol, tokens,
                 fee, tip, remaining_tokens, stop_loss_price, highest_price,
                 initial_tp_price, second_tp_price, first_tp_hit,
                 status, timestamp, initial_tokens, settings)
            VALUES ($1, 'buy', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, FALSE, 'active', $15, $16, $17)
        """
        connection = conn or await self.pool.acquire()
        try:
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, sol_base_amount, sol_price_usd, total_sol_investment, tokens_bought,
                                   buy_fee, buy_tip, tokens_bought, # remaining_tokens = initial_tokens
                                   initial_stop_loss_price, current_price, # highest_price = current_price
                                   initial_tp_price, second_tp_price,
                                   timestamp, tokens_bought, # initial_tokens
                                   settings_json) # settings
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    # Modify existing has_active_buy_order to accept optional connection
    async def has_active_buy_order(self, mint: str, conn=None):
        query = """
            SELECT 1 FROM portfolio WHERE mint = $1 AND tx_type = 'buy' AND status = 'active'
        """
        connection = conn or await self.pool.acquire()
        try:
            result = await connection.fetchval(query, mint)
            return result is not None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_last_trade_timestamp(self, mint: str) -> Optional[datetime]:
        """Get the timestamp of the last trade for a given mint."""
        query = "SELECT timestamp FROM v_unified_market_ticks_live WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, mint)
            return row['timestamp'] if row else None

    async def get_trade_history(self, mints: list[str]):
        """Fetches price and timestamp for given mints from trades and trades_backup."""
        if not mints:
            return []
        # Ensure logger is accessible if used within the method, assuming it's defined globally or passed in
        # from logger import logger # Uncomment if logger is needed and not globally accessible
        # Use the v_trades view which combines trades and trades_backup
        query = """
            SELECT mint, price_sol as price, timestamp
            FROM v_unified_market_ticks_historical -- CORRECT: Uses HISTORICAL view
            WHERE mint = ANY($1::text[])
            ORDER BY mint, timestamp;
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, mints)
                # Convert asyncpg Record objects to dictionaries for easier handling
                return [dict(row) for row in results]
            except Exception as e:
                # Log the error using the logger instance
                logger.error(f"Error fetching trade history for mints {mints}: {e}", exc_info=True)
                return [] # Return empty list on error

    async def get_all_unique_mints_with_names(self):
        """Fetches all unique mint addresses and their names from relevant tables."""
        # This query prioritizes names from the 'tokens' table, falling back to 'tokens_backup'.
        # It assumes mints exist in trades/trades_backup might also exist in tokens/tokens_backup.
        # Use the v_tokens and v_rugcheck views
        # Fetch symbol, socials_score, and latest rugcheck score for display
        query = """
            WITH LatestRugcheck AS (
                SELECT
                    mint,
                    score,
                    ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) as rn
                FROM v_rugcheck -- Use the rugcheck view
            )
            SELECT
                vt.mint,
                COALESCE(vt.name, vt.mint) AS name, -- Fallback to mint if name is null
                vt.symbol,
                vt.socials_score,
                lr.score AS rugcheck_score
            FROM v_tokens vt -- Use the tokens view
            LEFT JOIN LatestRugcheck lr ON vt.mint = lr.mint AND lr.rn = 1
            WHERE vt.mint IS NOT NULL -- Ensure mint is not null from the view
            ORDER BY name, vt.mint; -- Order by name from the view
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query) # No parameters needed for this version using views
                # Return list of dictionaries
                # Return richer dictionary including scores
                return [
                    {
                        'mint': row['mint'],
                        'name': row['name'],
                        'symbol': row['symbol'],
                        'socials_score': row['socials_score'],
                        'rugcheck_score': row['rugcheck_score'] # Might be None
                    } for row in results
                ]
            except Exception as e:
                logger.error(f"Error fetching unique mints with names: {e}", exc_info=True)
                return []
            
    async def get_all_migrated_tokens(self) -> List[str]:
        """Fetches all active tokens that have been marked as migrated to DEXScreener."""
        query = "SELECT mint FROM tokens WHERE data_source = 'DEXSCREENER' AND is_active = TRUE ORDER BY timestamp DESC"
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [row['mint'] for row in rows]
        except Exception as e:
            logger.error(f"Error fetching migrated tokens: {e}", exc_info=True)
            return []

    async def get_filtered_tokens(self, max_socials=100, max_rugcheck=10000, min_volume_sol=0, time_window_minutes=60, portfolio_only=False):
        """
        Fetches tokens filtered by:
        - socials score <= max_socials
        - latest rugcheck score <= max_rugcheck (or NULL)
        - trade volume in the last time_window_minutes relative to the token's latest trade >= min_volume_sol
        - optionally filters to tokens in the active portfolio
        """

        try:
            max_socials = int(max_socials)
            max_rugcheck = int(max_rugcheck)
            min_volume_sol = float(min_volume_sol)
            time_window_minutes = str(time_window_minutes)
        except (ValueError, TypeError):
            logger.error("Invalid filter parameter types received.")
            return []

        params = [max_socials, max_rugcheck, min_volume_sol, time_window_minutes]

        query = """
        WITH LatestRugcheck AS (
            SELECT
                mint,
                score,
                ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) AS rn
            FROM v_rugcheck
        ),
        LastTrades AS (
            SELECT
                mint,
                MAX(timestamp) AS last_trade_time
            FROM v_trades
            GROUP BY mint
        ),
        FilteredTrades AS (
            SELECT
                t.mint,
                SUM(t.sol_amount) AS volume_sol
            FROM v_trades t
            JOIN LastTrades lt ON t.mint = lt.mint
            WHERE t.timestamp BETWEEN (lt.last_trade_time - ($4 || ' minutes')::INTERVAL) AND lt.last_trade_time
            GROUP BY t.mint
        )
        SELECT DISTINCT
            vt.mint,
            COALESCE(vt.name, vt.mint) AS name,
            vt.socials_score,
            lr.score AS rugcheck_score,
            COALESCE(ft.volume_sol, 0) AS recent_volume_sol
        FROM v_tokens vt
        LEFT JOIN LatestRugcheck lr ON vt.mint = lr.mint AND lr.rn = 1
        LEFT JOIN FilteredTrades ft ON vt.mint = ft.mint
        """

        if portfolio_only:
            query += """
            INNER JOIN portfolio p ON vt.mint = p.mint
            """

        query += """
        WHERE
            vt.socials_score IS NOT NULL AND vt.socials_score <= $1
            AND (lr.score IS NULL OR lr.score <= $2)
            AND COALESCE(ft.volume_sol, 0) >= $3
        ORDER BY name, vt.mint;
        """
        print(f"Query: {query}")
        print(f"params: {params}")
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, *params)
                return [
                    {
                        'mint': row['mint'],
                        'name': row['name'],
                        'socials': row['socials_score'],
                        'rugcheck': row['rugcheck_score'],
                        'volume': round(row['recent_volume_sol'], 4)
                    } for row in results
                ]
            except Exception as e:
                logger.error(f"Error fetching filtered tokens: {e}", exc_info=True)
                return []


    async def get_portfolio_transactions(self, mints: list[str]):
        """Fetches buy/sell transaction timestamps and prices for given mints from the portfolio."""
        if not mints:
            return {} # Return empty dict if no mints provided

        query = """
            SELECT mint, tx_type, timestamp, price
            FROM portfolio
            WHERE mint = ANY($1::text[])
            ORDER BY mint, timestamp;
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, mints)
                portfolio_data = {}
                for row in results:
                    mint = row['mint']
                    if mint not in portfolio_data:
                        portfolio_data[mint] = {'buys': [], 'sells': []}

                    # Keep the original timestamp object and ensure price is float
                    tx_info = {'timestamp': row['timestamp'], 'price': float(row['price'])}

                    if row['tx_type'] == 'buy':
                        portfolio_data[mint]['buys'].append(tx_info)
                    elif row['tx_type'] == 'sell':
                        portfolio_data[mint]['sells'].append(tx_info)

                logger.debug(f"Fetched portfolio transactions for mints: {mints}")
                return portfolio_data
            except Exception as e:
                logger.error(f"Error fetching portfolio transactions for mints {mints}: {e}", exc_info=True)
                return {} # Return empty dict on error

    async def backup_and_delete_token(self, mint: str, archived_at: datetime, reason: str=None):
        """Backup core table data to a corresponding backup table."""

        # --- START: ADD THIS SAFETY CHECK BLOCK ---
        try:
            async with self.pool.acquire() as conn:
                is_active_in_portfolio = await conn.fetchval(
                    "SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' LIMIT 1",
                    mint
                )
                if is_active_in_portfolio:
                    logger.critical(
                        f"CRITICAL SAFEGUARD: Prevented backup/deletion of token {mint} because it has an ACTIVE position in the portfolio. Reason for attempted deletion: '{reason}'."
                    )
                    # Deactivate the token in the 'tokens' table so it's not picked up by other processes,
                    # but DO NOT delete it, allowing the sell logic to continue managing the position.
                    await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                    return # Exit the function immediately.
        except Exception as e:
            logger.error(f"Error during safety check in backup_and_delete_token for {mint}: {e}", exc_info=True)
            return # Exit on error to be safe
        # --- END: ADD THIS SAFETY CHECK BLOCK ---
        final_reason = reason # Initialize final_reason with the provided reason
 
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                                    INSERT INTO tokens_backup (
                                        mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
                                        vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
                                        socials_score, socials_last_checked, sol_price_usd, is_active, last_trade, timestamp,
                                        cooldown_until,
                                        backup_reason, backup_timestamp
                                    )
                                    SELECT
                                        mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
                                        vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
                                        socials_score, socials_last_checked, sol_price_usd, is_active, last_trade, timestamp,
                                        cooldown_until,
                                        $1, NOW()
                                    FROM tokens
                                    WHERE mint = $2
                                ''', final_reason, mint)
                        
                        await conn.execute('''
                            INSERT INTO trades_backup SELECT *, NOW() FROM trades WHERE mint = $1
                        ''', mint)
 
                        await conn.execute('''
                            INSERT INTO rugcheck_backup SELECT *, NOW() FROM rugcheck WHERE mint = $1
                        ''', mint)
 
                        # Backup migrations, ignoring conflicts on the primary key
                        await conn.execute('''
                            INSERT INTO migrations_backup SELECT *, NOW() FROM migrations WHERE mint = $1
                            ON CONFLICT (signature) DO NOTHING -- Conflict check on signature
                        ''', mint)

                        await conn.execute('''
                            INSERT INTO dexscreener_data_backup SELECT *, NOW() FROM dexscreener_data WHERE mint_address = $1
                        ''', mint)
 
                        await conn.execute("DELETE FROM tokens WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM trades WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM rugcheck WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM migrations WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM dexscreener_data WHERE mint_address = $1", mint)
 
                        logger.debug(f"🧹 Backup & deletion completed for {mint}")
 
                    except Exception as e:
                        logger.error(f"❌ Backup failed for {mint}: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f"🚨 backup_and_delete_token: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def backup_creator_wallets(self):
        """Dumps the creator_wallets table to a JSON file."""
        backup_file_path = os.path.join(os.path.dirname(__file__), self.config.get("_BACKUP_STORAGE_PATH", "backups"), "creator_wallets_backup.json")
        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)  # Ensure data directory exists

        logger.info("Backing up creator_wallets table...")
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT wallet_address, token_count, last_token_time FROM creator_wallets")
                
                # Convert rows to a list of dictionaries
                data = [
                    {
                        "wallet_address": row["wallet_address"],
                        "token_count": row["token_count"],
                        "last_token_time": row["last_token_time"].isoformat() if row["last_token_time"] else None
                    }
                    for row in rows
                ]
                
                # Write the data to a JSON file
                async with aiofiles.open(backup_file_path, "w") as f:
                    await f.write(json.dumps(data, indent=4))
                
                logger.info(f"✅ Successfully backed up {len(rows)} creator wallets to {backup_file_path}")
        except Exception as e:
            logger.exception(f"Error backing up creator_wallets table: {e}")
            # Decide if we should raise or just log


    async def restore_creator_wallets(self):
        backup_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            self.config.get("_BACKUP_STORAGE_PATH", "backups"), 
            "creator_wallets_backup.json"
        ))

        if not os.path.exists(backup_path):
            logger.warning("Backup file not found: %s", backup_path)
            return

        try:
            with open(backup_path, "r") as f:
                data = json.load(f)

            # Convert JSON data into tuples for faster insertion
            records = [
                (
                    record["wallet_address"],
                    record["token_count"],
                    datetime.fromisoformat(record["last_token_time"]) if record.get("last_token_time") else None
                )
                for record in data
            ]

            # Batch size
            BATCH_SIZE = 100

            # Insert using batches
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]
                sql = """
                    INSERT INTO creator_wallets (wallet_address, token_count, last_token_time)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (wallet_address) DO UPDATE SET
                        token_count = GREATEST(creator_wallets.token_count, EXCLUDED.token_count),
                        last_token_time = CASE
                            WHEN EXCLUDED.token_count > creator_wallets.token_count THEN EXCLUDED.last_token_time
                            ELSE creator_wallets.last_token_time
                        END;
                """
                async with self.pool.acquire() as conn:
                    await conn.executemany(sql, batch)

            logger.info("Loaded backup data from %s (%d records)", backup_path, len(records))

        except Exception as e:
            logger.exception("Error loading backup data: %s", e)
            raise

    # --- START: Refactored Price Calculation Logic ---
    async def _get_raw_trades_for_window(self, mint: str, window_minutes: float, conn) -> List[Dict[str, Any]]:
        """Fetches raw trades (timestamp, sol_amount, token_amount) for a given window."""
        query = """
            SELECT timestamp, sol_amount, token_amount
            FROM trades
            WHERE mint = $1
            AND timestamp >= NOW() - ($2 || ' minutes')::interval
            AND token_amount > 0 AND sol_amount > 0 -- Ensure valid amounts for price calculation
            ORDER BY timestamp ASC;
        """
        return await conn.fetch(query, mint, str(window_minutes))
    
    async def _get_latest_token_info(self, mint: str, conn) -> Dict[str, Optional[float]]:
        """
        Fetches the latest token_supply and token_decimals for a mint.
        It queries rugcheck and rugcheck_backup directly as v_rugcheck might not have token_decimals.
        """
        query = """
            SELECT
                token_supply,
                token_decimals
            FROM (
                SELECT
                    token_supply,
                    token_decimals,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY COALESCE(last_checked, '1970-01-01'::timestamptz) DESC) as rn
                FROM (
                    SELECT mint, token_supply, token_decimals, last_checked FROM rugcheck WHERE mint = $1
                    UNION ALL
                    SELECT mint, token_supply, token_decimals, last_checked FROM rugcheck_backup WHERE mint = $1
                ) combined_rugcheck_data
                WHERE token_supply IS NOT NULL AND token_supply > 0
                  AND token_decimals IS NOT NULL AND token_decimals >= 0
            ) ranked_supply_info
            WHERE rn = 1;
        """
        record = await conn.fetchrow(query, mint)
        if record:
            return {'token_supply': float(record['token_supply']), 'token_decimals': int(record['token_decimals'])}
        else:
            logger.warning(f"No token_supply/decimals found in rugcheck/rugcheck_backup for {mint}. Using default supply from config.")
            # Using _TOTAL_SUPPLY and assuming default decimals (e.g., 9, or make it configurable)
            # For this example, let's assume a common default like 6 if not found, or make it part of config
            default_decimals = self.config.get('_DEFAULT_DECIMALS_FOR_MISSING', 6) # Add to config if needed
            return {'token_supply': float(self.config.get('_TOTAL_SUPPLY', 1_000_000_000)), 'token_decimals': default_decimals}


    # --- START: MODIFIED/NEW Price Calculation Helper Logic ---

    async def _get_raw_trades_for_price_calc(self, mint: str, config_params: dict, conn) -> List[Dict[str, Any]]:
        """
        Fetches raw trades (timestamp, sol_amount, token_amount) for a given window,
        supporting both time-based and count-based windows.
        """
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        # Common base of the query selecting necessary columns and initial filters
        query_select_cols = "SELECT timestamp, sol_amount, token_amount, price_sol"
        query_from_where = """
            FROM v_unified_market_ticks_live -- <<< CHANGE TO LIVE VIEW
            WHERE mint = $1
            AND sol_amount IS NOT NULL AND sol_amount > 0 
            AND token_amount IS NOT NULL AND token_amount > 0
        """
        params = [mint]
        final_query: str

        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            # For time window, order by timestamp ascending directly
            final_query = query_select_cols + query_from_where + f" AND timestamp >= NOW() - ($2::text || ' minutes')::interval ORDER BY timestamp ASC;"
            params.append(window_minutes)
        elif window_type == "count":
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            # For count window:
            # 1. Subquery selects the latest N trades.
            # 2. Outer query orders these N trades by timestamp ascending.
            final_query = f"""
                SELECT timestamp, sol_amount, token_amount, price_sol
                FROM (
                    {query_select_cols}
                    {query_from_where} 
                    ORDER BY timestamp DESC
                    LIMIT $2 
                ) AS latest_n_trades
                ORDER BY timestamp ASC;
            """
            # Parameter $1 is mint, $2 is trade_count
            params.append(trade_count)
        else:
            logger.warning(f"Unknown PRICE_WINDOW_TYPE: {window_type}. Defaulting to time window of 1 min.")
            final_query = query_select_cols + query_from_where + " AND timestamp >= NOW() - INTERVAL '1 minute' ORDER BY timestamp ASC;"
        
        return await conn.fetch(final_query, *params)

    async def _get_raw_marketcaps_for_calc(self, mint: str, config_params: dict, conn) -> List[Dict[str, Any]]:
        """
        Fetches raw marketCapSol values from trades for a given window,
        supporting both time-based and count-based windows.
        """
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        query_select_cols = "SELECT timestamp, market_cap_sol"
        query_from_where = """
            FROM v_unified_market_ticks_live -- <<< CHANGE TO LIVE VIEW
            WHERE mint = $1
            AND market_cap_sol IS NOT NULL AND market_cap_sol > 0
        """
        params = [mint]
        final_query: str

        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            final_query = query_select_cols + query_from_where + f" AND timestamp >= NOW() - ($2::text || ' minutes')::interval ORDER BY timestamp ASC;"
            params.append(window_minutes)
        elif window_type == "count":
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            final_query = f"""
                SELECT *
                FROM (
                    {query_select_cols}
                    {query_from_where}
                    ORDER BY timestamp DESC
                    LIMIT $2
                ) AS latest_n_marketcaps
                ORDER BY timestamp ASC;
            """
            params.append(trade_count)
        else:
            logger.warning(f"Unknown PRICE_WINDOW_TYPE: {window_type}. Defaulting to time window of 1 min for MC calc.")
            final_query = query_select_cols + query_from_where + " AND timestamp >= NOW() - INTERVAL '1 minute' ORDER BY timestamp ASC;"
                
        return await conn.fetch(final_query, *params)

    def _apply_iqr_to_trades(self, trade_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates prices for trades and applies IQR filtering.
        Returns a list of trade records that are considered inliers.
        """
        if not trade_records:
            return []

        prices = []
        for r in trade_records:
            try:
                price = float(r['sol_amount']) / float(r['token_amount'])
                prices.append(price)
            except (TypeError, ValueError, ZeroDivisionError):
                prices.append(None) # Mark invalid prices

        # Filter out None prices before IQR
        valid_prices_for_iqr = [p for p in prices if p is not None]
        if not valid_prices_for_iqr:
            logger.warning("No valid prices to apply IQR filtering.")
            return [] # Return all trades if no valid prices for IQR

        q1 = np.percentile(valid_prices_for_iqr, 25)
        q3 = np.percentile(valid_prices_for_iqr, 75)
        iqr_val = q3 - q1
        lower_bound = q1 - 1.5 * iqr_val
        upper_bound = q3 + 1.5 * iqr_val

        inlier_trades = []
        for i, r in enumerate(trade_records):
            price = prices[i]
            if price is not None and lower_bound <= price <= upper_bound:
                # Add the calculated price to the trade record for convenience
                r_copy = dict(r) # Create a copy to avoid modifying the original record list
                r_copy['price'] = price
                inlier_trades.append(r_copy)

        if not inlier_trades:
            logger.warning("All trades filtered out as outliers by IQR. No inlier trades to use.")
            # Fallback: could return unfiltered trades or a subset based on other criteria
            # For now, returning empty list, forcing price calculation to fail or use other fallbacks.
            return []
        return inlier_trades
    
    def _apply_iqr_to_values(self, values: List[float]) -> List[float]: #
        if not values or len(values) < 4: #
            return values #

        try:
            q1 = np.percentile(values, 25) #
            q3 = np.percentile(values, 75) #
            iqr_val = q3 - q1 #
            
            if iqr_val == 0: #
                return values #

            lower_bound = q1 - 1.5 * iqr_val #
            upper_bound = q3 + 1.5 * iqr_val #
            inliers = [v for v in values if lower_bound <= v <= upper_bound] #
            
            if not inliers: #
                logger.warning("IQR filtering removed all values. Returning original values as fallback.") #
                return values #
            return inliers #
        except Exception as e:
            logger.error(f"Error during IQR calculation for values: {e}. Returning original values.", exc_info=True) #
            return values #

    async def _calculate_median_price_with_iqr(self, mint: str, config_params: dict, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades: #
            all_prices = [float(r['sol_amount'])/float(r['token_amount']) for r in trade_records if r.get('token_amount') and float(r['token_amount']) > 0 and r.get('sol_amount') is not None] #
            if all_prices: #
                 logger.warning(f"All prices for {mint} filtered by IQR. Falling back to unfiltered median for price calc.") #
                 return statistics.median(all_prices) #
            return None #

        inlier_prices = [float(trade['price']) for trade in inlier_trades] #
        return statistics.median(inlier_prices) if inlier_prices else None #

    async def _calculate_vwap_price_with_iqr(self, mint: str, config_params: dict, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades: #
            # Could add fallback to unfiltered VWAP here if desired
            logger.warning(f"No inlier trades for {mint} after IQR for VWAP calculation.") #
            return None #

        total_sol_inliers = sum(float(trade['sol_amount']) for trade in inlier_trades) #
        total_tokens_inliers = sum(float(trade['token_amount']) for trade in inlier_trades) #

        if total_tokens_inliers == 0: #
            return None #
        return total_sol_inliers / total_tokens_inliers #

    async def _calculate_twap_price_with_iqr(self, mint: str, config_params: dict, interval_seconds: int, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades_with_price = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades_with_price: #
            return None #

        df_data = [{'timestamp': pd.to_datetime(trade['timestamp'], utc=True), 'price': float(trade['price'])} for trade in inlier_trades_with_price] #
        df = pd.DataFrame(df_data) #
        if df.empty: return None #
        df = df.set_index('timestamp') #
        
        interval_prices = df['price'].resample(f'{interval_seconds}S').median(numeric_only=True) #
        valid_interval_prices = interval_prices.dropna() #
        if valid_interval_prices.empty: return None #
        
        twap = valid_interval_prices.mean() #
        return float(twap) if pd.notnull(twap) else None #

    # New helper for robust median market cap
    async def _calculate_median_marketcap_with_iqr(self, mint: str, config_params: dict, conn) -> float | None:
        trade_records_for_mc = await self._get_raw_marketcaps_for_calc(mint, config_params, conn)
        # logger.debug(f"Fetched {len(trade_records_for_mc)} market cap records for {mint}.")
        # logger.debug(f"First 5 records: {trade_records_for_mc[:5]}") # Debugging output)
        if not trade_records_for_mc:
            logger.debug(f"No market cap records found for {mint}. Cannot calculate median market cap.")
            return None

        market_caps = [float(r['market_cap_sol']) for r in trade_records_for_mc if r.get('market_cap_sol') is not None] #
        if not market_caps:
            logger.debug(f"No valid market caps found for {mint}. Cannot calculate median market cap.")
            return None #

        inlier_market_caps = self._apply_iqr_to_values(market_caps) #
        if not inlier_market_caps:
            logger.warning(f"All market caps for {mint} filtered by IQR. Falling back to unfiltered median for MC calc.") #
            return statistics.median(market_caps) if market_caps else None #
        
        return statistics.median(inlier_market_caps) if inlier_market_caps else None


    async def _get_latest_price_from_dexscreener(self, mint: str, conn) -> Dict[str, Optional[float]]:
        """
        NEW HELPER: Fetches the single latest price snapshot for a migrated token.
        """
        query = """
            SELECT price_usd, market_cap, sol_price_usd, volume_m5
            FROM dexscreener_data
            WHERE mint_address = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        record = await conn.fetchrow(query, mint)
        # --- FIX ---
        # This conditional logic is the core of the fix.
        # It now checks if 5-minute volume is greater than zero.
        if not record or not record['price_usd'] or not record['sol_price_usd'] or record['sol_price_usd'] <= 0 or float(record['volume_m5']) <= 0:
            logger.warning(f"DEXScreener data for {mint} is stale (0 volume in m5). Treating price AND market cap as invalid.")
            # Return None for both price and market cap
            return {'price': None, 'market_cap': None}
        # --- END FIX ---

        price_usd = float(record['price_usd'])
        market_cap_usd = float(record['market_cap'])
        sol_price_usd = float(record['sol_price_usd'])

        # Convert to SOL-denominated values for consistency
        price_sol = price_usd / sol_price_usd
        market_cap_sol = market_cap_usd / sol_price_usd

        return {'price': price_sol, 'market_cap': market_cap_sol}

    async def _get_robust_price_from_pump(self, mint: str, config_params: dict, conn) -> Dict[str, Optional[float]]:
        """
        MODIFIED LOGIC: Calculates robust price ONLY from Pump.fun trades.
        This re-uses your existing median/vwap/twap logic but on a clean data source.
        """
        # Note: Your existing helper functions like _calculate_median_price_with_iqr,
        # _calculate_vwap_price_with_iqr, and their own helpers (_get_raw_trades_for_price_calc)
        # would need to be modified to query the `trades` table directly instead of `v_unified_market_ticks_live`.
        # For simplicity, we will implement the MEDIAN calculation directly here.
        
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        # Build query to fetch raw trades only from the `trades` table
        params = [mint]
        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            query = """
                SELECT price, marketCapSol FROM trades
                WHERE mint = $1 AND timestamp >= NOW() - ($2::text || ' minutes')::interval
                ORDER BY timestamp DESC;
            """
            params.append(window_minutes)
        else: # 'count'
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            query = """
                SELECT price, marketCapSol FROM trades
                WHERE mint = $1 ORDER BY timestamp DESC LIMIT $2;
            """
            params.append(trade_count)

        trade_records = await conn.fetch(query, *params)
        if not trade_records:
            return {'price': None, 'market_cap': None}

        # Apply IQR outlier removal and calculate median
        prices = [float(r['price']) for r in trade_records if r.get('price') is not None]
        market_caps = [float(r['marketcapsol']) for r in trade_records if r.get('marketcapsol') is not None]

        if not prices:
             return {'price': None, 'market_cap': None}

        # Using your _apply_iqr_to_values helper for simplicity
        inlier_prices = self._apply_iqr_to_values(prices)
        inlier_market_caps = self._apply_iqr_to_values(market_caps)

        final_price = statistics.median(inlier_prices) if inlier_prices else None
        final_market_cap = statistics.median(inlier_market_caps) if inlier_market_caps else None
        
        return {'price': final_price, 'market_cap': final_market_cap}

    async def get_price_and_market_cap_for_decision(self, mint: str, config_from_caller: dict, conn) -> Dict[str, Optional[float]]:
        """
        REFACTORED: Centralized function to get the decision price and market cap for a token,
        using a source-specific strategy as you proposed.
        """
        # 1. Determine the data source for the token
        token_record = await conn.fetchrow("SELECT data_source FROM tokens WHERE mint = $1", mint)

        if not token_record:
            logger.warning(f"Could not find token {mint} in 'tokens' table to determine data source.")
            return {'price': None, 'market_cap': None}

        data_source = token_record['data_source']
        logger.debug(f"Getting price for {mint} using source-specific method for: {data_source}")

        # 2. Branch logic based on the data source
        if data_source == 'DEXSCREENER':
            # For migrated tokens, get the latest clean price from dexscreener_data
            return await self._get_latest_price_from_dexscreener(mint, conn)
        else: #// 'PUMP'
            # For non-migrated tokens, use the robust calculation to handle outliers
            return await self._get_robust_price_from_pump(mint, config_from_caller, conn)

    async def analyze_dexscreener_trend(self, mint: str, lookback_minutes: int, conn) -> list:
        """
        Fetches recent dexscreener_data snapshots for trend analysis.
        """
        query = """
            SELECT
                price_change_m5,
                buys_m5,
                sells_m5,
                liquidity_usd,
                timestamp
            FROM dexscreener_data
            WHERE mint_address = $1
              AND timestamp >= NOW() - ($2::text || ' minutes')::interval
            ORDER BY timestamp DESC;
        """
        try:
            return await conn.fetch(query, mint, str(lookback_minutes))
        except Exception as e:
            logger.error(f"Error fetching DexScreener trend data for {mint}: {e}", exc_info=True)
            return []

    async def get_latest_dexscreener_response(self, mint: str, conn=None) -> str | None:
        """Fetches the 'full_response' JSON string of the most recent entry for a mint."""
        query = """
            SELECT full_response FROM dexscreener_data
            WHERE mint_address = $1 ORDER BY timestamp DESC LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            record = await connection.fetchval(query, mint)
            return record
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_total_tracked_tokens(self, backedup=False):
        """Fetches the total number of tracked tokens from the database."""
        query = "SELECT COUNT(*) FROM tokens"
        if backedup:
            query = "SELECT COUNT(*) FROM v_tokens"
        
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(query)
                return result if result is not None else 0
            except Exception as e:
                logger.error(f"Error fetching total tracked tokens: {e}", exc_info=True)
                return 0

    async def load_all_configurations(self) -> Dict[str, Any]:
        """Loads all configuration parameters from the database."""
        query = "SELECT key, value, type FROM configurations"
        config_data = {}
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                for row in rows:
                    key, str_value, value_type = row['key'], row['value'], row['type']
                    try:
                        if value_type == 'int':
                            config_data[key] = int(str_value)
                        elif value_type == 'float':
                            config_data[key] = float(str_value)
                        elif value_type == 'bool':
                            config_data[key] = str_value.lower() == 'true'
                        elif value_type == 'list':
                            config_data[key] = json.loads(str_value) # Assuming lists are stored as JSON strings
                        elif value_type == 'str':
                            config_data[key] = str_value
                        else:
                            logger.warning(f"Unknown configuration type '{value_type}' for key '{key}'. Storing as string.")
                            config_data[key] = str_value
                    except (ValueError, TypeError, json.JSONDecodeError) as e:
                        logger.error(f"Error converting configuration value for key '{key}' (type: {value_type}, value: '{str_value}'): {e}. Storing as raw string or None.")
                        config_data[key] = str_value # Fallback to string
                logger.info(f"Loaded {len(config_data)} configurations from database.")
                return config_data
        except Exception as e:
            logger.error(f"Error loading configurations from database: {e}", exc_info=True)
            return {} # Return empty dict on error

    async def save_configuration_parameter(self, key: str, value: Any, value_type: str, description: Optional[str] = None):
        """Saves or updates a single configuration parameter in the database."""
        query = """
            INSERT INTO configurations (key, value, type, description, last_updated)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                type = EXCLUDED.type,
                description = EXCLUDED.description,
                last_updated = NOW();
        """
        str_value = ""
        if value_type == 'bool':
            str_value = 'true' if value else 'false'
        elif value_type == 'list':
            str_value = json.dumps(value) # Store lists as JSON strings
        elif value is None: # Handle None explicitly for other types
            str_value = None # Store as NULL in DB if appropriate, or handle as empty string
        else:
            str_value = str(value)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, key, str_value, value_type, description)
            logger.debug(f"Saved configuration: {key} = {value} (Type: {value_type})")
        except Exception as e:
            logger.error(f"Error saving configuration parameter {key}: {e}", exc_info=True)

    async def get_python_type_string(self, value: Any) -> str:
        """Determines the storable type string for a Python value."""
        if isinstance(value, bool): return 'bool'
        if isinstance(value, int): return 'int'
        if isinstance(value, float): return 'float'
        if isinstance(value, list): return 'list'
        if isinstance(value, str): return 'str'
        # Fallback for other types, or raise error
        logger.warning(f"Unsupported type for config persistence: {type(value)} for value '{value}'. Defaulting to 'str'.")
        return 'str'

    async def get_configuration_parameter(self, key: str) -> Optional[Any]:
        """Fetches a single configuration parameter from the database."""
        # This method might not be strictly necessary if all configs are loaded at once,
        # but can be useful for specific lookups.
        all_configs = await self.load_all_configurations()
        return all_configs.get(key)

    async def insert_heartbeat(self, event_type: str = 'heartbeat', details: Optional[dict] = None):
        """Insert a new heartbeat or event into the bot_heartbeat table."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO bot_heartbeat (event_type, details) VALUES ($1, $2)",
                    event_type, json.dumps(details) if details else None
                )
            # logger.debug(f"Heartbeat event '{event_type}' inserted.") # Optional logging
        except Exception as e:
            logger.error(f"Error inserting heartbeat event: {e}", exc_info=True)
            # Decide if you want to raise, as heartbeat failure could be critical

    async def get_last_heartbeat_before(self, timestamp: datetime) -> Optional[datetime]:
        """Get the last heartbeat recorded before a given timestamp."""
        query = "SELECT timestamp FROM bot_heartbeat WHERE timestamp < $1 ORDER BY timestamp DESC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, timestamp)
            return row['timestamp'] if row else None

    async def get_first_heartbeat_after(self, timestamp: datetime) -> Optional[datetime]:
        """Get the first heartbeat recorded after a given timestamp."""
        query = "SELECT timestamp FROM bot_heartbeat WHERE timestamp > $1 ORDER BY timestamp ASC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, timestamp)
            return row['timestamp'] if row else None

    async def check_for_data_gap_on_restart(self,
                                            archived_at: datetime,
                                            gap_detection_threshold_seconds: int) -> bool:
        """
        Checks if there was a significant gap in bot operation (missing heartbeats)
        immediately before the 'archived_at' timestamp.
        """
        try:
            query = """
                SELECT timestamp FROM bot_heartbeat
                WHERE timestamp < $1
                ORDER BY timestamp DESC
                LIMIT 1;
            """
            # Ensure self.pool is the correct way to get a connection
            # This might be self.db_pool or similar depending on your class structure
            async with self.pool.acquire() as conn:
                last_heartbeat_record = await conn.fetchrow(query, archived_at)

            if not last_heartbeat_record:
                # No heartbeats recorded before this token's archival.
                # Check if any heartbeats exist at all to distinguish a new bot from a long-dead one.
                async with self.pool.acquire() as conn: # Re-acquire if needed, or use existing conn if scope allows
                    first_ever_heartbeat = await conn.fetchval("SELECT MIN(timestamp) FROM bot_heartbeat")
                
                if first_ever_heartbeat and first_ever_heartbeat < archived_at:
                    # Heartbeats exist in the table, but none before the current archival time.
                    # This implies the bot was down for the entire period leading up to 'archived_at'.
                    logger.warning(f"No heartbeats found before {archived_at}, but older heartbeats exist. Gap detected.")
                    return True
                elif not first_ever_heartbeat:
                    logger.info(f"No heartbeats found in bot_heartbeat table. Cannot determine gap for token archived at {archived_at}. Assuming no gap for safety.")
                    return False # Cannot determine, conservatively assume no gap.
                else: # Should not happen if archived_at is current time and heartbeats exist after.
                    logger.debug(f"First heartbeat {first_ever_heartbeat} is after {archived_at}. No gap determined.")
                    return False

            last_heartbeat_ts = last_heartbeat_record['timestamp']
            # Ensure archived_at is offset-aware if last_heartbeat_ts is, or vice-versa.
            # If one is naive and the other is aware, comparison will raise an error.
            # Assuming both are consistently offset-aware (e.g., UTC from TIMESTAMPTZ).
            time_since_last_heartbeat_seconds = (archived_at - last_heartbeat_ts).total_seconds()

            logger.debug(f"Token archived_at: {archived_at}, Last heartbeat: {last_heartbeat_ts}, "
                        f"Duration since last heartbeat: {time_since_last_heartbeat_seconds:.2f}s, "
                        f"Gap threshold: {gap_detection_threshold_seconds}s")

            if time_since_last_heartbeat_seconds > gap_detection_threshold_seconds:
                logger.info(f"Data gap detected: Last heartbeat was {time_since_last_heartbeat_seconds:.2f}s ago "
                            f"(threshold: {gap_detection_threshold_seconds}s). Token lifecycle likely interrupted.")
                return True
            
            logger.debug("No significant pre-archival data gap detected based on heartbeats.")
            return False

        except Exception as e:
            logger.error(f"Error in check_for_data_gap_on_restart: {e}", exc_info=True)
            return False # Fail safe

    async def check_for_data_gap(self, token_start_time: datetime, token_end_time: datetime, gap_threshold_seconds: int = 300) -> bool:
        """
        Checks for significant data gaps in bot_heartbeat table during the token's active period.
        A gap is significant if the time between two consecutive heartbeats exceeds gap_threshold_seconds.
        """
        last_hb_before_token_end = await self.get_last_heartbeat_before(token_end_time)
        first_hb_after_token_start = await self.get_first_heartbeat_after(token_start_time)

        if not last_hb_before_token_end or not first_hb_after_token_start:
            # If no heartbeats surround the token's activity, assume a potential gap (conservative approach)
            # This might happen if the token's entire lifecycle was during a bot downtime.
            logger.warning(f"Heartbeat data missing around token activity ({token_start_time} - {token_end_time}). Assuming potential data gap.")
            return True

        # Check gap between the heartbeat just before the token died (or script stopped)
        # and the heartbeat just after the script restarted (which would be after the token_start_time if it was an existing token)

        # Scenario 1: Gap *during* the token's recorded lifecycle
        # This requires iterating heartbeats within the token_start_time and token_end_time,
        # but a simpler proxy is to check the continuity around the point of potential script failure.

        # Let's refine: We are interested if the bot was down for a period that *ended*
        # shortly before token_end_time (when it was marked dead).
        # And this downtime started *after* token_start_time.

        query_heartbeats_in_range = """
            SELECT timestamp FROM bot_heartbeat
            WHERE timestamp >= $1 AND timestamp <= $2
            ORDER BY timestamp ASC;
        """
        async with self.pool.acquire() as conn:
            heartbeats = await conn.fetch(query_heartbeats_in_range, token_start_time, token_end_time)

        if not heartbeats: # No heartbeats during the token's entire active period
            logger.debug(f"No bot heartbeats found during token {token_start_time} - {token_end_time} lifecycle. Likely a gap.")
            return True

        previous_hb_ts = None
        for record in heartbeats:
            current_hb_ts = record['timestamp']
            if previous_hb_ts:
                if (current_hb_ts - previous_hb_ts).total_seconds() > gap_threshold_seconds:
                    logger.info(f"Data gap detected for token: {previous_hb_ts} to {current_hb_ts} ({(current_hb_ts - previous_hb_ts).total_seconds()}s)")
                    return True
            previous_hb_ts = current_hb_ts

        # Also check the gap between the last known heartbeat *before* the token ended its lifecycle
        # and the token's end time. This covers the case where the bot stopped *while* this token was live.
        if previous_hb_ts and (token_end_time - previous_hb_ts).total_seconds() > gap_threshold_seconds:
            logger.info(f"Data gap detected leading up to token end: last heartbeat at {previous_hb_ts}, token ended at {token_end_time}")
            return True

        return False
    
    async def set_token_cooldown(self, mint: str, cooldown_minutes: int):
        """Sets a cooldown period on a token to prevent immediate re-buys."""
        if cooldown_minutes <= 0:
            return # No cooldown to set

        cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes)
        query = "UPDATE tokens SET cooldown_until = $1 WHERE mint = $2"
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, cooldown_until, mint)
            logger.info(f"Token {mint} is on a re-buy cooldown until {cooldown_until.strftime('%Y-%m-%d %H:%M:%S')} UTC.")
        except Exception as e:
            logger.error(f"Failed to set cooldown for token {mint}: {e}", exc_info=True)

    async def is_token_active_in_db(self, mint: str, conn=None) -> bool:
        """
        Checks if a token exists in the primary 'tokens' table (i.e., it has not been backed up).
        Returns True if the token exists, False otherwise.
        """
        query = "SELECT 1 FROM tokens WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            result = await connection.fetchval(query, mint)
            return result is not None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def mark_token_as_migrated(self, mint: str, conn=None):
        """Updates the data_source for a token to 'DEXSCREENER'."""
        logger.info(f"🚩 Flagging token {mint} as migrated. Switching data source to DEXScreener.")
        query = "UPDATE tokens SET data_source = 'DEXSCREENER' WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, mint)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def cleanup_db(self, cleanup_flag: bool):
        """Drop all application tables if cleanup_flag is True."""
        if cleanup_flag:
            logger.warning("🚨 Starting full database cleanup - Dropping all application tables...")
            async with self.pool.acquire() as conn:
                # List all known application tables (main and backup)
                # Add any other tables managed by the application if necessary (e.g., creator_wallets)
                tables_to_drop = [
                    'configurations',     # Add the new table
                    'portfolio',
                    'rugcheck',           # Depends on tokens
                    'trades',             # No explicit FK, but related to tokens
                    'migrations',         # Standalone or related? Assuming standalone for drop order
                    'tokens',             # Drop after dependents
                    'portfolio_backup',          
                    'rugcheck_backup',
                    'trades_backup',
                    'migrations_backup',
                    'tokens_backup'
                ]
                # Drop tables in an order that respects potential dependencies, or use CASCADE
                # Using DROP TABLE IF EXISTS ... CASCADE is generally safer
                for table in tables_to_drop:
                    try:
                        # Use CASCADE to handle potential foreign key dependencies automatically
                        await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                        logger.info(f"🗑️ Dropped table {table}")
                    except Exception as e:
                        # Log error but continue trying to drop other tables
                        logger.error(f"Error dropping table {table}: {e}", exc_info=False) # Keep log concise

            logger.warning("✅ Full database cleanup finished.")

    async def backup_db(self, backup_flag: bool):
        """Backup tables based on backup_flag."""
        if backup_flag:
            async with self.pool.acquire() as conn:
                try:
                    tables_to_backup = [
                        'tokens', 'trades', 'rugcheck', 'migrations', 'portfolio'
                    ]
                    for table in tables_to_backup:
                        logger.info("🗄️ Backing up table %s", table)

                        if table == 'tokens':
                            # Handle the 'tokens' table as a special case with explicit columns
                            await conn.execute("""
                                INSERT INTO tokens_backup (
                                    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey,
                                    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri,
                                    website, telegram, twitter, socials_score, socials_last_checked,
                                    sol_price_usd, is_active, last_trade, timestamp,
                                    cooldown_until,
                                    backup_reason, backup_timestamp
                                )
                                SELECT
                                    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey,
                                    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri,
                                    website, telegram, twitter, socials_score, socials_last_checked,
                                    sol_price_usd, is_active, last_trade, timestamp,
                                    cooldown_until,
                                    'manual_backup', NOW()
                                FROM tokens
                                ON CONFLICT (mint) DO NOTHING;
                            """)
                        else:
                            # Original logic for other tables (assuming their backup tables have identical columns)
                            # NOTE: This generic logic is still fragile. Explicit columns are always better.
                            conflict_key_map = {
                                'trades': 'signature',
                                'rugcheck': 'mint',
                                'migrations': 'signature',
                                'portfolio': 'id'
                            }
                            conflict_key = conflict_key_map.get(table)
                            if conflict_key:
                                await conn.execute(f"INSERT INTO {table}_backup SELECT * FROM {table} ON CONFLICT ({conflict_key}) DO NOTHING;")
                            else:
                                logger.warning(f"No conflict key defined for table '{table}' in backup_db. Skipping backup.")
                                continue

                        logger.info("🧹 Truncating table %s", table)
                        await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")

                except Exception as e:
                    logger.exception("Error during database backup: %s", e)
                    raise

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            logger.info("Closing database connection pool...")
            await self.pool.close()
            logger.info("Database connection pool closed.")

    async def get_token_lifespan(self, mint: str) -> Optional[Dict[str, datetime]]:
        """
        Fetches the approximate start and end timestamp of a token's activity
        based on its first and last trade records in the v_trades view.

        Args:
            mint: The mint address of the token.

        Returns:
            A dictionary {'start_ts': datetime, 'end_ts': datetime} if trades exist,
            otherwise None. Timestamps are timezone-aware (UTC).
        """
        if not self.pool:
            logger.error("Database pool not initialized.")
            return None

        query = """
            SELECT
                MIN(timestamp) as first_trade_ts,
                MAX(timestamp) as last_trade_ts
            FROM v_unified_market_ticks_historical
            WHERE mint = $1;
        """
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(query, mint)
                if row and row['first_trade_ts'] and row['last_trade_ts']:
                    # Ensure timestamps are timezone-aware UTC
                    start_ts = row['first_trade_ts'].replace(tzinfo=timezone.utc) if row['first_trade_ts'].tzinfo is None else row['first_trade_ts'].astimezone(timezone.utc)
                    end_ts = row['last_trade_ts'].replace(tzinfo=timezone.utc) if row['last_trade_ts'].tzinfo is None else row['last_trade_ts'].astimezone(timezone.utc)
                    return {'start_ts': start_ts, 'end_ts': end_ts}
                else:
                    logger.warning(f"No trade timestamps found for mint {mint} to determine lifespan.")
                    return None
            except Exception as e:
                logger.error(f"Error fetching token lifespan for {mint}: {e}", exc_info=True)
                return None

    def ohlcv_sql_like(self, df_group: pd.DataFrame) -> pd.Series:
        df = df_group 
        if df.empty:
            return pd.Series({
                'Open': np.nan, 'High': np.nan, 'Low': np.nan, 'Close': np.nan,
                'Volume': 0.0,
                'market_cap_calculated': np.nan, 
                'marketCapSol': np.nan,          
                'volatility': 0.0
            })

        last_rolling_volume = df['rolling_volume_sql'].iloc[-1] if 'rolling_volume_sql' in df.columns and not df['rolling_volume_sql'].empty else 0.0
        last_rolling_volatility = df['rolling_volatility_sql'].iloc[-1] if 'rolling_volatility_sql' in df.columns and not df['rolling_volatility_sql'].empty else 0.0
        
        last_market_cap_usd = df['market_cap_calculated'].iloc[-1] if 'market_cap_calculated' in df.columns and not df['market_cap_calculated'].isnull().all() else np.nan
        last_market_cap_sol_live = df['marketcapsol'].iloc[-1] if 'marketcapsol' in df.columns and not df['marketcapsol'].empty and pd.notna(df['marketcapsol'].iloc[-1]) else np.nan

        return pd.Series({
            'Open': df['price'].iloc[0] if 'price' in df.columns and not df['price'].empty else np.nan,
            'High': df['price'].max() if 'price' in df.columns and not df['price'].empty else np.nan,
            'Low': df['price'].min() if 'price' in df.columns and not df['price'].empty else np.nan,
            'Close': df['price'].iloc[-1] if 'price' in df.columns and not df['price'].empty else np.nan,
            'Volume': last_rolling_volume,
            'market_cap_calculated': last_market_cap_usd,
            'marketCapSol': last_market_cap_sol_live, 
            'volatility': last_rolling_volatility
        })

    async def get_historical_data_for_backtesting(
        self,
        mints: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> Dict[str, pd.DataFrame]:
        """
        [MODIFIED] Fetches historical OHLCV data for a list of mints.
        The date range is now optional. If start_date and end_date are None,
        it fetches the complete history for the given mints.
        """
        if not mints:
            logger.warning("get_historical_data_for_backtesting called with empty mints list.")
            return {}
        if not self.pool:
            logger.error("Database pool not initialized.")
            return {}

        # Ensure dates are UTC if provided
        start_date_utc = start_date.astimezone(timezone.utc) if start_date and start_date.tzinfo else start_date
        end_date_utc = end_date.astimezone(timezone.utc) if end_date and end_date.tzinfo else end_date

        # --- Build Trade Query with Optional Date Filters ---
        trade_query_parts = [
            "SELECT mint, timestamp, price_sol AS price, volume_usd AS volume,",
            "market_cap_usd AS market_cap_calculated, market_cap_sol AS live_market_cap_sol",
            "FROM v_unified_market_ticks_historical",
            "WHERE mint = ANY($1::text[]) AND price_sol > 0"
        ]
        trade_params = [mints]
        if start_date_utc:
            trade_params.append(start_date_utc)
            trade_query_parts.append(f"AND timestamp >= ${len(trade_params)}")
        if end_date_utc:
            trade_params.append(end_date_utc)
            trade_query_parts.append(f"AND timestamp < ${len(trade_params)}")
        trade_query_parts.append("ORDER BY mint, timestamp;")
        trade_query = " ".join(trade_query_parts)

        # --- Build Rugcheck Query with Optional Date Filters ---
        rugcheck_query_parts = [
            "WITH RankedRugcheck AS (",
            "SELECT mint, last_checked AS timestamp, score AS rugcheck_score, ROW_NUMBER() OVER (PARTITION BY mint ORDER BY last_checked DESC) as rn",
            "FROM v_rugcheck WHERE mint = ANY($1::text[])"
        ]
        rugcheck_params = [mints]
        if end_date_utc:
            rugcheck_params.append(end_date_utc)
            rugcheck_query_parts.append(f"AND last_checked < ${len(rugcheck_params)}")
        rugcheck_query_parts.append(")")
        rugcheck_query_parts.append("SELECT mint, timestamp, rugcheck_score FROM RankedRugcheck WHERE rn = 1")
        if start_date_utc:
            rugcheck_params.append(start_date_utc)
            rugcheck_query_parts.append(f"OR timestamp >= ${len(rugcheck_params)}")
        rugcheck_query = " ".join(rugcheck_query_parts) + ";"

        # --- Token Info Query (no date filter needed) ---
        token_info_query = """
            WITH TokenCreationData AS (
                SELECT
                    mint, socials_score, timestamp AS token_creation_time,
                    marketCapSol AS creation_init_market_cap_sol,
                    cooldown_until,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp ASC) as rn
                FROM v_tokens vt WHERE mint = ANY($1::text[])
            )
            SELECT mint, token_creation_time, socials_score, creation_init_market_cap_sol, cooldown_until
            FROM TokenCreationData WHERE rn = 1;
        """

        results_dict = {}
        async with self.pool.acquire() as conn:
            try:
                # --- Execute Queries ---
                trade_records_raw = await conn.fetch(trade_query, *trade_params)
                rugcheck_records_raw = await conn.fetch(rugcheck_query, *rugcheck_params)
                token_info_records_raw = await conn.fetch(token_info_query, mints)

                if not trade_records_raw:
                    logger.warning("No trade records found for the specified mints and period.")
                    return {}

                # --- Process Data (same logic as before) ---
                trade_records_list_of_dicts = [dict(rec) for rec in trade_records_raw]
                trades_df = pd.DataFrame(trade_records_list_of_dicts)
                
                trades_df.columns = [str(col).lower() for col in trades_df.columns]
                
                trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], errors='coerce', utc=True)
                trades_df.dropna(subset=['timestamp'], inplace=True)
                
                numeric_cols_from_trades = ['price', 'volume', 'market_cap_calculated', 'live_market_cap_sol']
                for col in numeric_cols_from_trades:
                    if col in trades_df.columns:
                        trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
                    else:
                        logger.error(f"Critical: Column '{col}' expected from trades query but missing. DataFrame columns: {list(trades_df.columns)}")
                        trades_df[col] = 0.0
                trades_df.dropna(subset=['price', 'volume'], inplace=True)

                all_processed_trades = []
                time_interval_minutes = self.config.get('DEFAULT_TIME_INTERVAL', 10)
                window_duration = f"{time_interval_minutes}min"

                for mint_name, mint_df_group in trades_df.groupby('mint'):
                    mint_df = mint_df_group.sort_values('timestamp').copy()
                    mint_df_indexed = mint_df.set_index('timestamp')
                    mint_df['rolling_volume_sql'] = mint_df_indexed['volume'].rolling(window_duration, closed='left').sum().fillna(0.0).values
                    
                    if 'live_market_cap_sol' in mint_df.columns:
                        mint_df.rename(columns={'live_market_cap_sol': 'marketcapsol'}, inplace=True)

                    prices_series = mint_df['price']
                    if len(prices_series) > 1:
                        log_returns = np.log(prices_series / prices_series.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
                        rolling_obj = log_returns.set_axis(mint_df['timestamp']).rolling(window_duration, closed='left')
                        rolling_std = rolling_obj.std().fillna(0.0)
                        rolling_count = rolling_obj.count().fillna(0.0)
                        volatility_sql = rolling_std.astype(float) * np.sqrt(np.maximum(rolling_count.astype(float), 1.0))
                        mint_df['rolling_volatility_sql'] = volatility_sql.where(rolling_count > 5, 0.0).values
                    else:
                        mint_df['rolling_volatility_sql'] = 0.0
                    mint_df['rolling_volatility_sql'] = mint_df['rolling_volatility_sql'].fillna(0.0)
                    all_processed_trades.append(mint_df)

                if not all_processed_trades: return {}
                processed_trades_df = pd.concat(all_processed_trades)

                ohlcv_df = processed_trades_df.groupby(['mint', pd.Grouper(key='timestamp', freq='5s')])\
                                            .apply(self.ohlcv_sql_like).reset_index()
                
                ohlcv_df.dropna(subset=['mint', 'timestamp'], inplace=True)
                ohlc_cols = ['Open', 'High', 'Low', 'Close']
                ohlcv_df[ohlc_cols] = ohlcv_df.groupby('mint')[ohlc_cols].ffill().bfill().fillna(0.0)
                
                cols_to_fill_ohlcv = ['Volume', 'volatility', 'market_cap_calculated', 'marketCapSol']
                for col in cols_to_fill_ohlcv:
                    if col in ohlcv_df.columns: ohlcv_df[col] = ohlcv_df[col].fillna(0.0)
                    else: ohlcv_df[col] = 0.0
                
                ohlcv_df = ohlcv_df.set_index('timestamp')
                if ohlcv_df.index.has_duplicates: ohlcv_df = ohlcv_df.loc[~ohlcv_df.index.duplicated(keep='last')]
                
                resampled_ohlcv_list = []
                for mint_name, group_df in ohlcv_df.groupby('mint'):
                    if group_df.index.has_duplicates: 
                        group_df = group_df.loc[~group_df.index.duplicated(keep='last')]
                    
                    min_ts, max_ts = group_df.index.min(), group_df.index.max()
                    if pd.isna(min_ts) or pd.isna(max_ts): 
                        logger.warning(f"Skipping mint {mint_name} due to NaT in min/max timestamp for reindexing.")
                        continue
                        
                    full_range = pd.date_range(start=min_ts, end=max_ts, freq='5s', tz='UTC')
                    group_reindexed = group_df.reindex(full_range)

                    cols_to_interpolate = [
                        'Open', 'High', 'Low', 'Close', 'Volume',
                        'market_cap_calculated', 'marketCapSol', 'volatility'
                    ]
                    
                    for col in cols_to_interpolate:
                        if col in group_reindexed.columns:
                            group_reindexed[col] = pd.to_numeric(group_reindexed[col], errors='coerce').interpolate(method='time')

                    group_resampled = group_reindexed
                    group_resampled['mint'] = mint_name
                    resampled_ohlcv_list.append(group_resampled)

                if not resampled_ohlcv_list: 
                    logger.warning("No data after resampling for any mints.")
                    return {}
                
                resampled_ohlcv_df = pd.concat(resampled_ohlcv_list)
                if resampled_ohlcv_df.index.name != 'timestamp': resampled_ohlcv_df.index.name = 'timestamp'

                if rugcheck_records_raw:
                    rugcheck_list_of_dicts = [dict(rec) for rec in rugcheck_records_raw]
                    rugcheck_df = pd.DataFrame(rugcheck_list_of_dicts)
                    rugcheck_df.columns = [str(col).lower() for col in rugcheck_df.columns]
                    if 'timestamp' in rugcheck_df.columns:
                        rugcheck_df['timestamp'] = pd.to_datetime(rugcheck_df['timestamp'], errors='coerce', utc=True)
                        rugcheck_df.dropna(subset=['timestamp'], inplace=True)
                        rugcheck_df = rugcheck_df.sort_values(['mint', 'timestamp']).drop_duplicates(subset=['mint', 'timestamp'], keep='last')
                        rugcheck_df.set_index('timestamp', inplace=True)
                        rugcheck_df['rugcheck_score'] = pd.to_numeric(rugcheck_df.get('rugcheck_score'), errors='coerce')
                        rugcheck_df = rugcheck_df[['mint', 'rugcheck_score']]
                    else:
                        logger.warning("Rugcheck data missing 'timestamp' column.")
                        rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))
                else:
                    rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))

                token_info_map = {}
                if token_info_records_raw:
                    for r_rec in token_info_records_raw:
                        r_dict = dict(r_rec)
                        mint_val = r_dict.get('mint')
                        creation_time_val = r_dict.get('token_creation_time')
                        socials_val = r_dict.get('socials_score')
                        creation_mc_sol_val = r_dict.get('creation_init_market_cap_sol')
                        cooldown_until_val = r_dict.get('cooldown_until')

                        creation_time = pd.to_datetime(creation_time_val, errors='coerce', utc=True)
                        socials = pd.to_numeric(socials_val, errors='coerce')
                        creation_mc_sol = pd.to_numeric(creation_mc_sol_val, errors='coerce')
                        cooldown_until_ts = pd.to_datetime(cooldown_until_val, errors='coerce', utc=True)

                        if mint_val and pd.notna(creation_time):
                            token_info_map[mint_val] = {'creation_time': creation_time, 
                                                        'socials_score': socials, 
                                                        'creation_init_market_cap_sol': creation_mc_sol,
                                                        'cooldown_until': cooldown_until_ts
                                                        }
                
                required_final_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'creation_init_market_cap_sol', 'volatility', 'rugcheck_score', 'socials_score', 'token_creation_time', 'cooldown_until']
                
                grouped_ohlcv = resampled_ohlcv_df.groupby('mint')
                for mint_name in grouped_ohlcv.groups:
                    mint_ohlcv_group = grouped_ohlcv.get_group(mint_name)
                    cols_to_select_from_ohlcv = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'volatility']
                    existing_cols_in_group = [col for col in cols_to_select_from_ohlcv if col in mint_ohlcv_group.columns]
                    if not all(c in existing_cols_in_group for c in ['market_cap_calculated', 'marketCapSol']):
                        logger.warning(f"Mint {mint_name} group missing essential live market cap columns. Columns present: {list(mint_ohlcv_group.columns)}. Skipping.")
                        continue
                    combined_df = mint_ohlcv_group[existing_cols_in_group].copy()

                    mint_rugcheck_data = rugcheck_df[rugcheck_df['mint'] == mint_name][['rugcheck_score']] if not rugcheck_df.empty else None
                    if mint_rugcheck_data is not None and not mint_rugcheck_data.empty:
                        combined_df = combined_df.sort_index()
                        mint_rugcheck_data = mint_rugcheck_data.sort_index()
                        if mint_rugcheck_data.index.has_duplicates: mint_rugcheck_data = mint_rugcheck_data.loc[~mint_rugcheck_data.index.duplicated(keep='last')]
                        combined_df = pd.merge_asof(combined_df, mint_rugcheck_data, left_index=True, right_index=True, direction='backward', tolerance=pd.Timedelta('1d'))
                    else: combined_df['rugcheck_score'] = np.nan

                    mint_specific_info = token_info_map.get(mint_name)
                    if mint_specific_info:
                        combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'], combined_df['cooldown_until'] = mint_specific_info['creation_time'], mint_specific_info['socials_score'], mint_specific_info.get('creation_init_market_cap_sol', np.nan), mint_specific_info.get('cooldown_until', pd.NaT)
                    else:
                        combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'], combined_df['cooldown_until'] = pd.NaT, 100, np.nan, pd.NaT
                    
                    for r_col in required_final_cols:
                        if r_col not in combined_df.columns: combined_df[r_col] = np.nan 

                    for col in ['rugcheck_score', 'socials_score', 'token_creation_time', 'creation_init_market_cap_sol', 'cooldown_until']: combined_df[col] = combined_df[col].ffill().bfill()
                    
                    combined_df['rugcheck_score'] = combined_df['rugcheck_score'].fillna(10000).astype(int)
                    combined_df['socials_score'] = combined_df['socials_score'].fillna(100).astype(int)
                    combined_df['creation_init_market_cap_sol'] = pd.to_numeric(combined_df['creation_init_market_cap_sol'], errors='coerce').fillna(0.0)
                    combined_df['cooldown_until'] = pd.to_datetime(combined_df['cooldown_until'], errors='coerce', utc=True) 

                    for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'volatility']:
                        combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0.0)
                    
                    final_df = combined_df.copy()
                    # If dates were provided, filter the final combined data at the end
                    if start_date_utc:
                        final_df = final_df[final_df.index >= start_date_utc]
                    if end_date_utc:
                        final_df = final_df[final_df.index < end_date_utc]

                    if not final_df.empty and all(col in final_df.columns for col in required_final_cols):
                        astype_dict = {
                            'Open': float, 'High': float, 'Low': float, 'Close': float, 
                            'Volume': float, 'market_cap_calculated': float, 
                            'marketCapSol': float, 'creation_init_market_cap_sol': float, 
                            'volatility': float, 'rugcheck_score': int, 'socials_score': int
                        }
                        cols_for_astype = [col for col in required_final_cols if col in astype_dict]
                        final_df[cols_for_astype] = final_df[cols_for_astype].astype(astype_dict)
                        
                        final_df.index = pd.to_datetime(final_df.index, utc=True)
                        results_dict[mint_name] = final_df[required_final_cols]
                    else:
                        logger.warning(f"No valid data or missing columns for {mint_name} after final processing. Skipping.")
            
            except Exception as e:
                logger.error(f"Error processing historical data ({type(e).__name__}): {e}", exc_info=True)
                return {}

        return results_dict

# Helper function moved outside class for potential reuse (optional)
async def get_token_lifespan(db_client: DatabaseClient, mint: str) -> Optional[Dict[str, datetime]]:
    """
    Fetches the approximate start and end timestamp of a token's activity
    based on its first and last trade records in the v_trades view.
    """
    if not db_client or not db_client.pool:
        logger.error("Database client not initialized or connected for get_token_lifespan.")
        return None

    query = """
        SELECT
            MIN(timestamp) as first_trade_ts,
            MAX(timestamp) as last_trade_ts
        FROM v_trades
        WHERE mint = $1;
    """
    async with db_client.pool.acquire() as conn:
        try:
            row = await conn.fetchrow(query, mint)
            if row and row['first_trade_ts'] and row['last_trade_ts']:
                start_ts = row['first_trade_ts'].replace(tzinfo=timezone.utc) if row['first_trade_ts'].tzinfo is None else row['first_trade_ts'].astimezone(timezone.utc)
                end_ts = row['last_trade_ts'].replace(tzinfo=timezone.utc) if row['last_trade_ts'].tzinfo is None else row['last_trade_ts'].astimezone(timezone.utc)
                end_ts += timedelta(seconds=1) # Add buffer
                return {'start_ts': start_ts, 'end_ts': end_ts}
            else:
                logger.warning(f"No trade timestamps found for mint {mint} to determine lifespan.")
                return None
        except Exception as e:
            logger.error(f"Error fetching token lifespan for {mint}: {e}", exc_info=True)
            return None

```

---

### 📄 rl_config.py

```python
# FILE: rl_config.py (Added Death Penalty)

"""
Configuration for the Reinforcement Learning (RL) agent and environment.

Defines the structure of the observation and action spaces, reward function
components, hyperparameters for the RL algorithm, training settings,
and data configurations.
"""

from datetime import datetime, timezone
import numpy as np
from typing import List, Dict, Any, Tuple, Union

# --- General Configuration ---
# NOTE: THESE DATES ARE EXAMPLES - ADJUST TO YOUR ACTUAL DATA RANGE
# Use the same extended range as GA for consistency?
RL_HISTORICAL_DATA_START_TS: datetime = datetime(2025, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
RL_HISTORICAL_DATA_END_TS: datetime = datetime(2025, 7, 13, 23, 59, 0, tzinfo=timezone.utc)

# --- Environment Configuration ---
DATA_SET_KEY_TRAIN: str = 'train'       # Data used for agent training episodes.
DATA_SET_KEY_EVAL: str = 'validation'   # Data used for periodic evaluation during training.

RL_INITIAL_CAPITAL: float = 100.0 # In SOL

# Max steps based on typical token lifespan (e.g., 4 hours * 12 steps/min * 60 min/hr = 2880 steps if 5s candles)
# Let's set a reasonable upper bound, actual episodes will be truncated by data end.
# MAX_STEPS_PER_EPISODE: int = 2880 # Max simulation steps if token lives unusually long
# --- START: Modified MAX_STEPS_PER_EPISODE ---
# This value is now calculated dynamically in rl_trainer.py based on the
# percentile of token lifespans in the training dataset.
# A fallback value can be set here if the calculation fails.
MAX_STEPS_PER_EPISODE: Union[int, None] = None # Set to None to indicate dynamic calculation
MAX_STEPS_PERCENTILE: float = 95.0 # The percentile of token lifespans to use as the max step limit.
# --- END: Modified MAX_STEPS_PER_EPISODE ---

# --- Observation Space Configuration ---
# Features observed at each step. Normalization is crucial.
OBSERVATION_PRICE_HISTORY_LENGTH: int = 15 # Steps of price history for features like log returns

OBSERVATION_FEATURES: List[str] = [
    # Price Change Features (Normalized Log Returns)
    'price_change_1',  # Log return over 1 step (~5s)
    'price_change_5',  # Log return over 5 steps (~25s)
    'price_change_10', # Log return over 10 steps (~50s)

    # Market Indicators (Normalized)
    'volatility',           # Rolling volatility (e.g., normalized 0-1)
    'live_market_cap_sol_norm',  # Normalized LIVE SOL market cap
    'live_market_cap_usd_norm',  # Normalized LIVE USD market cap
    'volume_sol_norm',      # Trade volume in SOL (e.g., log-normalized)
    'rugcheck_score_norm',  # RugCheck score (normalized 0-1, where 1=low risk)
    'socials_score_norm',   # Socials score (normalized 0-1, where 1=low risk)
    'time_since_creation_norm', # Time since token creation (normalized 0-1)

    # Portfolio State Features (Normalized)
    'is_holding',           # Binary flag (0 or 1)
    'position_pnl_norm',    # Unrealized PnL of current position, normalized (-1 to N)
    'time_holding_norm',    # Time the current position has been held, normalized (0-1)
    'sol_balance_norm',     # Current SOL balance, normalized (0-1 relative to initial capital * factor)

    # Time Features (Normalized)
    'weekday',              # Day of the week (e.g., normalized 0-1 or one-hot)
    'daytime'               # Time of day (e.g., normalized 0-1 or cyclical)
]
OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)

# Note: Observation normalization is handled by Stable Baselines3's VecNormalize.
# The bounds defined here are the *expected* range after normalization,
# but the Box space itself is defined by the shape only.
OBSERVATION_LOW: float = -np.inf 
OBSERVATION_HIGH: float = np.inf 

# --- Action Space Configuration (Continuous Parameter Tuning) ---
# Parameters controlled by the RL agent.
# Format: (parameter_name, low_bound, high_bound, type)
RL_TUNABLE_PARAMETERS: List[Tuple[str, float, float, type]] = [
    # Sell-side parameters
    ('INITIAL_STOP_LOSS_PERCENT', 5.0, 70.0, float),
    ('FIRST_SELL_PERCENT', 20.0, 100.0, float),
    ('TRAILING_STOP_LOSS_PERCENT', 5.0, 50.0, float),
    ('FIRST_SELL_PROFIT_MARGIN', 10.0, 200.0, float),
    ('SECOND_TAKE_PROFIT_PERCENT', 100.0, 1000.0, float),
    
    # Buy condition thresholds
    ('DEFAULT_VOLUME_THRESHOLD', 1000, 50000, int),
    ('DEFAULT_MARKETCAP_THRESHOLD', 10000, 100000, int),
    ('MIN_VOLATILITY', 0.01, 3.0, float),
    ('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 1, 1002, int),
    ('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100, 100, int),
    ('SOL_TO_BUY', 0.1, 0.5, float),
    
    # Emergency & Re-buy parameters
    ('MC_DROP_THRESHOLD_RL', 1.0, 20.0, float),
    ('USE_TREND_REVERSAL_CONFIRMATION', 0.0, 1.0, float),
    ('STOP_LOSS_COOLDOWN_MINUTES', 0.0, 60.0, int),
    
    # PUMP.FUN Trend Reversal Parameters
    ('TREND_REVERSAL_RECENCY_HOURS', 0.25, 12.0, int),
    ('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 30.0, 60.0, float),
    ('INDICATOR_LOOKBACK_HOURS', 0.25, 6.0, int),
    ('RSI_PERIOD', 4.0, 50.0, int),
    ('BBANDS_PERIOD', 10.0, 30.0, int),
    ('BBANDS_STD_DEV', 1.0, 2.5, float),
    ('FAST_EMA_PERIOD', 5.0, 20.0, int),
    ('SLOW_EMA_PERIOD', 15.0, 80.0, int),

    # [NEW] DEXSCREENER Trend Reversal Parameters
    ('DEX_REVERSAL_LOOKBACK_MINUTES', 15.0, 60.0, int),
    ('DEX_REVERSAL_MIN_SNAPSHOTS', 3.0, 10.0, int),
    ('DEX_REVERSAL_MIN_LIQUIDITY_USD', 1000.0, 10000.0, int),
    ('DEX_REVERSAL_MIN_BUY_SELL_RATIO', 1.1, 3.0, float),
    ('DEX_REVERSAL_MIN_CONFIRMATIONS', 1.0, 5.0, int),
]
ACTION_SPACE_DIM: int = len(RL_TUNABLE_PARAMETERS)

ACTION_LOW: np.ndarray = np.array([p[1] for p in RL_TUNABLE_PARAMETERS], dtype=np.float32)
ACTION_HIGH: np.ndarray = np.array([p[2] for p in RL_TUNABLE_PARAMETERS], dtype=np.float32)

# --- Reward Function Configuration ---
# Weights for different reward components. Tuning is critical.

# Primary Reward: Based on realized profit/loss from completed trades (sells).
REWARD_PNL_MULTIPLIER: float = 1.0 # Scale realized PnL

# Penalty for holding a position when the token dies (end of data).
# Make this substantial, e.g., equivalent to losing the initial investment.
REWARD_DEATH_PENALTY: float = -RL_INITIAL_CAPITAL * 0.5 # Example: Penalize half the initial capital

# Reward Shaping (Optional): Intermediate rewards/penalties.
REWARD_SL_HIT_PENALTY: float = -0.5 # Penalty for hitting initial or trailing stop loss
REWARD_TP_HIT_BONUS: float = 0.5  # Bonus for hitting first or second take profit (0.2)
REWARD_HOLDING_PENALTY: float = -0.001 # Small penalty per step while holding (discourages inaction)
# REWARD_UNREALIZED_PNL_CHANGE: float = 0.05 # Small bonus for increasing unrealized PnL (optional, can be noisy)

# --- Default Simulation Parameters (Fixed for RL Env) ---
# Non-optimized parameters used during simulation. Match main config where applicable.
DEFAULT_BUY_FEE: float = 0.001
DEFAULT_BUY_TIP: float = 0.001
DEFAULT_SELL_FEE: float = 0.001
DEFAULT_SELL_TIP: float = 0.001

MIN_MARKET_CAP_USD_FALLBACK: int = 4000

MIN_CANDLE_DATA_FOR_INDICATORS: int = 30
APPLY_TREND_REVERSAL_ON_SELL_REASONS = ["🛑 Stop Loss", "🆘 Emergency SL (MCap)", "↘️ Trailing SL", "🛡️ Breakeven SL", "manual_override"]

VOLATILITY_WINDOW: int = 120 # Window size (steps) for volatility calculation in env

# --- RL Agent & Training Configuration (Stable Baselines3) ---
RL_ALGORITHM: str = "PPO" # PPO is robust; SAC/TD3 are alternatives

# Policy network architecture. Adjust hidden layer sizes as needed.
POLICY_KWARGS: Dict[str, Any] = dict(net_arch=dict(pi=[128, 128], vf=[128, 128]))

# Total training timesteps. Needs significant increase for real training.
TOTAL_TIMESTEPS: int = 10_000_000 # Increase for more thorough training (e.g., 1M+)

# Number of parallel environments. Adjust based on CPU cores.
N_ENVS: int = 8 # Example: Use 8 parallel environments if CPU allows

TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/"
MODEL_SAVE_DIR: str = "./rl_trained_models/"

# Evaluation frequency (in total agent steps across all envs).
EVAL_FREQ: int = 50000 # Evaluate every 50k total steps

# Number of episodes for each evaluation run.
N_EVAL_EPISODES: int = 60 # More episodes for better evaluation stability

# Checkpoint saving frequency (in total agent steps).
CHECKPOINT_FREQ: int = 100000 # Save every 100k total steps

# --- Data Settings ---
# Same split as GA for consistency when reusing load_and_split_data
DATA_SPLIT_RL: Dict[str, float] = {
    "training": 0.6,
    "validation": 0.2,
    "test": 0.2
}

# --- Live Agent Configuration (for deployment) ---
# How often the live bot queries the trained agent for new parameters (seconds).
AGENT_ACTION_INTERVAL_SECONDS: int = 15 # Update parameters every minute
```

---

### 📄 rl_environment.py

```python
# FILE: rl_environment.py (OHLCV Adapted & Refinements)

"""
Custom Gymnasium Environment for Training a Solana Pump.fun Trading Bot RL Agent.

This environment simulates the trading process based on historical OHLCV data, including
handling for token death and applying appropriate rewards/penalties.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import random
from collections import deque
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import timezone, datetime, timedelta

# --- Project Modules ---
from bot_logger import logger
import rl_config # Import RL specific configurations
from utils import calculate_volatility, calculate_trend_indicators # Keep utility for potential recalculation

# --- Environment Class ---

class TradingEnv(gym.Env):
    """
    Custom Gymnasium Environment for Solana Pump Trading Simulation using OHLCV data.

    Action Space (Continuous):
        Box space representing tunable trading parameters (rl_config.RL_TUNABLE_PARAMETERS).

    Observation Space (Continuous):
        Box space representing market state and portfolio status from OHLCV data, normalized
        (rl_config.OBSERVATION_FEATURES).

    Reward:
        Combination of realized PnL, shaping rewards/penalties, and death penalty.
    """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}

    def __init__(
        self,
        historical_data_dict: Dict[str, pd.DataFrame], # Expects OHLCV data per mint
        token_lifespans: Dict[str, Dict[str, datetime]],
        dexscreener_snapshot_data: Dict[str, pd.DataFrame],
        initial_capital: float = rl_config.RL_INITIAL_CAPITAL,
        max_steps: int = rl_config.MAX_STEPS_PER_EPISODE,
        render_mode: Optional[str] = None
    ):
        """
        Initializes the Trading Environment with OHLCV data.

        Args:
            historical_data_dict: Dictionary mapping mints to their historical 5s OHLCV DataFrames.
                                  Indices MUST be timezone-aware UTC DatetimeIndex.
                                  Expected columns: 'Open', 'High', 'Low', 'Close', 'Volume',
                                                    'market_cap_calculated', 'rugcheck_score', 'socials_score',
                                                    'token_creation_time'.
                                  Note: Assumes a fixed step interval (e.g., 5 seconds) based on data frequency.
            token_lifespans: Dictionary mapping mints to their {'start_ts', 'end_ts'} (UTC).
            initial_capital: Starting SOL balance for each episode.
            max_steps: Maximum number of steps allowed per episode (truncation).
        """
        super().__init__()

        if not historical_data_dict:
            raise ValueError("Historical OHLCV data dictionary cannot be empty.")
        if not token_lifespans:
             raise ValueError("Token lifespans dictionary cannot be empty.")

        # --- Validate and Store OHLCV Data ---
        self.historical_data_dict = {}
        self.token_lifespans = {}

        # These are the columns expected in the DataFrame for each mint
        required_cols = [
            'Open', 'High', 'Low', 'Close', 'Volume',
            'market_cap_calculated',     # Live USD MC
            'marketCapSol',              # Live SOL MC
            'creation_init_market_cap_sol', # Creation-time SOL MC
            'volatility', 'rugcheck_score', 'socials_score',
            'token_creation_time'
        ]

        for mint, df in historical_data_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty and isinstance(df.index, pd.DatetimeIndex):
                 if df.index.tz is None or str(df.index.tz).upper() != 'UTC':
                     logger.error(f"DataFrame index for mint {mint} is not timezone-aware UTC! Skipping.")
                     continue
                 if mint not in token_lifespans:
                      logger.warning(f"Lifespan info missing for mint {mint}. Skipping.")
                      continue
                 missing_cols_check = [col for col in required_cols if col not in df.columns]
                 if missing_cols_check:
                     logger.error(f"Missing required OHLCV columns in data for mint {mint}: {missing_cols_check}. Skipping.")
                     continue
                 if df[required_cols].isnull().values.any():
                      logger.warning(f"NaN values found in required columns for mint {mint}. Will attempt fill/clip later.")
                 self.historical_data_dict[mint] = df
                 self.token_lifespans[mint] = token_lifespans[mint]
            else:
                 logger.warning(f"Skipping invalid/empty DataFrame for mint: {mint}")

        # Store the snapshot data
        self.dexscreener_snapshot_data = dexscreener_snapshot_data

        self.available_mints = list(self.historical_data_dict.keys())
        if not self.available_mints:
            raise ValueError("No valid OHLCV DataFrames found after validation.")

        self.initial_capital = initial_capital
        self._max_episode_steps = max_steps

        self.action_space = spaces.Box(
            low=rl_config.ACTION_LOW,
            high=rl_config.ACTION_HIGH,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        self._action_param_names = [p[0] for p in rl_config.RL_TUNABLE_PARAMETERS]

        self.observation_space = spaces.Box(
            low=rl_config.OBSERVATION_LOW, # Using -np.inf
            high=rl_config.OBSERVATION_HIGH, # Using np.inf
            shape=(rl_config.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        self.current_step: int = 0
        self.current_sol: float = 0.0
        self.current_data_df: Optional[pd.DataFrame] = None
        self.current_mint: Optional[str] = None
        self.current_token_end_ts: Optional[datetime] = None
        self.initial_creation_market_cap_sol: Optional[float] = None # For MC drop %
        self.active_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {}
        self.last_observation: np.ndarray = np.zeros(self.observation_space.shape, dtype=np.float32)
        self._price_history: deque = deque(maxlen=rl_config.OBSERVATION_PRICE_HISTORY_LENGTH)
        self._previous_unrealized_pnl: float = 0.0
        self._last_step_processed_index = -1
        self.current_snapshot_df: Optional[pd.DataFrame] = None # Add state for current snapshot df

        logger.info(f"TradingEnv (OHLCV) initialized. Observation space dim: {rl_config.OBSERVATION_SPACE_DIM}, Action space dim: {rl_config.ACTION_SPACE_DIM}")


    def _get_observation(self) -> np.ndarray:
        default_obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        if self.current_data_df is None or self._last_step_processed_index < 0 or self._last_step_processed_index >= len(self.current_data_df):
            return default_obs
        try:
            current_row = self.current_data_df.iloc[self._last_step_processed_index]
            current_timestamp = self.current_data_df.index[self._last_step_processed_index]
        except IndexError: return default_obs

        current_price = current_row.get('Close', 0.0)
        self._price_history.append(float(current_price) if pd.notna(current_price) and isinstance(current_price, (int, float)) else (self._price_history[-1] if self._price_history else 0.0))

        try:
            live_usd_market_cap = float(current_row.get('market_cap_calculated', 0.0))
            live_sol_market_cap = float(current_row.get('marketCapSol', 0.0)) # Live SOL MC
            volume = float(current_row.get('Volume', 0.0))
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            creation_time_ts = current_row.get('token_creation_time', pd.NaT)
            volatility = float(current_row.get('volatility', 0.0))

            live_usd_market_cap = 0.0 if pd.isna(live_usd_market_cap) else live_usd_market_cap
            live_sol_market_cap = 0.0 if pd.isna(live_sol_market_cap) else live_sol_market_cap
            volume = 0.0 if pd.isna(volume) else volume
            rugcheck_score = 10000 if pd.isna(rugcheck_score) else int(rugcheck_score)
            socials_score = 100 if pd.isna(socials_score) else int(socials_score)
            volatility = 0.0 if pd.isna(volatility) else volatility

        except (KeyError, ValueError, TypeError) as e: return default_obs

        prices_arr = np.array(self._price_history, dtype=np.float32)
        safe_prices = prices_arr[prices_arr > 1e-12]
        price_change_1 = np.log(safe_prices[-1] / safe_prices[-2]) if len(safe_prices) >= 2 else 0.0
        price_change_5 = np.log(safe_prices[-1] / safe_prices[-6]) if len(safe_prices) >= 6 else 0.0
        price_change_10 = np.log(safe_prices[-1] / safe_prices[-11]) if len(safe_prices) >= 11 else 0.0

        time_since_creation_seconds = 0.0
        if pd.notna(creation_time_ts) and isinstance(current_timestamp, pd.Timestamp):
            ct_ts_aware = creation_time_ts.tz_localize('UTC') if creation_time_ts.tzinfo is None else creation_time_ts.astimezone(timezone.utc)
            time_diff = current_timestamp - ct_ts_aware
            time_since_creation_seconds = max(0.0, time_diff.total_seconds())

        is_holding = 1.0 if self.active_position else 0.0
        position_pnl_current_unrealized = 0.0
        time_holding_seconds = 0.0
        if self.active_position:
            buy_p = self.active_position['buy_price']
            rem_t = self.active_position['remaining_tokens']
            total_inv = self.active_position.get('total_investment_sol', 1.0)
            last_p = prices_arr[-1] if prices_arr.size > 0 else buy_p
            curr_val = last_p * rem_t
            init_t = self.active_position.get('initial_tokens', rem_t)
            cost_frac = rem_t / init_t if init_t > 0 else 1.0
            cost_basis_rem = total_inv * cost_frac
            position_pnl_current_unrealized = curr_val - cost_basis_rem
            entry_ts = self.active_position.get('entry_timestamp')
            if entry_ts: time_holding_seconds = max(0.0, (current_timestamp - entry_ts).total_seconds())
        
        weekday = float(current_timestamp.weekday())
        hour = float(current_timestamp.hour)

        # These are raw values; VecNormalize will handle scaling
        observation_list = [
            price_change_1, price_change_5, price_change_10,
            volatility,
            live_sol_market_cap,    # For 'live_market_cap_sol_norm'
            live_usd_market_cap,    # For 'live_market_cap_usd_norm'
            volume,
            float(rugcheck_score), 
            float(socials_score), 
            time_since_creation_seconds,
            is_holding, 
            position_pnl_current_unrealized, 
            time_holding_seconds, 
            self.current_sol,
            weekday, 
            hour
        ]
        
        observation = np.array(observation_list, dtype=np.float32)
        if not np.all(np.isfinite(observation)): observation = default_obs
        elif observation.shape != self.observation_space.shape: observation = default_obs
        
        self.last_observation = observation
        self._previous_unrealized_pnl = position_pnl_current_unrealized
        return observation

    def _apply_action(self, action: np.ndarray):
        new_params = {}
        clipped_action = np.clip(action, rl_config.ACTION_LOW, rl_config.ACTION_HIGH)
        for i, param_config in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            param_name, _, _, p_type = param_config
            val = clipped_action[i]
            if param_name == "USE_TREND_REVERSAL_CONFIRMATION":
                # Convert float action (0.0-1.0) to boolean for this parameter
                new_params[param_name] = bool(val > 0.5)
            else:
                new_params[param_name] = p_type(np.round(val)) if p_type == int else float(val)
        self.current_parameters = new_params

    def _run_trading_logic_step(self) -> Tuple[float, float]:
        """
        [REWRITTEN] Simulates one step of the trading logic using OHLCV data.
        This now includes the complete, source-aware trend reversal logic to match the backtester.
        Returns realized PnL and any shaping bonuses/penalties for the step.
        """
        realized_pnl_this_step = 0.0
        reward_bonus_penalty = 0.0

        current_data_index = self.current_step
        self._last_step_processed_index = current_data_index

        if self.current_data_df is None or current_data_index >= len(self.current_data_df):
            return realized_pnl_this_step, reward_bonus_penalty

        try:
            current_row = self.current_data_df.iloc[current_data_index]
            current_timestamp = self.current_data_df.index[current_data_index]
            
            price = float(current_row.get('Close', 0.0))
            volume_ohlcv = float(current_row.get('Volume', 0.0))
            high_price = float(current_row.get('High', 0.0))
            current_live_usd_mc = float(current_row.get('market_cap_calculated', 0.0))
            rugcheck_val = int(current_row.get('rugcheck_score', 10000))
            socials_val = int(current_row.get('socials_score', 100))
            volatility_val = float(current_row.get('volatility', 0.0))

            if price <= 1e-12:
                return realized_pnl_this_step, reward_bonus_penalty

            agent_params = self.current_parameters
            initial_sl_percent = agent_params.get('INITIAL_STOP_LOSS_PERCENT', 40.0)
            first_sell_percent = agent_params.get('FIRST_SELL_PERCENT', 35.0)
            trailing_sl_percent = agent_params.get('TRAILING_STOP_LOSS_PERCENT', 15.0)
            first_sell_profit_margin = agent_params.get('FIRST_SELL_PROFIT_MARGIN', 70.0)
            second_take_profit_percent = agent_params.get('SECOND_TAKE_PROFIT_PERCENT', 450.0)
            
            volume_thresh_usd = agent_params.get('DEFAULT_VOLUME_THRESHOLD', 40000)
            mcap_thresh_buy_usd = agent_params.get('DEFAULT_MARKETCAP_THRESHOLD', 20000)
            rug_thresh_agent = agent_params.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 401)
            social_thresh_agent = agent_params.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100)
            volatility_thresh_agent = agent_params.get('MIN_VOLATILITY', 0.18)
            buy_amount_sol_agent = agent_params.get('SOL_TO_BUY', 0.5)
            use_trend_reversal = agent_params.get('USE_TREND_REVERSAL_CONFIRMATION', False)

            buy_fee = rl_config.DEFAULT_BUY_FEE
            buy_tip = rl_config.DEFAULT_BUY_TIP
            sell_fee = rl_config.DEFAULT_SELL_FEE
            sell_tip = rl_config.DEFAULT_SELL_TIP
            min_mcap_usd_fallback = rl_config.MIN_MARKET_CAP_USD_FALLBACK

        except (KeyError, ValueError, TypeError, IndexError) as e:
            logger.error(f"RL Env: Error getting data/params at step {self.current_step}: {e}", exc_info=False)
            return realized_pnl_this_step, reward_bonus_penalty
        
        if self.active_position:
            pos = self.active_position
            pos['highest_price'] = max(pos['highest_price'], high_price)
            
            sell_reason = None
            if price <= pos['stop_loss_price']:
                sell_reason = "Stop Loss" if not pos['first_tp_hit'] else "Breakeven SL"
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif price >= pos['second_tp_price']:
                sell_reason = "Second TP"
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif not pos['first_tp_hit'] and price >= pos['initial_tp_price']:
                sell_reason = "First TP"
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif pos['first_tp_hit']:
                trailing_sl_price = pos['highest_price'] * (1.0 - trailing_sl_percent / 100.0)
                if trailing_sl_price > 0 and price <= trailing_sl_price:
                    sell_reason = "Trailing SL"
                    reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            
            if current_live_usd_mc > 0 and current_live_usd_mc < min_mcap_usd_fallback and not sell_reason:
                 sell_reason = f"Emergency SL (Abs USD MCap < {min_mcap_usd_fallback})"
                 reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            
            if sell_reason:
                initial_tokens = pos['initial_tokens']
                remaining_tokens = pos['remaining_tokens']
                
                tokens_to_sell = remaining_tokens
                if sell_reason == "First TP":
                    tokens_to_sell = min(initial_tokens * (first_sell_percent / 100.0), remaining_tokens)
                
                if tokens_to_sell > 1e-9:
                    gross_sol_recv = tokens_to_sell * price
                    net_sol_recv = gross_sol_recv - sell_fee - sell_tip
                    cost_basis_sold = pos['total_investment_sol'] * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                    pnl = net_sol_recv - cost_basis_sold
                    realized_pnl_this_step += pnl
                    self.current_sol += net_sol_recv
                    pos['remaining_tokens'] -= tokens_to_sell
                    self.trade_history.append({'step': self.current_step, 'type': 'sell', 'price': price, 'tokens': tokens_to_sell, 'pnl': pnl, 'reason': sell_reason})
                    
                    if sell_reason == "First TP":
                        pos['first_tp_hit'] = True
                        pos['stop_loss_price'] = pos['buy_price'] # Breakeven
                    
                    if pos['remaining_tokens'] < 1e-9:
                        self.active_position = None
        
        if not self.active_position and self.current_sol >= (buy_amount_sol_agent + buy_fee + buy_tip):
            meets_standard_criteria = (
                volume_ohlcv >= volume_thresh_usd and
                current_live_usd_mc >= mcap_thresh_buy_usd and
                rugcheck_val < rug_thresh_agent and
                socials_val < social_thresh_agent and
                volatility_val >= volatility_thresh_agent
            )

            proceed_with_buy_attempt = False
            if not meets_standard_criteria:
                proceed_with_buy_attempt = False
            elif use_trend_reversal:
                recency_hours = agent_params.get('TREND_REVERSAL_RECENCY_HOURS', 6)
                applicable_reasons = rl_config.APPLY_TREND_REVERSAL_ON_SELL_REASONS
                was_recently_sold = False
                if self.trade_history:
                    last_sell = next((t for t in reversed(self.trade_history) if t['type'] == 'sell'), None)
                    if last_sell:
                        time_since_sell = current_timestamp - self.current_data_df.index[last_sell['step']]
                        if time_since_sell <= timedelta(hours=recency_hours) and any(r in last_sell.get('reason','') for r in applicable_reasons):
                            was_recently_sold = True

                if was_recently_sold:
                    is_migrated = self.current_snapshot_df is not None and not self.current_snapshot_df.empty
                    
                    if is_migrated:
                        lookback_minutes = agent_params.get('DEX_REVERSAL_LOOKBACK_MINUTES', 15)
                        min_snapshots = agent_params.get('DEX_REVERSAL_MIN_SNAPSHOTS', 3)
                        min_liquidity = agent_params.get('DEX_REVERSAL_MIN_LIQUIDITY_USD', 5000)
                        min_ratio = agent_params.get('DEX_REVERSAL_MIN_BUY_SELL_RATIO', 1.5)
                        min_confirmations = agent_params.get('DEX_REVERSAL_MIN_CONFIRMATIONS', 2)

                        time_filter_start = current_timestamp - timedelta(minutes=lookback_minutes)
                        snapshots = self.current_snapshot_df.loc[(self.current_snapshot_df.index > time_filter_start) & (self.current_snapshot_df.index <= current_timestamp)]

                        if len(snapshots) < min_snapshots or float(snapshots.iloc[-1]['liquidity_usd']) < min_liquidity:
                            proceed_with_buy_attempt = False
                        else:
                            count = sum(1 for _, s in snapshots.iterrows() if s.get('buys_m5', 0) > 0 and (s.get('sells_m5', 0) == 0 or (s.get('buys_m5') / s.get('sells_m5')) >= min_ratio))
                            proceed_with_buy_attempt = count >= min_confirmations
                    else: # PUMP.FUN Logic
                        lookback_h = agent_params.get('INDICATOR_LOOKBACK_HOURS', 1)
                        candles_needed = int(lookback_h * 3600 / 5)
                        start_idx = max(0, self.current_step - candles_needed + 1)
                        
                        if (self.current_step - start_idx + 1) >= rl_config.MIN_CANDLE_DATA_FOR_INDICATORS:
                            indicator_config = {
                                'MIN_CANDLE_DATA_FOR_INDICATORS': rl_config.MIN_CANDLE_DATA_FOR_INDICATORS,
                                **{k: agent_params.get(k, v) for k, v in {
                                    'RSI_PERIOD': 14, 'BBANDS_PERIOD': 20, 'BBANDS_STD_DEV': 2.0, 
                                    'FAST_EMA_PERIOD': 9, 'SLOW_EMA_PERIOD': 21
                                }.items()}
                            }
                            df_inds = calculate_trend_indicators(self.current_data_df.iloc[start_idx : self.current_step + 1].copy(), indicator_config)

                            if not df_inds.empty and len(df_inds) >= 2:
                                latest = df_inds.iloc[-1]; prev = df_inds.iloc[-2]
                                rsi_neutral = agent_params.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 45)
                                bbl_col = f"BBL_{indicator_config['BBANDS_PERIOD']}_{indicator_config['BBANDS_STD_DEV']}"
                                stage1 = (latest.get('RSI', 50) > 30 and prev.get('RSI', 50) <= 30) or \
                                         (latest.get('Close', 0) > latest.get(bbl_col, float('inf')) and prev.get('Close', 0) <= prev.get(bbl_col, float('inf'))) or \
                                         (latest.get('RSI', 0) > rsi_neutral)
                                stage2 = (latest.get('Close', 0) > latest.get('VWAP', float('-inf'))) and (latest.get('EMA_fast', 0) > latest.get('EMA_slow', float('inf')))
                                proceed_with_buy_attempt = stage1 and stage2
                            else:
                                proceed_with_buy_attempt = False
                        else:
                            proceed_with_buy_attempt = False
                else:
                    proceed_with_buy_attempt = meets_standard_criteria
            else:
                proceed_with_buy_attempt = meets_standard_criteria

            if proceed_with_buy_attempt:
                total_investment = buy_amount_sol_agent + buy_fee + buy_tip
                tokens_bought = buy_amount_sol_agent / price
                self.current_sol -= total_investment
                sl_price = price * (1.0 - initial_sl_percent / 100.0)
                
                cost_of_tp1_portion = total_investment * (first_sell_percent / 100.0)
                desired_profit_tp1 = cost_of_tp1_portion * (first_sell_profit_margin / 100.0)
                fees_tp1_sell = sell_fee + sell_tip
                gross_sol_tp1 = cost_of_tp1_portion + desired_profit_tp1 + fees_tp1_sell
                tokens_tp1 = tokens_bought * (first_sell_percent / 100.0)
                tp1_price = gross_sol_tp1 / tokens_tp1 if tokens_tp1 > 1e-9 else float('inf')
                tp2_price = price * (1.0 + second_take_profit_percent / 100.0)

                self.active_position = {'buy_price': price, 'initial_tokens': tokens_bought, 'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment, 'stop_loss_price': sl_price, 'initial_tp_price': tp1_price, 'second_tp_price': tp2_price, 'highest_price': price, 'first_tp_hit': False, 'entry_timestamp': current_timestamp}
                self.trade_history.append({'step': self.current_step, 'type': 'buy', 'price': price, 'tokens': tokens_bought})
        
        if self.active_position:
            reward_bonus_penalty += rl_config.REWARD_HOLDING_PENALTY
            
        return realized_pnl_this_step, reward_bonus_penalty


    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        if self.current_data_df is None:
            obs = np.zeros(self.observation_space.shape, dtype=np.float32)
            return obs, 0.0, True, False, {"error": "Environment not reset"}

        self._apply_action(action)
        realized_pnl, bonus_penalty = self._run_trading_logic_step()
        
        terminated = self.current_sol <= 0
        
        current_data_idx_for_check = self.current_step 
        end_of_data = current_data_idx_for_check >= len(self.current_data_df) - 1
        
        token_died_this_step = False
        if self.current_token_end_ts and current_data_idx_for_check < len(self.current_data_df):
            current_candle_timestamp = self.current_data_df.index[current_data_idx_for_check]
            if current_candle_timestamp >= self.current_token_end_ts:
                token_died_this_step = True
        
        max_steps_reached = (self.current_step + 1) >= self._max_episode_steps
        truncated = max_steps_reached or end_of_data or token_died_this_step
        is_token_death_event_for_reward = end_of_data or token_died_this_step

        reward = self._calculate_reward(realized_pnl, bonus_penalty, is_token_death_event_for_reward)
        
        self.current_step += 1

        if not (terminated or truncated):
             self._last_step_processed_index = self.current_step
        else:
             self._last_step_processed_index = min(self.current_step, len(self.current_data_df) - 1) if len(self.current_data_df) > 0 else -1

        observation = self._get_observation()

        info = {
            'mint': self.current_mint, 'step': self.current_step - 1,
            'sol_balance': self.current_sol, 'realized_pnl_step': realized_pnl,
            'is_holding': 1 if self.active_position else 0, 'raw_reward': reward
        }
        if terminated or truncated:
            final_val = self.current_sol
            if self.active_position and self._price_history:
                final_val += self.active_position['remaining_tokens'] * self._price_history[-1]
            info['final_portfolio_value'] = final_val
            info['total_steps_taken'] = self.current_step
            if terminated: info['episode_end_reason'] = "terminated (bankrupt)"
            elif token_died_this_step: info['episode_end_reason'] = "truncated (token_death)"
            elif end_of_data: info['episode_end_reason'] = "truncated (end_of_data)"
            elif max_steps_reached: info['episode_end_reason'] = "truncated (max_steps)"
            else: info['episode_end_reason'] = "truncated (unknown)"
            
        return observation, reward, terminated, truncated, info

    def _calculate_reward(self, realized_pnl: float, bonus_penalty: float, is_token_death_event: bool) -> float:
        reward = realized_pnl * rl_config.REWARD_PNL_MULTIPLIER
        reward += bonus_penalty
        if is_token_death_event and self.active_position:
            reward += rl_config.REWARD_DEATH_PENALTY
        return reward

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)

        self.current_mint = random.choice(self.available_mints)
        self.current_data_df = self.historical_data_dict[self.current_mint].copy()
        self.current_snapshot_df = self.dexscreener_snapshot_data.get(self.current_mint)
        
        lifespan = self.token_lifespans.get(self.current_mint)
        if not lifespan:
             raise RuntimeError(f"Lifespan info missing for selected mint {self.current_mint} during reset.")
        self.current_token_end_ts = lifespan['end_ts']

        self.initial_creation_market_cap_sol = None 
        if not self.current_data_df.empty and 'creation_init_market_cap_sol' in self.current_data_df.columns:
            val_series = pd.to_numeric(self.current_data_df['creation_init_market_cap_sol'], errors='coerce')
            first_valid_val = val_series.dropna().iloc[0] if not val_series.dropna().empty else np.nan
            if pd.notna(first_valid_val) and first_valid_val > 0:
                self.initial_creation_market_cap_sol = float(first_valid_val)
        
        if 'volatility' not in self.current_data_df.columns or self.current_data_df['volatility'].isnull().all():
             prices = pd.to_numeric(self.current_data_df.get('Close'), errors='coerce').ffill().bfill().fillna(0.0)
             self.current_data_df['volatility'] = calculate_volatility(prices, window=rl_config.VOLATILITY_WINDOW).fillna(0.0) if len(prices) > 1 else 0.0
        else:
             self.current_data_df['volatility'] = self.current_data_df['volatility'].fillna(0.0)
        
        self.current_step = 0
        self._last_step_processed_index = -1
        self.current_sol = self.initial_capital
        self.active_position = None
        self.trade_history = []
        self.current_parameters = {}
        self._price_history.clear()
        self._previous_unrealized_pnl = 0.0
        self.last_observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        initial_steps_to_fill = min(len(self.current_data_df), self._price_history.maxlen)
        for i in range(initial_steps_to_fill):
            try:
                price = float(self.current_data_df.iloc[i].get('Close', 0.0))
                self._price_history.append(price if pd.notna(price) else 0.0)
            except (IndexError, ValueError, TypeError): self._price_history.append(0.0)

        if len(self.current_data_df) > 0:
            self._last_step_processed_index = 0
            observation = self._get_observation()
            self._last_step_processed_index = -1 
        else:
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)
        return observation, {}

    def render(self, mode='human'):
        if mode == 'ansi':
            output = f"--- Step: {self.current_step}/{self._max_episode_steps} (Data Index: {self._last_step_processed_index}) ---\n"
            output += f"Mint: {self.current_mint}\n"
            output += f"SOL Balance: {self.current_sol:.4f}\n"
            if self.active_position:
                pos = self.active_position
                output += f"Holding: {pos['remaining_tokens']:.4f} tokens (Bought @ {pos['buy_price']:.9f})\n"
            else:
                output += "Holding: None\n"
            last_close = self._price_history[-1] if self._price_history else 'N/A'
            output += f"Last Close Price: {last_close}\n"
            return output
        elif mode == 'human':
            print(self.render(mode='ansi'))

    def close(self):
        pass

    def set_render_mode(self, render_mode: Optional[str]):
        self.render_mode = render_mode
```

---

### 📄 rl_trainer.py

```python
# FILE: rl_trainer.py (Updated Env Initialization)

"""
Reinforcement Learning Agent Training Script.

This module orchestrates the training process for a Reinforcement Learning (RL) agent 
using Stable Baselines3 to learn optimal trading parameters within a custom TradingEnv environment.

Key Features:
- Trains an RL agent for trading strategy optimization
- Supports visualization of training progress via TensorBoard
- Configurable environment and agent parameters

TensorBoard Visualization:
To monitor training details, run:
    tensorboard --logdir ./rl_tensorboard_logs/ --port 6006
"""

import os
import asyncio
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Union, Tuple
import warnings

# --- Stable Baselines3 Imports ---
try:
    import stable_baselines3
    from stable_baselines3 import PPO, SAC, TD3
    from stable_baselines3.common.env_util import make_vec_env
    # Import VecEnv types explicitly
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv, VecNormalize
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.env_checker import check_env
    from stable_baselines3.common.logger import configure as sb3_configure_logger
    RL_AVAILABLE = True
except ImportError:
    print("Stable Baselines3 library not found or has issues. RL training is unavailable.")
    print("Please install it: pip install stable-baselines3[extra]>=2.0.0a5")
    RL_AVAILABLE = False
    class DummyAlgorithm: pass
    PPO = SAC = TD3 = DummyAlgorithm
    class BaseCallback: pass
    class VecEnv: pass # Dummy VecEnv base class
    class DummyVecEnv(VecEnv): pass
    class SubprocVecEnv(VecEnv): pass
    class VecNormalize(VecEnv): pass

import shap
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt

# --- Project Modules ---
import rl_config
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_environment import TradingEnv # Ensure TradingEnv takes lifespan info
from utils import load_and_split_data, calculate_volatility, export_to_csv, NpEncoder # Import NpEncoder for saving

# --- Global Variables ---
db_client_global: Optional[DatabaseClient] = None


# --- Custom Callback ---
class TensorboardCallback(BaseCallback):
    """Logs additional custom values to TensorBoard."""
    def __init__(self, verbose=0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        # Log average final portfolio value from completed episodes
        final_values = [ep_info.get('final_portfolio_value') for ep_info in self.model.ep_info_buffer if 'final_portfolio_value' in ep_info]
        if final_values:
            avg_final_value = np.mean(final_values)
            self.logger.record('rollout/ep_final_value_mean', avg_final_value)

        # Log average SOL balance at episode end
        sol_balances = [ep_info.get('sol_balance') for ep_info in self.model.ep_info_buffer if 'sol_balance' in ep_info and ep_info.get('terminated', False) or ep_info.get('truncated', False)]
        if sol_balances:
             avg_sol_balance = np.mean(sol_balances)
             self.logger.record('rollout/ep_sol_balance_mean', avg_sol_balance)
        return True

# Add this class after the TensorboardCallback class
class SaveVecNormalizeCallback(BaseCallback):
    """Callback to save VecNormalize statistics when a new best model is found."""
    def __init__(self, save_path: str, verbose=0):
        super().__init__(verbose)
        self.save_path = save_path

    def _on_step(self) -> bool:
        vec_normalize = self.model.get_vec_normalize_env()
        if vec_normalize is not None:
            vec_normalize.save(self.save_path)
        return True

def analyze_feature_importance(model, env, num_samples=1000):
    """Analyzes feature importance using SHAP and Permutation Importance."""
    # Generate properly structured samples
    samples = np.array([env.observation_space.sample() for _ in range(num_samples)])

    # Create a simple wrapper class for the model to be used as an estimator
    class ModelPredictor:
        def __init__(self, model):
            self.model = model

        def predict(self, X):
            # Ensure the input X is treated as a batch for prediction
            # Stable Baselines3 returns (action, state) tuple
            return np.array([self.model.predict(sample)[0] for sample in X])

        # Add a dummy fit method to satisfy permutation_importance's check
        def fit(self, X, y=None):
            return self

    model_predictor = ModelPredictor(model)

    # SHAP Analysis
    # Use the ModelPredictor instance as the model for SHAP
    explainer = shap.Explainer(
        model_predictor.predict, # Pass the predict method
        samples,
        feature_names=rl_config.OBSERVATION_FEATURES
    )

    # Calculate SHAP values
    # Use a reasonable subset of samples for SHAP to manage memory and computation
    shap_samples = samples[:500] # Increased samples for SHAP
    shap_values = explainer(shap_samples)

    # Plot summary
    plt.figure()
    shap.summary_plot(shap_values, shap_samples, show=False, feature_names=rl_config.OBSERVATION_FEATURES) # Pass feature_names explicitly
    plt.savefig(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_shap.png"))
    plt.close()

    # Permutation Importance
    # Use a reasonable subset of samples for permutation importance
    perm_samples = samples[:500] # Increased samples for permutation importance

    # Define a scoring function for permutation_importance that accepts X and y but only uses X
    def mean_prediction_magnitude_score(estimator, X, y):
        # Estimator here is our ModelPredictor instance
        predictions = estimator.predict(X)
        # For a continuous action space, predictions is an array of actions.
        # We can take the mean of the sum of squares of actions to measure the magnitude.
        # Use negative because permutation_importance expects a score where higher is better,
        # and we want features that *decrease* the score (change the prediction) to be important.
        return -np.mean(np.sum(predictions**2, axis=-1))
    
    result = permutation_importance(
        model_predictor, # Pass the ModelPredictor instance as the estimator
        perm_samples, # This is X
        y=None, # Explicitly pass y=None
        scoring=mean_prediction_magnitude_score, # Provide custom scoring
        n_repeats=5,
        random_state=42, # FIX: Pass the generator instance instead of an integer seed
        n_jobs=1
    )

    # Save results
    importance_df = pd.DataFrame({
        'feature': rl_config.OBSERVATION_FEATURES,
        'importance_mean': result.importances_mean, # Access mean directly
        'importance_std': result.importances_std # Access std directly
    }).sort_values('importance_mean', ascending=False)

    importance_df.to_csv(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_permutation.csv"), index=False)

    logger.info("Feature importance analysis completed")

# --- Environment Creation Helper ---
def make_env_func(
    data_dict: Dict[str, pd.DataFrame],
    lifespan_dict: Dict[str, Dict[str, datetime]], # Add lifespans
    snapshot_dict: Dict[str, pd.DataFrame],
    initial_capital: float,
    max_steps: int,
    rank: int = 0,
    seed: int = 0,
    render_mode: Optional[str] = None # Added render_mode parameter
):
    """
    Utility function for creating and wrapping the environment for VecEnv.

    Args:
        data_dict: Historical data for this environment instance.
        lifespan_dict: Token lifespan data for this environment instance.
        initial_capital: Starting capital.
        max_steps: Max steps per episode.
        rank: Unique identifier for the environment instance.
        seed: Base random seed.

    Returns:
        A function that initializes and returns the wrapped environment.
    """
    def _init():
        # Filter data to only include mints present in lifespan_dict
        valid_data = {
            k: v for k, v in data_dict.items()
            if isinstance(v, pd.DataFrame) and not v.empty and k in lifespan_dict
        }
        valid_lifespans = {k: v for k, v in lifespan_dict.items() if k in valid_data}
        # Filter snapshots to only include those for valid mints
        valid_snapshots = {k: v for k, v in snapshot_dict.items() if k in valid_data}


        if not valid_data or not valid_lifespans:
            logger.error(f"make_env_func (rank {rank}) received empty/invalid data or missing lifespans!")
            raise ValueError(f"Cannot create environment for rank {rank} with empty data or missing lifespans.")

        env = TradingEnv(
            historical_data_dict=valid_data,
            token_lifespans=valid_lifespans, # Pass lifespans
            dexscreener_snapshot_data=valid_snapshots,
            initial_capital=initial_capital,
            max_steps=max_steps,
            render_mode=render_mode # Pass render_mode to TradingEnv
        )
        env.reset(seed=seed + rank) # Seed the environment
        log_dir_monitor = os.path.join(rl_config.MODEL_SAVE_DIR, f"monitor_logs_{rank}")
        os.makedirs(log_dir_monitor, exist_ok=True)
        env = Monitor(env, filename=log_dir_monitor)
        return env
    return _init

# --- Main Training Function ---
async def train_rl_agent(render_mode: Optional[str] = None):
    """
    Sets up the RL environment, agent, callbacks, and starts training.

    Args:
        render_mode: The render mode for the training environment (e.g., 'human', 'ansi').
                     Set to None to disable rendering.
    """
    global db_client_global
    setup_logging(logger_name="rl_trainer") # Initialize logger for this module
    logger.info("--- Starting RL Agent Training ---")

    if not RL_AVAILABLE:
        logger.critical("Stable Baselines3 is not available. Cannot start RL training.")
        return

    # --- Database Connection ---
    if not db_client_global:
        db_client_global = DatabaseClient()
        try:
            await db_client_global.connect()
            logger.info("DB Client connected for RL Trainer.")
        except Exception as e:
            logger.critical(f"Failed to connect database for RL Trainer: {e}")
            return

    # --- Load and Prepare Data ---
    start_date = rl_config.RL_HISTORICAL_DATA_START_TS
    end_date = rl_config.RL_HISTORICAL_DATA_END_TS
    data_split_config = rl_config.DATA_SPLIT_RL

    logger.info(f"Loading and splitting data from {start_date.isoformat()} to {end_date.isoformat()}...")
    loaded_results: Optional[Tuple[Dict, Dict, Dict]] = await load_and_split_data(
        db_client_global, start_date, end_date, data_split_config
    )

    if not loaded_results:
        logger.critical("Failed to load or split data. Exiting.")
        await db_client_global.close() if db_client_global else None
        return

    loaded_data_sets, token_lifespans, dexscreener_snapshots  = loaded_results

    training_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_EVAL)

    train_lifespans = {k: v for k, v in token_lifespans.items() if k in training_data} if training_data else {}
    eval_lifespans = {k: v for k, v in token_lifespans.items() if k in eval_data} if eval_data else {}

    # Filter snapshots for each data split
    train_snapshots = {k: v for k, v in dexscreener_snapshots.items() if k in training_data} if training_data else {}
    eval_snapshots = {k: v for k, v in dexscreener_snapshots.items() if k in eval_data} if eval_data else {}


    if not training_data or not train_lifespans:
        logger.critical("No training data or corresponding lifespans available. Exiting.")
        await db_client_global.close() if db_client_global else None
        return

    logger.info(f"Training data loaded for {len(training_data)} tokens with lifespan info.")
    if eval_data and eval_lifespans:
        logger.info(f"Evaluation data loaded for {len(eval_data)} tokens with lifespan info.")
    else:
        logger.warning("No evaluation data/lifespans found. Evaluation callback will not function correctly.")
        eval_data = None
        eval_lifespans = {}

    # --- START: Dynamic MAX_STEPS_PER_EPISODE Calculation ---
    if train_lifespans:
        lifespan_durations_seconds = [
            (v['end_ts'] - v['start_ts']).total_seconds()
            for v in train_lifespans.values()
            if v['end_ts'] and v['start_ts']
        ]
        if lifespan_durations_seconds:
            # Use the percentile from the config file
            percentile_value = rl_config.MAX_STEPS_PERCENTILE
            percentile_duration = np.percentile(lifespan_durations_seconds, percentile_value)
            
            # Assuming 5-second candles (steps)
            CANDLE_INTERVAL_SECONDS = 5
            max_steps_calculated = int(percentile_duration / CANDLE_INTERVAL_SECONDS)
            
            # Ensure a minimum number of steps
            max_steps = max(max_steps_calculated, 100) # e.g., minimum 100 steps
            
            logger.info(f"Dynamically calculated MAX_STEPS_PER_EPISODE based on {percentile_value}th percentile of training data lifespans: {max_steps} steps.")
        else:
            logger.warning("Could not calculate token lifespans from training data. Using fallback MAX_STEPS_PER_EPISODE.")
            max_steps = 2880 # Fallback value
    else:
        logger.error("No training lifespans available to calculate MAX_STEPS_PER_EPISODE. Using fallback.")
        max_steps = 2880 # Fallback value
    # --- END: Dynamic Calculation ---

    # --- Create Vectorized Environments ---
    logger.info("Creating RL Vectorized Environments...")
    train_env_raw: Optional[VecEnv] = None
    eval_env_raw: Optional[VecEnv] = None
    train_env: Optional[VecNormalize] = None
    eval_env: Optional[VecNormalize] = None


    try:
        VecEnvClass = SubprocVecEnv if rl_config.N_ENVS > 1 else DummyVecEnv

        # Create training environments, passing lifespans
        # Create training environments, passing all three data dictionaries
        env_fns = [
            make_env_func(
                data_dict=training_data, 
                lifespan_dict=train_lifespans,
                snapshot_dict=train_snapshots, # Pass snapshot data
                initial_capital=rl_config.RL_INITIAL_CAPITAL, 
                max_steps=max_steps, 
                rank=i, 
                render_mode=render_mode
            ) for i in range(rl_config.N_ENVS)
        ]
        train_env_raw = VecEnvClass(env_fns) # Revert passing render_mode to SubprocVecEnv constructor
        # Explicitly set render_mode on the VecEnv instance after creation
        if render_mode is not None:
             train_env_raw.render_mode = render_mode
        logger.info(f"Created Training VecEnv ({VecEnvClass.__name__}) with {rl_config.N_ENVS} environments.")

        # --- Environment Checker ---
        # try:
        #     logger.info("Running environment checker...")
        #     # Pass lifespans to the check env func too
        #     sample_env_fn = make_env_func(training_data, train_lifespans, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE, rank=99)
        #     check_env(sample_env_fn(), warn=True) # Create and check one instance
        #     logger.info("Environment check passed.")
        # except Exception as check_err:
        #     logger.error(f"Environment check failed: {check_err}", exc_info=True)
        #     # return # Exit if check fails

        # Create evaluation environment
        if eval_data and eval_lifespans:
            eval_env_fn = make_env_func(
                data_dict=eval_data, 
                lifespan_dict=eval_lifespans,
                snapshot_dict=eval_snapshots, # Pass snapshot data
                initial_capital=rl_config.RL_INITIAL_CAPITAL, 
                max_steps=rl_config.MAX_STEPS_PER_EPISODE, 
                rank=100
            )
            eval_env_raw = DummyVecEnv([eval_env_fn])
            # Explicitly set render_mode on the VecEnv instance after creation
            if render_mode is not None:
                 eval_env_raw.render_mode = render_mode
            logger.info("Created Evaluation VecEnv (DummyVecEnv).")
        else:
             eval_env_raw = None

        # --- Apply VecNormalize ---
        normalize_kwargs = {'norm_obs': True, 'norm_reward': False, 'gamma': 0.99}
        train_env = VecNormalize(train_env_raw, **normalize_kwargs)
        # Remove explicit render_mode setting on VecNormalize
        logger.info("Applied VecNormalize to training environment.")
        if eval_env_raw:
            eval_env = VecNormalize(eval_env_raw, training=False, **normalize_kwargs)
            # Remove explicit render_mode setting on VecNormalize
            # Load the SAME stats as the training env for consistent evaluation
            eval_env.obs_rms = train_env.obs_rms
            eval_env.ret_rms = train_env.ret_rms # If normalizing rewards (norm_reward=True)
            eval_env.clip_obs = train_env.clip_obs
            eval_env.clip_reward = train_env.clip_reward
            logger.info("Applied VecNormalize to evaluation environment using training stats.")
        else:
            eval_env = None

    except Exception as e:
        logger.exception(f"Error creating vectorized environments: {e}")
        # Clean up any created envs
        if train_env: train_env.close()
        elif train_env_raw: train_env_raw.close() # Close raw if wrapper failed
        if eval_env: eval_env.close()
        elif eval_env_raw: eval_env_raw.close()
        if db_client_global: await db_client_global.close()
        return

    # --- Configure Agent ---
    # (Agent selection, path setup, SB3 logger setup - same as before)
    logger.info(f"Setting up RL Agent: {rl_config.RL_ALGORITHM}")
    algo_map = {"PPO": PPO, "SAC": SAC, "TD3": TD3}
    AgentClass = algo_map.get(rl_config.RL_ALGORITHM)

    if AgentClass is None:
        logger.critical(f"RL Algorithm '{rl_config.RL_ALGORITHM}' not supported.")
        # Cleanup envs before exiting
        if train_env: train_env.close()
        if eval_env: eval_env.close()
        if db_client_global: await db_client_global.close()
        return

    os.makedirs(rl_config.TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(rl_config.MODEL_SAVE_DIR, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"{rl_config.RL_ALGORITHM}_{run_timestamp}"
    log_path_tb = os.path.join(rl_config.TENSORBOARD_LOG_DIR, model_prefix)
    save_path_model = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_final.zip")
    save_path_vecnormalize = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_vecnormalize.pkl")
    best_model_save_dir = os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_best")

    # Configure SB3 logger to output to tensorboard, csv, and stdout
    sb3_file_logger = sb3_configure_logger(log_path_tb, ["stdout", "csv", "tensorboard"])

    device = 'cpu' #"auto"
    logger.info(f"Using device: {device}")

    # Define agent parameters
    agent_params = dict(
        policy="MlpPolicy",
        env=train_env, # Use the normalized env
        policy_kwargs={
            "net_arch": {
                "pi": [64, 64],  # Policy network architecture
                "vf": [64, 64]   # Value function network architecture
            }
        },
        verbose=1,
        device=device,
        seed=42
    )
    # Algorithm-specific hyperparameters
    if rl_config.RL_ALGORITHM == "PPO":
        agent_params.update(dict(
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.1,  # Slightly increased for better exploration
            vf_coef=0.5,
            learning_rate=3e-4,
            max_grad_norm=0.5,  # Added to prevent explosive gradients
            use_sde=False,     # Added explicit SDE setting
            sde_sample_freq=-1
        ))
    # Add SAC/TD3 params if needed

    model = AgentClass(**agent_params)
    model.set_logger(sb3_file_logger) # Assign the configured logger

    # --- Setup Callbacks ---
    logger.info("Setting up Callbacks...")
    callbacks = []
    # Checkpoint callback
    checkpoint_callback = CheckpointCallback(
        save_freq=max(rl_config.CHECKPOINT_FREQ // rl_config.N_ENVS, 1), # Adjust freq by n_envs
        save_path=os.path.join(rl_config.MODEL_SAVE_DIR, f"{model_prefix}_checkpoints"),
        name_prefix="rl_model",
        save_replay_buffer=True if rl_config.RL_ALGORITHM in ["SAC", "TD3"] else False,
        save_vecnormalize=True # IMPORTANT: Save VecNormalize stats with checkpoints
    )
    callbacks.append(checkpoint_callback)

    # Evaluation callback
    if eval_env:
        save_vec_normalize_callback = SaveVecNormalizeCallback(
            save_path=os.path.join(best_model_save_dir, "best_vecnormalize.pkl")
        )
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=best_model_save_dir,
            log_path=best_model_save_dir,
            eval_freq=max(rl_config.EVAL_FREQ // rl_config.N_ENVS, 1),
            n_eval_episodes=rl_config.N_EVAL_EPISODES,
            deterministic=True,
            render=True,
            verbose=1,
            callback_on_new_best=save_vec_normalize_callback  # Use the new callback class
        )
        callbacks.append(eval_callback)
    else:
        logger.warning("EvalCallback disabled as evaluation environment is not available.")

    # Custom TensorBoard callback
    callbacks.append(TensorboardCallback())

    # --- Start Training ---
    logger.info(f"--- Starting RL Training ({rl_config.RL_ALGORITHM}) for {rl_config.TOTAL_TIMESTEPS} timesteps ---")
    start_train_time = time.time()
    training_successful = False
    try:
        model.learn(
            total_timesteps=rl_config.TOTAL_TIMESTEPS,
            callback=callbacks,
            log_interval=10, # Log stats every 10 updates (can adjust)
            reset_num_timesteps=True
        )
        training_successful = True
    except KeyboardInterrupt:
         logger.warning("Training interrupted by user (KeyboardInterrupt). Saving current model.")
    except Exception as learn_err:
        logger.exception(f"Error during model.learn(): {learn_err}")
    finally:
        # --- Save Final Model and Environment Statistics ---
        end_train_time = time.time()
        logger.info(f"--- Training loop finished. Duration: {end_train_time - start_train_time:.2f} seconds ---")

        try:
            # Save the final agent model
            model.save(save_path_model)
            logger.info(f"Final trained model saved to: {save_path_model}")

            # Save the VecNormalize statistics from the training environment
            if isinstance(train_env, VecNormalize):
                train_env.save(save_path_vecnormalize)
                logger.info(f"Final VecNormalize statistics saved to: {save_path_vecnormalize}")

            # Check if a best model was saved and report
            best_model_path = os.path.join(best_model_save_dir, "best_model.zip")
            best_vecnorm_path = os.path.join(best_model_save_dir, "best_vecnormalize.pkl")
            if eval_env and os.path.exists(best_model_path) and training_successful:
                logger.info(f"Best model saved during evaluation: {best_model_path}")
                if os.path.exists(best_vecnorm_path):
                    logger.info(f"Corresponding VecNormalize stats saved: {best_vecnorm_path}")
                else:
                    logger.warning(f"Best model saved, but VecNormalize stats file missing: {best_vecnorm_path}")

        except Exception as save_err:
             logger.error(f"Failed to save final model or VecNormalize stats: {save_err}")

        if training_successful:
            logger.info("Performing post-training feature importance analysis...")
            analyze_feature_importance(model, train_env)

        # --- Cleanup ---
        logger.info("Closing environments...")
        try:
            # Close VecNormalize wrappers first, then underlying VecEnvs
            if train_env: train_env.close()
            if eval_env: eval_env.close()
            # No need to explicitly close train_env_raw/eval_env_raw if wrappers were created
        except Exception as close_err:
            logger.error(f"Error closing environments: {close_err}")

        if db_client_global: await db_client_global.close()
        logger.info("--- RL Agent Training Finished ---")


# --- Entry Point Guard ---
if __name__ == "__main__":
    if os.name == 'nt':
         from multiprocessing import freeze_support
         freeze_support()

    try:
        # To enable rendering during debugging, change render_mode to 'human' or 'ansi'
        # Be aware that rendering can significantly slow down training, especially with N_ENVS > 1.
        asyncio.run(train_rl_agent(render_mode=None)) # Set render_mode here for training envs
    except Exception as main_err:
         logger.critical(f"Critical error in RL trainer entry point: {main_err}", exc_info=True)

```

---

## 📂 sql

---

### 📄 01_create_tokens.sql

```sql
-- Create the tokens table
CREATE TABLE IF NOT EXISTS tokens (
    mint TEXT PRIMARY KEY,          -- token mint
    traderPublicKey TEXT,           -- token creator's wallet address
    initialBuy NUMERIC,             -- initially buyed tokens
    solAmount NUMERIC,              -- initially spent amount of SOL
    bondingCurveKey TEXT,           -- bondingCurve key
    vTokensInBondingCurve NUMERIC,  -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,     -- SOL in BondingCurve
    marketCapSol NUMERIC,           -- market cap in SOL
    name TEXT,                      -- token name
    symbol TEXT,                    -- token symbol
    uri TEXT,                       -- META URL
    website TEXT,                   -- website link, fetched from META URL
    telegram TEXT,                  -- telegram link, fetched from META URL
    twitter TEXT,                   -- twitter link, fetched from META URL
    socials_score INTEGER,          -- calculated social score
    socials_last_checked TIMESTAMP WITH TIME ZONE,  -- last try to fetch META URL
    sol_price_usd NUMERIC,                          -- SOL price at token creation
    is_active BOOLEAN DEFAULT TRUE,                 -- TRUE or FALLS for considering in check_buy_opportunities
    last_trade TIMESTAMP WITH TIME ZONE,            -- TIMESTAMP of the last Trade event, updated when a new TRADE is fetched
    cooldown_until TIMESTAMP WITH TIME ZONE,        -- <<< ADD THIS LINE: Prevent re-buys until this time
    data_source TEXT DEFAULT 'PUMP', -- 'PUMP' for WebSocket, 'DEXSCREENER' for API
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- creation TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS tokens_backup (
    LIKE tokens INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_reason TEXT;
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE tokens_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 02_create_trades.sql

```sql
-- Create the trades table
CREATE TABLE IF NOT EXISTS trades (
    signature TEXT PRIMARY KEY,         -- signature of the token event
    mint TEXT,                          -- tokens mint address
    trader_pubkey TEXT,                 -- The wallet address of the trader
    tx_type TEXT,                       -- event type 'buy' or 'sell'
    token_amount NUMERIC,               -- amount of tokens traded
    sol_amount NUMERIC,                 -- amount of SOL traded
    price NUMERIC,                      -- token price in SOL
    bondingCurveKey TEXT,               -- BondingCurve key
    vTokensInBondingCurve NUMERIC,      -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,         -- amount of SOL in BondingCurve
    marketCapSol NUMERIC,               -- market cap in SOL
    sol_price_usd NUMERIC,              -- actual SOL price in USD at the time of the trade event
    market_cap_calculated NUMERIC,      -- calculated market cap in USD
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of the trade event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS trades_backup (
    LIKE trades INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE trades_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE trades_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 03_create_rugcheck.sql

```sql
CREATE TABLE IF NOT EXISTS rugcheck (
    mint TEXT PRIMARY KEY REFERENCES tokens(mint) ON DELETE CASCADE,
    tokenProgram TEXT,
    creator TEXT,
    token_mintAuthority TEXT,
    token_supply NUMERIC,
    token_decimals INTEGER,
    token_isInitialized BOOLEAN,
    token_freezeAuthority TEXT,
    tokenMeta_name TEXT,
    tokenMeta_symbol TEXT,
    tokenMeta_uri TEXT,
    tokenMeta_mutable BOOLEAN,
    tokenMeta_updateAuthority TEXT,
    freezeAuthority TEXT,
    mintAuthority TEXT,
    risks TEXT,
    score INTEGER,
    fileMeta_description TEXT,
    fileMeta_name TEXT,
    fileMeta_symbol TEXT,
    fileMeta_image TEXT,
    totalMarketLiquidity NUMERIC,
    totalLPProviders INTEGER,
    rugged BOOLEAN,
    tokenType TEXT,
    transferFee_pct NUMERIC,
    transferFee_maxAmount NUMERIC,
    transferFee_authority TEXT,
    graphInsidersDetected INTEGER,
    detectedAt TIMESTAMP WITH TIME ZONE,
    full_data TEXT,
    last_checked TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS rugcheck_backup (
    LIKE rugcheck INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE rugcheck_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE rugcheck_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 04_create_portfolio.sql

```sql
-- Original portfolio table creation
CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    mint TEXT,
    tx_type TEXT,                     -- 'buy' or 'sell'
    price NUMERIC,                    -- Price per token at the time of tx
    market_cap NUMERIC,               -- Market cap at the time of tx
    sol_amount NUMERIC,               -- Gross SOL spent (buy) or received (sell, before fees)
    sol_price_usd NUMERIC,            -- SOL price in USD at the time of tx
    tokens NUMERIC,                   -- Number of tokens bought or sold in this tx
    fee NUMERIC,                      -- Fee associated with this tx
    tip NUMERIC,                      -- Tip associated with this tx
    profit NUMERIC,                   -- Profit/Loss for sell tx (net_sol_received - cost_basis)
    status TEXT,                      -- Status of the original buy position ('active', 'closed')
    reason TEXT,                      -- Reason for sell ('Stop Loss', 'First TP', 'Second TP', 'Trailing SL', 'Breakeven SL', etc.)

    -- Fields primarily relevant for the original 'buy' entry
    total_investment_sol NUMERIC,     -- Total SOL invested in this position (including fees)
    initial_tokens NUMERIC,           -- Total tokens acquired in the initial buy tx
    remaining_tokens NUMERIC,         -- Tokens currently held from the initial buy tx (updated on sells)
    highest_price NUMERIC NOT NULL DEFAULT 0.0, -- Highest price observed since the buy
    stop_loss_price NUMERIC,          -- Current active stop loss price level
    initial_tp_price NUMERIC,         -- Calculated price for the first take profit
    second_tp_price NUMERIC,          -- Calculated price for the second take profit
    first_tp_hit BOOLEAN NOT NULL DEFAULT FALSE, -- Flag indicating if the first TP has been triggered

    settings JSONB,                   -- Settings for this position (e.g. stop loss price)

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS portfolio_backup (
    LIKE portfolio INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE portfolio_backup ADD COLUMN IF NOT EXISTS backed_up TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE portfolio_backup ALTER COLUMN timestamp DROP DEFAULT;

```

---

### 📄 05_create_migrations.sql

```sql
CREATE TABLE IF NOT EXISTS migrations (
    signature TEXT PRIMARY KEY, -- signature of the token event
    mint TEXT,                  -- tokens mint address
    txtype TEXT,                -- event type 'migrate'
    pool TEXT,                  -- migration pool
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of migration event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS migrations_backup (
    LIKE migrations INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE migrations_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE migrations_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 06_create_creator_wallets.sql

```sql
CREATE TABLE IF NOT EXISTS creator_wallets (
    wallet_address TEXT PRIMARY KEY,
    token_count INTEGER DEFAULT 0,
    last_token_time TIMESTAMP WITH TIME ZONE
);
```

---

### 📄 07_create_sol_price_usd.sql

```sql
CREATE TABLE IF NOT EXISTS sol_price_usd (
    id SERIAL PRIMARY KEY,
    price  NUMERIC(15, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

### 📄 08_create_bot_heartbeat.sql

```sql
-- sql/10_create_bot_heartbeat.sql
CREATE TABLE IF NOT EXISTS bot_heartbeat (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    event_type TEXT DEFAULT 'heartbeat', -- e.g., 'heartbeat', 'config_update', 'shutdown_signal'
    details JSONB -- Optional: for storing details about the event, like which config was updated
);

CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_timestamp ON bot_heartbeat(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_event_type ON bot_heartbeat(event_type);
```

---

### 📄 09_create_configuration.sql

```sql
-- Create the configurations table
CREATE TABLE IF NOT EXISTS configurations (
    key TEXT PRIMARY KEY,
    value TEXT,
    type TEXT NOT NULL CHECK (type IN ('int', 'float', 'bool', 'str', 'list')),
    description TEXT, -- Optional: for human-readable descriptions
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Trigger to update last_updated timestamp automatically
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.last_updated = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_configurations_last_updated
BEFORE UPDATE ON configurations
FOR EACH ROW
EXECUTE FUNCTION update_last_updated_column();

CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations(key);
```

---

### 📄 10_create_dexscreener_data.sql

```sql
-- Table to store periodic data snapshots from the DEX Screener API for migrated tokens
CREATE TABLE IF NOT EXISTS dexscreener_data (
    id SERIAL PRIMARY KEY,
    pair_address TEXT NOT NULL,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price_usd NUMERIC,
    price_native NUMERIC,
    sol_price_usd NUMERIC, -- <<< ADDED THIS COLUMN
    liquidity_usd NUMERIC,
    market_cap NUMERIC,
    fdv NUMERIC,
    
    -- Volume Columns
    volume_m5 NUMERIC,
    volume_h1 NUMERIC,
    volume_h6 NUMERIC,
    volume_h24 NUMERIC,
    
    -- Price Change Columns
    price_change_m5 NUMERIC,
    price_change_h1 NUMERIC,
    price_change_h6 NUMERIC,
    price_change_h24 NUMERIC,

    -- Transaction Columns
    buys_m5 INTEGER,
    sells_m5 INTEGER,
    buys_h1 INTEGER,
    sells_h1 INTEGER,
    buys_h6 INTEGER,
    sells_h6 INTEGER,
    buys_h24 INTEGER,
    sells_h24 INTEGER,

    full_response JSONB
);

CREATE INDEX IF NOT EXISTS idx_dexscreener_data_mint_timestamp ON dexscreener_data(mint_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_pair_address ON dexscreener_data(pair_address);

-- Backup table creation
CREATE TABLE IF NOT EXISTS dexscreener_data_backup (
    LIKE dexscreener_data INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE dexscreener_data_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE dexscreener_data_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 11_create_indexes.sql

```sql
-- *********************************************
-- INDEXES FOR BASE TABLES
-- *********************************************

-- Tokens Table
CREATE INDEX IF NOT EXISTS idx_tokens_is_active_timestamp ON public.tokens USING btree (is_active, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_tokens_mint ON public.tokens USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_name ON public.tokens USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_socials_score ON public.tokens USING btree (socials_score);
CREATE INDEX IF NOT EXISTS idx_tokens_traderpublickey ON public.tokens USING btree (traderpublickey);

-- Trades Table
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp ON trades(mint, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp_sol ON trades(mint, timestamp DESC, sol_amount); -- For View Queries

-- Portfolio Table
CREATE INDEX IF NOT EXISTS idx_portfolio_active_buy ON portfolio USING btree (mint, tx_type, status) WHERE ((status = 'active'::text) AND (tx_type = 'buy'::text));
CREATE INDEX IF NOT EXISTS idx_portfolio_mint ON portfolio USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_portfolio_mint_status ON portfolio USING btree (mint, status);

-- Rugcheck Table
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked ON rugcheck(mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked_desc ON rugcheck USING btree (mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_score ON rugcheck USING btree (score);

-- Dexscreener_data Table
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_mint_timestamp ON dexscreener_data USING btree (mint_address, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_pair_address ON dexscreener_data USING btree (pair_address);

-- bot_heartbeat Table
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_event_type ON bot_heartbeat USING btree (event_type);
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_timestamp ON bot_heartbeat USING btree ("timestamp" DESC);

-- configurations Table
CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations USING btree (key);

-- *********************************************
-- INDEXES FOR BACKUP TABLES
-- *********************************************

-- Tokens Backup
CREATE INDEX IF NOT EXISTS idx_tokens_backup_mint ON tokens_backup USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_name ON tokens_backup USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_socials_score ON tokens_backup USING btree (socials_score);

-- Trades Backup
CREATE INDEX IF NOT EXISTS idx_trades_backup_mint_timestamp ON trades_backup(mint, timestamp DESC);

-- Rugcheck Backup
CREATE INDEX IF NOT EXISTS idx_rugcheck_backup_mint_last_checked ON rugcheck_backup USING btree (mint, last_checked DESC);

-- Dexscreener_data Backup
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_mint_address_timestamp_idx ON dexscreener_data_backup USING btree (mint_address, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_pair_address_idx ON dexscreener_data_backup USING btree (pair_address);
```

---

### 📄 12_create_views.sql

```sql
-- sql/12_create_views.sql

-- View for combined tokens and tokens_backup
-- Prioritizes data from 'tokens' if a mint exists in both.
CREATE OR REPLACE VIEW v_tokens AS
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, is_active, last_trade,
    cooldown_until,
    '' as backup_reason, timestamp
FROM tokens
UNION ALL
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, FALSE AS is_active, last_trade,
    cooldown_until,
    backup_reason, timestamp
FROM tokens_backup tb
WHERE NOT EXISTS (SELECT 1 FROM tokens t WHERE t.mint = tb.mint);

-- View for combined trades and trades_backup
CREATE OR REPLACE VIEW v_trades AS
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades
UNION ALL
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades_backup;

-- View for combined rugcheck and rugcheck_backup
-- Note: Getting the *latest* score per mint will be handled in the query using this view.
CREATE OR REPLACE VIEW v_rugcheck AS
SELECT mint, score, token_supply, last_checked FROM rugcheck
UNION ALL
SELECT mint, score, token_supply, last_checked FROM rugcheck_backup;

-- View for combined migrations and migrations_backup
CREATE OR REPLACE VIEW v_migrations AS
SELECT 
    signature,
    mint,
    txType,
    pool,
    timestamp,
    NULL AS backup_timestamp,
    'active' AS record_source
FROM 
    migrations

UNION ALL

SELECT 
    signature,
    mint,
    txType,
    pool,
    timestamp,
    backup_timestamp,
    'backup' AS record_source
FROM 
    migrations_backup;


-- View for combined dexscreener_data and dexscreener_data_backup
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data
UNION ALL
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data_backup;


-- Creates unified views for market data from both Pump.fun and DEX Screener.

-- First, a helper view for all Dexscreener data (live + backup).
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data
UNION ALL
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data_backup;

-- ===================================================================================
--  HISTORICAL UNIFIED VIEW (Includes Backups via v_* views)
--  PURPOSE: For backtesting, GA/RL training, and full historical analysis.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_historical AS
SELECT
    mint, timestamp, tx_type, token_amount, sol_amount,
    price AS price_sol, marketCapSol AS market_cap_sol, market_cap_calculated as market_cap_usd,
    (sol_amount * sol_price_usd) AS volume_usd, -- <-- ADDED: Unified USD volume
    'PUMP' AS data_source
FROM v_trades -- Querying backup-inclusive view
WHERE price IS NOT NULL AND price > 0 AND sol_amount > 0 AND token_amount > 0
UNION ALL
SELECT
    mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount,
    (volume_m5 / sol_price_usd) AS sol_amount,      -- <-- CORRECTED: This is now SOL volume
    (price_usd / sol_price_usd) AS price_sol,
    (market_cap / sol_price_usd) AS market_cap_sol,
    market_cap AS market_cap_usd,
    volume_m5 AS volume_usd,                        -- <-- ADDED: Unified USD volume
    'DEXSCREENER' AS data_source
FROM v_dexscreener_data; -- Querying backup-inclusive view

-- ===================================================================================
--  LIVE-ONLY UNIFIED VIEW (Excludes Backups)
--  PURPOSE: For fast, forward-looking queries driving live trade decisions.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_live AS
SELECT
    mint, timestamp, tx_type, token_amount, sol_amount,
    price AS price_sol, marketCapSol AS market_cap_sol, market_cap_calculated as market_cap_usd,
    (sol_amount * sol_price_usd) AS volume_usd, -- <-- ADDED: Unified USD volume
    'PUMP' AS data_source
FROM trades -- Querying LIVE table
WHERE price IS NOT NULL AND price > 0 AND sol_amount > 0 AND token_amount > 0
UNION ALL
SELECT
    mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount,
    (volume_m5 / sol_price_usd) AS sol_amount,      -- <-- CORRECTED: This is now SOL volume
    (price_usd / sol_price_usd) AS price_sol,
    (market_cap / sol_price_usd) AS market_cap_sol,
    market_cap AS market_cap_usd,
    volume_m5 AS volume_usd,                        -- <-- ADDED: Unified USD volume
    'DEXSCREENER' AS data_source
FROM dexscreener_data; -- Querying LIVE table
```

---

## 📂 (Root Files)

---

### 📄 utils.py

```python
"""
Helper functions and utilities for the trading bot.
Includes URL validation, audio alerts, and log formatting.
"""

import os
import asyncio
import pandas as pd
import pandas_ta as ta
import warnings # Add this import
import numpy as np
import json
from datetime import datetime, timezone, timedelta # <-- Added timedelta
from bot_logger import logger, Panel, Table, Text, Align, Group, rich_box
# Type hint for DatabaseClient without creating circular dependency
from typing import TYPE_CHECKING, Dict, Optional, Tuple, List
# For type hinting TradingBot instance without circular import
if TYPE_CHECKING:
    from trading_bot import TradingBot # Assuming trading_bot.py has TradingBot class
    from state_manager import GlobalState
    from database_handler import DatabaseClient
from urllib.parse import urlparse
import winsound


async def format_task_monitor_rich(bot: 'TradingBot') -> Panel:
    """
    Formats the task monitor status into a Rich Panel.
    Args:
        bot: The TradingBot instance.
    Returns:
        A Rich Panel object.
    """
    try:
        sol_amount = await bot.state.get_current_sol_balance()
        tokens_subscribed_list = await bot.state.get_token_subscriptions()
        tokens_subscribed_count = len(tokens_subscribed_list)
        rug_queue_size = bot.state.get_rugcheck_queue().qsize()
        socials_queue_size = bot.state.get_socialscheck_queue().qsize()
        
        open_trades_count_display: Text | str = Text("N/A", style="white")
        if bot.db_client and bot.db_client.pool:
            try:
                active_positions = await bot.db_client.get_active_buy_positions()
                open_trades_count_display = Text(str(len(active_positions)), style="yellow")
            except Exception as e_db:
                logger.error(f"Error fetching open trades count for monitor: {e_db}")
                open_trades_count_display = Text("Error", style="bold red")

        # --- Summary Table ---
        summary_table = Table(show_header=False, box=None, padding=(0, 1, 0, 0))
        summary_table.add_column(style="dim cyan", justify="right", width=20)
        summary_table.add_column(justify="left")

        rl_agent_status_msg = Text("Loaded & Active", style="green") if bot.rl_agent else Text("Not Loaded", style="dim white")
        summary_table.add_row(":brain: RL Agent:", rl_agent_status_msg)
        summary_table.add_row(":moneybag: SOL Balance:", Text(f"{sol_amount:.4f}", style="green"))
        summary_table.add_row(":link: Subscribed Tokens:", Text(str(tokens_subscribed_count), style="magenta"))
        summary_table.add_row(":bar_chart: Open Trades:", open_trades_count_display) # Already a Text object
        summary_table.add_row(":mag_right: RugCheck Queue:", Text(str(rug_queue_size), style="blue"))
        summary_table.add_row(":busts_in_silhouette: Socials Queue:", Text(str(socials_queue_size), style="blue"))
        summary_table.add_row(":gear: Managed Tasks:", Text(f"{len([t for t in bot.tasks if not t.done()])}/{len(bot.tasks)}", style="white"))

        # --- Task Details Table ---
        task_table = Table(box=rich_box.MINIMAL, show_header=True, header_style="bold cyan", padding=(0,1,0,0), title_justify="left")
        task_table.add_column("Task Name", style="cyan", no_wrap=True, min_width=25)
        task_table.add_column("Status", style="white", min_width=20)

        for task in bot.tasks:
            task_name = task.get_name()
            status_text = Text()
            if task_name == "buy_opportunity_checker":
                if not bot.state.is_buying_enabled:
                    status_text.append("paused", style="yellow")
                    status_text.append(" (buys disabled)", style="dim yellow")
                elif task.done():
                    status_text.append("done", style="red")
                    if task.exception():
                        status_text.append(f" (Error: {task.exception()!r})", style="dim red")
                else:
                    status_text.append("running", style="green")
            else:
                if task.done():
                    status_text.append("done", style="red")
                    if task.exception():
                        status_text.append(f" (Error: {task.exception()!r})", style="dim red")
                else:
                    status_text.append("running", style="green")
            task_table.add_row(task_name, status_text)
        
        panel_content = Group(summary_table, task_table)

        final_panel = Panel(
            panel_content,
            title="[bold magenta]:robot: Bot Task Monitor[/bold magenta]",
            border_style="cyan",
            expand=False,
            padding=(1,2)
        )
        return final_panel
    except Exception as e:
        logger.error(f"Failed to format task monitor: {e}", exc_info=True)
        return Panel(Text(f"Error generating task monitor: {e!r}", style="bold red"), border_style="red")
# async def format_task_monitor_rich(bot: 'TradingBot') -> Panel:
#     logger.info("format_task_monitor_rich: Returning EXTREMELY simple panel for testing.") # Use the actual logger
#     return Panel(Text("Simple Test Panel Content", style="bold green"), title="[bold blue]Test Simple Panel[/bold blue]", border_style="red")

def is_valid_telegram(url: str) -> bool:
    """Validates if the provided URL is a valid Telegram link."""
    return url.startswith("https://t.me/") and "/joinchat/" not in url

def is_valid_twitter(url: str) -> bool:
    """Validates if the provided URL is a valid Twitter link."""
    return url.startswith(("https://twitter.com/", "https://x.com/"))

def is_valid_website(url: str) -> bool:
    """Validates if the provided URL is a proper website URL (not a social media domain)."""
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc not in ["x.com", "t.me", "telegram.org"]

def play_wav(file_path: str):
    """Synchronously plays a WAV file using winsound."""
    try:
        winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing the file {file_path}: {e}")

async def play_buy_opportunity_sound():
    """Asynchronously plays an alert sound for a buy opportunity."""
    import asyncio
    loop = asyncio.get_running_loop()
    wav_file = "assets/alert.wav"
    if not os.path.exists(wav_file):
        print(f"Sound file not found: {wav_file}")
        return
    await loop.run_in_executor(None, play_wav, wav_file)

def play_sell_sl_sound():
    """Synchronously play the stop-loss sell sound."""
    try:
        winsound.PlaySound("assets/hupe.wav", winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing sell SL sound: {e}")

def play_sell_tp_sound():
    """Synchronously play the take profit sell sound."""
    try:
        winsound.PlaySound("assets/ka_ching.wav", winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing sell TP sound: {e}")

async def play_sell_sl_sound_async():
    """Asynchronously play the stop-loss sell sound."""
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, play_sell_sl_sound)

async def play_sell_tp_sound_async():
    """Asynchronously play the take profit sell sound."""
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, play_sell_tp_sound)

def format_buy_order_log(state, name: str, mint: str, price_per_token: float, tokens_bought: float, market_cap: float, sol_price: float, total_investment: float, for_telegram: bool = False) -> str:
    """Formats the log message for a buy order with platform-specific links."""
    # URL construction
    base_url = "https://neo.bullx.io/terminal?chainId=1399811149&address="
    url = f"{base_url}{mint}"

    # Handle different platforms
    if for_telegram:
        #formatted_mint = f'<a href="{url}">{mint}</a>'
        formatted_mint = url
    else:
        # Use Rich markup for console hyperlinks
        # This requires `markup=True` in the RichHandler, which you have.
        formatted_mint = f"[link={url}]{mint}[/link]"

    # Handle name display with formatted mint
    token_display = f"{name} - {formatted_mint}" if name else formatted_mint
    if sol_price:
        price_usd = price_per_token * sol_price
        market_cap_usd = market_cap * sol_price
        total_usd = total_investment * sol_price
        return (
            f"★★★ 💲 BUY Order 💲 ★★★\n"
            f"│ Token: {token_display}\n"
            f"│ Price: {price_per_token:.8f} SOL (${price_usd:.8f} USD)\n"
            f"│ Market Cap: {market_cap:,.2f} SOL (${market_cap_usd:,.2f} USD)\n"
            f"│ Tokens Bought: {tokens_bought}\n"
            f"│ Total Investment: {total_investment} SOL (${total_usd:.2f} USD)\n"
            f"\n"
        )
    else:
        return (
            f"★★★ BUY Order ★★★\n"
            f"│ Token: {token_display}\n"
            f"│ Price: {price_per_token:.8f} SOL\n"
            f"│ Market Cap: {market_cap:,.2f} SOL\n"
            f"│ Tokens Bought: {tokens_bought}\n"
            f"│ Total Investment: {total_investment}\n"
        )
    

def format_sell_order_log(mint: str, token_name: str, market_cap_sol: float, profit: float, reason: str, sol_price: float | None, for_telegram: bool = False) -> str:
    """Formats the log message for a sell order."""
    profit_sign = "📈" if profit >= 0 else "📉"
    profit_text = f"{profit:+.6f} SOL" # Always show sign

    # URL construction
    base_url = "https://neo.bullx.io/terminal?chainId=1399811149&address="
    url = f"{base_url}{mint}"

    # Handle different platforms
    if for_telegram:
        #formatted_mint = f'<a href="{url}">{mint}</a>'
        formatted_mint = url
    else:
        ## Use Rich markup for console hyperlinks
        # This requires `markup=True` in the RichHandler, which you have.
        formatted_mint = f"[link={url}]{mint}[/link]"

    if sol_price and sol_price > 0:
        market_cap_usd = market_cap_sol * sol_price
        profit_usd = profit * sol_price
        profit_text += f" (${profit_usd:+.2f} USD)" # Add USD profit
        market_cap_text = f"{market_cap_sol:,.2f} SOL (${market_cap_usd:,.2f} USD)"
    else:
        # Handle case where SOL price might not be available
        market_cap_text = f"{market_cap_sol:,.2f} SOL (USD price unavailable)"
        profit_text += " (USD profit unavailable)"


    # Use token_name if available, otherwise just mint
    # https://neo.bullx.io/terminal?chainId=1399811149&address=3bgtCbZuXgFuHATFZmGcxKyyA6qtT8feEZV9gDSwpump
    display_name = f"{token_name} ({formatted_mint})" if token_name else mint

    return (
        f"*** {profit_sign} SELL Order ({reason}) {profit_sign} ***\n"
        f"│ Token: {display_name}\n"
        f"│ Market Cap: {market_cap_text}\n"
        f"│ Profit: {profit_text}\n"
    )
    

def calculate_social_score(social_data: dict, token_name: str, token_symbol: str) -> int:
    """Computes a social risk score based on provided social data."""
    total_penalty = 0
    token_name = (token_name or "").lower()
    token_symbol = (token_symbol or "").lower()
    
    website = social_data.get("website")
    if not website:
        total_penalty += 30
    else:
        if not is_valid_website(website):
            total_penalty += 20
        else:
            from urllib.parse import urlparse
            parsed = urlparse(website)
            domain = parsed.netloc
            if domain.endswith(f".{token_name}") or domain.endswith(f".{token_symbol}"):
                total_penalty -= 5
    
    telegram = social_data.get("telegram")
    if not telegram:
        total_penalty += 20
    else:
        if not is_valid_telegram(telegram):
            total_penalty += 10
    
    twitter = social_data.get("twitter")
    if not twitter:
        total_penalty += 20
    else:
        if not is_valid_twitter(twitter):
            total_penalty += 10
            
    return min(max(total_penalty, 0), 100)

def calculate_market_cap(vTokensInBondingCurve: float, vSolInBondingCurve: float, totalSupply: float, sol_price: float) -> float:
    """Calculates the market cap of a token using bonding curve data."""
    if vTokensInBondingCurve <= 0 or totalSupply <= 0:
        return 0.0
    price_per_token = vSolInBondingCurve / vTokensInBondingCurve
    return price_per_token * totalSupply * sol_price


def ensure_datetime(dt):
    """Ensure the input is a timezone-aware UTC datetime object."""
    # ... (function code as provided) ...
    if isinstance(dt, datetime):
        # If naive, assume UTC. If aware, convert to UTC.
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        else:
            return dt.astimezone(timezone.utc)
    elif isinstance(dt, str):
        try:
            # Attempt to parse with and without time component
            try:
                 parsed_dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                 parsed_dt = datetime.strptime(dt, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return parsed_dt
        except ValueError as e:
            raise ValueError(f"Unsupported date string format '{dt}': {e}") from e
    elif pd.isna(dt): # Handle potential pandas NaT
        return None
    raise TypeError(f"Unsupported date type: {type(dt)}")

async def load_and_split_data(
    db_client: 'DatabaseClient',
    start_date_dt: datetime,
    end_date_dt: datetime,
    data_split_config: dict,
    min_data_points: int = 100 # Minimum *trades* required per token
) -> Optional[Tuple[Dict[str, Dict[str, pd.DataFrame]], Dict[str, Dict[str, datetime]], Dict[str, pd.DataFrame]]]:
    """
    [MODIFIED] Loads historical data for tokens active within a time window.
    1. Identifies tokens created or traded within the specified time window.
    2. For these identified tokens, it fetches their *entire* historical data.
    3. Splits the list of tokens chronologically for training, validation, and testing.

    Returns:
        A tuple containing:
        - historical_data_sets (dict): {'train': {mint: ohlcv_df}, ...}
        - token_lifespans (dict): {mint: {'start_ts': dt, 'end_ts': dt}}
        - dexscreener_snapshots (dict): {mint: snapshot_df} for migrated tokens.
        Returns None if loading or splitting fails.
    """
    if not db_client or not db_client.pool:
        logger.error("Database client not initialized or connected.")
        return None

    try:
        start_date = ensure_datetime(start_date_dt)
        end_date = ensure_datetime(end_date_dt)
        if not start_date or not end_date or start_date >= end_date:
             logger.error(f"Invalid date range: Start={start_date}, End={end_date}.")
             return None

        logger.info(f"Loading & splitting data. Identifying tokens in window: {start_date.isoformat()} to {end_date.isoformat()}")

        # --- Step 1: Fetch candidate mints active in the window and their full lifespans ---
        query_mints_lifespans = """
            WITH MintsInWindow AS (
                -- Select unique mints with trades in the window
                SELECT mint FROM v_trades
                WHERE timestamp >= $1 AND timestamp < $2
                UNION
                -- Select unique mints created in the window
                SELECT mint FROM v_tokens
                WHERE timestamp >= $1 AND timestamp < $2
            ),
            -- For these candidates, get their full stats (all-time trades)
            TokenStats AS (
                SELECT
                    m.mint,
                    MIN(t.timestamp) as first_trade_ts,
                    MAX(t.timestamp) as last_trade_ts,
                    COUNT(t.signature) as trade_count
                FROM MintsInWindow m
                JOIN v_trades t ON m.mint = t.mint
                GROUP BY m.mint
            )
            SELECT
                ts.mint,
                ts.first_trade_ts,
                ts.last_trade_ts,
                ts.trade_count
            FROM TokenStats ts
            LEFT JOIN v_tokens AS vt ON ts.mint = vt.mint
            WHERE ts.trade_count >= $3 -- Filter by min_data_points
              AND (vt.backup_reason = 'rugged_dead' OR vt.backup_reason = '' OR vt.backup_reason IS NULL);
        """
        candidate_records = await db_client.pool.fetch(query_mints_lifespans, start_date, end_date, min_data_points)
        
        if not candidate_records:
            logger.error(f"No tokens found that were active in the window and met the minimum trade count of {min_data_points}.")
            return None
            
        token_lifespans_map = {r['mint']: {'start_ts': r['first_trade_ts'], 'end_ts': r['last_trade_ts']} for r in candidate_records if r['mint'] and r['first_trade_ts'] and r['last_trade_ts']}
        mints_to_load = list(token_lifespans_map.keys())
        
        if not mints_to_load: 
            logger.error("No valid mints with lifespans found after filtering.")
            return None
        
        logger.info(f"Found {len(mints_to_load)} candidate mints. Fetching their full historical data...")


        # --- Step 2: Fetch ALL historical data for the selected mints ---
        dexscreener_snapshot_query = """
            SELECT
                mint_address as mint, timestamp, liquidity_usd, buys_m5, sells_m5
            FROM v_dexscreener_data
            WHERE mint_address = ANY($1::text[])
            ORDER BY mint_address, timestamp;
        """
        # Call with None for dates to fetch all data for the mints
        all_historical_data, dexscreener_snapshot_records = await asyncio.gather(
            db_client.get_historical_data_for_backtesting(mints_to_load, start_date=None, end_date=None),
            db_client.pool.fetch(dexscreener_snapshot_query, mints_to_load) # Fetch all snapshots for these mints
        )

        if not all_historical_data:
            logger.error("Failed to fetch any historical OHLCV data for the candidate mints.")
            return None

        # Process DexScreener snapshots into a dictionary of DataFrames
        dexscreener_snapshots = {}
        if dexscreener_snapshot_records:
            df_snapshots = pd.DataFrame([dict(r) for r in dexscreener_snapshot_records])
            df_snapshots['timestamp'] = pd.to_datetime(df_snapshots['timestamp'], utc=True)
            for mint, group in df_snapshots.groupby('mint'):
                dexscreener_snapshots[mint] = group.set_index('timestamp').sort_index()
        logger.info(f"Fetched DexScreener snapshots for {len(dexscreener_snapshots)} migrated tokens.")

        # --- Step 3: Filter and Split tokens chronologically ---
        final_token_lifespans = {}
        for mint, df in all_historical_data.items():
            if mint in token_lifespans_map:
                final_token_lifespans[mint] = token_lifespans_map[mint]
        
        sorted_mints = sorted(final_token_lifespans.keys(), key=lambda m: final_token_lifespans[m]['start_ts'])
        n_tokens = len(sorted_mints)
        n_train = int(n_tokens * data_split_config['training'])
        n_val = int(n_tokens * data_split_config['validation'])
        historical_data_sets = {'train': {}, 'validation': {}, 'test': {}}
        for i, mint in enumerate(sorted_mints):
            if mint in all_historical_data:
                if i < n_train:
                    historical_data_sets['train'][mint] = all_historical_data[mint]
                elif i < n_train + n_val:
                    historical_data_sets['validation'][mint] = all_historical_data[mint]
                else:
                    historical_data_sets['test'][mint] = all_historical_data[mint]
        
        logger.info(f"Data split complete. Training tokens: {len(historical_data_sets['train'])}, Validation tokens: {len(historical_data_sets['validation'])}, Test tokens: {len(historical_data_sets['test'])}")
        if not historical_data_sets['train']:
             logger.error("Training set is empty after chronological splitting!")
             return None

        # Return all three data dictionaries
        return historical_data_sets, final_token_lifespans, dexscreener_snapshots

    except Exception as e:
        logger.exception(f"Unexpected error during data loading/splitting: {e}")
        return None

def calculate_volatility(prices: pd.Series, window: int = 120) -> pd.Series: # <-- Return Series
    """
    Calculate rolling volatility based on log returns over a specified window.
    Returns the *entire Series* of volatility values. # <-- Modified docstring

    Args:
        prices (pd.Series): A pandas Series of prices, typically indexed by time.
        window (int): The rolling window size (number of periods).

    Returns:
        pd.Series: The calculated rolling volatility series, or an empty Series. # <-- Modified docstring
    """
    if prices is None or not isinstance(prices, pd.Series) or len(prices) < 2:
        return pd.Series(dtype=np.float64) # Return empty Series

    # Ensure prices are numeric and sorted by index if time-based
    prices = pd.to_numeric(prices, errors='coerce').dropna()
    if not np.all(np.diff(prices.index) >= pd.Timedelta(0)):
        prices = prices.sort_index() # Ensure chronological order

    if len(prices) < 2:
         return pd.Series(dtype=np.float64)

    # Calculate log returns, handling potential division by zero or invalid values
    log_returns = np.log(prices / prices.shift(1))
    log_returns = log_returns.replace([np.inf, -np.inf], np.nan).fillna(0) # Replace inf/NaN with 0

    # Calculate rolling standard deviation
    min_periods_required = max(2, window // 2)
    rolling_std = log_returns.rolling(window=window, min_periods=min_periods_required).std()

    # Annualize/Scale volatility
    volatility_series = rolling_std * np.sqrt(window)

    # Return the entire volatility Series
    return volatility_series.fillna(0.0) # Fill leading NaNs with 0

import os

def export_to_csv(historical_data_sets: Dict[str, Dict[str, pd.DataFrame]],
                 output_dir: str,
                 token_lifespans: Optional[Dict[str, Dict[str, datetime]]] = None):
    """
    Exports historical_data_sets (OHLCV) and token_lifespans to CSV files.

    Args:
        historical_data_sets: Dictionary of datasets containing OHLCV histories.
        output_dir: Directory to save the exports.
        token_lifespans: Optional dictionary containing token lifespan information.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Export datasets
    validation_report = []

    for dataset_key, dataset in historical_data_sets.items():
        dataset_dir = os.path.join(output_dir, dataset_key)
        os.makedirs(dataset_dir, exist_ok=True)

        for mint, df in dataset.items():
            # Data validation (using 'Close' price)
            # ---> FIX: Use 'Close' column for validation <---
            if 'Close' in df.columns:
                zero_prices = df['Close'].eq(0).sum()
                null_prices = df['Close'].isnull().sum()
            else:
                logger.warning(f"Column 'Close' not found in DataFrame for mint {mint} in dataset {dataset_key}. Skipping price validation.")
                zero_prices = 0
                null_prices = 0
            # ---> END FIX <---

            if zero_prices > 0 or null_prices > 0:
                validation_report.append({
                    'dataset': dataset_key,
                    'mint': mint,
                    'zero_prices': zero_prices,
                    'null_prices': null_prices,
                    'total_rows': len(df),
                    'start_ts': df.index[0] if not df.empty else None,
                    'end_ts': df.index[-1] if not df.empty else None
                })

            # Export OHLCV data
            csv_file = os.path.join(dataset_dir, f"{mint}_ohlcv.csv") # Changed filename suffix
            df.to_csv(csv_file, index=True)

            # Export lifespan data if available
            if token_lifespans and mint in token_lifespans:
                lifespan_file = os.path.join(dataset_dir, f"{mint}_lifespan.json")
                with open(lifespan_file, 'w') as f:
                    json.dump({
                        'mint': mint,
                        'start_ts': token_lifespans[mint]['start_ts'].isoformat() if token_lifespans[mint]['start_ts'] else None,
                        'end_ts': token_lifespans[mint]['end_ts'].isoformat() if token_lifespans[mint]['end_ts'] else None
                    }, f, indent=4)

    # Write validation report with lifespan comparison
    if validation_report:
        report_file = os.path.join(output_dir, "validation_report.txt")
        with open(report_file, 'w') as f:
            f.write("Data Validation Report\n")
            f.write("====================\n\n")
            for report in validation_report:
                f.write(f"Dataset: {report['dataset']}\n")
                f.write(f"Mint: {report['mint']}\n")
                f.write(f"Zero Close prices: {report['zero_prices']}\n") # Updated label
                f.write(f"Null Close prices: {report['null_prices']}\n") # Updated label
                f.write(f"Total rows: {report['total_rows']}\n")
                f.write(f"Data range: {report['start_ts']} to {report['end_ts']}\n")

                # Add lifespan info if available
                if token_lifespans and report['mint'] in token_lifespans:
                    lifespan = token_lifespans[report['mint']]
                    f.write(f"Token lifespan: {lifespan['start_ts']} to {lifespan['end_ts']}\n")
                f.write("--------------------\n")

        logger.warning(f"Found data quality issues (zero/null Close prices). Check {report_file} for details.")

    logger.info(f"Exported OHLCV data and lifespans to {output_dir}")

def calculate_trend_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Calculates a suite of technical indicators using pandas-ta.

    Args:
        df (pd.DataFrame): DataFrame with columns 'Open', 'High', 'Low', 'Close', 'Volume'.
        config (dict): The bot's configuration dictionary for periods.

    Returns:
        pd.DataFrame: The original DataFrame with new indicator columns appended.
    """
    if df.empty or len(df) < config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30):
        logger.debug(f"Not enough data to calculate indicators (Have: {len(df)}, Need: {config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30)}).")
        return pd.DataFrame()

    try:
        df_ta = df.copy()

        # --- BUG FIX START ---
        # Explicitly use the 'Close' column for indicators that operate on a single price series.
        # This prevents pandas-ta from returning a multi-column DataFrame when a single Series is expected.
        close_prices = df_ta['Close']

        # Calculate Bollinger Bands (this is usually fine as it uses H, L, C)
        bbands = df_ta.ta.bbands(length=config['BBANDS_PERIOD'], std=config['BBANDS_STD_DEV'], append=True)

        # Calculate RSI using the specified close price series
        df_ta.ta.rsi(close=close_prices, length=config['RSI_PERIOD'], append=True)

        # Calculate EMAs using the specified close price series
        df_ta.ta.ema(close=close_prices, length=config['FAST_EMA_PERIOD'], append=True, col_names=('EMA_fast',))
        df_ta.ta.ema(close=close_prices, length=config['SLOW_EMA_PERIOD'], append=True, col_names=('EMA_slow',))
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            # VWAP requires High, Low, Close, and Volume, which df_ta has.
            df_ta.ta.vwap(append=True)
        # --- BUG FIX END ---
        
        df_ta.dropna(inplace=True)
        
        logger.debug(f"Successfully calculated indicators. Resulting data shape: {df_ta.shape}")
        return df_ta

    except Exception as e:
        logger.error(f"Error calculating indicators: {e}", exc_info=True)
        return pd.DataFrame()


class NpEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle NumPy, Pandas, and datetime types
    that are not serializable by default.
    """
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int_)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float_)):
            # Handle NaN, Infinity, -Infinity separately
            if np.isnan(obj):
                return None # Represent NaN as null in JSON
            elif np.isposinf(obj):
                return 'Infinity'
            elif np.isneginf(obj):
                return '-Infinity'
            else:
                return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist() # Convert arrays to lists
        elif isinstance(obj, (datetime, pd.Timestamp)):
            # Convert datetime/timestamp to ISO 8601 string format
            return obj.isoformat()
        # Let the base class default method raise the TypeError for unsupported types
        return super(NpEncoder, self).default(obj)

```

---

