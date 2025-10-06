# FILE: GA_Optimizer/ga_ingestion.py

import asyncio
import json
import os
import math
from pathlib import Path
from typing import Dict, Any
from datetime import datetime # Import the datetime object

import asyncpg
from dotenv import load_dotenv
from tqdm import tqdm

# --- ROBUST .ENV LOADING ---
script_location = Path(__file__).resolve().parent
project_root = script_location.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
raw_db_host = os.getenv("DB_HOST")
db_host_val = None
db_port_val = 5432

if raw_db_host:
    if ":" in raw_db_host:
        try:
            host, port_str = raw_db_host.split(":")
            db_host_val = host
            db_port_val = int(port_str)
        except ValueError:
            print(f"Warning: Could not parse DB_HOST '{raw_db_host}'. Using defaults.")
            db_host_val = "localhost"
    else:
        db_host_val = raw_db_host

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE"),
    "host": db_host_val,
    "port": db_port_val
}

DEFAULT_LOG_FILE_PATH = project_root / "ga_optimization_results" / "ga_detailed_trade_log.jsonl"


async def ingest_log_file(pool: asyncpg.Pool, file_path: str):
    """
    Reads the .jsonl log file and inserts its contents into the database.
    """
    if not os.path.exists(file_path):
        print(f"Error: Log file not found at '{file_path}'")
        return

    with open(file_path, 'r') as f:
        total_lines = sum(1 for _ in f)
    
    if total_lines == 0:
        print("Log file is empty. Nothing to ingest.")
        return
        
    print(f"Starting ingestion of {total_lines} records from '{file_path}'...")

    with open(file_path, 'r') as f:
        error_count = 0
        for line in tqdm(f, total=total_lines, desc="Ingesting Logs"):
            try:
                record = json.loads(line)
                await process_record(pool, record)
            except json.JSONDecodeError:
                print(f"Warning: Skipping malformed JSON line: {line.strip()}")
            except Exception as e:
                error_count += 1
                if error_count < 5:
                    print(f"An error occurred while processing a record: {e}")
                    print(f"Problematic record: {line.strip()}")
        if error_count > 0:
            print(f"Warning: A total of {error_count} records encountered errors during ingestion.")

def sanitize_metric(value):
    """Replaces non-finite numbers (inf, -inf, nan) with None."""
    if value is None or isinstance(value, str):
        return None
    if not math.isfinite(value):
        return None
    return value

def parse_iso_datetime(ts_string: str | None) -> datetime | None:
    """Converts an ISO format string to a datetime object, handling None."""
    if ts_string is None:
        return None
    try:
        return datetime.fromisoformat(ts_string)
    except (ValueError, TypeError):
        return None

async def process_record(pool: asyncpg.Pool, record: Dict[str, Any]):
    """
    Processes a single JSON record, sanitizes values, and inserts data.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO ga_runs (run_id) VALUES ($1) ON CONFLICT (run_id) DO NOTHING",
                record["run_id"]
            )

            solution_id = await conn.fetchval(
                """
                INSERT INTO ga_solutions (run_id, generation, solution_idx, parameters)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (run_id, generation, solution_idx) DO UPDATE
                SET parameters = EXCLUDED.parameters
                RETURNING id
                """,
                record["run_id"], record["generation"],
                record["solution_idx"], json.dumps(record.get("parameters", {}))
            )

            # Sanitize metrics and PARSE TIMESTAMPS before insertion
            final_portfolio_value = sanitize_metric(record.get("final_portfolio_value"))
            total_pnl = sanitize_metric(record.get("total_pnl"))
            total_return_pct = sanitize_metric(record.get("total_return_pct"))
            win_rate = sanitize_metric(record.get("win_rate"))
            profit_factor = sanitize_metric(record.get("profit_factor"))
            max_drawdown = sanitize_metric(record.get("max_drawdown"))
            simulation_start_ts = parse_iso_datetime(record.get("simulation_start_ts"))
            simulation_end_ts = parse_iso_datetime(record.get("simulation_end_ts"))

            backtest_id = await conn.fetchval(
                """
                INSERT INTO ga_backtests (
                    solution_id, mint_tested, status, error_message,
                    final_portfolio_value, total_pnl, total_return_pct,
                    win_rate, profit_factor, max_drawdown, total_trades,
                    simulation_start_ts, simulation_end_ts, simulation_end_reason
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (solution_id, mint_tested) DO NOTHING
                RETURNING id
                """,
                solution_id, record.get("mint_tested"), record.get("status"),
                record.get("error_message"), final_portfolio_value, total_pnl,
                total_return_pct, win_rate, profit_factor, max_drawdown,
                record.get("total_trades"), simulation_start_ts,
                simulation_end_ts, record.get("simulation_end_reason")
            )

            if not backtest_id:
                backtest_id = await conn.fetchval(
                    "SELECT id FROM ga_backtests WHERE solution_id = $1 AND mint_tested = $2",
                    solution_id, record.get("mint_tested")
                )

            if backtest_id and "trade_history" in record and record["trade_history"]:
                await conn.execute("DELETE FROM ga_trades WHERE backtest_id = $1", backtest_id)
                
                trades = record["trade_history"]
                trade_data_to_insert = [
                    (
                        backtest_id,
                        parse_iso_datetime(trade.get("timestamp")), # PARSE trade timestamp
                        trade.get("type"),
                        sanitize_metric(trade.get("price")),
                        sanitize_metric(trade.get("amount_sol")),
                        sanitize_metric(trade.get("amount_tokens")),
                        trade.get("reason"),
                        sanitize_metric(trade.get("pnl"))
                    ) for trade in trades
                ]
                
                await conn.copy_records_to_table(
                    'ga_trades', records=trade_data_to_insert,
                    columns=[
                        'backtest_id', 'timestamp', 'type', 'price',
                        'amount_sol', 'amount_tokens', 'reason', 'pnl'
                    ]
                )

async def run_ingestion(log_file_path: str):
    """
    Main entry point function to set up the DB pool and run the ingestion.
    """
    if not all([DB_CONFIG["user"], DB_CONFIG["password"], DB_CONFIG["database"], DB_CONFIG["host"]]):
        print("Error: Database credentials are not fully configured in the .env file.")
        print("Skipping database ingestion.")
        return
        
    pool = await asyncpg.create_pool(**DB_CONFIG)
    try:
        await ingest_log_file(pool, log_file_path)
    finally:
        await pool.close()
    print("Database ingestion process finished.")

if __name__ == "__main__":
    print("Running ingestion script in standalone mode...")
    asyncio.run(run_ingestion(DEFAULT_LOG_FILE_PATH))