# rl_agent/etl/prepare_rl_dataset.py
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
    python rl_agent/etl/prepare_rl_dataset.py \
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
from rl_agent.feature_engineering.features import calculate_all_features


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