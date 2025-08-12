# rl_agent/data/inspect_cache.py
"""
Read, inspect, and export cached token_data.pkl to CSV — either per token or combined.
"""

import os
import pickle
import sys
import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def inspect_pickle(pickle_path: str, export_all: bool, export_mode: str, output_dir: str):
    """Load and inspect cached data. Optionally export all tokens to CSV."""
    if not os.path.exists(pickle_path):
        print(f"❌ File not found: {pickle_path}")
        return

    print(f"📂 Loading pickle file: {pickle_path}")
    try:
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)

        print("\n" + "="*60)
        print("🧩 PICKLE CONTENTS")
        print("="*60)

        if not isinstance(data, dict) or 'token_data' not in data:
            print("⚠️  Unexpected structure: Expected a dict with key 'token_data'.")
            print(f"🔍 Top-level type: {type(data).__name__}")
            print(f"🔍 Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
            return

        token_data = data['token_data']
        print(f"🗂️  'token_data' contains {len(token_data)} tokens.")

        # Show a few token names
        token_names = list(token_data.keys())
        print(f"🏷️  Sample tokens: {token_names[:10]}")
        if len(token_names) > 10:
            print(f"   ... and {len(token_names) - 10} more.")

        # Choose a sample token for preview
        target_token = None
        if 'BTC/USDT' in token_names:
            target_token = 'BTC/USDT'
        elif 'DDgsffDbSicfq5x4RALtWsqTXmNWd33gQqNRoexgpump' in token_names:
            target_token = 'DDgsffDbSicfq5x4RALtWsqTXmNWd33gQqNRoexgpump'
        else:
            target_token = token_names[1] if len(token_names) > 1 else token_names[0]

        df = token_data.get(target_token)
        if isinstance(df, pd.DataFrame):
            cols_to_drop = ['mint', 'Open', 'High', 'Low', 'price_change_30s']
            existing_cols_to_drop = [col for col in cols_to_drop if col in df.columns]
            df_preview = df.drop(columns=existing_cols_to_drop)

            print(f"\n📊 Preview of token: '{target_token}' (shape: {df.shape})")
            print(f"📈 Showing {len(df_preview.columns)} columns (removed: {existing_cols_to_drop})")
            print(df_preview.head(50).to_string())
        else:
            print(f"⚠️  Preview token '{target_token}' is not a DataFrame.")

        # --- EXPORT ENTIRE CACHE ---
        if export_all:
            os.makedirs(output_dir, exist_ok=True)
            print(f"\n📦 Exporting all token data to: {output_dir} (mode: {export_mode})")

            if export_mode == "per_token":
                # Save one CSV per token
                for symbol, df in token_data.items():
                    if not isinstance(df, pd.DataFrame):
                        continue
                    safe_symbol = symbol.replace("/", "_").replace("\\", "")
                    csv_path = os.path.join(output_dir, f"{safe_symbol}.csv")
                    df.to_csv(csv_path, index=True, index_label='timestamp')
                    print(f"💾 Saved {symbol} → {csv_path}")

            elif export_mode == "combined":
                # Combine all into one DataFrame with a 'token' column
                combined_dfs = []
                for symbol, df in token_data.items():
                    if not isinstance(df, pd.DataFrame):
                        continue
                    df = df.copy()
                    df['token'] = symbol
                    combined_dfs.append(df)

                if combined_dfs:
                    full_df = pd.concat(combined_dfs, ignore_index=False)  # Keep original index
                    csv_path = os.path.join(output_dir, "all_tokens_combined.csv")
                    
                    # Option A: Save index as 'timestamp' column
                    full_df.to_csv(csv_path, index=True, index_label='timestamp')
                    
                    # Option B: Reset index to make timestamp a regular column (recommended)
                    # full_df_reset = full_df.reset_index()
                    # full_df_reset.to_csv(csv_path, index=False)

                    print(f"💾 Saved combined DataFrame → {csv_path}")
                else:
                    print("⚠️  No valid DataFrames to combine.")

        print("\n" + "="*60)
        print("✅ Inspection complete.")

    except Exception as e:
        print(f"💥 Failed to load or inspect pickle: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inspect and optionally export all data from token_data.pkl.")

    # Input selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cache-dir", type=str, help="Path to cache directory (e.g., rl_agent/data/cache/20250626_20250627)")
    group.add_argument("--start-date", type=str, help="Start date in YYYYMMDD format")
    group.add_argument("--end-date", type=str, help="End date in YYYYMMDD format")

    # Export options
    parser.add_argument("--export-all", action="store_true", help="Export all tokens to CSV")
    parser.add_argument(
        "--mode", choices=["per_token", "combined"], default="per_token",
        help="Export mode: 'per_token' (one file per token), 'combined' (single CSV)"
    )
    parser.add_argument("--output-dir", type=str, default="exports", help="Output directory for CSV files (default: 'exports')")

    args = parser.parse_args()

    # Resolve pickle path
    if args.cache_dir:
        pickle_path = os.path.join(args.cache_dir, "token_data.pkl")
    else:
        date_str = f"{args.start_date}_{args.end_date}"
        pickle_path = os.path.join(project_root, "rl_agent", "data", "cache", date_str, "token_data.pkl")

    # Run inspection
    inspect_pickle(
        pickle_path=pickle_path,
        export_all=args.export_all,
        export_mode=args.mode,
        output_dir=args.output_dir
    )