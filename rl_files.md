# `pump_trader` Project Files

📅 Generated on: 2025-05-04 23:02

📂 Project root: `C:/Users/Sascha/Documents/Projects/python/crypto/pump_trader`

---

### 📄 backtester.py

```python
# FILE: backtester.py (Modified for Lifespan & Refinements)

"""
Backtesting Engine Module

Simulates trading strategies on historical data, respecting token lifespans,
to evaluate performance.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any # Added Optional

from logger import logger

# --- Performance Metrics Calculation ---
def calculate_performance_metrics(
    trade_history: list,
    initial_capital: float,
    final_capital: float,
    start_ts: Optional[datetime] = None, # Optional start/end timestamps for context
    end_ts: Optional[datetime] = None,
    simulation_end_reason: str = "Completed" # Reason simulation stopped
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

    # Calculate PnL and Return %
    metrics["total_pnl"] = final_capital - initial_capital
    if initial_capital > 0:
        metrics["total_return_pct"] = (metrics["total_pnl"] / initial_capital) * 100.0

    # Analyze sell trades for win rate, avg profit/loss, profit factor
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
                metrics["total_loss_sells"] += abs(pnl) # Loss is positive here

        if metrics["total_trades"] > 0:
             metrics["win_rate"] = (metrics["winning_trades"] / metrics["total_trades"]) * 100.0

        if metrics["winning_trades"] > 0:
             metrics["avg_profit_per_win_trade"] = metrics["total_profit_sells"] / metrics["winning_trades"]

        if metrics["losing_trades"] > 0:
             metrics["avg_loss_per_loss_trade"] = metrics["total_loss_sells"] / metrics["losing_trades"]

        if metrics["total_loss_sells"] > 0:
             metrics["profit_factor"] = metrics["total_profit_sells"] / metrics["total_loss_sells"]
        elif metrics["total_profit_sells"] > 0:
             metrics["profit_factor"] = float('inf') # Profit but no losses


    # --- Calculate Max Drawdown ---
    # Track portfolio value over time based on trades
    portfolio_values = [initial_capital] # Start with initial capital
    current_portfolio_value = initial_capital
    peak_value = initial_capital
    max_dd = 0.0

    # Create an equity curve based on trade executions
    equity_curve = pd.Series(index=[], dtype=float)
    if trade_history:
        # Use the timestamp of the first trade, or the simulation start if available
        first_ts = trade_history[0]['timestamp']
        equity_curve.loc[start_ts if start_ts and start_ts < first_ts else first_ts] = initial_capital # Start point

    for trade in trade_history:
        trade_ts = trade['timestamp']
        if trade['type'] == 'buy':
            # Value decreases by investment cost just before buy
            equity_curve.loc[trade_ts - pd.Timedelta(nanoseconds=1)] = current_portfolio_value
            current_portfolio_value -= trade.get('amount_sol', 0)
            equity_curve.loc[trade_ts] = current_portfolio_value
        elif trade['type'] == 'sell':
            # Value increases by net SOL received just before sell
            equity_curve.loc[trade_ts - pd.Timedelta(nanoseconds=1)] = current_portfolio_value
            current_portfolio_value += trade.get('amount_sol', 0)
            equity_curve.loc[trade_ts] = current_portfolio_value

    # Add final capital point if simulation ended and value changed since last trade
    if end_ts:
        if not equity_curve.empty and equity_curve.index[-1] < end_ts:
             equity_curve.loc[end_ts] = final_capital
        elif equity_curve.empty: # Handle case with no trades
             equity_curve.loc[start_ts if start_ts else datetime.now(timezone.utc)] = initial_capital
             equity_curve.loc[end_ts] = final_capital


    # Ensure chronological order and remove duplicates keeping last value
    if not equity_curve.empty:
        equity_curve = equity_curve.sort_index()
        equity_curve = equity_curve[~equity_curve.index.duplicated(keep='last')]

        # Calculate drawdown from the equity curve
        roll_max = equity_curve.cummax()
        drawdown = (roll_max - equity_curve) / roll_max
        max_dd = drawdown.max() if not drawdown.empty else 0.0 # Handle empty drawdown case

    metrics["max_drawdown"] = max_dd * 100.0 # Store as percentage

    return metrics

# --- Backtesting Core Function ---
async def run_backtest(
    parameters: dict,
    ohlcv_data: pd.DataFrame, # Renamed: Expects pre-processed OHLCV data
    initial_capital: float,
    max_timestamp: Optional[datetime] = None # Token death timestamp
) -> dict:
    """
    Simulates trading with 5-second OHLCV candlestick data, respecting token lifespan.

    Args:
        parameters: Dictionary of trading parameters for this simulation run.
        ohlcv_data: DataFrame containing historical 5s OHLCV data for the token.
                    Index must be a timezone-aware UTC DatetimeIndex.
                    Expected columns: 'Open', 'High', 'Low', 'Close', 'Volume',
                                      'market_cap_calculated', 'rugcheck_score', 'socials_score'.
        initial_capital: Starting capital in SOL.
        max_timestamp: Optional UTC timestamp indicating the end of the token's
                       life. Simulation will stop at or before this time.

    Returns:
        A dictionary containing performance metrics calculated by
        `calculate_performance_metrics`.
    """
    mint_addr = parameters.get("mint", "UNKNOWN_MINT") # Get mint for logging if passed in params
    simulation_end_reason = "Completed" # Default end reason

    # --- Log Entry and Initial Checks ---
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

    # --- Prepare Data ---
    df = ohlcv_data.copy() # Use the input OHLCV data directly
    df = df.sort_index() # Ensure chronological order

    # Filter data up to max_timestamp if provided
    start_ts_data = df.index.min()
    end_ts_data = df.index.max()
    if max_timestamp:
        if max_timestamp.tzinfo is None:
             max_timestamp = max_timestamp.replace(tzinfo=timezone.utc)
        df = df[df.index <= max_timestamp]
        end_ts_data = max_timestamp # The effective end time is the token death time
        simulation_end_reason = "Token Death"
        if df.empty:
            logger.warning(f"No data remains for {mint_addr} after filtering up to max_timestamp {max_timestamp}.")
            return calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, simulation_end_reason)

    # --- Data Validation (Check for required OHLCV columns) ---
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required OHLCV columns in input data for {mint_addr}: {missing_cols}")
        return calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, "Missing OHLCV Cols")

    # --- Convert Columns to Numeric (Coerce errors) ---
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Fill NaNs that might result from coercion or were already present
    # Use ffill/bfill for price-like columns, 0 for volume/scores
    price_cols = ['Open', 'High', 'Low', 'Close', 'market_cap_calculated', 'volatility']
    df[price_cols] = df[price_cols].ffill().bfill()
    df[['Volume']] = df[['Volume']].fillna(0.0)
    df[['rugcheck_score', 'socials_score']] = df[[ 'rugcheck_score', 'socials_score']].fillna(1000.0)

    # Ensure no invalid prices remain after filling (use Close price as primary)
    df = df[df["Close"] > 1e-12] # Use epsilon

    # --- Calculate Volatility ---
    # Calculate based on the 'Close' price series
    # if not df.empty and 'Close' in df.columns:
    #     prices_series = df['Close'] # Use the 'Close' price
    #     if len(prices_series) > 1:
    #          # Ensure index is DatetimeIndex before passing
    #          if not isinstance(prices_series.index, pd.DatetimeIndex):
    #               prices_series.index = pd.to_datetime(prices_series.index, utc=True)

    #          # Use appropriate window (e.g., 10 minutes = 120 * 5s candles)
    #          df['volatility'] = calculate_volatility(prices_series, window=120).fillna(0.0)
    #     else:
    #         df['volatility'] = 0.0
    # else:
    #     df['volatility'] = 0.0 # Add column even if empty

    if df.empty:
         logger.warning(f"No candle data remained after filtering/validation for {mint_addr}.")
         return calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, "No Candle Data")
    
    # logger.debug(f"Data head:\n{df.head()}")
    # logger.debug(f"Data tail:\n{df.tail()}")

    # --- Extract Parameters (Same as before) ---
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
    min_market_cap_usd = parameters.get('_MIN_MARKET_CAP', 3600) # Emergency sell
    buy_fee = parameters.get('DEFAULT_BUY_FEE', 0.001)
    buy_tip = parameters.get('DEFAULT_BUY_TIP', 0.001)
    sell_fee = parameters.get('DEFAULT_SELL_FEE', 0.001)
    sell_tip = parameters.get('DEFAULT_SELL_TIP', 0.001)

    # --- Simulation State ---
    current_sol = initial_capital
    trade_history = []
    active_position = None # Dictionary to store buy details

    # --- Simulate Step-by-Step ---
    # Iterate directly over the OHLCV DataFrame index
    simulation_indices = df.index # Use all available 5s intervals
    total_steps = len(simulation_indices)
    log_interval = max(1, total_steps // 10)

    logger.debug(f"Starting simulation loop for {mint_addr}. Total steps: {total_steps}. Max Timestamp: {end_ts_data}")
    step_count = 0

    for timestamp in simulation_indices:
        step_count += 1
        if step_count % log_interval == 0:
             logger.debug(f"Simulating step {step_count}/{total_steps} for {mint_addr} (Timestamp: {timestamp})")

        # Timestamp should always exist as we iterate over the index
        try:
            row = df.loc[timestamp]
            # --- Use OHLCV columns ---
            price = float(row["Close"]) # Use Close price for decisions/executions
            volume = float(row["Volume"]) # Use aggregated Volume
            high_price = float(row["High"]) # Use High price for highest_price tracking
            low_price = float(row["Low"])   # Use Low price for SL check? (Using Close is simpler)
            # --- End OHLCV columns ---
            market_cap_sol = float(row.get("market_cap_calculated", 0.0))
            rugcheck_score = int(row.get("rugcheck_score", 10000))
            socials_score = int(row.get("socials_score", 100))
            volatility = float(row.get("volatility", 0.0))

            # --- Check Buy/Sell Logic ---

            # --- Sell Logic ---
            if active_position:
                pos = active_position
                # Update highest price using the High of the current candle
                hp = max(pos['highest_price'], high_price)
                pos['highest_price'] = hp

                # Calculate current sell trigger prices based on active position
                current_stop_loss_price = pos['stop_loss_price']
                initial_tp_price = pos['initial_tp_price']
                second_tp_price = pos['second_tp_price']
                first_tp_hit = pos['first_tp_hit']

                trailing_sl_price = 0.0
                if first_tp_hit:
                    trailing_sl_price = hp * (1.0 - trailing_stop_loss_percent / 100.0)

                # Determine sell reason (using Close price for checks)
                sell_reason = None
                sell_all = False; sell_partial = False
                sell_percentage = 0.0 # Percentage of initial tokens

                # Check SL/TP using Close price
                if price <= current_stop_loss_price:
                    sell_reason = "Stop Loss" if not first_tp_hit else "Breakeven SL"; sell_all = True; sell_percentage = 1.0
                elif price >= second_tp_price:
                    sell_reason = "Second TP"; sell_all = True; sell_percentage = 1.0
                elif not first_tp_hit and price >= initial_tp_price:
                    sell_reason = "First TP"; sell_partial = True; sell_percentage = first_sell_percent / 100.0
                elif first_tp_hit and price <= trailing_sl_price:
                    sell_reason = "Trailing SL"; sell_all = True; sell_percentage = 1.0
                # Emergency SL (requires SOL price - not implemented here for simplicity)
                # elif (market_cap_sol * sol_price_live) < min_market_cap_usd:
                #    sell_reason = "Emergency SL"; sell_all = True; sell_percentage = 1.0

                # --- Execute Sell ---
                if sell_reason:
                    initial_tokens = pos['initial_tokens']
                    remaining_tokens = pos['remaining_tokens']
                    total_investment = pos['total_investment_sol']
                    tokens_to_sell = 0.0

                    if sell_partial:
                        tokens_to_sell = initial_tokens * sell_percentage
                        tokens_to_sell = min(tokens_to_sell, remaining_tokens)
                    elif sell_all:
                        tokens_to_sell = remaining_tokens

                    if tokens_to_sell > 1e-9:
                        # Simulate sale using the Close price of the interval
                        gross_sol = tokens_to_sell * price
                        net_sol = gross_sol - sell_fee - sell_tip
                        cost_basis = total_investment * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                        pnl = net_sol - cost_basis

                        current_sol += net_sol
                        pos['remaining_tokens'] -= tokens_to_sell

                        trade_history.append({
                            'timestamp': timestamp, 'type': 'sell', 'price': price,
                            'amount_sol': net_sol, 'amount_tokens': tokens_to_sell,
                            'reason': sell_reason, 'pnl': pnl
                        })

                        if sell_partial:
                            pos['first_tp_hit'] = True
                            pos['stop_loss_price'] = pos['buy_price'] # Adjust SL to breakeven

                        if pos['remaining_tokens'] < 1e-9:
                            active_position = None # Close position fully

            # --- Buy Logic ---
            elif not active_position and current_sol >= (sol_to_buy + buy_fee + buy_tip):
                # Check buy criteria using current candle data (Volume, Close price)
                meets_buy_criteria = (
                    volume >= volume_threshold and # Use aggregated Volume
                    market_cap_sol >= marketcap_threshold and
                    rugcheck_score < rugcheck_threshold and
                    socials_score < socials_threshold and
                    volatility >= min_volatility
                )
                # logger.debug(f"Buy criteria for {mint_addr} at {timestamp}: \n")
                # logger.debug(f"Volume={volume_threshold} - {volume}")
                # logger.debug(f"MarketCap={marketcap_threshold} - {market_cap_sol}")
                # logger.debug(f"Volatility={min_volatility} - {volatility}")
                # logger.debug(f"RugCheck={rugcheck_threshold} - {rugcheck_score}")
                # logger.debug(f"Socials={socials_threshold} - {socials_score}")


                if meets_buy_criteria:
                    total_investment = sol_to_buy + buy_fee + buy_tip
                    sol_for_tokens = sol_to_buy
                    # Simulate buy using Close price
                    tokens_bought = sol_for_tokens / price if price > 0 else 0

                    if tokens_bought > 0:
                        # Calculate initial SL/TPs based on Close price
                        initial_sl_price = price * (1.0 - initial_stop_loss_percent / 100.0)

                        sell_fee_tp1 = sell_fee
                        sell_tip_tp1 = sell_tip
                        profit_margin_tp1 = first_sell_profit_margin / 100.0
                        sell_percent_tp1 = first_sell_percent / 100.0

                        total_cost_base_tp1 = total_investment + sell_fee_tp1 + sell_tip_tp1
                        target_net_sol_return_tp1 = total_cost_base_tp1 * (1 + profit_margin_tp1)
                        target_gross_sol_return_tp1 = target_net_sol_return_tp1 + sell_fee_tp1 + sell_tip_tp1
                        tokens_to_sell_tp1 = tokens_bought * sell_percent_tp1
                        initial_tp_price = (target_gross_sol_return_tp1 / tokens_to_sell_tp1) if tokens_to_sell_tp1 > 1e-9 else float('inf')

                        second_tp_price = price * (1.0 + second_take_profit_percent / 100.0)

                        # --- Update State ---
                        current_sol -= total_investment
                        active_position = {
                            'buy_price': price, 'initial_tokens': tokens_bought,
                            'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment,
                            'stop_loss_price': initial_sl_price, 'initial_tp_price': initial_tp_price,
                            'second_tp_price': second_tp_price, 'highest_price': price, # Initialize highest with buy price
                            'first_tp_hit': False, 'entry_timestamp': timestamp
                        }

                        trade_history.append({
                            'timestamp': timestamp, 'type': 'buy', 'price': price,
                            'amount_sol': total_investment, 'amount_tokens': tokens_bought,
                            'buy_fee': buy_fee, 'buy_tip': buy_tip
                        })

        except KeyError as ke:
            logger.error(f"KeyError accessing data at step {step_count} for {mint_addr} (Timestamp: {timestamp}): Missing key {ke}", exc_info=False)
            continue # Skip this step
        except ValueError as ve:
             logger.error(f"ValueError at step {step_count} for {mint_addr} (Timestamp: {timestamp}): {ve}", exc_info=False)
             continue # Skip this step
        except Exception as loop_err:
             logger.error(f"Error during simulation step {step_count} for {mint_addr} (Timestamp: {timestamp}): {loop_err}", exc_info=True)
             continue

    # --- Simulation End ---
    logger.debug(f"Simulation loop finished for {mint_addr} at step {step_count}.")

    # --- Final Value Calculation ---
    final_value = current_sol
    if active_position:
        # Use the Close price from the *last available candle* in the filtered df
        if not df.empty:
            last_valid_index = df.index[-1]
            last_close_price = float(df.loc[last_valid_index]["Close"]) # Use Close price

            remaining_tokens = active_position['remaining_tokens']
            gross_sol_final = remaining_tokens * last_close_price
            net_sol_final = gross_sol_final - sell_fee - sell_tip
            final_value += max(0, net_sol_final)
            logger.debug(f"Added value of remaining {remaining_tokens:.4f} tokens for {mint_addr} at final Close price {last_close_price:.9f} (Net: {net_sol_final:.6f})")
        else:
             logger.warning(f"No data available to value remaining position for {mint_addr}. Using current SOL only.")

    # --- Calculate Metrics ---
    logger.debug(f"Calculating final performance metrics for {mint_addr}")
    metrics = calculate_performance_metrics(
        trade_history,
        initial_capital,
        final_value,
        start_ts=start_ts_data,
        end_ts=end_ts_data,
        simulation_end_reason=simulation_end_reason
    )
    metrics["parameters"] = parameters
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
    from logger import setup_logging

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
    from logger import setup_logging
    setup_logging()
    asyncio.run(main_test())
```

---

### 📄 config.py

```python
"""
Configuration constants and settings for the trading bot.
"""

# Trading configuration
SOL_TO_BUY = 0.9                            # Amount of SOL to spend on each buy
_INITIAL_SOL_BALANCE = 100.0                  # Starting SOL balance for PnL tracking
PLAY_BUY_SOUND = True                      # Play the buy sound when a buy is made
PLAY_SELL_SOUND = True                     # Play the sell sound when a sell is made

# --- New Multi-Stage Sell Logic Configuration ---
INITIAL_STOP_LOSS_PERCENT = 10.0            # Initial SL as % below buy price (e.g., 25.0 for -25%)
# INITIAL_TAKE_PROFIT_PERCENT is removed as TP1 price is now calculated based on investment, costs, and margin.
FIRST_SELL_PERCENT = 65.0                   # % of *initial* tokens to sell at First TP (e.g., 50.0 for 50%)
TRAILING_STOP_LOSS_PERCENT = 15.0           # Trailing SL % drop from highest price *after* First TP (e.g., 15.0 for -15%)
SECOND_TAKE_PROFIT_PERCENT = 550.0          # Second TP as % above buy price (e.g., 200.0 for +200%)
FIRST_SELL_PROFIT_MARGIN = 170.0             # Desired profit margin % on the *total initial investment* for the first TP sell

# --- Fees and Tips ---
DEFAULT_BUY_FEE = 0.001                     # Fee for buying in SOL
DEFAULT_BUY_TIP = 0.001                     # Tip for buying in SOL
DEFAULT_SELL_FEE = 0.001                    # Fee for selling in SOL
DEFAULT_SELL_TIP = 0.001                    # Tip for selling in SOL

# Trading thresholds
DEFAULT_RUGCHECK_SCORE_THRESHOLD = 801      # No trading if Rugcheck score is equal or above this threshold
DEFAULT_SOCIAL_SCORE_THRESHOLD = 50         # No trading if Social score is equal or above this threshold
DEFAULT_VOLUME_THRESHOLD = 19000            # Minimum volume threshold in USD
MIN_MARKETCAP_THRESHOLD = 6000              # Minimum market cap threshold in USD to make emergency sell
DEFAULT_MARKETCAP_THRESHOLD = 10000         # Minimum market cap threshold in USD to search for buy opportunities
MIN_VOLATILITY = 0.1                        # Minimum volatility threshold in % to search for buy opportunities
DEFAULT_TIME_INTERVALL = 30                 # Time interval for checking volatility, volume and marketcap in minutes
MAX_DRAWDOWN_SOL = 10                       # Maximum allowed 24h loss in SOL (not integrated)
DRAWDOWN_CHECK_INTERVAL = 3600              # Drawdown check interval (seconds) (not integrated)

# UNSUBSCRIBING CONDITIONS
INACTIVITY_PERIOD = 10                      # Inactivity period in minutes before unsubscribing
MIN_MARKET_CAP = 3600                       # Minimum market cap (in USD) - for unsubscription & backup

# Subscription tracking
ACTIVE_SUBSCRIPTIONS = set()                # leave it alone ... can be deleted?
NEW_TOKEN_SUBSCRIPTION = False              # leave it alone ... can be deleted?

# PumpPortal
_WS_HOST: str = "wss://pumpportal.fun/api/data" # can be deleted?
_MAX_SUBSCRIPTION_BATCH: int = 100           # For batch unsubscription ... can be deleted?

# Token and API configurations
_TOTAL_SUPPLY = 1000000000                   # Assumed total supply if not provided
_PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"

_RUGCHECK_AUTH_API = "https://api.rugcheck.xyz/auth/login/solana"
_RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens"
_RUGCHECK_RATE_LIMIT = 10                    # 10 requests per minute
_RUGCHECK_INTERVAL = 60                      # 60 seconds interval for RugCheck checks
RUGCHECK_SCORE_THRESHOLD = 1002             # Score above which a token is considered high risk and deactivated

# SOL price configuration
_SOL_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# Logging
_LOGGER_NAME = "TradingBot"
_LOG_LEVEL_CONSOLE: str = "DEBUG"
_LOG_LEVEL_FILE: str = "DEBUG"
_LOG_STORAGE_PATH: str = "log"

# --- Socials Processor Configuration ---
SOCIALS_CHECK_REFRESH_INTERVAL = 60                  # Timeout for requeing socials check in minutes
SOCIALS_DISALLOWED_WEBSITE_DOMAINS = {
    "youtube.com", "youtu.be", "tiktok.com", "spotify.com", "soundcloud.com",
    "discord.com", "discord.gg", "medium.com", "substack.com", "linktr.ee",
    "t.me", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "reddit.com", "twitch.tv", "kick.com", "google.com",
}
SOCIALS_ALLOWED_NEWS_DOMAINS = {
    "bbc.com", "cnn.com", "reuters.com", "apnews.com", "nytimes.com",
    "washingtonpost.com", "theguardian.com", "bloomberg.com", "forbes.com",
    "wsj.com", "ft.com", "npr.org", "cnbc.com", "abcnews.go.com",
    "nbcnews.com", "cbsnews.com", "latimes.com", "usatoday.com",
    "politico.com", "aljazeera.com", "theatlantic.com", "newsweek.com",
    "time.com", "economist.com", "sky.com", "independent.co.uk",
    "telegraph.co.uk", "dailymail.co.uk", "mirror.co.uk", "huffpost.com",
    "vox.com", "slate.com", "buzzfeednews.com", "axios.com", "thehill.com",
    "scmp.com", "japantimes.co.jp", "hindustantimes.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "straitstimes.com", "smh.com.au",
    "theage.com.au", "globalnews.ca", "cbc.ca", "bitcointalk.org",
    "cnbcnews.us", "truthsocial.com"
}

# Penalties (Higher = Worse)
SOCIALS_PENALTY_NO_WEBSITE = 40
SOCIALS_PENALTY_INVALID_WEBSITE_TYPE = 35
SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED = 35
SOCIALS_PENALTY_WEBSITE_INVALID_URL = 35
SOCIALS_PENALTY_WEBSITE_TIMEOUT = 35
SOCIALS_PENALTY_WEBSITE_HTTP_ERROR = 35
SOCIALS_PENALTY_WEBSITE_OTHER_ERROR = 35
SOCIALS_PENALTY_NO_HTTPS = 10
SOCIALS_PENALTY_WEBSITE_NO_MENTION = 10         # No mention of token name or symbol in website
SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE = 25    # Common platforms like Youtube, TikTok, etc. 'SOCIALS_DISALLOWED_WEBSITE_DOMAINS'
SOCIALS_PENALTY_NO_TELEGRAM = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_URL = 25
SOCIALS_PENALTY_NO_TWITTER = 25
SOCIALS_PENALTY_INVALID_TWITTER_TYPE = 25
SOCIALS_PENALTY_INVALID_TWITTER_URL = 25
SOCIALS_PENALTY_DUPLICATE_LINKS = 15            # Duplicate links in metadata
SOCIALS_PENALTY_ACTION_TRIGGER_URL = 15         # Action trigger URL in metadata

# Bonuses (Negative = Better)
SOCIALS_BONUS_DOMAIN_MATCH = -10                # Bonus if domain mentions token name or symbol
SOCIALS_BONUS_NEWS_GOV_WEBSITE = 0              # No penalty/bonus currently applied for news/gov sites in 'SOCIALS_ALLOWED_NEWS_DOMAINS'

# Default Scores
SOCIALS_SCORE_FAILED_METADATA = 100             # Score assigned if metadata fetch fails
```

---

### 📄 database_handler.py

```python
"""
Database module.
Handles PostgreSQL connections and CRUD operations.
"""

import os
import glob
from datetime import datetime, timezone,timedelta
import asyncio
import asyncpg
import aiofiles
import json
import pandas as pd
from dotenv import load_dotenv
from logger import logger
from config import _TOTAL_SUPPLY
import config as base_config_module
from state_manager import GlobalState
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple # Added List, Tuple
from utils import calculate_volatility
import inspect 

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

class DatabaseClient:
    """Client to manage database connections and operations."""

    _DEFAULT_CONFIG = _config_module_to_dict(base_config_module)
    
    def __init__(self, config_dict: Optional[dict] = None):
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

                    if token_count > 2:
                            logger.debug(f"🤬 [bold red]Suspicious creator[/bold red] %s for token %s with %s tokens in 7 days", creator, data['mint'], token_count)
                            return False

                    sol_price = await self.state.get_sol_price()
                    if sol_price is None or sol_price <= 0:
                        logger.warning(f"⚠ Invalid SOL_PRICE ({sol_price}); skipping insert token operation.")
                        return # Cannot proceed without valid SOL price
                    
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
                        data.get('name'),
                        data.get('symbol'), 
                        data.get('uri'),
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
                            signature, mint, tx_type, token_amount, sol_amount, price,
                            bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
                            marketCapSol,sol_price_usd, market_cap_calculated, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
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

    async def get_tokens_to_unsubscribe(self, sol_price, min_market_cap):
        """Fetch tokens that should be unsubscribed based on market cap and activity."""
        query = """
            SELECT t.mint
            FROM tokens t
            INNER JOIN (
                SELECT mint, marketCapSol, timestamp AS lt,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM trades
            ) latest ON t.mint = latest.mint AND latest.rn = 1
            WHERE 
                ((latest.marketCapSol * $1) < $2 AND
                t.timestamp <= NOW() - INTERVAL '15 minutes') OR
				latest.lt <= NOW() - INTERVAL '60 minutes'
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
			ORDER BY timestamp DESC
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, sol_price, min_market_cap)

    async def get_active_tokens(self, limit: int = 1000):
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
        
    async def get_total_supply(self, mint: str):
        """Fetch the total supply of a token."""
        query = """
            SELECT total_supply FROM rugcheck WHERE mint = $1
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, mint)
            return result['total_supply'] if result else _TOTAL_SUPPLY


    async def find_trading_opportunities(self, sol_price: float, volume_threshold: float, marketcap_threshold: float, rugcheck_threshold: int, social_score_threshold: int, time_interval_minutes: int, min_volatility: float):
        """
        Identify potential token buy opportunities based on trading activity, volatility, and risk metrics.
        
        Criteria:
        - Analyzes trades within a rolling time window ($6 minutes)
        - Filters by volume, market cap, volatility, and risk scores
        - Excludes tokens already in active portfolio positions

        CTEs:
        1. LatestTradeData: Gets most recent trade price/status for each token
            - Uses row_number() to select latest trade per mint
        2. RecentTrades: Calculates buy/sell volume and trade count
            - total_buys_recent: SOL spent on buys
            - total_sells_recent: SOL received from sells
            - volume_recent: Total trading volume (SOL)
        3. VolatilityData: Computes price volatility using log returns
            - log_return = LN(price/previous_price)
            - volatility = STDDEV(log_return) * SQRT(return_count)
            - Requires min 5 valid returns

        Main Query:
        - Joins token data with rugcheck scores and latest trade metrics
        - Converts SOL values to USD using $1 (SOL price)
        - Filters tokens where:
            * rugcheck_score < $4 AND socials_score < $5
            * (volume_recent * SOL_price) >= volume_threshold
            * (market_cap * SOL_price) >= marketcap_threshold
            * volatility >= min_volatility
            * NOT already in active portfolio positions
        - Orders by descending recent volume

        Parameters (Bound in Query):
        $1: sol_price (float)           - Current SOL/USD price for conversions
        $2: volume_threshold (float)    - Min USD trading volume requirement
        $3: marketcap_threshold (float) - Min USD market cap requirement
        $4: rugcheck_threshold (float)  - Max allowed security risk score
        $5: social_score_threshold (float) - Max allowed social risk score
        $6: time_interval_minutes (int) - Analysis window duration (minutes)
        $7: min_volatility (float)      - Min price volatility requirement

        Volatility Calculation:
        Computed as standard deviation of log returns multiplied by sqrt(n):
        volatility = STDDEV(LN(price/prev_price)) * SQRT(GREATEST(COUNT(*), 1))
        - Uses natural log for continuous compounding returns
        - Multiplied by sqrt(n) to estimate volatility over full time window
        - Requires min 5 valid price changes

        Returns:
        List of candidate tokens sorted by volume, with metrics including:
        - Latest price, market cap, bonding curve balances
        - Recent volume/volatility metrics
        - Token metadata and risk scores
        """
        
        query = """
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
                WHERE timestamp >= NOW() - ($6 || ' minutes')::interval
            ),
            RecentTrades AS (
                SELECT
                    mint,
                    SUM(CASE WHEN tx_type = 'buy' THEN sol_amount ELSE 0 END) AS total_buys_recent,
                    SUM(CASE WHEN tx_type = 'sell' THEN sol_amount ELSE 0 END) AS total_sells_recent,
                    SUM(sol_amount) AS volume_recent,
                    COUNT(*) as trade_count
                FROM trades
                WHERE timestamp >= NOW() - ($6 || ' minutes')::interval
                GROUP BY mint
            ),
            VolatilityData AS (
                SELECT
                    mint,
                    STDDEV(log_return) * SQRT(GREATEST(COUNT(*), 1)) AS volatility
                FROM (
                    SELECT
                        mint,
                        price,
                        LAG(price) OVER (PARTITION BY mint ORDER BY timestamp) AS prev_price,
                        CASE
                            WHEN price > 0 AND LAG(price) OVER (PARTITION BY mint ORDER BY timestamp) > 0
                            THEN LN(price / LAG(price) OVER (PARTITION BY mint ORDER BY timestamp))
                            ELSE NULL
                        END AS log_return
                    FROM trades
                    WHERE timestamp >= NOW() - ($6 || ' minutes')::interval
                ) sub
                WHERE log_return IS NOT NULL
                GROUP BY mint
                HAVING COUNT(*) > 5
            )
            SELECT
                t.mint,
                t.marketCapSol,
                t.vTokensInBondingCurve,
                t.vSolInBondingCurve,
                COALESCE(ltd.marketCapSol, t.marketCapSol) AS latest_market_cap_sol,
                COALESCE(ltd.vTokensInBondingCurve, t.vTokensInBondingCurve) AS latest_v_tokens,
                COALESCE(ltd.vSolInBondingCurve, t.vSolInBondingCurve) AS latest_v_sol,
                COALESCE(ltd.price, 0) AS latest_price,
                COALESCE(rt.volume_recent, 0) AS volume_in_interval,
                COALESCE(vd.volatility, 0) AS volatility_in_interval,
                r.tokenMeta_name AS name,
                r.tokenMeta_symbol AS symbol,
                r.score AS rugcheck_score,
                t.socials_score
            FROM tokens AS t
            JOIN rugcheck AS r ON t.mint = r.mint
            JOIN LatestTradeData AS ltd ON t.mint = ltd.mint AND ltd.rn = 1
            LEFT JOIN RecentTrades AS rt ON t.mint = rt.mint
            LEFT JOIN VolatilityData AS vd ON t.mint = vd.mint
            WHERE
                t.is_active = TRUE AND
                r.score IS NOT NULL AND
                t.socials_score IS NOT NULL AND
                r.score < $4 AND
                t.socials_score < $5 AND
                (COALESCE(rt.volume_recent, 0) * $1) >= $2 AND
                (COALESCE(ltd.marketCapSol, t.marketCapSol, 0) * $1) >= $3 AND
                COALESCE(vd.volatility, 0) >= $7 AND
                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
            ORDER BY rt.volume_recent DESC;
        """
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch(query, sol_price, volume_threshold, marketcap_threshold, rugcheck_threshold, social_score_threshold, str(time_interval_minutes), min_volatility)
            except Exception as e:
                logger.error(f"Error finding trading opportunities: {e}", exc_info=True)
                return [] # Return empty list on error

    async def get_active_buy_positions(self, conn=None):
        """Fetches active buy positions from the portfolio."""
        query = '''
            SELECT id, mint, price AS buy_price, initial_tokens, remaining_tokens, total_investment_sol,
                   stop_loss_price, highest_price, initial_tp_price, second_tp_price, first_tp_hit
            FROM portfolio
            WHERE status = 'active' AND tx_type = 'buy'
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
                    price,
                    marketCapSol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                FROM trades
                WHERE mint = ANY($1::text[])
            )
            SELECT mint, price, marketCapSol FROM LatestTrades WHERE rn = 1
        '''
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, mints)
            return {row['mint']: {'price': float(row['price']), 'market_cap': float(row['marketcapsol'])}
                    for row in rows if row['price'] is not None and float(row['price']) > 0}
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

    async def get_trade_history(self, mints: list[str]):
        """Fetches price and timestamp for given mints from trades and trades_backup."""
        if not mints:
            return []
        # Ensure logger is accessible if used within the method, assuming it's defined globally or passed in
        # from logger import logger # Uncomment if logger is needed and not globally accessible
        # Use the v_trades view which combines trades and trades_backup
        query = """
            SELECT mint, price, timestamp
            FROM v_trades -- Use the view
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

    async def backup_and_delete_token(self, mint: str, archived_at: datetime):
        """Backup core table data to a corresponding backup table."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                            INSERT INTO tokens_backup SELECT *, NOW() FROM tokens WHERE mint = $1
                        ''', mint)
                        
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

                        await conn.execute("DELETE FROM tokens WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM trades WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM rugcheck WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM migrations WHERE mint = $1", mint)

                        logger.debug(f"🧹 Backup & deletion completed for {mint}")

                    except Exception as e:
                        logger.error(f"❌ Backup failed for {mint}: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f"🚨 backup_and_delete_token: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def backup_creator_wallets(self):
        """Dumps the creator_wallets table to a JSON file."""
        backup_file_path = os.path.join(os.path.dirname(__file__), "data", "creator_wallets_backup.json")
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
        ## Restore creator_wallets table from backup
        backup_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "data", 
            "creator_wallets_backup.json"
        ))
        if os.path.exists(backup_path):
            try:
                with open(backup_path, "r") as f:
                    data = json.load(f)
                
                # Generate and execute SQL statements dynamically
                for record in data:
                    wallet_address = record["wallet_address"]
                    token_count = record["token_count"]
                    last_token_time_str = f"'{record['last_token_time']}'" if record["last_token_time"] else "NULL"
                    
                    sql_line = (
                        f"INSERT INTO creator_wallets (wallet_address, token_count, last_token_time) "
                        f"VALUES ('{wallet_address}', {token_count}, {last_token_time_str}) "
                        f"ON CONFLICT (wallet_address) DO UPDATE SET token_count = GREATEST(creator_wallets.token_count, EXCLUDED.token_count), "
                        f"last_token_time = CASE WHEN EXCLUDED.token_count > creator_wallets.token_count THEN EXCLUDED.last_token_time ELSE creator_wallets.last_token_time END;"
                    )
                    async with self.pool.acquire() as conn:
                        await conn.execute(sql_line)
                
                logger.info("Loaded backup data from %s", backup_path)
            except Exception as e:
                logger.exception("Error loading backup data: %s", e)
                raise

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

    async def cleanup_db(self, cleanup_flag: bool):
        """Drop all application tables if cleanup_flag is True."""
        if cleanup_flag:
            logger.warning("🚨 Starting full database cleanup - Dropping all application tables...")
            async with self.pool.acquire() as conn:
                # List all known application tables (main and backup)
                # Add any other tables managed by the application if necessary (e.g., creator_wallets)
                tables_to_drop = [
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
                        # Insert into backup table, ignoring rows that already exist based on primary key 'id'
                        # Determine the correct primary key for conflict resolution based on table schema
                        if table == 'tokens':
                            conflict_key = 'mint'
                        elif table == 'trades':
                            conflict_key = 'signature'
                        elif table == 'rugcheck':
                            conflict_key = 'mint'
                        elif table == 'migrations':
                            conflict_key = 'signature'
                        elif table == 'portfolio':
                            table_columns = await conn.fetch(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
                            conflict_key = 'id'
                            columns = ", ".join([col for col in table_columns if col != "id"])
                            await conn.execute(f"""
                                INSERT INTO {table}_backup (id, {columns})
                                SELECT nextval('{table}_backup_id_seq'), {columns}
                                FROM {table} 
                                ORDER BY id
                                ON CONFLICT ({conflict_key}) DO NOTHING;
                            """)
                            logger.info("🗄️ Backed up table %s", table)
                            await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                            logger.info("🧹 Truncated table %s", table)
                        else:
                            # Should not happen with the current list, but add a warning
                            logger.warning(f"Unexpected table '{table}' in backup_db conflict handling.")
                            # If other tables are added later, their PK needs to be handled here.
                            # For now, skip conflict handling for unknown tables to avoid errors.
                            await conn.execute(f"INSERT INTO {table}_backup SELECT * FROM {table};") # Original insert without ON CONFLICT
                            logger.info("🗄️ Backed up table %s (without conflict check)", table)
                            await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                            continue # Skip the rest of the loop for this table

                        # Execute the INSERT with the correct ON CONFLICT clause
                        await conn.execute(f"INSERT INTO {table}_backup SELECT * FROM {table} ON CONFLICT ({conflict_key}) DO NOTHING;")
                        logger.info("🗄️ Backed up table %s", table)
                        await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                        logger.info("🧹 Truncated table %s", table)
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
            FROM v_trades
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

    def ohlcv_sql_like(self, df):
        """Aggregates trade data into OHLCV format, using pre-calculated rolling metrics."""
        # Ensure data is sorted by time within the group
        df = df.sort_values('timestamp')
        if df.empty:
            # Return a Series with expected columns and NaN/0 values if the group is empty
            return pd.Series({
                'Open': np.nan, 'High': np.nan, 'Low': np.nan, 'Close': np.nan,
                'Volume': 0.0, # Use the rolling volume name
                'market_cap_calculated': np.nan,
                'volatility': 0.0 # Use the rolling volatility name
            })

        # Use .iloc[-1] to safely get the last value, handling potential index issues
        # Use .fillna(0.0) or other appropriate defaults if iloc[-1] could be NaN
        last_rolling_volume = df['rolling_volume_sql'].iloc[-1] if not df['rolling_volume_sql'].empty else 0.0
        last_rolling_volatility = df['rolling_volatility_sql'].iloc[-1] if not df['rolling_volatility_sql'].empty else 0.0
        last_market_cap = df['market_cap_calculated'].iloc[-1] if not df['market_cap_calculated'].isnull().all() else np.nan

        return pd.Series({
            'Open': df['price'].iloc[0] if not df['price'].empty else np.nan,
            'High': df['price'].max() if not df['price'].empty else np.nan,
            'Low': df['price'].min() if not df['price'].empty else np.nan,
            'Close': df['price'].iloc[-1] if not df['price'].empty else np.nan,
            # --- MODIFIED LINES ---
            'Volume': last_rolling_volume,         # Take the LAST rolling volume in the interval
            'market_cap_calculated': last_market_cap,
            'volatility': last_rolling_volatility   # Take the LAST rolling volatility in the interval
            # --- END MODIFIED LINES ---
        })

    async def get_historical_data_for_backtesting(
            self, # Assuming this is part of the DatabaseClient class
            mints: List[str],
            start_date: datetime,
            end_date: datetime
        ) -> Dict[str, pd.DataFrame]:
            """
            Fetches comprehensive historical data for specified tokens within a date range,
            structured as 5-second OHLCV candles for backtesting.
            Calculates rolling volume and volatility similar to the SQL trading logic.
            """
            if not mints:
                logger.warning("get_historical_data_for_backtesting called with empty mints list.")
                return {}
            if not self.pool:
                logger.error("Database pool not initialized.")
                return {}

            if start_date.tzinfo is None: start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None: end_date = end_date.replace(tzinfo=timezone.utc)

            logger.info(f"Fetching historical data for {len(mints)} tokens from {start_date.isoformat()} to {end_date.isoformat()}...")

            # Fetch all necessary data within the time range
            trade_query = """
                SELECT
                    mint, timestamp, price, (sol_amount*sol_price_usd) AS volume, market_cap_calculated
                FROM v_trades
                WHERE mint = ANY($1::text[])
                AND timestamp >= $2 AND timestamp < $3
                AND price > 0 AND sol_amount IS NOT NULL AND price IS NOT NULL
                ORDER BY mint, timestamp;
            """
            rugcheck_query = """
                WITH RankedRugcheck AS (
                    SELECT
                        mint, last_checked AS timestamp, score AS rugcheck_score,
                        ROW_NUMBER() OVER (PARTITION BY mint ORDER BY last_checked DESC) as rn
                    FROM v_rugcheck
                    WHERE mint = ANY($1::text[])
                    AND last_checked < $3 -- Get checks before the period end
                )
                -- Select the latest check before the period OR any check within the period
                SELECT mint, timestamp, rugcheck_score
                FROM RankedRugcheck
                WHERE rn = 1 OR timestamp >= $2;
            """
            token_info_query = """
                WITH LatestTokenInfo AS (
                    SELECT
                        mint,
                        socials_score,
                        timestamp AS token_creation_time,
                        ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                    FROM v_tokens
                    WHERE mint = ANY($1::text[])
                    AND timestamp < $2 -- Get info created before the end_date
                )
                SELECT mint, token_creation_time, socials_score
                FROM LatestTokenInfo
                WHERE rn = 1;
            """

            results_dict = {}
            async with self.pool.acquire() as conn:
                try:
                    logger.debug("Fetching trade data...")
                    trade_records_raw = await conn.fetch(trade_query, mints, start_date, end_date)
                    logger.debug(f"Fetched {len(trade_records_raw)} raw trades.")

                    logger.debug("Fetching rugcheck data...")
                    rugcheck_records_raw = await conn.fetch(rugcheck_query, mints, start_date, end_date)
                    logger.debug(f"Fetched {len(rugcheck_records_raw)} rugchecks.")

                    logger.debug("Fetching token info data...")
                    token_info_records_raw = await conn.fetch(token_info_query, mints, end_date)
                    logger.debug(f"Fetched {len(token_info_records_raw)} token infos.")

                    if not trade_records_raw:
                        logger.warning("No trade records found for the specified mints and period.")
                        return {}

                    # --- Process Trade Data ---
                    trades_df = pd.DataFrame(trade_records_raw, columns=['mint', 'timestamp', 'price', 'volume', 'market_cap_calculated'])
                    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], errors='coerce', utc=True)
                    trades_df.dropna(subset=['timestamp'], inplace=True) # Drop rows where timestamp couldn't be parsed

                    # Convert relevant columns to numeric early, handling errors
                    trades_df['price'] = pd.to_numeric(trades_df['price'], errors='coerce')
                    trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce') # This is sol_amount
                    trades_df['market_cap_calculated'] = pd.to_numeric(trades_df['market_cap_calculated'], errors='coerce')
                    trades_df.dropna(subset=['price', 'volume'], inplace=True) # Drop rows essential for calcs if invalid

                    # --- Calculate SQL-like Rolling Volume & Volatility per Mint ---
                    logger.info("Calculating rolling volume and volatility per mint...")
                    all_processed_trades = []
                    time_interval_minutes = self.config['DEFAULT_TIME_INTERVALL'] # Get from config
                    window_duration = f"{time_interval_minutes}min"
                    logger.debug(f"Using rolling window duration: {window_duration}")

                    for mint_name, mint_df in trades_df.groupby('mint'):
                        if mint_df.empty:
                            continue

                        mint_df = mint_df.sort_values('timestamp').copy() # Sort and copy to avoid SettingWithCopyWarning

                        # Set timestamp as index for rolling calculations
                        mint_df_indexed = mint_df.set_index('timestamp')

                        # Calculate Rolling Volume (SQL-like)
                        mint_df['rolling_volume_sql'] = mint_df_indexed['volume']\
                                                        .rolling(window_duration, closed='left')\
                                                        .sum().values
                        mint_df['rolling_volume_sql'] = mint_df['rolling_volume_sql'].fillna(0.0)

                        # Calculate Rolling Volatility (SQL-like)
                        prices = mint_df['price']
                        if len(prices) > 1:
                            # Calculate log returns, handle potential division by zero or invalid values
                            log_returns = np.log(prices / prices.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)

                            # Use rolling window on log_returns indexed by time
                            rolling_obj = log_returns.set_axis(mint_df['timestamp'])\
                                                    .rolling(window_duration, closed='left')

                            # Calculate rolling std deviation and count
                            rolling_std = rolling_obj.std()
                            rolling_count = rolling_obj.count()

                            # Apply the SQL logic: std * sqrt(count), handle count <= 5
                            # Ensure intermediate arrays are float for sqrt
                            rolling_std_float = rolling_std.fillna(0.0).astype(float)
                            rolling_count_float = rolling_count.fillna(0.0).astype(float)

                            volatility_sql = rolling_std_float * np.sqrt(np.maximum(rolling_count_float, 1.0)) # Use maximum to avoid sqrt(0)
                            mint_df['rolling_volatility_sql'] = volatility_sql.where(rolling_count > 5, 0.0).values # Set to 0 if count <= 5
                        else:
                            mint_df['rolling_volatility_sql'] = 0.0 # Not enough data for log returns

                        mint_df['rolling_volatility_sql'] = mint_df['rolling_volatility_sql'].fillna(0.0) # Fill any remaining NaNs

                        all_processed_trades.append(mint_df)

                    if not all_processed_trades:
                        logger.warning("No trades remained after processing rolling metrics.")
                        return {}

                    processed_trades_df = pd.concat(all_processed_trades)

                    # --- Resample to 5-second OHLCV using SQL-like metrics ---
                    logger.info("Resampling trades to 5-second OHLCV intervals...")
                    # Apply the modified aggregation function
                    ohlcv_df = processed_trades_df.groupby(['mint', pd.Grouper(key='timestamp', freq='5s')])\
                                                .apply(self.ohlcv_sql_like).reset_index()

                    # Handle potential NaNs from empty groups BEFORE setting index
                    ohlcv_df.dropna(subset=['mint', 'timestamp'], inplace=True) # Drop rows if group keys are NaN
                    # Fill NaNs in OHLC columns resulting from empty groups (e.g., with ffill/bfill or 0)
                    ohlc_cols = ['Open', 'High', 'Low', 'Close']
                    # Forward fill first, then backfill to handle NaNs at the start/end
                    ohlcv_df[ohlc_cols] = ohlcv_df.groupby('mint')[ohlc_cols].ffill().bfill()
                    # Fill remaining NaNs (if entire mint group was NaN) with 0 or a suitable value
                    ohlcv_df[ohlc_cols] = ohlcv_df[ohlc_cols].fillna(0.0)
                    # Also fill Volume/Volatility/MarketCap NaNs that resulted from empty intervals
                    ohlcv_df[['Volume', 'volatility', 'market_cap_calculated']] = ohlcv_df[['Volume', 'volatility', 'market_cap_calculated']].fillna(0.0)


                    ohlcv_df = ohlcv_df.set_index('timestamp')

                    # ---> FIX: Handle duplicate index before resampling <---
                    # This should ideally happen *after* groupby.apply but *before* resample
                    # Check if duplicates exist after setting the index
                    if ohlcv_df.index.has_duplicates:
                        logger.warning(f"Duplicate timestamps found in aggregated OHLCV index before resampling. Keeping last entry.")
                        # Group by mint *and* timestamp, take the last row within each duplicate group
                        ohlcv_df = ohlcv_df.loc[~ohlcv_df.index.duplicated(keep='last')]
                    # ---> END FIX <---

                    # Resample to ensure continuous 5s intervals and interpolate missing values (if any remain)
                    # Group by mint *before* resampling to resample each token independently
                    resampled_ohlcv_list = []
                    for mint_name, group_df in ohlcv_df.groupby('mint'):
                        # Ensure index is unique within the group before resampling
                        if group_df.index.has_duplicates:
                            logger.warning(f"Duplicate timestamps found for mint {mint_name} before resampling. Keeping last.")
                            group_df = group_df.loc[~group_df.index.duplicated(keep='last')]

                        # Define the full time range for this mint based on its first/last resampled point
                        # This ensures resampling covers the actual activity period for the mint
                        min_ts = group_df.index.min()
                        max_ts = group_df.index.max()
                        full_range = pd.date_range(start=min_ts, end=max_ts, freq='5s', tz='UTC')

                        # ---> FIX: Call infer_objects() before interpolating <---
                        # group_resampled = group_df.reindex(full_range).interpolate(method='time')
                        # Reindex first, creating the DataFrame that might have object dtypes due to NaNs
                        group_reindexed = group_df.reindex(full_range)

                        try:
                            # Attempt to convert columns to more specific dtypes (e.g., float, int)
                            # copy=False modifies inplace if possible, potentially saving memory
                            group_reindexed = group_reindexed.infer_objects(copy=False)
                        except Exception as e:
                            # Log if infer_objects fails, but proceed cautiously
                            logger.warning(f"Failed to infer objects for {mint_name} before interpolation: {e}")

                        # Reindex and interpolate within the group's actual range
                        # Now interpolate. This should operate on more appropriate dtypes.
                        group_resampled = group_reindexed.interpolate(method='time')
                        # ---> END FIX <---
                        
                       
                       
                        # Add the mint column back after reindexing
                        group_resampled['mint'] = mint_name
                        resampled_ohlcv_list.append(group_resampled)

                    if not resampled_ohlcv_list:
                        logger.warning("No data remained after resampling OHLCV data.")
                        return {}

                    resampled_ohlcv_df = pd.concat(resampled_ohlcv_list)
                    resampled_ohlcv_df.index.name = 'timestamp' # Ensure index has a name

                    # --- Process RugCheck Data ---
                    # (Same as before)
                    if rugcheck_records_raw:
                        rugcheck_df = pd.DataFrame(rugcheck_records_raw, columns=['mint', 'timestamp', 'rugcheck_score'])
                        rugcheck_df['timestamp'] = pd.to_datetime(rugcheck_df['timestamp'], errors='coerce', utc=True)
                        rugcheck_df.dropna(subset=['timestamp'], inplace=True)
                        # Set index AFTER sorting and dropping duplicates
                        rugcheck_df = rugcheck_df.sort_values(['mint', 'timestamp'])
                        # Keep the last score for duplicate timestamps within the same mint
                        rugcheck_df = rugcheck_df.drop_duplicates(subset=['mint', 'timestamp'], keep='last')
                        rugcheck_df.set_index('timestamp', inplace=True)
                        rugcheck_df['rugcheck_score'] = pd.to_numeric(rugcheck_df['rugcheck_score'], errors='coerce')
                        rugcheck_df = rugcheck_df[['mint', 'rugcheck_score']] # Keep mint for merge_asof
                    else:
                        # Create an empty DataFrame with the correct columns and index type
                        rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))


                    # --- Process Token Info ---
                    # (Same as before)
                    token_info = {}
                    if token_info_records_raw:
                        for r in token_info_records_raw:
                            mint = r['mint']
                            # Use pd.to_datetime which handles NaT gracefully
                            creation_time = pd.to_datetime(r['token_creation_time'], errors='coerce', utc=True)
                            socials = pd.to_numeric(r['socials_score'], errors='coerce')
                            if pd.notna(creation_time): # Check if creation_time is valid
                                token_info[mint] = {'creation_time': creation_time, 'socials_score': socials}


                    # --- Combine data per mint ---
                    logger.info("Combining OHLCV, RugCheck, and Token Info data per mint...")
                    required_final_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score', 'token_creation_time']

                    # Process each mint group from the resampled data
                    grouped_ohlcv = resampled_ohlcv_df.groupby('mint')

                    for mint_name in grouped_ohlcv.groups:
                        # Select the mint's OHLCV data
                        mint_ohlcv = grouped_ohlcv.get_group(mint_name)[['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility']]

                        # Prepare mint-specific rugcheck data for merge_asof
                        mint_rugcheck_data = rugcheck_df[rugcheck_df['mint'] == mint_name][['rugcheck_score']] if not rugcheck_df.empty else None

                        # Create the combined DataFrame starting with OHLCV data
                        combined_df = mint_ohlcv.copy()

                        # Merge RugCheck data using merge_asof
                        if mint_rugcheck_data is not None and not mint_rugcheck_data.empty:
                            # Ensure both sides are sorted by index for merge_asof
                            combined_df = combined_df.sort_index()
                            mint_rugcheck_data = mint_rugcheck_data.sort_index()
                            # Handle potential duplicates in rugcheck index before merging
                            if mint_rugcheck_data.index.has_duplicates:
                                logger.warning(f"Duplicate timestamps found in RugCheck data for {mint_name}. Keeping last.")
                                mint_rugcheck_data = mint_rugcheck_data.loc[~mint_rugcheck_data.index.duplicated(keep='last')]

                            combined_df = pd.merge_asof(
                                combined_df,
                                mint_rugcheck_data,
                                left_index=True,
                                right_index=True,
                                direction='backward', # Find the latest rugcheck score at or before the OHLCV timestamp
                                tolerance=pd.Timedelta('1d') # Allow matching recent score
                            )
                        else:
                            combined_df['rugcheck_score'] = np.nan # Add column if no rugcheck data

                        # Add Token Info (Creation Time, Socials Score)
                        mint_info_data = token_info.get(mint_name)
                        if mint_info_data:
                            combined_df['token_creation_time'] = mint_info_data['creation_time']
                            combined_df['socials_score'] = mint_info_data['socials_score']
                        else:
                            logger.warning(f"Missing token info for {mint_name}. Using defaults.")
                            combined_df['token_creation_time'] = pd.NaT # Use NaT for missing dates
                            combined_df['socials_score'] = 100 # Default high risk score

                        # --- Final Fill and Type Conversion ---
                        # Forward fill scores and creation time
                        fill_cols = ['rugcheck_score', 'socials_score', 'token_creation_time']
                        combined_df[fill_cols] = combined_df[fill_cols].ffill()
                        # Backfill only if needed (e.g., if NaNs remain at the beginning)
                        combined_df[fill_cols] = combined_df[fill_cols].bfill()


                        # Convert score columns to integer types after filling NaNs
                        # Fill NaN scores with default high-risk values before converting to int
                        combined_df['rugcheck_score'] = combined_df['rugcheck_score'].fillna(10000).astype(int)
                        combined_df['socials_score'] = combined_df['socials_score'].fillna(100).astype(int)

                        # Ensure other numeric columns are floats, fill NaNs with 0.0 AFTER interpolation/ffill
                        numeric_cols_to_zero = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility']
                        for col in numeric_cols_to_zero:
                            if col in combined_df.columns:
                                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0.0)
                            else:
                                # Add the column if completely missing after merges (shouldn't happen ideally)
                                logger.warning(f"Column '{col}' missing for {mint_name} after merge. Adding default 0.0.")
                                combined_df[col] = 0.0


                        # Ensure all required columns exist, adding defaults if somehow missing
                        for r_col in required_final_cols:
                            if r_col not in combined_df.columns:
                                logger.warning(f"Required column '{r_col}' missing for {mint_name} at final stage. Adding default.")
                                if r_col == 'token_creation_time': combined_df[r_col] = pd.NaT
                                elif r_col in ['rugcheck_score', 'socials_score']: combined_df[r_col] = 100 if r_col == 'socials_score' else 10000
                                else: combined_df[r_col] = 0.0

                        # --- Final Filtering and Validation ---
                        # Filter final DataFrame to the originally requested date range
                        # This ensures we don't include data outside the requested bounds introduced by resampling/filling
                        final_df = combined_df[(combined_df.index >= start_date) & (combined_df.index < end_date)].copy() # Use .copy()

                        # Final check for validity before adding to results
                        if not final_df.empty and all(col in final_df.columns for col in required_final_cols):
                            # Select and ensure correct dtypes before returning
                            final_df = final_df[required_final_cols].astype({
                                'Open': float, 'High': float, 'Low': float, 'Close': float, 'Volume': float,
                                'market_cap_calculated': float, 'volatility': float, 'rugcheck_score': int, 'socials_score': int
                                # Keep token_creation_time as datetime
                            })
                            # Ensure the index is still a DatetimeIndex and timezone-aware
                            final_df.index = pd.to_datetime(final_df.index, utc=True)
                            results_dict[mint_name] = final_df
                        else:
                            logger.warning(f"No valid data remained for {mint_name} after final processing/filtering. Skipping.")


                    logger.info(f"Finished processing data for {len(results_dict)} tokens.")

                except asyncpg.exceptions.InterfaceError as iface_err:
                    logger.error(f"InterfaceError during historical data processing: {iface_err}", exc_info=True)
                    # Consider connection recovery logic or re-raising
                    return {}
                except Exception as e:
                    logger.error(f"Error processing historical data ({type(e).__name__}): {e}", exc_info=True)
                    return {}

            logger.info(f"Successfully fetched and processed historical data for {len(results_dict)} tokens.")
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
RL_HISTORICAL_DATA_START_TS: datetime = datetime(2025, 4, 19, 15, 0, 0, tzinfo=timezone.utc)
RL_HISTORICAL_DATA_END_TS: datetime = datetime(2025, 4, 19, 20, 0, 0, tzinfo=timezone.utc)

# --- Environment Configuration ---
DATA_SET_KEY_TRAIN: str = 'train'       # Data used for agent training episodes.
DATA_SET_KEY_EVAL: str = 'validation'   # Data used for periodic evaluation during training.

RL_INITIAL_CAPITAL: float = 100.0 # In SOL

# Max steps based on typical token lifespan (e.g., 4 hours * 12 steps/min * 60 min/hr = 2880 steps if 5s candles)
# Let's set a reasonable upper bound, actual episodes will be truncated by data end.
MAX_STEPS_PER_EPISODE: int = 2880 # Max simulation steps if token lives unusually long

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
    'market_cap_sol_norm',  # Market cap in SOL (e.g., log-normalized)
    'volume_sol_norm',      # Trade volume in SOL (e.g., log-normalized)
    'rugcheck_score_norm',  # RugCheck score (normalized 0-1, where 1=low risk)
    'socials_score_norm',   # Socials score (normalized 0-1, where 1=low risk)
    'time_since_creation_norm', # Time since token creation (normalized 0-1)

    # Portfolio State Features (Normalized)
    'is_holding',           # Binary flag (0 or 1)
    'position_pnl_norm',    # Unrealized PnL of current position, normalized (-1 to N)
    'time_holding_norm',    # Time the current position has been held, normalized (0-1)
    'sol_balance_norm'      # Current SOL balance, normalized (0-1 relative to initial capital * factor)
]
OBSERVATION_SPACE_DIM: int = len(OBSERVATION_FEATURES)

# Expected bounds of the observation space *after* normalization. [-1, 1] is common.
OBSERVATION_LOW: float = -1.0
OBSERVATION_HIGH: float = 1.0

# --- Action Space Configuration (Continuous Parameter Tuning) ---
# Parameters controlled by the RL agent.
# Format: (parameter_name, low_bound, high_bound, type)
RL_TUNABLE_PARAMETERS: List[Tuple[str, float, float, type]] = [
    # Focus on sell-side parameters for initial RL experiments
    ('INITIAL_STOP_LOSS_PERCENT', 5.0, 70.0, float),    # 5% to 70% SL
    ('FIRST_SELL_PERCENT', 20.0, 100.0, float),         # 20% to 100% partial sell
    ('TRAILING_STOP_LOSS_PERCENT', 5.0, 50.0, float),   # 5% to 50% TSL
    ('FIRST_SELL_PROFIT_MARGIN', 10.0, 200.0, float),   # 10% to 200% margin for TP1
    ('SECOND_TAKE_PROFIT_PERCENT', 100.0, 1000.0, float), # 100% to 1000% TP2
    ('FIRST_SELL_PROFIT_MARGIN', 10.0, 200.0, float),   # 10% to 200% margin for TP1
    ('DEFAULT_VOLUME_THRESHOLD', 10000, 50000, int),     # 5k to 50k USD volume threshold
    ('DEFAULT_MARKETCAP_THRESHOLD', 6000, 100000, int), # 10k to 100k USD market cap threshold
    ('MIN_VOLATILITY', 0.1, 1.0, float),                # 0.1% to 1% volatility threshold
    ('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 500, 1002, int), # 1 to 1000 score threshold
    ('DEFAULT_SOCIAL_SCORE_THRESHOLD', 40, 80, int),  # 1 to 100 score threshold
    # ('DEFAULT_TIME_INTERVALL', 1, 60, int),
    ('SOL_TO_BUY', 0.1, 0.5, float), # Add buy amount later if needed
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
DEFAULT_BUY_SOL_AMOUNT: float = 0.5 # Fixed buy amount for RL env simulation
SECOND_TAKE_PROFIT_PERCENT: float = 550.0 # Fixed second TP target

# Fixed thresholds for the *simulated* buy decision (agent learns parameters, not timing)
# DEFAULT_VOLUME_THRESHOLD: int = 19000
# DEFAULT_MARKETCAP_THRESHOLD: int = 10000
# DEFAULT_RUGCHECK_SCORE_THRESHOLD: int = 801
# DEFAULT_SOCIAL_SCORE_THRESHOLD: int = 50
# MIN_VOLATILITY: float = 0.1
MIN_MARKET_CAP: int = 3600 # Emergency sell market cap threshold (USD)

VOLATILITY_WINDOW: int = 120 # Window size (steps) for volatility calculation in env

# --- RL Agent & Training Configuration (Stable Baselines3) ---
RL_ALGORITHM: str = "PPO" # PPO is robust; SAC/TD3 are alternatives

# Policy network architecture. Adjust hidden layer sizes as needed.
POLICY_KWARGS: Dict[str, Any] = dict(net_arch=dict(pi=[128, 128], vf=[128, 128]))
# For SAC/TD3: dict(net_arch=[256, 256]) might be suitable

# Total training timesteps. Needs significant increase for real training.
TOTAL_TIMESTEPS: int = 1_000_000 # Increase for more thorough training (e.g., 1M+)

# Number of parallel environments. Adjust based on CPU cores.
N_ENVS: int = 8 # Example: Use 8 parallel environments if CPU allows

TENSORBOARD_LOG_DIR: str = "./rl_tensorboard_logs/"
MODEL_SAVE_DIR: str = "./rl_trained_models/"

# Evaluation frequency (in total agent steps across all envs).
EVAL_FREQ: int = 50000 # Evaluate every 50k total steps

# Number of episodes for each evaluation run.
N_EVAL_EPISODES: int = 20 # More episodes for better evaluation stability

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
AGENT_ACTION_INTERVAL_SECONDS: int = 60 # Update parameters every minute
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
from datetime import timezone, datetime

# --- Project Modules ---
from logger import logger
import rl_config # Import RL specific configurations
from utils import calculate_volatility # Keep utility for potential recalculation

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
        initial_capital: float = rl_config.RL_INITIAL_CAPITAL,
        max_steps: int = rl_config.MAX_STEPS_PER_EPISODE
    ):
        """
        Initializes the Trading Environment with OHLCV data.

        Args:
            historical_data_dict: Dictionary mapping mints to their historical 5s OHLCV DataFrames.
                                  Indices MUST be timezone-aware UTC DatetimeIndex.
                                  Expected columns: 'Open', 'High', 'Low', 'Close', 'Volume',
                                                    'market_cap_calculated', 'rugcheck_score', 'socials_score',
                                                    'token_creation_time'.
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
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'rugcheck_score', 'socials_score', 'token_creation_time']

        for mint, df in historical_data_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty and isinstance(df.index, pd.DatetimeIndex):
                 if df.index.tz is None or str(df.index.tz).upper() != 'UTC':
                     logger.error(f"DataFrame index for mint {mint} is not timezone-aware UTC! Skipping.")
                     continue
                 if mint not in token_lifespans:
                      logger.warning(f"Lifespan info missing for mint {mint}. Skipping.")
                      continue

                 # Check for required OHLCV columns
                 missing_cols = [col for col in required_cols if col not in df.columns]
                 if missing_cols:
                     logger.error(f"Missing required OHLCV columns in data for mint {mint}: {missing_cols}. Skipping.")
                     continue

                 # Basic NaN check (more thorough checks happen in _get_observation)
                 if df[required_cols].isnull().values.any():
                      logger.warning(f"NaN values found in required columns for mint {mint}. Will attempt fill/clip later.")
                      # Consider attempting to fill NaNs here if preferred

                 self.historical_data_dict[mint] = df
                 self.token_lifespans[mint] = token_lifespans[mint]
            else:
                 logger.warning(f"Skipping invalid/empty DataFrame for mint: {mint}")

        self.available_mints = list(self.historical_data_dict.keys())
        if not self.available_mints:
            raise ValueError("No valid OHLCV DataFrames found after validation.")

        self.initial_capital = initial_capital
        self._max_episode_steps = max_steps

        # --- Define Action Space (Same as before) ---
        self.action_space = spaces.Box(
            low=rl_config.ACTION_LOW,
            high=rl_config.ACTION_HIGH,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        self._action_param_names = [p[0] for p in rl_config.RL_TUNABLE_PARAMETERS]

        # --- Define Observation Space (Same as before) ---
        self.observation_space = spaces.Box(
            low=rl_config.OBSERVATION_LOW,
            high=rl_config.OBSERVATION_HIGH,
            shape=(rl_config.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        # --- Internal State Variables (Same as before) ---
        self.current_step: int = 0
        self.current_sol: float = 0.0
        self.current_data_df: Optional[pd.DataFrame] = None
        self.current_mint: Optional[str] = None
        self.current_token_end_ts: Optional[datetime] = None
        self.active_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {}
        self.last_observation: np.ndarray = np.zeros(self.observation_space.shape, dtype=np.float32)
        # Use 'Close' price for history
        self._price_history: deque = deque(maxlen=rl_config.OBSERVATION_PRICE_HISTORY_LENGTH)
        self._previous_unrealized_pnl: float = 0.0
        self._last_step_processed_index = -1

        logger.info(f"TradingEnv (OHLCV) initialized. Observation space dim: {rl_config.OBSERVATION_SPACE_DIM}, Action space dim: {rl_config.ACTION_SPACE_DIM}")

    def _get_observation(self) -> np.ndarray:
        """
        Calculates and returns the normalized observation vector using OHLCV data.
        """
        default_obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        if self.current_data_df is None or self._last_step_processed_index < 0 or self._last_step_processed_index >= len(self.current_data_df):
            return default_obs

        try:
            current_row = self.current_data_df.iloc[self._last_step_processed_index]
            current_timestamp = self.current_data_df.index[self._last_step_processed_index]
        except IndexError:
            logger.warning(f"IndexError getting observation at index {self._last_step_processed_index} (Step {self.current_step}) for mint {self.current_mint}. Returning zeros.")
            return default_obs

        # --- Update Price History (using Close price) ---
        current_price = current_row.get('Close', 0.0)
        if pd.notna(current_price) and isinstance(current_price, (int, float)):
            self._price_history.append(float(current_price))
        else:
            last_valid_price = self._price_history[-1] if self._price_history else 0.0
            self._price_history.append(last_valid_price) # Use last valid if current is NaN

        # --- Extract Base Features from OHLCV row ---
        try:
            market_cap_sol = float(current_row.get('market_cap_calculated', 0.0))
            volume = float(current_row.get('Volume', 0.0)) # Use 'Volume' column
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            creation_time_ts = current_row.get('token_creation_time', pd.NaT)
            # Use pre-calculated volatility if available, otherwise default to 0
            volatility = float(current_row.get('volatility', 0.0))
            if pd.isna(volatility): volatility = 0.0

            # Fill potential NaNs extracted (should ideally be handled in __init__ or data loading)
            market_cap_sol = 0.0 if pd.isna(market_cap_sol) else market_cap_sol
            volume = 0.0 if pd.isna(volume) else volume
            rugcheck_score = 10000 if pd.isna(rugcheck_score) else int(rugcheck_score)
            socials_score = 100 if pd.isna(socials_score) else int(socials_score)

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error accessing/converting OHLCV features at index {self._last_step_processed_index} for mint {self.current_mint}: {e}", exc_info=True)
            return default_obs

        # --- Calculate Derived Features (using Close price history) ---
        prices = np.array(self._price_history, dtype=np.float32)
        safe_prices = prices[prices > 1e-12]
        price_change_1 = np.log(safe_prices[-1] / safe_prices[-2]) if len(safe_prices) >= 2 else 0.0
        price_change_5 = np.log(safe_prices[-1] / safe_prices[-6]) if len(safe_prices) >= 6 else 0.0
        price_change_10 = np.log(safe_prices[-1] / safe_prices[-11]) if len(safe_prices) >= 11 else 0.0

        time_since_creation_seconds = 0.0
        if pd.notna(creation_time_ts) and isinstance(current_timestamp, pd.Timestamp):
            # Ensure creation_time_ts is timezone-aware for correct calculation
            if creation_time_ts.tzinfo is None: creation_time_ts = creation_time_ts.tz_localize('UTC')
            time_diff = current_timestamp - creation_time_ts
            time_since_creation_seconds = max(0.0, time_diff.total_seconds())

        is_holding = 1.0 if self.active_position else 0.0
        position_pnl_current_unrealized = 0.0
        time_holding_seconds = 0
        if self.active_position:
            buy_price = self.active_position['buy_price']
            rem_tokens = self.active_position['remaining_tokens']
            total_investment = self.active_position.get('total_investment_sol', 1.0)
            last_price = prices[-1] if prices.size > 0 else buy_price # Use last Close price
            current_value = last_price * rem_tokens
            initial_tokens = self.active_position.get('initial_tokens', rem_tokens)
            cost_fraction = rem_tokens / initial_tokens if initial_tokens > 0 else 1.0
            cost_basis_remaining = total_investment * cost_fraction
            position_pnl_current_unrealized = current_value - cost_basis_remaining
            entry_timestamp = self.active_position.get('entry_timestamp')
            if entry_timestamp:
                time_holding_seconds = max(0.0, (current_timestamp - entry_timestamp).total_seconds())

        # --- Normalization (Same logic as before, but using OHLCV-derived features) ---
        epsilon = 1e-9
        norm_price_change_1 = np.clip(price_change_1 * 20, -1, 1)
        norm_price_change_5 = np.clip(price_change_5 * 10, -1, 1)
        norm_price_change_10 = np.clip(price_change_10 * 5, -1, 1)
        norm_volatility = np.clip(volatility, 0, 1) # Assuming volatility is already 0-1
        norm_market_cap = np.clip(np.log10(market_cap_sol + epsilon) / 7, 0, 1)
        norm_volume = np.clip(np.log10(volume + epsilon) / 5, 0, 1) # Use OHLCV Volume
        norm_rugcheck = np.clip(1.0 - (float(rugcheck_score) / 10000.0), 0, 1)
        norm_socials = np.clip(1.0 - (float(socials_score) / 100.0), 0, 1)
        norm_time_creation = np.clip(np.log10(time_since_creation_seconds + 1) / 6, 0, 1)
        norm_pos_pnl = np.clip(position_pnl_current_unrealized / (total_investment if self.active_position else 1.0), -1, 5)
        max_duration_seconds = self._max_episode_steps * 5
        norm_time_held = np.clip(time_holding_seconds / (max_duration_seconds + epsilon), 0, 1)
        norm_sol_balance = np.clip(self.current_sol / (self.initial_capital * 2.0), 0, 1)

        # --- Construct Observation Vector (Order MUST match rl_config.OBSERVATION_FEATURES) ---
        observation = np.array([
            norm_price_change_1, norm_price_change_5, norm_price_change_10,
            norm_volatility, norm_market_cap, norm_volume, # Use norm_volume from OHLCV
            norm_rugcheck, norm_socials, norm_time_creation,
            is_holding, norm_pos_pnl, norm_time_held, norm_sol_balance
        ], dtype=np.float32)

        # --- Final Validation ---
        if not np.all(np.isfinite(observation)):
            logger.warning(f"NaN/inf in OHLCV observation @ Index {self._last_step_processed_index}, Mint {self.current_mint}. Replacing with zeros. Raw Obs: {observation}")
            observation = default_obs
        elif observation.shape != self.observation_space.shape:
            logger.error(f"OHLCV Observation shape mismatch! Expected {self.observation_space.shape}, got {observation.shape}. Returning zeros.")
            observation = default_obs
        else:
            observation = np.clip(observation, rl_config.OBSERVATION_LOW, rl_config.OBSERVATION_HIGH)

        self.last_observation = observation
        self._previous_unrealized_pnl = position_pnl_current_unrealized
        return observation

    def _apply_action(self, action: np.ndarray):
        """Applies the agent's action (Same as before)."""
        new_params = {}
        clipped_action = np.clip(action, rl_config.ACTION_LOW, rl_config.ACTION_HIGH)
        for i, param_config in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            param_name, _, _, p_type = param_config
            val = clipped_action[i]
            new_params[param_name] = p_type(np.round(val)) if p_type == int else float(val)
        self.current_parameters = new_params

    def _run_trading_logic_step(self) -> Tuple[float, float]:
        """
        Simulates one step of the trading logic using OHLCV data.
        Returns realized PnL and any shaping bonuses/penalties for the step.
        """
        realized_pnl_this_step = 0.0
        reward_bonus_penalty = 0.0

        current_data_index = self.current_step
        if self.current_data_df is None or current_data_index >= len(self.current_data_df):
            logger.warning(f"Attempted to run trading logic at invalid step index {current_data_index}.")
            self._last_step_processed_index = -1
            return realized_pnl_this_step, reward_bonus_penalty

        self._last_step_processed_index = current_data_index

        try:
            current_row = self.current_data_df.iloc[current_data_index]
            current_timestamp = self.current_data_df.index[current_data_index]
            # Use OHLCV columns
            price = float(current_row.get('Close', 0.0))
            volume = float(current_row.get('Volume', 0.0))
            high_price = float(current_row.get('High', 0.0))
            # ---
            market_cap_sol = float(current_row.get('market_cap_calculated', 0.0))

            if price <= 1e-12:
                return realized_pnl_this_step, reward_bonus_penalty

            # --- Get parameters (Agent's or Defaults) ---
            agent_params = self.current_parameters
            if not agent_params:
                agent_params = {p[0]: (p[1] + p[2]) / 2 for p in rl_config.RL_TUNABLE_PARAMETERS}

            initial_sl_percent = agent_params.get('INITIAL_STOP_LOSS_PERCENT', 50.0)
            first_sell_perc = agent_params.get('FIRST_SELL_PERCENT', 75.0) / 100.0
            trailing_sl_percent = agent_params.get('TRAILING_STOP_LOSS_PERCENT', 50.0)
            first_profit_margin = agent_params.get('FIRST_SELL_PROFIT_MARGIN', 100.0) / 100.0
            volume_thresh = agent_params.get('DEFAULT_VOLUME_THRESHOLD', 5000)
            mcap_thresh_buy = agent_params.get('DEFAULT_MARKETCAP_THRESHOLD', 10000)
            rug_thresh = agent_params.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 1000)
            social_thresh = agent_params.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100)
            volatility_thresh = agent_params.get('MIN_VOLATILITY', 0.0)
            buy_amount_sol = agent_params.get('SOL_TO_BUY', 0.1)
            time_interval = agent_params.get('DEFAULT_TIME_INTERVALL', 30)

            # Fixed simulation parameters
            buy_fee = rl_config.DEFAULT_BUY_FEE
            buy_tip = rl_config.DEFAULT_BUY_TIP
            sell_fee = rl_config.DEFAULT_SELL_FEE
            sell_tip = rl_config.DEFAULT_SELL_TIP
            # buy_amount_sol = rl_config.DEFAULT_BUY_SOL_AMOUNT
            # volume_thresh = rl_config.DEFAULT_VOLUME_THRESHOLD
            # mcap_thresh_buy = rl_config.DEFAULT_MARKETCAP_THRESHOLD
            # rug_thresh = rl_config.DEFAULT_RUGCHECK_SCORE_THRESHOLD
            # social_thresh = rl_config.DEFAULT_SOCIAL_SCORE_THRESHOLD
            # volatility_thresh = rl_config.MIN_VOLATILITY
            min_mcap_sell_usd = rl_config.MIN_MARKET_CAP

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error getting data/params in trading logic at index {current_data_index}: {e}", exc_info=True)
            return realized_pnl_this_step, reward_bonus_penalty

        # --- Sell Logic (using Close price for checks, High for highest_price) ---
        if self.active_position:
            pos = self.active_position
            # Update highest price using the High of the current candle
            hp = max(pos['highest_price'], high_price)
            pos['highest_price'] = hp

            current_stop_loss_price = pos['stop_loss_price']
            initial_tp_price = pos['initial_tp_price']
            second_tp_price = pos['second_tp_price']
            first_tp_hit = pos['first_tp_hit']

            current_trailing_sl_price = 0.0
            if first_tp_hit:
                current_trailing_sl_price = hp * (1.0 - trailing_sl_percent / 100.0)

            sell_reason = None
            sell_all = False; sell_partial = False
            sell_percentage = 0.0

            # Check conditions using Close price
            if price <= current_stop_loss_price:
                sell_reason = "Stop Loss" if not first_tp_hit else "Breakeven SL"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif price >= second_tp_price:
                sell_reason = "Second TP"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif not first_tp_hit and price >= initial_tp_price:
                sell_reason = "First TP"; sell_partial = True; sell_percentage = first_sell_perc
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif first_tp_hit and price <= current_trailing_sl_price:
                sell_reason = "Trailing SL"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            # Emergency SL (Simplified)
            # elif (market_cap_sol * 1.0) < min_mcap_sell_usd:
            #     sell_reason = "Emergency SL"; sell_all = True; sell_percentage = 1.0
            #     reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY

            if sell_reason:
                initial_tokens = pos['initial_tokens']
                remaining_tokens = pos['remaining_tokens']
                total_investment = pos['total_investment_sol']
                tokens_to_sell = 0.0

                if sell_partial:
                    tokens_to_sell = initial_tokens * sell_percentage
                    tokens_to_sell = min(tokens_to_sell, remaining_tokens)
                elif sell_all:
                    tokens_to_sell = remaining_tokens

                if tokens_to_sell > 1e-9:
                    # Execute sell using Close price
                    gross_sol = tokens_to_sell * price
                    net_sol = gross_sol - sell_fee - sell_tip
                    cost_basis = total_investment * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                    pnl = net_sol - cost_basis
                    realized_pnl_this_step += pnl

                    self.current_sol += net_sol
                    pos['remaining_tokens'] -= tokens_to_sell
                    self.trade_history.append({
                        'step': self.current_step, 'index': current_data_index, 'type': 'sell', 'price': price,
                        'tokens': tokens_to_sell, 'net_sol': net_sol, 'pnl': pnl, 'reason': sell_reason
                    })

                    if sell_partial:
                        pos['first_tp_hit'] = True
                        pos['stop_loss_price'] = pos['buy_price']

                    if pos['remaining_tokens'] < 1e-9:
                        self.active_position = None

        # --- Buy Logic (using OHLCV Volume) ---
        if not self.active_position and self.current_sol >= (buy_amount_sol + buy_fee + buy_tip):
            # Check fixed buy criteria using OHLCV Volume
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            volatility = float(current_row.get('volatility', 0.0))

            meets_buy_criteria = (
                volume >= volume_thresh and # Use OHLCV Volume
                market_cap_sol >= mcap_thresh_buy and
                rugcheck_score < rug_thresh and
                socials_score < social_thresh and
                volatility >= volatility_thresh
            )

            logger.debug(f"Buy criteria: Volume {volume} >= {volume_thresh}, Market Cap {market_cap_sol} >= {mcap_thresh_buy}, "
                         f"RugCheck {rugcheck_score} < {rug_thresh}, Socials {socials_score} < {social_thresh}, "
                         f"Volatility {volatility} >= {volatility_thresh}")

            if meets_buy_criteria:
                total_investment = buy_amount_sol + buy_fee + buy_tip
                tokens_bought = buy_amount_sol / price if price > 0 else 0

                if tokens_bought > 0:
                    self.current_sol -= total_investment

                    # Calculate initial SL/TPs using agent's CURRENT parameters and Close price
                    initial_sl_price = price * (1.0 - initial_sl_percent / 100.0)
                    sell_fee_tp1 = float(rl_config.DEFAULT_SELL_FEE)
                    sell_tip_tp1 = float(rl_config.DEFAULT_SELL_TIP)
                    total_cost_base_tp1 = total_investment + sell_fee_tp1 + sell_tip_tp1
                    target_net_sol_return_tp1 = total_cost_base_tp1 * (1.0 + first_profit_margin)
                    target_gross_sol_return_tp1 = target_net_sol_return_tp1 + sell_fee_tp1 + sell_tip_tp1
                    tokens_to_sell_tp1 = tokens_bought * first_sell_perc
                    initial_tp_price = (target_gross_sol_return_tp1 / tokens_to_sell_tp1) if tokens_to_sell_tp1 > 1e-9 else float('inf')
                    second_tp_price = price * (1.0 + rl_config.SECOND_TAKE_PROFIT_PERCENT / 100.0)

                    self.active_position = {
                        'buy_price': price, 'initial_tokens': tokens_bought,
                        'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment,
                        'stop_loss_price': initial_sl_price, 'initial_tp_price': initial_tp_price,
                        'second_tp_price': second_tp_price, 'highest_price': price, # Use Close price as initial high
                        'first_tp_hit': False, 'entry_step': self.current_step,
                        'entry_timestamp': current_timestamp
                    }
                    self.trade_history.append({
                        'step': self.current_step, 'index': current_data_index, 'type': 'buy', 'price': price,
                        'tokens': tokens_bought, 'investment': total_investment
                    })

        return realized_pnl_this_step, reward_bonus_penalty

    def _calculate_reward(self, realized_pnl: float, bonus_penalty: float, is_token_death: bool) -> float:
        """Calculates reward (Same as before, includes death penalty)."""
        reward = realized_pnl * rl_config.REWARD_PNL_MULTIPLIER
        reward += bonus_penalty
        if self.active_position and rl_config.REWARD_HOLDING_PENALTY != 0:
            reward += rl_config.REWARD_HOLDING_PENALTY
        if is_token_death and self.active_position:
            reward += rl_config.REWARD_DEATH_PENALTY
            # logger.debug(f"Applied death penalty ({rl_config.REWARD_DEATH_PENALTY}) for holding {self.current_mint} at end.")
        return reward

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Executes one time step (Same logic as before, relies on updated internal methods)."""
        if self.current_data_df is None:
            logger.error("Environment not reset properly, cannot step.")
            obs = np.zeros(self.observation_space.shape, dtype=np.float32)
            return obs, 0.0, True, False, {"error": "Environment not reset"}

        self._apply_action(action)
        realized_pnl, bonus_penalty = self._run_trading_logic_step()
        self.current_step += 1

        terminated = self.current_sol <= 0
        end_of_data = self._last_step_processed_index >= len(self.current_data_df) - 1
        token_died = False
        if self.current_token_end_ts and self._last_step_processed_index >=0 :
             current_timestamp = self.current_data_df.index[self._last_step_processed_index]
             token_died = current_timestamp >= self.current_token_end_ts

        max_steps_reached = self.current_step >= self._max_episode_steps
        truncated = max_steps_reached or end_of_data or token_died
        is_token_death_event = end_of_data or token_died

        reward = self._calculate_reward(realized_pnl, bonus_penalty, is_token_death_event)
        observation = self._get_observation()

        info = {
            'mint': self.current_mint, 'step': self.current_step,
            'last_processed_index': self._last_step_processed_index,
            'sol_balance': self.current_sol, 'realized_pnl_step': realized_pnl,
            'reward_shaping_step': bonus_penalty,
            'is_holding': 1 if self.active_position else 0, 'raw_reward': reward
        }
        if self.active_position:
             info['position_entry_price'] = self.active_position['buy_price']
             info['position_remaining_tokens'] = self.active_position['remaining_tokens']

        if terminated or truncated:
             final_portfolio_value = self.current_sol
             if self.active_position:
                  # Use last Close price for final valuation
                  last_price = self._price_history[-1] if self._price_history else self.active_position['buy_price']
                  final_portfolio_value += self.active_position['remaining_tokens'] * last_price
             info['final_portfolio_value'] = final_portfolio_value
             info['total_steps_taken'] = self.current_step
             if terminated: info['episode_end_reason'] = "terminated (bankrupt)"
             elif max_steps_reached: info['episode_end_reason'] = "truncated (max_steps)"
             elif is_token_death_event: info['episode_end_reason'] = "truncated (token_death)"
             else: info['episode_end_reason'] = "truncated (unknown)"

        return observation, reward, terminated, truncated, info

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Resets the environment (Same logic, but uses OHLCV data)."""
        super().reset(seed=seed)

        self.current_mint = random.choice(self.available_mints)
        self.current_data_df = self.historical_data_dict[self.current_mint].copy()
        lifespan = self.token_lifespans.get(self.current_mint)
        if not lifespan:
             raise RuntimeError(f"Lifespan info missing for selected mint {self.current_mint} during reset.")
        self.current_token_end_ts = lifespan['end_ts']

        # --- Pre-calculate Volatility if missing (use Close price) ---
        if 'volatility' not in self.current_data_df.columns or self.current_data_df['volatility'].isnull().all():
            logger.debug(f"Calculating volatility for {self.current_mint} during reset (using Close price)...")
            if 'Close' in self.current_data_df.columns and not self.current_data_df['Close'].isnull().all():
                prices = pd.to_numeric(self.current_data_df['Close'], errors='coerce').ffill().bfill().fillna(0.0)
                if len(prices) > 1:
                    # Pass the Series with its DatetimeIndex
                    volatility_series = calculate_volatility(prices, window=rl_config.VOLATILITY_WINDOW)
                    self.current_data_df['volatility'] = volatility_series.fillna(0.0)
                else:
                    self.current_data_df['volatility'] = 0.0
            else:
                self.current_data_df['volatility'] = 0.0
        # Ensure volatility column exists even if calculation failed
        if 'volatility' not in self.current_data_df.columns:
            self.current_data_df['volatility'] = 0.0
        else:
            # Fill any remaining NaNs just in case
            self.current_data_df['volatility'] = self.current_data_df['volatility'].fillna(0.0)


        # --- Reset State Variables (Same as before) ---
        self.current_step = 0
        self._last_step_processed_index = -1
        self.current_sol = self.initial_capital
        self.active_position = None
        self.trade_history = []
        self.current_parameters = {}
        self._price_history.clear()
        self._previous_unrealized_pnl = 0.0
        self.last_observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        # Pre-fill initial price history using Close prices
        initial_steps_to_fill = min(len(self.current_data_df), self._price_history.maxlen)
        for i in range(initial_steps_to_fill):
            try:
                price = float(self.current_data_df.iloc[i].get('Close', 0.0)) # Use Close
                self._price_history.append(price if pd.notna(price) else 0.0)
            except (IndexError, ValueError, TypeError):
                 self._price_history.append(0.0)

        # Get initial observation
        if len(self.current_data_df) > 0:
            self._last_step_processed_index = 0
            observation = self._get_observation()
            self._last_step_processed_index = -1
        else:
            logger.error(f"DataFrame for mint {self.current_mint} is empty after reset. Cannot generate initial observation.")
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        info = {}
        return observation, info

    def render(self, mode='human'):
        """Renders the environment state (Same as before)."""
        if mode == 'ansi':
            output = f"--- Step: {self.current_step}/{self._max_episode_steps} (Index: {self._last_step_processed_index}) ---\n"
            output += f"Mint: {self.current_mint}\n"
            output += f"SOL Balance: {self.current_sol:.4f}\n"
            if self.active_position:
                pos = self.active_position
                pnl_norm = self.last_observation[rl_config.OBSERVATION_FEATURES.index('position_pnl_norm')]
                output += f"Holding: {pos['remaining_tokens']:.4f} tokens (Bought @ {pos['buy_price']:.9f})\n"
                output += f"  Norm PnL: {pnl_norm:.3f}, Highest Price: {pos['highest_price']:.9f}\n"
                output += f"  SL: {pos['stop_loss_price']:.9f}, TP1: {pos['initial_tp_price']:.9f}, TP2: {pos['second_tp_price']:.9f}\n"
            else:
                output += "Holding: None\n"
            output += f"Agent Params: {self.current_parameters}\n"
            # Add last Close price
            last_close = self._price_history[-1] if self._price_history else 'N/A'
            output += f"Last Close Price: {last_close}\n"
            return output
        elif mode == 'human':
            print(self.render(mode='ansi'))

    def close(self):
        """Cleans up environment resources."""
        pass

```

---

### 📄 rl_trainer.py

```python
# FILE: rl_trainer.py (Updated Env Initialization)

"""
Reinforcement Learning Agent Training Script.

Orchestrates the training process for an RL agent using Stable Baselines3
to learn optimal trading parameters for the custom TradingEnv environment.

to see training details use:
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
from logger import logger, setup_logging
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
    """Analyzes feature importance using SHAP with proper output handling."""
    # Generate properly structured samples
    samples = np.array([env.observation_space.sample() for _ in range(num_samples)])
    
    # Create wrapper function that returns proper numpy array
    def model_predict_wrapper(x):
        # Stable Baselines3 returns (action, state) tuple
        return np.array([model.predict(sample)[0] for sample in x])

    # SHAP Analysis
    explainer = shap.Explainer(
        model_predict_wrapper, 
        samples,
        feature_names=rl_config.OBSERVATION_FEATURES
    )
    
    # Calculate SHAP values in batches to manage memory
    shap_values = explainer(samples[:100])  # Use smaller subset for demonstration
    
    # Plot summary
    plt.figure()
    shap.summary_plot(shap_values, samples[:100], show=False)
    plt.savefig(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_shap.png"))
    plt.close()

    # Permutation Importance
    def score_fn(X):
        return np.array([model.predict(x)[0] for x in X])

    result = permutation_importance(
        score_fn, 
        samples[:100], 
        n_repeats=5, 
        random_state=42,
        n_jobs=-1
    )
    
    # Save results
    importance_df = pd.DataFrame({
        'feature': rl_config.OBSERVATION_FEATURES,
        'importance_mean': result.importances_mean(axis=1),
        'importance_std': result.importances_std(axis=1)
    }).sort_values('importance_mean', ascending=False)
    
    importance_df.to_csv(os.path.join(rl_config.MODEL_SAVE_DIR, "feature_importance_permutation.csv"), index=False)
    
    logger.info("Feature importance analysis completed")

# --- Environment Creation Helper ---
def make_env_func(
    data_dict: Dict[str, pd.DataFrame],
    lifespan_dict: Dict[str, Dict[str, datetime]], # Add lifespans
    initial_capital: float,
    max_steps: int,
    rank: int = 0,
    seed: int = 0
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

        if not valid_data or not valid_lifespans:
            logger.error(f"make_env_func (rank {rank}) received empty/invalid data or missing lifespans!")
            raise ValueError(f"Cannot create environment for rank {rank} with empty data or missing lifespans.")

        env = TradingEnv(
            historical_data_dict=valid_data,
            token_lifespans=valid_lifespans, # Pass lifespans
            initial_capital=initial_capital,
            max_steps=max_steps
        )
        env.reset(seed=seed + rank) # Seed the environment
        log_dir_monitor = os.path.join(rl_config.MODEL_SAVE_DIR, f"monitor_logs_{rank}")
        os.makedirs(log_dir_monitor, exist_ok=True)
        env = Monitor(env, filename=log_dir_monitor)
        return env
    return _init

# --- Main Training Function ---
async def train_rl_agent():
    """Sets up the RL environment, agent, callbacks, and starts training."""
    global db_client_global
    setup_logging(logger_name="rl_trainer") # Initialize logger for this module
    logger.info("--- Starting RL Agent Training ---")

    if not RL_AVAILABLE:
        logger.critical("Stable Baselines3 is not available. Cannot start RL training.")
        return

    # --- Database Connection ---
    # (Connect DB - same as before)
    if not db_client_global:
        db_client_global = DatabaseClient()
        try:
            await db_client_global.connect()
            logger.info("DB Client connected for RL Trainer.")
        except Exception as e:
            logger.critical(f"Failed to connect database for RL Trainer: {e}")
            return

    # --- Load and Prepare Data (Receives data AND lifespans) ---
    start_date = rl_config.RL_HISTORICAL_DATA_START_TS
    end_date = rl_config.RL_HISTORICAL_DATA_END_TS
    data_split_config = rl_config.DATA_SPLIT_RL

    logger.info(f"Loading and splitting data from {start_date.isoformat()} to {end_date.isoformat()}...")
    loaded_results: Optional[Tuple[Dict, Dict]] = await load_and_split_data(db_client_global, start_date, end_date, data_split_config)

    if loaded_results is None:
        logger.critical("Failed to load or split data. Exiting.")
        if db_client_global: await db_client_global.close()
        return

    loaded_data_sets, token_lifespans = loaded_results # Unpack

    # Create an output directory for the datasets
    # output_dir = os.path.join("data", "exported_datasets", datetime.now().strftime("%Y%m%d_%H%M%S"))

    # # Export the datasets and token lifespans
    # export_to_csv(loaded_data_sets, output_dir, token_lifespans)
    # logger.info(f"Exported datasets and token lifespans to {output_dir}")

    training_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_TRAIN)
    eval_data = loaded_data_sets.get(rl_config.DATA_SET_KEY_EVAL)
    # Filter lifespans to match the data splits
    train_lifespans = {k: v for k, v in token_lifespans.items() if k in training_data} if training_data else {}
    eval_lifespans = {k: v for k, v in token_lifespans.items() if k in eval_data} if eval_data else {}


    if not training_data or not train_lifespans:
        logger.critical("No training data or corresponding lifespans available after loading/splitting. Exiting.")
        if db_client_global: await db_client_global.close()
        return

    logger.info(f"Training data loaded for {len(training_data)} tokens with lifespan info.")
    if eval_data and eval_lifespans:
        logger.info(f"Evaluation data loaded for {len(eval_data)} tokens with lifespan info.")
    else:
        logger.warning("No evaluation data/lifespans found. Evaluation callback will not function correctly.")
        eval_data = None # Ensure eval_data is None if lifespans are missing
        eval_lifespans = {}

    # --- Create Vectorized Environments ---
    logger.info("Creating RL Vectorized Environments...")
    train_env_raw: Optional[VecEnv] = None
    eval_env_raw: Optional[VecEnv] = None
    train_env: Optional[VecNormalize] = None
    eval_env: Optional[VecNormalize] = None


    try:
        VecEnvClass = SubprocVecEnv if rl_config.N_ENVS > 1 else DummyVecEnv

        # Create training environments, passing lifespans
        env_fns = [make_env_func(training_data, train_lifespans, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE, rank=i)
                   for i in range(rl_config.N_ENVS)]
        train_env_raw = VecEnvClass(env_fns)
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
            eval_env_fn = make_env_func(eval_data, eval_lifespans, rl_config.RL_INITIAL_CAPITAL, rl_config.MAX_STEPS_PER_EPISODE, rank=100)
            eval_env_raw = DummyVecEnv([eval_env_fn])
            logger.info("Created Evaluation VecEnv (DummyVecEnv).")
        else:
             eval_env_raw = None

        # --- Apply VecNormalize ---
        normalize_kwargs = {'norm_obs': True, 'norm_reward': False, 'gamma': 0.99}
        train_env = VecNormalize(train_env_raw, **normalize_kwargs)
        logger.info("Applied VecNormalize to training environment.")
        if eval_env_raw:
            eval_env = VecNormalize(eval_env_raw, training=False, **normalize_kwargs)
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
            ent_coef=0.01,  # Slightly increased for better exploration
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
            render=False,
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
        asyncio.run(train_rl_agent())
    except Exception as main_err:
         logger.critical(f"Critical error in RL trainer entry point: {main_err}", exc_info=True)
```

---

### 📄 trading_bot.py

```python
# FILE: trading_bot.py (Modified)

import argparse
import asyncio
import signal
import traceback
import inspect
import threading
import os
import time
import json
import numpy as np # <-- Add numpy import
import pandas as pd # <-- Add pandas import
from datetime import datetime, timezone, timedelta

import config as config_module
from database_handler import DatabaseClient
from trading_logic import TradingManager
from websocket_handler import WebSocketHandler
from logger import setup_logging, log_info, log_debug, log_error, log_warning, log_critical, rotate_log_file
from state_manager import GlobalState
from trade_processor import trade_worker
from sol_price_api import update_sol_price
from rugcheck_handler import Rugcheck
from socials_processor import SocialsProcessor
from utils import calculate_volatility

# --- RL Imports (add these) ---
try:
    import stable_baselines3
    # Import the specific algorithm class you trained (e.g., PPO)
    from stable_baselines3 import PPO # Or SAC, TD3, etc.
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
# Import RL config to know parameter names and observation details
import rl_config

# --- End RL Imports ---


# Define paths for communication files relative to project root
COMMAND_FILE = os.path.join('data', 'bot_command.txt')
STATUS_FILE = os.path.join('data', 'bot_status.txt')
DYNAMIC_CONFIG_FILE = os.path.join('data', 'dynamic_config.json')

class TradingBot:
    """Main class for running the trading bot."""

    # Modify __init__ to accept RL agent path
    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, rl_agent_path: str = None):
        """Initialize the TradingBot with optional cleanup, backup, GA params file, and RL agent path."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.state = GlobalState.get_instance()
        self.cleanup = cleanup
        self.backup = backup
        self.params_file = params_file # Store the GA params file path
        self.rl_agent_path = rl_agent_path # Store the RL agent path
        self.rl_agent = None # Placeholder for loaded RL agent
        self.db_client = None #DatabaseClient()
        self.ws_handler = None #WebSocketHandler(db_client=self.db_client)
        self.tasks = []

        # --- Configuration Handling ---
        self.config = {} # Holds the *active* configuration (mutable dictionary)
        self.base_config = {} # Holds the config as loaded initially from config.py
        self._load_base_config() # Load initial config into self.config and self.base_config
        # --- End Configuration Handling ---

        # Initialize trading_manager later in main after full config setup
        self.trading_manager = None
        self._write_status("INITIALIZING")
        self._last_dynamic_config_mtime = 0 # For config_updater task

    # --- Add a helper to filter non-JSON serializable types ---
    def _filter_serializable_config(self, config_dict):
        serializable_config = {}
        skipped_keys = []
        for key, value in config_dict.items():
            # Convert sets to lists for JSON serialization
            if isinstance(value, set):
                serializable_config[key] = list(value)
            elif isinstance(value, (timedelta)): # Add other types like custom classes if needed
                skipped_keys.append(key)
            else:
                serializable_config[key] = value
        if skipped_keys:
            log_debug(f"Skipped non-serializable keys when preparing config for JSON: {skipped_keys}")
        return serializable_config
    # --- End helper ---

    def _load_base_config(self):
        """Loads configuration from the config module into dictionaries."""
        try:
            loaded_config = {}
            for key in dir(config_module):
                # Load only uppercase variables that are not modules/classes/functions
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config_module, key)
                    # Check type to exclude modules etc. Be careful with complex types like timedelta
                    if not inspect.ismodule(value) and \
                       not inspect.isclass(value) and \
                       not inspect.isfunction(value):
                        loaded_config[key] = value

            self.base_config = loaded_config.copy() # Store the initial load
            self.config = loaded_config.copy() # Active config starts as base
            log_info(":gear: Base configuration loaded successfully.")
            log_debug(f"Initial Config: {self.config}") # Debug log loaded config
        except Exception as e:
            log_critical(f":x: [bold red]CRITICAL: Failed to load base configuration[/bold red]: {e}", exc_info=True)
            # Potentially raise the error or exit if config loading fails
            raise ValueError("Failed to load critical base configuration.") from e
        
    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""

        def signal_handler():
            log_info(":heavy_exclamation_mark: [bold red]Signal received[/bold red], initiating shutdown...")
            self.state.trigger_shutdown()

        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, lambda *_: signal_handler())
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, lambda *_: signal_handler())

    def _write_status(self, status):
        """Writes the bot's status to the status file."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                f.write(status.upper())
            log_debug(f"Status updated to: {status.upper()}")
        except IOError as e:
            log_error(f"Error writing status file {STATUS_FILE}: {e}")
        except Exception as e:
             log_error(f"Unexpected error writing status file: {e}", exc_info=True)

    #     log_info("⚙️ Dynamic config updater task shutting down.")
    async def config_updater(self):
        """Periodically checks dynamic_config.json for updates and applies them."""
        log_info(f"⚙️ Dynamic config updater started. Watching: {os.path.abspath(DYNAMIC_CONFIG_FILE)}")

        while not self.state.shutdown_event.is_set():
            await asyncio.sleep(10)  # Check every 10 seconds
            try:
                if not os.path.exists(DYNAMIC_CONFIG_FILE):
                    continue  # Nothing to do if file doesn't exist

                current_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)

                if current_mtime > self._last_dynamic_config_mtime:
                    log_info(f"Detected change in {DYNAMIC_CONFIG_FILE}. Attempting to load updates.")
                    try:
                        with open(DYNAMIC_CONFIG_FILE, 'r') as f:
                            dynamic_conf = json.load(f)

                        if not isinstance(dynamic_conf, dict):
                            log_warning(f"Invalid format in {DYNAMIC_CONFIG_FILE}: Expected JSON object. Skipping update.")
                            self._last_dynamic_config_mtime = current_mtime
                            continue

                        # Convert specific lists to sets before processing
                        set_conversions = {
                            'SOCIALS_DISALLOWED_WEBSITE_DOMAINS': set,
                            'SOCIALS_ALLOWED_NEWS_DOMAINS': set
                        }
                        for key, converter in set_conversions.items():
                            if key in dynamic_conf and isinstance(dynamic_conf[key], list):
                                dynamic_conf[key] = converter(dynamic_conf[key])

                        updated_count = 0
                        for key, value in dynamic_conf.items():
                            key_upper = key.upper()
                            if key_upper in self.config:
                                current_value = self.config[key_upper]

                                # Handle set comparisons properly
                                if isinstance(value, set) and isinstance(current_value, set):
                                    if value != current_value:
                                        self.config[key_upper] = value
                                        log_info(f"⚙️ Dynamic Config Update: '{key_upper}' changed to {value}")
                                        updated_count += 1
                                    continue

                                # Original type checking logic
                                if isinstance(value, type(current_value)) or \
                                (isinstance(value, int) and isinstance(current_value, float)):
                                    # Type conversion logic
                                    if isinstance(value, int) and isinstance(current_value, float):
                                        value_to_set = float(value)
                                    else:
                                        value_to_set = value

                                    if value_to_set != current_value:
                                        self.config[key_upper] = value_to_set
                                        log_info(f"⚙️ Dynamic Config Update: '{key_upper}' changed from {current_value} to {value_to_set}")
                                        updated_count += 1
                                else:
                                    log_warning(f"Type mismatch for '{key_upper}'. Expected {type(current_value)}, got {type(value)}. Skipping.")

                        if updated_count > 0:
                            log_info(f"Applied {updated_count} configuration updates from {DYNAMIC_CONFIG_FILE}.")
                        else:
                            log_info("No configuration values changed in dynamic config.")

                        self._last_dynamic_config_mtime = current_mtime

                    except json.JSONDecodeError as e:
                        log_error(f"JSON decode error in {DYNAMIC_CONFIG_FILE}: {e}. Skipping update.")
                    except Exception as e:
                        log_error(f"Error processing dynamic config: {e}", exc_info=True)

            except FileNotFoundError:
                if self._last_dynamic_config_mtime != 0:
                    log_info(f"{DYNAMIC_CONFIG_FILE} was removed.")
                    self._last_dynamic_config_mtime = 0
            except Exception as e:
                log_error(f"Error in config_updater loop: {e}", exc_info=True)
                await asyncio.sleep(30)

        log_info("⚙️ Dynamic config updater task shutting down.")
    # --- End config_updater task ---

    async def monitor_tasks(self):
        """Monitor and log the status of background tasks."""
        try:
            while not self.state.shutdown_event.is_set():
                try:
                    rug_queue_size = self.state.get_rugcheck_queue().qsize()
                    tokens_subscribed = list(await self.state.get_token_subscriptions())
                    task_status = [f"{task.get_name()}: {'[bold yellow]done[/bold yellow]' if task.done() else '[bold green]running[/bold green]'}\n" for task in self.tasks]
                    sol_amount = await self.state.get_current_sol_balance()

                    # Add RL agent status if loaded
                    rl_status = f"[bold cyan]│[/bold cyan] :brain: [bold]RL Agent:[/bold] {'Loaded' if self.rl_agent else 'Not Loaded'}\n"

                    log_debug(
                        f"\n"
                        f"[bold cyan]┌────────────────────────────────────[/bold cyan]\n"
                        f"[bold cyan]│[/bold cyan] :robot: [bold magenta]Task Monitor[/bold magenta]\n"
                        f"[bold cyan]│────────────────────────────────────[/bold cyan]\n"
                        f"{rl_status}" # Add RL status here
                        f"[bold cyan]│[/bold cyan] :moneybag: [bold]Actual SOL amount:[/bold] {sol_amount:.6f}\n"
                        f"[bold cyan]│[/bold cyan] :label: [bold]Subscribed tokens:[/bold] {len(tokens_subscribed)}\n"
                        f"[bold cyan]│[/bold cyan] :recycle: [bold]RugCheck Queue size:[/bold] {rug_queue_size}\n"
                        f"[bold cyan]│[/bold cyan] :gear: [bold]Active tasks:[/bold] {len([t for t in self.tasks if not t.done()])}/{len(self.tasks)}\n"
                        f"[bold cyan]│[/bold cyan] :clipboard: [bold]Tasks:[/bold]\n"
                        f"[bold cyan]├──[/bold cyan] {'[bold cyan]├──[/bold cyan] '.join(task_status)}"
                        f"[bold cyan]└────────────────────────────────────[/bold cyan]\n"
                    )
                    await asyncio.sleep(5)
                except Exception as e:
                    log_error(f":x: [bold red]Monitor task error[/bold red]: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(60) # Sleep longer if monitor loop has error
        except asyncio.CancelledError:
            log_info(":stop_sign: Monitor task shutting down")

    async def status_updater(self):
        """Periodically writes 'RUNNING' status to the status file."""
        try:
            while not self.state.shutdown_event.is_set():
                self._write_status("RUNNING")
                await asyncio.sleep(15) # Update status every 15 seconds
        except asyncio.CancelledError:
            log_info(":stop_sign: Status updater task shutting down.")
        except Exception as e:
            log_error(f":x: Error in status updater: {e}", exc_info=True)
            self._write_status("ERROR") # Write error status if updater fails
        finally:
            # Attempt to write STOPPED status when task ends, unless shutdown already happened
             if not self.state.shutdown_event.is_set():
                  self._write_status("STOPPED") # Or maybe ERROR?

    async def command_listener(self):
        """Periodically checks the command file for STOP command."""
        last_command = None
        try:
            while not self.state.shutdown_event.is_set():
                command = None
                try:
                    if os.path.exists(COMMAND_FILE):
                        with open(COMMAND_FILE, 'r') as f:
                            command = f.read().strip().upper()

                        if command == "STOP" and last_command != "STOP":
                            log_info(f":hand: Received STOP command from {COMMAND_FILE}. Initiating shutdown...")
                            self.state.trigger_shutdown() # Trigger internal shutdown
                            last_command = "STOP"
                            # Optionally delete the command file after processing
                            try:
                                os.remove(COMMAND_FILE)
                                log_debug(f"Removed command file: {COMMAND_FILE}")
                            except OSError as e:
                                log_error(f"Error removing command file {COMMAND_FILE}: {e}")
                            break # Exit listener loop once stop is triggered

                        elif command == "START" and last_command != "START":
                             log_info(f":arrow_forward: Received START command from {COMMAND_FILE}. Bot should already be starting/running.")
                             last_command = "START"
                             # Optionally delete START command file? Or leave it?
                             # If left, bot might re-log this message on restart.

                        elif command == "UNSUB_NEWTOKEN" and last_command != "UNSUB_NEWTOKEN":
                            log_info(f":no_bell: Received UNSUB_NEWTOKEN command from {COMMAND_FILE}.")
                            last_command = "UNSUB_NEWTOKEN"
                            if self.ws_handler:
                                try:
                                    await self.ws_handler.unsubscribe_new_tokens()
                                except Exception as e:
                                     log_error(f"Error calling unsubscribe_new_tokens: {e}", exc_info=True)
                            else:
                                log_warning("Cannot unsubscribe new tokens: WebSocket handler not ready.")
                            # Clear the command file after processing
                            try:
                                with open(COMMAND_FILE, 'w') as f: f.write("") # Clear file
                                log_debug(f"Cleared command file: {COMMAND_FILE}")
                            except OSError as e:
                                log_error(f"Error clearing command file {COMMAND_FILE}: {e}")

                        elif command and command not in ["START", "STOP", "UNSUB_NEWTOKEN"] and command != last_command:
                             log_warning(f"Ignoring unknown command '{command}' in {COMMAND_FILE}")
                             last_command = command # Avoid re-logging warning
                             # Clear the command file after processing unknown command
                             try:
                                 with open(COMMAND_FILE, 'w') as f: f.write("") # Clear file
                                 log_debug(f"Cleared command file: {COMMAND_FILE}")
                             except OSError as e:
                                 log_error(f"Error clearing command file {COMMAND_FILE}: {e}")

                        elif not command and last_command:
                            # If file is now empty, reset last_command to allow re-reading
                            last_command = None

                except IOError as e:
                    log_error(f"Error reading command file {COMMAND_FILE}: {e}")
                except Exception as e:
                    log_error(f"Unexpected error in command listener: {e}", exc_info=True)

                await asyncio.sleep(5) # Check command file every 5 seconds
        except asyncio.CancelledError:
            log_info(":stop_sign: Command listener task shutting down.")
        finally:
             log_debug("Command listener task finished.")

    async def shutdown(self):
        """Gracefully shut down all tasks and close resources."""
        log_info(":stop_button: [bold red]Shutdown initiated[/bold red]. Cleaning up resources...")
        self._write_status("STOPPING") # Update status during shutdown
        try:
            await asyncio.wait_for(self.ws_handler.shutdown(), timeout=60)
            log_info(":link: WebSocket shutdown complete.")
        except Exception as e:
            log_error(f":x: WebSocket shutdown error: {e}", exc_info=True)

        for task in self.tasks:
            task.cancel()
            log_debug(f":no_entry: Cancelling task: {task.get_name()}")

        # Backup creator wallets before closing the pool
        try:
            await self.db_client.backup_creator_wallets()
        except Exception as e:
            log_error(f":x: Error backing up creator wallets during shutdown: {e}", exc_info=True)

        if self.db_client and self.db_client.pool: # Check if pool exists before closing
            await self.db_client.pool.close()
            log_info(":electric_plug: Database connection closed.")
        else:
            log_info(":electric_plug: Database connection already closed or not initialized.")


        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            log_info(f"Waiting for {len(pending)} pending tasks to cancel...")
            await asyncio.gather(*pending, return_exceptions=True)
            log_info("Pending tasks cancelled.")
        else:
             log_info("No pending tasks found.")

        self._write_status("STOPPED") # Final status update
        log_info(":checkered_flag: Shutdown complete.")

    # --- RL Agent Integration Functions ---
    async def _get_live_observation(self) -> np.ndarray | None:
        """
        Gathers LIVE market and portfolio data and formats it into the
        observation format expected by the RL agent. Includes normalization.
        Returns None if essential data is missing or calculation fails.
        **NOTE:** This requires significant implementation based on live data sources.
        """
        log_debug("Attempting to generate live observation for RL agent...")
        obs_data = {} # Dictionary to hold raw feature values

        # --- Fetch Portfolio State ---
        try:
            obs_data['sol_balance'] = await self.state.get_current_sol_balance()
            active_positions = await self.db_client.get_active_buy_positions() # Assumes this returns quickly
            # Simplification: Focus observation on the *first* active position if multiple exist
            current_pos = active_positions[0] if active_positions else None
            obs_data['is_holding'] = 1.0 if current_pos else 0.0
        except Exception as e:
            log_error(f"Failed to get portfolio state for observation: {e}")
            return None

        # --- Fetch Market State (Focus on current position's mint if holding) ---
        target_mint = current_pos['mint'] if current_pos else None

        if target_mint:
            try:
                # Price, Volume, MC (Needs efficient fetching - maybe latest from DB?)
                latest_prices = await self.db_client.get_latest_prices([target_mint])
                if target_mint in latest_prices:
                    obs_data['current_price'] = latest_prices[target_mint]['price']
                    obs_data['market_cap'] = latest_prices[target_mint]['market_cap'] # Assuming SOL MC
                else:
                    log_warning(f"Could not get latest price/MC for active mint {target_mint}")
                    obs_data['current_price'] = current_pos['buy_price'] # Fallback? Risky
                    obs_data['market_cap'] = 0.0

                # --- Fetch recent trades for volume/volatility (Example DB Query) ---
                # This query needs optimization for speed in live trading
                query_recent = """
                    SELECT price, sol_amount as volume FROM trades
                    WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '10 minutes'
                    ORDER BY timestamp DESC LIMIT 100;
                """ # Adjust interval/limit as needed
                recent_trades = await self.db_client.pool.fetch(query_recent, target_mint)
                if recent_trades:
                    recent_df = pd.DataFrame(recent_trades, columns=['price', 'volume'])
                    obs_data['volume'] = recent_df['volume'].sum() # Example: sum volume
                    # Calculate volatility (needs sufficient points)
                    if len(recent_df) > 5:
                        prices_series = pd.Series(pd.to_numeric(recent_df['price'], errors='coerce'), index=pd.to_datetime(recent_df['timestamp'], errors='coerce', utc=True)).sort_index() # Create Series with time index
                        prices_series = prices_series.dropna()
                        # Use appropriate window size (e.g., matching training or a reasonable live window)
                        obs_data['volatility'] = calculate_volatility(prices_series, window=20) # Example window
                    else:
                        obs_data['volatility'] = 0.0
                else:
                    obs_data['volume'] = 0.0
                    obs_data['volatility'] = 0.0


                # Scores (Fetch latest from DB - needs dedicated functions)
                # obs_data['rugcheck_score'] = await self.db_client.get_latest_score(target_mint, 'rugcheck')
                # obs_data['socials_score'] = await self.db_client.get_latest_score(target_mint, 'socials')
                obs_data['rugcheck_score'] = 10000 # Placeholder
                obs_data['socials_score'] = 100 # Placeholder

                # Token creation time
                # token_info = await self.db_client.get_token_info(target_mint) # Needs function
                # obs_data['creation_time'] = token_info['timestamp'] if token_info else pd.NaT
                obs_data['creation_time'] = pd.NaT # Placeholder

            except Exception as e:
                log_error(f"Failed to get market state for {target_mint}: {e}")
                return None # Can't proceed without market data if holding
        else:
            # If not holding, what state to use? Average market state? Random token?
            # Simplest: return a 'neutral' state or zeros.
            log_debug("Not holding any position, generating neutral observation.")
            # Use defaults or averages if possible, otherwise zeros
            obs_data['current_price'] = 0.0
            obs_data['market_cap'] = 0.0
            obs_data['volume'] = 0.0
            obs_data['volatility'] = 0.0
            obs_data['rugcheck_score'] = 10000
            obs_data['socials_score'] = 100
            obs_data['creation_time'] = pd.NaT


        # --- Calculate Derived Features ---
        # Needs access to historical prices (e.g., stored in state_manager or queried)
        # This part is complex for live data - requires maintaining price history
        obs_data['price_change_1'] = 0.0 # Placeholder
        obs_data['price_change_5'] = 0.0 # Placeholder
        obs_data['price_change_10'] = 0.0 # Placeholder

        time_since_creation_seconds = 0
        if pd.notna(obs_data.get('creation_time')):
            time_diff = datetime.now(timezone.utc) - obs_data['creation_time'].replace(tzinfo=timezone.utc) # Ensure tz
            time_since_creation_seconds = max(0, time_diff.total_seconds())

        position_pnl_norm = 0.0
        steps_holding = 0 # How to track 'steps' live? Use time held instead.
        if obs_data['is_holding'] and current_pos:
            # Calculate PnL based on live price and DB data
            buy_price = float(current_pos['buy_price'])
            rem_tokens = float(current_pos['remaining_tokens'])
            total_investment = float(current_pos.get('total_investment_sol', 1.0) or 1.0)
            current_value = obs_data.get('current_price', buy_price) * rem_tokens
            initial_cost_for_remaining = buy_price * rem_tokens
            unrealized_pnl = current_value - initial_cost_for_remaining
            position_pnl_norm = unrealized_pnl / total_investment
            # Calculate time held instead of steps
            # time_held_seconds = (datetime.now(timezone.utc) - current_pos['timestamp'].replace(tzinfo=timezone.utc)).total_seconds()
            # steps_holding = time_held_seconds / 10 # Approximate steps if using 10s intervals

        # --- Normalization (MUST MATCH TRAINING ENV) ---
        # Apply the *exact same* normalization logic used in _get_observation
        norm_price_change_1 = np.clip(obs_data['price_change_1'] * 20, -1, 1)
        norm_price_change_5 = np.clip(obs_data['price_change_5'] * 10, -1, 1)
        norm_price_change_10 = np.clip(obs_data['price_change_10'] * 5, -1, 1)
        norm_volatility = np.clip(obs_data['volatility'] * 10, 0, 1)
        norm_market_cap = np.clip(np.log10(obs_data['market_cap'] + 1e-9) / 7, -1, 1)
        norm_volume = np.clip(np.log10(obs_data['volume'] + 1e-9) / 5, -1, 1)
        norm_rugcheck = np.clip(1.0 - (obs_data['rugcheck_score'] / 1000.0), 0, 1)
        norm_socials = np.clip(1.0 - (obs_data['socials_score'] / 100.0), 0, 1)
        norm_time_creation = np.clip(np.log10(time_since_creation_seconds + 1) / 6, 0, 1)
        norm_pos_pnl = np.clip(position_pnl_norm, -1, 1)
        norm_steps_held = np.clip(steps_holding / (rl_config.MAX_STEPS_PER_EPISODE * 0.5), 0, 1) # Or use normalized time held
        norm_sol_balance = np.clip(obs_data['sol_balance'] / (rl_config.RL_INITIAL_CAPITAL * 2.0), 0, 1)

        # --- Construct Observation Vector ---
        try:
            observation = np.array([
                norm_price_change_1, norm_price_change_5, norm_price_change_10,
                norm_volatility, norm_market_cap, norm_volume,
                norm_rugcheck, norm_socials, norm_time_creation,
                obs_data['is_holding'], norm_pos_pnl, norm_steps_held, norm_sol_balance
            ], dtype=np.float32)

            if observation.shape != (rl_config.OBSERVATION_SPACE_DIM,) or not np.all(np.isfinite(observation)):
                log_error(f"Live observation generation failed! Shape: {observation.shape}, Finite: {np.all(np.isfinite(observation))}")
                return None

            log_debug(f"Generated live observation: {observation}")
            return observation

        except Exception as e:
            log_error(f"Error constructing live observation array: {e}")
            return None


    async def run_rl_agent_updates(self):
        """Periodically query the RL agent and update trading parameters."""
        if not self.rl_agent:
            log_info("RL agent not loaded, skipping RL update task.")
            return

        log_info(":brain: Starting RL agent parameter update task...")
        while not self.state.shutdown_event.is_set():
            try:
                start_time = time.time()
                # 1. Get Live Observation
                observation = await self._get_live_observation()

                if observation is not None:
                    # 2. Predict Action (Parameters)
                    # Use deterministic=True for exploitation during live trading
                    action, _ = self.rl_agent.predict(observation, deterministic=True)
                    log_debug(f"RL Agent raw action output: {action}")

                    # 3. Apply Action (Update self.config used by TradingManager)
                    updated_params_count = 0
                    for i, (param_name, low, high, p_type) in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
                         # Clip action to ensure it's within training bounds
                        val = np.clip(action[i], low, high)
                        # Convert type if necessary (e.g., for int parameters)
                        current_val = p_type(val)
                        # Only log if value changes significantly?
                        if param_name in self.config and self.config[param_name] != current_val:
                             log_info(f"RL Agent Update: '{param_name}' changed from {self.config[param_name]} -> {current_val}")
                             self.config[param_name] = current_val # Update the shared config dictionary
                             updated_params_count += 1
                        elif param_name not in self.config:
                             log_info(f"RL Agent Update: Setting '{param_name}' -> {current_val}")
                             self.config[param_name] = current_val
                             updated_params_count += 1


                    if updated_params_count > 0:
                         log_info(f"Applied {updated_params_count} parameter updates from RL agent.")
                         # Pass the updated config to TradingManager if necessary,
                         # or ensure TradingManager reads from the updated self.config
                         if self.trading_manager:
                              self.trading_manager.config = self.config # Ensure manager uses the updated dict
                    else:
                         log_debug("RL Agent parameters did not change significantly.")

                else:
                    log_warning("Failed to get live observation for RL agent. Skipping parameter update.")

                # 4. Wait for the next interval
                end_time = time.time()
                wait_time = max(0, rl_config.AGENT_ACTION_INTERVAL_SECONDS - (end_time - start_time))
                await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                log_info(":no_entry_sign: RL agent update task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in RL agent update loop: {e}", exc_info=True)
                await asyncio.sleep(rl_config.AGENT_ACTION_INTERVAL_SECONDS) # Wait before retrying on error

    # --- End RL Agent Integration Functions ---


    async def main(self):
        """Main entry point for setting up and starting the bot."""
        self._write_status("STARTING")
        is_main_thread = threading.current_thread() is threading.main_thread()

        if is_main_thread:
            log_info("Running in main thread. Performing log rotation and registering signal handlers.")
            rotate_log_file()
        else:
             log_info("Running in a secondary thread. Skipping log rotation and signal handlers.")

        # Setup logging regardless of thread (moved from inside thread check)
        setup_logging()

        if is_main_thread:
            self.register_signal_handlers()

        # --- Load GA Parameters (if provided) ---
        if self.params_file and not self.rl_agent_path: # Only load GA if RL not specified
            log_info(f":dna: Attempting to load GA optimized parameters from: {self.params_file}")
            # ... (rest of GA param loading logic - same as before) ...
            if os.path.exists(self.params_file):
                try:
                    with open(self.params_file, 'r') as f:
                        optimized_data = json.load(f)
                    optimized_params = optimized_data.get('best_solution_parameters')
                    if optimized_params:
                        log_info(f":white_check_mark: Found {len(optimized_params)} GA optimized parameters.")
                        self.config.update(optimized_params) # Update config
                        log_info(":sparkles: Merged GA optimized parameters into configuration.")
                        overridden_keys = set(self.base_config.keys()) & set(optimized_params.keys())
                        log_debug(f"Overridden by GA: {overridden_keys}")
                    else:
                        log_warning(f":warning: 'best_solution_parameters' not found in {self.params_file}. Using base/default config.")
                except Exception as e:
                    log_error(f":x: Error loading GA parameters file {self.params_file}: {e}. Using base/default config.", exc_info=True)
            else:
                 log_warning(f":warning: GA Parameter file not found: {self.params_file}. Using base/default config.")

        # --- Load RL Agent (if provided) ---
        if self.rl_agent_path:
            if not RL_AVAILABLE:
                log_error(":x: RL Agent path specified, but Stable Baselines3 library is not installed!")
                log_error("Please install it: pip install stable-baselines3[extra]>=2.0.0a5")
                self.rl_agent_path = None # Disable RL mode
            else:
                log_info(f":brain: Attempting to load RL agent from: {self.rl_agent_path}")
                if os.path.exists(self.rl_agent_path):
                    try:
                        # Determine agent class based on config or filename convention? Assume PPO for now.
                        AgentClass = PPO # Or SAC, TD3 based on rl_config or how you save
                        self.rl_agent = AgentClass.load(self.rl_agent_path)
                        log_info(f":white_check_mark: Successfully loaded RL agent: {self.rl_agent_path}")
                        if self.params_file:
                            log_warning(":information: RL agent loaded, ignoring GA parameters file.")
                    except Exception as e:
                        log_error(f":x: Failed to load RL agent from {self.rl_agent_path}: {e}", exc_info=True)
                        self.rl_agent = None # Ensure agent is None if loading failed
                else:
                    log_warning(f":warning: RL Agent file not found: {self.rl_agent_path}. Cannot use RL agent.")
                    self.rl_agent = None

        # --- Final Config Log ---
        log_debug(f":wrench: FINAL CONFIG in use: {self.config}")
        if self.rl_agent:
             log_info(":robot: RL Agent will dynamically update parameters during runtime.")
             if self.params_file:
                log_warning(":information: RL agent loaded, ignoring GA parameters file for initial config (RL will override).")

        # --- Ensure data directory exists ---
        try:
            os.makedirs(os.path.dirname(DYNAMIC_CONFIG_FILE), exist_ok=True)
        except OSError as e:
             log_error(f"Could not create data directory '{os.path.dirname(DYNAMIC_CONFIG_FILE)}': {e}")
             # Decide if this is critical - maybe continue if dir already exists?

        # --- Write Initial Config to JSON if it doesn't exist ---
        try:
            if not os.path.exists(DYNAMIC_CONFIG_FILE):
                log_info(f"{DYNAMIC_CONFIG_FILE} not found. Writing initial configuration...")
                # Filter out non-serializable types before writing
                config_to_write = self._filter_serializable_config(self.config)
                with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    # Use indent for readability
                    json.dump(config_to_write, f, indent=4)
                log_info(f"Successfully wrote initial configuration to {DYNAMIC_CONFIG_FILE}")
                # Initialize the mtime tracker *after* writing the initial file
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
            else:
                log_info(f"Found existing {DYNAMIC_CONFIG_FILE}. Bot will use its contents for dynamic updates.")
                # Initialize the mtime tracker with the existing file's time
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)

        except (IOError, OSError, TypeError, json.JSONDecodeError) as e: # Added TypeError for json.dump issues
             log_error(f"Error handling initial dynamic config file {DYNAMIC_CONFIG_FILE}: {e}", exc_info=True)
             # Bot can likely continue, but dynamic updates might not work initially
             self._last_dynamic_config_mtime = 0 # Ensure updater tries to read later if possible
        # --- End Initial Config Write ---
        log_debug(f":wrench: FINAL INITIAL CONFIG in use: {self.config}")

        # --- Database and Services Setup ---
        try:
            self.db_client = DatabaseClient(self.config)
            await self.db_client.connect()
            await self.state.set_db_client(self.db_client)

            if self.backup:
                log_info(":floppy_disk: Starting database backup...")
                await self.db_client.backup_db(backup_flag=True)
                log_info(":white_check_mark: Database backup completed.")

            if self.cleanup:
                log_warning(":wastebasket: Starting database cleanup (dropping tables)...") # Changed to warning
                await self.db_client.cleanup_db(cleanup_flag=True)
                log_info(":white_check_mark: Database cleanup finished.")
                # No need to rotate log file again here

            log_info(":rocket: [bold]Initializing database schema...[/bold]")
            await self.db_client.init_db()
            log_info(":white_check_mark: Database schema initialized.")
            await self.db_client.restore_creator_wallets()
        except Exception as db_setup_err:
             log_critical(f"CRITICAL: Failed database setup: {db_setup_err}", exc_info=True)
             self._write_status("ERROR")
             return # Cannot continue without DB

        # --- Initialize Core Components ---
        # Initialize ws_handler here now that config is ready
        self.ws_handler = WebSocketHandler(db_client=self.db_client, config_dict=self.config, state_manager=self.state)
        await self.ws_handler.connect()
        await self.state.set_websocket_handler(self.ws_handler)

        # Pass the active self.config dictionary
        socials_proc = SocialsProcessor(state=self.state, db_client=self.db_client, config_dict=self.config)
        rugchecker = Rugcheck(state=self.state, db_client=self.db_client, websocket_handler=self.ws_handler, socials_processor=socials_proc, config_dict=self.config)
        self.trading_manager = TradingManager(db_client=self.db_client, config_dict=self.config, state=self.state) # Pass config dict


        # --- Start Background Tasks ---
        self.tasks = [
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"),
            asyncio.create_task(update_sol_price(self.state, self.db_client), name="sol_price_updater"),
            asyncio.create_task(trade_worker(), name="trade_worker"),
            rugchecker.start(),
            socials_proc.start(),
            asyncio.create_task(self.run_buy_checks(), name="buy_opportunity_checker"),
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker"),
            asyncio.create_task(self.status_updater(), name="status_updater"),
            asyncio.create_task(self.command_listener(), name="command_listener"),
            asyncio.create_task(self.config_updater(), name="config_updater")
        ]
        # Start WebSocket tasks (listen, manage_subscriptions)
        self.tasks.extend(self.ws_handler.start())

        # --- Start RL Agent Update Task (if agent loaded) ---
        if self.rl_agent:
            self.tasks.append(asyncio.create_task(self.run_rl_agent_updates(), name="rl_agent_updater"))

        self._write_status("RUNNING") # Bot is now fully running

        # # --- Main Execution Loop ---
        # try:
        #     log_info(":rocket: [bold green]Trading bot started successfully.[/bold green] Listening for market updates...")
        #     await self.state.wait_for_shutdown()
        # except Exception as e:
        #     log_error(f"Main loop encountered an error: {e}", exc_info=True)
        #     self._write_status("ERROR") # Set status to error if main loop crashes

        # --- Main Execution Loop ---
        try:
            log_info(":rocket: [bold green]Trading bot started successfully.[/bold green] Listening for market updates...")
            # Wait for any task to finish (usually the shutdown signal)
            done, pending = await asyncio.wait(self.tasks, return_when=asyncio.FIRST_COMPLETED)
            log_info(f"Primary task finished: { {t.get_name() for t in done} }. Initiating shutdown.")
            # Trigger shutdown for remaining tasks if not already triggered
            if not self.state.shutdown_event.is_set():
                 self.state.trigger_shutdown()

        except Exception as e:
            log_critical(f"CRITICAL ERROR in main loop: {e}", exc_info=True)
            self._write_status("ERROR") # Set status to error if main loop crashes
            if not self.state.shutdown_event.is_set():
                 self.state.trigger_shutdown() # Trigger shutdown on critical error

    # --- run_buy_checks / run_sell_checks (No changes needed here) ---
    async def run_buy_checks(self):
        """Continuously check for buy opportunities."""
        log_info(":chart_with_upwards_trend: [bold]Starting buy opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                # TradingManager uses self.config, which might be updated by RL agent
                await self.trading_manager.check_trading_opportunities()
                await asyncio.sleep(10) # Consider if interval needs adjusting based on RL update freq
            except asyncio.CancelledError:
                log_info(":no_entry_sign: Buy checker task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in buy checker loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def run_sell_checks(self):
        """Continuously check for sell opportunities."""
        log_info(":chart_with_downwards_trend: [bold]Starting sell opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                 # TradingManager uses self.config, which might be updated by RL agent
                await self.trading_manager.check_sell_opportunities()
                await asyncio.sleep(3) # Consider if interval needs adjusting
            except asyncio.CancelledError:
                log_info(":no_entry_sign: Sell checker task cancelled.")
                break
            except Exception as e:
                log_error(f":x: Error in sell checker loop: {e}", exc_info=True)
                await asyncio.sleep(12)


# --- Modify main execution block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file containing optimized parameters from GA.")
    # Add argument for RL agent
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")

    args = parser.parse_args()

    # Set policy for Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def run_bot():
        bot = TradingBot(
            cleanup=args.cleanup,
            backup=args.backup,
            params_file=args.params_file,
            rl_agent_path=args.rl_agent_path
        )
        try:
            await bot.main()
        except (KeyboardInterrupt, SystemExit):
            log_info(":stop_button: [bold red]Interrupted by user.[/bold red] Exiting.")
        except Exception as e:
            log_error(f":x: Unexpected error: {e}", exc_info=True)
        finally:
            await bot.shutdown()

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nShutdown requested by user...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Bot shutdown complete.")
```

---

