import os
import sys
import asyncio
import pandas as pd
from flask import Flask, request, jsonify, render_template

# Add project root to the Python path to allow importing modules from the parent directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from database_handler import DatabaseClient
    from logger import logger # Assuming logger is configured similarly
except ImportError as e:
    print(f"Error importing modules: {e}. Make sure you are running from the project root or the necessary modules are in the Python path.")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)

# No global DB client instance for this simplified approach

# Helper function to manage DB connection per request
async def execute_db_query(query_func, *args):
    """Creates a connection, executes a query function, and closes."""
    db_client = DatabaseClient()
    try:
        await db_client.connect()
        logger.debug("DB connection established for request.")
        result = await query_func(db_client, *args)
        return result
    except Exception as e:
        logger.exception(f"Database query failed: {e}")
        raise # Re-raise the exception to be handled by the route
    finally:
        if db_client.pool:
            await db_client.close()
            logger.debug("DB connection closed for request.")

# Wrapper for the specific query needed by index
async def fetch_unique_tokens_query(db_client):
    return await db_client.get_all_unique_mints_with_names()

# Wrapper for the specific query needed by the API
async def fetch_trade_history_query(db_client, mints):
    return await db_client.get_trade_history(mints)

# Route for the main page
@app.route('/')
async def index():
    """Fetches unique mints with names and renders the main HTML page."""
    tokens_list = []
    try:
        # Execute the query using the helper
        tokens_list = await execute_db_query(fetch_unique_tokens_query)
        logger.info(f"Fetched {len(tokens_list)} unique tokens for dropdown.")
    except Exception as e:
        # Error already logged by execute_db_query
        logger.error(f"Failed to fetch unique tokens for index page.")
        # Render the page anyway, dropdown will show error/be empty
    return render_template('index.html', tokens_list=tokens_list)

# API endpoint to get token chart data
@app.route('/api/token_chart_data', methods=['POST'])
async def get_token_chart_data():
    """API endpoint to fetch and process trade data for charting."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    mints = data.get('mints')

    if not mints or not isinstance(mints, list):
        return jsonify({"error": "Missing or invalid 'mints' list in request body"}), 400

    logger.info(f"Received request for chart data for mints: {mints}")

    try:
        # Execute the query using the helper
        trade_history = await execute_db_query(fetch_trade_history_query, mints)
        if not trade_history:
            logger.warning(f"No trade history found for mints: {mints}")
            return jsonify({}) # Return empty object if no data

        # Process data with pandas
        df = pd.DataFrame(trade_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price']) # Ensure price is numeric

        chart_data = {}
        grouped = df.groupby('mint')

        for mint, group in grouped:
            if group.empty:
                continue
            
            group = group.sort_values(by='timestamp') # Ensure data is sorted by time
            min_timestamp = group['timestamp'].min()
            
            # Calculate elapsed time in minutes
            group['elapsed_minutes'] = (group['timestamp'] - min_timestamp).dt.total_seconds() / 60.0
            
            # Prepare data for JSON response (convert NaN/NaT to None for JSON compatibility)
            chart_data[mint] = {
                'time': group['elapsed_minutes'].round(2).tolist(),
                'price': group['price'].round(10).tolist() # Adjust precision as needed
            }
            logger.debug(f"Processed data for mint: {mint}, {len(group)} points")

        return jsonify(chart_data)

    except Exception as e:
        # Error already logged by execute_db_query if it was a DB error
        logger.error(f"Error processing chart data request for mints {mints}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error processing request"}), 500

# Optional: Add a shutdown hook to close the DB connection pool gracefully
# This requires a more complex setup with signals or a different web server like gunicorn
# For simplicity with Flask's built-in server, we might omit explicit pool closing on exit.

if __name__ == '__main__':
    # Port can be changed here or via environment variable if needed
    # Keeping port 89 as manually set by the user previously.
    port = int(os.environ.get("FLASK_PORT", 89))
    logger.info(f"Starting Flask development server on port {port}...")
    # Removed explicit asyncio event loop handling - Flask/Werkzeug handles it.
    app.run(debug=True, port=port)