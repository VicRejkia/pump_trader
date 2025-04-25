"""
Helper functions and utilities for the trading bot.
Includes URL validation, audio alerts, and log formatting.
"""

import os
import asyncio # <-- Add if used implicitly by called async functions
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta # <-- Added timedelta
from logger import logger
# Type hint for DatabaseClient without creating circular dependency
from typing import TYPE_CHECKING, Dict, Optional
if TYPE_CHECKING:
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

def format_buy_order_log(state, name: str, mint: str, price_per_token: float, tokens_bought: float, market_cap: float, sol_price: float, total_investment: float) -> str:
    """Formats the log message for a buy order."""
    if sol_price:
        price_usd = price_per_token * sol_price
        market_cap_usd = market_cap * sol_price
        return (
            f"★★★ 💲 BUY Order 💲 ★★★\n"
            f"│ Token: {name} - {mint}\n"
            f"│ Price: {price_per_token:.8f} SOL (${price_usd:.8f} USD)\n"
            f"│ Market Cap: {market_cap:,.2f} SOL (${market_cap_usd:,.2f} USD)\n"
            f"│ Tokens Bought: {tokens_bought}\n"
            f"│ Total Investment: {total_investment}\n"
        )
    else:
        return (
            f"★★★ BUY Order ★★★\n"
            f"│ Token: {mint}\n"
            f"│ Price: {price_per_token:.8f} SOL\n"
            f"│ Market Cap: {market_cap:,.2f} SOL\n"
            f"│ Tokens Bought: {tokens_bought}\n"
            f"│ Total Investment: {total_investment}\n"
        )
    

def format_sell_order_log(mint: str, token_name: str, market_cap_sol: float, profit: float, reason: str, sol_price: float | None) -> str:
    """Formats the log message for a sell order."""
    profit_sign = "📈" if profit >= 0 else "📉"
    profit_text = f"{profit:+.6f} SOL" # Always show sign

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
    display_name = f"{token_name} ({mint})" if token_name else mint

    return (
        f"*** {profit_sign} SELL Order ({reason}) {profit_sign} ***\n"
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
    """Ensure the input is a timezone-aware UTC datetime object."""
    # ... (function code as provided) ...
    if isinstance(dt, datetime):
        # If naive, assume UTC. If aware, convert to UTC.
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        else:
            return dt.astimezone(timezone.utc)
    elif isinstance(dt, str):
        try:
            # Attempt to parse with and without time component
            try:
                 parsed_dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                 parsed_dt = datetime.strptime(dt, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return parsed_dt
        except ValueError as e:
            raise ValueError(f"Unsupported date string format '{dt}': {e}") from e
    elif pd.isna(dt): # Handle potential pandas NaT
        return None
    raise TypeError(f"Unsupported date type: {type(dt)}")

async def load_and_split_data(
    db_client: 'DatabaseClient',
    start_date_dt: datetime,
    end_date_dt: datetime,
    data_split_config: dict,
    min_data_points: int = 100 # Minimum data points required per token after fetching
) -> Optional[Dict[str, Dict[str, pd.DataFrame]]]:
    """
    Loads historical data for relevant tokens within a date range and splits
    it into training, validation, and test sets.
    """
    # ... (function code as provided) ...
    if not db_client or not db_client.pool:
        logger.error("Database client not initialized or connected.")
        return None

    try:
        start_date = ensure_datetime(start_date_dt)
        end_date = ensure_datetime(end_date_dt)
        if start_date >= end_date:
             logger.error(f"Start date ({start_date}) must be before end date ({end_date}).")
             return None

        logger.info(f"Attempting to load data from {start_date.isoformat()} to {end_date.isoformat()}")

        # --- Fetch candidate mints ---
        logger.info("Fetching list of mints with trades in the specified period...")
        query_mints_in_period = """
            SELECT mint, COUNT(*) as trade_count
            FROM v_trades
            WHERE timestamp >= $1 AND timestamp < $2
            GROUP BY mint
            HAVING COUNT(*) >= $3;
        """
        active_mints_records = await db_client.pool.fetch(query_mints_in_period, start_date, end_date, min_data_points)
        if not active_mints_records:
            logger.error(f"No tokens found with at least {min_data_points} trades in the specified period.")
            return None
        mints_to_load = [r['mint'] for r in active_mints_records]
        logger.info(f"Found {len(mints_to_load)} unique mints with >= {min_data_points} trades. Fetching detailed data...")

        # --- Fetch detailed historical data ---
        all_historical_data = await db_client.get_historical_data_for_backtesting(mints_to_load, start_date, end_date)

        if not all_historical_data:
            logger.error("Failed to fetch any historical data for the candidate mints.")
            return None
        logger.info(f"Successfully fetched data for {len(all_historical_data)} tokens.")

        # --- Split data chronologically ---
        historical_data_sets = {'train': {}, 'validation': {}, 'test': {}}
        total_duration_seconds = (end_date - start_date).total_seconds()
        if total_duration_seconds <= 0:
             logger.error("Total duration is zero or negative, cannot split data.")
             return None

        # Calculate split points based on seconds for precision
        train_end_seconds = start_date.timestamp() + total_duration_seconds * data_split_config['training']
        validation_end_seconds = train_end_seconds + total_duration_seconds * data_split_config['validation']

        train_end_dt = datetime.fromtimestamp(train_end_seconds, tz=timezone.utc)
        validation_end_dt = datetime.fromtimestamp(validation_end_seconds, tz=timezone.utc)

        logger.info(f"Data Split Timestamps: Train End={train_end_dt.isoformat()}, Validation End={validation_end_dt.isoformat()}")

        processed_count = 0
        for mint, df in all_historical_data.items():
            if df.empty or not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
                logger.warning(f"Skipping token {mint} due to empty data or invalid/naive index.")
                continue

            # Ensure data fully overlaps range before splitting
            if df.index.min() >= end_date or df.index.max() < start_date:
                logger.warning(f"Data for {mint} does not overlap with range {start_date}-{end_date}. Skipping.")
                continue

            # Filter strictly within the requested range *before* splitting
            df = df[(df.index >= start_date) & (df.index < end_date)]
            if df.empty:
                 logger.warning(f"No data remaining for {mint} after filtering by requested date range. Skipping.")
                 continue

            df_train = df[df.index < train_end_dt].copy()
            df_validation = df[(df.index >= train_end_dt) & (df.index < validation_end_dt)].copy()
            df_test = df[df.index >= validation_end_dt].copy()

            # Basic check for required columns (should be present after DB fetch)
            required_cols = ['price', 'volume', 'market_cap_calculated', 'rugcheck_score', 'socials_score']
            if not all(col in df.columns for col in required_cols):
                logger.warning(f"Token {mint} missing required columns. Columns present: {df.columns}. Skipping.")
                continue

            # Only include tokens that have data in the training set
            if not df_train.empty:
                historical_data_sets['train'][mint] = df_train
                if not df_validation.empty:
                    historical_data_sets['validation'][mint] = df_validation
                if not df_test.empty:
                    historical_data_sets['test'][mint] = df_test
                processed_count += 1
            else:
                 logger.warning(f"Token {mint} had no data points in the calculated training period ({start_date} to {train_end_dt}). Skipping.")


        if not historical_data_sets['train']:
             logger.error("No tokens had sufficient data for the training period after processing.")
             return None

        logger.info(f"Data split complete. Training tokens: {len(historical_data_sets['train'])}, Validation tokens: {len(historical_data_sets['validation'])}, Test tokens: {len(historical_data_sets['test'])}")
        return historical_data_sets

    except ValueError as ve:
        logger.exception(f"Date parsing or processing error: {ve}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error during data loading/splitting: {e}")
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