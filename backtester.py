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