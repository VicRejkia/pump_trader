# path: utils.py

"""
Helper functions and utilities for the trading bot.
Includes URL validation, audio alerts, and log formatting.
"""

import asyncio
import json
import os
import warnings  # Add this import
from datetime import datetime, timedelta, timezone  # <-- Added timedelta

# Type hint for DatabaseClient without creating circular dependency
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import ta as ta_lib

from bot_logger import Align, Group, Panel, Table, Text, logger, rich_box

# For type hinting TradingBot instance without circular import
if TYPE_CHECKING:
    from database_handler import DatabaseClient
    from state_manager import GlobalState
    from trading_bot import TradingBot  # Assuming trading_bot.py has TradingBot class
from urllib.parse import urlparse

try:
    import winsound
    _WINSOUND_AVAILABLE = True
except ImportError:
    _WINSOUND_AVAILABLE = False


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
    if not _WINSOUND_AVAILABLE:
        return
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
    if not _WINSOUND_AVAILABLE:
        return
    try:
        winsound.PlaySound("assets/hupe.wav", winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing sell SL sound: {e}")

def play_sell_tp_sound():
    """Synchronously play the take profit sell sound."""
    if not _WINSOUND_AVAILABLE:
        return
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

        if 'timestamp' in df_ta.columns:
            df_ta.set_index('timestamp', inplace=True)

        close = df_ta['Close']
        high = df_ta['High']
        low = df_ta['Low']
        volume = df_ta['Volume']

        bb_period = config['BBANDS_PERIOD']
        bb_std = config['BBANDS_STD_DEV']
        bb = ta_lib.volatility.BollingerBands(close=close, window=bb_period, window_dev=bb_std)
        df_ta[f'BBL_{bb_period}_{bb_std}'] = bb.bollinger_lband()
        df_ta[f'BBM_{bb_period}_{bb_std}'] = bb.bollinger_mavg()
        df_ta[f'BBU_{bb_period}_{bb_std}'] = bb.bollinger_hband()

        rsi_period = config['RSI_PERIOD']
        df_ta[f'RSI_{rsi_period}'] = ta_lib.momentum.RSIIndicator(close=close, window=rsi_period).rsi()

        df_ta['EMA_fast'] = ta_lib.trend.EMAIndicator(close=close, window=config['FAST_EMA_PERIOD']).ema_indicator()
        df_ta['EMA_slow'] = ta_lib.trend.EMAIndicator(close=close, window=config['SLOW_EMA_PERIOD']).ema_indicator()

        atr_period = config['ADAPTIVE_ATR_PERIOD']
        df_ta[f'ATRr_{atr_period}'] = ta_lib.volatility.AverageTrueRange(
            high=high, low=low, close=close, window=atr_period
        ).average_true_range()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            df_ta['VWAP'] = ta_lib.volume.VolumeWeightedAveragePrice(
                high=high, low=low, close=close, volume=volume
            ).volume_weighted_average_price()

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
