# test_ai_decision_maker_with_bot.py
"""
Standalone test script for AI Decision Maker using bot's codebase.
Usage: python test_ai_decision_maker_with_bot.py <token_mint>

- Fetches data for the given mint from DB and APIs.
- Distinguishes between PumpPortal (non-migrated) and DexScreener (migrated) sources.
- Builds current_data dict.
- Queries AI for advice.
- Optionally loads sample historical data to RAG.
"""

import sys
import asyncio
import datetime as dt  # Use alias to avoid module/class confusion

# Import bot modules (adjust paths if needed)
from bot_logger import logger, setup_logging
from config.config import *  # All config vars
from database_handler import DatabaseClient
from state_manager import GlobalState
from utils import calculate_volatility, ensure_datetime  # For volatility calc
import pandas as pd  # For volatility (if needed)

# AI module (assume you have it)
from ai_decision_maker import AIDecisionMaker

async def is_token_migrated(db: DatabaseClient, mint: str) -> bool:
    """
    Check if token is migrated (e.g., from Pump.fun to Raydium).
    - Query DB for migration status or recent DexScreener data.
    - Returns True if migrated (has DexScreener snapshots).
    """
    async with db.pool.acquire() as conn:
        has_dex_data = await conn.fetchval(
            "SELECT COUNT(*) > 0 FROM dexscreener_data WHERE mint_address = $1 LIMIT 1",
            mint
        )
    if has_dex_data:
        logger.info(f"Token {mint} is migrated (has DexScreener data).")
        return True
    else:
        logger.info(f"Token {mint} is non-migrated (using PumpPortal).")
        return False

async def fetch_pumpportal_data(db: DatabaseClient, mint: str) -> dict:
    """
    Fetch data for non-migrated token from PumpPortal (DB trades/tokens tables).
    - Uses recent trades to compute price, MC, volatility, etc.
    - Assumes data is in DB from WebSocket.
    - Refactored: Tokens table has name, symbol, traderspublickey (as creator).
    - Market cap from latest trade: marketcapsol (SOL), market_cap_calculated (USD).
    - Volume USD: sum(sol_amount * sol_price_usd) over recent trades (assuming sol_amount positive for trades).
    - Price: median/mean of (sol_amount / token_amount) over recent trades.
    """
    async with db.pool.acquire() as conn:
        # Get latest token metadata from tokens table (no market_cap here)
        token_data = await conn.fetchrow(
            "SELECT name, symbol, traderpublickey AS creator, timestamp FROM tokens WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1",
            mint
        )
        if not token_data:
            raise ValueError(f"No token data found for mint {mint} in DB.")

        # Get recent trades for calculations (last PRICE_AVG_WINDOW_MINUTES min)
        # Include sol_price_usd for volume calc, marketcapsol, market_cap_calculated
        end_time = dt.datetime.now(tz=dt.timezone.utc)
        start_time = end_time - dt.timedelta(minutes=PRICE_AVG_WINDOW_MINUTES)
        trades = await conn.fetch(
            "SELECT timestamp, sol_amount, token_amount, marketcapsol, market_cap_calculated, sol_price_usd FROM trades "
            "WHERE mint = $1 AND timestamp BETWEEN $2 AND $3 ORDER BY timestamp",
            mint, ensure_datetime(start_time), ensure_datetime(end_time)
        )
        if not trades:
            raise ValueError(f"No recent trades for mint {mint}.")

        # Convert to DataFrame and set timestamp as index (for time-based sorting/check in volatility)
        df_trades = pd.DataFrame([dict(r) for r in trades])
        df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'], utc=True)  # Ensure datetime
        df_trades.set_index('timestamp', inplace=True)
        df_trades.sort_index(inplace=True)

        # Compute price per trade: sol_amount / token_amount (assume positive for buys; if mixed, filter if is_buy exists)
        # Assuming trades table has only buys or sol_amount positive; adjust if needed
        prices = (df_trades['sol_amount'] / df_trades['token_amount']).dropna()
        price = prices.median() if PRICE_DETERMINATION_METHOD == "MEDIAN" else prices.mean()

        # Market cap: From latest trade
        latest_trade = df_trades.iloc[-1]
        market_cap_sol = latest_trade['marketcapsol']
        market_cap_usd = latest_trade['market_cap_calculated']

        # Volatility: On price series (now with time index)
        volatility_series = calculate_volatility(prices)
        volatility = volatility_series.iloc[-1] if not volatility_series.empty else 0.0

        # Rugcheck & Social (from their tables)
        rugcheck = await conn.fetchval("SELECT score FROM rugcheck WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1", mint) or 0
        social = await conn.fetchval("SELECT score_value as score FROM social_scores WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1", mint) or 0

        # Volume USD: sum(sol_amount * sol_price_usd) (assuming sol_amount is the SOL value traded)
        volume_usd = (df_trades['sol_amount'] * df_trades['sol_price_usd']).sum()

        return {
            'source': 'PumpPortal',
            'mint': mint,
            'name': token_data['name'],
            'price': price,
            'market_cap': market_cap_usd,
            'volatility': volatility,
            'rugcheck_score': rugcheck,
            'social_score': social,
            'volume': volume_usd,
            'dex_trends': {}  # No Dex trends for non-migrated
        }

async def fetch_dexscreener_data(db: DatabaseClient, mint: str) -> dict:
    """
    Fetch data for migrated token from database (dexscreener_data table).
    - Queries the latest and recent snapshots for price, MC, trends, volatility.
    - Uses sol_price_usd from snapshots for conversions.
    """
    async with db.pool.acquire() as conn:
        # Get latest DexScreener snapshot for price, MC, trends; include sol_price_usd
        latest_data = await conn.fetchrow(
            """
            SELECT 
                mint_address AS mint,
                timestamp,
                price_usd,
                fdv AS market_cap_usd,
                volume_h24 AS volume,
                price_change_m5,
                buys_m5,
                sells_m5,
                volume_m5,
                liquidity_usd,
                sol_price_usd
            FROM dexscreener_data 
            WHERE mint_address = $1 
            ORDER BY timestamp DESC 
            LIMIT 1
            """,
            mint
        )
        if not latest_data:
            raise ValueError(f"No DexScreener data found for mint {mint} in DB.")

        # Get token name from tokens table
        token_name = await conn.fetchval(
            "SELECT name FROM tokens WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1",
            mint
        ) or 'Unknown'

        # Get recent snapshots for volatility (last PRICE_AVG_WINDOW_MINUTES min); include price_usd
        end_time = dt.datetime.now(tz=dt.timezone.utc)
        start_time = end_time - dt.timedelta(minutes=PRICE_AVG_WINDOW_MINUTES)
        snapshots = await conn.fetch(
            "SELECT timestamp, price_usd FROM dexscreener_data "
            "WHERE mint_address = $1 AND timestamp BETWEEN $2 AND $3 ORDER BY timestamp",
            mint, ensure_datetime(start_time), ensure_datetime(end_time)
        )
        volatility = 0.0
        if snapshots:
            df_snapshots = pd.DataFrame([dict(r) for r in snapshots])
            df_snapshots['timestamp'] = pd.to_datetime(df_snapshots['timestamp'], utc=True)
            df_snapshots.set_index('timestamp', inplace=True)
            df_snapshots.sort_index(inplace=True)
            prices = df_snapshots['price_usd'].dropna()
            volatility_series = calculate_volatility(prices)
            volatility = volatility_series.iloc[-1] if not volatility_series.empty else 0.0

        # Rugcheck & Social (from DB)
        rugcheck = await conn.fetchval("SELECT score FROM rugcheck WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1", mint) or 0
        social = await conn.fetchval("SELECT score FROM social_scores WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1", mint) or 0

        # Trends from latest
        trends = {
            'price_change_m5': latest_data['price_change_m5'] or 0.0,
            'buys_m5': latest_data['buys_m5'] or 0,
            'sells_m5': latest_data['sells_m5'] or 0,
            'volume_m5': latest_data['volume_m5'] or 0.0
        }

        # Price in SOL: price_usd / sol_price_usd from latest snapshot
        sol_price = latest_data['sol_price_usd']
        price_sol = latest_data['price_usd'] / sol_price if sol_price > 0 else 0.0

        return {
            'source': 'DexScreener',
            'mint': mint,
            'name': token_name,
            'price': price_sol,
            'market_cap': latest_data['market_cap_usd'] or 0.0,
            'volatility': volatility,
            'rugcheck_score': rugcheck,
            'social_score': social,
            'volume': latest_data['volume'] or 0.0,
            'dex_trends': trends
        }

async def main(mint: str):
    setup_logging()  # Init logger
    state = GlobalState()  # Bot state (keep for consistency, even if unused here)
    db = DatabaseClient()  # Init DB
    await db.connect()  # Connect to DB
    ai = AIDecisionMaker()  # AI init

    try:
        # Optional: Load historical to RAG (comment out if not needed for test)
        # await load_historical_to_rag(ai, db)  # Implement if desired, similar to earlier example

        # Check migration
        migrated = await is_token_migrated(db, mint)

        # Fetch data based on source
        if migrated:
            current_data = await fetch_dexscreener_data(db, mint)
        else:
            current_data = await fetch_pumpportal_data(db, mint)

        logger.info(f"Fetched data for {mint} from {current_data['source']}: {current_data}")

        # Get AI advice
        advice = ai.get_trade_advice(current_data)
        logger.info("AI Advice: %s", advice)

    except Exception as e:
        logger.error("Error in test: %s", e)
    finally:
        await db.close()  # Cleanup

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ai_decision_maker_with_bot.py <token_mint>")
        sys.exit(1)
    mint_arg = sys.argv[1]
    asyncio.run(main(mint_arg))