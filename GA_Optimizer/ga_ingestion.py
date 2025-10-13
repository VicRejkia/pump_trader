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
DEFAULT_LOG_FILE_PATH = project_root / "ga_optimization_results" / "ga_detailed_trade_log.jsonl"

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

# --- Main Ingestion Logic (Refactored for Bulk Processing) ---
async def ingest_log_file_bulk(pool: asyncpg.Pool, file_path: str):
    """
    Reads the entire .jsonl log file, processes it with pandas, and bulk-inserts
    the data into the database for maximum performance.
    """
    if not os.path.exists(file_path):
        print(f"Error: Log file not found at '{file_path}'")
        return

    print("Reading log file into memory...")
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        if not lines:
            print("Log file is empty. Nothing to ingest.")
            return
        records = [json.loads(line) for line in lines]
        df = pd.DataFrame(records)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error reading or parsing log file: {e}")
        return

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
        id_map_df = pd.DataFrame(returned_ids, columns=['solution_id', 'run_id', 'generation', 'solution_idx'])
        
        # --- FIX 1: Robustly merge and cast solution_id ---
        df = pd.merge(df, id_map_df, on=['run_id', 'generation', 'solution_idx'], how='left')
        if df['solution_id'].isnull().any():
            print(f"Warning: {df['solution_id'].isnull().sum()} records failed to match a solution_id and will be dropped.")
            df.dropna(subset=['solution_id'], inplace=True)
        df['solution_id'] = df['solution_id'].astype(int)
        # --- END FIX 1 ---

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
    
    # --- FIX 2: Sanitize ALL numeric metrics, including `total_trades` ---
    numeric_metric_cols = [
        'final_portfolio_value', 'total_pnl', 'total_return_pct', 'win_rate',
        'profit_factor', 'max_drawdown', 'total_trades'
    ]
    for col in numeric_metric_cols:
        if col in backtests_df.columns:
            backtests_df[col] = backtests_df[col].apply(sanitize_metric)
    # --- END FIX 2 ---
    
    backtests_df['simulation_start_ts'] = backtests_df['simulation_start_ts'].apply(parse_iso_datetime)
    backtests_df['simulation_end_ts'] = backtests_df['simulation_end_ts'].apply(parse_iso_datetime)
    
    async with pool.acquire() as conn:
        stmt_bt = await conn.prepare(f"""
            INSERT INTO ga_backtests ({', '.join(backtest_cols)})
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
    # --- FIX 3: Robustly handle and cast backtest_id ---
    if df['backtest_id'].isnull().any():
        print(f"Warning: {df['backtest_id'].isnull().sum()} records could not be matched to a backtest_id and will be dropped before trade ingestion.")
        df.dropna(subset=['backtest_id'], inplace=True)

    if df.empty:
        print("No valid records remain after filtering. No trades to ingest.")
        return # Exit if no data is left

    df['backtest_id'] = df['backtest_id'].astype(int)
    # --- END FIX 3 ---
    
    trades_df = df[df['trade_history'].apply(lambda x: isinstance(x, list) and len(x) > 0)][['backtest_id', 'trade_history']]
    if not trades_df.empty:
        trades_exploded = trades_df.explode('trade_history').reset_index(drop=True)
        trade_details = pd.json_normalize(trades_exploded['trade_history'])
        final_trades_df = pd.concat([trades_exploded[['backtest_id']], trade_details], axis=1)

        final_trades_df.rename(columns={'timestamp': 'trade_timestamp'}, inplace=True)
        trade_cols_to_ingest = ['backtest_id', 'trade_timestamp', 'type', 'price', 'amount_sol', 'amount_tokens', 'reason', 'pnl']
        final_trades_df = final_trades_df.reindex(columns=trade_cols_to_ingest)
        
        final_trades_df['trade_timestamp'] = final_trades_df['trade_timestamp'].apply(parse_iso_datetime)
        for col in ['price', 'amount_sol', 'amount_tokens', 'pnl']:
            final_trades_df[col] = final_trades_df[col].apply(sanitize_metric)

        async with pool.acquire() as conn:
            affected_backtest_ids = final_trades_df['backtest_id'].unique().tolist()
            # It's safer to delete only from the backtests we are about to re-insert trades for
            if affected_backtest_ids:
                await conn.execute("DELETE FROM ga_trades WHERE backtest_id = ANY($1::int[])", affected_backtest_ids)
            
            await conn.copy_records_to_table('ga_trades', records=final_trades_df.to_records(index=False), columns=['backtest_id', 'timestamp', 'type', 'price', 'amount_sol', 'amount_tokens', 'reason', 'pnl'])
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
    asyncio.run(run_ingestion(DEFAULT_LOG_FILE_PATH))