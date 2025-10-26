# test_ai_decision_maker.py
import sys
import asyncio
import datetime as dt
import pandas as pd
import numpy as np
import json
import statistics
import httpx # For URI check
from datetime import datetime, timezone, timedelta
from decimal import Decimal # Import Decimal

from bot_logger import logger, setup_logging
from config.config import * # Import your base config values
from database_handler import DatabaseClient
from state_manager import GlobalState
from utils import calculate_volatility, ensure_datetime
from ai_decision_maker import AIDecisionMaker # Import your refactored class

# --- Calculation Helper Functions ---

# Helper to safely calculate percentage change
def safe_pct_change(old, new):
    if old is None or new is None or pd.isna(old) or pd.isna(new) or old == 0:
        return 0.0
    try:
        old_f, new_f = float(old), float(new)
        if old_f == 0: return 0.0
        return ((new_f / old_f) - 1) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0

async def check_uri_status(uri: str | None) -> str:
    """Performs a basic check on the metadata URI."""
    if not uri or not isinstance(uri, str): return "Missing"
    if not uri.startswith(('http://', 'https://')): return "Invalid Format"
    try:
        # Increased timeout slightly
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Use GET instead of HEAD as some servers block HEAD
            response = await client.get(uri)
            if 200 <= response.status_code < 400: return "Valid (Reachable)"
            else: return f"Error (HTTP {response.status_code})"
    except httpx.TimeoutException: return "Error (Timeout)"
    except httpx.RequestError as e:
        logger.debug(f"URI check request error for {uri}: {e}")
        return "Error (Request Failed)"
    except Exception as e:
        logger.warning(f"Unexpected error checking URI {uri}: {e}")
        return "Error (Unknown)"


def summarize_score_history(history_records: list, score_field: str, time_field: str, lookback_hours: float = 1.0) -> dict:
    """Summarizes score history including trends and stability."""
    # Determine prefix based on score_field early on
    result_prefix = 'rugcheck' if score_field == 'score' else 'social_score' if score_field == 'score_value' else 'unknown_score'

    default_result = {
        f"{result_prefix}_initial": None,
        f"{result_prefix}_latest": None,
        f"{result_prefix}_trend": "N/A",
        f"{result_prefix}_stability": "N/A",
        # Always include TG keys, they will be N/A if not social score
        "telegram_members_trend": "N/A",
        "telegram_online_ratio_trend": "N/A"
    }

    if not history_records:
        logger.debug(f"No history records provided for {score_field}.")
        return default_result

    try:
        df = pd.DataFrame(history_records)
        df[time_field] = pd.to_datetime(df[time_field], utc=True, errors='coerce')
        df = df.dropna(subset=[time_field]).sort_values(by=time_field)

        if df.empty:
            logger.debug(f"DataFrame empty after cleaning for {score_field}.")
            return default_result

        # Check for score field existence *before* trying to use it
        if score_field not in df.columns:
            logger.warning(f"Score field '{score_field}' not found in history records.")
            return default_result

        # Convert score field to numeric, handling potential errors
        df[score_field] = pd.to_numeric(df[score_field], errors='coerce')
        df = df.dropna(subset=[score_field]) # Drop rows where conversion failed or was NaN

        if df.empty:
            logger.debug(f"DataFrame empty after dropping NaN scores for {score_field}.")
            return default_result

        # Determine if it's rugcheck or social score *after* validation
        is_rugcheck = score_field == 'score'
        is_social = score_field == 'score_value'

        initial_score = df[score_field].iloc[0]
        latest_score = df[score_field].iloc[-1]

        # Trend calculation using a lookback window
        recent_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_hours)
        recent_scores = df[df[time_field] >= recent_cutoff][score_field]

        trend = "N/A"
        if len(recent_scores) > 1:
            change = recent_scores.iloc[-1] - recent_scores.iloc[0]
            # Trend description depends on score type (lower is better for both)
            trend_desc = "Improving" if change < 0 else "Worsening" if change > 0 else "Stable"
            trend = f"{change:+.0f} points ({trend_desc})"
        elif len(recent_scores) == 1:
             trend = "Stable (1 recent data point)"

        # Stability calculation (Standard Deviation)
        stability = "N/A"
        all_scores = df[score_field] # Use all available scores for stability
        if len(all_scores) > 1:
             std_dev = all_scores.std()
             if pd.isna(std_dev): stability = "N/A (Calc Error)"
             elif std_dev == 0: stability = "Very Stable"
             # Define stability thresholds based on score type
             elif (is_rugcheck and std_dev < 50) or (is_social and std_dev < 5): stability = "Stable"
             elif (is_rugcheck and std_dev < 200) or (is_social and std_dev < 15): stability = "Moderate Volatility"
             else: stability = "High Volatility"
        elif len(all_scores) == 1:
            stability = "Stable (1 data point)"

        # Telegram trend extraction (only if it's a social score)
        tg_members_trend = "N/A"
        tg_online_ratio_trend = "N/A"
        if is_social and 'details' in df.columns:
            # Filter for recent details within the lookback window
            recent_details_df = df[df[time_field] >= recent_cutoff].copy()

            # Safely parse JSON details
            def safe_json_loads(x):
                if isinstance(x, str):
                    try: return json.loads(x)
                    except json.JSONDecodeError: return {}
                elif isinstance(x, dict): return x
                return {}
            recent_details_df['details_dict'] = recent_details_df['details'].apply(safe_json_loads)

            # Safely extract Telegram stats
            def get_tg_stat(d, stat_key):
                if not isinstance(d, dict): return None
                tg_stats = d.get('telegram_stats')
                if isinstance(tg_stats, dict):
                    return tg_stats.get(stat_key)
                return None

            recent_details_df['members'] = recent_details_df['details_dict'].apply(lambda d: get_tg_stat(d, 'members'))
            recent_details_df['online'] = recent_details_df['details_dict'].apply(lambda d: get_tg_stat(d, 'online'))

            # Convert to numeric, handle errors
            recent_details_df['members'] = pd.to_numeric(recent_details_df['members'], errors='coerce')
            recent_details_df['online'] = pd.to_numeric(recent_details_df['online'], errors='coerce')

            # Calculate online ratio safely
            recent_details_df['online_ratio'] = np.where(
                recent_details_df['members'].notna() & (recent_details_df['members'] > 0) & recent_details_df['online'].notna(),
                recent_details_df['online'] / recent_details_df['members'],
                np.nan
            )

            # Calculate member trend
            valid_members = recent_details_df['members'].dropna()
            if len(valid_members) > 1:
                member_change = valid_members.iloc[-1] - valid_members.iloc[0]
                tg_members_trend = f"{member_change:+.0f}"

            # Calculate online ratio trend
            valid_ratios = recent_details_df['online_ratio'].dropna()
            if len(valid_ratios) > 1:
                ratio_change_pct = (valid_ratios.iloc[-1] - valid_ratios.iloc[0]) * 100
                tg_online_ratio_trend = f"{ratio_change_pct:+.1f}%"

        # Construct final result using the determined prefix
        final_result_renamed = {}
        final_result_renamed[f"{result_prefix}_initial"] = initial_score
        final_result_renamed[f"{result_prefix}_latest"] = latest_score
        final_result_renamed[f"{result_prefix}_trend"] = trend
        final_result_renamed[f"{result_prefix}_stability"] = stability
        final_result_renamed["telegram_members_trend"] = tg_members_trend # Already N/A if not social
        final_result_renamed["telegram_online_ratio_trend"] = tg_online_ratio_trend # Already N/A if not social

        return final_result_renamed

    except Exception as e:
        logger.error(f"Error in summarize_score_history for {score_field}: {e}", exc_info=True)
        # Return default structure on error, using the prefix determined earlier
        default_error_result = {
            f"{result_prefix}_initial": None, f"{result_prefix}_latest": None,
            f"{result_prefix}_trend": "N/A", f"{result_prefix}_stability": "N/A",
            "telegram_members_trend": "N/A", "telegram_online_ratio_trend": "N/A"
        }
        return default_error_result


def summarize_market_dynamics(history_records: list, source: str, lookback_mins: int = 15) -> dict:
    """Summarizes market dynamics (price change, volume velocity) from recent history."""
    summary = {}
    default_summary = {'market_dynamics_summary': "N/A - Insufficient recent market data"}

    if not history_records:
        logger.debug(f"Market Dynamics: No history records provided for source {source}.")
        return default_summary

    try:
        df = pd.DataFrame(history_records)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        df = df.dropna(subset=['timestamp']).set_index('timestamp').sort_index()

        # Define required columns based on source
        required_cols = []
        if source == 'PUMP':
            required_cols = ['price_sol', 'volume_usd']
        elif source == 'DEXSCREENER':
            # Needs fields used for both trend calculation and the summary string
            required_cols = ['price_change_m5', 'volume_m5', 'liquidity_usd']
        else:
             logger.warning(f"Market Dynamics: Unknown source '{source}'. Cannot determine required columns.")
             return default_summary

        # Add missing required columns with NaN
        for col in required_cols:
            if col not in df.columns:
                df[col] = np.nan

        # Convert potentially relevant columns to numeric after adding them
        numeric_cols = ['price_sol', 'volume_usd', 'price_change_m5', 'volume_m5', 'liquidity_usd']
        for col in numeric_cols:
             if col in df.columns: # Only convert if column exists
                # Use Decimal for price_sol if present, float otherwise
                if col == 'price_sol':
                    df[col] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) else pd.NA)
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce')


        now = dt.datetime.now(dt.timezone.utc)

        if source == 'PUMP':
            one_min_ago = now - dt.timedelta(minutes=1)
            recent_df_1m = df[df.index >= one_min_ago].copy()

            # Ensure 'price_sol' exists before trying to access it
            if 'price_sol' in recent_df_1m.columns and len(recent_df_1m['price_sol'].dropna()) > 1:
                first_price = recent_df_1m['price_sol'].dropna().iloc[0]
                last_price = recent_df_1m['price_sol'].dropna().iloc[-1]
                # Use Decimal safe_pct_change if needed, or cast to float
                price_change_1m = safe_pct_change(float(first_price), float(last_price))
                summary['pump_price_change_1m'] = f"{price_change_1m:.2f}%"
            else:
                summary['pump_price_change_1m'] = "N/A"

            # Ensure 'volume_usd' exists
            if 'volume_usd' in recent_df_1m.columns:
                 vol_sum_1m = recent_df_1m['volume_usd'].sum()
                 summary['pump_volume_velocity_1m'] = f"${vol_sum_1m:,.0f}"
            else:
                 summary['pump_volume_velocity_1m'] = "$N/A"

            summary['pump_tick_frequency_1m'] = len(recent_df_1m)

        elif source == 'DEXSCREENER':
            full_lookback_ago = now - dt.timedelta(minutes=lookback_mins)
            recent_df_lookback = df[df.index >= full_lookback_ago].copy()
            logger.debug(f"DexScreener dynamics: Found {len(recent_df_lookback)} snapshots in lookback window.")

            if len(recent_df_lookback) >= 2:
                # Price Trend (based on price_change_m5)
                price_change_col = recent_df_lookback['price_change_m5'].dropna() if 'price_change_m5' in recent_df_lookback else pd.Series(dtype=float)
                if len(price_change_col) > 1:
                    if len(price_change_col) > 2:
                         x = np.arange(len(price_change_col))
                         try:
                             slope = np.polyfit(x, price_change_col.values, 1)[0]
                             if slope > 0.1: summary['dex_price_trend_15m'] = "Increasing Momentum"
                             elif slope < -0.1: summary['dex_price_trend_15m'] = "Decreasing Momentum"
                             else: summary['dex_price_trend_15m'] = "Stable Momentum"
                         except (np.linalg.LinAlgError, ValueError): summary['dex_price_trend_15m'] = "Trend Calc Error"
                    else:
                        if price_change_col.iloc[-1] > price_change_col.iloc[0]: summary['dex_price_trend_15m'] = "Increasing Momentum"
                        elif price_change_col.iloc[-1] < price_change_col.iloc[0]: summary['dex_price_trend_15m'] = "Decreasing Momentum"
                        else: summary['dex_price_trend_15m'] = "Stable Momentum"
                elif len(price_change_col) == 1: summary['dex_price_trend_15m'] = "Stable (1 snapshot)"
                else: summary['dex_price_trend_15m'] = "N/A"

                # Volume Trend (using volume_m5)
                volume_col = recent_df_lookback['volume_m5'].dropna() if 'volume_m5' in recent_df_lookback else pd.Series(dtype=float)
                if len(volume_col) > 1:
                    if volume_col.iloc[-1] > volume_col.iloc[0] * 1.1: summary['dex_volume_trend_15m'] = "Increasing"
                    elif volume_col.iloc[-1] < volume_col.iloc[0] * 0.9: summary['dex_volume_trend_15m'] = "Decreasing"
                    else: summary['dex_volume_trend_15m'] = "Stable"
                elif len(volume_col) == 1: summary['dex_volume_trend_15m'] = "Stable (1 snapshot)"
                else: summary['dex_volume_trend_15m'] = "N/A"

                # Liquidity Trend (using liquidity_usd over 30 mins, but based on available data in lookback)
                # For simplicity, using the same recent_df_lookback (15 mins) for now
                liq_col = recent_df_lookback['liquidity_usd'].dropna() if 'liquidity_usd' in recent_df_lookback else pd.Series(dtype=float)
                if len(liq_col) > 1:
                     if liq_col.iloc[-1] > liq_col.iloc[0] * 1.05: summary['dex_liquidity_trend_30m'] = "Increasing"
                     elif liq_col.iloc[-1] < liq_col.iloc[0] * 0.95: summary['dex_liquidity_trend_30m'] = "Decreasing"
                     else: summary['dex_liquidity_trend_30m'] = "Stable"
                elif len(liq_col) == 1: summary['dex_liquidity_trend_30m'] = "Stable (1 snapshot)"
                else: summary['dex_liquidity_trend_30m'] = "N/A"
            else:
                 logger.debug(f"Not enough DexScreener snapshots ({len(recent_df_lookback)}) in the last {lookback_mins} mins.")
                 summary['dex_price_trend_15m'] = "N/A (Insufficient Data)"
                 summary['dex_volume_trend_15m'] = "N/A (Insufficient Data)"
                 summary['dex_liquidity_trend_30m'] = "N/A (Insufficient Data)"


        # --- Concise Summary String ---
        market_dynamics_parts = []
        if source == 'PUMP':
            market_dynamics_parts.append(f"Price(1m):{summary.get('pump_price_change_1m', 'N/A')}")
            market_dynamics_parts.append(f"Vol(1m):{summary.get('pump_volume_velocity_1m', 'N/A')}")
            market_dynamics_parts.append(f"Ticks(1m):{summary.get('pump_tick_frequency_1m', 'N/A')}")
        elif source == 'DEXSCREENER':
            market_dynamics_parts.append(f"Price Trend(15m):{summary.get('dex_price_trend_15m', 'N/A')}")
            market_dynamics_parts.append(f"Vol Trend(15m):{summary.get('dex_volume_trend_15m', 'N/A')}")
            market_dynamics_parts.append(f"Liq Trend(30m):{summary.get('dex_liquidity_trend_30m', 'N/A')}") # Name matches logic
        else:
             market_dynamics_parts.append("Unknown Source")

        summary['market_dynamics_summary'] = ", ".join(market_dynamics_parts) if market_dynamics_parts else "N/A"
        return summary

    except Exception as e:
        logger.error(f"Error summarizing market dynamics for source {source}: {e}", exc_info=True)
        return {'market_dynamics_summary': "Error calculating dynamics"}


def summarize_trade_history(history_records: list, max_events: int = 5) -> str:
    """
    Summarizes portfolio history chronologically for the AI prompt,
    focusing on the most recent events and highlighting reasons/outcomes.
    """
    if not history_records:
        return "No prior trading history for this token."

    df = pd.DataFrame(history_records)
    # Ensure timestamp is datetime before proceeding
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.dropna(subset=['timestamp']).sort_values(by='timestamp')

    # Convert profit to float, handling errors
    if 'profit' in df.columns:
        df['profit'] = pd.to_numeric(df['profit'], errors='coerce') # Coerce errors to NaN
    else:
        df['profit'] = np.nan # Add profit column if missing

    # Limit to the most recent events to keep the summary concise
    recent_events = df.tail(max_events).to_dict('records')

    summary_parts = []
    buy_count = len(df[df['tx_type'] == 'buy'])
    sell_count = len(df[df['tx_type'] == 'sell'])
    summary_parts.append(f"History Summary ({buy_count} Buys, {sell_count} Sells):")

    for event in recent_events:
        ts = event['timestamp']
        event_type = event['tx_type'].upper()
        price = event.get('price', 'N/A')
        reason = event.get('reason') # May be None for buys or if not recorded
        profit = event.get('profit') # May be NaN if conversion failed or not applicable

        # Format timestamp relative to now
        time_since = dt.datetime.now(timezone.utc) - ts
        if time_since < dt.timedelta(minutes=120):
            time_str = f"{time_since.total_seconds() / 60:.0f} mins ago"
        elif time_since < dt.timedelta(hours=48):
            time_str = f"{time_since.total_seconds() / 3600:.1f} hours ago"
        else:
            time_str = f"{time_since.days} days ago"

        event_str = f"- {event_type} ({time_str}) at {float(price):.8f} SOL."

        if event_type == 'SELL':
            reason_str = f" Reason: '{reason}'." if reason else ""
            profit_str = ""
            if pd.notna(profit): # Check if profit is not NaN
                 profit_str = f" Outcome: {profit:+.4f} SOL."
            else:
                 profit_str = " (Outcome N/A)." # Indicate if profit couldn't be determined
            event_str += reason_str + profit_str

        summary_parts.append(event_str)

    if len(df) > max_events:
        summary_parts.append(f"- ... (truncated, showing last {max_events} of {len(df)} events)")

    # Add overall outcome summary if possible (requires linking buys/sells, more complex)
    # For now, focus on recent events

    return "\n".join(summary_parts)

# --- Main Data Fetching Function (Refactored) ---
async def fetch_comprehensive_token_data(db: DatabaseClient, mint: str) -> dict:
    logger.info(f"Fetching comprehensive data for {mint}...")
    async with db.pool.acquire() as conn:
        # 1. Get Basic Info, Source, Creator, Timestamp, URI
        token_info = await conn.fetchrow(
            """SELECT name, symbol, data_source, traderpublickey, timestamp, uri
               FROM tokens WHERE mint = $1""", mint
        )
        if not token_info: raise ValueError(f"Token {mint} not found in 'tokens' table.")

        source = token_info['data_source']
        name = token_info['name']
        symbol = token_info['symbol']
        creator_wallet = token_info['traderpublickey']
        token_creation_ts = ensure_datetime(token_info['timestamp']) # Use helper
        uri = token_info['uri']

        token_age_minutes = None
        if token_creation_ts:
            token_age_minutes = (dt.datetime.now(dt.timezone.utc) - token_creation_ts).total_seconds() / 60

        creator_token_count = await conn.fetchval(
            "SELECT token_count FROM creator_wallets WHERE wallet_address = $1", creator_wallet
        ) or 0
        # Use config value for threshold check
        is_prolific_creator = creator_token_count > db.config.get('MAX_TOKEN_COUNT_PER_CREATOR', 50)

        uri_status = await check_uri_status(uri)

        # --- Determine Decision Context ---
        decision_context = "INITIAL BUY"
        # Check v_portfolio view which combines live and backup
        past_pos_count = await conn.fetchval(
             "SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint # Count only live portfolio
        )
        active_pos = await conn.fetchval( # Check specifically for active buys
            "SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint
        )

        if active_pos:
            decision_context = "SELL/HOLD"
        elif past_pos_count > 0: # If any past entries exist but none are active buys
            decision_context = "REBUY"
        # If no entries in portfolio, remains INITIAL BUY
        logger.debug(f"Decision context for {mint}: {decision_context}")
        # --- End Decision Context ---


        # 2. Get Current Price & MC (using unified method)
        price_data = await db.get_price_and_market_cap_for_decision(mint, db.config, conn) # Pass config
        current_price = price_data.get('price') # This is price_sol
        current_mcap_sol = price_data.get('market_cap') # This is market_cap_sol

        current_mcap_usd = 0.0
        sol_price = await GlobalState.get_instance().get_sol_price()
        if current_mcap_sol and sol_price and sol_price > 0:
            current_mcap_usd = float(current_mcap_sol) * sol_price # Ensure float calculation
        elif current_price is not None and current_price > 0:
             logger.warning(f"MCap SOL missing or invalid for {mint}. USD MCap will be 0.")
        else:
             logger.warning(f"Both Price and MCap SOL missing/invalid for {mint}. Cannot calculate USD MCap.")


        # 3. Fetch Score Histories (using views)
        # Fetch more history if available for better trend/stability
        rugcheck_hist_raw = await conn.fetch(
            "SELECT score, last_checked FROM v_rugcheck WHERE mint = $1 ORDER BY last_checked DESC LIMIT 50", mint
        )
        socials_hist_raw = await conn.fetch(
            "SELECT score_value, timestamp, details::TEXT as details FROM v_social_scores WHERE mint = $1 ORDER BY timestamp DESC LIMIT 50", mint
        )

        # 4. Fetch Recent Market History (source-specific for dynamics, unified for volatility)
        market_hist_lookback_mins = 15 # Consistent lookback for fetching base data
        market_hist_raw_unified = [] # For volatility calc (needs price_sol)
        market_hist_raw_source_specific = [] # For dynamics summary (needs source-specific fields)

        # Fetch from LIVE unified view for volatility base
        market_hist_raw_unified = await conn.fetch(
             f"""
             SELECT timestamp, price_sol, market_cap_sol, volume_usd
             FROM v_unified_market_ticks_live
             WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes' AND price_sol > 0
             ORDER BY timestamp ASC;
             """, mint
         )

        # Fetch source-specific data for dynamics summary
        if source == 'PUMP':
             # Use base 'trades' table for Pump dynamics calculation
             market_hist_raw_source_specific = await conn.fetch(
                f"""
                SELECT timestamp, price AS price_sol, sol_amount, token_amount, (sol_amount * sol_price_usd) AS volume_usd
                FROM trades
                WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes' AND price > 0
                ORDER BY timestamp ASC;
                """, mint
             )
        elif source == 'DEXSCREENER':
             # Use base 'dexscreener_data' for Dex dynamics calculation
             market_hist_raw_source_specific = await conn.fetch(
                 f"""
                 SELECT timestamp, price_change_m5, volume_m5, liquidity_usd, buys_m5, sells_m5
                 FROM dexscreener_data
                 WHERE mint_address = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes'
                 ORDER BY timestamp ASC;
                 """, mint
             )

        logger.debug(f"Fetched {len(market_hist_raw_unified)} unified and {len(market_hist_raw_source_specific)} source-specific market records for {mint}.")
        # Log samples only if data exists
        if market_hist_raw_unified: logger.debug(f"market_hist_raw_unified sample: {[dict(r) for r in market_hist_raw_unified[-5:]]}")
        if market_hist_raw_source_specific: logger.debug(f"market_hist_raw_source_specific sample: {[dict(r) for r in market_hist_raw_source_specific[-5:]]}")

        # --- Fetch Portfolio History ---
        portfolio_hist_raw = await conn.fetch(
            """
            SELECT timestamp, tx_type, price, reason, profit -- Ensure profit and reason are selected
            FROM portfolio -- Only need live portfolio for trade history summary
            WHERE mint = $1
            ORDER BY timestamp ASC;
            """, mint
        )
        # Pass raw records to the updated summary function
        trade_history_summary = summarize_trade_history([dict(r) for r in portfolio_hist_raw]) # Pass raw list
        logger.debug(f"Trade History Summary for {mint}:\n{trade_history_summary}") # Log multiline summary


        # 5. Calculate Summaries
        # Pass more records to summary functions
        rugcheck_summary = summarize_score_history(
            [dict(r) for r in rugcheck_hist_raw], 'score', 'last_checked', lookback_hours=1.0
        )
        socials_summary = summarize_score_history(
             [dict(r) for r in socials_hist_raw], 'score_value', 'timestamp', lookback_hours=1.0
        )
        # Use source-specific raw data for dynamics
        market_summary = summarize_market_dynamics(
            [dict(r) for r in market_hist_raw_source_specific], source, lookback_mins=market_hist_lookback_mins
        )


        # 6. Calculate/Retrieve Current Volatility
        volatility = 0.0
        if market_hist_raw_unified: # Use unified data for volatility calculation
            market_hist_df = pd.DataFrame([dict(r) for r in market_hist_raw_unified])
            if not market_hist_df.empty:
                market_hist_df['timestamp'] = pd.to_datetime(market_hist_df['timestamp'], utc=True, errors='coerce')
                # Ensure price_sol is numeric before calculating volatility
                market_hist_df['price_sol_numeric'] = pd.to_numeric(market_hist_df['price_sol'], errors='coerce')
                market_hist_df = market_hist_df.dropna(subset=['timestamp', 'price_sol_numeric'])

                if not market_hist_df.empty:
                     market_hist_df = market_hist_df.set_index('timestamp').sort_index()
                     price_series = market_hist_df['price_sol_numeric']
                     if not price_series.empty and len(price_series) > 1:
                         # Use utils.calculate_volatility which expects a Series
                         # Define a window size, e.g., using the number of fetched records or a fixed number
                         vol_window = min(len(price_series), 120) # Example: use up to 120 points, or fewer if less data
                         if vol_window >= 2:
                              volatility_series = calculate_volatility(price_series, window=vol_window)
                              if not volatility_series.empty:
                                   volatility = volatility_series.iloc[-1]
            logger.debug(f"Calculated Volatility for {mint} ({source}): {volatility:.4f}")
        else:
            logger.warning(f"No unified market history found for {mint} to calculate volatility.")


        # 7. Assemble final data dictionary (Refactored for Conditional Dynamics)
        current_data = {
            'mint': mint,
            'name': name,
            'symbol': symbol,
            'source': source, # Keep source identifier
            'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(),
            'decision_context': decision_context,
            'token_age_minutes': round(token_age_minutes, 1) if token_age_minutes is not None else None, # Include age
            'is_prolific_creator': is_prolific_creator,
            'uri_status': uri_status,
            'price': float(current_price) if current_price is not None else 0.0, # Ensure float
            'market_cap': current_mcap_usd, # Use calculated USD value
            'volatility': volatility,
            **rugcheck_summary,  # Includes *_initial, *_latest, *_trend, *_stability
            **socials_summary, # Includes *_initial, *_latest, *_trend, *_stability, tg_*_trend
            'trade_history_summary': trade_history_summary,
            'market_dynamics_summary_str': market_summary.get('market_dynamics_summary', "N/A"), # Store the summary string
        }

        # Conditionally add source-specific market dynamics keys used by prompts
        if source == 'PUMP':
            current_data['pump_price_change_1m'] = market_summary.get('pump_price_change_1m', "N/A")
            current_data['pump_volume_velocity_1m'] = market_summary.get('pump_volume_velocity_1m', "N/A")
            current_data['pump_tick_frequency_1m'] = market_summary.get('pump_tick_frequency_1m', "N/A")
        elif source == 'DEXSCREENER':
            # Get latest snapshot data (can reuse fetch from step 4 or fetch again)
            latest_dex_data = None
            if market_hist_raw_source_specific:
                 latest_dex_data = dict(market_hist_raw_source_specific[-1]) # Use last fetched
            else: # Fallback if history fetch failed but we know source is DEX
                 latest_dex_row = await conn.fetchrow(
                     "SELECT price_change_m5, buys_m5, sells_m5, volume_m5 "
                     "FROM dexscreener_data WHERE mint_address = $1 ORDER BY timestamp DESC LIMIT 1", mint
                 )
                 if latest_dex_row: latest_dex_data = dict(latest_dex_row)

            if latest_dex_data:
                 current_data['dex_price_change_m5'] = float(latest_dex_data.get('price_change_m5') or 0.0)
                 current_data['dex_buys_m5'] = int(latest_dex_data.get('buys_m5') or 0)
                 current_data['dex_sells_m5'] = int(latest_dex_data.get('sells_m5') or 0)
                 current_data['dex_volume_m5'] = float(latest_dex_data.get('volume_m5') or 0.0)
            else: # Still no data, add keys with defaults
                 current_data['dex_price_change_m5'] = 0.0
                 current_data['dex_buys_m5'] = 0
                 current_data['dex_sells_m5'] = 0
                 current_data['dex_volume_m5'] = 0.0

            # Add trend summaries
            current_data['dex_price_trend_15m'] = market_summary.get('dex_price_trend_15m', "N/A")
            current_data['dex_volume_trend_15m'] = market_summary.get('dex_volume_trend_15m', "N/A")
            current_data['dex_liquidity_trend_30m'] = market_summary.get('dex_liquidity_trend_30m', "N/A")

        # Rename score keys for clarity before returning (optional, but helps match prompt)
        # The spread operator already added them, this just ensures the prompt keys exist
        current_data['rugcheck_latest'] = current_data.get('rugcheck_latest', 'N/A')
        current_data['rugcheck_initial'] = current_data.get('rugcheck_initial', 'N/A')
        current_data['social_score_latest'] = current_data.get('social_score_latest', 'N/A')
        current_data['social_score_initial'] = current_data.get('social_score_initial', 'N/A')
        current_data['social_score_stability'] = current_data.get('social_score_stability', 'N/A')


        logger.info(f"Successfully assembled comprehensive data for {mint}.")
        return current_data

# --- Updated Main Function ---
async def main(mint: str):
    setup_logging()
    state = GlobalState.get_instance()
    # Pass base config dict to DatabaseClient
    db = DatabaseClient(config_dict=DatabaseClient._DEFAULT_CONFIG)
    await db.connect()
    await state.set_db_client(db)

    # Pre-fetch SOL price
    sol_price_initial = None
    if db.pool: # Check if pool connection succeeded
        sol_price_initial = await db.pool.fetchval("SELECT price FROM sol_price_usd ORDER BY timestamp DESC LIMIT 1")
    if sol_price_initial:
         await state.set_sol_price(float(sol_price_initial))
         logger.info(f"Pre-fetched SOL price: ${state.sol_price:.4f}")
    else:
         logger.warning("Could not pre-fetch SOL price from DB. Using default or 0. Calculations involving USD may be affected.")
         await state.set_sol_price(0.0) # Set a default to avoid NoneErrors


    # Initialize AI Decision Maker
    ai = AIDecisionMaker()

    try:
        # Fetch comprehensive data using the refactored function
        current_data = await fetch_comprehensive_token_data(db, mint)

        # Log the assembled data (using json.dumps for pretty printing)
        logger.info(f"--- Comprehensive Data for AI Prompt ({mint}) ---")
        # Use default=str to handle Decimals and potential datetimes if not converted
        logger.info("\n" + json.dumps(current_data, indent=2, default=str))
        logger.info(f"--- End Comprehensive Data ---")

        # Get trade advice using the refactored method
        advice = ai.get_trade_advice(current_data)

        # Log the AI's advice
        logger.info(f"--- AI Advice Received for {mint} ---")
        logger.info(f"Decision:   {advice['decision']}")
        logger.info(f"Confidence: {advice['confidence']}")
        logger.info(f"Explanation:\n{advice['explanation']}")
        logger.info(f"--- End AI Advice ---")

    except ValueError as ve:
         logger.error(f"Data fetching error for {mint}: {ve}", exc_info=True)
    except Exception as e:
        logger.error("Error in test script main execution: %s", e, exc_info=True)
    finally:
        if db.pool:
             await db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ai_decision_maker.py <token_mint>")
        sys.exit(1)
    mint_arg = sys.argv[1]
    # Ensure correct asyncio policy for Windows if needed
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(mint_arg))