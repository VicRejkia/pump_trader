# ai_data_assembler.py (formerly test_ai_decision_maker.py)
import sys
import os
import asyncio
import datetime as dt
import pandas as pd
import numpy as np
import json
import statistics
import httpx # For URI check
from decimal import Decimal # For precise calculations, especially price
import inspect # To help load config module

# --- Conditional Path Setup for Standalone Execution ---
# When running this script directly, we need to ensure the project root
# is in the Python path so imports like 'from config import ...' work.
if __name__ == "__main__":
    # Get the directory containing this script (ai_decision_module)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the parent directory (project root)
    project_root = os.path.dirname(current_dir)
    # Add project root to the start of the sys.path if it's not already there
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"[Standalone Mode] Added project root to sys.path: {project_root}")

# --- Now imports should work in both standalone and imported modes ---
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from state_manager import GlobalState
from utils import calculate_volatility, ensure_datetime
# Import AIDecisionMaker directly as it's in the same directory (module)
from ai_decision_maker import AIDecisionMaker
# Import the config *module* itself
from config import config as config_module
# Import specific values needed directly in this script's global scope (if any)
# Note: It's often cleaner to pass config values down through functions.
from config.config import MAX_TOKEN_COUNT_PER_CREATOR

# --- Calculation Helper Functions ---
# These functions remain unchanged from your provided script.
# (safe_pct_change, check_uri_status, summarize_score_history,
#  summarize_market_dynamics, summarize_trade_history)

def safe_pct_change(old, new) -> float:
    """
    Safely calculates the percentage change between two values.
    Handles None, NaN, Decimals, and division by zero.

    Args:
        old: The old value.
        new: The new value.

    Returns:
        The percentage change as a float, or 0.0 if calculation is not possible.
    """
    if old is None or new is None or pd.isna(old) or pd.isna(new):
        return 0.0
    try:
        # Convert Decimals to float for calculation if needed, handle potential strings
        old_f = float(str(old)) if isinstance(old, Decimal) else float(old)
        new_f = float(str(new)) if isinstance(new, Decimal) else float(new)

        if old_f == 0:
            # If old value is 0, change is infinite or undefined; return 0 for practical purposes
            return 0.0
        return ((new_f / old_f) - 1) * 100.0
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.warning(f"safe_pct_change error: old={old}, new={new}, error={e}")
        return 0.0

async def check_uri_status(uri: str | None) -> str:
    """
    Performs a basic reachability check on a metadata URI.

    Args:
        uri: The URI string to check.

    Returns:
        A string indicating the status ('Missing', 'Invalid Format', 'Valid (Reachable)', 'Error (...)').
    """
    if not uri or not isinstance(uri, str):
        return "Missing"
    # Basic format check
    if not uri.startswith(('http://', 'https://')):
        return "Invalid Format"

    try:
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Use GET request for metadata URIs
            response = await client.get(uri)
            # Check for success status codes (2xx or 3xx redirects)
            if 200 <= response.status_code < 400:
                return "Valid (Reachable)"
            else:
                # Return error status
                return f"Error (HTTP {response.status_code})"
    except httpx.TimeoutException:
        return "Error (Timeout)"
    except httpx.RequestError as e:
        # Log network-related errors
        logger.debug(f"URI check request error for {uri}: {e}")
        return "Error (Request Failed)"
    except Exception as e:
        # Catch unexpected errors during the check
        logger.warning(f"Unexpected error checking URI {uri}: {e}", exc_info=True)
        return "Error (Unknown)"


def summarize_score_history(history_records: list, score_field: str, time_field: str, lookback_hours: float = 1.0) -> dict:
    """
    Summarizes score history (Rugcheck or Social) including initial/latest scores,
    recent trend (change over lookback_hours), and overall stability (std dev).
    Also extracts Telegram trends if it's social score data.

    Args:
        history_records (list): List of dictionaries, each representing a score record.
        score_field (str): The key in the dictionaries containing the score value (e.g., 'score', 'score_value').
        time_field (str): The key containing the timestamp (e.g., 'last_checked', 'timestamp').
        lookback_hours (float): How many hours back to consider for the trend calculation.

    Returns:
        dict: A dictionary containing summary keys like '{prefix}_initial', '{prefix}_latest',
              '{prefix}_trend', '{prefix}_stability', 'telegram_members_trend', 'telegram_online_ratio_trend'.
              Prefix is 'rugcheck' or 'social_score'. Returns defaults if data is insufficient.
    """
    # Determine the prefix based on the score field name
    result_prefix = 'rugcheck' if score_field == 'score' else 'social_score' if score_field == 'score_value' else 'unknown_score'
    # Default result structure
    default_result = {
        f"{result_prefix}_initial": None, f"{result_prefix}_latest": None,
        f"{result_prefix}_trend": "N/A", f"{result_prefix}_stability": "N/A",
        "telegram_members_trend": "N/A", "telegram_online_ratio_trend": "N/A"
    }

    if not history_records:
        #logger.debug(f"No history records provided for score field '{score_field}'.")
        return default_result

    try:
        # Convert history to DataFrame for easier processing
        df = pd.DataFrame(history_records)
        # Convert timestamp field to datetime objects (UTC), coercing errors
        df[time_field] = pd.to_datetime(df[time_field], utc=True, errors='coerce')
        # Drop rows where timestamp conversion failed and sort by time
        df = df.dropna(subset=[time_field]).sort_values(by=time_field)

        if df.empty:
            #logger.debug(f"DataFrame empty after cleaning timestamps for '{score_field}'.")
            return default_result
        if score_field not in df.columns:
            logger.warning(f"Score field '{score_field}' not found in history records.")
            return default_result

        # Convert score field to numeric, coercing errors to NaN
        df[score_field] = pd.to_numeric(df[score_field], errors='coerce')
        # Drop rows with invalid scores
        df = df.dropna(subset=[score_field])
        if df.empty:
            #logger.debug(f"DataFrame empty after dropping NaN scores for '{score_field}'.")
            return default_result

        # --- Calculate Initial and Latest Scores ---
        initial_score = df[score_field].iloc[0]
        latest_score = df[score_field].iloc[-1]

        # --- Calculate Trend (over lookback_hours) ---
        recent_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_hours)
        recent_scores_series = df[df[time_field] >= recent_cutoff][score_field]
        trend_description = "N/A"
        if len(recent_scores_series) > 1:
            # Calculate change between first and last score in the recent period
            change = recent_scores_series.iloc[-1] - recent_scores_series.iloc[0]
            # Determine if trend is improving (lower score is better) or worsening
            trend_direction = "Improving" if change < 0 else "Worsening" if change > 0 else "Stable"
            trend_description = f"{change:+.0f} points ({trend_direction})"
        elif len(recent_scores_series) == 1:
            trend_description = "Stable (1 recent data point)"

        # --- Calculate Stability (Standard Deviation over all scores) ---
        stability_description = "N/A"
        all_scores_series = df[score_field]
        if len(all_scores_series) > 1:
             std_dev = all_scores_series.std()
             if pd.isna(std_dev):
                 stability_description = "N/A (Calc Error)"
             elif std_dev == 0:
                 stability_description = "Very Stable"
             # Use different thresholds for Rugcheck vs Social score volatility interpretation
             elif (score_field == 'score' and std_dev < 50) or (score_field == 'score_value' and std_dev < 5):
                 stability_description = "Stable"
             elif (score_field == 'score' and std_dev < 200) or (score_field == 'score_value' and std_dev < 15):
                 stability_description = "Moderate Volatility"
             else:
                 stability_description = "High Volatility"
        elif len(all_scores_series) == 1:
             stability_description = "Stable (1 data point)"

        # --- Calculate Telegram Trends (Only for social scores) ---
        tg_members_trend_str = "N/A"; tg_online_ratio_trend_str = "N/A"
        if score_field == 'score_value' and 'details' in df.columns:
            recent_details_df = df[df[time_field] >= recent_cutoff].copy()

            # Helper to safely parse JSON details (can be string or dict)
            def safe_json_loads(x):
                if isinstance(x, str):
                    try: return json.loads(x)
                    except json.JSONDecodeError: return {}
                elif isinstance(x, dict): return x
                return {} # Default empty dict
            recent_details_df['details_dict'] = recent_details_df['details'].apply(safe_json_loads)

            # Helper to safely extract specific TG stats
            def get_tg_stat(d, stat_key):
                if not isinstance(d, dict): return None
                tg_stats = d.get('telegram_stats')
                return tg_stats.get(stat_key) if isinstance(tg_stats, dict) else None

            # Extract members and online counts
            recent_details_df['members'] = recent_details_df['details_dict'].apply(lambda d: get_tg_stat(d, 'members'))
            recent_details_df['online'] = recent_details_df['details_dict'].apply(lambda d: get_tg_stat(d, 'online'))
            # Convert to numeric, coercing errors
            recent_details_df['members'] = pd.to_numeric(recent_details_df['members'], errors='coerce')
            recent_details_df['online'] = pd.to_numeric(recent_details_df['online'], errors='coerce')
            # Calculate online ratio, handling division by zero or NaN
            recent_details_df['online_ratio'] = np.where(
                recent_details_df['members'].notna() & (recent_details_df['members'] > 0) & recent_details_df['online'].notna(),
                recent_details_df['online'] / recent_details_df['members'],
                np.nan
            )

            # Calculate member trend
            valid_members_series = recent_details_df['members'].dropna()
            if len(valid_members_series) > 1:
                member_change = valid_members_series.iloc[-1] - valid_members_series.iloc[0]
                tg_members_trend_str = f"{member_change:+.0f}"

            # Calculate online ratio trend
            valid_ratios_series = recent_details_df['online_ratio'].dropna()
            if len(valid_ratios_series) > 1:
                ratio_change_pct = (valid_ratios_series.iloc[-1] - valid_ratios_series.iloc[0]) * 100
                tg_online_ratio_trend_str = f"{ratio_change_pct:+.1f}%"

        # --- Assemble Final Result ---
        final_result = {
            f"{result_prefix}_initial": initial_score,
            f"{result_prefix}_latest": latest_score,
            f"{result_prefix}_trend": trend_description,
            f"{result_prefix}_stability": stability_description,
            "telegram_members_trend": tg_members_trend_str,
            "telegram_online_ratio_trend": tg_online_ratio_trend_str
        }
        return final_result

    except Exception as e:
        logger.error(f"Error in summarize_score_history for {score_field}: {e}", exc_info=True)
        # Return default structure on unexpected error
        return default_result


def summarize_market_dynamics(history_records: list, source: str, lookback_mins: int = 15) -> dict:
    """
    Summarizes recent market dynamics based on the data source (PUMP or DEXSCREENER).

    Args:
        history_records (list): List of dictionaries containing market data records (trades or snapshots).
        source (str): The source of the data ('PUMP' or 'DEXSCREENER').
        lookback_mins (int): How many minutes back to consider for trends (primarily for DEXSCREENER).

    Returns:
        dict: A dictionary containing summary keys specific to the source
              (e.g., 'pump_price_change_1m', 'dex_price_trend_15m') and a
              combined 'market_dynamics_summary' string. Returns defaults if data insufficient.
    """
    summary = {}
    default_summary = {'market_dynamics_summary': "N/A - Insufficient recent market data"}

    if not history_records:
        #logger.debug(f"Market Dynamics: No history records provided for source '{source}'.")
        return default_summary

    try:
        # Convert history to DataFrame
        df = pd.DataFrame(history_records)
        # Ensure timestamp is datetime, set as index, and sort
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        df = df.dropna(subset=['timestamp']).set_index('timestamp').sort_index()

        # Define required and numeric columns based on source
        required_cols = []; numeric_cols = []
        if source == 'PUMP':
            # PUMP source uses individual trades from 'trades' table (via v_unified_market_ticks_live)
            required_cols = ['price_sol', 'volume_usd'] # These come from v_unified_market_ticks_live now
            numeric_cols = ['price_sol', 'volume_usd']
        elif source == 'DEXSCREENER':
            # DEXSCREENER source uses snapshots from 'dexscreener_data' table
            required_cols = ['price_change_m5', 'volume_m5', 'liquidity_usd', 'buys_m5', 'sells_m5']
            numeric_cols = ['price_change_m5', 'volume_m5', 'liquidity_usd', 'buys_m5', 'sells_m5']
        else:
            logger.warning(f"Market Dynamics: Unknown source '{source}'.")
            return default_summary

        # Ensure required columns exist, fill with NaN if missing
        for col in required_cols:
            if col not in df.columns:
                df[col] = np.nan
        # Convert numeric columns, coercing errors
        for col in numeric_cols:
             if col in df.columns:
                if col == 'price_sol':
                    # Handle price_sol carefully, converting potential Decimals from DB
                    df[col] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) else pd.NA)
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

        now_utc = dt.datetime.now(dt.timezone.utc)

        # --- Source-Specific Calculations ---
        if source == 'PUMP':
            # Calculate metrics over the last 1 minute
            one_min_ago = now_utc - dt.timedelta(minutes=1)
            recent_df_1m = df[df.index >= one_min_ago].copy()

            # Price Change (1 min)
            price_series_1m = recent_df_1m['price_sol'].dropna()
            if len(price_series_1m) > 1:
                first_price = price_series_1m.iloc[0]
                last_price = price_series_1m.iloc[-1]
                price_change_1m = safe_pct_change(first_price, last_price)
                summary['pump_price_change_1m'] = f"{price_change_1m:.2f}%"
            else:
                summary['pump_price_change_1m'] = "N/A"

            # Volume Velocity (1 min sum)
            if 'volume_usd' in recent_df_1m.columns:
                vol_sum_1m = recent_df_1m['volume_usd'].sum()
                summary['pump_volume_velocity_1m'] = f"${vol_sum_1m:,.0f}"
            else:
                summary['pump_volume_velocity_1m'] = "$N/A"

            # Tick Frequency (1 min count)
            summary['pump_tick_frequency_1m'] = len(recent_df_1m)

        elif source == 'DEXSCREENER':
            # Calculate trends over the specified lookback period (e.g., 15 mins)
            full_lookback_ago = now_utc - dt.timedelta(minutes=lookback_mins)
            recent_df_lookback = df[df.index >= full_lookback_ago].copy()
            #logger.debug(f"Dex Dynamics: Analyzing {len(recent_df_lookback)} snapshots over {lookback_mins} mins.")

            if len(recent_df_lookback) >= 2:
                # --- Price Trend (15 min) ---
                price_change_col = recent_df_lookback['price_change_m5'].dropna() if 'price_change_m5' in recent_df_lookback else pd.Series(dtype=float)
                if len(price_change_col) > 1:
                    # Use linear regression slope for >2 points, simple comparison for 2 points
                    if len(price_change_col) > 2:
                         x_vals = np.arange(len(price_change_col)) # Time steps
                         try:
                             # Fit a line (y = mx + c) where y=price_change, x=time_step
                             slope = np.polyfit(x_vals, price_change_col.values, 1)[0]
                             # Interpret slope: positive = increasing momentum, negative = decreasing
                             if slope > 0.1: summary['dex_price_trend_15m'] = "Increasing Momentum"
                             elif slope < -0.1: summary['dex_price_trend_15m'] = "Decreasing Momentum"
                             else: summary['dex_price_trend_15m'] = "Stable Momentum"
                         except (np.linalg.LinAlgError, ValueError):
                             logger.warning("LinAlgError during Dex price trend calculation.")
                             summary['dex_price_trend_15m'] = "Trend Calc Error"
                    else: # Exactly 2 points
                        if price_change_col.iloc[-1] > price_change_col.iloc[0]: summary['dex_price_trend_15m'] = "Increasing Momentum"
                        elif price_change_col.iloc[-1] < price_change_col.iloc[0]: summary['dex_price_trend_15m'] = "Decreasing Momentum"
                        else: summary['dex_price_trend_15m'] = "Stable Momentum"
                elif len(price_change_col) == 1: summary['dex_price_trend_15m'] = "Stable (1 snapshot)"
                else: summary['dex_price_trend_15m'] = "N/A"

                # --- Volume Trend (15 min) ---
                volume_col = recent_df_lookback['volume_m5'].dropna() if 'volume_m5' in recent_df_lookback else pd.Series(dtype=float)
                if len(volume_col) > 1:
                    # Compare latest volume to earliest volume in the window
                    if volume_col.iloc[-1] > volume_col.iloc[0] * 1.1: summary['dex_volume_trend_15m'] = "Increasing" # Require > 10% increase
                    elif volume_col.iloc[-1] < volume_col.iloc[0] * 0.9: summary['dex_volume_trend_15m'] = "Decreasing" # Require > 10% decrease
                    else: summary['dex_volume_trend_15m'] = "Stable"
                elif len(volume_col) == 1: summary['dex_volume_trend_15m'] = "Stable (1 snapshot)"
                else: summary['dex_volume_trend_15m'] = "N/A"

                # --- Liquidity Trend (Lookback period, e.g., 30 min if lookback_mins >= 30) ---
                # NOTE: Using the same lookback_mins for simplicity here, but could be adjusted
                liq_col = recent_df_lookback['liquidity_usd'].dropna() if 'liquidity_usd' in recent_df_lookback else pd.Series(dtype=float)
                trend_key_liq = f"dex_liquidity_trend_{lookback_mins}m" # Dynamic key based on actual lookback
                if len(liq_col) > 1:
                     if liq_col.iloc[-1] > liq_col.iloc[0] * 1.05: summary[trend_key_liq] = "Increasing" # > 5% increase
                     elif liq_col.iloc[-1] < liq_col.iloc[0] * 0.95: summary[trend_key_liq] = "Decreasing" # > 5% decrease
                     else: summary[trend_key_liq] = "Stable"
                elif len(liq_col) == 1: summary[trend_key_liq] = "Stable (1 snapshot)"
                else: summary[trend_key_liq] = "N/A"
                # Add a fixed key for the prompt template compatibility
                summary['dex_liquidity_trend_30m'] = summary.get(trend_key_liq, "N/A")

            else:
                 # Not enough snapshots for trend analysis
                 #logger.debug(f"Not enough Dex snapshots ({len(recent_df_lookback)}) within {lookback_mins} mins for trend calculation.")
                 summary['dex_price_trend_15m'] = "N/A (Few Snaps)"
                 summary['dex_volume_trend_15m'] = "N/A (Few Snaps)"
                 summary['dex_liquidity_trend_30m'] = "N/A (Few Snaps)"

        # --- Create Summary String ---
        market_dynamics_parts = []
        if source == 'PUMP':
            market_dynamics_parts.extend([
                f"Price(1m):{summary.get('pump_price_change_1m', 'N/A')}",
                f"Vol(1m):{summary.get('pump_volume_velocity_1m', 'N/A')}",
                f"Ticks(1m):{summary.get('pump_tick_frequency_1m', 'N/A')}"
            ])
        elif source == 'DEXSCREENER':
            market_dynamics_parts.extend([
                f"Price Trend(15m):{summary.get('dex_price_trend_15m', 'N/A')}",
                f"Vol Trend(15m):{summary.get('dex_volume_trend_15m', 'N/A')}",
                f"Liq Trend({lookback_mins}m):{summary.get(f'dex_liquidity_trend_{lookback_mins}m', 'N/A')}" # Use dynamic key
            ])
        else: market_dynamics_parts.append("Unknown Source")

        summary['market_dynamics_summary'] = ", ".join(market_dynamics_parts) if market_dynamics_parts else "N/A"
        return summary

    except Exception as e:
        logger.error(f"Error summarizing market dynamics for {source}: {e}", exc_info=True)
        return {'market_dynamics_summary': "Error calculating dynamics"}


def summarize_trade_history(history_records: list, max_events: int = 5) -> str:
    """
    Summarizes portfolio history chronologically for the AI prompt.
    Focuses on the most recent events, highlighting sell reasons and outcomes (profit/loss).

    Args:
        history_records (list): List of dictionaries from the 'portfolio' table.
        max_events (int): The maximum number of recent events to include in the summary.

    Returns:
        str: A formatted multi-line string summarizing the trade history.
    """
    if not history_records:
        return "No prior trading history for this token."

    try:
        # Convert to DataFrame for easier handling
        df = pd.DataFrame(history_records)
        # Ensure timestamp is datetime and sort
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        df = df.dropna(subset=['timestamp']).sort_values(by='timestamp')
        # Ensure profit is numeric, coercing errors
        if 'profit' in df.columns:
            df['profit'] = pd.to_numeric(df['profit'], errors='coerce')
        else: df['profit'] = np.nan # Add profit column if missing

        # Get the most recent events
        recent_events = df.tail(max_events).to_dict('records')

        summary_parts = []
        buy_count = len(df[df['tx_type'] == 'buy'])
        sell_count = len(df[df['tx_type'] == 'sell'])
        summary_parts.append(f"History Summary ({buy_count} Buys, {sell_count} Sells):")

        now_utc = dt.datetime.now(dt.timezone.utc)
        for event in recent_events:
            ts = event['timestamp']
            event_type = event['tx_type'].upper()
            price = event.get('price', 'N/A') # Price of the transaction
            reason = event.get('reason')     # Sell reason
            profit = event.get('profit')     # Profit/Loss for sell events

            # Calculate time since event for display
            time_since = now_utc - ts
            if time_since < dt.timedelta(minutes=120): time_str = f"{time_since.total_seconds() / 60:.0f} mins ago"
            elif time_since < dt.timedelta(hours=48): time_str = f"{time_since.total_seconds() / 3600:.1f} hours ago"
            else: time_str = f"{time_since.days} days ago"

            # Format price safely
            price_str = f"{float(price):.8f}" if isinstance(price, (Decimal, float, int)) and pd.notna(price) else "N/A"
            event_str = f"- {event_type} ({time_str}) at {price_str} SOL."

            # Add Sell-specific details (Reason and Outcome)
            if event_type == 'SELL':
                reason_str = f" Reason: '{reason}'." if reason else ""
                profit_str = ""
                if pd.notna(profit):
                    profit_str = f" Outcome: {profit:+.4f} SOL."
                else: profit_str = " (Outcome N/A)." # Indicate if profit wasn't recorded/calculable
                event_str += reason_str + profit_str
            summary_parts.append(event_str)

        # Indicate if history was truncated
        if len(df) > max_events:
            summary_parts.append(f"- ... (truncated, showing last {max_events} of {len(df)} total events)")

        return "\n".join(summary_parts)

    except Exception as e:
        logger.error(f"Error summarizing trade history: {e}", exc_info=True)
        return "Error generating trade history summary."


# --- Main Data Fetching Function ---
async def fetch_comprehensive_token_data(db: DatabaseClient, mint: str) -> dict:
    """
    Fetches and processes all necessary data for a given token mint to be used
    as input for the AIDecisionMaker.

    Args:
        db (DatabaseClient): An initialized database client instance.
        mint (str): The token mint address.

    Returns:
        dict: A comprehensive dictionary containing all formatted data points
              required by the `AIDecisionMaker.get_trade_advice` method.

    Raises:
        ValueError: If the token is not found in the primary 'tokens' table.
    """
    logger.info(f"Fetching comprehensive data for token {mint}...")
    async with db.pool.acquire() as conn:
        # --- 1. Basic Token Info & Context ---
        # Fetch initial token details: name, source, creator, creation time, URI
        token_info = await conn.fetchrow(
            "SELECT name, symbol, data_source, traderpublickey, timestamp, uri FROM tokens WHERE mint = $1",
            mint
        )
        if not token_info:
            # TRY fetching from backup table if not found in active tokens
            token_info = await conn.fetchrow(
                 "SELECT name, symbol, 'PUMP' as data_source, traderpublickey, timestamp, uri FROM tokens_backup WHERE mint = $1", # Assume backup is PUMP
                mint
            )
            if not token_info:
                logger.error(f"Token {mint} not found in 'tokens' or 'tokens_backup' table.")
                raise ValueError(f"Token {mint} not found in 'tokens' or 'tokens_backup' table.")
            else:
                 logger.warning(f"Token {mint} found in backup table. Proceeding with backup data.")


        source = token_info['data_source']
        name = token_info['name']
        symbol = token_info['symbol']
        creator_wallet = token_info['traderpublickey']
        # Ensure creation timestamp is timezone-aware UTC
        token_creation_ts = ensure_datetime(token_info['timestamp'])
        uri = token_info['uri']

        # Calculate token age
        token_age_minutes = (dt.datetime.now(dt.timezone.utc) - token_creation_ts).total_seconds() / 60 if token_creation_ts else None

        # Check creator status (prolific/suspicious based on token count)
        creator_token_count = await conn.fetchval("SELECT token_count FROM creator_wallets WHERE wallet_address = $1", creator_wallet) or 0
        # Use MAX_TOKEN_COUNT_PER_CREATOR from config
        max_creator_tokens = db.config.get('MAX_TOKEN_COUNT_PER_CREATOR', 50)
        is_prolific_creator = creator_token_count > max_creator_tokens

        # Check metadata URI status
        uri_status = await check_uri_status(uri)

        # --- 2. Determine Current Decision Context ---
        # Based on portfolio history: INITIAL BUY, REBUY, or SELL/HOLD
        decision_context = "INITIAL BUY"
        # Count past entries (buy or sell) for this mint
        past_pos_count = await conn.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
        # Check if there's an 'active' 'buy' entry (meaning we currently hold tokens)
        active_pos = await conn.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)

        if active_pos:
            decision_context = "SELL/HOLD" # Currently holding
        elif past_pos_count > 0:
            decision_context = "REBUY" # Held in the past, but not currently
        # Else: Stays "INITIAL BUY"

        #logger.debug(f"Decision context for {mint}: {decision_context}")

        # --- 3. Get Current Price & Market Cap ---
        # Use the robust price calculation method from DatabaseClient
        price_data = await db.get_price_and_market_cap_for_decision(mint, db.config, conn)
        current_price_sol = price_data.get('price') # Price in SOL
        current_mcap_sol = price_data.get('market_cap') # Market cap in SOL

        # Convert Market Cap to USD using the current SOL price from global state
        current_mcap_usd = 0.0
        sol_price = await GlobalState.get_instance().get_sol_price()
        if current_mcap_sol and sol_price and sol_price > 0:
            current_mcap_usd = float(current_mcap_sol) * sol_price
        elif current_price_sol is not None and current_price_sol > 0:
            # Log warning if MC couldn't be determined but price exists
            logger.warning(f"Market Cap in SOL missing or invalid for {mint}. Setting USD Market Cap to 0.")
        else:
            # Log warning if both price and MC are missing/invalid
            logger.warning(f"Both Price and Market Cap in SOL missing or invalid for {mint}. Setting USD Market Cap to 0.")

        # --- 4. Fetch Score Histories ---
        # Fetch recent Rugcheck scores
        rugcheck_hist_raw = await conn.fetch(
            "SELECT score, last_checked FROM v_rugcheck WHERE mint = $1 ORDER BY last_checked DESC LIMIT 50", mint
        )
        # Fetch recent Social scores (including details JSON)
        socials_hist_raw = await conn.fetch(
            "SELECT score_value, timestamp, details::TEXT as details FROM v_social_scores WHERE mint = $1 ORDER BY timestamp DESC LIMIT 50", mint
        )

        # --- 5. Fetch Market History ---
        # Define lookback period for market dynamics and volatility
        market_hist_lookback_mins = 15 # Consistent lookback for dynamics and volatility
        # Fetch unified history (from v_unified_market_ticks_live) for volatility calculation
        # This view includes both PUMP trades and DEXSCREENER snapshots
        # IMPORTANT: Use HISTORICAL view if fetching for a potentially inactive/backed-up token
        view_to_use = "v_unified_market_ticks_live" if await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint) else "v_unified_market_ticks_historical"
        market_hist_raw_unified = await conn.fetch(
            f"""SELECT timestamp, price_sol, market_cap_sol, volume_usd
                FROM {view_to_use}
                WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes' AND price_sol > 0
                ORDER BY timestamp ASC;""",
            mint
        )

        # Fetch source-specific history for detailed dynamics calculation
        market_hist_raw_source_specific = []
        if source == 'PUMP':
            # Fetch raw trades if source is PUMP (use v_trades to include backups if necessary)
            table_to_use_pump = "trades" if await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint) else "trades_backup"
            market_hist_raw_source_specific = await conn.fetch(
                f"""SELECT timestamp, price AS price_sol, sol_amount, token_amount, (sol_amount * sol_price_usd) AS volume_usd
                    FROM {table_to_use_pump} WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes' AND price > 0
                    ORDER BY timestamp ASC;""",
                mint
            )
        elif source == 'DEXSCREENER':
            # Fetch Dexscreener snapshots if source is DEXSCREENER (use v_dexscreener_data)
            market_hist_raw_source_specific = await conn.fetch(
                f"""SELECT timestamp, price_change_m5, volume_m5, liquidity_usd, buys_m5, sells_m5
                    FROM v_dexscreener_data WHERE mint_address = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes'
                    ORDER BY timestamp ASC;""",
                mint
            )
        #logger.debug(f"Fetched {len(market_hist_raw_unified)} unified and {len(market_hist_raw_source_specific)} source-specific market records for {mint}.")
        # Log samples if data exists
        #if market_hist_raw_unified: logger.debug(f"Unified market sample (last 5): {[dict(r) for r in market_hist_raw_unified[-5:]]}")
        #if market_hist_raw_source_specific: logger.debug(f"Source-specific market sample (last 5): {[dict(r) for r in market_hist_raw_source_specific[-5:]]}")


        # --- 6. Fetch Portfolio (Trade) History ---
        # Get all buy/sell records for this mint from the portfolio table
        # IMPORTANT: Fetch from portfolio AND portfolio_backup if token might be inactive
        portfolio_hist_raw = await conn.fetch(
            """SELECT timestamp, tx_type, price, reason, profit FROM portfolio WHERE mint = $1
               UNION ALL
               SELECT timestamp, tx_type, price, reason, profit FROM portfolio_backup WHERE mint = $1
               ORDER BY timestamp ASC;""",
            mint
        )
        # Summarize the history into a string format for the LLM prompt
        trade_history_summary = summarize_trade_history([dict(r) for r in portfolio_hist_raw])
        #logger.debug(f"Trade History Summary for {mint}:\n{trade_history_summary}")

        # --- 7. Calculate Summaries & Volatility ---
        # Summarize Rugcheck score history (initial, latest, trend, stability)
        rugcheck_summary = summarize_score_history([dict(r) for r in rugcheck_hist_raw], 'score', 'last_checked', lookback_hours=1.0)
        # Summarize Social score history (initial, latest, trend, stability, TG trends)
        socials_summary = summarize_score_history([dict(r) for r in socials_hist_raw], 'score_value', 'timestamp', lookback_hours=1.0)
        # Summarize market dynamics based on source-specific data
        market_summary = summarize_market_dynamics([dict(r) for r in market_hist_raw_source_specific], source, lookback_mins=market_hist_lookback_mins)

        # Calculate Volatility using the unified market history
        volatility = 0.0
        if market_hist_raw_unified:
            # Convert unified history to DataFrame
            market_hist_df = pd.DataFrame([dict(r) for r in market_hist_raw_unified])
            if not market_hist_df.empty:
                # Convert timestamp and price, drop invalid rows
                market_hist_df['timestamp'] = pd.to_datetime(market_hist_df['timestamp'], utc=True, errors='coerce')
                # Use Decimal for price to maintain precision before calculation
                market_hist_df['price_sol_decimal'] = market_hist_df['price_sol'].apply(lambda x: Decimal(str(x)) if pd.notna(x) else pd.NA)
                market_hist_df = market_hist_df.dropna(subset=['timestamp', 'price_sol_decimal'])

                if not market_hist_df.empty:
                     market_hist_df = market_hist_df.set_index('timestamp').sort_index()
                     # Use the numeric price series for volatility calculation
                     price_series = pd.to_numeric(market_hist_df['price_sol_decimal'])
                     if not price_series.empty and len(price_series) > 1:
                         # Use a window size up to 120 points, or fewer if less data available
                         vol_window = min(len(price_series), 120)
                         if vol_window >= 2: # Need at least 2 points for std dev
                              # Calculate rolling volatility based on log returns
                              volatility_series = calculate_volatility(price_series, window=vol_window)
                              # Take the latest calculated volatility value
                              if not volatility_series.empty: volatility = volatility_series.iloc[-1]
            #logger.debug(f"Calculated Volatility for {mint} ({source}): {volatility:.4f}")
        else:
            logger.warning(f"No unified market history available for {mint} to calculate volatility.")

        # --- 8. Assemble Final Data Dictionary ---
        # Combine all fetched and calculated data into the structure expected by AIDecisionMaker
        current_data = {
            'mint': mint, 'name': name, 'symbol': symbol, 'source': source,
            'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(), # Timestamp of data fetch
            'decision_context': decision_context,
            'token_age_minutes': round(token_age_minutes, 1) if token_age_minutes is not None else None,
            'is_prolific_creator': is_prolific_creator, 'uri_status': uri_status,
            # Core Metrics
            'price': float(current_price_sol) if current_price_sol is not None else 0.0,
            'market_cap': current_mcap_usd, # USD Market Cap
            'volatility': volatility,
            # Score Summaries (unpacking results from summarize functions)
            **rugcheck_summary, **socials_summary,
            # History & Dynamics Summaries
            'trade_history_summary': trade_history_summary,
            'market_dynamics_summary_str': market_summary.get('market_dynamics_summary', "N/A"),
            # Explicitly include renamed score keys used directly in prompt template
            # (using .get() provides default 'N/A' if summary failed)
            'rugcheck_latest': rugcheck_summary.get('rugcheck_latest', 'N/A'),
            'rugcheck_initial': rugcheck_summary.get('rugcheck_initial', 'N/A'),
            'rugcheck_trend': rugcheck_summary.get('rugcheck_trend', 'N/A'),
            'rugcheck_stability': rugcheck_summary.get('rugcheck_stability', 'N/A'),
            'social_latest': socials_summary.get('social_score_latest', 'N/A'),
            'social_initial': socials_summary.get('social_score_initial', 'N/A'),
            'social_score_trend': socials_summary.get('social_score_trend', 'N/A'),
            'social_stability': socials_summary.get('social_score_stability', 'N/A'),
            'telegram_members_trend': socials_summary.get('telegram_members_trend', 'N/A'),
            'telegram_online_ratio_trend': socials_summary.get('telegram_online_ratio_trend', 'N/A'),
        }

        # Add source-specific dynamics keys required by the prompt templates
        if source == 'PUMP':
            current_data['pump_price_change_1m'] = market_summary.get('pump_price_change_1m', "N/A")
            current_data['pump_volume_velocity_1m'] = market_summary.get('pump_volume_velocity_1m', "N/A")
            current_data['pump_tick_frequency_1m'] = market_summary.get('pump_tick_frequency_1m', "N/A")
        elif source == 'DEXSCREENER':
            # Get the absolute latest snapshot values for current state (m5 metrics)
            latest_dex_data = None
            if market_hist_raw_source_specific:
                # Use the last record from the fetched history if available
                latest_dex_data = dict(market_hist_raw_source_specific[-1])
            else:
                # If no recent history, fetch the single latest record from DB (use v_dexscreener_data)
                 latest_dex_row = await conn.fetchrow(
                     """SELECT price_change_m5, buys_m5, sells_m5, volume_m5
                        FROM v_dexscreener_data WHERE mint_address = $1
                        ORDER BY timestamp DESC LIMIT 1""",
                     mint
                 )
                 if latest_dex_row: latest_dex_data = dict(latest_dex_row)

            # Populate m5 metrics from the latest snapshot data
            current_data['dex_price_change_m5'] = float(latest_dex_data.get('price_change_m5', 0.0)) if latest_dex_data else 0.0
            current_data['dex_buys_m5'] = int(latest_dex_data.get('buys_m5', 0)) if latest_dex_data else 0
            current_data['dex_sells_m5'] = int(latest_dex_data.get('sells_m5', 0)) if latest_dex_data else 0
            current_data['dex_volume_m5'] = float(latest_dex_data.get('volume_m5', 0.0)) if latest_dex_data else 0.0
            # Populate trend metrics from the market_summary calculation
            current_data['dex_price_trend_15m'] = market_summary.get('dex_price_trend_15m', "N/A")
            current_data['dex_volume_trend_15m'] = market_summary.get('dex_volume_trend_15m', "N/A")
            current_data['dex_liquidity_trend_30m'] = market_summary.get('dex_liquidity_trend_30m', "N/A")

        logger.info(f"Successfully assembled comprehensive data package for {mint}.")
        return current_data

# --- Helper Function to Load Config Module to Dict ---
# (Needed for standalone execution to initialize DatabaseClient correctly)
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
    #logger.debug(f"Converted config module to dict: {list(config_dict.keys())}")
    return config_dict

# --- Main Test Execution ---
async def main(mint: str, include_explanation_in_output: bool = True):
    """
    Main async function to run the data assembly and AI decision test.

    Args:
        mint (str): The token mint address to analyze.
        include_explanation_in_output (bool): Whether to log the full explanation from the AI.
    """
    # Initialize logging
    setup_logging()
    logger.info(f"--- Starting AI Data Assembler Test for Mint: {mint} ---")

    # Get global state instance
    state = GlobalState.get_instance()

    # --- Load Configuration Explicitly (needed for standalone DatabaseClient init) ---
    loaded_config = {}
    try:
        # We imported 'from config import config as config_module' earlier
        loaded_config = _config_module_to_dict(config_module)
        if not loaded_config:
            raise ValueError("Config module loaded as empty dictionary.")
        logger.info(f"Successfully loaded {len(loaded_config)} config items for standalone run.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to load config module: {e}", exc_info=True)
        return # Cannot proceed without config

    # Initialize database client *with the loaded config*
    db = DatabaseClient(config_dict=loaded_config)

    try:
        # Connect to the database
        await db.connect()
        # Set the DB client in the global state
        await state.set_db_client(db)

        # Pre-fetch the current SOL price for efficiency
        sol_price_initial = None
        if db.pool:
            sol_price_initial = await db.pool.fetchval("SELECT price FROM sol_price_usd ORDER BY timestamp DESC LIMIT 1")
        if sol_price_initial:
            await state.set_sol_price(float(sol_price_initial))
            logger.info(f"Pre-fetched initial SOL price: ${state.sol_price:.4f}")
        else:
            logger.warning("Could not pre-fetch SOL price from DB. Setting to 0.0.")
            await state.set_sol_price(0.0) # Set a default if fetch fails

        # Initialize the AI Decision Maker
        ai = AIDecisionMaker()

        # Fetch the comprehensive data package for the specified mint
        current_data = await fetch_comprehensive_token_data(db, mint)

        # Log the fetched data (optional, can be verbose)
        #logger.info(f"--- Comprehensive Data Prepared for AI Prompt ({mint}) ---")
        #logger.info("\n" + json.dumps(current_data, indent=2, default=str)) # default=str handles Decimal/datetime
        #logger.info(f"--- End Comprehensive Data ---")

        # Get trade advice from the AI
        advice = ai.get_trade_advice(current_data, include_explanation=include_explanation_in_output)

        # Log the received advice clearly
        logger.info(f"--- AI Advice Received for {mint} ---")
        logger.info(f"Decision:   {advice['decision']}")
        logger.info(f"Confidence: {advice['confidence']}")
        if include_explanation_in_output:
            # Add indentation to make explanation block easier to read in logs
            explanation_lines = advice['explanation'].split('\n')
            indented_explanation = "\n".join(["  " + line for line in explanation_lines])
            logger.info(f"Explanation:\n{indented_explanation}")
        else:
            logger.info("Explanation: (Processing Skipped by flag)")
        logger.info(f"--- End AI Advice ---")

    except ValueError as ve:
        # Handle specific errors like token not found during data fetching
        logger.error(f"Data fetching or processing error for {mint}: {ve}", exc_info=True)
    except Exception as e:
        # Catch any other unexpected errors during execution
        logger.error(f"An unexpected error occurred in the main test function: {e}", exc_info=True)
    finally:
        # Ensure database connection pool is closed gracefully
        if db and db.pool:
            await db.close()
            logger.info("Database connection closed.")
        logger.info(f"--- Finished AI Data Assembler Test for Mint: {mint} ---")


if __name__ == "__main__":
    # This block executes only when the script is run directly

    # --- Command Line Argument Parsing ---
    include_expl = True # Default to include explanation
    mint_arg = None

    # Basic argument parsing: script_name <token_mint> [--no-explanation]
    if len(sys.argv) < 2:
        print("Usage: python ai_decision_module/ai_data_assembler.py <token_mint> [--no-explanation]")
        sys.exit(1)

    mint_arg = sys.argv[1] # First argument is the mint address

    # Check for optional flag to disable explanation processing/logging
    if len(sys.argv) > 2 and sys.argv[2] == '--no-explanation':
        include_expl = False
        print("[Standalone Mode] Running test without processing/logging the explanation.")

    # Set asyncio policy for Windows compatibility if needed
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run the main asynchronous function
    asyncio.run(main(mint_arg, include_explanation_in_output=include_expl))