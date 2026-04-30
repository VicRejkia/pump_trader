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
from config.ga_config import HISTORICAL_DATA_END_TS, HISTORICAL_DATA_START_TS
from database_handler import DatabaseClient
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
