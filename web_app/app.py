import os
import threading
import queue
import sys
import asyncio
import pandas as pd
from flask import Flask, request, jsonify, render_template
import json         # For reading the price file
import requests     # For synchronous API fallback
import time         # For checking file age
import os           # For file path operations
from datetime import datetime, timezone
import numpy as np

# Add project root to the Python path to allow importing modules from the parent directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from database_handler import DatabaseClient
    from trading_bot import TradingBot
    from state_manager import GlobalState
    # Only import log_queue, not the logger instance or setup function from logger.py
    from logger import log_queue
    import config  # Import the API URL
except ImportError as e:
    print(f"Error importing modules: {e}. Make sure you are running from the project root or the necessary modules are in the Python path.")
    sys.exit(1)


# Define the path for the shared SOL price file (must match state_manager.py)
SOL_PRICE_FILE = 'data/sol_price.json'
MAX_FILE_AGE_SECONDS = 3600 # 5 minutes - how old the file can be before we call the API

# Removed global setup_logging() call. Bot will configure its own logging.
app = Flask(__name__)
# Removed redirection of Flask logger to keep logs separate
# Flask logs will go to console by default

db_client = DatabaseClient()

# Define paths for communication files relative to project root
COMMAND_FILE = os.path.join(project_root, 'data', 'bot_command.txt')
STATUS_FILE = os.path.join(project_root, 'data', 'bot_status.txt')
LOG_FILE = os.path.join(project_root, config.LOG_STORAGE_PATH, f"{config.LOGGER_NAME}.log")

async def get_db():
    """Helper function to get a database connection."""
    if not db_client.pool:
        try:
            await db_client.connect()
            app.logger.info("Database connection established.")
        except Exception as e:
            app.logger.error(f"Failed to connect to database: {e}")
            raise # Re-raise to handle in the route
    return db_client

# --- Helper Functions for File Flags ---
def write_command(command):
    """Writes a command (START/STOP) to the command file."""
    try:
        with open(COMMAND_FILE, 'w') as f:
            f.write(command.upper())
        app.logger.info(f"Wrote command '{command}' to {COMMAND_FILE}")
    except IOError as e:
        app.logger.error(f"Error writing command file {COMMAND_FILE}: {e}")

def read_status():
    """Reads the status (RUNNING/STOPPED) from the status file."""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r') as f:
                status = f.read().strip().upper()
                # Basic validation
                if status in ["RUNNING", "STOPPED", "STARTING", "STOPPING", "ERROR"]:
                     return status
                else:
                     app.logger.warning(f"Read invalid status '{status}' from {STATUS_FILE}. Defaulting to STOPPED.")
                     return "STOPPED" # Default to STOPPED if file content is invalid
        else:
            # If status file doesn't exist, assume stopped
            return "STOPPED"
    except IOError as e:
        app.logger.error(f"Error reading status file {STATUS_FILE}: {e}")
        return "ERROR" # Indicate an error reading the status

def convert_datetime(o):
    """Helper to serialize datetime objects."""
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Type {type(o)} not serializable")
# --- End Helper Functions ---

# Removed redundant /log_file endpoint. /logs now reads from the file.
# --- SOL Price Fetching Logic ---
def get_sol_price_from_file():
    """Tries to read the SOL price from the shared JSON file."""
    try:
        if os.path.exists(SOL_PRICE_FILE):
            file_mod_time = os.path.getmtime(SOL_PRICE_FILE)
            if (time.time() - file_mod_time) < MAX_FILE_AGE_SECONDS:
                with open(SOL_PRICE_FILE, 'r') as f:
                    data = json.load(f)
                    price = data.get("price")
                    if isinstance(price, (int, float)):
                        app.logger.info(f"Read SOL price {price} from file {SOL_PRICE_FILE}") # Use app.logger
                        return float(price)
                    else:
                        app.logger.warning(f"Invalid price data type in {SOL_PRICE_FILE}") # Use app.logger
            else:
                app.logger.warning(f"{SOL_PRICE_FILE} is older than {MAX_FILE_AGE_SECONDS} seconds.") # Use app.logger
        else:
            app.logger.info(f"{SOL_PRICE_FILE} not found.") # Use app.logger
    except (IOError, json.JSONDecodeError, KeyError, TypeError) as e:
        app.logger.error(f"Error reading SOL price from {SOL_PRICE_FILE}: {e}") # Use app.logger
    return None # Return None if file read fails or file is too old/missing

def get_sol_price_from_api():
    """Fetches the SOL price directly from the API (synchronous fallback)."""
    app.logger.info(f"Falling back to fetching SOL price directly from API: {config.SOL_PRICE_API_URL}") # Use app.logger
    try:
        response = requests.get(config.SOL_PRICE_API_URL, timeout=10) # Add timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        price = data.get("solana", {}).get("usd")
        if isinstance(price, (int, float)):
            app.logger.info(f"Fetched SOL price {price} from API") # Use app.logger
            return float(price)
        else:
            app.logger.error(f"Invalid price data type received from API: {price}") # Use app.logger
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching SOL price from API: {e}") # Use app.logger
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        app.logger.error(f"Error parsing SOL price API response: {e}") # Use app.logger
    return None # Return None if API call fails

def get_current_sol_price():
    """Gets SOL price, preferring the file, falling back to API."""
    price = get_sol_price_from_file()
    if price is None:
        price = get_sol_price_from_api()
    return price
# --- End SOL Price Fetching Logic ---

# Helper function to manage DB connection per request
async def execute_db_query(query_func, *args):
    """Creates a connection, executes a query function, and closes."""
    try:
        await db_client.connect()
        app.logger.debug("DB connection established for request.") # Use app.logger
        result = await query_func(db_client, *args)
        return result
    except Exception as e:
        app.logger.exception(f"Database query failed: {e}") # Use app.logger
        raise # Re-raise the exception to be handled by the route
    finally:
        if db_client.pool:
            await db_client.close()
            app.logger.debug("DB connection closed for request.") # Use app.logger

# Wrapper for the specific query needed by the API (trade history)
async def fetch_trade_history_query(db_client, mints):
    return await db_client.get_trade_history(mints)

# Wrapper for portfolio transactions query
async def fetch_portfolio_transactions_query(db_client, mints):
    return await db_client.get_portfolio_transactions(mints)
# Routes for the dashboard pages



@app.route('/logs')
def logs():
    """Reads the last N lines from the TradingBot log file."""
    MAX_LOG_LINES = 100 # Adjust as needed
    try:
        if not os.path.exists(LOG_FILE):
            return jsonify([]) # Return empty list if log file doesn't exist yet

        # Explicitly specify UTF-8 encoding and ignore errors
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            # Read all lines and take the last N
            lines = f.readlines()
            log_content = lines[-MAX_LOG_LINES:]
        # Strip newline characters for cleaner JSON output
        log_content = [line.strip() for line in log_content]
        return jsonify(log_content)
    except IOError as e:
        app.logger.error(f"Error reading log file {LOG_FILE}: {e}")
        return jsonify({"error": f"Could not read log file: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error reading log file {LOG_FILE}: {e}")
        return jsonify({"error": f"Unexpected error reading log file: {e}"}), 500
    
@app.route('/')
@app.route('/charts')
async def index():
    """Renders the main charts page. Token list is loaded dynamically via JS."""
    # No initial token fetching here anymore
    return render_template('token_price_analysis.html') # Pass no token list initially

@app.route('/config')
async def configuration():
    """Renders the configuration page."""
    return render_template('configuration.html')

@app.route('/portfolio')
async def portfolio():
    """Renders the portfolio page."""

    # Fetch all tracked tokens
    async def fetch_tracked_tokens_query(db_client, bc): # Added po
        return await db_client.get_total_tracked_tokens(backedup=bc) # Pass po

    try:
        # Execute the query using the helper
        fetched_tokens = await execute_db_query(
            fetch_tracked_tokens_query,
            False
        )
        app.logger.info(f"Returning {len(fetched_tokens)} tokens matching filters.") # Use app.logger
        print(fetched_tokens) # Debug print to check the data structure

        total_tracked_tokens = fetched_tokens
    
    except Exception as e:
        # Error already logged by execute_db_query
        app.logger.error(f"Failed to fetch filtered tokens for API request.") # Use app.logger
        return jsonify({"error": "Failed to fetch filtered tokens"}), 500
    
    return render_template('portfolio.html')

@app.route('/analytics')
async def analytics():
    """Renders the analytics page."""
    return render_template('analytics.html')

# API endpoint to get filtered tokens for the dropdown
@app.route('/api/filtered_tokens', methods=['GET'])
async def get_filtered_tokens_api():
    """API endpoint to fetch tokens based on filter criteria."""
    # Get filter parameters from query string, providing defaults
    max_socials = request.args.get('max_socials', default=100, type=int)
    max_rugcheck = request.args.get('max_rugcheck', default=10000, type=int)
    min_volume = request.args.get('min_volume', default=0, type=float)
    time_window_minutes = request.args.get('time_window', default=60, type=int) # e.g., 60, 360, 1440
    # Get portfolio_only flag, converting 'true'/'false' string to boolean
    portfolio_only = request.args.get('portfolio_only', default=False, type=lambda v: v.lower() == 'true')
    # Get volume aggregation type, default to 'avg'

    current_sol_price = get_current_sol_price()
    if current_sol_price is None:
         # Handle error: maybe return an error response or use a default SOL price
         app.logger.error("Could not get SOL price for volume conversion in /api/filtered_tokens") # Use app.logger
         return jsonify({"error": "Could not determine SOL price"}), 503

    min_volume_sol = (min_volume / current_sol_price) if min_volume > 0 and current_sol_price > 0 else 0 # Convert to SOL, handle zero price

    app.logger.info(f"Received request for filtered tokens: socials<={max_socials}, rug<={max_rugcheck}, vol>={min_volume_sol} (last {time_window_minutes} min), portfolio_only={portfolio_only}") # Use app.logger

    # Wrapper for the specific query needed by this route
    async def fetch_filtered_tokens_query(db_client, ms, mr, mv, tw, po): # Added po
        return await db_client.get_filtered_tokens(max_socials=ms, max_rugcheck=mr, min_volume_sol=mv, time_window_minutes=tw, portfolio_only=po) # Pass po

    try:
        # Execute the query using the helper
        filtered_tokens = await execute_db_query(
            fetch_filtered_tokens_query,
            max_socials,
            max_rugcheck,
            min_volume_sol,
            time_window_minutes,
            portfolio_only
        )
        app.logger.info(f"Returning {len(filtered_tokens)} tokens matching filters.") # Use app.logger
        return jsonify(filtered_tokens)
    except Exception as e:
        # Error already logged by execute_db_query
        app.logger.error(f"Failed to fetch filtered tokens for API request.") # Use app.logger
        return jsonify({"error": "Failed to fetch filtered tokens"}), 500

# API endpoint to get token chart data (remains largely the same)
@app.route('/api/token_chart_data', methods=['POST'])
async def get_token_chart_data():
    """API endpoint to fetch and process trade and portfolio data for charting."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    mints = data.get('mints')

    if not mints or not isinstance(mints, list):
        return jsonify({"error": "Missing or invalid 'mints' list in request body"}), 400

    app.logger.info(f"Received request for chart data for mints: {mints}") # Use app.logger

    try:
        # Execute the trade history query
        trade_history = await execute_db_query(fetch_trade_history_query, mints)
        # Execute the portfolio transactions query
        portfolio_transactions = await execute_db_query(fetch_portfolio_transactions_query, mints)

        if not trade_history:
            app.logger.warning(f"No trade history found for mints: {mints}") # Use app.logger
            # Still return portfolio data if it exists, even without trade history
            # The frontend will need to handle cases where only portfolio markers are available
            processed_portfolio_data = {}
            if portfolio_transactions:
                 # Process portfolio timestamps relative to *something* if no trade history
                 # For simplicity, let's just return the raw portfolio data here if no trades
                 # Or maybe calculate elapsed time from the *first* portfolio event?
                 # Let's return it for now, frontend needs adjustment.
                 # A better approach might be to find the earliest timestamp across both datasets.
                 # For now, returning raw portfolio data if no trade history.
                 app.logger.warning(f"Returning only portfolio data as trade history is missing for {mints}") # Use app.logger
                 # Convert timestamps to Unix ms for JS compatibility before returning
                 for mint_key, data_val in portfolio_transactions.items():
                     for tx_type in ['buys', 'sells']:
                         if tx_type in data_val:
                             for event in data_val[tx_type]:
                                 # Assuming event['timestamp'] is a datetime object from DB
                                 event['time'] = int(pd.to_datetime(event['timestamp']).timestamp() * 1000)
                                 del event['timestamp'] # Remove original datetime object
                 return jsonify(portfolio_transactions) # Adjust frontend to handle this structure
            else:
                 return jsonify({}) # Return empty if neither trade nor portfolio data exists


        # Fetch the current SOL price
        sol_price_usd = get_current_sol_price()
        if sol_price_usd is None:
            app.logger.error("Failed to obtain SOL price. Cannot calculate USD prices.") # Use app.logger
            return jsonify({"error": "Could not determine SOL price"}), 503

        app.logger.info(f"Using SOL price: {sol_price_usd} USD for calculations.") # Use app.logger

        # Process trade data with pandas
        df = pd.DataFrame(trade_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price_sol'] = pd.to_numeric(df['price'])
        df['price_usd'] = df['price_sol'] * sol_price_usd

        chart_data = {}
        grouped = df.groupby('mint')

        # Find the overall minimum timestamp across all requested mints in trade history
        # This ensures consistent x-axis (elapsed time) across multiple charts if displayed together
        # If only one mint is requested, this is just the min timestamp for that mint.
        overall_min_timestamp = df['timestamp'].min()
        app.logger.debug(f"Overall minimum timestamp for relative calculation: {overall_min_timestamp}") # Use app.logger


        for mint, group in grouped:
            if group.empty:
                continue

            group = group.sort_values(by='timestamp')
            # Use the overall min timestamp for consistent elapsed time calculation
            group['elapsed_minutes'] = (group['timestamp'] - overall_min_timestamp).dt.total_seconds() / 60.0

            # Prepare trade data
            mint_chart_data = {
                'time': group['elapsed_minutes'].round(2).tolist(),
                'price_usd': group['price_usd'].round(4).tolist(),
                'buys': [],
                'sells': []
            }

            # Process portfolio data for this mint
            if mint in portfolio_transactions:
                mint_portfolio = portfolio_transactions[mint]
                for buy_event in mint_portfolio.get('buys', []):
                    buy_timestamp = pd.to_datetime(buy_event['timestamp'])
                    elapsed_minutes = (buy_timestamp - overall_min_timestamp).total_seconds() / 60.0
                    price_usd = buy_event['price'] * sol_price_usd # Assume portfolio price is SOL, convert to USD
                    mint_chart_data['buys'].append({
                        'time': round(elapsed_minutes, 2),
                        'price_usd': round(price_usd, 4)
                    })
                for sell_event in mint_portfolio.get('sells', []):
                    sell_timestamp = pd.to_datetime(sell_event['timestamp'])
                    elapsed_minutes = (sell_timestamp - overall_min_timestamp).total_seconds() / 60.0
                    price_usd = sell_event['price'] * sol_price_usd # Assume portfolio price is SOL, convert to USD
                    mint_chart_data['sells'].append({
                        'time': round(elapsed_minutes, 2),
                        'price_usd': round(price_usd, 4)
                    })
                app.logger.debug(f"Processed {len(mint_chart_data['buys'])} buys and {len(mint_chart_data['sells'])} sells for mint: {mint}") # Use app.logger


            chart_data[mint] = mint_chart_data
            app.logger.debug(f"Processed chart data (trades + portfolio) for mint: {mint}, {len(group)} trade points") # Use app.logger

        return jsonify(chart_data)

    except Exception as e:
        # Error already logged by execute_db_query if it was a DB error
        app.logger.error(f"Error processing chart data request for mints {mints}: {e}", exc_info=True) # Use app.logger
        return jsonify({"error": "Internal server error processing request"}), 500

@app.route('/start_bot', methods=['POST'])
def start_bot():
    """Signals the external bot process to start by writing to the command file."""
    app.logger.info("Received request to start bot via command file.")
    write_command("START")
    # We don't know the exact status immediately, client JS should poll /api/bot_status
    return jsonify({"status": "START command issued"}), 200

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    """Signals the external bot process to stop by writing to the command file."""
    app.logger.info("Received request to stop bot via command file.")
    write_command("STOP")
    # We don't know the exact status immediately, client JS should poll /api/bot_status
    return jsonify({"status": "STOP command issued"}), 200

@app.route('/api/bot_status', methods=['GET'])
def bot_status():
    """Reads the status file written by the bot process."""
    status = read_status()
    app.logger.debug(f"Reporting bot status as: {status}")
    return jsonify({"status": status}), 200

@app.route('/trading_view') # Corrected route name
async def trading_view_page():
    """Renders the TradingView chart page."""
    db = None
    tokens_sorted = []
    try:
        db = await get_db()
        # Fetch all unique tokens for the dropdown menu
        tokens = await db.get_all_unique_mints_with_names()
        # Sort tokens alphabetically by name for the dropdown
        tokens_sorted = sorted(tokens, key=lambda x: x.get('name', '').lower())
        app.logger.info(f"Fetched {len(tokens_sorted)} tokens for TradingView dropdown.")
    except Exception as e:
        app.logger.error(f"Error fetching token list for TradingView page: {e}")
        tokens_sorted = [] # Ensure it's always a list
    finally:
        if db and db.pool:
             # Consider if you want to close the pool here or keep it open
             # await db.close() # Uncomment if you want to close after each request
             pass
    # Pass the sorted list to the template
    return render_template('trading_view.html', tokens=tokens_sorted) # Ensure template name matches

# Add/Update the API endpoint for TradingView chart data
@app.route('/api/trading_view/<string:mint>') # Corrected route name
async def get_trading_view_data(mint):
    """Provides OHLCV and portfolio data for the TradingView chart."""
    db = None
    # Define the time window (e.g., last 24 hours, adjust as needed)
    end_date = datetime.now(timezone.utc)
    # Fetch a reasonable duration, e.g., 7 days, or make it configurable
    start_date = end_date - pd.Timedelta(days=7)
    app.logger.info(f"Fetching TradingView data for mint: {mint} from {start_date} to {end_date}")

    try:
        db = await get_db()

        # 1. Fetch OHLCV data using the backtesting data function
        # This function already calculates OHLCV at 5s intervals
        ohlcv_data_dict = await db.get_historical_data_for_backtesting(
            mints=[mint],
            start_date=start_date,
            end_date=end_date
        )

        if not ohlcv_data_dict or mint not in ohlcv_data_dict:
            app.logger.warning(f"No OHLCV data found for mint {mint} in the time range.")
            return jsonify({"error": "No OHLCV data found for this token in the time range."}), 404

        ohlcv_df = ohlcv_data_dict[mint]
        app.logger.debug(f"Fetched {len(ohlcv_df)} OHLCV data points for {mint}.")

        # Convert DataFrame to list of dictionaries suitable for Lightweight Charts
        # Ensure timestamp is in seconds (epoch time)
        ohlcv_formatted = []
        volume_formatted = []
        for timestamp, row in ohlcv_df.iterrows():
            # Ensure timestamp is timezone-aware before converting
            ts_aware = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            epoch_time = int(ts_aware.timestamp())

            # Check for NaN or None values before appending
            open_val = row.get('Open')
            high_val = row.get('High')
            low_val = row.get('Low')
            close_val = row.get('Close')
            volume_val = row.get('Volume') # Fetch Volume

            if all(v is not None and not np.isnan(v) for v in [open_val, high_val, low_val, close_val]):
                 ohlcv_formatted.append({
                     "time": epoch_time,
                     "open": open_val,
                     "high": high_val,
                     "low": low_val,
                     "close": close_val,
                 })

            # Add volume data separately
            if volume_val is not None and not np.isnan(volume_val):
                 # Determine volume bar color based on price change
                 color = 'rgba(239, 83, 80, 0.5)' if close_val < open_val else 'rgba(38, 166, 154, 0.5)' # Red down, Green up
                 volume_formatted.append({
                    "time": epoch_time,
                    "value": volume_val,
                    "color": color
                 })


        app.logger.debug(f"Formatted {len(ohlcv_formatted)} valid OHLCV points and {len(volume_formatted)} volume points.")

        # 2. Fetch portfolio transactions (buy/sell markers)
        portfolio_data = await db.get_portfolio_transactions(mints=[mint])
        portfolio_markers = []
        if mint in portfolio_data:
            buy_markers = portfolio_data[mint].get('buys', [])
            sell_markers = portfolio_data[mint].get('sells', [])
            app.logger.debug(f"Fetched {len(buy_markers)} buys and {len(sell_markers)} sells for {mint}.")

            for buy in buy_markers:
                ts_aware = buy['timestamp'] if buy['timestamp'].tzinfo else buy['timestamp'].replace(tzinfo=timezone.utc)
                portfolio_markers.append({
                    "time": int(ts_aware.timestamp()),
                    "position": 'belowBar',
                    "color": '#26a69a', # Green for buy
                    "shape": 'arrowUp',
                    "text": f'Buy @ {buy["price"]:.6f}'
                })
            for sell in sell_markers:
                ts_aware = sell['timestamp'] if sell['timestamp'].tzinfo else sell['timestamp'].replace(tzinfo=timezone.utc)
                portfolio_markers.append({
                    "time": int(ts_aware.timestamp()),
                    "position": 'aboveBar',
                    "color": '#ef5350', # Red for sell
                    "shape": 'arrowDown',
                    "text": f'Sell @ {sell["price"]:.6f}'
                })
        else:
            app.logger.debug(f"No portfolio transactions found for {mint}.")


        # Combine data
        chart_data = {
            "ohlcv": ohlcv_formatted,
            "volume": volume_formatted, # Add volume data
            "markers": portfolio_markers
        }
        return jsonify(chart_data)

    except Exception as e:
        app.logger.error(f"Error fetching TradingView data for mint {mint}: {e}", exc_info=True)
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return jsonify({"error": "Failed to fetch chart data."}), 500
    finally:
        if db and db.pool:
             # await db.close() # Uncomment if you want to close after each request
             pass
    
if __name__ == '__main__':
    # Port can be changed here or via environment variable if needed
    # Keeping port 89 as manually set by the user previously.
    port = int(os.environ.get("FLASK_PORT", 89))
    # Use Flask's logger for Flask-specific messages
    app.logger.info(f"Starting Flask development server on http://127.0.0.1:{port}...")
    app.run(debug=True, port=port, use_reloader=False)