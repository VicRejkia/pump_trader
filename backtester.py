# FILE: backtester.py (Refactored)

"""
Backtesting Engine Module

Simulates trading strategies on historical data to evaluate performance.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from logger import logger
# Import necessary components from existing modules (adjust paths if needed)
# from trading_logic import TradingManager # We might need parts of this logic
# from state_manager import StateManager # Or simulate state management here
# from config import ... # We'll use parameters dict instead of direct config import


def calculate_volatility(prices, window=120):
    """Calculate rolling volatility based on log returns over a window of 120 periods."""
    price_ratio = prices / prices.shift(1)
    log_returns = np.where(price_ratio <= 0, 0, np.log(price_ratio))
    return log_returns.rolling(window=window).std() * np.sqrt(window)

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


# --- Backtesting Core Function ---
async def run_backtest(parameters: dict, raw_trade_data: pd.DataFrame, initial_capital: float) -> dict:
    """
    Simulates real-time trading with 10-second intervals using 5-second candlestick summaries.
    Includes volatility filtering and full trade logic.
    """

    if raw_trade_data.empty:
        logger.warning("Historical trade data is empty.")
        return calculate_performance_metrics([], initial_capital, initial_capital)

    # Prepare data
    df = raw_trade_data.copy()
    df.index = pd.to_datetime(df.index)  # Ensure datetime index
    df = df.sort_index()

    # --- Resample to 5-second candles
    candles = df.resample("5s").agg({
        "price": "last",
        "volume": "sum",
        "market_cap_calculated": "last",
        "rugcheck_score": "last",
        "socials_score": "last"
    }).dropna()

    # --- Calculate volatility
    price_ratio = candles["price"] / candles["price"].shift(1)
    candles["log_return"] = np.where(price_ratio <= 0, 0, np.log(price_ratio))
    candles["volatility"] = candles["log_return"].rolling(window=120).std() * np.sqrt(120)

    # --- Extract Parameters
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

    buy_fee_pct = 0.001
    sell_fee_pct = 0.001

    current_sol = initial_capital
    current_tokens = 0.0
    trade_history = []
    active_position = None

    # --- Simulate every 10s
    logger.debug(f"Candles index type: {type(candles.index)}") # Debug log index type
    if not candles.empty: # Check if candles is not empty before accessing index
        sample_timestamp = candles.index[0] if not candles.empty else None # Get sample timestamp
        logger.debug(f"Sample timestamp from candles index: {sample_timestamp}") # Debug log sample timestamp

    for timestamp in candles.index[::2]:  # 2x5s = 10s interval
        try:
            row = candles.loc[timestamp]
        except KeyError as e:
            logger.error(f"KeyError accessing timestamp: {timestamp}, type: {type(timestamp)}, value: {timestamp}, in candles index: {e}")
            continue
        # row = candles.iloc[i] # Use integer index instead of timestamp

        if (
            row["volume"] < volume_threshold or
            row["market_cap_calculated"] < marketcap_threshold or
            row["rugcheck_score"] >= rugcheck_threshold or
            row["socials_score"] >= socials_threshold or
            row["volatility"] < min_volatility
        ):
            continue

        price = row["price"]

        # --- Sell logic
        if active_position:
            hp = max(active_position['highest_price'], price)
            active_position['highest_price'] = hp
            sell_reason = None
            tokens_to_sell = 0

            if price <= active_position['stop_loss_price']:
                sell_reason = "Stop Loss"
                tokens_to_sell = active_position['remaining_tokens']
            elif active_position['first_tp_hit']:
                trailing_sl = hp * (1 - trailing_stop_loss_percent / 100.0)
                effective_sl = max(active_position['stop_loss_price'], trailing_sl)
                if price <= effective_sl:
                    sell_reason = "Trailing Stop Loss"
                    tokens_to_sell = active_position['remaining_tokens']
                elif price >= active_position['second_tp_price']:
                    sell_reason = "Second Take Profit"
                    tokens_to_sell = active_position['remaining_tokens']
            elif price >= active_position['initial_tp_price']:
                sell_reason = "First Take Profit"
                tokens_to_sell = active_position['initial_tokens'] * (first_sell_percent / 100.0)

            if sell_reason and tokens_to_sell > 0:
                tokens_to_sell = min(tokens_to_sell, active_position['remaining_tokens'])
                sol_received = tokens_to_sell * price * (1 - sell_fee_pct)
                pnl = sol_received - (tokens_to_sell * (active_position['total_investment_sol'] / active_position['initial_tokens']))
                current_sol += sol_received
                current_tokens -= tokens_to_sell
                active_position['remaining_tokens'] -= tokens_to_sell

                trade_history.append({
                    'timestamp': timestamp,
                    'type': 'sell',
                    'price': price,
                    'amount_sol': sol_received,
                    'amount_tokens': tokens_to_sell,
                    'fee': sol_received * sell_fee_pct,
                    'reason': sell_reason,
                    'pnl': pnl
                })

                if sell_reason == "First Take Profit":
                    active_position['first_tp_hit'] = True
                    active_position['stop_loss_price'] = active_position['buy_price']

                if active_position['remaining_tokens'] < 1e-9:
                    active_position = None

        # --- Buy logic
        if not active_position and current_sol >= sol_to_buy:
            buy_fee = sol_to_buy * buy_fee_pct
            tokens_bought = sol_to_buy / price
            total_investment = sol_to_buy + buy_fee

            tp1_profit_margin = first_sell_profit_margin / 100.0
            sell_percent_tp1 = first_sell_percent / 100.0
            target_net_return = total_investment * (1 + tp1_profit_margin)
            gross_needed = target_net_return  # ignoring sell fees for now
            tokens_to_sell_tp1 = tokens_bought * sell_percent_tp1
            tp1_price = gross_needed / tokens_to_sell_tp1 if tokens_to_sell_tp1 > 0 else float('inf')
            tp2_price = price * (1 + second_take_profit_percent / 100.0)
            stop_loss_price = price * (1 - initial_stop_loss_percent / 100.0)

            current_sol -= total_investment
            current_tokens += tokens_bought

            active_position = {
                'buy_price': price,
                'initial_tokens': tokens_bought,
                'remaining_tokens': tokens_bought,
                'total_investment_sol': total_investment,
                'stop_loss_price': stop_loss_price,
                'initial_tp_price': tp1_price,
                'second_tp_price': tp2_price,
                'highest_price': price,
                'first_tp_hit': False
            }

            trade_history.append({
                'timestamp': timestamp,
                'type': 'buy',
                'price': price,
                'amount_sol': total_investment,
                'amount_tokens': tokens_bought,
                'fee': buy_fee
            })

    # --- Final Value
    final_value = current_sol
    if active_position:
        final_value += active_position['remaining_tokens'] * candles.iloc[-1]["price"] * (1 - sell_fee_pct)

    metrics = calculate_performance_metrics(trade_history, initial_capital, final_value)
    metrics.update({
        "parameters": parameters,
        "initial_capital": initial_capital,
        "final_portfolio_value": final_value
    })

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
    logger.info(f"Fetched {len(test_historical_data)} data points for {test_mint}.")
    logger.debug(f"Test Data Head:\n{test_historical_data.head()}")
    logger.debug(f"Test Data Tail:\n{test_historical_data.tail()}")
    logger.debug(f"Test Data Columns: {test_historical_data.columns}")
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