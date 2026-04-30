# FILE: ga_backtester.py

"""
Backtesting Engine Module (Refactored for DexScreener & Advanced Logic)

Simulates trading strategies on historical data, respecting token lifespans,
cooldown periods, and implementing source-aware (Pump.fun vs. DexScreener)
trend-reversal re-buy logic to evaluate performance.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import config.config as config_module  # To access fixed configurations
import utils  # For calculate_trend_indicators
from bot_logger import logger


# --- Performance Metrics Calculation (Unchanged) ---
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
    This function's logic is self-contained and requires no changes.
    """
    # Initialize the dictionary to hold all performance metrics.
    metrics = {
        "total_pnl": 0.0, "total_return_pct": 0.0, "total_trades": 0,
        "winning_trades": 0, "losing_trades": 0, "total_profit_sells": 0.0,
        "total_loss_sells": 0.0, "win_rate": 0.0, "avg_profit_per_win_trade": 0.0,
        "avg_loss_per_loss_trade": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0,
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
        if metrics["total_trades"] > 0:
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
            current_portfolio_value += trade.get('amount_sol', 0)
            equity_curve.loc[trade_ts] = current_portfolio_value
    if end_ts:
        if not equity_curve.empty and equity_curve.index[-1] < end_ts:
             equity_curve.loc[end_ts] = final_capital
        elif equity_curve.empty:
             equity_curve.loc[start_ts if start_ts else datetime.now(timezone.utc)] = initial_capital
             equity_curve.loc[end_ts] = final_capital
    if not equity_curve.empty:
        equity_curve = equity_curve.sort_index()[~equity_curve.index.duplicated(keep='last')]
        roll_max = equity_curve.cummax()
        drawdown = (roll_max - equity_curve) / roll_max
        max_dd = drawdown.max() if not drawdown.empty else 0.0
    else:
        max_dd = 0.0
    metrics["max_drawdown"] = max_dd * 100.0

    return metrics

# --- Backtesting Core Function ---
def run_backtest_sync(
    parameters: dict,
    ohlcv_data: pd.DataFrame,
    initial_capital: float,
    max_timestamp: Optional[datetime] = None,
    dexscreener_snapshot_data: Optional[pd.DataFrame] = None,
    indicator_cache: Optional[Dict] = None
) -> dict:
    mint_addr = parameters.get("mint", "UNKNOWN_MINT")
    simulation_end_reason = "Completed"

    # --- Early exit conditions now create a complete metrics dictionary ---
    if ohlcv_data.empty:
        metrics = calculate_performance_metrics([], initial_capital, initial_capital, simulation_end_reason="No Data")
        metrics["final_portfolio_value"] = initial_capital
        return metrics

    # --- 1. Data Preparation & Validation ---
    if not isinstance(ohlcv_data.index, pd.DatetimeIndex) or ohlcv_data.index.tz is None:
        try:
             ohlcv_data.index = pd.to_datetime(ohlcv_data.index, utc=True)
        except Exception:
             metrics = calculate_performance_metrics([], initial_capital, initial_capital, simulation_end_reason="Invalid Index")
             metrics["final_portfolio_value"] = initial_capital
             return metrics

    df = ohlcv_data.copy().sort_index()
    start_ts_data = df.index.min()
    end_ts_data = df.index.max()

    # --- Pre-calculate indicators for the entire dataframe ---
    indicator_config = {
        'MIN_CANDLE_DATA_FOR_INDICATORS': parameters.get('MIN_CANDLE_DATA_FOR_INDICATORS', config_module.MIN_CANDLE_DATA_FOR_INDICATORS),
        'RSI_PERIOD': parameters.get('RSI_PERIOD', config_module.RSI_PERIOD),
        'BBANDS_PERIOD': parameters.get('BBANDS_PERIOD', config_module.BBANDS_PERIOD),
        'BBANDS_STD_DEV': parameters.get('BBANDS_STD_DEV', config_module.BBANDS_STD_DEV),
        'FAST_EMA_PERIOD': parameters.get('FAST_EMA_PERIOD', config_module.FAST_EMA_PERIOD),
        'SLOW_EMA_PERIOD': parameters.get('SLOW_EMA_PERIOD', config_module.SLOW_EMA_PERIOD),
        'ADAPTIVE_ATR_PERIOD': parameters.get('ADAPTIVE_ATR_PERIOD', config_module.ADAPTIVE_ATR_PERIOD)
    }
    df_with_indicators = utils.calculate_trend_indicators(df, indicator_config)

    if not df_with_indicators.empty:
        df = df_with_indicators

    if max_timestamp:
        if max_timestamp.tzinfo is None: max_timestamp = max_timestamp.replace(tzinfo=timezone.utc)
        df = df[df.index <= max_timestamp].copy()
        end_ts_data = max_timestamp
        simulation_end_reason = "Token Death"
        if df.empty:
            metrics = calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, simulation_end_reason)
            metrics["final_portfolio_value"] = initial_capital
            return metrics

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score', 'cooldown_until', 'token_creation_time']
    for col in required_cols:
        if col not in df.columns: df[col] = pd.NaT if 'time' in col or 'until' in col else np.nan
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score']
    for col in numeric_cols: df[col] = pd.to_numeric(df[col], errors='coerce')
    df['cooldown_until'] = pd.to_datetime(df['cooldown_until'], errors='coerce', utc=True)
    df['token_creation_time'] = pd.to_datetime(df['token_creation_time'], errors='coerce', utc=True)
    df[['Open', 'High', 'Low', 'Close', 'market_cap_calculated', 'volatility', 'token_creation_time']] = df[['Open', 'High', 'Low', 'Close', 'market_cap_calculated', 'volatility', 'token_creation_time']].ffill().bfill()
    df[['Volume']] = df[['Volume']].fillna(0.0)
    df[['rugcheck_score', 'socials_score']] = df[['rugcheck_score', 'socials_score']].fillna(1000.0)
    df['cooldown_until'] = df['cooldown_until'].fillna(pd.NaT)

    df = df[df["Close"] > 1e-12]

    if df.empty:
         metrics = calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, "No Candle Data")
         metrics["final_portfolio_value"] = initial_capital
         return metrics

    # --- 2. Extract Parameters from GA Solution ---
    sol_to_buy = parameters.get('SOL_TO_BUY', config_module.SOL_TO_BUY)
    initial_stop_loss_percent = parameters.get('INITIAL_STOP_LOSS_PERCENT', config_module.INITIAL_STOP_LOSS_PERCENT)
    first_sell_percent = parameters.get('FIRST_SELL_PERCENT', config_module.FIRST_SELL_PERCENT)
    trailing_stop_loss_percent = parameters.get('TRAILING_STOP_LOSS_PERCENT', config_module.TRAILING_STOP_LOSS_PERCENT)
    second_take_profit_percent = parameters.get('SECOND_TAKE_PROFIT_PERCENT', config_module.SECOND_TAKE_PROFIT_PERCENT)
    first_sell_profit_margin = parameters.get('FIRST_SELL_PROFIT_MARGIN', config_module.FIRST_SELL_PROFIT_MARGIN)
    volume_threshold = parameters.get('DEFAULT_VOLUME_THRESHOLD', config_module.DEFAULT_VOLUME_THRESHOLD)
    marketcap_threshold = parameters.get('DEFAULT_MARKETCAP_THRESHOLD', config_module.DEFAULT_MARKETCAP_THRESHOLD)
    rugcheck_threshold = parameters.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', config_module.DEFAULT_RUGCHECK_SCORE_THRESHOLD)
    socials_threshold = parameters.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', config_module.DEFAULT_SOCIAL_SCORE_THRESHOLD)
    min_volatility = parameters.get('MIN_VOLATILITY', config_module.MIN_VOLATILITY)
    min_emergency_mcap_usd = parameters.get('MIN_MARKET_CAP', config_module.MIN_MARKETCAP_THRESHOLD)
    buy_fee, buy_tip = parameters.get('DEFAULT_BUY_FEE', config_module.DEFAULT_BUY_FEE), parameters.get('DEFAULT_BUY_TIP', config_module.DEFAULT_BUY_TIP)
    sell_fee, sell_tip = parameters.get('DEFAULT_SELL_FEE', config_module.DEFAULT_SELL_FEE), parameters.get('DEFAULT_SELL_TIP', config_module.DEFAULT_SELL_TIP)
    use_trend_reversal = bool(parameters.get('USE_TREND_REVERSAL_CONFIRMATION', config_module.USE_TREND_REVERSAL_CONFIRMATION))
    stop_loss_cooldown_minutes_ga = parameters.get('STOP_LOSS_COOLDOWN_MINUTES', config_module.STOP_LOSS_COOLDOWN_MINUTES)
    min_candle_data_for_indicators_config = config_module.MIN_CANDLE_DATA_FOR_INDICATORS
    trend_reversal_recency_hours_ga = parameters.get('TREND_REVERSAL_RECENCY_HOURS', config_module.TREND_REVERSAL_RECENCY_HOURS)
    trend_reversal_rsi_neutral_level_ga = parameters.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', config_module.TREND_REVERSAL_RSI_NEUTRAL_LEVEL)
    indicator_lookback_hours_ga = parameters.get('INDICATOR_LOOKBACK_HOURS', config_module.INDICATOR_LOOKBACK_HOURS)
    rsi_period_ga = parameters.get('RSI_PERIOD', config_module.RSI_PERIOD)
    bbands_period_ga, bbands_std_dev_ga = parameters.get('BBANDS_PERIOD', config_module.BBANDS_PERIOD), parameters.get('BBANDS_STD_DEV', config_module.BBANDS_STD_DEV)
    fast_ema_period_ga, slow_ema_period_ga = parameters.get('FAST_EMA_PERIOD', config_module.FAST_EMA_PERIOD), parameters.get('SLOW_EMA_PERIOD', config_module.SLOW_EMA_PERIOD)
    apply_trend_reversal_on_sell_reasons_config = config_module.APPLY_TREND_REVERSAL_ON_SELL_REASONS
    dex_lookback_mins = parameters.get('DEX_REVERSAL_LOOKBACK_MINUTES', config_module.DEX_REVERSAL_LOOKBACK_MINUTES)
    dex_min_snapshots = parameters.get('DEX_REVERSAL_MIN_SNAPSHOTS', config_module.DEX_REVERSAL_MIN_SNAPSHOTS)
    dex_min_liquidity = parameters.get('DEX_REVERSAL_MIN_LIQUIDITY_USD', config_module.DEX_REVERSAL_MIN_LIQUIDITY_USD)
    dex_min_ratio = parameters.get('DEX_REVERSAL_MIN_BUY_SELL_RATIO', config_module.DEX_REVERSAL_MIN_BUY_SELL_RATIO)
    dex_min_confirmations = parameters.get('DEX_REVERSAL_MIN_CONFIRMATIONS', config_module.DEX_REVERSAL_MIN_CONFIRMATIONS)

    use_dynamic_second_tp = bool(parameters.get('USE_DYNAMIC_SECOND_TP', config_module.USE_DYNAMIC_SECOND_TP))
    adaptive_atr_period = parameters.get('ADAPTIVE_ATR_PERIOD', config_module.ADAPTIVE_ATR_PERIOD)
    rsi_period = parameters.get('RSI_PERIOD', config_module.RSI_PERIOD)
    adaptive_rsi_strong = parameters.get('ADAPTIVE_RSI_STRONG_LEVEL', config_module.ADAPTIVE_RSI_STRONG_LEVEL)
    adaptive_rsi_extreme = parameters.get('ADAPTIVE_RSI_EXTREME_LEVEL', config_module.ADAPTIVE_RSI_EXTREME_LEVEL)
    adaptive_atr_base_mult = parameters.get('ADAPTIVE_ATR_BASE_MULTIPLIER', config_module.ADAPTIVE_ATR_BASE_MULTIPLIER)
    adaptive_atr_strong_mult = parameters.get('ADAPTIVE_ATR_STRONG_MULTIPLIER', config_module.ADAPTIVE_ATR_STRONG_MULTIPLIER)
    adaptive_atr_extreme_mult = parameters.get('ADAPTIVE_ATR_EXTREME_MULTIPLIER', config_module.ADAPTIVE_ATR_EXTREME_MULTIPLIER)

    # --- 3. Simulation State Initialization ---
    current_sol, trade_history, active_position = initial_capital, [], None
    simulated_active_cooldowns: Dict[str, datetime] = {}

    # --- 4. Main Simulation Loop ---
    for timestamp in df.index:
        try:
            row = df.loc[timestamp]
            price, high_price, volume = float(row["Close"]), float(row["High"]), float(row["Volume"])
            market_cap_sol, rugcheck_score = float(row.get("market_cap_calculated", 0.0)), int(row.get("rugcheck_score", 10000))
            socials_score, volatility_val = int(row.get("socials_score", 100)), float(row.get("volatility", 0.0))
            pre_existing_cooldown_until_data = pd.to_datetime(row.get('cooldown_until'), errors='coerce', utc=True)
            is_migrated_token = dexscreener_snapshot_data is not None and not dexscreener_snapshot_data.empty

            # --- 4a. Sell Logic ---
            if active_position:
                pos = active_position
                # Update the highest price seen since the buy
                pos['highest_price'] = max(pos['highest_price'], high_price)

                # Initialize sell trigger variables for the current timestep
                sell_reason, sell_all, sell_partial, sell_percentage = None, False, False, 0.0

                # --- Stage 1: Logic before the first take-profit is hit ---
                if not pos['first_tp_hit']:
                    if price <= pos['stop_loss_price']:
                        sell_reason, sell_all, sell_percentage = "🛑 Stop Loss", True, 1.0
                    # A very high TP can still be hit before the first one
                    elif price >= pos['second_tp_price']:
                        sell_reason, sell_all, sell_percentage = "Second TP", True, 1.0
                    # Check for the first take-profit
                    elif price >= pos['initial_tp_price']:
                        sell_reason, sell_partial, sell_percentage = "First TP", True, first_sell_percent / 100.0

                # --- Stage 2: Logic after the first take-profit has been hit ---
                else:
                    # --- DYNAMIC SELL LOGIC BRANCH ---
                    if use_dynamic_second_tp:
                        # Use the Adaptive Chandelier Exit logic
                        atr_col = f"ATRr_{adaptive_atr_period}"
                        rsi_col = f"RSI_{rsi_period}"

                        if atr_col in row and rsi_col in row and pd.notna(row[atr_col]) and pd.notna(row[rsi_col]):
                            # Determine the adaptive ATR multiplier based on RSI
                            multiplier = adaptive_atr_base_mult
                            if row[rsi_col] >= adaptive_rsi_extreme:
                                multiplier = adaptive_atr_extreme_mult
                            elif row[rsi_col] >= adaptive_rsi_strong:
                                multiplier = adaptive_atr_strong_mult

                            # Calculate the dynamic exit price
                            chandelier_exit_price = pos['highest_price'] - (multiplier * row[atr_col])

                            if price < chandelier_exit_price:
                                sell_reason = "Dynamic Exit (Chandelier)"
                                sell_all = True
                                sell_percentage = 1.0

                    # --- Original Trailing SL logic (fallback if dynamic TP is off or indicators fail) ---
                    if not sell_reason:
                        trailing_sl_price = pos['highest_price'] * (1.0 - trailing_stop_loss_percent / 100.0)
                        if price >= pos['second_tp_price']:
                            sell_reason, sell_all, sell_percentage = "Second TP", True, 1.0
                        elif price <= trailing_sl_price:
                            sell_reason, sell_all, sell_percentage = "↘️ Trailing SL", True, 1.0

                    # The breakeven stop loss is always active after the first TP is hit
                    if not sell_reason and price <= pos['stop_loss_price']:
                        sell_reason, sell_all, sell_percentage = "🛡️ Breakeven SL", True, 1.0

                # --- Emergency Sell Conditions (checked at every step) ---
                if not sell_reason:
                    initial_mcap_sol = pos.get('initial_market_cap_sol', 0.0)
                    mc_drop_threshold_percent = parameters.get('MC_DROP_THRESHOLD', 5.0)

                    if market_cap_sol < min_emergency_mcap_usd:
                        sell_reason, sell_all, sell_percentage = "🆘 Emergency SL (MCap)", True, 1.0
                    elif initial_mcap_sol > 0 and market_cap_sol < (initial_mcap_sol * (1 - mc_drop_threshold_percent / 100.0)):
                        sell_reason, sell_all, sell_percentage = "🆘 Emergency SL (MC Drop%)", True, 1.0
                    elif is_migrated_token and volume <= 0:
                        sell_reason, sell_all, sell_percentage = "🆘 Emergency SL (No Volume)", True, 1.0

                # --- Execute Sell Action if a reason was triggered ---
                if sell_reason:
                    # Determine how many tokens to sell based on the trigger
                    tokens_to_sell = (pos['initial_tokens'] * sell_percentage) if sell_partial else (pos['remaining_tokens'] * sell_percentage)
                    tokens_to_sell = min(tokens_to_sell, pos['remaining_tokens']) # Cannot sell more than held

                    if tokens_to_sell > 1e-9: # Ensure there's a non-trivial amount to sell
                        # Simulate the transaction
                        net_sol = (tokens_to_sell * price) - sell_fee - sell_tip
                        cost_basis = pos['total_investment_sol'] * (tokens_to_sell / pos['initial_tokens']) if pos['initial_tokens'] > 0 else 0
                        pnl = net_sol - cost_basis

                        # Update portfolio state
                        current_sol += net_sol
                        pos['remaining_tokens'] -= tokens_to_sell

                        # Log the trade
                        trade_history.append({'timestamp': timestamp, 'type': 'sell', 'price': price, 'amount_sol': net_sol, 'amount_tokens': tokens_to_sell, 'reason': sell_reason, 'pnl': pnl, 'mint': mint_addr})

                        # Update position state after a partial sell (First TP)
                        if sell_partial:
                            pos['first_tp_hit'] = True
                            pos['stop_loss_price'] = pos['buy_price'] # Move SL to breakeven

                        # Close the position if all tokens are sold
                        if pos['remaining_tokens'] < 1e-9:
                            active_position = None

                        # Apply cooldown period for stop-loss related sells
                        if stop_loss_cooldown_minutes_ga > 0 and any(trigger in sell_reason for trigger in apply_trend_reversal_on_sell_reasons_config):
                            cooldown_end_ts = timestamp + pd.Timedelta(minutes=stop_loss_cooldown_minutes_ga)
                            simulated_active_cooldowns[mint_addr] = cooldown_end_ts

            # --- 4b. Buy Logic ---
            elif not active_position and current_sol >= (sol_to_buy + buy_fee + buy_tip):
                is_on_pre_existing_cooldown = pd.notna(pre_existing_cooldown_until_data) and timestamp < pre_existing_cooldown_until_data
                simulated_cooldown_end_ts = simulated_active_cooldowns.get(mint_addr)
                is_on_simulated_cooldown = simulated_cooldown_end_ts and timestamp < simulated_cooldown_end_ts
                if is_on_pre_existing_cooldown or is_on_simulated_cooldown: continue

                meets_standard_criteria = (volume >= volume_threshold and market_cap_sol >= marketcap_threshold and rugcheck_score < rugcheck_threshold and socials_score < socials_threshold and volatility_val >= min_volatility)
                proceed_with_buy_attempt = False

                if not meets_standard_criteria:
                    proceed_with_buy_attempt = False
                elif use_trend_reversal:
                    was_recently_sold_for_reversal_reason = False
                    if trade_history:
                        for trade in reversed(trade_history):
                            if trade.get('mint') == mint_addr and trade.get('type') == 'sell':
                                if (timestamp - trade['timestamp']) <= pd.Timedelta(hours=trend_reversal_recency_hours_ga):
                                    if any(reason in trade.get('reason', '') for reason in apply_trend_reversal_on_sell_reasons_config):
                                        was_recently_sold_for_reversal_reason = True; break
                                else: break
                    if was_recently_sold_for_reversal_reason:
                        if is_migrated_token:
                            lookback_start_ts = timestamp - pd.Timedelta(minutes=dex_lookback_mins)
                            mask = (dexscreener_snapshot_data.index <= timestamp) & (dexscreener_snapshot_data.index >= lookback_start_ts)
                            snapshots = dexscreener_snapshot_data.loc[mask]
                            if len(snapshots) < dex_min_snapshots: proceed_with_buy_attempt = False
                            elif float(snapshots.iloc[-1]['liquidity_usd']) < dex_min_liquidity: proceed_with_buy_attempt = False
                            else:
                                confirmations = sum(1 for _, s in snapshots.iterrows() if s.get('buys_m5', 0) > 0 and (s.get('sells_m5', 0) == 0 or (s.get('buys_m5', 0) / s.get('sells_m5', 0)) >= dex_min_ratio))
                                if confirmations >= dex_min_confirmations:
                                    proceed_with_buy_attempt = True
                                else: proceed_with_buy_attempt = False
                        else:
                            current_loc = df.index.get_loc(timestamp)
                            candles_for_lookback = int(indicator_lookback_hours_ga * 720)
                            start_loc = max(0, current_loc - candles_for_lookback + 1)
                            if (current_loc - start_loc + 1) >= min_candle_data_for_indicators_config:
                                indicator_slice = df.iloc[start_loc : current_loc + 1]
                                indicator_params = (rsi_period_ga, bbands_period_ga, bbands_std_dev_ga, fast_ema_period_ga, slow_ema_period_ga)
                                cache_key = (mint_addr, indicator_params)
                                if indicator_cache is not None and cache_key in indicator_cache:
                                    df_with_indicators = indicator_cache[cache_key]
                                else:
                                    # --- FIX: Add missing ADAPTIVE_ATR_PERIOD key to this config dict ---
                                    # This prevents a potential KeyError in the utility function.
                                    indicator_config = {
                                        'MIN_CANDLE_DATA_FOR_INDICATORS': min_candle_data_for_indicators_config,
                                        'RSI_PERIOD': rsi_period_ga,
                                        'BBANDS_PERIOD': bbands_period_ga,
                                        'BBANDS_STD_DEV': bbands_std_dev_ga,
                                        'FAST_EMA_PERIOD': fast_ema_period_ga,
                                        'SLOW_EMA_PERIOD': slow_ema_period_ga,
                                        'ADAPTIVE_ATR_PERIOD': adaptive_atr_period # This key was missing
                                    }
                                    # --- END FIX ---
                                    df_with_indicators = utils.calculate_trend_indicators(indicator_slice.copy(), indicator_config)
                                    if indicator_cache is not None and df_with_indicators is not None and not df_with_indicators.empty:
                                        indicator_cache[cache_key] = df_with_indicators
                                if df_with_indicators is not None and not df_with_indicators.empty and len(df_with_indicators) >= 2:
                                    latest, prev = df_with_indicators.iloc[-1], df_with_indicators.iloc[-2]
                                    rsi_cross = pd.notna(latest.get('RSI')) and pd.notna(prev.get('RSI')) and latest['RSI'] > 30 and prev['RSI'] <= 30
                                    bb_lower_col = f"BBL_{bbands_period_ga}_{bbands_std_dev_ga}"
                                    bb_reenter = pd.notna(latest.get('Close')) and pd.notna(prev.get('Close')) and pd.notna(latest.get(bb_lower_col)) and pd.notna(prev.get(bb_lower_col)) and latest['Close'] > latest[bb_lower_col] and prev['Close'] <= prev[bb_lower_col]
                                    stage1 = rsi_cross or bb_reenter or (pd.notna(latest.get('RSI')) and latest['RSI'] > trend_reversal_rsi_neutral_level_ga)
                                    if stage1:
                                        vwap_ok = pd.notna(latest.get('VWAP')) and latest['Close'] > latest['VWAP']
                                        ema_ok = pd.notna(latest.get('EMA_fast')) and pd.notna(latest.get('EMA_slow')) and latest['EMA_fast'] > latest['EMA_slow']
                                        if vwap_ok and ema_ok: proceed_with_buy_attempt = True
                    else:
                        proceed_with_buy_attempt = True
                else:
                    proceed_with_buy_attempt = meets_standard_criteria

                if proceed_with_buy_attempt:
                    total_investment, sol_for_tokens = sol_to_buy + buy_fee + buy_tip, sol_to_buy
                    tokens_bought = sol_for_tokens / price if price > 0 else 0
                    if tokens_bought > 0:
                        initial_sl = price * (1.0 - initial_stop_loss_percent / 100.0)
                        cost_tp1 = total_investment * (first_sell_percent / 100.0)
                        profit_tp1 = cost_tp1 * (first_sell_profit_margin / 100.0)
                        gross_needed_tp1 = cost_tp1 + profit_tp1 + sell_fee + sell_tip
                        tokens_tp1 = tokens_bought * (first_sell_percent / 100.0)
                        initial_tp = (gross_needed_tp1 / tokens_tp1) if tokens_tp1 > 1e-9 else float('inf')
                        second_tp = price * (1.0 + second_take_profit_percent / 100.0)
                        current_sol -= total_investment
                        active_position = {
                            'buy_price': price,
                            'initial_tokens': tokens_bought,
                            'remaining_tokens': tokens_bought,
                            'total_investment_sol': total_investment,
                            'stop_loss_price': initial_sl,
                            'initial_tp_price': initial_tp,
                            'second_tp_price': second_tp,
                            'highest_price': price,
                            'first_tp_hit': False,
                            'entry_timestamp': timestamp,
                            'initial_market_cap_sol': market_cap_sol # Store the market cap at the time of buy
                        }
                        trade_history.append({'timestamp': timestamp, 'type': 'buy', 'price': price, 'amount_sol': total_investment, 'amount_tokens': tokens_bought, 'buy_fee': buy_fee, 'buy_tip': buy_tip, 'mint': mint_addr})
                        if mint_addr in simulated_active_cooldowns: del simulated_active_cooldowns[mint_addr]
        except (KeyError, ValueError) as e:
            logger.error(f"Data error at step for {mint_addr} (Timestamp: {timestamp}): {e}", exc_info=False)
            continue
        except Exception as e:
            logger.error(f"Unexpected error during simulation step for {mint_addr}: {e}", exc_info=True)
            continue

    # --- 5. Final Portfolio Valuation ---
    final_value = current_sol
    if active_position and not df.empty:
        last_candle_ts = df.index[-1]
        if end_ts_data and end_ts_data < df.index[-1]:
            valid_ts = df.index[df.index <= end_ts_data]
            if not valid_ts.empty: last_candle_ts = valid_ts[-1]
        last_close_price = float(df.loc[last_candle_ts]["Close"])
        net_sol_final = (active_position['remaining_tokens'] * last_close_price) - sell_fee - sell_tip
        final_value += max(0, net_sol_final)

    # --- 6. Return Performance Metrics ---
    metrics = calculate_performance_metrics(trade_history, initial_capital, final_value, start_ts=start_ts_data, end_ts=end_ts_data, simulation_end_reason=simulation_end_reason)
    metrics.update({
        "parameters": parameters,
        "initial_capital": initial_capital,
        "final_portfolio_value": final_value,
        "trade_history": trade_history
    })
    return metrics
