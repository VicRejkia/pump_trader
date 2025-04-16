"""
Backtesting Engine Module

Simulates trading strategies on historical data to evaluate performance.
"""

import pandas as pd
from datetime import datetime, timezone
from logger import logger
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
        - max_drawdown: Maximum peak-to-trough decline in portfolio value.
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
        "max_drawdown": 0.0,
        # Add more metrics as needed
    }

    if not trade_history:
        metrics["total_pnl"] = final_capital - initial_capital
        return metrics # Return basic PnL if no trades occurred

    # --- Basic Metrics ---
    metrics["total_trades"] = len([t for t in trade_history if t['type'] == 'sell']) # Count sell events as completed trades
    sell_trades = [t for t in trade_history if t['type'] == 'sell' and 'pnl' in t]

    for trade in sell_trades:
        pnl = trade.get('pnl', 0.0)
        if pnl > 0:
            metrics["winning_trades"] += 1
            metrics["total_profit"] += pnl
        elif pnl < 0:
            metrics["losing_trades"] += 1
            metrics["total_loss"] += abs(pnl) # Loss is positive here

    if metrics["total_trades"] > 0:
        metrics["win_rate"] = (metrics["winning_trades"] / metrics["total_trades"]) * 100 if metrics["total_trades"] > 0 else 0.0

    if metrics["winning_trades"] > 0:
        metrics["avg_profit_per_trade"] = metrics["total_profit"] / metrics["winning_trades"]

    if metrics["losing_trades"] > 0:
        metrics["avg_loss_per_trade"] = metrics["total_loss"] / metrics["losing_trades"]

    metrics["total_pnl"] = final_capital - initial_capital # Based on final portfolio value

    # --- Max Drawdown Calculation (Simplified Example) ---
    # Requires tracking portfolio value over time. This is a placeholder.
    # A more accurate calculation needs a time series of portfolio equity.
    # For now, just using the final PnL relative to initial capital as a rough idea (not true drawdown).
    peak_value = initial_capital
    portfolio_value = initial_capital # Start with initial capital
    max_drawdown = 0.0

    # This needs a proper equity curve simulation within run_backtest
    # Placeholder:
    # for value in equity_curve: # equity_curve needs to be generated during simulation
    #     if value > peak_value:
    #         peak_value = value
    #     drawdown = (peak_value - value) / peak_value
    #     if drawdown > max_drawdown:
    #         max_drawdown = drawdown
    # metrics["max_drawdown"] = max_drawdown * 100 # As percentage

    logger.debug(f"Calculated Metrics: {metrics}")
    return metrics


# --- Backtesting Core Function ---

async def run_backtest(parameters: dict, historical_data: pd.DataFrame, initial_capital: float) -> dict:
    """
    Runs a backtest simulation for a single token using the provided parameters
    and historical data.

    Args:
        parameters: A dictionary containing the trading parameters to use for this run
                    (e.g., {'SOL_TO_BUY': 0.1, 'INITIAL_STOP_LOSS_PERCENT': 20.0, ...}).
        historical_data: A pandas DataFrame for a single token, indexed by timestamp,
                         containing columns like 'price', 'volume', 'market_cap',
                         'rugcheck_score', 'socials_score', 'token_creation_time'.
        initial_capital: The starting capital in SOL for the simulation.

    Returns:
        A dictionary containing the performance metrics calculated by
        calculate_performance_metrics().
    """
    logger.info(f"Starting backtest for token (inferred from data) with parameters: {parameters}")
    if historical_data.empty:
        logger.warning("Historical data is empty. Cannot run backtest.")
        # Return metrics indicating no activity and zero PnL from initial capital
        return calculate_performance_metrics([], initial_capital, initial_capital)

    # --- Simulation Setup ---
    current_sol = initial_capital
    current_tokens = 0.0
    active_position = None # Stores info about the current buy position
    trade_history = []
    portfolio_value_over_time = [] # To track equity curve for drawdown

    # Extract parameters for easier access
    sol_to_buy = parameters.get('SOL_TO_BUY', 0.1)
    initial_stop_loss_percent = parameters.get('INITIAL_STOP_LOSS_PERCENT', 50.0)
    first_sell_percent = parameters.get('FIRST_SELL_PERCENT', 75.0)
    trailing_stop_loss_percent = parameters.get('TRAILING_STOP_LOSS_PERCENT', 50.0)
    second_take_profit_percent = parameters.get('SECOND_TAKE_PROFIT_PERCENT', 300.0)
    first_sell_profit_margin = parameters.get('FIRST_SELL_PROFIT_MARGIN', 30.0)
    # Add other parameters as needed (volume, marketcap thresholds etc.)
    volume_threshold = parameters.get('DEFAULT_VOLUME_THRESHOLD', 7500)
    marketcap_threshold = parameters.get('DEFAULT_MARKETCAP_THRESHOLD', 10000)
    rugcheck_threshold = parameters.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 600)
    socials_threshold = parameters.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 65)
    min_volatility = parameters.get('MIN_VOLATILITY', 0.2) # Need volatility calculation if used
    # Fees (consider making these optimizable too?)
    buy_fee_pct = 0.001 # Example fee
    sell_fee_pct = 0.001 # Example fee

    # --- Simulation Loop ---
    # Iterate through the historical data, timestamp by timestamp
    for timestamp, row in historical_data.iterrows():
        current_price = row['price']
        # Skip data points with invalid prices
        if pd.isna(current_price) or current_price <= 0:
            continue

        # Update portfolio value for drawdown calculation
        current_portfolio_value = current_sol + (current_tokens * current_price * (1 - sell_fee_pct)) # Estimate value if sold now
        portfolio_value_over_time.append({'timestamp': timestamp, 'value': current_portfolio_value})


        # --- Sell Logic ---
        if active_position:
            highest_price_since_buy = max(active_position['highest_price'], current_price)
            active_position['highest_price'] = highest_price_since_buy
            sell_reason = None
            sell_price = current_price
            tokens_to_sell = 0.0

            # 1. Check Stop Loss (Initial or Trailing)
            current_stop_loss_price = active_position['stop_loss_price']
            if not active_position['first_tp_hit']: # Initial Stop Loss
                if current_price <= current_stop_loss_price:
                    sell_reason = "Initial Stop Loss Hit"
                    tokens_to_sell = active_position['remaining_tokens']
            else: # Trailing Stop Loss (after TP1)
                trailing_sl_price = highest_price_since_buy * (1 - trailing_stop_loss_percent / 100.0)
                # Adjust SL upwards if trailing SL is higher than current SL (breakeven or previous trail)
                active_position['stop_loss_price'] = max(current_stop_loss_price, trailing_sl_price)
                if current_price <= active_position['stop_loss_price']:
                    sell_reason = "Trailing Stop Loss Hit"
                    tokens_to_sell = active_position['remaining_tokens']

            # 2. Check Second Take Profit (if TP1 already hit)
            if not sell_reason and active_position['first_tp_hit'] and current_price >= active_position['second_tp_price']:
                 sell_reason = "Second Take Profit Hit"
                 tokens_to_sell = active_position['remaining_tokens']

            # 3. Check First Take Profit (if not hit yet)
            if not sell_reason and not active_position['first_tp_hit'] and current_price >= active_position['initial_tp_price']:
                sell_reason = "First Take Profit Hit"
                tokens_to_sell = active_position['initial_tokens'] * (first_sell_percent / 100.0)
                # Ensure we don't sell more than we have
                tokens_to_sell = min(tokens_to_sell, active_position['remaining_tokens'])


            # --- Execute Sell ---
            if sell_reason:
                sol_received = tokens_to_sell * sell_price
                sell_fee = sol_received * sell_fee_pct
                net_sol_received = sol_received - sell_fee
                current_sol += net_sol_received
                current_tokens -= tokens_to_sell

                # Calculate PnL for this specific sell portion
                cost_basis_per_token = active_position['total_investment_sol'] / active_position['initial_tokens']
                cost_of_sold_tokens = tokens_to_sell * cost_basis_per_token
                pnl = net_sol_received - cost_of_sold_tokens

                logger.debug(f"{timestamp}: SELL {tokens_to_sell:.4f} tokens at {sell_price:.6f} SOL. Reason: {sell_reason}. PnL: {pnl:.4f} SOL.")
                trade_history.append({
                    'timestamp': timestamp, 'type': 'sell', 'price': sell_price,
                    'amount_sol': net_sol_received, 'amount_tokens': tokens_to_sell,
                    'fee': sell_fee, 'reason': sell_reason, 'pnl': pnl
                })

                active_position['remaining_tokens'] -= tokens_to_sell

                # Update position state after sell
                if sell_reason == "First Take Profit Hit":
                    active_position['first_tp_hit'] = True
                    # Adjust SL to breakeven (buy price)
                    active_position['stop_loss_price'] = active_position['buy_price']
                    logger.debug(f"{timestamp}: First TP hit. Stop loss adjusted to breakeven: {active_position['stop_loss_price']:.6f} SOL.")

                # If all tokens sold, close position
                if active_position['remaining_tokens'] < 1e-9: # Use tolerance for float comparison
                    logger.debug(f"{timestamp}: Position closed.")
                    active_position = None


        # --- Buy Logic ---
        if not active_position and current_sol >= sol_to_buy: # Check if we have enough SOL
            # Check conditions (Volume, Market Cap, Rugcheck, Socials, etc.)
            # Note: Historical data needs to have these values available at each timestamp.
            # The provided DataFrame structure assumes this.
            # We might need to calculate volume/volatility over a rolling window if not pre-calculated.
            current_volume = row.get('volume', 0) # Need volume calculation/data
            current_market_cap = row.get('market_cap', 0)
            current_rugcheck = row.get('rugcheck_score', 10000)
            current_socials = row.get('socials_score', 100)
            # current_volatility = row.get('volatility', 0) # Need volatility calculation/data

            passes_volume = True # Assume true if no volume data
            passes_marketcap = current_market_cap >= marketcap_threshold
            passes_rugcheck = current_rugcheck < rugcheck_threshold
            passes_socials = current_socials < socials_threshold
            # passes_volatility = current_volatility >= min_volatility

            # TODO: Add more sophisticated checks (e.g., rate of change, indicators) if needed.

            if passes_marketcap and passes_rugcheck and passes_socials: # Add other conditions
                # --- Execute Buy ---
                buy_amount_sol = min(sol_to_buy, current_sol) # Don't spend more than available
                buy_fee = buy_amount_sol * buy_fee_pct
                sol_for_tokens = buy_amount_sol - buy_fee
                tokens_bought = sol_for_tokens / current_price
                total_investment = buy_amount_sol # Including fee

                current_sol -= total_investment
                current_tokens += tokens_bought

                # Calculate initial SL and TP prices
                initial_sl_price = current_price * (1 - initial_stop_loss_percent / 100.0)
                # Calculate TP1 based on profit margin on *investment*
                required_sol_at_tp1 = total_investment * (1 + first_sell_profit_margin / 100.0)
                # Estimate tokens to sell at TP1
                tokens_to_sell_at_tp1 = tokens_bought * (first_sell_percent / 100.0)
                # Calculate price needed to achieve the required SOL from selling that portion (ignoring sell fee for simplicity here, or add it)
                initial_tp1_price = required_sol_at_tp1 / tokens_to_sell_at_tp1 if tokens_to_sell_at_tp1 > 0 else float('inf')

                second_tp_price = current_price * (1 + second_take_profit_percent / 100.0)


                active_position = {
                    'buy_timestamp': timestamp,
                    'buy_price': current_price,
                    'initial_tokens': tokens_bought,
                    'remaining_tokens': tokens_bought,
                    'total_investment_sol': total_investment,
                    'stop_loss_price': initial_sl_price,
                    'initial_tp_price': initial_tp1_price,
                    'second_tp_price': second_tp_price,
                    'highest_price': current_price,
                    'first_tp_hit': False,
                }

                logger.debug(f"{timestamp}: BUY {tokens_bought:.4f} tokens at {current_price:.6f} SOL. Invested: {total_investment:.4f} SOL. SL: {initial_sl_price:.6f}, TP1: {initial_tp1_price:.6f}, TP2: {second_tp_price:.6f}")
                trade_history.append({
                    'timestamp': timestamp, 'type': 'buy', 'price': current_price,
                    'amount_sol': total_investment, 'amount_tokens': tokens_bought,
                    'fee': buy_fee
                })


    # --- End of Simulation ---
    # Calculate final portfolio value (remaining SOL + value of remaining tokens)
    final_portfolio_value = current_sol
    if active_position and active_position['remaining_tokens'] > 0:
        # Use the last known price to value remaining tokens
        last_price = historical_data['price'].iloc[-1]
        if pd.notna(last_price) and last_price > 0:
             final_portfolio_value += active_position['remaining_tokens'] * last_price * (1 - sell_fee_pct) # Assume sold at last price
        else:
            logger.warning("Could not value remaining tokens at end of backtest due to invalid last price.")


    logger.info(f"Backtest finished. Initial SOL: {initial_capital:.4f}, Final SOL: {current_sol:.4f}, Remaining Tokens: {current_tokens:.4f}, Final Portfolio Value: {final_portfolio_value:.4f}")

    # --- Calculate Performance Metrics ---
    # Pass the proper equity curve to the calculator if implemented
    metrics = calculate_performance_metrics(trade_history, initial_capital, final_portfolio_value)

    # Add parameters used to the results for easy tracking
    metrics['parameters'] = parameters
    metrics['initial_capital'] = initial_capital
    metrics['final_portfolio_value'] = final_portfolio_value

    return metrics

# --- Example Usage (for testing) ---
async def main_test():
    # This is a placeholder for testing the backtester module directly.
    # You would need to:
    # 1. Connect to DB (or load data from file)
    # 2. Get historical data for a test token and date range
    # 3. Define test parameters
    # 4. Run the backtest
    # 5. Print the results

    from database_handler import DatabaseClient # Assuming relative import works
    from ga_config import OPTIMIZABLE_PARAMETERS, BACKTEST_INITIAL_CAPITAL
    import random

    # --- Dummy Data Generation (Replace with actual DB call) ---
    # Create a sample DataFrame
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min', tz='UTC')
    prices = 10 + pd.Series(range(1000)).apply(lambda x: random.uniform(-0.1, 0.1)).cumsum()
    prices = prices.clip(lower=0.01) # Ensure price doesn't go below zero
    data = pd.DataFrame({
        'price': prices,
        'volume': [random.uniform(100, 5000) for _ in range(1000)],
        'market_cap': [random.uniform(5000, 20000) for _ in range(1000)],
        'rugcheck_score': [random.randint(0, 800) for _ in range(1000)],
        'socials_score': [random.randint(20, 90) for _ in range(1000)],
        'token_creation_time': dates[0] # Dummy creation time
    }, index=dates)
    test_historical_data = data
    # --- End Dummy Data ---


    # --- Test Parameters ---
    test_params = {p['name']: random.uniform(p['low'], p['high']) if p['type'] == float else random.randint(p['low'], p['high'])
                   for p in OPTIMIZABLE_PARAMETERS}
    test_params['SOL_TO_BUY'] = 0.5 # Override for testing

    logger.info("--- Running Backtester Test ---")
    logger.info(f"Test Parameters: {test_params}")
    logger.info(f"Initial Capital: {BACKTEST_INITIAL_CAPITAL}")

    results = await run_backtest(test_params, test_historical_data, BACKTEST_INITIAL_CAPITAL)

    logger.info("--- Backtester Test Results ---")
    import pprint
    pprint.pprint(results)

if __name__ == "__main__":
    import asyncio
    # Configure logger for direct script execution
    from logger import setup_logging
    setup_logging()
    asyncio.run(main_test())