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


async def format_task_monitor_rich(bot: 'TradingBot') -> Panel:
    """
    Formats the task monitor status into a Rich Panel.
    Args:
        bot: The TradingBot instance.
    Returns:
        A Rich Panel object.
    """
    try:
        sol_amount = await bot.state.get_current_sol_balance()
        tokens_subscribed_list = await bot.state.get_token_subscriptions()
        tokens_subscribed_count = len(tokens_subscribed_list)
        rug_queue_size = bot.state.get_rugcheck_queue().qsize()
        socials_queue_size = bot.state.get_socialscheck_queue().qsize()
        
        open_trades_count_display: Text | str = Text("N/A", style="white")
        if bot.db_client and bot.db_client.pool:
            try:
                active_positions = await bot.db_client.get_active_buy_positions()
                open_trades_count_display = Text(str(len(active_positions)), style="yellow")
            except Exception as e_db:
                logger.error(f"Error fetching open trades count for monitor: {e_db}")
                open_trades_count_display = Text("Error", style="bold red")

        # --- Summary Table ---
        summary_table = Table(show_header=False, box=None, padding=(0, 1, 0, 0))
        summary_table.add_column(style="dim cyan", justify="right", width=20)
        summary_table.add_column(justify="left")

        rl_agent_status_msg = Text("Loaded & Active", style="green") if bot.rl_agent else Text("Not Loaded", style="dim white")
        summary_table.add_row(":brain: RL Agent:", rl_agent_status_msg)
        summary_table.add_row(":moneybag: SOL Balance:", Text(f"{sol_amount:.4f}", style="green"))
        summary_table.add_row(":link: Subscribed Tokens:", Text(str(tokens_subscribed_count), style="magenta"))
        summary_table.add_row(":bar_chart: Open Trades:", open_trades_count_display) # Already a Text object
        summary_table.add_row(":mag_right: RugCheck Queue:", Text(str(rug_queue_size), style="blue"))
        summary_table.add_row(":busts_in_silhouette: Socials Queue:", Text(str(socials_queue_size), style="blue"))
        summary_table.add_row(":gear: Managed Tasks:", Text(f"{len([t for t in bot.tasks if not t.done()])}/{len(bot.tasks)}", style="white"))

        # --- Task Details Table ---
        task_table = Table(box=rich_box.MINIMAL, show_header=True, header_style="bold cyan", padding=(0,1,0,0), title_justify="left")
        task_table.add_column("Task Name", style="cyan", no_wrap=True, min_width=25)
        task_table.add_column("Status", style="white", min_width=20)

        for task in bot.tasks:
            task_name = task.get_name()
            status_text = Text()
            if task_name == "buy_opportunity_checker":
                if not bot.state.is_buying_enabled:
                    status_text.append("paused", style="yellow")
                    status_text.append(" (buys disabled)", style="dim yellow")
                elif task.done():
                    status_text.append("done", style="red")
                    if task.exception():
                        status_text.append(f" (Error: {task.exception()!r})", style="dim red")
                else:
                    status_text.append("running", style="green")
            else:
                if task.done():
                    status_text.append("done", style="red")
                    if task.exception():
                        status_text.append(f" (Error: {task.exception()!r})", style="dim red")
                else:
                    status_text.append("running", style="green")
            task_table.add_row(task_name, status_text)
        
        panel_content = Group(summary_table, task_table)

        final_panel = Panel(
            panel_content,
            title="[bold magenta]:robot: Bot Task Monitor[/bold magenta]",
            border_style="cyan",
            expand=False,
            padding=(1,2)
        )
        return final_panel
    except Exception as e:
        logger.error(f"Failed to format task monitor: {e}", exc_info=True)
        return Panel(Text(f"Error generating task monitor: {e!r}", style="bold red"), border_style="red")
# async def format_task_monitor_rich(bot: 'TradingBot') -> Panel:
#     logger.info("format_task_monitor_rich: Returning EXTREMELY simple panel for testing.") # Use the actual logger
#     return Panel(Text("Simple Test Panel Content", style="bold green"), title="[bold blue]Test Simple Panel[/bold blue]", border_style="red")

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

def format_buy_order_log(state, name: str, mint: str, price_per_token: float, tokens_bought: float, market_cap: float, sol_price: float, total_investment: float, for_telegram: bool = False) -> str:
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
    if sol_price:
        price_usd = price_per_token * sol_price
        market_cap_usd = market_cap * sol_price
        total_usd = total_investment * sol_price
        return (
            f"★★★ 💲 BUY Order 💲 ★★★\n"
            f"│ Token: {token_display}\n"
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
            f"│ Price: {price_per_token:.8f} SOL\n"
            f"│ Market Cap: {market_cap:,.2f} SOL\n"
            f"│ Tokens Bought: {tokens_bought}\n"
            f"│ Total Investment: {total_investment}\n"
        )
    

def format_sell_order_log(mint: str, token_name: str, market_cap_sol: float, profit: float, reason: str, sol_price: float | None, for_telegram: bool = False) -> str:
    """Formats the log message for a sell order."""
    profit_sign = "📈" if profit >= 0 else "📉"
    profit_text = f"{profit:+.6f} SOL" # Always show sign

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
    min_data_points: int = 100 # Minimum *trades* required per token
) -> Optional[Tuple[Dict[str, Dict[str, pd.DataFrame]], Dict[str, Dict[str, datetime]], Dict[str, pd.DataFrame]]]:
    """
    [MODIFIED] Loads historical data, lifespans, and DexScreener snapshots, then splits
    tokens chronologically into training, validation, and test sets.

    Returns:
        A tuple containing:
        - historical_data_sets (dict): {'train': {mint: ohlcv_df}, ...}
        - token_lifespans (dict): {mint: {'start_ts': dt, 'end_ts': dt}}
        - dexscreener_snapshots (dict): {mint: snapshot_df} for migrated tokens.
        Returns None if loading or splitting fails.
    """
    if not db_client or not db_client.pool:
        logger.error("Database client not initialized or connected.")
        return None

    try:
        start_date = ensure_datetime(start_date_dt)
        end_date = ensure_datetime(end_date_dt)
        if not start_date or not end_date or start_date >= end_date:
             logger.error(f"Invalid date range: Start={start_date}, End={end_date}.")
             return None

        logger.info(f"Loading & splitting data. Overall Period: {start_date.isoformat()} to {end_date.isoformat()}")

        # --- Step 1: Fetch candidate mints and their lifespans (No change here) ---
        # (This part of the logic remains the same as the previous version)
        query_mints_lifespans = """
            WITH RankedTrades AS (
                SELECT
                    mint,
                    timestamp,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp ASC) as rn_asc,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn_desc
                FROM v_trades
                WHERE timestamp >= $1 AND timestamp < $2
            ),
            MintCounts AS (
                SELECT mint, COUNT(*) as trade_count
                FROM v_trades
                WHERE timestamp >= $1 AND timestamp < $2
                GROUP BY mint
                HAVING COUNT(*) >= $3
            )
            SELECT
                mc.mint,
                MIN(rt.timestamp) FILTER (WHERE rt.rn_asc = 1) as first_trade_ts,
                MAX(rt.timestamp) FILTER (WHERE rt.rn_desc = 1) as last_trade_ts,
                mc.trade_count
            FROM MintCounts mc
            JOIN RankedTrades rt ON mc.mint = rt.mint
            LEFT JOIN v_tokens AS vt ON mc.mint = vt.mint
            WHERE (rt.rn_asc = 1 OR rt.rn_desc = 1)
                AND (vt.backup_reason = 'rugged_dead' OR vt.backup_reason = '')
            GROUP BY mc.mint, mc.trade_count;
        """
        candidate_records = await db_client.pool.fetch(query_mints_lifespans, start_date, end_date, min_data_points)
        if not candidate_records:
            logger.error(f"No tokens found with at least {min_data_points} trades in the specified period.")
            return None
        token_lifespans_map = {r['mint']: {'start_ts': r['first_trade_ts'], 'end_ts': r['last_trade_ts']} for r in candidate_records if r['mint'] and r['first_trade_ts'] and r['last_trade_ts']}
        mints_to_load = list(token_lifespans_map.keys())
        if not mints_to_load: return None
        logger.info(f"Found {len(mints_to_load)} candidate mints. Fetching detailed data...")


        # --- Step 2: Fetch OHLCV data and DexScreener snapshot data concurrently ---
        dexscreener_snapshot_query = """
            SELECT
                mint_address as mint, timestamp, liquidity_usd, buys_m5, sells_m5
            FROM v_dexscreener_data
            WHERE mint_address = ANY($1::text[])
            AND timestamp >= $2 AND timestamp < $3
            ORDER BY mint_address, timestamp;
        """
        all_historical_data, dexscreener_snapshot_records = await asyncio.gather(
            db_client.get_historical_data_for_backtesting(mints_to_load, start_date, end_date),
            db_client.pool.fetch(dexscreener_snapshot_query, mints_to_load, start_date, end_date)
        )

        if not all_historical_data:
            logger.error("Failed to fetch any historical OHLCV data for the candidate mints.")
            return None

        # Process DexScreener snapshots into a dictionary of DataFrames
        dexscreener_snapshots = {}
        if dexscreener_snapshot_records:
            df_snapshots = pd.DataFrame([dict(r) for r in dexscreener_snapshot_records])
            df_snapshots['timestamp'] = pd.to_datetime(df_snapshots['timestamp'], utc=True)
            for mint, group in df_snapshots.groupby('mint'):
                dexscreener_snapshots[mint] = group.set_index('timestamp').sort_index()
        logger.info(f"Fetched DexScreener snapshots for {len(dexscreener_snapshots)} migrated tokens.")

        # --- Step 3: Filter and Split (No change here) ---
        final_token_lifespans = {}
        for mint, df in all_historical_data.items():
            if mint in token_lifespans_map:
                final_token_lifespans[mint] = token_lifespans_map[mint]
        
        sorted_mints = sorted(final_token_lifespans.keys(), key=lambda m: final_token_lifespans[m]['start_ts'])
        n_tokens = len(sorted_mints)
        n_train = int(n_tokens * data_split_config['training'])
        n_val = int(n_tokens * data_split_config['validation'])
        historical_data_sets = {'train': {}, 'validation': {}, 'test': {}}
        for i, mint in enumerate(sorted_mints):
            if mint in all_historical_data:
                if i < n_train:
                    historical_data_sets['train'][mint] = all_historical_data[mint]
                elif i < n_train + n_val:
                    historical_data_sets['validation'][mint] = all_historical_data[mint]
                else:
                    historical_data_sets['test'][mint] = all_historical_data[mint]
        
        logger.info(f"Data split complete. Training tokens: {len(historical_data_sets['train'])}, Validation tokens: {len(historical_data_sets['validation'])}, Test tokens: {len(historical_data_sets['test'])}")
        if not historical_data_sets['train']:
             logger.error("Training set is empty after chronological splitting!")
             return None

        # Return all three data dictionaries
        return historical_data_sets, final_token_lifespans, dexscreener_snapshots

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
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            # VWAP requires High, Low, Close, and Volume, which df_ta has.
            df_ta.ta.vwap(append=True)
        # --- BUG FIX END ---
        
        df_ta.dropna(inplace=True)
        
        logger.debug(f"Successfully calculated indicators. Resulting data shape: {df_ta.shape}")
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