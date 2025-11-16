## 📚 Project Context: `pump_trader_v2`

This project briefing contains the following key files:
- `ai_decision_module/__init__.py`
- `ai_decision_module/ai_data_assembler.py`
- `ai_decision_module/ai_decision_maker.py`
- `ai_decision_module/prompts/base.yaml`
- `ai_decision_module/prompts/buy.yaml`
- `ai_decision_module/prompts/rebuy.yaml`
- `ai_decision_module/prompts/sell.yaml`
- `bot_logger.py`
- `config/__init__.py`
- `config/config.py`
- `config/ga_config.py`
- `config/rl_config.py`
- `connectors/__init__.py`
- `connectors/dexscreener_api.py`
- `connectors/live_trader_gmgn.py`
- `connectors/live_trader_pumpportal.py`
- `connectors/rugcheck_handler.py`
- `connectors/sol_price_api.py`
- `connectors/telegram_monitor.py`
- `connectors/telegram_sentiment.py`
- `connectors/websocket_handler.py`
- `data/bot_command.txt`
- `database_handler.py`
- `ga_optimization_results/__GA-result-files__`
- `ga_optimizer_module/ga_backtester.py`
- `ga_optimizer_module/ga_dashboard.py`
- `ga_optimizer_module/ga_ingestion.py`
- `ga_optimizer_module/ga_optimizer.py`
- `ga_optimizer_module/ga_prepare_dataset.py`
- `generate_chart.py`
- `log/__log-files_`
- `main.py`
- `rl_agent_module/agents/__init__.py`
- `rl_agent_module/agents/ppo_agent.py`
- `rl_agent_module/data/__init__.py`
- `rl_agent_module/data/cache_manager.py`
- `rl_agent_module/data/data_manager.py`
- `rl_agent_module/data/inspect_cache.py`
- `rl_agent_module/environments/__init__.py`
- `rl_agent_module/environments/meme_coin_env.py`
- `rl_agent_module/etl/prepare_rl_dataset.py`
- `rl_agent_module/evaluation/__init__.py`
- `rl_agent_module/evaluation/evaluate.py`
- `rl_agent_module/evaluation/feature_importance.py`
- `rl_agent_module/feature_engineering/__init__.py`
- `rl_agent_module/feature_engineering/features.py`
- `rl_agent_module/inference/__init__.py`
- `rl_agent_module/inference/model_server.py`
- `rl_agent_module/mlflow_model.py`
- `rl_agent_module/rewards/__init__.py`
- `rl_agent_module/rewards/reward_function.py`
- `rl_agent_module/training/__init__.py`
- `rl_agent_module/training/train.py`
- `rl_agent_module/utils/hardware_advisor.py`
- `rl_agent_module/utils/mlflow_utils.py`
- `rl_agent_module/utils/script_utils.py`
- `rl_main.py`
- `socials_processor.py`
- `sql/01_create_tokens.sql`
- `sql/02_create_trades.sql`
- `sql/03_create_rugcheck.sql`
- `sql/04_create_portfolio.sql`
- `sql/05_create_migrations.sql`
- `sql/06_create_creator_wallets.sql`
- `sql/07_create_sol_price_usd.sql`
- `sql/08_create_bot_heartbeat.sql`
- `sql/09_create_configuration.sql`
- `sql/10_create_dexscreener_data.sql`
- `sql/11_create_completed_trades.sql`
- `sql/12_create_indexes.sql`
- `sql/13_create_views.sql`
- `sql/14_create_rl_tables.sql`
- `sql/15_create_social_scores.sql`
- `sql/16_create_ga_tables.sql`
- `sql/17_create_ai_decision_memory.sql`
- `sql/18_create_market_knowledge_base.sql`
- `state_manager.py`
- `telegram_interface.py`
- `trade_processor.py`
- `trading_bot.py`
- `trading_logic.py`
- `utils.py`



### 1. Project Structure

```
.
├── ai_decision_module/
│   ├── __init__.py
│   ├── ai_data_assembler.py
│   ├── ai_decision_maker.py
│   └── prompts/
│       ├── base.yaml
│       ├── buy.yaml
│       ├── rebuy.yaml
│       └── sell.yaml
├── bot_logger.py
├── config/
│   ├── __init__.py
│   ├── config.py
│   ├── ga_config.py
│   └── rl_config.py
├── connectors/
│   ├── __init__.py
│   ├── dexscreener_api.py
│   ├── live_trader_gmgn.py
│   ├── live_trader_pumpportal.py
│   ├── rugcheck_handler.py
│   ├── sol_price_api.py
│   ├── telegram_monitor.py
│   ├── telegram_sentiment.py
│   └── websocket_handler.py
├── data/
│   └── bot_command.txt
├── database_handler.py
├── ga_optimization_results/
│   └── __GA-result-files__
├── ga_optimizer_module/
│   ├── ga_backtester.py
│   ├── ga_dashboard.py
│   ├── ga_ingestion.py
│   ├── ga_optimizer.py
│   └── ga_prepare_dataset.py
├── generate_chart.py
├── log/
│   └── __log-files_
├── main.py
├── rl_agent_module/
│   ├── agents/
│   │   ├── __init__.py
│   │   └── ppo_agent.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── cache_manager.py
│   │   ├── data_manager.py
│   │   └── inspect_cache.py
│   ├── environments/
│   │   ├── __init__.py
│   │   └── meme_coin_env.py
│   ├── etl/
│   │   └── prepare_rl_dataset.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── evaluate.py
│   │   └── feature_importance.py
│   ├── feature_engineering/
│   │   ├── __init__.py
│   │   └── features.py
│   ├── inference/
│   │   ├── __init__.py
│   │   └── model_server.py
│   ├── mlflow_model.py
│   ├── rewards/
│   │   ├── __init__.py
│   │   └── reward_function.py
│   ├── training/
│   │   ├── __init__.py
│   │   └── train.py
│   └── utils/
│       ├── hardware_advisor.py
│       ├── mlflow_utils.py
│       └── script_utils.py
├── rl_main.py
├── socials_processor.py
├── sql/
│   ├── 01_create_tokens.sql
│   ├── 02_create_trades.sql
│   ├── 03_create_rugcheck.sql
│   ├── 04_create_portfolio.sql
│   ├── 05_create_migrations.sql
│   ├── 06_create_creator_wallets.sql
│   ├── 07_create_sol_price_usd.sql
│   ├── 08_create_bot_heartbeat.sql
│   ├── 09_create_configuration.sql
│   ├── 10_create_dexscreener_data.sql
│   ├── 11_create_completed_trades.sql
│   ├── 12_create_indexes.sql
│   ├── 13_create_views.sql
│   ├── 14_create_rl_tables.sql
│   ├── 15_create_social_scores.sql
│   ├── 16_create_ga_tables.sql
│   ├── 17_create_ai_decision_memory.sql
│   └── 18_create_market_knowledge_base.sql
├── state_manager.py
├── telegram_interface.py
├── trade_processor.py
├── trading_bot.py
├── trading_logic.py
└── utils.py
```

### 2. File Contents

#### 📄 `__init__.py`
*path: `ai_decision_module/__init__.py`*

_This file is empty._

#### 📄 `ai_data_assembler.py`
*path: `ai_decision_module/ai_data_assembler.py`*

```python
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
    [MODIFIED V3 - CORRECTED]
    Fetches and processes all necessary data for a given token mint.
    - Fixes logic to ensure creator history is fetched for BOTH active and backed-up tokens.
    - Computes time-to-peak, max price, and drawdown metrics.
    """
    logger.info(f"🧠 Fetching comprehensive data for token {mint}...")
    async with db.pool.acquire() as conn:
        # 1. Basic Token Info & Context
        token_info = await conn.fetchrow(
            "SELECT name, symbol, data_source, traderpublickey, timestamp, uri FROM tokens WHERE mint = $1", mint
        )
        
        creator_wallet = None
        
        if not token_info:
            # Token is not in the active 'tokens' table.
            backup_info = await conn.fetchrow(
                 "SELECT backup_reason, timestamp, traderPublicKey FROM tokens_backup WHERE mint = $1 LIMIT 1", mint
            )
            if backup_info:
                # This is the race condition. The token was just backed up.
                logger.warning(f"🧠 Token {mint} is no longer active (found in backup). Returning minimal outcome packet.")
                creator_wallet = backup_info['traderpublickey'] # Get creator from backup
                
                # --- [FIXED] Fetch creator summary for backup token ---
                creator_summary_string, creator_summary_dict = "N/A", {}
                if creator_wallet:
                     creator_summary_string, creator_summary_dict = await db.get_creator_history_summary(creator_wallet, mint)
                # --- [END FIX] ---

                return {
                    "status": "INACTIVE_BACKED_UP",
                    "mint": mint,
                    "backup_reason": backup_info['backup_reason'],
                    "backup_timestamp": backup_info['timestamp'],
                    "creator_history_summary": creator_summary_string,
                    **creator_summary_dict,
                    "decision_context": "NON_TRADE_OUTCOME"
                }
            else:
                # The token doesn't exist anywhere.
                logger.error(f"🧠 Token {mint} not found in 'tokens' or 'tokens_backup' table.")
                raise ValueError(f"Token {mint} not found in 'tokens' or 'tokens_backup' table.")

        # --- [FIXED] This block now runs for all ACTIVE tokens ---
        # If we are here, token_info is valid and from the active 'tokens' table.
        source, name, symbol, creator_wallet = token_info['data_source'], token_info['name'], token_info['symbol'], token_info['traderpublickey']
        token_creation_ts = ensure_datetime(token_info['timestamp'])
        uri = token_info['uri']
        token_age_minutes = (dt.datetime.now(dt.timezone.utc) - token_creation_ts).total_seconds() / 60 if token_creation_ts else None
        
        # Fetch creator summary for the active token
        creator_summary_string, creator_summary_dict = await db.get_creator_history_summary(creator_wallet, mint)
        
        uri_status = await check_uri_status(uri)
        # --- [END FIX] ---

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

        # 5. Fetch Market History (for recent dynamics)
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

        # --- [NEW BLOCK 5b: Fetch Full History for Peak/Drawdown Metrics] ---
        max_price_sol = None
        max_mcap_sol = None
        max_price_ts = None
        time_to_peak_minutes = None
        minutes_since_peak = None
        drawdown_from_peak_pct = 0.0

        peak_data = await conn.fetchrow(
            f"""SELECT
                   MAX(price_sol) as max_price_sol,
                   MAX(market_cap_sol) as max_mcap_sol,
                   (array_agg(timestamp ORDER BY price_sol DESC))[1] as max_price_ts
               FROM v_unified_market_ticks_historical
               WHERE mint = $1 AND price_sol > 0 AND market_cap_sol > 0
            """, mint
        )
        
        if peak_data and peak_data['max_price_sol'] and peak_data['max_price_ts'] and token_creation_ts:
            try:
                max_price_sol = float(peak_data['max_price_sol'])
                max_mcap_sol = float(peak_data['max_mcap_sol'])
                max_price_ts = ensure_datetime(peak_data['max_price_ts'])
                
                time_to_peak_minutes = (max_price_ts - token_creation_ts).total_seconds() / 60
                minutes_since_peak = (dt.datetime.now(dt.timezone.utc) - max_price_ts).total_seconds() / 60
                
                if current_price_sol and max_price_sol > 0:
                    drawdown_from_peak_pct = ((float(current_price_sol) / max_price_sol) - 1) * 100.0
                
            except Exception as e:
                logger.warning(f"🧠 Error calculating peak/drawdown metrics for {mint}: {e}", exc_info=True)
        # --- [END NEW BLOCK 5b] ---

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
            
            # --- [FIXED] This now correctly includes data for active tokens ---
            'creator_history_summary': creator_summary_string, # The summary string
            **creator_summary_dict, # Unpack structured data (creator_rug_rate, etc.)
            
            # Add new peak/drawdown metrics
            'max_price_sol': max_price_sol,
            'max_mcap_sol': max_mcap_sol,
            'max_price_ts': max_price_ts.isoformat() if max_price_ts else None,
            'time_to_peak_minutes': round(time_to_peak_minutes, 1) if time_to_peak_minutes is not None else None,
            'minutes_since_peak': round(minutes_since_peak, 1) if minutes_since_peak is not None else None,
            'drawdown_from_peak_pct': round(drawdown_from_peak_pct, 2),
            # --- [END FIX] ---
            
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
```

#### 📄 `ai_decision_maker.py`
*path: `ai_decision_module/ai_decision_maker.py`*

```python
# ai_decision_maker.py
import ollama
import asyncio 
from sentence_transformers import SentenceTransformer
from bot_logger import logger
import json
import re
import yaml
import os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from database_handler import DatabaseClient 

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')

class AIDecisionMaker:
    """
    [REFACTORED]
    Manages communication with an LLM (via Ollama) to get trading advice.
    Uses PostgreSQL (with pgvector) for RAG memory, and runs all blocking
    operations in a thread pool to be fully asynchronous.
    """
    
    EMBEDDING_DIM = 384
    # --- [NEW] ---
    # Define the confidence threshold for BUY/SELL actions
    CONFIDENCE_ACTION_THRESHOLD = 50 
    # --- [END NEW] ---

    def __init__(self, config: Dict[str, Any], db_client: DatabaseClient):
        """
        Initializes the AIDecisionMaker.
        """
        self.config = config
        self.db_client = db_client 
        self.model = self.config.get('AI_MODEL_NAME', 'llama3:latest')
        self.prompts_dir = self.config.get('_AI_PROMPTS_DIR', 'ai_decision_module/prompts')
        self.prompts = self._load_prompts()
        
        self.log_verbose = self.config.get('AI_LOG_VERBOSE', False)
        
        embedding_model_name = self.config.get('_AI_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

        try:
            self.embedder = SentenceTransformer(embedding_model_name)
            logger.info(f"🧠 Sentence Transformer embedding model '{embedding_model_name}' loaded.")
        except Exception as e:
            logger.critical(f"🧠 Failed to load Sentence Transformer model '{embedding_model_name}': {e}", exc_info=True)
            raise
        
        logger.info(f"🧠 AI Decision Maker initialized with Ollama model: {self.model} and pgvector backend.")

    def _load_prompts(self) -> Dict[str, Any]:
        """Loads prompt templates and configurations from YAML files with comment removal."""
        loaded_prompts = {}
        
        def remove_comments(content: str) -> str:
            """Remove comments from YAML content.
            
            Args:
                content: Raw YAML content as string
                
            Returns:
                YAML content with comments removed
            """
            lines = []
            for line in content.splitlines():
                line = line.split('#')[0]
                if line.strip():
                    lines.append(line)
            return '\n'.join(lines)
        
        try:
            base_path = os.path.join(self.prompts_dir, 'base.yaml')
            with open(base_path, 'r', encoding='utf-8') as f:
                content = remove_comments(f.read())
                base_config = yaml.safe_load(content)
                if not base_config: raise ValueError(f"{base_path} is empty or invalid")
                loaded_prompts['base'] = base_config

            for context_type in ['buy', 'sell', 'rebuy']: # <-- Add 'rebuy'
                specific_path = os.path.join(self.prompts_dir, f'{context_type}.yaml')
                if not os.path.exists(specific_path):
                    if context_type == 'rebuy':
                        logger.info(f"Optional prompt '{specific_path}' not found. Skipping.")
                        continue # It's okay if rebuy.yaml doesn't exist
                    else:
                         # Keep original error for required files
                         raise FileNotFoundError(f"{specific_path} is missing and required.")
                with open(specific_path, 'r', encoding='utf-8') as f:
                    content = remove_comments(f.read())
                    specific_config = yaml.safe_load(content)
                    if not specific_config: raise ValueError(f"{specific_path} is empty or invalid")
                    loaded_prompts[context_type] = {**base_config, **specific_config}

            logger.info(f"🧠 Successfully loaded prompt configurations from '{self.prompts_dir}'.")
            return loaded_prompts

        except FileNotFoundError as e:
            logger.critical(f"🧠 Prompt YAML file not found: {e}. Ensure '{self.prompts_dir}' contains base.yaml, buy.yaml, sell.yaml.", exc_info=True)
            raise
        except (yaml.YAMLError, Exception) as e:
            logger.critical(f"🧠 Error loading or parsing prompts: {e}", exc_info=True)
            raise

    def _set_log_verbose(self, verbose: bool):
        """Sets the verbosity of AI logging."""
        self.log_verbose = verbose
        logger.info(f"🧠 AI Decision Maker log verbosity set to: {self.log_verbose}")

    async def embed_text(self, text: str) -> Optional[list]:
        """
        [REFACTORED] Generates sentence embeddings for the given text asynchronously.
        Wraps the blocking SentenceTransformer call in asyncio.to_thread().
        """
        if not text:
            logger.warning("🧠 Attempted to embed empty text.")
            return None
        try:
            if self.log_verbose: logger.debug("🧠 AI Worker: Embedding text... (STARTING BLOCKING CALL)")
            embedding = await asyncio.to_thread(self.embedder.encode, text)
            if self.log_verbose: logger.debug("🧠 AI Worker: Embedding text... (BLOCKING CALL COMPLETE)")
            return embedding.tolist()
        except Exception as e:
            logger.error(f"🧠 Failed to embed text: '{text[:100]}...'. Error: {e}", exc_info=True)
            return None

    async def add_decision_snapshot_to_memory(self, snapshot_data: dict, decision_info: dict, raw_llm_response: Optional[str] = None):
        """
        [MODIFIED] Stores a snapshot of the market data, context, AI decision, and reasoning
        into the PostgreSQL `ai_decision_memory` table for future RAG retrieval.
        
        [NEW in this version] If 'raw_llm_response' is provided, it is minified
        to a one-line JSON string before being stored in the 'explanation' column.
        """
        mcap_usd = snapshot_data.get('market_cap', 0)
        volatility = snapshot_data.get('volatility', 0)
        rug_score = snapshot_data.get('rugcheck_latest', 'N/A')
        rug_trend = snapshot_data.get('rugcheck_trend', 'N/A')
        social_score = snapshot_data.get('social_latest', 'N/A')
        social_trend = snapshot_data.get('social_score_trend', 'N/A')
        token_age = snapshot_data.get('token_age_minutes', 'N/A')
        timestamp = snapshot_data.get('timestamp', datetime.now(timezone.utc).isoformat())
        mint = snapshot_data.get('mint', 'N/A')
        context = snapshot_data.get('decision_context', 'N/A')
        source = snapshot_data.get('source', 'N/A')
        
        # --- MODIFICATION START: Extract new fields ---
        creator_history = snapshot_data.get('creator_history_summary', 'N/A')
        max_price_sol = snapshot_data.get('max_price_sol', 'N/A')
        time_to_peak_minutes = snapshot_data.get('time_to_peak_minutes', 'N/A')
        drawdown_from_peak_pct = snapshot_data.get('drawdown_from_peak_pct', 'N/A')
        creator_rug_rate = snapshot_data.get('creator_rug_rate', 'N/A')

        uri_status = snapshot_data.get('uri_status', 'N/A')
        market_summary = snapshot_data.get('market_dynamics_summary_str', 'N/A')
        trade_history = snapshot_data.get('trade_history_summary', 'N/A')

        # --- [START OF REFACTOR] ---
        # The 'explanation' column in the DB will store the minified raw LLM JSON
        # or a simple text explanation for internal logs (like 'DODGED_BULLET').
        
        parsed_explanation = decision_info.get('explanation')
        full_response_to_store = None # Initialize
        explanation_snippet = "N/A"
        placeholder_explanations = ["Explanation not found or invalid format.", "No explanation processed."]

        if raw_llm_response:
            # This is the path for a direct LLM response. Minify it.
            try:
                # 1. Parse the (potentially) pretty-printed JSON string.
                parsed_json = json.loads(raw_llm_response)
                # 2. Re-dump it as a minified string (one-liner).
                full_response_to_store = json.dumps(parsed_json, separators=(',', ':'))
            except json.JSONDecodeError:
                # Fallback: If it's not valid JSON (e.g., an error message from query_llm), store it as-is.
                logger.warning(f"🧠 Could not re-parse raw_llm_response for minification. Storing as raw text. Response: {raw_llm_response[:100]}...")
                full_response_to_store = raw_llm_response
        else:
            # This is the path for internal "DODGED_BULLET" or "MISSED_OPPORTUNITY" logs.
            # In this case, 'parsed_explanation' is the simple text string.
            full_response_to_store = parsed_explanation
        # --- [END OF REFACTOR] ---

        # Use the *parsed* explanation for the snippet (this logic is unchanged)
        if parsed_explanation and parsed_explanation not in placeholder_explanations:
            explanation_snippet = parsed_explanation[:150] + ('...' if len(parsed_explanation) > 150 else '')
        elif raw_llm_response:
             # Fallback for snippet if parsing failed but we have a raw response
             # This snippet logic is fine, it doesn't need to be minified.
            explanation_snippet = raw_llm_response.split('---', 1)[-1].strip()[:150] + '...'
        
        if not full_response_to_store or full_response_to_store in placeholder_explanations:
            full_response_to_store = None # Ensure we store NULL if it's empty/placeholder
            
        # --- [START OF FIX] ---
        # Helper function to safely format numeric values that might be None or "N/A"
        def safe_format(val, format_spec):
            if val is None or isinstance(val, str):
                return "N/A"
            try:
                return f"{float(val):{format_spec}}"
            except (ValueError, TypeError):
                return "N/A"

        # Apply safe formatting
        mcap_usd_str = safe_format(mcap_usd, ",.0f")
        volatility_str = safe_format(volatility, ".3f")
        drawdown_str = safe_format(drawdown_from_peak_pct, ".1f")
        max_price_str = safe_format(max_price_sol, ".9f")
        ttp_str = safe_format(time_to_peak_minutes, ".1f")
        # --- [END OF FIX] ---

        # --- MODIFICATION START ---
        # Update situation_summary to use new creator history
        # --- [MODIFIED] Now includes the translated decision
        situation_summary = (
            f"Situation Snapshot at {timestamp} for {mint} ({context} context):\n"
            f"Source: {source}, MCap (USD): ${mcap_usd_str}, Volatility: {volatility_str}\n"
            f"Token Age: {token_age} mins, URI: {uri_status}\n"
            f"Creator History: {creator_history} (Rug Rate: {creator_rug_rate})\n"
            f"Peak/Drawdown: Peak at {max_price_str} SOL ({ttp_str} mins). Current Drawdown: {drawdown_str}%.\n"
            f"Rug Score: {rug_score} (Trend: {rug_trend})\n"
            f"Social Score: {social_score} (Trend: {social_trend})\n"
            f"Market Dynamics Summary: {market_summary}\n"
            f"Trade History: {trade_history}\n"
            f"AI Decision: {decision_info.get('decision', 'N/A')} (Confidence: {decision_info.get('confidence', 'N/A')})\n"
            f"Reasoning Snippet: {explanation_snippet}\n"
        )
        # --- MODIFICATION END ---
        
        embedding = await self.embed_text(situation_summary)
        if not embedding:
            logger.warning(f"🧠 Failed to create embedding for decision snapshot (Mint: {mint}). Skipping memory add.")
            return

        snapshot_time_str = timestamp if isinstance(timestamp, str) else datetime.now(timezone.utc).isoformat()
        
        # --- MODIFICATION START: Update metadata_to_store ---
        metadata_to_store = {
            "mint": mint, "timestamp": snapshot_time_str, "decision_context": context, "source": source,
            "market_cap": float(mcap_usd) if mcap_usd is not None and not np.isnan(mcap_usd) and not isinstance(mcap_usd, str) else None,
            "volatility": float(volatility) if volatility is not None and not np.isnan(volatility) and not isinstance(volatility, str) else None,
            "token_age_minutes": float(token_age) if token_age is not None and not np.isnan(token_age) and not isinstance(token_age, str) else None,
            "creator_history_summary": str(creator_history),
            "uri_status": str(uri_status),
            "rugcheck_score": str(rug_score), "social_score": str(social_score), "rugcheck_trend": str(rug_trend),
            "social_score_trend": str(social_trend),
            
            # Add decision info (which now includes new fields)
            **decision_info, # Unpack decision, confidence, expected_return_1h_pct, etc.
            
            "model_name": self.model,

            # Add new computed metrics from snapshot_data
            "max_price_sol": snapshot_data.get('max_price_sol'),
            "max_mcap_sol": snapshot_data.get('max_mcap_sol'),
            "max_price_ts": snapshot_data.get('max_price_ts'),
            "time_to_peak_minutes": snapshot_data.get('time_to_peak_minutes'),
            "minutes_since_peak": snapshot_data.get('minutes_since_peak'),
            "drawdown_from_peak_pct": snapshot_data.get('drawdown_from_peak_pct'),
            "creator_total_launches": snapshot_data.get('creator_total_launches'),
            "creator_rug_count": snapshot_data.get('creator_rug_count'),
            "creator_rug_rate": snapshot_data.get('creator_rug_rate'),
            "creator_good_runs_count": snapshot_data.get('creator_good_runs_count'),
            "creator_avg_lifespan_minutes": snapshot_data.get('creator_avg_lifespan_minutes')
        }
        
        metadata_to_store = {k: v for k, v in metadata_to_store.items() if v is not None}
        metadata_json = json.dumps(metadata_to_store)

        query = """
            INSERT INTO ai_decision_memory (
                mint, evaluation_timestamp, decision_context, decision, confidence,
                model_name, explanation, situation_summary, embedding, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            );
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                await conn.execute(
                    query,
                    mint, datetime.fromisoformat(snapshot_time_str), context,
                    decision_info.get('decision'), int(decision_info.get('confidence', 0)),
                    self.model,
                    full_response_to_store, # <-- This is now the minified JSON
                    situation_summary, 
                    str(embedding), 
                    metadata_json
                )
            if self.log_verbose: logger.debug(f"🧠 Added decision snapshot to pgvector memory for {mint}")
        except Exception as e:
            logger.error(f"🧠 Failed to add decision snapshot to pgvector (Mint: {mint}): {e}", exc_info=True)

    async def retrieve_context(self, current_data: dict, top_k_actions: int = 5, top_k_market: int = 8) -> dict:
        """
        [REFACTORED V3 - CORRECTED] Retrieves relevant past contexts from pgvector.
        - Queries 'ai_decision_memory' for past actions.
        - Queries 'market_knowledge_base' using METADATA FILTERS for comparable market examples.
        - Fixes a SQL ambiguity error by casting parameter $3 to text.
        
        Args:
            current_data: The full data dictionary for the current token (used for filtering).
            top_k_actions: K for past actions.
            top_k_market: K for market examples.

        Returns:
            A dictionary containing formatted context strings.
        """
        default_return = {
            "actions": "No relevant past actions found in memory.",
            "market_examples": "No relevant market examples found in memory."
        }
        
        # --- MODIFICATION: Build situation query from current_data dict ---
        situation_query = (
            f"Analyze similar Solana meme coin situations: Context={current_data.get('decision_context', 'N/A')}, "
            f"Source={current_data.get('source', 'N/A')}, MCap approx ${current_data.get('market_cap', 0):,.0f}, "
            f"Volatility level {current_data.get('volatility', 0):.3f}, Token Age: {current_data.get('token_age_minutes', 'N/A')} mins. "
            f"Creator Rug Rate: {current_data.get('creator_rug_rate', 'N/A')}. "
            f"Drawdown: {current_data.get('drawdown_from_peak_pct', 0.0):.1f}%. "
            f"RSI: {current_data.get('latest_rsi', 'N/A')}."
        )
        # --- END MODIFICATION ---

        if not situation_query:
            logger.warning("🧠 Retrieve context called with empty situation query.")
            return default_return

        query_embedding = await self.embed_text(situation_query)
        if not query_embedding:
            logger.warning("🧠 Failed to create embedding for RAG query. Cannot retrieve context.")
            return default_return

        # Query 1: The bot's own past actions (pure vector search)
        query_actions = """
            SELECT
                situation_summary, metadata, embedding <=> $1 AS distance
            FROM ai_decision_memory
            ORDER BY embedding <=> $1
            LIMIT $2;
        """
        
        # --- [START OF FIX] ---
        # --- MODIFICATION: New Market Query with Metadata Filters ---
        query_market = """
            SELECT
                summary, metadata, embedding <=> $1 AS distance
            FROM market_knowledge_base
            WHERE
              -- Filter 1: Match the data source (PUMP or DEXSCREENER)
              -- [FIX] Cast $3 to text to resolve ambiguity when it is NULL
              ($3::text IS NULL OR (metadata->>'source') = $3::text)
              -- Filter 2: Match a market cap band (e.g., 0.5x to 2.0x current)
              AND ( (metadata->>'max_mcap_usd')::float BETWEEN $4 AND $5 )
            ORDER BY embedding <=> $1
            LIMIT $2;
        """
        # --- [END OF FIX] ---
        
        # Prepare filter parameters
        source_filter = current_data.get('source')
        current_mcap = current_data.get('market_cap', 0.0)
        # Define mcap bands (e.g., 0-10k, 10k-50k, 50k-250k, 250k+)
        if current_mcap < 10000:
            min_mcap, max_mcap = 0.0, 10000.0
        elif current_mcap < 50000:
            min_mcap, max_mcap = 10000.0, 50000.0
        elif current_mcap < 250000:
            min_mcap, max_mcap = 50000.0, 250000.0
        else:
            min_mcap, max_mcap = 250000.0, float('inf')

        try:
            results_actions, results_market = await asyncio.gather(
                self.db_client.pool.fetch(query_actions, str(query_embedding), top_k_actions),
                # Pass new filter params to the market query
                self.db_client.pool.fetch(query_market, str(query_embedding), top_k_market, source_filter, min_mcap, max_mcap)
            )

            # --- Process Past Actions (Unchanged) ---
            if not results_actions:
                if self.log_verbose: logger.debug("🧠 No relevant past actions found in 'ai_decision_memory'.")
            else:
                context_parts = ["--- Relevant Past Situations (Your Actions) ---"]
                for i, record in enumerate(results_actions):
                    context_parts.append(f"Past Case {i+1} (Similarity Distance: {record['distance']:.4f}):")
                    context_parts.append(record['situation_summary'].strip()) 
                    metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                    if metadata:
                        mcap_display = f"${metadata.get('market_cap', 0):,.0f}" if metadata.get('market_cap') else "N/A"
                        context_parts.append(
                            f"  (Metadata: Decision={metadata.get('decision', '?')}, "
                            f"Conf={metadata.get('confidence', '?')}, Context={metadata.get('decision_context', '?')}, "
                            f"MCap={mcap_display})"
                        )
                    context_parts.append("---")
                default_return["actions"] = "\n".join(context_parts)


            # --- Process Market Examples (Unchanged, but benefits from better query) ---
            if not results_market:
                if self.log_verbose: logger.debug(f"🧠 No relevant market examples found in 'market_knowledge_base' (with filters).")
            else:
                context_parts = ["--- Relevant Market Examples (Other Tokens) ---"]
                for i, record in enumerate(results_market):
                    context_parts.append(f"Market Example {i+1} (Similarity Distance: {record['distance']:.4f}):")
                    context_parts.append(record['summary'].strip()) 
                    metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                    if metadata:
                        context_parts.append(
                            f"  (Metadata: Outcome={metadata.get('reason', '?')}, "
                            f"Creator={metadata.get('creator', '?')}, "
                            f"MaxMCap={metadata.get('max_mcap', 'N/A')} SOL)"
                        )
                    context_parts.append("---")
                default_return["market_examples"] = "\n".join(context_parts)
            
            return default_return

        except Exception as e:
            logger.error(f"🧠 Error querying pgvector for RAG context: {e}", exc_info=True)
            return {
                "actions": "Error retrieving past actions from memory.",
                "market_examples": "Error retrieving market examples from memory."
            }

    async def query_llm(self, prompt: str) -> str:
        """
        [REFACTORED] Sends the fully formatted prompt to the Ollama LLM asynchronously
        by wrapping the blocking 'ollama.chat' call in asyncio.to_thread().
        """
        if self.log_verbose: logger.debug(f"🧠 Sending prompt to LLM '{self.model}' (approx {len(prompt)} chars)")

        try:
            if self.log_verbose: 
                logger.debug("🧠 AI Worker: Querying LLM... (STARTING BLOCKING CALL)")
                #logger.debug(f"🧠 LLM Prompt Preview:\n{prompt[:11000]}{'...' if len(prompt) > 11000 else ''}")
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                options={'temperature': 0.3},
                messages=[{'role': 'user', 'content': prompt}],
                format="json"  # <-- ENFORCE JSON OUTPUT
            )
            if self.log_verbose: logger.debug("🧠 AI Worker: Querying LLM... (BLOCKING CALL COMPLETE)")
            
            # The result is now a JSON string
            result = response['message']['content'].strip()
            
            if self.log_verbose:
                log_result_snippet = result[:11000] + ('...' if len(result) > 11000 else '')
                logger.debug(f"🧠 LLM JSON Response received:\n{log_result_snippet}")
            return result

        except Exception as e:
            logger.error(f"🧠 Ollama query failed using model '{self.model}': {e}", exc_info=True)
            # Return a fallback JSON error string
            # --- [MODIFIED] Removed "decision" key from this fallback ---
            return json.dumps({
                "confidence": 0,
                "expected_return_1h_pct": 0.0,
                "expected_return_6h_pct": 0.0,
                "suggested_size_pct": 0.0,
                "primary_risk": "INTERNAL_ERROR",
                "explanation": f"AI decision unavailable due to LLM query error: {e}"
            })

    async def get_trade_advice(self, current_data: dict, include_explanation: bool = True) -> dict:
        """
        [REFACTORED V8 - CONTEXT-AWARE PARSING]
        Orchestrates the process of getting trade advice from the LLM.
        - Passes current_data to retrieve_context for filtered RAG.
        - Parses the new, confidence-only JSON response.
        - **[NEW]** Passes `decision_context` to the parser so it can
          translate `confidence` back into a `decision` string.
        - [FIX] Sanitizes prompt_data to handle None values before formatting.
        """
        required_keys = ['mint', 'source', 'price', 'market_cap', 'volatility', 'decision_context', 'token_age_minutes']
        missing_keys = [k for k in required_keys if k not in current_data or current_data[k] is None]
        if missing_keys:
             logger.error(f"🧠 Missing essential keys for AI advice: {missing_keys}. Input data: {list(current_data.keys())}")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Incomplete essential data: Missing {missing_keys}"}

        # --- 1. Determine Context and Load Prompt Snippets ---
        decision_context = current_data['decision_context']

        if decision_context == "INITIAL BUY":
            context_key = 'buy'
        elif decision_context == "REBUY":
            context_key = 'rebuy'
        elif decision_context == "SELL/HOLD":
            context_key = 'sell'
        else:
            logger.warning(f"🧠 Unknown decision context '{decision_context}'. Defaulting to SELL/HOLD logic.")
            context_key = 'sell'
            decision_context = "SELL/HOLD" # Normalize

        if context_key == 'rebuy' and 'rebuy' not in self.prompts:
            logger.warning("🧠 'rebuy.yaml' not loaded. Falling back to 'buy.yaml' for REBUY context.")
            context_key = 'buy'
            
        prompt_config = self.prompts.get(context_key, self.prompts['sell']) # Fallback to 'sell'
        base_prompts = self.prompts.get('base')
        if not base_prompts:
            logger.critical("🧠 CRITICAL: 'base.yaml' prompt snippets not found. Cannot build prompt.")
            return {"decision": "HOLD", "confidence": 0, "explanation": "Internal Error: Base prompts missing."}

        # --- 2. Generate RAG Context ---
        if self.log_verbose: logger.debug(f"🧠 Generating RAG context for {current_data['mint']}...")
        rag_context = await self.retrieve_context(current_data) # Pass the full dict

        # --- 3. Format Dynamic Data Blocks ---
        market_dynamics_formatted = "Market dynamics data not available or source unknown."
        source = current_data['source']
        try:
            if source == 'PUMP':
                market_dynamics_formatted = prompt_config['market_dynamics_template_pump'].format(**current_data)
            elif source == 'DEXSCREENER':
                market_dynamics_formatted = prompt_config['market_dynamics_template_dex'].format(**current_data)
        except KeyError as e:
            logger.error(f"🧠 KeyError formatting market dynamics for {source}: Missing key '{e}'.")
            market_dynamics_formatted = f"Error formatting market dynamics for {source} (KeyError: {e})."
        
        # --- 4. Assemble Full Prompt Data ---
        prompt_data = {**current_data} 
        prompt_data.update({
            'rag_context_actions': rag_context['actions'],
            'rag_context_market': rag_context['market_examples'],
            'market_dynamics_formatted': market_dynamics_formatted,
            'source_explanation': prompt_config.get('source_explanation', ''),
            'market_cap_guidance': prompt_config.get('market_cap_guidance', '').format(
                default_marketcap_threshold=self.config.get('DEFAULT_MARKETCAP_THRESHOLD', 14000),
                min_marketcap_threshold=self.config.get('MIN_MARKETCAP_THRESHOLD', 4000)
            ),
            'context_specific_rules': prompt_config.get('context_specific_rules', ''),
            'default_marketcap_threshold': self.config.get('DEFAULT_MARKETCAP_THRESHOLD', 14000),
            'min_marketcap_threshold': self.config.get('MIN_MARKETCAP_THRESHOLD', 4000),
        })

        # --- [START OF FIX] ---
        # 4b. Sanitize None values that require numeric formatting in the prompt
        # We replace None with 0.0 or "N/A" depending on what the prompt expects.
        # For numeric formats (like :.9f), we MUST use a number (0.0).
        # For string formats, "N/A" is fine.
        
        # Keys that are formatted as numbers (e.g., :.9f, :.1f, :.2f)
        numeric_format_keys = [
            'price', 'market_cap', 'volatility', 'max_price_sol', 
            'time_to_peak_minutes', 'minutes_since_peak', 'drawdown_from_peak_pct',
            'dex_price_change_m5', 'dex_volume_m5'
        ]
        # Keys that are formatted as strings or integers (e.g., {})
        string_format_keys = [
            'latest_rsi', 'latest_ema_fast', 'latest_ema_slow',
            'token_age_minutes', # This one is formatted as {token_age_minutes}
            'pump_price_change_1m', 'pump_volume_velocity_1m', 'pump_tick_frequency_1m',
            'dex_buys_m5', 'dex_sells_m5', 'dex_price_trend_15m', 
            'dex_volume_trend_15m', 'dex_liquidity_trend_30m'
        ]

        for key in numeric_format_keys:
            if prompt_data.get(key) is None:
                prompt_data[key] = 0.0 # Use 0.0 for numeric formatting

        for key in string_format_keys:
            if prompt_data.get(key) is None:
                prompt_data[key] = "N/A" # Use "N/A" for string formatting

        # Ensure creator_history_summary is at least an empty string
        if prompt_data.get('creator_history_summary') is None:
            prompt_data['creator_history_summary'] = "N/A"
            
        # Ensure data completeness notes are present
        if prompt_data.get('data_completeness_notes') is None:
            prompt_data['data_completeness_notes'] = "N/A"

        # --- 5. Dynamically Build the Final Prompt (Context -> Data -> Rules -> JSON Format) ---
        try:
            prompt_sections = []
            
            # 1. Task Definition (from buy.yaml, etc.)
            prompt_sections.append(prompt_config['task_definition'].format(**prompt_data))
            
            # 2. Data Blocks (from base.yaml)
            prompt_sections.append(base_prompts['current_token_data_header'].format(**prompt_data))
            prompt_sections.append(base_prompts['metadata_context_section'].format(**prompt_data))
            
            # This section now contains the new peak/drawdown metrics
            prompt_sections.append(base_prompts['core_metrics_section'].format(**prompt_data)) 
            
            prompt_sections.append(base_prompts['risk_assessment_section'].format(**prompt_data))
            prompt_sections.append(base_prompts['market_dynamics_header'].format(**prompt_data))
            prompt_sections.append(base_prompts['trade_history_section'].format(**prompt_data))
            
            # 3. Rules & RAG Context (from base.yaml)
            prompt_sections.append(base_prompts['key_decision_rules_section'].format(**prompt_data))
            
            # 4. FINAL INSTRUCTION: The JSON format (from base.yaml)
            prompt_sections.append(base_prompts['json_output_format'].format(**prompt_data))
            
            final_prompt = "\n\n".join(prompt_sections)
            
            if self.log_verbose:
                logger.debug(f"🧠 Final dynamic prompt for {current_data['mint']}:\n{final_prompt}")
                
        except (KeyError, TypeError) as e: # Catch TypeError as well
             logger.critical(f"🧠 CRITICAL: Missing key or Type error '{e}' during prompt final formatting.")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed on key/type '{e}'."}
        except Exception as e:
             logger.critical(f"🧠 CRITICAL: Unexpected error during prompt final formatting: {e}", exc_info=True)
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed unexpectedly."}

        # --- 6. Query LLM and Process Response ---
        llm_response_string = await self.query_llm(final_prompt) # This is now a JSON string

        if self.log_verbose:
            logger.debug(f"🧠 LLM Raw JSON Response for {current_data['mint']} ({decision_context}): {llm_response_string}")

        # --- [MODIFIED] ---
        # Pass the decision_context to the parser so it can translate the confidence score
        parsed_decision_rich = self._parse_llm_json_response(
            llm_response_string, 
            decision_context, # <-- Pass the context
            include_explanation
        )
        # --- [END MODIFIED] ---

        if self.log_verbose:
            log_explanation_snippet = parsed_decision_rich['explanation'][:200] + ('...' if len(parsed_decision_rich['explanation']) > 200 else '') if include_explanation and parsed_decision_rich.get('explanation') else "(Explanation Skipped or Missing)"
            logger.debug(f"🧠 AI Advice for {current_data['mint']} ({decision_context}): {parsed_decision_rich['decision']} "
                        f"(Confidence: {parsed_decision_rich['confidence']}) - Risk: {parsed_decision_rich.get('primary_risk', 'N/A')} "
                        f"- Return(1h): {parsed_decision_rich.get('expected_return_1h_pct', 'N/A')}%")

        # Save the new decision (and its rich explanation) to RAG memory
        # We pass the full current_data (with all computed metrics)
        # and the full parsed_decision_rich (with all LLM outputs)
        await self.add_decision_snapshot_to_memory(current_data, parsed_decision_rich, raw_llm_response=llm_response_string)

        return parsed_decision_rich

    # --- [MODIFIED] ---
    def _parse_llm_json_response(self, llm_response_string: str, decision_context: str, parse_explanation: bool = True) -> dict:
        """
        [MODIFIED V2]
        Parses the confidence-only JSON response from the LLM.
        Translates the `confidence` score into a `decision` string based on the
        `decision_context` and the `CONFIDENCE_ACTION_THRESHOLD`.
        """
        
        # Map for string-based confidence values to integers
        CONFIDENCE_STRING_MAP = {
            "very low": 10,
            "low": 25,
            "moderate": 50,
            "medium": 50,
            "average": 50,
            "reasonable": 60,
            "good": 75,
            "strong": 85,
            "high": 90,
            "very high": 95,
            "extreme": 100,
            "certain": 100,
            "none": 0,
            "zero": 0,
        }

        default_reasoning = "Explanation not found or invalid JSON format."
        # --- [MODIFIED] Default output now includes a 'decision' key
        default_output = {
            "decision": "HOLD", # Default action is always HOLD
            "confidence": 0, 
            "expected_return_1h_pct": 0.0,
            "expected_return_6h_pct": 0.0,
            "suggested_size_pct": 0.0,
            "primary_risk": "UNKNOWN",
            "explanation": "No explanation processed." if not parse_explanation else default_reasoning
        }

        try:
            # --- FIX: Replaced re.sub with simple string methods ---
            llm_response_string = llm_response_string.strip()
            if llm_response_string.startswith("```json"):
                llm_response_string = llm_response_string[7:]
            if llm_response_string.endswith("```"):
                llm_response_string = llm_response_string[:-3]
            llm_response_string = llm_response_string.strip()
            # --- END FIX ---

            data = json.loads(llm_response_string)
            if not isinstance(data, dict):
                raise TypeError("LLM returned valid JSON, but it was not a dictionary.")

            # --- [ NEW SCHEMA PARSING ] ---
            # 'decision' key is NO LONGER expected from the LLM
            
            # --- [ MODIFIED CONFIDENCE PARSING ] ---
            raw_confidence = data.get("confidence")
            confidence = 0 # Default

            if isinstance(raw_confidence, int):
                confidence = raw_confidence
            elif isinstance(raw_confidence, float):
                confidence = int(raw_confidence)
            elif isinstance(raw_confidence, str):
                confidence_str_low = raw_confidence.strip().lower()
                if confidence_str_low in CONFIDENCE_STRING_MAP:
                    confidence = CONFIDENCE_STRING_MAP[confidence_str_low]
                    logger.debug(f"🧠 Parser: Mapped confidence string '{raw_confidence}' to {confidence}.")
                else:
                    try:
                        # Try to cast string-as-number (e.g., "80")
                        confidence = int(float(confidence_str_low.strip('% '))) # Handle "80", "80.0", "80%", " 80 "
                    except (ValueError, TypeError):
                        logger.warning(f"🧠 Parser: Could not parse string confidence '{raw_confidence}'. Defaulting to 0.")
                        confidence = 0
            elif raw_confidence is None:
                 logger.warning(f"🧠 Parser: Confidence was 'null' in JSON response. Defaulting to 0.")
                 confidence = 0
            else:
                 logger.warning(f"🧠 Parser: Confidence was of an unexpected type '{type(raw_confidence)}'. Defaulting to 0.")
                 confidence = 0
            # --- [ END MODIFIED CONFIDENCE PARSING ] ---

            explanation = default_reasoning
            if parse_explanation:
                # Use the new 'explanation' key
                reasoning_str = data.get("explanation") # <-- KEY CHANGED
                if reasoning_str and isinstance(reasoning_str, str):
                    explanation = reasoning_str
                # Fallback for old key, just in case
                elif data.get("full_reasoning") and isinstance(data.get("full_reasoning"), str):
                    explanation = data.get("full_reasoning")
            
            # --- MODIFICATION: Parse new fields ---
            def parse_numeric_field(key: str, default_val: float = 0.0) -> float:
                val = data.get(key)
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    try:
                        return float(val.strip('% '))
                    except (ValueError, TypeError):
                        return default_val
                return default_val

            expected_return_1h_pct = parse_numeric_field("expected_return_1h_pct")
            expected_return_6h_pct = parse_numeric_field("expected_return_6h_pct")
            suggested_size_pct = parse_numeric_field("suggested_size_pct")
            
            primary_risk = str(data.get("primary_risk", "UNKNOWN")).upper()
            # --- END MODIFICATION ---

            # --- [NEW] TRANSLATION LOGIC ---
            # Translate the confidence score back into a decision string
            decision = "HOLD" # Default
            if decision_context in ["INITIAL BUY", "REBUY"]:
                if confidence >= self.CONFIDENCE_ACTION_THRESHOLD:
                    decision = "BUY"
                else:
                    decision = "HOLD"
            elif decision_context == "SELL/HOLD":
                if confidence >= self.CONFIDENCE_ACTION_THRESHOLD:
                    decision = "SELL"
                else:
                    decision = "HOLD"
            # --- [END NEW] ---

            # --- MODIFICATION: Return new rich dictionary ---
            return {
                "decision": decision, # The *translated* decision
                "confidence": confidence, # The *raw* confidence from the LLM
                "expected_return_1h_pct": expected_return_1h_pct,
                "expected_return_6h_pct": expected_return_6h_pct,
                "suggested_size_pct": max(0, min(100, suggested_size_pct)), # Clamp 0-100
                "primary_risk": primary_risk,
                "explanation": explanation
            }
            # --- END MODIFICATION ---

        except json.JSONDecodeError as e:
            logger.error(f"🧠 Parser: Failed to decode LLM JSON response. Error: {e}. Response: {llm_response_string[:500]}...")
            return default_output
        except (TypeError, ValueError) as e:
            logger.error(f"🧠 Parser: Error parsing fields from LLM JSON. Error: {e}. Data: {llm_response_string[:500]}...")
            return default_output
    
    # --- [DELETED] ---
    # The old _parse_llm_response_structured and _parse_llm_response_fallback
    # functions have been removed as they are no longer used by get_trade_advice.
    # --- [END DELETED] ---
```

#### 📄 `base.yaml`
*path: `ai_decision_module/prompts/base.yaml`*

```yaml
# Prompts - Base Template (FINETUNED V9 - Forceful Data Re-injection)
# This file contains REUSABLE SNIPPETS for the dynamic prompt builder.

# --- 1. CURRENT TOKEN DATA (Data-First Structure) ---
current_token_data_header: |
  **Current Token Data ({name} - {mint}):**

metadata_context_section: |
  **Metadata & Context:**
  - Token Age: {token_age_minutes} minutes
  - Creator History: {creator_history_summary}
  - Metadata URI Status: {uri_status}

core_metrics_section: |
  **Core Metrics:**
  - Price (SOL): {price:.9f}
  - Market Cap (USD): ${market_cap:,.0f}
  - Volatility (Recent): {volatility:.3f}
  - TA (5s Candle): RSI: {latest_rsi} | EMA Fast: {latest_ema_fast} | EMA Slow: {latest_ema_slow}
  
  **Peak & Drawdown Metrics:**
  - Peak Price (SOL): {max_price_sol:.9f} (at {time_to_peak_minutes:.1f} mins)
  - Time Since Peak: {minutes_since_peak:.1f} mins
  - Drawdown from Peak: {drawdown_from_peak_pct:.2f}%

risk_assessment_section: |
  **Risk Assessment:**
  - Rugcheck: Latest: {rugcheck_latest}, Initial: {rugcheck_initial}, Trend(1h): {rugcheck_trend}
  - Social Score: Latest: {social_latest}, Initial: {social_initial}, Trend(1h): {social_score_trend}
  - Telegram Stats: {latest_telegram_members} members ({latest_telegram_online} online)
  - TG Trends(1h): Members: {telegram_members_trend}, Online Ratio: {telegram_online_ratio_trend}

market_dynamics_header: |
  **Market Dynamics (Source: {source}):**
  {market_dynamics_formatted} # Placeholder filled dynamically

# --- 2. TRADE HISTORY ---
trade_history_section: |
  **Past Trade History Summary:**
  {trade_history_summary}

# --- 3. DECISION RULES (MODIFIED: Graded Penalties) ---
key_decision_rules_section: |
  **Key Decision Rules & Interpretation Guide:**
  - **Data Source:** Interpret '{source}' data correctly ({source_explanation}).
  
  - **CRITICAL VETO SIGNALS (Graded Risk):**
    - **Creator History (CRITICAL):**
      - If `creator_history_summary` is "This is the creator's first token.", the `creator_rug_rate` is 0. This is NEUTRAL, not negative.
      - If `creator_rug_rate` > 0.5, this is a **MAJOR VETO SIGNAL**.
      - **You MUST NOT** confuse a new creator with a bad creator. Prioritize the `Creator History:` data block over RAG context for this specific metric.
    - **Dead Token (N/A):** If Market Dynamics are 'N/A' or volatility is 0.000, it means **ZERO activity**. This is a **MAJOR VETO SIGNAL (set confidence to 0 for buys)**. For SELL/HOLD, this is a strong **SELL** signal (set confidence to 100).
    - **Temporal Risk:** If creator_avg_time_to_rug_minutes is known (e.g., 30 mins) and token_age_minutes is close to that (e.g., 28 mins), the risk is **EXTREME**.

  - **Risk Scores (Lower is Better):**
      - **Rugcheck Score:** Scale: <50 (Low), <600 (Moderate), 900+ (Very High).
      - **Social Score (0-100):** Scale: <10 (Excellent), <30 (Good), <50 (Moderate), 70+ (Very Poor).
  
  - **Market Cap (USD):** {market_cap_guidance}
  - **URI Status:** 'Missing', 'Invalid Format', or 'Error' is a strong negative signal, apply a high risk penalty.
  {context_specific_rules}

  - **CRITICAL - RAG CONTEXT WARNING (READ THIS):**
    - The past situations below are for *context only*.
    - **DO NOT** copy the `explanation` or `primary_risk` from a past case.
    - **YOUR PRIMARY TASK** is to analyze the **Current Token Data** block above.
    - **FAILURE MODE TO AVOID:** If the `Creator History:` line above says "This is the creator's first token.", you MUST treat this as a **NEUTRAL** signal. DO NOT look at a RAG example of a bad creator and copy its risk. You MUST base your `primary_risk` and `explanation` on the *current token's* data.
    
  --- Relevant Past Situations (Your Actions) ---
  {rag_context_actions}

  --- Relevant Market Examples (Other Tokens) ---
  {rag_context_market}
  
  **Overall Market Context:** The current Solana market regime is **{market_regime}**.
  - In 'BULLISH' regimes, you can be more tolerant of risk for high momentum.
  - In 'BEARISH' regimes, you must be extremely risk-averse and prioritize capital preservation.

# --- 4. NEW: JSON OUTPUT FORMAT (Confidence-Only Decision) ---
json_output_format: |
  **CRITICAL DATA RECAP (USE THIS DATA, NOT RAG EXAMPLES):**
  - **Current Creator History:** {creator_history_summary}
  - **Current Creator Rug Rate:** {creator_rug_rate}
  - **Current Data Completeness:** {data_completeness_score}% - {data_completeness_notes}

  **CRITICAL: YOUR TASK IS TO RETURN A VALID JSON OBJECT.**
  - Your *entire* response must be a single JSON object.
  - **DO NOT** include any text, titles, markdown (like `###`), or explanations before or after the JSON.
  - Perform a step-by-step analysis *internally* using the 7 steps below.
  - **Compute a utility score:** utility = (expected_return_1h_pct * (confidence/100)) - (risk_penalty_score).
  - Risk Penalty: Start at 0. Add +40 if creator_rug_rate > 0.5. Add +30 if social_score > 60. Add +30 if rugcheck_score > 800. Add +20 if drawdown_from_peak_pct < -50%.
  - **Base your `confidence` score on this utility score, scaled to the context.**
  - **Context 'BUY'/'REBUY'**: 0 = No Buy, 100 = Strong Buy.
  - **Context 'SELL'**: 0 = Hold, 100 = Strong Sell.

  **Internal Reasoning Steps (Do not include these steps in the final output):**
  1.  **Analyze Creator History (CRITICAL FIRST STEP):**
      - Look *only* at the **CRITICAL DATA RECAP** block directly above this.
      - **If `Current Creator History` is "This is the creator's first token."**: This is a **NEUTRAL** signal. `primary_risk` MUST NOT be 'CREATOR_HISTORY'.
      - **If `Current Creator Rug Rate` > 0.5**: This is a **MAJOR VETO SIGNAL**. `primary_risk` MUST be 'CREATOR_HISTORY'.
      - **DO NOT** copy explanations from RAG examples. Your explanation MUST reflect the *actual* data from the **CRITICAL DATA RECAP**.
  2.  **VETO Check (Other)**: Check for Dead Token (Market Dynamics 'N/A' or volatility 0.000), Bad URI. Apply VETO if found.
  3.  **Risk Analysis**: Evaluate *other* scores (rug, social) to compute `risk_penalty_score`. Add the creator risk penalty *only if* step 1 determined it was bad (e.g. Rug Rate > 0.5).
  4.  **Momentum Analysis**: Evaluate market dynamics, RSI, and drawdown to estimate `expected_return_1h_pct`.
  5.  **RAG Synthesis**: Compare to past cases. Do they support the momentum or the risk? (Remember Step 1's warning!).
  6.  **Utility Calculation**: Compute the utility score based on your estimates.
  7.  **Data Quality**: Check completeness using the **CRITICAL DATA RECAP** block.
  8.  **Final Synthesis**: Formulate the final `confidence` score and `explanation` based on the utility score, the *actual* creator history, and the current context.

  **REQUIRED JSON OUTPUT SCHEMA:**
  Make 100% sure your output matches this schema exactly:
  {{
    "confidence": "integer [0-100]",
    "expected_return_1h_pct": "number (Your numeric estimate, e.g., 50.5 or -10.0)",
    "expected_return_6h_pct": "number (Your numeric estimate)",
    "suggested_size_pct": "number (e.g., 25 for 25% of allocated capital, 0 for HOLD/SELL)",
    "primary_risk": "string (One of: 'CREATOR_HISTORY', 'LOW_LIQUIDITY', 'RAPID_DECAY', 'POOR_SOCIALS', 'RUG_SIGNALS', 'NONE')",
    "explanation": "string (A concise, one-paragraph summary of your final synthesis, justifying the confidence score and utility calculation.)"
  }}
```

#### 📄 `buy.yaml`
*path: `ai_decision_module/prompts/buy.yaml`*

```yaml
# Prompts - BUY/REBUY Context Configuration (FINETUNED V6 - Confidence-Only)

# --- TASK DEFINITION ---
task_definition: |
  You are an expert Solana meme coin trading analyst AI. Your goal is to evaluate an **ENTRY POINT** for a trading bot.
  **Current Decision Context:** {decision_context}
  Your output `confidence` score [0-100] will determine the action: 0 means DO NOT BUY, 100 means STRONG BUY.
  
  Based on the **Current Token Data** and **Key Decision Rules** provided below, perform a step-by-step analysis.
  
  **YOUR FINAL TASK:** Return a single JSON object with your analysis. Do not add any other text or explanation outside of the JSON object.

# --- CONTEXT-SPECIFIC RULES ---
context_specific_rules: |
  - **Creator History / URI:** A poor creator history (e.g., many rugs) is a **MAJOR VETO SIGNAL. You MUST set confidence to 0.** An 'Error'/'Missing' URI is also a strong VETO signal.
  - **Market Activity:** If Market Dynamics are 'N/A' or volatility is 0.000, it means **ZERO activity**. This is a **MAJOR VETO SIGNAL. You MUST set confidence to 0.**
  - **Rebuy Context:** If this is a `REBUY`, your signals for `BUY` must be *stronger* than an initial buy. The reason for the previous exit (in trade history) must be resolved.

# --- DATA FORMATTING TEMPLATES (Unchanged) ---
source_explanation: "PUMP = High-frequency individual trades on a new, unmigrated token. DEXSCREENER = Periodic aggregate snapshots on a token that has successfully migrated to a standard DEX (e.g., Raydium). A 'DEXSCREENER' source is a positive signal, as it means the token was not an immediate rug-pull and achieved a liquidity pool."
market_cap_guidance: "Avoid buys below ${default_marketcap_threshold:,.0f} unless other signals are exceptionally strong. Very low MC indicates high risk."

market_dynamics_template_pump: |
  - Price Change (1min): {pump_price_change_1m}
  - Volume Velocity (1min): {pump_volume_velocity_1m}
  - Tick Frequency (1min): {pump_tick_frequency_1m} trades/min

market_dynamics_template_dex: |
  - Price Change (5min snap): {dex_price_change_m5:.2f}%
  - Volume (5min snap): ${dex_volume_m5:,.0f}
  - Buys/Sells (5min snap): {dex_buys_m5} / {dex_sells_m5}
  - Price Trend (15min): {dex_price_trend_15m}
  - Volume Trend (15min): {dex_volume_trend_15m}
  - Liquidity Trend (30min): {dex_liquidity_trend_30m}
```

#### 📄 `rebuy.yaml`
*path: `ai_decision_module/prompts/rebuy.yaml`*

```yaml
# Prompts - REBUY Context Configuration (FINETUNED V6 - Confidence-Only)

# --- TASK DEFINITION ---
task_definition: |
  You are an expert Solana meme coin trading analyst AI. Your goal is to evaluate a **RE-ENTRY POINT** for a trading bot.
  **Current Decision Context:** {decision_context}
  Your output `confidence` score [0-100] will determine the action: 0 means DO NOT BUY, 100 means STRONG BUY.
  
  Based on the **Current Token Data** and **Key Decision Rules** provided below, perform a step-by-step analysis.
  
  **YOUR FINAL TASK:** Return a single JSON object with your analysis. Do not add any other text or explanation outside of the JSON object.

# --- CONTEXT-SPECIFIC RULES ---
context_specific_rules: |
  - **Creator History / URI:** A poor creator history (e.g., many rugs) is a **MAJOR VETO SIGNAL. You MUST set confidence to 0.** An 'Error'/'Missing' URI is also a strong VETO signal.
  - **Market Activity:** If Market Dynamics are 'N/A' or volatility is 0.000, it means **ZERO activity**. This is a **MAJOR VETO SIGNAL. You MUST set confidence to 0.**
  - **CRITICAL Rebuy Context:** This is a `REBUY`. Your signals for `BUY` must be *exceptionally strong*.
  - **You MUST check the 'Past Trade History'**: What was the reason for the last sell?
  - If the previous sell was a 'Stop Loss' or 'AI Triggered Sell' due to risk, you *must* see clear evidence that this risk is resolved (e.g., new hype, rising RSI, strong market dynamics).
  - If the token is just drifting sideways or down after the last sell, it is a **VETO. You MUST set confidence to 0.**

# --- DATA FORMATTING TEMPLATES (Unchanged) ---
source_explanation: "PUMP = High-frequency individual trades on a new, unmigrated token. DEXSCREENER = Periodic aggregate snapshots on a token that has successfully migrated to a standard DEX (e.g., Raydium). A 'DEXSCREENER' source is a positive signal, as it means the token was not an immediate rug-pull and achieved a liquidity pool."
market_cap_guidance: "Avoid re-buys below ${default_marketcap_threshold:,.0f}. The token must show new strength, not just a low price."

market_dynamics_template_pump: |
  - Price Change (1min): {pump_price_change_1m}
  - Volume Velocity (1min): {pump_volume_velocity_1m}
  - Tick Frequency (1min): {pump_tick_frequency_1m} trades/min

market_dynamics_template_dex: |
  - Price Change (5min snap): {dex_price_change_m5:.2f}%
  - Volume (5min snap): ${dex_volume_m5:,.0f}
  - Buys/Sells (5min snap): {dex_buys_m5} / {dex_sells_m5}
  - Price Trend (15min): {dex_price_trend_15m}
  - Volume Trend (15min): {dex_volume_trend_15m}
  - Liquidity Trend (30min): {dex_liquidity_trend_30m}
```

#### 📄 `sell.yaml`
*path: `ai_decision_module/prompts/sell.yaml`*

```yaml
# Prompts - SELL/HOLD Context Configuration (FINETUNED V6 - Confidence-Only)

# --- TASK DEFINITION ---
task_definition: |
  You are an expert Solana meme coin trading analyst AI. Your goal is to evaluate an **EXIT POINT** for a trading bot.
  The bot is **CURRENTLY HOLDING** this token.
  **Current Decision Context:** {decision_context}
  Your output `confidence` score [0-100] will determine the action: 0 means HOLD, 100 means SELL IMMEDIATELY.

  Based on the **Current Token Data** and **Key Decision Rules** provided below, perform a step-by-step analysis.

  **YOUR FINAL TASK:** Return a single JSON object with your analysis. Do not add any other text or explanation outside of the JSON object.

# --- CONTEXT-SPECIFIC RULES ---
context_specific_rules: |
  - **Market Activity / Stagnation:** If Market Dynamics become 'N/A' or volatility drops to 0.000, the token is **DEAD**. This is an **IMMEDIATE SELL SIGNAL. You MUST set confidence to 100.**
  - **DexScreener Specific:** For DEX tokens, near-zero `Volume (5min snap)` or a 'Decreasing' `Liquidity Trend (30min)` are critical exit signals.
  - **Creator History / URI:** If holding a token from a creator with a poor history, your tolerance for risk should be **ZERO**. The first sign of negative momentum is an **IMMEDIATE SELL SIGNAL (set confidence to 100).**

# --- DATA FORMATTING TEMPLATES (Unchanged) ---
source_explanation: "PUMP = High-frequency individual trades on a new, unmigrated token. DEXSCREENER = Periodic aggregate snapshots on a token that has successfully migrated to a standard DEX (e.g., Raydium). A 'DEXSCREENER' source is a positive signal, as it means the token was not an immediate rug-pull and achieved a liquidity pool."
market_cap_guidance: "Consider selling if Market Cap drops significantly, especially below ${min_marketcap_threshold:,.0f} (emergency threshold). Stagnant or decreasing MC over time is negative for holds."

market_dynamics_template_pump: |
  - Price Change (1min): {pump_price_change_1m}
  - Volume Velocity (1min): {pump_volume_velocity_1m}
  - Tick Frequency (1min): {pump_tick_frequency_1m} trades/min

market_dynamics_template_dex: |
  - Price Change (5min snap): {dex_price_change_m5:.2f}%
  - Volume (5min snap): ${dex_volume_m5:,.0f}
  - Buys/Sells (5min snap): {dex_buys_m5} / {dex_sells_m5}
  - Price Trend (15min): {dex_price_trend_15m}
  - Volume Trend (15min): {dex_volume_trend_15m}
  - Liquidity Trend (30min): {dex_liquidity_trend_30m}
```

#### 📄 `bot_logger.py`
*path: `bot_logger.py`*

```python
# bot_logger.py
import os
import queue
import inspect
from datetime import datetime
import logging
from functools import wraps
from rich.logging import RichHandler
from rich.console import Console
from config.config import _LOGGER_NAME, _LOG_LEVEL_CONSOLE, _LOG_LEVEL_FILE, _LOG_STORAGE_PATH
import os

# --- RICH COMPONENT IMPORTS AND RE-EXPORTS ---
import rich.panel
import rich.table
import rich.text
import rich.align
import rich.console
import rich.box as _rich_box_module

Panel = rich.panel.Panel
Table = rich.table.Table
Text = rich.text.Text
Align = rich.align.Align
Group = rich.console.Group
rich_box = _rich_box_module
# --- END RICH RE-EXPORTS ---

logger = logging.getLogger(name=_LOGGER_NAME)
log_queue = queue.Queue()
console_for_queue_capture = Console() # Define a console instance for capturing

# --- ADD THIS CUSTOM HANDLER ---
class DebugRichHandler(RichHandler):
    def emit(self, record: logging.LogRecord) -> None:
        # Log what RichHandler's emit method receives as record.msg
        is_rich_in_emit = hasattr(record.msg, "__rich_console__") or hasattr(record.msg, "__rich__")
        print(f"DEBUG_HANDLER_EMIT: Type of record.msg: {type(record.msg)}")
        print(f"DEBUG_HANDLER_EMIT: Is Panel instance: {isinstance(record.msg, Panel)}") # Use your re-exported Panel
        print(f"DEBUG_HANDLER_EMIT: Has __rich_console__ in emit: {hasattr(record.msg, '__rich_console__')}")
        print(f"DEBUG_HANDLER_EMIT: Has __rich__ in emit: {hasattr(record.msg, '__rich__')}")
        print(f"DEBUG_HANDLER_EMIT: String of record.msg: {str(record.msg)[:150]}...") # First 150 chars

        # Original RichHandler emit logic follows
        try:
            super().emit(record)
        except Exception as e:
            # This will catch errors happening *during* RichHandler's own processing
            print(f"DEBUG_HANDLER_EMIT: Error during super().emit(): {e}")
            # Fallback to basic printing if super().emit fails
            log_message = self.format(record) # Get the string formatted by the handler
            self.console.print(log_message, overflow="ignore", no_wrap=True) # Basic print
# --- END CUSTOM HANDLER ---


def setup_logging(logger_name=_LOGGER_NAME):
    """
    Setup logging with both file and console handlers using config-defined levels.
    """
    logger.setLevel(logging.DEBUG)
    if logger.hasHandlers():
        logger.handlers.clear()

    os.makedirs(_LOG_STORAGE_PATH, exist_ok=True)

    # File Handler
    try:
        file_handler = logging.FileHandler(
            f"{_LOG_STORAGE_PATH}/{logger_name}.log", encoding="utf-8"
        )
        file_level = logging.getLevelName(_LOG_LEVEL_FILE)
        file_handler.setLevel(file_level)

        file_formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(funcName)s() - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
    except Exception as e:
        logging.error(f"Failed to create file handler: {e}")
        file_handler = None

    console_handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        # Ensure RichHandler can handle renderables by not trying to stringify them too early
        # The default behavior should be fine.
    )
    console_level = logging.getLevelName(_LOG_LEVEL_CONSOLE)
    console_handler.setLevel(console_level)

    if file_handler:
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.propagate = False

    logger.debug(":writing_hand: [green]Logging system initialized with level:[/green] [bold red]%s[/bold red]", logging.getLevelName(logger.level))
    
    def log_to_queue(record):
        # Check if the message is already a Rich renderable object
        if hasattr(record.msg, '__rich_console__'):
            # Render the Rich object to a string for the queue
            with console_for_queue_capture.capture() as capture:
                console_for_queue_capture.print(record.msg)
            log_queue.put(capture.get().strip()) # Put stringified version
        else:
            log_queue.put(record.getMessage()) # Standard string message

    log_handler = logging.StreamHandler()
    # log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')) # Formatter might interfere with Rich renderables if not careful
    log_handler.emit = log_to_queue # type: ignore
    # logger.addHandler(log_handler) # Decide if this queue logging is still needed with Rich. For simplicity, can be commented out if not strictly used.


def rotate_log_file(logger_name=_LOGGER_NAME):
    """Rotate current log file with timestamp and create new log"""
    try:
        handlers = logger.handlers.copy()
        for handler in handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
                handler.close()
                logger.removeHandler(handler)

        log_path = f"{_LOG_STORAGE_PATH}/{logger_name}.log"
        if os.path.exists(log_path):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_name = f"{_LOG_STORAGE_PATH}/{_LOGGER_NAME}.{timestamp}.log"
            os.rename(log_path, new_name)
            logger.info(f"Log rotated to: {new_name}")

        setup_logging() # This re-initializes handlers, including RichHandler
        logger.info(":newspaper: Initialized new log file after rotation")

    except Exception as e:
        logger.error(f":exclamation: Log rotation failed: {str(e)}", exc_info=True)


# -------------------------------
# 🚀 Contextual Logging Functions
# -------------------------------

def _get_caller_context():
    frame = inspect.currentframe()
    # Go up the stack to find the caller outside of logger.py
    while frame and frame.f_code.co_filename == __file__:
        frame = frame.f_back # type: ignore
    if not frame: # Should not happen in normal use
        return "[unknown_context]"
        
    func_name = frame.f_code.co_name
    cls = frame.f_locals.get("self", None)
    class_name = cls.__class__.__name__ if cls else None
    return f"[{class_name}.{func_name}]" if class_name else f"[{func_name}]"


def log_with_context(level, msg, *args, **kwargs):
    # If msg is a Rich renderable, it's passed directly to logger.log.
    # Otherwise, context is prepended.
    if not hasattr(msg, '__rich_console__'): # Check if msg is NOT a Rich renderable
        context = _get_caller_context()
        logger.log(level, f"{context} {msg}", *args, **kwargs) # msg becomes part of an f-string -> str(msg)
    else: # msg IS a Rich renderable (like your Panel)
        logger.log(level, msg, *args, **kwargs) # msg is passed AS IS (the Panel object)


def log_debug(msg, *args, **kwargs):
    log_with_context(logging.DEBUG, msg, *args, **kwargs)

def log_info(msg, *args, **kwargs):
    log_with_context(logging.INFO, msg, *args, **kwargs)

def log_warning(msg, *args, **kwargs):
    log_with_context(logging.WARNING, msg, *args, **kwargs)

def log_error(msg, *args, **kwargs):
    log_with_context(logging.ERROR, msg, *args, **kwargs)

def log_critical(msg, *args, **kwargs):
    log_with_context(logging.CRITICAL, msg, *args, **kwargs)

# -------------------------------------
# 🧙 Decorators: Auto Entry/Exit Logging
# -------------------------------------

def log_calls(level=logging.DEBUG):
    """
    Decorator to automatically log entry and exit of a function.
    Supports both sync and async functions.
    """
    def decorator(func):
        is_coroutine = inspect.iscoroutinefunction(func)
        func_name_for_log = func.__name__ # Get func name at decoration time

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # For decorators, explicitly construct the context string
            cls = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
            context = f"[{cls}.{func_name_for_log}]" if cls else f"[{func_name_for_log}]"

            logger.log(level, f"{context} → Entered")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"{context} ← Exited")
                return result
            except Exception as e:
                logger.exception(f"{context} ❌ Exception: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cls = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
            context = f"[{cls}.{func_name_for_log}]" if cls else f"[{func_name_for_log}]"

            logger.log(level, f"{context} → Entered")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{context} ← Exited")
                return result
            except Exception as e:
                logger.exception(f"{context} ❌ Exception: {e}")
                raise

        return async_wrapper if is_coroutine else sync_wrapper
    return decorator
```

#### 📄 `__init__.py`
*path: `config/__init__.py`*

_This file is empty._

#### 📄 `config.py`
*path: `config/config.py`*

```python
# path: config/config.py

"""
Configuration constants and settings for the trading bot.
"""
import datetime

# Trading configuration
_INITIAL_SOL_BALANCE = 100.0                # Starting SOL balance for PnL tracking
SOL_TO_BUY = 0.5                            # Amount of SOL to spend on each buy
PLAY_BUY_SOUND = False                      # Play the buy sound when a buy is made
PLAY_SELL_SOUND = False                     # Play the sell sound when a sell is made

# --- NEW TRADING MODE ---
# Options: "simulate", "paper_trading", "live"
# "simulate": Records trades to DB as if they happened, no external calls for execution.
# "paper_trading": Calls live execution APIs, signs transactions, but DOES NOT send to network. Simulates fills.
# "live": Full live trading, sends transactions to the network.
TRADING_MODE = "simulate"                   # <<< SET YOUR DEFAULT MODE HERE (e.g., "simulate" for safety)
DEFAULT_SLIPPAGE_PERCENT = 15.0                # Default slippage percentage for trades (e.g., 1.0 for 1%)
DEFAULT_BUY_POOL = "auto"
DEFAULT_SELL_POOL = "auto"

# --- New Multi-Stage Sell Logic Configuration ---
FIRST_SELL_PROFIT_MARGIN = 110.0             # Desired profit margin % on the *total initial investment* for the first TP sell
FIRST_SELL_PERCENT = 45.0                   # % of *initial* tokens to sell at First TP (e.g., 50.0 for 50%)
INITIAL_STOP_LOSS_PERCENT = 25.0            # Initial SL as % below buy price (e.g., 25.0 for -25%)
TRAILING_STOP_LOSS_PERCENT = 20.0           # Trailing SL % drop from highest price *after* First TP (e.g., 15.0 for -15%)
SECOND_TAKE_PROFIT_PERCENT = 600.0          # Second TP as % above buy price (e.g., 200.0 for +200%)

# --- NEW: Dynamic Second Take-Profit Configuration ---
USE_DYNAMIC_SECOND_TP = True                # Master switch. If False, uses fixed SECOND_TAKE_PROFIT_PERCENT.

# Parameters for the Adaptive Chandelier Exit
ADAPTIVE_ATR_PERIOD = 14                    # Period for the ATR calculation.
ADAPTIVE_ATR_BASE_MULTIPLIER = 2.0          # Base multiplier for moderate momentum.
ADAPTIVE_ATR_STRONG_MULTIPLIER = 3.0        # Multiplier for strong momentum.
ADAPTIVE_ATR_EXTREME_MULTIPLIER = 4.0       # Multiplier for extreme parabolic momentum.
ADAPTIVE_RSI_STRONG_LEVEL = 70              # RSI level considered "strong" momentum.
ADAPTIVE_RSI_EXTREME_LEVEL = 85             # RSI level considered "extreme" momentum.

# --- Fees and Tips ---
DEFAULT_BUY_FEE = 0.001                     # Fee for buying in SOL
DEFAULT_BUY_TIP = 0.001                     # Tip for buying in SOL
DEFAULT_SELL_FEE = 0.001                    # Fee for selling in SOL
DEFAULT_SELL_TIP = 0.001                    # Tip for selling in SOL

# Price determination strategy
PRICE_DETERMINATION_METHOD = "MEDIAN"       # Options: "VWAP", "TWAP", "LATEST", "MEDIAN" (Applies to chosen source)
TWAP_SUB_INTERVAL_SECONDS = 15              # Sub-interval for TWAP calculation (if TWAP is used) in seconds
PRICE_AVG_WINDOW_MINUTES = 0.25           # You mentioned you already set this to 0.25 (15 seconds) - keep it

# --- NEW: Price Calculation Strategy Control ---
# Determines the primary source for decision price and market cap.
# "direct_price": Calculates robust price from trades (sol_amount/token_amount), then derives MC.
# "market_cap": Calculates robust MC from trades (marketCapSol), then derives price.
PRICE_SOURCE_METHOD = "direct_price"  # Default, Options: "direct_price", "market_cap"

# Determines how the lookback window for price/MC calculation is defined.
# "time": Uses PRICE_AVG_WINDOW_MINUTES.
# "count": Uses PRICE_AVG_TRADE_COUNT.
PRICE_WINDOW_TYPE = "count"  # Default, Options: "time", "count"
PRICE_AVG_TRADE_COUNT = 15  # Number of trades for window if PRICE_WINDOW_TYPE is "count" (e.g., last 20 trades)


# Trading thresholds
DEFAULT_RUGCHECK_SCORE_THRESHOLD = 901      # No trading if Rugcheck score is equal or above this threshold
DEFAULT_SOCIAL_SCORE_THRESHOLD = 100        # No trading if Social score is equal or above this threshold
DEFAULT_VOLUME_THRESHOLD = 2000            # Minimum volume threshold in USD
MIN_MARKETCAP_THRESHOLD = 4000              # Minimum market cap threshold in USD to make emergency sell
DEFAULT_MARKETCAP_THRESHOLD = 14000         # Minimum market cap threshold in USD to search for buy opportunities
MIN_VOLATILITY = 0.11                       # Minimum volatility threshold in % to search for buy opportunities
DEFAULT_TIME_INTERVAL = 10                 # Time interval for checking volatility, volume and marketcap in minutes
MAX_TOKEN_COUNT_PER_CREATOR = 100           # Maximum number of tokens per creator to consider token as safe

# --- Re-Buy Logic Configuration ---
USE_TREND_REVERSAL_CONFIRMATION = True      # Master switch to enable/disable this feature
STOP_LOSS_COOLDOWN_MINUTES = 17              # How long a token is ignored after a Stop Loss
MIN_CANDLE_DATA_FOR_INDICATORS = 30         # Min 5-second data points required to calculate indicators
TREND_REVERSAL_RECENCY_HOURS = 24 
TREND_REVERSAL_RSI_NEUTRAL_LEVEL = 20.0     # RSI level considered neutral for trend reversal
INDICATOR_LOOKBACK_HOURS = 1.7                # Lookback period for indicators in hours

# Indicator Time Periods
# MODIFICATION: Emojis removed from this list to ensure robust string comparisons.
APPLY_TREND_REVERSAL_ON_SELL_REASONS = ["Stop Loss", "Emergency SL (MCap)", "Emergency SL (No Volume)", "Trailing SL", "Breakeven SL", "manual_override", "manual_override_all"]
RSI_PERIOD = 9 
BBANDS_PERIOD = 19
BBANDS_STD_DEV = 1.5
FAST_EMA_PERIOD = 9
SLOW_EMA_PERIOD = 150

# --- DexScreener Trend Reversal Configuration ---
DEX_REVERSAL_LOOKBACK_MINUTES = 20          # How many minutes of snapshot data to analyze.
DEX_REVERSAL_MIN_SNAPSHOTS = 5              # Minimum number of snapshots required within the lookback window.
DEX_REVERSAL_MIN_LIQUIDITY_USD = 3500       # Minimum liquidity in USD for the token to be considered viable for a re-buy.
DEX_REVERSAL_MIN_PRICE_CHANGE_M5 = 2.0      # The m5 price change must be at least +2.0% to be counted as a positive signal.
DEX_REVERSAL_MIN_BUY_SELL_RATIO = 2.4       # Ratio of buys to sells must be at least 1.5 for a strong buying pressure signal.
DEX_REVERSAL_MIN_CONFIRMATIONS = 3          # How many snapshots must show strong buying pressure to confirm the trend.
DEXSCREENER_MIGRATION_GRACE_PERIOD_MINUTES = 5 # How many minutes after migration to ignore stale volume checks. # <<< ADD THIS LINE


# UNSUBSCRIBING CONDITIONS
INACTIVITY_PERIOD = 60                      # Inactivity period in minutes before unsubscribing & backup
MC_DROP_THRESHOLD = 2                       # Market cap drop threshold (in %) under creation MC - for unsubscription & backup
MIN_TOKEN_AGE = 30                          # Minimum token age in minutes before possible unsubscription & backup


# PumpPortal
_TOTAL_SUPPLY = 1000000000                   # Assumed total supply if not provided
_PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"
_PUMPORTAL_LOCAL_API_URL = "https://pumpportal.fun/api/trade-local"
_WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED = True       # Enable periodic refresh of all trade subscriptions
_WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES = 240 # Interval in minutes to perform the refresh

# --- WebSocket Stability ---
WEBSOCKET_MAX_SUBSCRIPTIONS = 3000  # Cap to avoid server limits
WEBSOCKET_PING_INTERVAL_SECONDS = 30  # Send ping every 30s
WEBSOCKET_PONG_TIMEOUT_SECONDS = 20  # Expect pong within 10s or reconnect
WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS = 1  # Exponential backoff start
WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS = 60  # Max delay
INACTIVITY_UNSUBSCRIBE_MINUTES = 60  # Unsub tokens inactive > this (from existing INACTIVITY_PERIOD)
WEBSOCKET_HEALTH_CHECK_INTERVAL = 10  # seconds
WEBSOCKET_SUBSCRIPTION_BATCH_SIZE = 100
WEBSOCKET_BATCH_DELAY = 0.5  # seconds between batches

_RUGCHECK_AUTH_API = "https://api.rugcheck.xyz/auth/login/solana"
_RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens"
_RUGCHECK_RATE_LIMIT = 10                    # 10 requests per minute
_RUGCHECK_INTERVAL = 60                      # 60 seconds interval for RugCheck checks
RUGCHECK_SCORE_THRESHOLD = 10000             # Score above which a token is considered high risk and deactivated
RUGCHECK_REQUEUE_PRIORITY_BOOST_PURCHASED = 1000.0 # High priority boost for purchased tokens
RUGCHECK_REQUEUE_INTERVAL_MINUTES = 5 # How often to check for requeue opportunities
RUGCHECK_MAX_INITIAL_ATTEMPTS = 3      # Number of high-priority attempts before deprioritizing.
RUGCHECK_MAX_DEPRIORITIZED_ATTEMPTS = 5 # Number of low-priority re-attempts before culling a token.

# SOL price configuration
_SOL_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# --- Solana RPC ---
_SOLANA_RPC_ENDPOINT = "https://solana.drpc.org"
_DRPC_ENDPOINT = "https://lb.drpc.org/ogrpc?network=solana"

# "https://api.mainnet-beta.solana.com" # A public endpoint
# Alternative free endpoints:
# "https://solana-mainnet.g.alchemy.com/v2/YOUR_API_KEY" (requires free sign-up)
# "https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY" (requires free sign-up)

# --- AI Decision Maker Configuration ---
AI_DECISION_MAKING_ENABLED = True           # Master switch to enable/disable AI evaluation
AI_MODEL_NAME = 'ibm/granite4:latest'       #'lucasmg/gemma3-12b-tool-thinking-true:latest' #'deepseek-r1:8b-0528-qwen3-q4_K_M' #'deepseek-r1:8b'             # Ollama model to use (e.g., 'llama3', 'mistral')
AI_LOG_VERBOSE = False                      # Set to True for full AI debug spam, False for concise logs
_AI_EMBEDDNG_MODEL = 'all-MiniLM-L6-v2'     # Sentence Transformer model for RAG embeddings
_AI_PROMPTS_DIR = 'ai_decision_module/prompts' # Path to the YAML prompt files
_AI_CHROMA_DB_PATH = './ai_decision_module/chroma_db_aidm' # Path for ChromaDB persistence

# AI Queue & Worker Settings
AI_QUEUE_MAX_SIZE = 1000                     # Max items in the AI evaluation queue
AI_WORKER_SLEEP_SECONDS = 0.5               # Sleep time for AI worker if queue is empty
AI_MAX_CONCURRENT_EVALUATIONS = 1           # How many AI evaluations to run in parallel (adjust based on resources)

# AI Advice Staleness & Refresh Intervals (in minutes)
AI_ADVICE_MAX_STALENESS_MINUTES = 20        # How old AI advice can be before being ignored
AI_REFRESH_INTERVAL_PORTFOLIO_MIN = 5       # How often to re-evaluate held portfolio tokens
AI_REFRESH_INTERVAL_MOMENTUM_MIN = 15       # How often to re-evaluate high-momentum tokens
AI_REFRESH_INTERVAL_EVENT_MIN = 30          # Minimum time between re-evaluating due to events (score changes, migration)
AI_REFRESH_INTERVAL_STALE_MIN = 60          # How often to check for the oldest evaluated tokens to refresh

# AI Confidence Thresholds for Trading Logic
AI_CONFIDENCE_THRESHOLD_INITIAL_BUY = 90    # 90 is just an example. Set your desired threshold.
AI_CONFIDENCE_THRESHOLD_STRONG = 70         # Confidence level for strong confirmation/action
AI_CONFIDENCE_THRESHOLD_VETO = 75           # Confidence level for AI to veto a rule-based buy
AI_BUY_HOLD_CONFIDENCE_THRESHOLD = 75       # Min confidence for AI 'HOLD' to defer a buy
AI_SELL_TRIGGER_CONFIDENCE_THRESHOLD = 85   # Min confidence for AI 'SELL' to trigger an early sell
AI_HOLD_OVERRIDE_CONFIDENCE_THRESHOLD = 85  # Min confidence for AI 'HOLD' to potentially override a non-critical rule-based sell

# AI Queue Population Settings
AI_MOMENTUM_TOP_N = 5                       # How many top momentum tokens (PUMP & DEX) to queue
AI_NEW_TOKEN_SAMPLE_RATE = 0.02             # Percentage (0.0 to 1.0) of new tokens to sample for AI eval
AI_STALE_REFRESH_BATCH_SIZE = 5             # How many oldest tokens to refresh in the general refresh cycle

# Logging
_LOGGER_NAME = "TradingBot"
_LOG_LEVEL_CONSOLE: str = "DEBUG"
_LOG_LEVEL_FILE: str = "DEBUG"
_LOG_STORAGE_PATH: str = "log"

# Backup
_BACKUP_STORAGE_PATH: str = "backups"  # Directory for backups

# Telegram
TELEGRAM_INTERACTION = True

# Telegram Monitoring Settings
TELEGRAM_AUTO_JOIN_GROUPS = True
TELEGRAM_MAX_GROUPS_PER_TOKEN = 5
TELEGRAM_REALTIME_MONITORING = True
TELEGRAM_MESSAGE_HISTORY_HOURS = 24
TELEGRAM_MAX_MESSAGES_PER_GROUP = 200
TELEGRAM_SENTIMENT_ANALYSIS_ENABLED = True
# Sentiment Analysis Settings
SENTIMENT_ANALYSIS_MODEL = "llama3.1:8b"  # Ollama model for sentiment
SENTIMENT_CONFIDENCE_THRESHOLD = 0.7
SENTIMENT_URGENCY_THRESHOLD = 0.8
# Group Health Scoring Weights
GROUP_HEALTH_WEIGHTS = {
    'member_count': 0.2,
    'message_frequency': 0.3,
    'active_users_ratio': 0.25,
    'admin_activity': 0.15,
    'media_share_ratio': 0.1
}

# --- Metadata Processor Configuration ---
HEARTBEAT_EMIT_INTERVAL_SECONDS = 60  # Interval for emitting heartbeat messages in seconds
RESTART_GAP_THRESHOLD_SECONDS = 600  # Threshold for restart gap in seconds
# --- Metadata Processor Configuration ---

# --- Socials Processor Configuration ---
SOCIALS_CHECK_REFRESH_INTERVAL = 120                  # Timeout for requeing socials check in minutes
SOCIALS_DISALLOWED_WEBSITE_DOMAINS = {
    "youtube.com", "youtu.be", "tiktok.com", "spotify.com", "soundcloud.com",
    "discord.com", "discord.gg", "medium.com", "substack.com", "linktr.ee",
    "t.me", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "reddit.com", "twitch.tv", "kick.com", "google.com",
    "example.com",
}
SOCIALS_ALLOWED_NEWS_DOMAINS = {
    "bbc.com", "cnn.com", "reuters.com", "apnews.com", "nytimes.com",
    "washingtonpost.com", "theguardian.com", "bloomberg.com", "forbes.com",
    "wsj.com", "ft.com", "npr.org", "cnbc.com", "abcnews.go.com",
    "nbcnews.com", "cbsnews.com", "latimes.com", "usatoday.com",
    "politico.com", "aljazeera.com", "theatlantic.com", "newsweek.com",
    "time.com", "economist.com", "sky.com", "independent.co.uk",
    "telegraph.co.uk", "dailymail.co.uk", "mirror.co.uk", "huffpost.com",
    "vox.com", "slate.com", "buzzfeednews.com", "axios.com", "thehill.com",
    "scmp.com", "japantimes.co.jp", "hindustantimes.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "straitstimes.com", "smh.com.au",
    "theage.com.au", "globalnews.ca", "cbc.ca", "bitcointalk.org",
    "cnbcnews.us", "truthsocial.com"
}

# --- DYNAMIC SOCIALS SCORING ---
SOCIALS_SCORE_TYPE_INITIAL = 'INITIAL_METADATA'
SOCIALS_SCORE_TYPE_FOLLOWUP = 'FOLLOWUP_METADATA'
SOCIALS_SCORE_TYPE_TELEGRAM = 'TELEGRAM_UPDATE'
SOCIALS_SCORE_TYPE_WEBSITE = 'WEBSITE_UPDATE'
SOCIALS_TELEGRAM_UPDATE_INTERVAL_MINUTES = 15 # How often to re-check telegram stats for active tokens

# Penalties (Higher = Worse)
SOCIALS_PENALTY_NO_WEBSITE = 40
SOCIALS_PENALTY_INVALID_WEBSITE_TYPE = 35
SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED = 35
SOCIALS_PENALTY_WEBSITE_INVALID_URL = 35
SOCIALS_PENALTY_WEBSITE_TIMEOUT = 35
SOCIALS_PENALTY_WEBSITE_HTTP_ERROR = 35
SOCIALS_PENALTY_WEBSITE_OTHER_ERROR = 35
SOCIALS_PENALTY_NO_HTTPS = 10
SOCIALS_PENALTY_WEBSITE_NO_MENTION = 10         # No mention of token name or symbol in website
SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE = 25    # Common platforms like Youtube, TikTok, etc. 'SOCIALS_DISALLOWED_WEBSITE_DOMAINS'
SOCIALS_PENALTY_NO_TELEGRAM = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_URL = 25
SOCIALS_PENALTY_NO_TWITTER = 25
SOCIALS_PENALTY_INVALID_TWITTER_TYPE = 25
SOCIALS_PENALTY_INVALID_TWITTER_URL = 25
SOCIALS_PENALTY_DUPLICATE_LINKS = 15            # Duplicate links in metadata
SOCIALS_PENALTY_ACTION_TRIGGER_URL = 15         # Action trigger URL in metadata

# Bonuses (Negative = Better)
SOCIALS_BONUS_DOMAIN_MATCH = -10                # Bonus if domain mentions token name or symbol
SOCIALS_BONUS_NEWS_GOV_WEBSITE = 0              # No penalty/bonus currently applied for news/gov sites in 'SOCIALS_ALLOWED_NEWS_DOMAINS'
SOCIALS_BONUS_TG_HIGH_MEMBERS = -10             # Bonus for having a large number of members
SOCIALS_THRESHOLD_TG_HIGH_MEMBERS = 2000        # Threshold above which high member bonus applies
SOCIALS_BONUS_TG_HIGH_ONLINE_RATIO = -5         # Bonus for a healthy online-to-member ratio
SOCIALS_THRESHOLD_TG_HIGH_ONLINE_RATIO = 0.10   # Ratio (10%) above which the high online ratio bonus applies

# Default Scores
SOCIALS_SCORE_FAILED_METADATA = 100             # Score assigned if metadata fetch fails
```

#### 📄 `ga_config.py`
*path: `config/ga_config.py`*

```python
# FILE: ga_config.py

"""
Configuration for the Genetic Algorithm (GA) optimizer.

This module defines the parameters to be optimized by the GA,
their respective ranges (boundaries), data splitting configurations,
backtesting settings, and GA hyperparameters.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Union
import numpy as np

# --- Parameters to Optimize (Fine-Tuned Set) ---
# This set provides more focused ranges and includes all new parameters
# for both Pump.fun and DexScreener trend reversal logic.
OPTIMIZABLE_PARAMETERS: List[Dict[str, Any]] = [
    # --- Standard Trading Parameters ---
    {
        "name": "SOL_TO_BUY",
        "values": [0.5], # Fixed to a single value by enclosing in a list.
        "type": float
    },
    {
        "name": "INITIAL_STOP_LOSS_PERCENT",
        "values": list(range(15, 51, 5)),    # Range: 10, 12, ..., 40
        "type": float
    },
    {
        "name": "FIRST_SELL_PERCENT",
        "values": list(range(10, 81, 10)),    # Range: 5, 10, ..., 100
        "type": float
    },
    {
        "name": "FIRST_SELL_PROFIT_MARGIN",
        "values": list(range(10, 151, 10)), # Range: 10, 60, 110, 160
        "type": float
    },
    {
        "name": "TRAILING_STOP_LOSS_PERCENT",
        "values": list(range(5, 66, 5)),    # Range: 5, 10, ..., 60
        "type": float
    },
    {
        "name": "SECOND_TAKE_PROFIT_PERCENT", # Note: This is now a fallback if dynamic TP is disabled.
        "values": list(range(350, 801, 50)), # Range: 200, 250, ..., 600
        "type": float
    },

    # +++ [NEW] DYNAMIC SECOND TAKE-PROFIT PARAMETERS +++
    {
        "name": "USE_DYNAMIC_SECOND_TP",
        "values": [1], # 0 for False (use fixed/trailing SL), 1 for True (use Chandelier Exit)
        "type": int # Booleans are treated as integers (0 or 1) by the GA
    },
    {
        "name": "ADAPTIVE_ATR_PERIOD",
        "values": list(range(10, 21, 2)), # e.g., 10, 12, ..., 20
        "type": int
    },
    {
        "name": "ADAPTIVE_ATR_BASE_MULTIPLIER",
        "values": [1.5], #list(np.arange(1.5, 3.1, 0.25)), # 1.5, 1.75, ..., 3.0
        "type": float
    },
    {
        "name": "ADAPTIVE_ATR_STRONG_MULTIPLIER",
        "values": [2.5], #list(np.arange(2.5, 4.1, 0.25)), # 2.5, 2.75, ..., 4.0
        "type": float
    },
    {
        "name": "ADAPTIVE_ATR_EXTREME_MULTIPLIER",
        "values": [5.0], #list(np.arange(3.5, 5.1, 0.25)), # 3.5, 3.75, ..., 5.0
        "type": float
    },
    {
        "name": "ADAPTIVE_RSI_STRONG_LEVEL",
        "values": list(range(20, 81, 10)), # 65, 66, ..., 75
        "type": int
    },
    {
        "name": "ADAPTIVE_RSI_EXTREME_LEVEL",
        "values":  list(range(40, 101, 10)), # 80, 81, ..., 90
        "type": int
    },
    # +++ [END NEW] +++

    # --- Buy Condition Thresholds ---
    {
        "name": "DEFAULT_VOLUME_THRESHOLD",
        "values": [1000, 5000, 10000], #list(range(1000, 10001, 1000)), # Range: 1000, 2000, ..., 10000
        "type": int
    },
    {
        "name": "DEFAULT_MARKETCAP_THRESHOLD",
        "values": [5000, 15000, 25000], #list(range(5000, 30001, 1000)), # Range: 5000, 6000, ..., 30000
        "type": int
    },
    {
        "name": "MIN_VOLATILITY",
        "values": [0.05, 0.15, 0.25], #[round(x * 0.01, 2) for x in range(5, 41)], # Range: 0.10, 0.11, ..., 0.30
        "type": float
    },
    {
        "name": "DEFAULT_RUGCHECK_SCORE_THRESHOLD",
        "values": list(range(1, 1001, 100)),   # Range: 1, 101, ..., 901
        "type": int
    },
    {
        "name": "DEFAULT_SOCIAL_SCORE_THRESHOLD",
        "values": [20, 50, 100], #list(range(0, 101, 10)),     # Range: 0, 10, ..., 100
        "type": int
    },

    # --- PUMP.FUN Trend Reversal Parameters ---
    {
        "name": "USE_TREND_REVERSAL_CONFIRMATION",
        "values": [1], # 0 (False) or 1 (True)
        "type": int
    },
    {
        "name": "STOP_LOSS_COOLDOWN_MINUTES",
        "values": [20], #list(range(5, 46, 5)),      # Range: 1, 3, ..., 19
        "type": int
    },
    {
        "name": "TREND_REVERSAL_RECENCY_HOURS",
        "values": [1.0], # list(np.arange(0.1, 2.0, 0.2)), # Range: 0.1, 0.3, ..., 1.9
        "type": float
    },
    {
        "name": "TREND_REVERSAL_RSI_NEUTRAL_LEVEL",
        "values": list(range(5, 55, 5)),      # Range: 5, 10, ..., 50
        "type": float
    },
    {
        "name": "INDICATOR_LOOKBACK_HOURS",
        "values": list(np.arange(0.1, 1.2, 0.2)), # Range: 0.1, 0.2, ..., 1.9
        "type": float
    },
    {
        "name": "RSI_PERIOD",
        "values": list(range(4, 20, 5)),      # Range: 4, 5, ..., 14
        "type": int
    },
    {
        "name": "BBANDS_PERIOD",
        "values": [20], #list(range(15, 23, 1)),     # Range: 15, 16, ..., 22
        "type": int
    },
    {
        "name": "BBANDS_STD_DEV",
        "values": [1.5], # [round(x * 0.1 + 1.5, 1) for x in range(0, 8)], # Range: 1.5, 1.6, ..., 2.2
        "type": float
    },
    {
        "name": "FAST_EMA_PERIOD",
        "values": list(range(7, 16, 2)),      # Range: 7, 8, ..., 13
        "type": int
    },
    {
        "name": "SLOW_EMA_PERIOD",
        "values": list(range(15, 56, 5)),     # Range: 18, 19, ..., 25
        "type": int
    },

    # --- DEXSCREENER Trend Reversal Parameters ---
    {
        "name": "DEX_REVERSAL_LOOKBACK_MINUTES",
        "values": [15], # list(range(15, 31, 5)), # 15, 20, 25, 30
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_SNAPSHOTS",
        "values": [5], # list(range(4, 8, 1)), # 4, 5, 6, 7
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_LIQUIDITY_USD",
        "values": [2000], #list(range(500, 4001, 500)), # 500, 1000, ..., 4000
        "type": int
    },
    {
        "name": "DEX_REVERSAL_MIN_BUY_SELL_RATIO",
        "values": [2.0], #[round(x * 0.2 + 1.2, 1) for x in range(0, 10)], # 1.2, 1.4, ..., 3.0
        "type": float
    },
    {
        "name": "DEX_REVERSAL_MIN_CONFIRMATIONS",
        "values": [2], #list(range(1, 4, 1)), # 1, 2, 3
        "type": int
    },
]

# --- GA Settings ---
# STOP_CRITERIA
# Explanation: Defines the condition to stop the GA run early if it's no longer improving.
# This prevents wasting time on a run that has plateaued.
# Analogy: A "mercy rule" in a sports game. If one team is ahead by too much for too long, the game ends.
# Example & Effect:
#   - "saturate_15": Stops if the best fitness score doesn't improve for 15 consecutive generations. (Good default)
#   - "saturate_25": More lenient; gives the GA more time to try and find a better solution.
#   - None: Disables the stop criteria, forcing the GA to run for all NUM_GENERATIONS.
STOP_CRITERIA: str | None = "saturate_50"


# POPULATION_SIZE
# Explanation: The number of unique strategies (individuals) tested in each generation.
# A larger population explores more diverse solutions simultaneously.
# Analogy: The number of contestants in each round of a tournament.
# Example & Effect:
#   - 50 (Smaller): Faster, narrower search. Good for quick tests but might miss optimal strategies.
#   - 200 (Larger): Slower, more comprehensive search. Less likely to get stuck on a suboptimal solution.
POPULATION_SIZE: int = 200

# NUM_GENERATIONS
# Explanation: The number of evolutionary cycles the algorithm will run. More generations
# allow the best strategies more time to refine and improve.
# Analogy: The number of rounds in your tournament.
# Example & Effect:
#   - 50 (Fewer): Finishes quickly but solutions may not be fully optimized.
#   - 1000 (Larger): A very deep search, allowing for significant improvement over time. Expect long run times.
NUM_GENERATIONS: int = 100

# CROSSOVER_PROBABILITY
# Explanation: The probability that two successful "parent" strategies will combine
# their parameters to create new "child" strategies for the next generation.
# Analogy: The likelihood that two champion athletes will have a child who inherits a mix of their best skills.
# Example & Effect:
#   - 0.6 (Lower): Preserves more successful strategies as-is, leading to slower, more stable evolution.
#   - 0.9 (Higher): Creates more new combinations, which can speed up convergence but may reduce diversity.
CROSSOVER_PROBABILITY: float = 0.8

# MUTATION_PROBABILITY
# Explanation: The probability that a single parameter ("gene") will be randomly changed.
# Mutation introduces new ideas and prevents the GA from getting stuck.
# Analogy: A "wild card" or a sudden spark of genius that discovers a new path to success.
# Example & Effect:
#   - 0.1 (Lower): A more focused search that refines existing strategies. Risks getting stuck.
#   - 0.7 (Higher): A more chaotic and exploratory search. Good for finding unique solutions but can slow down refinement.
MUTATION_PROBABILITY: float = 0.7

# KEEP_ELITISM
# Explanation: The number of the absolute best strategies from a generation that are
# guaranteed to pass to the next generation unchanged. Ensures you never lose your best result.
# Analogy: The "reigning champions" rule; winners automatically qualify for the next round.
# Example & Effect:
#   - 1: Guarantees the single best solution is never lost.
#   - 5: Preserves the top 5. Can speed up convergence but might reduce diversity if they dominate the gene pool.
KEEP_ELITISM: int = 5

# The following parameters control the specific algorithms for selection, crossover, and mutation.
# The defaults ('sss', 'single_point', 'random') are robust and well-suited for this problem.
PARENT_SELECTION_TYPE: str = "sss"
CROSSOVER_TYPE: str = "single_point"
MUTATION_TYPE: str = "random"

# --- Fitness Function Settings ---

# FITNESS_METRIC
# Explanation: Defines the goal of the optimization. The GA will try to maximize or minimize this value.
# The string must exactly match a key in the results dictionary from the backtester.
# Analogy: The scoring system for your tournament. Are you judging on total points, goal difference, or win record?
# Example & Effect:
#   - "final_portfolio_value": Aims for the highest possible ending SOL balance. Good for maximizing raw profit.
#   - "profit_factor": Aims for the best risk-to-reward ratio. Often produces more stable, consistent strategies.
FITNESS_METRIC: str = "final_portfolio_value" # Focus on ending portfolio value

# FITNESS_GOAL
# Explanation: Tells the GA whether to maximize or minimize the FITNESS_METRIC.
# Should be "max" for goals like profit and "min" for goals like drawdown.
FITNESS_GOAL: str = "max" # Maximize the metric

# GA_FITNESS_SAMPLE_SIZE
# Explanation: Instead of backtesting every solution against all training tokens,
# we test against a random sample. This dramatically speeds up the process
# and reduces memory pressure, fixing potential crashes.
# Example & Effect:
#  - 0: Disables sampling, uses all available training tokens. Most accurate but slowest.
#  - 30: Evaluates each strategy against 30 random tokens from the training set. A good balance of speed and accuracy.
GA_FITNESS_SAMPLE_SIZE: Union[int, None] = 300

# --- Data Settings ---
DATA_SPLIT: Dict[str, float] = {
    "training": 0.6,
    "validation": 0.2,
    "test": 0.2
}
HISTORICAL_DATA_START_TS: datetime = datetime(2025, 9, 20, 0, 0, 0)
HISTORICAL_DATA_END_TS: datetime = datetime(2025, 10, 12, 0, 0, 0)

# --- Backtester Settings ---
BACKTEST_INITIAL_CAPITAL: float = 100.0 # In SOL

# --- Multiprocessing Settings ---
# Explanation: The number of CPU cores to use for parallel processing.
# 'auto' is a good default, but for stability on systems with many cores,
# specifying a fixed number like "8" or "12" can prevent resource exhaustion.
MULTIPROCESSING_CORES: str = "12"

# --- Results ---
RESULTS_DIR: str = "ga_optimization_results"
DETAILED_LOG_FILENAME: str = "ga_detailed_trade_log.parquet"
```

#### 📄 `rl_config.py`
*path: `config/rl_config.py`*

```python
# config/rl_config.py
"""
Dedicated configuration constants and settings for the Reinforcement Learning Agent.
This file centralizes all parameters into a structured dictionary for different
operational modes like tuning, training, and fine-tuning.
"""
import torch as th

# --- NEW: Local cache for downloaded MLflow datasets ---
# Defines the local directory where feature stores downloaded from MLflow runs will be cached.
RL_LOCAL_CACHE_PATH = "data/rl_cache"
RL_FEATURE_STORE_VERSION = "0.1" # Kept for compatibility with ETL script versioning

# --- NEW: Feature Group Definitions ---
# Logically groups features for modular storage and loading in the ETL pipeline.
# This dictionary drives how data is partitioned in the feature store.
FEATURE_GROUPS = {
    'base_ohlcv': [
        'Open', 'High', 'Low', 'Close', 'volume_usd', 'buy_volume_usd',
        'sell_volume_usd', 'market_cap_sol', 'tx_buy_count', 'tx_sell_count', 'sol_price_avg',
        'mint' # IMPORTANT: Ensure 'mint' is part of the base features
    ],
    'static_and_age': [
        'rugcheck_score', 'socials_score', 'token_age_seconds'
    ],
    'price_change_and_volatility': [
        'price_change_15s', 'price_change_30s', 'volatility_15s',
        'atr_7', 'atr_14', 'bollinger_width'
    ],
    'momentum_indicators': [
        'rsi_3', 'rsi_6', 'cci_20', 'macd', 'macd_signal',
        'macd_histogram', 'adx_15s'
    ],
    'volume_and_flow': [
        'volume_change_15s', 'buy_sell_ratio', 'buy_sell_ratio_15s',
        'tx_buy_count_15s', 'tx_sell_count_15s', 'tx_total_count_15s',
        'ad_line', 'obv'
    ],
    'bollinger_bands': [
        'bollinger_upper', 'bollinger_lower'
    ],
    'emas': [
        'ema_short', 'ema_long'
    ]
}

# --- Central Configuration Dictionary ---
RL_CONFIG = {
    "common": {

        # --- MLFlow Experiment categories
        "MLFLOW_EXPERIMENT_TUNING":     "PumpTrader.RL Hyperparameter Tuning",
        "MLFLOW_EXPERIMENT_TRAINING":   "PumpTrader.RL PPO Training",
        "MLFLOW_EXPERIMENT_DATASET":    "PumpTrader.RL Dataset Generation",
        "MLFLOW_EXPERIMENT_ANALYSIS":   "PumpTrader.RL Feature Analysis",
        "MLFLOW_EXPERIMENT_BACKTESTING": "PumpTrader.RL Backtesting",

        # --- Hardware & Performance ---
        "DEVICE": "cuda" if th.cuda.is_available() else "cpu",

        # --- Training Data Configuration ---
        # DATA_START_DATE and DATA_END_DATE are now obsolete and removed.
        # The data source is determined by the selected MLflow dataset run.
        "MIN_TRADE_COUNT_FOR_DATASET": 50,

        # --- Caching and Data Splitting ---
        "CACHE_STRATEGY": "parquet",
        "DATA_SPLIT_RATIO": [0.8, 0.2],
        "DATA_SPLIT_RANDOM_SEED": 42,

        # --- Environment Configuration ---
        "ENV_INITIAL_BALANCE": 100.0,
        "ENV_MAX_CONCURRENT_POSITIONS": 5,
        "ENV_NUM_TOP_TOKENS_TO_OBSERVE": 10,
        "ENV_ACTION_BUY_THRESHOLD": 0.2,
        "ENV_ACTION_SELL_THRESHOLD": -0.2,
        "ENV_CAPITAL_PER_BUY_PERCENT": 0.95,
        "ENV_TIME_IN_POSITION_NORM_SECONDS": 36000.0,
        "ENV_EPS": 1e-9,  # Epsilon for safe division
        "ENV_MAX_STEPS_PER_EPISODE": 7200,
        "ENV_WARMUP_STEPS": 200,

        # --- Reward Function Configuration ---
        "REWARD_DENSE_WEIGHT": 1.0,
        "REWARD_SPARSE_WEIGHT": 0.2,
        "REWARD_PNL_WEIGHT": 0.5,
        "REWARD_RISK_WEIGHT": 0.2,
        "REWARD_POSITION_MANAGEMENT_WEIGHT": 0.2,
        "REWARD_EXECUTION_WEIGHT": 0.1,
        "MAX_EXPECTED_PNL_PER_TRADE_SOL": 1.0,

        # --- Feature Management ---
        "FEATURES_CONFIG": {
            'tx_sell_count': True,
            'market_cap_sol': True,
            'sol_price_avg': True,
            'price_change_15s': True,
            'price_change_30s': True,
            'volume_usd': True,
            'volume_change_15s': True,
            'volatility_15s': True,
            'buy_sell_ratio': True,
            'buy_sell_ratio_15s': True,
            'buy_volume_usd': True,
            'sell_volume_usd': True,
            'tx_buy_count_15s': True,
            'tx_sell_count_15s': True,
            'tx_total_count_15s': True,
            'rsi_3': True,
            'rsi_6': True,
            'atr_7': True,
            'atr_14': True,
            'cci_20': True,
            'ad_line': True,
            'macd': True,
            'macd_signal': True,
            'macd_histogram': True,
            'bollinger_upper': True,
            'bollinger_lower': True,
            'bollinger_width': True,
            'ema_short': True,
            'ema_long': True,
            'adx_15s': True,
            'obv': True,
            'rugcheck_score': True,
            'socials_score': True,
            'token_age_seconds': True
        }
    },
    "tune": {
        "N_CPU": 1,
        "DEVICE": "cuda",
        "PPO_TIMESTEPS_PER_TRIAL": 250_000,
        "OPTUNA_N_TRIALS": 50,
        "OPTUNA_TIMEOUT_SECONDS": 7200, # 4 hours
        "OPTUNA_PRUNER_N_WARMUP_STEPS": 5,
        "OPTUNA_PRUNER_N_MIN_TRIALS": 5,
    },
    "train": {
        "N_CPU": 16,
        "DEVICE": "cpu",
        "PPO_FINAL_MODEL_TIMESTEPS": 1_500_000,
        "PPO_EVAL_FREQ": 2048,
    },
    "finetune": {
        "N_CPU": 16,
        "DEVICE": "cpu",
        "PPO_FINAL_MODEL_TIMESTEPS": 150_000, # Shorter duration for fine-tuning
        "PPO_EVAL_FREQ": 2048,
    },
    "continue": {
        "N_CPU": 16,
        "DEVICE": "cpu",
        "PPO_FINAL_MODEL_TIMESTEPS": 1_500_000,
        "PPO_EVAL_FREQ": 2048,
    },
    "importance": {
        "N_CPU": 16,
        "DEVICE": "cpu", # Inference is typically faster on CPU
        # Use a very short number of steps, as we only need to complete single episodes
        "PPO_FINAL_MODEL_TIMESTEPS": 50_000, 
        "PPO_EVAL_FREQ": 1024, # Not critical for this mode, but good to have
    }
}

def get_config_for_mode(mode: str) -> dict:
    """Merges common config with mode-specific config."""
    if mode not in RL_CONFIG:
        raise ValueError(f"Unknown configuration mode: '{mode}'. Must be one of {list(RL_CONFIG.keys())}")

    # Start with a copy of the common configuration
    config = RL_CONFIG['common'].copy()
    # Update it with the mode-specific settings, overriding common ones if necessary
    config.update(RL_CONFIG[mode])
    return config

def get_active_features(config: dict) -> list[str]:
    """
    Reads the FEATURES_CONFIG dictionary from a given config
    and returns a list of feature names that are set to True.
    """
    features_config = config.get("FEATURES_CONFIG", {})
    # Return all features except 'mint', which is an identifier, not a training feature
    return [feature for feature, is_active in features_config.items() if is_active and feature != 'mint']
```

#### 📄 `__init__.py`
*path: `connectors/__init__.py`*

_This file is empty._

#### 📄 `dexscreener_api.py`
*path: `connectors/dexscreener_api.py`*

```python
import asyncio
import httpx
import json
import time
from datetime import datetime, timezone
from aiolimiter import AsyncLimiter
from typing import List

# Make sure to use your bot's logger
from bot_logger import logger
from state_manager import GlobalState
from database_handler import DatabaseClient

# --- API Configuration ---
# CORRECTED: Using the correct multi-token endpoint as per documentation
DEXSCREENER_API_BASE_URL = "https://api.dexscreener.com/tokens/v1/solana"
# DexScreener allows up to 30 token addresses per batch request
DEXSCREENER_BATCH_SIZE = 30

# --- Rate Limit and Cooldown Management ---
TARGET_RPM = 280  # Target requests per minute, well within typical limits
CONSECUTIVE_429_THRESHOLD = 3  # Lowered threshold for faster cooldown activation
COOLDOWN_MINUTES = 3
POLLING_INTERVAL_SECONDS = 30.0 # Interval between full polling cycles

class DexscreenerFetcher:
    def __init__(self, state: GlobalState, db_client: DatabaseClient):
        self.state = state
        self.db = db_client
        self.limiter = AsyncLimiter(TARGET_RPM, 60)
        self.client = httpx.AsyncClient(timeout=20.0)
        self._consecutive_429_errors = 0
        self._cooldown_until_timestamp = 0

    def _sanitize_for_comparison(self, data: dict) -> dict:
        """
        Removes volatile, non-market data keys from a response dictionary
        to allow for a meaningful comparison of market state.
        """
        sanitized_data = data.copy()
        # The 'info' key contains URLs with changing timestamps (e.g., for images),
        # which are not relevant for detecting a change in core market data.
        sanitized_data.pop('info', None)
        return sanitized_data

    async def _fetch_data_for_batch(self, token_batch: List[str]) -> List | None:
        """
        Fetches data for a batch of token addresses in a single API call.
        """
        if not token_batch:
            return None
        
        # Construct the URL with comma-separated token addresses
        url = f"{DEXSCREENER_API_BASE_URL}/{','.join(token_batch)}"
        
        try:
            async with self.limiter:
                response = await self.client.get(url)
            
            if response.status_code == 429:
                logger.warning(f"DEXScreener API returned HTTP 429 (Rate Limited) for batch starting with {token_batch[0]}.")
                self._consecutive_429_errors += 1
                return None

            response.raise_for_status()
            
            # Reset error count on a successful request
            self._consecutive_429_errors = 0
            
            data = response.json()
            
            # CORRECTED: The batch API returns a direct list of pair objects
            if isinstance(data, list):
                return data
            # Fallback for old endpoint format, just in case
            elif isinstance(data, dict) and "pairs" in data and isinstance(data["pairs"], list):
                logger.warning("DEXScreener API returned a dictionary with a 'pairs' key, but expected a direct list. Processing 'pairs' list anyway.")
                return data["pairs"]
            else:
                logger.warning(f"DEX Screener batch response not in expected list format. Response: {str(data)[:500]}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"DEXScreener API HTTP error for batch: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"DEXScreener API unexpected error for batch: {e}", exc_info=True)
        
        return None

    def _parse_pair_data(self, pair: dict, sol_price_usd: float) -> tuple | None:
        """
        Parses a single pair dictionary from the API response into a tuple for DB insertion.
        """
        try:
            base_token = pair.get('baseToken', {})
            mint_address = base_token.get('address')
            if not mint_address: return None
            
            txns = pair.get('txns', {})
            volume = pair.get('volume', {})
            price_change = pair.get('priceChange', {})
            liquidity = pair.get('liquidity', {})
            
            m5 = txns.get('m5', {})
            h1 = txns.get('h1', {})
            h6 = txns.get('h6', {})
            h24 = txns.get('h24', {})
            
            return (
                pair.get('pairAddress'), mint_address, datetime.now(timezone.utc),
                float(pair.get('priceUsd', 0)), float(pair.get('priceNative', 0)), sol_price_usd,
                liquidity.get('usd', 0), pair.get('marketCap', 0), pair.get('fdv', 0),
                volume.get('m5', 0), volume.get('h1', 0), volume.get('h6', 0), volume.get('h24', 0),
                price_change.get('m5', 0), price_change.get('h1', 0), price_change.get('h6', 0), price_change.get('h24', 0),
                m5.get('buys', 0), m5.get('sells', 0), h1.get('buys', 0), h1.get('sells', 0),
                h6.get('buys', 0), h6.get('sells', 0), h24.get('buys', 0), h24.get('sells', 0),
                json.dumps(pair) # Store the full original response
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error parsing pair data for mint {pair.get('baseToken',{}).get('address')}: {e}")
            return None

    async def _insert_data_batch(self, parsed_data: list):
        """
        Inserts a batch of parsed data into the dexscreener_data table.
        """
        if not parsed_data: return
        query = """
            INSERT INTO dexscreener_data (
                pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
                liquidity_usd, market_cap, fdv,
                volume_m5, volume_h1, volume_h6, volume_h24,
                price_change_m5, price_change_h1, price_change_h6, price_change_h24,
                buys_m5, sells_m5, buys_h1, sells_h1,
                buys_h6, sells_h6, buys_h24, sells_h24,
                full_response
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26)
        """
        async with self.db.pool.acquire() as conn:
            await conn.executemany(query, parsed_data)
        logger.debug(f"Saved {len(parsed_data)} new snapshots from DEX Screener to database.")

    async def _process_batch_response(self, pairs: List[dict]):
        """
        Processes a list of pairs from a batch API response, handling de-duplication
        and preparing data for insertion.
        """
        current_sol_price = await self.state.get_sol_price()
        if not current_sol_price:
            logger.warning("DEXScreener Processor: Cannot get SOL price from state. Using 0.0 for this batch.")
            current_sol_price = 0.0
            
        records_to_insert = []
        for pair_data in pairs:
            mint_address = pair_data.get('baseToken', {}).get('address')
            if not mint_address:
                continue

            # --- De-duplication Logic ---
            last_stored_response_str = await self.db.get_latest_dexscreener_response(mint_address)
            has_changed = True # Default to true if no previous data exists
            if last_stored_response_str:
                try:
                    last_stored_dict = json.loads(last_stored_response_str)
                    sanitized_last = self._sanitize_for_comparison(last_stored_dict)
                    sanitized_new = self._sanitize_for_comparison(pair_data)
                    if sanitized_last == sanitized_new:
                        has_changed = False
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse stored JSON for {mint_address}. Assuming data has changed.")

            if has_changed:
                #logger.debug(f"Data for {mint_address} has changed. Preparing for DB insert.")
                parsed_record = self._parse_pair_data(pair_data, current_sol_price)
                if parsed_record:
                    records_to_insert.append(parsed_record)
            # else:
            #     logger.debug(f"No meaningful data change for {mint_address}. Skipping database insert.")

        if records_to_insert:
            await self._insert_data_batch(records_to_insert)

    async def run(self):
        """The main worker loop that polls migrated tokens in batches."""
        logger.info("🚀 DEX Screener Fetcher worker started (Mode: Batch Processing).")

        while not self.state.shutdown_event.is_set():
            try:
                # --- Cooldown Check ---
                if time.time() < self._cooldown_until_timestamp:
                    cooldown_remaining = self._cooldown_until_timestamp - time.time()
                    logger.info(f"DEX Screener is in cooldown due to rate-limiting. Resuming in {cooldown_remaining:.0f} seconds.")
                    await self.state.wait_or_interrupt(timeout=cooldown_remaining)
                    continue

                # --- Fetch Tokens to Poll ---
                migrated_tokens = await self.db.get_all_migrated_tokens()
                
                if not migrated_tokens:
                    logger.debug("DEX Screener: No migrated tokens found. Waiting before next check.")
                    await self.state.wait_or_interrupt(timeout=POLLING_INTERVAL_SECONDS)
                    continue

                logger.debug(f"DEXScreener Fetcher: Starting new batch cycle for {len(migrated_tokens)} migrated tokens.")
                
                # --- Create Batches ---
                token_batches = [migrated_tokens[i:i + DEXSCREENER_BATCH_SIZE] for i in range(0, len(migrated_tokens), DEXSCREENER_BATCH_SIZE)]

                # --- Process Batches ---
                for batch in token_batches:
                    if self.state.shutdown_event.is_set():
                        break

                    # Check for cooldown activation before fetching
                    if self._consecutive_429_errors >= CONSECUTIVE_429_THRESHOLD:
                        self._cooldown_until_timestamp = time.time() + (COOLDOWN_MINUTES * 60)
                        logger.error(f"DEXScreener API rate limit threshold reached ({self._consecutive_429_errors} consecutive 429s). Entering cooldown for {COOLDOWN_MINUTES} minutes.")
                        self._consecutive_429_errors = 0
                        break # Break out of the batch loop to start cooldown

                    batch_pairs = await self._fetch_data_for_batch(batch)
                    
                    if batch_pairs:
                        await self._process_batch_response(batch_pairs)
                    else:
                        logger.debug(f"No pairs returned from API for batch starting with {batch[0]}. Skipping batch.")

                # --- Wait for Next Cycle ---
                if not (time.time() < self._cooldown_until_timestamp):
                    logger.debug(f"DEX Screener batch cycle complete. Waiting {POLLING_INTERVAL_SECONDS}s.")
                    await self.state.wait_or_interrupt(timeout=POLLING_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in DEX Screener Fetcher worker loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=60) # Longer wait on unexpected error
            
        logger.info("🛑 DEX Screener Fetcher worker shutting down.")
```

#### 📄 `live_trader_gmgn.py`
*path: `connectors/live_trader_gmgn.py`*

```python
# live_trader.py (GMGN API Version)

import os
import httpx # Using httpx for async requests
import base64
import time
import asyncio
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
# We won't use SolanaClient here as GMGN has its own send_transaction endpoint
# from solana.rpc.api import Client as SolanaClient
# from solana.rpc.types import TxOpts
# from solana.rpc.commitment import Confirmed

from bot_logger import logger
# Import your main config module to access TRADING_MODE and other settings
import config.config as bot_config # Use an alias

load_dotenv()

PRIVATE_KEY_STRING = os.getenv("SOLANA_PRIVATE_KEY")
# RPC_ENDPOINT is not directly used for sending if using GMGN's send_transaction,
# but good to have for other potential Solana interactions or if you choose to send yourself.
# RPC_ENDPOINT = os.getenv("RPC_ENDPOINT")

WALLET_KEYPAIR = None
WALLET_PUBLIC_KEY_STR = None

if PRIVATE_KEY_STRING:
    try:
        WALLET_KEYPAIR = Keypair.from_base58_string(PRIVATE_KEY_STRING)
        WALLET_PUBLIC_KEY_STR = str(WALLET_KEYPAIR.pubkey())
    except Exception as e:
        logger.error(f"Failed to load Solana wallet from private key: {e}")
        WALLET_KEYPAIR = None
        WALLET_PUBLIC_KEY_STR = None
else:
    if bot_config.TRADING_MODE in ["paper_trading", "live"]:
        logger.critical("SOLANA_PRIVATE_KEY not found in .env. 'paper_trading' and 'live' modes WILL FAIL.")


GMGN_API_HOST = "https://gmgn.ai"
GMGN_GET_SWAP_ROUTE_ENDPOINT = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/get_swap_route"
GMGN_SEND_TRANSACTION_ENDPOINT = f"{GMGN_API_HOST}/txproxy/v1/send_transaction"
GMGN_GET_TRANSACTION_STATUS_ENDPOINT = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/get_transaction_status"


async def get_gmgn_swap_transaction(
    token_in_address: str,
    token_out_address: str,
    in_amount_lamports: str, # Amount in lamports as string
    from_address: str,
    slippage_percent: float, # e.g., 10 for 10%
    fee_sol: float,          # e.g., 0.006 SOL
    is_anti_mev: bool = True # Default to true as it's a feature
):
    """
    Fetches the swap route and unsigned transaction from GMGN API.
    Returns the API response data or None on error.
    """
    params = {
        "token_in_address": token_in_address,
        "token_out_address": token_out_address,
        "in_amount": in_amount_lamports,
        "from_address": from_address,
        "slippage": slippage_percent,
        "fee": fee_sol, # Network priority fees and PRC node tip fees.
        "is_anti_mev": str(is_anti_mev).lower() # API expects bool as string 'true' or 'false'
    }
    logger.debug(f"GMGN get_swap_route params: {params}")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client: # Increased timeout
            response = await client.get(GMGN_GET_SWAP_ROUTE_ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"GMGN get_swap_route HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"GMGN get_swap_route Error: {e}", exc_info=True)
        return None


async def send_gmgn_signed_transaction(signed_tx_base64: str, is_anti_mev: bool = True):
    """
    Submits a signed transaction to GMGN's send_transaction endpoint.
    Returns the API response data or None on error.
    """
    payload = {
        "chain": "sol",
        "signedTx": signed_tx_base64,
        "isAntiMev": is_anti_mev # Optional, set 'true' when swap with JITO Anti-MEV.
    }
    logger.debug(f"GMGN send_transaction payload (signedTx omitted for brevity)")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client: # Increased timeout
            response = await client.post(GMGN_SEND_TRANSACTION_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"GMGN send_transaction HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"GMGN send_transaction Error: {e}", exc_info=True)
        return None


async def get_gmgn_transaction_status(tx_hash: str, last_valid_block_height: int):
    """
    Queries the status of a submitted transaction.
    Returns the API response data or None on error.
    """
    params = {
        "hash": tx_hash,
        "last_valid_height": last_valid_block_height
    }
    logger.debug(f"GMGN get_transaction_status params: {params}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(GMGN_GET_TRANSACTION_STATUS_ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"GMGN get_transaction_status HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"GMGN get_transaction_status Error: {e}", exc_info=True)
        return None


async def execute_live_gmgn_trade(
    trigger_price: float, # Price that triggered the trade logic, for paper trading simulation
    action: str, # "buy" or "sell"
    input_token_address: str, # e.g., SOL mint for a buy
    output_token_address: str, # e.g., Meme coin mint for a buy
    # Amount is of the input_token_address, in lamports if SOL or base units if token
    in_amount_lamports_str: str,
    slippage_percent: float, # e.g., 10 for 10%
    # Fee for GMGN API is network priority + RPC tip. We'll use your bot's "tip" config for this.
    network_and_tip_fee_sol: float,
    is_anti_mev: bool = True
):
    """
    Handles trade execution via GMGN API for paper and live modes.
    Returns a dictionary like the previous execute_live_pumpportal_trade.
    """
    current_trading_mode = bot_config.TRADING_MODE.lower()

    if current_trading_mode not in ["paper_trading", "live"]:
        logger.error(f"execute_live_gmgn_trade called with invalid mode: {current_trading_mode}")
        return {"success": False, "mode": current_trading_mode, "error": "Invalid trading mode"}

    if not WALLET_KEYPAIR or not WALLET_PUBLIC_KEY_STR:
        logger.error(f"[{current_trading_mode.upper()} MODE] Wallet not loaded. Cannot execute GMGN trade.")
        return {"success": False, "mode": current_trading_mode, "error": "Wallet not loaded"}

    # Step 1: Get Swap Route and Unsigned Transaction from GMGN
    route_response = await get_gmgn_swap_transaction(
        token_in_address=input_token_address,
        token_out_address=output_token_address,
        in_amount_lamports=in_amount_lamports_str,
        from_address=WALLET_PUBLIC_KEY_STR,
        slippage_percent=slippage_percent,
        fee_sol=network_and_tip_fee_sol,
        is_anti_mev=is_anti_mev
    )

    if not route_response or route_response.get("code") != 0 or "data" not in route_response or "raw_tx" not in route_response["data"]:
        error_msg = route_response.get("msg", "Failed to get swap route from GMGN") if route_response else "No response from GMGN get_swap_route"
        logger.error(f"[{current_trading_mode.upper()} MODE] GMGN API Error: {error_msg}. Full response: {route_response}")
        return {"success": False, "mode": current_trading_mode, "error": error_msg}

    try:
        # Extract unsigned transaction and necessary details
        raw_tx_data = route_response["data"]["raw_tx"]
        swap_transaction_b64 = raw_tx_data["swapTransaction"] # This is base64 encoded
        last_valid_block_height = raw_tx_data["lastValidBlockHeight"] # For status query
        # recent_blockhash = raw_tx_data["recentBlockhash"] # Available if needed

        quote_data = route_response["data"].get("quote", {})
        expected_out_amount_lamports_str = quote_data.get("outAmount", "0")
        
        # Decode and deserialize the transaction
        swap_transaction_bytes = base64.b64decode(swap_transaction_b64)
        unsigned_tx = VersionedTransaction.deserialize(swap_transaction_bytes) # Deserialize from bytes

        # Sign the transaction
        unsigned_tx.sign([WALLET_KEYPAIR]) # Sign with your Keypair object
        signed_tx_bytes = unsigned_tx.serialize()
        signed_tx_b64 = base64.b64encode(signed_tx_bytes).decode('utf-8') # Encode to base64 string for sending
        
        tx_signature_str_from_local_signing = str(unsigned_tx.signatures[0])


        if current_trading_mode == "paper_trading":
            logger.info(f"[PAPER TRADING] GMGN: Prepared TX for {action} {input_token_address} -> {output_token_address}. Sig_prefix: {tx_signature_str_from_local_signing[:10]}... NOT SENDING.")
            
            # Simulate fill:
            # Use the expected_out_amount from the quote for paper trading.
            # If buying tokens (output is token), quantity_exchanged is tokens.
            # If selling tokens (output is SOL), quantity_exchanged is SOL.
            quantity_exchanged_simulated = 0.0
            try:
                quantity_exchanged_simulated = int(expected_out_amount_lamports_str)
                # Convert to human-readable units if needed for P&L (e.g., SOL or token decimals)
                # Assuming trigger_price is price of output_token in terms of input_token_units (e.g. lamports_in / tokens_out)
                # Or, if it's SOL/Token, and input is SOL, then expected_out_amount is tokens.
                # Price is input_amount / output_amount
                # If action is "buy", input is SOL, output is TOKEN. executed_price is SOL_per_TOKEN.
                # Price = in_amount_lamports / expected_out_amount_tokens
                if action == "buy" and input_token_address == "So11111111111111111111111111111111111111112": # Buying with SOL
                    if quantity_exchanged_simulated > 0: # quantity_exchanged_simulated is tokens
                        sim_executed_price_sol_per_token = int(in_amount_lamports_str) / quantity_exchanged_simulated
                    else: sim_executed_price_sol_per_token = trigger_price # Fallback
                elif action == "sell" and output_token_address == "So11111111111111111111111111111111111111112": # Selling for SOL
                    # quantity_exchanged_simulated is SOL lamports. input_amount_lamports_str is token units.
                    if int(in_amount_lamports_str) > 0:
                         sim_executed_price_sol_per_token = quantity_exchanged_simulated / int(in_amount_lamports_str)
                    else: sim_executed_price_sol_per_token = trigger_price # Fallback
                else:
                    sim_executed_price_sol_per_token = trigger_price # Fallback for other cases

            except ValueError:
                logger.warning("[PAPER TRADING] Could not parse expected_out_amount for simulation.")
                sim_executed_price_sol_per_token = trigger_price

            return {
                "success": True, "mode": "paper_trading", "signature": f"PAPER_{tx_signature_str_from_local_signing}",
                "executed_price": sim_executed_price_sol_per_token,
                "quantity_exchanged": quantity_exchanged_simulated, # This is in lamports/base units of output_token
                "error": None, "last_valid_block_height": last_valid_block_height
            }

        elif current_trading_mode == "live":
            logger.info(f"[LIVE TRADING] GMGN: Sending signed TX for {action} {input_token_address} -> {output_token_address}. Local Sig: {tx_signature_str_from_local_signing}")
            
            send_response = await send_gmgn_signed_transaction(signed_tx_b64, is_anti_mev)

            if not send_response or send_response.get("code") != 0 or "data" not in send_response or not send_response["data"].get("hash"):
                error_msg = send_response.get("msg", "Failed to send transaction via GMGN") if send_response else "No response from GMGN send_transaction"
                logger.error(f"[LIVE TRADING] GMGN send_transaction API Error: {error_msg}. Full response: {send_response}")
                return {"success": False, "mode": "live", "error": error_msg}

            actual_tx_hash_from_gmgn = send_response["data"]["hash"]
            logger.info(f"Live {action} submitted via GMGN. GMGN Hash: {actual_tx_hash_from_gmgn}")
            logger.info(f"Track on Solscan (using GMGN hash): https://solscan.io/tx/{actual_tx_hash_from_gmgn}")
            logger.info(f"Original local signature was: {tx_signature_str_from_local_signing}")


            # --- Transaction Confirmation Polling ---
            confirmed = False
            expired = False
            poll_attempts = 0
            max_poll_attempts = 60 # Poll for up to 60 seconds (60 * 1s sleep)

            while not confirmed and not expired and poll_attempts < max_poll_attempts:
                await asyncio.sleep(1) # Wait 1 second between status checks
                poll_attempts += 1
                logger.debug(f"Polling GMGN tx status for {actual_tx_hash_from_gmgn}, attempt {poll_attempts}")
                status_response = await get_gmgn_transaction_status(actual_tx_hash_from_gmgn, last_valid_block_height)

                if status_response and status_response.get("code") == 0 and "data" in status_response:
                    status_data = status_response["data"]
                    if status_data.get("success") is True: # Transaction successfully added to the blockchain
                        confirmed = True
                        logger.info(f"✅ GMGN Transaction Confirmed: {actual_tx_hash_from_gmgn}")
                    elif status_data.get("expired") is True: # Transaction expired
                        expired = True
                        logger.warning(f"⚠️ GMGN Transaction Expired: {actual_tx_hash_from_gmgn}. Needs resubmission.")
                    elif status_data.get("failed") is True: # Transaction failed on-chain
                        expired = True # Treat as terminal
                        logger.error(f"❌ GMGN Transaction Failed on-chain: {actual_tx_hash_from_gmgn}. Details: {status_data}")
                    else:
                        logger.debug(f"GMGN Tx {actual_tx_hash_from_gmgn} status pending...")
                else:
                    logger.warning(f"Could not get valid status for GMGN tx {actual_tx_hash_from_gmgn}. Response: {status_response}")
            
            if not confirmed and not expired:
                 logger.warning(f"GMGN Tx {actual_tx_hash_from_gmgn} status unclear after {max_poll_attempts} attempts. Assuming not confirmed for now.")


            # For live mode, ideally, you'd parse the confirmed transaction from Solana chain
            # to get actual in/out amounts. GMGN quote gives `expected_out_amount`.
            live_quantity_exchanged = 0.0
            live_executed_price = trigger_price # Fallback
            if confirmed:
                try:
                    live_quantity_exchanged = int(expected_out_amount_lamports_str) # Use the quoted out amount
                    if action == "buy" and input_token_address == "So11111111111111111111111111111111111111112":
                        if live_quantity_exchanged > 0: live_executed_price = int(in_amount_lamports_str) / live_quantity_exchanged
                except ValueError:
                    logger.warning("[LIVE TRADING] Could not parse expected_out_amount for confirmed trade.")
            
            return {
                "success": confirmed, "mode": "live", "signature": actual_tx_hash_from_gmgn,
                "executed_price": live_executed_price, # This is an estimate based on quote
                "quantity_exchanged": live_quantity_exchanged, # Lamports/base units of output token, from quote
                "error": "Transaction expired or failed on-chain" if expired and not confirmed else ("Polling timed out" if not confirmed and not expired else None),
                "last_valid_block_height": last_valid_block_height
            }

    except Exception as e:
        logger.error(f"[{current_trading_mode.upper()} MODE] GMGN Unhandled Error in execute_live_gmgn_trade: {e}", exc_info=True)
        return {"success": False, "mode": current_trading_mode, "error": str(e)}
```

#### 📄 `live_trader_pumpportal.py`
*path: `connectors/live_trader_pumpportal.py`*

```python
import os
import httpx
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client as SolanaClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed

from bot_logger import logger
# Import your main config module to access TRADING_MODE and other settings
import config.config as bot_config # Use an alias to avoid confusion if config is passed

load_dotenv()

PRIVATE_KEY_STRING = os.getenv("SOLANA_PRIVATE_KEY")
RPC_ENDPOINT = os.getenv("RPC_ENDPOINT")

WALLET_KEYPAIR = None
WALLET_PUBLIC_KEY = None
SOLANA_CLIENT = None

# Initialize wallet and client only if essential keys are present
# This allows the module to be imported even if keys are not set (e.g., for pure "simulate" mode)
if PRIVATE_KEY_STRING:
    try:
        WALLET_KEYPAIR = Keypair.from_base58_string(PRIVATE_KEY_STRING)
        WALLET_PUBLIC_KEY = str(WALLET_KEYPAIR.pubkey())
    except Exception as e:
        logger.error(f"Failed to load Solana wallet from private key: {e}")
        # Bot should not proceed to live/paper if wallet fails
        WALLET_KEYPAIR = None 
        WALLET_PUBLIC_KEY = None

if RPC_ENDPOINT:
    SOLANA_CLIENT = SolanaClient(RPC_ENDPOINT)
else:
    if bot_config.TRADING_MODE in ["paper_trading", "live"]:
        logger.warning("RPC_ENDPOINT not found in .env. 'paper_trading' and 'live' modes will fail to send transactions.")

PUMPORTAL_LOCAL_API_URL = bot_config._PUMPORTAL_LOCAL_API_URL

async def execute_live_pumpportal_trade(
    # Pass the specific price that triggered the buy/sell for paper trading simulation
    trigger_price: float,
    action: str,
    mint_address: str,
    amount_str: str, # Amount as a string (SOL or token units)
    denominated_in_sol: bool,
    slippage_percent: int,
    priority_fee_sol: float,
    pool: str = "auto"
):
    """
    Handles interaction with PumpPortal Local API for paper and live trading.
    Returns a dictionary:
    {
        "success": bool,
        "mode": str ("paper_trading" or "live"),
        "signature": str or None,
        "executed_price": float (actual or simulated),
        "quantity_exchanged": float (tokens bought/sold, or SOL received),
        "error": str or None
    }
    """
    # Use TRADING_MODE from the global bot_config
    current_trading_mode = bot_config.TRADING_MODE

    if current_trading_mode not in ["paper_trading", "live"]:
        logger.error(f"execute_live_pumpportal_trade called with invalid mode: {current_trading_mode}")
        return {"success": False, "mode": current_trading_mode, "error": "Invalid trading mode for live execution function"}

    if not WALLET_KEYPAIR or not WALLET_PUBLIC_KEY:
        logger.error(f"[{current_trading_mode.upper()} MODE] Wallet not loaded. Cannot execute trade.")
        return {"success": False, "mode": current_trading_mode, "error": "Wallet not loaded"}

    if current_trading_mode == "live" and not SOLANA_CLIENT:
        logger.error(f"[LIVE MODE] Solana client (RPC) not initialized. Cannot send transaction.")
        return {"success": False, "mode": "live", "error": "RPC client not initialized"}

    payload = {
        "publicKey": WALLET_PUBLIC_KEY,
        "action": action,
        "mint": mint_address,
        "amount": amount_str,
        "denominatedInSol": "true" if denominated_in_sol else "false",
        "slippage": slippage_percent,
        "priorityFee": priority_fee_sol,
        "pool": pool
    }

    logger.debug(f"[{current_trading_mode.upper()} MODE] Preparing API call to PumpPortal: {payload}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(PUMPORTAL_LOCAL_API_URL, data=payload) # Assuming form data
            response.raise_for_status()
        
        raw_tx_bytes = response.content
        unsigned_tx = VersionedTransaction.from_bytes(raw_tx_bytes)
        signed_tx = WALLET_KEYPAIR.sign_transaction(unsigned_tx)
        tx_signature_str = str(signed_tx.signatures[0])

        if current_trading_mode == "paper_trading":
            logger.info(f"[PAPER TRADING] Prepared TX for {action} on {mint_address}. Sig_prefix: {tx_signature_str[:10]}... NOT SENDING.")
            
            # Simulate fill for paper trading:
            # Use the trigger_price as the basis for simulation.
            # This is a simplified simulation. A real paper trader might fetch fresh quotes.
            quantity_exchanged_simulated = 0.0
            if denominated_in_sol and action == "buy": # Buying tokens with SOL
                if trigger_price > 0:
                    quantity_exchanged_simulated = float(amount_str) / trigger_price # Tokens bought
            elif not denominated_in_sol and action == "sell": # Selling tokens for SOL
                quantity_exchanged_simulated = float(amount_str) * trigger_price # SOL received
            else: # Selling SOL for tokens (less common for this param structure) or buying tokens with tokens
                 logger.warning(f"[PAPER TRADING] Complex simulation for {action} where denominatedInSol={denominated_in_sol}. Using 0 for quantity_exchanged.")


            return {
                "success": True, "mode": "paper_trading", "signature": f"PAPER_{tx_signature_str}",
                "executed_price": trigger_price, # Assume filled at the price that triggered the logic
                "quantity_exchanged": quantity_exchanged_simulated,
                "error": None
            }

        elif current_trading_mode == "live":
            if not SOLANA_CLIENT: # Should have been caught earlier, but double check
                return {"success": False, "mode": "live", "error": "RPC client not initialized for sending"}

            logger.info(f"[LIVE TRADING] Sending TX for {action} on {mint_address}. Sig: {tx_signature_str}")
            # Using skip_preflight=False for safety, you can change it
            options = TxOpts(skip_preflight=False, preflight_commitment=Confirmed) # Use preflight for safety
            
            tx_receipt = SOLANA_CLIENT.send_raw_transaction(txn=bytes(signed_tx), opts=options)
            actual_tx_signature = str(tx_receipt.value)
            
            logger.info(f"Live {action} submitted. Signature: {actual_tx_signature}")
            logger.info(f"Track on Solscan: https://solscan.io/tx/{actual_tx_signature}")

            # TODO: Implement robust transaction confirmation polling here.
            # TODO: After confirmation, fetch transaction details to get *actual* fill price and amounts.
            # This is critical for accurate P&L in live mode.
            # For now, we'll return success upon sending and use trigger_price as a placeholder.
            
            # Placeholder: In a real system, these would come from confirmed transaction details
            # If denominated_in_sol (buy with SOL): quantity_exchanged = tokens received
            # If not denominated_in_sol (sell tokens): quantity_exchanged = SOL received
            live_quantity_exchanged = 0.0
            if denominated_in_sol and action == "buy":
                 if trigger_price > 0: live_quantity_exchanged = float(amount_str) / trigger_price # Approx tokens
            elif not denominated_in_sol and action == "sell":
                 live_quantity_exchanged = float(amount_str) * trigger_price # Approx SOL

            return {
                "success": True, "mode": "live", "signature": actual_tx_signature,
                "executed_price": trigger_price, # Placeholder: replace with actual fill price
                "quantity_exchanged": live_quantity_exchanged, # Placeholder: replace with actual quantity
                "error": None
            }

    except httpx.HTTPStatusError as e:
        error_message = f"HTTP Error: {e.response.status_code} - {e.response.text}"
        logger.error(f"[{current_trading_mode.upper()} MODE] {error_message}", exc_info=True)
        return {"success": False, "mode": current_trading_mode, "error": error_message}
    except Exception as e:
        logger.error(f"[{current_trading_mode.upper()} MODE] Error: {e}", exc_info=True)
        return {"success": False, "mode": current_trading_mode, "error": str(e)}
```

#### 📄 `rugcheck_handler.py`
*path: `connectors/rugcheck_handler.py`*

```python
"""
rugcheck.py - Manages fetching RugCheck data, prioritization, and processing.
"""

import asyncio
import os
import json
import time
from datetime import datetime, timezone, timedelta
import traceback
import httpx
import base58
from dotenv import load_dotenv
from aiolimiter import AsyncLimiter
from decimal import Decimal
from solders.keypair import Keypair # type: ignore

from config.config import (
    _RUGCHECK_AUTH_API, _RUGCHECK_RATE_LIMIT, _RUGCHECK_API, _RUGCHECK_INTERVAL,
    RUGCHECK_SCORE_THRESHOLD, RUGCHECK_REQUEUE_PRIORITY_BOOST_PURCHASED,
    RUGCHECK_REQUEUE_INTERVAL_MINUTES, RUGCHECK_MAX_INITIAL_ATTEMPTS,
    RUGCHECK_MAX_DEPRIORITIZED_ATTEMPTS
)
from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState
from connectors.websocket_handler import WebSocketHandler
from socials_processor import SocialsProcessor

# --- Configuration for Retries & Maintenance ---
DEPRIORITIZED_PRIORITY = float('inf')
DEPRIORITIZED_TOKEN_MAX_AGE_SECONDS = 3600 # e.g., 1 hour: Time after which a deprioritized token might be culled
RUGCHECK_REQUEST_TIMEOUT = 20.0
RUGCHECK_MAINTENANCE_URL = "https://api.rugcheck.xyz/v1/maintenance"
MAINTENANCE_CHECK_TIMEOUT = 10.0
CONSECUTIVE_API_ERROR_LIMIT_FOR_MAINTENANCE_CHECK = 5 # How many /report errors trigger maintenance check
MAINTENANCE_MODE_RECHECK_INTERVAL_SECONDS = 600  # 5 minutes
MAINTENANCE_ENDPOINT_FAILURES_THRESHOLD = 3 # How many times maintenance endpoint must fail to assume active maintenance

class Rugcheck:
    def __init__(self, state: GlobalState, db_client: DatabaseClient, websocket_handler: WebSocketHandler, socials_processor: SocialsProcessor, config_dict: dict):
        self.state = state
        self.config = config_dict
        self.db_client = db_client
        self.websocket_handler = websocket_handler
        self.limiter = AsyncLimiter(max_rate=_RUGCHECK_RATE_LIMIT, time_period=_RUGCHECK_INTERVAL)
        self.queue = self.state.get_rugcheck_queue()
        self.fetch_attempts = {}
        self.deprioritized_tokens_tracker = {} # Stores {mint: {'first_deprio_timestamp': datetime, 'reprocess_count': int}}
        self.jwt_token: str | None = None
        self.wallet: Keypair | None = None
        
        # --- NEW State Variables for Maintenance Handling ---
        self.maintenance_mode_active = False
        self.consecutive_api_errors = 0 # For the main /report endpoint
        self.consecutive_maintenance_check_failures = 0
        # ---

        load_dotenv()
        private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
        if private_key_str:
            try:
                self.wallet = Keypair.from_base58_string(private_key_str)
                logger.info("🔑 Solana wallet loaded successfully for RugCheck authentication.")
            except Exception as e:
                logger.error(f"❌ Failed to load Solana wallet from private key: {e}")
                self.wallet = None
        else:
            logger.warning("⚠️ SOLANA_PRIVATE_KEY not set. RugCheck API calls will be unauthenticated.")

    def _sign_message(self, message: str) -> dict | None:
        if not self.wallet:
            logger.error("Cannot sign message: Wallet not loaded.")
            return None
        try:
            message_bytes = message.encode("utf-8")
            signature = self.wallet.sign_message(message_bytes)
            signature_base58 = str(signature)
            signature_data = list(base58.b58decode(signature_base58))
            return {
                "data": signature_data,
                "type": "ed25519",
            }
        except Exception as e:
            logger.error(f":police_car_light: Error signing message: {e}", exc_info=True)
            return None

    async def _login_to_rugcheck(self) -> bool:
        if not self.wallet:
            logger.warning("Skipping RugCheck login: Wallet not loaded.")
            return False
        logger.info("🔑 Attempting to login to RugCheck API...")
        try:
            message_data = {
                "message": "Sign-in to Rugcheck.xyz",
                "timestamp": int(time.time() * 1000),
                "publicKey": str(self.wallet.pubkey()),
            }
            message_json = json.dumps(message_data, separators=(',', ':'))
            signature = self._sign_message(message_json)
            if not signature: return False
            payload = {"signature": signature, "wallet": str(self.wallet.pubkey()), "message": message_data}
            async with httpx.AsyncClient(timeout=RUGCHECK_REQUEST_TIMEOUT) as client:
                response = await client.post(_RUGCHECK_AUTH_API, headers={"Content-Type": "application/json"}, json=payload)
            if response.status_code == 200:
                self.jwt_token = response.json().get("token")
                if self.jwt_token:
                    logger.info("✅ RugCheck API login successful.")
                    return True
                logger.error("❌ RugCheck login response missing token.")
            else:
                logger.error(f"❌ Failed to login to RugCheck API: {response.status_code} - {response.text}")
            self.jwt_token = None
            return False
        except httpx.TimeoutException:
             logger.error(f"⏳ Timeout during RugCheck API login.")
        except Exception as e:
            logger.error(f":police_car_light: Unexpected error during RugCheck API login: {e}", exc_info=True)
        self.jwt_token = None
        return False

    async def _check_api_maintenance_status(self):
        """Checks the RugCheck API maintenance status."""
        logger.debug("Checking RugCheck API maintenance status...")
        try:
            async with httpx.AsyncClient(timeout=MAINTENANCE_CHECK_TIMEOUT) as client:
                response = await client.get(RUGCHECK_MAINTENANCE_URL)

            if response.status_code == 200:
                try:
                    data = response.json()
                    message = data.get("message", "")
                    logger.info(f"RugCheck API maintenance check OK (Status: {response.status_code}, Message: '{message}'). Service is responsive.")
                except json.JSONDecodeError:
                    if response.headers.get('content-length') == '0':
                         logger.info(f"RugCheck API maintenance check OK (Status: {response.status_code}, Empty Body). Service is responsive.")
                    else:
                        logger.warning(f"RugCheck API maintenance check returned 200 but with invalid JSON body: {response.text[:100]}")
                        self.consecutive_maintenance_check_failures += 1

                if self.consecutive_maintenance_check_failures == 0 or response.status_code == 200 :
                    self.maintenance_mode_active = False
                    self.consecutive_maintenance_check_failures = 0

            else:
                logger.warning(f"RugCheck API maintenance check failed or indicated issue: Status {response.status_code} - {response.text}")
                self.consecutive_maintenance_check_failures += 1

        except httpx.TimeoutException:
            logger.error("⏳ Timeout checking RugCheck API maintenance status.")
            self.consecutive_maintenance_check_failures += 1
        except httpx.RequestError as e:
            logger.error(f":police_car_light: Request error checking RugCheck API maintenance status: {e}")
            self.consecutive_maintenance_check_failures += 1
        except Exception as e:
            logger.error(f":police_car_light: Unexpected error checking RugCheck API maintenance status: {e}", exc_info=True)
            self.consecutive_maintenance_check_failures += 1

        if self.consecutive_maintenance_check_failures >= MAINTENANCE_ENDPOINT_FAILURES_THRESHOLD:
            if not self.maintenance_mode_active:
                logger.error(f"🚨 RugCheck API assumed to be in maintenance/unavailable after {self.consecutive_maintenance_check_failures} failed checks to maintenance endpoint. Pausing Rugcheck tasks.")
            self.maintenance_mode_active = True
        elif self.maintenance_mode_active and self.consecutive_maintenance_check_failures == 0 :
            logger.info("✅ RugCheck API maintenance mode appears to have ended.")
            self.maintenance_mode_active = False

    async def _refresh_queue(self):
        """Refreshes the queue with new, unchecked tokens."""
        try:
            sol_price = await self.state.get_sol_price()
            if sol_price is None:
                logger.warning("⚠ SOL_PRICE not updated yet; skipping RugCheck queue refresh.")
                return False

            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    WITH ranked_tokens AS (
                        SELECT
                            t.mint,
                            t.timestamp,
                            COALESCE(SUM(tr.sol_amount), 0) AS total_volume,
                            COALESCE(SUM(CASE WHEN tr.tx_type = 'buy' THEN tr.sol_amount END), 0) AS buy_volume,
                            ROW_NUMBER() OVER (ORDER BY t.timestamp ASC) AS row_num
                        FROM tokens t
                        LEFT JOIN rugcheck r ON t.mint = r.mint
                        LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '15 minutes'
                        WHERE t.is_active = TRUE AND r.mint IS NULL
                        GROUP BY t.mint, t.timestamp
                    )
                    SELECT
                        mint,
                        (total_volume + buy_volume + (1.0 - row_num * 0.001)) AS priority_score
                    FROM ranked_tokens;
                """)

                logger.debug(f"🔍 Found {len(rows)} active tokens missing RugCheck data for refresh.")
                if rows:
                    for row in rows:
                        mint = row["mint"]
                        priority_score = row["priority_score"] or Decimal(0)
                        priority = -float(priority_score)
                        current_attempts = self.fetch_attempts.get(mint, 0)
                        if current_attempts < self.config.get('RUGCHECK_MAX_INITIAL_ATTEMPTS', 3):
                            await self.queue.put((priority, mint))

                    logger.debug(f"🔄 Refreshed RugCheck queue with {len(rows)} new tokens (current size: {self.queue.qsize()}).")
            return True
        except Exception as e:
            logger.error(f":police_car_light: Critical error in _refresh_queue: {e}", exc_info=True)
            return False

    async def _requeue_processed_tokens(self):
        """Identifies already-processed tokens and adds them back to the queue for re-checking."""
        try:
            async with self.db_client.pool.acquire() as conn:
                requeue_candidates = await conn.fetch("""
                    WITH TokenVolatility AS (
                        SELECT mint, STDDEV(price) / AVG(price) as volatility
                        FROM trades WHERE timestamp >= NOW() - INTERVAL '15 minutes' AND price > 0
                        GROUP BY mint HAVING COUNT(*) > 5
                    ),
                    TokenVolume AS (
                        SELECT mint, SUM(sol_amount) as volume
                        FROM trades WHERE timestamp >= NOW() - INTERVAL '15 minutes' GROUP BY mint
                    ),
                    RugcheckCounts AS (
                        SELECT mint, COUNT(*) AS check_count FROM rugcheck GROUP BY mint
                    )
                    SELECT
                        r.mint, COALESCE(rc.check_count, 0) as check_count,
                        COALESCE(tv.volatility, 0) as volatility, COALESCE(tvl.volume, 0) as volume,
                        CASE WHEN p.mint IS NOT NULL THEN TRUE ELSE FALSE END as is_purchased
                    FROM rugcheck r
                    JOIN tokens t ON r.mint = t.mint
                    LEFT JOIN RugcheckCounts rc ON r.mint = rc.mint
                    LEFT JOIN TokenVolatility tv ON r.mint = tv.mint
                    LEFT JOIN TokenVolume tvl ON r.mint = tvl.mint
                    LEFT JOIN portfolio p ON r.mint = p.mint AND p.status = 'active'
                    WHERE t.is_active = TRUE;
                """)

                if not requeue_candidates:
                    logger.debug("Re-queue check: No processed tokens found to re-evaluate.")
                    return

                requeued_count = 0
                for candidate in requeue_candidates:
                    mint = candidate['mint']
                    if mint in [item[1] for item in self.queue._queue]:
                        continue
                    base_priority = 0
                    if candidate['is_purchased']:
                        base_priority += self.config.get('RUGCHECK_REQUEUE_PRIORITY_BOOST_PURCHASED', 1000.0)
                    base_priority += float(candidate['volume']) * 10
                    base_priority += float(candidate['volatility']) * 50
                    
                    check_count = candidate['check_count']
                    final_priority_score = base_priority / (check_count ** 2) if check_count > 0 else base_priority
                    priority = -final_priority_score
                    
                    if final_priority_score > 1.0:
                        await self.queue.put((priority, mint))
                        requeued_count += 1
                        logger.debug(f"Re-queuing processed token {mint} with priority score: {final_priority_score:.2f}")

                if requeued_count > 0:
                    logger.info(f"Re-queued {requeued_count} processed tokens for another RugCheck.")

        except Exception as e:
            logger.error(f":police_car_light: Error during RugCheck re-queue process: {e}", exc_info=True)

    async def _fetch_and_store_data(self, mint: str, is_retry: bool = False) -> dict | None | str:
        url = f"{_RUGCHECK_API}/{mint}/report"
        response = None
        headers = {}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        else:
            logger.debug(f"Making unauthenticated RugCheck request for {mint}")

        try:
            async with httpx.AsyncClient(timeout=RUGCHECK_REQUEST_TIMEOUT) as client:
                logger.debug(f"📡 Fetching RugCheck for {mint} from {url}")
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data.get("error") == "failed to generate report cached":
                    logger.warning(f"⚠ RugCheck API for {mint} reported: failed to generate report cached.")
                    return 'GENERATION_ERROR'
                if not data or "score" not in data:
                    logger.warning(f"⚠ RugCheck data incomplete or invalid for {mint}. Response: {data}")
                    return 'GENERATION_ERROR'

                try:
                    token = data.get("token") or {}
                    tokenMeta = data.get("tokenMeta") or {}
                    fileMeta = data.get("fileMeta") or {}
                    transferFee = data.get("transferFee") or {}
                    risks_list = data.get("risks", [])
                    risks_json = json.dumps(risks_list) if isinstance(risks_list, list) else None
                    full_data_json = json.dumps(data)

                    detected_at = None
                    detected_at_str = data.get("detectedAt")
                    if detected_at_str:
                        try:
                            detected_at_str = detected_at_str.replace('Z', '+00:00')
                            if '.' in detected_at_str:
                                base, fraction = detected_at_str.split('.', 1)
                                tz_part = ""
                                if '+' in fraction:
                                    fraction, tz_part = fraction.split('+', 1)
                                    tz_part = '+' + tz_part
                                elif '-' in fraction:
                                     fraction, tz_part = fraction.split('-', 1)
                                     tz_part = '-' + tz_part
                                detected_at_str = f"{base}.{fraction[:6]}{tz_part}"
                            detected_at = datetime.fromisoformat(detected_at_str).astimezone(timezone.utc)
                        except ValueError as date_err:
                            logger.warning(f"Could not parse detectedAt '{data.get('detectedAt')}' for {mint}: {date_err}")
                            detected_at = datetime.now(timezone.utc)

                    async with self.db_client.pool.acquire() as conn:
                        async with conn.transaction():
                            token_exists = await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint)
                            if not token_exists:
                                logger.info(f"Token {mint} was deleted from DB while its RugCheck data was being fetched. Aborting DB storage.")
                                return 'TOKEN_DELETED_MID_FETCH'
                            await conn.execute('''
                                INSERT INTO rugcheck
                                (mint, tokenProgram, creator, token_mintAuthority, token_supply,
                                token_decimals, token_isInitialized, token_freezeAuthority,
                                tokenMeta_name, tokenMeta_symbol, tokenMeta_uri, tokenMeta_mutable,
                                tokenMeta_updateAuthority, freezeAuthority, mintAuthority, risks,
                                score, fileMeta_description, fileMeta_name, fileMeta_symbol,
                                fileMeta_image, totalMarketLiquidity, totalLPProviders, rugged,
                                tokenType, transferFee_pct, transferFee_maxAmount, transferFee_authority,
                                graphInsidersDetected, detectedAt, full_data, last_checked)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                                        $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26,
                                        $27, $28, $29, $30, $31, NOW())
                            ''',
                                mint, data.get("tokenProgram"), data.get("creator"),
                                token.get("mintAuthority"), token.get("supply"),
                                token.get("decimals"), token.get("isInitialized"),
                                token.get("freezeAuthority"), tokenMeta.get("name"),
                                tokenMeta.get("symbol"), tokenMeta.get("uri"),
                                tokenMeta.get("mutable"), tokenMeta.get("updateAuthority"),
                                data.get("freezeAuthority"), data.get("mintAuthority"),
                                risks_json, data.get("score"), fileMeta.get("description"),
                                fileMeta.get("name"), fileMeta.get("symbol"), fileMeta.get("image"),
                                data.get("totalMarketLiquidity"), data.get("totalLPProviders"),
                                data.get("rugged"), data.get("tokenType"),
                                transferFee.get("pct"), transferFee.get("maxAmount"),
                                transferFee.get("authority"), data.get("graphInsidersDetected"),
                                detected_at, full_data_json
                            )
                    logger.debug(f"💾 RugCheck data stored/updated for {mint}")
                    return data
                except Exception as db_err:
                    logger.error(f":police_car_light: DB Error storing RugCheck for {mint}: {db_err}", exc_info=True)
                    return 'DB_INSERT_ERROR'

            elif response.status_code == 404:
                return 'NOT_FOUND'
            elif response.status_code in [401, 403]:
                 logger.warning(f"🔑 RugCheck API returned {response.status_code} (Authorization Error) for {mint}.")
                 self.jwt_token = None
                 if not is_retry:
                     if await self._login_to_rugcheck():
                         return await self._fetch_and_store_data(mint, is_retry=True)
                 return 'AUTH_ERROR'
            else:
                logger.warning(f"⚠ RugCheck API returned HTTP {response.status_code} for {mint}. Response: {response.text}")
                return 'HTTP_ERROR'
        except httpx.TimeoutException:
            return 'TIMEOUT'
        except httpx.RequestError as req_err:
            return 'REQUEST_ERROR'
        except json.JSONDecodeError as json_err:
            response_text = response.text if response else "N/A"
            logger.error(f"❌ JSON Decode Error for RugCheck response {mint}: {json_err}. Response: {response_text[:100]}")
            return 'GENERATION_ERROR'
        except Exception as e:
            logger.error(f"❌ Unexpected Error fetching RugCheck data for {mint}: {e}", exc_info=True)
            return None

    async def _process_token(self, mint: str) -> bool | str:
        fetch_result = await self._fetch_and_store_data(mint)

        if isinstance(fetch_result, str):
            return fetch_result

        if fetch_result is None or fetch_result == 'DB_INSERT_ERROR':
            logger.warning(f"Processing failed for {mint}: Could not fetch/store RugCheck data due to error: {fetch_result}")
            return False

        fetched_data = fetch_result
        score = fetched_data.get("score")
        if score is not None and score > self.config.get('RUGCHECK_SCORE_THRESHOLD', 1002):
            logger.debug(f"🚨 High RugCheck score ({score} > {self.config['RUGCHECK_SCORE_THRESHOLD']}) for {mint}. Deactivating.")
            try:
                async with self.db_client.pool.acquire() as conn:
                    is_active_in_portfolio = await conn.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' LIMIT 1", mint)
                    if not is_active_in_portfolio:
                        await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                
                if self.websocket_handler:
                    await self.websocket_handler.unsubscribe_from_trades([mint], "high_rugcheckscore")
                    logger.debug(f"[bold]:hot_pepper: Too spicy:[/bold] Sent unsubscribe for high-score token {mint}")

                await self.db_client.backup_and_delete_token(mint=mint, archived_at=datetime.now(timezone.utc), reason="high_rugcheckscore")
                return True
            except Exception as deactivation_err:
                logger.error(f":police_car_light: Error during deactivation for high-score token {mint}: {deactivation_err}", exc_info=True)
                return True
        else:
            logger.debug(f"✅ RugCheck score OK for {mint} (Score: {score})")
            return True

    async def _worker(self):
        logger.info(":rocket: RugCheck worker started.")

        if self.wallet:
            await self._login_to_rugcheck()

        while not self.state.shutdown_event.is_set():
            task_completed_in_loop = False
            priority = None
            mint = None
            try:
                if self.maintenance_mode_active:
                    logger.info(f"🚨 RugCheck worker paused due to active maintenance mode. Re-checking API status in {MAINTENANCE_MODE_RECHECK_INTERVAL_SECONDS}s.")
                    await self.state.wait_or_interrupt(timeout=MAINTENANCE_MODE_RECHECK_INTERVAL_SECONDS)
                    await self._check_api_maintenance_status()
                    continue

                # --- START: REFACTORED QUEUE FILLING LOGIC ---
                if self.queue.empty():
                    logger.debug("RugCheck queue is empty. Attempting to refill...")
                    
                    # Priority 1: Refresh with new, unchecked tokens.
                    await self._refresh_queue()

                    # Priority 2: If still empty, requeue already processed tokens.
                    if self.queue.empty():
                        logger.info("No new tokens found. Checking for processed tokens to re-queue...")
                        await self._requeue_processed_tokens()

                    # If still empty after all attempts, wait before trying again.
                    if self.queue.empty():
                        logger.debug("No new or re-queueable tokens found. Waiting.")
                        await self.state.wait_or_interrupt(timeout=5) # Prevent busy-looping
                        continue
                # --- END: REFACTORED QUEUE FILLING LOGIC ---

                try:
                    priority, mint = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                except Exception as q_err:
                    logger.error(f":police_car_light: Error getting item from rugcheck queue: {q_err}"); continue

                if priority == DEPRIORITIZED_PRIORITY and mint in self.deprioritized_tokens_tracker:
                    tracker_entry = self.deprioritized_tokens_tracker[mint]
                    tracker_entry['reprocess_count'] += 1
                    age_seconds = (datetime.now(timezone.utc) - tracker_entry['first_deprio_timestamp']).total_seconds()

                    cull_reason = None
                    max_deprio_attempts = self.config.get('RUGCHECK_MAX_DEPRIORITIZED_ATTEMPTS', 5)
                    if age_seconds > DEPRIORITIZED_TOKEN_MAX_AGE_SECONDS:
                        cull_reason = f"exceeded max age ({DEPRIORITIZED_TOKEN_MAX_AGE_SECONDS}s)"
                    elif tracker_entry['reprocess_count'] > max_deprio_attempts:
                        cull_reason = f"exceeded max reprocess attempts ({max_deprio_attempts})"

                    if cull_reason:
                        logger.warning(f"🧹 Culling deprioritized token {mint} due to {cull_reason} for RugCheck.")
                        try:
                            if self.websocket_handler and self.websocket_handler.get_status().get('is_connected'):
                                try:
                                    await self.websocket_handler.unsubscribe_from_trades([mint], "rugcheck_error_culled")
                                    logger.info(f"🧹 Culled {mint}: Unsubscribed from WebSocket due to persistent RugCheck issues.")
                                except Exception as ws_err:
                                    logger.error(f":police_car_light: Error unsubscribing culled token {mint} from WebSocket: {ws_err}", exc_info=True)

                            await self.db_client.backup_and_delete_token(mint=mint, archived_at=datetime.now(timezone.utc), reason="rugcheck_error_culled")
                            logger.info(f"🧹 Culled {mint}: Backed up and deleted from DB with reason 'rugcheck_error_culled'.")
                        except Exception as e:
                            logger.error(f":police_car_light: Error during culling operations for deprioritized token {mint}: {e}", exc_info=True)
                        finally:
                            self.fetch_attempts.pop(mint, None)
                            self.deprioritized_tokens_tracker.pop(mint, None)
                            self.queue.task_done(); task_completed_in_loop = True
                            continue

                async with self.limiter:
                    async with self.db_client.pool.acquire() as conn:
                        is_active = await conn.fetchval("SELECT is_active FROM tokens WHERE mint = $1", mint)

                    if not is_active:
                        logger.debug(f"Token {mint} no longer active or exists. Skipping RugCheck.")
                        self.fetch_attempts.pop(mint, None)
                        self.deprioritized_tokens_tracker.pop(mint, None)
                        self.queue.task_done(); task_completed_in_loop = True
                        continue

                    process_status = await self._process_token(mint)
                    task_completed_in_loop = True

                    retryable_api_error_statuses = ['TIMEOUT', 'GENERATION_ERROR', 'HTTP_ERROR', 'REQUEST_ERROR']
                    max_initial_attempts = self.config.get('RUGCHECK_MAX_INITIAL_ATTEMPTS', 3)

                    if process_status is True:
                        self.fetch_attempts.pop(mint, None)
                        self.deprioritized_tokens_tracker.pop(mint, None)
                        self.consecutive_api_errors = 0
                    elif process_status in retryable_api_error_statuses:
                        self.consecutive_api_errors += 1
                        if self.consecutive_api_errors >= CONSECUTIVE_API_ERROR_LIMIT_FOR_MAINTENANCE_CHECK:
                            logger.warning(f"{self.consecutive_api_errors} consecutive API errors on /report. Checking API maintenance status...")
                            await self._check_api_maintenance_status()

                        current_attempts = self.fetch_attempts.get(mint, 0) + 1
                        self.fetch_attempts[mint] = current_attempts
                        logger.warning(f"🔄 RugCheck API failed for {mint} ({process_status}). Attempt {current_attempts}/{max_initial_attempts}.")
                        if current_attempts < max_initial_attempts:
                            await self.queue.put((priority, mint))
                        else:
                            await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                            logger.warning(f"Max fetch attempts ({max_initial_attempts}) reached for {mint} due to {process_status}. Deprioritizing.")
                            if mint not in self.deprioritized_tokens_tracker:
                                self.deprioritized_tokens_tracker[mint] = {'first_deprio_timestamp': datetime.now(timezone.utc), 'reprocess_count': 0}
                    elif process_status == 'NOT_FOUND':
                        current_attempts = self.fetch_attempts.get(mint, 0) + 1
                        self.fetch_attempts[mint] = current_attempts
                        logger.warning(f"❓ RugCheck API 404 for {mint}. Attempt {current_attempts}/{max_initial_attempts}.")
                        if current_attempts < max_initial_attempts:
                            await self.queue.put((priority, mint))
                        else:
                            await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                            logger.warning(f"Max 404 attempts for {mint}. Deprioritizing.")
                            if mint not in self.deprioritized_tokens_tracker:
                                self.deprioritized_tokens_tracker[mint] = {'first_deprio_timestamp': datetime.now(timezone.utc), 'reprocess_count': 0}
                        self.consecutive_api_errors = 0
                    elif process_status == 'AUTH_ERROR':
                        logger.error(f"🔑 Persistent RugCheck Auth Error for {mint}. Deprioritizing and marking max attempts.")
                        await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                        self.fetch_attempts[mint] = max_initial_attempts
                        if mint not in self.deprioritized_tokens_tracker:
                            self.deprioritized_tokens_tracker[mint] = {'first_deprio_timestamp': datetime.now(timezone.utc), 'reprocess_count': 0}
                        self.consecutive_api_errors = 0
                    elif process_status is False or process_status == 'DB_INSERT_ERROR':
                        logger.error(f"📉 RugCheck processing internal/DB error for {mint} (Status: {process_status}). Requeuing with original priority.")
                        await self.queue.put((priority, mint))
                        self.fetch_attempts.pop(mint, None)
                        self.deprioritized_tokens_tracker.pop(mint, None)

                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("⏹ RugCheck worker task cancelled.")
                if mint:
                    try: self.queue.task_done()
                    except ValueError: pass
                break
            except Exception as e:
                logger.error(f"💥 Unexpected error in RugCheck worker main loop: {e}", exc_info=True)
                if mint and not task_completed_in_loop:
                    try: self.queue.task_done()
                    except ValueError: pass
                await self.state.wait_or_interrupt(timeout=10)

        logger.info("🛑 RugCheck worker shutting down.")

    def start(self) -> asyncio.Task:
        """Creates and returns the asyncio task for the RugCheck worker."""
        logger.info("Creating RugCheck background task...")
        return asyncio.create_task(self._worker(), name="rugcheck_worker")
```

#### 📄 `sol_price_api.py`
*path: `connectors/sol_price_api.py`*

```python
import asyncio
import httpx
import json
from config.config import _SOL_PRICE_API_URL
from bot_logger import logger
from database_handler import DatabaseClient
from state_manager import GlobalState


async def update_sol_price(state: GlobalState, db_client: DatabaseClient):
    """Periodically fetches and updates the global SOL price from an external API."""
    logger.info("🚀 Starting update_sol_price task...")

    try:
        while True:
            if state.shutdown_event.is_set():
                logger.info("Shutdown event detected. Exiting update_sol_price task.")
                break

            try:
                # Fetch the SOL price from an external API
                async with httpx.AsyncClient() as client:
                    response = await client.get(_SOL_PRICE_API_URL, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        new_price = data.get("solana", {}).get("usd")
                        if new_price is None or not isinstance(new_price, (int, float)):
                            logger.error("Invalid or missing SOL price in API response.")
                            continue

                        # Update the in-memory state and database
                        #async with state.lock:
                        await state.set_sol_price(new_price)
                        await db_client.insert_sol_price(new_price)

                        logger.info(f"✅ Updated Solana price: {new_price} USD")
                    else:
                        logger.error(f"⚠ Error fetching Solana price. Status code: {response.status_code}, Response: {response.text}")
            except Exception as e:
                logger.error(f"❌ Exception in update_sol_price task: {e}", exc_info=True)

            logger.debug("⏳ Sleeping for 1 hour...")
            await state.wait_or_interrupt(timeout=3600)

    except asyncio.CancelledError:
        logger.info("⏹ update_sol_price task cancelled.")
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in update_sol_price task: {e}", exc_info=True)
    finally:
        logger.info("🛑 update_sol_price task finished.")
```

#### 📄 `telegram_monitor.py`
*path: `connectors/telegram_monitor.py`*

```python
import re
from bs4 import BeautifulSoup
import httpx
import asyncio

async def check_telegram_channel(tg_url: str) -> dict:
    """
    Checks a Telegram channel link for validity and extracts info.
    Works for both public (/s/) and private-style pages.

    Args:
        tg_url: The URL of the Telegram channel to check.

    Returns:
        A dictionary containing channel information.
    """
    result = {
        "valid": False,
        "title": None,
        "members": None,
        "online": None,
        "public_preview": False,
        "message_count": None,
        "error": None
    }

    # 1. Validate the link format
    match = re.search(r"t\.me/([a-zA-Z0-9_]+)", tg_url)
    if not match:
        result["error"] = "Invalid Telegram link format"
        return result

    username = match.group(1)
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # 2. Scrape the main channel page for basic info
        try:
            main_url = f"https://t.me/{username}"
            resp = await client.get(main_url, headers=headers)

            if resp.status_code != 200:
                result["error"] = f"HTTP Error: {resp.status_code}"
                return result

            soup = BeautifulSoup(resp.text, "html.parser")

            title_tag = soup.find("div", {"class": "tgme_page_title"})
            extra_tag = soup.find("div", {"class": "tgme_page_extra"})

            if not title_tag or not extra_tag:
                result["error"] = "Channel not found or page structure is unexpected."
                return result

            result["title"] = title_tag.get_text(strip=True)
            extra_text = extra_tag.get_text(strip=True).lower()

            # Updated regex to find 'members' or 'subscribers'
            member_match = re.search(r"([\d\s,]+)(?:members|subscribers)", extra_text.replace('\n', ' '))
            if member_match:
                result["members"] = int(re.sub(r"[\s,]", "", member_match.group(1)))

            online_match = re.search(r"([\d\s,]+)online", extra_text.replace('\n', ' '))
            if online_match:
                result["online"] = int(re.sub(r"[\s,]", "", online_match.group(1)))

            if result["title"] and result["members"] is not None:
                result["valid"] = True

        except httpx.RequestError as e:
            result["error"] = f"Network error while checking main link: {e}"
            return result
        except Exception as e:
            result["error"] = f"An unexpected error occurred: {e}"
            return result

        # 3. Scrape the public preview (/s/) page for message count
        if result["valid"]:
            try:
                public_url = f"https://t.me/s/{username}"
                resp_pub = await client.get(public_url, headers=headers)
                if resp_pub.status_code == 200:
                    soup_pub = BeautifulSoup(resp_pub.text, "html.parser")
                    
                    # FIX: A public preview only exists if message containers are found.
                    messages = soup_pub.find_all("div", {"class": "tgme_widget_message_wrap"})
                    if messages:
                        result["public_preview"] = True
                        result["message_count"] = len(messages)
            except Exception:
                # Silently fail if the public page can't be checked
                pass

    return result

def main():
    # Example usage
    #url = "https://t.me/flashorca"
    #url = "https://t.me/db_butt_token"  # Change to test different channels
    #url = "https://t.me/homelessdegens"  # Change to test different channels
    #url = "https://t.me/frogwifhat_FWIF"  # Change to test different channels
    url = "https://t.me/adzillaofficial"  # Change to test different channels
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(check_telegram_channel(url))
    print(result)

if __name__ == "__main__":
    main()
```

#### 📄 `telegram_sentiment.py`
*path: `connectors/telegram_sentiment.py`*

```python
# enhanced_telegram_monitor.py
from telethon import TelegramClient
from telethon.tl.types import Message, Channel
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from datetime import datetime, timedelta

@dataclass
class EnhancedTelegramData:
    messages: List[str]
    member_count: int
    online_count: int
    message_frequency: float  # messages per hour
    active_users: int
    admin_activity: bool
    media_share_ratio: float

class EnhancedTelegramMonitor:
    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self.client = TelegramClient('bot_session', api_id, api_hash)
        self.bot_token = bot_token
        self.monitored_groups = {}  # {group_id: last_message_id}
        
    async def connect(self):
        """Connect using bot credentials"""
        await self.client.start(bot_token=self.bot_token)
        logger.info("🤖 Telegram Bot connected successfully")
    
    async def join_and_monitor_group(self, group_link: str) -> bool:
        """Join a group and start monitoring it"""
        try:
            # Join the group using invite link
            group_entity = await self.client.get_entity(group_link)
            await self.client.join_channel(group_entity)
            
            # Store for monitoring
            self.monitored_groups[group_entity.id] = 0
            logger.info(f"✅ Joined and monitoring group: {group_entity.title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to join group {group_link}: {e}")
            return False
    
    async def scrape_private_group_messages(self, group_identifier, limit: int = 200) -> EnhancedTelegramData:
        """Scrape messages from private groups the bot has joined"""
        try:
            group_entity = await self.client.get_entity(group_identifier)
            
            # Get recent messages
            messages = []
            async for message in self.client.iter_messages(
                group_entity, 
                limit=limit,
                offset_date=datetime.now() - timedelta(hours=24)  # Last 24 hours only
            ):
                if message.text and message.text.strip():
                    messages.append({
                        'text': message.text,
                        'date': message.date,
                        'user_id': message.sender_id,
                        'is_admin': await self._is_admin(group_entity, message.sender_id)
                    })
            
            # Analyze group metrics
            group_metrics = await self._analyze_group_health(group_entity, messages)
            
            return EnhancedTelegramData(
                messages=[msg['text'] for msg in messages],
                member_count=group_metrics['member_count'],
                online_count=group_metrics['online_count'],
                message_frequency=group_metrics['message_frequency'],
                active_users=group_metrics['active_users'],
                admin_activity=group_metrics['admin_activity'],
                media_share_ratio=group_metrics['media_share_ratio']
            )
            
        except Exception as e:
            logger.error(f"❌ Error scraping private group {group_identifier}: {e}")
            return EnhancedTelegramData([], 0, 0, 0, 0, False, 0)
    
    async def _analyze_group_health(self, group_entity, messages: List) -> Dict:
        """Analyze group health metrics"""
        if not messages:
            return {
                'member_count': 0,
                'online_count': 0, 
                'message_frequency': 0,
                'active_users': 0,
                'admin_activity': False,
                'media_share_ratio': 0
            }
        
        # Get group info
        try:
            full_chat = await self.client.get_entity(group_entity)
            member_count = getattr(full_chat, 'participants_count', 0)
            online_count = getattr(full_chat, 'online_count', 0)
        except:
            member_count = online_count = 0
        
        # Calculate metrics
        time_span_hours = 24
        message_frequency = len(messages) / time_span_hours
        
        unique_users = len(set(msg['user_id'] for msg in messages))
        active_users = unique_users
        
        admin_activity = any(msg['is_admin'] for msg in messages)
        
        # Media share ratio (approximate)
        media_messages = sum(1 for msg in messages if any(media_indicator in msg['text'].lower() 
                                                         for media_indicator in ['http', '.com', 't.me']))
        media_share_ratio = media_messages / len(messages) if messages else 0
        
        return {
            'member_count': member_count,
            'online_count': online_count,
            'message_frequency': message_frequency,
            'active_users': active_users,
            'admin_activity': admin_activity,
            'media_share_ratio': media_share_ratio
        }
    
    async def _is_admin(self, group_entity, user_id) -> bool:
        """Check if user is admin in group"""
        try:
            participants = await self.client.get_participants(group_entity)
            for participant in participants:
                if participant.id == user_id:
                    return participant.admin_rights is not None
        except:
            pass
        return False
```

#### 📄 `websocket_handler.py`
*path: `connectors/websocket_handler.py`*

```python
# path: connectors/websocket_handler.py

"""
Manages all WebSocket communication with the PumpPortal API.
This class is designed as a robust, self-healing supervisor that ensures a
persistent connection, manages subscriptions, and provides a clean
interface for the rest of the application.
"""

import asyncio
import json
import random
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List

import websockets
from websockets import exceptions as ws_exceptions

from bot_logger import logger
from state_manager import GlobalState
from database_handler import DatabaseClient
from config.config import (
    _PUMPPORTAL_WS,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES,
    WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS,
    WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS,
    WEBSOCKET_SUBSCRIPTION_BATCH_SIZE,
    WEBSOCKET_BATCH_DELAY,
)

class ConnectionStatus(Enum):
    """Defines the possible states of the WebSocket connection."""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    SHUTTING_DOWN = "Shutting Down"

class WebSocketHandler:
    """A supervisor for managing a persistent WebSocket connection."""

    def __init__(self, db_client: DatabaseClient, state_manager: GlobalState, config: dict):
        """
        Initializes the WebSocketHandler.

        Args:
            db_client: An instance of the DatabaseClient for database operations.
            state_manager: The global state manager instance.
            config: The application's configuration dictionary.
        """
        self.db_client = db_client
        self.state = state_manager
        self.config = config
        self.trade_queue = asyncio.Queue()

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._status = ConnectionStatus.DISCONNECTED
        self._reconnect_delay = WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS
        self._last_message_time: float = 0.0

        # Stores the status of global, non-token-specific subscriptions.
        self._subscribed_to_new_token = False
        self._subscribed_to_migration = False

        # The main task that manages the connection lifecycle.
        self._manager_task: Optional[asyncio.Task] = None

    def start(self):
        """Starts the connection manager as a background task."""
        if self._manager_task is None or self._manager_task.done():
            self._manager_task = asyncio.create_task(self._connection_supervisor(), name="websocket_supervisor")
            logger.info(":rocket: WebSocket Connection Supervisor started.")
        else:
            logger.warning("WebSocket Connection Supervisor is already running.")

    async def shutdown(self):
        """Gracefully shuts down the WebSocket connection and all associated tasks."""
        if self._status == ConnectionStatus.SHUTTING_DOWN:
            return
            
        logger.info("🔌 Shutting down WebSocket handler...")
        self._set_status(ConnectionStatus.SHUTTING_DOWN)

        # Unsubscribe from all active token trades before closing.
        if self._ws and self._ws.open:
            logger.debug("Unsubscribing from all open token trades before shutdown.")
            all_subs = list(await self.state.get_token_subscriptions())
            await self._unsubscribe_in_batches(all_subs, "shutdown")
            self._subscribed_to_new_token = False
            self._subscribed_to_migration = False

        # Cancel the main manager task.
        if self._manager_task and not self._manager_task.done():
            self._manager_task.cancel()
            try:
                await self._manager_task
            except asyncio.CancelledError:
                pass # This is expected on cancellation.

        # Perform final connection cleanup.
        await self._close_connection("Shutdown requested")
        logger.info("✅ WebSocket handler has been shut down successfully.")

    # --- Public Methods for Other Modules ---

    async def unsubscribe_from_trades(self, mints: List[str], reason: str):
        """
        Public method to unsubscribe from token trades for a list of mints.
        Used by modules like `rugcheck_handler` and the `_dead_token_monitor`.

        Args:
            mints: A list of mint addresses to unsubscribe from.
            reason: A string explaining why the unsubscription is happening (for logging).
        """
        if not mints:
            return
        
        #logger.info(f"Request received to unsubscribe from {len(mints)} tokens (Reason: {reason}).")
        await self._unsubscribe_in_batches(mints, reason)

    def get_status(self) -> dict:
        """
        Provides a detailed status report for monitoring purposes (e.g., `monitor_tasks`).

        Returns:
            A dictionary containing the current connection status and health metrics.
        """
        now = asyncio.get_event_loop().time()
        time_since_last_msg = now - self._last_message_time if self._last_message_time > 0 else -1

        return {
            "connection_status": self._status.value,
            "is_connected": self._ws is not None and self._ws.open,
            "new_token_subscribed": self._subscribed_to_new_token,
            "migration_subscribed": self._subscribed_to_migration,
            "trade_subscriptions_count": len(self.state.active_token_subscriptions),
            "time_since_last_message_s": round(time_since_last_msg, 1),
            "time_since_last_pong_s": -1.0, # Kept for backward compatibility in status logs.
        }
        
    # --- Internal Logic: Connection Supervisor ---

    def _set_status(self, new_status: ConnectionStatus):
        """Atomically updates the connection status and logs the change."""
        if self._status != new_status:
            logger.info(f":satellite: WebSocket status changed: {self._status.value} -> {new_status.value}")
            self._status = new_status

    async def _connection_supervisor(self):
        """
        The main supervisor loop that ensures the WebSocket is always connected.
        It handles connection attempts, disconnects, and reconnection with
        exponential backoff and jitter to avoid spamming the server.
        """
        while self._status != ConnectionStatus.SHUTTING_DOWN:
            try:
                self._set_status(ConnectionStatus.CONNECTING)
                # We disable the library's automatic pinging (`ping_interval=None`)
                # in favor of our own application-level pinger, which is more reliable
                # for custom WebSocket APIs.
                async for websocket in websockets.connect(
                    _PUMPPORTAL_WS,
                    ping_interval=None, 
                    open_timeout=20,
                    extra_headers={"Origin": "https://pumpportal.fun"}
                ):
                    self._ws = websocket
                    self._set_status(ConnectionStatus.CONNECTED)
                    logger.info("✅ WebSocket connection established successfully.")
                    # Reset the reconnect delay upon a successful connection.
                    self._reconnect_delay = WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS
                    
                    # Start the session handler which manages the active connection.
                    await self._session_handler()
            
            except ws_exceptions.WebSocketException as e:
                logger.warning(f":police_car_light: WebSocket connection error: {e}. Attempting to reconnect.")
            except asyncio.CancelledError:
                logger.info(":stop_sign: Connection supervisor task was cancelled.")
                break
            except Exception as e:
                logger.error(f":police_car_light: Unexpected error in connection supervisor: {e}", exc_info=True)

            if self._status == ConnectionStatus.SHUTTING_DOWN:
                break
            
            # If the loop breaks for any reason other than shutdown, initiate reconnection.
            self._set_status(ConnectionStatus.RECONNECTING)
            
            # Calculate wait time with jitter to prevent synchronized reconnect storms.
            jitter = random.uniform(0.5, 1.5)
            wait_time = min(self._reconnect_delay * jitter, WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS)
            logger.info(f":stopwatch: Waiting {wait_time:.2f} seconds before next connection attempt...")
            
            await asyncio.sleep(wait_time)
            # Increase the delay for the next potential attempt.
            self._reconnect_delay = min(self._reconnect_delay * 2, WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS)

        logger.info("🛑 WebSocket Connection Supervisor has shut down.")

    # --- Internal Logic: Session and Message Handling ---

    async def _session_handler(self):
        """
        Manages an active WebSocket session by running all necessary background tasks
        like message receiving, health checks, and subscription management. The session
        ends if any of these tasks fail, which triggers the supervisor to reconnect.
        """
        if not self._ws: return

        self._last_message_time = asyncio.get_event_loop().time()

        # Create all tasks that should run during an active session.
        session_tasks = [
            asyncio.create_task(self._message_receiver(), name="ws_receiver"),
            asyncio.create_task(self._health_checker(), name="ws_health_checker"),
            asyncio.create_task(self._application_pinger(), name="ws_app_pinger"),
            asyncio.create_task(self._subscription_refresher(), name="ws_subscription_refresher"),
            asyncio.create_task(self._dead_token_monitor(), name="ws_dead_token_monitor")
        ]
        
        try:
            # Subscribe to all required streams at the start of the session.
            await self._initialize_subscriptions()
            
            # Wait for the first task to complete, which indicates the session has ended.
            done, pending = await asyncio.wait(session_tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Log why the session ended.
            for task in done:
                if task.exception():
                    logger.warning(f"WebSocket session ended because task '{task.get_name()}' failed with error: {task.exception()}")
                else:
                    logger.warning(f"WebSocket session ended because task '{task.get_name()}' finished unexpectedly.")
            
            # Cancel all other running session tasks.
            for task in pending:
                task.cancel()

        except Exception as e:
            logger.error(f":police_car_light: Error during WebSocket session handling: {e}", exc_info=True)
        finally:
            await self._close_connection("Session ended")

    async def _message_receiver(self):
        """Continuously listens for incoming messages and dispatches them."""
        if not self._ws: return
        try:
            async for message in self._ws:
                # Update the timestamp of the last message to keep the health check happy.
                self._last_message_time = asyncio.get_event_loop().time()
                await self._handle_incoming(message)
        except asyncio.CancelledError:
            pass # Normal shutdown procedure.
        except ws_exceptions.ConnectionClosed as e:
            logger.warning(f"Connection closed in receiver: {e.code} {e.reason}")
            raise ConnectionError(f"Connection closed: {e.code}") # Raise to terminate the session.
        except Exception as e:
            logger.error(f":police_car_light: Error in message receiver: {e}", exc_info=True)
            raise # Raise to terminate the session.

    async def _handle_incoming(self, raw_message: str):
        """
        Processes the logic for a single incoming message, similar to the old implementation.
        """
        try:
            data = json.loads(raw_message)
            tx_type = data.get("txType")

            if tx_type == "create":
                mint = data.get("mint")
                if not mint: return
                
                # The logic to insert into DB and check creator limits is encapsulated in `insert_token`.
                # It returns `True` if the token is new and meets all criteria.
                is_new_and_valid = await self.db_client.insert_token(data)
                
                if is_new_and_valid:
                    logger.info(f":heavy_plus_sign: New valid token detected: {mint}. Subscribing to trades.")
                    await self._send_json({"method": "subscribeTokenTrade", "keys": [mint]})
                    await self.state.add_token_subscription(mint)

                    # <<< ADD TO AI QUEUE (Priority 4 Sampling) >>>
                    if self.config.get('AI_DECISION_MAKING_ENABLED', False):
                        sample_rate = self.config.get('AI_NEW_TOKEN_SAMPLE_RATE', 0.02)
                        if random.random() < sample_rate:
                            ai_q = self.state.get_ai_evaluation_queue()
                            if not ai_q.full():
                                # --- [START SOLUTION 2: DUPLICATE CHECK] ---
                                async with self.state.ai_queue_lock:
                                    if mint not in self.state.ai_queue_mints:
                                        await ai_q.put((0, (mint, 'INITIAL BUY'))) # Priority 0
                                        self.state.ai_queue_mints.add(mint)
                                        logger.debug(f"AI Queue: Added new token {mint} via sampling.")
                                # --- [END SOLUTION 2] ---
                            else:
                                logger.warning(f"AI Queue is full, could not add sampled new token {mint}.")
                    # <<< END AI QUEUE ADDITION >>>

            elif tx_type == "migrate":
                mint = data.get("mint")
                if mint and await self.db_client.is_token_active_in_db(mint):
                    await self.db_client.mark_token_as_migrated(mint)
                    await self.db_client.insert_migration(data)
                    # <<< Optional: Trigger AI eval on migration (Priority 3) >>>
                    # You could add logic here to put the migrated token
                    # into the AI queue if desired, similar to the event checker.
                    # ai_q = self.state.get_ai_evaluation_queue()
                    # if not ai_q.full():
                    #    await ai_q.put((-25, (mint, 'SELL/HOLD' or 'REBUY'))) # Adjust context

            elif tx_type in ["buy", "sell"]:
                await self.trade_queue.put(data)
                
        except json.JSONDecodeError:
            logger.debug(f"Received non-JSON message: {raw_message[:100]}")
        except Exception as e:
            logger.error(f":police_car_light: Error processing incoming message: {e}", exc_info=True)

    # --- Internal Logic: Subscriptions & Health Checks ---

    async def _application_pinger(self):
        """Periodically sends an application-level ping message to keep the connection alive."""
        while self._status == ConnectionStatus.CONNECTED:
            try:
                await asyncio.sleep(20) # Send a ping every 20 seconds.
                await self._send_json({"method": "ping"})
                logger.debug("Application-level ping sent.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Failed to send application-level ping: {e}")
                break # Failure to send means the connection is likely dead; break to trigger a reconnect.

    async def _health_checker(self):
        """
        Monitors connection health by checking if any message (including responses to our pings)
        has been received recently.
        """
        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(30) # Check every 30 seconds.
            
            time_since_last_message = asyncio.get_event_loop().time() - self._last_message_time
            
            # If we haven't received ANY message for 60 seconds (despite sending a ping every 20s),
            # the connection is considered stale/dead.
            if time_since_last_message > 60:
                logger.warning(f"No message received for {time_since_last_message:.0f}s. Connection is considered stale.")
                raise ConnectionError("Stale connection")
    
    async def _initialize_subscriptions(self):
        """Subscribes to all necessary streams when a new connection is established."""
        logger.info("Initializing subscriptions...")
        
        # Global streams
        await self._send_json({"method": "subscribeNewToken"})
        self._subscribed_to_new_token = True
        logger.debug("-> 'subscribeNewToken' message sent.")
        
        await self._send_json({"method": "subscribeMigration"})
        self._subscribed_to_migration = True
        logger.debug("-> 'subscribeMigration' message sent.")

        # Subscriptions for existing active tokens from the database
        active_tokens = await self.db_client.get_active_tokens()
        mints_to_subscribe = [record["mint"] for record in active_tokens]
        
        if mints_to_subscribe:
            logger.info(f"Resuming {len(mints_to_subscribe)} existing token subscriptions...")
            await self._subscribe_in_batches(mints_to_subscribe)
            
        logger.info("✅ All initial subscriptions have been sent.")

    async def _subscribe_in_batches(self, mints: List[str]):
        """Subscribes to a list of mints in batches to avoid overwhelming the API."""
        for i in range(0, len(mints), WEBSOCKET_SUBSCRIPTION_BATCH_SIZE):
            if self._status != ConnectionStatus.CONNECTED: break
            batch = mints[i:i + WEBSOCKET_SUBSCRIPTION_BATCH_SIZE]
            await self._send_json({"method": "subscribeTokenTrade", "keys": batch})
            for mint in batch:
                await self.state.add_token_subscription(mint)
            logger.debug(f"Sent subscription batch for {len(batch)} tokens.")
            await asyncio.sleep(WEBSOCKET_BATCH_DELAY)

    async def _unsubscribe_in_batches(self, mints: List[str], reason: str):
        """Unsubscribes from mints in batches and updates the state accordingly."""
        for i in range(0, len(mints), WEBSOCKET_SUBSCRIPTION_BATCH_SIZE):
            batch = mints[i:i + WEBSOCKET_SUBSCRIPTION_BATCH_SIZE]
            
            # Send unsubscribe message if connected.
            if self._ws and self._ws.open:
                await self._send_json({"method": "unsubscribeTokenTrade", "keys": batch})
            
            # Always update the local state.
            for mint in batch:
                await self.state.remove_token_subscription(mint)

            logger.debug(f"Sent unsubscription batch for {len(batch)} tokens (Reason: {reason}).")
            
            # If the reason is terminal (e.g., dead token), also archive/delete from DB.
            if reason in ["dead_token", "high_rugcheckscore"]:
                for mint in batch:
                    await self.db_client.backup_and_delete_token(
                        mint=mint, 
                        archived_at=datetime.now(timezone.utc),
                        reason=reason
                    )
            
            await asyncio.sleep(WEBSOCKET_BATCH_DELAY)

    async def _subscription_refresher(self):
        """Periodically refreshes all `subscribeTokenTrade` subscriptions to prevent them from going stale."""
        if not _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED:
            logger.info("Automatic subscription refresher is disabled.")
            return

        interval = _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES * 60
        logger.info(f"🔄 Subscription refresher started. Interval: {interval / 60} minutes.")

        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(interval)
            logger.info("Starting periodic subscription refresh...")
            
            # Unsubscribe from all currently tracked tokens.
            current_subs = list(await self.state.get_token_subscriptions())
            if current_subs:
                await self._unsubscribe_in_batches(current_subs, "periodic_refresh")
                
            await asyncio.sleep(2) # Brief pause before re-subscribing.
            
            # Get the latest list of active tokens from the database and re-subscribe.
            active_tokens_now = await self.db_client.get_active_tokens()
            mints_to_resubscribe = [r["mint"] for r in active_tokens_now]
            
            if mints_to_resubscribe:
                await self._subscribe_in_batches(mints_to_resubscribe)
            
            logger.info(f"✅ Periodic refresh complete. {len(mints_to_resubscribe)} subscriptions are now active.")
        
        logger.info("Subscription refresher stopped because connection was lost.")

    async def _dead_token_monitor(self):
        """
        Periodically checks the database for tokens that have become inactive or "dead"
        and unsubscribes from their trade streams.
        """
        # Check at half the inactivity period to be proactive.
        interval = 60
        logger.info(f"🗑️ Dead token monitor started. Check interval: {interval / 60:.1f} minutes.")
        
        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(interval)
            try:
                tokens_to_unsub = await self.db_client.get_tokens_to_unsubscribe(
                    self.config["MC_DROP_THRESHOLD"],
                    self.config["INACTIVITY_PERIOD"],
                    self.config["MIN_TOKEN_AGE"]
                )
                
                if tokens_to_unsub:
                    mints = [record["mint"] for record in tokens_to_unsub]
                    logger.info(f"Found {len(mints)} dead/inactive tokens. Unsubscribing.")
                    await self.unsubscribe_from_trades(mints, "dead_token")

            except Exception as e:
                logger.error(f":police_car_light: Error in dead token monitor: {e}", exc_info=True)
                
        logger.info("Dead token monitor stopped because connection was lost.")

    # --- Helper Functions ---

    async def _send_json(self, data: dict):
        """Safely sends a JSON payload over the WebSocket."""
        if self._ws and self._ws.open:
            try:
                await self._ws.send(json.dumps(data))
            except ws_exceptions.ConnectionClosed:
                logger.warning("Attempted to send on a closed connection.")
                raise ConnectionError("Connection closed during send")
            except Exception as e:
                logger.error(f"Failed to send data: {e}")
                raise
        else:
            logger.warning("Attempted to send but WebSocket is not connected.")
            raise ConnectionError("WebSocket is not open")

    async def _close_connection(self, reason: str):
        """Closes the WebSocket connection if it exists."""
        if self._ws:
            logger.debug(f"Closing WebSocket connection (Reason: {reason})...")
            try:
                await self._ws.close(code=1000, reason=reason)
            except Exception as e:
                # This can happen if the connection is already dead, which is fine.
                logger.debug(f":police_car_light: Error while closing WebSocket connection (may be expected): {e}")
            finally:
                self._ws = None
                self._set_status(ConnectionStatus.DISCONNECTED)
```

#### 📄 `bot_command.txt`
*path: `data/bot_command.txt`*

_This file is empty._

#### 📄 `database_handler.py`
*path: `database_handler.py`*

```python
"""
Database module.
Handles PostgreSQL connections and CRUD operations.
"""

import os
import io
import csv
import glob
from datetime import datetime, timezone,timedelta
import asyncio
import asyncpg
import aiofiles
import json
import pandas as pd
from dotenv import load_dotenv
from bot_logger import logger
from config.config import _TOTAL_SUPPLY
import config.config as base_config_module
from state_manager import GlobalState
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from utils import calculate_volatility
import inspect 
from typing import Optional
import statistics 
from decimal import Decimal

# Load environment variables from .env file
load_dotenv()

# Construct the database URL from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?options=-c%20timezone%3Dutc"

# --- Helper Function to Convert Module to Dict ---
# (Place this helper function outside the class, near the imports)
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
    logger.debug(f"Converted config module to dict: {list(config_dict.keys())}")
    return config_dict

# --- Helper Function to Sanitize Strings ---
def _sanitize_string(value: Any) -> Optional[str]:
    """Removes null bytes from strings and ensures the value is a string or None."""
    if isinstance(value, str):
        return value.replace('\x00', '')
    return None if value is None else str(value) # Convert other types to string, handle None
class DatabaseClient:
    """Client to manage database connections and operations."""
 
    _DEFAULT_CONFIG = _config_module_to_dict(base_config_module)
    
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict
        self.pool = None
        self.state = GlobalState.get_instance()

        # Use the provided config_dict if available, otherwise use the class default
        if config_dict is not None:
            self.config = config_dict
            logger.debug("DatabaseClient initialized with provided config_dict.")
        else:
            # Use a copy of the default to prevent modifications affecting others
            self.config = self._DEFAULT_CONFIG.copy()
            logger.debug("DatabaseClient initialized with default config from config.py.")

        # Ensure self.config is always a dictionary
        if not isinstance(self.config, dict):
             logger.error(f"DatabaseClient self.config is not a dict! Type: {type(self.config)}. Falling back to default.")
             self.config = self._DEFAULT_CONFIG.copy() # Fallback just in case

    def get_sync_connection_pool(self):
        """
        Creates and returns a synchronous connection pool for psycopg2.
        This version correctly parses the host and port.
        """
        from psycopg2.pool import SimpleConnectionPool
        import os

        if hasattr(self, '_sync_pool') and self._sync_pool:
            return self._sync_pool

        # --- START FIX ---
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_database = os.getenv("DB_DATABASE")
        db_host_raw = os.getenv("DB_HOST")

        db_host = db_host_raw
        db_port = None

        # Check if the host string contains a port and split it if it does
        if db_host_raw and ':' in db_host_raw:
            parts = db_host_raw.split(':')
            db_host = parts[0]
            db_port = parts[1]

        # Build the DSN string component by component
        dsn_parts = [
            f"dbname={db_database}",
            f"user={db_user}",
            f"password={db_password}",
            f"host={db_host}"
        ]
        if db_port:
            dsn_parts.append(f"port={db_port}")

        dsn = " ".join(dsn_parts)
        # --- END FIX ---
        
        self._sync_pool = SimpleConnectionPool(minconn=1, maxconn=5, dsn=dsn)
        return self._sync_pool

    async def connect(self):
        """Establish a connection pool to the PostgreSQL database."""
        try:
            # Use the DB_URL constructed from environment variables
            self.pool = await asyncpg.create_pool(dsn=DB_URL)
            logger.info(":handshake: Connected to the database successfully.")
        except Exception as e:
            logger.exception(":police_car_light: Errorconnecting to the database: %s", e)
            raise

    async def init_db(self):
        """
        Initialize the database schema by reading and executing all SQL files 
        from the 'sql' subfolder. Additionally, restore the creator_wallets 
        table from the backup file if necessary.
        """
        sql_folder = os.path.join(os.path.dirname(__file__), "sql")
        sql_files = sorted(glob.glob(os.path.join(sql_folder, "*.sql")))
        
        async with self.pool.acquire() as conn:
            # Execute schema SQL files
            for file_path in sql_files:
                try:
                    with open(file_path, "r") as f:
                        sql = f.read()
                    await conn.execute(sql)
                    logger.info("Executed SQL file: %s", os.path.basename(file_path))
                except Exception as e:
                    logger.exception(":exclamation: Errorexecuting SQL file %s: %s", os.path.basename(file_path), e)
                    raise

    async def insert_sol_price(self, price: float, timestamp: datetime = datetime.now(timezone.utc)):
        """Insert a new SOL price into the database."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO sol_price_usd (price, timestamp) VALUES ($1, $2)", price, timestamp)
        except Exception as e:
            logger.exception(":exclamation: Errorinserting SOL price into the database: %s", e)
            raise

    async def insert_token(self, data: dict):
        """Checks if the token is valid and stores it if conditions are met."""
        async with self.pool.acquire() as conn:
            mint = data.get('mint')
            if not mint:
                logger.warning("Mint address is missing in the token data.")
                return False
            try:
                async with conn.transaction():
                    # 1. Check if token already exists in tokens or tokens_backup
                    token_exists = await conn.fetchval("""
                        SELECT 1 FROM tokens WHERE mint = $1
                        UNION
                        SELECT 1 FROM tokens_backup WHERE mint = $1
                    """, mint)
                    if token_exists:
                        logger.info(f"Token {mint} is already stored. Skipping.")
                        return False  # Token already exists, no need to insert

                    # 2. Check how many tokens the creator has recently created
                    creator = data.get('traderPublicKey')
                    now = datetime.now(timezone.utc)
                    row = await conn.fetchrow(
                        "SELECT token_count, last_token_time FROM creator_wallets WHERE wallet_address = $1",
                        creator
                    )
                    
                    token_count = 1
                    if row:
                        token_count, last_token_time = row
                        if last_token_time and (now - last_token_time).total_seconds() < 604800:
                            token_count += 1

                        await conn.execute(
                            "UPDATE creator_wallets SET token_count = $1, last_token_time = $2 WHERE wallet_address = $3",
                            token_count, now, creator
                        )
                    else:
                        await conn.execute(
                            "INSERT INTO creator_wallets (wallet_address, token_count, last_token_time) VALUES ($1, $2, $3)",
                            creator, token_count, now
                        )

                    if token_count > self.config.get('MAX_TOKEN_COUNT_PER_CREATOR', 100):
                            logger.debug(f"🤬 [bold red]Suspicious creator[/bold red] %s for token %s with %s tokens. Skipping.", creator, data['mint'], token_count)
                            return False

                    sol_price = await self.state.get_sol_price()
                    if sol_price is None or sol_price <= 0:
                        logger.warning(f"⚠ Invalid SOL_PRICE ({sol_price}); skipping insert token operation.")
                        return False # Cannot proceed without valid SOL price
                    
                    # 3. Insert/update token
                    await conn.execute("""
                        INSERT INTO tokens(mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, 
                            vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri, sol_price_usd,
                            is_active, timestamp)
                        VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, True, NOW());
                        """, 
                        data.get('mint'), 
                        data.get('traderPublicKey'), 
                        data.get('initialBuy'), 
                        data.get('solAmount'), 
                        data.get('bondingCurveKey'), 
                        data.get('vTokensInBondingCurve'),
                        data.get('vSolInBondingCurve'), 
                        data.get('marketCapSol'), 
                        _sanitize_string(data.get('name')),
                        _sanitize_string(data.get('symbol')), 
                        _sanitize_string(data.get('uri')),
                        sol_price
                    )
                    logger.debug("Inserted/Updated token %s", data.get('mint'))
                    return True
            except Exception as e:
                logger.exception(":exclamation: Errorinserting token data: %s", e)
                raise

    async def insert_migration(self, data: dict):
        """Batch-insert trade data into trades table."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                            INSERT INTO migrations (signature, mint, txType, pool)
                            VALUES ($1, $2, $3, $4)
                        ''',data["signature"], data["mint"], data["txType"], data["pool"])

                        logger.debug(f"Stored migration event for token {data['mint']}")
                    except Exception as e:
                        logger.error(f"❌ Storing migration for {data['mint']} failed: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f":police_car_light: Error on storing migration: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def insert_trades_batch(self, trade_params: list, mints: list):
        """
        Inserts a batch of trades into the database and updates the last_trade timestamp for the tokens.
        """
        if not trade_params:
            return

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Batch insert trades
                    await conn.executemany('''
                        INSERT INTO trades (
                            signature, mint, trader_pubkey, tx_type, token_amount, sol_amount, price,
                            bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
                            marketCapSol,sol_price_usd, market_cap_calculated, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        ON CONFLICT (signature) DO NOTHING
                    ''', trade_params)

                    # Batch update last_trade timestamps
                    if mints:
                        # Ensure mints are unique before updating
                        unique_mints = list(set(mints))
                        await conn.execute('''
                            UPDATE tokens
                            SET last_trade = NOW()
                            WHERE mint = ANY($1::text[])
                        ''', unique_mints)

                    logger.debug(f"✅ Processed {len(trade_params)} trades in batch")

                except Exception as e:
                    logger.error(f":police_car_light: Error during batch trade insert: {e}", exc_info=True)
                    # The transaction will be rolled back automatically
                    raise # Re-raise the exception so the caller knows about the failure

    async def get_tokens_to_unsubscribe(self, mc_drop_threshold, inactivity_period, min_token_age):
        """Fetch tokens to unsubscribe based on market cap drop and inactivity."""
        query = """
            SELECT t.mint
            FROM tokens t
            LEFT JOIN (
                -- Subquery to find the very latest trade tick for each token
                SELECT mint, market_cap_sol, timestamp,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM v_unified_market_ticks_live
            ) latest ON t.mint = latest.mint AND latest.rn = 1
            WHERE
                -- Condition 1: The token must be older than the minimum age.
                t.timestamp <= NOW() - (INTERVAL '1 minute' * $3) -- $3 = min_token_age
                
                -- Condition 2: The token must not have an active position in the portfolio.
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
                
                -- Condition 3: The token must meet one of the "dead" criteria.
                AND (
                    -- Criteria A: The token HAS trades but is inactive or has crashed.
                    (
                        latest.mint IS NOT NULL AND (
                            -- Market cap has dropped below the threshold.
                            (latest.market_cap_sol * 100.0 / t.marketCapSol) < (100 - $1) -- $1 = mc_drop_threshold
                            OR
                            -- The last trade was longer ago than the inactivity period.
                            latest.timestamp <= NOW() - (INTERVAL '1 minute' * $2) -- $2 = inactivity_period
                        )
                    )
                    OR
                    -- Criteria B: The token has NO trades at all.
                    (latest.mint IS NULL)
                )
            ORDER BY t.timestamp DESC;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, mc_drop_threshold, inactivity_period, min_token_age)
        
    async def get_social_check_count(self, mint: str, conn=None) -> int:
        """Counts how many times a social check has been performed for a token."""
        query = "SELECT COUNT(*) FROM social_scores WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            count = await connection.fetchval(query, mint)
            return count if count is not None else 0
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_active_tokens(self, limit: int = 20000):
        """Fetch active tokens from the database."""
        query = """
            SELECT mint FROM tokens WHERE is_active = True
            ORDER BY timestamp DESC LIMIT $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, limit)

    async def is_suspicious_creator(self, creator: str):
        """Check if a creator is suspicious based on the number of tokens created."""
        query = """
            SELECT token_count FROM creator_wallets WHERE wallet_address = $1
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, creator)
            if row and row['token_count'] > 2:
                return True
            return False

    async def fetch_tokens_by_creator(self, creator: str, respect_portfolio: bool = False):
        if respect_portfolio:
            query = """
                SELECT mint FROM tokens 
                WHERE traderpublickey = $1
                    AND mint NOT IN (SELECT mint FROM portfolio)
            """
        else:
            query = """
                SELECT mint FROM tokens 
                WHERE traderpublickey = $1
            """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, creator)
        
    async def get_total_supply(self, mint: str): #
        """Fetch the total supply of a token (RAW units) from rugcheck table.
           NOTE: For price calculations, use _get_latest_token_info which also gets decimals.
        """
        query = "SELECT token_supply FROM rugcheck WHERE mint = $1" #
        async with self.pool.acquire() as conn: #
            result = await conn.fetchrow(query, mint) #
            # Ensure _TOTAL_SUPPLY is fetched from self.config
            default_supply = self.config.get('_TOTAL_SUPPLY', 1_000_000_000) #
            return result['token_supply'] if result and result['token_supply'] is not None else default_supply #

    async def find_trading_opportunities(self, sol_price: float, volume_threshold: float, marketcap_threshold: float, rugcheck_threshold: int, social_score_threshold: int, time_interval_minutes: int, min_volatility: float): 
        """
        [MODIFIED] Identifies potential token buy opportunities, ensuring only the latest rugcheck score is used.
        - Volume Calculation is source-aware:
            - PUMP: SUMs all individual trade sol_amounts.
            - DEXSCREENER: Takes only the SINGLE LATEST volume snapshot to prevent duplicate counting.
        - Volatility is calculated ONLY from high-frequency PUMP trades for accuracy.
        """
        
        query = """
            WITH LatestTickData AS (
                -- This correctly gets the latest price/MC from either source
                SELECT
                    mint,
                    price_sol,
                    market_cap_sol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM v_unified_market_ticks_live -- Uses LIVE view, which is correct
                WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
            ),
            -- START OF FIX: Add a CTE to get only the latest rugcheck score per mint
            LatestRugcheck AS (
                SELECT
                    mint,
                    score,
                    tokenMeta_name,
                    tokenMeta_symbol,
                    ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) as rn
                FROM rugcheck
            ),
            -- END OF FIX
            RecentMetrics AS (
                -- THIS CTE IS NOW SOURCE-AWARE TO PREVENT DOUBLE-COUNTING VOLUME
                SELECT
                    mint,
                    SUM(calculated_volume) AS volume_recent_sol
                FROM (
                    -- 1. Sum up all individual Pump.fun trades from the 'trades' table
                    SELECT
                        mint,
                        sol_amount AS calculated_volume
                    FROM trades -- Use base table for PUMP data
                    WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval

                    UNION ALL

                    -- 2. Get only the LATEST 5-minute volume for migrated tokens
                    SELECT
                        mint_address AS mint,
                        (volume_m5 / sol_price_usd) AS calculated_volume
                    FROM (
                        SELECT
                            mint_address,
                            volume_m5,
                            sol_price_usd,
                            ROW_NUMBER() OVER(PARTITION BY mint_address ORDER BY timestamp DESC) as rn
                        FROM dexscreener_data -- Use base table for DEXSCREENER data
                        WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
                          AND sol_price_usd > 0 -- Avoid division by zero
                    ) AS ranked_dex
                    WHERE rn = 1
                ) AS combined_volume_sources
                GROUP BY mint
            ),
            VolatilityData AS (
                -- THIS CTE IS NOW MODIFIED TO ONLY USE PUMP.FUN TRADES FOR RELIABLE CALCULATION
                SELECT
                    mint,
                    -- The volatility formula remains the same
                    STDDEV(log_return) * SQRT(GREATEST(COUNT(*), 1)) AS volatility
                FROM (
                    SELECT
                        mint,
                        -- Use price_sol from the unified view
                        LN(price_sol / LAG(price_sol) OVER (PARTITION BY mint ORDER BY timestamp)) AS log_return
                    -- <<< CHANGE: Use 'v_unified_market_ticks_historical' view instead of 'trades'
                    FROM v_unified_market_ticks_live
                    WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
                      -- <<< CHANGE: Use 'price_sol' column from the view
                      AND price_sol > 0
                ) sub
                WHERE log_return IS NOT NULL
                    AND log_return > '-Infinity'::double precision
                    AND log_return < 'Infinity'::double precision
                GROUP BY mint
                HAVING COUNT(*) > 5
            )
            SELECT
                t.mint, ltd.price_sol AS latest_price, ltd.market_cap_sol AS latest_market_cap_sol,
                COALESCE(rm.volume_recent_sol, 0) AS volume_in_interval,
                COALESCE(vd.volatility, 0) AS volatility_in_interval,
                lrc.tokenMeta_name AS name, lrc.tokenMeta_symbol AS symbol, -- FIX: Use new CTE alias
                lrc.score AS rugcheck_score, t.socials_score -- FIX: Use new CTE alias
            FROM tokens AS t
            -- FIX: Join with the new LatestRugcheck CTE instead of the raw table
            INNER JOIN LatestRugcheck AS lrc ON t.mint = lrc.mint AND lrc.rn = 1
            INNER JOIN LatestTickData AS ltd ON t.mint = ltd.mint AND ltd.rn = 1
            LEFT JOIN RecentMetrics AS rm ON t.mint = rm.mint
            LEFT JOIN VolatilityData AS vd ON t.mint = vd.mint
            WHERE
                t.is_active = TRUE AND
                lrc.score IS NOT NULL AND lrc.score <= $4 AND -- FIX: Use new CTE alias
                t.socials_score IS NOT NULL AND t.socials_score <= $5 AND
                (COALESCE(rm.volume_recent_sol, 0) * $1) >= $2 AND
                (ltd.market_cap_sol * $1) >= $3 AND
                COALESCE(vd.volatility, 0) >= $7 AND
                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') AND
                (t.cooldown_until IS NULL OR t.cooldown_until < NOW())
            ORDER BY rm.volume_recent_sol DESC;
        """
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch(query, sol_price, volume_threshold, marketcap_threshold, rugcheck_threshold, social_score_threshold, str(time_interval_minutes), min_volatility)
            except Exception as e:
                logger.error(f":police_car_light: Error finding trading opportunities: {e}", exc_info=True)
                return []

    async def get_active_buy_positions(self, conn=None):
        """Fetches active buy positions from the portfolio."""
        query = '''
            SELECT p.id, p.mint, p.price AS buy_price, p.initial_tokens, p.remaining_tokens, p.total_investment_sol,
                p.stop_loss_price, p.highest_price, p.initial_tp_price, p.second_tp_price, p.first_tp_hit,
                t.marketCapSol as initial_market_cap_sol, t.data_source,
                p.timestamp, p.volume_stale_since
            FROM portfolio p
            JOIN tokens t ON p.mint = t.mint
            WHERE p.status = 'active' AND p.tx_type = 'buy'
        '''
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetch(query)
        finally:
            if not conn and connection: # Release connection only if it was acquired here
                await self.pool.release(connection)

    async def get_latest_prices(self, mints: list[str], conn=None):
        """Fetches the latest price and market cap for a list of mints."""
        if not mints:
            return {}
        query = f'''
            WITH LatestTrades AS (
                SELECT
                    mint,
                    price_sol AS price,
                    market_cap_sol AS marketCapSol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                FROM v_unified_market_ticks_live
                WHERE mint = ANY($1::text[])
            )
            SELECT mint, price, marketCapSol FROM LatestTrades WHERE rn = 1
        '''
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, mints)
            results = {}
            for row in rows:
                mint = row['mint']
                price_val = float(row['price']) if row['price'] is not None else None
                market_cap_val = float(row['marketcapsol']) if row['marketcapsol'] is not None else None # Ensure marketcapsol from DB

                # Store market cap if it's valid, regardless of price for now
                # Store price only if it's valid and positive
                current_data = {'price': None, 'market_cap': None}

                if market_cap_val is not None and market_cap_val > 0: # Require positive MC
                    current_data['market_cap'] = market_cap_val
                
                if price_val is not None and price_val > 0:
                    current_data['price'] = price_val
                
                # Only add to results if we have at least a valid market_cap or a valid price
                if current_data['market_cap'] is not None or current_data['price'] is not None:
                    results[mint] = current_data
                else:
                    logger.warning(f"For mint {mint}, latest trade had invalid price ({row['price']}) AND invalid marketcap ({row['marketcapsol']}). Not returning data.")
            return results
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_primary_dex_id_for_migrated_token(self, mint: str, conn=None) -> str | None:
        """
        Fetches the dexId of the highest-liquidity pair for a migrated token
        from the most recent dexscreener_data entry.
        """
        query = """
            SELECT full_response
            FROM dexscreener_data
            WHERE mint_address = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            latest_record = await connection.fetchrow(query, mint)
            if latest_record and latest_record['full_response']:
                try:
                    # The full_response is stored as a JSON string, so we load it
                    pair_data = json.loads(latest_record['full_response'])
                    dex_id = pair_data.get('dexId')
                    if dex_id:
                        logger.debug(f"Found primary dexId '{dex_id}' for migrated token {mint}.")
                        return dex_id
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse dexId from full_response for {mint}: {e}")
            return None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    # --- NEW METHODS for AI Integration ---

    # async def insert_ai_decision(self, mint: str, context: str, decision: str, confidence: int, explanation: Optional[str] = None, data_snapshot: Optional[dict] = None, prompt_hash: Optional[str] = None, conn=None):
    #     """Inserts a new AI decision record."""
    #     query = """
    #         INSERT INTO ai_decisions
    #         (mint, decision_context, decision, confidence, explanation, data_snapshot, prompt_hash)
    #         VALUES ($1, $2, $3, $4, $5, $6, $7)
    #     """
    #     connection = conn or await self.pool.acquire()
    #     try:
    #         # Convert data_snapshot dict to JSON string if provided
    #         data_snapshot_json = json.dumps(data_snapshot, default=str) if data_snapshot else None
    #         await connection.execute(query, mint, context, decision, confidence, explanation, data_snapshot_json, prompt_hash)
    #         logger.debug(f"Stored AI decision for {mint}: {decision} ({confidence}%)")
    #     except Exception as e:
    #         logger.error(f":police_car_light: Error inserting AI decision for {mint}: {e}", exc_info=True)
    #         if not conn: raise # Re-raise if we acquired the connection here
    #     finally:
    #         if not conn and connection:
    #             await self.pool.release(connection)

    async def update_token_ai_eval_timestamp(self, mint: str, timestamp: datetime, conn=None):
        """Updates the ai_last_evaluation_ts for a token."""
        query = "UPDATE tokens SET ai_last_evaluation_ts = $1 WHERE mint = $2"
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, timestamp, mint)
        except Exception as e:
            logger.error(f":police_car_light: Error updating AI eval timestamp for {mint}: {e}", exc_info=True)
            if not conn: raise
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_latest_ai_decision(self, mint: str, conn=None) -> Optional[asyncpg.Record]:
        """Fetches the most recent AI decision record for a given mint."""
        query = """
            SELECT decision, confidence, evaluation_timestamp
            FROM ai_decision_memory
            WHERE mint = $1
                AND decision_context IN ('INITIAL BUY', 'SELL/HOLD', 'REBUY') -- Only get actionable contexts
            ORDER BY evaluation_timestamp DESC
            LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, mint)
        except Exception as e:
            logger.error(f":police_car_light: Error fetching latest AI decision for {mint}: {e}", exc_info=True)
            return None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_tokens_for_outcome_analysis(self, lookback_hours: int, conn=None) -> List[asyncpg.Record]:
        """
        Fetches tokens that the AI has evaluated but the bot does not own,
        and which have not had an "outcome" logged yet.
        """
        query = """
            WITH LastDecision AS (
                -- 1. Find the *last* decision the AI made for each mint
                SELECT
                    mint,
                    decision,
                    evaluation_timestamp,
                    metadata,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY evaluation_timestamp DESC) as rn
                FROM
                    ai_decision_memory
                WHERE
                    -- Only look at decisions that were NOT buys
                    decision != 'BUY' 
                    AND evaluation_timestamp >= NOW() - ($1 || ' hours')::interval
            ),
            LastOutcome AS (
                -- 2. Find the last *outcome* we logged for each mint
                SELECT
                    mint,
                    evaluation_timestamp AS last_outcome_ts
                FROM
                    ai_decision_memory
                WHERE
                    decision_context = 'NON_TRADE_OUTCOME'
            )
            -- 3. Return tokens that meet the criteria
            SELECT
                ld.mint,
                ld.decision,
                ld.evaluation_timestamp,
                ld.metadata
            FROM
                LastDecision ld
            WHERE
                ld.rn = 1 -- It's the most recent decision
                -- 4. And is not in the active portfolio
                AND ld.mint NOT IN (SELECT p.mint FROM portfolio p WHERE p.status = 'active')
                -- 5. And we have *never* logged an outcome for it, OR
                --    the last decision is *newer* than the last outcome we logged
                AND (
                    ld.mint NOT IN (SELECT lo.mint FROM LastOutcome lo)
                    OR
                    ld.evaluation_timestamp > (SELECT lo.last_outcome_ts FROM LastOutcome lo WHERE lo.mint = ld.mint ORDER BY lo.last_outcome_ts DESC LIMIT 1)
                );
        """
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetch(query, str(lookback_hours))
        except Exception as e:
            logger.error(f":police_car_light: Error fetching tokens for outcome analysis: {e}", exc_info=True)
            return []
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_active_portfolio_for_ai_eval(self, staleness_minutes: int, conn=None):
        """Fetches active portfolio mints needing AI evaluation."""
        query = """
            SELECT p.mint
            FROM portfolio p JOIN tokens t ON p.mint = t.mint
            WHERE p.status = 'active' AND p.tx_type = 'buy'
              AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($1 || ' minutes')::interval);
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
            if not conn and connection: await self.pool.release(connection)

    async def get_top_pump_momentum_for_ai_eval(self, top_n: int, window_minutes: int, staleness_minutes: int, conn=None):
        """Fetches top N PUMP tokens by recent volume needing AI eval."""
        query = f"""
            SELECT
                t.mint,
                SUM(td.sol_amount) AS recent_pump_volume
            FROM
                tokens t JOIN trades td ON t.mint = td.mint
            WHERE
                td.timestamp >= NOW() - ($2 || ' minutes')::interval
                AND t.data_source = 'PUMP'
                AND t.is_active = TRUE
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') -- Exclude held tokens
                AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($3 || ' minutes')::interval)
            GROUP BY t.mint
            ORDER BY recent_pump_volume DESC
            LIMIT $1;
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, top_n, str(window_minutes), str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
            if not conn and connection: await self.pool.release(connection)

    async def get_top_dex_momentum_for_ai_eval(self, top_n: int, window_minutes: int, staleness_minutes: int, conn=None):
        """Fetches top N DEX tokens by latest volume needing AI eval."""
        query = f"""
            WITH RankedDexVolume AS (
                SELECT
                    dsd.mint_address,
                    dsd.volume_m5,
                    t.ai_last_evaluation_ts,
                    ROW_NUMBER() OVER (PARTITION BY dsd.mint_address ORDER BY dsd.timestamp DESC) as rn
                FROM
                    dexscreener_data dsd JOIN tokens t ON dsd.mint_address = t.mint
                WHERE
                    dsd.timestamp >= NOW() - ($2 || ' minutes')::interval -- Ensure snapshot is recent
                    AND t.data_source = 'DEXSCREENER'
                    AND t.is_active = TRUE
                    AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') -- Exclude held tokens
                    AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($3 || ' minutes')::interval)
            )
            SELECT
                mint_address AS mint,
                volume_m5 AS latest_dex_volume_m5
            FROM
                RankedDexVolume
            WHERE
                rn = 1
            ORDER BY
                latest_dex_volume_m5 DESC NULLS LAST
            LIMIT $1;
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, top_n, str(window_minutes), str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
             if not conn and connection: await self.pool.release(connection)

    async def get_tokens_with_recent_events_for_ai_eval(self, rug_change_threshold: int, social_change_threshold: int, staleness_minutes: int, conn=None):
        """Fetches tokens with significant score changes or migration needing AI eval."""
        # This query is complex. It finds tokens that migrated recently OR had significant score changes.
        query = f"""
            WITH RecentScoreChanges AS (
                -- Find latest and previous Rugcheck scores
                SELECT mint, score, last_checked,
                       LAG(score) OVER (PARTITION BY mint ORDER BY last_checked) as prev_score
                FROM v_rugcheck
                WHERE last_checked >= NOW() - INTERVAL '1 hour' -- Look at recent score history
            ),
            SignificantRugChange AS (
                SELECT DISTINCT mint
                FROM RecentScoreChanges
                WHERE ABS(score - prev_score) >= $1
            ),
            RecentSocialChanges AS (
                -- Find latest and previous Social scores
                SELECT mint, score_value, timestamp,
                       LAG(score_value) OVER (PARTITION BY mint ORDER BY timestamp) as prev_score
                FROM v_social_scores
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            ),
            SignificantSocialChange AS (
                SELECT DISTINCT mint
                FROM RecentSocialChanges
                WHERE ABS(score_value - prev_score) >= $2
            ),
            RecentMigrations AS (
                SELECT DISTINCT mint
                FROM v_migrations
                WHERE txType = 'migrate' AND timestamp >= NOW() - INTERVAL '1 hour'
            )
            -- Combine tokens with events and filter by staleness
            SELECT t.mint
            FROM tokens t
            WHERE t.is_active = TRUE
              AND (t.mint IN (SELECT mint FROM SignificantRugChange) OR
                   t.mint IN (SELECT mint FROM SignificantSocialChange) OR
                   t.mint IN (SELECT mint FROM RecentMigrations))
              AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($3 || ' minutes')::interval);
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, rug_change_threshold, social_change_threshold, str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
             if not conn and connection: await self.pool.release(connection)

    async def get_stale_tokens_for_ai_eval(self, batch_size: int, staleness_minutes: int, conn=None):
        """Fetches the oldest evaluated active tokens needing AI refresh."""
        query = f"""
            SELECT mint
            FROM tokens
            WHERE is_active = TRUE
              AND (ai_last_evaluation_ts IS NULL OR ai_last_evaluation_ts < NOW() - ($2 || ' minutes')::interval)
            ORDER BY ai_last_evaluation_ts ASC NULLS FIRST -- Oldest first
            LIMIT $1;
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, batch_size, str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
             if not conn and connection: await self.pool.release(connection)

    # --- (End of new methods) ---

    async def update_portfolio_highest_price(self, position_id: int, price: float, conn=None):
        """Updates the highest price for a given portfolio position."""
        query = 'UPDATE portfolio SET highest_price = $1 WHERE id = $2'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, price, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def mark_first_tp_hit_and_adjust_sl(self, position_id: int, buy_price: float, conn=None):
        """Marks the first TP as hit and adjusts the stop loss to breakeven."""
        query = 'UPDATE portfolio SET first_tp_hit = TRUE, stop_loss_price = $1 WHERE id = $2'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, buy_price, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_portfolio_entry_for_update(self, position_id: int, conn=None):
        """Fetches a specific portfolio buy entry needed for sell calculations."""
        query = '''
            SELECT price AS buy_price, initial_tokens, remaining_tokens, total_investment_sol, fee AS buy_fee, tip AS buy_tip
            FROM portfolio
            WHERE id = $1 AND status = 'active' AND tx_type = 'buy'
        '''
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def update_portfolio_entry_after_sell(self, position_id: int, new_remaining_tokens: float, new_status: str, conn=None):
        """Updates remaining tokens and status of a portfolio entry after a sell."""
        query = 'UPDATE portfolio SET remaining_tokens = $1, status = $2 WHERE id = $3'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, new_remaining_tokens, new_status, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def insert_portfolio_sell_record(self, mint: str, current_price: float, market_cap_sol: float, net_sol_received: float, sol_price_usd: float, tokens_sold: float, sell_fee: float, sell_tip: float, profit: float, reason: str, timestamp: datetime, settings: dict, ai_context: Optional[dict] = None, conn=None):
        """Inserts a sell transaction record into the portfolio, including settings."""
        query = '''
            INSERT INTO portfolio
            (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, tokens, fee, tip, profit, total_investment_sol,
             remaining_tokens, status, reason, timestamp, initial_tokens, stop_loss_price, highest_price, settings)
            VALUES ($1, 'sell', $2, $3, $4, $5, $6, $7, $8, $9, 0, 0, 'closed', $10, $11, 0, 0, 0, $12)
        '''
        connection = conn or await self.pool.acquire()
        try:
            if ai_context:
                settings['ai_advice_at_sell'] = ai_context # Add AI info
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, net_sol_received, sol_price_usd, tokens_sold,
                                   sell_fee, sell_tip, profit, reason, timestamp, settings_json)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_token_name(self, mint: str, conn=None):
        """Fetches the name of a token given its mint address."""
        query = "SELECT name FROM tokens WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, mint)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def insert_portfolio_buy_record(self, mint: str, current_price: float, market_cap_sol: float, sol_base_amount: float, sol_price_usd: float, total_sol_investment: float, tokens_bought: float, buy_fee: float, buy_tip: float, initial_stop_loss_price: float, initial_tp_price: float, second_tp_price: float, timestamp: datetime, settings: dict, buy_reason: str, ai_context: Optional[dict] = None, conn=None): # <<< 1. ADD buy_reason: str
        """Inserts a buy transaction record into the portfolio, including settings."""
        query = """
            INSERT INTO portfolio
                (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, total_investment_sol, tokens,
                 fee, tip, remaining_tokens, stop_loss_price, highest_price,
                 initial_tp_price, second_tp_price, first_tp_hit,
                 status, timestamp, initial_tokens, settings, buy_reason) -- <<< 2. ADD buy_reason
            VALUES ($1, 'buy', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, FALSE, 'active', $15, $16, $17, $18) -- <<< 3. ADD $18
        """
        connection = conn or await self.pool.acquire()
        try:
            if ai_context:
                settings['ai_advice_at_buy'] = ai_context
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, sol_base_amount, sol_price_usd, total_sol_investment, tokens_bought,
                                   buy_fee, buy_tip, tokens_bought, # remaining_tokens = initial_tokens
                                   initial_stop_loss_price, current_price, # highest_price = current_price
                                   initial_tp_price, second_tp_price,
                                   timestamp, tokens_bought, # initial_tokens
                                   settings_json, buy_reason) # <<< 4. PASS buy_reason
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    # Modify existing has_active_buy_order to accept optional connection
    async def has_active_buy_order(self, mint: str, conn=None):
        query = """
            SELECT 1 FROM portfolio WHERE mint = $1 AND tx_type = 'buy' AND status = 'active'
        """
        connection = conn or await self.pool.acquire()
        try:
            result = await connection.fetchval(query, mint)
            return result is not None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_last_trade_timestamp(self, mint: str) -> Optional[datetime]:
        """Get the timestamp of the last trade for a given mint."""
        query = "SELECT timestamp FROM v_unified_market_ticks_live WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, mint)
            return row['timestamp'] if row else None

    async def get_trade_history(self, mints: list[str]):
        """Fetches price and timestamp for given mints from trades and trades_backup."""
        if not mints:
            return []
        # Ensure logger is accessible if used within the method, assuming it's defined globally or passed in
        # from logger import logger # Uncomment if logger is needed and not globally accessible
        # Use the v_trades view which combines trades and trades_backup
        query = """
            SELECT mint, price_sol as price, timestamp
            FROM v_unified_market_ticks_historical -- CORRECT: Uses HISTORICAL view
            WHERE mint = ANY($1::text[])
            ORDER BY mint, timestamp;
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, mints)
                # Convert asyncpg Record objects to dictionaries for easier handling
                return [dict(row) for row in results]
            except Exception as e:
                # Log the error using the logger instance
                logger.error(f":police_car_light: Error fetching trade history for mints {mints}: {e}", exc_info=True)
                return [] # Return empty list on error

    async def get_all_unique_mints_with_names(self):
        """Fetches all unique mint addresses and their names from relevant tables."""
        # This query prioritizes names from the 'tokens' table, falling back to 'tokens_backup'.
        # It assumes mints exist in trades/trades_backup might also exist in tokens/tokens_backup.
        # Use the v_tokens and v_rugcheck views
        # Fetch symbol, socials_score, and latest rugcheck score for display
        query = """
            WITH LatestRugcheck AS (
                SELECT
                    mint,
                    score,
                    ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) as rn
                FROM v_rugcheck -- Use the rugcheck view
            )
            SELECT
                vt.mint,
                COALESCE(vt.name, vt.mint) AS name, -- Fallback to mint if name is null
                vt.symbol,
                vt.socials_score,
                lr.score AS rugcheck_score
            FROM v_tokens vt -- Use the tokens view
            LEFT JOIN LatestRugcheck lr ON vt.mint = lr.mint AND lr.rn = 1
            WHERE vt.mint IS NOT NULL -- Ensure mint is not null from the view
            ORDER BY name, vt.mint; -- Order by name from the view
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query) # No parameters needed for this version using views
                # Return list of dictionaries
                # Return richer dictionary including scores
                return [
                    {
                        'mint': row['mint'],
                        'name': row['name'],
                        'symbol': row['symbol'],
                        'socials_score': row['socials_score'],
                        'rugcheck_score': row['rugcheck_score'] # Might be None
                    } for row in results
                ]
            except Exception as e:
                logger.error(f":police_car_light: Error fetching unique mints with names: {e}", exc_info=True)
                return []
            
    async def get_all_migrated_tokens(self) -> List[str]:
        """Fetches all active tokens that have been marked as migrated to DEXScreener."""
        query = "SELECT mint FROM tokens WHERE data_source = 'DEXSCREENER' AND is_active = TRUE ORDER BY timestamp DESC"
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [row['mint'] for row in rows]
        except Exception as e:
            logger.error(f":police_car_light: Error fetching migrated tokens: {e}", exc_info=True)
            return []

    async def get_filtered_tokens(self, max_socials=100, max_rugcheck=10000, min_volume_sol=0, time_window_minutes=60, portfolio_only=False):
        """
        Fetches tokens filtered by:
        - socials score <= max_socials
        - latest rugcheck score <= max_rugcheck (or NULL)
        - trade volume in the last time_window_minutes relative to the token's latest trade >= min_volume_sol
        - optionally filters to tokens in the active portfolio
        """

        try:
            max_socials = int(max_socials)
            max_rugcheck = int(max_rugcheck)
            min_volume_sol = float(min_volume_sol)
            time_window_minutes = str(time_window_minutes)
        except (ValueError, TypeError):
            logger.error("Invalid filter parameter types received.")
            return []

        params = [max_socials, max_rugcheck, min_volume_sol, time_window_minutes]

        query = """
        WITH LatestRugcheck AS (
            SELECT
                mint,
                score,
                ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) AS rn
            FROM v_rugcheck
        ),
        LastTrades AS (
            SELECT
                mint,
                MAX(timestamp) AS last_trade_time
            FROM v_trades
            GROUP BY mint
        ),
        FilteredTrades AS (
            SELECT
                t.mint,
                SUM(t.sol_amount) AS volume_sol
            FROM v_trades t
            JOIN LastTrades lt ON t.mint = lt.mint
            WHERE t.timestamp BETWEEN (lt.last_trade_time - ($4 || ' minutes')::INTERVAL) AND lt.last_trade_time
            GROUP BY t.mint
        )
        SELECT DISTINCT
            vt.mint,
            COALESCE(vt.name, vt.mint) AS name,
            vt.socials_score,
            lr.score AS rugcheck_score,
            COALESCE(ft.volume_sol, 0) AS recent_volume_sol
        FROM v_tokens vt
        LEFT JOIN LatestRugcheck lr ON vt.mint = lr.mint AND lr.rn = 1
        LEFT JOIN FilteredTrades ft ON vt.mint = ft.mint
        """

        if portfolio_only:
            query += """
            INNER JOIN portfolio p ON vt.mint = p.mint
            """

        query += """
        WHERE
            vt.socials_score IS NOT NULL AND vt.socials_score <= $1
            AND (lr.score IS NULL OR lr.score <= $2)
            AND COALESCE(ft.volume_sol, 0) >= $3
        ORDER BY name, vt.mint;
        """
        print(f"Query: {query}")
        print(f"params: {params}")
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, *params)
                return [
                    {
                        'mint': row['mint'],
                        'name': row['name'],
                        'socials': row['socials_score'],
                        'rugcheck': row['rugcheck_score'],
                        'volume': round(row['recent_volume_sol'], 4)
                    } for row in results
                ]
            except Exception as e:
                logger.error(f":police_car_light: Error fetching filtered tokens: {e}", exc_info=True)
                return []


    async def get_portfolio_transactions(self, mints: list[str]):
        """Fetches buy/sell transaction timestamps and prices for given mints from the portfolio."""
        if not mints:
            return {} # Return empty dict if no mints provided

        query = """
            SELECT mint, tx_type, timestamp, price
            FROM portfolio
            WHERE mint = ANY($1::text[])
            ORDER BY mint, timestamp;
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, mints)
                portfolio_data = {}
                for row in results:
                    mint = row['mint']
                    if mint not in portfolio_data:
                        portfolio_data[mint] = {'buys': [], 'sells': []}

                    # Keep the original timestamp object and ensure price is float
                    tx_info = {'timestamp': row['timestamp'], 'price': float(row['price'])}

                    if row['tx_type'] == 'buy':
                        portfolio_data[mint]['buys'].append(tx_info)
                    elif row['tx_type'] == 'sell':
                        portfolio_data[mint]['sells'].append(tx_info)

                logger.debug(f"Fetched portfolio transactions for mints: {mints}")
                return portfolio_data
            except Exception as e:
                logger.error(f":police_car_light: Error fetching portfolio transactions for mints {mints}: {e}", exc_info=True)
                return {} # Return empty dict on error
            
    # In class DatabaseClient:

    async def get_creator_history_summary(self, creator_wallet: str, current_mint: str) -> Tuple[str, dict]:
        """
        [REFACTORED]
        Analyzes a creator's past tokens and generates a summary string AND
        a structured metadata dictionary for the AI.
        """
        if not creator_wallet:
            return "Creator wallet not specified.", {}

        query = """
        WITH PastTokens AS (
            SELECT
                t.mint,
                t.marketCapSol AS creation_mcap,
                (SELECT MAX(tr.marketCapSol) FROM v_trades tr WHERE tr.mint = t.mint) AS max_mcap,
                ( (SELECT MAX(tr.timestamp) FROM v_trades tr WHERE tr.mint = t.mint) -
                  (SELECT MIN(tr.timestamp) FROM v_trades tr WHERE tr.mint = t.mint) ) AS lifespan,
                tb.backup_reason
            FROM v_tokens t
            LEFT JOIN tokens_backup tb ON t.mint = tb.mint
            WHERE t.traderPublicKey = $1 AND t.mint != $2
        )
        SELECT * FROM PastTokens WHERE max_mcap IS NOT NULL OR backup_reason IS NOT NULL;
        """
        
        summary_dict = {
            "creator_total_launches": 0,
            "creator_rug_count": 0,
            "creator_rug_rate": 0.0,
            "creator_good_runs_count": 0,
            "creator_avg_lifespan_minutes": 0.0
        }

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, creator_wallet, current_mint)

            if not rows:
                return "This is the creator's first token.", summary_dict

            total_tokens = len(rows)
            rugged_count = 0
            good_runs_count = 0
            total_lifespan_minutes = 0
            lifespan_count = 0

            # Define "rugged"
            rug_reasons = {'high_rugcheckscore', 'dead_token'}

            for row in rows:
                if row['backup_reason'] in rug_reasons:
                    rugged_count += 1
                
                # Define "good run" (e.g., > 10x MCap from creation)
                if row['max_mcap'] and row['creation_mcap'] and row['max_mcap'] > (row['creation_mcap'] * 10):
                    good_runs_count += 1
                
                if row['lifespan']:
                    total_lifespan_minutes += row['lifespan'].total_seconds() / 60
                    lifespan_count += 1

            avg_lifespan_str = "N/A"
            avg_lifespan_minutes_val = 0.0
            if lifespan_count > 0:
                avg_lifespan_minutes_val = total_lifespan_minutes / lifespan_count
                if avg_lifespan_minutes_val < 120:
                    avg_lifespan_str = f"{avg_lifespan_minutes_val:.0f} minutes"
                else:
                    avg_lifespan_str = f"{avg_lifespan_minutes_val / 60:.1f} hours"

            summary_string = (
                f"Creator has {total_tokens} past tokens. "
                f"{rugged_count} were rugged. "
                f"{good_runs_count} achieved >10x MCap. "
                f"Average lifespan: {avg_lifespan_str}."
            )
            
            summary_dict = {
                "creator_total_launches": total_tokens,
                "creator_rug_count": rugged_count,
                "creator_rug_rate": (rugged_count / total_tokens) if total_tokens > 0 else 0.0,
                "creator_good_runs_count": good_runs_count,
                "creator_avg_lifespan_minutes": avg_lifespan_minutes_val
            }
            
            return summary_string, summary_dict

        except Exception as e:
            logger.error(f"Error generating creator history summary for {creator_wallet}: {e}", exc_info=True)
            return "Error generating creator history.", summary_dict

    async def backup_and_delete_token(self, mint: str, archived_at: datetime, reason: str=None):
        """Backup core table data to a corresponding backup table."""

        # --- START: ADD THIS SAFETY CHECK BLOCK ---
        try:
            async with self.pool.acquire() as conn:
                is_active_in_portfolio = await conn.fetchval(
                    "SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' LIMIT 1",
                    mint
                )
                if is_active_in_portfolio:
                    logger.critical(
                        f"CRITICAL SAFEGUARD: Prevented backup/deletion of token {mint} because it has an ACTIVE position in the portfolio. Reason for attempted deletion: '{reason}'."
                    )
                    # Deactivate the token in the 'tokens' table so it's not picked up by other processes,
                    # but DO NOT delete it, allowing the sell logic to continue managing the position.
                    await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                    return # Exit the function immediately.
        except Exception as e:
            logger.error(f":police_car_light: Error during safety check in backup_and_delete_token for {mint}: {e}", exc_info=True)
            return # Exit on error to be safe
        # --- END: ADD THIS SAFETY CHECK BLOCK ---
        final_reason = reason # Initialize final_reason with the provided reason
 
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                                    INSERT INTO tokens_backup (
                                        mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
                                        vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
                                        socials_score, socials_last_checked, sol_price_usd, is_active, last_trade, timestamp,
                                        cooldown_until,
                                        backup_reason, backup_timestamp
                                    )
                                    SELECT
                                        mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
                                        vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
                                        socials_score, socials_last_checked, sol_price_usd, is_active, last_trade, timestamp,
                                        cooldown_until,
                                        $1, NOW()
                                    FROM tokens
                                    WHERE mint = $2
                                ''', final_reason, mint)
                        
                        await conn.execute('''
                            INSERT INTO trades_backup SELECT *, NOW() FROM trades WHERE mint = $1
                        ''', mint)
 
                        await conn.execute('''
                            INSERT INTO rugcheck_backup SELECT *, NOW() FROM rugcheck WHERE mint = $1
                        ''', mint)

                        await conn.execute('''
                            INSERT INTO social_scores_backup (id, mint, timestamp, score_type, score_value, details, backup_timestamp)
                            SELECT id, mint, timestamp, score_type, score_value, details, NOW() FROM social_scores WHERE mint = $1
                        ''', mint)
 
                        # Backup migrations, ignoring conflicts on the primary key
                        await conn.execute('''
                            INSERT INTO migrations_backup SELECT *, NOW() FROM migrations WHERE mint = $1
                            ON CONFLICT (signature) DO NOTHING -- Conflict check on signature
                        ''', mint)

                        await conn.execute('''
                            INSERT INTO dexscreener_data_backup SELECT *, NOW() FROM dexscreener_data WHERE mint_address = $1
                        ''', mint)
 
                        await conn.execute("DELETE FROM tokens WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM trades WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM rugcheck WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM social_scores WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM migrations WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM dexscreener_data WHERE mint_address = $1", mint)
 
                        logger.debug(f"🧹 Backup & deletion completed for {mint}")
 
                    except Exception as e:
                        logger.error(f"❌ Backup failed for {mint}: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f":police_car_light: backup_and_delete_token: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def backup_creator_wallets(self):
        """Dumps the creator_wallets table to a JSON file."""
        backup_file_path = os.path.join(os.path.dirname(__file__), self.config.get("_BACKUP_STORAGE_PATH", "backups"), "creator_wallets_backup.json")
        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)  # Ensure data directory exists

        logger.info("Backing up creator_wallets table...")
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT wallet_address, token_count, last_token_time FROM creator_wallets")
                
                # Convert rows to a list of dictionaries
                data = [
                    {
                        "wallet_address": row["wallet_address"],
                        "token_count": row["token_count"],
                        "last_token_time": row["last_token_time"].isoformat() if row["last_token_time"] else None
                    }
                    for row in rows
                ]
                
                # Write the data to a JSON file
                async with aiofiles.open(backup_file_path, "w") as f:
                    await f.write(json.dumps(data, indent=4))
                
                logger.info(f"✅ Successfully backed up {len(rows)} creator wallets to {backup_file_path}")
        except Exception as e:
            logger.exception(f":police_car_light: Error backing up creator_wallets table: {e}")
            # Decide if we should raise or just log


    async def restore_creator_wallets(self):
        backup_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            self.config.get("_BACKUP_STORAGE_PATH", "backups"), 
            "creator_wallets_backup.json"
        ))

        if not os.path.exists(backup_path):
            logger.warning("Backup file not found: %s", backup_path)
            return

        try:
            with open(backup_path, "r") as f:
                data = json.load(f)

            # Convert JSON data into tuples for faster insertion
            records = [
                (
                    record["wallet_address"],
                    record["token_count"],
                    datetime.fromisoformat(record["last_token_time"]) if record.get("last_token_time") else None
                )
                for record in data
            ]

            # Batch size
            BATCH_SIZE = 100

            # Insert using batches
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]
                sql = """
                    INSERT INTO creator_wallets (wallet_address, token_count, last_token_time)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (wallet_address) DO UPDATE SET
                        token_count = GREATEST(creator_wallets.token_count, EXCLUDED.token_count),
                        last_token_time = CASE
                            WHEN EXCLUDED.token_count > creator_wallets.token_count THEN EXCLUDED.last_token_time
                            ELSE creator_wallets.last_token_time
                        END;
                """
                async with self.pool.acquire() as conn:
                    await conn.executemany(sql, batch)

            logger.info("Loaded backup data from %s (%d records)", backup_path, len(records))

        except Exception as e:
            logger.exception(":police_car_light: Error loading backup data: %s", e)
            raise

    # --- START: Refactored Price Calculation Logic ---
    async def _get_raw_trades_for_window(self, mint: str, window_minutes: float, conn) -> List[Dict[str, Any]]:
        """Fetches raw trades (timestamp, sol_amount, token_amount) for a given window."""
        query = """
            SELECT timestamp, sol_amount, token_amount
            FROM trades
            WHERE mint = $1
            AND timestamp >= NOW() - ($2 || ' minutes')::interval
            AND token_amount > 0 AND sol_amount > 0 -- Ensure valid amounts for price calculation
            ORDER BY timestamp ASC;
        """
        return await conn.fetch(query, mint, str(window_minutes))
    
    async def _get_latest_token_info(self, mint: str, conn) -> Dict[str, Optional[float]]:
        """
        Fetches the latest token_supply and token_decimals for a mint.
        It queries rugcheck and rugcheck_backup directly as v_rugcheck might not have token_decimals.
        """
        query = """
            SELECT
                token_supply,
                token_decimals
            FROM (
                SELECT
                    token_supply,
                    token_decimals,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY COALESCE(last_checked, '1970-01-01'::timestamptz) DESC) as rn
                FROM (
                    SELECT mint, token_supply, token_decimals, last_checked FROM rugcheck WHERE mint = $1
                    UNION ALL
                    SELECT mint, token_supply, token_decimals, last_checked FROM rugcheck_backup WHERE mint = $1
                ) combined_rugcheck_data
                WHERE token_supply IS NOT NULL AND token_supply > 0
                  AND token_decimals IS NOT NULL AND token_decimals >= 0
            ) ranked_supply_info
            WHERE rn = 1;
        """
        record = await conn.fetchrow(query, mint)
        if record:
            return {'token_supply': float(record['token_supply']), 'token_decimals': int(record['token_decimals'])}
        else:
            logger.warning(f"No token_supply/decimals found in rugcheck/rugcheck_backup for {mint}. Using default supply from config.")
            # Using _TOTAL_SUPPLY and assuming default decimals (e.g., 9, or make it configurable)
            # For this example, let's assume a common default like 6 if not found, or make it part of config
            default_decimals = self.config.get('_DEFAULT_DECIMALS_FOR_MISSING', 6) # Add to config if needed
            return {'token_supply': float(self.config.get('_TOTAL_SUPPLY', 1_000_000_000)), 'token_decimals': default_decimals}


    # --- START: MODIFIED/NEW Price Calculation Helper Logic ---

    async def _get_raw_trades_for_price_calc(self, mint: str, config_params: dict, conn) -> List[Dict[str, Any]]:
        """
        Fetches raw trades (timestamp, sol_amount, token_amount) for a given window,
        supporting both time-based and count-based windows.
        """
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        # Common base of the query selecting necessary columns and initial filters
        query_select_cols = "SELECT timestamp, sol_amount, token_amount, price_sol"
        query_from_where = """
            FROM v_unified_market_ticks_live -- <<< CHANGE TO LIVE VIEW
            WHERE mint = $1
            AND sol_amount IS NOT NULL AND sol_amount > 0 
            AND token_amount IS NOT NULL AND token_amount > 0
        """
        params = [mint]
        final_query: str

        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            # For time window, order by timestamp ascending directly
            final_query = query_select_cols + query_from_where + f" AND timestamp >= NOW() - ($2::text || ' minutes')::interval ORDER BY timestamp ASC;"
            params.append(window_minutes)
        elif window_type == "count":
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            # For count window:
            # 1. Subquery selects the latest N trades.
            # 2. Outer query orders these N trades by timestamp ascending.
            final_query = f"""
                SELECT timestamp, sol_amount, token_amount, price_sol
                FROM (
                    {query_select_cols}
                    {query_from_where} 
                    ORDER BY timestamp DESC
                    LIMIT $2 
                ) AS latest_n_trades
                ORDER BY timestamp ASC;
            """
            # Parameter $1 is mint, $2 is trade_count
            params.append(trade_count)
        else:
            logger.warning(f"Unknown PRICE_WINDOW_TYPE: {window_type}. Defaulting to time window of 1 min.")
            final_query = query_select_cols + query_from_where + " AND timestamp >= NOW() - INTERVAL '1 minute' ORDER BY timestamp ASC;"
        
        return await conn.fetch(final_query, *params)

    async def _get_raw_marketcaps_for_calc(self, mint: str, config_params: dict, conn) -> List[Dict[str, Any]]:
        """
        Fetches raw marketCapSol values from trades for a given window,
        supporting both time-based and count-based windows.
        """
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        query_select_cols = "SELECT timestamp, market_cap_sol"
        query_from_where = """
            FROM v_unified_market_ticks_live -- <<< CHANGE TO LIVE VIEW
            WHERE mint = $1
            AND market_cap_sol IS NOT NULL AND market_cap_sol > 0
        """
        params = [mint]
        final_query: str

        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            final_query = query_select_cols + query_from_where + f" AND timestamp >= NOW() - ($2::text || ' minutes')::interval ORDER BY timestamp ASC;"
            params.append(window_minutes)
        elif window_type == "count":
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            final_query = f"""
                SELECT *
                FROM (
                    {query_select_cols}
                    {query_from_where}
                    ORDER BY timestamp DESC
                    LIMIT $2
                ) AS latest_n_marketcaps
                ORDER BY timestamp ASC;
            """
            params.append(trade_count)
        else:
            logger.warning(f"Unknown PRICE_WINDOW_TYPE: {window_type}. Defaulting to time window of 1 min for MC calc.")
            final_query = query_select_cols + query_from_where + " AND timestamp >= NOW() - INTERVAL '1 minute' ORDER BY timestamp ASC;"
                
        return await conn.fetch(final_query, *params)

    def _apply_iqr_to_trades(self, trade_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates prices for trades and applies IQR filtering.
        Returns a list of trade records that are considered inliers.
        """
        if not trade_records:
            return []

        prices = []
        for r in trade_records:
            try:
                price = float(r['sol_amount']) / float(r['token_amount'])
                prices.append(price)
            except (TypeError, ValueError, ZeroDivisionError):
                prices.append(None) # Mark invalid prices

        # Filter out None prices before IQR
        valid_prices_for_iqr = [p for p in prices if p is not None]
        if not valid_prices_for_iqr:
            logger.warning("No valid prices to apply IQR filtering.")
            return [] # Return all trades if no valid prices for IQR

        q1 = np.percentile(valid_prices_for_iqr, 25)
        q3 = np.percentile(valid_prices_for_iqr, 75)
        iqr_val = q3 - q1
        lower_bound = q1 - 1.5 * iqr_val
        upper_bound = q3 + 1.5 * iqr_val

        inlier_trades = []
        for i, r in enumerate(trade_records):
            price = prices[i]
            if price is not None and lower_bound <= price <= upper_bound:
                # Add the calculated price to the trade record for convenience
                r_copy = dict(r) # Create a copy to avoid modifying the original record list
                r_copy['price'] = price
                inlier_trades.append(r_copy)

        if not inlier_trades:
            logger.warning("All trades filtered out as outliers by IQR. No inlier trades to use.")
            # Fallback: could return unfiltered trades or a subset based on other criteria
            # For now, returning empty list, forcing price calculation to fail or use other fallbacks.
            return []
        return inlier_trades
    
    def _apply_iqr_to_values(self, values: List[float]) -> List[float]: #
        if not values or len(values) < 4: #
            return values #

        try:
            q1 = np.percentile(values, 25) #
            q3 = np.percentile(values, 75) #
            iqr_val = q3 - q1 #
            
            if iqr_val == 0: #
                return values #

            lower_bound = q1 - 1.5 * iqr_val #
            upper_bound = q3 + 1.5 * iqr_val #
            inliers = [v for v in values if lower_bound <= v <= upper_bound] #
            
            if not inliers: #
                logger.warning("IQR filtering removed all values. Returning original values as fallback.") #
                return values #
            return inliers #
        except Exception as e:
            logger.error(f":police_car_light: Error during IQR calculation for values: {e}. Returning original values.", exc_info=True) #
            return values #

    async def _calculate_median_price_with_iqr(self, mint: str, config_params: dict, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades: #
            all_prices = [float(r['sol_amount'])/float(r['token_amount']) for r in trade_records if r.get('token_amount') and float(r['token_amount']) > 0 and r.get('sol_amount') is not None] #
            if all_prices: #
                 logger.warning(f"All prices for {mint} filtered by IQR. Falling back to unfiltered median for price calc.") #
                 return statistics.median(all_prices) #
            return None #

        inlier_prices = [float(trade['price']) for trade in inlier_trades] #
        return statistics.median(inlier_prices) if inlier_prices else None #

    async def _calculate_vwap_price_with_iqr(self, mint: str, config_params: dict, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades: #
            # Could add fallback to unfiltered VWAP here if desired
            logger.warning(f"No inlier trades for {mint} after IQR for VWAP calculation.") #
            return None #

        total_sol_inliers = sum(float(trade['sol_amount']) for trade in inlier_trades) #
        total_tokens_inliers = sum(float(trade['token_amount']) for trade in inlier_trades) #

        if total_tokens_inliers == 0: #
            return None #
        return total_sol_inliers / total_tokens_inliers #

    async def _calculate_twap_price_with_iqr(self, mint: str, config_params: dict, interval_seconds: int, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades_with_price = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades_with_price: #
            return None #

        df_data = [{'timestamp': pd.to_datetime(trade['timestamp'], utc=True), 'price': float(trade['price'])} for trade in inlier_trades_with_price] #
        df = pd.DataFrame(df_data) #
        if df.empty: return None #
        df = df.set_index('timestamp') #
        
        interval_prices = df['price'].resample(f'{interval_seconds}S').median(numeric_only=True) #
        valid_interval_prices = interval_prices.dropna() #
        if valid_interval_prices.empty: return None #
        
        twap = valid_interval_prices.mean() #
        return float(twap) if pd.notnull(twap) else None #

    # New helper for robust median market cap
    async def _calculate_median_marketcap_with_iqr(self, mint: str, config_params: dict, conn) -> float | None:
        trade_records_for_mc = await self._get_raw_marketcaps_for_calc(mint, config_params, conn)
        # logger.debug(f"Fetched {len(trade_records_for_mc)} market cap records for {mint}.")
        # logger.debug(f"First 5 records: {trade_records_for_mc[:5]}") # Debugging output)
        if not trade_records_for_mc:
            logger.debug(f"No market cap records found for {mint}. Cannot calculate median market cap.")
            return None

        market_caps = [float(r['market_cap_sol']) for r in trade_records_for_mc if r.get('market_cap_sol') is not None] #
        if not market_caps:
            logger.debug(f"No valid market caps found for {mint}. Cannot calculate median market cap.")
            return None #

        inlier_market_caps = self._apply_iqr_to_values(market_caps) #
        if not inlier_market_caps:
            logger.warning(f"All market caps for {mint} filtered by IQR. Falling back to unfiltered median for MC calc.") #
            return statistics.median(market_caps) if market_caps else None #
        
        return statistics.median(inlier_market_caps) if inlier_market_caps else None


    async def _get_migration_timestamp(self, mint: str, conn) -> Optional[datetime]:
        """Fetches the timestamp of when a token was migrated."""
        query = "SELECT timestamp FROM migrations WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1"
        migration_ts = await conn.fetchval(query, mint)
        return migration_ts

    async def _get_latest_price_from_dexscreener(self, mint: str, conn) -> Dict[str, Optional[float]]:
        """
        [MODIFIED] Fetches the single latest price snapshot for a migrated token,
        with a grace period for newly migrated tokens to allow for data aggregation.
        """
        query = """
            SELECT price_usd, market_cap, sol_price_usd, volume_m5, price_native
            FROM dexscreener_data
            WHERE mint_address = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        record = await conn.fetchrow(query, mint)

        # --- START OF FIX ---
        # Initial checks for fundamental data validity.
        if not record or not record['price_usd'] or not record['sol_price_usd'] or record['sol_price_usd'] <= 0:
            logger.warning(f"DEXScreener data for {mint} is missing critical price data. Treating as invalid.")
            return {'price': None, 'market_cap': None}

        # Now check for staleness (0 volume), but apply a grace period for newly migrated tokens.
        is_stale_by_volume = float(record['volume_m5']) <= 0
        is_within_grace_period = False

        # Check migration timestamp to determine if we are in the grace period.
        migration_ts = await self._get_migration_timestamp(mint, conn)
        if migration_ts:
            grace_period_minutes = self.config.get('DEXSCREENER_MIGRATION_GRACE_PERIOD_MINUTES', 5)
            time_since_migration = datetime.now(timezone.utc) - migration_ts
            if time_since_migration < timedelta(minutes=grace_period_minutes):
                is_within_grace_period = True
                logger.debug(f"Token {mint} is within the {grace_period_minutes}-minute migration grace period ({time_since_migration.total_seconds():.0f}s ago). Stale volume check will be bypassed.")

        # The price is considered invalid ONLY IF it's stale by volume AND we are NOT within the grace period.
        # If the volume is stale and we are outside the grace period, the price is invalid.
        # However, we MUST still return the last known market cap.
        if is_stale_by_volume and not is_within_grace_period:
            logger.warning(f"DEXScreener data for {mint} is stale (0 volume in m5). Price is invalid, but using latest market cap for safety checks.")
            # Calculate the market cap in SOL from the USD values in the record
            market_cap_usd = float(record['market_cap'])
            sol_price_usd = float(record['sol_price_usd'])
            market_cap_sol = market_cap_usd / sol_price_usd
            price = float(record['price_native'])
            # Return a valid market cap but an invalid price
            return {'price': price, 'market_cap': market_cap_sol}

        price_usd = float(record['price_usd'])
        market_cap_usd = float(record['market_cap'])
        sol_price_usd = float(record['sol_price_usd'])

        # Convert to SOL-denominated values for consistency
        price_sol = price_usd / sol_price_usd
        market_cap_sol = market_cap_usd / sol_price_usd

        return {'price': price_sol, 'market_cap': market_cap_sol}

    async def _get_robust_price_from_pump(self, mint: str, config_params: dict, conn) -> Dict[str, Optional[float]]:
        """
        MODIFIED LOGIC: Calculates robust price ONLY from Pump.fun trades.
        This re-uses your existing median/vwap/twap logic but on a clean data source.
        """
        # Note: Your existing helper functions like _calculate_median_price_with_iqr,
        # _calculate_vwap_price_with_iqr, and their own helpers (_get_raw_trades_for_price_calc)
        # would need to be modified to query the `trades` table directly instead of `v_unified_market_ticks_live`.
        # For simplicity, we will implement the MEDIAN calculation directly here.
        
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        # Build query to fetch raw trades only from the `trades` table
        params = [mint]
        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            query = """
                SELECT price, marketCapSol FROM trades
                WHERE mint = $1 AND timestamp >= NOW() - ($2::text || ' minutes')::interval
                ORDER BY timestamp DESC;
            """
            params.append(window_minutes)
        else: # 'count'
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            query = """
                SELECT price, marketCapSol FROM trades
                WHERE mint = $1 ORDER BY timestamp DESC LIMIT $2;
            """
            params.append(trade_count)

        trade_records = await conn.fetch(query, *params)
        if not trade_records:
            return {'price': None, 'market_cap': None}

        # Apply IQR outlier removal and calculate median
        prices = [float(r['price']) for r in trade_records if r.get('price') is not None]
        market_caps = [float(r['marketcapsol']) for r in trade_records if r.get('marketcapsol') is not None]

        if not prices:
             return {'price': None, 'market_cap': None}

        # Using your _apply_iqr_to_values helper for simplicity
        inlier_prices = self._apply_iqr_to_values(prices)
        inlier_market_caps = self._apply_iqr_to_values(market_caps)

        final_price = statistics.median(inlier_prices) if inlier_prices else None
        final_market_cap = statistics.median(inlier_market_caps) if inlier_market_caps else None
        
        return {'price': final_price, 'market_cap': final_market_cap}

    async def get_price_and_market_cap_for_decision(self, mint: str, config_from_caller: dict, conn) -> Dict[str, Optional[float]]:
        """
        [MODIFIED] Centralized function to get the decision price and market cap for a token.
        If a token is marked as migrated ('DEXSCREENER') but its Dexscreener data is invalid
        (e.g., no recent volume, or no data yet), it will temporarily fall back to using
        its last known Pump.fun data if the migration occurred within a grace period.
        """
        # 1. Determine the data source for the token
        token_record = await conn.fetchrow("SELECT data_source FROM tokens WHERE mint = $1", mint)

        if not token_record:
            logger.warning(f":triangular_flag: Could not find token {mint} in 'tokens' table to determine data source.")
            return {'price': None, 'market_cap': None}

        data_source = token_record['data_source']
        #logger.debug(f":bar_chart: Getting price for {mint}. Primary source: {data_source}")

        # 2. Branch logic based on the data source
        if data_source == 'DEXSCREENER':
            # For migrated tokens, first attempt to get the latest clean price from dexscreener_data
            price_data = await self._get_latest_price_from_dexscreener(mint, conn)

            # --- START: FALLBACK SECURITY LAYER ---
            # If Dexscreener data is invalid (e.g., stale volume, or no data yet),
            # check if we are within the migration grace period.
            if price_data.get('price') is None:
                migration_ts = await self._get_migration_timestamp(mint, conn)
                if migration_ts:
                    grace_period_minutes = self.config.get('DEXSCREENER_MIGRATION_GRACE_PERIOD_MINUTES', 5)
                    time_since_migration = datetime.now(timezone.utc) - migration_ts
                    
                    if time_since_migration < timedelta(minutes=grace_period_minutes):
                        logger.info(
                            f"DEXScreener price for {mint} is invalid, but token is within the {grace_period_minutes}-minute "
                            f"migration grace period ({time_since_migration.total_seconds():.0f}s ago). "
                            f"Attempting to fall back to last known Pump.fun data."
                        )
                        # Fall back to using robust calculation on its (now historical) Pump.fun trades.
                        return await self._get_robust_price_from_pump(mint, config_from_caller, conn)
            # --- END: FALLBACK SECURITY LAYER ---

            # If not in grace period or if Dexscreener data was valid, return the original result.
            return price_data
            
        else: # 'PUMP'
            # For non-migrated tokens, use the robust calculation to handle outliers
            return await self._get_robust_price_from_pump(mint, config_from_caller, conn)


    async def analyze_dexscreener_trend(self, mint: str, lookback_minutes: int, conn) -> list:
        """
        Fetches recent dexscreener_data snapshots for trend analysis.
        """
        query = """
            SELECT
                price_change_m5,
                buys_m5,
                sells_m5,
                liquidity_usd,
                timestamp
            FROM dexscreener_data
            WHERE mint_address = $1
              AND timestamp >= NOW() - ($2::text || ' minutes')::interval
            ORDER BY timestamp DESC;
        """
        try:
            return await conn.fetch(query, mint, str(lookback_minutes))
        except Exception as e:
            logger.error(f":police_car_light: Error fetching DexScreener trend data for {mint}: {e}", exc_info=True)
            return []

    async def get_latest_dexscreener_response(self, mint: str, conn=None) -> str | None:
        """Fetches the 'full_response' JSON string of the most recent entry for a mint."""
        query = """
            SELECT full_response FROM dexscreener_data
            WHERE mint_address = $1 ORDER BY timestamp DESC LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            record = await connection.fetchval(query, mint)
            return record
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_total_tracked_tokens(self, backedup=False):
        """Fetches the total number of tracked tokens from the database."""
        query = "SELECT COUNT(*) FROM tokens"
        if backedup:
            query = "SELECT COUNT(*) FROM v_tokens"
        
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(query)
                return result if result is not None else 0
            except Exception as e:
                logger.error(f":police_car_light: Error fetching total tracked tokens: {e}", exc_info=True)
                return 0

    async def load_all_configurations(self) -> Dict[str, Any]:
        """Loads all configuration parameters from the database."""
        query = "SELECT key, value, type FROM configurations"
        config_data = {}
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                for row in rows:
                    key, str_value, value_type = row['key'], row['value'], row['type']
                    try:
                        if value_type == 'int':
                            config_data[key] = int(str_value)
                        elif value_type == 'float':
                            config_data[key] = float(str_value)
                        elif value_type == 'bool':
                            config_data[key] = str_value.lower() == 'true'
                        elif value_type == 'list':
                            config_data[key] = json.loads(str_value) # Assuming lists are stored as JSON strings
                        elif value_type == 'str':
                            config_data[key] = str_value
                        else:
                            logger.warning(f"Unknown configuration type '{value_type}' for key '{key}'. Storing as string.")
                            config_data[key] = str_value
                    except (ValueError, TypeError, json.JSONDecodeError) as e:
                        logger.error(f":police_car_light: Error converting configuration value for key '{key}' (type: {value_type}, value: '{str_value}'): {e}. Storing as raw string or None.")
                        config_data[key] = str_value # Fallback to string
                logger.info(f"Loaded {len(config_data)} configurations from database.")
                return config_data
        except Exception as e:
            logger.error(f":police_car_light: Error loading configurations from database: {e}", exc_info=True)
            return {} # Return empty dict on error

    async def save_configuration_parameter(self, key: str, value: Any, value_type: str, description: Optional[str] = None):
        """Saves or updates a single configuration parameter in the database."""
        query = """
            INSERT INTO configurations (key, value, type, description, last_updated)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                type = EXCLUDED.type,
                description = EXCLUDED.description,
                last_updated = NOW();
        """
        str_value = ""
        if value_type == 'bool':
            str_value = 'true' if value else 'false'
        elif value_type == 'list':
            str_value = json.dumps(value) # Store lists as JSON strings
        elif value is None: # Handle None explicitly for other types
            str_value = None # Store as NULL in DB if appropriate, or handle as empty string
        else:
            str_value = str(value)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, key, str_value, value_type, description)
            logger.debug(f"Saved configuration: {key} = {value} (Type: {value_type})")
        except Exception as e:
            logger.error(f":police_car_light: Error saving configuration parameter {key}: {e}", exc_info=True)

    async def get_python_type_string(self, value: Any) -> str:
        """Determines the storable type string for a Python value."""
        if isinstance(value, bool): return 'bool'
        if isinstance(value, int): return 'int'
        if isinstance(value, float): return 'float'
        if isinstance(value, list): return 'list'
        if isinstance(value, str): return 'str'
        # Fallback for other types, or raise error
        logger.warning(f"Unsupported type for config persistence: {type(value)} for value '{value}'. Defaulting to 'str'.")
        return 'str'

    async def get_configuration_parameter(self, key: str) -> Optional[Any]:
        """Fetches a single configuration parameter from the database."""
        # This method might not be strictly necessary if all configs are loaded at once,
        # but can be useful for specific lookups.
        all_configs = await self.load_all_configurations()
        return all_configs.get(key)

    async def insert_heartbeat(self, event_type: str = 'heartbeat', details: Optional[dict] = None):
        """Insert a new heartbeat or event into the bot_heartbeat table."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO bot_heartbeat (event_type, details) VALUES ($1, $2)",
                    event_type, json.dumps(details) if details else None
                )
            # logger.debug(f"Heartbeat event '{event_type}' inserted.") # Optional logging
        except Exception as e:
            logger.error(f":police_car_light: Error inserting heartbeat event: {e}", exc_info=True)
            # Decide if you want to raise, as heartbeat failure could be critical

    async def get_last_heartbeat_before(self, timestamp: datetime) -> Optional[datetime]:
        """Get the last heartbeat recorded before a given timestamp."""
        query = "SELECT timestamp FROM bot_heartbeat WHERE timestamp < $1 ORDER BY timestamp DESC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, timestamp)
            return row['timestamp'] if row else None

    async def get_first_heartbeat_after(self, timestamp: datetime) -> Optional[datetime]:
        """Get the first heartbeat recorded after a given timestamp."""
        query = "SELECT timestamp FROM bot_heartbeat WHERE timestamp > $1 ORDER BY timestamp ASC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, timestamp)
            return row['timestamp'] if row else None

    async def check_for_data_gap_on_restart(self,
                                            archived_at: datetime,
                                            gap_detection_threshold_seconds: int) -> bool:
        """
        Checks if there was a significant gap in bot operation (missing heartbeats)
        immediately before the 'archived_at' timestamp.
        """
        try:
            query = """
                SELECT timestamp FROM bot_heartbeat
                WHERE timestamp < $1
                ORDER BY timestamp DESC
                LIMIT 1;
            """
            # Ensure self.pool is the correct way to get a connection
            # This might be self.db_pool or similar depending on your class structure
            async with self.pool.acquire() as conn:
                last_heartbeat_record = await conn.fetchrow(query, archived_at)

            if not last_heartbeat_record:
                # No heartbeats recorded before this token's archival.
                # Check if any heartbeats exist at all to distinguish a new bot from a long-dead one.
                async with self.pool.acquire() as conn: # Re-acquire if needed, or use existing conn if scope allows
                    first_ever_heartbeat = await conn.fetchval("SELECT MIN(timestamp) FROM bot_heartbeat")
                
                if first_ever_heartbeat and first_ever_heartbeat < archived_at:
                    # Heartbeats exist in the table, but none before the current archival time.
                    # This implies the bot was down for the entire period leading up to 'archived_at'.
                    logger.warning(f"No heartbeats found before {archived_at}, but older heartbeats exist. Gap detected.")
                    return True
                elif not first_ever_heartbeat:
                    logger.info(f"No heartbeats found in bot_heartbeat table. Cannot determine gap for token archived at {archived_at}. Assuming no gap for safety.")
                    return False # Cannot determine, conservatively assume no gap.
                else: # Should not happen if archived_at is current time and heartbeats exist after.
                    logger.debug(f"First heartbeat {first_ever_heartbeat} is after {archived_at}. No gap determined.")
                    return False

            last_heartbeat_ts = last_heartbeat_record['timestamp']
            # Ensure archived_at is offset-aware if last_heartbeat_ts is, or vice-versa.
            # If one is naive and the other is aware, comparison will raise an error.
            # Assuming both are consistently offset-aware (e.g., UTC from TIMESTAMPTZ).
            time_since_last_heartbeat_seconds = (archived_at - last_heartbeat_ts).total_seconds()

            logger.debug(f"Token archived_at: {archived_at}, Last heartbeat: {last_heartbeat_ts}, "
                        f"Duration since last heartbeat: {time_since_last_heartbeat_seconds:.2f}s, "
                        f"Gap threshold: {gap_detection_threshold_seconds}s")

            if time_since_last_heartbeat_seconds > gap_detection_threshold_seconds:
                logger.info(f"Data gap detected: Last heartbeat was {time_since_last_heartbeat_seconds:.2f}s ago "
                            f"(threshold: {gap_detection_threshold_seconds}s). Token lifecycle likely interrupted.")
                return True
            
            logger.debug("No significant pre-archival data gap detected based on heartbeats.")
            return False

        except Exception as e:
            logger.error(f":police_car_light: Error in check_for_data_gap_on_restart: {e}", exc_info=True)
            return False # Fail safe

    async def check_for_data_gap(self, token_start_time: datetime, token_end_time: datetime, gap_threshold_seconds: int = 300) -> bool:
        """
        Checks for significant data gaps in bot_heartbeat table during the token's active period.
        A gap is significant if the time between two consecutive heartbeats exceeds gap_threshold_seconds.
        """
        last_hb_before_token_end = await self.get_last_heartbeat_before(token_end_time)
        first_hb_after_token_start = await self.get_first_heartbeat_after(token_start_time)

        if not last_hb_before_token_end or not first_hb_after_token_start:
            # If no heartbeats surround the token's activity, assume a potential gap (conservative approach)
            # This might happen if the token's entire lifecycle was during a bot downtime.
            logger.warning(f"Heartbeat data missing around token activity ({token_start_time} - {token_end_time}). Assuming potential data gap.")
            return True

        # Check gap between the heartbeat just before the token died (or script stopped)
        # and the heartbeat just after the script restarted (which would be after the token_start_time if it was an existing token)

        # Scenario 1: Gap *during* the token's recorded lifecycle
        # This requires iterating heartbeats within the token_start_time and token_end_time,
        # but a simpler proxy is to check the continuity around the point of potential script failure.

        # Let's refine: We are interested if the bot was down for a period that *ended*
        # shortly before token_end_time (when it was marked dead).
        # And this downtime started *after* token_start_time.

        query_heartbeats_in_range = """
            SELECT timestamp FROM bot_heartbeat
            WHERE timestamp >= $1 AND timestamp <= $2
            ORDER BY timestamp ASC;
        """
        async with self.pool.acquire() as conn:
            heartbeats = await conn.fetch(query_heartbeats_in_range, token_start_time, token_end_time)

        if not heartbeats: # No heartbeats during the token's entire active period
            logger.debug(f"No bot heartbeats found during token {token_start_time} - {token_end_time} lifecycle. Likely a gap.")
            return True

        previous_hb_ts = None
        for record in heartbeats:
            current_hb_ts = record['timestamp']
            if previous_hb_ts:
                if (current_hb_ts - previous_hb_ts).total_seconds() > gap_threshold_seconds:
                    logger.info(f"Data gap detected for token: {previous_hb_ts} to {current_hb_ts} ({(current_hb_ts - previous_hb_ts).total_seconds()}s)")
                    return True
            previous_hb_ts = current_hb_ts

        # Also check the gap between the last known heartbeat *before* the token ended its lifecycle
        # and the token's end time. This covers the case where the bot stopped *while* this token was live.
        if previous_hb_ts and (token_end_time - previous_hb_ts).total_seconds() > gap_threshold_seconds:
            logger.info(f"Data gap detected leading up to token end: last heartbeat at {previous_hb_ts}, token ended at {token_end_time}")
            return True

        return False
    
    async def set_token_cooldown(self, mint: str, cooldown_minutes: int):
        """Sets a cooldown period on a token to prevent immediate re-buys."""
        if cooldown_minutes <= 0:
            return # No cooldown to set

        cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes)
        query = "UPDATE tokens SET cooldown_until = $1 WHERE mint = $2"
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, cooldown_until, mint)
            logger.info(f"Token {mint} is on a re-buy cooldown until {cooldown_until.strftime('%Y-%m-%d %H:%M:%S')} UTC.")
        except Exception as e:
            logger.error(f"Failed to set cooldown for token {mint}: {e}", exc_info=True)

    async def is_token_active_in_db(self, mint: str, conn=None) -> bool:
        """
        Checks if a token exists in the primary 'tokens' table (i.e., it has not been backed up).
        Returns True if the token exists, False otherwise.
        """
        query = "SELECT 1 FROM tokens WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            result = await connection.fetchval(query, mint)
            return result is not None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def mark_token_as_migrated(self, mint: str, conn=None):
        """Updates the data_source for a token to 'DEXSCREENER'."""
        logger.info(f":twisted_rightwards_arrows: Flagging token {mint} as migrated. Switching data source to DEXScreener.")
        query = "UPDATE tokens SET data_source = 'DEXSCREENER' WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, mint)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def cleanup_db(self, cleanup_flag: bool):
        """Drop all application tables if cleanup_flag is True."""
        if cleanup_flag:
            logger.warning(":police_car_light: Starting full database cleanup - Dropping all application tables...")
            async with self.pool.acquire() as conn:
                # List all known application tables (main and backup)
                # Add any other tables managed by the application if necessary (e.g., creator_wallets)
                tables_to_drop = [
                    'configurations',     # Add the new table
                    'portfolio',
                    'rugcheck',           # Depends on tokens
                    'trades',             # No explicit FK, but related to tokens
                    'migrations',         # Standalone or related? Assuming standalone for drop order
                    'tokens',             # Drop after dependents
                    'social_scores_backup',
                    'portfolio_backup',          
                    'rugcheck_backup',
                    'trades_backup',
                    'migrations_backup',
                    'tokens_backup'
                ]
                # Drop tables in an order that respects potential dependencies, or use CASCADE
                # Using DROP TABLE IF EXISTS ... CASCADE is generally safer
                for table in tables_to_drop:
                    try:
                        # Use CASCADE to handle potential foreign key dependencies automatically
                        await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                        logger.info(f"🗑️ Dropped table {table}")
                    except Exception as e:
                        # Log error but continue trying to drop other tables
                        logger.error(f":police_car_light: Error dropping table {table}: {e}", exc_info=False) # Keep log concise

            logger.warning("✅ Full database cleanup finished.")

    async def backup_db(self, backup_flag: bool):
        """Backup tables based on backup_flag."""
        if backup_flag:
            async with self.pool.acquire() as conn:
                try:
                    tables_to_backup = [
                        'tokens', 'trades', 'rugcheck', 'migrations', 'portfolio', 'social_scores'
                    ]
                    for table in tables_to_backup:
                        logger.info("🗄️ Backing up table %s", table)

                        if table == 'tokens':
                            # Handle the 'tokens' table as a special case with explicit columns
                            await conn.execute("""
                                INSERT INTO tokens_backup (
                                    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey,
                                    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri,
                                    website, telegram, twitter, socials_score, socials_last_checked,
                                    sol_price_usd, is_active, last_trade, timestamp,
                                    cooldown_until,
                                    backup_reason, backup_timestamp
                                )
                                SELECT
                                    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey,
                                    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri,
                                    website, telegram, twitter, socials_score, socials_last_checked,
                                    sol_price_usd, is_active, last_trade, timestamp,
                                    cooldown_until,
                                    'manual_backup', NOW()
                                FROM tokens
                                ON CONFLICT (mint) DO NOTHING;
                            """)
                        elif table == 'social_scores':
                            await conn.execute("""
                                INSERT INTO social_scores_backup (id, mint, timestamp, score_type, score_value, details, backup_timestamp)
                                SELECT id, mint, timestamp, score_type, score_value, details, NOW()
                                FROM social_scores
                                ON CONFLICT (id) DO NOTHING;
                            """)
                        else:
                            # Original logic for other tables (assuming their backup tables have identical columns)
                            # NOTE: This generic logic is still fragile. Explicit columns are always better.
                            conflict_key_map = {
                                'trades': 'signature',
                                'rugcheck': 'mint',
                                'migrations': 'signature',
                                'portfolio': 'id'
                            }
                            conflict_key = conflict_key_map.get(table)
                            if conflict_key:
                                await conn.execute(f"INSERT INTO {table}_backup SELECT * FROM {table} ON CONFLICT ({conflict_key}) DO NOTHING;")
                            else:
                                logger.warning(f"No conflict key defined for table '{table}' in backup_db. Skipping backup.")
                                continue

                        logger.info("🧹 Truncating table %s", table)
                        await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")

                except Exception as e:
                    logger.exception(":police_car_light: Error during database backup: %s", e)
                    raise

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            logger.info("Closing database connection pool...")
            await self.pool.close()
            logger.info("Database connection pool closed.")

    async def get_token_lifespan(self, mint: str) -> Optional[Dict[str, datetime]]:
        """
        Fetches the approximate start and end timestamp of a token's activity
        based on its first and last trade records in the v_trades view.

        Args:
            mint: The mint address of the token.

        Returns:
            A dictionary {'start_ts': datetime, 'end_ts': datetime} if trades exist,
            otherwise None. Timestamps are timezone-aware (UTC).
        """
        if not self.pool:
            logger.error("Database pool not initialized.")
            return None

        query = """
            SELECT
                MIN(timestamp) as first_trade_ts,
                MAX(timestamp) as last_trade_ts
            FROM v_unified_market_ticks_historical
            WHERE mint = $1;
        """
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(query, mint)
                if row and row['first_trade_ts'] and row['last_trade_ts']:
                    # Ensure timestamps are timezone-aware UTC
                    start_ts = row['first_trade_ts'].replace(tzinfo=timezone.utc) if row['first_trade_ts'].tzinfo is None else row['first_trade_ts'].astimezone(timezone.utc)
                    end_ts = row['last_trade_ts'].replace(tzinfo=timezone.utc) if row['last_trade_ts'].tzinfo is None else row['last_trade_ts'].astimezone(timezone.utc)
                    return {'start_ts': start_ts, 'end_ts': end_ts}
                else:
                    logger.warning(f"No trade timestamps found for mint {mint} to determine lifespan.")
                    return None
            except Exception as e:
                logger.error(f":police_car_light: Error fetching token lifespan for {mint}: {e}", exc_info=True)
                return None

    def ohlcv_sql_like(self, df_group: pd.DataFrame) -> pd.Series:
        df = df_group 
        if df.empty:
            return pd.Series({
                'Open': np.nan, 'High': np.nan, 'Low': np.nan, 'Close': np.nan,
                'Volume': 0.0,
                'market_cap_calculated': np.nan, 
                'marketCapSol': np.nan,          
                'volatility': 0.0
            })

        last_rolling_volume = df['rolling_volume_sql'].iloc[-1] if 'rolling_volume_sql' in df.columns and not df['rolling_volume_sql'].empty else 0.0
        last_rolling_volatility = df['rolling_volatility_sql'].iloc[-1] if 'rolling_volatility_sql' in df.columns and not df['rolling_volatility_sql'].empty else 0.0
        
        last_market_cap_usd = df['market_cap_calculated'].iloc[-1] if 'market_cap_calculated' in df.columns and not df['market_cap_calculated'].isnull().all() else np.nan
        last_market_cap_sol_live = df['marketcapsol'].iloc[-1] if 'marketcapsol' in df.columns and not df['marketcapsol'].empty and pd.notna(df['marketcapsol'].iloc[-1]) else np.nan

        return pd.Series({
            'Open': df['price'].iloc[0] if 'price' in df.columns and not df['price'].empty else np.nan,
            'High': df['price'].max() if 'price' in df.columns and not df['price'].empty else np.nan,
            'Low': df['price'].min() if 'price' in df.columns and not df['price'].empty else np.nan,
            'Close': df['price'].iloc[-1] if 'price' in df.columns and not df['price'].empty else np.nan,
            'Volume': last_rolling_volume,
            'market_cap_calculated': last_market_cap_usd,
            'marketCapSol': last_market_cap_sol_live, 
            'volatility': last_rolling_volatility
        })

    async def get_historical_data_for_backtesting(
        self,
        mints: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> Dict[str, pd.DataFrame]:
        """
        [MODIFIED] Fetches historical OHLCV data for a list of mints.
        The date range is now optional. If start_date and end_date are None,
        it fetches the complete history for the given mints.
        """
        if not mints:
            logger.warning("get_historical_data_for_backtesting called with empty mints list.")
            return {}
        if not self.pool:
            logger.error("Database pool not initialized.")
            return {}

        # Ensure dates are UTC if provided
        start_date_utc = start_date.astimezone(timezone.utc) if start_date and start_date.tzinfo else start_date
        end_date_utc = end_date.astimezone(timezone.utc) if end_date and end_date.tzinfo else end_date

        # --- Build Trade Query with Optional Date Filters ---
        trade_query_parts = [
            "SELECT mint, timestamp, price_sol AS price, volume_usd AS volume,",
            "market_cap_usd AS market_cap_calculated, market_cap_sol AS live_market_cap_sol",
            "FROM v_unified_market_ticks_historical",
            "WHERE mint = ANY($1::text[]) AND price_sol > 0"
        ]
        trade_params = [mints]
        if start_date_utc:
            trade_params.append(start_date_utc)
            trade_query_parts.append(f"AND timestamp >= ${len(trade_params)}")
        if end_date_utc:
            trade_params.append(end_date_utc)
            trade_query_parts.append(f"AND timestamp < ${len(trade_params)}")
        trade_query_parts.append("ORDER BY mint, timestamp;")
        trade_query = " ".join(trade_query_parts)

        # --- Build Rugcheck Query with Optional Date Filters ---
        rugcheck_query_parts = [
            "WITH RankedRugcheck AS (",
            "SELECT mint, last_checked AS timestamp, score AS rugcheck_score, ROW_NUMBER() OVER (PARTITION BY mint ORDER BY last_checked DESC) as rn",
            "FROM v_rugcheck WHERE mint = ANY($1::text[])"
        ]
        rugcheck_params = [mints]
        if end_date_utc:
            rugcheck_params.append(end_date_utc)
            rugcheck_query_parts.append(f"AND last_checked < ${len(rugcheck_params)}")
        rugcheck_query_parts.append(")")
        rugcheck_query_parts.append("SELECT mint, timestamp, rugcheck_score FROM RankedRugcheck WHERE rn = 1")
        if start_date_utc:
            rugcheck_params.append(start_date_utc)
            rugcheck_query_parts.append(f"OR timestamp >= ${len(rugcheck_params)}")
        rugcheck_query = " ".join(rugcheck_query_parts) + ";"

        # --- Token Info Query (no date filter needed) ---
        token_info_query = """
            WITH TokenCreationData AS (
                SELECT
                    mint, socials_score, timestamp AS token_creation_time,
                    marketCapSol AS creation_init_market_cap_sol,
                    cooldown_until,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp ASC) as rn
                FROM v_tokens vt WHERE mint = ANY($1::text[])
            )
            SELECT mint, token_creation_time, socials_score, creation_init_market_cap_sol, cooldown_until
            FROM TokenCreationData WHERE rn = 1;
        """

        results_dict = {}
        async with self.pool.acquire() as conn:
            try:
                # --- Execute Queries ---
                trade_records_raw = await conn.fetch(trade_query, *trade_params)
                rugcheck_records_raw = await conn.fetch(rugcheck_query, *rugcheck_params)
                token_info_records_raw = await conn.fetch(token_info_query, mints)

                if not trade_records_raw:
                    logger.warning("No trade records found for the specified mints and period.")
                    return {}

                # --- Process Data (same logic as before) ---
                trade_records_list_of_dicts = [dict(rec) for rec in trade_records_raw]
                trades_df = pd.DataFrame(trade_records_list_of_dicts)
                
                trades_df.columns = [str(col).lower() for col in trades_df.columns]
                
                trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], errors='coerce', utc=True)
                trades_df.dropna(subset=['timestamp'], inplace=True)
                
                numeric_cols_from_trades = ['price', 'volume', 'market_cap_calculated', 'live_market_cap_sol']
                for col in numeric_cols_from_trades:
                    if col in trades_df.columns:
                        trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
                    else:
                        logger.error(f"Critical: Column '{col}' expected from trades query but missing. DataFrame columns: {list(trades_df.columns)}")
                        trades_df[col] = 0.0
                trades_df.dropna(subset=['price', 'volume'], inplace=True)

                all_processed_trades = []
                time_interval_minutes = self.config.get('DEFAULT_TIME_INTERVAL', 10)
                window_duration = f"{time_interval_minutes}min"

                for mint_name, mint_df_group in trades_df.groupby('mint'):
                    mint_df = mint_df_group.sort_values('timestamp').copy()
                    mint_df_indexed = mint_df.set_index('timestamp')
                    mint_df['rolling_volume_sql'] = mint_df_indexed['volume'].rolling(window_duration, closed='left').sum().fillna(0.0).values
                    
                    if 'live_market_cap_sol' in mint_df.columns:
                        mint_df.rename(columns={'live_market_cap_sol': 'marketcapsol'}, inplace=True)

                    prices_series = mint_df['price']
                    if len(prices_series) > 1:
                        log_returns = np.log(prices_series / prices_series.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
                        rolling_obj = log_returns.set_axis(mint_df['timestamp']).rolling(window_duration, closed='left')
                        rolling_std = rolling_obj.std().fillna(0.0)
                        rolling_count = rolling_obj.count().fillna(0.0)
                        volatility_sql = rolling_std.astype(float) * np.sqrt(np.maximum(rolling_count.astype(float), 1.0))
                        mint_df['rolling_volatility_sql'] = volatility_sql.where(rolling_count > 5, 0.0).values
                    else:
                        mint_df['rolling_volatility_sql'] = 0.0
                    mint_df['rolling_volatility_sql'] = mint_df['rolling_volatility_sql'].fillna(0.0)
                    all_processed_trades.append(mint_df)

                if not all_processed_trades: return {}
                processed_trades_df = pd.concat(all_processed_trades)

                ohlcv_df = processed_trades_df.groupby(['mint', pd.Grouper(key='timestamp', freq='5s')])\
                                            .apply(self.ohlcv_sql_like).reset_index()
                
                ohlcv_df.dropna(subset=['mint', 'timestamp'], inplace=True)
                ohlc_cols = ['Open', 'High', 'Low', 'Close']
                ohlcv_df[ohlc_cols] = ohlcv_df.groupby('mint')[ohlc_cols].ffill().bfill().fillna(0.0)
                
                cols_to_fill_ohlcv = ['Volume', 'volatility', 'market_cap_calculated', 'marketCapSol']
                for col in cols_to_fill_ohlcv:
                    if col in ohlcv_df.columns: ohlcv_df[col] = ohlcv_df[col].fillna(0.0)
                    else: ohlcv_df[col] = 0.0
                
                ohlcv_df = ohlcv_df.set_index('timestamp')
                if ohlcv_df.index.has_duplicates: ohlcv_df = ohlcv_df.loc[~ohlcv_df.index.duplicated(keep='last')]
                
                resampled_ohlcv_list = []
                for mint_name, group_df in ohlcv_df.groupby('mint'):
                    if group_df.index.has_duplicates: 
                        group_df = group_df.loc[~group_df.index.duplicated(keep='last')]
                    
                    min_ts, max_ts = group_df.index.min(), group_df.index.max()
                    if pd.isna(min_ts) or pd.isna(max_ts): 
                        logger.warning(f"Skipping mint {mint_name} due to NaT in min/max timestamp for reindexing.")
                        continue
                        
                    full_range = pd.date_range(start=min_ts, end=max_ts, freq='5s', tz='UTC')
                    group_reindexed = group_df.reindex(full_range)

                    cols_to_interpolate = [
                        'Open', 'High', 'Low', 'Close', 'Volume',
                        'market_cap_calculated', 'marketCapSol', 'volatility'
                    ]
                    
                    for col in cols_to_interpolate:
                        if col in group_reindexed.columns:
                            group_reindexed[col] = pd.to_numeric(group_reindexed[col], errors='coerce').interpolate(method='time')

                    group_resampled = group_reindexed
                    group_resampled['mint'] = mint_name
                    resampled_ohlcv_list.append(group_resampled)

                if not resampled_ohlcv_list: 
                    logger.warning("No data after resampling for any mints.")
                    return {}
                
                resampled_ohlcv_df = pd.concat(resampled_ohlcv_list)
                if resampled_ohlcv_df.index.name != 'timestamp': resampled_ohlcv_df.index.name = 'timestamp'

                if rugcheck_records_raw:
                    rugcheck_list_of_dicts = [dict(rec) for rec in rugcheck_records_raw]
                    rugcheck_df = pd.DataFrame(rugcheck_list_of_dicts)
                    rugcheck_df.columns = [str(col).lower() for col in rugcheck_df.columns]
                    if 'timestamp' in rugcheck_df.columns:
                        rugcheck_df['timestamp'] = pd.to_datetime(rugcheck_df['timestamp'], errors='coerce', utc=True)
                        rugcheck_df.dropna(subset=['timestamp'], inplace=True)
                        rugcheck_df = rugcheck_df.sort_values(['mint', 'timestamp']).drop_duplicates(subset=['mint', 'timestamp'], keep='last')
                        rugcheck_df.set_index('timestamp', inplace=True)
                        rugcheck_df['rugcheck_score'] = pd.to_numeric(rugcheck_df.get('rugcheck_score'), errors='coerce')
                        rugcheck_df = rugcheck_df[['mint', 'rugcheck_score']]
                    else:
                        logger.warning("Rugcheck data missing 'timestamp' column.")
                        rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))
                else:
                    rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))

                token_info_map = {}
                if token_info_records_raw:
                    for r_rec in token_info_records_raw:
                        r_dict = dict(r_rec)
                        mint_val = r_dict.get('mint')
                        creation_time_val = r_dict.get('token_creation_time')
                        socials_val = r_dict.get('socials_score')
                        creation_mc_sol_val = r_dict.get('creation_init_market_cap_sol')
                        cooldown_until_val = r_dict.get('cooldown_until')

                        creation_time = pd.to_datetime(creation_time_val, errors='coerce', utc=True)
                        socials = pd.to_numeric(socials_val, errors='coerce')
                        creation_mc_sol = pd.to_numeric(creation_mc_sol_val, errors='coerce')
                        cooldown_until_ts = pd.to_datetime(cooldown_until_val, errors='coerce', utc=True)

                        if mint_val and pd.notna(creation_time):
                            token_info_map[mint_val] = {'creation_time': creation_time, 
                                                        'socials_score': socials, 
                                                        'creation_init_market_cap_sol': creation_mc_sol,
                                                        'cooldown_until': cooldown_until_ts
                                                        }
                
                required_final_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'creation_init_market_cap_sol', 'volatility', 'rugcheck_score', 'socials_score', 'token_creation_time', 'cooldown_until']
                
                grouped_ohlcv = resampled_ohlcv_df.groupby('mint')
                for mint_name in grouped_ohlcv.groups:
                    mint_ohlcv_group = grouped_ohlcv.get_group(mint_name)
                    cols_to_select_from_ohlcv = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'volatility']
                    existing_cols_in_group = [col for col in cols_to_select_from_ohlcv if col in mint_ohlcv_group.columns]
                    if not all(c in existing_cols_in_group for c in ['market_cap_calculated', 'marketCapSol']):
                        logger.warning(f"Mint {mint_name} group missing essential live market cap columns. Columns present: {list(mint_ohlcv_group.columns)}. Skipping.")
                        continue
                    combined_df = mint_ohlcv_group[existing_cols_in_group].copy()

                    mint_rugcheck_data = rugcheck_df[rugcheck_df['mint'] == mint_name][['rugcheck_score']] if not rugcheck_df.empty else None
                    if mint_rugcheck_data is not None and not mint_rugcheck_data.empty:
                        combined_df = combined_df.sort_index()
                        mint_rugcheck_data = mint_rugcheck_data.sort_index()
                        if mint_rugcheck_data.index.has_duplicates: mint_rugcheck_data = mint_rugcheck_data.loc[~mint_rugcheck_data.index.duplicated(keep='last')]
                        combined_df = pd.merge_asof(combined_df, mint_rugcheck_data, left_index=True, right_index=True, direction='backward', tolerance=pd.Timedelta('1d'))
                    else: combined_df['rugcheck_score'] = np.nan

                    mint_specific_info = token_info_map.get(mint_name)
                    if mint_specific_info:
                        combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'], combined_df['cooldown_until'] = mint_specific_info['creation_time'], mint_specific_info['socials_score'], mint_specific_info.get('creation_init_market_cap_sol', np.nan), mint_specific_info.get('cooldown_until', pd.NaT)
                    else:
                        combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'], combined_df['cooldown_until'] = pd.NaT, 100, np.nan, pd.NaT
                    
                    for r_col in required_final_cols:
                        if r_col not in combined_df.columns: combined_df[r_col] = np.nan 

                    for col in ['rugcheck_score', 'socials_score', 'token_creation_time', 'creation_init_market_cap_sol', 'cooldown_until']: combined_df[col] = combined_df[col].ffill().bfill()
                    
                    combined_df['rugcheck_score'] = combined_df['rugcheck_score'].fillna(10000).astype(int)
                    combined_df['socials_score'] = combined_df['socials_score'].fillna(100).astype(int)
                    combined_df['creation_init_market_cap_sol'] = pd.to_numeric(combined_df['creation_init_market_cap_sol'], errors='coerce').fillna(0.0)
                    combined_df['cooldown_until'] = pd.to_datetime(combined_df['cooldown_until'], errors='coerce', utc=True) 

                    for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'volatility']:
                        combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0.0)
                    
                    final_df = combined_df.copy()
                    # If dates were provided, filter the final combined data at the end
                    if start_date_utc:
                        final_df = final_df[final_df.index >= start_date_utc]
                    if end_date_utc:
                        final_df = final_df[final_df.index < end_date_utc]

                    if not final_df.empty and all(col in final_df.columns for col in required_final_cols):
                        astype_dict = {
                            'Open': float, 'High': float, 'Low': float, 'Close': float, 
                            'Volume': float, 'market_cap_calculated': float, 
                            'marketCapSol': float, 'creation_init_market_cap_sol': float, 
                            'volatility': float, 'rugcheck_score': int, 'socials_score': int
                        }
                        cols_for_astype = [col for col in required_final_cols if col in astype_dict]
                        final_df[cols_for_astype] = final_df[cols_for_astype].astype(astype_dict)
                        
                        final_df.index = pd.to_datetime(final_df.index, utc=True)
                        results_dict[mint_name] = final_df[required_final_cols]
                    else:
                        logger.warning(f"No valid data or missing columns for {mint_name} after final processing. Skipping.")
            
            except Exception as e:
                logger.error(f":police_car_light: Error processing historical data ({type(e).__name__}): {e}", exc_info=True)
                return {}

        return results_dict
    
    async def get_raw_data_for_rl(
        self,
        start_date: datetime,
        end_date: datetime,
        min_trade_count: int
    ) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
        """
        [NEW & OPTIMIZED] Fetches all the necessary raw, time-series data for the RL
        feature engineering script. It does not perform any calculations and cleanly
        separates Pump.fun trades from DexScreener data.
        """
        if not self.pool:
            logger.error("Database pool not initialized.")
            return None

        mints_query = """
            SELECT mint FROM (
                SELECT mint, COUNT(signature) as trade_count
                FROM v_trades
                WHERE timestamp >= $1 AND timestamp < $2
                GROUP BY mint
            ) AS trade_counts
            WHERE trade_count >= $3;
        """
        
        try:
            eligible_mint_records = await self.pool.fetch(mints_query, start_date, end_date, min_trade_count)
            if not eligible_mint_records:
                logger.warning(f"No tokens found in the date range with at least {min_trade_count} trades.")
                return None
            
            mints = [r['mint'] for r in eligible_mint_records]
            logger.info(f"Found {len(mints)} eligible tokens. Fetching their full raw data...")

            # --- THIS IS THE FIX ---
            # Query v_trades for Pump.fun data, not the unified view.
            # We also calculate volume_usd directly here AND FETCH TX_TYPE.
            trade_query = """
                SELECT 
                    t.mint, t.timestamp, t.price AS price_sol, t.marketCapSol AS market_cap_sol,
                    (t.sol_amount * t.sol_price_usd) AS volume_usd, t.tx_type, sol_price_usd AS sol_price_usd
                FROM v_trades t
                WHERE t.mint = ANY($1::text[]);
            """
            # --- END OF FIX ---
            
            rugcheck_query = "SELECT mint, last_checked AS timestamp, score AS rugcheck_score FROM v_rugcheck WHERE mint = ANY($1::text[]) ORDER BY timestamp;"
            token_info_query = "SELECT mint, socials_score, socials_last_checked, timestamp AS token_creation_time FROM v_tokens WHERE mint = ANY($1::text[]);"
            dexscreener_query = "SELECT mint_address as mint, timestamp, liquidity_usd, buys_m5, sells_m5, volume_m5, price_change_m5 FROM v_dexscreener_data WHERE mint_address = ANY($1::text[]) ORDER BY timestamp;"

            results = await asyncio.gather(
                self.pool.fetch(trade_query, mints),
                self.pool.fetch(rugcheck_query, mints),
                self.pool.fetch(token_info_query, mints),
                self.pool.fetch(dexscreener_query, mints)
            )

            trades_df = pd.DataFrame([dict(r) for r in results[0]])
            rugcheck_df = pd.DataFrame([dict(r) for r in results[1]])
            token_info_df = pd.DataFrame([dict(r) for r in results[2]])
            dexscreener_df = pd.DataFrame([dict(r) for r in results[3]])

            return trades_df, rugcheck_df, token_info_df, dexscreener_df

        except Exception as e:
            logger.error(f":police_car_light: Error fetching raw data for RL: {e}", exc_info=True)
            return None

    # --- NEW METHOD FOR RL FEEDBACK LOOP ---
    async def log_completed_trade(
        self,
        token_address: str,
        side: str,
        amount_in_sol: float,
        amount_out_tokens: float,
        fill_price: float,
        market_cap_at_trade: Optional[float],
        tx_fee_sol: Optional[float],
        tip_sol: Optional[float],
        slippage_percent: Optional[float],
        trade_context: Optional[Dict[str, Any]],
        conn=None
    ):
        """
        Logs a detailed record of a completed trade to the `completed_trades` table.
        This serves as the foundational feedback loop for the RL agent's learning process.

        Args:
            token_address (str): The mint address of the token traded.
            side (str): The side of the trade, must be 'buy' or 'sell'.
            amount_in_sol (float): The amount of SOL involved in the trade.
            amount_out_tokens (float): The amount of tokens involved in the trade.
            fill_price (float): The actual executed price of the trade in SOL per token.
            market_cap_at_trade (Optional[float]): The market cap in SOL at the time of the trade.
            tx_fee_sol (Optional[float]): The base network fee for the transaction in SOL.
            tip_sol (Optional[float]): The priority fee (Jito tip) for the transaction in SOL.
            slippage_percent (Optional[float]): The slippage percentage experienced.
            trade_context (Optional[Dict[str, Any]]): A JSONB field for storing other metadata.
            conn: An optional existing database connection or transaction.
        """
        if side not in ('buy', 'sell'):
            raise ValueError("The 'side' parameter must be either 'buy' or 'sell'.")

        query = """
            INSERT INTO completed_trades (
                token_address, side, amount_in_sol, amount_out_tokens, fill_price,
                market_cap_at_trade, tx_fee_sol, tip_sol, slippage_percent, trade_context
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);
        """
        
        # Convert trade_context dict to a JSON string if it exists
        trade_context_json = json.dumps(trade_context) if trade_context else None
        
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(
                query, token_address, side, amount_in_sol, amount_out_tokens, fill_price,
                market_cap_at_trade, tx_fee_sol, tip_sol, slippage_percent, trade_context_json
            )
            logger.debug(f"Logged completed '{side}' trade for {token_address} to feedback table.")
        except Exception as e:
            logger.error(f"Failed to log completed trade for {token_address}: {e}", exc_info=True)
            # Re-raise if not using an external transaction, so the caller can handle it.
            if not conn:
                raise
        finally:
            # Release connection only if it was acquired here
            if not conn and connection:
                await self.pool.release(connection)

# Helper function moved outside class for potential reuse (optional)
async def get_token_lifespan(db_client: DatabaseClient, mint: str) -> Optional[Dict[str, datetime]]:
    """
    Fetches the approximate start and end timestamp of a token's activity
    based on its first and last trade records in the v_trades view.
    """
    if not db_client or not db_client.pool:
        logger.error("Database client not initialized or connected for get_token_lifespan.")
        return None

    query = """
        SELECT
            MIN(timestamp) as first_trade_ts,
            MAX(timestamp) as last_trade_ts
        FROM v_trades
        WHERE mint = $1;
    """
    async with db_client.pool.acquire() as conn:
        try:
            row = await conn.fetchrow(query, mint)
            if row and row['first_trade_ts'] and row['last_trade_ts']:
                start_ts = row['first_trade_ts'].replace(tzinfo=timezone.utc) if row['first_trade_ts'].tzinfo is None else row['first_trade_ts'].astimezone(timezone.utc)
                end_ts = row['last_trade_ts'].replace(tzinfo=timezone.utc) if row['last_trade_ts'].tzinfo is None else row['last_trade_ts'].astimezone(timezone.utc)
                end_ts += timedelta(seconds=1) # Add buffer
                return {'start_ts': start_ts, 'end_ts': end_ts}
            else:
                logger.warning(f"No trade timestamps found for mint {mint} to determine lifespan.")
                return None
        except Exception as e:
            logger.error(f":police_car_light: Error fetching token lifespan for {mint}: {e}", exc_info=True)
            return None
```

#### 📄 `__GA-result-files__`
*path: `ga_optimization_results/__GA-result-files__`*

_This file is empty._

#### 📄 `ga_backtester.py`
*path: `ga_optimizer_module/ga_backtester.py`*

```python
# FILE: ga_backtester.py

"""
Backtesting Engine Module (Refactored for DexScreener & Advanced Logic)

Simulates trading strategies on historical data, respecting token lifespans,
cooldown periods, and implementing source-aware (Pump.fun vs. DexScreener)
trend-reversal re-buy logic to evaluate performance.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from bot_logger import logger
import utils # For calculate_trend_indicators
import config.config as config_module # To access fixed configurations

# --- Performance Metrics Calculation (Unchanged) ---
def calculate_performance_metrics(
    trade_history: list,
    initial_capital: float,
    final_capital: float,
    start_ts: Optional[datetime] = None,
    end_ts: Optional[datetime] = None,
    simulation_end_reason: str = "Completed"
) -> dict:
    """
    Calculates various performance metrics based on simulated trades.
    This function's logic is self-contained and requires no changes.
    """
    # Initialize the dictionary to hold all performance metrics.
    metrics = {
        "total_pnl": 0.0, "total_return_pct": 0.0, "total_trades": 0,
        "winning_trades": 0, "losing_trades": 0, "total_profit_sells": 0.0,
        "total_loss_sells": 0.0, "win_rate": 0.0, "avg_profit_per_win_trade": 0.0,
        "avg_loss_per_loss_trade": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0,
        "simulation_start_ts": start_ts.isoformat() if start_ts else None,
        "simulation_end_ts": end_ts.isoformat() if end_ts else None,
        "simulation_duration_minutes": (end_ts - start_ts).total_seconds() / 60.0 if start_ts and end_ts else None,
        "simulation_end_reason": simulation_end_reason,
    }

    metrics["total_pnl"] = final_capital - initial_capital
    if initial_capital > 0:
        metrics["total_return_pct"] = (metrics["total_pnl"] / initial_capital) * 100.0
    sell_trades = [t for t in trade_history if t['type'] == 'sell' and 'pnl' in t]
    metrics["total_trades"] = len(sell_trades)
    if metrics["total_trades"] > 0:
        for trade in sell_trades:
            pnl = trade.get('pnl', 0.0)
            if pnl > 0:
                metrics["winning_trades"] += 1
                metrics["total_profit_sells"] += pnl
            elif pnl < 0:
                metrics["losing_trades"] += 1
                metrics["total_loss_sells"] += abs(pnl)
        if metrics["total_trades"] > 0:
             metrics["win_rate"] = (metrics["winning_trades"] / metrics["total_trades"]) * 100.0
        if metrics["winning_trades"] > 0:
             metrics["avg_profit_per_win_trade"] = metrics["total_profit_sells"] / metrics["winning_trades"]
        if metrics["losing_trades"] > 0:
             metrics["avg_loss_per_loss_trade"] = metrics["total_loss_sells"] / metrics["losing_trades"]
        if metrics["total_loss_sells"] > 0:
             metrics["profit_factor"] = metrics["total_profit_sells"] / metrics["total_loss_sells"]
        elif metrics["total_profit_sells"] > 0:
             metrics["profit_factor"] = float('inf')
             
    equity_curve = pd.Series(index=[], dtype=float)
    if trade_history:
        first_ts = trade_history[0]['timestamp']
        equity_curve.loc[start_ts if start_ts and start_ts < first_ts else first_ts] = initial_capital
    current_portfolio_value = initial_capital
    for trade in trade_history:
        trade_ts = trade['timestamp']
        if trade['type'] == 'buy':
            equity_curve.loc[trade_ts - pd.Timedelta(nanoseconds=1)] = current_portfolio_value
            current_portfolio_value -= trade.get('amount_sol', 0)
            equity_curve.loc[trade_ts] = current_portfolio_value
        elif trade['type'] == 'sell':
            equity_curve.loc[trade_ts - pd.Timedelta(nanoseconds=1)] = current_portfolio_value
            current_portfolio_value += trade.get('amount_sol', 0)
            equity_curve.loc[trade_ts] = current_portfolio_value
    if end_ts:
        if not equity_curve.empty and equity_curve.index[-1] < end_ts:
             equity_curve.loc[end_ts] = final_capital
        elif equity_curve.empty:
             equity_curve.loc[start_ts if start_ts else datetime.now(timezone.utc)] = initial_capital
             equity_curve.loc[end_ts] = final_capital
    if not equity_curve.empty:
        equity_curve = equity_curve.sort_index()[~equity_curve.index.duplicated(keep='last')]
        roll_max = equity_curve.cummax()
        drawdown = (roll_max - equity_curve) / roll_max
        max_dd = drawdown.max() if not drawdown.empty else 0.0
    else:
        max_dd = 0.0
    metrics["max_drawdown"] = max_dd * 100.0

    return metrics

# --- Backtesting Core Function ---
def run_backtest_sync(
    parameters: dict,
    ohlcv_data: pd.DataFrame,
    initial_capital: float,
    max_timestamp: Optional[datetime] = None,
    dexscreener_snapshot_data: Optional[pd.DataFrame] = None,
    indicator_cache: Optional[Dict] = None
) -> dict:
    mint_addr = parameters.get("mint", "UNKNOWN_MINT")
    simulation_end_reason = "Completed"

    # --- Early exit conditions now create a complete metrics dictionary ---
    if ohlcv_data.empty:
        metrics = calculate_performance_metrics([], initial_capital, initial_capital, simulation_end_reason="No Data")
        metrics["final_portfolio_value"] = initial_capital
        return metrics

    # --- 1. Data Preparation & Validation ---
    if not isinstance(ohlcv_data.index, pd.DatetimeIndex) or ohlcv_data.index.tz is None:
        try:
             ohlcv_data.index = pd.to_datetime(ohlcv_data.index, utc=True)
        except Exception:
             metrics = calculate_performance_metrics([], initial_capital, initial_capital, simulation_end_reason="Invalid Index")
             metrics["final_portfolio_value"] = initial_capital
             return metrics

    df = ohlcv_data.copy().sort_index()
    start_ts_data = df.index.min()
    end_ts_data = df.index.max()

    # --- Pre-calculate indicators for the entire dataframe ---
    indicator_config = {
        'MIN_CANDLE_DATA_FOR_INDICATORS': parameters.get('MIN_CANDLE_DATA_FOR_INDICATORS', config_module.MIN_CANDLE_DATA_FOR_INDICATORS),
        'RSI_PERIOD': parameters.get('RSI_PERIOD', config_module.RSI_PERIOD),
        'BBANDS_PERIOD': parameters.get('BBANDS_PERIOD', config_module.BBANDS_PERIOD),
        'BBANDS_STD_DEV': parameters.get('BBANDS_STD_DEV', config_module.BBANDS_STD_DEV),
        'FAST_EMA_PERIOD': parameters.get('FAST_EMA_PERIOD', config_module.FAST_EMA_PERIOD),
        'SLOW_EMA_PERIOD': parameters.get('SLOW_EMA_PERIOD', config_module.SLOW_EMA_PERIOD),
        'ADAPTIVE_ATR_PERIOD': parameters.get('ADAPTIVE_ATR_PERIOD', config_module.ADAPTIVE_ATR_PERIOD)
    }
    df_with_indicators = utils.calculate_trend_indicators(df, indicator_config)
    
    if not df_with_indicators.empty:
        df = df_with_indicators

    if max_timestamp:
        if max_timestamp.tzinfo is None: max_timestamp = max_timestamp.replace(tzinfo=timezone.utc)
        df = df[df.index <= max_timestamp].copy()
        end_ts_data = max_timestamp
        simulation_end_reason = "Token Death"
        if df.empty:
            metrics = calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, simulation_end_reason)
            metrics["final_portfolio_value"] = initial_capital
            return metrics

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score', 'cooldown_until', 'token_creation_time']
    for col in required_cols:
        if col not in df.columns: df[col] = pd.NaT if 'time' in col or 'until' in col else np.nan
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score']
    for col in numeric_cols: df[col] = pd.to_numeric(df[col], errors='coerce')
    df['cooldown_until'] = pd.to_datetime(df['cooldown_until'], errors='coerce', utc=True)
    df['token_creation_time'] = pd.to_datetime(df['token_creation_time'], errors='coerce', utc=True)
    df[['Open', 'High', 'Low', 'Close', 'market_cap_calculated', 'volatility', 'token_creation_time']] = df[['Open', 'High', 'Low', 'Close', 'market_cap_calculated', 'volatility', 'token_creation_time']].ffill().bfill()
    df[['Volume']] = df[['Volume']].fillna(0.0)
    df[['rugcheck_score', 'socials_score']] = df[['rugcheck_score', 'socials_score']].fillna(1000.0)
    df['cooldown_until'] = df['cooldown_until'].fillna(pd.NaT)
    
    df = df[df["Close"] > 1e-12]

    if df.empty:
         metrics = calculate_performance_metrics([], initial_capital, initial_capital, start_ts_data, end_ts_data, "No Candle Data")
         metrics["final_portfolio_value"] = initial_capital
         return metrics

    # --- 2. Extract Parameters from GA Solution ---
    sol_to_buy = parameters.get('SOL_TO_BUY', config_module.SOL_TO_BUY)
    initial_stop_loss_percent = parameters.get('INITIAL_STOP_LOSS_PERCENT', config_module.INITIAL_STOP_LOSS_PERCENT)
    first_sell_percent = parameters.get('FIRST_SELL_PERCENT', config_module.FIRST_SELL_PERCENT)
    trailing_stop_loss_percent = parameters.get('TRAILING_STOP_LOSS_PERCENT', config_module.TRAILING_STOP_LOSS_PERCENT)
    second_take_profit_percent = parameters.get('SECOND_TAKE_PROFIT_PERCENT', config_module.SECOND_TAKE_PROFIT_PERCENT)
    first_sell_profit_margin = parameters.get('FIRST_SELL_PROFIT_MARGIN', config_module.FIRST_SELL_PROFIT_MARGIN)
    volume_threshold = parameters.get('DEFAULT_VOLUME_THRESHOLD', config_module.DEFAULT_VOLUME_THRESHOLD)
    marketcap_threshold = parameters.get('DEFAULT_MARKETCAP_THRESHOLD', config_module.DEFAULT_MARKETCAP_THRESHOLD)
    rugcheck_threshold = parameters.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', config_module.DEFAULT_RUGCHECK_SCORE_THRESHOLD)
    socials_threshold = parameters.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', config_module.DEFAULT_SOCIAL_SCORE_THRESHOLD)
    min_volatility = parameters.get('MIN_VOLATILITY', config_module.MIN_VOLATILITY)
    min_emergency_mcap_usd = parameters.get('MIN_MARKET_CAP', config_module.MIN_MARKETCAP_THRESHOLD)
    buy_fee, buy_tip = parameters.get('DEFAULT_BUY_FEE', config_module.DEFAULT_BUY_FEE), parameters.get('DEFAULT_BUY_TIP', config_module.DEFAULT_BUY_TIP)
    sell_fee, sell_tip = parameters.get('DEFAULT_SELL_FEE', config_module.DEFAULT_SELL_FEE), parameters.get('DEFAULT_SELL_TIP', config_module.DEFAULT_SELL_TIP)
    use_trend_reversal = bool(parameters.get('USE_TREND_REVERSAL_CONFIRMATION', config_module.USE_TREND_REVERSAL_CONFIRMATION))
    stop_loss_cooldown_minutes_ga = parameters.get('STOP_LOSS_COOLDOWN_MINUTES', config_module.STOP_LOSS_COOLDOWN_MINUTES)
    min_candle_data_for_indicators_config = config_module.MIN_CANDLE_DATA_FOR_INDICATORS
    trend_reversal_recency_hours_ga = parameters.get('TREND_REVERSAL_RECENCY_HOURS', config_module.TREND_REVERSAL_RECENCY_HOURS)
    trend_reversal_rsi_neutral_level_ga = parameters.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', config_module.TREND_REVERSAL_RSI_NEUTRAL_LEVEL)
    indicator_lookback_hours_ga = parameters.get('INDICATOR_LOOKBACK_HOURS', config_module.INDICATOR_LOOKBACK_HOURS)
    rsi_period_ga = parameters.get('RSI_PERIOD', config_module.RSI_PERIOD)
    bbands_period_ga, bbands_std_dev_ga = parameters.get('BBANDS_PERIOD', config_module.BBANDS_PERIOD), parameters.get('BBANDS_STD_DEV', config_module.BBANDS_STD_DEV)
    fast_ema_period_ga, slow_ema_period_ga = parameters.get('FAST_EMA_PERIOD', config_module.FAST_EMA_PERIOD), parameters.get('SLOW_EMA_PERIOD', config_module.SLOW_EMA_PERIOD)
    apply_trend_reversal_on_sell_reasons_config = config_module.APPLY_TREND_REVERSAL_ON_SELL_REASONS
    dex_lookback_mins = parameters.get('DEX_REVERSAL_LOOKBACK_MINUTES', config_module.DEX_REVERSAL_LOOKBACK_MINUTES)
    dex_min_snapshots = parameters.get('DEX_REVERSAL_MIN_SNAPSHOTS', config_module.DEX_REVERSAL_MIN_SNAPSHOTS)
    dex_min_liquidity = parameters.get('DEX_REVERSAL_MIN_LIQUIDITY_USD', config_module.DEX_REVERSAL_MIN_LIQUIDITY_USD)
    dex_min_ratio = parameters.get('DEX_REVERSAL_MIN_BUY_SELL_RATIO', config_module.DEX_REVERSAL_MIN_BUY_SELL_RATIO)
    dex_min_confirmations = parameters.get('DEX_REVERSAL_MIN_CONFIRMATIONS', config_module.DEX_REVERSAL_MIN_CONFIRMATIONS)

    use_dynamic_second_tp = bool(parameters.get('USE_DYNAMIC_SECOND_TP', config_module.USE_DYNAMIC_SECOND_TP))
    adaptive_atr_period = parameters.get('ADAPTIVE_ATR_PERIOD', config_module.ADAPTIVE_ATR_PERIOD)
    rsi_period = parameters.get('RSI_PERIOD', config_module.RSI_PERIOD)
    adaptive_rsi_strong = parameters.get('ADAPTIVE_RSI_STRONG_LEVEL', config_module.ADAPTIVE_RSI_STRONG_LEVEL)
    adaptive_rsi_extreme = parameters.get('ADAPTIVE_RSI_EXTREME_LEVEL', config_module.ADAPTIVE_RSI_EXTREME_LEVEL)
    adaptive_atr_base_mult = parameters.get('ADAPTIVE_ATR_BASE_MULTIPLIER', config_module.ADAPTIVE_ATR_BASE_MULTIPLIER)
    adaptive_atr_strong_mult = parameters.get('ADAPTIVE_ATR_STRONG_MULTIPLIER', config_module.ADAPTIVE_ATR_STRONG_MULTIPLIER)
    adaptive_atr_extreme_mult = parameters.get('ADAPTIVE_ATR_EXTREME_MULTIPLIER', config_module.ADAPTIVE_ATR_EXTREME_MULTIPLIER)

    # --- 3. Simulation State Initialization ---
    current_sol, trade_history, active_position = initial_capital, [], None
    simulated_active_cooldowns: Dict[str, datetime] = {}

    # --- 4. Main Simulation Loop ---
    for timestamp in df.index:
        try:
            row = df.loc[timestamp]
            price, high_price, volume = float(row["Close"]), float(row["High"]), float(row["Volume"])
            market_cap_sol, rugcheck_score = float(row.get("market_cap_calculated", 0.0)), int(row.get("rugcheck_score", 10000))
            socials_score, volatility_val = int(row.get("socials_score", 100)), float(row.get("volatility", 0.0))
            pre_existing_cooldown_until_data = pd.to_datetime(row.get('cooldown_until'), errors='coerce', utc=True)
            is_migrated_token = dexscreener_snapshot_data is not None and not dexscreener_snapshot_data.empty

            # --- 4a. Sell Logic ---
            if active_position:
                pos = active_position
                # Update the highest price seen since the buy
                pos['highest_price'] = max(pos['highest_price'], high_price)
                
                # Initialize sell trigger variables for the current timestep
                sell_reason, sell_all, sell_partial, sell_percentage = None, False, False, 0.0

                # --- Stage 1: Logic before the first take-profit is hit ---
                if not pos['first_tp_hit']:
                    if price <= pos['stop_loss_price']:
                        sell_reason, sell_all, sell_percentage = "🛑 Stop Loss", True, 1.0
                    # A very high TP can still be hit before the first one
                    elif price >= pos['second_tp_price']:
                        sell_reason, sell_all, sell_percentage = "Second TP", True, 1.0
                    # Check for the first take-profit
                    elif price >= pos['initial_tp_price']:
                        sell_reason, sell_partial, sell_percentage = "First TP", True, first_sell_percent / 100.0
                
                # --- Stage 2: Logic after the first take-profit has been hit ---
                else:
                    # --- DYNAMIC SELL LOGIC BRANCH ---
                    if use_dynamic_second_tp:
                        # Use the Adaptive Chandelier Exit logic
                        atr_col = f"ATRr_{adaptive_atr_period}"
                        rsi_col = f"RSI_{rsi_period}"

                        if atr_col in row and rsi_col in row and pd.notna(row[atr_col]) and pd.notna(row[rsi_col]):
                            # Determine the adaptive ATR multiplier based on RSI
                            multiplier = adaptive_atr_base_mult
                            if row[rsi_col] >= adaptive_rsi_extreme:
                                multiplier = adaptive_atr_extreme_mult
                            elif row[rsi_col] >= adaptive_rsi_strong:
                                multiplier = adaptive_atr_strong_mult
                            
                            # Calculate the dynamic exit price
                            chandelier_exit_price = pos['highest_price'] - (multiplier * row[atr_col])
                            
                            if price < chandelier_exit_price:
                                sell_reason = "Dynamic Exit (Chandelier)"
                                sell_all = True
                                sell_percentage = 1.0
                    
                    # --- Original Trailing SL logic (fallback if dynamic TP is off or indicators fail) ---
                    if not sell_reason:
                        trailing_sl_price = pos['highest_price'] * (1.0 - trailing_stop_loss_percent / 100.0)
                        if price >= pos['second_tp_price']:
                            sell_reason, sell_all, sell_percentage = "Second TP", True, 1.0
                        elif price <= trailing_sl_price:
                            sell_reason, sell_all, sell_percentage = "↘️ Trailing SL", True, 1.0

                    # The breakeven stop loss is always active after the first TP is hit
                    if not sell_reason and price <= pos['stop_loss_price']:
                        sell_reason, sell_all, sell_percentage = "🛡️ Breakeven SL", True, 1.0
                
                # --- Emergency Sell Conditions (checked at every step) ---
                if not sell_reason:
                    initial_mcap_sol = pos.get('initial_market_cap_sol', 0.0)
                    mc_drop_threshold_percent = parameters.get('MC_DROP_THRESHOLD', 5.0)

                    if market_cap_sol < min_emergency_mcap_usd:
                        sell_reason, sell_all, sell_percentage = "🆘 Emergency SL (MCap)", True, 1.0
                    elif initial_mcap_sol > 0 and market_cap_sol < (initial_mcap_sol * (1 - mc_drop_threshold_percent / 100.0)):
                        sell_reason, sell_all, sell_percentage = "🆘 Emergency SL (MC Drop%)", True, 1.0
                    elif is_migrated_token and volume <= 0:
                        sell_reason, sell_all, sell_percentage = "🆘 Emergency SL (No Volume)", True, 1.0

                # --- Execute Sell Action if a reason was triggered ---
                if sell_reason:
                    # Determine how many tokens to sell based on the trigger
                    tokens_to_sell = (pos['initial_tokens'] * sell_percentage) if sell_partial else (pos['remaining_tokens'] * sell_percentage)
                    tokens_to_sell = min(tokens_to_sell, pos['remaining_tokens']) # Cannot sell more than held

                    if tokens_to_sell > 1e-9: # Ensure there's a non-trivial amount to sell
                        # Simulate the transaction
                        net_sol = (tokens_to_sell * price) - sell_fee - sell_tip
                        cost_basis = pos['total_investment_sol'] * (tokens_to_sell / pos['initial_tokens']) if pos['initial_tokens'] > 0 else 0
                        pnl = net_sol - cost_basis
                        
                        # Update portfolio state
                        current_sol += net_sol
                        pos['remaining_tokens'] -= tokens_to_sell
                        
                        # Log the trade
                        trade_history.append({'timestamp': timestamp, 'type': 'sell', 'price': price, 'amount_sol': net_sol, 'amount_tokens': tokens_to_sell, 'reason': sell_reason, 'pnl': pnl, 'mint': mint_addr})
                        
                        # Update position state after a partial sell (First TP)
                        if sell_partial:
                            pos['first_tp_hit'] = True
                            pos['stop_loss_price'] = pos['buy_price'] # Move SL to breakeven
                        
                        # Close the position if all tokens are sold
                        if pos['remaining_tokens'] < 1e-9:
                            active_position = None
                        
                        # Apply cooldown period for stop-loss related sells
                        if stop_loss_cooldown_minutes_ga > 0 and any(trigger in sell_reason for trigger in apply_trend_reversal_on_sell_reasons_config):
                            cooldown_end_ts = timestamp + pd.Timedelta(minutes=stop_loss_cooldown_minutes_ga)
                            simulated_active_cooldowns[mint_addr] = cooldown_end_ts

            # --- 4b. Buy Logic ---
            elif not active_position and current_sol >= (sol_to_buy + buy_fee + buy_tip):
                is_on_pre_existing_cooldown = pd.notna(pre_existing_cooldown_until_data) and timestamp < pre_existing_cooldown_until_data
                simulated_cooldown_end_ts = simulated_active_cooldowns.get(mint_addr)
                is_on_simulated_cooldown = simulated_cooldown_end_ts and timestamp < simulated_cooldown_end_ts
                if is_on_pre_existing_cooldown or is_on_simulated_cooldown: continue

                meets_standard_criteria = (volume >= volume_threshold and market_cap_sol >= marketcap_threshold and rugcheck_score < rugcheck_threshold and socials_score < socials_threshold and volatility_val >= min_volatility)
                proceed_with_buy_attempt = False

                if not meets_standard_criteria:
                    proceed_with_buy_attempt = False
                elif use_trend_reversal:
                    was_recently_sold_for_reversal_reason = False
                    if trade_history:
                        for trade in reversed(trade_history):
                            if trade.get('mint') == mint_addr and trade.get('type') == 'sell':
                                if (timestamp - trade['timestamp']) <= pd.Timedelta(hours=trend_reversal_recency_hours_ga):
                                    if any(reason in trade.get('reason', '') for reason in apply_trend_reversal_on_sell_reasons_config):
                                        was_recently_sold_for_reversal_reason = True; break
                                else: break
                    if was_recently_sold_for_reversal_reason:
                        if is_migrated_token:
                            lookback_start_ts = timestamp - pd.Timedelta(minutes=dex_lookback_mins)
                            mask = (dexscreener_snapshot_data.index <= timestamp) & (dexscreener_snapshot_data.index >= lookback_start_ts)
                            snapshots = dexscreener_snapshot_data.loc[mask]
                            if len(snapshots) < dex_min_snapshots: proceed_with_buy_attempt = False
                            elif float(snapshots.iloc[-1]['liquidity_usd']) < dex_min_liquidity: proceed_with_buy_attempt = False
                            else:
                                confirmations = sum(1 for _, s in snapshots.iterrows() if s.get('buys_m5', 0) > 0 and (s.get('sells_m5', 0) == 0 or (s.get('buys_m5', 0) / s.get('sells_m5', 0)) >= dex_min_ratio))
                                if confirmations >= dex_min_confirmations:
                                    proceed_with_buy_attempt = True
                                else: proceed_with_buy_attempt = False
                        else:
                            current_loc = df.index.get_loc(timestamp)
                            candles_for_lookback = int(indicator_lookback_hours_ga * 720)
                            start_loc = max(0, current_loc - candles_for_lookback + 1)
                            if (current_loc - start_loc + 1) >= min_candle_data_for_indicators_config:
                                indicator_slice = df.iloc[start_loc : current_loc + 1]
                                indicator_params = (rsi_period_ga, bbands_period_ga, bbands_std_dev_ga, fast_ema_period_ga, slow_ema_period_ga)
                                cache_key = (mint_addr, indicator_params)
                                if indicator_cache is not None and cache_key in indicator_cache:
                                    df_with_indicators = indicator_cache[cache_key]
                                else:
                                    # --- FIX: Add missing ADAPTIVE_ATR_PERIOD key to this config dict ---
                                    # This prevents a potential KeyError in the utility function.
                                    indicator_config = {
                                        'MIN_CANDLE_DATA_FOR_INDICATORS': min_candle_data_for_indicators_config, 
                                        'RSI_PERIOD': rsi_period_ga, 
                                        'BBANDS_PERIOD': bbands_period_ga, 
                                        'BBANDS_STD_DEV': bbands_std_dev_ga, 
                                        'FAST_EMA_PERIOD': fast_ema_period_ga, 
                                        'SLOW_EMA_PERIOD': slow_ema_period_ga,
                                        'ADAPTIVE_ATR_PERIOD': adaptive_atr_period # This key was missing
                                    }
                                    # --- END FIX ---
                                    df_with_indicators = utils.calculate_trend_indicators(indicator_slice.copy(), indicator_config)
                                    if indicator_cache is not None and df_with_indicators is not None and not df_with_indicators.empty:
                                        indicator_cache[cache_key] = df_with_indicators
                                if df_with_indicators is not None and not df_with_indicators.empty and len(df_with_indicators) >= 2:
                                    latest, prev = df_with_indicators.iloc[-1], df_with_indicators.iloc[-2]
                                    rsi_cross = pd.notna(latest.get('RSI')) and pd.notna(prev.get('RSI')) and latest['RSI'] > 30 and prev['RSI'] <= 30
                                    bb_lower_col = f"BBL_{bbands_period_ga}_{bbands_std_dev_ga}"
                                    bb_reenter = pd.notna(latest.get('Close')) and pd.notna(prev.get('Close')) and pd.notna(latest.get(bb_lower_col)) and pd.notna(prev.get(bb_lower_col)) and latest['Close'] > latest[bb_lower_col] and prev['Close'] <= prev[bb_lower_col]
                                    stage1 = rsi_cross or bb_reenter or (pd.notna(latest.get('RSI')) and latest['RSI'] > trend_reversal_rsi_neutral_level_ga)
                                    if stage1:
                                        vwap_ok = pd.notna(latest.get('VWAP')) and latest['Close'] > latest['VWAP']
                                        ema_ok = pd.notna(latest.get('EMA_fast')) and pd.notna(latest.get('EMA_slow')) and latest['EMA_fast'] > latest['EMA_slow']
                                        if vwap_ok and ema_ok: proceed_with_buy_attempt = True
                    else:
                        proceed_with_buy_attempt = True
                else:
                    proceed_with_buy_attempt = meets_standard_criteria

                if proceed_with_buy_attempt:
                    total_investment, sol_for_tokens = sol_to_buy + buy_fee + buy_tip, sol_to_buy
                    tokens_bought = sol_for_tokens / price if price > 0 else 0
                    if tokens_bought > 0:
                        initial_sl = price * (1.0 - initial_stop_loss_percent / 100.0)
                        cost_tp1 = total_investment * (first_sell_percent / 100.0)
                        profit_tp1 = cost_tp1 * (first_sell_profit_margin / 100.0)
                        gross_needed_tp1 = cost_tp1 + profit_tp1 + sell_fee + sell_tip
                        tokens_tp1 = tokens_bought * (first_sell_percent / 100.0)
                        initial_tp = (gross_needed_tp1 / tokens_tp1) if tokens_tp1 > 1e-9 else float('inf')
                        second_tp = price * (1.0 + second_take_profit_percent / 100.0)
                        current_sol -= total_investment
                        active_position = {
                            'buy_price': price, 
                            'initial_tokens': tokens_bought, 
                            'remaining_tokens': tokens_bought, 
                            'total_investment_sol': total_investment, 
                            'stop_loss_price': initial_sl, 
                            'initial_tp_price': initial_tp, 
                            'second_tp_price': second_tp, 
                            'highest_price': price, 
                            'first_tp_hit': False, 
                            'entry_timestamp': timestamp,
                            'initial_market_cap_sol': market_cap_sol # Store the market cap at the time of buy
                        }
                        trade_history.append({'timestamp': timestamp, 'type': 'buy', 'price': price, 'amount_sol': total_investment, 'amount_tokens': tokens_bought, 'buy_fee': buy_fee, 'buy_tip': buy_tip, 'mint': mint_addr})
                        if mint_addr in simulated_active_cooldowns: del simulated_active_cooldowns[mint_addr]
        except (KeyError, ValueError) as e:
            logger.error(f"Data error at step for {mint_addr} (Timestamp: {timestamp}): {e}", exc_info=False)
            continue
        except Exception as e:
            logger.error(f"Unexpected error during simulation step for {mint_addr}: {e}", exc_info=True)
            continue

    # --- 5. Final Portfolio Valuation ---
    final_value = current_sol
    if active_position and not df.empty:
        last_candle_ts = df.index[-1]
        if end_ts_data and end_ts_data < df.index[-1]:
            valid_ts = df.index[df.index <= end_ts_data]
            if not valid_ts.empty: last_candle_ts = valid_ts[-1]
        last_close_price = float(df.loc[last_candle_ts]["Close"])
        net_sol_final = (active_position['remaining_tokens'] * last_close_price) - sell_fee - sell_tip
        final_value += max(0, net_sol_final)

    # --- 6. Return Performance Metrics ---
    metrics = calculate_performance_metrics(trade_history, initial_capital, final_value, start_ts=start_ts_data, end_ts=end_ts_data, simulation_end_reason=simulation_end_reason)
    metrics.update({
        "parameters": parameters,
        "initial_capital": initial_capital, 
        "final_portfolio_value": final_value,
        "trade_history": trade_history
    })
    return metrics
```

#### 📄 `ga_dashboard.py`
*path: `ga_optimizer_module/ga_dashboard.py`*

```python
# FILE: ga_optimizer_module/ga_dashboard.py
# **MODIFIED:** This version adds a 'Run' axis to the parameter plot for easy
# identification, improves the layout, and uses the latest Streamlit APIs.

import os
from pathlib import Path
import json

import psycopg2
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go 

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="GA Optimizer Dashboard")

# --- Database Connection (Synchronous with psycopg2) ---
@st.cache_resource
def init_connection():
    """Initializes a connection to the PostgreSQL database."""
    script_location = Path(__file__).resolve().parent
    project_root = script_location.parent
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    raw_db_host = os.getenv("DB_HOST")
    db_host_val, db_port_val = (None, 5432)
    if raw_db_host:
        if ":" in raw_db_host:
            host, port_str = raw_db_host.split(":")
            db_host_val, db_port_val = (host, int(port_str))
        else:
            db_host_val = raw_db_host
    
    conn = psycopg2.connect(
        host=db_host_val,
        port=db_port_val,
        dbname=os.getenv("DB_DATABASE"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

# --- Data Fetching Functions (Unchanged) ---
def get_runs(conn):
    """Fetches all run_ids from the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT run_id, created_at FROM ga_runs ORDER BY created_at DESC")
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

def get_ranked_solutions(conn, run_id):
    """Fetches and ranks all solutions for a given run by their average performance."""
    query = """
    SELECT
        s.id as solution_id, s.generation, AVG(b.final_portfolio_value) as avg_portfolio,
        AVG(b.win_rate) as avg_win_rate, AVG(b.profit_factor) as avg_profit_factor,
        SUM(b.total_trades) as total_trades, COUNT(b.id) as backtest_count, s.parameters
    FROM ga_solutions s JOIN ga_backtests b ON s.id = b.solution_id
    WHERE s.run_id = %s AND b.status = 'success'
    GROUP BY s.id, s.generation, s.parameters ORDER BY avg_portfolio DESC;
    """
    with conn.cursor() as cur:
        cur.execute(query, (run_id,))
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

def get_solution_backtests(conn, solution_id):
    """Fetches all individual backtest results for a specific solution."""
    query = """
    SELECT id as backtest_id, mint_tested, final_portfolio_value, win_rate, profit_factor, total_trades
    FROM ga_backtests WHERE solution_id = %s AND status = 'success' ORDER BY final_portfolio_value DESC;
    """
    with conn.cursor() as cur:
        cur.execute(query, (solution_id,))
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

def get_trade_history(conn, backtest_id):
    """Fetches the complete trade history for a single backtest."""
    query = 'SELECT "timestamp", "type", price, amount_sol, amount_tokens, reason, pnl FROM ga_trades WHERE backtest_id = %s ORDER BY "timestamp" ASC;'
    with conn.cursor() as cur:
        cur.execute(query, (backtest_id,))
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

# --- Main Application Logic ---
def main():
    st.title("📈 Genetic Algorithm Performance Dashboard")

    conn = init_connection()
    runs_df = get_runs(conn)

    if runs_df.empty:
        st.error("No runs found in the database. Please run the optimizer and ingestion script first.")
        st.stop()
        
    runs_df['display'] = runs_df.apply(lambda row: f"{row['created_at'].strftime('%Y-%m-%d %H:%M')} ({str(row['run_id'])[:8]})", axis=1)

    # --- TABS FOR SINGLE AND COMPARISON VIEWS ---
    tab1, tab2 = st.tabs(["Single Run Analysis", "Cross-Run Comparison"])

    # --- TAB 1: ORIGINAL SINGLE RUN ANALYSIS VIEW ---
    with tab1:
        st.header("Single Run Deep Dive")
        selected_display = st.selectbox("Select Optimization Run", runs_df['display'])
        
        selected_run_id = runs_df[runs_df['display'] == selected_display]['run_id'].iloc[0]

        st.info(f"Analyzing Run ID: `{selected_run_id}`")
        
        with st.spinner("Fetching optimization data for selected run..."):
            solutions_df = get_ranked_solutions(conn, selected_run_id)

        if solutions_df.empty:
            st.warning("This run has no successful backtests to analyze.")
        else:
            best_solution = solutions_df.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Top Portfolio Value", f"{float(best_solution['avg_portfolio']):.2f} SOL")
            col2.metric("Total Solutions Tested", f"{len(solutions_df)}")
            col3.metric("Best Solution's Win Rate", f"{float(best_solution['avg_win_rate']):.2f}%")

            st.subheader("Ranked Strategies")
            st.text("Click on any row to load its details below.")
            
            display_cols = ['solution_id', 'generation', 'avg_portfolio', 'avg_win_rate', 'avg_profit_factor', 'total_trades', 'backtest_count']
            
            st.dataframe(
                solutions_df[display_cols],
                width='stretch',
                on_select="rerun",
                selection_mode="single-row",
                key="ranked_strategies_df"
            )

            selection = st.session_state.get('ranked_strategies_df', {}).get('selection', {})
            selected_solution_id = None
            if selection and selection.get("rows"):
                selected_index = selection["rows"][0]
                selected_solution_id = int(solutions_df.iloc[selected_index]['solution_id'])
            else:
                selected_solution_id = int(best_solution['solution_id'])

            st.subheader(f"Strategy Deep Dive (Solution ID: `{selected_solution_id}`)")

            if selected_solution_id:
                solution_params = solutions_df.loc[solutions_df['solution_id'] == selected_solution_id, 'parameters'].iloc[0]
                
                with st.expander(f"View Parameters", expanded=False):
                    st.json(solution_params)

                st.write("**Individual Backtest Performance**")
                backtests_df = get_solution_backtests(conn, selected_solution_id)
                st.dataframe(backtests_df, width='stretch')

                if not backtests_df.empty:
                    selected_backtest_id = st.selectbox(
                        "Select a 'backtest_id' to view trade history:",
                        backtests_df['backtest_id']
                    )
                    if selected_backtest_id:
                        st.write(f"**Trade History for Backtest ID {selected_backtest_id}**")
                        trades_df = get_trade_history(conn, int(selected_backtest_id))
                        st.dataframe(trades_df, width='stretch')

    # --- TAB 2: NEW CROSS-RUN COMPARISON VIEW ---
    with tab2:
        st.header("Compare Multiple Optimization Runs")
        selected_run_displays = st.multiselect(
            "Select 2 or more runs to compare:", 
            runs_df['display'],
            max_selections=5
        )

        if len(selected_run_displays) < 2:
            st.info("Please select at least two runs to generate a comparison.")
        else:
            run_ids_to_compare = runs_df[runs_df['display'].isin(selected_run_displays)]['run_id'].tolist()
            
            all_solutions_list = []
            best_solutions_data = [] 
            with st.spinner("Fetching and aggregating data for comparison..."):
                for run_id, display_name in zip(run_ids_to_compare, selected_run_displays):
                    run_solutions_df = get_ranked_solutions(conn, run_id)
                    if not run_solutions_df.empty:
                        run_solutions_df['run_display_name'] = display_name
                        all_solutions_list.append(run_solutions_df)
                        best_solution = run_solutions_df.iloc[0].to_dict()
                        best_solution['run_display_name'] = display_name
                        best_solutions_data.append(best_solution)

            if not all_solutions_list:
                st.warning("Could not fetch valid data for the selected runs.")
            else:
                st.subheader("Performance Distribution")
                st.markdown("This plot shows the distribution of the final portfolio value for all solutions in each run. It helps identify which run was consistently better, not just lucky with one outlier.")
                
                combined_df = pd.concat(all_solutions_list, ignore_index=True)
                fig_box = px.box(
                    combined_df, 
                    x='run_display_name', y='avg_portfolio', color='run_display_name',
                    points="all", title="Distribution of Average Portfolio Value Across Runs",
                    labels={"run_display_name": "Optimization Run", "avg_portfolio": "Average Final Portfolio (SOL)"}
                )
                st.plotly_chart(fig_box, use_container_width=True)

                st.subheader("Best Solution Parameter Comparison")
                st.markdown("This chart compares the best strategies found in each run. Each line represents a run, colored by its final portfolio value. Use the 'Run' axis on the left to identify which line corresponds to which run.")
                
                best_solutions_df = pd.DataFrame(best_solutions_data)
                params_unpacked = best_solutions_df['parameters'].apply(pd.Series)
                plot_df = pd.concat([best_solutions_df[['run_display_name', 'avg_portfolio']], params_unpacked], axis=1)

                all_possible_params = sorted([col for col in params_unpacked.columns if plot_df[col].nunique() > 1])
                default_params = [
                    'INITIAL_STOP_LOSS_PERCENT', 'FIRST_SELL_PERCENT', 'FIRST_SELL_PROFIT_MARGIN',
                    'TRAILING_STOP_LOSS_PERCENT', 'SECOND_TAKE_PROFIT_PERCENT', 'USE_DYNAMIC_SECOND_TP',
                    'MIN_VOLATILITY', 'DEFAULT_RUGCHECK_SCORE_THRESHOLD'
                ]
                default_selection = [p for p in default_params if p in all_possible_params]

                params_to_display = st.multiselect(
                    "Select parameters to display on the chart:",
                    options=all_possible_params,
                    default=default_selection
                )

                if params_to_display:
                    # --- NEW: Create a categorical axis for the Run Name ---
                    run_names = plot_df['run_display_name'].unique()
                    run_name_map = {name: i for i, name in enumerate(run_names)}
                    plot_df['run_idx'] = plot_df['run_display_name'].map(run_name_map)
                    
                    dimensions = [
                        {
                            'label': 'Run',
                            'tickvals': list(run_name_map.values()),
                            'ticktext': list(run_name_map.keys()),
                            'values': plot_df['run_idx']
                        }
                    ]
                    # Add the numeric parameter dimensions after the run name
                    dimensions.extend([{'label': param, 'values': plot_df[param]} for param in params_to_display])
                    
                    fig_parallel = go.Figure(data=
                        go.Parcoords(
                            line = dict(
                                color = plot_df['avg_portfolio'],
                                colorscale = 'Electric',
                                showscale = True,
                                colorbar = {'title': 'Avg Portfolio'},
                                cmin = plot_df['avg_portfolio'].min(),
                                cmax = plot_df['avg_portfolio'].max()
                            ),
                            dimensions = list(dimensions)
                        )
                    )
                    
                    fig_parallel.update_layout(
                        title='Comparison of Best Parameters by Performance',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        margin=dict(l=80, r=80, t=100, b=40) # Increased margins
                    )

                    st.plotly_chart(fig_parallel, use_container_width=True)
                else:
                    st.warning("Please select at least one parameter to display.")

if __name__ == "__main__":
    main()
```

#### 📄 `ga_ingestion.py`
*path: `ga_optimizer_module/ga_ingestion.py`*

```python
# FILE: GA_Optimizer/ga_ingestion.py

import asyncio
import json
import os
import math
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

import asyncpg
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

# --- ROBUST .ENV LOADING ---
script_location = Path(__file__).resolve().parent
project_root = script_location.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
raw_db_host = os.getenv("DB_HOST")
db_host_val, db_port_val = ("localhost", 5432)
if raw_db_host:
    if ":" in raw_db_host:
        try:
            host, port_str = raw_db_host.split(":")
            db_host_val, db_port_val = (host, int(port_str))
        except ValueError:
            print(f"Warning: Could not parse DB_HOST '{raw_db_host}'. Using defaults.")
    else: db_host_val = raw_db_host

DB_CONFIG = {"user": os.getenv("DB_USER"),"password": os.getenv("DB_PASSWORD"),"database": os.getenv("DB_DATABASE"),"host": db_host_val,"port": db_port_val}
DEFAULT_LOG_FILE_PATH = project_root / "ga_optimization_results" / "ga_detailed_trade_log.parquet"

# --- Helper Functions (for data cleaning) ---
def sanitize_metric(value):
    """Replaces non-finite numbers (inf, -inf, nan) with None."""
    if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value

def parse_iso_datetime(ts_string: str | None) -> datetime | None:
    """Converts an ISO format string to a datetime object, handling None and NaT."""
    if pd.isna(ts_string) or ts_string is None:
        return None
    try:
        return datetime.fromisoformat(ts_string)
    except (ValueError, TypeError):
        return None

# --- REFACTORED FOR PARQUET ---
async def ingest_log_file_bulk(pool: asyncpg.Pool, file_path: str):
    """
    Reads the entire .parquet log file with pandas and bulk-inserts
    the data into the database for maximum performance.
    """
    if not os.path.exists(file_path):
        print(f"Error: Log file not found at '{file_path}'")
        return

    print("Reading Parquet log file into memory...")
    try:
        df = pd.read_parquet(file_path)
        if df.empty:
            print("Log file is empty or could not be read. Nothing to ingest.")
            return
    except Exception as e:
        print(f"Error reading or parsing Parquet file: {e}")
        return

    # --- DESERIALIZE JSON STRINGS ---
    if 'parameters' in df.columns:
        df['parameters'] = df['parameters'].apply(json.loads)
    if 'trade_history' in df.columns:
        df['trade_history'] = df['trade_history'].apply(lambda x: json.loads(x) if pd.notna(x) and isinstance(x, str) else [])
    
    print(f"Preparing {len(df)} records for database ingestion...")

    # 1. Prepare and Ingest `ga_runs`
    runs_df = df[['run_id']].drop_duplicates().dropna()
    run_records = runs_df.to_records(index=False)
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                "INSERT INTO ga_runs (run_id) VALUES ($1) ON CONFLICT (run_id) DO NOTHING",
                run_records
            )
    print(f"Ingested {len(runs_df)} unique runs.")

    # 2. Prepare and Ingest `ga_solutions`
    solutions_df = df[['run_id', 'generation', 'solution_idx', 'parameters']].drop_duplicates(subset=['run_id', 'generation', 'solution_idx'])
    solutions_df['parameters'] = solutions_df['parameters'].apply(json.dumps)
    
    async with pool.acquire() as conn:
        stmt = await conn.prepare("""
            INSERT INTO ga_solutions (run_id, generation, solution_idx, parameters)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (run_id, generation, solution_idx) DO UPDATE
            SET parameters = EXCLUDED.parameters
            RETURNING id, run_id, generation, solution_idx
        """)
        
        returned_ids = await stmt.fetchmany(solutions_df.to_records(index=False))
        returned_ids_list = [dict(rec) for rec in returned_ids]
        id_map_df = pd.DataFrame(returned_ids_list)

        if not id_map_df.empty:
            id_map_df.rename(columns={'id': 'solution_id'}, inplace=True)
            id_map_df['run_id'] = id_map_df['run_id'].astype(str)
        
        df = pd.merge(df, id_map_df, on=['run_id', 'generation', 'solution_idx'], how='left')

        if df['solution_id'].isnull().any():
            print(f"Warning: {df['solution_id'].isnull().sum()} records failed to match a solution_id and will be dropped.")
            df.dropna(subset=['solution_id'], inplace=True)
        df['solution_id'] = df['solution_id'].astype(int)

    print(f"Ingested {len(solutions_df)} unique solutions.")

    # 3. Prepare and Ingest `ga_backtests`
    backtests_df = df.drop_duplicates(subset=['solution_id', 'mint_tested']).copy()
    
    if 'error_message' not in backtests_df.columns:
        backtests_df['error_message'] = None

    backtest_cols = [
        'solution_id', 'mint_tested', 'status', 'error_message',
        'final_portfolio_value', 'total_pnl', 'total_return_pct', 'win_rate',
        'profit_factor', 'max_drawdown', 'total_trades',
        'simulation_start_ts', 'simulation_end_ts', 'simulation_end_reason'
    ]
    
    numeric_metric_cols = [
        'final_portfolio_value', 'total_pnl', 'total_return_pct', 'win_rate',
        'profit_factor', 'max_drawdown', 'total_trades'
    ]
    for col in numeric_metric_cols:
        if col in backtests_df.columns:
            backtests_df[col] = backtests_df[col].apply(sanitize_metric)
    
    backtests_df['simulation_start_ts'] = backtests_df['simulation_start_ts'].apply(parse_iso_datetime)
    backtests_df['simulation_end_ts'] = backtests_df['simulation_end_ts'].apply(parse_iso_datetime)
    
    for col in backtest_cols:
        if col not in backtests_df.columns:
            backtests_df[col] = pd.NaT if 'ts' in col else None
            
    async with pool.acquire() as conn:
        stmt_bt = await conn.prepare(f"""
            INSERT INTO ga_backtests ({', '.join(f'"{c}"' for c in backtest_cols)})
            VALUES ({', '.join([f'${i+1}' for i in range(len(backtest_cols))])})
            ON CONFLICT (solution_id, mint_tested) DO NOTHING
            RETURNING id, solution_id, mint_tested
        """)
        returned_bt_ids = await stmt_bt.fetchmany(backtests_df[backtest_cols].to_records(index=False))
        bt_id_map_df = pd.DataFrame(returned_bt_ids, columns=['backtest_id', 'solution_id', 'mint_tested'])
        
        if not bt_id_map_df.empty:
            bt_id_map_df['backtest_id'] = bt_id_map_df['backtest_id'].astype(int)
        
        df = pd.merge(df, bt_id_map_df, on=['solution_id', 'mint_tested'], how='left')
    print(f"Ingested {len(backtests_df)} unique backtests.")

    # 4. Prepare and Ingest `ga_trades`
    if 'backtest_id' not in df.columns or df['backtest_id'].isnull().all():
        print("No valid backtest IDs were generated. Skipping trade ingestion.")
        return
        
    if df['backtest_id'].isnull().any():
        print(f"Warning: {df['backtest_id'].isnull().sum()} records could not be matched to a backtest_id and will be dropped before trade ingestion.")
        df.dropna(subset=['backtest_id'], inplace=True)

    if df.empty:
        print("No valid records remain after filtering. No trades to ingest.")
        return

    df['backtest_id'] = df['backtest_id'].astype(int)
    
    trades_df = df[df['trade_history'].apply(lambda x: isinstance(x, list) and len(x) > 0)][['backtest_id', 'trade_history']]
    if not trades_df.empty:
        trades_exploded = trades_df.explode('trade_history').reset_index(drop=True)
        trade_details = pd.json_normalize(trades_exploded['trade_history'])
        final_trades_df = pd.concat([trades_exploded[['backtest_id']], trade_details], axis=1)

        final_trades_df.rename(columns={'timestamp': 'trade_timestamp'}, inplace=True)
        trade_cols_to_ingest = ['backtest_id', 'trade_timestamp', 'type', 'price', 'amount_sol', 'amount_tokens', 'reason', 'pnl']
        
        # --- FIX 1: Ensure all expected columns exist, filling missing ones with None ---
        for col in trade_cols_to_ingest:
            if col not in final_trades_df.columns:
                final_trades_df[col] = None
        
        final_trades_df = final_trades_df.reindex(columns=trade_cols_to_ingest)
        # --- END FIX 1 ---
        
        final_trades_df['trade_timestamp'] = final_trades_df['trade_timestamp'].apply(parse_iso_datetime)
        
        # --- FIX 2: Apply sanitation to all numeric trade columns to handle NaNs ---
        for col in ['price', 'amount_sol', 'amount_tokens', 'pnl']:
            if col in final_trades_df.columns:
                final_trades_df[col] = final_trades_df[col].apply(sanitize_metric)
        # --- END FIX 2 ---

        # --- FIX 3 (APPLIED): Explicitly handle non-string types in text columns ---
        # `pd.json_normalize` can introduce NaN (a float) for missing keys (e.g., 'reason' on a buy trade).
        # This causes a TypeError on ingestion into a TEXT column. We convert NaN to None (which becomes NULL).
        if 'reason' in final_trades_df.columns:
            final_trades_df['reason'] = final_trades_df['reason'].apply(lambda x: str(x) if pd.notna(x) else None)
        # --- END FIX 3 ---

        async with pool.acquire() as conn:
            final_trades_df['backtest_id'] = final_trades_df['backtest_id'].astype(int)
            affected_backtest_ids = final_trades_df['backtest_id'].unique().tolist()

            if affected_backtest_ids:
                await conn.execute("DELETE FROM ga_trades WHERE backtest_id = ANY($1::int[])", affected_backtest_ids)
            
            # The columns list for copy_records_to_table MUST match the database schema exactly
            db_trade_columns = ['backtest_id', 'timestamp', 'type', 'price', 'amount_sol', 'amount_tokens', 'reason', 'pnl']
            
            # Rename dataframe column to match DB schema for copy_records_to_table
            final_trades_df.rename(columns={'trade_timestamp': 'timestamp'}, inplace=True)
            
            await conn.copy_records_to_table(
                'ga_trades', 
                records=final_trades_df.to_records(index=False), 
                columns=db_trade_columns
            )
        print(f"Ingested {len(final_trades_df)} trades for {len(affected_backtest_ids)} backtests.")

async def run_ingestion(log_file_path: str):
    """ Main entry point function to set up the DB pool and run the ingestion. """
    if not all([DB_CONFIG["user"], DB_CONFIG["password"], DB_CONFIG["database"], DB_CONFIG["host"]]):
        print("Error: Database credentials are not fully configured. Skipping ingestion.")
        return
    
    pool = None
    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        await ingest_log_file_bulk(pool, log_file_path)
    except Exception as e:
        print(f"A critical error occurred during the ingestion process: {e}")
    finally:
        if pool:
            await pool.close()
    print("Database ingestion process finished.")


if __name__ == "__main__":
    print("Running ingestion script in standalone mode...")
    log_file_path_str = str(DEFAULT_LOG_FILE_PATH)
    asyncio.run(run_ingestion(log_file_path_str))
```

#### 📄 `ga_optimizer.py`
*path: `ga_optimizer_module/ga_optimizer.py`*

```python
# ga_optimizer_module/ga_optimizer.py
import os
import sys
import asyncio
import pygad
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import time
import json
import random
import uuid
from multiprocessing import Manager, freeze_support, Process, Queue
from typing import Dict, List, Optional
from glob import glob
import gc  # For manual garbage collection

# --- Project Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
import config.config as bot_config
from config.ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS, CROSSOVER_PROBABILITY,
    MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL, DATA_SPLIT,
    BACKTEST_INITIAL_CAPITAL, RESULTS_DIR, HISTORICAL_DATA_START_TS,
    HISTORICAL_DATA_END_TS, MULTIPROCESSING_CORES, KEEP_ELITISM, PARENT_SELECTION_TYPE,
    CROSSOVER_TYPE, MUTATION_TYPE, GA_FITNESS_SAMPLE_SIZE, DETAILED_LOG_FILENAME, STOP_CRITERIA
)
from ga_optimizer_module.ga_backtester import run_backtest_sync
from utils import NpEncoder
from ga_optimizer_module.ga_ingestion import run_ingestion

# --- NEW: WORKER-LOCAL GLOBAL VARIABLES & CACHE PATH ---
WORKER_DATA = {}
GA_CACHE_PATH = os.path.join(project_root, "data", "ga_cache")

# --- Log Writer (Unchanged) ---
def log_writer_process(log_queue: Queue, log_file_path: str):
    records = []
    try:
        while True:
            record = log_queue.get()
            if record is None: break
            records.append(record)
        if records:
            df = pd.DataFrame(records)
            if 'parameters' in df.columns: df['parameters'] = df['parameters'].apply(json.dumps, cls=NpEncoder)
            if 'trade_history' in df.columns: df['trade_history'] = df['trade_history'].apply(json.dumps, cls=NpEncoder)
            df.to_parquet(log_file_path, index=False, engine='pyarrow')
            logger.debug(f"Successfully wrote {len(df)} records to {log_file_path}")
    except Exception as e:
        logger.debug(f"Log writer process error: {e}")

# --- Fitness Function (Loads from Parquet Cache) ---
def fitness_func_main_process(ga_instance, solution: np.ndarray, solution_idx: int) -> float:
    global WORKER_DATA
    worst_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')

    try:
        # --- ONE-TIME INITIALIZATION PER WORKER (FROM CACHE) ---
        if not WORKER_DATA:
            logger.debug(f"Worker PID {os.getpid()}: Initializing... Loading metadata (paths, lifespans, snapshots) from Parquet cache.")
            date_str = f"{HISTORICAL_DATA_START_TS.strftime('%Y%m%d')}_{HISTORICAL_DATA_END_TS.strftime('%Y%m%d')}"
            cache_dir = os.path.join(GA_CACHE_PATH, date_str)

            if not os.path.isdir(cache_dir):
                logger.debug(f"FATAL ERROR in Worker PID {os.getpid()}: Cache directory not found at '{cache_dir}'.")
                logger.debug("Please run 'python ga_optimizer_module/prepare_ga_dataset.py' first.")
                return worst_fitness
            
            # 1. Load mint-to-path for OHLCV (LAZY: don't load data yet)
            ohlcv_dir = os.path.join(cache_dir, "ohlcv_data")
            mint_to_path = {os.path.basename(f).replace('.parquet', ''): f for f in glob(os.path.join(ohlcv_dir, "*.parquet"))}
            all_mints = list(mint_to_path.keys())

            # 2. Load lifespans
            lifespans_df = pd.read_parquet(os.path.join(cache_dir, "token_lifespans.parquet"))
            token_lifespans = lifespans_df.to_dict(orient='index')
            
            # 3. Load DexScreener snapshots
            snapshots_dir = os.path.join(cache_dir, "dexscreener_snapshots")
            dexscreener_snapshots = {os.path.basename(f).replace('.parquet', ''): pd.read_parquet(f) for f in glob(os.path.join(snapshots_dir, "*.parquet"))}

            # Split data into train/validation/test sets
            all_mints = sorted(list(mint_to_path.keys()))
            random.Random(42).shuffle(all_mints) # Use a fixed seed for reproducibility
            train_ratio, val_ratio = DATA_SPLIT['training'], DATA_SPLIT['validation']
            train_idx = int(len(all_mints) * train_ratio)
            val_idx = int(len(all_mints) * (train_ratio + val_ratio))
            
            train_mints = all_mints[:train_idx]
            val_mints = all_mints[train_idx:val_idx]
            test_mints = all_mints[val_idx:]

            # Store paths for train set (lazy)
            WORKER_DATA['train_data_paths'] = {m: mint_to_path[m] for m in train_mints}
            WORKER_DATA['validation_data'] = {m: pd.read_parquet(mint_to_path[m]) for m in val_mints}
            WORKER_DATA['test_data'] = {m: pd.read_parquet(mint_to_path[m]) for m in test_mints}
            WORKER_DATA['lifespans'] = token_lifespans
            WORKER_DATA['snapshots'] = dexscreener_snapshots
            WORKER_DATA['train_mints'] = train_mints  # Store for sampling
            logger.debug(f"Worker PID {os.getpid()}: Loaded {len(WORKER_DATA['train_mints'])} train mints, {len(WORKER_DATA['validation_data'])} validation mints, {len(WORKER_DATA['test_data'])} test mints.")

        # --- REGULAR FITNESS CALCULATION ---
        train_mints = WORKER_DATA.get('train_mints', [])
        if not train_mints:
            logger.warning(f"Worker PID {os.getpid()}: No training mints available.")
            return worst_fitness
        
        parameters = {p['name']: p['type'](float(solution[i]) if p['type'] in [float, 'float'] else int(round(solution[i]))) for i, p in enumerate(OPTIMIZABLE_PARAMETERS)}
        
        sample_size = GA_FITNESS_SAMPLE_SIZE
        mints_to_evaluate = train_mints if not sample_size or sample_size >= len(train_mints) else random.sample(train_mints, min(sample_size, len(train_mints)))
        logger.debug(f"Worker PID {os.getpid()}: Evaluating solution {solution_idx} on {len(mints_to_evaluate)} mints (sample size: {sample_size})")

        fitness_values = []
        for mint in mints_to_evaluate:
            # Lazy load ONLY this mint's OHLCV data
            path = WORKER_DATA['train_data_paths'].get(mint)
            if not path or not os.path.exists(path):
                logger.warning(f"No Parquet file found for mint {mint}. Skipping.")
                continue
            df_data = pd.read_parquet(path)
            
            lifespan = WORKER_DATA['lifespans'].get(mint)
            snapshots = WORKER_DATA['snapshots'].get(mint)

            if df_data is None:
                logger.warning(f"No data loaded for mint {mint}. Skipping.")
                continue

            max_timestamp = lifespan['end_ts'] if lifespan else None
            parameters['mint'] = mint
            
            log_record = {
                "run_id": ga_instance.run_id,
                "generation": ga_instance.generations_completed,
                "solution_idx": solution_idx,
                "mint_tested": mint,
                "parameters": parameters,
                "status": "success"
            }
            try:
                result = run_backtest_sync(parameters, df_data, BACKTEST_INITIAL_CAPITAL, max_timestamp, snapshots, ga_instance.indicator_cache)
                if isinstance(result, dict):
                    log_record.update(result)
                    fitness = result.get(FITNESS_METRIC)
                    if fitness is not None and pd.notna(fitness) and np.isfinite(fitness):
                        fitness_values.append(float(fitness))
                else:
                    log_record.update({"status": "failed", "error_message": "Backtest returned invalid result."})
            except Exception as e:
                log_record.update({"status": "failed", "error_message": str(e)})
            finally:
                del df_data  # Free memory
                gc.collect()  # Force garbage collection

            ga_instance.log_queue.put(log_record)

        if not fitness_values:
            logger.warning(f"No valid backtests completed for solution {solution_idx}.")
            return worst_fitness
        average_fitness = np.mean(fitness_values)
        return average_fitness if np.isfinite(average_fitness) else worst_fitness

    except Exception as e:
        logger.debug(f"CRITICAL ERROR in worker PID {os.getpid()}: {e}")
        return worst_fitness

# --- PyGAD Callbacks (Unchanged) ---
def on_generation(ga_instance):
    generation = ga_instance.generations_completed
    if not hasattr(ga_instance, 'best_solutions_fitness') or not ga_instance.best_solutions_fitness:
        logger.warning(f"--- Generation {generation} Finished --- No valid solutions found yet.")
        return
    try:
        best_fitness = ga_instance.best_solutions_fitness[-1]
        avg_fitness_list = [f for f in ga_instance.last_generation_fitness if np.isfinite(f)]
        avg_fitness = np.mean(avg_fitness_list) if avg_fitness_list else 'N/A'
        avg_fitness_str = f"{avg_fitness:.6f}" if isinstance(avg_fitness, float) else avg_fitness
        logger.info(f"--- Generation {generation} Finished --- Best Fitness: {best_fitness:.6f} | Avg Fitness: {avg_fitness_str}")
        
        if generation > 0 and (generation % 5 == 0 or generation == ga_instance.num_generations):
            if ga_instance.best_solutions:
                best_solution = ga_instance.best_solutions[-1]
                best_params_dict = {p['name']: p['type'](float(best_solution[i]) if p['type'] in [float, 'float'] else int(round(best_solution[i]))) for i, p in enumerate(OPTIMIZABLE_PARAMETERS)}
                logger.info(f"Best Solution Parameters @ Gen {generation}:\n{json.dumps(best_params_dict, indent=2)}")
    except Exception as e:
        logger.error(f"Error in on_generation callback: {e}", exc_info=True)

# --- Final Evaluation Helper (Unchanged) ---
async def evaluate_solution(parameters: Dict, data_set_key: str, initial_capital: float, cache_for_eval: Optional[Dict] = None):
    logger.warning(f"Evaluation on '{data_set_key}' set is a placeholder. Full implementation should load from cache.")
    return {"data_set": data_set_key, "status": "placeholder"}

# --- Main Logic ---
async def main_async_logic(log_queue, shared_cache):
    setup_logging(logger_name="ga_optimizer_module")
    try:
        date_str = f"{HISTORICAL_DATA_START_TS.strftime('%Y%m%d')}_{HISTORICAL_DATA_END_TS.strftime('%Y%m%d')}"
        cache_dir = os.path.join(GA_CACHE_PATH, date_str)
        if not os.path.isdir(cache_dir):
            logger.critical(f"Cache directory not found: '{cache_dir}'")
            logger.critical("Please run 'python ga_optimizer_module/prepare_ga_dataset.py' to generate the required data cache.")
            return

        logger.info(f"Using pre-computed dataset from: {cache_dir}")
        
        optimization_run_id = str(uuid.uuid4())
        logger.info(f"Starting Optimization Run ID: {optimization_run_id}")
        
        # Validate OPTIMIZABLE_PARAMETERS
        for param in OPTIMIZABLE_PARAMETERS:
            param_name = param.get('name', 'Unnamed')
            param_type = param.get('type', float)
            if 'values' not in param and ('low' not in param or 'high' not in param):
                logger.error(f"Parameter {param_name} is missing 'values' or both 'low' and 'high'. Configuration: {param}")
                raise ValueError(f"Invalid parameter configuration for {param_name}")
            if param_type not in [float, int, bool, 'float', 'int', 'bool']:
                logger.error(f"Parameter {param_name} has invalid type '{param_type}'. Must be float, int, bool, 'float', 'int', or 'bool'. Configuration: {param}")
                raise ValueError(f"Invalid parameter type for {param_name}")

        gene_space = [{'low': p['low'], 'high': p['high']} if 'low' in p else p['values'] for p in OPTIMIZABLE_PARAMETERS]
        num_processes = os.cpu_count() - 2 if MULTIPROCESSING_CORES == "auto" and os.cpu_count() and os.cpu_count() > 2 else int(MULTIPROCESSING_CORES)
        
        # --- Population Seeding Logic ---
        logger.info("Building a seeded initial population...")
        initial_population = []
        
        seed_solution = []
        for param in OPTIMIZABLE_PARAMETERS:
            param_name = param['name']
            if hasattr(bot_config, param_name):
                value = getattr(bot_config, param_name)
                if isinstance(value, tuple) and len(value) == 1: value = value[0]
                if isinstance(value, bool): value = int(value)
                seed_solution.append(value)
            else:
                if 'values' in param:
                    seed_solution.append(param['values'][len(param['values']) // 2])
                else:
                    seed_solution.append((param.get('low', 0) + param.get('high', 0)) / 2)
        initial_population.append(seed_solution)

        num_to_generate = POPULATION_SIZE - 1
        for i in range(num_to_generate):
            new_solution = list(seed_solution)
            num_mutations = max(1, int(len(new_solution) * 0.20))
            for _ in range(num_mutations):
                gene_idx = random.randrange(len(new_solution))
                param_space = OPTIMIZABLE_PARAMETERS[gene_idx]
                if 'values' in param_space:
                    new_gene = random.choice(param_space['values'])
                else:
                    low, high = param_space.get('low', 0), param_space.get('high', 1)
                    new_gene = random.uniform(low, high)
                new_solution[gene_idx] = param_space['type'](new_gene)
            initial_population.append(new_solution)
        logger.info(f"Seeded population of {len(initial_population)} individuals created.")
        
        ga_instance = pygad.GA(
            num_generations=NUM_GENERATIONS, 
            num_parents_mating=max(2, int(POPULATION_SIZE * 0.3)), 
            fitness_func=fitness_func_main_process, 
            sol_per_pop=POPULATION_SIZE, 
            num_genes=len(OPTIMIZABLE_PARAMETERS), 
            initial_population=initial_population,
            gene_space=gene_space, 
            parent_selection_type=PARENT_SELECTION_TYPE, 
            crossover_type=CROSSOVER_TYPE, 
            crossover_probability=CROSSOVER_PROBABILITY, 
            mutation_type=MUTATION_TYPE, 
            mutation_probability=MUTATION_PROBABILITY, 
            keep_elitism=max(0, KEEP_ELITISM), 
            on_generation=on_generation, 
            parallel_processing=['process', num_processes], 
            stop_criteria=STOP_CRITERIA
        )
        
        ga_instance.log_queue = log_queue
        ga_instance.indicator_cache = shared_cache
        ga_instance.run_id = optimization_run_id

        logger.info(f"--- Starting GA Optimization ({num_processes} processes) ---")
        start_time = time.time()
        ga_instance.run()
        logger.info(f"--- GA Optimization Finished (Duration: {(time.time() - start_time)/60:.2f} minutes) ---")
        
        # --- Save Best Solution to JSON ---
        if hasattr(ga_instance, 'best_solution_generation') and ga_instance.best_solution_generation != -1:
            solution, solution_fitness, solution_idx = ga_instance.best_solution()
            
            logger.info(f"Best solution found at generation {ga_instance.best_solution_generation} with fitness: {solution_fitness}")
            
            best_params_dict = {
                p['name']: p['type'](float(solution[i]) if p['type'] in [float, 'float'] else int(round(solution[i])))
                for i, p in enumerate(OPTIMIZABLE_PARAMETERS)
            }
            
            # Construct the final JSON object
            results_to_save = {
                "best_solution_id": f"gen{ga_instance.best_solution_generation}_idx{solution_idx}",
                "best_solution_parameters": best_params_dict,
                "best_solution_fitness_training": solution_fitness,
                "validation_metrics": {"status": "not_run"},
                "test_metrics": {"status": "not_run"}
            }
            
            # Generate filename and save
            date_today_str = datetime.now().strftime("%Y%m%d")
            filename = f"ga_results_{date_today_str}_{optimization_run_id}.json"
            output_path = os.path.join(RESULTS_DIR, filename)
            
            try:
                with open(output_path, 'w') as f:
                    json.dump(results_to_save, f, indent=4, cls=NpEncoder)
                logger.info(f"✅ Successfully saved best parameters to {output_path}")
            except Exception as e:
                logger.error(f"Failed to save best parameters to JSON: {e}", exc_info=True)
        else:
            logger.warning("No best solution was found or recorded by the GA instance. Skipping JSON export.")

    except Exception as e:
        logger.critical(f"A critical error occurred in main_async_logic: {e}", exc_info=True)
    finally:
        logger.info("Optimizer async logic finished.")

# --- Entry Point (Unchanged) ---
if __name__ == "__main__":
    freeze_support()
    with Manager() as manager:
        log_queue = manager.Queue()
        shared_cache = manager.dict() # Indicator cache can still be shared
        
        os.makedirs(RESULTS_DIR, exist_ok=True)
        log_file_path = os.path.join(RESULTS_DIR, DETAILED_LOG_FILENAME)
        
        log_process = Process(target=log_writer_process, args=(log_queue, log_file_path))
        log_process.start()
        
        try:
            asyncio.run(main_async_logic(log_queue, shared_cache))
        finally:
            logger.info("Main logic finished. Shutting down logger process...")
            log_queue.put(None); log_process.join()
            logger.info("Logger process has been shut down.")

        logger.info("--- Starting Automatic Database Ingestion ---")
        try:
            if os.path.exists(log_file_path): 
                asyncio.run(run_ingestion(log_file_path))
                logger.info("--- Database Ingestion Completed Successfully ---")
        except Exception as e:
            logger.error(f"DB ingestion failed: {e}", exc_info=True)
        logger.info("Open GA Dashboard with: 'streamlit run ga_optimizer_module/ga_dashboard.py'")
```

#### 📄 `ga_prepare_dataset.py`
*path: `ga_optimizer_module/ga_prepare_dataset.py`*

```python
# ga_optimizer_module/prepare_ga_dataset.py
"""
Standalone ETL script for preparing the Genetic Algorithm backtesting dataset.

This script connects to the database ONCE, runs the expensive historical data
query to get resampled and feature-enriched data, and then saves the final
DataFrames into a local, versioned Parquet cache.

This decouples heavy data processing from the optimization run, allowing the
optimizer's worker processes to start quickly by loading pre-computed data.

Usage:
    python ga_optimizer_module/prepare_ga_dataset.py --start-date 2025-09-20 --end-date 2025-10-12
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
import pandas as pd
from tqdm import tqdm

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from config.ga_config import HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS
from utils import load_and_split_data

# --- DEFINE THE CACHE PATH ---
GA_CACHE_PATH = os.path.join(project_root, "data", "ga_cache")


async def run_ga_etl(start_date: datetime, end_date: datetime, force_rebuild: bool = False):
    """Main ETL orchestration function for the GA dataset."""
    logger.info("--- Starting GA Dataset ETL ---")
    
    date_str = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    output_dir = os.path.join(GA_CACHE_PATH, date_str)

    if os.path.exists(output_dir) and not force_rebuild:
        logger.info(f"✅ Cache directory '{output_dir}' already exists. ETL skipped.")
        logger.info("Use --force to rebuild the cache.")
        return

    if force_rebuild:
        logger.warning(f"Force rebuild enabled. Deleting existing cache at '{output_dir}' if it exists.")
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output cache directory: {output_dir}")

    db_client = None
    try:
        db_client = DatabaseClient()
        await db_client.connect()

        logger.info("Fetching and splitting data from database... This may take a long time.")
        
        # --- THIS IS THE FIX ---
        # Changed the keyword argument `data_split_ratios=None` to a positional argument `None`.
        loaded_results = await load_and_split_data(db_client, start_date, end_date, None)
        # --- END OF FIX ---

        if loaded_results is None:
            logger.error("Failed to load or split data. Aborting ETL.")
            return

        all_data, token_lifespans, dexscreener_snapshots = loaded_results
        
        all_data_dir = os.path.join(output_dir, "ohlcv_data")
        os.makedirs(all_data_dir, exist_ok=True)
        logger.info(f"Saving {len(all_data)} tokens to Parquet cache...")
        for mint, df in tqdm(all_data.items(), desc="Saving OHLCV data"):
            if not df.empty:
                df.to_parquet(os.path.join(all_data_dir, f"{mint}.parquet"))

        lifespans_df = pd.DataFrame.from_dict(token_lifespans, orient='index')
        lifespans_df.index.name = 'mint'
        lifespans_df.to_parquet(os.path.join(output_dir, "token_lifespans.parquet"))
        logger.info(f"Saved lifespans for {len(token_lifespans)} tokens.")

        snapshots_dir = os.path.join(output_dir, "dexscreener_snapshots")
        os.makedirs(snapshots_dir, exist_ok=True)
        if dexscreener_snapshots:
            logger.info(f"Saving DexScreener snapshots for {len(dexscreener_snapshots)} tokens...")
            for mint, df in tqdm(dexscreener_snapshots.items(), desc="Saving snapshots"):
                 if not df.empty:
                    df.to_parquet(os.path.join(snapshots_dir, f"{mint}.parquet"))
        else:
            logger.info("No DexScreener snapshots to save.")

        logger.info("✅ ETL process completed successfully. Data is cached.")

    except Exception as e:
        logger.error(f"ETL process failed: {e}", exc_info=True)
    finally:
        if db_client:
            await db_client.close()

if __name__ == "__main__":
    setup_logging(logger_name="ga_etl")
    parser = argparse.ArgumentParser(description="Run the ETL pipeline for GA dataset generation.")
    
    # Use defaults from ga_config.py
    default_start_str = HISTORICAL_DATA_START_TS.isoformat()
    default_end_str = HISTORICAL_DATA_END_TS.isoformat()

    parser.add_argument("--start-date", type=str, default=default_start_str, help=f"Start date in ISO format (default: {default_start_str}).")
    parser.add_argument("--end-date", type=str, default=default_end_str, help=f"End date in ISO format (default: {default_end_str}).")
    parser.add_argument("--force", action="store_true", help="Force a rebuild of the cache if it already exists.")
    args = parser.parse_args()

    start_dt = datetime.fromisoformat(args.start_date.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(args.end_date.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)

    asyncio.run(run_ga_etl(start_date=start_dt, end_date=end_dt, force_rebuild=args.force))
```

#### 📄 `generate_chart.py`
*path: `generate_chart.py`*

```python
"""
Pump.fun Trader - Advanced Charting Dashboard

This script launches a Dash web application to visualize trading data
for tokens in the active portfolio. It connects to the bot's PostgreSQL database,
fetches token data, generates OHLCV candles for all tokens, calculates indicators,
and displays an interactive, multi-paned chart that accurately reflects the bot's trading logic.

This script is designed to be run from the root of your project directory.
"""
import os
from dotenv import load_dotenv
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from psycopg2.extras import DictCursor

# --- Load Environment Variables ---
load_dotenv()

# --- Project-Specific Imports ---
try:
    from bot_logger import logger, setup_logging
    from database_handler import DatabaseClient
    from config.config import (
        RSI_PERIOD, TREND_REVERSAL_RSI_NEUTRAL_LEVEL, ADAPTIVE_RSI_STRONG_LEVEL, ADAPTIVE_RSI_EXTREME_LEVEL,
        BBANDS_PERIOD, BBANDS_STD_DEV,
        FAST_EMA_PERIOD, SLOW_EMA_PERIOD, ADAPTIVE_ATR_PERIOD,
        MIN_CANDLE_DATA_FOR_INDICATORS
    )
    from utils import calculate_trend_indicators
except ImportError as e:
    print(f"Error: Could not import necessary modules. {e}")
    print("Please ensure this script is run from the root directory of the pump_trader project.")
    exit(1)

# --- Logger and DB Client Initialization ---
setup_logging()
db_client = DatabaseClient()
db_pool = db_client.get_sync_connection_pool()


# --- Database & Data Functions ---

def get_active_portfolio_tokens():
    """Fetches a list of unique tokens currently active in the portfolio."""
    query = """
    SELECT DISTINCT
        p.mint AS token_address,
        COALESCE(t.symbol, t.name, p.mint) AS token_symbol,
        p.mint
    FROM portfolio p
    LEFT JOIN tokens t ON p.mint = t.mint
    WHERE p.status = 'active'
    ORDER BY token_symbol;
    """
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query)
            tokens = cursor.fetchall()
            return [dict(t) for t in tokens]
    except Exception as e:
        logger.error(f"Error fetching active portfolio tokens: {e}", exc_info=True)
        return []
    finally:
        if conn:
            db_pool.putconn(conn)

def get_all_trades_for_token(token_address):
    """Fetches all buy and sell transactions for a token from the portfolio table."""
    query = "SELECT timestamp, price AS price_sol, tx_type AS trade_type FROM portfolio WHERE mint = %s ORDER BY timestamp;"
    conn = None
    try:
        conn = db_pool.getconn()
        df = pd.read_sql_query(query, conn, params=(token_address,))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price_sol'] = pd.to_numeric(df['price_sol'], errors='coerce')
        return df
    except Exception as e:
        logger.error(f"Error fetching portfolio trades for {token_address}: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn:
            db_pool.putconn(conn)

def check_if_migrated(token_address):
    """Checks if a token's data_source is 'DEXSCREENER'."""
    query = "SELECT data_source FROM tokens WHERE mint = %s LIMIT 1"
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, (token_address,))
            result = cursor.fetchone()
            return result and result['data_source'] == 'DEXSCREENER'
    except Exception as e:
        logger.error(f"Error checking migration status for {token_address}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            db_pool.putconn(conn)

def get_trade_ticks(token_address, is_migrated):
    """Fetches raw trade ticks from the appropriate source."""
    if is_migrated:
        query = "SELECT timestamp, price_native AS price, (volume_m5 / sol_price_usd) AS volume FROM dexscreener_data WHERE mint_address = %s AND sol_price_usd > 0 ORDER BY timestamp"
    else:
        query = "SELECT timestamp, price, sol_amount as volume FROM trades WHERE mint = %s ORDER BY timestamp"
    
    conn = None
    try:
        conn = db_pool.getconn()
        df = pd.read_sql_query(query, conn, params=(token_address,))
        if df.empty: return pd.DataFrame()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df.dropna(subset=['price', 'volume'], inplace=True)
        return df
    except Exception as e:
        logger.error(f"Error fetching trade ticks for {token_address}: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn:
            db_pool.putconn(conn)

def generate_ohlcv_from_ticks(df_ticks, timeframe='1Min'):
    """Generates an OHLCV DataFrame from a tick data DataFrame."""
    if df_ticks.empty or 'price' not in df_ticks.columns:
        return pd.DataFrame()
    df_ticks = df_ticks.set_index('timestamp')
    ohlc = df_ticks['price'].resample(timeframe).ohlc()
    volume = df_ticks['volume'].resample(timeframe).sum()
    df_ohlcv = pd.concat([ohlc, volume], axis=1)
    df_ohlcv.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    df_ohlcv.reset_index(inplace=True)
    df_ohlcv.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
    return df_ohlcv

# --- Dash App Layout ---
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
app.title = "Pump.fun Trader Dashboard"
app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#AAAAAA'}, children=[
    dcc.Store(id='selected-token-store', data=None),
    dcc.Interval(id='token-list-interval', interval=30 * 1000, n_intervals=0),
    html.Div([html.H1('Pump.fun Trader - Chart Analysis', style={'textAlign': 'center', 'color': '#FFFFFF', 'margin': '20px'})]),
    html.Div(className='row', style={'margin': '10px'}, children=[
        html.Div(className='three columns', style={'padding': '10px', 'backgroundColor': '#1E1E1E', 'borderRadius': '5px'}, children=[
            html.H4('Active Portfolio', style={'color': '#FFFFFF', 'borderBottom': '1px solid #444444', 'paddingBottom': '10px'}),
            dcc.RadioItems(id='token-list', options=[], value=None, labelStyle={'display': 'block', 'padding': '5px', 'cursor': 'pointer', 'borderBottom': '1px solid #333333'}, style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #444444', 'borderRadius': '5px'}),
            html.H4('Indicator Settings', style={'color': '#FFFFFF', 'marginTop': '30px', 'borderBottom': '1px solid #444444', 'paddingBottom': '10px'}),
            html.Div(id='indicator-settings-display', style={'fontSize': '12px', 'lineHeight': '1.6', 'wordBreak': 'break-all'})
        ]),
        html.Div(className='nine columns', children=[dcc.Graph(id='main-chart', figure={}, config={'responsive': True}, style={'height': '80vh'})])
    ])
])

# --- Callbacks ---
@app.callback(
    [Output('token-list', 'options'), Output('token-list', 'value'), Output('selected-token-store', 'data')],
    Input('token-list-interval', 'n_intervals'),
    State('selected-token-store', 'data')
)
def update_token_list(n_intervals, stored_token_address):
    logger.info("Refreshing active token list...")
    tokens = get_active_portfolio_tokens()
    if not tokens:
        logger.info("No active tokens found.")
        return [], None, None
    options = [{'label': f"{t.get('token_symbol', '???')} ({t.get('mint')})", 'value': t['token_address']} for t in tokens]
    active_addresses = [t['token_address'] for t in tokens]
    new_selected_value = stored_token_address if stored_token_address and stored_token_address in active_addresses else (options[0]['value'] if options else None)
    return options, new_selected_value, new_selected_value

@app.callback(
    Output('selected-token-store', 'data', allow_duplicate=True),
    Input('token-list', 'value'),
    prevent_initial_call=True
)
def store_selected_token(selected_token_address):
    return selected_token_address

@app.callback(
    [Output('main-chart', 'figure'), Output('indicator-settings-display', 'children')],
    Input('selected-token-store', 'data')
)
def update_chart(selected_token_address):
    if not selected_token_address:
        return go.Figure().update_layout(title="Please select a token", template='plotly_dark'), "Select a token."

    logger.info(f"Generating chart for token: {selected_token_address}")
    
    config_params = {
        'RSI_PERIOD': RSI_PERIOD, 'BBANDS_PERIOD': BBANDS_PERIOD, 'BBANDS_STD_DEV': BBANDS_STD_DEV,
        'FAST_EMA_PERIOD': FAST_EMA_PERIOD, 'SLOW_EMA_PERIOD': SLOW_EMA_PERIOD,
        'ADAPTIVE_ATR_PERIOD': ADAPTIVE_ATR_PERIOD, 'MIN_CANDLE_DATA_FOR_INDICATORS': MIN_CANDLE_DATA_FOR_INDICATORS
    }
    
    settings_display = [
        html.P(f"Token: {selected_token_address}", style={'color': '#FFFFFF', 'fontWeight': 'bold'}),
        html.H5("Trend Reversal (Buy)", style={'color': '#4682B4', 'marginTop': '10px'}),
        html.P(f"BBands: ({BBANDS_PERIOD}, {BBANDS_STD_DEV})"),
        html.P(f"EMA Cross: ({FAST_EMA_PERIOD}, {SLOW_EMA_PERIOD})"),
        html.P("VWAP (if calculated)"),
        html.H5("Dynamic Selling & Logic", style={'color': '#FFD700', 'marginTop': '10px'}),
        html.P(f"EMA Cross: ({FAST_EMA_PERIOD}, {SLOW_EMA_PERIOD})"),
        html.P(f"RSI-Adaptive ATR: ({ADAPTIVE_ATR_PERIOD})"),
        html.P(f"RSI Levels (Neutral/Strong/Extreme): {TREND_REVERSAL_RSI_NEUTRAL_LEVEL} / {ADAPTIVE_RSI_STRONG_LEVEL} / {ADAPTIVE_RSI_EXTREME_LEVEL}")
    ]
    
    is_migrated = check_if_migrated(selected_token_address)
    df_ticks = get_trade_ticks(selected_token_address, is_migrated)
    
    if df_ticks.empty:
        return go.Figure().update_layout(title=f"No trade data found for token: {selected_token_address}", template='plotly_dark'), settings_display

    df_ohlcv = generate_ohlcv_from_ticks(df_ticks, timeframe='1Min')
    df_indicators = calculate_trend_indicators(df_ohlcv.copy(), config_params)
    df_trades = get_all_trades_for_token(selected_token_address)

    chart_title = "Price & Trend Indicators"
    if not is_migrated:
        chart_title += " (Pre-Migration)"
    
    fig = build_unified_chart(df_indicators if not df_indicators.empty else df_ohlcv, df_trades, config_params, selected_token_address, chart_title)
        
    return fig, settings_display

def build_unified_chart(df, df_trades, settings, token_address, chart_title):
    """Builds a unified, multi-pane chart for any token with OHLCV data."""
    row_config, row_heights, subplot_titles = {'main': 1}, [0.6], [chart_title]
    rows_total = 1
    
    if 'Volume' in df.columns and not df['Volume'].empty:
        rows_total += 1; row_config['volume'] = rows_total; row_heights.append(0.1); subplot_titles.append("Volume")
    
    rsi_col = f'RSI_{settings["RSI_PERIOD"]}'
    if rsi_col in df.columns:
        rows_total += 1; row_config['rsi'] = rows_total; row_heights.append(0.15); subplot_titles.append("RSI")
        
    atr_col = f'ATRr_{settings["ADAPTIVE_ATR_PERIOD"]}'
    if atr_col in df.columns:
        rows_total += 1; row_config['atr'] = rows_total; row_heights.append(0.15); subplot_titles.append("ATR (for Dynamic Sell Logic)")
        
    fig = make_subplots(rows=rows_total, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights, subplot_titles=subplot_titles)
    
    main_row = row_config['main']
    fig.add_trace(go.Candlestick(x=df['timestamp'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Candles'), row=main_row, col=1)
    
    bb_lower_col = f'BBL_{settings["BBANDS_PERIOD"]}_{settings["BBANDS_STD_DEV"]}'
    bb_upper_col = f'BBU_{settings["BBANDS_PERIOD"]}_{settings["BBANDS_STD_DEV"]}'
    if bb_lower_col in df.columns and bb_upper_col in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[bb_upper_col], name='BB Upper', line=dict(color='rgba(100, 100, 255, 0.4)', width=1)), row=main_row, col=1)
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[bb_lower_col], name='BB Lower', line=dict(color='rgba(100, 100, 255, 0.4)', width=1), fill='tonexty', fillcolor='rgba(100, 100, 255, 0.05)'), row=main_row, col=1)
    
    if 'EMA_fast' in df.columns: fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_fast'], name=f'EMA {settings["FAST_EMA_PERIOD"]}', line=dict(color='aqua', width=1.5)), row=main_row, col=1)
    if 'EMA_slow' in df.columns: fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_slow'], name=f'EMA {settings["SLOW_EMA_PERIOD"]}', line=dict(color='magenta', width=1.5)), row=main_row, col=1)
    if 'VWAP' in df.columns: fig.add_trace(go.Scatter(x=df['timestamp'], y=df['VWAP'], name='VWAP', line=dict(color='orange', width=1, dash='dot')), row=main_row, col=1)

    if not df_trades.empty:
        buys, sells = df_trades[df_trades['trade_type'] == 'buy'], df_trades[df_trades['trade_type'] == 'sell']
        fig.add_trace(go.Scatter(x=buys['timestamp'], y=buys['price_sol'], name='Buys', mode='markers', marker=dict(color='lime', symbol='triangle-up', size=10, line=dict(width=1, color='DarkGreen'))), row=main_row, col=1)
        fig.add_trace(go.Scatter(x=sells['timestamp'], y=sells['price_sol'], name='Sells', mode='markers', marker=dict(color='red', symbol='triangle-down', size=10, line=dict(width=1, color='DarkRed'))), row=main_row, col=1)
    
    if 'volume' in row_config:
        fig.add_trace(go.Bar(x=df['timestamp'], y=df['Volume'], name='Volume', marker=dict(color='rgba(255, 255, 255, 0.5)')), row=row_config['volume'], col=1)
    
    if 'rsi' in row_config:
        rs_row = row_config['rsi']
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[rsi_col], name='RSI', line=dict(color='cyan')), row=rs_row, col=1)
        fig.add_hline(y=ADAPTIVE_RSI_EXTREME_LEVEL, line=dict(color='red', dash='dot', width=1), annotation_text="Extreme", annotation_position="bottom right", row=rs_row, col=1)
        fig.add_hline(y=ADAPTIVE_RSI_STRONG_LEVEL, line=dict(color='orange', dash='dot', width=1), annotation_text="Strong", annotation_position="bottom right", row=rs_row, col=1)
        fig.add_hline(y=TREND_REVERSAL_RSI_NEUTRAL_LEVEL, line=dict(color='green', dash='dot', width=1), annotation_text="Neutral", annotation_position="bottom right", row=rs_row, col=1)
        fig.update_yaxes(range=[0, 100], row=rs_row, col=1)
    
    if 'atr' in row_config:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[atr_col], name='ATR', line=dict(color='goldenrod')), row=row_config['atr'], col=1)

    fig.update_layout(title_text=f"Chart for {token_address}", xaxis_rangeslider_visible=False, template='plotly_dark', height=850, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    for i in range(1, rows_total + 1): fig.update_yaxes(autorange=True, fixedrange=False, row=i, col=1)
    if rows_total > 1: fig.update_xaxes(showticklabels=False, row=1, col=1)
    return fig

# --- Run the App ---
if __name__ == '__main__':
    logger.info("Starting Dash server on http://127.0.0.1:8050")
    app.run(debug=True, port=8050)
```

#### 📄 `__log-files_`
*path: `log/__log-files_`*

_This file is empty._

#### 📄 `main.py`
*path: `main.py`*

```python
import argparse
import asyncio
import os
import sys
import subprocess
import time
import json
from datetime import datetime, timezone
from bot_logger import setup_logging, rotate_log_file, log_info, log_debug, log_error, log_warning, log_critical
from config.config import TELEGRAM_INTERACTION

# --- Project Setup ---
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = CURRENT_SCRIPT_DIR  # Assuming main.py is in the project root

# --- File Paths ---
DATA_DIR = os.path.join(PROJECT_ROOT_DIR, 'data')
STATUS_FILE = os.path.join(DATA_DIR, 'bot_status.json')
COMMAND_FILE = os.path.join(DATA_DIR, 'bot_command.txt')
TELEGRAM_SCRIPT_PATH = os.path.join(PROJECT_ROOT_DIR, 'telegram_interface.py')
TRADING_BOT_SCRIPT_PATH = os.path.join(PROJECT_ROOT_DIR, 'trading_bot.py')

# --- Configuration ---
BOT_INITIAL_WARMUP_SECONDS = 60  # Wait this long after starting the bot before the first check
BOT_CHECK_INTERVAL_SECONDS = 15  # How often to check if the TradingBot is running after warmup
PYTHON_EXECUTABLE = sys.executable
MAX_RESTART_ATTEMPTS = 5 # Maximum number of consecutive restart attempts before giving up for a while
RESTART_COOLDOWN_SECONDS = 300 # Wait this long after max restart attempts
# --- NEW: Timeout for graceful shutdown ---
GRACEFUL_SHUTDOWN_TIMEOUT = 45

# --- Helper Functions ---
def is_process_running(process_handle):
    """Checks if the given subprocess.Popen handle is still running."""
    if process_handle is None:
        return False
    return process_handle.poll() is None

# --- NEW: IPC helper function to send commands to the bot ---
def write_bot_command(command: str):
    """Writes a command to the shared command file for the bot to process."""
    try:
        with open(COMMAND_FILE, 'w', encoding='utf-8') as f:
            f.write(command)
        log_info(f"Controller sent command to bot: '{command}'")
        return True
    except IOError as e:
        log_error(f":police_car_light: Controller error writing command file: {e}")
        return False

def get_trading_bot_status_from_file() -> str:
    """
    Reads the TradingBot status from the bot_status.json file with a retry mechanism.
    Returns 'RUNNING', 'STARTING', 'STOPPED', 'STALE', or 'ERROR_READING_STATUS'.
    """
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if not os.path.exists(STATUS_FILE):
                return "STOPPED"
            with open(STATUS_FILE, 'r') as f:
                # If file is empty, wait and retry
                if os.fstat(f.fileno()).st_size == 0:
                    raise json.JSONDecodeError("File is empty", "", 0)
                status_data = json.load(f)

            bot_process_status = status_data.get("bot_process_status", "UNKNOWN").upper()
            timestamp_str = status_data.get("timestamp")

            if not timestamp_str:
                return "STALE" if bot_process_status == "RUNNING" else bot_process_status

            status_dt = datetime.fromisoformat(timestamp_str)
            if status_dt.tzinfo is None:
                status_dt = status_dt.replace(tzinfo=timezone.utc)
            else:
                status_dt = status_dt.astimezone(timezone.utc)

            age_seconds = (datetime.now(timezone.utc) - status_dt).total_seconds()

            stale_threshold = BOT_CHECK_INTERVAL_SECONDS * 2.5
            if bot_process_status in ["RUNNING", "STARTING"] and age_seconds > stale_threshold:
                log_warning(f"Status file is STALE. Status: {bot_process_status}, Age: {age_seconds:.2f}s, Threshold: {stale_threshold}s")
                return "STALE"
            
            if bot_process_status in ["RUNNING", "STARTING"]:
                return bot_process_status
            
            return "STOPPED"

        except json.JSONDecodeError as e:
            log_warning(f"Attempt {attempt + 1}/{max_attempts} failed to read bot_status.json: {e}. Retrying in 1 second...")
            if attempt < max_attempts - 1:
                time.sleep(1) # Wait before the next attempt
            else:
                log_error(f":police_car_light: Error reading bot_status.json after {max_attempts} attempts: {e}")
                return "ERROR_READING_STATUS"
        except (IOError, ValueError) as e:
            log_error(f":police_car_light: Error reading bot_status.json: {e}")
            return "ERROR_READING_STATUS"
        except Exception as e:
            log_error(f":police_car_light: Unexpected error in get_trading_bot_status_from_file: {e}")
            return "ERROR_READING_STATUS"
    return "ERROR_READING_STATUS" # Should not be reached, but as a fallback

def start_script_in_new_console(script_path: str, cwd: str, args: list = None) -> subprocess.Popen:
    """Starts a Python script in a new console window."""
    if not os.path.exists(script_path):
        log_error(f"Script not found: {script_path}")
        raise FileNotFoundError(f"Script not found: {script_path}")

    command = [PYTHON_EXECUTABLE, script_path]
    if args:
        command.extend(args)

    log_info(f"Starting script: {' '.join(command)} in CWD: {cwd}")
    creation_flags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    try:
        process = subprocess.Popen(command, cwd=cwd, creationflags=creation_flags)
        log_info(f"Successfully started {os.path.basename(script_path)} with PID: {process.pid}")
        return process
    except Exception as e:
        log_error(f"Failed to Popen {os.path.basename(script_path)}: {e}")
        return None

# --- MODIFICATION: The role of this function is now a fallback ---
async def ensure_process_terminated(process_handle: subprocess.Popen, process_name: str):
    """Forcefully terminates a process that did not shut down gracefully."""
    if process_handle and is_process_running(process_handle):
        log_warning(f"Graceful shutdown failed for {process_name}. Forcefully terminating process (PID: {process_handle.pid})...")
        process_handle.terminate()
        try:
            # wait() is blocking, so we use a loop with sleep in async context
            for _ in range(10): # ~10 seconds
                if not is_process_running(process_handle): break
                await asyncio.sleep(1)
            else: # If loop finishes without break
                log_warning(f"{process_name} did not terminate gracefully, killing (PID: {process_handle.pid}).")
                process_handle.kill()
        except Exception as e:
            log_error(f":police_car_light: Error during forceful termination of {process_name}: {e}")

# --- NEW: Function to request a graceful shutdown from the trading bot ---
async def request_graceful_shutdown(process_handle: subprocess.Popen, process_name: str):
    """Sends a STOP command to the bot and waits for it to terminate."""
    if not process_handle or not is_process_running(process_handle):
        log_debug(f"Process {process_name} is not running, no shutdown needed.")
        return

    log_info(f"Requesting graceful shutdown for {process_name} (PID: {process_handle.pid})...")
    # Send the STOP command via the file IPC mechanism
    if not write_bot_command("STOP"):
        log_error(f"Failed to send STOP command to {process_name}. Proceeding with forceful termination.")
        await ensure_process_terminated(process_handle, process_name)
        return

    # Wait for the process to terminate
    try:
        # In an async context, we poll instead of using wait()
        shutdown_start_time = time.monotonic()
        while time.monotonic() - shutdown_start_time < GRACEFUL_SHUTDOWN_TIMEOUT:
            if not is_process_running(process_handle):
                log_info(f"✅ {process_name} shut down gracefully.")
                return
            await asyncio.sleep(1)

        # If the loop finishes, the timeout was reached
        log_warning(f"Timeout ({GRACEFUL_SHUTDOWN_TIMEOUT}s) reached while waiting for {process_name} to shut down gracefully.")
        await ensure_process_terminated(process_handle, process_name)

    except Exception as e:
        log_error(f":police_car_light: Error during graceful shutdown for {process_name}: {e}", exc_info=True)
        await ensure_process_terminated(process_handle, process_name)



async def main_controller(args):
    setup_logging()
    # Perform log rotation when the main controller starts
    log_info("Main controller performing initial log rotation.")
    rotate_log_file()
    # setup_logging() will be called again inside rotate_log_file, which is fine.
    log_info("--- Main Controller Started ---")

    trading_bot_process = None
    telegram_interface_process = None
    restart_attempts = 0

    try:
        # 1. Start the Telegram Interface
        try:
            log_info("Attempting to start Telegram Interface...")
            if TELEGRAM_INTERACTION:
                telegram_interface_process = start_script_in_new_console(TELEGRAM_SCRIPT_PATH, PROJECT_ROOT_DIR)
                if not telegram_interface_process:
                    log_warning("Failed to start Telegram Interface, but controller will continue.")
        except Exception as e:
            log_error(f":police_car_light: Error during Telegram Interface startup: {e}")

        # Function to start the trading bot
        async def start_trading_bot(pass_args):
            nonlocal trading_bot_process # To modify the outer scope variable
            await ensure_process_terminated(trading_bot_process, "Trading Bot") # Ensure old instance is gone
            log_info("Attempting to start Trading Bot...")
            trading_bot_process = start_script_in_new_console(TRADING_BOT_SCRIPT_PATH, PROJECT_ROOT_DIR, pass_args)
            if trading_bot_process:
                log_info(f"Trading Bot started. Waiting {BOT_INITIAL_WARMUP_SECONDS}s for warmup...")
                await asyncio.sleep(BOT_INITIAL_WARMUP_SECONDS)
                return True
            else:
                log_error("Failed to start Trading Bot process.")
                return False

        # 2. Initial Trading Bot Start
        trading_bot_cli_args = []
        if args.cleanup: trading_bot_cli_args.append("--cleanup")
        if args.backup: trading_bot_cli_args.append("--backup")
        if args.params_file: trading_bot_cli_args.extend(["--params-file", args.params_file])
        if args.rl_agent_path: trading_bot_cli_args.extend(["--rl-agent-path", args.rl_agent_path])
        
        # Add the --no-log-rotate flag when starting from the controller
        trading_bot_cli_args.append("--no-log-rotate")
        
        if not await start_trading_bot(trading_bot_cli_args):
            log_critical("Trading Bot could not be started initially. Exiting controller.")
            return

        # 3. Monitor the Trading Bot
        while True:
            await asyncio.sleep(BOT_CHECK_INTERVAL_SECONDS)
            bot_needs_restart = False

            # Check 1: Subprocess handle
            if not is_process_running(trading_bot_process):
                log_warning("Trading Bot process is no longer running (detected by process handle).")
                bot_needs_restart = True
            else:
                # Check 2: Status file (only if process handle seems okay)
                bot_status_from_file = get_trading_bot_status_from_file()
                log_debug(f"Trading Bot status from file: {bot_status_from_file}")

                if bot_status_from_file in ["STALE", "STOPPED", "ERROR_READING_STATUS"]:
                    log_warning(f"Trading Bot status from file indicates an issue: {bot_status_from_file}.")
                    # If process *is* running but status is bad, it might be stuck.
                    # Let's try to restart it.
                    bot_needs_restart = True

            if bot_needs_restart:
                if restart_attempts < MAX_RESTART_ATTEMPTS:
                    restart_attempts += 1
                    log_info(f"Attempting to restart Trading Bot (Attempt {restart_attempts}/{MAX_RESTART_ATTEMPTS})...")

                    # Prepare restart arguments: exclude --cleanup and --backup
                    restart_args = [arg for arg in trading_bot_cli_args if arg not in ["--cleanup", "--backup"]]
                    # Ensure --params-file and --rl-agent-path are included if they were in the original args
                    # This is already handled by the list comprehension if they were in trading_bot_cli_args

                    if not await start_trading_bot(restart_args):
                        log_error(f"Failed to restart Trading Bot on attempt {restart_attempts}. Will retry after interval.")
                    else:
                        log_info("Trading Bot restarted successfully.")
                        # restart_attempts = 0 # Reset attempts on successful explicit restart
                                                # Let's keep incrementing to see if it stabilizes.
                                                # If it stabilizes, next check will not trigger restart, then we can reset.
                else:
                    log_error(f"Maximum restart attempts ({MAX_RESTART_ATTEMPTS}) reached for Trading Bot. Cooling down for {RESTART_COOLDOWN_SECONDS}s.")
                    await asyncio.sleep(RESTART_COOLDOWN_SECONDS)
                    restart_attempts = 0 # Reset attempts after cooldown
                    log_info("Cooldown finished. Will attempt to start Trading Bot on next cycle if needed.")
                    # No immediate restart here, will be caught in the next loop iteration if still needed
            else:
                # If bot is running fine, reset restart_attempts
                if restart_attempts > 0:
                    log_info("Trading Bot is running stable. Resetting restart attempt counter.")
                    restart_attempts = 0


            # Monitor Telegram Interface (optional)
            if telegram_interface_process and not is_process_running(telegram_interface_process):
                log_warning("Telegram Interface process is no longer running. Attempting to restart...")
                try:
                    await ensure_process_terminated(telegram_interface_process, "Telegram Interface")
                    telegram_interface_process = start_script_in_new_console(TELEGRAM_SCRIPT_PATH, PROJECT_ROOT_DIR)
                    if not telegram_interface_process:
                         log_error("Failed to restart Telegram Interface.")
                except Exception as e:
                    log_error(f":police_car_light: Error restarting Telegram Interface: {e}")


    except KeyboardInterrupt:
        log_info("KeyboardInterrupt received in Main Controller. Shutting down...")
    except Exception as e:
        log_error(f":police_car_light: An unexpected error occurred in Main Controller: {e}", exc_info=True)
    finally:
        log_info("--- Main Controller Shutting Down ---")
        await request_graceful_shutdown(trading_bot_process, "Trading Bot")
        # await ensure_process_terminated(trading_bot_process, "Trading Bot")
        await ensure_process_terminated(telegram_interface_process, "Telegram Interface")
        log_info("Main Controller shutdown complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot Controller")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file containing optimized parameters from GA.")
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")

    cmd_args = parser.parse_args()

    # Ensure data directory exists for status files etc.
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created data directory: {DATA_DIR}")

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main_controller(cmd_args))
    except KeyboardInterrupt:
        print("\nMain Controller interrupted by user. Exiting.")
    except Exception as e:
        print(f":police_car_light: Fatal error in controller startup: {e}")
```

#### 📄 `__init__.py`
*path: `rl_agent_module/agents/__init__.py`*

_This file is empty._

#### 📄 `ppo_agent.py`
*path: `rl_agent_module/agents/ppo_agent.py`*

```python
# rl_agent_module/agents/ppo_agent.py
from typing import Dict, Any, Optional
import gymnasium as gym
import torch as th
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy

def create_ppo_agent(
    env: gym.Env,
    hyperparams: Dict[str, Any],
    device: str = 'cpu',
    tensorboard_log_path: Optional[str] = None
) -> PPO:
    """
    Creates a PPO agent from a dictionary of hyperparameters.
    This is used for final model training after tuning.
    """
    # Create a deep copy to avoid modifying the original dictionary
    agent_params = hyperparams.copy()

    # Extract policy_kwargs from the main hyperparams dict, or create a default
    policy_kwargs = agent_params.pop("policy_kwargs", {})
    if not policy_kwargs:
        # Define a default architecture if not specified in the params file
        pi_layers = agent_params.pop("pi_layers", [256, 256])
        vf_layers = agent_params.pop("vf_layers", [256, 256])
        policy_kwargs = {
            "activation_fn": th.nn.ReLU,
            "net_arch": {"pi": pi_layers, "vf": vf_layers}
        }
    else:
        # Ensure nested dicts like activation_fn are handled if they are strings
        if isinstance(policy_kwargs.get("activation_fn"), str):
             # For now, we only support ReLU, but this could be expanded
            if policy_kwargs["activation_fn"].lower() == 'relu':
                policy_kwargs["activation_fn"] = th.nn.ReLU
            else:
                policy_kwargs["activation_fn"] = th.nn.ReLU # Default fallback

    # Remove any lingering architecture keys from the top level
    agent_params.pop("pi_layers", None)
    agent_params.pop("vf_layers", None)
    agent_params.pop("pi_vf_layers", None)
    
    # Instantiate and return the PPO agent
    model = PPO(
        policy=ActorCriticPolicy,
        env=env,
        policy_kwargs=policy_kwargs,
        tensorboard_log=tensorboard_log_path,
        verbose=0,
        device=device,
        **agent_params  # Pass the rest of the hyperparameters
    )
    
    return model
```

#### 📄 `__init__.py`
*path: `rl_agent_module/data/__init__.py`*

_This file is empty._

#### 📄 `cache_manager.py`
*path: `rl_agent_module/data/cache_manager.py`*

```python
# rl_agent_module/data/cache_manager.py
"""
DEPRECATED: This module is part of the legacy data preparation pipeline.

This CacheManager was used to compute and cache features on-the-fly during
the training script's execution. This approach has been replaced by a more
robust, offline ETL pipeline.

The new workflow is as follows:
1.  Run `rl_agent_module/etl/prepare_rl_dataset.py` to pre-compute all features and save
    them to a versioned Parquet data lake (`data/rl_feature_store/`).
2.  The `rl_agent_module.data.data_manager.DataManager` now acts as a feature
    assembler, reading directly from this pre-computed store.

This file is kept for historical reference but should not be used for any
new development.
"""
import os
import hashlib
import json
import pickle
import time
import pandas as pd
from typing import Dict, Any
from datetime import datetime, timezone
from tqdm import tqdm

# Project-specific imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from database_handler import DatabaseClient

class CacheManager:
    """
    Handles creation, validation, and loading of cached data using a configurable strategy.
    It measures performance and storage usage for comparison.
    """
    def __init__(self, db_client: DatabaseClient, start_ts: datetime, end_ts: datetime, rl_config: dict, verbose: bool = True):
        self.db_client = db_client
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.rl_config = rl_config
        self.strategy = self.rl_config.get('CACHE_STRATEGY', 'parquet').lower()

        date_str = f"{self.start_ts.strftime('%Y%m%d')}_{self.end_ts.strftime('%Y%m%d')}"
        # --- REFACTORED PATH ---
        # The cache is now stored in the top-level 'data/cache' directory,
        # completely separate from the 'rl_agent_module' source code.
        self.cache_dir = os.path.join(project_root, "data", "cache", date_str)
        self.manifest_path = os.path.join(self.cache_dir, "manifest.json")

        self.verbose = verbose

        os.makedirs(self.cache_dir, exist_ok=True)

    def _generate_fingerprint(self) -> str:
        """Generates a hash from relevant config params to detect changes."""
        config_params = {
            'DATA_START_DATE': self.rl_config.get('DATA_START_DATE'),
            'DATA_END_DATE': self.rl_config.get('DATA_END_DATE'),
            'MIN_TRADE_COUNT_FOR_DATASET': self.rl_config.get('MIN_TRADE_COUNT_FOR_DATASET'),
            'DATA_SPLIT_RATIO': self.rl_config.get('DATA_SPLIT_RATIO'),
            'DATA_SPLIT_RANDOM_SEED': self.rl_config.get('DATA_SPLIT_RANDOM_SEED'),
        }
        config_str = json.dumps(config_params, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    async def is_cache_valid(self, verbose: bool = True) -> bool:
        """Checks if a valid cache exists by comparing fingerprints."""
        if not os.path.exists(self.manifest_path):
            if (verbose and self.verbose):
                logger.info(f"No cache manifest found for window. Preparation is required.")
            return False

        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)

            stored_fingerprint = manifest.get('fingerprint')
            current_fingerprint = self._generate_fingerprint()

            stored_strategy = manifest.get('strategy', 'pickle')
            if stored_strategy != self.strategy:
                if (verbose and self.verbose):
                    logger.info(f"Cache strategy changed from '{stored_strategy}' to '{self.strategy}'. Re-caching is required.")
                return False

            if stored_fingerprint == current_fingerprint:
                if (verbose and self.verbose):
                    logger.info(f"Cache is valid (Strategy: {self.strategy}). Skipping data preparation.")
                return True
            else:
                if (verbose and self.verbose):
                    logger.info("Config fingerprint mismatch. Cache is stale. Re-running data preparation.")
                return False
        except Exception as e:
            if (verbose and self.verbose):
                logger.warning(f"Could not validate cache manifest: {e}. Re-running data preparation.")
            return False

    def save_to_cache(self, fingerprint: str, data_to_cache: Dict[str, Any], verbose: bool = True):
        """Saves the processed dataframes and manifest using the configured strategy."""
        if (verbose and self.verbose):
            logger.info(f"Saving data to cache using '{self.strategy}' strategy...")
        start_time = time.time()

        if self.strategy == 'pickle':
            self._save_as_pickle(data_to_cache, verbose)
        elif self.strategy == 'parquet':
            self._save_as_parquet(data_to_cache, verbose=verbose)
        else:
            raise ValueError(f"Unknown cache strategy: {self.strategy}")

        end_time = time.time()
        if (verbose and self.verbose):
            logger.info(f"Cache save operation took {end_time - start_time:.2f} seconds.")

        manifest = {
            'fingerprint': fingerprint,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'strategy': self.strategy,
            'file_keys': list(data_to_cache.keys())
        }
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)

    def load_from_cache(self, verbose: bool = True) -> Dict[str, Any]:
        """Loads data from the cache using the configured strategy."""
        if (verbose and self.verbose):
            logger.info(f"Loading data from cache using '{self.strategy}' strategy...")
        start_time = time.time()

        cached_data = {}
        if self.strategy == 'pickle':
            cached_data = self._load_from_pickle(verbose)
        elif self.strategy == 'parquet':
            cached_data = self._load_from_parquet(verbose=verbose)
        else:
            raise ValueError(f"Unknown cache strategy: {self.strategy}")

        end_time = time.time()
        if (verbose and self.verbose):
            logger.info(f"Cache load operation took {end_time - start_time:.2f} seconds.")
        return cached_data

    def _save_as_pickle(self, data: Dict[str, Any], verbose: bool = True):
        total_size_mb = 0
        for key, content in data.items():
            file_path = os.path.join(self.cache_dir, f"{key}.pkl")
            with open(file_path, 'wb') as f:
                pickle.dump(content, f)
            total_size_mb += os.path.getsize(file_path) / (1024 * 1024)
        if (verbose and self.verbose):
            logger.info(f"💾 Pickle Strategy: Saved {len(data)} key(s). Total size: {total_size_mb:.2f} MB")

    def _load_from_pickle(self, verbose: bool = True) -> Dict[str, Any]:
        loaded_data = {}
        with open(self.manifest_path, 'r') as f:
            keys = json.load(f)['file_keys']
        for key in keys:
            file_path = os.path.join(self.cache_dir, f"{key}.pkl")
            with open(file_path, 'rb') as f:
                loaded_data[key] = pickle.load(f)
        return loaded_data

    def _save_as_parquet(self, data: Dict[str, Any], verbose: bool = True):
        total_size_mb = 0
        for key, content in data.items():
            if isinstance(content, dict) and all(isinstance(df, pd.DataFrame) for df in content.values()):
                key_dir = os.path.join(self.cache_dir, key)
                os.makedirs(key_dir, exist_ok=True)

                desc = f"Saving '{key}' to Parquet"
                iterable = tqdm(content.items(), desc=desc, disable=not verbose)

                for mint, df in iterable:
                    safe_mint = mint.replace('/', '_').replace('\\', '_')
                    file_path = os.path.join(key_dir, f"{safe_mint}.parquet")
                    df.to_parquet(file_path)
                    total_size_mb += os.path.getsize(file_path) / (1024 * 1024)
            else:
                if (verbose and self.verbose):
                    logger.warning(f"Content for key '{key}' is not a DataFrame dict. Falling back to pickle.")
                self._save_as_pickle({key: content}, verbose)

        if (verbose and self.verbose):
            logger.info(f"💾 Parquet Strategy: Save complete. Total size: {total_size_mb:.2f} MB")

    def _load_from_parquet(self, verbose: bool = True) -> Dict[str, Any]:
        loaded_data = {}
        with open(self.manifest_path, 'r') as f:
            keys = json.load(f)['file_keys']

        for key in keys:
            key_dir = os.path.join(self.cache_dir, key)
            if os.path.isdir(key_dir):
                data_dict = {}
                parquet_files = [f for f in os.listdir(key_dir) if f.endswith('.parquet')]

                desc = f"Loading '{key}' from Parquet"
                iterable = tqdm(parquet_files, desc=desc, disable=not verbose)

                for filename in iterable:
                    mint = os.path.splitext(filename)[0]
                    file_path = os.path.join(key_dir, filename)
                    data_dict[mint] = pd.read_parquet(file_path)
                loaded_data[key] = data_dict
            else:
                if (verbose and self.verbose):
                    logger.warning(f"Directory for key '{key}' not found. Attempting to load as pickle.")
                file_path = os.path.join(self.cache_dir, f"{key}.pkl")
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        loaded_data[key] = pickle.load(f)
        return loaded_data
```

#### 📄 `data_manager.py`
*path: `rl_agent_module/data/data_manager.py`*

```python
# rl_agent_module/data/data_manager.py
"""
Handles assembling feature data by directly accessing the MLflow artifact store path.
NOTE: This approach is optimized for a local 'file://' MLflow backend.
"""
import os
import sys
from typing import Dict, Optional, Tuple, List
import pandas as pd
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import mlflow
from mlflow.tracking import MlflowClient
from urllib.parse import urlparse
import platform

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from config.rl_config import FEATURE_GROUPS, get_active_features

# Dynamically create the reverse mapping from the config
FEATURE_TO_GROUP_MAP = {
    feature: group_name
    for group_name, features in FEATURE_GROUPS.items()
    for feature in features
}

class DataManager:
    """
    Manages RL feature data by linking to a versioned dataset in MLflow.
    - Determines the direct local path to the artifact store for a given run.
    - Loads and merges data for specified tokens from the Parquet store.
    - Splits available tokens into training and evaluation sets.
    """
    def __init__(self, rl_config: dict, dataset_run_id: str):
        self.rl_config = rl_config
        self.dataset_run_id = dataset_run_id
        
        # The path will be populated dynamically by resolving the artifact URI.
        self.feature_store_path: Optional[str] = None

        self.training_data: Optional[pd.DataFrame] = None
        self.evaluation_data: Optional[pd.DataFrame] = None
        self.training_set_mints: List[str] = []
        self.evaluation_set_mints: List[str] = []

        self._current_dataset_iterator = None
        self._columns = None

        self.verbose = True

    def get_training_data(self) -> Optional[pd.DataFrame]: return self.training_data
    def get_evaluation_data(self) -> Optional[pd.DataFrame]: return self.evaluation_data
    def get_split_token_mints(self) -> Tuple[List[str], List[str]]: return self.training_set_mints, self.evaluation_set_mints

    def _resolve_artifact_path(self) -> bool:
        """
        Gets the direct, local filesystem path to the 'feature_store' artifact.
        This method is suitable for 'file://' MLflow backends.
        """
        try:
            if self.verbose:
                logger.info(f"Resolving direct artifact path for run '{self.dataset_run_id}'...")
            client = MlflowClient()
            run = client.get_run(self.dataset_run_id)
            artifact_uri = run.info.artifact_uri
            
            # The artifact_uri is the root of the artifacts for the run.
            # We need to append our specific artifact's path.
            parsed_uri = urlparse(artifact_uri)
            
            # For local file URIs (e.g., 'file:///C:/path'), extract the path correctly.
            if parsed_uri.scheme == 'file':
                # On Windows, urlparse might add an extra leading '/' (e.g., /C:/...).
                # We need to remove it.
                local_artifact_root = parsed_uri.path
                if platform.system() == "Windows" and local_artifact_root.startswith('/'):
                    local_artifact_root = local_artifact_root[1:]
                
                self.feature_store_path = os.path.join(local_artifact_root, "feature_store")
                if self.verbose:
                    logger.info(f"✅ Resolved artifact path to: {self.feature_store_path}")
                return True
            else:
                logger.error(f"Cannot resolve direct path for non-file URI: {artifact_uri}. This method only works for local MLflow stores.")
                return False

        except Exception as e:
            logger.error(f"Failed to resolve artifact path for run '{self.dataset_run_id}': {e}", exc_info=True)
            return False

    def _load_data_for_mints(
        self,
        mints_to_load: List[str],
        active_features: List[str],
        verbose: bool = True
    ) -> Dict[str, pd.DataFrame]:
        if not mints_to_load or self.feature_store_path is None: return {}

        groups_to_load = {'base_ohlcv'}
        for feature in active_features:
            if feature in FEATURE_TO_GROUP_MAP:
                groups_to_load.add(FEATURE_TO_GROUP_MAP[feature])
        if verbose: logger.info(f"Required feature groups: {sorted(list(groups_to_load))}")

        all_mint_data = {mint: [] for mint in mints_to_load}
        for group in groups_to_load:
            group_root_path = os.path.join(self.feature_store_path, f"group={group}")
            if not os.path.isdir(group_root_path): continue

            for date_dir in os.listdir(group_root_path):
                date_path = os.path.join(group_root_path, date_dir)
                if not os.path.isdir(date_path): continue
                for mint in mints_to_load:
                    file_path = os.path.join(date_path, f"{mint}.parquet")
                    if os.path.exists(file_path):
                        try:
                            all_mint_data[mint].append(pd.read_parquet(file_path))
                        except Exception as e:
                            if verbose: logger.warning(f"Could not read {file_path}: {e}")

        assembled_dfs = {}
        desc = "Assembling mint dataframes"
        for mint, df_list in tqdm(all_mint_data.items(), desc=desc, disable=not verbose):
            if df_list:
                full_df = pd.concat(df_list).sort_index()
                full_df = full_df.loc[~full_df.index.duplicated(keep='first')]
                assembled_dfs[mint] = full_df
            
        return assembled_dfs

    def load_and_prepare_data(self, mints_to_load: Optional[List[str]] = None, verbose: bool = True) -> bool:
        if self.feature_store_path is None:
            if not self._resolve_artifact_path():
                return False
        
        active_features = get_active_features(self.rl_config)
        active_features_with_mint = active_features + ['mint']

        if not mints_to_load and not (self.training_set_mints or self.evaluation_set_mints):
            if verbose: logger.info("Discovering available tokens in the feature store...")
            base_path = os.path.join(self.feature_store_path, "group=base_ohlcv")
            
            if not os.path.isdir(base_path):
                 logger.error(f"Critical error: 'group=base_ohlcv' not found at path {base_path}")
                 return False

            available_mints = set(os.path.splitext(f)[0] for root, _, files in os.walk(base_path) for f in files if f.endswith(".parquet"))
            
            if not available_mints:
                logger.error("No token data found in the feature store. Aborting.")
                return False

            if verbose: logger.info(f"Found {len(available_mints)} unique tokens. Splitting into train/eval sets.")
            train_ratio = self.rl_config.get('DATA_SPLIT_RATIO')[0]
            self.training_set_mints, self.evaluation_set_mints = train_test_split(
                list(available_mints), train_size=train_ratio,
                random_state=self.rl_config.get('DATA_SPLIT_RANDOM_SEED'), shuffle=True
            )
        
        mints_for_training = mints_to_load or self.training_set_mints
        mints_for_evaluation = [] if mints_to_load else self.evaluation_set_mints

        training_dict = self._load_data_for_mints(mints_for_training, active_features_with_mint, verbose)
        if training_dict:
            self.training_data = pd.concat(training_dict.values()).sort_index()
            if verbose: logger.info(f"Training data prepared. Total steps: {len(self.training_data)}")
        
        if mints_for_evaluation:
            eval_dict = self._load_data_for_mints(mints_for_evaluation, active_features_with_mint, verbose)
            if eval_dict:
                self.evaluation_data = pd.concat(eval_dict.values()).sort_index()
                if verbose: logger.info(f"Evaluation data prepared. Total steps: {len(self.evaluation_data)}")
        
        self.use_training_data()
        return True

    def use_training_data(self):
        if self.training_data is not None:
            self._current_dataset_iterator, self._columns = self.training_data.itertuples(), self.training_data.columns
        else: self._current_dataset_iterator = iter([])

    def use_evaluation_data(self):
        if self.evaluation_data is not None:
            self._current_dataset_iterator, self._columns = self.evaluation_data.itertuples(), self.evaluation_data.columns
        else: self._current_dataset_iterator = iter([])
            
    def use_single_token_data(self, token_df: pd.DataFrame):
        if token_df is not None and not token_df.empty:
            self._current_dataset_iterator, self._columns = token_df.itertuples(), token_df.columns
        else: self._current_dataset_iterator = iter([])

    def __iter__(self):
        self.reset(); return self

    def __next__(self) -> Optional[Tuple[pd.Timestamp, pd.Series]]:
        if self._current_dataset_iterator is None: return None
        try:
            row_tuple = next(self._current_dataset_iterator)
            timestamp = row_tuple[0]
            return timestamp, pd.Series(row_tuple[1:], index=self._columns, name=timestamp)
        except StopIteration: return None

    def reset(self) -> None: self.use_training_data()
```

#### 📄 `inspect_cache.py`
*path: `rl_agent_module/data/inspect_cache.py`*

```python
# rl_agent_module/data/inspect_cache.py
"""
Read, inspect, and export cached token data — either from pickle or parquet format.
Supports both caching strategies: 'pickle' (single file) and 'parquet' (per-token files).
"""
import os
import pickle
import sys
import argparse
import psutil
import pandas as pd
from typing import Dict, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger  # Optional: for consistent logging

def get_memory_usage():
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"📊 Current memory usage: {mem_mb:.1f} MB")


def load_from_pickle(cache_dir: str) -> Dict[str, Any]:
    """Load cached data from token_data.pkl."""
    pickle_path = os.path.join(cache_dir, "token_data.pkl")
    if not os.path.exists(pickle_path):
        print(f"❌ Pickle file not found: {pickle_path}")
        return {}

    print(f"📂 Loading data from pickle: {pickle_path}")
    try:
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
        if not isinstance(data, dict):
            print("⚠️  Unexpected pickle structure: top-level is not a dict.")
            return {}
        return data
    except Exception as e:
        print(f"❌ Error loading pickle: {e}")
        return {}


def load_from_parquet(cache_dir: str) -> Dict[str, Any]:
    """Load cached data from parquet directories (training_set, evaluation_set)."""
    print(f"📂 Loading data from parquet files in: {cache_dir}")
    result = {}

    sets = ['training_set', 'evaluation_set']
    for dataset in sets:
        set_dir = os.path.join(cache_dir, dataset)
        if not os.path.exists(set_dir):
            print(f"⚠️  Parquet dataset directory not found: {set_dir}")
            continue

        print(f"📊 Loading '{dataset}' from parquet...")
        token_dfs = {}
        for filename in os.listdir(set_dir):
            if not filename.endswith(".parquet"):
                continue
            mint = os.path.splitext(filename)[0]
            file_path = os.path.join(set_dir, filename)
            try:
                df = pd.read_parquet(file_path)
                token_dfs[mint] = df
            except Exception as e:
                print(f"❌ Error reading {file_path}: {e}")
        result[dataset] = token_dfs

    return result


def inspect_data(data: Dict[str, Any], export_all: bool, export_mode: str, output_dir: str):
    """Inspect loaded data and optionally export to CSV."""
    print("\n" + "=" * 60)
    print("🧩 CACHED DATA INSPECTION")
    print("=" * 60)

    if 'token_data' in data:  # Pickle mode
        token_data = data['token_data']
        print(f"🗂  Found 'token_data' with {len(token_data)} tokens (Pickle mode).")
        _inspect_token_data(token_data, export_all, export_mode, output_dir, prefix="token_data")

    elif 'training_set' in data or 'evaluation_set' in data:  # Parquet mode
        if 'training_set' in data:
            print(f"🗂  Found 'training_set' with {len(data['training_set'])} tokens.")
            _inspect_token_data(data['training_set'], export_all, export_mode, output_dir, prefix="training_set")
        if 'evaluation_set' in data:
            print(f"🗂  Found 'evaluation_set' with {len(data['evaluation_set'])} tokens.")
            _inspect_token_data(data['evaluation_set'], export_all, export_mode, output_dir, prefix="evaluation_set")
    else:
        print("⚠️  No recognizable data sets found (expected 'token_data', 'training_set', or 'evaluation_set').")
        print(f"🔍 Available keys: {list(data.keys())}")


def _inspect_token_data(token_data: Dict[str, pd.DataFrame], export_all: bool, export_mode: str,
                        output_dir: str, prefix: str = ""):
    """Helper to inspect and export a dictionary of token DataFrames with memory-efficient combined export."""
    if not token_data:
        print(f"⚠️  {prefix or 'Token data'} is empty.")
        return

    # Preview first token
    first_mint = next(iter(token_data))
    df = token_data[first_mint]
    if isinstance(df, pd.DataFrame) and not df.empty:
        print(f"\n🔍 Preview of first token (Mint: {first_mint}):")
        print(df.head())
        print(f"\n📅 Time range: {df.index.min()} → {df.index.max()}")
        print(f"📊 Shape: {df.shape}")
    else:
        print(f"⚠️  First token '{first_mint}' has invalid or empty DataFrame.")

    # Export logic
    if export_all:
        export_dir = os.path.join(output_dir, prefix) if prefix else output_dir
        os.makedirs(export_dir, exist_ok=True)

        if export_mode == "per_token":
            # Standard: one CSV per token
            for mint, df in token_data.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    safe_mint = mint.replace('/', '_').replace('\\', '_')
                    csv_path = os.path.join(export_dir, f"{safe_mint}.csv")
                    df.to_csv(csv_path)
            print(f"✅ Exported {len(token_data)} tokens to {export_dir} (one CSV per token).")

        elif export_mode == "combined":
            combined_csv_path = os.path.join(export_dir, "combined_tokens.csv")
            processed_count = 0

            # Write the first token with header, then append the rest
            first = True
            for mint, df in token_data.items():
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue

                # Add a 'mint' column to identify the token
                df_export = df.copy()
                df_export['mint'] = mint  # Identify source token

                # Write to CSV: header only on first, then append
                df_export.to_csv(
                    combined_csv_path,
                    mode='w' if first else 'a',
                    header=first,
                    index=True  # Keep timestamp as index (or reset_index() if you want it as a column)
                )
                first = False
                processed_count += 1

                # Optional: log progress every 1000 tokens
                if processed_count % 1000 == 0:
                    print(f"📌 Exported {processed_count} tokens to combined CSV...")

            print(f"✅ Exported {processed_count} tokens to {combined_csv_path} (streaming mode).")


def main():
    parser = argparse.ArgumentParser(description="Inspect RL cache (supports pickle and parquet).")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cache-dir", type=str, help="Path to cache directory (e.g., rl_agent_module/data/cache/20250626_20250627)")
    group.add_argument("--auto-detect", action="store_true",
                      help="Auto-detect latest cache directory by date")

    parser.add_argument("--strategy", choices=["pickle", "parquet", "auto"], default="auto",
                        help="Specify cache strategy. 'auto' detects based on files present.")

    # Export options
    parser.add_argument("--export-all", action="store_true", help="Export all tokens to CSV")
    parser.add_argument(
        "--mode", choices=["per_token", "combined"], default="per_token",
        help="Export mode: 'per_token' (one file per token), 'combined' (single CSV)"
    )
    parser.add_argument("--output-dir", type=str, default="exports",
                        help="Output directory for CSV files (default: 'exports')")

    args = parser.parse_args()

    # Resolve cache directory
    if args.auto_detect:
        cache_base = os.path.join(project_root, "rl_agent_module", "data", "cache")
        if not os.path.exists(cache_base):
            print(f"❌ Cache base directory not found: {cache_base}")
            return
        # List directories and pick the latest by name (assumes YYYYMMDD_YYYYMMDD format)
        dirs = [d for d in os.listdir(cache_base) if os.path.isdir(os.path.join(cache_base, d))]
        dirs = sorted(dirs, reverse=True)
        if not dirs:
            print("❌ No cache directories found.")
            return
        cache_dir = os.path.join(cache_base, dirs[0])
        print(f"📁 Auto-detected cache directory: {cache_dir}")
    else:
        cache_dir = args.cache_dir

    if not os.path.exists(cache_dir):
        print(f"❌ Cache directory does not exist: {cache_dir}")
        return

    # Detect or use strategy
    strategy = args.strategy
    if strategy == "auto":
        has_pickle = os.path.exists(os.path.join(cache_dir, "token_data.pkl"))
        has_parquet_dirs = any(os.path.exists(os.path.join(cache_dir, d)) for d in ["training_set", "evaluation_set"])
        if has_pickle and not has_parquet_dirs:
            strategy = "pickle"
        elif has_parquet_dirs and not has_pickle:
            strategy = "parquet"
        elif has_pickle and has_parquet_dirs:
            print("⚠️  Both pickle and parquet files found. Defaulting to 'parquet' (more granular).")
            strategy = "parquet"
        else:
            print("❌ Could not auto-detect strategy: no known cache files found.")
            return
        print(f"🔍 Auto-detected cache strategy: {strategy}")
    else:
        print(f"🔧 Using user-specified strategy: {strategy}")

    # Load data
    if strategy == "pickle":
        data = load_from_pickle(cache_dir)
    elif strategy == "parquet":
        data = load_from_parquet(cache_dir)
    else:
        print(f"❌ Unknown strategy: {strategy}")
        return

    if not data:
        print("❌ No data loaded. Exiting.")
        return

    # Inspect and export
    inspect_data(data, args.export_all, args.mode, args.output_dir)


if __name__ == "__main__":
    main()
```

#### 📄 `__init__.py`
*path: `rl_agent_module/environments/__init__.py`*

_This file is empty._

#### 📄 `meme_coin_env.py`
*path: `rl_agent_module/environments/meme_coin_env.py`*

```python
# rl_agent_module/environments/meme_coin_env.py
import gymnasium as gym
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from gymnasium import spaces
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from rl_agent_module.data.data_manager import DataManager
from rl_agent_module.rewards.reward_function import RewardFunction
from config.rl_config import get_active_features

# --- NEW: Stability constants ---
EPS = 1e-9  # Epsilon for safe division
MAX_STEPS_PER_EPISODE = 5000  # Ensures episodes finish, e.g., ~7 hours of 5s ticks
WARMUP_STEPS = 200 # Approx. 17 mins of 5s ticks to let indicators build up

class MemeCoinEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, data_manager: DataManager, rl_config: Dict[str, Any], silent: bool = False):
        super().__init__()
        self.data_manager = data_manager
        self.rl_config = rl_config
        self.reward_function = RewardFunction(self.rl_config)
        self.silent = silent # MODIFIED: Use the passed argument
        self.eps = self.rl_config.get('ENV_EPS', EPS)

        self.feature_columns = get_active_features(self.rl_config)
        
        # --- Load parameters from the config dictionary ---
        self.initial_balance = self.rl_config.get('ENV_INITIAL_BALANCE', 100.0)
        self.max_concurrent_positions = self.rl_config.get('ENV_MAX_CONCURRENT_POSITIONS', 5)
        self.num_top_tokens_to_observe = self.rl_config.get('ENV_NUM_TOP_TOKENS_TO_OBSERVE', 5)
        self.time_norm_seconds = self.rl_config.get('ENV_TIME_IN_POSITION_NORM_SECONDS', 14400.0)

        # Observation Space
        num_portfolio_features = 4
        num_base_token_features = len(self.feature_columns)
        num_position_features = 5
        total_token_features = num_base_token_features + num_position_features
        obs_space_size = num_portfolio_features + (self.num_top_tokens_to_observe * total_token_features)
        
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_space_size,), dtype=np.float32)
        
        # Action Space
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(self.num_top_tokens_to_observe,), dtype=np.float32)
        
        # Initialize state variables
        self.balance = self.initial_balance
        self.portfolio_value = self.initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.current_step = 0
        self.current_timestamp = None
        self.current_data_point = None
        self._steps = 0
        self._warmup_left = 0
        # --- NEW: Episode stats for logging ---
        self.episode_buys = 0
        self.episode_sells = 0

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.data_manager.reset()
        
        self.balance = self.initial_balance
        self.portfolio_value = self.initial_balance
        self.positions = {}
        self.current_step = 0
        self.reward_function.reset(self.initial_balance)
        self._steps = 0
        self._warmup_left = self.rl_config.get('ENV_WARMUP_STEPS', WARMUP_STEPS)
        # --- NEW: Episode stats for logging ---
        self.episode_buys = 0
        self.episode_sells = 0
        
        next_data = next(self.data_manager, None)
        if next_data is None: raise StopIteration("No data available in DataManager.")
        self.current_timestamp, self.current_data_point = next_data
        
        obs = self._get_observation()
        obs = np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6)
        obs = np.clip(obs, -10.0, 10.0)
        return obs, {}

    def _log_episode_end(self, reason: str):
        """Helper to log a summary when an episode finishes."""
        # MODIFICATION: Only log if not in silent mode
        if not self.silent:
            final_pnl = self.portfolio_value - self.initial_balance
            final_pnl_pct = (final_pnl / self.initial_balance) * 100
            logger.info(f"--- Episode End: {reason} ---")
            logger.info(f"Duration: {self._steps} steps ({self.current_timestamp})")
            logger.info(f"Final Portfolio: {self.portfolio_value:.2f} SOL (PnL: {final_pnl:.2f} SOL, {final_pnl_pct:.2f}%)")
            logger.info(f"Trades: {self.episode_buys} Buys, {self.episode_sells} Sells")
            logger.info("-" * (25 + len(reason)))


    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self._steps += 1

        if self._warmup_left > 0:
            self._warmup_left -= 1
            next_step_data = next(self.data_manager, None)
            terminated = next_step_data is None
            if not terminated:
                self.current_timestamp, self.current_data_point = next_step_data
                self._update_portfolio()
            else:
                self._log_episode_end("Data ended during warmup")
            
            obs = self._get_observation()
            return obs, 0.0, terminated, False, {}

        observed_tokens = self._get_top_tokens()
        self._execute_sells(action, observed_tokens)
        self._execute_buys(action, observed_tokens)

        next_step_data = next(self.data_manager, None)
        terminated = next_step_data is None
        truncated = self._steps >= self.rl_config.get('ENV_MAX_STEPS_PER_EPISODE', MAX_STEPS_PER_EPISODE)
        
        if not terminated:
            self.current_timestamp, self.current_data_point = next_step_data
            self.current_step += 1
        
        self._update_portfolio()
        
        if self.portfolio_value < (self.initial_balance * 0.5):
            terminated = True
            truncated = False
            self._log_episode_end("Bankrupted (portfolio < 50%)")

        if terminated and not truncated:
             self._log_episode_end("End of dataset reached")
        if truncated:
             self._log_episode_end("Max episode steps reached")

        reward = self.reward_function.calculate_reward({}, self._get_current_global_state(), self.portfolio_value)
        reward = float(np.nan_to_num(reward, nan=-1e-3, posinf=-1e-3, neginf=-1e-3))

        obs = self._get_observation()
        return obs, reward, terminated, truncated, {}

    def _get_top_tokens(self) -> List[pd.Series]:
        current_df = self.current_data_point
        if isinstance(current_df, pd.Series): current_df = current_df.to_frame().T
        if 'volume_usd' in current_df.columns:
            top_tokens = current_df.sort_values('volume_usd', ascending=False).head(self.num_top_tokens_to_observe)
            return [row for _, row in top_tokens.iterrows()]
        return []

    def _get_observation(self) -> np.ndarray:
        balance_norm = self.balance / max(self.portfolio_value, self.eps)
        portfolio_value_norm = self.portfolio_value / max(self.initial_balance, self.eps)
        num_positions_norm = len(self.positions) / self.max_concurrent_positions
        
        unrealized_pnl = sum(
            (self._get_price_for_mint(mint) - pos['entry_price']) * (pos['size_sol'] / max(pos['entry_price'], self.eps))
            for mint, pos in self.positions.items() if self._get_price_for_mint(mint) is not None
        )
        unrealized_pnl_norm = unrealized_pnl / max(self.initial_balance, self.eps)

        portfolio_features = np.array([balance_norm, portfolio_value_norm, num_positions_norm, unrealized_pnl_norm], dtype=np.float32)

        top_tokens = self._get_top_tokens()
        token_features_list = []
        num_base_token_features = len(self.feature_columns)
        num_position_features = 5
        
        for i in range(self.num_top_tokens_to_observe):
            if i < len(top_tokens):
                token_data = top_tokens[i]
                mint = token_data.get('mint', 'unknown')
                base_features = token_data[self.feature_columns].values.astype(np.float32)

                if mint in self.positions:
                    pos = self.positions[mint]
                    price = self._get_price_for_mint(mint)
                    time_in_pos = (self.current_timestamp - pos['timestamp']).total_seconds() if self.current_timestamp else 0
                    pnl_ratio = (price - pos['entry_price']) / max(pos['entry_price'], self.eps) if price is not None else 0
                    highest_price_ratio = price / max(pos['highest_price'], self.eps) if price is not None else 1.0

                    position_features = np.array([
                        1.0, 
                        pos['size_sol'] / max(self.portfolio_value, self.eps),
                        pnl_ratio,
                        min(time_in_pos / self.time_norm_seconds, 1.0),
                        highest_price_ratio
                    ], dtype=np.float32)
                else:
                    position_features = np.zeros(num_position_features, dtype=np.float32)
                
                token_features_list.append(np.concatenate([base_features, position_features]))
            else:
                token_features_list.append(np.zeros(num_base_token_features + num_position_features, dtype=np.float32))
        
        obs = np.concatenate([portfolio_features] + token_features_list, axis=0).astype(np.float32)
        
        obs = np.nan_to_num(obs, nan=0.0, posinf=10.0, neginf=-10.0)
        obs = np.clip(obs, -10.0, 10.0)
        
        return obs

    def _execute_sells(self, action: np.ndarray, observed_tokens: List[pd.Series]):
        sell_threshold = self.rl_config.get('ENV_ACTION_SELL_THRESHOLD', -0.2)
        for i, token_data in enumerate(observed_tokens):
            mint = token_data.get('mint')
            if mint in self.positions and action[i] < sell_threshold:
                position = self.positions[mint]
                current_price = token_data.get('Close')
                if current_price is None: continue

                sell_value_sol = position['size_sol'] * (current_price / max(position['entry_price'], self.eps))
                pnl = sell_value_sol - position['size_sol']
                self.balance += sell_value_sol
                del self.positions[mint]
                self.episode_sells += 1
                # MODIFICATION: Only log if not in silent mode
                if not self.silent:
                    logger.debug(f"SELL: {mint[:6]} at price {current_price:.6f}. PnL: {pnl:.4f} SOL. Balance: {self.balance:.2f} SOL.")


    def _execute_buys(self, action: np.ndarray, observed_tokens: List[pd.Series]):
        buy_threshold = self.rl_config.get('ENV_ACTION_BUY_THRESHOLD', 0.2)
        capital_pct = self.rl_config.get('ENV_CAPITAL_PER_BUY_PERCENT', 0.95)

        for i, token_data in enumerate(observed_tokens):
            mint = token_data.get('mint')
            if action[i] > buy_threshold and mint not in self.positions and len(self.positions) < self.max_concurrent_positions:
                available_slots = self.max_concurrent_positions - len(self.positions)
                capital_per_buy = (self.balance / available_slots) * capital_pct
                current_price = token_data.get('Close')
                if current_price is None or current_price <= 0: continue
                
                if self.balance >= capital_per_buy > 0:
                    self.balance -= capital_per_buy
                    self.positions[mint] = {
                        'entry_price': current_price,
                        'size_sol': capital_per_buy,
                        'highest_price': current_price,
                        'timestamp': self.current_timestamp
                    }
                    self.episode_buys += 1
                    # MODIFICATION: Only log if not in silent mode
                    if not self.silent:
                        logger.debug(f"BUY: {mint[:6]} for {capital_per_buy:.4f} SOL at price {current_price:.6f}. Balance: {self.balance:.2f} SOL.")

    def _update_portfolio(self):
        held_value = 0
        for mint, position in self.positions.items():
            current_price = self._get_price_for_mint(mint)
            if current_price is None:
                held_value += 0 
                continue

            position['highest_price'] = max(position['highest_price'], current_price)
            held_value += position['size_sol'] * (current_price / max(position['entry_price'], self.eps))
        
        self.portfolio_value = self.balance + held_value
        
    def _get_price_for_mint(self, mint: str) -> Optional[float]:
        if self.current_data_point is None: return None
        if isinstance(self.current_data_point, pd.Series):
            return self.current_data_point['Close'] if self.current_data_point.get('mint') == mint else None
        
        token_row = self.current_data_point[self.current_data_point['mint'] == mint]
        return token_row['Close'].iloc[0] if not token_row.empty else None

    def _get_current_global_state(self) -> Dict:
        return {}
        
    def render(self, mode='human'):
        logger.info(f"Step: {self.current_step}, Timestamp: {self.current_timestamp}, "
              f"Portfolio Value: {self.portfolio_value:.4f} SOL, Positions: {len(self.positions)}")
```

#### 📄 `prepare_rl_dataset.py`
*path: `rl_agent_module/etl/prepare_rl_dataset.py`*

```python
# rl_agent_module/etl/prepare_rl_dataset.py
"""
Standalone ETL script for preparing the Reinforcement Learning dataset.

This script performs the following steps:
1.  Connects to the PostgreSQL database to fetch raw trade and token data.
2.  Invokes the feature engineering pipeline to calculate a wide array of technical
    indicators and informational features.
3.  Groups the calculated features into logical sets as defined in rl_config.py.
4.  Saves the feature groups into a versioned, partitioned Parquet data lake.
5.  Logs the generated dataset to MLflow for versioning and traceability.

The output data structure is designed for efficient, modular access during model training:
    <RL_FEATURE_STORE_PATH>/v<version>/group=<group_name>/date=YYYY-MM-DD/<mint>.parquet

Usage:
    python rl_agent_module/etl/prepare_rl_dataset.py \
        --start-date 2025-06-26T00:00:00Z \
        --end-date 2025-07-20T00:00:00Z \
        --output-version 1.0
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime
import pandas as pd
from tqdm import tqdm
 # +++ Add this import
import tempfile

import mlflow
from mlflow.data.pandas_dataset import PandasDataset


# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from config.rl_config import RL_CONFIG, FEATURE_GROUPS
from rl_agent_module.feature_engineering.features import calculate_all_features


async def run_etl(start_date: datetime, end_date: datetime, version: str):
    """Main ETL orchestration function."""
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_DATASET"])
    run_name = f"bigDF_v{version}_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"

    with tempfile.TemporaryDirectory() as temp_output_dir, mlflow.start_run(run_name=run_name, log_system_metrics=True) as run:
        logger.info(f"Starting ETL run '{run.info.run_name}' (ID: {run.info.run_id})")
        mlflow.log_params({"start_date": start_date, "end_date": end_date, "version": version})

        db_client = None
        try:
            db_client = DatabaseClient()
            await db_client.connect()
            min_trades = RL_CONFIG['common'].get('MIN_TRADE_COUNT_FOR_DATASET', 100)
            
            logger.info(f"Fetching raw data for tokens with >= {min_trades} trades...")
            raw_data = await db_client.get_raw_data_for_rl(
                start_date, end_date, min_trades
            )
            if raw_data is None:
                logger.error("No raw data fetched. Aborting.")
                return

            trades_df, rugcheck_df, token_info_df, dexscreener_df = raw_data
            num_tokens = trades_df['mint'].nunique()
            logger.info(f"Fetched raw data for {num_tokens} tokens.")
            mlflow.log_metric("initial_token_count", num_tokens)

            feature_groups_data, feature_list = await calculate_all_features(
                trades_df, rugcheck_df, token_info_df, dexscreener_df
            )
            if not feature_groups_data:
                logger.error("Feature calculation resulted in no data. Aborting.")
                return
            
            # Prepare lists for mlflow.log_inputs()
            datasets = []
            contexts = []
            tags_list = []

            # Optional: Log the list of all features used
            mlflow.set_tag("feature_columns", ", ".join(feature_list))

            
            mlflow.log_metric("feature_count", len(feature_list))
            mlflow.log_param("features_used", feature_list)
            
            
            base_output_dir = os.path.join(temp_output_dir) # MODIFIED
            logger.info(f"Saving partitioned data to: {temp_output_dir}")

            processed_mints = set()
            total_files = sum(len(mints) for _, mints in feature_groups_data.items())
            pbar = tqdm(total=total_files, desc="Saving Parquet files")

            for group_name, mint_data in feature_groups_data.items():

                sample_mint = next(iter(mint_data))
                sample_df = mint_data[sample_mint]

                for mint, df in mint_data.items():
                    if df.empty: continue
                    processed_mints.add(mint)
                    for day, daily_df in df.groupby(pd.Grouper(freq='D')):
                        if daily_df.empty: continue
                        date_str = day.strftime('%Y-%m-%d')
                        output_path = os.path.join(base_output_dir, f"group={group_name}", f"date={date_str}")
                        os.makedirs(output_path, exist_ok=True)
                        parquet_path = os.path.join(output_path, f"{mint}.parquet")
                        daily_df.to_parquet(parquet_path)
                    pbar.update(1)

                dataset: PandasDataset = mlflow.data.from_pandas(
                    sample_df,
                    # source=source,  # optional: point to origin
                    name=f"features_{group_name}"
                )

                datasets.append(dataset)
                contexts.append(f"feature_group_{group_name}")
                tags_list.append({
                    "group": group_name,
                    "num_tokens": str(len(mint_data)),
                    "example_mint": sample_mint,
                    "version": version
                })

                
            pbar.close()

            
            # Log all datasets
            mlflow.log_inputs(
                datasets=datasets,
                contexts=contexts,
                tags_list=tags_list
            )


            # --- MLflow Dataset Logging (FIXED) ---
            active_run = mlflow.active_run()
            if active_run:
                run_id = active_run.info.run_id
                artifact_uri = f"runs:/{run_id}/feature_store"
                mlflow.log_artifacts(base_output_dir, artifact_path="feature_store")
                logger.info(f"✅ Dataset successfully logged. Artifact URI: {artifact_uri}")

            mlflow.log_metric("processed_token_count", len(processed_mints))
            logger.info(f"✅ ETL process completed. Logged dataset to MLflow run.")

        except Exception as e:
            logger.error(f"ETL process failed: {e}", exc_info=True)
            mlflow.set_tag("status", "failed")
        finally:
            if db_client:
                await db_client.close()

if __name__ == "__main__":
    setup_logging(logger_name="rl_etl")
    # --- MODIFICATION: Point to the MLflow server ---
    # Assumes the server is running at the default location started by rl_main.py
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    #mlflow.set_tracking_uri("file:./data/rl_runs")

    parser = argparse.ArgumentParser(description="Run the ETL pipeline for RL feature generation.")
    parser.add_argument("--start-date", type=str, required=True, help="Start date in ISO format.")
    parser.add_argument("--end-date", type=str, required=True, help="End date in ISO format.")
    parser.add_argument("--output-version", type=str, default=RL_CONFIG.get('RL_FEATURE_STORE_VERSION', '1.0'), help="Version for the output feature store.")
    args = parser.parse_args()

    start_dt = datetime.fromisoformat(args.start_date.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(args.end_date.replace("Z", "+00:00"))

    asyncio.run(run_etl(start_date=start_dt, end_date=end_dt, version=args.output_version))
```

#### 📄 `__init__.py`
*path: `rl_agent_module/evaluation/__init__.py`*

_This file is empty._

#### 📄 `evaluate.py`
*path: `rl_agent_module/evaluation/evaluate.py`*

```python
# rl_agent_module/evaluation/evaluate.py
"""
Standalone script for evaluating a trained RL agent's performance using a pre-generated dataset.

This script runs a backtest of a saved agent model on the evaluation split
of a specified MLflow dataset run. It logs parameters, key performance metrics, and a
detailed quantstats report to MLflow for tracking and comparison.
"""

import argparse
import asyncio
import os
from datetime import datetime
from typing import Dict, Any

import numpy as np
import pandas as pd
import quantstats as qs
from stable_baselines3 import PPO

# --- MLflow Integration ---
import mlflow

# Project-specific imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from rl_agent_module.data.data_manager import DataManager
from rl_agent_module.environments.meme_coin_env import MemeCoinEnv
from config.rl_config import get_config_for_mode, RL_CONFIG


def _run_backtest(model: PPO, env: MemeCoinEnv) -> pd.Series:
    """
    Runs the agent through the environment and records portfolio value over time.
    """
    logger.info("Starting backtest simulation...")
    obs, _ = env.reset()
    done = False
    truncated = False
    portfolio_history = {}

    while not (done or truncated):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, truncated, info = env.step(action)
        
        # Store portfolio value at each step using the environment's timestamp
        if env.current_timestamp:
            portfolio_history[env.current_timestamp] = env.portfolio_value
        
        if done or truncated:
            logger.info("Backtest simulation finished.")
            break
            
    if not portfolio_history:
        logger.warning("Backtest resulted in no portfolio history. Cannot generate report.")
        return pd.Series(dtype=float)

    return pd.Series(portfolio_history)


def _generate_quantstats_report(
    portfolio_history: pd.Series,
    report_filename: str,
    run_name: str
) -> pd.Series:
    """
    Processes the portfolio history, generates a quantstats report, and returns key metrics.
    """
    if portfolio_history.empty or portfolio_history.isnull().all():
        logger.error("Portfolio history is empty. Cannot generate Quantstats report.")
        return pd.Series(dtype=float)

    logger.info("Generating Quantstats performance report...")
    
    portfolio_history.index = pd.to_datetime(portfolio_history.index, utc=True)
    portfolio_history = portfolio_history.loc[~portfolio_history.index.duplicated(keep='last')]
    returns = portfolio_history.pct_change().fillna(0)

    # --- FIX: Check if there were any non-zero returns ---
    # If the portfolio value never changed, returns.abs().sum() will be 0.
    if returns.abs().sum() == 0:
        logger.warning("⚠️ No trades were made, so no performance metrics can be calculated.")
        logger.warning("Quantstats report will be skipped.")
        # Return an empty Series to indicate no metrics were generated.
        return pd.Series(dtype=float)
    # --- END FIX ---
    
    try:
        title = f"RL Agent Performance ({run_name})"
        qs.reports.html(
            returns,
            benchmark=None,
            output=report_filename,
            title=title
        )
        logger.info(f"✅ Quantstats report successfully saved to: {report_filename}")
        return qs.reports.metrics(returns, display=False)
    except Exception as e:
        logger.error(f"Failed to generate Quantstats report: {e}", exc_info=True)
        return pd.Series(dtype=float)


async def run_evaluation(model_path: str, dataset_run_id: str, output_dir: str):
    """
    Main orchestration function for the evaluation process, wrapped in an MLflow run.
    """
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_BACKTESTING"])
    model_basename = os.path.splitext(os.path.basename(model_path))[0]
    run_name = f"Backtest_{model_basename}_on_DS_{dataset_run_id[:8]}"

    with mlflow.start_run(run_name=run_name) as run:
        logger.info(f"Starting evaluation run: {run.info.run_name}")

        mlflow.log_param("model_path", model_path)
        mlflow.log_param("source_dataset_run_id", dataset_run_id)
        
        setup_logging()
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at: {model_path}")
            return

        # Use a generic config mode to get environment parameters
        rl_config = get_config_for_mode('train') 

        try:
            logger.info(f"Loading pre-trained model from {model_path}...")
            model = PPO.load(model_path, device=rl_config.get("DEVICE", "cpu"))

            logger.info(f"Loading data from dataset run: {dataset_run_id}")
            data_manager = DataManager(
                rl_config=rl_config,
                dataset_run_id=dataset_run_id
            )
            if not data_manager.load_and_prepare_data():
                logger.error("Failed to load and prepare evaluation data. Aborting.")
                return
            
            data_manager.use_evaluation_data()
            evaluation_df = data_manager.get_evaluation_data()

            if evaluation_df is not None and not evaluation_df.empty:
                eval_dataset = mlflow.data.from_pandas(evaluation_df, name="evaluation_set")
                mlflow.log_input(eval_dataset, context="evaluation")
            else:
                logger.warning("Evaluation data split is empty, cannot run backtest.")
                return

            env = MemeCoinEnv(data_manager, rl_config=rl_config, silent=False)
            portfolio_history = _run_backtest(model, env)

            if not portfolio_history.empty:
                report_filename = os.path.join(output_dir, f"report_{run.info.run_id}.html")
                metrics = _generate_quantstats_report(portfolio_history, report_filename, run.info.run_name)
                
                if not metrics.empty:
                    mlflow.log_artifact(report_filename, "quantstats_report")
                    logger.info("✅ Quantstats report logged to MLflow as an artifact.")

                    key_metrics_dict = {
                        "sharpe_ratio": metrics.loc['Sharpe'],
                        "sortino_ratio": metrics.loc['Sortino'],
                        "max_drawdown_pct": metrics.loc['Max Drawdown'],
                        "cumulative_return_pct": metrics.loc['Cumulative Return'],
                        "win_rate_pct": metrics.loc['Win Rate']
                    }
                    cleaned_metrics = {k: float(v) for k, v in key_metrics_dict.items() if np.isfinite(v)}
                    mlflow.log_metrics(cleaned_metrics)
                    logger.info("✅ Key performance metrics logged to MLflow.")

        except Exception as e:
            logger.error(f"An error occurred during the evaluation process: {e}", exc_info=True)
        finally:
            logger.info("Evaluation finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a trained RL trading agent on a prepared dataset.")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the saved PPO model .zip file.")
    parser.add_argument("--dataset-run-id", type=str, required=True, help="MLflow run ID of the prepared dataset to use for the backtest.")
    parser.add_argument("--output-dir", type=str, default="data/evaluation_reports", help="Directory to save the performance report.")
    args = parser.parse_args()

    asyncio.run(run_evaluation(
        model_path=args.model_path,
        dataset_run_id=args.dataset_run_id,
        output_dir=args.output_dir
    ))
```

#### 📄 `feature_importance.py`
*path: `rl_agent_module/evaluation/feature_importance.py`*

```python
# rl_agent_module/evaluation/feature_importance.py
"""
Calculates Permutation Feature Importance and logs results to MLflow.

This script runs a backtest for multiple individual tokens to establish a baseline.
It then shuffles a feature for each token, re-runs the backtest, and averages the
performance drop across all tokens to determine the feature's importance.
Each analysis is logged as a distinct run in MLflow.
"""
import argparse
import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import random
from stable_baselines3 import PPO
from tqdm import tqdm

# --- MLflow Integration ---
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.data.pandas_dataset import PandasDataset


# --- Project-specific imports ---
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from config.rl_config import get_config_for_mode, get_active_features, RL_CONFIG
from rl_agent_module.data.data_manager import DataManager
from rl_agent_module.environments.meme_coin_env import MemeCoinEnv
from rl_agent_module.utils.script_utils import generate_config_json # Import the utility

import nest_asyncio
nest_asyncio.apply()

def run_single_token_episode(model: PPO, env: MemeCoinEnv) -> float:
    """
    Runs one full episode on the data currently loaded in the env and returns the final PnL.
    """
    obs, _ = env.reset()
    done = False
    truncated = False
    initial_value = env.initial_balance
    while not (done or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
    final_pnl = env.portfolio_value - initial_value
    return final_pnl

async def run_feature_importance(model_path: str, dataset_run_id: str, n_tokens: int, model_run_id: str):
    """
    Main orchestration function for feature importance, wrapped in an MLflow run.
    """
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_ANALYSIS"])
    model_basename = os.path.splitext(os.path.basename(model_path))[0]
    run_name = f"Importance_{model_basename}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with mlflow.start_run(run_name=run_name, log_system_metrics=True) as run:
        logger.info(f"🚀 Starting Permutation Feature Importance run '{run.info.run_name}'...")
        staging_dir = os.path.abspath(f"./.rl_staging/{run.info.run_id}")
        os.makedirs(staging_dir, exist_ok=True)
        client = MlflowClient()

        try:
            # --- 1. Log Initial Parameters & Tags ---
            # *** MODIFIED: Use the new 'importance' config mode ***
            rl_config = get_config_for_mode('importance') 
            features_to_analyze = get_active_features(rl_config)
            
            # **FIXED**: Log the persistent model URI, not the temporary path.
            model_uri = f"runs:/{model_run_id}/model"
            mlflow.log_params({
                "model_uri": model_uri,
                "n_tokens_sampled": n_tokens,
                "features_analyzed_count": len(features_to_analyze),
                "features_analyzed": features_to_analyze,
            })
            mlflow.set_tags({
                "source_model_run_id": model_run_id,
                "source_dataset_run_id": dataset_run_id
            })

            # **NEW**: Log the rl_config as an artifact, same as in train.py
            config_staging_path = os.path.join(staging_dir, "config")
            generate_config_json(rl_config, config_staging_path)

            # **NEW**: Fetch and log the parent model's training parameters
            try:
                # Use tempfile for safe download within the staging area
                param_download_path = tempfile.mkdtemp(dir=staging_dir)
                client.download_artifacts(model_run_id, "best_params.json", param_download_path)
                downloaded_params_file = os.path.join(param_download_path, "best_params.json")
                # Move it to the config staging path to be logged with other configs
                shutil.move(downloaded_params_file, os.path.join(config_staging_path, "parent_model_training_params.json"))
                logger.info("✅ Logged parent model's training parameters.")
            except Exception:
                logger.warning(f"Could not find or log 'best_params.json' from parent model run {model_run_id}.")


            # --- 2. Load Data & Log as Input ---
            logger.info(f"Loading data from dataset run '{dataset_run_id}'...")
            data_manager = DataManager(rl_config=rl_config, dataset_run_id=dataset_run_id)
            if not data_manager.load_and_prepare_data():
                raise RuntimeError("Failed to load data, aborting analysis.")

            # **NEW**: Log the evaluation dataset as an input for data lineage
            full_eval_df = data_manager.get_evaluation_data()
            if full_eval_df is None or full_eval_df.empty:
                raise RuntimeError("Evaluation data is empty. Aborting.")
            
            eval_dataset: PandasDataset = mlflow.data.from_pandas(full_eval_df, name="evaluation_set")
            mlflow.log_input(eval_dataset, context="evaluation_data")
            logger.info("✅ Logged evaluation dataset as an MLflow input.")

            # --- 3. Prepare Evaluation DataFrames per Token ---
            _, eval_mints_all = data_manager.get_split_token_mints()
            eval_token_dfs = {
                mint: df.copy() for mint, df in full_eval_df.groupby('mint') 
                if mint in eval_mints_all and not df.empty
            }
            if not eval_token_dfs:
                raise RuntimeError("Could not prepare any valid evaluation token DataFrames.")

            # --- 4. Sample Tokens and Load Model ---
            n_tokens = min(n_tokens, len(eval_token_dfs))
            eval_sample_mints = random.sample(list(eval_token_dfs.keys()), n_tokens)
            logger.info(f"Analyzing {n_tokens} randomly sampled tokens.")
            mlflow.log_param("n_tokens_actually_used", n_tokens)

            model = PPO.load(model_path, device=rl_config.get('DEVICE', 'cpu'))
            env = MemeCoinEnv(data_manager, rl_config, silent=True)

            # --- 5. Calculate Baseline Performance ---
            logger.info(f"Calculating baseline performance across {n_tokens} tokens...")
            baseline_pnls = []
            for mint in tqdm(eval_sample_mints, desc="Baseline"):
                data_manager.use_single_token_data(eval_token_dfs[mint])
                pnl = run_single_token_episode(model, env)
                baseline_pnls.append(pnl)

            baseline_mean_pnl = np.mean(baseline_pnls)
            mlflow.log_metric("baseline_mean_pnl", baseline_mean_pnl)
            logger.info(f"✅ Baseline Mean PnL: {baseline_mean_pnl:.4f} SOL")

            # --- 6. Calculate Permutation Importance ---
            importances = {}
            pbar = tqdm(features_to_analyze, desc="Shuffling Features")
            for feature in pbar:
                pbar.set_postfix_str(f"Feature: {feature}")
                shuffled_pnls = []
                for mint in eval_sample_mints:
                    original_df = eval_token_dfs[mint]
                    shuffled_df = original_df.copy()
                    shuffled_df[feature] = np.random.permutation(shuffled_df[feature].values)
                    data_manager.use_single_token_data(shuffled_df)
                    pnl = run_single_token_episode(model, env)
                    shuffled_pnls.append(pnl)
                
                shuffled_mean_pnl = np.mean(shuffled_pnls)
                importances[feature] = baseline_mean_pnl - shuffled_mean_pnl
            
            logger.info("Finished calculating all feature importances.")
            sorted_importances = sorted(importances.items(), key=lambda x: x[1], reverse=True)

            # --- 7. Save and Log Results Artifact ---
            results_data = {
                "metadata": { "timestamp_utc": datetime.now(timezone.utc).isoformat() },
                "baseline_mean_pnl": baseline_mean_pnl,
                "feature_importance_pnl_drop": [{"feature": f, "importance": i} for f, i in sorted_importances]
            }

            # Save the final report to the staging directory
            report_path = os.path.join(staging_dir, "feature_importance_report.json")
            with open(report_path, "w") as f:
                json.dump(results_data, f, indent=4)
            
            # Log all collected artifacts from the staging directory
            mlflow.log_artifacts(staging_dir, artifact_path="analysis_outputs")
            logger.info("💾 All analysis artifacts, including the report and configs, logged to MLflow.")

        except Exception as e:
            logger.error(f"An error occurred during feature analysis: {e}", exc_info=True)
            mlflow.set_tag("status", "failed")
        finally:
            # Cleanup the staging directory
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)

if __name__ == "__main__":
    setup_logging(logger_name='feature_importance')
    # --- Point to the MLflow server ---
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    #mlflow.set_tracking_uri("file:./data/rl_runs")
    
    parser = argparse.ArgumentParser(description="Calculate Permutation Feature Importance.")
    parser.add_argument("--model-run-id", type=str, required=True, help="MLflow run ID of the trained PPO model.")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the saved PPO model .zip file.")
    parser.add_argument("--dataset-run-id", type=str, required=True, help="MLflow run ID of the dataset to use for analysis.")
    parser.add_argument("--n-tokens", type=int, default=50, help="Number of random tokens to use for the analysis.")
    args = parser.parse_args()

    asyncio.run(run_feature_importance(
        model_path=args.model_path,
        dataset_run_id=args.dataset_run_id,
        n_tokens=args.n_tokens,
        model_run_id=args.model_run_id
    ))
```

#### 📄 `__init__.py`
*path: `rl_agent_module/feature_engineering/__init__.py`*

_This file is empty._

#### 📄 `features.py`
*path: `rl_agent_module/feature_engineering/features.py`*

```python
# rl_agent_module/feature_engineering/features.py
"""
Contains all functions for calculating features for the RL agent's observation space.
This module transforms raw time-series data into a feature-rich DataFrame dictionary,
with one DataFrame per token.
"""
import pandas as pd
import numpy as np
import warnings
from typing import Dict, List, Tuple
from tqdm import tqdm

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from config.rl_config import FEATURE_GROUPS, get_active_features

warnings.filterwarnings(
    "ignore",
    message="The 'grouped' keyword is deprecated and will be removed in a future version of pandas.",
    category=FutureWarning
)


def _calculate_pump_features(group: pd.DataFrame) -> pd.DataFrame:
    """Calculates time-series features for a single token's OHLCV data."""
    if group.empty:
        return pd.DataFrame()

    # Cache frequently used columns and constants
    close = group['Close']
    high = group['High']
    low = group['Low']
    volume_usd = group['volume_usd']
    buy_volume_usd = group['buy_volume_usd']
    sell_volume_usd = group['sell_volume_usd']
    
    # Constants
    window_15s = pd.Timedelta(seconds=15)
    window_30s = pd.Timedelta(seconds=30)
    epsilon = 1e-10
    
    # Pre-calculate common values
    close_shift1 = close.shift(1)
    
    # --- Rolling Price Change ---
    price_15s_ago = close.rolling(window_15s, closed='left').apply(lambda x: x.iloc[0], raw=False)
    price_change_15s = (close / price_15s_ago - 1).replace([np.inf, -np.inf], np.nan)

    price_30s_ago = close.rolling(window_30s, closed='left').apply(lambda x: x.iloc[0], raw=False)
    price_change_30s = (close / price_30s_ago - 1).replace([np.inf, -np.inf], np.nan)
    
    # --- Custom Volume Change ---
    rolling_vol_sum = volume_usd.rolling(window=window_15s, closed='left').sum()
    previous_vol_sum = rolling_vol_sum.shift(1)
    volume_change_15s = np.where(
        previous_vol_sum > 0,
        (rolling_vol_sum - previous_vol_sum) / (previous_vol_sum + epsilon),
        np.where(rolling_vol_sum > 0, 1.0, 0.0)
    )

    # --- Volatility ---
    log_returns = np.log(close / close_shift1)
    volatility_15s = log_returns.rolling(window=window_15s, closed='left').std()

    # --- Shared calculations for RSI ---
    deltas = close.diff()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    
    # RSI 3-period
    ema_gains_3 = gains.ewm(span=3, adjust=False).mean()
    ema_losses_3 = losses.ewm(span=3, adjust=False).mean()
    rs_3 = ema_gains_3 / ema_losses_3
    rsi_3 = np.where(
        ema_losses_3 > 0,
        100 - 100 / (1 + rs_3),
        np.where(ema_gains_3 > 0, 100.0, 50.0)
    )
    
    # RSI 6-period
    ema_gains_6 = gains.ewm(span=6, adjust=False).mean()
    ema_losses_6 = losses.ewm(span=6, adjust=False).mean()
    rs_6 = ema_gains_6 / ema_losses_6
    rsi_6 = np.where(
        ema_losses_6 > 0,
        100 - 100 / (1 + rs_6),
        np.where(ema_gains_6 > 0, 100.0, 50.0)
    )

    # --- True Range calculation (shared for ATR and ADX) ---
    high_low = high - low
    high_close_prev = abs(high - close_shift1)
    low_close_prev = abs(low - close_shift1)
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    
    # ATR calculations
    atr_14 = tr.ewm(span=14, adjust=False).mean()
    atr_7 = tr.ewm(span=7, adjust=False).mean()
    
    # --- CCI Calculation ---
    typical_price = (high + low + close) / 3
    typical_price_sma = typical_price.rolling(window=20).mean()
    mean_deviation = typical_price.rolling(window=20).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    )
    cci_20 = (typical_price - typical_price_sma) / (0.015 * mean_deviation + epsilon)

    # --- A/D Line Calculation ---
    high_low_safe = high - low + epsilon  # Avoid division by zero
    money_flow_multiplier = ((close - low) - (high - close)) / high_low_safe
    money_flow_volume = money_flow_multiplier * volume_usd
    ad_line = money_flow_volume.cumsum()

    # --- Buy/Sell Ratios ---
    volume_usd_safe = np.where(volume_usd > 0, volume_usd, epsilon)
    buy_sell_ratio = (buy_volume_usd - sell_volume_usd) / volume_usd_safe
    buy_sell_ratio = np.where(volume_usd > 0, buy_sell_ratio, 0.0)

    # 15s rolling buy/sell volumes
    buy_vol_15s = buy_volume_usd.rolling(window=window_15s, closed='left').sum()
    sell_vol_15s = sell_volume_usd.rolling(window=window_15s, closed='left').sum()
    total_vol_15s = buy_vol_15s + sell_vol_15s
    buy_sell_ratio_15s = np.where(total_vol_15s > 0, (buy_vol_15s - sell_vol_15s) / total_vol_15s, 0.0)

    # Transaction counts
    tx_buy_count_15s = group['tx_buy_count'].rolling(window=window_15s).sum()
    tx_sell_count_15s = group['tx_sell_count'].rolling(window=window_15s).sum()
    tx_total_count_15s = tx_buy_count_15s + tx_sell_count_15s

    # --- MACD Calculation ---
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_histogram = macd - macd_signal

    # --- Bollinger Bands ---
    rolling_mean_20 = close.rolling(window=20).mean()
    rolling_std_20 = close.rolling(window=20).std()
    bollinger_upper = rolling_mean_20 + (rolling_std_20 * 2)
    bollinger_lower = rolling_mean_20 - (rolling_std_20 * 2)
    bollinger_width = (bollinger_upper - bollinger_lower) / rolling_mean_20

    # --- EMA calculations ---
    ema_short = close.ewm(span=5, adjust=False).mean()
    ema_long = close.ewm(span=20, adjust=False).mean()

    # --- ADX Calculation ---
    high_shift1 = high.shift(1)
    low_shift1 = low.shift(1)
    
    up_move = high - high_shift1
    down_move = low_shift1 - low
    
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=group.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=group.index)
    
    periods_15s = 3
    tr_smooth = tr.rolling(window=periods_15s, min_periods=1).mean()
    plus_di = 100 * plus_dm.rolling(window=periods_15s, min_periods=1).mean() / (tr_smooth + epsilon)
    minus_di = 100 * minus_dm.rolling(window=periods_15s, min_periods=1).mean() / (tr_smooth + epsilon)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + epsilon)
    adx_15s = dx.rolling(window=periods_15s, min_periods=1).mean()

    # --- On-Balance Volume ---
    price_direction = np.where(close > close_shift1, volume_usd,
                              np.where(close < close_shift1, -volume_usd, 0))
    obv = price_direction.cumsum()

    # Construct result DataFrame efficiently using dictionary
    result_data = {
        'price_change_15s': price_change_15s,
        'price_change_30s': price_change_30s,
        'volume_change_15s': volume_change_15s,
        'volatility_15s': volatility_15s,
        'buy_sell_ratio': buy_sell_ratio,
        'buy_sell_ratio_15s': buy_sell_ratio_15s,
        'rsi_3': rsi_3,
        'rsi_6': rsi_6,
        'atr_7': atr_7,
        'atr_14': atr_14,
        'cci_20': cci_20,
        'ad_line': ad_line,
        'tx_buy_count_15s': tx_buy_count_15s,
        'tx_sell_count_15s': tx_sell_count_15s,
        'tx_total_count_15s': tx_total_count_15s,
        'macd': macd,
        'macd_signal': macd_signal,
        'macd_histogram': macd_histogram,
        'bollinger_upper': bollinger_upper,
        'bollinger_lower': bollinger_lower,
        'bollinger_width': bollinger_width,
        'ema_short': ema_short,
        'ema_long': ema_long,
        'adx_15s': adx_15s,
        'obv': obv
    }
    
    return pd.DataFrame(result_data, index=group.index)


async def calculate_all_features(
    trades_df: pd.DataFrame,
    rugcheck_df: pd.DataFrame,
    token_info_df: pd.DataFrame,
    dexscreener_df: pd.DataFrame
) -> Tuple[Dict[str, Dict[str, pd.DataFrame]], List[str]]:
    """
    Main pipeline: Processes raw data and returns a nested dictionary of
    feature group DataFrames, structured as {group_name: {mint: df}}.
    """
    if trades_df.empty:
        logger.warning("Trades DataFrame is empty. Cannot perform feature engineering.")
        return {}, []

    # --- 1. Data Cleaning & Type Conversion ---
    for df, date_col in [(trades_df, 'timestamp'), (rugcheck_df, 'timestamp'), 
                         (token_info_df, 'token_creation_time'), (dexscreener_df, 'timestamp')]:
        if not df.empty and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')

    for col in ['price_sol', 'market_cap_sol', 'volume_usd', 'sol_price_usd']:
        if not trades_df.empty and col in trades_df.columns:
            trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
        
    if not trades_df.empty and 'price_sol' in trades_df.columns:
        trades_df = trades_df[trades_df['price_sol'] > 0]
    trades_df.dropna(subset=['timestamp', 'price_sol', 'volume_usd', 'mint'], inplace=True)

    trades_df['buy_volume_usd'] = trades_df.apply(lambda row: row['volume_usd'] if row['tx_type'] == 'buy' else 0, axis=1)
    trades_df['sell_volume_usd'] = trades_df.apply(lambda row: row['volume_usd'] if row['tx_type'] == 'sell' else 0, axis=1)
    trades_df['tx_buy_count'] = trades_df['tx_type'].apply(lambda x: 1 if x == 'buy' else 0)
    trades_df['tx_sell_count'] = trades_df['tx_type'].apply(lambda x: 1 if x == 'sell' else 0)

    grouped_feature_data = {group_name: {} for group_name in FEATURE_GROUPS.keys()}
    unique_mints = trades_df['mint'].unique()
    
    logger.info(f"Starting feature engineering for {len(unique_mints)} tokens...")
    all_feature_columns = set()

    for mint in tqdm(unique_mints, desc="Processing Tokens"):
        mint_trades = trades_df[trades_df['mint'] == mint].set_index('timestamp').sort_index()
        if mint_trades.empty: continue
            
        resampler = mint_trades.resample('5s')
        ohlcv = resampler['price_sol'].ohlc()
        agg_dict = {
            'volume_usd': 'sum', 'buy_volume_usd': 'sum', 'sell_volume_usd': 'sum',
            'market_cap_sol': 'last', 'tx_buy_count': 'sum', 'tx_sell_count': 'sum',
            'sol_price_usd': 'mean' 
        }
        aggregated_data = resampler.agg(agg_dict)
        
        mint_df = pd.concat([ohlcv, aggregated_data], axis=1)
        mint_df.columns = ['Open', 'High', 'Low', 'Close', 'volume_usd', 'buy_volume_usd', 'sell_volume_usd', 'market_cap_sol', 'tx_buy_count', 'tx_sell_count', 'sol_price_avg']
        
        mint_df.interpolate(method='time', inplace=True)
        mint_df[['volume_usd', 'buy_volume_usd', 'sell_volume_usd']] = mint_df[['volume_usd', 'buy_volume_usd', 'sell_volume_usd']].fillna(0)
        mint_df.dropna(subset=['Close'], inplace=True)

        if mint_df.empty or len(mint_df) < 20: continue
            
        pump_features = _calculate_pump_features(mint_df.copy())
        mint_df = mint_df.join(pump_features, how='left')

        if not rugcheck_df.empty:
            mint_rugcheck = rugcheck_df[rugcheck_df['mint'] == mint].set_index('timestamp').sort_index()
            if not mint_rugcheck.empty:
                mint_df = pd.merge_asof(mint_df, mint_rugcheck[['rugcheck_score']], left_index=True, right_index=True, direction='backward')
            else: mint_df['rugcheck_score'] = np.nan
        
        if not token_info_df.empty:
            mint_info = token_info_df[token_info_df['mint'] == mint].iloc[0] if not token_info_df[token_info_df['mint'] == mint].empty else None
            if mint_info is not None:
                mint_df['socials_score'] = mint_info['socials_score']
                mint_df['token_creation_time'] = mint_info['token_creation_time']
                mint_df['token_age_seconds'] = (mint_df.index - mint_info['token_creation_time']).total_seconds()

        final_df = mint_df.copy()
        final_df['rugcheck_score'] = final_df['rugcheck_score'].fillna(2500) / 2500.0
        final_df['socials_score'] = final_df['socials_score'].fillna(100) / 100.0
        final_df.fillna(0, inplace=True)
        
        # *** CRITICAL FIX: Add mint as a column for identification later ***
        final_df['mint'] = mint
        all_feature_columns.update(final_df.columns)

        for group_name, features in FEATURE_GROUPS.items():
            group_cols = [f for f in features if f in final_df.columns]
            group_df = final_df[group_cols].copy()
            for col in group_df.columns: 
                group_df[col] = group_df[col].astype(np.float32) if pd.api.types.is_numeric_dtype(group_df[col]) else group_df[col]
            grouped_feature_data[group_name][mint] = group_df

    logger.info(f"Finished feature engineering for {len(unique_mints)} tokens into {len(FEATURE_GROUPS)} groups.")

    # Return the full list of generated columns
    return grouped_feature_data, sorted(list(all_feature_columns))
```

#### 📄 `__init__.py`
*path: `rl_agent_module/inference/__init__.py`*

_This file is empty._

#### 📄 `model_server.py`
*path: `rl_agent_module/inference/model_server.py`*

```python
# rl_agent_module/inference/model_server.py
"""
Manages the lifecycle of the production RL model for live inference.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import numpy as np
from stable_baselines3 import PPO

import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from bot_logger import logger


class RLModelServer:
    """
    A thread-safe server for loading a trained RL model and providing actions.

    This class encapsulates a Stable Baselines 3 model, providing a simple
    interface for getting predictions. It includes a crucial "hot-swap"
    feature to update the model on-the-fly without downtime, which is essential
    for continuous operation and retraining cycles.
    """

    def __init__(self, model_path: str, device: str = 'cpu'):
        """
        Initializes the RLModelServer.

        Args:
            model_path: The initial path to the trained model's .zip file.
            device: The computation device ('cpu' or 'cuda'). 'cpu' is
                    recommended for inference unless high throughput is needed.
        """
        self.model_path: Optional[str] = model_path
        self.device = device
        self.model: Optional[PPO] = None
        self.last_update_time: Optional[datetime] = None
        self.lock = asyncio.Lock()  # Lock to ensure atomic operations on the model

        self._load_initial_model()

    def _load_initial_model(self):
        """Loads the model specified during initialization."""
        logger.info(f"Attempting to load initial RL model from: {self.model_path}")
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Initial model file not found: {self.model_path}")
                return

            self.model = PPO.load(self.model_path, device=self.device)
            self.last_update_time = datetime.now(timezone.utc)
            logger.info(f"✅ Successfully loaded initial RL model. Ready for inference on '{self.device}'.")
        except Exception as e:
            logger.error(f"❌ Failed to load initial RL model from {self.model_path}: {e}", exc_info=True)
            self.model = None
            self.model_path = None

    async def get_action(self, observation: np.ndarray) -> Optional[np.ndarray]:
        """
        Predicts the next action for a given observation in a thread-safe manner.

        Args:
            observation: The current observation from the environment.

        Returns:
            The predicted action as a numpy array, or None if no model is loaded.
        """
        async with self.lock:
            if self.model is None:
                logger.warning("get_action called, but no model is loaded.")
                return None

            try:
                # Use deterministic=True for inference to get the most likely action
                action, _states = self.model.predict(observation, deterministic=True)
                return action
            except Exception as e:
                logger.error(f"Error during model prediction: {e}", exc_info=True)
                return None

    async def hot_swap_model(self, new_model_path: str) -> bool:
        """
        Atomically updates the currently loaded model with a new one from a file.

        This method is safe to call concurrently. It first loads the new model
        into memory. Only upon a successful load does it replace the existing
        model, ensuring the server remains operational even if the new model
        file is corrupted or invalid.

        Args:
            new_model_path: The file path to the new .zip model file.

        Returns:
            True if the model was successfully updated, False otherwise.
        """
        logger.info(f"Attempting to hot-swap model with: {new_model_path}")

        if not os.path.exists(new_model_path):
            logger.error(f"Hot-swap failed: New model file not found at '{new_model_path}'.")
            return False
            
        async with self.lock:
            if new_model_path == self.model_path:
                logger.warning("Hot-swap skipped: New model path is the same as the current one.")
                return True

            try:
                # Load the new model into a temporary variable first.
                # This is a critical safety check.
                new_model = PPO.load(new_model_path, device=self.device)

                # If loading succeeds, replace the old model and update metadata.
                self.model = new_model
                self.model_path = new_model_path
                self.last_update_time = datetime.now(timezone.utc)
                logger.info(f"✅ Model hot-swap successful. Now using model from '{new_model_path}'.")
                return True
            except Exception as e:
                logger.error(f"❌ Hot-swap failed: Could not load the new model. The server will continue using the old model. Error: {e}", exc_info=True)
                return False

    async def get_status(self) -> Dict[str, Any]:
        """
        Retrieves the current status of the model server in a thread-safe manner.

        Returns:
            A dictionary containing the server's status.
        """
        async with self.lock:
            return {
                "is_model_loaded": self.model is not None,
                "model_path": self.model_path,
                "device": self.device,
                "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None
            }
```

#### 📄 `mlflow_model.py`
*path: `rl_agent_module/mlflow_model.py`*

```python
"""
Custom MLflow pyfunc wrapper for Stable-Baselines3 PPO models so they can be
logged, versioned, and served via the MLflow Model Registry.

Usage:
    from rl_agent.mlflow_model import log_sb3_model
    log_sb3_model(model, run_name, signature_dict, input_example, extra_artifacts)
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import mlflow
from mlflow import pyfunc
from mlflow.models.signature import ModelSignature, infer_signature
from mlflow.types import Schema, ColSpec

from stable_baselines3 import PPO


class SB3PPOWrapper(pyfunc.PythonModel):
    """A minimal pyfunc wrapper that loads and predicts with a PPO .zip."""

    def load_context(self, context):  # type: ignore[override]
        model_path = os.path.join(context.artifacts["sb3_zip"])  # full path
        self.model = PPO.load(model_path, device="cpu")

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        """
        Generates predictions from the model. The input is passed directly
        to the wrapped SB3 model's predict method.
        """
        # The SB3 PPO model's predict method can handle both single observations
        # (e.g., a NumPy array) and batches (e.g., a DataFrame or 2D array).
        # We pass the input directly without iteration.
        action, _ = self.model.predict(model_input, deterministic=True)
        return action


def _ensure_signature(signature_dict: Optional[Dict[str, Any]], input_example) -> ModelSignature:
    if signature_dict:
        inputs = Schema([ColSpec(x["type"], x["name"]) for x in signature_dict["inputs"]])
        outputs = Schema([ColSpec(x["type"], x["name"]) for x in signature_dict["outputs"]])
        return ModelSignature(inputs=inputs, outputs=outputs)
    # Fallback: infer from example
    return infer_signature(input_example, np.zeros((len(getattr(input_example, "shape", [1])), 1)))


def log_sb3_model(
    model: PPO,
    run_name: str,
    signature_dict: Optional[Dict[str, Any]] = None,
    input_example: Optional[Any] = None,
    extra_artifacts: Optional[Dict[str, str]] = None,
    register_as: Optional[str] = None,
    staging_path: Optional[str] = None
) -> str:
    """Logs a PPO model as an MLflow pyfunc and optionally registers it.

    Returns the `model_uri` (e.g., "runs:/<run_id>/model").
    """
    run = mlflow.active_run()
    if run is None:
        raise RuntimeError("log_sb3_model must be called inside an active MLflow run")

    # Use the provided staging_path for the temporary directory
    with tempfile.TemporaryDirectory(dir=staging_path) as tmp:
        sb3_zip = os.path.join(tmp, "model.zip")
        model.save(sb3_zip)

        artifacts = {"sb3_zip": sb3_zip}
        if extra_artifacts:
            artifacts.update(extra_artifacts)

        signature = None
        if input_example is not None:
            signature = _ensure_signature(signature_dict, input_example)

        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=SB3PPOWrapper(),
            artifacts=artifacts,
            signature=signature,
            input_example=input_example,
        )

    model_uri = f"runs:/{run.info.run_id}/model"

    if register_as:
        mv = mlflow.register_model(model_uri, register_as)
        mlflow.set_tag("registered_model_name", register_as)
        mlflow.set_tag("registered_model_version", mv.version)
        return f"models:/{register_as}/{mv.version}"

    return model_uri
```

#### 📄 `__init__.py`
*path: `rl_agent_module/rewards/__init__.py`*

_This file is empty._

#### 📄 `reward_function.py`
*path: `rl_agent_module/rewards/reward_function.py`*

```python
# rl_agent_module/rewards/reward_function.py
"""
Implements the multi-objective reward function for the RL agent.
"""
import numpy as np
from typing import Dict, Any

class RewardFunction:
    """
    Calculates the reward for the agent based on a weighted sum of different objectives.
    Combines a dense, step-wise reward with sparse rewards on completed trades.
    """
    def __init__(self, config: Dict[str, Any]):
        self.rl_config = config
        # Use a small epsilon to avoid division by zero
        self.epsilon = 1e-9
        self.previous_portfolio_value = self.rl_config.get('ENV_INITIAL_BALANCE', 100.0)

    def calculate_reward(self, trade_result: Dict, current_state: Dict, current_portfolio_value: float) -> float:
        """
        Calculates the total reward for a completed trade or a timestep.
        """
        # --- 1. Dense Reward (Portfolio Value Change) ---
        # This provides a continuous feedback signal at every step.
        portfolio_change_pct = (current_portfolio_value / max(self.previous_portfolio_value, self.epsilon)) - 1.0
        dense_reward = portfolio_change_pct * self.rl_config.get('REWARD_DENSE_WEIGHT', 1.0)
        self.previous_portfolio_value = current_portfolio_value

        # --- 2. Sparse Reward (On Completed Trades) ---
        sparse_reward = 0.0
        if trade_result:
            pnl_component = self._calculate_pnl_reward(trade_result)
            risk_component = self._calculate_risk_adjusted_reward(trade_result, current_state)
            pos_mgmt_component = self._calculate_position_management_reward(trade_result)
            exec_component = self._calculate_execution_quality_reward(trade_result)

            sparse_reward = (
                self.rl_config.get('REWARD_PNL_WEIGHT', 0.5) * pnl_component +
                self.rl_config.get('REWARD_RISK_WEIGHT', 0.2) * risk_component +
                self.rl_config.get('REWARD_POSITION_MANAGEMENT_WEIGHT', 0.2) * pos_mgmt_component +
                self.rl_config.get('REWARD_EXECUTION_WEIGHT', 0.1) * exec_component
            )
        
        # --- 3. Combine Rewards ---
        total_reward = dense_reward + (sparse_reward * self.rl_config.get('REWARD_SPARSE_WEIGHT', 0.2))
        return total_reward

    def _calculate_pnl_reward(self, trade_result: Dict) -> float:
        """Calculates reward based on the profit and loss of a trade."""
        pnl = trade_result.get('pnl', 0.0)
        max_pnl = self.rl_config.get('MAX_EXPECTED_PNL_PER_TRADE_SOL', 1.0)
        return np.tanh(pnl / max(max_pnl, self.epsilon))

    def _calculate_risk_adjusted_reward(self, trade_result: Dict, state: Dict) -> float:
        """Penalizes trades on high-risk tokens."""
        pnl = trade_result.get('pnl', 0.0)
        rugcheck_risk = state.get('rugcheck_score', 1.0)
        social_risk = state.get('socials_score', 1.0)
        combined_risk = (rugcheck_risk * 0.7) + (social_risk * 0.3)
        
        if pnl > 0:
            return -pnl * combined_risk * 0.5
        else:
            return pnl * (1 + combined_risk)

    def _calculate_position_management_reward(self, trade_result: Dict) -> float:
        """Rewards effective position management."""
        if trade_result.get('side') == 'sell':
            price_to_highest = trade_result.get('price_to_highest_ratio', 1.0)
            profit_timing_reward = 1.0 - abs(0.9 - price_to_highest)
            return profit_timing_reward
        return 0

    def _calculate_execution_quality_reward(self, trade_result: Dict) -> float:
        """Penalizes for high slippage."""
        # This is a placeholder as slippage is not yet in trade_result
        return 0.0

    def reset(self, initial_portfolio_value: float):
        """Resets the internal state of the reward function for a new episode."""
        self.previous_portfolio_value = initial_portfolio_value
```

#### 📄 `__init__.py`
*path: `rl_agent_module/training/__init__.py`*

_This file is empty._

#### 📄 `train.py`
*path: `rl_agent_module/training/train.py`*

```python
# rl_agent_module/training/train.py
"""
Main script for the RL agent training workflow, centered around MLflow.

This script orchestrates the entire process from hyperparameter tuning to final
model training, continuation, and fine-tuning. It relies on MLflow as the
single source of truth for all experiment artifacts.

--------------------------------------------------------------------------------------
WORKFLOW INSTRUCTIONS
--------------------------------------------------------------------------------------
PRE-REQUISITE: DATA PREPARATION
Before running any training, the feature store must be populated using the ETL script.
This creates a dataset run in MLflow.

    Command (via rl_main.py):
    > 0) Generate/Update Feature Store (ETL)

PHASE 1: HYPERPARAMETER TUNING (tune)
Find the best model settings using Optuna, with all trials logged to MLflow.
Requires a dataset run ID to source the data.

    Command (via rl_main.py):
    > 1) Start Hyperparameter Tuning (Optuna)

PHASE 2: NEW MODEL TRAINING (train)
Train a new model from scratch using the best parameters from a tuning run.

    Command (via rl_main.py):
    > 2) Train a New Model

PHASE 3 & 4: CONTINUE OR FINETUNE
Resume a previous training run or fine-tune an existing model.

    Command (via rl_main.py):
    > 3) Continue Training a Model
    > 4) Perform Model Fine-Tuning
"""
import asyncio
import json
import os
import sys
import argparse
import time
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List
from functools import partial
import pandas as pd
import multiprocessing
import random

# --- Project Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Third-Party Imports ---
import numpy as np
import optuna
import torch as th
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, CallbackList
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.evaluation import evaluate_policy
from optuna.samplers import TPESampler
from stable_baselines3.common.logger import configure

# --- MLflow Integration ---
import mlflow
from mlflow.tracking import MlflowClient
from rl_agent_module.mlflow_model import log_sb3_model
from mlflow.data.pandas_dataset import PandasDataset
from mlflow.entities import RunStatus

# --- Local Application Imports ---
import nest_asyncio
from config.rl_config import get_config_for_mode, RL_CONFIG
from bot_logger import logger, setup_logging
from rl_agent_module.agents.ppo_agent import create_ppo_agent
from rl_agent_module.data.data_manager import DataManager
from rl_agent_module.environments.meme_coin_env import MemeCoinEnv
from rl_agent_module.utils.mlflow_utils import get_parent_run_info, build_tensorboard_command, find_mlflow_entity_by_run_id
from rl_agent_module.utils.script_utils import generate_tensorboard_launch_scripts, generate_readme, generate_config_json

# Apply asyncio patch for environments that use it internally
nest_asyncio.apply()

MLFLOW_EXPERIMENT_DATASET = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_DATASET"]



# ==============================================================================
# Helper Functions & Callbacks
# ==============================================================================

class AdvancedMlflowCallback(EvalCallback):
    """Logs key training and evaluation metrics to MLflow during the training loop."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_eval_reward = -np.inf

    def _on_step(self) -> bool:
        for key in ["train/entropy_loss", "train/value_loss", "train/policy_gradient_loss", "train/approx_kl", "train/clip_fraction", "train/learning_rate"]:
            if key in self.logger.name_to_value:
                mlflow.log_metric(key.replace("/", "_"), self.logger.name_to_value[key], step=self.num_timesteps)

        for info in self.locals.get("infos", []):
            if "episode" in info:
                mlflow.log_metric("rollout_ep_rew_mean", info["episode"]["r"], step=self.num_timesteps)
                mlflow.log_metric("rollout_ep_len_mean", info["episode"]["l"], step=self.num_timesteps)
        
        if not super()._on_step():
            return False

        if self.last_mean_reward != self._last_eval_reward:
            mlflow.log_metric("eval_mean_reward", self.last_mean_reward, step=self.num_timesteps)
            ep_lengths = self.eval_env.get_attr("episode_lengths")
            if ep_lengths and ep_lengths[0]:
                 mlflow.log_metric("eval_mean_ep_length", np.mean(ep_lengths[0]), step=self.num_timesteps)
            self._last_eval_reward = self.last_mean_reward
        return True


def find_latest_dataset_run() -> mlflow.entities.Run | None:
    """Finds the most recent successful MLflow run from the dataset generation experiment."""
    client = MlflowClient()
    try:
        exp = client.get_experiment_by_name(MLFLOW_EXPERIMENT_DATASET)
        if not exp:
            logger.error(f"MLflow experiment '{ MLFLOW_EXPERIMENT_DATASET }' not found.")
            return None
        
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=["start_time DESC"],
            max_results=1
        )
        return runs[0] if runs else None
    except Exception as e:
        logger.error(f"Could not fetch dataset run from MLflow: {e}", exc_info=True)
        return None


# ==============================================================================
# Optuna Objective for Hyperparameter Tuning
# ==============================================================================

def _valid_batch_sizes(n_steps: int, n_envs: int) -> List[int]:
    """Calculates valid batch sizes for PPO."""
    candidates = [32, 64, 128, 256, 512, 1024]
    total = n_steps * n_envs
    return [b for b in candidates if total % b == 0 and b <= total]

def sample_ppo_params(trial: optuna.trial.Trial, n_envs: int) -> Dict[str, Any]:
    """Defines the hyperparameter search space for Optuna."""
    n_steps = trial.suggest_categorical("n_steps", [1024, 2048, 4096])
    valid_bs = _valid_batch_sizes(n_steps, n_envs)
    if not valid_bs: raise optuna.exceptions.TrialPruned("No valid batch_size.")
    
    batch_size = trial.suggest_categorical("batch_size", valid_bs)
    pi_vf_layers = trial.suggest_categorical("pi_vf_layers", ["64,64", "128,128", "256,256"])
    
    return {
        "n_steps": n_steps, "batch_size": batch_size,
        "gamma": trial.suggest_float("gamma", 0.95, 0.9999),
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "ent_coef": trial.suggest_float("ent_coef", 1e-6, 1e-2, log=True),
        "gae_lambda": trial.suggest_float("gae_lambda", 0.8, 0.99),
        "clip_range": trial.suggest_float("clip_range", 0.1, 0.3),
        "vf_coef": trial.suggest_float("vf_coef", 0.5, 1.0),
        "max_grad_norm": trial.suggest_float("max_grad_norm", 0.3, 1.0),
        "policy_kwargs": {
            "activation_fn": "ReLU",
            "net_arch": {
                "pi": list(map(int, pi_vf_layers.split(','))),
                "vf": list(map(int, pi_vf_layers.split(',')))
            }
        },
    }

def objective(trial: optuna.trial.Trial, rl_config: Dict, train_mints: List[str], eval_mints: List[str], dataset_run_id: str) -> float:
    """An Optuna objective function that trains and evaluates a model for one trial."""
    with mlflow.start_run(nested=True, log_system_metrics=True):
        train_env, eval_env = None, None
        try:
            mlflow.log_params(rl_config)
            mlflow.log_param("action", "tuning")

            train_subset = random.sample(train_mints, min(len(train_mints), 50))
            eval_subset = random.sample(eval_mints, min(len(eval_mints), 10))
            
            train_dm = DataManager(rl_config, dataset_run_id=dataset_run_id)
            train_dm.load_and_prepare_data(mints_to_load=train_subset, verbose=False)
            train_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(train_dm, rl_config, silent=True))])
            
            params = sample_ppo_params(trial, n_envs=1)
            if params["policy_kwargs"]["activation_fn"] == 'ReLU':
                params["policy_kwargs"]["activation_fn"] = th.nn.ReLU
            mlflow.log_params(params)
            
            model = PPO("MlpPolicy", train_env, device=rl_config.get('DEVICE', 'cpu'), verbose=0, **params)
            model.learn(total_timesteps=rl_config['PPO_TIMESTEPS_PER_TRIAL'])
            
            eval_dm = DataManager(rl_config, dataset_run_id=dataset_run_id)
            eval_dm.load_and_prepare_data(mints_to_load=eval_subset, verbose=False)
            eval_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(eval_dm, rl_config, silent=True))])
            
            datasets, contexts, tags_list = [], [], []

            training_data = train_dm.get_training_data()
            if training_data is not None and not training_data.empty:
                train_dataset: PandasDataset = mlflow.data.from_pandas(training_data, name=f"training_set")
                datasets.append(train_dataset)
                contexts.append(f"training_set")
                tags_list.append({"num_tokens": str(len(train_mints))})

            eval_data = eval_dm.get_evaluation_data()
            if eval_data is not None and not eval_data.empty:
                eval_dataset: PandasDataset = mlflow.data.from_pandas(eval_data, name=f"evaluation_set")
                datasets.append(eval_dataset)
                contexts.append(f"evaluation_set")
                tags_list.append({"num_tokens": str(len(eval_mints))})

            if datasets:
                mlflow.log_inputs(
                    datasets=datasets,
                    contexts=contexts,
                    tags_list=tags_list
                )
            
            mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=5, deterministic=True)
            if not np.isfinite(mean_reward):
                raise optuna.exceptions.TrialPruned("Reward is not finite.")
            
            mlflow.log_metric("final_mean_reward", float(mean_reward))
            return float(mean_reward)
        except optuna.exceptions.TrialPruned as e:
            raise e
        finally:
            if train_env: train_env.close()
            if eval_env: eval_env.close()

# ==============================================================================
# Main Workflow Functions
# ==============================================================================

async def run_hyperparameter_tuning(rl_config: Dict[str, Any], dataset_run_id: str):
    """Orchestrates the Optuna hyperparameter tuning process."""
    logger.info("PHASE 1: Starting Hyperparameter Tuning.")
    
    data_provider = DataManager(rl_config=rl_config, dataset_run_id=dataset_run_id)
    if not data_provider.load_and_prepare_data():
        logger.error("Failed to load data. Aborting tuning."); return
    train_mints, eval_mints = data_provider.get_split_token_mints()

    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TUNING"])
    with mlflow.start_run(run_name=f"OptunaStudy_{datetime.now().strftime('%Y%m%d-%H%M%S')}", log_system_metrics=True):
        mlflow.log_params({"n_trials": rl_config['OPTUNA_N_TRIALS'], "timeout": rl_config['OPTUNA_TIMEOUT_SECONDS']})
        mlflow.set_tag("source_dataset_run_id", dataset_run_id)
        
        study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
        objective_with_args = partial(objective, rl_config=rl_config, train_mints=train_mints, eval_mints=eval_mints, dataset_run_id=dataset_run_id)
        study.optimize(objective_with_args, n_trials=rl_config['OPTUNA_N_TRIALS'], n_jobs=1, gc_after_trial=True)

        logger.info(f"Tuning finished. Best trial: #{study.best_trial.number} with reward: {study.best_trial.value:.4f}")
        mlflow.log_params(study.best_trial.params)
        mlflow.log_metric("best_trial_value", study.best_trial.value)
        
        best_params = study.best_trial.params
        if 'policy_kwargs' in best_params and 'activation_fn' in best_params['policy_kwargs']:
            if not isinstance(best_params['policy_kwargs']['activation_fn'], str):
                 best_params['policy_kwargs']['activation_fn'] = 'ReLU'

        mlflow.log_dict(best_params, "best_params.json")
        logger.info("✅ Best hyperparameters logged to MLflow as 'best_params.json'.")


def make_env_lazy(rank: int, rl_config: Dict, mint_chunks: List[List[str]], dataset_run_id: str, seed: int = 0):
    """Factory function to create a lazy-loading environment for a subprocess."""
    def _init():
        data_manager = DataManager(rl_config=rl_config, dataset_run_id=dataset_run_id)
        data_manager.load_and_prepare_data(mints_to_load=mint_chunks[rank], verbose=False)
        env = MemeCoinEnv(data_manager, rl_config, silent=True)
        env.reset(seed=seed + rank)
        return Monitor(env)
    return _init

async def run_model_training(rl_config: Dict[str, Any], args: argparse.Namespace):
    """Orchestrates the main model training, continuation, or fine-tuning process."""
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TRAINING"])
    client = MlflowClient()
    
    with mlflow.start_run(run_name=f"{args.name}-{args.action}", log_system_metrics=True) as run:
        logger.info(f"Starting model '{args.action}' with MLflow run '{run.info.run_name}'.")
        staging_dir = os.path.abspath(f"./.rl_staging/{run.info.run_id}")
        os.makedirs(staging_dir, exist_ok=True)
        
        vec_env, eval_env = None, None
        try:
            
            mlflow.log_params(rl_config)

            srl_config_staging = os.path.join(staging_dir, "config")
            generate_config_json(rl_config, srl_config_staging)
            mlflow.log_artifacts(srl_config_staging, artifact_path="config")

            mlflow.log_param("action", args.action)

            current_run_name = run.data.tags.get("mlflow.runName", f"model_{run.info.run_id}")
            tensorboard_staging_path = os.path.join(staging_dir, "tensorboard_logs")

            parent_run_infos = []
            if hasattr(args, 'parent_run_id') and args.parent_run_id:
                parent_run_infos = get_parent_run_info(args.parent_run_id, client)

            initial_cmd = build_tensorboard_command(
                current_run_id=run.info.run_id,
                current_run_name=current_run_name,
                parent_run_infos=parent_run_infos,
                current_tensorboard_path=tensorboard_staging_path,
                client=client
            )
            logger.info(f"Run the Training TensorBoard UI with this command:\n`cmd:{initial_cmd}`")
            print(initial_cmd)

            mlflow.set_tag("source_dataset_run_id", args.dataset_run_id)

            if hasattr(args, 'parent_run_id') and args.parent_run_id:
                mlflow.set_tag("continued_from", args.parent_run_id)
            if hasattr(args, 'params_path') and args.params_path:
                mlflow.log_artifact(args.params_path, "config")

            dataset_run = find_mlflow_entity_by_run_id(args.dataset_run_id)
            if not dataset_run:
                logger.error("No dataset run found with ID: %s. Aborting.", args.dataset_run_id)
                return
            
            datasets, contexts, tags_list = [], [], []

            data_manager = DataManager(rl_config, dataset_run_id=args.dataset_run_id)
            if not data_manager.load_and_prepare_data(): return

            train_mints, eval_mints = data_manager.get_split_token_mints()

            training_data = data_manager.get_training_data()
            if training_data is not None and not training_data.empty:
                train_dataset: PandasDataset = mlflow.data.from_pandas(training_data, name=f"training_set")
                datasets.append(train_dataset)
                contexts.append(f"training_set")
                tags_list.append({"num_tokens": str(len(train_mints))})

            eval_data = data_manager.get_evaluation_data()
            if eval_data is not None and not eval_data.empty:
                eval_dataset: PandasDataset = mlflow.data.from_pandas(eval_data, name=f"evaluation_set")
                datasets.append(eval_dataset)
                contexts.append(f"evaluation_set")
                tags_list.append({"num_tokens": str(len(eval_mints))})

            if datasets:
                mlflow.log_inputs(
                    datasets=datasets,
                    contexts=contexts,
                    tags_list=tags_list
                )

            n_cpu = rl_config['N_CPU']
            mint_chunks = [c.tolist() for c in np.array_split(train_mints, n_cpu) if c.size > 0]
            
            # --- SAFETY CHECK: Ensure N_CPU is not too high for the dataset size ---
            if not mint_chunks:
                logger.error(f"Cannot train with N_CPU={n_cpu} as there are not enough tokens to split ({len(train_mints)} available).")
                logger.error("Please reduce N_CPU or use a larger dataset.")
                return
            
            vec_env = SubprocVecEnv([make_env_lazy(i, rl_config, mint_chunks, args.dataset_run_id) for i in range(len(mint_chunks))])
            eval_env = DummyVecEnv([make_env_lazy(0, rl_config, [eval_mints], args.dataset_run_id)])

            model, reset_num_timesteps = None, True

            if args.action == 'train':
                with open(args.params_path, 'r') as f: hyperparams = json.load(f)
                model = create_ppo_agent(vec_env, hyperparams, rl_config['DEVICE'], tensorboard_staging_path)
            elif args.action in ['continue', 'finetune']:
                model = PPO.load(args.model_path, env=vec_env, device=rl_config['DEVICE'])
                model.set_logger(configure(tensorboard_staging_path, ["tensorboard"]))
                reset_num_timesteps = False
                if args.action == 'finetune' and hasattr(args, 'learning_rate') and args.learning_rate:
                    model.learning_rate = args.learning_rate

            if not model: 
                logger.error("Model could not be initialized. Aborting.")
                return

            chk_cb = CheckpointCallback(max(rl_config['PPO_EVAL_FREQ']//n_cpu,1), os.path.join(staging_dir, "models"), "checkpoint")
            adv_cb = AdvancedMlflowCallback(eval_env, best_model_save_path=os.path.join(staging_dir, "models"), log_path=os.path.join(staging_dir, "logs"), eval_freq=max(rl_config['PPO_EVAL_FREQ']//n_cpu,1))
            
            logger.info("🚀 Starting model training...")
            model.learn(
                total_timesteps=rl_config['PPO_FINAL_MODEL_TIMESTEPS'], 
                callback=CallbackList([chk_cb, adv_cb]), 
                reset_num_timesteps=reset_num_timesteps,
                tb_log_name=args.name
            )

            final_model_path = os.path.join(staging_dir, "models", "final_model.zip")
            model.save(final_model_path)

            for item in os.listdir(staging_dir):
                item_path = os.path.join(staging_dir, item)
                if os.path.isdir(item_path):
                    mlflow.log_artifacts(item_path, artifact_path=item)

            current_artifact_uri = run.info.artifact_uri.rstrip("/")
            final_tensorboard_path = f"{current_artifact_uri}/tensorboard_logs"

            final_cmd = build_tensorboard_command(
                current_run_id=run.info.run_id,
                current_run_name=current_run_name,
                parent_run_infos=parent_run_infos,
                current_tensorboard_path=final_tensorboard_path,
                client=client
            )

            mlflow.log_param("tensorboard_log_command", final_cmd)

            scripts_staging = os.path.join(staging_dir, "scripts")
            generate_tensorboard_launch_scripts(final_cmd, scripts_staging)
            generate_readme(final_cmd, scripts_staging)
            mlflow.log_artifacts(scripts_staging, artifact_path="scripts")

            best_model_path = os.path.join(staging_dir, "models", "best_model.zip")
            model_to_log = PPO.load(best_model_path if os.path.exists(best_model_path) else final_model_path)
            
            obs = eval_env.reset()
            input_example = np.asarray(obs[0] if isinstance(obs, np.ndarray) and obs.ndim > 1 else obs)
            
            log_sb3_model(
                model_to_log, 
                args.name, 
                input_example=input_example, 
                staging_path=staging_dir,
                register_as=args.register_as
            )

            logger.info("✅ Training finished. Model and results logged to MLflow.")
        finally:
            if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
            if vec_env: vec_env.close()
            if eval_env: eval_env.close()

# ==============================================================================
# Script Entry Point
# ==============================================================================
async def main():
    """Parses command-line arguments and calls the appropriate workflow function."""
    parser = argparse.ArgumentParser(description="RL Agent Training Workflow")
    subparsers = parser.add_subparsers(dest="action", required=True)
    
    # --- Shared parser for hardware and common training arguments ---
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--dataset-run-id", required=True, help="MLflow run ID of the dataset to use.")
    common_parser.add_argument("--register-as", help="If provided, registers the model with this name.")
    common_parser.add_argument("--device", type=str, help="Override the computation device (e.g., 'cuda', 'cpu').")
    common_parser.add_argument("--n-cpu", type=int, help="Override the number of CPU cores to use.")
    
    p_tune = subparsers.add_parser("tune", help="Run hyperparameter tuning.")
    p_tune.add_argument("--dataset-run-id", required=True, help="MLflow run ID of the dataset to use.")
    
    p_train = subparsers.add_parser("train", help="Train a new model.", parents=[common_parser])
    p_train.add_argument("--params-path", required=True); p_train.add_argument("--name", default="PPO_Model")
    
    p_cont = subparsers.add_parser("continue", help="Continue training.", parents=[common_parser])
    p_cont.add_argument("--model-path", required=True); p_cont.add_argument("--parent-run-id", required=True); p_cont.add_argument("--name", default="PPO_Model")

    p_fine = subparsers.add_parser("finetune", help="Fine-tune a model.", parents=[common_parser])
    p_fine.add_argument("--model-path", required=True); p_fine.add_argument("--parent-run-id", required=True); p_fine.add_argument("--name", default="PPO_Model"); p_fine.add_argument("--learning-rate", type=float)

    args = parser.parse_args()
    rl_config = get_config_for_mode(args.action)

    # --- Override config with command-line arguments if provided ---
    # This logic is now centralized here for all workflows
    if hasattr(args, 'device') and args.device:
        rl_config['DEVICE'] = args.device
        logger.info(f"Overriding DEVICE with command-line value: '{args.device}'")
    if hasattr(args, 'n_cpu') and args.n_cpu is not None:
        rl_config['N_CPU'] = args.n_cpu
        logger.info(f"Overriding N_CPU with command-line value: {args.n_cpu}")

    if args.action == 'tune': 
        await run_hyperparameter_tuning(rl_config, args.dataset_run_id)
    else: 
        await run_model_training(rl_config, args)

if __name__ == "__main__":
    setup_logging(logger_name='rl_training')
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    if sys.platform in ['win32', 'darwin']: multiprocessing.freeze_support()
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("Process interrupted by user.")
```

#### 📄 `hardware_advisor.py`
*path: `rl_agent_module/utils/hardware_advisor.py`*

```python
import json
import platform
import os
import sys
import argparse
from urllib.parse import urlparse

try:
    import psutil
except ImportError:
    print("psutil not installed. Please install it via pip install psutil.")
    raise

try:
    import torch
except ImportError:
    print("torch not installed. Please install it via pip install torch.")
    raise

import mlflow
from mlflow.tracking import MlflowClient

# --- Project Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.rl_config import get_active_features, FEATURE_GROUPS
from bot_logger import logger, setup_logging

# Dynamically create the reverse mapping
FEATURE_TO_GROUP_MAP = {
    feature: group_name
    for group_name, features in FEATURE_GROUPS.items()
    for feature in features
}

class SystemInfoCollector:
    # ... (This class is unchanged)
    def __init__(self):
        self.data = {}
    def collect_cpu_info(self):
        self.data['cpu'] = {'physical_cores': psutil.cpu_count(logical=False)}
    def collect_ram_info(self):
        vm = psutil.virtual_memory()
        self.data['ram'] = {'total_gb': round(vm.total / (1024 ** 3), 2), 'available_gb': round(vm.available / (1024 ** 3), 2)}
    def collect_cuda_info(self):
        cuda_available = torch.cuda.is_available()
        self.data['cuda'] = {'available': cuda_available}
        if cuda_available:
            self.data['cuda']['device_count'] = torch.cuda.device_count()
            self.data['cuda']['devices'] = [{'name': torch.cuda.get_device_properties(i).name} for i in range(torch.cuda.device_count())]
    def collect_all(self) -> dict:
        self.collect_cpu_info()
        self.collect_ram_info()
        self.collect_cuda_info()
        return self.data

class RLHardwareAdvisor:
    # ... (This class is unchanged)
    IN_MEMORY_FACTOR = 2.5
    PROCESS_OVERHEAD_GB = 0.7
    def __init__(self, sys_info: dict, dataset_gb: float, safety_margin: float):
        self.sys_info = sys_info
        self.dataset_gb = dataset_gb
        self.safety_margin = safety_margin
        self.recommendations = {}
    def analyze(self):
        self._recommend_device()
        self._recommend_n_cpu()
        return self.recommendations
    def _recommend_device(self):
        if self.sys_info.get('cuda', {}).get('available'): self.recommendations['DEVICE'] = 'cuda'
        else: self.recommendations['DEVICE'] = 'cpu'
    def _recommend_n_cpu(self):
        usable_ram = self.sys_info['ram']['available_gb'] * self.safety_margin
        physical_cores = self.sys_info['cpu']['physical_cores']
        total_data_in_memory_gb = self.dataset_gb * self.IN_MEMORY_FACTOR
        self.recommendations['breakdown'] = []
        safe_cpu_options = []
        for n_cpu in range(1, physical_cores + 1):
            total_estimated_ram = total_data_in_memory_gb + (self.PROCESS_OVERHEAD_GB * n_cpu)
            status = "✅ OK" if total_estimated_ram < usable_ram else "❌ TOO HIGH"
            self.recommendations['breakdown'].append({"N_CPU": n_cpu, "Total_Est_RAM_GB": total_estimated_ram, "Status": status})
            if status == "✅ OK": safe_cpu_options.append(n_cpu)
        if safe_cpu_options: self.recommendations['N_CPU'] = max(safe_cpu_options)
        else:
            self.recommendations['N_CPU'] = 0
            if total_data_in_memory_gb > usable_ram: self.recommendations['analysis_notes'] = "WARNING: Dataset too large for available RAM."
            else: self.recommendations['analysis_notes'] = "WARNING: Not enough RAM for even one process."

def get_feature_store_path(dataset_run_id: str) -> str | None:
    # ... (This function is unchanged)
    try:
        client = MlflowClient()
        run = client.get_run(dataset_run_id)
        artifact_uri = run.info.artifact_uri
        parsed_uri = urlparse(artifact_uri)
        if parsed_uri.scheme == 'file':
            local_root = parsed_uri.path
            if platform.system() == "Windows" and local_root.startswith('/'): local_root = local_root[1:]
            return os.path.join(local_root, "feature_store")
        else: return None
    except Exception: return None

def calculate_data_size(feature_store_path: str) -> float:
    # ... (This function is unchanged)
    if not os.path.isdir(feature_store_path): return 0.0
    dummy_config = {"FEATURES_CONFIG": {f: True for f in FEATURE_TO_GROUP_MAP.keys()}}
    active_features = get_active_features(dummy_config)
    groups_to_load = { 'base_ohlcv' } | {FEATURE_TO_GROUP_MAP.get(f) for f in active_features if f in FEATURE_TO_GROUP_MAP}
    total_size_bytes = 0
    for group in groups_to_load:
        group_path = os.path.join(feature_store_path, f"group={group}")
        if os.path.isdir(group_path):
            for root, _, files in os.walk(group_path):
                for f in files:
                    if f.endswith(".parquet"): total_size_bytes += os.path.getsize(os.path.join(root, f))
    return total_size_bytes / (1024**3)

# --- NEW: Importable function that returns results as a dictionary ---
def get_hardware_recommendations(dataset_run_id: str, safety_margin: float = 0.9) -> dict:
    """Collects hardware info, analyzes dataset size, and returns recommendations."""
    # 1. Collect System Info
    sys_collector = SystemInfoCollector()
    sys_info = sys_collector.collect_all()

    # 2. Analyze Dataset Size
    feature_store_path = get_feature_store_path(dataset_run_id)
    total_data_gb = 0
    if feature_store_path:
        total_data_gb = calculate_data_size(feature_store_path)
    
    # 3. Get Recommendations
    advisor = RLHardwareAdvisor(sys_info, total_data_gb, safety_margin)
    recommendations = advisor.analyze()
    
    # 4. Combine all info into a single dictionary and return it
    return {
        "system_info": sys_info,
        "dataset_gb": total_data_gb,
        "recommendations": recommendations
    }


def display_advisor_results(results: dict):
    """Takes the results dictionary and prints a formatted summary."""
    sys_info = results['system_info']
    dataset_gb = results['dataset_gb']
    recs = results['recommendations']

    logger.info("--- Hardware Detection ---")
    logger.info(f"🖥️  CPU Cores: {sys_info['cpu']['physical_cores']} Physical")
    logger.info(f"🧠 RAM: {sys_info['ram']['available_gb']:.2f} GB Available / {sys_info['ram']['total_gb']:.2f} GB Total")
    if sys_info['cuda']['available']:
        logger.info(f"🚀 GPU: Found {sys_info['cuda']['device_count']} CUDA device(s) ({sys_info['cuda']['devices'][0]['name']})")
    else:
        logger.info("⚪️ GPU: No CUDA devices found.")
    
    logger.info("--- Dataset Analysis ---")
    logger.info(f"📊 Total on-disk size of dataset: {dataset_gb:.2f} GB")
    logger.info(f"📈 Estimated in-memory data size: {dataset_gb * RLHardwareAdvisor.IN_MEMORY_FACTOR:.2f} GB")

    logger.info("--- Recommendations ---")
    logger.info(f"Optimal Device: {recs['DEVICE']}")
    if recs['N_CPU'] > 0:
        logger.info(f"Optimal N_CPU (Sweet Spot): {recs['N_CPU']}")
    else:
        logger.warning(f"Optimal N_CPU: ⚠️ {recs.get('analysis_notes', 'Not enough RAM.')}")
    
    logger.info("="*70)
    logger.info("💡 Total System RAM Usage Calculation")
    logger.info("="*70)
    logger.info(f"{'N_CPU':>6} | {'Total Est. RAM (GB)':>25} | {'Status':>15}")
    logger.info("-"*70)
    for item in recs.get('breakdown', []):
        logger.info(f"{item['N_CPU']:>6} | {item['Total_Est_RAM_GB']:>25.2f} | {item['Status']:>15}")
    logger.info("-"*70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Training Hardware Advisor")
    parser.add_argument("--dataset-run-id", required=True)
    parser.add_argument("--output-file", help="Optional: Path to save recommended settings.")
    parser.add_argument("--safety-margin", type=float, default=0.9)
    parser.add_argument("--tracking-uri", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    # Setup logger and MLflow URI
    if not os.path.exists("log"): os.makedirs("log")
    setup_logging(logger_name='hardware_advisor', log_level_console='INFO')
    mlflow.set_tracking_uri(args.tracking_uri)

    # Get results by calling the new function
    results = get_hardware_recommendations(args.dataset_run_id, args.safety_margin)
    
    # Display the results
    display_advisor_results(results)
    
    # Save output if requested
    if args.output_file:
        settings_to_save = results['recommendations']
        with open(args.output_file, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        logger.info(f"✅ Recommended settings saved to {args.output_file}")
```

#### 📄 `mlflow_utils.py`
*path: `rl_agent_module/utils/mlflow_utils.py`*

```python
# utils/mlflow_utils.py or similar

import os
import subprocess
import socket
import time
import logging
from typing import List, Tuple, Optional, Any
from datetime import datetime
import mlflow
from mlflow.entities import RunStatus
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException


logger = logging.getLogger(__name__)

def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use (to avoid starting multiple servers)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def start_mlflow_server(
    backend_store_uri: str = "file:./data/rl_runs",
    artifact_root: str = "./artifacts",
    host: str = "127.0.0.1",
    port: int = 8080,
    wait_time: int = 5
) -> str:
    """
    Starts an MLflow tracking server (if not already running) and sets the tracking URI.
    Returns the tracking URI.
    """
    tracking_uri = f"http://{host}:{port}"

    if _is_port_in_use(port, host):
        logger.info(f"MLflow server already running at {tracking_uri}")
    else:
        cmd = [
            "mlflow", "server",
            "--backend-store-uri", backend_store_uri,
            "--default-artifact-root", artifact_root,
            "--host", host,
            "--port", str(port)
        ]
        logger.info(f"Starting MLflow server with: {' '.join(cmd)}")
        subprocess.Popen(cmd)

        # Give it a few seconds to boot
        time.sleep(wait_time)
        if _is_port_in_use(port, host):
            logger.info(f"✅ MLflow server is up at {tracking_uri}")
        else:
            logger.warning(f"⚠️ Could not verify MLflow server at {tracking_uri} after {wait_time}s")

    # Set MLflow tracking URI globally
    mlflow.set_tracking_uri(tracking_uri)
    logger.info(f"MLflow tracking URI set to {tracking_uri}")
    return tracking_uri

def check_mlflow_ui() -> bool:
    """
    Check if the MLflow server is reachable.
    
    Returns:
        bool: True if MLflow server is reachable, False otherwise.
    """
    try:
        MlflowClient().search_experiments()
        print("✅ MLflow Tracking Server is reachable.")
        return True
    except MlflowException:
        print("\n❌ Warning: The MLflow Tracking Server does not seem to be running.")
        print("   Please start it in a separate terminal with the command:")
        print("\n   mlflow ui --backend-store-uri file:./data/rl_runs\n")
        input("Press Enter to continue anyway...")
        return False


def start_mlflow_ui(backend_store_uri: str = "file:./data/rl_runs", port: int = 5000):
    """
    Optionally: lightweight mode to just start the UI for visualization.
    """
    if _is_port_in_use(port):
        logger.info(f"MLflow UI already running at http://127.0.0.1:{port}")
    else:
        cmd = [
            "mlflow", "ui",
            "--backend-store-uri", backend_store_uri,
            "--port", str(port)
        ]
        logger.info(f"Starting MLflow UI with: {' '.join(cmd)}")
        subprocess.Popen(cmd)
        time.sleep(2)
        logger.info(f"MLflow UI available at http://127.0.0.1:{port}")

def find_mlflow_entity_by_run_id(run_id: str) -> mlflow.entities.Run | None:
    client = MlflowClient()
    try:
        return client.get_run(run_id)
    except Exception as e:
        logger.error(f"Could not fetch MLflow entity by run_id: {e}", exc_info=True)
        return None

def get_parent_run_info(run_id: str, client: MlflowClient) -> List[Tuple[str, str]]:
    """
    Recursively collects parent run info by traversing 'continued_from' tags.
    Returns list of (run_name, run_id), ordered from oldest ancestor to direct parent.
    """
    parent_infos = []
    current_run_id = run_id

    while current_run_id:
        try:
            run = client.get_run(current_run_id)
            if run.info.status != RunStatus.FINISHED:
                logger.warning(f"Run {current_run_id} is not FINISHED (status: {run.info.status})")

            run_name = run.data.tags.get("mlflow.runName", f"model_{current_run_id}")
            parent_infos.append((run_name, current_run_id))

            # Move to parent
            current_run_id = run.data.tags.get("continued_from")

        except Exception as e:
            logger.warning(f"Failed to retrieve parent run {current_run_id}: {e}")
            break

    return list(reversed(parent_infos))  # Oldest first


def build_tensorboard_command(
    current_run_id: str,
    current_run_name: str,
    parent_run_infos: List[Tuple[str, str]],
    current_tensorboard_path: str,
    client: MlflowClient,
    use_forward_slashes: bool = True
) -> str:
    """
    Builds a tensorboard --logdir command using given paths.
    current_tensorboard_path: local or final URI (e.g., staging or artifact URI)
    """
    logdir_entries = []

    # Add parents
    for parent_name, parent_id in parent_run_infos:
        try:
            parent_run = client.get_run(parent_id)
            parent_uri = parent_run.info.artifact_uri.rstrip("/").lstrip("file:///")
            tb_path = f"{parent_uri}/tensorboard_logs"
            if use_forward_slashes:
                tb_path = tb_path.replace("\\", "/")
            logdir_entries.append(f"{parent_name}:{tb_path}")
        except Exception as e:
            logger.warning(f"Could not resolve tensorboard path for parent {parent_id}: {e}")

    # Add current run
    safe_name = current_run_name.replace(" ", "_").replace(":", "-")
    tb_path = current_tensorboard_path.rstrip("/").lstrip("file:///")
    if use_forward_slashes:
        tb_path = tb_path.replace("\\", "/")
    logdir_entries.append(f"{safe_name}:{tb_path}")

    logdir_arg = ",".join(logdir_entries)
    return f"tensorboard --logdir_spec={logdir_arg}"

def find_artifact_in_run(
    run_id: str,
    file_prefix: str,
    file_suffix: str = ".json"
) -> Optional[str]:
    """
    Search for an artifact file in an MLflow run by prefix and suffix.
    """
    client = MlflowClient()
    try:
        stack = [""]
        while stack:
            current_path = stack.pop()
            artifacts = client.list_artifacts(run_id, path=current_path)
            for artifact in artifacts:
                if artifact.is_dir:
                    stack.append(artifact.path)
                else:
                    basename = os.path.basename(artifact.path)
                    if basename.startswith(file_prefix) and basename.endswith(file_suffix):
                        return artifact.path
        return None
    except MlflowException as e:
        logger.error(f"❌ MLflow error while searching for artifact starting with '{file_prefix}': {e}")
        return None

def fetch_mlflow_parent_runs(
    experiment_name: str,
    num_runs: int = 15
) -> List[Any]:
    """
    Fetch parent runs (non-child runs) from an MLflow experiment.
    """
    try:
        client = MlflowClient()
        experiment = client.get_experiment_by_name(experiment_name)
        if not experiment:
            logger.warning(f"⚠️ Experiment '{experiment_name}' not found.")
            return []
        
        all_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=["start_time DESC"],
            max_results=num_runs * 10
        )
        
        parent_runs = [
            run for run in all_runs
            if 'mlflow.parentRunId' not in run.data.tags
        ]
        return parent_runs[:num_runs]
    except MlflowException as e:
        logger.error(f"Error fetching MLflow runs: {e}")
        return []

def get_artifact_path(
    run_id: str,
    artifact_name: str,
    dst_path: str
) -> Optional[str]:
    """
    Download and get the local path of an artifact from an MLflow run.
    """
    try:
        return mlflow.artifacts.download_artifacts(
            run_id=run_id,
            artifact_path=artifact_name,
            dst_path=dst_path
        )
    except MlflowException as e:
        logger.error(f"❌ Error downloading artifact '{artifact_name}': {e}")
        return None
```

#### 📄 `script_utils.py`
*path: `rl_agent_module/utils/script_utils.py`*

```python
# utils/script_utils.py

import os
import json


def generate_tensorboard_launch_scripts(
    command: str,
    output_dir: str
):
    """
    Generates both .sh and .bat launch scripts in the given directory.
    Uses UTF-8 encoding for future-proofing.
    """
    os.makedirs(output_dir, exist_ok=True)

    sh_path = os.path.join(output_dir, "launch_tensorboard.sh")
    with open(sh_path, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\n")
        f.write("# Launch TensorBoard with full training lineage\n")
        f.write(f"{command}\n")
    os.chmod(sh_path, 0o755)

    bat_path = os.path.join(output_dir, "launch_tensorboard.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write(":: Launch TensorBoard with full training lineage\n")
        f.write(f"{command}\n")


def generate_readme(
    command: str,
    output_dir: str
):
    """
    Generates a README.md with instructions, using UTF-8 encoding for emojis and special chars.
    """
    os.makedirs(output_dir, exist_ok=True)
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# Model Training Artifacts\n\n")
        f.write("## 📊 Visualize Training with TensorBoard\n\n")
        f.write("This model was trained with lineage from parent models. ")
        f.write("Use the command below or the provided scripts to launch TensorBoard:\n\n")
        f.write("```bash\n")
        f.write(f"{command}\n")
        f.write("```\n\n")
        f.write("### 🚀 Launch Scripts\n\n")
        f.write("- `launch_tensorboard.sh` — for Linux/macOS\n")
        f.write("- `launch_tensorboard.bat` — for Windows\n\n")
        f.write("### 📁 Log Directories Mapped:\n")
        f.write("Each entry is in `name:path` format:\n")
        for part in command.split("--logdir=")[-1].split(","):
            if ":" in part:
                name, path = part.split(":", 1)
                f.write(f"- `{name}` → `{path}`\n")
        f.write("\n> 💡 Tip: Run `pip install tensorboard` if not already installed.\n")

def generate_config_json(
    rl_config: dict,
    output_dir: str
):
    """
    Generates a README.md with instructions, using UTF-8 encoding for emojis and special chars.
    """
    os.makedirs(output_dir, exist_ok=True)
    rl_config_path = os.path.join(output_dir, "rl_config.json")
    with open(rl_config_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rl_config, indent=4))
        f.write("\n")
```

#### 📄 `rl_main.py`
*path: `rl_main.py`*

```python
# rl_main.py
"""
Interactive command center for the Reinforcement Learning workflow.

This script serves as a central entry point for all phases of the
ML lifecycle, from hyperparameter search to analysis. It uses
MLflow in the background to manage experiments and provide the user with
context-aware choices.

Ensure the MLflow UI is running before starting this script:
    mlflow ui --backend-store-uri file:./data/rl_runs
"""

import os
import subprocess
import tempfile
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from rich.table import Table
from rich.console import Console
from rl_agent_module.utils.hardware_advisor import get_hardware_recommendations

import inquirer
from rich.console import Console
from rich.table import Table
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException

from rl_agent_module.utils.mlflow_utils import (
    start_mlflow_server,
    find_artifact_in_run,
    fetch_mlflow_parent_runs,
    get_artifact_path
)
from config.rl_config import RL_CONFIG

MLFLOW_EXPERIMENT_DATASET = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_DATASET"]
MLFLOW_EXPERIMENT_TRAINING = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TRAINING"]
MLFLOW_EXPERIMENT_TUNING = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TUNING"]
MLFLOW_EXPERIMENT_BACKTESTING = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_BACKTESTING"]


# --- MLflow Configuration & Console ---
mlflow.set_tracking_uri("file:./data/rl_runs")
console = Console()

# --- Helper Functions (run_command, select_run_from_list, _select_dataset_run, run_hardware_advisor) ---
# ... (These functions remain unchanged from the previous version) ...
def run_command(command: List[str]) -> None:
    """
    Execute a shell command and display the output.
    
    Args:
        command: List of command arguments to execute.
    """
    try:
        print("\n" + "=" * 60)
        print(f"🚀 Executing command:\n   {' '.join(command)}")
        print("=" * 60 + "\n")
        
        # Clean environment to avoid MLflow run ID conflicts
        clean_env = os.environ.copy()
        if "MLFLOW_RUN_ID" in clean_env:
            del clean_env["MLFLOW_RUN_ID"]
            
        subprocess.run(command, check=True, env=clean_env)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {e}")
    except FileNotFoundError:
        print("❌ Command not found. Make sure Python is in the system path.")


def select_run_from_list(runs: List[Any], message: str) -> Optional[str]:
    """
    Display a list of runs for user selection and return the selected run ID.
    
    Args:
        runs: List of MLflow run objects.
        message: Message to display to the user.
        
    Returns:
        str or None: Selected run ID if chosen, None otherwise.
    """
    if not runs:
        print("No suitable runs found for selection.")
        return None
    
    choices = []
    for run in runs:
        # Extract run information for display
        run_name = run.data.tags.get('mlflow.runName', run.info.run_id[:8])
        start_time = datetime.fromtimestamp(run.info.start_time / 1000).strftime('%Y-%m-%d %H:%M')
        
        # Try to get a meaningful metric value
        metric_val = (
            run.data.metrics.get('best_trial_value') or
            run.data.metrics.get('eval_mean_reward') or
            run.data.metrics.get('processed_token_count')
        )
        metric_display = f"{metric_val:.2f}" if metric_val is not None else "N/A"
        
        choice_str = (
            f"[{start_time}] {run_name} "
            f"(Metric: {metric_display}, ID: {run.info.run_id[:6]}...)"
        )
        choices.append((choice_str, run.info.run_id))

    answer = inquirer.prompt([
        inquirer.List('run_id', message=message, choices=choices, carousel=True)
    ])
    
    return answer['run_id'] if answer else None


def _select_dataset_run() -> Optional[str]:
    """
    Helper function to select a dataset run from available options.
    
    Returns:
        str or None: Selected dataset run ID if chosen, None otherwise.
    """
    print("\n🔎 Please select a dataset to use for this action.")
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_DATASET)
    
    if not runs:
        print("No dataset runs found. Please generate one first.")
        return None
    
    run_id = select_run_from_list(runs, "Choose the dataset run:")
    if run_id:
        print(f"✅ Using dataset from run ID: {run_id[:8]}...")
    
    return run_id


def run_hardware_advisor(dataset_run_id: str) -> Optional[Dict[str, Any]]:
    """Runs the hardware advisor directly and displays the results."""
    print("\n" + "="*60)
    print("🤖 Running Hardware Advisor...")
    print("="*60)
    
    try:
        results = get_hardware_recommendations(dataset_run_id)
        sys_info = results['system_info']
        recs = results['recommendations']

        # Display a summary table
        table = Table(title="Hardware Advisor Summary")
        table.add_column("Parameter", style="cyan")
        table.add_column("Detected / Recommended", style="magenta")

        table.add_row("Available RAM", f"{sys_info['ram']['available_gb']:.2f} GB")
        table.add_row("Physical CPU Cores", str(sys_info['cpu']['physical_cores']))
        table.add_row("CUDA Available", "Yes" if sys_info['cuda']['available'] else "No")
        table.add_row("Dataset Size", f"{results['dataset_gb']:.2f} GB")
        table.add_section()
        table.add_row("Recommended Device", recs.get('DEVICE', 'N/A'))
        table.add_row("Recommended N_CPU", str(recs.get('N_CPU', 'N/A')))
        
        console = Console()
        console.print(table)
        
        if recs.get('analysis_notes'):
            print(f"Note: {recs.get('analysis_notes')}")
        
        # Ask user to accept
        answer = inquirer.prompt([
            inquirer.Confirm('accept', message="Accept recommended settings?", default=True)
        ])

        if answer and answer['accept']:
            return {'DEVICE': recs.get('DEVICE'), 'N_CPU': recs.get('N_CPU')}
        else:
            print("Aborted by user.")
            return None

    except Exception as e:
        print(f"Error running hardware advisor: {e}")
        return None

# --- Main Menu Functions (generate_dataset, start_tuning, start_training, etc.) ---
# ... (These functions remain unchanged) ...
def generate_dataset() -> None:
    """Start the ETL process to generate a new feature store dataset."""
    print("\n--- Phase 0: Generate Feature Store (ETL) ---")
    
    questions = [
        inquirer.Text(
            'start_date', 
            message="Enter start date (e.g., 2025-06-26T00:00:00Z)", 
            default="2025-06-26T00:00:00Z"
        ),
        inquirer.Text(
            'end_date', 
            message="Enter end date (e.g., 2025-07-20T00:00:00Z)", 
            default="2025-07-20T00:00:00Z"
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if not all(answers.values()):
        print("Aborted: All fields are required.")
        return
    
    command = [
        "python", 
        "rl_agent_module/etl/prepare_rl_dataset.py", 
        "--start-date", answers['start_date'], 
        "--end-date", answers['end_date']
    ]
    run_command(command)


def start_tuning() -> None:
    """Start a new hyperparameter tuning run."""
    print("\n--- Phase 1: Hyperparameter Tuning ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return

    hw_settings = _run_hardware_advisor_and_get_settings(dataset_run_id)
    if not hw_settings:
        print("Aborted due to hardware advisor issue.")
        return

    command = [
        "python", "rl_agent_module/training/train.py", "tune", 
        "--dataset-run-id", dataset_run_id,
        "--device", hw_settings['DEVICE'],
        "--n-cpu", str(hw_settings['N_CPU'])
    ]
    run_command(command)


def start_training() -> None:
    """Start a new training based on the results of a tuning run."""
    print("\n--- Phase 2: Train New Model ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return

    # --- INTEGRATION: Run advisor to get hardware settings ---
    hw_settings = run_hardware_advisor(dataset_run_id)
    if not hw_settings or hw_settings.get('N_CPU', 0) == 0:
        print("Aborted due to hardware advisor issue or insufficient resources.")
        return
        
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TUNING)
    if not runs:
        print("No tuning runs found. Please run hyperparameter tuning first.")
        return
    
    run_id = select_run_from_list(runs, "Select a tuning run to source best parameters from:")
    if not run_id:
        return
    
    params_artifact_name = find_artifact_in_run(run_id, file_prefix="best_params", file_suffix=".json")
    if not params_artifact_name:
        print(f"\n❌ FATAL: Could not find 'best_params.json' in the selected tuning run.")
        return
    
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        params_path = get_artifact_path(run_id, params_artifact_name, dst_path=tmpdir)
        if not params_path:
            return
        
        answers = inquirer.prompt([
            inquirer.Text('name', message="Enter a name for this new training run"),
            inquirer.Confirm('register', message="Register this model in MLflow?", default=True)
        ])
        if not answers or not answers.get('name'):
            print("Aborted: A name is required.")
            return
        
        model_name = answers['name']
        command = [
            "python", "rl_agent_module/training/train.py", "train", 
            "--params-path", params_path, 
            "--name", model_name, 
            "--dataset-run-id", dataset_run_id,
            # --- Pass hardware settings to the training script ---
            "--device", hw_settings['DEVICE'],
            "--n-cpu", str(hw_settings['N_CPU'])
        ]
        
        if answers.get('register'):
            command.extend(["--register-as", model_name])
            
        run_command(command)


def continue_or_finetune_training(action: str) -> None:
    """Continue or finetune an existing training run."""
    print(f"\n--- Phase 3/4: {action.capitalize()} Training ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return

    # --- INTEGRATION: Run advisor to get hardware settings ---
    hw_settings = run_hardware_advisor(dataset_run_id)
    if not hw_settings or hw_settings.get('N_CPU', 0) == 0:
        print("Aborted due to hardware advisor issue or insufficient resources.")
        return
    
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs:
        print("No previous training runs found to continue from.")
        return
    
    run_id = select_run_from_list(runs, f"Select a training run to {action}:")
    if not run_id:
        return
    
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        model_artifact_path = (
            find_artifact_in_run(run_id, "best_model", ".zip") or
            find_artifact_in_run(run_id, "final_model", ".zip")
        )
        
        if not model_artifact_path:
            print("❌ Could not find a model artifact in this run.")
            return
        
        model_path = get_artifact_path(run_id, model_artifact_path, dst_path=tmpdir)
        if not model_path:
            return
        
        parent_run = MlflowClient().get_run(run_id)
        parent_run_name = parent_run.data.tags.get('mlflow.runName', run_id[:8])
        registered_model_name = parent_run.data.tags.get("registered_model_name")
        suggested_name = f"{parent_run_name}_{action[:2]}"
        
        questions = [
            inquirer.Text('name', message=f"Enter a name for this '{action}' run", default=suggested_name),
            inquirer.Confirm('register', message="Register this new version under the same model name?", default=True)
        ]
        
        if action == 'finetune':
            questions.append(inquirer.Text('lr', message="New learning rate (optional, press Enter to keep existing)"))
        
        answers = inquirer.prompt(questions)
        if not answers or not answers['name']:
            print("Aborted.")
            return
        
        command = [
            "python", "rl_agent_module/training/train.py", action, 
            "--model-path", model_path, 
            "--parent-run-id", run_id, 
            "--name", answers['name'], 
            "--dataset-run-id", dataset_run_id,
            # --- Pass hardware settings to the training script ---
            "--device", hw_settings['DEVICE'],
            "--n-cpu", str(hw_settings['N_CPU'])
        ]
        
        if answers.get('register') and registered_model_name:
            command.extend(["--register-as", registered_model_name])
        elif answers.get('register'):
            print(f"⚠️ Parent model was not registered. This model will be registered as '{answers['name']}'.")
            command.extend(["--register-as", answers['name']])

        if action == 'finetune' and answers.get('lr'):
            command.extend(["--learning-rate", answers['lr']])
        
        run_command(command)


def start_feature_analysis() -> None:
    """Start feature importance analysis on a trained model."""
    print("\n--- Phase 5: Feature Importance Analysis ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return
    
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs:
        print("No trained models found to analyze.")
        return
    
    run_id = select_run_from_list(runs, "Select the trained model to be analyzed:")
    if not run_id:
        return
    
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        model_artifact_path = (
            find_artifact_in_run(run_id, "best_model", ".zip") or
            find_artifact_in_run(run_id, "final_model", ".zip")
        )
        
        if not model_artifact_path:
            print("❌ Could not find a model artifact for analysis.")
            return
        
        model_path = get_artifact_path(run_id, model_artifact_path, dst_path=tmpdir)
        if not model_path:
            return
        
        command = [
            "python", 
            "rl_agent_module/evaluation/feature_importance.py", 
            "--model-run-id", run_id, 
            "--model-path", model_path, 
            "--dataset-run-id", dataset_run_id
        ]
        run_command(command)

# --- REFACTORED BACKTESTING FUNCTION ---
def start_backtesting() -> None:
    """Run a backtest on a trained model using a prepared, out-of-sample dataset."""
    print("\n--- Phase 6: Backtest a Trained Model ---")

    # 1. Select the trained model to evaluate
    print("\n🔎 First, select a trained model to backtest.")
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs:
        print("No trained models found to backtest.")
        return
    
    model_run_id = select_run_from_list(runs, "Select the trained model you want to backtest:")
    if not model_run_id:
        return

    # 2. Select the dataset for backtesting
    print("\n🔎 Next, select the prepared dataset to use for the backtest.")
    print("⚠️  Ensure this dataset is from a different time period than the model's training data.")
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return

    # 3. Download the model artifact to a temporary location
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        model_artifact_path = (
            find_artifact_in_run(model_run_id, "best_model", ".zip") or
            find_artifact_in_run(model_run_id, "final_model", ".zip")
        )
        
        if not model_artifact_path:
            print("❌ Could not find a model artifact (.zip) in the selected model run.")
            return
        
        model_path = get_artifact_path(model_run_id, model_artifact_path, dst_path=tmpdir)
        if not model_path:
            print("❌ Failed to download the model artifact.")
            return

        # 4. Construct and run the evaluation command
        command = [
            "python", "rl_agent_module/evaluation/evaluate.py",
            "--model-path", model_path,
            "--dataset-run-id", dataset_run_id
        ]
        run_command(command)


# --- Main Workflow ---

def main_menu() -> None:
    """Display the interactive main menu and control the workflow."""
    while True:
        answers = inquirer.prompt([
            inquirer.List(
                'action',
                message="MLOps Command Center",
                choices=[
                    ('0) Generate New Dataset (ETL)', 'etl'),
                    ('1) Start Hyperparameter Tuning (Optuna)', 'tune'),
                    ('2) Train a New Model', 'train'),
                    ('3) Continue Training a Model', 'continue'),
                    ('4) Perform Model Fine-Tuning', 'finetune'),
                    ('5) Start Feature Importance Analysis', 'analyze'),
                    ('6) Run Backtest on a Trained Model', 'backtest'),
                    ('7) Exit', 'exit')
                ],
                carousel=True
            )
        ])
        
        action = answers['action'] if answers else 'exit'

        if action == 'exit':
            print("👋 Goodbye!")
            break
        elif action == 'etl':
            generate_dataset()
        elif action == 'tune':
            start_tuning()
        elif action == 'train':
            start_training()
        elif action == 'continue':
            continue_or_finetune_training('continue')
        elif action == 'finetune':
            continue_or_finetune_training('finetune')
        elif action == 'analyze':
            start_feature_analysis()
        elif action == 'backtest':
            start_backtesting()
        
        input("\nPress Enter to return to the main menu...")
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == "__main__":
    os.makedirs("./.rl_staging", exist_ok=True)
    
    # Start MLflow Server and set tracking URI
    tracking_uri = start_mlflow_server(backend_store_uri="file:./data/rl_runs")
    mlflow.set_tracking_uri(tracking_uri)
    
    main_menu()
```

#### 📄 `socials_processor.py`
*path: `socials_processor.py`*

```python
# path: socials_processor.py

"""
Handles fetching, scoring, and storing social media links for tokens.
Now supports multiple, prioritized check types (Initial, Follow-up, Telegram).
"""

import asyncio
import json
from urllib.parse import urlparse, urlsplit
import httpx
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import asyncpg
from typing import Tuple

from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState
from utils import is_valid_telegram, is_valid_twitter
from connectors.telegram_monitor import check_telegram_channel

# --- Configuration for Retries ---
MAX_FETCH_ATTEMPTS = 3
DEPRIORITIZED_PRIORITY = float('inf')

class SocialsProcessor:
    def __init__(self, state: GlobalState, db_client: DatabaseClient, config_dict: dict):
        self.state = state
        self.db_client = db_client
        self.config = config_dict
        self.queue = self.state.get_socialscheck_queue()
        self.fetch_attempts = {}

        # --- Scoring values are loaded dynamically in _calculate_social_score ---

        # Shared HTTP client for website verification
        self._verify_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, limits=httpx.Limits(max_connections=5))

    async def _fetch_metadata(self, uri: str) -> dict | str | None:
        # ... (this method remains unchanged)
        if not uri or not uri.startswith('http'):
            logger.debug(f"🚩 Invalid or missing URI for social metadata: {uri}")
            return "Error InvalidURI"

        response_obj_for_logging = None
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(uri)
                response_obj_for_logging = response

                content_type = response.headers.get('content-type', '').lower()
                if not ('application/json' in content_type or 'text/json' in content_type or not content_type):
                    if content_type.startswith('image/') or content_type.startswith('application/octet-stream') or content_type.startswith('text/html'):
                        logger.warning(f"🚩 Metadata fetch for {uri} returned non-JSON content-type: {content_type}.")
                        return f"Error NotJSONContentType: {content_type}"

                response.raise_for_status()

                try:
                    metadata = response.json()
                    return metadata
                except json.JSONDecodeError as e_initial:
                    if "Invalid control character" in str(e_initial):
                        logger.warning(f"🚩 Initial JSON parsing for {uri} failed. Attempting with strict=False.")
                        try:
                            metadata_strict_false = json.loads(response.text, strict=False)
                            return metadata_strict_false
                        except json.JSONDecodeError as e_strict:
                            logger.error(f"🚩 Failed to decode JSON from {uri} even with strict=False. Error: {e_strict}. Response text: {response.text[:200]}...")
                            return "Error DecodeFailedStrict"
                    else:
                        logger.error(f"🚩 Failed to decode JSON from {uri}. Error: {e_initial}. Response text: {response.text[:200]}...")
                        return "Error DecodeGeneral"

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"🚩 HTTP error fetching social metadata from {uri}: {status_code} {e.response.reason_phrase}")
            return f"Error HTTP {status_code}"
        except httpx.TimeoutException:
            logger.warning(f"🚩 Timeout fetching social metadata from {uri}")
            return "Error Timeout"
        except httpx.RequestError as e:
            logger.warning(f"🚩 Request error fetching social metadata from {uri}: {e}")
            return "Error Request"
        except Exception as e:
            response_text_snippet = response_obj_for_logging.text[:200] if response_obj_for_logging and hasattr(response_obj_for_logging, 'text') else 'N/A'
            logger.error(f"🚩 Unexpected error processing social metadata from {uri}: {e}. Response text: {response_text_snippet}...", exc_info=True)
            return "Error UnknownFetch"

    async def _verify_website_details(self, url: str, token_name: str, token_symbol: str) -> dict:
        # ... (this method remains unchanged)
        results = {'uses_https': False, 'is_reachable': False, 'mentions_token': False, 'error': None}
        token_name_lower = (token_name or "").lower()
        token_symbol_lower = (token_symbol or "").lower()

        try:
            parsed_url = urlsplit(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                 results['error'] = "Invalid URL format"
                 return results

            results['uses_https'] = parsed_url.scheme == 'https'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await self._verify_client.get(url, headers=headers)
            response.raise_for_status()
            results['is_reachable'] = True

            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                page_content = ""
                if soup.title and soup.title.string:
                    page_content += soup.title.string.lower() + " "
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    page_content += meta_desc['content'].lower()

                if token_name_lower and token_name_lower in page_content:
                    results['mentions_token'] = True
                elif token_symbol_lower and token_symbol_lower in page_content:
                     results['mentions_token'] = True
            
        except httpx.HTTPStatusError as e:
            results['error'] = f"HTTP Error {e.response.status_code}"
        except httpx.TimeoutException:
            results['error'] = "Timeout"
        except httpx.RequestError as e:
            results['error'] = f"Request Error: {type(e).__name__}"
        except ImportError:
             results['error'] = "Missing 'beautifulsoup4' library"
             logger.error("🚨 Dependency missing: Please install 'beautifulsoup4' (`pip install beautifulsoup4`) for website content checking.")
        except Exception as e:
            results['error'] = f"Unexpected Error: {type(e).__name__}"
            logger.error(f"🚩 Website Verify Fail ({url}): Unexpected error: {e}", exc_info=True)
        return results

    def _calculate_social_score(self, social_data: dict, token_name: str | None, token_symbol: str | None, verification_results: dict | None, telegram_results: dict | None) -> Tuple[int, list]:
        # ... (this method is mostly unchanged but now returns reasons for logging)
        total_penalty = 0
        reasons = []
        token_name = (token_name or "").lower()
        token_symbol = (token_symbol or "").lower()

        # Dynamically load config values to allow for live updates
        disallowed_domains = self.config['SOCIALS_DISALLOWED_WEBSITE_DOMAINS']
        
        website = social_data.get("website")
        if not website:
            penalty = self.config['SOCIALS_PENALTY_NO_WEBSITE']
            total_penalty += penalty
            reasons.append(f"No Website: +{penalty}")
        elif not isinstance(website, str):
            penalty = self.config['SOCIALS_PENALTY_INVALID_WEBSITE_TYPE']
            total_penalty += penalty
            reasons.append(f"Invalid Website Type: +{penalty}")
        else:
            try:
                parsed_domain_obj = urlparse(website)
                parsed_domain = parsed_domain_obj.netloc.lower().replace('www.', '')
                is_disallowed_website = False
                if parsed_domain:
                    if any(parsed_domain == d or parsed_domain.endswith('.' + d) for d in disallowed_domains):
                        penalty = self.config['SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE']
                        total_penalty += penalty
                        reasons.append(f"Disallowed Domain: +{penalty}")
                        is_disallowed_website = True
                else:
                    penalty = self.config['SOCIALS_PENALTY_WEBSITE_INVALID_URL']
                    total_penalty += penalty
                    reasons.append(f"Invalid URL: +{penalty}")
                    is_disallowed_website = True

                if not is_disallowed_website:
                    if verification_results and verification_results['error']:
                        error_str = verification_results['error']
                        if "Timeout" in error_str:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_TIMEOUT']
                            total_penalty += penalty
                            reasons.append(f"Website Timeout: +{penalty}")
                        elif "HTTP Error" in error_str:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_HTTP_ERROR']
                            total_penalty += penalty
                            reasons.append(f"HTTP Error: +{penalty}")
                        else:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_OTHER_ERROR']
                            total_penalty += penalty
                            reasons.append(f"Website Error: +{penalty}")
                    elif verification_results:
                        if not verification_results['uses_https']:
                            penalty = self.config['SOCIALS_PENALTY_NO_HTTPS']
                            total_penalty += penalty
                            reasons.append(f"No HTTPS: +{penalty}")
                        if not verification_results['mentions_token']:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_NO_MENTION']
                            total_penalty += penalty
                            reasons.append(f"No Token Mention: +{penalty}")
                        if parsed_domain:
                            bonus = self.config['SOCIALS_BONUS_DOMAIN_MATCH']
                            if token_name and (token_name in parsed_domain):
                                total_penalty += bonus
                                reasons.append(f"Domain Match: {bonus}")
                            elif token_symbol and (token_symbol in parsed_domain):
                                total_penalty += bonus
                                reasons.append(f"Domain Match: {bonus}")
            except Exception as e:
                penalty = self.config['SOCIALS_PENALTY_WEBSITE_INVALID_URL']
                total_penalty += penalty
                reasons.append(f"URL Parse Error: +{penalty}")

        telegram = social_data.get("telegram") or social_data.get("tg")
        if not telegram:
            penalty = self.config['SOCIALS_PENALTY_NO_TELEGRAM']
            total_penalty += penalty
            reasons.append(f"No Telegram: +{penalty}")
        elif not isinstance(telegram, str) or not is_valid_telegram(telegram):
            penalty = self.config['SOCIALS_PENALTY_INVALID_TELEGRAM_URL']
            total_penalty += penalty
            reasons.append(f"Invalid TG URL: +{penalty}")
        elif telegram_results and telegram_results.get('valid'):
            members = telegram_results.get('members') or 0
            online = telegram_results.get('online') or 0
            if members > self.config['SOCIALS_THRESHOLD_TG_HIGH_MEMBERS']:
                bonus = self.config['SOCIALS_BONUS_TG_HIGH_MEMBERS']
                total_penalty += bonus
                reasons.append(f"High TG Members: {bonus}")
            if members > 0:
                online_ratio = online / members
                if online_ratio > self.config['SOCIALS_THRESHOLD_TG_HIGH_ONLINE_RATIO']:
                    bonus = self.config['SOCIALS_BONUS_TG_HIGH_ONLINE_RATIO']
                    total_penalty += bonus
                    reasons.append(f"High Online Ratio: {bonus}")
        
        twitter = social_data.get("twitter") or social_data.get("x")
        if not twitter:
            penalty = self.config['SOCIALS_PENALTY_NO_TWITTER']
            total_penalty += penalty
            reasons.append(f"No Twitter/X: +{penalty}")
        elif not isinstance(twitter, str) or not is_valid_twitter(twitter):
            penalty = self.config['SOCIALS_PENALTY_INVALID_TWITTER_URL']
            total_penalty += penalty
            reasons.append(f"Invalid Twitter URL: +{penalty}")

        valid_links = [link for link in [website, telegram, twitter] if isinstance(link, str) and link]
        if len(valid_links) > len(set(valid_links)):
            penalty = self.config['SOCIALS_PENALTY_DUPLICATE_LINKS']
            total_penalty += penalty
            reasons.append(f"Duplicate Links: +{penalty}")

        final_score = min(max(total_penalty, 0), 100)
        return final_score, reasons

    async def _update_token_socials(self, mint: str, website: str | None, telegram: str | None, twitter: str | None, score: int, score_type: str, details: dict | None):
        # ... (this method remains unchanged)
        try:
            async with self.db_client.pool.acquire() as conn:
                async with conn.transaction():
                    token_exists = await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint)
                    if not token_exists:
                        logger.warning(f"🚩 Token {mint} was deleted from DB before socials could be updated. Aborting storage.")
                        return True

                    await conn.execute("""
                        UPDATE tokens
                        SET website = COALESCE($2, website),
                            telegram = COALESCE($3, telegram),
                            twitter = COALESCE($4, twitter),
                            socials_score = $5,
                            socials_last_checked = NOW()
                        WHERE mint = $1
                    """, mint, website, telegram, twitter, score)

                    await conn.execute("""
                        INSERT INTO social_scores (mint, score_type, score_value, details)
                        VALUES ($1, $2, $3, $4)
                    """, mint, score_type, score, json.dumps(details) if details else None)

            logger.debug(f"💾 Updated socials for {mint}. Score: {score}, Type: {score_type}.")
            return True
        except asyncpg.exceptions.ForeignKeyViolationError as fk_error:
            logger.warning(f"🚩 Caught a Foreign Key violation for {mint} despite the pre-check. Aborting. Details: {fk_error}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update socials in DB for {mint}: {e}", exc_info=True)
            return False

    async def _process_metadata_check(self, mint: str, is_initial_check: bool) -> str | bool:
        """
        Handles the full metadata check workflow: fetch URI, fetch metadata,
        verify socials, calculate score, and store results.
        """
        score_type = self.config['SOCIALS_SCORE_TYPE_INITIAL'] if is_initial_check else self.config['SOCIALS_SCORE_TYPE_FOLLOWUP']
        logger.debug(f"🔍 Processing '{score_type}' for token: {mint}")
        
        try:
            async with self.db_client.pool.acquire() as conn:
                token_info_row = await conn.fetchrow("SELECT uri, name, symbol FROM tokens WHERE mint = $1", mint)

            if not token_info_row: return "NOT_FOUND"

            primary_uri, token_name, token_symbol = token_info_row['uri'], token_info_row['name'], token_info_row['symbol']
            metadata = await self._fetch_metadata(primary_uri)
            metadata_source = primary_uri

            if isinstance(metadata, str) or metadata is None:
                metadata_fetch_error = metadata or "UNKNOWN_ERROR"
                logger.warning(f"Primary URI for {mint} failed ({metadata_fetch_error}). No fallback for metadata checks.")
                await self._update_token_socials(mint, None, None, None, self.config['SOCIALS_SCORE_FAILED_METADATA'], "METADATA_FETCH_FAILURE", {"error": metadata_fetch_error, "source": metadata_source})
                return metadata_fetch_error

            website = metadata.get("website") or metadata.get("homepage") or metadata.get("url") or metadata.get("external_url")
            telegram = metadata.get("telegram") or metadata.get("tg")
            twitter = metadata.get("twitter") or metadata.get("x")
            
            social_links = {"website": str(website) if website else None, "telegram": telegram, "twitter": str(twitter) if twitter else None}
            
            verification_results, telegram_results = None, None
            if social_links["website"]:
                verification_results = await self._verify_website_details(social_links["website"], token_name, token_symbol)
            if social_links["telegram"] and is_valid_telegram(social_links["telegram"]):
                telegram_results = await check_telegram_channel(social_links["telegram"])

            social_score, reasons = self._calculate_social_score(social_links, token_name, token_symbol, verification_results, telegram_results)
            details = {"metadata_source": metadata_source, "website_verification": verification_results, "telegram_stats": telegram_results, "reasons": reasons}
            
            display_name = token_name or token_symbol or mint
            logger.debug(f"📊 Socials Score for '{display_name}': {social_score} (Reasons: {', '.join(reasons)})")
            
            await self._update_token_socials(mint, social_links["website"], social_links["telegram"], social_links["twitter"], social_score, score_type, details)
            return True

        except Exception as e:
            logger.error(f"🚨 Unexpected error in _process_metadata_check for {mint}: {e}", exc_info=True)
            return "Error UnhandledProcess"

    async def _process_telegram_update(self, mint: str) -> str | bool:
        """
        Handles fetching the latest Telegram stats for a token and updating its record.
        This recalculates the main score based on the new Telegram data.
        """
        logger.debug(f"🔍 Processing 'TELEGRAM_UPDATE' for token: {mint}")
        try:
            async with self.db_client.pool.acquire() as conn:
                token_info = await conn.fetchrow("SELECT name, symbol, website, telegram, twitter FROM tokens WHERE mint = $1", mint)
            
            if not token_info or not token_info['telegram']:
                return "NO_TELEGRAM_LINK"
            
            telegram_url = token_info['telegram']
            telegram_results = await check_telegram_channel(telegram_url)
            
            if not telegram_results or not telegram_results.get('valid'):
                # Not a retryable error if the link is now invalid
                logger.warning(f"Telegram link {telegram_url} for {mint} is no longer valid.")
                return "TELEGRAM_INVALID"
            
            # Re-calculate score with EXISTING social links but NEW telegram data
            existing_socials = {"website": token_info['website'], "telegram": token_info['telegram'], "twitter": token_info['twitter']}
            
            # We don't re-verify the website here to keep this check lightweight
            # Pass None for verification_results to use only link presence/format checks
            new_score, reasons = self._calculate_social_score(existing_socials, token_info['name'], token_info['symbol'], None, telegram_results)
            
            details = {"source": "Telegram Update", "telegram_stats": telegram_results, "reasons": reasons}
            await self._update_token_socials(mint, None, None, None, new_score, self.config['SOCIALS_SCORE_TYPE_TELEGRAM'], details)
            
            return True
        except Exception as e:
            logger.error(f"🚨 Unexpected error in _process_telegram_update for {mint}: {e}", exc_info=True)
            return "Error UnhandledProcess"

    async def _refresh_initial_checks_queue(self):
        """Queues tokens that have never had a socials check (highest priority)."""
        try:
            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND t.socials_score IS NULL
                    GROUP BY t.mint ORDER BY volume DESC
                """)
            if rows:
                for row in rows:
                    if row["mint"] not in self.fetch_attempts:
                        priority = -float(row["volume"] or 0)  # High priority for active new tokens
                        await self.queue.put((priority, (row["mint"], 'INITIAL_METADATA')))
                logger.debug(f"🔄 Refreshed Socials queue with {len(rows)} initial checks.")
        except Exception as e:
            logger.error(f"🚨 Critical error in _refresh_initial_checks_queue: {e}", exc_info=True)

    async def _requeue_followup_metadata_checks(self):
        """Queues active tokens for a periodic re-check of their full metadata URI."""
        try:
            interval = self.config.get('SOCIALS_METADATA_UPDATE_INTERVAL_MINUTES', 60)
            # --- START FIX ---
            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS recent_volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND t.socials_score IS NOT NULL
                      AND t.socials_last_checked < NOW() - ($1 || ' minutes')::interval
                    GROUP BY t.mint ORDER BY recent_volume DESC;
                """, str(interval))
                
                if rows:
                    for row in rows:
                        if row["mint"] not in self.fetch_attempts:
                            # Lower priority based on volume + penalty for previous checks
                            check_count = await self.db_client.get_social_check_count(row["mint"], conn)
                            priority = -(float(row["recent_volume"] or 0) / (check_count + 1))
                            await self.queue.put((priority, (row["mint"], 'FOLLOWUP_METADATA')))
                    logger.info(f"🔁 Re-queued {len(rows)} tokens for follow-up metadata checks.")
            # --- END FIX ---
        except Exception as e:
            logger.error(f"🚨 Error in _requeue_followup_metadata_checks: {e}", exc_info=True)

    async def _requeue_telegram_updates(self):
        """Queues active tokens for a Telegram stats update."""
        try:
            interval = self.config.get('SOCIALS_TELEGRAM_UPDATE_INTERVAL_MINUTES', 15)
            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS recent_volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND t.telegram IS NOT NULL AND t.telegram != ''
                      AND t.socials_last_checked < NOW() - ($1 || ' minutes')::interval
                    GROUP BY t.mint ORDER BY recent_volume DESC;
                """, str(interval))
            if rows:
                for row in rows:
                     if row["mint"] not in self.fetch_attempts:
                        priority = -float(row['recent_volume'])
                        await self.queue.put((priority, (row['mint'], 'TELEGRAM_UPDATE')))
                logger.info(f"🔁 Re-queued {len(rows)} tokens for Telegram status update.")
        except Exception as e:
            logger.error(f"🚨 Error during Telegram re-queue process: {e}", exc_info=True)

    async def _worker(self):
        logger.info("🔗 Socials worker started.")
        while not self.state.shutdown_event.is_set():
            try:
                if self.queue.empty():
                    logger.debug("Socials queue is empty. Refilling...")
                    await self._refresh_initial_checks_queue()
                    await self._requeue_followup_metadata_checks()
                    await self._requeue_telegram_updates()
                    if self.queue.empty():
                        await self.state.wait_or_interrupt(timeout=15)
                        continue

                priority, (mint, check_type) = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                if self.fetch_attempts.get(mint, 0) >= MAX_FETCH_ATTEMPTS:
                    self.queue.task_done(); continue

                async with self.db_client.pool.acquire() as conn:
                    is_active = await conn.fetchval("SELECT is_active FROM tokens WHERE mint = $1", mint)
                if not is_active:
                    self.queue.task_done(); continue

                process_status = False
                if check_type in ['INITIAL_METADATA', 'FOLLOWUP_METADATA']:
                    process_status = await self._process_metadata_check(mint, is_initial_check=(check_type == 'INITIAL_METADATA'))
                elif check_type == 'TELEGRAM_UPDATE':
                    process_status = await self._process_telegram_update(mint)
                
                # --- Preserved Error Handling Logic ---
                permanent_failures = {"NOT_FOUND", "Error InvalidURI", "NO_PRIMARY_URI", "NO_TELEGRAM_LINK", "TELEGRAM_INVALID", "Error NotJSONContentType", "Error DecodeFailedStrict", "Error DecodeGeneral", "Error HTTP 404", "Error HTTP 403", "Error HTTP 401"}
                is_permanent_failure = isinstance(process_status, str) and any(pf in process_status for pf in permanent_failures)

                if process_status is True:
                    self.fetch_attempts.pop(mint, None)
                elif is_permanent_failure:
                    logger.warning(f" socials Socials Check for {mint} ('{check_type}') failed with permanent error: '{process_status}'. No more retries.")
                    self.fetch_attempts[mint] = MAX_FETCH_ATTEMPTS
                else:
                    current_attempts = self.fetch_attempts.get(mint, 0) + 1
                    self.fetch_attempts[mint] = current_attempts
                    logger.warning(f" socials Socials Check for {mint} ('{check_type}') failed with transient error ('{process_status}'). Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")
                    if current_attempts < MAX_FETCH_ATTEMPTS:
                        await self.queue.put((priority, (mint, check_type)))
                    else:
                        await self.queue.put((DEPRIORITIZED_PRIORITY, (mint, check_type)))
                        logger.warning(f"🚩 Max socials check attempts ({MAX_FETCH_ATTEMPTS}) reached for {mint}. Deprioritizing.")
                
                self.queue.task_done()

            except asyncio.TimeoutError: continue
            except asyncio.CancelledError: logger.info("🛑 Socials Check worker task cancelled."); break
            except Exception as e:
                logger.error(f"🚨 Unexpected error in Socials Check worker main loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=10)
        
        logger.info("🛑 Socials check worker shutting down.")

    def start(self) -> list[asyncio.Task]:
        logger.info("Creating Socials Check background task...")
        return [asyncio.create_task(self._worker(), name="socialscheck_worker")]
```

#### 📄 `01_create_tokens.sql`
*path: `sql/01_create_tokens.sql`*

```sql
-- Create the tokens table
CREATE TABLE IF NOT EXISTS tokens (
    mint TEXT PRIMARY KEY,          -- token mint
    traderPublicKey TEXT,           -- token creator's wallet address
    initialBuy NUMERIC,             -- initially buyed tokens
    solAmount NUMERIC,              -- initially spent amount of SOL
    bondingCurveKey TEXT,           -- bondingCurve key
    vTokensInBondingCurve NUMERIC,  -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,     -- SOL in BondingCurve
    marketCapSol NUMERIC,           -- market cap in SOL
    name TEXT,                      -- token name
    symbol TEXT,                    -- token symbol
    uri TEXT,                       -- META URL
    website TEXT,                   -- website link, fetched from META URL
    telegram TEXT,                  -- telegram link, fetched from META URL
    twitter TEXT,                   -- twitter link, fetched from META URL
    socials_score INTEGER,          -- calculated social score
    socials_last_checked TIMESTAMP WITH TIME ZONE,  -- last try to fetch META URL
    sol_price_usd NUMERIC,                          -- SOL price at token creation
    is_active BOOLEAN DEFAULT TRUE,                 -- TRUE or FALLS for considering in check_buy_opportunities
    last_trade TIMESTAMP WITH TIME ZONE,            -- TIMESTAMP of the last Trade event, updated when a new TRADE is fetched
    cooldown_until TIMESTAMP WITH TIME ZONE,        -- <<< ADD THIS LINE: Prevent re-buys until this time
    data_source TEXT DEFAULT 'PUMP', -- 'PUMP' for WebSocket, 'DEXSCREENER' for API
    ai_last_evaluation_ts TIMESTAMPTZ, -- Timestamp of the last AI evaluation
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- creation TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS tokens_backup (
    LIKE tokens INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS ai_last_evaluation_ts TIMESTAMPTZ;
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_reason TEXT;
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE tokens_backup ALTER COLUMN timestamp DROP DEFAULT;
```

#### 📄 `02_create_trades.sql`
*path: `sql/02_create_trades.sql`*

```sql
-- Create the trades table
CREATE TABLE IF NOT EXISTS trades (
    signature TEXT PRIMARY KEY,         -- signature of the token event
    mint TEXT,                          -- tokens mint address
    trader_pubkey TEXT,                 -- The wallet address of the trader
    tx_type TEXT,                       -- event type 'buy' or 'sell'
    token_amount NUMERIC,               -- amount of tokens traded
    sol_amount NUMERIC,                 -- amount of SOL traded
    price NUMERIC,                      -- token price in SOL
    bondingCurveKey TEXT,               -- BondingCurve key
    vTokensInBondingCurve NUMERIC,      -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,         -- amount of SOL in BondingCurve
    marketCapSol NUMERIC,               -- market cap in SOL
    sol_price_usd NUMERIC,              -- actual SOL price in USD at the time of the trade event
    market_cap_calculated NUMERIC,      -- calculated market cap in USD
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of the trade event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS trades_backup (
    LIKE trades INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE trades_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE trades_backup ALTER COLUMN timestamp DROP DEFAULT;
```

#### 📄 `03_create_rugcheck.sql`
*path: `sql/03_create_rugcheck.sql`*

```sql
-- sql/03_create_rugcheck.sql

CREATE TABLE IF NOT EXISTS rugcheck (
    id SERIAL PRIMARY KEY, -- Use a serial ID as the primary key
    mint TEXT REFERENCES tokens(mint) ON DELETE CASCADE, -- Mint is no longer primary, but still references tokens
    tokenProgram TEXT,
    creator TEXT,
    token_mintAuthority TEXT,
    token_supply NUMERIC,
    token_decimals INTEGER,
    token_isInitialized BOOLEAN,
    token_freezeAuthority TEXT,
    tokenMeta_name TEXT,
    tokenMeta_symbol TEXT,
    tokenMeta_uri TEXT,
    tokenMeta_mutable BOOLEAN,
    tokenMeta_updateAuthority TEXT,
    freezeAuthority TEXT,
    mintAuthority TEXT,
    risks TEXT,
    score INTEGER,
    fileMeta_description TEXT,
    fileMeta_name TEXT,
    fileMeta_symbol TEXT,
    fileMeta_image TEXT,
    totalMarketLiquidity NUMERIC,
    totalLPProviders INTEGER,
    rugged BOOLEAN,
    tokenType TEXT,
    transferFee_pct NUMERIC,
    transferFee_maxAmount NUMERIC,
    transferFee_authority TEXT,
    graphInsidersDetected INTEGER,
    detectedAt TIMESTAMP WITH TIME ZONE,
    full_data TEXT,
    last_checked TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS rugcheck_backup (
    LIKE rugcheck INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE rugcheck_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE rugcheck_backup ALTER COLUMN timestamp DROP DEFAULT;
```

#### 📄 `04_create_portfolio.sql`
*path: `sql/04_create_portfolio.sql`*

```sql
-- path: sql/04_create_portfolio.sql

-- Original portfolio table creation
CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    mint TEXT,
    tx_type TEXT,                     -- 'buy' or 'sell'
    price NUMERIC,                    -- Price per token at the time of tx
    market_cap NUMERIC,               -- Market cap at the time of tx
    sol_amount NUMERIC,               -- Gross SOL spent (buy) or received (sell, before fees)
    sol_price_usd NUMERIC,            -- SOL price in USD at the time of tx
    tokens NUMERIC,                   -- Number of tokens bought or sold in this tx
    fee NUMERIC,                      -- Fee associated with this tx
    tip NUMERIC,                      -- Tip associated with this tx
    profit NUMERIC,                   -- Profit/Loss for sell tx (net_sol_received - cost_basis)
    status TEXT,                      -- Status of the original buy position ('active', 'closed')
    reason TEXT,                      -- Reason for sell ('Stop Loss', 'First TP', etc.)
    buy_reason TEXT,                  -- <<< ADD THIS LINE: Reason for buy ('Rule-Based', 'AI-Advised')

    -- Fields primarily relevant for the original 'buy' entry
    total_investment_sol NUMERIC,     -- Total SOL invested in this position (including fees)
    initial_tokens NUMERIC,           -- Total tokens acquired in the initial buy tx
    remaining_tokens NUMERIC,         -- Tokens currently held from the initial buy tx (updated on sells)
    highest_price NUMERIC NOT NULL DEFAULT 0.0, -- Highest price observed since the buy
    stop_loss_price NUMERIC,          -- Current active stop loss price level
    initial_tp_price NUMERIC,         -- Calculated price for the first take profit
    second_tp_price NUMERIC,          -- Calculated price for the second take profit
    first_tp_hit BOOLEAN NOT NULL DEFAULT FALSE, -- Flag indicating if the first TP has been triggered

    settings JSONB,                   -- Settings for this position (e.g. stop loss price)

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS portfolio_backup (
    LIKE portfolio INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE portfolio_backup ADD COLUMN IF NOT EXISTS backed_up TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE portfolio_backup ALTER COLUMN timestamp DROP DEFAULT;
```

#### 📄 `05_create_migrations.sql`
*path: `sql/05_create_migrations.sql`*

```sql
CREATE TABLE IF NOT EXISTS migrations (
    signature TEXT PRIMARY KEY, -- signature of the token event
    mint TEXT,                  -- tokens mint address
    txtype TEXT,                -- event type 'migrate'
    pool TEXT,                  -- migration pool
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of migration event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS migrations_backup (
    LIKE migrations INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE migrations_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE migrations_backup ALTER COLUMN timestamp DROP DEFAULT;
```

#### 📄 `06_create_creator_wallets.sql`
*path: `sql/06_create_creator_wallets.sql`*

```sql
CREATE TABLE IF NOT EXISTS creator_wallets (
    wallet_address TEXT PRIMARY KEY,
    token_count INTEGER DEFAULT 0,
    last_token_time TIMESTAMP WITH TIME ZONE
);
```

#### 📄 `07_create_sol_price_usd.sql`
*path: `sql/07_create_sol_price_usd.sql`*

```sql
CREATE TABLE IF NOT EXISTS sol_price_usd (
    id SERIAL PRIMARY KEY,
    price  NUMERIC(15, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### 📄 `08_create_bot_heartbeat.sql`
*path: `sql/08_create_bot_heartbeat.sql`*

```sql
-- sql/10_create_bot_heartbeat.sql
CREATE TABLE IF NOT EXISTS bot_heartbeat (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    event_type TEXT DEFAULT 'heartbeat', -- e.g., 'heartbeat', 'config_update', 'shutdown_signal'
    details JSONB -- Optional: for storing details about the event, like which config was updated
);

CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_timestamp ON bot_heartbeat(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_event_type ON bot_heartbeat(event_type);
```

#### 📄 `09_create_configuration.sql`
*path: `sql/09_create_configuration.sql`*

```sql
-- Create the configurations table
CREATE TABLE IF NOT EXISTS configurations (
    key TEXT PRIMARY KEY,
    value TEXT,
    type TEXT NOT NULL CHECK (type IN ('int', 'float', 'bool', 'str', 'list')),
    description TEXT, -- Optional: for human-readable descriptions
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Trigger to update last_updated timestamp automatically
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.last_updated = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_configurations_last_updated
BEFORE UPDATE ON configurations
FOR EACH ROW
EXECUTE FUNCTION update_last_updated_column();

CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations(key);
```

#### 📄 `10_create_dexscreener_data.sql`
*path: `sql/10_create_dexscreener_data.sql`*

```sql
-- Table to store periodic data snapshots from the DEX Screener API for migrated tokens
CREATE TABLE IF NOT EXISTS dexscreener_data (
    id SERIAL PRIMARY KEY,
    pair_address TEXT NOT NULL,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price_usd NUMERIC,
    price_native NUMERIC,
    sol_price_usd NUMERIC, -- <<< ADDED THIS COLUMN
    liquidity_usd NUMERIC,
    market_cap NUMERIC,
    fdv NUMERIC,
    
    -- Volume Columns
    volume_m5 NUMERIC,
    volume_h1 NUMERIC,
    volume_h6 NUMERIC,
    volume_h24 NUMERIC,
    
    -- Price Change Columns
    price_change_m5 NUMERIC,
    price_change_h1 NUMERIC,
    price_change_h6 NUMERIC,
    price_change_h24 NUMERIC,

    -- Transaction Columns
    buys_m5 INTEGER,
    sells_m5 INTEGER,
    buys_h1 INTEGER,
    sells_h1 INTEGER,
    buys_h6 INTEGER,
    sells_h6 INTEGER,
    buys_h24 INTEGER,
    sells_h24 INTEGER,

    full_response JSONB
);

CREATE INDEX IF NOT EXISTS idx_dexscreener_data_mint_timestamp ON dexscreener_data(mint_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_pair_address ON dexscreener_data(pair_address);

-- Backup table creation
CREATE TABLE IF NOT EXISTS dexscreener_data_backup (
    LIKE dexscreener_data INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE dexscreener_data_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE dexscreener_data_backup ALTER COLUMN timestamp DROP DEFAULT;
```

#### 📄 `11_create_completed_trades.sql`
*path: `sql/11_create_completed_trades.sql`*

```sql
CREATE TABLE IF NOT EXISTS public.completed_trades
(
    trade_id integer NOT NULL DEFAULT nextval('completed_trades_trade_id_seq'::regclass),
    token_address character varying(44) COLLATE pg_catalog."default" NOT NULL,
    side character varying(4) COLLATE pg_catalog."default" NOT NULL,
    amount_in_sol numeric NOT NULL,
    amount_out_tokens numeric NOT NULL,
    fill_price numeric NOT NULL,
    market_cap_at_trade numeric,
    tx_fee_sol numeric,
    tip_sol numeric DEFAULT 0,
    slippage_percent numeric,
    trade_context jsonb,
    created_at timestamp with time zone DEFAULT now(),
    social_velocity double precision,
    volatility_at_entry double precision,
    rugcheck_score_at_entry integer,
    market_regime text COLLATE pg_catalog."default",
    crossed_cooldown_boundary boolean,
    sell_fraction double precision,
    rebuy boolean DEFAULT false,
    CONSTRAINT completed_trades_pkey PRIMARY KEY (trade_id),
    CONSTRAINT completed_trades_side_check CHECK (side::text = ANY (ARRAY['buy'::character varying, 'sell'::character varying]::text[]))
)
```

#### 📄 `12_create_indexes.sql`
*path: `sql/12_create_indexes.sql`*

```sql
-- *********************************************
-- INDEXES FOR BASE TABLES
-- *********************************************

-- Tokens Table
CREATE INDEX IF NOT EXISTS idx_tokens_is_active_timestamp ON public.tokens USING btree (is_active, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_tokens_mint ON public.tokens USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_name ON public.tokens USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_socials_score ON public.tokens USING btree (socials_score);
CREATE INDEX IF NOT EXISTS idx_tokens_traderpublickey ON public.tokens USING btree (traderpublickey);

-- Trades Table
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp ON trades(mint, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp_sol ON trades(mint, timestamp DESC, sol_amount); -- For View Queries

-- Portfolio Table
CREATE INDEX IF NOT EXISTS idx_portfolio_active_buy ON portfolio USING btree (mint, tx_type, status) WHERE ((status = 'active'::text) AND (tx_type = 'buy'::text));
CREATE INDEX IF NOT EXISTS idx_portfolio_mint ON portfolio USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_portfolio_mint_status ON portfolio USING btree (mint, status);

-- Rugcheck Table
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked ON rugcheck(mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked_desc ON rugcheck USING btree (mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_score ON rugcheck USING btree (score);

-- Dexscreener_data Table
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_mint_timestamp ON dexscreener_data USING btree (mint_address, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_pair_address ON dexscreener_data USING btree (pair_address);

-- bot_heartbeat Table
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_event_type ON bot_heartbeat USING btree (event_type);
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_timestamp ON bot_heartbeat USING btree ("timestamp" DESC);

-- configurations Table
CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations USING btree (key);

-- *********************************************
-- INDEXES FOR BACKUP TABLES
-- *********************************************

-- Tokens Backup
CREATE INDEX IF NOT EXISTS idx_tokens_backup_mint ON tokens_backup USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_name ON tokens_backup USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_socials_score ON tokens_backup USING btree (socials_score);

-- Trades Backup
CREATE INDEX IF NOT EXISTS idx_trades_backup_mint_timestamp ON trades_backup(mint, timestamp DESC);

-- Rugcheck Backup
CREATE INDEX IF NOT EXISTS idx_rugcheck_backup_mint_last_checked ON rugcheck_backup USING btree (mint, last_checked DESC);

-- Dexscreener_data Backup
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_mint_address_timestamp_idx ON dexscreener_data_backup USING btree (mint_address, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_pair_address_idx ON dexscreener_data_backup USING btree (pair_address);
```

#### 📄 `13_create_views.sql`
*path: `sql/13_create_views.sql`*

```sql
-- sql/12_create_views.sql

-- View for combined tokens and tokens_backup
-- Prioritizes data from 'tokens' if a mint exists in both.
CREATE OR REPLACE VIEW v_tokens AS
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, is_active, last_trade,
    cooldown_until,
    '' as backup_reason, timestamp
FROM tokens
UNION ALL
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, FALSE AS is_active, last_trade,
    cooldown_until,
    backup_reason, timestamp
FROM tokens_backup tb
WHERE NOT EXISTS (SELECT 1 FROM tokens t WHERE t.mint = tb.mint);

-- View for combined trades and trades_backup
CREATE OR REPLACE VIEW v_trades AS
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades
UNION ALL
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades_backup;

-- View for combined rugcheck and rugcheck_backup
-- Note: Getting the *latest* score per mint will be handled in the query using this view.
CREATE OR REPLACE VIEW v_rugcheck AS
SELECT mint, score, token_supply, last_checked, timestamp FROM rugcheck
UNION ALL
SELECT mint, score, token_supply, last_checked, timestamp FROM rugcheck_backup;

-- View for combined migrations and migrations_backup
CREATE OR REPLACE VIEW v_migrations AS
SELECT 
    signature,
    mint,
    txType,
    pool,
    timestamp,
    NULL AS backup_timestamp,
    'active' AS record_source
FROM 
    migrations

UNION ALL

SELECT 
    signature,
    mint,
    txType,
    pool,
    timestamp,
    backup_timestamp,
    'backup' AS record_source
FROM 
    migrations_backup;


-- View for combined dexscreener_data and dexscreener_data_backup
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data
UNION ALL
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data_backup;


-- Creates unified views for market data from both Pump.fun and DEX Screener.

-- First, a helper view for all Dexscreener data (live + backup).
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data
UNION ALL
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data_backup;

-- ===================================================================================
--  HISTORICAL UNIFIED VIEW (Includes Backups via v_* views)
--  PURPOSE: For backtesting, GA/RL training, and full historical analysis.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_historical AS
SELECT
    mint, timestamp, tx_type, token_amount, sol_amount,
    price AS price_sol, marketCapSol AS market_cap_sol, market_cap_calculated as market_cap_usd,
    (sol_amount * sol_price_usd) AS volume_usd, -- <-- ADDED: Unified USD volume
    'PUMP' AS data_source
FROM v_trades -- Querying backup-inclusive view
WHERE price IS NOT NULL AND price > 0 AND sol_amount > 0 AND token_amount > 0
UNION ALL
SELECT
    mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount,
    (volume_m5 / sol_price_usd) AS sol_amount,      -- <-- CORRECTED: This is now SOL volume
    (price_usd / sol_price_usd) AS price_sol,
    (market_cap / sol_price_usd) AS market_cap_sol,
    market_cap AS market_cap_usd,
    volume_m5 AS volume_usd,                        -- <-- ADDED: Unified USD volume
    'DEXSCREENER' AS data_source
FROM v_dexscreener_data; -- Querying backup-inclusive view

-- ===================================================================================
--  LIVE-ONLY UNIFIED VIEW (Excludes Backups)
--  PURPOSE: For fast, forward-looking queries driving live trade decisions.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_live AS
SELECT
    mint, timestamp, tx_type, token_amount, sol_amount,
    price AS price_sol, marketCapSol AS market_cap_sol, market_cap_calculated as market_cap_usd,
    (sol_amount * sol_price_usd) AS volume_usd, -- <-- ADDED: Unified USD volume
    'PUMP' AS data_source
FROM trades -- Querying LIVE table
WHERE price IS NOT NULL AND price > 0 AND sol_amount > 0 AND token_amount > 0
UNION ALL
SELECT
    mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount,
    (volume_m5 / sol_price_usd) AS sol_amount,      -- <-- CORRECTED: This is now SOL volume
    (price_usd / sol_price_usd) AS price_sol,
    (market_cap / sol_price_usd) AS market_cap_sol,
    market_cap AS market_cap_usd,
    volume_m5 AS volume_usd,                        -- <-- ADDED: Unified USD volume
    'DEXSCREENER' AS data_source
FROM dexscreener_data; -- Querying LIVE table
```

#### 📄 `14_create_rl_tables.sql`
*path: `sql/14_create_rl_tables.sql`*

```sql
-- Table to track training sessions and their outcomes
CREATE TABLE IF NOT EXISTS rl_training_sessions (
    session_id UUID PRIMARY KEY,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    hyperparameters JSONB,
    final_metrics JSONB,
    model_path TEXT,
    notes TEXT -- For manual notes on the training run
);

-- Table for detailed performance logging of the agent's actions
-- Partitioning by time is crucial for performance with large datasets
CREATE TABLE IF NOT EXISTS rl_agent_performance (
    timestamp TIMESTAMPTZ NOT NULL,
    token_mint TEXT NOT NULL,
    action_taken JSONB,
    reward REAL,
    observation JSONB,
    session_id UUID REFERENCES rl_training_sessions(session_id)
) PARTITION BY RANGE (timestamp);

-- Optional: Create partitions for the next few months as an example
-- In a production PostgreSQL environment, you would automate this process.
CREATE TABLE IF NOT EXISTS rl_agent_performance_y2025m08 PARTITION OF rl_agent_performance
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS rl_agent_performance_y2025m09 PARTITION OF rl_agent_performance
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

-- Create an index on the partitioned table
CREATE INDEX IF NOT EXISTS idx_rl_agent_performance_timestamp ON rl_agent_performance(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_rl_agent_performance_token_mint ON rl_agent_performance(token_mint);
```

#### 📄 `15_create_social_scores.sql`
*path: `sql/15_create_social_scores.sql`*

```sql
-- sql/15_create_social_scores.sql

-- Create a table to store historical and detailed social scoring data
CREATE TABLE IF NOT EXISTS social_scores (
    id SERIAL PRIMARY KEY,
    mint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score_type TEXT NOT NULL, -- e.g., 'INITIAL', 'TELEGRAM_UPDATE', 'WEBSITE_UPDATE'
    score_value INTEGER NOT NULL,
    details JSONB, -- For storing specific metrics like member count, online count, etc.
    CONSTRAINT fk_mint
        FOREIGN KEY(mint)
        REFERENCES tokens(mint)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_social_scores_mint_timestamp ON social_scores(mint, timestamp DESC);

-- Create the backup table for social_scores
CREATE TABLE IF NOT EXISTS social_scores_backup (
    id INTEGER NOT NULL,
    mint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    score_type TEXT NOT NULL,
    score_value INTEGER NOT NULL,
    details JSONB,
    backup_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(id) -- Primary key to handle conflicts on backup
);

-- Add indexes for querying backups
CREATE INDEX IF NOT EXISTS idx_social_scores_backup_mint_timestamp ON social_scores_backup(mint, timestamp DESC);

-- View to combine live and backed-up social score entries
CREATE OR REPLACE VIEW v_social_scores AS
SELECT
    id,
    mint,
    timestamp,
    score_type,
    score_value,
    details,
    NULL AS backup_timestamp,
    'active' as record_source
FROM
    social_scores

UNION ALL

SELECT
    id,
    mint,
    timestamp,
    score_type,
    score_value,
    details,
    backup_timestamp,
    'backup' as record_source
FROM
    social_scores_backup;
```

#### 📄 `16_create_ga_tables.sql`
*path: `sql/16_create_ga_tables.sql`*

```sql
-- FILE: schema.sql
--
-- This script sets up the database schema for storing results from the
-- Genetic Algorithm (GA) optimizer. It's designed for PostgreSQL.

-- Drop existing tables in reverse order of dependency to avoid foreign key errors.
/* 
DROP TABLE IF EXISTS ga_trades;
DROP TABLE IF EXISTS ga_backtests;
DROP TABLE IF EXISTS ga_solutions;
DROP TABLE IF EXISTS ga_runs;
*/

-- =================================================================
-- Table to track each individual execution of the optimizer.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_runs (
    run_id UUID PRIMARY KEY,
    -- The timestamp when this run was first recorded in the database.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE ga_runs IS 'Stores metadata for each complete execution of the GA optimizer.';
COMMENT ON COLUMN ga_runs.run_id IS 'Unique identifier for the optimization run.';


-- =================================================================
-- Table to store each unique solution (parameter set) for a given run.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_solutions (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES ga_runs(run_id) ON DELETE CASCADE,
    generation INT NOT NULL,
    solution_idx INT NOT NULL,
    -- Using JSONB is highly efficient for storing and querying parameter sets.
    parameters JSONB NOT NULL,
    -- Ensures that each solution within a generation is unique for a given run.
    UNIQUE(run_id, generation, solution_idx)
);

COMMENT ON TABLE ga_solutions IS 'Represents a single individual (a set of parameters) within a generation.';
COMMENT ON COLUMN ga_solutions.run_id IS 'Foreign key linking to the specific optimization run.';
COMMENT ON COLUMN ga_solutions.parameters IS 'The complete set of parameters for this solution.';

-- Index for quickly finding all solutions for a specific run.
CREATE INDEX IF NOT EXISTS idx_ga_solutions_run_id ON ga_solutions(run_id);
-- A GIN index allows for efficient querying of the JSONB parameter data.
CREATE INDEX IF NOT EXISTS idx_ga_solutions_parameters_gin ON ga_solutions USING GIN(parameters);


-- =================================================================
-- Table to store the results of a backtest for a given solution on a specific token.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_backtests (
    id SERIAL PRIMARY KEY,
    solution_id INT NOT NULL REFERENCES ga_solutions(id) ON DELETE CASCADE,
    mint_tested TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT, -- Populated only if status is 'failed'
    
    -- Performance Metrics
    final_portfolio_value NUMERIC(20, 10),
    total_pnl NUMERIC(20, 10),
    total_return_pct NUMERIC(20, 10),
    win_rate NUMERIC(10, 5),
    profit_factor NUMERIC(20, 10),
    max_drawdown NUMERIC(10, 5),
    total_trades INT,
    
    -- Simulation Metadata
    simulation_start_ts TIMESTAMPTZ,
    simulation_end_ts TIMESTAMPTZ,
    simulation_end_reason TEXT,
    
    -- Ensures a solution is only tested once per mint.
    UNIQUE(solution_id, mint_tested)
);

COMMENT ON TABLE ga_backtests IS 'Stores the summary results of a single backtest simulation.';
COMMENT ON COLUMN ga_backtests.solution_id IS 'Foreign key linking to the solution that was tested.';
COMMENT ON COLUMN ga_backtests.mint_tested IS 'The token mint address used in this backtest.';

-- Index for quickly finding all backtests for a given solution.
CREATE INDEX IF NOT EXISTS idx_ga_backtests_solution_id ON ga_backtests(solution_id);
-- Index for quickly finding high-performing backtests.
CREATE INDEX IF NOT EXISTS idx_ga_backtests_final_portfolio_value ON ga_backtests(final_portfolio_value DESC);


-- =================================================================
-- Table to store every individual trade from a backtest.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_trades (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INT NOT NULL REFERENCES ga_backtests(id) ON DELETE CASCADE,
    
    -- Trade Details
    "timestamp" TIMESTAMPTZ NOT NULL,
    "type" TEXT NOT NULL, -- 'buy' or 'sell'
    price NUMERIC(30, 20) NOT NULL,
    amount_sol NUMERIC(20, 10),
    amount_tokens NUMERIC(30, 10),
    reason TEXT,
    pnl NUMERIC(20, 10)
);

COMMENT ON TABLE ga_trades IS 'Stores every individual trade action from all backtest histories.';
COMMENT ON COLUMN ga_trades.backtest_id IS 'Foreign key linking to the backtest this trade belongs to.';

-- Index for quickly retrieving all trades for a specific backtest.
CREATE INDEX IF NOT EXISTS idx_ga_trades_backtest_id ON ga_trades(backtest_id);
-- Index for time-series analysis of trades.
CREATE INDEX IF NOT EXISTS idx_ga_trades_timestamp ON ga_trades("timestamp" DESC);
```

#### 📄 `17_create_ai_decision_memory.sql`
*path: `sql/17_create_ai_decision_memory.sql`*

```sql
-- Creates the extension if it doesn't exist (you've already done this, but it's safe to include)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the table to store AI decision snapshots for RAG
CREATE TABLE IF NOT EXISTS ai_decision_memory (
    id SERIAL PRIMARY KEY,
    mint TEXT NOT NULL,
    evaluation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_context TEXT,
    decision TEXT,
    confidence INTEGER,
    model_name TEXT, -- <-- ADDED THIS COLUMN
    explanation TEXT,
    
    -- This is the document that gets queried (the text summary)
    situation_summary TEXT, 
    
    -- This is the vector embedding for the summary
    -- all-MiniLM-L6-v2 produces 384-dimensional vectors
    embedding vector(384), 
    
    -- Store source, mcap, volatility etc. as structured data
    metadata JSONB 
);

-- Index for fast retrieval by mint
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_mint ON ai_decision_memory(mint);

-- Index for fast retrieval by timestamp
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_timestamp ON ai_decision_memory(evaluation_timestamp DESC);

-- Create a vector index for fast similarity search (ANN)
-- This is crucial for performance.
-- We use an IVFFlat index, a good all-around choice.
-- 'lists = 100' is a good starting point if you expect < 1 million records.
-- You can tune this later.
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_embedding_ivfflat ON ai_decision_memory 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Note: Building the index can take time. You may need to run
-- VACUUM ANALYZE ai_decision_memory;
-- periodically after large inserts.
```

#### 📄 `18_create_market_knowledge_base.sql`
*path: `sql/18_create_market_knowledge_base.sql`*

```sql
CREATE TABLE IF NOT EXISTS market_knowledge_base (
    id SERIAL PRIMARY KEY,
    mint TEXT UNIQUE,
    summary TEXT,
    embedding vector(384), -- Same dimension as ai_decision_memory
    metadata JSONB, -- Store creator, reason, max_mcap, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mkt_kb_embedding_ivfflat ON market_knowledge_base 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
```

#### 📄 `state_manager.py`
*path: `state_manager.py`*

```python
"""
state.py - Centralized storage for dynamic global values.
Manages mutable global state such as SOL price, shutdown flag, active subscriptions, and API rate timestamps.
"""
import asyncio
from asyncio import Queue
from collections import deque
import config.config as config # Import config to access INITIAL_SOL_BALANCE
import json # Added for file writing
from bot_logger import logger
import os
from typing import Optional
from datetime import datetime

# Define the path for the shared SOL price file
SOL_PRICE_FILE = 'data/sol_price.json'
SUBSCRIPTIONS_FILE = 'data/current_subscriptions.json'

class GlobalState:
    """Thread-safe Singleton class to store global state variables."""
    _instance = None
    _lock = asyncio.Lock()  # Ensures only one instance is created

    def __init__(self):
        if GlobalState._instance is not None:
            raise Exception("This class is a singleton!")

        """Initialize state variables."""
        self.shutdown_event = asyncio.Event()  # 🚀 Interruptible sleep support

        self.websocket_handler = None  # 🚀 Store WebSocketHandler instance
        self.new_token_subscription = False  # WebSocket subscription status
        self.migration_stream_subscribed = False  # Migration stream subscription status 
        self.active_token_subscriptions = set()  # Active token subscriptions

        self.sol_price = None          # SOL price (updated hourly)
        self.db_client = None          # Database client instance
        self.is_buying_enabled = True # ADDED: Flag to control buy orders

        # API rate limiting
        self.request_timestamps = deque(maxlen=10)  # API request tracker

        # PnL Tracking
        self.current_sol_balance = float(config._INITIAL_SOL_BALANCE) # Initialize from config

        # Queues
        self.rugcheck_queue = asyncio.PriorityQueue()  # RugCheck processing queue
        self.socialscheck_queue = asyncio.PriorityQueue()  # SocialsCheck processing queue
        self.enrichment_queue = asyncio.Queue() # Transaction enrichment queue
        self.ai_evaluation_queue = asyncio.PriorityQueue(maxsize=config.AI_QUEUE_MAX_SIZE) # AI eval queue with max size
        self.ai_queue_mints = set() # Tracks mints currently in the AI queue
        self.ai_queue_lock = asyncio.Lock() # Lock to protect the set

        self.ws_refresh_next_run_ts: Optional[datetime] = None

        # Concurrency control
        self.lock = asyncio.Lock()  # General state lock
        self.db_write_lock = asyncio.Lock()  # Database write lock

        # In GlobalState.__init__
        self.market_regime: str = "NEUTRAL"
        self.market_regime_lock = asyncio.Lock()
        

    def _load_subscriptions_from_file(self):
        """Load active token subscriptions from file if it exists."""
        try:
            if os.path.exists(SUBSCRIPTIONS_FILE):
                with open(SUBSCRIPTIONS_FILE, 'r') as f:
                    return set(json.load(f))
            else:
                return set()
        except Exception as e:
            logger.error(f"Error loading subscriptions from file: {e}")
            return set()

    def _save_subscriptions_to_file(self):
        """Save current active token subscriptions to file atomically."""
        # Ensure data directory exists (it's created in TradingBot, but good to be robust)
        data_dir = os.path.dirname(SUBSCRIPTIONS_FILE)
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
            except OSError as e:
                logger.error(f"Could not create data directory {data_dir}: {e}")
                return # Cannot proceed if directory cannot be created

        temp_file_path = SUBSCRIPTIONS_FILE + ".tmp"
        try:
            # The self.active_token_subscriptions set is already under self.lock in the calling methods
            # So, here we just perform the file operation.
            with open(temp_file_path, 'w') as f:
                json.dump(list(self.active_token_subscriptions), f, indent=2)
            os.replace(temp_file_path, SUBSCRIPTIONS_FILE) # Atomic rename
            # logger.debug(f"Saved {len(self.active_token_subscriptions)} subscriptions to {SUBSCRIPTIONS_FILE}")
        except Exception as e:
            logger.error(f"Error saving subscriptions to file {SUBSCRIPTIONS_FILE}: {e}")
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as ose:
                    logger.error(f"Error removing temporary subscription file {temp_file_path}: {ose}")

    def remove_from_rugcheck_queue(self, mint: str):
        """Remove mint from RugCheck queue."""
        # Assuming self.rugcheck_queue is a priority queue; clear entries for mint
        while True:
            try:
                priority, queued_mint = self.rugcheck_queue.get_nowait()
                if queued_mint != mint:
                    self.rugcheck_queue.put((priority, queued_mint))
                else:
                    logger.debug(f"Removed {mint} from RugCheck queue.")
            except asyncio.QueueEmpty:
                break

    def remove_from_socials_queue(self, mint: str):
        """Remove mint from Socials queue."""
        # Similar to above
        while True:
            try:
                priority, queued_mint = self.socials_queue.get_nowait()  # Assume exists
                if queued_mint != mint:
                    self.socials_queue.put((priority, queued_mint))
                else:
                    logger.debug(f"Removed {mint} from Socials queue.")
            except asyncio.QueueEmpty:
                break

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def wait_for_shutdown(self):
        await self.shutdown_event.wait()

    def trigger_shutdown(self):
        self.shutdown_event.set()

    async def set_websocket_handler(self, handler):
        async with self.lock:
            self.websocket_handler = handler

    async def set_db_client(self, client):
        async with self.lock:
            self.db_client = client

    ## 🚀 SOL Price Management
    async def set_sol_price(self, price: float):
        """Sets the in-memory SOL price and writes it to a shared file."""
        if price is None:
            logger.warning("Attempted to set SOL price to None. Skipping file write.")
            return
            
        async with self.lock:
            self.sol_price = price
            # Also write to the shared file for the web app process
            try:
                # Use 'w' to overwrite the file completely each time
                with open(SOL_PRICE_FILE, 'w') as f:
                    json.dump({"price": price}, f)
                # logger.debug(f"Wrote SOL price {price} to {SOL_PRICE_FILE}") # Optional: debug log
            except IOError as e:
                logger.error(f"Failed to write SOL price to {SOL_PRICE_FILE}: {e}")
            except Exception as e: # Catch potential JSON errors too
                logger.error(f"Unexpected error writing SOL price to {SOL_PRICE_FILE}: {e}")

    #🚀 Market Regime Awareness
    async def set_market_regime(self, regime: str):
        async with self.market_regime_lock:
            self.market_regime = regime

    async def get_market_regime(self) -> str:
        async with self.market_regime_lock:
            return self.market_regime

    async def get_sol_price(self) -> float:
        async with self.lock:
            return self.sol_price

    async def wait_or_interrupt(self, timeout: float):
        """Waits for a given timeout, but exits early if shutdown is triggered."""
        # logger.debug(f"wait_or_interrupt: waiting for {timeout} seconds")
        try:
            await asyncio.wait_for(self.shutdown_event.wait(), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            #logger.debug("wait_or_interrupt: timeout expired normally")
            pass  # This is expected if the timeout expires normally

    ## 🚀 Subscription Management
    async def add_token_subscription(self, mint: str):
        async with self.lock:
            self.active_token_subscriptions.add(mint)
        self._save_subscriptions_to_file()

    async def remove_token_subscription(self, mint: str):
        async with self.lock:
            self.active_token_subscriptions.discard(mint)
        self._save_subscriptions_to_file()

    async def get_token_subscriptions(self):
        async with self.lock:
            return set(self.active_token_subscriptions)

    ## 🚀 WebSocket Subscription Flag
    async def set_new_token_subscription(self, status: bool):
        async with self.lock:
            self.new_token_subscription = status

    async def get_new_token_subscription(self) -> bool:
        async with self.lock:
            return self.new_token_subscription
        
    async def set_migration_subscription(self, status: bool):
        async with self.lock:
            self.migration_stream_subscribed = status

    async def get_migration_subscription(self) -> bool:
        async with self.lock:
            return self.migration_stream_subscribed
        
    async def set_ws_refresh_next_run_ts(self, timestamp: Optional[datetime]):
        """Sets the timestamp for the next WebSocket subscription refresh."""
        async with self.lock:
            self.ws_refresh_next_run_ts = timestamp

    async def get_ws_refresh_next_run_ts(self) -> Optional[datetime]:
        """Gets the timestamp for the next WebSocket subscription refresh."""
        async with self.lock:
            return self.ws_refresh_next_run_ts

    ## 🚀 API Rate Limiting
    async def add_request_timestamp(self, timestamp):
        async with self.lock:
            self.request_timestamps.append(timestamp)

    async def get_request_timestamps(self):
        async with self.lock:
            return list(self.request_timestamps)

    ## 🚀 Queue Accessors
    def get_rugcheck_queue(self) -> asyncio.PriorityQueue:
        return self.rugcheck_queue

    def get_socialscheck_queue(self) -> asyncio.PriorityQueue:
        return self.socialscheck_queue
    
    def get_enrichment_queue(self) -> asyncio.Queue: # <<< ADD THIS
        return self.enrichment_queue
    
    def get_ai_evaluation_queue(self) -> asyncio.PriorityQueue:
        """Returns the priority queue for AI evaluations."""
        return self.ai_evaluation_queue

    def get_db_write_lock(self):
        return self.db_write_lock

    ## 🚀 PnL Tracking
    async def get_current_sol_balance(self) -> float:
        """Get the current tracked SOL balance."""
        async with self.lock:
            #logger.info(f"💰 Current SOL Balance: {self.current_sol_balance:.6f} SOL")
            return self.current_sol_balance

    async def update_sol_balance(self, change: float):
        """Update the SOL balance by adding the change (can be negative)."""
        async with self.lock:
            self.current_sol_balance += change
            logger.info(f"💰 Updated SOL Balance: {self.current_sol_balance:.6f} SOL (Change: {change:+.6f} SOL)")
```

#### 📄 `telegram_interface.py`
*path: `telegram_interface.py`*

```python
# telegram_interface.py
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from typing import Union
import asyncio
from dotenv import load_dotenv
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta
import math
import sys
import re
import asyncpg

load_dotenv()

# --- Environment Variables ---
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_ID = os.getenv("TG_CHAT_ID")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?options=-c%20timezone%3Dutc"


# --- Constants ---
STATUS_FILE_CHECK_SECONDS = 10
ITEMS_PER_PAGE_CONFIG = 15
ITEMS_PER_PAGE_TRADES = 10
BULLX_URL_BASE = "https://neo.bullx.io/terminal?chainId=1399811149&address=" # Added BullX base URL

# --- Directory Setup ---
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = CURRENT_SCRIPT_DIR
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

os.makedirs(DATA_DIR_BOT, exist_ok=True)

# --- Conversation States ---
CHOOSING_PARAM, TYPING_VALUE = range(2)
EDIT_CONFIG_PARAM_KEY = "edit_config_param_name"
CONFIG_PAGE_KEY = "config_page_key"
ASK_MINT_FOR_SELL, ASK_MINT_FOR_UNSUB = range(2, 4)
COMMAND_TYPE_KEY = "command_type_key"
OPEN_TRADES_PAGE_KEY = "open_trades_page"

# --- Callback Data Constants ---
CB_MAIN_MENU = "main_menu"
CB_GET_SOL_AMOUNT = "get_sol_amount"
CB_GET_TOKEN_COUNT = "get_token_count"
CB_VIEW_OPEN_TRADES = "view_open_trades"
CB_MANAGE_DYNAMIC_CONFIG = "manage_dynamic_config"
CB_BOT_CONTROL_MENU = "bot_control_menu"
CB_REFRESH_STATUS = "refresh_status"
CB_START_BOT = "start_trading_bot"
CB_START_BOT_FORCE = "start_trading_bot_force"
CB_STOP_BOT = "stop_trading_bot"
CB_STOP_BUYING = "stop_buying_command"
CB_START_BUYING = "start_buying_command"
CB_UNSUB_NEWTOKEN = "unsub_newtoken_command"
CB_UNSUB_TOKEN_PROMPT = "unsub_token_prompt"
CB_VIEW_DYNAMIC_CONFIG = "view_dynamic_config"
CB_EDIT_DYNAMIC_CONFIG_START = "edit_dynamic_config_start"
CB_CANCEL_EDIT_CONFIG = "cancel_edit_config"
CB_CONFIG_PAGE_PREFIX = "config_page_"
CB_OPEN_TRADES_PAGE_PREFIX = "open_trades_page_"
CB_SELL_NOW_PREFIX = "sell_now_"
CB_SELL_CONFIRM_YES_PREFIX = "sell_confirm_yes_"
CB_SELL_CONFIRM_CANCEL_PREFIX = "sell_confirm_cancel_"
# --- NEW CALLBACKS ---
CB_SELL_ALL_NOW_PROMPT = "sell_all_now_prompt"
CB_SELL_ALL_CONFIRM_YES = "sell_all_confirm_yes"
CB_RESTART_WEBSOCKET = "restart_websocket"

def get_sol_price_from_status_file() -> float | None:
    try:
        if not os.path.exists(STATUS_FILE):
            print("Status file not found for SOL price.")
            return None
        with open(STATUS_FILE, 'r') as f:
            status_data = json.load(f)
        sol_price = status_data.get("current_sol_price_usd")
        if sol_price is not None:
            return float(sol_price)
        return None
    except (IOError, json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"Error reading SOL price from status.json: {e}")
        return None

async def send_telegram_message(message: str):
    if not TG_TOKEN or not TG_ID:
        print("Error: Telegram token or chat ID is not configured for send_telegram_message.")
        return
    try:
        bot = Bot(token=TG_TOKEN)
        await bot.send_message(chat_id=str(TG_ID), text=message)
    except Exception as e:
        print(f"Error in send_telegram_message: {e}")

# --- Markdown Escaping Helpers ---
def escape_markdown_v2_text(text: str) -> str:
    processed_text = text
    for char in r'\_*[]()~`>#+-=|{}.!':
        if char in processed_text:
            processed_text = processed_text.replace(char, f'\\{char}')
    return processed_text

def escape_markdown_v2_text_for_code_block(text: str) -> str:
    processed_text = text.replace('\\', '\\\\\\\\')
    processed_text = processed_text.replace('`', '\\`')
    return processed_text

def escape_url_for_markdownv2_link(url: str) -> str:
    """
    Escapes a URL specifically for the URL part of a MarkdownV2 link [text](url).
    """
    temp_url = url.replace('\\', '\\\\')
    temp_url = temp_url.replace(')', '\\)')
    return temp_url

# --- IPC Helper ---
def write_bot_command(command: str):
    try:
        with open(COMMAND_FILE, 'w', encoding='utf-8') as f:
            f.write(command)
        print(f"Sent command to bot: {command}")
        return True
    except IOError as e:
        print(f"Error writing command file: {e}")
        return False

# --- Helper Functions for Dynamic Config ---
def load_dynamic_config() -> dict:
    try:
        if os.path.exists(DYNAMIC_CONFIG_FILE):
            with open(DYNAMIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading {DYNAMIC_CONFIG_FILE}: {e}")
        return {}

def save_dynamic_config(config_data: dict) -> bool:
    try:
        with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, sort_keys=True)
        return True
    except IOError as e:
        print(f"Error saving {DYNAMIC_CONFIG_FILE}: {e}")
        return False

def get_type_hint(value) -> str:
    if isinstance(value, bool): return " (boolean: true/false)"
    if isinstance(value, int): return " (integer)"
    if isinstance(value, float): return " (float)"
    if isinstance(value, list):
        if value and all(isinstance(item, str) for item in value):
            return " (list of strings, comma-separated)"
        return " (list, JSON format e.g. [\"a\", \"b\"] or [1, 2])"
    return " (string)"

# --- Telegram Bot Status & Control Functions ---
async def get_bot_status_and_ws() -> tuple[str, dict | None]:
    """Reads full status file, returning bot status string and WebSocket summary dict."""
    try:
        if not os.path.exists(STATUS_FILE):
            return "UNKNOWN (No Status File)", None
        with open(STATUS_FILE, 'r') as f:
            status_data = json.load(f)

        bot_process_status = status_data.get("bot_process_status", "UNKNOWN").upper()
        ws_summary = status_data.get("websocket_summary")
        status_timestamp_str = status_data.get("timestamp")

        if not status_timestamp_str:
            return "STALE (No Timestamp)", ws_summary

        status_dt_naive = datetime.fromisoformat(status_timestamp_str)
        status_dt = status_dt_naive.replace(tzinfo=status_dt_naive.tzinfo or timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - status_dt).total_seconds()
        stale_threshold = STATUS_FILE_CHECK_SECONDS * 2.5

        if bot_process_status in ["RUNNING", "STARTING"] and age_seconds > stale_threshold:
            return f"STALE ({bot_process_status})", ws_summary
        elif bot_process_status == "STOPPING" and age_seconds > stale_threshold * 2:
            return "STOPPED (Stale Stopping)", ws_summary
        return bot_process_status, ws_summary
    except (IOError, json.JSONDecodeError, ValueError) as e:
        print(f"Error reading status.json: {e}")
        return "ERROR_READING_STATUS", None
    except Exception as e:
        print(f"Unexpected error in get_bot_status_and_ws: {e}")
        return "ERROR_UNEXPECTED_STATUS_READ", None

async def toggle_bot_process_command(update: Update, context: ContextTypes.DEFAULT_TYPE, force_start_flag: bool = False) -> None:
    query = update.callback_query
    if query: await query.answer()
    message_text = ""
    current_bot_status, _ = await get_bot_status_and_ws()

    if query and query.data == CB_STOP_BOT:
        if write_bot_command("STOP"):
            message_text = "🛑 STOP command sent to the trading bot. It may take a moment to fully stop."
        else:
            message_text = "⚠️ Error sending STOP command to the trading bot."
    elif query and (query.data == CB_START_BOT or query.data == CB_START_BOT_FORCE):
        try:
            if os.path.exists(COMMAND_FILE):
                with open(COMMAND_FILE, 'w') as f: f.write("")
            main_script_path = os.path.join(PROJECT_ROOT_DIR, 'main.py')
            python_executable = sys.executable
            if not os.path.exists(main_script_path):
                raise FileNotFoundError(f"Main controller script not found: {main_script_path}")
            subprocess.Popen([python_executable, main_script_path], cwd=PROJECT_ROOT_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            message_text = "🚀 Main controller (and trading bot) initiated. Check status shortly."
        except Exception as e:
            message_text = f"❌ Error starting main controller: {e}"
    else:
        message_text = f"Unhandled toggle action. Current status: {current_bot_status}"
    if query:
        await menu_command(update, context)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=escape_markdown_v2_text(message_text), parse_mode="MarkdownV2")
    elif update.message:
        await menu_command(update, context)
        await update.message.reply_text(text=escape_markdown_v2_text(message_text), parse_mode="MarkdownV2")

async def send_simple_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, friendly_name: str) -> None:
    query = update.callback_query
    if query: await query.answer()
    if write_bot_command(command):
        response_text = f"✅ Command '{friendly_name}' sent to the bot."
    else:
        response_text = f"⚠️ Error sending '{friendly_name}' command."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=escape_markdown_v2_text(response_text), parse_mode="MarkdownV2")
    await menu_command(update, context)

# --- Main Menu ---
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
        target_message_for_edit = query.message
    else:
        target_message_for_edit = update.message

    current_bot_status, ws_summary = await get_bot_status_and_ws()
    status_emoji = "🟢" if current_bot_status == "RUNNING" else \
                   "🟡" if current_bot_status == "STARTING" else \
                   "🟠" if "STALE" in current_bot_status else \
                   "🔴" if current_bot_status == "STOPPED" else \
                   "🟣" if current_bot_status == "STOPPING" else \
                   "⚠️"

    # --- WEBSOCKET STATUS DISPLAY ---
    ws_status_text = ""
    ws_restart_needed = False
    if ws_summary:
        ws_conn_status = ws_summary.get("connection_status", "N/A")
        ws_subs = ws_summary.get("trade_subscriptions_count", "N/A")
        last_msg_s = ws_summary.get("time_since_last_message_s", -1)
        
        ws_emoji = "✅"
        if ws_conn_status != "connected":
            ws_emoji = "🔌"
            ws_restart_needed = True
        elif last_msg_s > 60:
            ws_emoji = "⏳"
            ws_conn_status = f"Stale ({last_msg_s:.0f}s)"
            ws_restart_needed = True

        ws_status_text = escape_markdown_v2_text(f"\n\n{ws_emoji} WebSocket: {ws_conn_status} | Subs: {ws_subs}")
    # --- END WEBSOCKET DISPLAY ---

    menu_text = f"{status_emoji} Bot Status: *{escape_markdown_v2_text(current_bot_status)}*{ws_status_text}\n\nChoose an option:"
    
    keyboard = []
    if ws_restart_needed:
        keyboard.append([InlineKeyboardButton("🔄 Restart WebSocket", callback_data=CB_RESTART_WEBSOCKET)])

    keyboard.extend([
        [InlineKeyboardButton("💰 Bot Wallet Info", callback_data=CB_GET_SOL_AMOUNT)],
        [InlineKeyboardButton("📊 Subscribed Tokens Count", callback_data=CB_GET_TOKEN_COUNT)],
        [InlineKeyboardButton("📈 View Open Trades", callback_data=CB_VIEW_OPEN_TRADES)],
        [InlineKeyboardButton("⚙️ Dynamic Config", callback_data=CB_MANAGE_DYNAMIC_CONFIG)],
        [InlineKeyboardButton("🤖 Bot Control", callback_data=CB_BOT_CONTROL_MENU)],
        [InlineKeyboardButton("🔄 Refresh Status", callback_data=CB_REFRESH_STATUS)],
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        if query :
            if target_message_for_edit.text != menu_text or target_message_for_edit.reply_markup != reply_markup :
                await target_message_for_edit.edit_text(menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
        else:
            await target_message_for_edit.reply_text(menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Error updating menu: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

# --- Bot Control Submenu ---
async def bot_control_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    current_bot_status, _ = await get_bot_status_and_ws()
    start_stop_button_text = "▶️ Start Trading Bot"
    start_stop_callback = CB_START_BOT

    if current_bot_status == "RUNNING":
        start_stop_button_text = "⏹️ Stop Trading Bot"
        start_stop_callback = CB_STOP_BOT
    elif current_bot_status == "STARTING":
        start_stop_button_text = "⏳ Starting..."
        start_stop_callback = CB_REFRESH_STATUS
    elif "STALE" in current_bot_status or current_bot_status == "ERROR_READING_STATUS":
        start_stop_button_text = "▶️ Force Start Controller"
        start_stop_callback = CB_START_BOT_FORCE
    
    keyboard = [
        [InlineKeyboardButton(start_stop_button_text, callback_data=start_stop_callback)],
        [
            InlineKeyboardButton("🚫 Stop Buys", callback_data=CB_STOP_BUYING),
            InlineKeyboardButton("✅ Start Buys", callback_data=CB_START_BUYING)
        ],
        [InlineKeyboardButton("🚨 Sell All Immediately", callback_data=CB_SELL_ALL_NOW_PROMPT)],
        [
            InlineKeyboardButton("🔕 Unsub New Tokens", callback_data=CB_UNSUB_NEWTOKEN),
            InlineKeyboardButton("🔕 Unsub Token", callback_data=CB_UNSUB_TOKEN_PROMPT)
        ],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = escape_markdown_v2_text("🤖 Bot Control Panel:")
    await query.message.edit_text(text=message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

# --- Dynamic Config Management ---
async def manage_dynamic_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query: await query.answer()
    context.user_data[CONFIG_PAGE_KEY] = 0
    keyboard = [
        [InlineKeyboardButton("👁️ View Current Config", callback_data=CB_VIEW_DYNAMIC_CONFIG)],
        [InlineKeyboardButton("✏️ Edit Config Parameter", callback_data=CB_EDIT_DYNAMIC_CONFIG_START)],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = escape_markdown_v2_text("⚙️ Dynamic Configuration Management:")
    target_message = query.message if query else update.message
    if query: await target_message.edit_text(message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    elif target_message: await target_message.reply_text(message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

async def view_dynamic_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    config_data = load_dynamic_config()
    if not config_data:
        text_md = escape_markdown_v2_text("Could not load dynamic_config.json or it's empty.")
    else:
        sorted_config_data = dict(sorted(config_data.items()))
        raw_json_content = json.dumps(sorted_config_data, indent=2)
        text_md = escape_markdown_v2_text("Current dynamic_config.json:") + "\n\n"
        text_md += "```json\n" + raw_json_content + "\n```"
    keyboard = [[InlineKeyboardButton("🔙 Back to Config Menu", callback_data=CB_MANAGE_DYNAMIC_CONFIG)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.message.edit_text(text=text_md, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Markdown formatting error for view_dynamic_config: {e}. Sending as plain text.")
        plain_text = "Current dynamic_config.json:\n\n" + json.dumps(config_data, indent=2) if config_data else "Config empty."
        await query.message.edit_text(text=plain_text, reply_markup=reply_markup)

async def edit_dynamic_config_start_command(
    update_or_cb_query: Union[Update, CallbackQuery],
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 0
) -> int:
    actual_query_object: CallbackQuery | None = None
    if isinstance(update_or_cb_query, Update):
        actual_query_object = update_or_cb_query.callback_query
        if not actual_query_object:
            print("Error: edit_dynamic_config_start_command (as Update) did not find a callback_query.")
            if update_or_cb_query.effective_chat:
                await context.bot.send_message(
                    chat_id=update_or_cb_query.effective_chat.id,
                    text="Error processing request. Please try returning to the main menu."
                )
            return ConversationHandler.END
    elif isinstance(update_or_cb_query, CallbackQuery):
        actual_query_object = update_or_cb_query
    else:
        print(f"Error: edit_dynamic_config_start_command received unexpected type: {type(update_or_cb_query)}")
        return ConversationHandler.END
    await actual_query_object.answer()
    target_message_to_edit = actual_query_object.message
    context.user_data[CONFIG_PAGE_KEY] = page
    config_data = load_dynamic_config()
    sorted_config_items = sorted(config_data.items())
    if not sorted_config_items:
        await target_message_to_edit.edit_text(
            escape_markdown_v2_text("Dynamic config is empty or could not be loaded. Cannot edit."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Config Menu", callback_data=CB_MANAGE_DYNAMIC_CONFIG)]]),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    start_index = page * ITEMS_PER_PAGE_CONFIG
    end_index = start_index + ITEMS_PER_PAGE_CONFIG
    current_page_items = sorted_config_items[start_index:end_index]
    params_list_md_parts = [escape_markdown_v2_text(f"Available parameters (Page {page + 1}/{ (len(sorted_config_items) -1) // ITEMS_PER_PAGE_CONFIG + 1 }):")]
    for key, value in current_page_items:
        raw_key = key
        raw_value_json_str = json.dumps(value, ensure_ascii=False)
        raw_type_hint = get_type_hint(value)
        line_part_1_bullet = escape_markdown_v2_text("- ")
        line_part_2_key_code = f"`{escape_markdown_v2_text_for_code_block(raw_key)}`"
        line_part_3_current_literal = escape_markdown_v2_text(" (current: ")
        line_part_4_value_code = f"`{escape_markdown_v2_text_for_code_block(raw_value_json_str)}`"
        line_part_5_closing_paren_literal = escape_markdown_v2_text(")")
        line_part_6_type_hint_escaped = escape_markdown_v2_text(raw_type_hint)
        full_line = (line_part_1_bullet + line_part_2_key_code + line_part_3_current_literal +
                     line_part_4_value_code + line_part_5_closing_paren_literal + line_part_6_type_hint_escaped)
        params_list_md_parts.append(full_line)
    params_text_md = "\n".join(params_list_md_parts)
    params_text_md += "\n\n" + escape_markdown_v2_text("Which parameter do you want to edit? (Type the exact name)")
    pagination_buttons = []
    if page > 0: pagination_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"{CB_CONFIG_PAGE_PREFIX}{page-1}"))
    if end_index < len(sorted_config_items): pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{CB_CONFIG_PAGE_PREFIX}{page+1}"))
    keyboard_layout = []
    if pagination_buttons: keyboard_layout.append(pagination_buttons)
    keyboard_layout.append([InlineKeyboardButton("🔙 Cancel Edit", callback_data=CB_CANCEL_EDIT_CONFIG)])
    reply_markup = InlineKeyboardMarkup(keyboard_layout)
    try:
        if target_message_to_edit.text != params_text_md or target_message_to_edit.reply_markup != reply_markup :
            await target_message_to_edit.edit_text(text=params_text_md, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Error displaying params for edit (MarkdownV2, Page {page}): {e}.")
        plain_text_parts = [f"Parameters (Page {page + 1}/{ (len(sorted_config_items) -1) // ITEMS_PER_PAGE_CONFIG + 1 }):"]
        for key, value in current_page_items: plain_text_parts.append(f"- {key} (current: {json.dumps(value, ensure_ascii=False)}) {get_type_hint(value)}")
        plain_text_parts.append("\nWhich parameter to edit? (Type exact name)")
        if target_message_to_edit.text != "\n".join(plain_text_parts) or target_message_to_edit.reply_markup != reply_markup:
            await target_message_to_edit.edit_text(text="\n".join(plain_text_parts), reply_markup=reply_markup)
    return CHOOSING_PARAM

async def choose_param_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    param_name_unescaped = update.message.text.strip()
    config_data = load_dynamic_config()
    if param_name_unescaped not in config_data:
        await update.message.reply_text(
            escape_markdown_v2_text(f"Parameter '{param_name_unescaped}' not found. Please try again or /cancel_edit_config."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel Edit", callback_data=CB_CANCEL_EDIT_CONFIG)]]),
            parse_mode="MarkdownV2"
        )
        return CHOOSING_PARAM
    context.user_data[EDIT_CONFIG_PARAM_KEY] = param_name_unescaped
    current_value = config_data[param_name_unescaped]
    param_name_display_escaped = escape_markdown_v2_text(param_name_unescaped)
    current_value_for_code_block = escape_markdown_v2_text_for_code_block(json.dumps(current_value, ensure_ascii=False))
    type_hint_display_escaped = escape_markdown_v2_text(get_type_hint(current_value))
    text_to_send = f"Editing `{param_name_display_escaped}`\\. Current value: `{current_value_for_code_block}`{type_hint_display_escaped}\\.\n" \
                   f"Enter the new value for `{param_name_display_escaped}`:"
    await update.message.reply_text(text_to_send, parse_mode="MarkdownV2")
    return TYPING_VALUE

async def typing_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    param_name = context.user_data.get(EDIT_CONFIG_PARAM_KEY)
    new_value_str = update.message.text.strip()
    config_data = load_dynamic_config()
    if not param_name or param_name not in config_data:
        await update.message.reply_text(
            escape_markdown_v2_text("Error: Parameter context lost. Please start over."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config Menu", callback_data=CB_MANAGE_DYNAMIC_CONFIG)]]),
            parse_mode="MarkdownV2"
        )
        if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
        return ConversationHandler.END
    original_value = config_data[param_name]
    parsed_value = None; parse_error = None
    try:
        if isinstance(original_value, bool):
            if new_value_str.lower() in ['true', '1', 'yes', 'on']: parsed_value = True
            elif new_value_str.lower() in ['false', '0', 'no', 'off']: parsed_value = False
            else: raise ValueError("Boolean must be true/false/1/0/yes/no/on/off")
        elif isinstance(original_value, int): parsed_value = int(new_value_str)
        elif isinstance(original_value, float): parsed_value = float(new_value_str)
        elif isinstance(original_value, list):
            try:
                parsed_value = json.loads(new_value_str)
                if not isinstance(parsed_value, list): raise ValueError("Input was not a valid JSON list.")
            except json.JSONDecodeError:
                if original_value and all(isinstance(item, str) for item in original_value):
                    parsed_value = [s.strip() for s in new_value_str.split(',')]
                elif not original_value:
                    parsed_value = [s.strip() for s in new_value_str.split(',')] if new_value_str else []
                else: raise ValueError("List format is complex. Provide valid JSON list (e.g., [\"item1\"] or [1, 2]).")
        else: parsed_value = new_value_str
    except ValueError as e: parse_error = str(e)
    if parse_error:
        param_name_display_escaped = escape_markdown_v2_text(param_name)
        type_hint_display_escaped = escape_markdown_v2_text(get_type_hint(original_value))
        error_message_escaped = escape_markdown_v2_text(parse_error)
        text_to_send = f"Error converting value '{escape_markdown_v2_text(new_value_str)}' for `{param_name_display_escaped}`\\. Expected type like{type_hint_display_escaped}\\. Error: {error_message_escaped}\n" \
                       f"Please enter the value again or /cancel_edit_config\\."
        await update.message.reply_text(text_to_send, parse_mode="MarkdownV2")
        return TYPING_VALUE
    config_data[param_name] = parsed_value
    param_name_display_escaped = escape_markdown_v2_text(param_name)
    parsed_value_for_code_block = escape_markdown_v2_text_for_code_block(json.dumps(parsed_value, ensure_ascii=False))
    if save_dynamic_config(config_data):
        confirmation_text = f"✅ Successfully updated `{param_name_display_escaped}` to `{parsed_value_for_code_block}`\\.\n" \
                            "The trading bot should pick up this change shortly\\."
        await update.message.reply_text(confirmation_text, parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(escape_markdown_v2_text(f"❌ Failed to save changes to {DYNAMIC_CONFIG_FILE}."), parse_mode="MarkdownV2")
    if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
    await manage_dynamic_config_command(update, context)
    return ConversationHandler.END

async def cancel_edit_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query: await query.answer("Edit cancelled.")
    if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
    if query: await manage_dynamic_config_command(update, context)
    elif update.message:
        await update.message.reply_text("Edit cancelled.")
        await manage_dynamic_config_command(update, context)
    return ConversationHandler.END

async def fallback_edit_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        escape_markdown_v2_text("Sorry, I didn't understand that. If you're editing, please provide the value or use /cancel_edit_config to stop."),
        parse_mode="MarkdownV2"
    )
    return

# --- Bot Command Handling (with arguments) ---
async def prompt_mint_address(update: Update, context: ContextTypes.DEFAULT_TYPE, command_type: str) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[COMMAND_TYPE_KEY] = command_type
    action_text = "sell" if command_type == "SELL" else "unsubscribe from"
    await query.message.edit_text(
        text=escape_markdown_v2_text(f"Please enter the MINT address of the token you want to {action_text}:"),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data=CB_BOT_CONTROL_MENU)]])
    )
    return ASK_MINT_FOR_SELL if command_type == "SELL" else ASK_MINT_FOR_UNSUB

async def process_mint_address_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mint_address = update.message.text.strip()
    command_type = context.user_data.get(COMMAND_TYPE_KEY)
    if not mint_address:
        await update.message.reply_text("No mint address provided. Please try again or cancel.")
        return ASK_MINT_FOR_SELL if command_type == "SELL" else ASK_MINT_FOR_UNSUB
    final_command = ""; friendly_action = ""
    if command_type == "SELL":
        final_command = f"SELL_{mint_address}"
        friendly_action = f"Sell {mint_address}"
    elif command_type == "UNSUB_TRADES":
        final_command = f"UNSUB_TOKEN_TRADES_{mint_address}"
        friendly_action = f"Unsubscribe from {mint_address} trades"
    if final_command:
        if write_bot_command(final_command):
            await update.message.reply_text(escape_markdown_v2_text(f"✅ Command '{friendly_action}' sent to the bot."), parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(escape_markdown_v2_text(f"⚠️ Error sending '{friendly_action}' command."), parse_mode="MarkdownV2")
    else: await update.message.reply_text("Internal error: Unknown command type.")
    del context.user_data[COMMAND_TYPE_KEY]
    await bot_control_menu_command(update, context)
    return ConversationHandler.END

async def cancel_mint_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Operation cancelled.")
    if COMMAND_TYPE_KEY in context.user_data: del context.user_data[COMMAND_TYPE_KEY]
    await bot_control_menu_command(update, context)
    return ConversationHandler.END

# --- View Open Trades ---
async def get_token_name(conn: asyncpg.Connection, mint: str) -> str:
    """Fetches the token name from v_tokens, falling back to mint address."""
    try:
        row = await conn.fetchrow("SELECT name FROM v_tokens WHERE mint = $1 LIMIT 1", mint)
        if row and row['name'] and row['name'].strip():
            return row['name'].strip()
        return mint # Fallback to mint address
    except Exception as e:
        print(f"Error fetching token name for {mint}: {e}")
        return mint # Fallback

def format_open_trade_display(trade_data: dict, sol_usd_price: float | None) -> str:
    """Formats a single open trade for display with BullX link and token name."""
    mint = trade_data['mint']
    token_name = trade_data.get('token_name', mint)
    buy_price_sol = float(trade_data['buy_price'])
    initial_tokens = float(trade_data['initial_tokens'])
    remaining_tokens = float(trade_data['remaining_tokens'])
    total_investment_sol = float(trade_data['total_investment_sol'])
    buy_timestamp = trade_data['timestamp']

    current_price_sol = float(trade_data.get('current_price_sol', 0.0))
    current_market_cap_sol = float(trade_data.get('current_market_cap_sol', 0.0))

    # Calculate Age
    age_delta = datetime.now(timezone.utc) - buy_timestamp
    days, remainder = divmod(age_delta.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    age_str_raw = ""
    if days > 0: age_str_raw += f"{int(days)}d "
    if hours > 0 or days > 0: age_str_raw += f"{int(hours)}h "
    age_str_raw += f"{int(minutes)}m"
    age_str_raw = age_str_raw.strip() if age_str_raw else "0m"

    # Calculate PnL
    unrealized_pnl_sol = 0.0
    current_value_sol = current_price_sol * remaining_tokens
    cost_basis_remaining_sol = 0.0
    if initial_tokens > 1e-9:
        cost_basis_remaining_sol = (total_investment_sol / initial_tokens) * remaining_tokens

    if not math.isclose(remaining_tokens, 0.0, abs_tol=1e-9):
        unrealized_pnl_sol = current_value_sol - cost_basis_remaining_sol

    pnl_emoji = "📈" if unrealized_pnl_sol >= 0 else "📉"
    profit_percentage_raw = ((unrealized_pnl_sol / cost_basis_remaining_sol) * 100) if cost_basis_remaining_sol > 1e-9 else 0.0

    # --- Prepare components for Markdown ---
    mint_for_code = escape_markdown_v2_text_for_code_block(mint)
    buy_price_for_code = escape_markdown_v2_text_for_code_block(f"{buy_price_sol:.8f}")
    current_price_for_code = escape_markdown_v2_text_for_code_block(f"{current_price_sol:.8f}")
    remaining_tokens_for_code = escape_markdown_v2_text_for_code_block(f"{remaining_tokens:.3f}")
    initial_tokens_for_code = escape_markdown_v2_text_for_code_block(f"{initial_tokens:.3f}")
    pnl_sol_for_code = escape_markdown_v2_text_for_code_block(f"{unrealized_pnl_sol:+.4f}")
    profit_percentage_for_code = escape_markdown_v2_text_for_code_block(f"{profit_percentage_raw:+.2f}%")
    current_mc_sol_for_code = escape_markdown_v2_text_for_code_block(f"{current_market_cap_sol:,.0f}")
    age_md = escape_markdown_v2_text(age_str_raw)

    token_name_str = str(token_name) if token_name is not None else ""
    mint_str = str(mint) if mint is not None else ""
    display_name_md_parts = []
    if token_name_str and token_name_str.lower() != mint_str.lower():
        display_name_md_parts.append(escape_markdown_v2_text(token_name_str))
        display_name_md_parts.append(escape_markdown_v2_text(" ("))
        display_name_md_parts.append(f"`{mint_for_code}`")
        display_name_md_parts.append(escape_markdown_v2_text(")"))
    else:
        display_name_md_parts.append(f"`{mint_for_code}`")
    display_name_final_md = "".join(display_name_md_parts)

    bullx_url_raw = f"{BULLX_URL_BASE}{mint_str}"
    escaped_bullx_url_for_link_part = escape_url_for_markdownv2_link(bullx_url_raw)
    link_text_md = escape_markdown_v2_text("BullX")
    link_final_md = f"[{link_text_md}]({escaped_bullx_url_for_link_part})"

    pnl_usd_str_md = ""
    current_mc_usd_str_md = ""
    if sol_usd_price and sol_usd_price > 0:
        unrealized_pnl_usd = unrealized_pnl_sol * sol_usd_price
        current_market_cap_usd = current_market_cap_sol * sol_usd_price
        pnl_usd_str_md = escape_markdown_v2_text(f" (${unrealized_pnl_usd:+.2f} USD)")
        current_mc_usd_str_md = escape_markdown_v2_text(f" (${current_market_cap_usd:,.0f} USD)")

    line1 = escape_markdown_v2_text("🔵 ") + display_name_final_md + escape_markdown_v2_text(" ") + link_final_md + escape_markdown_v2_text("\n")
    line2 = escape_markdown_v2_text('  Age: ') + age_md + escape_markdown_v2_text("\n")
    line3 = escape_markdown_v2_text('  Bought at: ') + f"`{buy_price_for_code}`" + escape_markdown_v2_text(' SOL\n')
    line4 = escape_markdown_v2_text('  Current Price: ') + f"`{current_price_for_code}`" + escape_markdown_v2_text(' SOL\n')
    line5 = escape_markdown_v2_text('  Tokens (Rem/Initial): ') + f"`{remaining_tokens_for_code}`" + escape_markdown_v2_text('/') + f"`{initial_tokens_for_code}`" + escape_markdown_v2_text("\n")
    line6 = escape_markdown_v2_text(f'  Unrealized PnL {pnl_emoji}: ') + f"`{pnl_sol_for_code}`" + escape_markdown_v2_text(' SOL ') + f"`{profit_percentage_for_code}`" + pnl_usd_str_md + escape_markdown_v2_text("\n")
    line7 = escape_markdown_v2_text('  Current MC: ') + f"`{current_mc_sol_for_code}`" + escape_markdown_v2_text(' SOL') + current_mc_usd_str_md

    return line1 + line2 + line3 + line4 + line5 + line6 + line7

async def view_open_trades_command(actual_callback_query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    context.user_data[OPEN_TRADES_PAGE_KEY] = page
    sol_usd_price = get_sol_price_from_status_file()

    if not sol_usd_price:
        await actual_callback_query.message.edit_text(
            text=escape_markdown_v2_text("⚠️ Could not retrieve current SOL/USD price. Please try again later."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)]]),
            parse_mode="MarkdownV2"
        )
        return

    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        offset = page * ITEMS_PER_PAGE_TRADES

        optimized_query = """
        WITH ActiveTrades AS (
            SELECT
                id, mint, price AS buy_price, initial_tokens, remaining_tokens,
                total_investment_sol, timestamp,
                ROW_NUMBER() OVER (ORDER BY timestamp DESC) as rn
            FROM portfolio
            WHERE status = 'active' AND tx_type = 'buy'
        ),
        PagedTrades AS (
            SELECT * FROM ActiveTrades WHERE rn > $2 AND rn <= ($2 + $1)
        ),
        LatestMarketData AS (
            SELECT
                mint,
                (array_agg(price_sol ORDER BY timestamp DESC))[1] AS current_price_sol, -- USE UNIFIED COLUMN
                (array_agg(market_cap_sol ORDER BY timestamp DESC))[1] AS current_market_cap_sol -- USE UNIFIED COLUMN
            FROM v_unified_market_ticks_live -- <<< CORRECTED: USE LIVE UNIFIED VIEW
            WHERE mint = ANY(SELECT mint FROM PagedTrades)
            GROUP BY mint
        )
        SELECT
            pt.id, pt.mint, pt.buy_price, pt.initial_tokens, pt.remaining_tokens,
            pt.total_investment_sol, pt.timestamp,
            COALESCE(vt.name, pt.mint) AS token_name,
            lmd.current_price_sol,
            lmd.current_market_cap_sol,
            (SELECT COUNT(*) FROM ActiveTrades) AS total_trades
        FROM PagedTrades pt
        LEFT JOIN tokens vt ON pt.mint = vt.mint
        LEFT JOIN LatestMarketData lmd ON pt.mint = lmd.mint
        ORDER BY pt.timestamp DESC;
        """

        open_trades_rows = await conn.fetch(optimized_query, ITEMS_PER_PAGE_TRADES, offset)
        total_trades = open_trades_rows[0]['total_trades'] if open_trades_rows else 0

        page_count = (total_trades - 1) // ITEMS_PER_PAGE_TRADES + 1 if total_trades > 0 else 1
        message_text_parts = [escape_markdown_v2_text(f"📈 Open Trades (Page {page + 1}/{page_count}):")]

        if not open_trades_rows:
            message_text_parts.append(escape_markdown_v2_text("\nNo open trades found on this page."))
        else:
            for trade_row in open_trades_rows:
                full_trade_data = dict(trade_row)
                message_text_parts.append("\n" + format_open_trade_display(full_trade_data, sol_usd_price))
                message_text_parts.append(escape_markdown_v2_text("➖" * 20))

        if message_text_parts and message_text_parts[-1] == escape_markdown_v2_text("➖" * 20):
            message_text_parts.pop()

    except Exception as e:
        print(f"Error processing open trades view: {e}")
        message_text_parts = [escape_markdown_v2_text("An error occurred while fetching open trades.")]
        total_trades = 0
        open_trades_rows = []
    finally:
        if conn:
            await conn.close()

    message_text = "\n".join(message_text_parts)

    keyboard_layout = []
    if open_trades_rows:
        current_sell_button_row = []
        for trade_info in open_trades_rows:
            btn_text_raw = trade_info['token_name']
            if len(btn_text_raw) > 12 or btn_text_raw == trade_info['mint']:
                btn_text_raw = trade_info['mint'][:6] + "..."

            sell_button = InlineKeyboardButton(f"🚨 Sell {btn_text_raw}", callback_data=f"{CB_SELL_NOW_PREFIX}{trade_info['mint']}")

            if len(current_sell_button_row) < 2:
                current_sell_button_row.append(sell_button)
            else:
                keyboard_layout.append(current_sell_button_row)
                current_sell_button_row = [sell_button]
        if current_sell_button_row:
            keyboard_layout.append(current_sell_button_row)

    pagination_buttons_row = []
    if page > 0:
        pagination_buttons_row.append(InlineKeyboardButton("⬅️ Prev Page", callback_data=f"{CB_OPEN_TRADES_PAGE_PREFIX}{page-1}"))
    if (page + 1) * ITEMS_PER_PAGE_TRADES < total_trades:
        pagination_buttons_row.append(InlineKeyboardButton("Next Page ➡️", callback_data=f"{CB_OPEN_TRADES_PAGE_PREFIX}{page+1}"))

    if pagination_buttons_row:
        keyboard_layout.append(pagination_buttons_row)

    keyboard_layout.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)])
    reply_markup = InlineKeyboardMarkup(keyboard_layout)

    target_message = actual_callback_query.message
    try:
        if target_message.text != message_text or target_message.reply_markup != reply_markup:
            await target_message.edit_text(text=message_text, reply_markup=reply_markup, parse_mode="MarkdownV2", disable_web_page_preview=True)
    except Exception as e_edit:
        print(f"Error editing open trades message: {e_edit}")
        await context.bot.send_message(chat_id=actual_callback_query.message.chat_id, text=message_text, reply_markup=reply_markup, parse_mode="MarkdownV2", disable_web_page_preview=True)


# --- General Button Callback Handler ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query: CallbackQuery = update.callback_query
    command = query.data

    if command == CB_VIEW_OPEN_TRADES:
        await query.answer()
        asyncio.create_task(view_open_trades_command(query, context, page=0))
        return

    if command.startswith(CB_OPEN_TRADES_PAGE_PREFIX):
        await query.answer()
        page = int(command.split('_')[-1])
        asyncio.create_task(view_open_trades_command(query, context, page=page))
        return

    if command.startswith(CB_SELL_NOW_PREFIX):
        await query.answer()
        mint_to_sell = command[len(CB_SELL_NOW_PREFIX):]
        
        token_name = mint_to_sell
        conn = None
        try:
            conn = await asyncpg.connect(dsn=DB_URL)
            token_name = await get_token_name(conn, mint_to_sell)
        except Exception as e:
            print(f"DB Error fetching token name for confirmation: {e}")
        finally:
            if conn: await conn.close()

        current_page = context.user_data.get(OPEN_TRADES_PAGE_KEY, 0)
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Sell Now", callback_data=f"{CB_SELL_CONFIRM_YES_PREFIX}{mint_to_sell}"),
                InlineKeyboardButton("❌ No, Cancel", callback_data=f"{CB_OPEN_TRADES_PAGE_PREFIX}{current_page}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        prompt_text = f"Are you sure you want to sell all holdings for token *{escape_markdown_v2_text(token_name)}*?"
        await query.message.edit_text(text=prompt_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
        return

    if command.startswith(CB_SELL_CONFIRM_YES_PREFIX):
        await query.answer("Sending sell command...")
        mint_to_sell = command[len(CB_SELL_CONFIRM_YES_PREFIX):]
        sell_command_str = f"SELL_{mint_to_sell}"
        
        confirmation_text = ""
        if write_bot_command(sell_command_str):
            confirmation_text = f"✅ Sell command for token `{escape_markdown_v2_text_for_code_block(mint_to_sell)}` has been sent to the bot."
        else:
            confirmation_text = f"⚠️ Error sending sell command for token `{escape_markdown_v2_text_for_code_block(mint_to_sell)}`."
        
        await query.message.edit_text(text=escape_markdown_v2_text(confirmation_text), parse_mode="MarkdownV2")
        
        await asyncio.sleep(2)
        current_page = context.user_data.get(OPEN_TRADES_PAGE_KEY, 0)
        await view_open_trades_command(query, context, page=current_page)
        return

    if command == CB_GET_SOL_AMOUNT:
        await query.answer()
        try:
            if not os.path.exists(STATUS_FILE): text = "Status file not found."
            else:
                with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
                text = (f"💰 SOL: {bot_status.get('current_sol_balance', 'N/A')}\n"
                        f"💲 Price: ${bot_status.get('current_sol_price_usd', 'N/A')}\n"
                        f"💼 Value: ${bot_status.get('current_portfolio_value_usd', 'N/A')}\n"
                        f"🕒 Updated: {bot_status.get('timestamp', 'N/A')}")
        except Exception as e: text = f"Error: {e}"
        try:
            original_title = (query.message.text or "").splitlines()
            original_title = original_title[0] if original_title else "Bot Wallet Info"
            await query.edit_message_text(text=f"{escape_markdown_v2_text(original_title)}\n\n{escape_markdown_v2_text(text)}", reply_markup=query.message.reply_markup, parse_mode="MarkdownV2")
        except Exception as e_edit:
            print(f"Error editing for SOL amount: {e_edit}")
            await query.message.reply_text(escape_markdown_v2_text(text), parse_mode="MarkdownV2")

    elif command == CB_GET_TOKEN_COUNT:
        await query.answer()
        try:
            if not os.path.exists(STATUS_FILE): text = "Status file not found."
            else:
                with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
                text = (f"📊 Subscribed Tokens: {bot_status.get('active_token_subscriptions_count', 'N/A')}\n"
                        f"🕒 Updated: {bot_status.get('timestamp', 'N/A')}")
        except Exception as e: text = f"Error: {e}"
        try:
            original_title = (query.message.text or "").splitlines()
            original_title = original_title[0] if original_title else "Token Count"
            await query.edit_message_text(text=f"{escape_markdown_v2_text(original_title)}\n\n{escape_markdown_v2_text(text)}", reply_markup=query.message.reply_markup, parse_mode="MarkdownV2")
        except Exception as e_edit:
            print(f"Error editing for token count: {e_edit}")
            await query.message.reply_text(escape_markdown_v2_text(text), parse_mode="MarkdownV2")

    elif command == CB_START_BOT or command == CB_STOP_BOT or command == CB_START_BOT_FORCE:
        await toggle_bot_process_command(update, context)

    elif command == CB_REFRESH_STATUS or command == CB_MAIN_MENU:
        await menu_command(update, context)

    elif command == CB_MANAGE_DYNAMIC_CONFIG:
        await manage_dynamic_config_command(update, context)

    elif command == CB_VIEW_DYNAMIC_CONFIG:
        await view_dynamic_config_command(update, context)

    elif command == CB_BOT_CONTROL_MENU:
        await bot_control_menu_command(update, context)

    elif command == CB_STOP_BUYING:
        await send_simple_bot_command(update, context, "STOP_BUYING", "Stop Buys")

    elif command == CB_START_BUYING:
        await send_simple_bot_command(update, context, "START_BUYING", "Start Buys")

    elif command == CB_UNSUB_NEWTOKEN:
        await send_simple_bot_command(update, context, "UNSUB_NEWTOKEN", "Unsubscribe New Tokens")

    elif command == CB_RESTART_WEBSOCKET:
        await query.answer("Sending WebSocket restart command...")
        await send_simple_bot_command(update, context, "RESTART_WEBSOCKET", "Restart WebSocket")

    elif command == CB_SELL_ALL_NOW_PROMPT:
        await query.answer()
        keyboard = [[
            InlineKeyboardButton("✅ YES, SELL ALL", callback_data=CB_SELL_ALL_CONFIRM_YES),
            InlineKeyboardButton("❌ No, Cancel", callback_data=CB_BOT_CONTROL_MENU)
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            text=escape_markdown_v2_text("⚠️ Are you sure you want to sell ALL open positions immediately? This cannot be undone."),
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
        return

    elif command == CB_SELL_ALL_CONFIRM_YES:
        await query.answer("Sending SELL ALL command...")
        await send_simple_bot_command(update, context, "SELL_ALL_IMMEDIATELY", "Sell All Immediately")

    elif command.startswith(CB_CONFIG_PAGE_PREFIX):
        page = int(command.split('_')[-1])
        await edit_dynamic_config_start_command(query, context, page=page)

    else:
        # Default fallback for any unhandled command
        await query.answer("Unknown or unhandled command.")
        print(f"Unhandled callback query command: {command}")


# --- Main Function ---
def main_telegram_bot() -> None:
    print("Starting Telegram bot interface...")
    if not TG_TOKEN or not TG_ID:
        print("Error: Telegram environment variables (TG_BOT_TOKEN, TG_CHAT_ID) not set.")
        return
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_DATABASE]):
        print("Error: Database environment variables not fully set for Telegram interface.")
        return

    # --- FINAL CORRECTED NETWORK CONFIGURATION ---
    # The timeout arguments are passed directly to the builder, not to a Defaults object.
    application = (
        Application.builder()
        .token(TG_TOKEN)
        .connect_timeout(10)
        .read_timeout(30)
        .pool_timeout(60)
        .build()
    )
    # --- END CORRECTION ---

    edit_config_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_dynamic_config_start_command, pattern=f"^{CB_EDIT_DYNAMIC_CONFIG_START}$")],
        states={
            CHOOSING_PARAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_param_handler)],
            TYPING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, typing_value_handler)],
        },
        fallbacks=[
            CommandHandler('cancel_edit_config', cancel_edit_config_command),
            CallbackQueryHandler(cancel_edit_config_command, pattern=f"^{CB_CANCEL_EDIT_CONFIG}$"),
            MessageHandler(filters.COMMAND, fallback_edit_config)
        ],
        per_message=False
    )
    mint_command_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lambda u, c: prompt_mint_address(u, c, "UNSUB_TRADES"), pattern=f"^{CB_UNSUB_TOKEN_PROMPT}$"),
        ],
        states={
            ASK_MINT_FOR_SELL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_mint_address_command)],
            ASK_MINT_FOR_UNSUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_mint_address_command)],
        },
        fallbacks=[
            CommandHandler('cancel_mint_command', cancel_mint_command),
            CallbackQueryHandler(cancel_mint_command, pattern=f"^{CB_BOT_CONTROL_MENU}$"),
            MessageHandler(filters.COMMAND, fallback_edit_config)
        ],
        per_message=False
    )
    application.add_handler(CommandHandler("start", menu_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(edit_config_conv_handler)
    application.add_handler(mint_command_conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    print("Telegram bot polling...")
    try:
        application.run_polling()
    except Exception as e:
        print(f"Telegram bot failed to start or polling error: {e}")

if __name__ == '__main__':
    main_telegram_bot()
```

#### 📄 `trade_processor.py`
*path: `trade_processor.py`*

```python
"""
Processes trade messages from the PumpPortal queue and writes them in batches to the database.
"""

import asyncio
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from bot_logger import logger
from state_manager import GlobalState
from utils import calculate_market_cap
from config.config import _TOTAL_SUPPLY

async def trade_worker(trade_queue: asyncio.Queue):
    """
    Processes trade messages from the provided queue and writes them in batches to the database.
    """
    state = GlobalState.get_instance()
    db_client = state.db_client

    if not db_client:
        logger.error(":police_car_light: Trade worker cannot start: DatabaseClient not initialized in GlobalState.")
        return

    BATCH_SIZE = 100
    BATCH_TIMEOUT = 5

    logger.info(":rocket: Trade worker started.")

    while not state.shutdown_event.is_set():
        batch_from_queue = []
        trade_params_to_db = []
        mints_in_batch = []

        try:
            # Collect trades for a batch until BATCH_SIZE is reached or BATCH_TIMEOUT expires
            start_time = asyncio.get_event_loop().time()
            while len(batch_from_queue) < BATCH_SIZE:
                remaining_time = BATCH_TIMEOUT - (asyncio.get_event_loop().time() - start_time)
                if remaining_time <= 0:
                    break
                try:
                    trade_data = await asyncio.wait_for(trade_queue.get(), timeout=remaining_time)
                    batch_from_queue.append(trade_data)
                except asyncio.TimeoutError:
                    break

            if not batch_from_queue:
                await asyncio.sleep(0.1) # Prevent busy-waiting if queue is empty
                continue

            active_subscriptions = await state.get_token_subscriptions()
            sol_price = await state.get_sol_price()
            sol_price_decimal = Decimal(sol_price) if sol_price is not None else Decimal('0')


            for data in batch_from_queue:
                mint = data.get('mint')
                # Process only if the token is actively subscribed
                if not mint or mint not in active_subscriptions:
                    trade_queue.task_done()
                    continue

                try:
                    # Safely convert API data to Decimal
                    token_amount_raw = data.get('tokenAmount')
                    sol_amount_raw = data.get('solAmount')
                    
                    token_amount = Decimal(str(token_amount_raw)) if token_amount_raw else Decimal('0')
                    sol_amount = Decimal(str(sol_amount_raw)) if sol_amount_raw else Decimal('0')

                    # Skip trades with invalid amounts
                    if token_amount <= 0 or sol_amount <= 0:
                        trade_queue.task_done()
                        continue

                    price = sol_amount / token_amount
                    market_cap_sol = Decimal(str(data.get('marketCapSol'))) if data.get('marketCapSol') else Decimal('0')
                    v_tokens_in_bc = Decimal(str(data.get('vTokensInBondingCurve'))) if data.get('vTokensInBondingCurve') else Decimal('0')
                    v_sol_in_bc = Decimal(str(data.get('vSolInBondingCurve'))) if data.get('vSolInBondingCurve') else Decimal('0')

                    market_cap_calculated = market_cap_sol * sol_price_decimal

                    trade_params_to_db.append((
                        data.get('signature'), mint, data.get('traderPublicKey'), data.get('txType'),
                        token_amount, sol_amount, price,
                        data.get('bondingCurveKey', ""),
                        v_tokens_in_bc, v_sol_in_bc,
                        market_cap_sol, sol_price_decimal, market_cap_calculated,
                        datetime.now(timezone.utc) # Use current time as fallback for timestamp
                    ))
                    mints_in_batch.append(mint)
                except (InvalidOperation, TypeError) as e:
                    logger.error(f":police_car_light: Invalid data for trade (Sig: {data.get('signature')}). Skipping. Error: {e}")
                    trade_queue.task_done()
                except Exception as e:
                    logger.error(f":police_car_light: Unexpected error processing trade item (Sig: {data.get('signature')}). Error: {e}", exc_info=True)
                    trade_queue.task_done()

            if trade_params_to_db:
                try:
                    await db_client.insert_trades_batch(trade_params_to_db, mints_in_batch)
                    
                    # Mark all items in the processed batch as done
                    for _ in batch_from_queue:
                        try:
                            trade_queue.task_done()
                        except ValueError:
                            pass # Can happen if queue is manipulated elsewhere, safe to ignore
                    
                    logger.debug(f":bank: Successfully processed and saved a batch of {len(trade_params_to_db)} trades.")

                except Exception as e:
                    logger.error(f":police_car_light: Trade worker failed during batch insert. Error: {e}", exc_info=True)
                    # Note: In case of DB failure, items remain in queue and will be re-processed, which is the desired behavior.
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info(":stop_sign: Trade worker task cancelled.")
            break
        except Exception as e:
            logger.error(f"🚨 Unexpected error in trade worker main loop: {e}", exc_info=True)
            await asyncio.sleep(5)

    logger.info(":stop_sign: Trade worker shutting down.")
```

#### 📄 `trading_bot.py`
*path: `trading_bot.py`*

```python
# path: trading_bot.py

import argparse
import asyncio
import signal
import traceback
import inspect
import threading
import os
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import httpx
from typing import Dict, Any, List, Optional
import random
import hashlib 

# --- Project Imports ---
import config.config as config_module
from database_handler import DatabaseClient
from trading_logic import TradingManager
from connectors.websocket_handler import WebSocketHandler 
from bot_logger import setup_logging, logger, rotate_log_file
from state_manager import GlobalState
from trade_processor import trade_worker
from connectors.sol_price_api import update_sol_price
from connectors.rugcheck_handler import Rugcheck
from socials_processor import SocialsProcessor
from utils import calculate_volatility, ensure_datetime
from connectors.dexscreener_api import DexscreenerFetcher
from ai_decision_module.ai_decision_maker import AIDecisionMaker
from ai_decision_module.ai_data_assembler import fetch_comprehensive_token_data
from telegram_interface import send_telegram_message

from typing import Optional

# --- Constants for File-Based IPC ---
PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

class TradingBot:
    """
    Main class for running the trading bot.
    
    This class orchestrates all components, including:
    - Database connection
    - Configuration loading (base, dynamic, and params files)
    - WebSocket connection management
    - Core service tasks (trade processing, price updates, rug checks, etc.)
    - Dynamic AI module lifecycle management
    - Status reporting and command listening
    - Graceful shutdown
    """

    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, no_log_rotate: bool = False):
        """
        Initializes the TradingBot instance.
        
        Args:
            cleanup (bool): If True, cleans up the database on start.
            backup (bool): If True, backs up the database on start.
            params_file (str): Path to an optional JSON file for GA/RL parameters.
            no_logger.rotate (bool): If True, disables log rotation (used when run by main.py).
        """
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.state = GlobalState.get_instance()
        self.cleanup = cleanup
        self.backup = backup
        self.no_log_rotate = no_log_rotate
        self.params_file = params_file
        self.db_client: Optional[DatabaseClient] = None
        self.ws_handler: Optional[WebSocketHandler] = None
        self.tasks: List[asyncio.Task] = []
        self.config: Dict[str, Any] = {}
        self.base_config: Dict[str, Any] = {}
        self._load_base_config()
        self.trading_manager: Optional[TradingManager] = None
        self._last_dynamic_config_mtime: float = 0.0
        self.bot_start_time = datetime.now(timezone.utc)
        self.dexscreener_fetcher: Optional[DexscreenerFetcher] = None
        self.socials_proc: Optional[SocialsProcessor] = None
        self.rugchecker: Optional[Rugcheck] = None

        # --- AI Component Placeholders (Dynamically Managed) ---
        # --- FIX: Renamed attributes to avoid conflict with method names ---
        self.ai_decision_maker: Optional[AIDecisionMaker] = None
        self.ai_semaphore: Optional[asyncio.Semaphore] = None
        self.ai_worker_task_handle: Optional[asyncio.Task] = None
        self.ai_populator_task_handle: Optional[asyncio.Task] = None
        self.ai_outcome_monitor_task_handle: Optional[asyncio.Task] = None
        self.ai_vector_maint_task_handle: Optional[asyncio.Task] = None
        # --- [NEW] Add task handle for migration KB ---
        self.migration_knowledge_builder_task_handle: Optional[asyncio.Task] = None
        self.knowledge_base_builder_task_handle: Optional[asyncio.Task] = None
        # --- END FIX ---

        os.makedirs(DATA_DIR_BOT, exist_ok=True)
        self._write_status({"bot_process_status": "INITIALIZING", "timestamp": datetime.now(timezone.utc).isoformat()})

    async def _fetch_initial_sol_price(self) -> bool:
        """
        Fetches the SOL price once on startup to ensure the bot has a valid
        price before other services (like the price updater) start.
        """
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Fetching initial SOL price from {config_module._SOL_PRICE_API_URL}")
                response = await client.get(config_module._SOL_PRICE_API_URL, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    new_price = data.get("solana", {}).get("usd")
                    if new_price is None or not isinstance(new_price, (int, float)):
                        logger.error("Invalid or missing SOL price in initial API response.")
                        return False
                    # Set in-memory state and write to DB
                    await self.state.set_sol_price(new_price)
                    await self.db_client.insert_sol_price(new_price) 
                    logger.info(f"✅ Initial SOL price successfully fetched and set: {new_price} USD")
                    return True
                else:
                    logger.error(f":police_car_light: Error fetching initial SOL price. Status: {response.status_code}, Response: {response.text}")
                    return False
        except (httpx.TimeoutException, httpx.RequestError, Exception) as e:
            logger.error(f"❌ Exception fetching initial SOL price: {e}", exc_info=True)
            return False

    def _filter_serializable_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Filters a config dict to only include JSON-serializable types."""
        serializable_config = {}
        for key, value in config_dict.items():
            if isinstance(value, set):
                serializable_config[key] = list(value)
            elif isinstance(value, timedelta):
                serializable_config[key] = str(value)
            elif isinstance(value, (int, float, str, bool, list, dict)) or value is None:
                serializable_config[key] = value
            else:
                # Fallback: convert unknown types to string
                serializable_config[key] = str(value)
        return serializable_config

    def _load_base_config(self):
        """
        Loads the base configuration from config/config.py and writes
        the first dynamic_config.json if it doesn't exist.
        """
        try:
            loaded_config = {}
            # Iterate over attributes in config_module
            for key in dir(config_module):
                # Load only uppercase variables that are not modules/classes/functions/private
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config_module, key)
                    if not inspect.ismodule(value) and not inspect.isclass(value) and not inspect.isfunction(value):
                        loaded_config[key] = value
            
            self.base_config = loaded_config.copy() # The immutable base
            self.config = loaded_config.copy()      # The mutable, active config
            logger.info(":gear: Base configuration loaded successfully.")
            
            # Write the initial dynamic config file if it's missing
            if not os.path.exists(DYNAMIC_CONFIG_FILE):
                with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    # Filter for serializable types before dumping
                    json.dump(self._filter_serializable_config(self.config), f, indent=4)
                logger.info(f"Initial '{DYNAMIC_CONFIG_FILE}' created from base config.")
                
        except Exception as e:
            logger.critical(f":x: [bold red]CRITICAL: Failed to load base configuration[/bold red]: {e}", exc_info=True)
            raise ValueError("Failed to load critical base configuration.") from e
        
    def register_signal_handlers(self):
        """Registers OS signal handlers for graceful shutdown."""
        def signal_handler():
            logger.info(":heavy_exclamation_mark: [bold red]Signal received[/bold red], initiating shutdown...")
            self.state.trigger_shutdown()
        
        if hasattr(signal, 'SIGINT'): # Handle Ctrl+C
            signal.signal(signal.SIGINT, lambda *_: signal_handler())
        if hasattr(signal, 'SIGTERM'): # Handle kill/system shutdown
            signal.signal(signal.SIGTERM, lambda *_: signal_handler())

    async def start_ai_services(self):
        """Initializes and starts all AI-related components and tasks."""
        if self.ai_decision_maker is not None:
            logger.warning("AI services are already running. Start request ignored.")
            return

        logger.info("🧠 [bold green]Starting AI services...[/bold green]")
        try:
            self.ai_decision_maker = AIDecisionMaker(config=self.config, db_client=self.db_client)
            logger.info("✅ AI Decision Maker initialized successfully.")
            
            self.ai_semaphore = asyncio.Semaphore(self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1))
            
            # --- FIX: Call the methods, store in the renamed attributes ---
            self.ai_worker_task_handle = asyncio.create_task(self.ai_evaluation_worker(), name="ai_evaluation_worker")
            self.ai_populator_task_handle = asyncio.create_task(self.populate_ai_queue_periodic(), name="ai_queue_populator")
            self.ai_outcome_monitor_task_handle = asyncio.create_task(self.ai_outcome_monitor_task(), name="ai_outcome_monitor")
            self.ai_vector_maint_task_handle = asyncio.create_task(self.run_vector_index_maintenance(), name="vector_index_maintenance")
            self.knowledge_base_builder_task_handle = asyncio.create_task(self.knowledge_base_builder(), name="knowledge_base_builder")
            # --- [NEW] Start the migration knowledge builder task ---
            self.migration_knowledge_builder_task_handle = asyncio.create_task(self.migration_knowledge_builder_task(), name="migration_knowledge_builder_task")

            # Add new tasks to the main task list for monitoring
            self.tasks.extend([
                self.ai_worker_task_handle,
                self.ai_populator_task_handle,
                self.ai_outcome_monitor_task_handle,
                self.ai_vector_maint_task_handle,
                self.knowledge_base_builder_task_handle,
                self.migration_knowledge_builder_task_handle # <-- ADD THIS
            ])
            
            # Update the TradingManager with the new AI instance
            if self.trading_manager:
                self.trading_manager.ai_decision_maker = self.ai_decision_maker
                
            logger.info("🧠 AI tasks (worker, populator, outcome_monitor, vector_maint, kb_builder, migration_kb_builder) have been started.")

        except Exception as ai_init_err:
            logger.critical(f"CRITICAL: Failed to initialize AI Decision Maker: {ai_init_err}", exc_info=True)
            self.config['AI_DECISION_MAKING_ENABLED'] = False # Force disable in config
            logger.warning("🧠 AI Decision Making has been DISABLED due to initialization error.")
            # Ensure partial cleanup
            self.ai_decision_maker = None
            self.ai_semaphore = None
            if self.trading_manager:
                self.trading_manager.ai_decision_maker = self.ai_decision_maker


    async def stop_ai_services(self):
        """Cancels all AI-related tasks and cleans up components."""
        if self.ai_decision_maker is None:
            logger.debug("AI services are already stopped. Stop request ignored.")
            return

        logger.info("🧠 [bold red]Stopping AI services...[/bold red]")
        
        # Update the TradingManager first
        if self.trading_manager:
            self.trading_manager.ai_decision_maker = self.ai_decision_maker
            
        # --- FIX: Use renamed task attributes ---
        ai_tasks = [
            self.ai_worker_task_handle, 
            self.ai_populator_task_handle, 
            self.ai_outcome_monitor_task_handle,
            self.ai_vector_maint_task_handle,
            self.knowledge_base_builder_task_handle,
            self.migration_knowledge_builder_task_handle # <-- ADD THIS
        ]
        # --- END FIX ---
        
        for task in ai_tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.debug(f"AI task {task.get_name()} cancelled.")
            
            # Remove from the main self.tasks list
            if task in self.tasks:
                self.tasks.remove(task)

        # Clear components
        # --- FIX: Use renamed task attributes ---
        self.ai_decision_maker = None
        self.ai_semaphore = None
        self.ai_worker_task_handle = None
        self.ai_populator_task_handle = None
        self.ai_outcome_monitor_task_handle = None
        self.ai_vector_maint_task_handle = None
        self.knowledge_base_builder_task_handle = None
        self.migration_knowledge_builder_task_handle = None # <-- ADD THIS
        # --- END FIX ---
        
        logger.info("🧠 AI services have been stopped.")

    async def config_updater(self):
        """
        Periodically checks the dynamic_config.json file for changes and
        hot-reloads the bot's self.config.
        
        This task is now also responsible for starting/stopping AI services
        based on the `AI_DECISION_MAKING_ENABLED` flag.
        """
        logger.info(f"⚙️ Dynamic config updater started. Watching: {os.path.abspath(DYNAMIC_CONFIG_FILE)}")
        while not self.state.shutdown_event.is_set():
            try:
                if not os.path.exists(DYNAMIC_CONFIG_FILE): 
                    logger.warning(f"'{DYNAMIC_CONFIG_FILE}' not found. Will retry.")
                    await self.state.wait_or_interrupt(timeout=10)
                    continue
                
                # Check file modification time
                current_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
                if current_mtime > self._last_dynamic_config_mtime:
                    logger.info(f"Detected change in {DYNAMIC_CONFIG_FILE}. Attempting to load updates.")
                    
                    # --- DYNAMIC AI LIFECYCLE LOGIC ---
                    # 1. Check AI state *before* loading new config
                    was_ai_enabled = bool(self.ai_decision_maker is not None)
                    
                    # 2. Load new config from file
                    with open(DYNAMIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                        dynamic_conf = json.load(f)
                        
                    # 3. Apply updates to self.config
                    updated_count = 0
                    changed_params = {}
                    for key, value in dynamic_conf.items():
                        key_upper = key.upper()
                        # Only update if key exists in base config and value is different
                        if key_upper in self.base_config and value != self.config.get(key_upper):
                            self.config[key_upper] = value
                            changed_params[key_upper] = value
                            updated_count += 1
                            
                    if updated_count > 0:
                        logger.info(f"Applied {updated_count} configuration updates: {changed_params}")
                    
                    self._last_dynamic_config_mtime = current_mtime
                    
                    # 4. Check AI state *after* loading new config
                    is_ai_enabled_now = self.config.get('AI_DECISION_MAKING_ENABLED', False)

                    # 5. Start or stop AI services based on the state change
                    if is_ai_enabled_now and not was_ai_enabled:
                        logger.info("Config change detected: ENABLING AI services...")
                        # Schedule the start, don't block the updater
                        asyncio.create_task(self.start_ai_services()) 
                    elif not is_ai_enabled_now and was_ai_enabled:
                        logger.info("Config change detected: DISABLING AI services...")
                        # Schedule the stop, don't block the updater
                        asyncio.create_task(self.stop_ai_services())
                    # --- END DYNAMIC AI LIFECYCLE LOGIC ---
                        
                await self.state.wait_or_interrupt(timeout=10) # Poll every 10 seconds
                
            except asyncio.CancelledError: 
                break
            except json.JSONDecodeError as json_err:
                logger.error(f":police_car_light: Error decoding {DYNAMIC_CONFIG_FILE}: {json_err}. Config not updated.")
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE) # Acknowledge mtime to avoid loop
            except Exception as e:
                logger.error(f":police_car_light: Error in config_updater loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=30)
                
        logger.info("⚙️ Dynamic config updater task shutting down.")

    def _write_status(self, status_data: dict):
        """Atomically writes the bot's current status to the JSON file."""
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=4)
        except IOError as e:
            logger.error(f":police_car_light: Error writing status file {STATUS_FILE}: {e}")

    async def market_regime_updater(self):
        """Periodically checks SOL price to determine market regime."""
        logger.info("📈 Market Regime Updater started.")
        while not self.state.shutdown_event.is_set():
            try:
                # Get 1h and 24h SOL price change (simplified example)
                # A real implementation might query dexscreener for a "meme index"
                sol_price_1h_ago = await self.db_client.pool.fetchval(
                    "SELECT price FROM sol_price_usd WHERE timestamp <= NOW() - INTERVAL '1 day' ORDER BY timestamp DESC LIMIT 1"
                )
                current_sol_price = await self.state.get_sol_price()

                regime = "NEUTRAL"
                if sol_price_1h_ago and current_sol_price:
                    change_pct = ((current_sol_price / float(sol_price_1h_ago)) - 1) * 100
                    if change_pct > 0.5: regime = "BULLISH"
                    elif change_pct < -0.5: regime = "BEARISH"

                await self.state.set_market_regime(regime)
                logger.debug(f"Market regime set to: {regime}")

                await self.state.wait_or_interrupt(timeout=600) # Update every 10 mins
            except Exception as e:
                logger.error(f"Error in market_regime_updater: {e}")
                await self.state.wait_or_interrupt(timeout=600) 
    
    async def knowledge_base_builder(self):
        """
        [REFACTORED V6] Builds a case-study library from all backed-up tokens
        with enriched data and corrected lifespan formatting.
        """
        logger.info("📚 Market-Wide Knowledge Base Builder started.")
        BATCH_SIZE = 500  # Process 500 tokens at a time

        while not self.state.shutdown_event.is_set():
            try:
                # --- [START SHUTDOWN/SAFETY CHECK 1] ---
                # Check 1: AI must be enabled AND self.ai_decision_maker must exist
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False) or self.state.shutdown_event.is_set():
                    logger.warning("📚 Knowledge Base Builder is paused (AI disabled or shutting down).")
                    await self.state.wait_or_interrupt(timeout=1800) # Sleep for an hour
                    continue
                # --- [END SHUTDOWN/SAFETY CHECK 1] ---

                logger.info("📚 Knowledge Base: Checking 'tokens_backup' for new case studies to process...")
                
                # --- Batch Processing Loop ---
                while not self.state.shutdown_event.is_set():
                    
                    # --- [START SHUTDOWN/SAFETY CHECK 2] ---
                    # Check again inside the batch loop, as shutdown could be triggered
                    if not self.ai_decision_maker or self.state.shutdown_event.is_set():
                        logger.info("📚 Knowledge Base: Shutdown detected during batch processing.")
                        break # Exit inner loop
                    # --- [END SHUTDOWN/SAFETY CHECK 2] ---

                    # --- [ENRICHED QUERY] ---
                    query = """
                        SELECT
                            t.mint, t.name, t.traderpublickey, t.backup_reason, t.timestamp as token_creation_ts,
                            ((SELECT MAX(tr.timestamp) FROM trades_backup tr WHERE tr.mint = t.mint) - t.timestamp) as lifespan,
                            (SELECT MAX(tr.marketCapSol) FROM trades_backup tr WHERE tr.mint = t.mint) as max_mcap,
                            (SELECT MAX(tr.price) FROM trades_backup tr WHERE tr.mint = t.mint) as max_price,
                            (SELECT (array_agg(tr.timestamp ORDER BY tr.price DESC))[1] FROM trades_backup tr WHERE tr.mint = t.mint AND tr.price > 0) as max_price_ts,
                            (SELECT SUM(tr.sol_amount) FROM trades_backup tr WHERE tr.mint = t.mint) as total_volume_sol,
                            (SELECT score FROM rugcheck_backup rb WHERE rb.mint = t.mint ORDER BY rb.last_checked DESC LIMIT 1) as last_rug_score,
                            (SELECT score_value FROM social_scores_backup sb WHERE sb.mint = t.mint ORDER BY sb.timestamp DESC LIMIT 1) as last_social_score,
                            (SELECT details FROM social_scores_backup sb WHERE sb.mint = t.mint ORDER BY sb.timestamp DESC LIMIT 1) as last_social_details
                        FROM tokens_backup t
                        LEFT JOIN market_knowledge_base kb ON t.mint = kb.mint
                        WHERE kb.mint IS NULL AND t.backup_reason IS NOT NULL
                        LIMIT $1;
                    """
                    records = await self.db_client.pool.fetch(query, BATCH_SIZE)

                    if not records:
                        logger.info("📚 Knowledge Base: All available case studies have been processed. Sleeping for 1 hour.")
                        break 

                    logger.info(f"📚 Knowledge Base: Found a batch of {len(records)} new case studies to process...")
                    batch_to_insert = []
                    
                    for r in records:
                        try:
                            # 1. Extract all new fields
                            mint = r['mint']
                            creator_wallet = r['traderpublickey']
                            backup_reason = r['backup_reason']
                            name = r['name']
                            token_creation_ts = ensure_datetime(r['token_creation_ts'])
                            max_mcap = r['max_mcap']
                            max_price = r['max_price']
                            max_price_ts = ensure_datetime(r['max_price_ts'])
                            lifespan_delta = r['lifespan']
                            total_volume_sol = r['total_volume_sol']
                            last_rug_score = r['last_rug_score']
                            last_social_score = r['last_social_score']
                            last_social_details_json = r['last_social_details']

                            # 2. Call for creator history
                            creator_history_summary, creator_summary_dict = await self.db_client.get_creator_history_summary(creator_wallet, mint)

                            # --- [START FIX] ---
                            # 3. Parse lifespan with better granularity
                            lifespan_str = "N/A"
                            lifespan_minutes = None
                            if lifespan_delta:
                                lifespan_seconds = lifespan_delta.total_seconds()
                                lifespan_minutes = lifespan_seconds / 60.0
                                
                                if lifespan_seconds < 60:
                                    lifespan_str = f"{lifespan_seconds:.0f} sec"
                                elif lifespan_seconds < 7200: # Less than 2 hours
                                    lifespan_str = f"{lifespan_minutes:.1f} min"
                                else: # 2+ hours
                                    lifespan_str = f"{lifespan_minutes / 60.0:.1f} hrs"
                            # --- [END FIX] ---

                            # --- [NEW] Compute time-to-peak ---
                            time_to_peak_minutes = None
                            if max_price_ts and token_creation_ts:
                                time_to_peak_minutes = (max_price_ts - token_creation_ts).total_seconds() / 60.0
                            
                            # 4. Parse social details for hype
                            last_member_count_str = "N/A"
                            last_member_count_int = None
                            if last_social_details_json:
                                details_dict = {}
                                if isinstance(last_social_details_json, str):
                                    try: details_dict = json.loads(last_social_details_json)
                                    except json.JSONDecodeError: pass
                                elif isinstance(last_social_details_json, dict):
                                    details_dict = last_social_details_json
                                
                                telegram_stats = details_dict.get('telegram_stats', {})
                                if telegram_stats and telegram_stats.get('members') is not None:
                                    last_member_count_str = f"{telegram_stats['members']}"
                                    last_member_count_int = int(telegram_stats['members'])
                            
                            # --- [START FIX for TypeError] ---
                            # Pre-format the time_to_peak_minutes to handle None
                            ttp_str = f"{time_to_peak_minutes:.1f}" if time_to_peak_minutes is not None else "N/A"
                            # --- [END FIX] ---
                            
                            # 5. Format the rich summary string
                            summary = (
                                f"Case Study: Token '{name}' ({mint}) by creator {creator_wallet}.\n"
                                f"Outcome: {backup_reason} (Lifespan: {lifespan_str}).\n"
                                f"Creator History: {creator_history_summary}\n"
                                # --- [MODIFIED LINE] ---
                                f"Metrics at End: Max MCap: {max_mcap or 'N/A'} SOL | Max Price: {max_price or 'N/A'} SOL (at {ttp_str} mins)\n"
                                # --- [END MODIFIED LINE] ---
                                f"Last Scores: Rug: {last_rug_score or 'N/A'} | Social: {last_social_score or 'N/A'}"
                            )

                            # 6. Format the rich metadata dict
                            metadata = {
                                'creator': creator_wallet, 
                                'reason': backup_reason, 
                                'max_mcap': float(max_mcap) if max_mcap is not None else None,
                                'max_price': float(max_price) if max_price is not None else None,
                                'max_price_ts': max_price_ts.isoformat() if max_price_ts else None,
                                'time_to_peak_minutes': float(time_to_peak_minutes) if time_to_peak_minutes is not None else None,
                                'total_volume_sol': float(total_volume_sol) if total_volume_sol is not None else None,
                                'lifespan_minutes': float(lifespan_minutes) if lifespan_minutes is not None else None,
                                'last_rug_score': int(last_rug_score) if last_rug_score is not None else None,
                                'last_social_score': int(last_social_score) if last_social_score is not None else None,
                                # Unpack the structured creator data
                                **creator_summary_dict
                            }
                            
                            # 7. Add to batch
                            # --- [START SHUTDOWN/SAFETY CHECK 3] ---
                            # Final check before making the await call
                            if not self.ai_decision_maker:
                                logger.warning("📚 Knowledge Base: AI maker was shut down mid-batch. Aborting.")
                                break # Exit 'for' loop
                            # --- [END SHUTDOWN/SAFETY CHECK 3] ---
                            
                            embedding = await self.ai_decision_maker.embed_text(summary)
                            if embedding:
                                batch_to_insert.append((
                                    mint, summary, str(embedding), json.dumps(metadata)
                                ))
                            else:
                                logger.warning(f"📚 Knowledge Base: Failed to generate embedding for {mint}. Skipping this record.")
                        
                        except Exception as processing_err:
                            logger.error(f"📚 Knowledge Base: Failed to process record {r.get('mint')}: {processing_err}", exc_info=True)
                    
                    # CHECK 5: Insert the processed batch
                    if batch_to_insert:
                        # --- [START SHUTDOWN/SAFETY CHECK 4] ---
                        # Check before DB insert
                        if not self.ai_decision_maker or self.state.shutdown_event.is_set():
                            logger.warning("📚 Knowledge Base: AI maker was shut down before batch insert.")
                            break # Exit inner loop
                        # --- [END SHUTDOWN/SAFETY CHECK 4] ---

                        try:
                            insert_query = """
                                INSERT INTO market_knowledge_base (mint, summary, embedding, metadata) 
                                VALUES ($1, $2, $3, $4) 
                                ON CONFLICT(mint) DO NOTHING
                            """
                            await self.db_client.pool.executemany(insert_query, batch_to_insert)
                            logger.info(f"📚 Knowledge Base: Successfully inserted {len(batch_to_insert)} case studies.")
                        except Exception as insert_err:
                            logger.error(f"📚 Knowledge Base: Error during batch insert: {insert_err}", exc_info=True)
                    
                    if len(records) < BATCH_SIZE:
                        logger.info("📚 Knowledge Base: Finished processing the last batch.")
                        break 
                    
                    await self.state.wait_or_interrupt(timeout=2) 
                
                await self.state.wait_or_interrupt(timeout=1800) # Sleep for 1 hour

            except asyncio.CancelledError:
                logger.info("📚 Market-Wide Knowledge Base Builder task cancelled.")
                break
            except Exception as e:
                # Catch the 'NoneType' error here if it still happens
                if isinstance(e, AttributeError) and "'NoneType' object has no attribute 'embed_text'":
                    logger.warning(f"📚 Knowledge Base: Caught shutdown race condition. Task will exit.")
                    break # Gracefully exit the task
                
                logger.error(f"Error in knowledge_base_builder: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=1800) # Wait 1 hour on other errors
        
        logger.info("📚 Market-Wide Knowledge Base Builder task shutting down.")

    # --- [NEW TASK - REFACTORED] ---
    async def migration_knowledge_builder_task(self):
        """
        [REFACTORED] Builds case studies for tokens that have successfully migrated
        and adds them to the market_knowledge_base.
        """
        logger.info("📚 Migration Knowledge Base Builder started.")
        BATCH_SIZE = 100 # Process 100 migrations at a time

        while not self.state.shutdown_event.is_set():
            try:
                # --- [START SHUTDOWN/SAFETY CHECK 1] ---
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False) or self.state.shutdown_event.is_set():
                    logger.warning("📚 Migration KB Builder is paused (AI disabled or shutting down).")
                    await self.state.wait_or_interrupt(timeout=3600) # Sleep for an hour
                    continue
                # --- [END SHUTDOWN/SAFETY CHECK 1] ---

                logger.info("📚 Migration KB: Checking 'v_migrations' for new case studies to process...")
                
                # --- Batch Processing Loop ---
                while not self.state.shutdown_event.is_set():
                    
                    if not self.ai_decision_maker or self.state.shutdown_event.is_set():
                        logger.info("📚 Migration KB: Shutdown detected during batch processing.")
                        break # Exit inner loop

                    # --- [ENRICHED QUERY] ---
                    # Find migrations that are not yet in the knowledge base
                    query = """
                        WITH LatestMigration AS (
                            SELECT 
                                mint, 
                                MAX(timestamp) as migration_ts
                            FROM v_migrations
                            GROUP BY mint
                        )
                        SELECT 
                            lm.mint, lm.migration_ts,
                            vt.traderpublickey, vt.timestamp as token_creation_ts, vt.name
                        FROM LatestMigration lm
                        JOIN v_tokens vt ON lm.mint = vt.mint
                        LEFT JOIN market_knowledge_base kb ON lm.mint = kb.mint
                        WHERE kb.mint IS NULL -- Not yet in the knowledge base
                        LIMIT $1;
                    """
                    records = await self.db_client.pool.fetch(query, BATCH_SIZE)

                    if not records:
                        logger.info("📚 Migration KB: All available migration cases have been processed. Sleeping for 1 hour.")
                        break 

                    logger.info(f"📚 Migration KB: Found a batch of {len(records)} new migration cases to process...")
                    batch_to_insert = []
                    
                    # --- [START FIX] ---
                    # Acquire connection *outside* the loop
                    async with self.db_client.pool.acquire() as conn:
                        for r in records:
                            try:
                                # 1. Extract data
                                mint = r['mint']
                                name = r['name']
                                migration_ts = ensure_datetime(r['migration_ts'])
                                token_creation_ts = ensure_datetime(r['token_creation_ts'])
                                creator_wallet = r['traderpublickey']

                                if not all([mint, migration_ts, token_creation_ts, creator_wallet]):
                                    logger.warning(f"Migration KB: Skipping {mint}, missing core data.")
                                    continue

                                age_at_migration_minutes = (migration_ts - token_creation_ts).total_seconds() / 60.0

                                # 2. Get pre-migration data (last 30 mins of Pump)
                                pre_migration_data = await conn.fetch(
                                    """
                                    SELECT price, marketcapsol FROM v_trades 
                                    WHERE mint = $1 AND timestamp < $2 
                                    ORDER BY timestamp DESC LIMIT 100
                                    """, mint, migration_ts
                                )
                                pre_mig_price, pre_mig_mcap = None, None
                                if pre_migration_data:
                                    pre_mig_price = float(pre_migration_data[0]['price'])
                                    pre_mig_mcap = float(pre_migration_data[0]['marketcapsol'])

                                # 3. Get post-migration data (first 30 mins of Dex)
                                post_migration_data = await conn.fetch(
                                    """
                                    SELECT price_native, (market_cap / sol_price_usd) as market_cap_sol 
                                    FROM v_dexscreener_data 
                                    WHERE mint_address = $1 AND timestamp > $2 
                                    ORDER BY timestamp ASC LIMIT 10
                                    """, mint, migration_ts
                                )
                                post_mig_price, post_mig_mcap = None, None
                                if post_migration_data:
                                    post_mig_price = float(post_migration_data[0]['price_native'])
                                    post_mig_mcap = float(post_migration_data[0]['market_cap_sol'])
                                
                                # 4. Get 1-hour post-migration peak
                                peak_post_migration = await conn.fetchrow(
                                    """
                                    SELECT MAX(price_native) as peak_price, MAX(market_cap / sol_price_usd) as peak_mcap
                                    FROM v_dexscreener_data
                                    WHERE mint_address = $1 AND timestamp BETWEEN $2 AND $2 + INTERVAL '1 hour'
                                    """, mint, migration_ts
                                )
                                peak_price_1h_post = float(peak_post_migration['peak_price']) if peak_post_migration and peak_post_migration['peak_price'] else None
                                peak_mcap_1h_post = float(peak_post_migration['peak_mcap']) if peak_post_migration and peak_post_migration['peak_mcap'] else None

                                # 5. Creator history
                                creator_history_summary, creator_summary_dict = await self.db_client.get_creator_history_summary(creator_wallet, mint)

                                # 6. Format summary string
                                summary = (
                                    f"Case Study: Token '{name}' ({mint}) by creator {creator_wallet}.\n"
                                    f"Outcome: Successful Migration at {age_at_migration_minutes:.1f} minutes old.\n"
                                    f"Creator History: {creator_history_summary}\n"
                                    f"Pre-Migration (Pump): Price: {pre_mig_price or 'N/A'} SOL | MCap: {pre_mig_mcap or 'N/A'} SOL\n"
                                    f"Post-Migration (DEX): Price: {post_mig_price or 'N/A'} SOL | MCap: {post_mig_mcap or 'N/A'} SOL\n"
                                    f"Peak within 1h post-migration: {peak_price_1h_post or 'N/A'} SOL | {peak_mcap_1h_post or 'N/A'} SOL MCap"
                                )

                                # 7. Format metadata dict
                                metadata = {
                                    'creator': creator_wallet, 
                                    'reason': "Successful Migration", 
                                    'label': "MIGRATION_SUCCESS",
                                    'age_at_migration_minutes': age_at_migration_minutes,
                                    'pre_migration_price_sol': pre_mig_price,
                                    'pre_migration_mcap_sol': pre_mig_mcap,
                                    'post_migration_price_sol': post_mig_price,
                                    'post_migration_mcap_sol': post_mig_mcap,
                                    'peak_price_1h_post_sol': peak_price_1h_post,
                                    'peak_mcap_1h_post_sol': peak_mcap_1h_post,
                                    **creator_summary_dict
                                }
                                
                                # 8. Add to batch
                                if not self.ai_decision_maker:
                                    logger.warning("📚 Migration KB: AI maker was shut down mid-batch. Aborting.")
                                    break 
                                
                                embedding = await self.ai_decision_maker.embed_text(summary)
                                if embedding:
                                    batch_to_insert.append((
                                        mint, summary, str(embedding), json.dumps(metadata)
                                    ))
                                else:
                                    logger.warning(f"📚 Migration KB: Failed to generate embedding for {mint}. Skipping this record.")
                            
                            except Exception as processing_err:
                                logger.error(f"📚 Migration KB: Failed to process record {r.get('mint')}: {processing_err}", exc_info=True)
                        
                        # 9. Insert the processed batch (Still inside the `with` block)
                        if batch_to_insert:
                            if not self.ai_decision_maker or self.state.shutdown_event.is_set():
                                logger.warning("📚 Migration KB: AI maker was shut down before batch insert.")
                            else:
                                try:
                                    insert_query = """
                                        INSERT INTO market_knowledge_base (mint, summary, embedding, metadata) 
                                        VALUES ($1, $2, $3, $4) 
                                        ON CONFLICT(mint) DO NOTHING
                                    """
                                    await conn.executemany(insert_query, batch_to_insert)
                                    logger.info(f"📚 Migration KB: Successfully inserted {len(batch_to_insert)} migration case studies.")
                                except Exception as insert_err:
                                    logger.error(f"📚 Migration KB: Error during batch insert: {insert_err}", exc_info=True)
                    # --- [END FIX] ---
                    
                    if len(records) < BATCH_SIZE:
                        logger.info("📚 Migration KB: Finished processing the last batch.")
                        break 
                    
                    await self.state.wait_or_interrupt(timeout=2) 
                
                await self.state.wait_or_interrupt(timeout=3600) # Sleep for 1 hour

            except asyncio.CancelledError:
                logger.info("📚 Migration Knowledge Base Builder task cancelled.")
                break
            except Exception as e:
                if isinstance(e, AttributeError) and "'NoneType' object has no attribute 'embed_text'":
                    logger.warning(f"📚 Migration KB: Caught shutdown race condition. Task will exit.")
                    break 
                
                logger.error(f"Error in migration_knowledge_builder_task: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=3600)
        
        logger.info("📚 Migration Knowledge Base Builder task shutting down.")
    # --- [END NEW TASK] ---

    async def ai_evaluation_worker(self):
        """
        Continuously processes tokens from the AI evaluation queue.
        Fetches comprehensive data and calls AIDecisionMaker.get_trade_advice,
        which now handles its own database logging (RAG memory).
        """
        logger.info("🧠 AI Evaluation Worker started.")
        if not self.db_client: # self.ai_decision_maker is checked in the loop
            logger.critical("🧠 AI Worker cannot start: DatabaseClient not initialized.")
            return
            
        while not self.state.shutdown_event.is_set():
            mint = None
            context = None 
            priority = None 
            try:
                # Check if AI is enabled at the start of the loop
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False):
                    await self.state.wait_or_interrupt(timeout=5)
                    continue
                    
                # 1. Get task from queue
                priority, (mint, context) = await asyncio.wait_for(
                    self.state.get_ai_evaluation_queue().get(), timeout=1.0
                )

                # Immediately remove it from the tracking set so it can be re-queued if needed
                async with self.state.ai_queue_lock:
                    self.state.ai_queue_mints.discard(mint)
                
                logger.debug(f"🧠 AI Worker: Picked up {mint} (Context: {context}, Prio: {priority})")
                
                # 2. Acquire semaphore
                async with self.ai_semaphore:
                    # Re-check state after acquiring semaphore
                    if self.state.shutdown_event.is_set() or not self.ai_decision_maker: 
                        break
                        
                    evaluation_start_time = time.monotonic()
                    
                    # 3. Fetch data
                    comprehensive_data = await fetch_comprehensive_token_data(self.db_client, mint)
                    
                    # --- NEW LOGIC ---
                    # 4. Check if the token was backed up (race condition)
                    if comprehensive_data.get("status") == "INACTIVE_BACKED_UP":
                        logger.info(f"🧠 AI Worker: Logging 'Dodged Bullet' for rugged/dead token {mint}.")
                        
                        # We don't need to call the LLM. Just format the outcome for RAG.
                        outcome_snapshot = {
                            "mint": mint, "source": "PUMP", # Source is unknown, but irrelevant
                            "timestamp": comprehensive_data['backup_timestamp'].isoformat(),
                            "decision_context": "NON_TRADE_OUTCOME",
                            "market_cap": 0, "volatility": 0, "token_age_minutes": 0,
                            "creator_history_summary": comprehensive_data.get('creator_history_summary', 'N/A'),
                            "uri_status": "N/A",
                            "market_dynamics_summary_str": f"Token rugged/dead. Reason: {comprehensive_data['backup_reason']}",
                            "trade_history_summary": "No trades by bot."
                        }
                        outcome_decision = {
                            "decision": "DODGED_BULLET (RUGGED)", "confidence": 100,
                            "explanation": f"Bot detected a rule-based buy opportunity, but the token was backed up (reason: {comprehensive_data['backup_reason']}) "
                                         f"before the AI could evaluate it. This log confirms the token was a bad buy."
                        }
                        
                        # Directly add this outcome to the RAG memory
                        await self.ai_decision_maker.add_decision_snapshot_to_memory(outcome_snapshot, outcome_decision)
                        
                        # We don't update the 'ai_last_evaluation_ts' on the (now deleted) token
                        # We just mark the queue task as done.
                    
                    else:
                        # --- ORIGINAL LOGIC (for active tokens) ---
                        
                        # 4b. Get AI Advice (this now *also* saves to ai_decision_memory)
                        advice = await self.ai_decision_maker.get_trade_advice(comprehensive_data) 
                        
                        eval_ts = datetime.now(timezone.utc)

                        # 5. Update the token's last evaluation timestamp
                        async with self.db_client.pool.acquire() as conn:
                            await self.db_client.update_token_ai_eval_timestamp(mint, eval_ts, conn=conn)

                        # --- [START FIX] ---
                        # Check for both 'INITIAL BUY' and 'REBUY' contexts.
                        # We also trust the 'decision' from the parser, which has already
                        # applied the 50% confidence threshold.
                        if (comprehensive_data.get('decision_context') in ['INITIAL BUY', 'REBUY'] and 
                            advice['decision'] == 'BUY'):

                            # The check against AI_CONFIDENCE_THRESHOLD_INITIAL_BUY is no longer needed here,
                            # because the parser ('_parse_llm_json_response') has already done this
                            # by translating any confidence >= 50 into a "BUY" decision.
                            
                            logger.info(f"🧠 [bold green]AI-First Buy Triggered[/bold green] for {mint} (Context: {comprehensive_data.get('decision_context')}, Confidence: {advice['confidence']}%).")
                            
                            price_to_buy = comprehensive_data.get('price')
                            # execute_buy expects market_cap in SOL
                            mcap_to_buy = (comprehensive_data.get('market_cap', 0) / (await self.state.get_sol_price())) if await self.state.get_sol_price() else 0.0

                            if price_to_buy and mcap_to_buy and price_to_buy > 0 and mcap_to_buy > 0:
                                if not self.state.is_buying_enabled:
                                    logger.info(f"🧠 AI-First Buy for {mint} skipped: Buying is globally disabled.")
                                else:
                                    # Call execute_buy from the trading_manager
                                    await self.trading_manager.execute_buy(
                                        mint=mint,
                                        trigger_price=price_to_buy,
                                        market_cap_sol_at_trigger=mcap_to_buy,
                                        buy_reason=f"AI-First ({comprehensive_data.get('decision_context')})", # More specific reason
                                        ai_context=advice # Pass the full advice dict
                                    )
                            else:
                                logger.warning(f"🧠 AI-First Buy for {mint} skipped: Invalid price ({price_to_buy}) or mcap ({mcap_to_buy}).")
                        
                        elif (comprehensive_data.get('decision_context') in ['INITIAL BUY', 'REBUY'] and
                            advice['decision'] == 'HOLD'):
                            logger.debug(f"🧠 AI-First Buy: AI advised HOLD for {mint} (Confidence: {advice['confidence']}%). No action taken.")
                        # --- [END FIX] ---

                        evaluation_duration = time.monotonic() - evaluation_start_time
                        
                        logger.info(f"🧠 AI eval complete for {mint} ({context}) -> {advice['decision']} ({advice['confidence']}%) in {evaluation_duration:.2f}s")
                    
                    # --- END OF LOGIC ---
                
                self.state.get_ai_evaluation_queue().task_done()
                mint = None # Clear mint on success
                
            except asyncio.TimeoutError: 
                continue # Queue was empty, loop again
            except asyncio.CancelledError: 
                logger.info("🧠 AI Evaluation Worker task cancelled."); 
                break
            except ValueError as ve: 
                # This often happens if fetch_comprehensive_token_data fails (e.g., token deleted)
                logger.error(f"🧠 AI Worker: Error fetching data for {mint} (likely deleted): {ve}")
                if mint:
                    try: self.state.get_ai_evaluation_queue().task_done()
                    except ValueError: pass
            except Exception as e:
                logger.error(f"🚨 Unexpected error in AI Evaluation Worker: {e}", exc_info=True)
                if mint:
                    try: self.state.get_ai_evaluation_queue().task_done()
                    except ValueError: pass
                await self.state.wait_or_interrupt(timeout=10) # Pause on unexpected error
            finally:
                # --- [START SOLUTION 2: FAIL-SAFE REMOVAL] ---
                # If an error happened before the item was processed
                if mint:
                    async with self.state.ai_queue_lock:
                        self.state.ai_queue_mints.discard(mint)
                    try:
                        self.state.get_ai_evaluation_queue().task_done()
                    except ValueError: pass
                # --- [END SOLUTION 2] ---
                
        logger.info("🧠 AI Evaluation Worker shutting down.")

    async def populate_ai_queue_periodic(self):
        """Periodically scans the database for tokens that need AI evaluation and adds them to the queue."""
        logger.info("📊 AI Queue Populator started.")
        while not self.state.shutdown_event.is_set():
            try:
                # Check if AI is enabled at the start of the loop
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False):
                    await self.state.wait_or_interrupt(timeout=60)
                    continue

                q = self.state.get_ai_evaluation_queue()
                max_q_size = self.config.get('AI_QUEUE_MAX_SIZE', 1000)
                added_count = 0

                # --- [START SOLUTION 1: PER-PRIORITY FILLING] ---
                
                # --- Priority 1: Active Portfolio ---
                if not q.full():
                    portfolio_mints = await self.db_client.get_active_portfolio_for_ai_eval(
                        self.config.get('AI_REFRESH_INTERVAL_PORTFOLIO_MIN', 5)
                    )
                    for mint in portfolio_mints:
                        if q.qsize() < max_q_size: 
                            async with self.state.ai_queue_lock:
                                if mint not in self.state.ai_queue_mints:
                                    await q.put((-100, (mint, 'SELL/HOLD')))
                                    self.state.ai_queue_mints.add(mint)
                                    added_count += 1
                        else: 
                            logger.warning("AI Queue became full while adding P1 Portfolio items.")
                            break # Stop adding this category
                    if portfolio_mints: logger.debug(f"🧠 AI Queue: Added {len(portfolio_mints)} portfolio tokens.")
                
                # --- Priority 2: High Momentum (PUMP) ---
                if not q.full():
                    pump_mints = await self.db_client.get_top_pump_momentum_for_ai_eval(
                        self.config.get('AI_MOMENTUM_TOP_N', 5), 30, self.config.get('AI_REFRESH_INTERVAL_MOMENTUM_MIN', 15)
                    )
                    for mint in pump_mints:
                        if q.qsize() < max_q_size:
                            past_pos_count = await self.db_client.pool.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
                            context = "REBUY" if past_pos_count > 0 else "INITIAL BUY"
                            async with self.state.ai_queue_lock:
                                if mint not in self.state.ai_queue_mints:
                                    await q.put((-50, (mint, context)))
                                    self.state.ai_queue_mints.add(mint)
                                    added_count += 1
                        else: 
                            logger.warning("AI Queue became full while adding P2 PUMP items.")
                            break # Stop adding this category
                    if pump_mints: logger.debug(f"🧠 AI Queue: Added {len(pump_mints)} PUMP momentum tokens.")

                # --- Priority 2: High Momentum (DEX) ---
                if not q.full():
                    dex_mints = await self.db_client.get_top_dex_momentum_for_ai_eval(
                        self.config.get('AI_MOMENTUM_TOP_N', 5), 30, self.config.get('AI_REFRESH_INTERVAL_MOMENTUM_MIN', 15)
                    )
                    for mint in dex_mints:
                         if q.qsize() < max_q_size:
                            past_pos_count = await self.db_client.pool.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
                            context = "REBUY" if past_pos_count > 0 else "INITIAL BUY"

                            async with self.state.ai_queue_lock:
                                if mint not in self.state.ai_queue_mints:
                                    await q.put((-45, (mint, context)))
                                    self.state.ai_queue_mints.add(mint)
                                    added_count += 1
                         else: 
                            logger.warning("AI Queue became full while adding P2 DEX items.")
                            break # Stop adding this category
                    if dex_mints: logger.debug(f"🧠 AI Queue: Added {len(dex_mints)} DEX momentum tokens.")
                
                # --- Priority 3: Events (Score changes, Migrations) ---
                if not q.full():
                    event_mints = await self.db_client.get_tokens_with_recent_events_for_ai_eval(
                        200, 15, self.config.get('AI_REFRESH_INTERVAL_EVENT_MIN', 30)
                    )
                    for mint in event_mints:
                        if q.qsize() < max_q_size:
                            active_pos = await self.db_client.pool.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)
                            context = "SELL/HOLD" if active_pos else "REBUY"
                            # (We will add duplicate check from Solution 2 here)
                            async with self.state.ai_queue_lock:
                                if mint not in self.state.ai_queue_mints:
                                    await q.put((-25, (mint, context)))
                                    self.state.ai_queue_mints.add(mint)
                                    added_count += 1
                        else: 
                            logger.warning("AI Queue became full while adding P3 Event items.")
                            break # Stop adding this category
                    if event_mints: logger.debug(f"🧠 AI Queue: Added {len(event_mints)} event-triggered tokens.")

                # --- Priority 5: General Staleness Refresh ---
                if not q.full():
                    stale_mints = await self.db_client.get_stale_tokens_for_ai_eval(
                         self.config.get('AI_STALE_REFRESH_BATCH_SIZE', 5), self.config.get('AI_REFRESH_INTERVAL_STALE_MIN', 60)
                    )
                    for mint in stale_mints:
                        if q.qsize() < max_q_size:
                            active_pos = await self.db_client.pool.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)
                            context = "SELL/HOLD" if active_pos else "INITIAL BUY"
                            # (We will add duplicate check from Solution 2 here)
                            async with self.state.ai_queue_lock:
                                if mint not in self.state.ai_queue_mints:
                                    await q.put((50, (mint, context)))
                                    self.state.ai_queue_mints.add(mint)
                                    added_count += 1
                        else: 
                            logger.warning("AI Queue became full while adding P5 Stale items.")
                            break # Stop adding this category
                    if stale_mints: logger.debug(f"🧠 AI Queue: Added {len(stale_mints)} stale tokens for refresh.")
                
                # --- [END SOLUTION 1] ---

                if added_count > 0:
                    logger.info(f"🧠 AI Queue Populator added {added_count} tasks. Current size: {q.qsize()}.")

            except asyncio.CancelledError: 
                logger.info("📊 AI Queue Populator task cancelled.")
                break
            except Exception as e: 
                logger.error(f"🚨 Error in AI Queue Populator: {e}", exc_info=True)
            
            await self.state.wait_or_interrupt(timeout=60) # Run once per minute
            
        logger.info("📊 AI Queue Populator shutting down.")

    async def status_updater(self):
        """Periodically updates the bot_status.json file with key metrics."""
        logger.info(":rocket: Status updater task started.")
        while not self.state.shutdown_event.is_set():
            try:
                current_process_status = "RUNNING"
                if self.state.shutdown_event.is_set(): 
                    current_process_status = "STOPPING"
                    
                uptime_seconds = (datetime.now(timezone.utc) - self.bot_start_time).total_seconds()
                active_subs = await self.state.get_token_subscriptions()
                sol_balance = await self.state.get_current_sol_balance()
                sol_price = await self.state.get_sol_price()
                sol_balance_usd = (sol_balance * sol_price) if sol_balance is not None and sol_price is not None else 0.0
                
                ws_summary = {}
                if self.ws_handler: 
                    ws_summary = self.ws_handler.get_status()

                # AI-specific stats
                ai_q_size = -1
                ai_workers_active = -1
                # Check if AI components are active
                if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_semaphore:
                    ai_q_size = self.state.get_ai_evaluation_queue().qsize()
                    max_workers = self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1)
                    # Read semaphore value to see how many workers are "out"
                    active_workers = max_workers - self.ai_semaphore._value 
                    ai_workers_active = active_workers

                status_data = {
                    "bot_process_status": current_process_status, 
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": int(uptime_seconds), 
                    "active_token_subscriptions_count": len(active_subs),
                    "current_sol_balance": round(sol_balance, 6) if sol_balance is not None else None,
                    "current_sol_price_usd": round(sol_price, 4) if sol_price is not None else None,
                    "current_portfolio_value_usd": round(sol_balance_usd, 2),
                    "rugcheck_queue_size": self.state.get_rugcheck_queue().qsize(),
                    "socialscheck_queue_size": self.state.get_socialscheck_queue().qsize(),
                    "ai_evaluation_queue_size": ai_q_size,
                    "ai_workers_active": ai_workers_active,
                    "websocket_summary": ws_summary 
                }
                self._write_status(status_data)
                
                await self.state.wait_or_interrupt(timeout=5) # Update status every 5s
                
            except asyncio.CancelledError:
                logger.info(":stop_sign: Status updater task shutting down.")
                break
            except Exception as e:
                logger.error(f":police_car_light: Error in status updater: {e}", exc_info=True)
                self._write_status({"bot_process_status": "ERROR_IN_STATUS_UPDATER", "error_message": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
                await self.state.wait_or_interrupt(timeout=15)
        
        logger.info("Status updater task finished. Writing final STOPPED status.")
        self._write_status({"bot_process_status": "STOPPED", "timestamp": datetime.now(timezone.utc).isoformat()})

    async def monitor_tasks(self):
        """Periodically logs a rich status panel of all bot components and tasks."""
        try:
            while not self.state.shutdown_event.is_set():
                sol_amount = await self.state.get_current_sol_balance() or 0.0
                sol_price_usd = await self.state.get_sol_price()
                sol_price_str = f"[bold green]${sol_price_usd:.4f}[/bold green]" if sol_price_usd else "[bold red]N/A[/red]"
                uptime = str(timedelta(seconds=int((datetime.now(timezone.utc) - self.bot_start_time).total_seconds())))
                open_trades_str = f"[yellow]{len(await self.db_client.get_active_buy_positions())}[/yellow]" if self.db_client and self.db_client.pool else "[dim]N/A[/dim]"

                # WebSocket Status
                ws_lines = []
                if self.ws_handler:
                    summary = self.ws_handler.get_status()
                    status = summary.get("connection_status", "Error")
                    style = "green" if status == "Connected" else "yellow" if status == "Reconnecting" else "red"
                    time_since = summary.get("time_since_last_message_s", -1)
                    if isinstance(time_since, (int, float)) and time_since > 60: 
                        status += f" (Stale: {time_since:.0f}s)"
                        style = "red" # Mark stale as red
                    ws_lines.append(f"[bold cyan]│[/bold cyan] :electric_plug: [bold]Websocket:[/bold] [{style}]{status}[/{style}]")
                    ws_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]NewToken Stream:[/bold] [{'green' if summary.get('new_token_subscribed') else 'red'}]Subscribed[/]")
                    ws_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]Migration Stream:[/bold] [{'green' if summary.get('migration_subscribed') else 'red'}]Subscribed[/]")
                    ws_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Token Trades Subbed:[/bold] [magenta]{summary.get('trade_subscriptions_count', 0)}[/magenta]")
                    next_run = await self.state.get_ws_refresh_next_run_ts()
                    if next_run:
                        remaining = (next_run - datetime.now(timezone.utc)).total_seconds() / 60
                        timer = f"[yellow]{remaining:.1f} min[/yellow]" if remaining > 0 else "[yellow]Soon.[/yellow]"
                    else: 
                        timer = "[green]In Progress.[/green]"
                    ws_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Next WS Refresh:[/bold] {timer}")

                # --- MODIFIED AI Status ---
                ai_lines = []
                ai_enabled = self.config.get('AI_DECISION_MAKING_ENABLED', False)
                ai_status_color = "green" if ai_enabled else "red"
                ai_status_text = "ENABLED" if ai_enabled else "DISABLED"
                
                ai_model_name_str = ""
                # Only show model name if AI is enabled AND the maker is initialized
                if ai_enabled and self.ai_decision_maker:
                    model_name = self.config.get('AI_MODEL_NAME', 'N/A')
                    ai_model_name_str = f" [dim](Model: {model_name})[/dim]"

                ai_lines.append(f"[bold cyan]│[/bold cyan] :brain: [bold]AI Status:[/bold] [bold {ai_status_color}]{ai_status_text}[/bold {ai_status_color}]{ai_model_name_str}")
                
                if ai_enabled and self.ai_semaphore:
                    max_workers = self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1)
                    active_workers = max_workers - self.ai_semaphore._value 
                    ai_q_size = self.state.get_ai_evaluation_queue().qsize()
                    
                    ai_lines.extend([
                        f"[bold cyan]│  ├─ [/bold cyan][bold]AI Queue:[/bold] [blue]{ai_q_size}[/blue]",
                        f"[bold cyan]│  └─ [/bold cyan][bold]Active Workers:[/bold] [magenta]{active_workers}/{max_workers}[/magenta]",
                    ])
                # --- END MODIFIED AI Status ---

                # Task Status
                task_lines = []
                active_count = 0
                # --- MODIFIED: Show all tasks, including dynamic AI tasks ---
                all_tasks = self.tasks # self.tasks is now dynamically updated
                for task in all_tasks:
                    if not task: continue # Skip if a task handle is None
                    name = task.get_name()
                    status = "running"
                    style = "green"
                    if task.done(): 
                        status = "error" if task.exception() else "done"
                        style = "red"
                    else: 
                        active_count += 1
                    task_lines.append(f"[bold cyan]├──[/bold cyan] {name}: [bold {style}]{status}[/bold {style}]")

                # Assemble Log Panel
                log_parts = [
                    "\n[bold cyan]┌────────────────────────────────────[/bold cyan]",
                    "[bold cyan]│[/bold cyan] :robot: [bold magenta]Task Monitor[/bold magenta]",
                    "[bold cyan]│────────────────────────────────────[/bold cyan]",
                    f"[bold cyan]│[/bold cyan] :moneybag: [bold]SOL Balance:[/bold] {sol_amount:.4f}",
                    f"[bold cyan]│[/bold cyan] :timer_clock:  [bold]Uptime:[/bold]  {uptime}",
                    f"[bold cyan]│[/bold cyan] :heavy_dollar_sign: [bold]Actual SOL Price:[/bold] {sol_price_str}",
                    f"[bold cyan]│[/bold cyan] :bar_chart: [bold]Open Trades:[/bold] {open_trades_str}",
                    f"[bold cyan]│[/bold cyan] :recycle: [bold]RugCheck Queue:[/bold] [blue]{self.state.get_rugcheck_queue().qsize()}[/blue]",
                    f"[bold cyan]│[/bold cyan] :speech_balloon: [bold]Socials Queue:[/bold] [blue]{self.state.get_socialscheck_queue().qsize()}[/blue]",
                    *ai_lines,
                    *ws_lines,
                    f"[bold cyan]│[/bold cyan] :gear: [bold]Managed Tasks:[/bold] {active_count}/{len(all_tasks)}",
                    "[bold cyan]│[/bold cyan] :clipboard: [bold]Tasks:[/bold]",
                    *task_lines,
                    "[bold cyan]└────────────────────────────────────[/bold cyan]"
                ]
                logger.debug("\n".join(log_parts))
                
                await self.state.wait_or_interrupt(timeout=self.config.get('MONITOR_TASK_INTERVAL_SECONDS', 30))
                
        except asyncio.CancelledError:
            logger.info(":stop_sign: Monitor task shutting down.")
        except Exception as e:
            logger.error(f":police_car_light: [bold red]FATAL error in Monitor task[/bold red]: {e}", exc_info=True)

    async def command_listener(self):
        """Listens for commands (e.g., 'STOP') from the main.py controller via a file."""
        last_command = None
        while not self.state.shutdown_event.is_set():
            try:
                if os.path.exists(COMMAND_FILE):
                    with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                        command = f.read().strip()
                    
                    if command and command != last_command:
                        logger.info(f"Received command: '{command}'")
                        last_command = command
                        
                        # --- Process Commands ---
                        if command.upper() == "RESTART_WEBSOCKET":
                            if self.ws_handler: 
                                # Call start() on the handler; its internal supervisor will handle
                                # the reconnection logic.
                                self.ws_handler.start()
                                logger.info("WebSocket restart initiated by command.")
                        elif command.upper() == "STOP": 
                            self.state.trigger_shutdown()
                        elif command.upper() == "STOP_BUYING": 
                            self.state.is_buying_enabled = False
                            logger.info("Buying has been disabled by command.")
                        elif command.upper() == "START_BUYING": 
                            self.state.is_buying_enabled = True
                            logger.info("Buying has been enabled by command.")
                        elif command.upper() == "SELL_ALL_IMMEDIATELY": 
                            if self.trading_manager:
                                asyncio.create_task(self.trading_manager.execute_manual_sell_all())
                        elif command.upper().startswith("SELL_"): 
                            mint = command[len("SELL_"):]
                            if self.trading_manager:
                                asyncio.create_task(self.trading_manager.execute_manual_sell(mint))
                        
                        # Clear the command file after processing
                        with open(COMMAND_FILE, 'w') as f: f.write("")
                        
                await self.state.wait_or_interrupt(timeout=5) # Poll for command every 5s
                
            except asyncio.CancelledError: 
                logger.info(":stop_sign: Command listener task shutting down."); 
                break
            except Exception as e: 
                logger.error(f":police_car_light: Error in command listener: {e}", exc_info=True)
    
    async def shutdown(self):
        """Performs a graceful shutdown of all bot components."""
        if getattr(self, '_shutdown_called', False): 
            return # Shutdown already in progress
        self._shutdown_called = True
        
        logger.info(":stop_button: [bold red]Shutdown initiated[/bold red]...")
        self.state.trigger_shutdown() # Signal all tasks to stop
        
        # --- Explicitly stop dynamic services first ---
        logger.info("Shutting down AI services...")
        await self.stop_ai_services()

        logger.info("Shutting down WebSocket handler...")
        if self.ws_handler: 
            await self.ws_handler.shutdown()
            
        logger.info("Cancelling all remaining tasks...")
        for task in self.tasks: 
            if task and not task.done():
                task.cancel()
                
        # Wait for all tasks to acknowledge cancellation
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        if self.db_client and self.db_client.pool:
            await self.db_client.close()
            
        logger.info(":checkered_flag: Bot shutdown complete.")

    async def run_vector_index_maintenance(self):
        """Periodically runs VACUUM ANALYZE on the AI memory table."""
        await self.state.wait_or_interrupt(timeout=300) # Wait 5 mins after startup
        logger.info("🔧 Vector Index Maintenance task started.")
        
        while not self.state.shutdown_event.is_set():
            try:
                logger.info("🔧 Starting periodic VACUUM ANALYZE on ai_decision_memory...")
                async with self.db_client.pool.acquire() as conn:
                    # Set a statement timeout (e.g., 10 minutes)
                    await conn.execute("SET statement_timeout = 600000;")
                    await conn.execute("VACUUM ANALYZE ai_decision_memory;")
                    await conn.execute("RESET statement_timeout;")
                logger.info("🔧 Vector index maintenance complete.")
                
                # Run every 6 hours
                await self.state.wait_or_interrupt(timeout=(6 * 60 * 60)) 
            
            except asyncio.CancelledError:
                logger.info("🔧 Vector Index Maintenance task cancelled.")
                break
            except Exception as e:
                logger.error(f":police_car_light: Error in vector index maintenance: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=1800) # Wait 1 hour on error
        
        logger.info("🔧 Vector Index Maintenance task shutting down.")

    async def ai_outcome_monitor_task(self):
        """
        [REFACTORED V2]
        Periodically checks for outcomes (rugs, moons) of tokens the
        AI evaluated but the bot did not purchase.
        - Now writes a full, labeled case study to `market_knowledge_base`.
        """
        await self.state.wait_or_interrupt(timeout=600) # Wait 10 mins after startup
        logger.info("🧠 AI Outcome Monitor task started.")

        while not self.state.shutdown_event.is_set():
            try:
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False):
                    await self.state.wait_or_interrupt(timeout=1800)
                    continue

                logger.debug("🧠 AI Outcome Monitor: Checking for non-trade outcomes...")
                async with self.db_client.pool.acquire() as conn:
                    tokens_to_check = await self.db_client.get_tokens_for_outcome_analysis(lookback_hours=24, conn=conn)
                    if not tokens_to_check:
                        logger.debug("🧠 AI Outcome Monitor: No new non-portfolio tokens to analyze.")
                        await self.state.wait_or_interrupt(timeout=1800)
                        continue

                    logger.info(f"🧠 AI Outcome Monitor: Found {len(tokens_to_check)} tokens to analyze for outcomes.")
                    
                    for record in tokens_to_check:
                        mint = record['mint']
                        last_decision = record['decision']
                        last_decision_ts = record['evaluation_timestamp']
                        last_metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                        price_at_decision = last_metadata.get('price', 0.0)

                        outcome_label = None
                        outcome_reason = None
                        outcome_timestamp = None
                        current_price = None

                        rugged_record = await conn.fetchrow(
                            "SELECT backup_reason, backup_timestamp FROM tokens_backup WHERE mint = $1 AND backup_reason IN ('high_rugcheckscore', 'dead_token')",
                            mint
                        )
                        
                        if rugged_record:
                            outcome_label = "DODGED_BULLET (RUGGED)"
                            outcome_reason = rugged_record['backup_reason']
                            outcome_timestamp = ensure_datetime(rugged_record['backup_timestamp'])
                        else:
                            price_data = await self.db_client.get_price_and_market_cap_for_decision(mint, self.config, conn)
                            current_price = price_data.get('price')
                            
                            if current_price and price_at_decision > 0:
                                price_multiplier = current_price / price_at_decision
                                if price_multiplier >= 10.0:
                                    outcome_label = "MISSED_OPPORTUNITY (MOON)"
                                    outcome_reason = f"{price_multiplier:.0f}x price increase"
                                    outcome_timestamp = datetime.now(timezone.utc)
                        
                        # If we found a definitive outcome, log it to both RAG tables
                        if outcome_label and self.ai_decision_maker:
                            logger.info(f"🧠 AI Outcome: Logging '{outcome_label}' for {mint}.")
                            
                            # --- [START NEW LOGIC: Build full case study] ---
                            
                            # 1. Get token creation info
                            token_info = await conn.fetchrow("SELECT traderpublickey, timestamp FROM v_tokens WHERE mint = $1 LIMIT 1", mint)
                            if not token_info:
                                logger.warning(f"Could not find token info for {mint} to build outcome case study.")
                                continue
                            
                            creator_wallet = token_info['traderpublickey']
                            token_creation_ts = ensure_datetime(token_info['timestamp'])

                            # 2. Get full historical metrics
                            peak_data = await conn.fetchrow(
                                f"""SELECT
                                       MAX(price_sol) as max_price_sol,
                                       MAX(market_cap_sol) as max_mcap_sol,
                                       (array_agg(timestamp ORDER BY price_sol DESC))[1] as max_price_ts
                                   FROM v_unified_market_ticks_historical
                                   WHERE mint = $1 AND price_sol > 0
                                """, mint
                            )
                            max_price_sol, max_mcap_sol, max_price_ts, time_to_peak_minutes = None, None, None, None
                            if peak_data and peak_data['max_price_sol'] and peak_data['max_price_ts']:
                                max_price_sol = float(peak_data['max_price_sol'])
                                max_mcap_sol = float(peak_data['max_mcap_sol'])
                                max_price_ts = ensure_datetime(peak_data['max_price_ts'])
                                time_to_peak_minutes = (max_price_ts - token_creation_ts).total_seconds() / 60

                            # 3. Get creator summary
                            creator_history_summary, creator_summary_dict = await self.db_client.get_creator_history_summary(creator_wallet, mint)

                            # 4. Build the RAG snapshot for ai_decision_memory (the "why")
                            outcome_snapshot = {
                                "mint": mint, "source": last_metadata.get('source', 'PUMP'), "timestamp": outcome_timestamp.isoformat(),
                                "decision_context": "NON_TRADE_OUTCOME",
                                "market_cap": 0, "volatility": 0, "token_age_minutes": last_metadata.get('token_age_minutes', 0),
                                "creator_history_summary": creator_history_summary,
                                **creator_summary_dict,
                                "uri_status": last_metadata.get('uri_status', 'N/A'),
                                "market_dynamics_summary_str": f"Token outcome: {outcome_reason}",
                                "trade_history_summary": "No trades by bot.",
                                "max_price_sol": max_price_sol, "time_to_peak_minutes": time_to_peak_minutes
                            }
                            outcome_decision = {
                                "decision": outcome_label, "confidence": 100, # This was an actual event
                                "explanation": f"AI previously decided '{last_decision}' at {last_decision_ts.isoformat()}.\n"
                                             f"Token's final outcome was: {outcome_reason} at {outcome_timestamp.isoformat()}.\n"
                                             f"This was a {'correct' if 'DODGED' in outcome_label else 'incorrect'} non-action."
                            }
                            
                            await self.ai_decision_maker.add_decision_snapshot_to_memory(outcome_snapshot, outcome_decision)
                            
                            # 5. Build the case study for market_knowledge_base (the "what")
                            market_summary_str = (
                                f"Case Study: Token {mint} by creator {creator_wallet}.\n"
                                f"Outcome: {outcome_reason} (Label: {outcome_label}).\n"
                                f"Creator History: {creator_history_summary}\n"
                                f"Metrics: Max MCap: {max_mcap_sol or 'N/A'} SOL (at {time_to_peak_minutes:.1f} mins)"
                            )
                            market_metadata_dict = {
                                "creator": creator_wallet,
                                "reason": outcome_reason,
                                "label": outcome_label,
                                "max_mcap": float(max_mcap_sol) if max_mcap_sol else None,
                                "max_price": float(max_price_sol) if max_price_sol else None,
                                "max_price_ts": max_price_ts.isoformat() if max_price_ts else None,
                                "time_to_peak_minutes": float(time_to_peak_minutes) if time_to_peak_minutes else None,
                                **creator_summary_dict
                            }
                            
                            market_embedding = await self.ai_decision_maker.embed_text(market_summary_str)
                            if market_embedding:
                                await conn.execute(
                                    """
                                    INSERT INTO market_knowledge_base (mint, summary, embedding, metadata) 
                                    VALUES ($1, $2, $3, $4) 
                                    ON CONFLICT(mint) DO UPDATE SET
                                        summary = EXCLUDED.summary,
                                        embedding = EXCLUDED.embedding,
                                        metadata = EXCLUDED.metadata,
                                        created_at = NOW();
                                    """,
                                    mint, market_summary_str, str(market_embedding), json.dumps(market_metadata_dict)
                                )
                                logger.debug(f"📚 Knowledge Base: Added new case study for {mint} from outcome monitor.")
                            # --- [END NEW LOGIC] ---

            except asyncio.CancelledError:
                logger.info("🧠 AI Outcome Monitor task cancelled.")
                break
            except Exception as e:
                logger.error(f":police_car_light: Error in AI Outcome Monitor: {e}", exc_info=True)
            
            await self.state.wait_or_interrupt(timeout=1800)
        
        logger.info("🧠 AI Outcome Monitor task shutting down.")

    async def main(self):
        """The main entry point for the bot's asynchronous execution."""
        self.loop = asyncio.get_running_loop()
        
        # --- 1. Setup Logging & Signals ---
        if threading.current_thread() is threading.main_thread():
            if not self.no_log_rotate:
                rotate_log_file()
            self.register_signal_handlers()
        
        setup_logging()
        
        try:
            # --- 2. Initialize Database ---
            self.db_client = DatabaseClient(config_dict=self.config)
            await self.db_client.connect()
            await self.state.set_db_client(self.db_client)
            
            # --- 3. Handle DB Maintenance Flags ---
            if self.backup: 
                await self.db_client.backup_db(True)
            if self.cleanup: 
                await self.db_client.cleanup_db(True)
                
        except Exception as db_err:
            logger.critical(f"CRITICAL: Failed database setup: {db_err}", exc_info=True)
            self._write_status({"bot_process_status": "ERROR_DB_SETUP", "error_message": str(db_err), "timestamp": datetime.now(timezone.utc).isoformat()})
            return        

        # --- 4. Fetch Initial Price ---
        if not await self._fetch_initial_sol_price():
            logger.critical("🔴 Failed to fetch initial SOL price. Functionality may be limited.")

        # --- 5. Start AI Services (if enabled) ---
        if self.config.get('AI_DECISION_MAKING_ENABLED', False):
            logger.info("Initial config is set to ENABLE AI. Starting services...")
            await self.start_ai_services() # This now populates self.ai_decision_maker
        else:
            logger.info("🧠 AI Decision Making is DISABLED by initial configuration.")

        # --- 6. Initialize Core Components ---
        self.ws_handler = WebSocketHandler(self.db_client, self.state, self.config)
        await self.state.set_websocket_handler(self.ws_handler)
        self.socials_proc = SocialsProcessor(state=self.state, db_client=self.db_client, config_dict=self.config)
        
        # Pass the (potentially None) ai_decision_maker instance to TradingManager
        self.trading_manager = TradingManager(
            db_client=self.db_client, 
            config_dict=self.config, 
            state=self.state,
            ai_decision_maker=self.ai_decision_maker 
        )

        self.dexscreener_fetcher = DexscreenerFetcher(state=self.state, db_client=self.db_client)
        self.rugchecker = Rugcheck(
            state=self.state, db_client=self.db_client,
            websocket_handler=self.ws_handler, 
            socials_processor=self.socials_proc,
            config_dict=self.config
        )

        # --- 7. Start WebSocket and All Tasks ---
        self.ws_handler.start()

        # self.tasks now only contains non-AI tasks
        self.tasks = [
            asyncio.create_task(self.status_updater(), name="status_updater"),
            asyncio.create_task(self.config_updater(), name="config_updater"),
            asyncio.create_task(self.command_listener(), name="command_listener"),
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"),
            asyncio.create_task(update_sol_price(self.state, self.db_client), name="sol_price_updater"),
            asyncio.create_task(trade_worker(self.ws_handler.trade_queue), name="trade_worker"),
            asyncio.create_task(self.dexscreener_fetcher.run(), name="dexscreener_fetcher"),
            *self.socials_proc.start(),
            asyncio.create_task(self.run_buy_checks(), name="buy_opportunity_checker"),
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker"),
            asyncio.create_task(self.run_heartbeat_emitter(), name="heartbeat_emitter"),
            self.rugchecker.start(),
        ]
        
        logger.info(":rocket: [bold green]Trading bot core components started.[/bold green]")
        
        # --- 8. Run Until Shutdown ---
        try:
            await self.state.wait_for_shutdown()
        except Exception as e:
            logger.critical(f":police_car_light: CRITICAL ERROR in bot's main execution: {e}", exc_info=True)
            self.state.trigger_shutdown()
        finally:
            logger.info("Main execution loop ended. Proceeding to full shutdown.")

    async def run_heartbeat_emitter(self):
        """Emits a periodic 'heartbeat' to the database to monitor bot liveness."""
        logger.debug("❤️ Heartbeat emitter started.")
        try:
            if self.db_client: await self.db_client.insert_heartbeat(event_type="STARTUP")
        except Exception as e:
            logger.error(f":police_car_light: Error in heartbeat emitter startup: {e}", exc_info=True)
            
        while not self.state.shutdown_event.is_set():
            try:
                if self.db_client: await self.db_client.insert_heartbeat()
                await self.state.wait_or_interrupt(timeout=self.config.get('HEARTBEAT_EMIT_INTERVAL_SECONDS', 60))
            except asyncio.CancelledError: 
                break
            except Exception as e:
                logger.error(f":police_car_light: Error in heartbeat emitter: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=60)

    async def run_buy_checks(self):
        """Periodically runs the logic to check for new buy opportunities."""
        logger.info(":chart_with_upwards_trend: [bold]Starting buy opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: 
                    await self.trading_manager.check_trading_opportunities()
                await self.state.wait_or_interrupt(timeout=self.config.get('BUY_CHECK_INTERVAL', 10))
            except asyncio.CancelledError: 
                break
            except Exception as e:
                logger.error(f":police_car_light: Error in buy checker loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=30)

    async def run_sell_checks(self):
        """Periodically runs the logic to manage and sell active positions."""
        logger.info(":chart_with_downwards_trend: [bold]Starting sell opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: 
                    await self.trading_manager.check_sell_opportunities()
                await self.state.wait_or_interrupt(timeout=self.config.get('SELL_CHECK_INTERVAL', 3))
            except asyncio.CancelledError: 
                break
            except Exception as e:
                logger.error(f":police_car_light: Error in sell checker loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=12)

# --- Main Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting.")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file with GA parameters.")
    parser.add_argument("--no-log-rotate", action="store_true", help="Disable log rotation (used by main.py).")
    # --- NEW: Add --rl-agent-path argument ---
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")

    args = parser.parse_args()

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    bot_instance = None
    async def run_bot_async_wrapper():
        """Async wrapper to create, run, and shut down the bot instance."""
        global bot_instance
        bot_instance = TradingBot(
            cleanup=args.cleanup, 
            backup=args.backup, 
            params_file=args.params_file, 
            no_log_rotate=args.no_log_rotate
        )
        try:
            await bot_instance.main()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Interrupted. Triggering shutdown...")
            if bot_instance and not bot_instance.state.shutdown_event.is_set():
                bot_instance.state.trigger_shutdown()
        except Exception as e:
            logger.critical(f":police_car_light: Unexpected error in bot's main execution: {e}", exc_info=True)
            if bot_instance and not bot_instance.state.shutdown_event.is_set():
                 bot_instance.state.trigger_shutdown()
        finally:
            if bot_instance:
                await bot_instance.shutdown()

    try:
        asyncio.run(run_bot_async_wrapper())
    except KeyboardInterrupt:
        logger.info("Top-level KeyboardInterrupt.")
    finally:
        logger.info("Trading Bot script finished.")
```

#### 📄 `trading_logic.py`
*path: `trading_logic.py`*

```python
# path: trading_logic.py

"""
Handles trading logic including buy/sell decision making,
emergency sell triggers, and portfolio management, supporting multiple trading modes.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
from typing import Optional, Dict, Any

from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState
from utils import (
    play_buy_opportunity_sound, play_sell_sl_sound_async, play_sell_tp_sound_async,
    format_buy_order_log, format_sell_order_log, calculate_trend_indicators
)
from connectors.live_trader_pumpportal import execute_live_pumpportal_trade
from telegram_interface import send_telegram_message

# --- ADD THIS IMPORT ---
from ai_decision_module.ai_decision_maker import AIDecisionMaker

# --- HELPER FUNCTIONS FOR LOGGING (Unchanged) ---
def format_price_for_log(price):
    if price is None: return "N/A"
    if price == 0: return "0.0"
    if abs(price) < 1e-4 or abs(price) >= 1e6: return f"{price:.2e}"
    else: return f"{price:.9f}".rstrip('0').rstrip('.')

def format_pnl_value(value):
    if value < 0: return f"[red]{value:+.4f} SOL[/red]"
    else: return f"{value:+.4f} SOL"

def format_profit_pct(pct):
    if pct < 0: return f"[red]({pct:+.2f}%)[/red]"
    else: return f"({pct:+.2f}%)"
# --- END HELPER FUNCTIONS ---

class TradingManager:
    # --- MODIFIED __init__ ---
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state: GlobalState, ai_decision_maker: Optional[AIDecisionMaker] = None):
        self.db = db_client
        self.config = config_dict
        self.state = state
        # --- ADD THIS LINE ---
        self.ai_decision_maker = ai_decision_maker
    # --- END MODIFICATION ---

    def get_adaptive_atr_multiplier(self, rsi_value: float) -> float:
        """ Returns an ATR multiplier based on the current RSI momentum. (Unchanged) """
        if rsi_value >= self.config['ADAPTIVE_RSI_EXTREME_LEVEL']:
            return self.config['ADAPTIVE_ATR_EXTREME_MULTIPLIER']
        elif rsi_value >= self.config['ADAPTIVE_RSI_STRONG_LEVEL']:
            return self.config['ADAPTIVE_ATR_STRONG_MULTIPLIER']
        else:
            return self.config['ADAPTIVE_ATR_BASE_MULTIPLIER']

    async def _is_trend_reversal_confirmed(self, mint: str) -> bool:
        """
        Checks if a token that was recently stopped out shows signs of a trend reversal. (Unchanged)
        """
        if not self.config.get('USE_TREND_REVERSAL_CONFIRMATION', False):
            return True

        async with self.db.pool.acquire() as conn:
            token_record = await conn.fetchrow("""
                SELECT t.data_source, p.reason, p.timestamp
                FROM tokens t
                LEFT JOIN (
                    SELECT mint, reason, timestamp, ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                    FROM portfolio WHERE tx_type = 'sell'
                ) p ON t.mint = p.mint AND p.rn = 1
                WHERE t.mint = $1;
            """, mint)

        if not token_record:
            logger.warning(f":triangular_flag: Could not find token record for {mint} during trend reversal check.")
            return True

        last_sell_reason = token_record['reason']
        last_sell_timestamp = token_record['timestamp']

        if not last_sell_reason or not last_sell_timestamp:
            return True

        apply_reversal_on_reasons = self.config.get('APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
        recency_hours = self.config.get('TREND_REVERSAL_RECENCY_HOURS', 6)

        is_relevant_reason = any(reason_str in last_sell_reason for reason_str in apply_reversal_on_reasons)
        is_recent = (datetime.now(timezone.utc) - last_sell_timestamp.astimezone(timezone.utc)) < timedelta(hours=recency_hours)

        if not (is_relevant_reason and is_recent):
            logger.debug(f":thumbs_up: Trend reversal check not required for {mint} (Reason: '{last_sell_reason}', IsRecent: {is_recent}).")
            return True

        data_source = token_record['data_source']

        if data_source == 'DEXSCREENER':
            logger.info(f"Token {mint} is migrated. Performing DexScreener snapshot-based trend reversal check...")
            async with self.db.pool.acquire() as conn:
                snapshots = await self.db.analyze_dexscreener_trend(
                    mint,
                    self.config['DEX_REVERSAL_LOOKBACK_MINUTES'],
                    conn
                )

            if len(snapshots) < self.config['DEX_REVERSAL_MIN_SNAPSHOTS']:
                logger.info(f":triangular_flag: DEX Reversal FAILED for {mint}: Not enough recent data points (have {len(snapshots)}, need {self.config['DEX_REVERSAL_MIN_SNAPSHOTS']}).")
                return False

            latest_snapshot = snapshots[0]
            min_liquidity_usd = self.config['DEX_REVERSAL_MIN_LIQUIDITY_USD']
            if float(latest_snapshot['liquidity_usd']) < min_liquidity_usd:
                logger.info(f":thumbs_down: DEX Reversal FAILED for {mint}: Liquidity (${latest_snapshot['liquidity_usd']:.2f}) is below threshold (${min_liquidity_usd:.2f}).")
                return False

            strong_buy_pressure_count = 0
            for snap in snapshots:
                buys = snap['buys_m5']
                sells = snap['sells_m5']
                if buys > 0 and (sells == 0 or (buys / sells) >= self.config['DEX_REVERSAL_MIN_BUY_SELL_RATIO']):
                    strong_buy_pressure_count += 1

            logger.debug(f":bookmark: DEX Reversal analysis for {mint}: Strong Buy Pressure Signals={strong_buy_pressure_count} found in the last {len(snapshots)} snapshots.")

            min_confirmations = self.config['DEX_REVERSAL_MIN_CONFIRMATIONS']
            if strong_buy_pressure_count >= min_confirmations:
                logger.info(f":bookmark: DEXScreener Trend Reversal CONFIRMED for {mint}. Strong buy pressure found in {strong_buy_pressure_count}/{len(snapshots)} recent snapshots.")
                return True
            else:
                logger.info(f":thumbs_down: DEX Reversal FAILED for {mint}: Not enough confirmations of strong buying pressure (have {strong_buy_pressure_count}, need {min_confirmations}).")
                return False

        elif data_source == 'PUMP':
            logger.info(f"Token {mint} is on Pump.fun. Performing indicator-based trend reversal check...")
            start_date_hist = datetime.now(timezone.utc) - timedelta(hours=self.config.get('INDICATOR_LOOKBACK_HOURS', 1))
            end_date_hist = datetime.now(timezone.utc)
            historical_data = await self.db.get_historical_data_for_backtesting([mint], start_date_hist, end_date_hist)

            if not historical_data or mint not in historical_data:
                return False

            df = historical_data[mint]
            df_with_indicators = calculate_trend_indicators(df, self.config)

            if df_with_indicators.empty or len(df_with_indicators) < self.config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30):
                return False

            latest = df_with_indicators.iloc[-1]
            previous = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else latest

            stage1_passed = False
            rsi_neutral_level = self.config.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 45)
            rsi_val = latest.get('RSI', float('nan'))
            bb_lower_band = latest.get(f"BBL_{self.config['BBANDS_PERIOD']}_{self.config['BBANDS_STD_DEV']}", float('inf'))

            if (rsi_val > 30 and previous.get('RSI', float('nan')) <= 30) or \
            (latest.get('Close', 0) > bb_lower_band and previous.get('Close', 0) <= previous.get(f"BBL_{self.config['BBANDS_PERIOD']}_{self.config['BBANDS_STD_DEV']}", float('inf'))):
                stage1_passed = True
            elif rsi_val > rsi_neutral_level:
                stage1_passed = True

            if not stage1_passed:
                return False

            is_above_vwap = latest.get('Close', 0) > latest.get('VWAP', float('-inf'))
            is_ema_bullish = latest.get('EMA_fast', float('-inf')) > latest.get('EMA_slow', float('inf'))

            if is_above_vwap and is_ema_bullish:
                logger.info(f":thumbs_up: Pump.fun Trend Reversal Fully Confirmed for {mint}!")
                return True
            else:
                return False
                
        else:
            logger.warning(f":triangular_flag: Unknown data_source '{data_source}' for {mint} in trend reversal check.")
            return False

    async def _get_valid_ai_advice(self, mint: str) -> (Optional[str], int, Optional[dict]):
        """
        Fetches the latest, non-stale, actionable AI advice for a mint.

        Returns:
            Tuple[Optional[str], int, Optional[dict]]:
                - decision (e.g., 'BUY', 'SELL', 'HOLD') or None if no valid advice
                - confidence (0-100)
                - ai_context_for_log (a dict for logging) or None
        """
        if not self.config.get('AI_DECISION_MAKING_ENABLED', False) or not self.ai_decision_maker:
            return None, 0, None

        async with self.db.pool.acquire() as conn_ai:
            # This function now correctly fetches only actionable advice
            ai_decision_record = await self.db.get_latest_ai_decision(mint, conn_ai)

        if not ai_decision_record:
            logger.debug(f"🧠 AI advice for {mint} buy check unavailable. Using rule-based logic only.")
            return None, 0, None

        ai_decision = ai_decision_record['decision']
        ai_confidence = ai_decision_record['confidence']
        ai_timestamp = ai_decision_record['evaluation_timestamp']
        advice_age = datetime.now(timezone.utc) - ai_timestamp
        max_staleness = timedelta(minutes=self.config.get('AI_ADVICE_MAX_STALENESS_MINUTES', 20))

        if advice_age > max_staleness:
            logger.debug(f"🧠 AI advice for {mint} is stale (Age: {advice_age.total_seconds():.0f}s > {max_staleness.total_seconds():.0f}s). Ignoring.")
            return None, 0, None

        # Valid, non-stale advice found
        ai_context_for_log = {'decision': ai_decision, 'confidence': ai_confidence, 'timestamp': ai_timestamp.isoformat()}
        logger.debug(f"🧠 AI Advice ({mint}): {ai_decision} ({ai_confidence}%) - Age: {advice_age.total_seconds():.0f}s")
        
        return ai_decision, ai_confidence, ai_context_for_log

    async def _evaluate_buy_opportunity(self, row: dict) -> (Optional[str], Optional[dict]):
        """
        Evaluates a single potential buy opportunity, checking all vetos.

        Args:
            row (dict): The data row from find_trading_opportunities.

        Returns:
            Tuple[Optional[str], Optional[dict]]:
                - buy_reason (str) or None if vetoed
                - ai_context (dict) or None
        """
        mint = row['mint']
        opportunity_price = float(row['latest_price'])

        if opportunity_price <= 0:
            logger.warning(f"Skipping buy for {mint} due to invalid opportunity price: {opportunity_price}")
            return None, None

        buy_reason = "Rule-Based"  # Default reason
        ai_decision, ai_confidence, ai_context_for_log = await self._get_valid_ai_advice(mint)

        if ai_decision:
            # --- AI VETO LOGIC ---
            
            # Veto 1: Check for a confident HOLD decision
            hold_veto_threshold = self.config.get('AI_BUY_HOLD_CONFIDENCE_THRESHOLD', 60)
            if ai_decision == 'HOLD' and ai_confidence >= hold_veto_threshold:
                logger.info(f"🧠 AI advised HOLD (Confidence: {ai_confidence} >= {hold_veto_threshold}) for potential buy of {mint}. Deferring purchase.")
                return None, None

            # Veto 2: Check for a confident SELL decision (Fixes the instant sell-after-buy bug)
            sell_veto_threshold = self.config.get('AI_CONFIDENCE_THRESHOLD_VETO', 75)
            if ai_decision == 'SELL' and ai_confidence >= sell_veto_threshold:
                logger.info(f"🧠 AI advised SELL (Confidence: {ai_confidence} >= {sell_veto_threshold}) for potential buy of {mint}. Vetoing purchase.")
                return None, None
            
            # --- AI CONFIRMATION LOGIC ---
            if ai_decision.upper() in ['BUY', 'REBUY']:
                logger.debug(f"🧠 AI confirmed potential BUY for {mint} (Confidence: {ai_confidence}).")
                buy_reason = "AI-Advised"

        # --- TREND REVERSAL VETO LOGIC ---
        if self.config.get('USE_TREND_REVERSAL_CONFIRMATION', False):
            if not await self._is_trend_reversal_confirmed(mint):
                logger.debug(f"Trend reversal not confirmed for {mint}. Skipping buy opportunity.")
                return None, None
        
        # All checks passed
        return buy_reason, ai_context_for_log

    async def check_trading_opportunities(self):
        """
        ✅ [REFACTORED]
        Checks for new trading opportunities by getting rule-based candidates
        and then evaluating each one.
        """
        if self.state.shutdown_event.is_set():
            return

        if not self.state.is_buying_enabled:
            logger.debug(":closed_lock_with_key: Buying is currently disabled by command. Skipping buy checks.")
            return

        try:
            sol_price_usd = await self.state.get_sol_price()
            if sol_price_usd is None or sol_price_usd <= 0:
                logger.warning(f"⚠️ Invalid SOL_PRICE_USD ({sol_price_usd}); skipping buy check.")
                return

            # 1. Get all rule-based opportunities
            rows = await self.db.find_trading_opportunities(
                sol_price=sol_price_usd,
                volume_threshold=self.config['DEFAULT_VOLUME_THRESHOLD'],
                marketcap_threshold=self.config['DEFAULT_MARKETCAP_THRESHOLD'],
                rugcheck_threshold=self.config['DEFAULT_RUGCHECK_SCORE_THRESHOLD'],
                social_score_threshold=self.config['DEFAULT_SOCIAL_SCORE_THRESHOLD'],
                time_interval_minutes=self.config['DEFAULT_TIME_INTERVAL'],
                min_volatility=self.config['MIN_VOLATILITY']
            )

            if rows:
                logger.debug(f":magnifying_glass_tilted_right: Found {len(rows)} potential trading opportunities after initial DB filter.")

            # 2. Evaluate each opportunity one by one
            for row in rows:
                mint = row['mint']
                opportunity_price = float(row['latest_price'])
                opportunity_market_cap_sol = float(row['latest_market_cap_sol'])

                # 3. Check all vetos (AI, Trend, etc.)
                buy_reason, ai_context = await self._evaluate_buy_opportunity(row)
                
                # 4. If all checks pass (buy_reason is not None), then execute the buy
                if buy_reason:
                    await self.execute_buy(
                        mint, 
                        opportunity_price, 
                        opportunity_market_cap_sol, 
                        buy_reason, 
                        ai_context
                    )
                    await asyncio.sleep(0.1) # Brief pause between buys

        except Exception as e:
            logger.error(f"❌ Error in check_trading_opportunities: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def execute_buy(self, mint: str, trigger_price: float, market_cap_sol_at_trigger: float, buy_reason: str, ai_context: Optional[dict] = None):
        """🛒 Dispatches buy execution based on TRADING_MODE. (Unchanged)"""
        trading_mode = self.config['TRADING_MODE'].lower()

        if trigger_price <= 0:
            logger.error(f"❌ [{trading_mode.upper()}] Attempted to buy {mint} with invalid trigger price: {trigger_price}")
            return

        async with self.db.pool.acquire() as conn:
            async with conn.transaction(): 
                already_active = await self.db.has_active_buy_order(mint, conn)
                if already_active:
                    logger.debug(f"⚠️ [{trading_mode.upper()}] Attempted to buy {mint}, but it's already active in portfolio. Skipping.")
                    return

                sol_price_usd = await self.state.get_sol_price()
                if sol_price_usd is None or sol_price_usd <=0: 
                    logger.warning(f"⚠️ [{trading_mode.upper()}] Invalid SOL_PRICE_USD ({sol_price_usd}) for buy of {mint}.")

                sol_to_spend_on_tokens = float(self.config['SOL_TO_BUY']) 
                sim_buy_fee = float(self.config['DEFAULT_BUY_FEE'])
                sim_buy_tip = float(self.config['DEFAULT_BUY_TIP'])
                sim_total_investment = sol_to_spend_on_tokens + sim_buy_fee + sim_buy_tip
                current_sol_balance = await self.state.get_current_sol_balance()

                if trading_mode == "simulate":
                    if current_sol_balance < sim_total_investment:
                        logger.warning(f"💰 [SIMULATE] Insufficient balance ({current_sol_balance:.4f} SOL) for buy of {mint} requiring ~{sim_total_investment:.4f} SOL.")
                        return
                elif trading_mode in ["paper_trading", "live"]:
                    priority_fee_for_api = float(self.config['DEFAULT_BUY_TIP']) 
                    required_for_api_call = sol_to_spend_on_tokens + priority_fee_for_api
                    if current_sol_balance < required_for_api_call:
                        logger.warning(f"💰 [{trading_mode.upper()}] Insufficient balance ({current_sol_balance:.4f} SOL) for buy of {mint} requiring {sol_to_spend_on_tokens:.4f} SOL (base) + {priority_fee_for_api:.6f} SOL (priority).")
                        return
        
        if trading_mode == "simulate":
            logger.info(f"[SIMULATE MODE] Executing simulated buy for {mint} at {trigger_price:.9f} SOL")
            async with self.db.pool.acquire() as conn_sim: 
                async with conn_sim.transaction():
                    try:
                        tokens_bought_calculated = sol_to_spend_on_tokens / trigger_price
                        initial_sl_price_calc = trigger_price * (1 - float(self.config['INITIAL_STOP_LOSS_PERCENT']) / 100.0)
                        
                        sim_sell_fee_tp1 = float(self.config['DEFAULT_SELL_FEE'])
                        sim_sell_tip_tp1 = float(self.config['DEFAULT_SELL_TIP'])
                        sim_fees_for_tp1_sell = sim_sell_fee_tp1 + sim_sell_tip_tp1
                        sim_profit_margin_tp1_frac = float(self.config['FIRST_SELL_PROFIT_MARGIN']) / 100.0
                        sim_sell_percent_tp1_frac = float(self.config['FIRST_SELL_PERCENT']) / 100.0
                        
                        sim_tokens_to_sell_tp1 = tokens_bought_calculated * sim_sell_percent_tp1_frac
                        initial_tp1_price_calc = float('inf') 
                        if sim_tokens_to_sell_tp1 > 1e-9:
                            sim_cost_of_tp1_tokens = sim_total_investment * sim_sell_percent_tp1_frac
                            sim_desired_profit_tp1 = sim_cost_of_tp1_tokens * sim_profit_margin_tp1_frac
                            sim_gross_sol_needed_tp1 = sim_cost_of_tp1_tokens + sim_desired_profit_tp1 + sim_fees_for_tp1_sell
                            initial_tp1_price_calc = sim_gross_sol_needed_tp1 / sim_tokens_to_sell_tp1
                        else:
                            logger.warning(f"[SIMULATE] Tokens to sell at TP1 for {mint} is negligible. TP1 price set to infinity.")

                        second_tp_price_calc = trigger_price * (1 + float(self.config['SECOND_TAKE_PROFIT_PERCENT']) / 100.0)
                        
                        sim_buy_settings = {
                            "mode": "simulate", "simulated_price": trigger_price,
                            "buy_reason": buy_reason,
                            "sol_to_buy_config": self.config['SOL_TO_BUY'],
                            "initial_stop_loss_percent_config": self.config['INITIAL_STOP_LOSS_PERCENT'],
                            "first_sell_percent_config": self.config['FIRST_SELL_PERCENT'],
                            "first_sell_profit_margin_config": self.config['FIRST_SELL_PROFIT_MARGIN'],
                            "second_take_profit_percent_config": self.config['SECOND_TAKE_PROFIT_PERCENT'],
                            "trailing_stop_loss_percent_config": self.config['TRAILING_STOP_LOSS_PERCENT'],
                            "calculated_initial_sl_price": initial_sl_price_calc,
                            "calculated_initial_tp_price": initial_tp1_price_calc,
                            "calculated_second_tp_price": second_tp_price_calc,
                             "price_determination_method_at_buy_opportunity": self.config.get('PRICE_DETERMINATION_METHOD')
                        }
                        await self.db.insert_portfolio_buy_record(
                            mint=mint, current_price=trigger_price, market_cap_sol=market_cap_sol_at_trigger,
                            sol_base_amount=sol_to_spend_on_tokens, sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                            total_sol_investment=sim_total_investment, tokens_bought=tokens_bought_calculated,
                            buy_fee=sim_buy_fee, buy_tip=sim_buy_tip,
                            initial_stop_loss_price=initial_sl_price_calc,
                            initial_tp_price=initial_tp1_price_calc, second_tp_price=second_tp_price_calc,
                            timestamp=datetime.now(timezone.utc), settings=sim_buy_settings, buy_reason=buy_reason, ai_context=ai_context, conn=conn_sim
                        )
                        await self.db.log_completed_trade(
                            token_address=mint,
                            side='buy',
                            amount_in_sol=sol_to_spend_on_tokens,
                            amount_out_tokens=tokens_bought_calculated,
                            fill_price=trigger_price,
                            market_cap_at_trade=market_cap_sol_at_trigger,
                            tx_fee_sol=sim_buy_fee,
                            tip_sol=sim_buy_tip,
                            slippage_percent=0,
                            trade_context={**sim_buy_settings, "ai_advice_at_buy": ai_context} if ai_context else sim_buy_settings
                        )
                        await self.state.update_sol_balance(-sim_total_investment)
                        
                        token_name_row = await self.db.get_token_name(mint, conn_sim)
                        token_name = token_name_row['name'] if token_name_row else mint

                        log_msg = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=trigger_price, tokens_bought=tokens_bought_calculated, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sim_total_investment, buy_reason=buy_reason)
                        logger.info(log_msg)
                        if self.config.get('PLAY_BUY_SOUND'): asyncio.create_task(play_buy_opportunity_sound())
                        if self.config.get('TELEGRAM_INTERACTION'):
                            telegram_msg  = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=trigger_price, tokens_bought=tokens_bought_calculated, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sim_total_investment, buy_reason=buy_reason, for_telegram=True)
                            asyncio.create_task(send_telegram_message(telegram_msg))

                        if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_decision_maker:
                            ai_q = self.state.get_ai_evaluation_queue()
                            if not ai_q.full():
                                # Put with high priority (-100) to be checked next
                                await ai_q.put((-100, (mint, 'SELL/HOLD'))) 
                                logger.debug(f"🧠 AI Queue: Immediately queued {mint} for SELL/HOLD re-evaluation after buy.")
                            else:
                                logger.warning(f"AI Queue is full, could not add {mint} for immediate re-evaluation.")
                    except Exception as e_sim:
                        logger.error(f"[SIMULATE MODE] Buy DB operation failed for {mint}: {e_sim}", exc_info=True)

        elif trading_mode in ["paper_trading", "live"]:
            api_amount_str = f"{sol_to_spend_on_tokens:.9f}" 
            api_priority_fee = float(self.config['DEFAULT_BUY_TIP']) 
            api_slippage = int(self.config.get('DEFAULT_SLIPPAGE_PERCENT', 25))
            api_pool = self.config.get('DEFAULT_BUY_POOL', "auto")
            logger.info(f"[{trading_mode.upper()} MODE] Initiating buy for {mint} with {api_amount_str} SOL (Priority: {api_priority_fee} SOL) via PumpPortal API.")
            trade_result = await execute_live_pumpportal_trade(
                trigger_price=trigger_price, action="buy", mint_address=mint,
                amount_str=api_amount_str, denominated_in_sol=True,
                slippage_percent=api_slippage, priority_fee_sol=api_priority_fee, pool=api_pool
            )
            if trade_result and trade_result.get("success"):
                signature = trade_result.get("signature", "N/A")
                executed_price = trade_result.get("executed_price", trigger_price) 
                tokens_bought_actual = trade_result.get("quantity_exchanged", 0.0) 
                if tokens_bought_actual <= 0 or executed_price <= 0:
                    logger.error(f"[{trading_mode.upper()} MODE] Trade for {mint} reported success but returned invalid executed price/quantity. Sig: {signature}")
                    return
                logger.info(f"[{trading_mode.upper()} MODE] Buy for {mint} successful. Sig: {signature}, Executed Price (approx): {executed_price:.9f}, Tokens (approx): {tokens_bought_actual:.4f}")
                async with self.db.pool.acquire() as conn_live: 
                    async with conn_live.transaction():
                        total_sol_outflow_for_pnl = sol_to_spend_on_tokens + api_priority_fee 
                        initial_sl_price_live = executed_price * (1 - float(self.config['INITIAL_STOP_LOSS_PERCENT']) / 100.0)
                        live_sell_fee_tp1 = float(self.config.get('DEFAULT_SELL_FEE_LIVE', self.config['DEFAULT_SELL_FEE']))
                        live_sell_tip_tp1 = float(self.config.get('DEFAULT_SELL_TIP_LIVE', self.config['DEFAULT_SELL_TIP'])) 
                        live_fees_for_tp1_sell = live_sell_fee_tp1 + live_sell_tip_tp1
                        live_profit_margin_tp1_frac = float(self.config['FIRST_SELL_PROFIT_MARGIN']) / 100.0
                        live_sell_percent_tp1_frac = float(self.config['FIRST_SELL_PERCENT']) / 100.0
                        live_cost_of_all_tokens = sol_to_spend_on_tokens
                        live_tokens_to_sell_tp1 = tokens_bought_actual * live_sell_percent_tp1_frac
                        initial_tp1_price_live = float('inf')
                        if live_tokens_to_sell_tp1 > 1e-9:
                            live_cost_of_tp1_tokens = live_cost_of_all_tokens * live_sell_percent_tp1_frac
                            live_desired_profit_tp1 = live_cost_of_tp1_tokens * live_profit_margin_tp1_frac
                            live_gross_sol_needed_tp1 = live_cost_of_tp1_tokens + live_desired_profit_tp1 + live_fees_for_tp1_sell
                            initial_tp1_price_live = live_gross_sol_needed_tp1 / live_tokens_to_sell_tp1
                        else:
                            logger.warning(f"[{trading_mode.upper()}] Tokens to sell at TP1 for {mint} is negligible. TP1 price set to infinity.")
                        second_tp_price_live = executed_price * (1 + float(self.config['SECOND_TAKE_PROFIT_PERCENT']) / 100.0)
                        live_buy_settings = {
                            "mode": trading_mode, "signature": signature,
                            "buy_reason": buy_reason,
                            "api_executed_price": executed_price, "api_tokens_bought": tokens_bought_actual,
                            "api_priority_fee_sent": api_priority_fee, "api_slippage_sent": api_slippage,
                            "sol_to_buy_config": self.config['SOL_TO_BUY'],
                            "initial_stop_loss_percent_config": self.config['INITIAL_STOP_LOSS_PERCENT'],
                            "first_sell_percent_config": self.config['FIRST_SELL_PERCENT'],
                            "first_sell_profit_margin_config": self.config['FIRST_SELL_PROFIT_MARGIN'],
                            "second_take_profit_percent_config": self.config['SECOND_TAKE_PROFIT_PERCENT'],
                            "trailing_stop_loss_percent_config": self.config['TRAILING_STOP_LOSS_PERCENT'],
                             "calculated_initial_sl_price": initial_sl_price_live,
                            "calculated_initial_tp_price": initial_tp1_price_live,
                            "calculated_second_tp_price": second_tp_price_live,
                            "price_determination_method_at_buy_opportunity": self.config.get('PRICE_DETERMINATION_METHOD')
                        }
                        await self.db.insert_portfolio_buy_record(
                            mint=mint, current_price=executed_price, market_cap_sol=market_cap_sol_at_trigger,
                            sol_base_amount=sol_to_spend_on_tokens, sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                            total_sol_investment=total_sol_outflow_for_pnl, 
                            tokens_bought=tokens_bought_actual,
                            buy_fee=0, buy_tip=api_priority_fee, 
                            initial_stop_loss_price=initial_sl_price_live,
                            initial_tp_price=initial_tp1_price_live, second_tp_price=second_tp_price_live,
                            timestamp=datetime.now(timezone.utc), settings=live_buy_settings, buy_reason=buy_reason, ai_context=ai_context, conn=conn_live
                        )
                        await self.db.log_completed_trade(
                            token_address=mint,
                            side='buy',
                            amount_in_sol=sol_to_spend_on_tokens,
                            amount_out_tokens=tokens_bought_actual,
                            fill_price=executed_price,
                            market_cap_at_trade=market_cap_sol_at_trigger,
                            tx_fee_sol=0,
                            tip_sol=api_priority_fee,
                            slippage_percent=trade_result.get("slippage"),
                            trade_context={**live_buy_settings, "ai_advice_at_buy": ai_context} if ai_context else live_buy_settings,
                        )
                        await self.state.update_sol_balance(-total_sol_outflow_for_pnl)
                        token_name_row = await self.db.get_token_name(mint, conn_live)
                        token_name = token_name_row['name'] if token_name_row else mint
                        log_msg = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=executed_price, tokens_bought=tokens_bought_actual, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sol_to_spend_on_tokens, buy_reason=buy_reason)
                        logger.info(f"[{trading_mode.upper()}] {log_msg}")
                        if self.config.get('PLAY_BUY_SOUND'): asyncio.create_task(play_buy_opportunity_sound())
                        if self.config.get('TELEGRAM_INTERACTION'):
                            telegram_msg  = format_buy_order_log(self.state, name=token_name, mint=mint, price_per_token=executed_price, tokens_bought=tokens_bought_actual, market_cap=market_cap_sol_at_trigger, sol_price=sol_price_usd, total_investment=sol_to_spend_on_tokens, buy_reason=buy_reason, for_telegram=True)
                            telegram_msg += f"\nMode: {trading_mode.upper()}\nSignature: {signature}"
                            asyncio.create_task(send_telegram_message(telegram_msg))
            else:
                logger.error(f"[{trading_mode.upper()} MODE] Buy failed for {mint}. API Error: {trade_result.get('error', 'Unknown') if trade_result else 'No API result'}")
        else:
            logger.error(f"Unknown TRADING_MODE: '{trading_mode}' in execute_buy for {mint}.")
    
    # --- MODIFIED execute_sell ---
    async def execute_sell(self, conn, mint: str, trigger_price: float, market_cap_sol_at_trigger: float, reason: str, sell_percentage: float, position_id_to_update: int, sell_trigger_values: dict = None, ai_context: Optional[dict] = None):
        """
        💸 Dispatches sell execution based on TRADING_MODE.
        NOW ALSO logs the sell event to the AI RAG memory for feedback.
        """
        trading_mode = self.config['TRADING_MODE'].lower()
        if sell_trigger_values is None: sell_trigger_values = {}
        
        sol_price_usd = await self.state.get_sol_price() 
        profit_from_sell = None # Initialize profit variable

        try:
            buy_entry = await self.db.get_portfolio_entry_for_update(position_id_to_update, conn)
            if not buy_entry:
                logger.warning(f"⚠️ [{trading_mode.upper()}] Could not find active buy entry for ID {position_id_to_update} ({mint}) to sell.")
                return None

            remaining_tokens_portfolio = float(buy_entry['remaining_tokens'])
            initial_tokens_portfolio = float(buy_entry['initial_tokens'])
            total_investment_sol_at_buy_portfolio = float(buy_entry['total_investment_sol']) 

            if remaining_tokens_portfolio <= 1e-9: 
                logger.info(f"ℹ️ [{trading_mode.upper()}] No remaining tokens for pos ID {position_id_to_update} ({mint}). Skipping sell.")
                return None

            tokens_to_sell_on_trigger: float
            if reason == "First TP": 
                tokens_to_sell_on_trigger = initial_tokens_portfolio * sell_percentage
                tokens_to_sell_on_trigger = min(tokens_to_sell_on_trigger, remaining_tokens_portfolio)
            else: 
                tokens_to_sell_on_trigger = remaining_tokens_portfolio * sell_percentage

            if tokens_to_sell_on_trigger <= 1e-9:
                logger.info(f"ℹ️ [{trading_mode.upper()}] Sell amount for {mint} (Reason: {reason}) is negligible ({tokens_to_sell_on_trigger:.12f}). Skipping.")
                return None
            
            # --- Initialize variables for RAG logging ---
            final_executed_price = trigger_price # Default to trigger price
            final_profit_sol = 0.0
            final_net_sol_received = 0.0
            final_market_cap_sol = market_cap_sol_at_trigger
            final_sell_settings = {}
            # ---

            if trading_mode == "simulate":
                logger.info(f"[SIMULATE MODE] Executing simulated sell for {tokens_to_sell_on_trigger:.4f} of {mint} at {trigger_price:.9f} (Reason: {reason})")
                
                sim_gross_sol_received = tokens_to_sell_on_trigger * trigger_price
                sim_sell_fee = float(self.config['DEFAULT_SELL_FEE'])
                sim_sell_tip = float(self.config['DEFAULT_SELL_TIP'])
                sim_net_sol_received = sim_gross_sol_received - sim_sell_fee - sim_sell_tip

                sim_cost_basis_sold_portion = total_investment_sol_at_buy_portfolio * (tokens_to_sell_on_trigger / initial_tokens_portfolio) if initial_tokens_portfolio > 0 else 0
                sim_profit = sim_net_sol_received - sim_cost_basis_sold_portion

                sim_new_remaining_tokens = remaining_tokens_portfolio - tokens_to_sell_on_trigger
                sim_new_status = 'closed' if sim_new_remaining_tokens < 1e-9 else 'active'

                await self.db.update_portfolio_entry_after_sell(position_id_to_update, sim_new_remaining_tokens, sim_new_status, conn)
                sim_sell_settings = {
                    "mode": "simulate", "reason": reason, **sell_trigger_values,
                    "sell_percentage_of_initial_request": sell_percentage * 100 if reason == "First TP" else (sell_percentage * 100.0 if reason in ["Stop Loss", "Breakeven SL", "Second TP", "Trailing SL", "Emergency SL (MCap)", "manual_override"] else 0.0),
                    "actual_tokens_sold_as_fraction_of_remaining_at_sell_time": (tokens_to_sell_on_trigger / remaining_tokens_portfolio) if remaining_tokens_portfolio > 0 else 0,
                    "sell_fee_config": self.config['DEFAULT_SELL_FEE'],
                    "sell_tip_config": self.config['DEFAULT_SELL_TIP'],
                    "price_determination_method_used": self.config.get('PRICE_DETERMINATION_METHOD'),
                    "trigger_price_at_sell": trigger_price
                }
                if market_cap_sol_at_trigger is not None: sim_sell_settings["market_cap_sol_at_sell"] = market_cap_sol_at_trigger

                await self.db.insert_portfolio_sell_record(
                    mint=mint, current_price=trigger_price, market_cap_sol=market_cap_sol_at_trigger,
                    net_sol_received=sim_net_sol_received, sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                    tokens_sold=tokens_to_sell_on_trigger, sell_fee=sim_sell_fee, sell_tip=sim_sell_tip, profit=sim_profit,
                    reason=reason, timestamp=datetime.now(timezone.utc), settings=sim_sell_settings, ai_context=ai_context, conn=conn
                )
                await self.db.log_completed_trade(
                    token_address=mint, side='sell',
                    amount_in_sol=sim_net_sol_received, amount_out_tokens=tokens_to_sell_on_trigger,
                    fill_price=trigger_price, market_cap_at_trade=market_cap_sol_at_trigger,
                    tx_fee_sol=sim_sell_fee, tip_sol=sim_sell_tip, slippage_percent=0,
                    trade_context={**sim_sell_settings, "ai_advice_at_sell": ai_context} if ai_context else sim_sell_settings,
                )
                await self.state.update_sol_balance(sim_net_sol_received)
                
                # Set variables for RAG logging
                profit_from_sell = sim_profit
                final_profit_sol = sim_profit
                final_net_sol_received = sim_net_sol_received
                final_sell_settings = sim_sell_settings

            elif trading_mode in ["paper_trading", "live"]:
                api_pool = self.config.get('DEFAULT_SELL_POOL', "auto")
                
                token_record = await conn.fetchrow("SELECT data_source FROM tokens WHERE mint = $1", mint)
                if token_record and token_record['data_source'] == 'DEXSCREENER':
                    logger.debug(f"Token {mint} is migrated. Attempting to find primary DEX ID for selling.")
                    dex_id = await self.db.get_primary_dex_id_for_migrated_token(mint, conn)
                    if dex_id:
                        api_pool = dex_id
                        logger.info(f"Using dynamically determined pool '{api_pool}' for migrated token {mint}.")
                    else:
                        logger.warning(f"Could not determine specific DEX ID for migrated token {mint}. Falling back to default pool '{api_pool}'.")
                
                api_amount_tokens_str = f"{tokens_to_sell_on_trigger:.9f}" 
                api_priority_fee = float(self.config['DEFAULT_SELL_TIP']) 
                api_slippage = int(self.config.get('DEFAULT_SLIPPAGE_PERCENT', 25))

                logger.info(f"[{trading_mode.upper()} MODE] Initiating sell of {api_amount_tokens_str} {mint} on pool '{api_pool}' (Reason: {reason}, Priority: {api_priority_fee} SOL)")

                trade_result = await execute_live_pumpportal_trade(
                    trigger_price=trigger_price, action="sell", mint_address=mint,
                    amount_str=api_amount_tokens_str, denominated_in_sol=False, 
                    slippage_percent=api_slippage, priority_fee_sol=api_priority_fee, pool=api_pool
                )

                if trade_result and trade_result.get("success"):
                    signature = trade_result.get("signature", "N/A")
                    executed_price_live = trade_result.get("executed_price", trigger_price)
                    sol_received_from_api = trade_result.get("quantity_exchanged", 0.0)

                    if sol_received_from_api <= 0 and executed_price_live > 0:
                        sol_received_from_api = tokens_to_sell_on_trigger * executed_price_live
                    
                    logger.info(f"[{trading_mode.upper()} MODE] Sell for {mint} successful. Sig: {signature}, Executed Price (approx): {executed_price_live:.9f}, SOL Received (approx gross): {sol_received_from_api:.9f}")

                    # --- This transaction is now inside the outer `execute_sell` transaction ---
                    cost_basis_sold_portion_live = total_investment_sol_at_buy_portfolio * (tokens_to_sell_on_trigger / initial_tokens_portfolio) if initial_tokens_portfolio > 0 else 0
                    profit_live = sol_received_from_api - cost_basis_sold_portion_live

                    new_remaining_tokens_live = remaining_tokens_portfolio - tokens_to_sell_on_trigger
                    new_status_live = 'closed' if new_remaining_tokens_live < 1e-9 else 'active'

                    await self.db.update_portfolio_entry_after_sell(position_id_to_update, new_remaining_tokens_live, new_status_live, conn)
                    
                    live_sell_settings = {
                        "mode": trading_mode, "signature": signature, "reason": reason,
                        "api_pool_used": api_pool,
                        "api_executed_price": executed_price_live, "api_sol_received": sol_received_from_api,
                        "api_priority_fee_sent": api_priority_fee, "api_slippage_sent": api_slippage,
                        **sell_trigger_values,
                        "sell_percentage_of_initial_request": sell_percentage * 100 if reason == "First TP" else (sell_percentage * 100.0 if reason in ["Stop Loss", "Breakeven SL", "Second TP", "Trailing SL", "Emergency SL (MCap)", "manual_override"] else 0.0),
                        "actual_tokens_sold_as_fraction_of_remaining_at_sell_time": (tokens_to_sell_on_trigger / remaining_tokens_portfolio) if remaining_tokens_portfolio > 0 else 0,
                        "sell_fee_config": self.config['DEFAULT_SELL_FEE'],
                        "sell_tip_config": self.config['DEFAULT_SELL_TIP'],
                        "price_determination_method_used": self.config.get('PRICE_DETERMINATION_METHOD'),
                        "trigger_price_at_sell": trigger_price
                    }
                    if market_cap_sol_at_trigger is not None: live_sell_settings["market_cap_sol_at_sell"] = market_cap_sol_at_trigger

                    await self.db.insert_portfolio_sell_record(
                        mint=mint, current_price=executed_price_live, market_cap_sol=market_cap_sol_at_trigger,
                        net_sol_received=sol_received_from_api, 
                        sol_price_usd=sol_price_usd if sol_price_usd else 0.0,
                        tokens_sold=tokens_to_sell_on_trigger,
                        sell_fee=0, tip_sol=api_priority_fee, 
                        profit=profit_live,
                        reason=reason, timestamp=datetime.now(timezone.utc), settings=live_sell_settings, ai_context=ai_context, conn=conn
                    )
                    await self.db.log_completed_trade(
                        token_address=mint,
                        side='sell',
                        amount_in_sol=sol_received_from_api,
                        amount_out_tokens=tokens_to_sell_on_trigger,
                        fill_price=executed_price_live,
                        market_cap_at_trade=market_cap_sol_at_trigger,
                        tx_fee_sol=0,
                        tip_sol=api_priority_fee,
                        slippage_percent=trade_result.get("slippage"),
                        trade_context={**live_sell_settings, "ai_advice_at_sell": ai_context} if ai_context else live_sell_settings,
                    )
                    await self.state.update_sol_balance(sol_received_from_api)

                    # Set variables for RAG logging
                    profit_from_sell = profit_live
                    final_executed_price = executed_price_live
                    final_profit_sol = profit_live
                    final_net_sol_received = sol_received_from_api
                    final_sell_settings = live_sell_settings

                else:
                    logger.error(f"[{trading_mode.upper()} MODE] Sell failed for {mint}. API Error: {trade_result.get('error', 'Unknown error') if trade_result else 'No API result'}")
                    return None
            else:
                logger.error(f"Unknown TRADING_MODE: '{trading_mode}' in execute_sell for {mint}.")
                return None
            
            # --- RAG FEEDBACK LOOP & LOGGING ---
            # This block runs for *both* SIMULATE and LIVE modes if profit_from_sell is not None
            if profit_from_sell is not None:
                token_name_row = await self.db.get_token_name(mint, conn)
                token_name = token_name_row['name'] if token_name_row else mint
                log_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=profit_from_sell, reason=reason, sol_price=sol_price_usd)
                logger.info(log_msg)
                
                # --- NEW: Log Outcome to RAG Memory ---
                if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_decision_maker:
                    # Create a "snapshot" of the sell event
                    sell_snapshot_data = {
                        "mint": mint,
                        "source": (await conn.fetchval("SELECT data_source FROM tokens WHERE mint = $1", mint)) or "PUMP",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "decision_context": "SELL_EVENT_OUTCOME", # Special context
                        "market_cap": (final_market_cap_sol * sol_price_usd) if final_market_cap_sol and sol_price_usd else 0,
                        "volatility": 0, # Volatility at sell time isn't as relevant as the reason
                        "token_age_minutes": (datetime.now(timezone.utc) - (await conn.fetchval("SELECT timestamp FROM tokens WHERE mint = $1", mint))).total_seconds() / 60,
                        "is_prolific_creator": False, # Not relevant for sell event
                        "uri_status": "N/A", # Not relevant
                        "market_dynamics_summary_str": f"Sell executed at {final_executed_price:.9f} SOL",
                        "trade_history_summary": "N/A" # Not relevant, outcome is what matters
                    }
                    # Create the "decision" (outcome) info
                    sell_decision_info = {
                        "decision": f"SELL_OUTCOME: {reason}",
                        "confidence": 100, # This was an actual event
                        "explanation": f"Sell of {tokens_to_sell_on_trigger:.4f} tokens executed.\nReason: {reason}\nProfit: {final_profit_sol:+.6f} SOL\nNet SOL Received: {final_net_sol_received:+.6f} SOL"
                    }
                    
                    # Asynchronously add this to RAG memory, don't block the sell logic
                    asyncio.create_task(
                        self.ai_decision_maker.add_decision_snapshot_to_memory(sell_snapshot_data, sell_decision_info)
                    )
                    logger.debug(f"🧠 AI Feedback: Queued sell outcome for {mint} (Reason: {reason}) to RAG memory.")
                # --- END RAG FEEDBACK LOOP ---

                if self.config.get('PLAY_SELL_SOUND'):
                    if any(sl_reason in reason for sl_reason in ["Stop Loss", "Breakeven SL", "Emergency SL", "manual_override"]): asyncio.create_task(play_sell_sl_sound_async())
                    elif any(tp_reason in reason for tp_reason in ["First TP", "Second TP", "Trailing SL"]): asyncio.create_task(play_sell_tp_sound_async())
                if self.config.get('TELEGRAM_INTERACTION'):
                    telegram_msg = format_sell_order_log(mint=mint, token_name=token_name, market_cap_sol=market_cap_sol_at_trigger, profit=profit_from_sell, reason=reason, sol_price=sol_price_usd, for_telegram=True)
                    if trading_mode in ["paper_trading", "live"]:
                        telegram_msg += f"\nMode: {trading_mode.upper()}\nSignature: {final_sell_settings.get('signature', 'N/A')}"
                    asyncio.create_task(send_telegram_message(telegram_msg))
                
                sell_reasons_triggering_hard_cooldown = self.config.get('APPLY_TREND_REVERSAL_ON_SELL_REASONS', [])
                if any(configured_reason in reason for configured_reason in sell_reasons_triggering_hard_cooldown):
                    cooldown_minutes = self.config.get('STOP_LOSS_COOLDOWN_MINUTES', 0)
                    if cooldown_minutes > 0:
                        await self.db.set_token_cooldown(mint, cooldown_minutes) 
                return profit_from_sell
            
            # This return is for cases where the trade_result failed
            return None

        except Exception as e:
            logger.error(f"❌ [{trading_mode.upper()}] Overall error in execute_sell for {mint} (PosID: {position_id_to_update}, Reason: {reason}): {e}", exc_info=True)
            if trading_mode == "simulate": raise 
            return None
    
    async def check_sell_opportunities(self):
        """
        [REFACTORED v3] Checks for sell opportunities with combined post-TP1 logic. (Unchanged)
        """
        if self.state.shutdown_event.is_set():
            return
        
        sol_price_usd = await self.state.get_sol_price()
        if sol_price_usd is None or sol_price_usd <= 0:
            logger.warning(f"⚠️ Invalid SOL_PRICE_USD ({sol_price_usd}); skipping sell check.")
            return

        async with self.db.pool.acquire() as conn:
            async with conn.transaction(): 
                try:
                    positions = await self.db.get_active_buy_positions(conn)
                    if not positions:
                        return

                    for position in positions:
                        pos_id, mint, token_data_source, volume_stale_since = position['id'], position['mint'], position['data_source'], position['volume_stale_since']
                        
                        price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn)
                        current_price_to_use = price_data.get('price')
                        current_market_cap_sol_for_log = price_data.get('market_cap')
                        
                        if token_data_source == 'DEXSCREENER':
                            if current_price_to_use is None:
                                min_mcap_threshold_usd = self.config['MIN_MARKETCAP_THRESHOLD']
                                if current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0:
                                    current_mcap_usd = current_market_cap_sol_for_log * sol_price_usd
                                    if current_mcap_usd < min_mcap_threshold_usd:
                                        sell_reason = "Emergency SL (MCap during stale volume)"
                                        logger.info(f"🚨 {sell_reason} for {mint} (ID: {pos_id}). MC crashed to ${current_mcap_usd:,.2f} while volume was stale. Overriding patience timer.")
                                        await self.execute_sell(
                                            conn, mint, float(position['buy_price']), current_market_cap_sol_for_log,
                                            sell_reason, 1.0, pos_id, {"reason": "MCap crash during stale period"}
                                        )
                                        continue

                                if volume_stale_since is None:
                                    logger.warning(f"Token {mint} (ID: {pos_id}) has stale volume. Starting patience timer.")
                                    await conn.execute("UPDATE portfolio SET volume_stale_since = NOW() WHERE id = $1", pos_id)
                                    continue
                                else:
                                    time_since_stale = datetime.now(timezone.utc) - volume_stale_since
                                    patience_delay = timedelta(minutes=self.config.get('DEXSCREENER_STALE_VOLUME_SELL_DELAY_MINUTES', 120))
                                    if time_since_stale >= patience_delay:
                                        sell_reason = "Emergency SL (No Volume)"
                                        logger.info(f"🆘 {sell_reason} for {mint} (ID: {pos_id}) after waiting {time_since_stale.total_seconds() / 60:.1f} minutes.")
                                        await self.execute_sell(
                                            conn, mint, float(position['buy_price']), current_market_cap_sol_for_log or 0,
                                            sell_reason, 1.0, pos_id, {"reason": "Stale volume patience timer expired"}
                                        )
                                        continue
                                    else:
                                        wait_time = (patience_delay - time_since_stale).total_seconds() / 60
                                        logger.debug(f"Token {mint} (ID: {pos_id}) is within stale patience window. MCap is OK. Waiting for another {wait_time:.1f} mins.")
                                        continue
                            elif volume_stale_since is not None:
                                logger.info(f"✅ Token {mint} (ID: {pos_id}) has recovered volume. Resetting stale timer.")
                                await conn.execute("UPDATE portfolio SET volume_stale_since = NULL WHERE id = $1", pos_id)
                        
                        safe_price = format_price_for_log(current_price_to_use)
                        safe_mcap = f"{current_market_cap_sol_for_log:,.2f}" if current_market_cap_sol_for_log is not None else "N/A"
                        pnl_emoji, unrealized_pnl_str = "❓", "\tPnL: N/A"

                        if current_price_to_use is not None and current_price_to_use > 0:
                            try:
                                remaining_tokens, initial_tokens, total_investment_sol = float(position['remaining_tokens']), float(position['initial_tokens']), float(position['total_investment_sol'])
                                if initial_tokens > 1e-9 and remaining_tokens > 1e-9:
                                    cost_basis_remaining = (total_investment_sol / initial_tokens) * remaining_tokens
                                    unrealized_pnl_sol = (remaining_tokens * current_price_to_use) - cost_basis_remaining
                                    profit_percentage = (unrealized_pnl_sol / cost_basis_remaining) * 100 if cost_basis_remaining > 1e-9 else 0.0
                                    pnl_emoji = "📈" if unrealized_pnl_sol >= 0 else "📉"
                                    unrealized_pnl_str = f"\tPnL: {str(format_pnl_value(unrealized_pnl_sol))} {str(format_profit_pct(profit_percentage))}"
                            except (TypeError, ValueError, ZeroDivisionError):
                                unrealized_pnl_str, pnl_emoji = "\tPnL: [bold yellow]error[/bold yellow]", "⚠️"

                        #logger.debug(f":abacus: Checking sell for {mint:<44} (ID: {pos_id:<4}) {pnl_emoji} ({token_data_source[:4]}) - Price: {safe_price:<12} MCap: {safe_mcap:<10} SOL {unrealized_pnl_str}")

                        ai_advice_used = None
                        ai_decision = None
                        ai_confidence = 0
                        is_ai_advice_valid = False 
                        ai_log_part = "AI: N/A" # Default if no record

                        if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_decision_maker:
                            ai_decision_record = await self.db.get_latest_ai_decision(mint, conn)
                            if ai_decision_record:
                                ai_timestamp = ai_decision_record['evaluation_timestamp']
                                advice_age = datetime.now(timezone.utc) - ai_timestamp
                                max_staleness = timedelta(minutes=self.config.get('AI_ADVICE_MAX_STALENESS_MINUTES', 20))

                                if advice_age <= max_staleness:
                                    is_ai_advice_valid = True
                                    ai_decision = ai_decision_record['decision']
                                    ai_confidence = ai_decision_record['confidence']
                                    ai_advice_used = {'decision': ai_decision, 'confidence': ai_confidence, 'timestamp': ai_timestamp.isoformat()}
                                    ai_log_part = f"AI: {ai_decision} ({ai_confidence}%) {advice_age.total_seconds():.0f}s"
                                else:
                                    ai_log_part = f"AI: Stale ({advice_age.total_seconds():.0f}s)"
                        
                        logger.debug(
                            f":abacus: Sell check {mint:<44} (ID: {pos_id:<4}) {pnl_emoji} ({token_data_source[:4]}) "
                            f"Price: {safe_price:<12} MCap: {safe_mcap:<10} SOL {unrealized_pnl_str} | "
                            f"{ai_log_part}"
                        )   
                        if current_price_to_use is None or current_price_to_use <= 0:
                            continue

                        buy_price = float(position['buy_price'])
                        initial_tokens = float(position['initial_tokens'])
                        active_stop_loss_price = float(position['stop_loss_price'])
                        highest_price_since_buy = float(position['highest_price'])
                        initial_tp_price = float(position['initial_tp_price'])
                        second_tp_price = float(position['second_tp_price'])
                        first_tp_hit = position['first_tp_hit']

                        if initial_tokens <= 0: continue 

                        if current_price_to_use > highest_price_since_buy:
                            highest_price_since_buy = current_price_to_use
                            await self.db.update_portfolio_highest_price(pos_id, current_price_to_use, conn)

                        sell_reason = None
                        rule_based_sell_triggered = False 
                        rule_reason = None 
                        trigger_values_for_log = {}

                        if not first_tp_hit:
                            if current_price_to_use <= active_stop_loss_price: rule_based_sell_triggered=True; rule_reason="Stop Loss"; trigger_values_for_log = {"stop_loss_price_threshold": active_stop_loss_price}
                            elif current_price_to_use >= second_tp_price: rule_based_sell_triggered=True; rule_reason="Second TP"; trigger_values_for_log = {"second_tp_price_threshold": second_tp_price}
                            elif current_price_to_use >= initial_tp_price: rule_based_sell_triggered=True; rule_reason="First TP"; trigger_values_for_log = {"first_tp_price_threshold": initial_tp_price}
                        else:
                            lookback_hours = self.config.get('INDICATOR_LOOKBACK_HOURS', 2.0)
                            start_date = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
                            historical_data = await self.db.get_historical_data_for_backtesting([mint], start_date, None)
                            
                            df_indicators = pd.DataFrame() 
                            if historical_data and mint in historical_data:
                                if len(historical_data[mint]) >= self.config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30):
                                    loop = asyncio.get_running_loop()
                                    df_indicators = await loop.run_in_executor(None, calculate_trend_indicators, historical_data[mint], self.config)
                                else:
                                    logger.debug(f"Not enough historical data for {mint} ({len(historical_data[mint])} points) to calculate indicators for sell logic.")

                            if not df_indicators.empty and len(df_indicators) >= 2:
                                latest = df_indicators.iloc[-1]
                                previous = df_indicators.iloc[-2]
                                if latest.get('EMA_fast') < latest.get('EMA_slow') and previous.get('EMA_fast') >= previous.get('EMA_slow'):
                                    rule_based_sell_triggered=True; rule_reason="Trend Reversal (EMA Cross)"; trigger_values_for_log = {"ema_fast": latest.get('EMA_fast'), "ema_slow": latest.get('EMA_slow')}
                                    logger.info(f" EMA cross-down detected for {mint}. Fast EMA: {latest.get('EMA_fast'):.9f}, Slow EMA: {latest.get('EMA_slow'):.9f}")

                            if not rule_based_sell_triggered:
                                effective_sl_price = active_stop_loss_price
                                simple_trailing_sl = highest_price_since_buy * (1 - self.config['TRAILING_STOP_LOSS_PERCENT'] / 100.0)
                                effective_sl_price = max(effective_sl_price, simple_trailing_sl)
                                
                                if self.config['USE_DYNAMIC_SECOND_TP'] and not df_indicators.empty:
                                    latest = df_indicators.iloc[-1]
                                    atr_col = f"ATRr_{self.config['ADAPTIVE_ATR_PERIOD']}"
                                    rsi_col = f"RSI_{self.config['RSI_PERIOD']}"
                                    
                                    if atr_col in latest and rsi_col in latest and pd.notna(latest[atr_col]) and pd.notna(latest[rsi_col]):
                                        multiplier = self.get_adaptive_atr_multiplier(latest[rsi_col])
                                        chandelier_exit = highest_price_since_buy - (multiplier * latest[atr_col])
                                        effective_sl_price = max(effective_sl_price, chandelier_exit)
                                        logger.debug(f"Dynamic SL for {mint}: Breakeven={active_stop_loss_price:.9f}, SimpleTrail={simple_trailing_sl:.9f}, Chandelier={chandelier_exit:.9f} -> Effective SL={effective_sl_price:.9f}")

                                if current_price_to_use <= effective_sl_price:
                                    rule_based_sell_triggered=True
                                    rule_reason="Trailing SL Hybrid"
                                    trigger_values_for_log = {
                                        "effective_sl_price": effective_sl_price, 
                                        "highest_price": highest_price_since_buy,
                                        "breakeven_price": active_stop_loss_price,
                                        "simple_trail_price": simple_trailing_sl
                                    }
                        
                        if not rule_based_sell_triggered:
                            if current_market_cap_sol_for_log is not None and current_market_cap_sol_for_log > 0 and \
                               (current_market_cap_sol_for_log * sol_price_usd) < self.config['MIN_MARKETCAP_THRESHOLD']:
                                rule_based_sell_triggered=True
                                rule_reason="Emergency SL (MCap)"
                                sell_trigger_values = {"current_market_cap_usd_at_trigger": (current_market_cap_sol_for_log * sol_price_usd), "min_mcap_threshold_config": self.config['MIN_MARKETCAP_THRESHOLD']}

                        if is_ai_advice_valid:
                            if rule_based_sell_triggered:
                                if ai_decision == 'SELL':
                                    logger.debug(f"🧠 AI confirmed rule-based SELL trigger ({rule_reason}) for {mint} (Confidence: {ai_confidence}).")
                                    sell_reason = rule_reason
                                elif ai_decision == 'HOLD':
                                    override_threshold = self.config.get('AI_HOLD_OVERRIDE_CONFIDENCE_THRESHOLD', 85)
                                    can_override = rule_reason not in ["Stop Loss", "Emergency SL (MCap)", "Emergency SL (No Volume)"]
                                    if can_override and ai_confidence >= override_threshold:
                                        logger.warning(f"🧠 AI advised HOLD (Confidence: {ai_confidence} >= {override_threshold}), overriding rule-based sell trigger ({rule_reason}) for {mint} this cycle.")
                                        continue 
                                    else:
                                        logger.debug(f"🧠 AI advised HOLD (Confidence: {ai_confidence}) but rule ({rule_reason}) is critical or confidence too low. Proceeding with rule-based sell.")
                                        sell_reason = rule_reason
                            else:
                                if ai_decision == 'SELL':
                                    trigger_threshold = self.config.get('AI_SELL_TRIGGER_CONFIDENCE_THRESHOLD', 75)
                                    if ai_confidence >= trigger_threshold:
                                        logger.info(f"🧠 AI advised SELL (Confidence: {ai_confidence} >= {trigger_threshold}) for {mint}, triggering early sell despite no rule match.")
                                        sell_reason = "AI Triggered Sell"
                                        trigger_values_for_log = {"ai_confidence_threshold": trigger_threshold}
                                    #else:
                                         #logger.debug(f"🧠 AI advised SELL but confidence ({ai_confidence}) is below threshold ({trigger_threshold}). Holding based on rules.")
                                #elif ai_decision == 'HOLD':
                                    #logger.debug(f"🧠 AI confirmed HOLD for {mint} (Confidence: {ai_confidence}), aligning with rules.")
                        elif rule_based_sell_triggered:
                            sell_reason = rule_reason


                        if sell_reason:
                            sell_percentage_of_initial = 0.0 
                            if sell_reason == "First TP":
                                sell_percentage_of_initial = self.config['FIRST_SELL_PERCENT'] / 100.0
                            else:
                                sell_percentage_of_initial = 1.0 
                            
                            log_message_sell_trigger = (f"Trigger for {mint} (ID: {pos_id}): Reason='{sell_reason}', PriceToUse={current_price_to_use:.9f}")
                            logger.info(log_message_sell_trigger)
                            
                            profit_from_sell = await self.execute_sell(
                                conn, mint, current_price_to_use, 
                                current_market_cap_sol_for_log if current_market_cap_sol_for_log is not None else 0.0,
                                sell_reason, sell_percentage_of_initial, 
                                pos_id, trigger_values_for_log, ai_advice_used
                            )
                            
                            if profit_from_sell is not None and sell_reason == "First TP":
                                await self.db.mark_first_tp_hit_and_adjust_sl(pos_id, buy_price, conn)
                                logger.info(f"📈 Marked First TP as hit for {mint} (ID: {pos_id}) and SL adjusted to breakeven ({buy_price:.9f}).")
                            
                            if profit_from_sell is not None: 
                                await asyncio.sleep(0.1) 
                except Exception as e:
                    logger.error(f"❌ Error in check_sell_opportunities transaction block: {e}", exc_info=True)
    
    async def execute_manual_sell_all(self):
        """Executes a manual sell for ALL active positions. (Unchanged)"""
        trading_mode = self.config['TRADING_MODE'].lower()
        logger.info(f"[{trading_mode.upper()} MODE] Received command to sell ALL active positions.")
        
        positions_to_sell = []
        async with self.db.pool.acquire() as conn_fetch:
            positions_to_sell = await self.db.get_active_buy_positions(conn_fetch)

        if not positions_to_sell:
            logger.info("No active positions found to sell.")
            await send_telegram_message("ℹ️ Sell All Command: No active positions found to sell.")
            return

        logger.info(f"Found {len(positions_to_sell)} active positions to sell.")
        await send_telegram_message(f"🚨 Executing SELL ALL command for {len(positions_to_sell)} positions...")

        for position in positions_to_sell:
            mint = position['mint']
            pos_id = position['id']
            try:
                # --- Must use a NEW connection for each sell's transaction ---
                async with self.db.pool.acquire() as conn_sell:
                    price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn_sell)
                    trigger_price = price_data.get('price')
                    market_cap = price_data.get('market_cap', 0.0)

                    if trigger_price is None or trigger_price <= 0:
                        logger.error(f"[{trading_mode.upper()}] Cannot execute sell for {mint} (part of SELL ALL): Invalid current price ({trigger_price}).")
                        continue

                    logger.info(f"[{trading_mode.upper()}] Selling {mint} (Pos ID: {pos_id}) at price {trigger_price:.9f}...")
                    # --- Pass the new connection to execute_sell ---
                    await self.execute_sell(
                        conn=conn_sell,
                        mint=mint,
                        trigger_price=trigger_price,
                        market_cap_sol_at_trigger=market_cap,
                        reason="manual_override_all",
                        sell_percentage=1.0,
                        position_id_to_update=pos_id,
                        sell_trigger_values={"command": "SELL_ALL_IMMEDIATELY"}
                    )
            except Exception as e:
                logger.error(f"Failed to sell {mint} (Pos ID: {pos_id}) during SELL ALL operation: {e}", exc_info=True)
        
        logger.info("SELL ALL operation completed.")
        await send_telegram_message("✅ SELL ALL operation completed.")
        
    async def execute_manual_sell(self, mint: str):
        """Executes a manual sell for all holdings of a specific token. (Unchanged)"""
        trading_mode = self.config['TRADING_MODE'].lower()
        logger.info(f"[{trading_mode.upper()} MODE] Attempting manual sell for all holdings of token: {mint}")
        
        position_id_to_sell = None
        trigger_price_for_manual_sell = None
        market_cap_for_manual_sell = 0.0

        async with self.db.pool.acquire() as conn_manual_fetch:
            position_data = await conn_manual_fetch.fetchrow(
                "SELECT id, price AS buy_price, remaining_tokens FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' ORDER BY timestamp DESC LIMIT 1",
                mint
            )
            if not position_data:
                logger.warning(f"[{trading_mode.upper()}] No active buy position found for mint {mint} to execute manual sell.")
                await send_telegram_message(f"⚠️ Manual Sell Error: No active position for {mint}.")
                return
            
            if float(position_data['remaining_tokens']) <= 1e-9:
                logger.info(f"[{trading_mode.upper()}] No remaining tokens for active position of {mint}. Manual sell skipped.")
                await send_telegram_message(f"ℹ️ Manual Sell Info: No remaining tokens for {mint}.")
                return

            position_id_to_sell = position_data['id']
            
            price_data = await self.db.get_price_and_market_cap_for_decision(mint, self.config, conn_manual_fetch)
            trigger_price_for_manual_sell = price_data.get('price')
            market_cap_for_manual_sell = price_data.get('market_cap') if price_data.get('market_cap') is not None else 0.0

            if trigger_price_for_manual_sell is None or trigger_price_for_manual_sell <= 0:
                logger.error(f"[{trading_mode.upper()}] Cannot execute manual sell for {mint}: Invalid current price ({trigger_price_for_manual_sell}) for execution.")
                await send_telegram_message(f"⚠️ Manual Sell Error for {mint}: Could not determine a valid current price.")
                return

        logger.info(f"[{trading_mode.upper()} MODE] Proceeding with manual sell for {mint} (Pos ID: {position_id_to_sell}) at price {trigger_price_for_manual_sell:.9f}")

        # --- This must also acquire its own connection for the transaction ---
        async with self.db.pool.acquire() as conn_for_execute_sell: 
             await self.execute_sell(
                conn=conn_for_execute_sell, 
                mint=mint,
                trigger_price=trigger_price_for_manual_sell,
                market_cap_sol_at_trigger=market_cap_for_manual_sell,
                reason="manual_override",
                sell_percentage=1.0,  
                position_id_to_update=position_id_to_sell,
                sell_trigger_values={"command": f"SELL_{mint}", "manual_override_timestamp": datetime.now(timezone.utc).isoformat()}
            )
```

#### 📄 `utils.py`
*path: `utils.py`*

```python
# path: utils.py

"""
Helper functions and utilities for the trading bot.
Includes URL validation, audio alerts, and log formatting.
"""

import os
import asyncio
import pandas as pd
import pandas_ta as ta
import warnings # Add this import
import numpy as np
import json
from datetime import datetime, timezone, timedelta # <-- Added timedelta
from bot_logger import logger, Panel, Table, Text, Align, Group, rich_box
# Type hint for DatabaseClient without creating circular dependency
from typing import TYPE_CHECKING, Dict, Optional, Tuple, List
# For type hinting TradingBot instance without circular import
if TYPE_CHECKING:
    from trading_bot import TradingBot # Assuming trading_bot.py has TradingBot class
    from state_manager import GlobalState
    from database_handler import DatabaseClient
from urllib.parse import urlparse
import winsound


def is_valid_telegram(url: str) -> bool:
    """Validates if the provided URL is a valid Telegram link."""
    return url.startswith("https://t.me/") and "/joinchat/" not in url

def is_valid_twitter(url: str) -> bool:
    """Validates if the provided URL is a valid Twitter link."""
    return url.startswith(("https://twitter.com/", "https://x.com/"))

def is_valid_website(url: str) -> bool:
    """Validates if the provided URL is a proper website URL (not a social media domain)."""
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc not in ["x.com", "t.me", "telegram.org"]

def play_wav(file_path: str):
    """Synchronously plays a WAV file using winsound."""
    try:
        winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing the file {file_path}: {e}")

async def play_buy_opportunity_sound():
    """Asynchronously plays an alert sound for a buy opportunity."""
    import asyncio
    loop = asyncio.get_running_loop()
    wav_file = "assets/alert.wav"
    if not os.path.exists(wav_file):
        print(f"Sound file not found: {wav_file}")
        return
    await loop.run_in_executor(None, play_wav, wav_file)

def play_sell_sl_sound():
    """Synchronously play the stop-loss sell sound."""
    try:
        winsound.PlaySound("assets/hupe.wav", winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing sell SL sound: {e}")

def play_sell_tp_sound():
    """Synchronously play the take profit sell sound."""
    try:
        winsound.PlaySound("assets/ka_ching.wav", winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing sell TP sound: {e}")

async def play_sell_sl_sound_async():
    """Asynchronously play the stop-loss sell sound."""
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, play_sell_sl_sound)

async def play_sell_tp_sound_async():
    """Asynchronously play the take profit sell sound."""
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, play_sell_tp_sound)

def format_buy_order_log(state, name: str, mint: str, price_per_token: float, tokens_bought: float, market_cap: float, sol_price: float, total_investment: float, buy_reason: str, for_telegram: bool = False) -> str:
    """Formats the log message for a buy order with platform-specific links."""
    # URL construction
    base_url = "https://neo.bullx.io/terminal?chainId=1399811149&address="
    url = f"{base_url}{mint}"

    # Handle different platforms
    if for_telegram:
        #formatted_mint = f'<a href="{url}">{mint}</a>'
        formatted_mint = url
    else:
        # Use Rich markup for console hyperlinks
        # This requires `markup=True` in the RichHandler, which you have.
        formatted_mint = f"[link={url}]{mint}[/link]"

    # Handle name display with formatted mint
    token_display = f"{name} - {formatted_mint}" if name else formatted_mint

    # <<< 2. ADD REASON LOGIC >>>
    reason_emoji = "🧠" if buy_reason == "AI-Advised" else "⚙️"
    reason_text = f"│ {reason_emoji} Reason: {buy_reason}\n"
    # <<< END REASON LOGIC >>>
    
    if sol_price:
        price_usd = price_per_token * sol_price
        market_cap_usd = market_cap * sol_price
        total_usd = total_investment * sol_price
        return (
            f"★★★ 💲 BUY Order 💲 ★★★\n"
            f"│ Token: {token_display}\n"
            f"{reason_text}"  # <<< 3. ADDED LINE
            f"│ Price: {price_per_token:.8f} SOL (${price_usd:.8f} USD)\n"
            f"│ Market Cap: {market_cap:,.2f} SOL (${market_cap_usd:,.2f} USD)\n"
            f"│ Tokens Bought: {tokens_bought}\n"
            f"│ Total Investment: {total_investment} SOL (${total_usd:.2f} USD)\n"
            f"\n"
        )
    else:
        return (
            f"★★★ BUY Order ★★★\n"
            f"│ Token: {token_display}\n"
            f"{reason_text}"  # <<< 3. ADDED LINE
            f"│ Price: {price_per_token:.8f} SOL\n"
            f"│ Market Cap: {market_cap:,.2f} SOL\n"
            f"│ Tokens Bought: {tokens_bought}\n"
            f"│ Total Investment: {total_investment}\n"
        )
    

def format_sell_order_log(mint: str, token_name: str, market_cap_sol: float, profit: float, reason: str, sol_price: float | None, for_telegram: bool = False) -> str:
    """Formats the log message for a sell order."""
    profit_sign = "📈" if profit >= 0 else "📉"
    profit_text = f"{profit:+.6f} SOL" # Always show sign

    # MODIFICATION: Add emojis for display based on the clean reason string
    display_reason = reason # Default
    if "First TP" in reason: display_reason = f"🥇 {reason}"
    elif "Second TP" in reason: display_reason = f"🎯 {reason}"
    elif "Trailing SL" in reason: display_reason = f"↘️ {reason}"
    elif "Stop Loss" in reason: display_reason = f"🛑 {reason}"
    elif "Breakeven SL" in reason: display_reason = f"🛡️ {reason}"
    elif "Emergency SL" in reason: display_reason = f"🆘 {reason}"
    # 'manual_override' and other reasons are left as-is for clarity

    # URL construction
    base_url = "https://neo.bullx.io/terminal?chainId=1399811149&address="
    url = f"{base_url}{mint}"

    # Handle different platforms
    if for_telegram:
        #formatted_mint = f'<a href="{url}">{mint}</a>'
        formatted_mint = url
    else:
        ## Use Rich markup for console hyperlinks
        # This requires `markup=True` in the RichHandler, which you have.
        formatted_mint = f"[link={url}]{mint}[/link]"

    if sol_price and sol_price > 0:
        market_cap_usd = market_cap_sol * sol_price
        profit_usd = profit * sol_price
        profit_text += f" (${profit_usd:+.2f} USD)" # Add USD profit
        market_cap_text = f"{market_cap_sol:,.2f} SOL (${market_cap_usd:,.2f} USD)"
    else:
        # Handle case where SOL price might not be available
        market_cap_text = f"{market_cap_sol:,.2f} SOL (USD price unavailable)"
        profit_text += " (USD profit unavailable)"


    # Use token_name if available, otherwise just mint
    # https://neo.bullx.io/terminal?chainId=1399811149&address=3bgtCbZuXgFuHATFZmGcxKyyA6qtT8feEZV9gDSwpump
    display_name = f"{token_name} ({formatted_mint})" if token_name else mint

    return (
        f"*** {profit_sign} SELL Order ({display_reason}) {profit_sign} ***\n"
        f"│ Token: {display_name}\n"
        f"│ Market Cap: {market_cap_text}\n"
        f"│ Profit: {profit_text}\n"
    )
    

def calculate_social_score(social_data: dict, token_name: str, token_symbol: str) -> int:
    """Computes a social risk score based on provided social data."""
    total_penalty = 0
    token_name = (token_name or "").lower()
    token_symbol = (token_symbol or "").lower()
    
    website = social_data.get("website")
    if not website:
        total_penalty += 30
    else:
        if not is_valid_website(website):
            total_penalty += 20
        else:
            from urllib.parse import urlparse
            parsed = urlparse(website)
            domain = parsed.netloc
            if domain.endswith(f".{token_name}") or domain.endswith(f".{token_symbol}"):
                total_penalty -= 5
    
    telegram = social_data.get("telegram")
    if not telegram:
        total_penalty += 20
    else:
        if not is_valid_telegram(telegram):
            total_penalty += 10
    
    twitter = social_data.get("twitter")
    if not twitter:
        total_penalty += 20
    else:
        if not is_valid_twitter(twitter):
            total_penalty += 10
            
    return min(max(total_penalty, 0), 100)

def calculate_market_cap(vTokensInBondingCurve: float, vSolInBondingCurve: float, totalSupply: float, sol_price: float) -> float:
    """Calculates the market cap of a token using bonding curve data."""
    if vTokensInBondingCurve <= 0 or totalSupply <= 0:
        return 0.0
    price_per_token = vSolInBondingCurve / vTokensInBondingCurve
    return price_per_token * totalSupply * sol_price


def ensure_datetime(dt):
    """
    [CORRECTED] Ensures the input is a timezone-aware UTC datetime object.
    - If the input is a naive datetime, it's assumed to be in the system's local timezone and converted to UTC.
    - If the input is an aware datetime, it's converted to UTC.
    - If the input is a string, it's parsed as an ISO 8601 timestamp.
    """
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Naive datetime: assume local timezone, then convert to UTC for consistency.
            return dt.astimezone().astimezone(timezone.utc)
        else:
            # Aware datetime: simply convert to UTC.
            return dt.astimezone(timezone.utc)
    elif isinstance(dt, str):
        try:
            # Parse the string. fromisoformat creates a naive object if no tz is present.
            parsed_dt = datetime.fromisoformat(dt)
            # Now apply the same logic as for a datetime object.
            if parsed_dt.tzinfo is None:
                return parsed_dt.astimezone().astimezone(timezone.utc)
            else:
                return parsed_dt.astimezone(timezone.utc)
        except ValueError as e:
            raise ValueError(f"Unsupported date string format '{dt}': {e}") from e
    elif pd.isna(dt):
        return None # Handle pandas NaT (Not a Time)
    raise TypeError(f"Unsupported date type: {type(dt)}")

# --- [CORRECTED] Data Loading Function ---
async def load_and_split_data(
    db_client: 'DatabaseClient',
    start_date_dt: datetime,
    end_date_dt: datetime,
    data_split_ratios: Optional[Dict[str, float]], # Corrected argument name and made it optional
    min_data_points: int = 100
) -> Optional[Tuple[Dict, Dict[str, Dict[str, datetime]], Dict[str, pd.DataFrame]]]:
    """
    [CORRECTED] Loads and optionally splits historical data.
    - If data_split_ratios is None, returns all data in a single dictionary (for ETL).
    - If data_split_ratios is provided, splits data into train/validation/test sets.
    """
    if not db_client or not db_client.pool:
        logger.error("Database client not initialized or connected."); return None

    try:
        start_date = ensure_datetime(start_date_dt)
        end_date = ensure_datetime(end_date_dt)
        if not start_date or not end_date or start_date >= end_date:
            logger.error(f"Invalid date range: Start={start_date}, End={end_date}."); return None

        logger.info(f"Loading & splitting data. Identifying tokens in window: {start_date.isoformat()} to {end_date.isoformat()}")

        query_mints_lifespans = """
            WITH MintsInWindow AS (
                SELECT mint FROM v_trades WHERE timestamp >= $1 AND timestamp < $2
                UNION
                SELECT mint FROM v_tokens WHERE "timestamp" >= $1 AND "timestamp" < $2
            ),
            TokenStats AS (
                SELECT m.mint, MIN(t.timestamp) as first_trade_ts, MAX(t.timestamp) as last_trade_ts, COUNT(t.signature) as trade_count
                FROM MintsInWindow m JOIN v_trades t ON m.mint = t.mint
                GROUP BY m.mint
            )
            SELECT ts.mint, ts.first_trade_ts, ts.last_trade_ts, ts.trade_count
            FROM TokenStats ts
            LEFT JOIN v_tokens AS vt ON ts.mint = vt.mint
            WHERE ts.trade_count >= $3
              AND (vt.backup_reason NOT IN ('suspicious_creator', 'high_rugcheckscore') OR vt.backup_reason IS NULL);
        """
        candidate_records = await db_client.pool.fetch(query_mints_lifespans, start_date, end_date, min_data_points)
        
        if not candidate_records:
            logger.error(f"No tokens found that met the criteria (active in window, min trades: {min_data_points})."); return None
            
        token_lifespans_map = {r['mint']: {'start_ts': r['first_trade_ts'], 'end_ts': r['last_trade_ts']} for r in candidate_records if all(r.get(k) for k in ['mint', 'first_trade_ts', 'last_trade_ts'])}
        mints_to_load = list(token_lifespans_map.keys())
        
        if not mints_to_load: 
            logger.error("No valid mints with lifespans found after filtering."); return None
        
        logger.info(f"Found {len(mints_to_load)} candidate mints. Fetching their full historical data...")

        all_historical_data, dexscreener_snapshot_records = await asyncio.gather(
            db_client.get_historical_data_for_backtesting(mints_to_load, start_date=None, end_date=None),
            db_client.pool.fetch(
                "SELECT mint_address as mint, timestamp, liquidity_usd, buys_m5, sells_m5, volume_m5, price_change_m5 FROM v_dexscreener_data WHERE mint_address = ANY($1::text[]) ORDER BY mint_address, timestamp;",
                mints_to_load
            )
        )

        dexscreener_snapshots = {}
        if dexscreener_snapshot_records:
            df_snapshots = pd.DataFrame([dict(r) for r in dexscreener_snapshot_records])
            df_snapshots['timestamp'] = pd.to_datetime(df_snapshots['timestamp'], utc=True)
            for mint, group in df_snapshots.groupby('mint'):
                dexscreener_snapshots[mint] = group.set_index('timestamp').sort_index()
        logger.info(f"Fetched DexScreener snapshots for {len(dexscreener_snapshots)} migrated tokens.")

        if not all_historical_data:
            logger.error("Failed to fetch any historical OHLCV data for the candidate mints."); return None

        final_token_lifespans = {mint: token_lifespans_map[mint] for mint, df in all_historical_data.items() if mint in token_lifespans_map}
        
        # --- THIS IS THE FIX ---
        if data_split_ratios is None:
            # If no split config is given (ETL mode), return all data in a single dictionary.
            # No sorting is needed here as the optimizer will handle its own splitting.
            logger.info(f"Data splitting is disabled. Returning all {len(all_historical_data)} tokens.")
            return all_historical_data, final_token_lifespans, dexscreener_snapshots
        else:
            # Original GA optimizer mode: Split the data.
            sorted_mints = sorted(final_token_lifespans.keys(), key=lambda m: final_token_lifespans[m]['start_ts'])
            
            historical_data_sets = {}
            train_ratio = data_split_ratios.get('training', 0.6)
            val_ratio = data_split_ratios.get('validation', 0.2)
            
            train_idx = int(len(sorted_mints) * train_ratio)
            val_idx = train_idx + int(len(sorted_mints) * val_ratio)

            train_mints = sorted_mints[:train_idx]
            val_mints = sorted_mints[train_idx:val_idx]
            test_mints = sorted_mints[val_idx:]

            historical_data_sets['train'] = {m: all_historical_data[m] for m in train_mints if m in all_historical_data}
            historical_data_sets['validation'] = {m: all_historical_data[m] for m in val_mints if m in all_historical_data}
            historical_data_sets['test'] = {m: all_historical_data[m] for m in test_mints if m in all_historical_data}

            logger.info(f"Data split complete. Training: {len(historical_data_sets['train'])}, Validation: {len(historical_data_sets['validation'])}, Test: {len(historical_data_sets['test'])}")
            
            return historical_data_sets, final_token_lifespans, dexscreener_snapshots

    except Exception as e:
        logger.error(f"Unexpected error during data loading/splitting: {e}", exc_info=True)
        return None


def calculate_volatility(prices: pd.Series, window: int = 120) -> pd.Series: # <-- Return Series
    """
    Calculate rolling volatility based on log returns over a specified window.
    Returns the *entire Series* of volatility values. # <-- Modified docstring

    Args:
        prices (pd.Series): A pandas Series of prices, typically indexed by time.
        window (int): The rolling window size (number of periods).

    Returns:
        pd.Series: The calculated rolling volatility series, or an empty Series. # <-- Modified docstring
    """
    if prices is None or not isinstance(prices, pd.Series) or len(prices) < 2:
        return pd.Series(dtype=np.float64) # Return empty Series

    # Ensure prices are numeric and sorted by index if time-based
    prices = pd.to_numeric(prices, errors='coerce').dropna()
    if not np.all(np.diff(prices.index) >= pd.Timedelta(0)):
        prices = prices.sort_index() # Ensure chronological order

    if len(prices) < 2:
         return pd.Series(dtype=np.float64)

    # Calculate log returns, handling potential division by zero or invalid values
    log_returns = np.log(prices / prices.shift(1))
    log_returns = log_returns.replace([np.inf, -np.inf], np.nan).fillna(0) # Replace inf/NaN with 0

    # Calculate rolling standard deviation
    min_periods_required = max(2, window // 2)
    rolling_std = log_returns.rolling(window=window, min_periods=min_periods_required).std()

    # Annualize/Scale volatility
    volatility_series = rolling_std * np.sqrt(window)

    # Return the entire volatility Series
    return volatility_series.fillna(0.0) # Fill leading NaNs with 0

import os

def export_to_csv(historical_data_sets: Dict[str, Dict[str, pd.DataFrame]],
                 output_dir: str,
                 token_lifespans: Optional[Dict[str, Dict[str, datetime]]] = None):
    """
    Exports historical_data_sets (OHLCV) and token_lifespans to CSV files.

    Args:
        historical_data_sets: Dictionary of datasets containing OHLCV histories.
        output_dir: Directory to save the exports.
        token_lifespans: Optional dictionary containing token lifespan information.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Export datasets
    validation_report = []

    for dataset_key, dataset in historical_data_sets.items():
        dataset_dir = os.path.join(output_dir, dataset_key)
        os.makedirs(dataset_dir, exist_ok=True)

        for mint, df in dataset.items():
            # Data validation (using 'Close' price)
            # ---> FIX: Use 'Close' column for validation <---
            if 'Close' in df.columns:
                zero_prices = df['Close'].eq(0).sum()
                null_prices = df['Close'].isnull().sum()
            else:
                logger.warning(f"Column 'Close' not found in DataFrame for mint {mint} in dataset {dataset_key}. Skipping price validation.")
                zero_prices = 0
                null_prices = 0
            # ---> END FIX <---

            if zero_prices > 0 or null_prices > 0:
                validation_report.append({
                    'dataset': dataset_key,
                    'mint': mint,
                    'zero_prices': zero_prices,
                    'null_prices': null_prices,
                    'total_rows': len(df),
                    'start_ts': df.index[0] if not df.empty else None,
                    'end_ts': df.index[-1] if not df.empty else None
                })

            # Export OHLCV data
            csv_file = os.path.join(dataset_dir, f"{mint}_ohlcv.csv") # Changed filename suffix
            df.to_csv(csv_file, index=True)

            # Export lifespan data if available
            if token_lifespans and mint in token_lifespans:
                lifespan_file = os.path.join(dataset_dir, f"{mint}_lifespan.json")
                with open(lifespan_file, 'w') as f:
                    json.dump({
                        'mint': mint,
                        'start_ts': token_lifespans[mint]['start_ts'].isoformat() if token_lifespans[mint]['start_ts'] else None,
                        'end_ts': token_lifespans[mint]['end_ts'].isoformat() if token_lifespans[mint]['end_ts'] else None
                    }, f, indent=4)

    # Write validation report with lifespan comparison
    if validation_report:
        report_file = os.path.join(output_dir, "validation_report.txt")
        with open(report_file, 'w') as f:
            f.write("Data Validation Report\n")
            f.write("====================\n\n")
            for report in validation_report:
                f.write(f"Dataset: {report['dataset']}\n")
                f.write(f"Mint: {report['mint']}\n")
                f.write(f"Zero Close prices: {report['zero_prices']}\n") # Updated label
                f.write(f"Null Close prices: {report['null_prices']}\n") # Updated label
                f.write(f"Total rows: {report['total_rows']}\n")
                f.write(f"Data range: {report['start_ts']} to {report['end_ts']}\n")

                # Add lifespan info if available
                if token_lifespans and report['mint'] in token_lifespans:
                    lifespan = token_lifespans[report['mint']]
                    f.write(f"Token lifespan: {lifespan['start_ts']} to {lifespan['end_ts']}\n")
                f.write("--------------------\n")

        logger.warning(f"Found data quality issues (zero/null Close prices). Check {report_file} for details.")

    logger.info(f"Exported OHLCV data and lifespans to {output_dir}")

def calculate_trend_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Calculates a suite of technical indicators using pandas-ta.

    Args:
        df (pd.DataFrame): DataFrame with columns 'Open', 'High', 'Low', 'Close', 'Volume'.
        config (dict): The bot's configuration dictionary for periods.

    Returns:
        pd.DataFrame: The original DataFrame with new indicator columns appended.
    """
    if df.empty or len(df) < config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30):
        logger.debug(f"Not enough data to calculate indicators (Have: {len(df)}, Need: {config.get('MIN_CANDLE_DATA_FOR_INDICATORS', 30)}).")
        return pd.DataFrame()

    try:
        df_ta = df.copy()

        # --- BUG FIX: Set the timestamp as the index before calculating indicators ---
        if 'timestamp' in df_ta.columns:
            df_ta.set_index('timestamp', inplace=True)

        # --- BUG FIX START ---
        # Explicitly use the 'Close' column for indicators that operate on a single price series.
        # This prevents pandas-ta from returning a multi-column DataFrame when a single Series is expected.
        close_prices = df_ta['Close']

        # Calculate Bollinger Bands (this is usually fine as it uses H, L, C)
        bbands = df_ta.ta.bbands(length=config['BBANDS_PERIOD'], std=config['BBANDS_STD_DEV'], append=True)

        # Calculate RSI using the specified close price series
        df_ta.ta.rsi(close=close_prices, length=config['RSI_PERIOD'], append=True)

        # Calculate EMAs using the specified close price series
        df_ta.ta.ema(close=close_prices, length=config['FAST_EMA_PERIOD'], append=True, col_names=('EMA_fast',))
        df_ta.ta.ema(close=close_prices, length=config['SLOW_EMA_PERIOD'], append=True, col_names=('EMA_slow',))

        # Calculate ATR for the Chandelier Exit
        df_ta.ta.atr(length=config['ADAPTIVE_ATR_PERIOD'], append=True)

        # Calculate Parabolic SAR (optional, but good for confirmation strategies)
        df_ta.ta.psar(append=True)
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            # VWAP requires High, Low, Close, and Volume, which df_ta has.
            df_ta.ta.vwap(append=True)
        # --- BUG FIX END ---
        
        df_ta.dropna(inplace=True)
        
        #logger.debug(f"Successfully calculated indicators. Resulting data shape: {df_ta.shape}")
        return df_ta

    except Exception as e:
        logger.error(f"Error calculating indicators: {e}", exc_info=True)
        return pd.DataFrame()


class NpEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle NumPy, Pandas, and datetime types
    that are not serializable by default.
    """
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int_)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float_)):
            # Handle NaN, Infinity, -Infinity separately
            if np.isnan(obj):
                return None # Represent NaN as null in JSON
            elif np.isposinf(obj):
                return 'Infinity'
            elif np.isneginf(obj):
                return '-Infinity'
            else:
                return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist() # Convert arrays to lists
        elif isinstance(obj, (datetime, pd.Timestamp)):
            # Convert datetime/timestamp to ISO 8601 string format
            return obj.isoformat()
        # Let the base class default method raise the TypeError for unsupported types
        return super(NpEncoder, self).default(obj)
```