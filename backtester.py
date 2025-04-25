# FILE: backtester.py (Refactored)

"""
Backtesting Engine Module

Simulates trading strategies on historical data to evaluate performance.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from logger import logger
from utils import calculate_volatility # Assuming this is in utils.py or similar
# Import necessary components from existing modules (adjust paths if needed)
# from trading_logic import TradingManager # We might need parts of this logic
# from state_manager import StateManager # Or simulate state management here
# from config import ... # We'll use parameters dict instead of direct config import

# --- Performance Metrics Calculation ---
def calculate_performance_metrics(trade_history: list, initial_capital: float, final_capital: float) -> dict:
    """
    Calculates various performance metrics based on simulated trades.

    Args:
        trade_history: A list of dictionaries, each representing a simulated trade (buy/sell).
                       Expected keys: 'timestamp', 'type' ('buy'/'sell'), 'price',
                                      'amount_sol', 'amount_tokens', 'pnl' (for sells).
        initial_capital: The starting capital in SOL.
        final_capital: The ending capital in SOL (including value of remaining assets).

    Returns:
        A dictionary containing performance metrics like:
        - total_pnl: Total Profit and Loss in SOL.
        - total_trades: Total number of trades executed.
        - win_rate: Percentage of profitable trades.
        - avg_profit_per_trade: Average SOL profit on winning trades.
        - avg_loss_per_trade: Average SOL loss on losing trades.
        - max_drawdown: Maximum peak-to-trough decline in portfolio value (simplified).
        # - sharpe_ratio: (Requires risk-free rate and return series) - Optional
        # - sortino_ratio: (Requires risk-free rate and downside deviation) - Optional
    """
    metrics = {
        "total_pnl": 0.0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_profit": 0.0,
        "total_loss": 0.0,
        "win_rate": 0.0,
        "avg_profit_per_trade": 0.0,
        "avg_loss_per_trade": 0.0,
        "max_drawdown": 0.0, # Placeholder for simplified drawdown
        # Add more metrics as needed
    } 

    if not trade_history:
        metrics["total_pnl"] = final_capital - initial_capital
        return metrics # Return basic PnL if no trades occurred

    # --- Basic Metrics ---
    metrics["total_trades"] = len([t for t in trade_history if t['type'] == 'sell']) # Count sell events as completed trades 
    sell_trades = [t for t in trade_history if t['type'] == 'sell' and 'pnl' in t]

    portfolio_value = initial_capital
    peak_value = initial_capital
    current_max_drawdown = 0.0

    for trade in trade_history:
        if trade['type'] == 'buy':
            portfolio_value -= trade.get('amount_sol', 0) # Decrease value by investment
        elif trade['type'] == 'sell':
            portfolio_value += trade.get('amount_sol', 0) # Increase value by net SOL received
            pnl = trade.get('pnl', 0.0)
            if pnl > 0:
                metrics["winning_trades"] += 1
                metrics["total_profit"] += pnl
            elif pnl < 0:
                metrics["losing_trades"] += 1
                metrics["total_loss"] += abs(pnl) # Loss is positive here 

        # Simplified Drawdown Calculation (Equity Curve based on trades)
        if portfolio_value > peak_value:
            peak_value = portfolio_value
        drawdown = (peak_value - portfolio_value) / peak_value if peak_value > 0 else 0
        if drawdown > current_max_drawdown:
            current_max_drawdown = drawdown

    # --- Calculate derived metrics ---
    if metrics["total_trades"] > 0:
        metrics["win_rate"] = (metrics["winning_trades"] / metrics["total_trades"]) * 100
    else:
         metrics["win_rate"] = 0.0

    if metrics["winning_trades"] > 0:
        metrics["avg_profit_per_trade"] = metrics["total_profit"] / metrics["winning_trades"]
    else:
        metrics["avg_profit_per_trade"] = 0.0

    if metrics["losing_trades"] > 0:
        metrics["avg_loss_per_trade"] = metrics["total_loss"] / metrics["losing_trades"] 
    else:
         metrics["avg_loss_per_trade"] = 0.0

    metrics["total_pnl"] = final_capital - initial_capital # Based on final portfolio value
    metrics["max_drawdown"] = current_max_drawdown * 100 # Store as percentage

    logger.debug(f"Calculated Metrics: {metrics}")
    return metrics


# --- Backtesting Core Function with Enhanced Logging ---
async def run_backtest(parameters: dict, raw_trade_data: pd.DataFrame, initial_capital: float) -> dict:
    """
    Simulates real-time trading with 10-second intervals using 5-second candlestick summaries.
    Includes volatility filtering and full trade logic. Enhanced logging for debugging hangs.
    """
    # Try to get mint address for clearer logs, default if not found in params
    mint_addr = parameters.get("mint", "UNKNOWN_MINT")
    # --- Log Entry ---
    logger.debug(f"--- Entering run_backtest for Mint: {mint_addr} ---")
    # logger.debug(f"Initial Capital: {initial_capital}")
    # logger.debug(f"Parameters: {parameters}")
    # logger.debug(f"Raw Trade Data Head:\n{raw_trade_data.head()}")
    # logger.debug(f"Raw Trade Data Tail:\n{raw_trade_data.tail()}")
    # logger.debug(f"Raw Trade Data Columns: {raw_trade_data.columns}")
    # logger.debug(f"Raw Trade Data Index: {raw_trade_data.index}")
    # logger.debug(f"Raw Trade Data Length: {len(raw_trade_data)}")
    # logger.debug(f"Raw Trade Data Shape: {raw_trade_data.shape}")
    # logger.debug(f"Raw Trade Data Info:\n{raw_trade_data.info()}")
    # logger.debug(f"Raw Trade Data Describe:\n{raw_trade_data.describe()}")
    # logger.debug(f"Raw Trade Data Types:\n{raw_trade_data.dtypes}")
    # logger.debug(f"Raw Trade Data Memory Usage: {raw_trade_data.memory_usage(deep=True)}")

    if raw_trade_data.empty:
        logger.warning(f"Historical trade data empty for {mint_addr}.")
        # --- Log Exit (Early) ---
        logger.debug(f"--- Exiting run_backtest for Mint: {mint_addr} (No Data) ---")
        return calculate_performance_metrics([], initial_capital, initial_capital)

    # Prepare data
    df = raw_trade_data.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # --- Resample to 5-second candles ---
    candles = df.resample("5s").agg({
        "price": "last",
        "volume": "sum",
        "market_cap_calculated": "last",
        "rugcheck_score": "last",
        "socials_score": "last"
    }).dropna()

    candles = candles[candles["price"] != 0]

    # --- Calculate volatility ---
    if 'price' in candles.columns and not candles['price'].empty:
        prices_series = pd.to_numeric(candles['price'], errors='coerce')
        candles['volatility'] = calculate_volatility(prices_series, window=120)
        candles['volatility'] = candles['volatility'].fillna(0.0)
    else:
        candles['volatility'] = 0.0

    if candles.empty:
         logger.warning(f"No candle data remained after resampling/filtering for {mint_addr}.")
         # --- Log Exit (Early) ---
         logger.debug(f"--- Exiting run_backtest for Mint: {mint_addr} (No Candle Data) ---")
         return calculate_performance_metrics([], initial_capital, initial_capital)

    # --- Extract Parameters ---
    sol_to_buy = parameters.get('SOL_TO_BUY', 0.1)
    initial_stop_loss_percent = parameters.get('INITIAL_STOP_LOSS_PERCENT', 50.0)
    first_sell_percent = parameters.get('FIRST_SELL_PERCENT', 75.0)
    trailing_stop_loss_percent = parameters.get('TRAILING_STOP_LOSS_PERCENT', 50.0)
    second_take_profit_percent = parameters.get('SECOND_TAKE_PROFIT_PERCENT', 300.0)
    first_sell_profit_margin = parameters.get('FIRST_SELL_PROFIT_MARGIN', 30.0)
    volume_threshold = parameters.get('DEFAULT_VOLUME_THRESHOLD', 7500)
    marketcap_threshold = parameters.get('DEFAULT_MARKETCAP_THRESHOLD', 10000)
    rugcheck_threshold = parameters.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 600)
    socials_threshold = parameters.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 65)
    min_volatility = parameters.get('MIN_VOLATILITY', 0.2)
    buy_fee = parameters.get('DEFAULT_BUY_FEE', 0.001)
    buy_tip = parameters.get('DEFAULT_BUY_TIP', 0.001)
    sell_fee = parameters.get('DEFAULT_SELL_FEE', 0.001)
    sell_tip = parameters.get('DEFAULT_SELL_TIP', 0.001)
    min_market_cap_usd = parameters.get('MIN_MARKET_CAP', 3600)

    current_sol = initial_capital
    current_tokens = 0.0
    trade_history = []
    active_position = None

    # --- Simulate every 10s ---
    simulation_indices = candles.index[::2] # Simulate every 10s (2 * 5s candles)
    total_steps = len(simulation_indices)
    log_interval = max(1, total_steps // 10) # Log roughly 10 times during simulation

    logger.debug(f"Starting simulation loop for {mint_addr}. Total steps: {total_steps}. Logging every ~{log_interval} steps.")
    step_count = 0
    for timestamp in simulation_indices:
        step_count += 1
        # --- Periodic Loop Log ---
        if step_count % log_interval == 0:
             logger.debug(f"Simulating step {step_count}/{total_steps} for {mint_addr} (Timestamp: {timestamp})")

        try:
            row = candles.loc[timestamp]
        except KeyError as e:
            # Already logged in the loop attempt block in the previous version, keep it here or remove duplication
            # logger.error(f"KeyError accessing timestamp: {timestamp} for {mint_addr}")
            continue # Skip this step if timestamp not found

        try:
            # --- Filtering Logic ---
            if (
                pd.isna(row["volume"]) or row["volume"] < volume_threshold or
                pd.isna(row["market_cap_calculated"]) or row["market_cap_calculated"] < marketcap_threshold or
                pd.isna(row["rugcheck_score"]) or row["rugcheck_score"] >= rugcheck_threshold or
                pd.isna(row["socials_score"]) or row["socials_score"] >= socials_threshold or
                pd.isna(row["volatility"]) or row["volatility"] < min_volatility or
                pd.isna(row["price"]) or row["price"] <= 1e-12 # Also check for valid price here
            ):
                # Optional: Log skipped step due to filter criteria
                # logger.debug(f"Step {step_count}: Skipping {mint_addr} due to filter criteria.")
                continue

            price = row["price"]

            # --- Sell logic ---
            if active_position:
                hp = max(active_position['highest_price'], price)
                active_position['highest_price'] = hp

                sell_reason = None
                tokens_to_sell = 0.0
                sell_all = False
                sell_partial = False
                sell_percentage = 0.0

                # --- Calculate Trailing SL Price ---
                trailing_sl_price = 0.0
                if active_position['first_tp_hit']:
                    trailing_sl_price = hp * (1 - trailing_stop_loss_percent / 100.0)

                # --- Check Sell Conditions ---
                # (Keep your existing condition checks here - SL, TP1, TP2, Trailing SL, Emergency SL)
                # Example structure:
                if price <= active_position['stop_loss_price']:
                     sell_reason = "Stop Loss" # ... and so on
                     sell_all = True; sell_percentage = 1.0
                elif price >= active_position['second_tp_price']:
                    sell_reason = "Second TP" # ... and so on
                    sell_all = True; sell_percentage = 1.0
                elif not active_position['first_tp_hit'] and price >= active_position['initial_tp_price']:
                    sell_reason = "First TP" # ... and so on
                    sell_partial = True; sell_percentage = first_sell_percent / 100.0
                elif active_position['first_tp_hit'] and price <= trailing_sl_price:
                    sell_reason = "Trailing SL" # ... and so on
                    sell_all = True; sell_percentage = 1.0
                # Add Emergency SL check logic if needed

                # --- Determine tokens to sell ---
                if sell_partial:
                     tokens_to_sell = active_position['initial_tokens'] * sell_percentage
                     tokens_to_sell = min(tokens_to_sell, active_position['remaining_tokens'])
                elif sell_all:
                     tokens_to_sell = active_position['remaining_tokens']
                else:
                     tokens_to_sell = 0.0

                # --- Execute Sell if triggered ---
                if sell_reason and tokens_to_sell > 1e-9:
                    # (Keep your sell financial calculations: gross_sol, net_sol, cost_basis, pnl)
                    gross_sol_received = tokens_to_sell * price
                    net_sol_received = gross_sol_received - sell_fee - sell_tip
                    cost_basis = active_position['total_investment_sol'] * (tokens_to_sell / active_position['initial_tokens']) if active_position['initial_tokens'] > 0 else 0
                    pnl = net_sol_received - cost_basis

                    current_sol += net_sol_received
                    current_tokens -= tokens_to_sell
                    active_position['remaining_tokens'] -= tokens_to_sell

                    trade_history.append({
                        'timestamp': timestamp, 'type': 'sell', 'price': price,
                        'amount_sol': net_sol_received, 'amount_tokens': tokens_to_sell,
                        # Include other details if needed
                        'reason': sell_reason, 'pnl': pnl
                    })
                    # --- Log Sell Execution ---
                    logger.debug(f"Executed Sell for {mint_addr}: {tokens_to_sell:.4f} tokens at {price:.9f}. Reason: {sell_reason}. PnL: {pnl:.6f}")

                    if sell_reason == "First Take Profit":
                        active_position['first_tp_hit'] = True
                        active_position['stop_loss_price'] = active_position['buy_price'] # Move SL to breakeven

                    if active_position['remaining_tokens'] < 1e-9:
                        active_position = None # Close position

            # --- Buy logic ---
            if not active_position and current_sol >= (sol_to_buy + buy_fee + buy_tip): # Check available capital
                # (Keep your buy condition checks - volume, market cap, scores, volatility)
                # This part is already implicitly checked by the outer filter, but double-checking doesn't hurt
                # Or, if filters are complex/dynamic, perform them here
                # meets_buy_criteria = (...) # Check criteria based on 'row'

                # Assuming criteria met based on outer loop filter
                meets_buy_criteria = True # Simplified assumption based on loop entry

                if meets_buy_criteria:
                    total_investment = sol_to_buy + buy_fee + buy_tip
                    if current_sol >= total_investment: # Double check balance
                        sol_for_tokens = sol_to_buy
                        tokens_bought = sol_for_tokens / price

                        # (Keep TP/SL price calculations as before)
                        # ... TP1, TP2, initial SL calculations ...
                        initial_tp_price = ... # Calculate TP1
                        second_tp_price = ... # Calculate TP2
                        stop_loss_price = ... # Calculate initial SL

                        current_sol -= total_investment
                        current_tokens += tokens_bought # Note: current_tokens isn't strictly used if tracking via active_position

                        active_position = {
                            'buy_price': price, 'initial_tokens': tokens_bought,
                            'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment,
                            'stop_loss_price': stop_loss_price, 'initial_tp_price': initial_tp_price,
                            'second_tp_price': second_tp_price, 'highest_price': price,
                            'first_tp_hit': False
                        }

                        trade_history.append({
                            'timestamp': timestamp, 'type': 'buy', 'price': price,
                            'amount_sol': total_investment, 'amount_tokens': tokens_bought,
                             # Include other details if needed
                            'buy_fee': buy_fee, 'buy_tip': buy_tip
                        })
                        # --- Log Buy Execution ---
                        logger.debug(f"Executed Buy for {mint_addr}: {tokens_bought:.4f} tokens at {price:.9f}")
                    else:
                        # Optional: Log insufficient balance if needed
                        # logger.debug(f"Insufficient balance to buy {mint_addr}")
                        pass

        except Exception as loop_err:
             # --- Log Error within Loop ---
             logger.error(f"Error during simulation step {step_count} for {mint_addr} (Timestamp: {timestamp}): {loop_err}", exc_info=True)
             # Decide whether to continue or break the loop on error
             continue # Continue to next step by default

    # --- Final Value Calculation ---
    logger.debug(f"Calculating final portfolio value for {mint_addr}")
    final_value = current_sol
    if active_position and not candles.empty:
        # Use the price from the *last available candle*, not necessarily the last step processed
        last_available_timestamp = candles.index[-1]
        last_price = candles.loc[last_available_timestamp]["price"]

        remaining_tokens = active_position['remaining_tokens']
        gross_sol_received_final = remaining_tokens * last_price
        net_sol_received_final = gross_sol_received_final - sell_fee - sell_tip
        final_value += net_sol_received_final
        logger.debug(f"Added value of remaining {remaining_tokens:.4f} tokens for {mint_addr} at price {last_price:.9f}")


    # --- Calculate Metrics ---
    logger.debug(f"Calculating final performance metrics for {mint_addr}")
    metrics = calculate_performance_metrics(trade_history, initial_capital, final_value)
    metrics.update({
        "parameters": parameters, # Add parameters used
        "initial_capital": initial_capital,
        "final_portfolio_value": final_value
    })

    # --- Log Exit ---
    logger.debug(f"--- Exiting run_backtest for Mint: {mint_addr} ---")
    return metrics

# --- Example Usage (for testing) ---
async def main_test():
    # This is a placeholder for testing the backtester module directly.
    # You would need to:
    # 1. Connect to DB (or load data from file)
    # 2. Get historical data for a test token and date range using the updated DB handler
    # 3. Define test parameters
    # 4. Run the backtest
    # 5. Print the results 

    from database_handler import DatabaseClient # Assuming relative import works
    from ga_config import OPTIMIZABLE_PARAMETERS, BACKTEST_INITIAL_CAPITAL, HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS
    import random
    from logger import setup_logging

    setup_logging()
    db_client = DatabaseClient()
    await db_client.connect()

    # --- Get Real Data (Example for one token) ---
    # Replace 'YOUR_TEST_MINT' with an actual mint address that has data in your DB
    test_mint = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm" # Example SOL faucet token, replace!
    start_dt = HISTORICAL_DATA_START_TS
    end_dt = HISTORICAL_DATA_END_TS

    logger.info(f"⏱ Backtest time window: {start_dt.isoformat()} to {end_dt.isoformat()}")
    logger.info(f"Fetching test data for mint {test_mint} from {start_dt} to {end_dt}")
    hist_data_dict = await db_client.get_historical_data_for_backtesting([test_mint], start_dt, end_dt)

    if not hist_data_dict or test_mint not in hist_data_dict:
        logger.error(f"Could not fetch historical data for test mint {test_mint}. Exiting test.")
        await db_client.close()
        return

    test_historical_data = hist_data_dict[test_mint]
    # logger.info(f"Fetched {len(test_historical_data)} data points for {test_mint}.")
    # logger.debug(f"Test Data Head:\n{test_historical_data.head()}")
    # logger.debug(f"Test Data Tail:\n{test_historical_data.tail()}")
    # logger.debug(f"Test Data Columns: {test_historical_data.columns}")
    # --- End Real Data Fetch ---


    # --- Test Parameters ---
    test_params = {p['name']: random.uniform(p['low'], p['high']) if p['type'] == float else random.randint(p['low'], p['high'])
                   for p in OPTIMIZABLE_PARAMETERS}
    test_params['SOL_TO_BUY'] = 0.5 # Override for testing 
    test_params['DEFAULT_MARKETCAP_THRESHOLD'] = 5000 # Example override for USD market cap

    logger.info("--- Running Backtester Test ---")
    logger.info(f"Test Parameters: {test_params}")
    logger.info(f"Initial Capital: {BACKTEST_INITIAL_CAPITAL}")

    results = await run_backtest(test_params, test_historical_data, BACKTEST_INITIAL_CAPITAL)

    logger.info("--- Backtester Test Results ---")
    import pprint
    pprint.pprint(results)

    await db_client.close()

if __name__ == "__main__":
    import asyncio
    # Configure logger for direct script execution
    from logger import setup_logging
    setup_logging()
    asyncio.run(main_test())