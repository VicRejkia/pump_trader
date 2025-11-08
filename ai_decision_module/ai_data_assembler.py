# ai_data_assembler.py
import sys
import os
import asyncio
import datetime as dt
import pandas as pd
import numpy as np
import json
import statistics
import httpx 
from decimal import Decimal 
import inspect 

# --- Conditional Path Setup for Standalone Execution ---
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"[Standalone Mode] Added project root to sys.path: {project_root}")

# --- Imports ---
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from state_manager import GlobalState
from utils import calculate_volatility, ensure_datetime, calculate_trend_indicators
from ai_decision_module.ai_decision_maker import AIDecisionMaker 
from config import config as config_module
# (Removed MAX_TOKEN_COUNT_PER_CREATOR import)

# --- Calculation Helper Functions ---
# (safe_pct_change, check_uri_status, summarize_score_history,
#  summarize_market_dynamics, summarize_trade_history)
# --- These functions are unchanged ---

def safe_pct_change(old, new) -> float:
    """Safely calculates the percentage change between two values."""
    if old is None or new is None or pd.isna(old) or pd.isna(new):
        return 0.0
    try:
        old_f = float(str(old)) if isinstance(old, Decimal) else float(old)
        new_f = float(str(new)) if isinstance(new, Decimal) else float(new)
        if old_f == 0: return 0.0
        return ((new_f / old_f) - 1) * 100.0
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.warning(f"🧠 safe_pct_change error: old={old}, new={new}, error={e}")
        return 0.0

async def check_uri_status(uri: str | None) -> str:
    """Performs a basic reachability check on a metadata URI."""
    if not uri or not isinstance(uri, str): return "Missing"
    if not uri.startswith(('http://', 'https://')): return "Invalid Format"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(uri)
            if 200 <= response.status_code < 400: return "Valid (Reachable)"
            else: return f"Error (HTTP {response.status_code})"
    except httpx.TimeoutException: return "Error (Timeout)"
    except httpx.RequestError as e:
        logger.debug(f"🧠 URI check request error for {uri}: {e}"); return "Error (Request Failed)"
    except Exception as e:
        logger.warning(f"🧠 Unexpected error checking URI {uri}: {e}", exc_info=True); return "Error (Unknown)"

def summarize_score_history(history_records: list, score_field: str, time_field: str, lookback_hours: float = 1.0) -> dict:
    """Summarizes score history (Rugcheck or Social) (Unchanged)."""
    result_prefix = 'rugcheck' if score_field == 'score' else 'social_score' if score_field == 'score_value' else 'unknown_score'
    default_result = {
        f"{result_prefix}_initial": None, f"{result_prefix}_latest": None,
        f"{result_prefix}_trend": "N/A", f"{result_prefix}_stability": "N/A",
        "telegram_members_trend": "N/A", "telegram_online_ratio_trend": "N/A",
        "latest_telegram_members": None, "latest_telegram_online": None # <-- ADD THESE DEFAULTS
    }
    if not history_records: return default_result
    try:
        df = pd.DataFrame(history_records)
        df[time_field] = pd.to_datetime(df[time_field], utc=True, errors='coerce')
        df = df.dropna(subset=[time_field]).sort_values(by=time_field)
        if df.empty: return default_result
        if score_field not in df.columns:
            logger.warning(f"Score field '{score_field}' not found."); return default_result
        
        df[score_field] = pd.to_numeric(df[score_field], errors='coerce')
        df = df.dropna(subset=[score_field])
        if df.empty: return default_result

        initial_score = df[score_field].iloc[0]
        latest_score = df[score_field].iloc[-1]
        
        recent_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_hours)
        recent_scores_series = df[df[time_field] >= recent_cutoff][score_field]
        trend_description = "N/A"
        if len(recent_scores_series) > 1:
            change = recent_scores_series.iloc[-1] - recent_scores_series.iloc[0]
            trend_direction = "Improving" if change < 0 else "Worsening" if change > 0 else "Stable"
            trend_description = f"{change:+.0f} points ({trend_direction})"
        elif len(recent_scores_series) == 1:
            trend_description = "Stable (1 recent data point)"

        stability_description = "N/A"
        all_scores_series = df[score_field]
        if len(all_scores_series) > 1:
             std_dev = all_scores_series.std()
             if pd.isna(std_dev): stability_description = "N/A (Calc Error)"
             elif std_dev == 0: stability_description = "Very Stable"
             elif (score_field == 'score' and std_dev < 50) or (score_field == 'score_value' and std_dev < 5): stability_description = "Stable"
             elif (score_field == 'score' and std_dev < 200) or (score_field == 'score_value' and std_dev < 15): stability_description = "Moderate Volatility"
             else: stability_description = "High Volatility"
        elif len(all_scores_series) == 1:
             stability_description = "Stable (1 data point)"

        tg_members_trend_str, tg_online_ratio_trend_str = "N/A", "N/A"
        latest_telegram_members, latest_telegram_online = None, None

        if score_field == 'score_value' and 'details' in df.columns:
            recent_details_df = df[df[time_field] >= recent_cutoff].copy()
            def safe_json_loads(x):
                if isinstance(x, str):
                    try: return json.loads(x)
                    except json.JSONDecodeError: return {}
                elif isinstance(x, dict): return x
                return {}
            recent_details_df['details_dict'] = recent_details_df['details'].apply(safe_json_loads)
            def get_tg_stat(d, stat_key):
                if not isinstance(d, dict): return None
                tg_stats = d.get('telegram_stats')
                return tg_stats.get(stat_key) if isinstance(tg_stats, dict) else None
            recent_details_df['members'] = recent_details_df['details_dict'].apply(lambda d: get_tg_stat(d, 'members'))
            recent_details_df['online'] = recent_details_df['details_dict'].apply(lambda d: get_tg_stat(d, 'online'))
            recent_details_df['members'] = pd.to_numeric(recent_details_df['members'], errors='coerce')
            recent_details_df['online'] = pd.to_numeric(recent_details_df['online'], errors='coerce')
            recent_details_df['online_ratio'] = np.where(
                recent_details_df['members'].notna() & (recent_details_df['members'] > 0) & recent_details_df['online'].notna(),
                recent_details_df['online'] / recent_details_df['members'], np.nan
            )
            valid_members_series = recent_details_df['members'].dropna()
            if len(valid_members_series) > 1:
                member_change = valid_members_series.iloc[-1] - valid_members_series.iloc[0]
                tg_members_trend_str = f"{member_change:+.0f}"
            
            if not valid_members_series.empty:
                latest_telegram_members = valid_members_series.iloc[-1]
            valid_online_series = recent_details_df['online'].dropna()
            if not valid_online_series.empty:
                latest_telegram_online = valid_online_series.iloc[-1]
            
            valid_ratios_series = recent_details_df['online_ratio'].dropna()
            if len(valid_ratios_series) > 1:
                ratio_change_pct = (valid_ratios_series.iloc[-1] - valid_ratios_series.iloc[0]) * 100
                tg_online_ratio_trend_str = f"{ratio_change_pct:+.1f}%"

        final_result = {
            f"{result_prefix}_initial": initial_score, f"{result_prefix}_latest": latest_score,
            f"{result_prefix}_trend": trend_description, f"{result_prefix}_stability": stability_description,
            "telegram_members_trend": tg_members_trend_str, "telegram_online_ratio_trend": tg_online_ratio_trend_str,
            "latest_telegram_members": latest_telegram_members, # <-- ADD THIS
            "latest_telegram_online": latest_telegram_online   # <-- ADD THIS
        }
        return final_result
    except Exception as e:
        logger.error(f"🧠 Error in summarize_score_history for {score_field}: {e}", exc_info=True)
        return default_result

def summarize_market_dynamics(history_records: list, source: str, lookback_mins: int = 15) -> dict:
    """Summarizes recent market dynamics (Unchanged)."""
    summary = {}; default_summary = {'market_dynamics_summary': "N/A - Insufficient recent market data"}
    if not history_records: return default_summary
    try:
        df = pd.DataFrame(history_records)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        df = df.dropna(subset=['timestamp']).set_index('timestamp').sort_index()
        required_cols, numeric_cols = [], []
        if source == 'PUMP':
            required_cols, numeric_cols = ['price_sol', 'volume_usd'], ['price_sol', 'volume_usd']
        elif source == 'DEXSCREENER':
            required_cols = ['price_change_m5', 'volume_m5', 'liquidity_usd', 'buys_m5', 'sells_m5']
            numeric_cols = ['price_change_m5', 'volume_m5', 'liquidity_usd', 'buys_m5', 'sells_m5']
        else:
            logger.warning(f"🧠 Market Dynamics: Unknown source '{source}'."); return default_summary
        
        for col in required_cols:
            if col not in df.columns: df[col] = np.nan
        for col in numeric_cols:
             if col in df.columns:
                if col == 'price_sol': df[col] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) else pd.NA)
                else: df[col] = pd.to_numeric(df[col], errors='coerce')
        
        now_utc = dt.datetime.now(dt.timezone.utc)
        if source == 'PUMP':
            one_min_ago = now_utc - dt.timedelta(minutes=1)
            recent_df_1m = df[df.index >= one_min_ago].copy()
            price_series_1m = recent_df_1m['price_sol'].dropna()
            if len(price_series_1m) > 1:
                summary['pump_price_change_1m'] = f"{safe_pct_change(price_series_1m.iloc[0], price_series_1m.iloc[-1]):.2f}%"
            else: summary['pump_price_change_1m'] = "N/A"
            if 'volume_usd' in recent_df_1m.columns:
                summary['pump_volume_velocity_1m'] = f"${recent_df_1m['volume_usd'].sum():,.0f}"
            else: summary['pump_volume_velocity_1m'] = "$N/A"
            summary['pump_tick_frequency_1m'] = len(recent_df_1m)
        elif source == 'DEXSCREENER':
            full_lookback_ago = now_utc - dt.timedelta(minutes=lookback_mins)
            recent_df_lookback = df[df.index >= full_lookback_ago].copy()
            if len(recent_df_lookback) >= 2:
                price_change_col = recent_df_lookback['price_change_m5'].dropna() if 'price_change_m5' in recent_df_lookback else pd.Series(dtype=float)
                if len(price_change_col) > 1:
                    if len(price_change_col) > 2:
                         x_vals = np.arange(len(price_change_col))
                         try:
                             slope = np.polyfit(x_vals, price_change_col.values, 1)[0]
                             if slope > 0.1: summary['dex_price_trend_15m'] = "Increasing Momentum"
                             elif slope < -0.1: summary['dex_price_trend_15m'] = "Decreasing Momentum"
                             else: summary['dex_price_trend_15m'] = "Stable Momentum"
                         except (np.linalg.LinAlgError, ValueError):
                             logger.warning("LinAlgError during Dex price trend calculation."); summary['dex_price_trend_15m'] = "Trend Calc Error"
                    else: 
                        if price_change_col.iloc[-1] > price_change_col.iloc[0]: summary['dex_price_trend_15m'] = "Increasing Momentum"
                        elif price_change_col.iloc[-1] < price_change_col.iloc[0]: summary['dex_price_trend_15m'] = "Decreasing Momentum"
                        else: summary['dex_price_trend_15m'] = "Stable Momentum"
                elif len(price_change_col) == 1: summary['dex_price_trend_15m'] = "Stable (1 snapshot)"
                else: summary['dex_price_trend_15m'] = "N/A"
                volume_col = recent_df_lookback['volume_m5'].dropna() if 'volume_m5' in recent_df_lookback else pd.Series(dtype=float)
                if len(volume_col) > 1:
                    if volume_col.iloc[-1] > volume_col.iloc[0] * 1.1: summary['dex_volume_trend_15m'] = "Increasing"
                    elif volume_col.iloc[-1] < volume_col.iloc[0] * 0.9: summary['dex_volume_trend_15m'] = "Decreasing"
                    else: summary['dex_volume_trend_15m'] = "Stable"
                elif len(volume_col) == 1: summary['dex_volume_trend_15m'] = "Stable (1 snapshot)"
                else: summary['dex_volume_trend_15m'] = "N/A"
                liq_col = recent_df_lookback['liquidity_usd'].dropna() if 'liquidity_usd' in recent_df_lookback else pd.Series(dtype=float)
                trend_key_liq = f"dex_liquidity_trend_{lookback_mins}m"
                if len(liq_col) > 1:
                     if liq_col.iloc[-1] > liq_col.iloc[0] * 1.05: summary[trend_key_liq] = "Increasing"
                     elif liq_col.iloc[-1] < liq_col.iloc[0] * 0.95: summary[trend_key_liq] = "Decreasing"
                     else: summary[trend_key_liq] = "Stable"
                elif len(liq_col) == 1: summary[trend_key_liq] = "Stable (1 snapshot)"
                else: summary[trend_key_liq] = "N/A"
                summary['dex_liquidity_trend_30m'] = summary.get(trend_key_liq, "N/A")
            else:
                 summary['dex_price_trend_15m'] = "N/A (Few Snaps)"; summary['dex_volume_trend_15m'] = "N/A (Few Snaps)"; summary['dex_liquidity_trend_30m'] = "N/A (Few Snaps)"

        market_dynamics_parts = []
        if source == 'PUMP':
            market_dynamics_parts.extend([
                f"Price(1m):{summary.get('pump_price_change_1m', 'N/A')}", f"Vol(1m):{summary.get('pump_volume_velocity_1m', 'N/A')}",
                f"Ticks(1m):{summary.get('pump_tick_frequency_1m', 'N/A')}"
            ])
        elif source == 'DEXSCREENER':
            market_dynamics_parts.extend([
                f"Price Trend(15m):{summary.get('dex_price_trend_15m', 'N/A')}", f"Vol Trend(15m):{summary.get('dex_volume_trend_15m', 'N/A')}",
                f"Liq Trend({lookback_mins}m):{summary.get(f'dex_liquidity_trend_{lookback_mins}m', 'N/A')}"
            ])
        else: market_dynamics_parts.append("Unknown Source")
        summary['market_dynamics_summary'] = ", ".join(market_dynamics_parts) if market_dynamics_parts else "N/A"
        return summary
    except Exception as e:
        logger.error(f"🧠 Error summarizing market dynamics for {source}: {e}", exc_info=True)
        return {'market_dynamics_summary': "Error calculating dynamics"}

def summarize_trade_history(history_records: list, max_events: int = 5) -> str:
    """Summarizes portfolio history chronologically (Unchanged)."""
    if not history_records: return "No prior trading history for this token."
    try:
        df = pd.DataFrame(history_records)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        df = df.dropna(subset=['timestamp']).sort_values(by='timestamp')
        if 'profit' in df.columns:
            df['profit'] = pd.to_numeric(df['profit'], errors='coerce')
        else: df['profit'] = np.nan
        recent_events = df.tail(max_events).to_dict('records')
        summary_parts = [f"History Summary ({len(df[df['tx_type'] == 'buy'])} Buys, {len(df[df['tx_type'] == 'sell'])} Sells):"]
        now_utc = dt.datetime.now(dt.timezone.utc)
        for event in recent_events:
            ts, event_type, price, reason, profit = event['timestamp'], event['tx_type'].upper(), event.get('price'), event.get('reason'), event.get('profit')
            time_since = now_utc - ts
            if time_since < dt.timedelta(minutes=120): time_str = f"{time_since.total_seconds() / 60:.0f} mins ago"
            elif time_since < dt.timedelta(hours=48): time_str = f"{time_since.total_seconds() / 3600:.1f} hours ago"
            else: time_str = f"{time_since.days} days ago"
            price_str = f"{float(price):.8f}" if isinstance(price, (Decimal, float, int)) and pd.notna(price) else "N/A"
            event_str = f"- {event_type} ({time_str}) at {price_str} SOL."
            if event_type == 'SELL':
                reason_str = f" Reason: '{reason}'." if reason else ""
                profit_str = f" Outcome: {profit:+.4f} SOL." if pd.notna(profit) else " (Outcome N/A)."
                event_str += reason_str + profit_str
            summary_parts.append(event_str)
        if len(df) > max_events:
            summary_parts.append(f"- ... (truncated, showing last {max_events} of {len(df)} total events)")
        return "\n".join(summary_parts)
    except Exception as e:
        logger.error(f"🧠 Error summarizing trade history: {e}", exc_info=True)
        return "Error generating trade history summary."

# --- Main Data Fetching Function ---
async def fetch_comprehensive_token_data(db: DatabaseClient, mint: str) -> dict:
    """
    [MODIFIED]
    Fetches and processes all necessary data for a given token mint.
    Now uses `get_creator_history_summary` instead of the old binary flag.
    """
    logger.info(f"🧠 Fetching comprehensive data for token {mint}...")
    async with db.pool.acquire() as conn:
        # 1. Basic Token Info & Context
        token_info = await conn.fetchrow(
            "SELECT name, symbol, data_source, traderpublickey, timestamp, uri FROM tokens WHERE mint = $1", mint
        )
        if not token_info:
            # Token is not in the active 'tokens' table.
            # Check if it's in the backup table to detect the race condition.
            backup_info = await conn.fetchrow(
                 "SELECT backup_reason, timestamp, traderPublicKey FROM tokens_backup WHERE mint = $1 LIMIT 1", mint
            )
            if backup_info:
                # This is the race condition. The token was just backed up.
                # We should not evaluate it, but we *should* log this outcome.
                logger.warning(f"🧠 Token {mint} is no longer active (found in backup). Returning minimal outcome packet.")
                
                # --- NEW: Fetch the creator summary properly ---
                creator_wallet = backup_info['traderpublickey']
                creator_summary_string = "N/A"
                if creator_wallet:
                     creator_summary_string = await db.get_creator_history_summary(creator_wallet, mint)
                # --- END NEW ---

                # Return a special dictionary that the AI worker can use to log this outcome
                return {
                    "status": "INACTIVE_BACKED_UP", # Special key to be checked by the worker
                    "mint": mint,
                    "backup_reason": backup_info['backup_reason'],
                    "backup_timestamp": backup_info['timestamp'],
                    "creator_history_summary": creator_summary_string, # <-- THIS IS THE FIX
                    "decision_context": "NON_TRADE_OUTCOME" # Use the outcome context
                }
            else:
                # The token doesn't exist anywhere.
                logger.error(f"🧠 Token {mint} not found in 'tokens' or 'tokens_backup' table.")
                raise ValueError(f"Token {mint} not found in 'tokens' or 'tokens_backup' table.")

        # If we are here, token_info is valid and from the active 'tokens' table.
        source, name, symbol, creator_wallet = token_info['data_source'], token_info['name'], token_info['symbol'], token_info['traderpublickey']
        token_creation_ts = ensure_datetime(token_info['timestamp'])
        uri = token_info['uri']
        token_age_minutes = (dt.datetime.now(dt.timezone.utc) - token_creation_ts).total_seconds() / 60 if token_creation_ts else None
        
        # --- MODIFICATION START ---
        # Get the new rich creator summary from the database
        # We pass 'conn' so it uses the existing connection/transaction
        creator_summary_string = await db.get_creator_history_summary(creator_wallet, mint)
        # --- MODIFICATION END ---
        
        uri_status = await check_uri_status(uri)

        # 2. Determine Current Decision Context
        decision_context = "INITIAL BUY"
        past_pos_count = await conn.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
        active_pos = await conn.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)
        if active_pos: decision_context = "SELL/HOLD"
        elif past_pos_count > 0: decision_context = "REBUY"

        # 3. Get Current Price & Market Cap
        price_data = await db.get_price_and_market_cap_for_decision(mint, db.config, conn)
        current_price_sol = price_data.get('price')
        current_mcap_sol = price_data.get('market_cap')
        current_mcap_usd = 0.0
        sol_price = await GlobalState.get_instance().get_sol_price()
        if current_mcap_sol and sol_price and sol_price > 0:
            current_mcap_usd = float(current_mcap_sol) * sol_price
        elif current_price_sol is None or current_price_sol <= 0:
            logger.warning(f"🧠 Both Price and Market Cap in SOL missing or invalid for {mint}. Setting USD Market Cap to 0.")
        
        # 4. Fetch Score Histories
        rugcheck_hist_raw = await conn.fetch(
            "SELECT score, last_checked FROM v_rugcheck WHERE mint = $1 ORDER BY last_checked DESC LIMIT 50", mint
        )
        socials_hist_raw = await conn.fetch(
            "SELECT score_value, timestamp, details::TEXT as details FROM v_social_scores WHERE mint = $1 ORDER BY timestamp DESC LIMIT 50", mint
        )

        # 5. Fetch Market History
        market_hist_lookback_mins = 15
        view_to_use = "v_unified_market_ticks_live" if await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint) else "v_unified_market_ticks_historical"
        market_hist_raw_unified = await conn.fetch(
            f"""SELECT timestamp, price_sol, market_cap_sol, volume_usd
                FROM {view_to_use}
                WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes' AND price_sol > 0
                ORDER BY timestamp ASC;""", mint
        )
        market_hist_raw_source_specific = []
        if source == 'PUMP':
            table_to_use_pump = "trades" if await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint) else "trades_backup"
            market_hist_raw_source_specific = await conn.fetch(
                f"""SELECT timestamp, price AS price_sol, sol_amount, token_amount, (sol_amount * sol_price_usd) AS volume_usd
                    FROM {table_to_use_pump} WHERE mint = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes' AND price > 0
                    ORDER BY timestamp ASC;""", mint
            )
        elif source == 'DEXSCREENER':
            market_hist_raw_source_specific = await conn.fetch(
                f"""SELECT timestamp, price_change_m5, volume_m5, liquidity_usd, buys_m5, sells_m5
                    FROM v_dexscreener_data WHERE mint_address = $1 AND timestamp >= NOW() - INTERVAL '{market_hist_lookback_mins} minutes'
                    ORDER BY timestamp ASC;""", mint
            )

        # 6. Fetch Portfolio (Trade) History
        portfolio_hist_raw = await conn.fetch(
            """SELECT timestamp, tx_type, price, reason, profit FROM portfolio WHERE mint = $1
               UNION ALL
               SELECT timestamp, tx_type, price, reason, profit FROM portfolio_backup WHERE mint = $1
               ORDER BY timestamp ASC;""", mint
        )
        trade_history_summary = summarize_trade_history([dict(r) for r in portfolio_hist_raw])

        # 7. Calculate Summaries & Volatility
        rugcheck_summary = summarize_score_history([dict(r) for r in rugcheck_hist_raw], 'score', 'last_checked', lookback_hours=1.0)
        socials_summary = summarize_score_history([dict(r) for r in socials_hist_raw], 'score_value', 'timestamp', lookback_hours=1.0)
        market_summary = summarize_market_dynamics([dict(r) for r in market_hist_raw_source_specific], source, lookback_mins=market_hist_lookback_mins)
        volatility = 0.0
        latest_rsi = 'N/A'
        latest_ema_fast = 'N/A'
        latest_ema_slow = 'N/A'
        if market_hist_raw_unified:
            market_hist_df = pd.DataFrame([dict(r) for r in market_hist_raw_unified])
            if not market_hist_df.empty:
                market_hist_df['timestamp'] = pd.to_datetime(market_hist_df['timestamp'], utc=True, errors='coerce')
                market_hist_df['price_sol_decimal'] = market_hist_df['price_sol'].apply(lambda x: Decimal(str(x)) if pd.notna(x) else pd.NA)
                market_hist_df = market_hist_df.dropna(subset=['timestamp', 'price_sol_decimal'])
                if not market_hist_df.empty:
                    market_hist_df = market_hist_df.set_index('timestamp').sort_index()
                    price_series = pd.to_numeric(market_hist_df['price_sol_decimal'])
                    
                    if not price_series.empty and len(price_series) > 1:
                        vol_window = min(len(price_series), 120)
                        if vol_window >= 2:
                            volatility_series = calculate_volatility(price_series, window=vol_window)
                            if not volatility_series.empty: volatility = volatility_series.iloc[-1]

                        # Resample price to OHLC
                        ohlc = price_series.resample('5s').ohlc()
                        # Resample volume
                        if 'volume_usd' in market_hist_df.columns:
                            volume_series = pd.to_numeric(market_hist_df['volume_usd'])
                            vol = volume_series.resample('5s').sum()
                            ohlc['Volume'] = vol
                        else:
                            ohlc['Volume'] = 0 # No volume data

                        # Forward-fill gaps from resampling and drop any remaining NaNs
                        ohlc = ohlc.ffill().dropna()

                        min_candles = db.config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30)
                        if len(ohlc) >= min_candles:
                            # Rename columns to what calculate_trend_indicators expects
                            ohlc.rename(columns={
                                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'
                            }, inplace=True)

                            # Run the existing TA function
                            df_with_indicators = calculate_trend_indicators(ohlc, db.config)
                            
                            if not df_with_indicators.empty:
                                latest_row = df_with_indicators.iloc[-1]
                                
                                # Get the column names from config
                                rsi_col = f"RSI_{db.config['RSI_PERIOD']}"
                                ema_fast_col = 'EMA_fast'
                                ema_slow_col = 'EMA_slow'
                                
                                # Safely extract values and format them
                                if rsi_col in latest_row and pd.notna(latest_row[rsi_col]):
                                    latest_rsi = f"{latest_row[rsi_col]:.2f}"
                                if ema_fast_col in latest_row and pd.notna(latest_row[ema_fast_col]):
                                    latest_ema_fast = f"{latest_row[ema_fast_col]:.9f}"
                                if ema_slow_col in latest_row and pd.notna(latest_row[ema_slow_col]):
                                    latest_ema_slow = f"{latest_row[ema_slow_col]:.9f}"
                                
                                logger.debug(f"🧠 TA Indicators for {mint}: RSI={latest_rsi}, EMA_F={latest_ema_fast}, EMA_S={latest_ema_slow}")
                        else:
                            logger.debug(f"🧠 Not enough resampled candles for TA ({len(ohlc)} < {min_candles})")
        else:
            logger.warning(f"🧠 No unified market history available for {mint} to calculate volatility.")

        # --- 7b. Calculate Data Completeness ---
        data_completeness_score = 100
        completeness_notes = []
        if rugcheck_summary.get('rugcheck_latest') is None or str(rugcheck_summary.get('rugcheck_latest')).lower() == 'none':
            data_completeness_score -= 30
            completeness_notes.append("Missing Rugcheck Score")
        if socials_summary.get('social_score_latest') is None or str(socials_summary.get('social_score_latest')).lower() == 'none':
            data_completeness_score -= 20
            completeness_notes.append("Missing Social Score")
        if socials_summary.get('latest_telegram_members') is None: # Use the field we just added
            data_completeness_score -= 10 # Less penalty than core social score
            completeness_notes.append("Missing Telegram Stats")
        if uri_status != "Valid (Reachable)":
            data_completeness_score -= 25
            completeness_notes.append(f"Invalid URI: {uri_status}")
        if market_summary.get('market_dynamics_summary_str', "N/A").startswith("N/A"):
            data_completeness_score -= 15
            completeness_notes.append("Missing Market Dynamics")
        
        data_completeness_score = max(0, data_completeness_score) # Clamp at 0
        market_regime = await GlobalState.get_instance().get_market_regime()

        # 8. Assemble Final Data Dictionary
        current_data = {
            'mint': mint, 'name': name, 'symbol': symbol, 'source': source,
            'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(),
            'decision_context': decision_context,
            'token_age_minutes': round(token_age_minutes, 1) if token_age_minutes is not None else None,
            
            # --- MODIFICATION START ---
            'creator_history_summary': creator_summary_string, # ADD this
            # --- MODIFICATION END ---
            
            'uri_status': uri_status,
            'price': float(current_price_sol) if current_price_sol is not None else 0.0,
            'market_cap': current_mcap_usd, 'volatility': volatility,
            'latest_rsi': latest_rsi,
            'latest_ema_fast': latest_ema_fast,
            'latest_ema_slow': latest_ema_slow,
            'data_completeness_score': data_completeness_score,
            'data_completeness_notes': ", ".join(completeness_notes) or "All data present",
            'market_regime': market_regime,
            **rugcheck_summary, **socials_summary,
            'trade_history_summary': trade_history_summary,
            'market_dynamics_summary_str': market_summary.get('market_dynamics_summary', "N/A"),
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

        if source == 'PUMP':
            current_data['pump_price_change_1m'] = market_summary.get('pump_price_change_1m', "N/A")
            current_data['pump_volume_velocity_1m'] = market_summary.get('pump_volume_velocity_1m', "N/A")
            current_data['pump_tick_frequency_1m'] = market_summary.get('pump_tick_frequency_1m', "N/A")
        elif source == 'DEXSCREENER':
            latest_dex_data = None
            if market_hist_raw_source_specific:
                latest_dex_data = dict(market_hist_raw_source_specific[-1])
            else:
                 latest_dex_row = await conn.fetchrow(
                     """SELECT price_change_m5, buys_m5, sells_m5, volume_m5
                        FROM v_dexscreener_data WHERE mint_address = $1
                        ORDER BY timestamp DESC LIMIT 1""", mint
                 )
                 if latest_dex_row: latest_dex_data = dict(latest_dex_row)
            current_data['dex_price_change_m5'] = float(latest_dex_data.get('price_change_m5', 0.0)) if latest_dex_data else 0.0
            current_data['dex_buys_m5'] = int(latest_dex_data.get('buys_m5', 0)) if latest_dex_data else 0
            current_data['dex_sells_m5'] = int(latest_dex_data.get('sells_m5', 0)) if latest_dex_data else 0
            current_data['dex_volume_m5'] = float(latest_dex_data.get('volume_m5', 0.0)) if latest_dex_data else 0.0
            current_data['dex_price_trend_15m'] = market_summary.get('dex_price_trend_15m', "N/A")
            current_data['dex_volume_trend_15m'] = market_summary.get('dex_volume_trend_15m', "N/A")
            current_data['dex_liquidity_trend_30m'] = market_summary.get('dex_liquidity_trend_30m', "N/A")

        logger.info(f"🧠 Successfully assembled comprehensive data package for {mint}.")
        return current_data

# --- Helper Function to Load Config Module to Dict ---
def _config_module_to_dict(module) -> dict:
    """Converts public, uppercase attributes of a module into a dictionary (Unchanged)."""
    config_dict = {}
    for key in dir(module):
        if key.isupper() and not key.startswith('_'):
            value = getattr(module, key)
            if not inspect.ismodule(value) and \
               not inspect.isclass(value) and \
               not inspect.isfunction(value):
                config_dict[key] = value
    return config_dict

# --- Main Test Execution ---
async def main(mint: str, include_explanation_in_output: bool = True):
    """
    (Unchanged) Main async function to run the data assembly and AI decision test.
    """
    setup_logging('ai_data_assembler_test')
    logger.info(f"--- Starting AI Data Assembler Test for Mint: {mint} ---")
    state = GlobalState.get_instance()
    loaded_config = {}
    try:
        loaded_config = _config_module_to_dict(config_module)
        if not loaded_config: raise ValueError("Config module loaded as empty dictionary.")
        logger.info(f"Successfully loaded {len(loaded_config)} config items for standalone run.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to load config module: {e}", exc_info=True)
        return

    db = DatabaseClient(config_dict=loaded_config)

    try:
        await db.connect()
        await state.set_db_client(db)

        sol_price_initial = None
        if db.pool:
            sol_price_initial = await db.pool.fetchval("SELECT price FROM sol_price_usd ORDER BY timestamp DESC LIMIT 1")
        if sol_price_initial:
            await state.set_sol_price(float(sol_price_initial))
            logger.info(f"Pre-fetched initial SOL price: ${state.sol_price:.4f}")
        else:
            logger.warning("Could not pre-fetch SOL price from DB. Setting to 0.0.")
            await state.set_sol_price(0.0)

        ai = AIDecisionMaker(config=loaded_config, db_client=db)
        ai._set_log_verbose(True)

        current_data = await fetch_comprehensive_token_data(db, mint)
        
        # logger.info(f"--- Comprehensive Data Prepared for AI Prompt ({mint}) ---")
        # logger.info("\n" + json.dumps(current_data, indent=2, default=str))
        # logger.info(f"--- End Comprehensive Data ---")

        advice = await ai.get_trade_advice(current_data, include_explanation=include_explanation_in_output)

        logger.info(f"--- AI Advice Received for {mint} ---")
        logger.info(f"Decision:   {advice['decision']}")
        logger.info(f"Confidence: {advice['confidence']}")
        if include_explanation_in_output:
            explanation_lines = advice['explanation'].split('\n')
            indented_explanation = "\n".join(["  " + line for line in explanation_lines])
            logger.info(f"Explanation:\n{indented_explanation}")
        else:
            logger.info("Explanation: (Processing Skipped by flag)")
        logger.info(f"--- End AI Advice ---")

    except ValueError as ve:
        logger.error(f"Data fetching or processing error for {mint}: {ve}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main test function: {e}", exc_info=True)
    finally:
        if db and db.pool:
            await db.close()
            logger.info("Database connection closed.")
        logger.info(f"--- Finished AI Data Assembler Test for Mint: {mint} ---")


if __name__ == "__main__":
    """Main entry point (Unchanged)."""
    include_expl, mint_arg = True, None
    if len(sys.argv) < 2:
        print("Usage: python ai_decision_module/ai_data_assembler.py <token_mint> [--no-explanation]")
        sys.exit(1)
    mint_arg = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == '--no-explanation':
        include_expl = False
        print("[Standalone Mode] Running test without processing/logging the explanation.")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(mint_arg, include_explanation_in_output=include_expl))