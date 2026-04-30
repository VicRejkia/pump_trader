# FILE: GA_Optimizer/ga_ingestion.py

import asyncio
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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
