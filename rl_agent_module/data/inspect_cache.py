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