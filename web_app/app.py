import sys
import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
import pandas as pd # For chart data handling

from flask import Flask, render_template, jsonify, request, send_from_directory

# --- Add Project Root to Python Path ---
# This allows importing modules from the parent directory (your bot's root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Import from your Trading Bot Project ---
try:
    from database_handler import DatabaseClient
    from state_manager import GlobalState, SOL_PRICE_FILE # Import SOL_PRICE_FILE if defined there
    import config as bot_config_module # Alias to avoid naming conflict
    from bot_logger import _LOG_STORAGE_PATH as BOT_LOG_DIR_CONFIG, _LOGGER_NAME as BOT_LOGGER_NAME_CONFIG
    # Import any other necessary utilities or configs
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import trading bot modules: {e}")
    print(f"Ensure the Flask app is in a 'web_app' subfolder of your main project, and all bot modules are in the root.")
    print(f"PROJECT_ROOT tried: {PROJECT_ROOT}")
    sys.exit(1)

# --- File Paths (relative to project root, derived from bot's config) ---
DATA_DIR = os.path.join(PROJECT_ROOT, 'data') # Standard data directory
# Use log path and name from the bot's config
LOG_DIR = os.path.join(PROJECT_ROOT, BOT_LOG_DIR_CONFIG)
LOG_FILE_NAME = f"{BOT_LOGGER_NAME_CONFIG}.log"
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)

DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR, 'dynamic_config.json')
BOT_STATUS_FILE = os.path.join(DATA_DIR, 'bot_status.txt') # Status file written by the bot
# If SOL_PRICE_FILE is not in state_manager, define it:
# SOL_PRICE_FILE = os.path.join(DATA_DIR, 'sol_price.json')


app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Initialize Bot Components (Flask app gets its own instances) ---
# These will be fresh instances. For live data from a *running bot process*,
# the bot needs to write its state to files/DB that Flask can read.
# The GlobalState singleton here will be specific to the Flask process.
db_client = DatabaseClient(config_dict=None) # Pass config if your DBClient expects it from bot's config
global_state = GlobalState.get_instance() # Flask app's instance of GlobalState

# --- Helper function to load base config from bot's config module ---
def load_base_bot_config():
    """Loads configuration from the bot's config module."""
    config_dict = {}
    skipped_keys = []
    for key in dir(bot_config_module):
        if key.isupper() and not key.startswith('_'):
            value = getattr(bot_config_module, key)
            if not callable(value) and not isinstance(value, type(sys)): # type(sys) is module
                 # Skip types that are definitely not config values or not easily serializable by default
                if isinstance(value, (set, timedelta)): # Example: convert set to list for JSON
                    config_dict[key] = list(value) if isinstance(value, set) else str(value)
                elif isinstance(value, (int, float, str, bool, list, dict, type(None))):
                    config_dict[key] = value
                else:
                    skipped_keys.append(f"{key} (type: {type(value).__name__})")
    if skipped_keys:
        print(f"WebApp Info: Skipped loading some base config keys due to type: {', '.join(skipped_keys)}")
    return config_dict

BASE_BOT_CONFIG = load_base_bot_config()


# Ensure data and log directories exist (Flask app might be first to run)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
if not os.path.exists(DYNAMIC_CONFIG_FILE):
    print(f"Info: {DYNAMIC_CONFIG_FILE} not found. Creating with base bot config.")
    # Initialize with base config if it doesn't exist, so UI has something to show
    initial_dynamic_config = {k: v for k, v in BASE_BOT_CONFIG.items() if isinstance(v, (int, float, str, bool, list))}
    try:
        with open(DYNAMIC_CONFIG_FILE, 'w') as f:
            json.dump(initial_dynamic_config, f, indent=4)
    except Exception as e:
        print(f"Error creating initial {DYNAMIC_CONFIG_FILE}: {e}")
        with open(DYNAMIC_CONFIG_FILE, 'w') as f: # Create empty if base fails
            json.dump({}, f)


# --- Helper Functions (mostly same as before) ---
def read_log_file(lines=100):
    if not os.path.exists(LOG_FILE_PATH):
        return f"Log file not found at: {LOG_FILE_PATH}"
    try:
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
            return "".join(log_lines[-lines:])
    except Exception as e:
        return f"Error reading log file: {str(e)}"

def read_dynamic_config_file_content(): # Renamed to avoid conflict with variable
    try:
        with open(DYNAMIC_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {DYNAMIC_CONFIG_FILE} not found. Returning empty config.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {DYNAMIC_CONFIG_FILE}. Returning empty config.")
        return {"error": "Invalid JSON in config file"} # So UI can show error
    except Exception as e:
        print(f"Error reading {DYNAMIC_CONFIG_FILE}: {str(e)}. Returning empty config.")
        return {"error": f"Error reading config: {str(e)}"}

def write_dynamic_config_to_file(config_data): # Renamed to avoid conflict
    try:
        with open(DYNAMIC_CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error writing dynamic config to {DYNAMIC_CONFIG_FILE}: {e}")
        return False

def get_bot_status_from_file():
    try:
        if os.path.exists(BOT_STATUS_FILE):
            with open(BOT_STATUS_FILE, 'r') as f:
                return f.read().strip().upper()
        return "NOT_RUNNING_OR_STATUS_FILE_MISSING"
    except Exception as e:
        print(f"Error reading status file {BOT_STATUS_FILE}: {e}")
        return "ERROR_READING_STATUS"

async def get_live_sol_price_from_file():
    """Reads SOL price from the file shared by the bot."""
    try:
        # Use SOL_PRICE_FILE from state_manager or defined above
        if os.path.exists(SOL_PRICE_FILE): # SOL_PRICE_FILE defined in state_manager.py
            with open(SOL_PRICE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("price")
        return None # Or a default/stale value
    except Exception as e:
        print(f"Error reading SOL price file ({SOL_PRICE_FILE}): {e}")
        return None

# --- Event Loop Management for Async DB Calls ---
# This is a simplified way. For production, use an ASGI server.
def async_adapter(awaitable):
    """Runs an awaitable in a new event loop if not already in one."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(awaitable)
    # If already in a loop (e.g. under ASGI server), just await
    return asyncio.ensure_future(awaitable)


# --- Flask App Setup ---
@app.before_request
async def before_request_async():
    # This ensures DB connection for async routes if needed
    # However, with asyncpg, connections are typically acquired per query/transaction
    if not db_client.pool: # Assuming pool is None if not connected
        print("Attempting to connect DB client before request...")
        try:
            await db_client.connect()
            print("DB client connected via before_request_async.")
        except Exception as e:
            print(f"Failed to connect DB client in before_request_async: {e}")
            # You might want to return an error response here if DB is critical for all requests


@app.teardown_appcontext
async def teardown_db(exception=None):
    # This might not work as expected with `flask run` for async cleanup.
    # Proper cleanup is better handled when the app server (Gunicorn, Uvicorn) shuts down.
    if db_client and db_client.pool:
        print("Attempting to close DB client pool on app teardown...")
        # await db_client.close() # Ensure this method correctly closes the pool
        print("DB client pool closed via teardown_db.")
        pass


# --- Routes (largely same, but using actual components) ---
@app.route('/')
def index():
    return render_template('base.html')

@app.route('/page/dashboard')
def page_dashboard():
    return render_template('dashboard.html')

@app.route('/page/config')
def page_config():
    return render_template('config.html')

@app.route('/page/charts')
def page_charts():
    return render_template('charts.html')

# --- API Endpoints ---

@app.route('/api/status', methods=['GET'])
async def api_status():
    try:
        # Uptime: If the bot writes its start time to a file, read that.
        # Otherwise, this shows Flask app's uptime via global_state.
        # For this example, we'll assume the bot writes its status.
        bot_file_status = get_bot_status_from_file()
        
        # Get live SOL price from the bot's shared file
        live_sol_price = await get_live_sol_price_from_file()
        sol_balance_usd = 0
        current_sol_bal = 0
        # Note: global_state.get_current_sol_balance() is from *this Flask app's* state.
        # If the bot updates a file with its actual balance, read that.
        # For now, we'll use a placeholder or the Flask app's GlobalState.
        try:
            current_sol_bal = await global_state.get_current_sol_balance() # Reads from config._INITIAL_SOL_BALANCE
            if live_sol_price:
                sol_balance_usd = current_sol_bal * live_sol_price
        except Exception as e:
            print(f"Could not get SOL balance for status: {e}")


        # Number of active subscriptions - this should ideally come from the running bot.
        # The Flask app's global_state.active_token_subscriptions will be empty
        # unless this Flask app also runs subscription logic (not typical).
        # For now, let's assume the bot could write this to a status file or DB.
        # Fallback: Display total tracked tokens from DB as a proxy.
        active_subs_count = "N/A (Bot needs to provide)"
        try:
            if db_client.pool: # Check if DB is connected
                 active_subs_count = await db_client.get_total_tracked_tokens(backedup=False) # Example metric
            else:
                print("DB not connected for active_subs_count in api_status")
        except Exception as e:
            print(f"Error getting active_subs_count: {e}")
            active_subs_count = "Error"


        status_data = {
            "uptime": "N/A (Bot needs to provide start time)", # Placeholder
            "asyncio_tasks": len(asyncio.all_tasks(loop=asyncio.get_event_loop_policy().get_event_loop())), # Tasks in Flask process
            "token_subscriptions_count": active_subs_count,
            "current_sol_balance_val": f"{current_sol_bal:.4f}",
            "current_sol_price_usd": f"{live_sol_price:.2f}" if live_sol_price else "N/A",
            "current_sol_balance_usd": f"${sol_balance_usd:,.2f}" if live_sol_price else "N/A",
            "bot_file_status": bot_file_status,
            "dynamic_config_last_modified": datetime.fromtimestamp(os.path.getmtime(DYNAMIC_CONFIG_FILE)).isoformat() if os.path.exists(DYNAMIC_CONFIG_FILE) else "N/A"
        }
        return jsonify(status_data)
    except Exception as e:
        print(f"Error in /api/status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def api_logs():
    lines = request.args.get('lines', 100, type=int)
    log_content = read_log_file(lines)
    return jsonify({"logs": log_content})

@app.route('/api/config', methods=['GET'])
def api_get_config():
    # Merge base config with dynamic config for display
    # Dynamic config takes precedence
    dynamic_conf = read_dynamic_config_file_content()
    if "error" in dynamic_conf: # If reading dynamic_config.json failed
        # Fallback to base config or show error
        print(f"Error reading dynamic config for GET: {dynamic_conf['error']}. Showing base config.")
        #return jsonify(BASE_BOT_CONFIG) # Or return error
        # For UI, better to show what IS there + error
        return jsonify({"error_reading_dynamic": dynamic_conf['error'], **BASE_BOT_CONFIG})


    # Create a new dict for the merged config to preserve original types from BASE_BOT_CONFIG where possible
    # and apply dynamic overrides.
    merged_config = {}
    for key, base_value in BASE_BOT_CONFIG.items():
        if key in dynamic_conf:
            # Override with dynamic value, try to cast to original type if simple
            dyn_value = dynamic_conf[key]
            try:
                if isinstance(base_value, bool): merged_config[key] = bool(dyn_value)
                elif isinstance(base_value, int): merged_config[key] = int(dyn_value)
                elif isinstance(base_value, float): merged_config[key] = float(dyn_value)
                elif isinstance(base_value, list) and isinstance(dyn_value, list): merged_config[key] = dyn_value # Assume list is fine
                else: merged_config[key] = dyn_value # string or other complex types
            except (ValueError, TypeError):
                merged_config[key] = dyn_value # Fallback to dynamic value if cast fails
        else:
            merged_config[key] = base_value # Use base value

    # Add any keys from dynamic_conf that are not in BASE_BOT_CONFIG (newly added params)
    for key, dyn_value in dynamic_conf.items():
        if key not in merged_config:
            merged_config[key] = dyn_value

    return jsonify(merged_config)


@app.route('/api/config/update', methods=['POST'])
def api_update_config():
    try:
        new_config_data_from_form = request.json
        if not isinstance(new_config_data_from_form, dict):
            return jsonify({"error": "Invalid data format, expected a JSON object."}), 400

        current_dynamic_config = read_dynamic_config_file_content()
        if "error" in current_dynamic_config:
             return jsonify({"error": f"Could not read current config to update: {current_dynamic_config['error']}"}), 500

        updated_config = current_dynamic_config.copy() # Start with current dynamic config

        for key_from_form, value_from_form in new_config_data_from_form.items():
            # All keys from form are assumed to be intended for DYNAMIC_CONFIG_FILE
            # Type conversion based on BASE_BOT_CONFIG if key exists there, otherwise store as is from form
            key_upper = key_from_form.upper() # Standardize key

            final_value = value_from_form
            if key_upper in BASE_BOT_CONFIG:
                base_type = type(BASE_BOT_CONFIG[key_upper])
                try:
                    if base_type == bool: final_value = bool(value_from_form)
                    elif base_type == int: final_value = int(value_from_form)
                    elif base_type == float: final_value = float(value_from_form)
                    elif base_type == list and isinstance(value_from_form, list): final_value = value_from_form
                    elif base_type == set and isinstance(value_from_form, list): final_value = list(value_from_form) # Store as list in JSON
                    # else string or already correct type
                except (ValueError, TypeError) as e:
                    print(f"Warning: Could not convert form value for '{key_upper}' to base type {base_type}. Storing as received. Error: {e}")
            
            updated_config[key_upper] = final_value

        if write_dynamic_config_to_file(updated_config):
            return jsonify({"message": "Configuration update written to dynamic_config.json. Bot should apply changes."})
        else:
            return jsonify({"error": "Failed to write configuration file."}), 500
    except Exception as e:
        print(f"Error in /api/config/update: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tokens', methods=['GET'])
async def api_get_tokens():
    """API endpoint to get a list of tokens for TradingView chart selection."""
    if not db_client.pool:
        await db_client.connect() # Ensure connected
    try:
        # Your DatabaseClient.get_all_unique_mints_with_names() is async
        tokens = await db_client.get_all_unique_mints_with_names()
        return jsonify(tokens)
    except Exception as e:
        print(f"Error in /api/tokens: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/token_data/<mint_address>', methods=['GET'])
async def api_get_token_data(mint_address):
    if not db_client.pool:
        await db_client.connect() # Ensure connected
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=request.args.get('days', 7, type=int)) # Allow dynamic days

        # Your DatabaseClient.get_historical_data_for_backtesting is async
        data_dict = await db_client.get_historical_data_for_backtesting(
            mints=[mint_address],
            start_date=start_date,
            end_date=end_date
        )

        if not data_dict or mint_address not in data_dict or data_dict[mint_address].empty:
            return jsonify({"error": "No data found for this token in the selected range."}), 404

        df = data_dict[mint_address]
        # Ensure required columns exist, otherwise provide defaults or error
        required_cols = ['Open', 'High', 'Low', 'Close']
        for col in required_cols:
            if col not in df.columns:
                 return jsonify({"error": f"Missing required column '{col}' in data for {mint_address}."}), 500

        chart_data = []
        for timestamp, row in df.iterrows():
            # Ensure timestamp is timezone-aware before converting
            ts_aware = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            chart_data.append({
                "time": int(ts_aware.timestamp()),
                "open": row['Open'],
                "high": row['High'],
                "low": row['Low'],
                "close": row['Close'],
                "volume": row.get('Volume', 0)
            })
        return jsonify(chart_data)
    except Exception as e:
        print(f"Error in /api/token_data/{mint_address}: {e}")
        return jsonify({"error": str(e)}), 500


async def flask_main():
    """Main entry point to run the Flask app with an ASGI server like Hypercorn."""
    # This function is intended to be called by an ASGI server.
    # Example: `hypercorn web_app.app:app`
    # For development, you can still use `flask run --debug` which handles its own loop.
    # When using `flask run`, async routes are handled by Flask's development server's capabilities.
    try:
        if not db_client.pool: # Check if already connected (e.g., by multiple workers)
            await db_client.connect()
            print("Flask App: DB Client connected via flask_main.")
        # The app object is already defined globally.
        # The ASGI server will run the app.
    except Exception as e:
        print(f"Error during Flask app async setup: {e}")
        # Potentially re-raise or handle gracefully


if __name__ == '__main__':
    # This block is for direct execution (python web_app/app.py)
    # For development, `flask run --debug` is preferred after setting FLASK_APP.
    # For production, use an ASGI server like Hypercorn or Uvicorn:
    # e.g., `hypercorn web_app.app:app -b 0.0.0.0:5001` (install hypercorn first)

    print("Starting Flask development server...")
    print("IMPORTANT: For async routes to work correctly with database calls,")
    print("           consider running with an ASGI server like Hypercorn for production,")
    print("           or ensure your development Flask server supports async/await properly.")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Log file path: {LOG_FILE_PATH}")
    print(f"Dynamic config path: {DYNAMIC_CONFIG_FILE}")

    # Simplified run for development (Flask's dev server has some async support)
    async def run_dev_server():
        if not db_client.pool:
            try:
                await db_client.connect()
                print("DB Client connected for dev server.")
            except Exception as e:
                print(f"Failed to connect DB for dev server: {e}")
                # Decide if app should run without DB for UI testing
    
    # Flask's app.run() is synchronous. To manage the async DB connection:
    # We connect before starting the Flask app.
    # For Flask's dev server, routes with `async def` are generally handled.
    try:
        asyncio.run(run_dev_server()) # Connect DB
    except Exception as e:
        print(f"Error during pre-run setup: {e}")

    app.run(debug=True, host='0.0.0.0', port=89, use_reloader=True)
    # Note: use_reloader=True might cause issues with async setup in some cases or
    # re-run the module-level code (like DB connection) multiple times.
    # `flask run --debug` is generally more robust for development.

    # Cleanup (might not be reached if app.run() blocks indefinitely until Ctrl+C)
    # async def cleanup_on_exit():
    #     if db_client and db_client.pool:
    #         print("Closing DB client pool on script exit...")
    #         await db_client.close()
    # asyncio.run(cleanup_on_exit())