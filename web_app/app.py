import sys
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone

from flask import Flask, render_template, jsonify, request

# --- Add Project Root to Python Path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Import from your Trading Bot Project ---
try:
    from database_handler import DatabaseClient
    from bot_logger import logger
    import config as bot_config_module
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import necessary modules: {e}")
    sys.exit(1)

# --- File Path Constants ---
STATUS_FILE = os.path.join(PROJECT_ROOT, 'data', 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(PROJECT_ROOT, 'data', 'dynamic_config.json')
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, bot_config_module._LOG_STORAGE_PATH, f"{bot_config_module._LOGGER_NAME}.log")

# --- Flask App Setup ---
app = Flask(__name__)

# --- Helper Functions ---
def read_json_file(file_path):
    """Safely reads and parses a JSON file."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {os.path.basename(file_path)}"}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Handle empty file case
            if os.fstat(f.fileno()).st_size == 0:
                return {}
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return {"error": f"Could not read or parse {os.path.basename(file_path)}"}

def write_dynamic_config_file(data):
    """Writes data to the dynamic configuration file."""
    try:
        with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True, None
    except Exception as e:
        logger.error(f"Error writing dynamic config file: {e}")
        return False, str(e)

# --- Page-Serving Routes ---
@app.route('/')
def route_index():
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
def api_status():
    """Provides status data for the dashboard by reading the bot's status file."""
    status_data = read_json_file(STATUS_FILE)
    return jsonify(status_data)

@app.route('/api/config', methods=['GET'])
def api_get_config():
    """Provides the current editable configuration."""
    config_data = read_json_file(DYNAMIC_CONFIG_FILE)
    return jsonify(config_data)

@app.route('/api/config/update', methods=['POST'])
def api_update_config():
    """Updates the dynamic configuration file from user input."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    success, error = write_dynamic_config_file(request.get_json())
    if success:
        return jsonify({"message": "Configuration saved. Bot will apply changes shortly."})
    else:
        return jsonify({"error": f"Failed to write to config file: {error}"}), 500

@app.route('/api/tokens', methods=['GET'])
async def api_get_tokens():
    """Fetches all unique token mints and names for the dropdown."""
    db = DatabaseClient()
    try:
        await db.connect()
        tokens = await db.get_all_unique_mints_with_names()
        return jsonify(tokens)
    except Exception as e:
        logger.error(f"Error in /api/tokens: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch tokens from database."}), 500
    finally:
        if db.pool:
            await db.close()

@app.route('/api/token_data/<string:mint_address>', methods=['GET'])
async def api_get_token_data(mint_address):
    """Fetches OHLCV data for a selected token."""
    db = DatabaseClient()
    try:
        await db.connect()
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        data_dict = await db.get_historical_data_for_backtesting(mints=[mint_address], start_date=start_date, end_date=end_date)

        if not data_dict or mint_address not in data_dict or data_dict[mint_address].empty:
            return jsonify({"error": "No data found for this token."}), 404

        df = data_dict[mint_address]
        
        chart_data = []
        for timestamp, row in df.iterrows():
            ts_aware = timestamp.tz_convert(timezone.utc) if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            chart_data.append({
                "time": int(ts_aware.timestamp()),
                "open": row.get('Open', 0.0), "high": row.get('High', 0.0),
                "low": row.get('Low', 0.0), "close": row.get('Close', 0.0),
                "volume": row.get('Volume', 0.0)
            })
        
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error in /api/token_data/{mint_address}: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch chart data."}), 500
    finally:
        if db.pool:
            await db.close()

@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Returns the last 100 lines of the main bot log file."""
    try:
        if not os.path.exists(LOG_FILE_PATH):
            return jsonify({"logs": "Log file not found."})
        
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return jsonify({"logs": "".join(lines[-100:])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # For development, run with: flask --app web_app.app:app run --debug
    # This ensures the Flask development server is used correctly.
    app.run(host='0.0.0.0', port=89, debug=True)