# `pump_trader` Project Files

📅 Generated on: 2025-05-01 16:16

📂 Project root: `C:/Users/Sascha/Documents/Projects/python/crypto/pump_trader`

---

### 📄 config.py

```python
"""
Configuration constants and settings for the trading bot.
"""

from datetime import timedelta

""" Configuration constants and settings for the trading bot. """

# Trading configuration
SOL_TO_BUY = 0.9                            # Amount of SOL to spend on each buy
INITIAL_SOL_BALANCE = 100.0                  # Starting SOL balance for PnL tracking
PLAY_BUY_SOUND = True                      # Play the buy sound when a buy is made
PLAY_SELL_SOUND = True                     # Play the sell sound when a sell is made

# --- New Multi-Stage Sell Logic Configuration ---
INITIAL_STOP_LOSS_PERCENT = 10.0            # Initial SL as % below buy price (e.g., 25.0 for -25%)
# INITIAL_TAKE_PROFIT_PERCENT is removed as TP1 price is now calculated based on investment, costs, and margin.
FIRST_SELL_PERCENT = 65.0                   # % of *initial* tokens to sell at First TP (e.g., 50.0 for 50%)
TRAILING_STOP_LOSS_PERCENT = 15.0           # Trailing SL % drop from highest price *after* First TP (e.g., 15.0 for -15%)
SECOND_TAKE_PROFIT_PERCENT = 550.0          # Second TP as % above buy price (e.g., 200.0 for +200%)
FIRST_SELL_PROFIT_MARGIN = 170.0             # Desired profit margin % on the *total initial investment* for the first TP sell

# --- Fees and Tips ---
DEFAULT_BUY_FEE = 0.001                     # Fee for buying in SOL
DEFAULT_BUY_TIP = 0.001                     # Tip for buying in SOL
DEFAULT_SELL_FEE = 0.001                    # Fee for selling in SOL
DEFAULT_SELL_TIP = 0.001                    # Tip for selling in SOL

# Trading thresholds
DEFAULT_RUGCHECK_SCORE_THRESHOLD = 801      # No trading if Rugcheck score is equal or above this threshold
DEFAULT_SOCIAL_SCORE_THRESHOLD = 50         # No trading if Social score is equal or above this threshold
DEFAULT_VOLUME_THRESHOLD = 19000            # Minimum volume threshold in USD
MIN_MARKETCAP_THRESHOLD = 6000              # Minimum market cap threshold in USD to make emergency sell
DEFAULT_MARKETCAP_THRESHOLD = 10000         # Minimum market cap threshold in USD to search for buy opportunities
MIN_VOLATILITY = 0.1                        # Minimum volatility threshold in % to search for buy opportunities
DEFAULT_TIME_INTERVALL = 30                 # Time interval for checking volatility, volume and marketcap in minutes
MAX_DRAWDOWN_SOL = 10                       # Maximum allowed 24h loss in SOL (not integrated)
DRAWDOWN_CHECK_INTERVAL = 3600              # Drawdown check interval (seconds) (not integrated)

# UNSUBSCRIBING CONDITIONS
INACTIVITY_PERIOD = timedelta(minutes=10)
MIN_MARKET_CAP = 3600                       # Minimum market cap (in USD)

# Subscription tracking
ACTIVE_SUBSCRIPTIONS = set()                # leave it alone
NEW_TOKEN_SUBSCRIPTION = False              # leave it alone

# PumpPortal
WS_HOST: str = "wss://pumpportal.fun/api/data"
MAX_SUBSCRIPTION_BATCH: int = 100           # For batch unsubscription

# Token and API configurations
TOTAL_SUPPLY = 1000000000                   # Assumed total supply if not provided
PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"

RUGCHECK_AUTH_API = "https://api.rugcheck.xyz/auth/login/solana"
RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens"
RUGCHECK_RATE_LIMIT = 10                    # 10 requests per minute
RUGCHECK_INTERVAL = 60                      # 60 seconds interval for RugCheck checks
RUGCHECK_SCORE_THRESHOLD = 1002             # Score above which a token is considered high risk and deactivated

# SOL price configuration
SOL_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# Logging
LOGGER_NAME = "TradingBot"
LOG_LEVEL_CONSOLE: str = "DEBUG"
LOG_LEVEL_FILE: str = "DEBUG"
LOG_STORAGE_PATH = "log"

# --- Socials Processor Configuration ---
SOCIALS_CHECK_REFRESH_INTERVAL = 60                  # Timeout for requeing socials check in minutes
SOCIALS_DISALLOWED_WEBSITE_DOMAINS = {
    "youtube.com", "youtu.be", "tiktok.com", "spotify.com", "soundcloud.com",
    "discord.com", "discord.gg", "medium.com", "substack.com", "linktr.ee",
    "t.me", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "reddit.com", "twitch.tv", "kick.com", "google.com",
}
SOCIALS_ALLOWED_NEWS_DOMAINS = {
    "bbc.com", "cnn.com", "reuters.com", "apnews.com", "nytimes.com",
    "washingtonpost.com", "theguardian.com", "bloomberg.com", "forbes.com",
    "wsj.com", "ft.com", "npr.org", "cnbc.com", "abcnews.go.com",
    "nbcnews.com", "cbsnews.com", "latimes.com", "usatoday.com",
    "politico.com", "aljazeera.com", "theatlantic.com", "newsweek.com",
    "time.com", "economist.com", "sky.com", "independent.co.uk",
    "telegraph.co.uk", "dailymail.co.uk", "mirror.co.uk", "huffpost.com",
    "vox.com", "slate.com", "buzzfeednews.com", "axios.com", "thehill.com",
    "scmp.com", "japantimes.co.jp", "hindustantimes.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "straitstimes.com", "smh.com.au",
    "theage.com.au", "globalnews.ca", "cbc.ca", "bitcointalk.org",
    "cnbcnews.us", "truthsocial.com"
}

# Penalties (Higher = Worse)
SOCIALS_PENALTY_NO_WEBSITE = 40
SOCIALS_PENALTY_INVALID_WEBSITE_TYPE = 35
SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED = 35
SOCIALS_PENALTY_WEBSITE_INVALID_URL = 35
SOCIALS_PENALTY_WEBSITE_TIMEOUT = 35
SOCIALS_PENALTY_WEBSITE_HTTP_ERROR = 35
SOCIALS_PENALTY_WEBSITE_OTHER_ERROR = 35
SOCIALS_PENALTY_NO_HTTPS = 10
SOCIALS_PENALTY_WEBSITE_NO_MENTION = 10         # No mention of token name or symbol in website
SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE = 25    # Common platforms like Youtube, TikTok, etc. 'SOCIALS_DISALLOWED_WEBSITE_DOMAINS'
SOCIALS_PENALTY_NO_TELEGRAM = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_URL = 25
SOCIALS_PENALTY_NO_TWITTER = 25
SOCIALS_PENALTY_INVALID_TWITTER_TYPE = 25
SOCIALS_PENALTY_INVALID_TWITTER_URL = 25
SOCIALS_PENALTY_DUPLICATE_LINKS = 15            # Duplicate links in metadata
SOCIALS_PENALTY_ACTION_TRIGGER_URL = 15         # Action trigger URL in metadata

# Bonuses (Negative = Better)
SOCIALS_BONUS_DOMAIN_MATCH = -10                # Bonus if domain mentions token name or symbol
SOCIALS_BONUS_NEWS_GOV_WEBSITE = 0              # No penalty/bonus currently applied for news/gov sites in 'SOCIALS_ALLOWED_NEWS_DOMAINS'

# Default Scores
SOCIALS_SCORE_FAILED_METADATA = 100             # Score assigned if metadata fetch fails
```

---

### 📄 database_handler.py

```python
"""
Database module.
Handles PostgreSQL connections and CRUD operations.
"""

import os
import glob
from datetime import datetime, timezone,timedelta
import asyncio
import asyncpg
import aiofiles
import json
import pandas as pd
from dotenv import load_dotenv
from logger import logger
import config
from state_manager import GlobalState
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple # Added List, Tuple
from utils import calculate_volatility

# Load environment variables from .env file
load_dotenv()

# Construct the database URL from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?options=-c%20timezone%3Dutc"

class DatabaseClient:
    """Client to manage database connections and operations."""
    
    def __init__(self):
        self.pool = None
        self.state = GlobalState.get_instance()

    async def connect(self):
        """Establish a connection pool to the PostgreSQL database."""
        try:
            # Use the DB_URL constructed from environment variables
            self.pool = await asyncpg.create_pool(dsn=DB_URL)
            logger.info("Connected to the database successfully.")
        except Exception as e:
            logger.exception("Error connecting to the database: %s", e)
            raise

    async def init_db(self):
        """
        Initialize the database schema by reading and executing all SQL files 
        from the 'sql' subfolder. Additionally, restore the creator_wallets 
        table from the backup file if necessary.
        """
        sql_folder = os.path.join(os.path.dirname(__file__), "sql")
        sql_files = sorted(glob.glob(os.path.join(sql_folder, "*.sql")))
        
        async with self.pool.acquire() as conn:
            # Execute schema SQL files
            for file_path in sql_files:
                try:
                    with open(file_path, "r") as f:
                        sql = f.read()
                    await conn.execute(sql)
                    logger.info("Executed SQL file: %s", os.path.basename(file_path))
                except Exception as e:
                    logger.exception("Error executing SQL file %s: %s", os.path.basename(file_path), e)
                    raise

    async def insert_sol_price(self, price: float, timestamp: datetime = datetime.now(timezone.utc)):
        """Insert a new SOL price into the database."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO sol_price_usd (price, timestamp) VALUES ($1, $2)", price, timestamp)
        except Exception as e:
            logger.exception("Error inserting SOL price into the database: %s", e)
            raise

    async def insert_token(self, data: dict):
        """Checks if the token is valid and stores it if conditions are met."""
        async with self.pool.acquire() as conn:
            mint = data.get('mint')
            if not mint:
                logger.warning("Mint address is missing in the token data.")
                return False
            try:
                async with conn.transaction():
                    # 1. Check if token already exists in tokens or tokens_backup
                    token_exists = await conn.fetchval("""
                        SELECT 1 FROM tokens WHERE mint = $1
                        UNION
                        SELECT 1 FROM tokens_backup WHERE mint = $1
                    """, mint)
                    if token_exists:
                        logger.info(f"Token {mint} is already stored. Skipping.")
                        return False  # Token already exists, no need to insert

                    # 2. Check how many tokens the creator has recently created
                    creator = data.get('traderPublicKey')
                    now = datetime.now(timezone.utc)
                    row = await conn.fetchrow(
                        "SELECT token_count, last_token_time FROM creator_wallets WHERE wallet_address = $1",
                        creator
                    )
                    
                    token_count = 1
                    if row:
                        token_count, last_token_time = row
                        if last_token_time and (now - last_token_time).total_seconds() < 604800:
                            token_count += 1

                        await conn.execute(
                            "UPDATE creator_wallets SET token_count = $1, last_token_time = $2 WHERE wallet_address = $3",
                            token_count, now, creator
                        )
                    else:
                        await conn.execute(
                            "INSERT INTO creator_wallets (wallet_address, token_count, last_token_time) VALUES ($1, $2, $3)",
                            creator, token_count, now
                        )

                    if token_count > 2:
                            logger.debug(f"🤬 [bold red]Suspicious creator[/bold red] %s for token %s with %s tokens in 7 days", creator, data['mint'], token_count)
                            return False

                    sol_price = await self.state.get_sol_price()
                    if sol_price is None or sol_price <= 0:
                        logger.warning(f"⚠ Invalid SOL_PRICE ({sol_price}); skipping insert token operation.")
                        return # Cannot proceed without valid SOL price
                    
                    # 3. Insert/update token
                    await conn.execute("""
                        INSERT INTO tokens(mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, 
                            vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri, sol_price_usd,
                            is_active, timestamp)
                        VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, True, NOW());
                        """, 
                        data.get('mint'), 
                        data.get('traderPublicKey'), 
                        data.get('initialBuy'), 
                        data.get('solAmount'), 
                        data.get('bondingCurveKey'), 
                        data.get('vTokensInBondingCurve'),
                        data.get('vSolInBondingCurve'), 
                        data.get('marketCapSol'), 
                        data.get('name'),
                        data.get('symbol'), 
                        data.get('uri'),
                        sol_price
                    )
                    logger.debug("Inserted/Updated token %s", data.get('mint'))
                    return True
            except Exception as e:
                logger.exception("Error inserting token data: %s", e)
                raise

    async def insert_migration(self, data: dict):
        """Batch-insert trade data into trades table."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                            INSERT INTO migrations (signature, mint, txType, pool)
                            VALUES ($1, $2, $3, $4)
                        ''',data["signature"], data["mint"], data["txType"], data["pool"])

                        logger.debug(f"Stored migration event for token {data['mint']}")
                    except Exception as e:
                        logger.error(f"❌ Storing migration for {data['mint']} failed: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f"🚨 Error on storing migration: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def insert_trades_batch(self, trade_params: list, mints: list):
        """
        Inserts a batch of trades into the database and updates the last_trade timestamp for the tokens.
        """
        if not trade_params:
            return

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Batch insert trades
                    await conn.executemany('''
                        INSERT INTO trades (
                            signature, mint, tx_type, token_amount, sol_amount, price,
                            bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
                            marketCapSol,sol_price_usd, market_cap_calculated, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        ON CONFLICT (signature) DO NOTHING
                    ''', trade_params)

                    # Batch update last_trade timestamps
                    if mints:
                        # Ensure mints are unique before updating
                        unique_mints = list(set(mints))
                        await conn.execute('''
                            UPDATE tokens
                            SET last_trade = NOW()
                            WHERE mint = ANY($1::text[])
                        ''', unique_mints)

                    logger.debug(f"✅ Processed {len(trade_params)} trades in batch")

                except Exception as e:
                    logger.error(f"🚨 Error during batch trade insert: {e}", exc_info=True)
                    # The transaction will be rolled back automatically
                    raise # Re-raise the exception so the caller knows about the failure

    async def get_tokens_to_unsubscribe(self, sol_price, min_market_cap):
        """Fetch tokens that should be unsubscribed based on market cap and activity."""
        query = """
            SELECT t.mint
            FROM tokens t
            INNER JOIN (
                SELECT mint, marketCapSol, timestamp AS lt,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM trades
            ) latest ON t.mint = latest.mint AND latest.rn = 1
            WHERE 
                ((latest.marketCapSol * $1) < $2 AND
                t.timestamp <= NOW() - INTERVAL '15 minutes') OR
				latest.lt <= NOW() - INTERVAL '60 minutes'
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
			ORDER BY timestamp DESC
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, sol_price, min_market_cap)

    async def get_active_tokens(self, limit: int = 1000):
        """Fetch active tokens from the database."""
        query = """
            SELECT mint FROM tokens WHERE is_active = True
            ORDER BY timestamp DESC LIMIT $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, limit)
        
    async def is_suspicious_creator(self, creator: str):
        """Check if a creator is suspicious based on the number of tokens created."""
        query = """
            SELECT token_count FROM creator_wallets WHERE wallet_address = $1
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, creator)
            if row and row['token_count'] > 2:
                return True
            return False

    async def fetch_tokens_by_creator(self, creator: str, respect_portfolio: bool = False):
        if respect_portfolio:
            query = """
                SELECT mint FROM tokens 
                WHERE traderpublickey = $1
                    AND mint NOT IN (SELECT mint FROM portfolio)
            """
        else:
            query = """
                SELECT mint FROM tokens 
                WHERE traderpublickey = $1
            """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, creator)
        
    async def has_active_buy_order(self, mint: str):
        query = """
            SELECT 1 FROM portfolio WHERE mint = $1 AND tx_type = 'buy' AND status = 'active'
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, mint)
            return result is not None
        
    async def get_total_supply(self, mint: str):
        """Fetch the total supply of a token."""
        query = """
            SELECT total_supply FROM rugcheck WHERE mint = $1
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, mint)
            return result['total_supply'] if result else config.TOTAL_SUPPLY


    async def find_trading_opportunities(self, sol_price: float, volume_threshold: float, marketcap_threshold: float, rugcheck_threshold: int, social_score_threshold: int, time_interval_minutes: int, min_volatility: float):
        """
        Identify potential token buy opportunities based on trading activity, volatility, and risk metrics.
        
        Criteria:
        - Analyzes trades within a rolling time window ($6 minutes)
        - Filters by volume, market cap, volatility, and risk scores
        - Excludes tokens already in active portfolio positions

        CTEs:
        1. LatestTradeData: Gets most recent trade price/status for each token
            - Uses row_number() to select latest trade per mint
        2. RecentTrades: Calculates buy/sell volume and trade count
            - total_buys_recent: SOL spent on buys
            - total_sells_recent: SOL received from sells
            - volume_recent: Total trading volume (SOL)
        3. VolatilityData: Computes price volatility using log returns
            - log_return = LN(price/previous_price)
            - volatility = STDDEV(log_return) * SQRT(return_count)
            - Requires min 5 valid returns

        Main Query:
        - Joins token data with rugcheck scores and latest trade metrics
        - Converts SOL values to USD using $1 (SOL price)
        - Filters tokens where:
            * rugcheck_score < $4 AND socials_score < $5
            * (volume_recent * SOL_price) >= volume_threshold
            * (market_cap * SOL_price) >= marketcap_threshold
            * volatility >= min_volatility
            * NOT already in active portfolio positions
        - Orders by descending recent volume

        Parameters (Bound in Query):
        $1: sol_price (float)           - Current SOL/USD price for conversions
        $2: volume_threshold (float)    - Min USD trading volume requirement
        $3: marketcap_threshold (float) - Min USD market cap requirement
        $4: rugcheck_threshold (float)  - Max allowed security risk score
        $5: social_score_threshold (float) - Max allowed social risk score
        $6: time_interval_minutes (int) - Analysis window duration (minutes)
        $7: min_volatility (float)      - Min price volatility requirement

        Volatility Calculation:
        Computed as standard deviation of log returns multiplied by sqrt(n):
        volatility = STDDEV(LN(price/prev_price)) * SQRT(GREATEST(COUNT(*), 1))
        - Uses natural log for continuous compounding returns
        - Multiplied by sqrt(n) to estimate volatility over full time window
        - Requires min 5 valid price changes

        Returns:
        List of candidate tokens sorted by volume, with metrics including:
        - Latest price, market cap, bonding curve balances
        - Recent volume/volatility metrics
        - Token metadata and risk scores
        """
        
        query = """
            WITH LatestTradeData AS (
                SELECT
                    mint,
                    price,
                    marketCapSol,
                    vTokensInBondingCurve,
                    vSolInBondingCurve,
                    timestamp,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM trades
                WHERE timestamp >= NOW() - ($6 || ' minutes')::interval
            ),
            RecentTrades AS (
                SELECT
                    mint,
                    SUM(CASE WHEN tx_type = 'buy' THEN sol_amount ELSE 0 END) AS total_buys_recent,
                    SUM(CASE WHEN tx_type = 'sell' THEN sol_amount ELSE 0 END) AS total_sells_recent,
                    SUM(sol_amount) AS volume_recent,
                    COUNT(*) as trade_count
                FROM trades
                WHERE timestamp >= NOW() - ($6 || ' minutes')::interval
                GROUP BY mint
            ),
            VolatilityData AS (
                SELECT
                    mint,
                    STDDEV(log_return) * SQRT(GREATEST(COUNT(*), 1)) AS volatility
                FROM (
                    SELECT
                        mint,
                        price,
                        LAG(price) OVER (PARTITION BY mint ORDER BY timestamp) AS prev_price,
                        CASE
                            WHEN price > 0 AND LAG(price) OVER (PARTITION BY mint ORDER BY timestamp) > 0
                            THEN LN(price / LAG(price) OVER (PARTITION BY mint ORDER BY timestamp))
                            ELSE NULL
                        END AS log_return
                    FROM trades
                    WHERE timestamp >= NOW() - ($6 || ' minutes')::interval
                ) sub
                WHERE log_return IS NOT NULL
                GROUP BY mint
                HAVING COUNT(*) > 5
            )
            SELECT
                t.mint,
                t.marketCapSol,
                t.vTokensInBondingCurve,
                t.vSolInBondingCurve,
                COALESCE(ltd.marketCapSol, t.marketCapSol) AS latest_market_cap_sol,
                COALESCE(ltd.vTokensInBondingCurve, t.vTokensInBondingCurve) AS latest_v_tokens,
                COALESCE(ltd.vSolInBondingCurve, t.vSolInBondingCurve) AS latest_v_sol,
                COALESCE(ltd.price, 0) AS latest_price,
                COALESCE(rt.volume_recent, 0) AS volume_in_interval,
                COALESCE(vd.volatility, 0) AS volatility_in_interval,
                r.tokenMeta_name AS name,
                r.tokenMeta_symbol AS symbol,
                r.score AS rugcheck_score,
                t.socials_score
            FROM tokens AS t
            JOIN rugcheck AS r ON t.mint = r.mint
            JOIN LatestTradeData AS ltd ON t.mint = ltd.mint AND ltd.rn = 1
            LEFT JOIN RecentTrades AS rt ON t.mint = rt.mint
            LEFT JOIN VolatilityData AS vd ON t.mint = vd.mint
            WHERE
                t.is_active = TRUE AND
                r.score IS NOT NULL AND
                t.socials_score IS NOT NULL AND
                r.score < $4 AND
                t.socials_score < $5 AND
                (COALESCE(rt.volume_recent, 0) * $1) >= $2 AND
                (COALESCE(ltd.marketCapSol, t.marketCapSol, 0) * $1) >= $3 AND
                COALESCE(vd.volatility, 0) >= $7 AND
                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
            ORDER BY rt.volume_recent DESC;
        """
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch(query, sol_price, volume_threshold, marketcap_threshold, rugcheck_threshold, social_score_threshold, str(time_interval_minutes), min_volatility)
            except Exception as e:
                logger.error(f"Error finding trading opportunities: {e}", exc_info=True)
                return [] # Return empty list on error

    async def get_active_buy_positions(self, conn=None):
        """Fetches active buy positions from the portfolio."""
        query = '''
            SELECT id, mint, price AS buy_price, initial_tokens, remaining_tokens, total_investment_sol,
                   stop_loss_price, highest_price, initial_tp_price, second_tp_price, first_tp_hit
            FROM portfolio
            WHERE status = 'active' AND tx_type = 'buy'
        '''
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetch(query)
        finally:
            if not conn and connection: # Release connection only if it was acquired here
                await self.pool.release(connection)

    async def get_latest_prices(self, mints: list[str], conn=None):
        """Fetches the latest price and market cap for a list of mints."""
        if not mints:
            return {}
        query = f'''
            WITH LatestTrades AS (
                SELECT
                    mint,
                    price,
                    marketCapSol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                FROM trades
                WHERE mint = ANY($1::text[])
            )
            SELECT mint, price, marketCapSol FROM LatestTrades WHERE rn = 1
        '''
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, mints)
            return {row['mint']: {'price': float(row['price']), 'market_cap': float(row['marketcapsol'])}
                    for row in rows if row['price'] is not None and float(row['price']) > 0}
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def update_portfolio_highest_price(self, position_id: int, price: float, conn=None):
        """Updates the highest price for a given portfolio position."""
        query = 'UPDATE portfolio SET highest_price = $1 WHERE id = $2'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, price, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def mark_first_tp_hit_and_adjust_sl(self, position_id: int, buy_price: float, conn=None):
        """Marks the first TP as hit and adjusts the stop loss to breakeven."""
        query = 'UPDATE portfolio SET first_tp_hit = TRUE, stop_loss_price = $1 WHERE id = $2'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, buy_price, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_portfolio_entry_for_update(self, position_id: int, conn=None):
        """Fetches a specific portfolio buy entry needed for sell calculations."""
        query = '''
            SELECT price AS buy_price, initial_tokens, remaining_tokens, total_investment_sol, fee AS buy_fee, tip AS buy_tip
            FROM portfolio
            WHERE id = $1 AND status = 'active' AND tx_type = 'buy'
        '''
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def update_portfolio_entry_after_sell(self, position_id: int, new_remaining_tokens: float, new_status: str, conn=None):
        """Updates remaining tokens and status of a portfolio entry after a sell."""
        query = 'UPDATE portfolio SET remaining_tokens = $1, status = $2 WHERE id = $3'
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, new_remaining_tokens, new_status, position_id)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def insert_portfolio_sell_record(self, mint: str, current_price: float, market_cap_sol: float, net_sol_received: float, sol_price_usd: float, tokens_sold: float, sell_fee: float, sell_tip: float, profit: float, reason: str, timestamp: datetime, settings: dict, conn=None):
        """Inserts a sell transaction record into the portfolio, including settings."""
        query = '''
            INSERT INTO portfolio
            (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, tokens, fee, tip, profit, total_investment_sol,
             remaining_tokens, status, reason, timestamp, initial_tokens, stop_loss_price, highest_price, settings)
            VALUES ($1, 'sell', $2, $3, $4, $5, $6, $7, $8, $9, 0, 0, 'closed', $10, $11, 0, 0, 0, $12)
        '''
        connection = conn or await self.pool.acquire()
        try:
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, net_sol_received, sol_price_usd, tokens_sold,
                                   sell_fee, sell_tip, profit, reason, timestamp, settings_json)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_token_name(self, mint: str, conn=None):
        """Fetches the name of a token given its mint address."""
        query = "SELECT name FROM tokens WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, mint)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def insert_portfolio_buy_record(self, mint: str, current_price: float, market_cap_sol: float, sol_base_amount: float, sol_price_usd: float, total_sol_investment: float, tokens_bought: float, buy_fee: float, buy_tip: float, initial_stop_loss_price: float, initial_tp_price: float, second_tp_price: float, timestamp: datetime, settings: dict, conn=None):
        """Inserts a buy transaction record into the portfolio, including settings."""
        query = """
            INSERT INTO portfolio
                (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, total_investment_sol, tokens,
                 fee, tip, remaining_tokens, stop_loss_price, highest_price,
                 initial_tp_price, second_tp_price, first_tp_hit,
                 status, timestamp, initial_tokens, settings)
            VALUES ($1, 'buy', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, FALSE, 'active', $15, $16, $17)
        """
        connection = conn or await self.pool.acquire()
        try:
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, sol_base_amount, sol_price_usd, total_sol_investment, tokens_bought,
                                   buy_fee, buy_tip, tokens_bought, # remaining_tokens = initial_tokens
                                   initial_stop_loss_price, current_price, # highest_price = current_price
                                   initial_tp_price, second_tp_price,
                                   timestamp, tokens_bought, # initial_tokens
                                   settings_json) # settings
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    # Modify existing has_active_buy_order to accept optional connection
    async def has_active_buy_order(self, mint: str, conn=None):
        query = """
            SELECT 1 FROM portfolio WHERE mint = $1 AND tx_type = 'buy' AND status = 'active'
        """
        connection = conn or await self.pool.acquire()
        try:
            result = await connection.fetchval(query, mint)
            return result is not None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_trade_history(self, mints: list[str]):
        """Fetches price and timestamp for given mints from trades and trades_backup."""
        if not mints:
            return []
        # Ensure logger is accessible if used within the method, assuming it's defined globally or passed in
        # from logger import logger # Uncomment if logger is needed and not globally accessible
        # Use the v_trades view which combines trades and trades_backup
        query = """
            SELECT mint, price, timestamp
            FROM v_trades -- Use the view
            WHERE mint = ANY($1::text[])
            ORDER BY mint, timestamp;
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, mints)
                # Convert asyncpg Record objects to dictionaries for easier handling
                return [dict(row) for row in results]
            except Exception as e:
                # Log the error using the logger instance
                logger.error(f"Error fetching trade history for mints {mints}: {e}", exc_info=True)
                return [] # Return empty list on error

    async def get_all_unique_mints_with_names(self):
        """Fetches all unique mint addresses and their names from relevant tables."""
        # This query prioritizes names from the 'tokens' table, falling back to 'tokens_backup'.
        # It assumes mints exist in trades/trades_backup might also exist in tokens/tokens_backup.
        # Use the v_tokens and v_rugcheck views
        # Fetch symbol, socials_score, and latest rugcheck score for display
        query = """
            WITH LatestRugcheck AS (
                SELECT
                    mint,
                    score,
                    ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) as rn
                FROM v_rugcheck -- Use the rugcheck view
            )
            SELECT
                vt.mint,
                COALESCE(vt.name, vt.mint) AS name, -- Fallback to mint if name is null
                vt.symbol,
                vt.socials_score,
                lr.score AS rugcheck_score
            FROM v_tokens vt -- Use the tokens view
            LEFT JOIN LatestRugcheck lr ON vt.mint = lr.mint AND lr.rn = 1
            WHERE vt.mint IS NOT NULL -- Ensure mint is not null from the view
            ORDER BY name, vt.mint; -- Order by name from the view
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query) # No parameters needed for this version using views
                # Return list of dictionaries
                # Return richer dictionary including scores
                return [
                    {
                        'mint': row['mint'],
                        'name': row['name'],
                        'symbol': row['symbol'],
                        'socials_score': row['socials_score'],
                        'rugcheck_score': row['rugcheck_score'] # Might be None
                    } for row in results
                ]
            except Exception as e:
                logger.error(f"Error fetching unique mints with names: {e}", exc_info=True)
                return []

    async def get_filtered_tokens(self, max_socials=100, max_rugcheck=10000, min_volume_sol=0, time_window_minutes=60, portfolio_only=False):
        """
        Fetches tokens filtered by:
        - socials score <= max_socials
        - latest rugcheck score <= max_rugcheck (or NULL)
        - trade volume in the last time_window_minutes relative to the token's latest trade >= min_volume_sol
        - optionally filters to tokens in the active portfolio
        """

        try:
            max_socials = int(max_socials)
            max_rugcheck = int(max_rugcheck)
            min_volume_sol = float(min_volume_sol)
            time_window_minutes = str(time_window_minutes)
        except (ValueError, TypeError):
            logger.error("Invalid filter parameter types received.")
            return []

        params = [max_socials, max_rugcheck, min_volume_sol, time_window_minutes]

        query = """
        WITH LatestRugcheck AS (
            SELECT
                mint,
                score,
                ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) AS rn
            FROM v_rugcheck
        ),
        LastTrades AS (
            SELECT
                mint,
                MAX(timestamp) AS last_trade_time
            FROM v_trades
            GROUP BY mint
        ),
        FilteredTrades AS (
            SELECT
                t.mint,
                SUM(t.sol_amount) AS volume_sol
            FROM v_trades t
            JOIN LastTrades lt ON t.mint = lt.mint
            WHERE t.timestamp BETWEEN (lt.last_trade_time - ($4 || ' minutes')::INTERVAL) AND lt.last_trade_time
            GROUP BY t.mint
        )
        SELECT DISTINCT
            vt.mint,
            COALESCE(vt.name, vt.mint) AS name,
            vt.socials_score,
            lr.score AS rugcheck_score,
            COALESCE(ft.volume_sol, 0) AS recent_volume_sol
        FROM v_tokens vt
        LEFT JOIN LatestRugcheck lr ON vt.mint = lr.mint AND lr.rn = 1
        LEFT JOIN FilteredTrades ft ON vt.mint = ft.mint
        """

        if portfolio_only:
            query += """
            INNER JOIN portfolio p ON vt.mint = p.mint
            """

        query += """
        WHERE
            vt.socials_score IS NOT NULL AND vt.socials_score <= $1
            AND (lr.score IS NULL OR lr.score <= $2)
            AND COALESCE(ft.volume_sol, 0) >= $3
        ORDER BY name, vt.mint;
        """
        print(f"Query: {query}")
        print(f"params: {params}")
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, *params)
                return [
                    {
                        'mint': row['mint'],
                        'name': row['name'],
                        'socials': row['socials_score'],
                        'rugcheck': row['rugcheck_score'],
                        'volume': round(row['recent_volume_sol'], 4)
                    } for row in results
                ]
            except Exception as e:
                logger.error(f"Error fetching filtered tokens: {e}", exc_info=True)
                return []


    async def get_portfolio_transactions(self, mints: list[str]):
        """Fetches buy/sell transaction timestamps and prices for given mints from the portfolio."""
        if not mints:
            return {} # Return empty dict if no mints provided

        query = """
            SELECT mint, tx_type, timestamp, price
            FROM portfolio
            WHERE mint = ANY($1::text[])
            ORDER BY mint, timestamp;
        """
        async with self.pool.acquire() as conn:
            try:
                results = await conn.fetch(query, mints)
                portfolio_data = {}
                for row in results:
                    mint = row['mint']
                    if mint not in portfolio_data:
                        portfolio_data[mint] = {'buys': [], 'sells': []}

                    # Keep the original timestamp object and ensure price is float
                    tx_info = {'timestamp': row['timestamp'], 'price': float(row['price'])}

                    if row['tx_type'] == 'buy':
                        portfolio_data[mint]['buys'].append(tx_info)
                    elif row['tx_type'] == 'sell':
                        portfolio_data[mint]['sells'].append(tx_info)

                logger.debug(f"Fetched portfolio transactions for mints: {mints}")
                return portfolio_data
            except Exception as e:
                logger.error(f"Error fetching portfolio transactions for mints {mints}: {e}", exc_info=True)
                return {} # Return empty dict on error

    async def backup_and_delete_token(self, mint: str, archived_at: datetime):
        """Backup core table data to a corresponding backup table."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                            INSERT INTO tokens_backup SELECT *, NOW() FROM tokens WHERE mint = $1
                        ''', mint)
                        
                        await conn.execute('''
                            INSERT INTO trades_backup SELECT *, NOW() FROM trades WHERE mint = $1
                        ''', mint)

                        await conn.execute('''
                            INSERT INTO rugcheck_backup SELECT *, NOW() FROM rugcheck WHERE mint = $1
                        ''', mint)

                        # Backup migrations, ignoring conflicts on the primary key
                        await conn.execute('''
                            INSERT INTO migrations_backup SELECT *, NOW() FROM migrations WHERE mint = $1
                            ON CONFLICT (signature) DO NOTHING -- Conflict check on signature
                        ''', mint)

                        await conn.execute("DELETE FROM tokens WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM trades WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM rugcheck WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM migrations WHERE mint = $1", mint)

                        logger.debug(f"🧹 Backup & deletion completed for {mint}")

                    except Exception as e:
                        logger.error(f"❌ Backup failed for {mint}: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f"🚨 backup_and_delete_token: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def backup_creator_wallets(self):
        """Dumps the creator_wallets table to a JSON file."""
        backup_file_path = os.path.join(os.path.dirname(__file__), "data", "creator_wallets_backup.json")
        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)  # Ensure data directory exists

        logger.info("Backing up creator_wallets table...")
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT wallet_address, token_count, last_token_time FROM creator_wallets")
                
                # Convert rows to a list of dictionaries
                data = [
                    {
                        "wallet_address": row["wallet_address"],
                        "token_count": row["token_count"],
                        "last_token_time": row["last_token_time"].isoformat() if row["last_token_time"] else None
                    }
                    for row in rows
                ]
                
                # Write the data to a JSON file
                async with aiofiles.open(backup_file_path, "w") as f:
                    await f.write(json.dumps(data, indent=4))
                
                logger.info(f"✅ Successfully backed up {len(rows)} creator wallets to {backup_file_path}")
        except Exception as e:
            logger.exception(f"Error backing up creator_wallets table: {e}")
            # Decide if we should raise or just log

    async def restore_creator_wallets(self):
        ## Restore creator_wallets table from backup
        backup_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "data", 
            "creator_wallets_backup.json"
        ))
        if os.path.exists(backup_path):
            try:
                with open(backup_path, "r") as f:
                    data = json.load(f)
                
                # Generate and execute SQL statements dynamically
                for record in data:
                    wallet_address = record["wallet_address"]
                    token_count = record["token_count"]
                    last_token_time_str = f"'{record['last_token_time']}'" if record["last_token_time"] else "NULL"
                    
                    sql_line = (
                        f"INSERT INTO creator_wallets (wallet_address, token_count, last_token_time) "
                        f"VALUES ('{wallet_address}', {token_count}, {last_token_time_str}) "
                        f"ON CONFLICT (wallet_address) DO UPDATE SET token_count = GREATEST(creator_wallets.token_count, EXCLUDED.token_count), "
                        f"last_token_time = CASE WHEN EXCLUDED.token_count > creator_wallets.token_count THEN EXCLUDED.last_token_time ELSE creator_wallets.last_token_time END;"
                    )
                    async with self.pool.acquire() as conn:
                        await conn.execute(sql_line)
                
                logger.info("Loaded backup data from %s", backup_path)
            except Exception as e:
                logger.exception("Error loading backup data: %s", e)
                raise

    async def get_total_tracked_tokens(self, backedup=False):
        """Fetches the total number of tracked tokens from the database."""
        query = "SELECT COUNT(*) FROM tokens"
        if backedup:
            query = "SELECT COUNT(*) FROM v_tokens"
        
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(query)
                return result if result is not None else 0
            except Exception as e:
                logger.error(f"Error fetching total tracked tokens: {e}", exc_info=True)
                return 0

    async def cleanup_db(self, cleanup_flag: bool):
        """Drop all application tables if cleanup_flag is True."""
        if cleanup_flag:
            logger.warning("🚨 Starting full database cleanup - Dropping all application tables...")
            async with self.pool.acquire() as conn:
                # List all known application tables (main and backup)
                # Add any other tables managed by the application if necessary (e.g., creator_wallets)
                tables_to_drop = [
                    'portfolio',          
                    'rugcheck',           # Depends on tokens
                    'trades',             # No explicit FK, but related to tokens
                    'migrations',         # Standalone or related? Assuming standalone for drop order
                    'tokens',             # Drop after dependents
                    'portfolio_backup',          
                    'rugcheck_backup',
                    'trades_backup',
                    'migrations_backup',
                    'tokens_backup'
                ]
                # Drop tables in an order that respects potential dependencies, or use CASCADE
                # Using DROP TABLE IF EXISTS ... CASCADE is generally safer
                for table in tables_to_drop:
                    try:
                        # Use CASCADE to handle potential foreign key dependencies automatically
                        await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                        logger.info(f"🗑️ Dropped table {table}")
                    except Exception as e:
                        # Log error but continue trying to drop other tables
                        logger.error(f"Error dropping table {table}: {e}", exc_info=False) # Keep log concise

            logger.warning("✅ Full database cleanup finished.")

    async def backup_db(self, backup_flag: bool):
        """Backup tables based on backup_flag."""
        if backup_flag:
            async with self.pool.acquire() as conn:
                try:
                    tables_to_backup = [
                        'tokens', 'trades', 'rugcheck', 'migrations', 'portfolio'
                    ]
                    for table in tables_to_backup:
                        # Insert into backup table, ignoring rows that already exist based on primary key 'id'
                        # Determine the correct primary key for conflict resolution based on table schema
                        if table == 'tokens':
                            conflict_key = 'mint'
                        elif table == 'trades':
                            conflict_key = 'signature'
                        elif table == 'rugcheck':
                            conflict_key = 'mint'
                        elif table == 'migrations':
                            conflict_key = 'signature'
                        elif table == 'portfolio':
                            table_columns = await conn.fetch(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
                            conflict_key = 'id'
                            columns = ", ".join([col for col in table_columns if col != "id"])
                            await conn.execute(f"""
                                INSERT INTO {table}_backup (id, {columns})
                                SELECT nextval('{table}_backup_id_seq'), {columns}
                                FROM {table} 
                                ORDER BY id
                                ON CONFLICT ({conflict_key}) DO NOTHING;
                            """)
                            logger.info("🗄️ Backed up table %s", table)
                            await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                            logger.info("🧹 Truncated table %s", table)
                        else:
                            # Should not happen with the current list, but add a warning
                            logger.warning(f"Unexpected table '{table}' in backup_db conflict handling.")
                            # If other tables are added later, their PK needs to be handled here.
                            # For now, skip conflict handling for unknown tables to avoid errors.
                            await conn.execute(f"INSERT INTO {table}_backup SELECT * FROM {table};") # Original insert without ON CONFLICT
                            logger.info("🗄️ Backed up table %s (without conflict check)", table)
                            await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                            continue # Skip the rest of the loop for this table

                        # Execute the INSERT with the correct ON CONFLICT clause
                        await conn.execute(f"INSERT INTO {table}_backup SELECT * FROM {table} ON CONFLICT ({conflict_key}) DO NOTHING;")
                        logger.info("🗄️ Backed up table %s", table)
                        await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                        logger.info("🧹 Truncated table %s", table)
                except Exception as e:
                    logger.exception("Error during database backup: %s", e)
                    raise

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            logger.info("Closing database connection pool...")
            await self.pool.close()
            logger.info("Database connection pool closed.")

    async def get_token_lifespan(self, mint: str) -> Optional[Dict[str, datetime]]:
        """
        Fetches the approximate start and end timestamp of a token's activity
        based on its first and last trade records in the v_trades view.

        Args:
            mint: The mint address of the token.

        Returns:
            A dictionary {'start_ts': datetime, 'end_ts': datetime} if trades exist,
            otherwise None. Timestamps are timezone-aware (UTC).
        """
        if not self.pool:
            logger.error("Database pool not initialized.")
            return None

        query = """
            SELECT
                MIN(timestamp) as first_trade_ts,
                MAX(timestamp) as last_trade_ts
            FROM v_trades
            WHERE mint = $1;
        """
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(query, mint)
                if row and row['first_trade_ts'] and row['last_trade_ts']:
                    # Ensure timestamps are timezone-aware UTC
                    start_ts = row['first_trade_ts'].replace(tzinfo=timezone.utc) if row['first_trade_ts'].tzinfo is None else row['first_trade_ts'].astimezone(timezone.utc)
                    end_ts = row['last_trade_ts'].replace(tzinfo=timezone.utc) if row['last_trade_ts'].tzinfo is None else row['last_trade_ts'].astimezone(timezone.utc)
                    return {'start_ts': start_ts, 'end_ts': end_ts}
                else:
                    logger.warning(f"No trade timestamps found for mint {mint} to determine lifespan.")
                    return None
            except Exception as e:
                logger.error(f"Error fetching token lifespan for {mint}: {e}", exc_info=True)
                return None

    def ohlcv_sql_like(self, df):
        """Aggregates trade data into OHLCV format, using pre-calculated rolling metrics."""
        # Ensure data is sorted by time within the group
        df = df.sort_values('timestamp')
        if df.empty:
            # Return a Series with expected columns and NaN/0 values if the group is empty
            return pd.Series({
                'Open': np.nan, 'High': np.nan, 'Low': np.nan, 'Close': np.nan,
                'Volume': 0.0, # Use the rolling volume name
                'market_cap_calculated': np.nan,
                'volatility': 0.0 # Use the rolling volatility name
            })

        # Use .iloc[-1] to safely get the last value, handling potential index issues
        # Use .fillna(0.0) or other appropriate defaults if iloc[-1] could be NaN
        last_rolling_volume = df['rolling_volume_sql'].iloc[-1] if not df['rolling_volume_sql'].empty else 0.0
        last_rolling_volatility = df['rolling_volatility_sql'].iloc[-1] if not df['rolling_volatility_sql'].empty else 0.0
        last_market_cap = df['market_cap_calculated'].iloc[-1] if not df['market_cap_calculated'].isnull().all() else np.nan

        return pd.Series({
            'Open': df['price'].iloc[0] if not df['price'].empty else np.nan,
            'High': df['price'].max() if not df['price'].empty else np.nan,
            'Low': df['price'].min() if not df['price'].empty else np.nan,
            'Close': df['price'].iloc[-1] if not df['price'].empty else np.nan,
            # --- MODIFIED LINES ---
            'Volume': last_rolling_volume,         # Take the LAST rolling volume in the interval
            'market_cap_calculated': last_market_cap,
            'volatility': last_rolling_volatility   # Take the LAST rolling volatility in the interval
            # --- END MODIFIED LINES ---
        })

    async def get_historical_data_for_backtesting(
            self, # Assuming this is part of the DatabaseClient class
            mints: List[str],
            start_date: datetime,
            end_date: datetime
        ) -> Dict[str, pd.DataFrame]:
            """
            Fetches comprehensive historical data for specified tokens within a date range,
            structured as 5-second OHLCV candles for backtesting.
            Calculates rolling volume and volatility similar to the SQL trading logic.
            """
            if not mints:
                logger.warning("get_historical_data_for_backtesting called with empty mints list.")
                return {}
            if not self.pool:
                logger.error("Database pool not initialized.")
                return {}

            if start_date.tzinfo is None: start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None: end_date = end_date.replace(tzinfo=timezone.utc)

            logger.info(f"Fetching historical data for {len(mints)} tokens from {start_date.isoformat()} to {end_date.isoformat()}...")

            # Fetch all necessary data within the time range
            trade_query = """
                SELECT
                    mint, timestamp, price, (sol_amount*sol_price_usd) AS volume, market_cap_calculated
                FROM v_trades
                WHERE mint = ANY($1::text[])
                AND timestamp >= $2 AND timestamp < $3
                AND price > 0 AND sol_amount IS NOT NULL AND price IS NOT NULL
                ORDER BY mint, timestamp;
            """
            rugcheck_query = """
                WITH RankedRugcheck AS (
                    SELECT
                        mint, last_checked AS timestamp, score AS rugcheck_score,
                        ROW_NUMBER() OVER (PARTITION BY mint ORDER BY last_checked DESC) as rn
                    FROM v_rugcheck
                    WHERE mint = ANY($1::text[])
                    AND last_checked < $3 -- Get checks before the period end
                )
                -- Select the latest check before the period OR any check within the period
                SELECT mint, timestamp, rugcheck_score
                FROM RankedRugcheck
                WHERE rn = 1 OR timestamp >= $2;
            """
            token_info_query = """
                WITH LatestTokenInfo AS (
                    SELECT
                        mint,
                        socials_score,
                        timestamp AS token_creation_time,
                        ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                    FROM v_tokens
                    WHERE mint = ANY($1::text[])
                    AND timestamp < $2 -- Get info created before the end_date
                )
                SELECT mint, token_creation_time, socials_score
                FROM LatestTokenInfo
                WHERE rn = 1;
            """

            results_dict = {}
            async with self.pool.acquire() as conn:
                try:
                    logger.debug("Fetching trade data...")
                    trade_records_raw = await conn.fetch(trade_query, mints, start_date, end_date)
                    logger.debug(f"Fetched {len(trade_records_raw)} raw trades.")

                    logger.debug("Fetching rugcheck data...")
                    rugcheck_records_raw = await conn.fetch(rugcheck_query, mints, start_date, end_date)
                    logger.debug(f"Fetched {len(rugcheck_records_raw)} rugchecks.")

                    logger.debug("Fetching token info data...")
                    token_info_records_raw = await conn.fetch(token_info_query, mints, end_date)
                    logger.debug(f"Fetched {len(token_info_records_raw)} token infos.")

                    if not trade_records_raw:
                        logger.warning("No trade records found for the specified mints and period.")
                        return {}

                    # --- Process Trade Data ---
                    trades_df = pd.DataFrame(trade_records_raw, columns=['mint', 'timestamp', 'price', 'volume', 'market_cap_calculated'])
                    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], errors='coerce', utc=True)
                    trades_df.dropna(subset=['timestamp'], inplace=True) # Drop rows where timestamp couldn't be parsed

                    # Convert relevant columns to numeric early, handling errors
                    trades_df['price'] = pd.to_numeric(trades_df['price'], errors='coerce')
                    trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce') # This is sol_amount
                    trades_df['market_cap_calculated'] = pd.to_numeric(trades_df['market_cap_calculated'], errors='coerce')
                    trades_df.dropna(subset=['price', 'volume'], inplace=True) # Drop rows essential for calcs if invalid

                    # --- Calculate SQL-like Rolling Volume & Volatility per Mint ---
                    logger.info("Calculating rolling volume and volatility per mint...")
                    all_processed_trades = []
                    time_interval_minutes = config.DEFAULT_TIME_INTERVALL # Get from config
                    window_duration = f"{time_interval_minutes}min"
                    logger.debug(f"Using rolling window duration: {window_duration}")

                    for mint_name, mint_df in trades_df.groupby('mint'):
                        if mint_df.empty:
                            continue

                        mint_df = mint_df.sort_values('timestamp').copy() # Sort and copy to avoid SettingWithCopyWarning

                        # Set timestamp as index for rolling calculations
                        mint_df_indexed = mint_df.set_index('timestamp')

                        # Calculate Rolling Volume (SQL-like)
                        mint_df['rolling_volume_sql'] = mint_df_indexed['volume']\
                                                        .rolling(window_duration, closed='left')\
                                                        .sum().values
                        mint_df['rolling_volume_sql'] = mint_df['rolling_volume_sql'].fillna(0.0)

                        # Calculate Rolling Volatility (SQL-like)
                        prices = mint_df['price']
                        if len(prices) > 1:
                            # Calculate log returns, handle potential division by zero or invalid values
                            log_returns = np.log(prices / prices.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)

                            # Use rolling window on log_returns indexed by time
                            rolling_obj = log_returns.set_axis(mint_df['timestamp'])\
                                                    .rolling(window_duration, closed='left')

                            # Calculate rolling std deviation and count
                            rolling_std = rolling_obj.std()
                            rolling_count = rolling_obj.count()

                            # Apply the SQL logic: std * sqrt(count), handle count <= 5
                            # Ensure intermediate arrays are float for sqrt
                            rolling_std_float = rolling_std.fillna(0.0).astype(float)
                            rolling_count_float = rolling_count.fillna(0.0).astype(float)

                            volatility_sql = rolling_std_float * np.sqrt(np.maximum(rolling_count_float, 1.0)) # Use maximum to avoid sqrt(0)
                            mint_df['rolling_volatility_sql'] = volatility_sql.where(rolling_count > 5, 0.0).values # Set to 0 if count <= 5
                        else:
                            mint_df['rolling_volatility_sql'] = 0.0 # Not enough data for log returns

                        mint_df['rolling_volatility_sql'] = mint_df['rolling_volatility_sql'].fillna(0.0) # Fill any remaining NaNs

                        all_processed_trades.append(mint_df)

                    if not all_processed_trades:
                        logger.warning("No trades remained after processing rolling metrics.")
                        return {}

                    processed_trades_df = pd.concat(all_processed_trades)

                    # --- Resample to 5-second OHLCV using SQL-like metrics ---
                    logger.info("Resampling trades to 5-second OHLCV intervals...")
                    # Apply the modified aggregation function
                    ohlcv_df = processed_trades_df.groupby(['mint', pd.Grouper(key='timestamp', freq='5s')])\
                                                .apply(self.ohlcv_sql_like).reset_index()

                    # Handle potential NaNs from empty groups BEFORE setting index
                    ohlcv_df.dropna(subset=['mint', 'timestamp'], inplace=True) # Drop rows if group keys are NaN
                    # Fill NaNs in OHLC columns resulting from empty groups (e.g., with ffill/bfill or 0)
                    ohlc_cols = ['Open', 'High', 'Low', 'Close']
                    # Forward fill first, then backfill to handle NaNs at the start/end
                    ohlcv_df[ohlc_cols] = ohlcv_df.groupby('mint')[ohlc_cols].ffill().bfill()
                    # Fill remaining NaNs (if entire mint group was NaN) with 0 or a suitable value
                    ohlcv_df[ohlc_cols] = ohlcv_df[ohlc_cols].fillna(0.0)
                    # Also fill Volume/Volatility/MarketCap NaNs that resulted from empty intervals
                    ohlcv_df[['Volume', 'volatility', 'market_cap_calculated']] = ohlcv_df[['Volume', 'volatility', 'market_cap_calculated']].fillna(0.0)


                    ohlcv_df = ohlcv_df.set_index('timestamp')

                    # ---> FIX: Handle duplicate index before resampling <---
                    # This should ideally happen *after* groupby.apply but *before* resample
                    # Check if duplicates exist after setting the index
                    if ohlcv_df.index.has_duplicates:
                        logger.warning(f"Duplicate timestamps found in aggregated OHLCV index before resampling. Keeping last entry.")
                        # Group by mint *and* timestamp, take the last row within each duplicate group
                        ohlcv_df = ohlcv_df.loc[~ohlcv_df.index.duplicated(keep='last')]
                    # ---> END FIX <---

                    # Resample to ensure continuous 5s intervals and interpolate missing values (if any remain)
                    # Group by mint *before* resampling to resample each token independently
                    resampled_ohlcv_list = []
                    for mint_name, group_df in ohlcv_df.groupby('mint'):
                        # Ensure index is unique within the group before resampling
                        if group_df.index.has_duplicates:
                            logger.warning(f"Duplicate timestamps found for mint {mint_name} before resampling. Keeping last.")
                            group_df = group_df.loc[~group_df.index.duplicated(keep='last')]

                        # Define the full time range for this mint based on its first/last resampled point
                        # This ensures resampling covers the actual activity period for the mint
                        min_ts = group_df.index.min()
                        max_ts = group_df.index.max()
                        full_range = pd.date_range(start=min_ts, end=max_ts, freq='5s', tz='UTC')

                        # Reindex and interpolate within the group's actual range
                        group_resampled = group_df.reindex(full_range).interpolate(method='time')
                        # Add the mint column back after reindexing
                        group_resampled['mint'] = mint_name
                        resampled_ohlcv_list.append(group_resampled)

                    if not resampled_ohlcv_list:
                        logger.warning("No data remained after resampling OHLCV data.")
                        return {}

                    resampled_ohlcv_df = pd.concat(resampled_ohlcv_list)
                    resampled_ohlcv_df.index.name = 'timestamp' # Ensure index has a name

                    # --- Process RugCheck Data ---
                    # (Same as before)
                    if rugcheck_records_raw:
                        rugcheck_df = pd.DataFrame(rugcheck_records_raw, columns=['mint', 'timestamp', 'rugcheck_score'])
                        rugcheck_df['timestamp'] = pd.to_datetime(rugcheck_df['timestamp'], errors='coerce', utc=True)
                        rugcheck_df.dropna(subset=['timestamp'], inplace=True)
                        # Set index AFTER sorting and dropping duplicates
                        rugcheck_df = rugcheck_df.sort_values(['mint', 'timestamp'])
                        # Keep the last score for duplicate timestamps within the same mint
                        rugcheck_df = rugcheck_df.drop_duplicates(subset=['mint', 'timestamp'], keep='last')
                        rugcheck_df.set_index('timestamp', inplace=True)
                        rugcheck_df['rugcheck_score'] = pd.to_numeric(rugcheck_df['rugcheck_score'], errors='coerce')
                        rugcheck_df = rugcheck_df[['mint', 'rugcheck_score']] # Keep mint for merge_asof
                    else:
                        # Create an empty DataFrame with the correct columns and index type
                        rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))


                    # --- Process Token Info ---
                    # (Same as before)
                    token_info = {}
                    if token_info_records_raw:
                        for r in token_info_records_raw:
                            mint = r['mint']
                            # Use pd.to_datetime which handles NaT gracefully
                            creation_time = pd.to_datetime(r['token_creation_time'], errors='coerce', utc=True)
                            socials = pd.to_numeric(r['socials_score'], errors='coerce')
                            if pd.notna(creation_time): # Check if creation_time is valid
                                token_info[mint] = {'creation_time': creation_time, 'socials_score': socials}


                    # --- Combine data per mint ---
                    logger.info("Combining OHLCV, RugCheck, and Token Info data per mint...")
                    required_final_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility', 'rugcheck_score', 'socials_score', 'token_creation_time']

                    # Process each mint group from the resampled data
                    grouped_ohlcv = resampled_ohlcv_df.groupby('mint')

                    for mint_name in grouped_ohlcv.groups:
                        # Select the mint's OHLCV data
                        mint_ohlcv = grouped_ohlcv.get_group(mint_name)[['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility']]

                        # Prepare mint-specific rugcheck data for merge_asof
                        mint_rugcheck_data = rugcheck_df[rugcheck_df['mint'] == mint_name][['rugcheck_score']] if not rugcheck_df.empty else None

                        # Create the combined DataFrame starting with OHLCV data
                        combined_df = mint_ohlcv.copy()

                        # Merge RugCheck data using merge_asof
                        if mint_rugcheck_data is not None and not mint_rugcheck_data.empty:
                            # Ensure both sides are sorted by index for merge_asof
                            combined_df = combined_df.sort_index()
                            mint_rugcheck_data = mint_rugcheck_data.sort_index()
                            # Handle potential duplicates in rugcheck index before merging
                            if mint_rugcheck_data.index.has_duplicates:
                                logger.warning(f"Duplicate timestamps found in RugCheck data for {mint_name}. Keeping last.")
                                mint_rugcheck_data = mint_rugcheck_data.loc[~mint_rugcheck_data.index.duplicated(keep='last')]

                            combined_df = pd.merge_asof(
                                combined_df,
                                mint_rugcheck_data,
                                left_index=True,
                                right_index=True,
                                direction='backward', # Find the latest rugcheck score at or before the OHLCV timestamp
                                tolerance=pd.Timedelta('1d') # Allow matching recent score
                            )
                        else:
                            combined_df['rugcheck_score'] = np.nan # Add column if no rugcheck data

                        # Add Token Info (Creation Time, Socials Score)
                        mint_info_data = token_info.get(mint_name)
                        if mint_info_data:
                            combined_df['token_creation_time'] = mint_info_data['creation_time']
                            combined_df['socials_score'] = mint_info_data['socials_score']
                        else:
                            logger.warning(f"Missing token info for {mint_name}. Using defaults.")
                            combined_df['token_creation_time'] = pd.NaT # Use NaT for missing dates
                            combined_df['socials_score'] = 100 # Default high risk score

                        # --- Final Fill and Type Conversion ---
                        # Forward fill scores and creation time
                        fill_cols = ['rugcheck_score', 'socials_score', 'token_creation_time']
                        combined_df[fill_cols] = combined_df[fill_cols].ffill()
                        # Backfill only if needed (e.g., if NaNs remain at the beginning)
                        combined_df[fill_cols] = combined_df[fill_cols].bfill()


                        # Convert score columns to integer types after filling NaNs
                        # Fill NaN scores with default high-risk values before converting to int
                        combined_df['rugcheck_score'] = combined_df['rugcheck_score'].fillna(10000).astype(int)
                        combined_df['socials_score'] = combined_df['socials_score'].fillna(100).astype(int)

                        # Ensure other numeric columns are floats, fill NaNs with 0.0 AFTER interpolation/ffill
                        numeric_cols_to_zero = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'volatility']
                        for col in numeric_cols_to_zero:
                            if col in combined_df.columns:
                                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0.0)
                            else:
                                # Add the column if completely missing after merges (shouldn't happen ideally)
                                logger.warning(f"Column '{col}' missing for {mint_name} after merge. Adding default 0.0.")
                                combined_df[col] = 0.0


                        # Ensure all required columns exist, adding defaults if somehow missing
                        for r_col in required_final_cols:
                            if r_col not in combined_df.columns:
                                logger.warning(f"Required column '{r_col}' missing for {mint_name} at final stage. Adding default.")
                                if r_col == 'token_creation_time': combined_df[r_col] = pd.NaT
                                elif r_col in ['rugcheck_score', 'socials_score']: combined_df[r_col] = 100 if r_col == 'socials_score' else 10000
                                else: combined_df[r_col] = 0.0

                        # --- Final Filtering and Validation ---
                        # Filter final DataFrame to the originally requested date range
                        # This ensures we don't include data outside the requested bounds introduced by resampling/filling
                        final_df = combined_df[(combined_df.index >= start_date) & (combined_df.index < end_date)].copy() # Use .copy()

                        # Final check for validity before adding to results
                        if not final_df.empty and all(col in final_df.columns for col in required_final_cols):
                            # Select and ensure correct dtypes before returning
                            final_df = final_df[required_final_cols].astype({
                                'Open': float, 'High': float, 'Low': float, 'Close': float, 'Volume': float,
                                'market_cap_calculated': float, 'volatility': float, 'rugcheck_score': int, 'socials_score': int
                                # Keep token_creation_time as datetime
                            })
                            # Ensure the index is still a DatetimeIndex and timezone-aware
                            final_df.index = pd.to_datetime(final_df.index, utc=True)
                            results_dict[mint_name] = final_df
                        else:
                            logger.warning(f"No valid data remained for {mint_name} after final processing/filtering. Skipping.")


                    logger.info(f"Finished processing data for {len(results_dict)} tokens.")

                except asyncpg.exceptions.InterfaceError as iface_err:
                    logger.error(f"InterfaceError during historical data processing: {iface_err}", exc_info=True)
                    # Consider connection recovery logic or re-raising
                    return {}
                except Exception as e:
                    logger.error(f"Error processing historical data ({type(e).__name__}): {e}", exc_info=True)
                    return {}

            logger.info(f"Successfully fetched and processed historical data for {len(results_dict)} tokens.")
            return results_dict

# Helper function moved outside class for potential reuse (optional)
async def get_token_lifespan(db_client: DatabaseClient, mint: str) -> Optional[Dict[str, datetime]]:
    """
    Fetches the approximate start and end timestamp of a token's activity
    based on its first and last trade records in the v_trades view.
    """
    if not db_client or not db_client.pool:
        logger.error("Database client not initialized or connected for get_token_lifespan.")
        return None

    query = """
        SELECT
            MIN(timestamp) as first_trade_ts,
            MAX(timestamp) as last_trade_ts
        FROM v_trades
        WHERE mint = $1;
    """
    async with db_client.pool.acquire() as conn:
        try:
            row = await conn.fetchrow(query, mint)
            if row and row['first_trade_ts'] and row['last_trade_ts']:
                start_ts = row['first_trade_ts'].replace(tzinfo=timezone.utc) if row['first_trade_ts'].tzinfo is None else row['first_trade_ts'].astimezone(timezone.utc)
                end_ts = row['last_trade_ts'].replace(tzinfo=timezone.utc) if row['last_trade_ts'].tzinfo is None else row['last_trade_ts'].astimezone(timezone.utc)
                end_ts += timedelta(seconds=1) # Add buffer
                return {'start_ts': start_ts, 'end_ts': end_ts}
            else:
                logger.warning(f"No trade timestamps found for mint {mint} to determine lifespan.")
                return None
        except Exception as e:
            logger.error(f"Error fetching token lifespan for {mint}: {e}", exc_info=True)
            return None

```

---

### 📄 sol_price_api.py

```python

import asyncio
import httpx
import json
from config import SOL_PRICE_API_URL
from logger import logger
from database_handler import DatabaseClient


async def update_sol_price(state, db_client: DatabaseClient):
    """Periodically fetches and updates the global SOL price from an external API."""
    logger.info("🚀 Starting update_sol_price task...")

    try:
        while True:
            if state.shutdown_event.is_set():
                logger.info("Shutdown event detected. Exiting update_sol_price task.")
                break

            try:
                # Fetch the SOL price from an external API
                async with httpx.AsyncClient() as client:
                    response = await client.get(SOL_PRICE_API_URL)
                    if response.status_code == 200:
                        data = response.json()
                        new_price = data.get("solana", {}).get("usd")
                        if new_price is None or not isinstance(new_price, (int, float)):
                            logger.error("Invalid or missing SOL price in API response.")
                            continue

                        # Update the in-memory state and database
                        #async with state.lock:
                        await state.set_sol_price(new_price)
                        await db_client.insert_sol_price(new_price)

                        logger.info(f"✅ Updated Solana price: {new_price} USD")
                    else:
                        logger.error(f"⚠ Error fetching Solana price. Status code: {response.status_code}, Response: {response.text}")
            except Exception as e:
                logger.error(f"❌ Exception in update_sol_price task: {e}", exc_info=True)

            logger.debug("⏳ Sleeping for 1 hour...")
            await state.wait_or_interrupt(timeout=3600)

    except asyncio.CancelledError:
        logger.info("⏹ update_sol_price task cancelled.")
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in update_sol_price task: {e}", exc_info=True)
    finally:
        logger.info("🛑 update_sol_price task finished.")

```

---

## 📂 sql

---

### 📄 01_create_tokens.sql

```sql
-- Create the tokens table
CREATE TABLE IF NOT EXISTS tokens (
    mint TEXT PRIMARY KEY,          -- token mint
    traderPublicKey TEXT,           -- token creator's wallet address
    initialBuy NUMERIC,             -- initially buyed tokens
    solAmount NUMERIC,              -- initially spent amount of SOL
    bondingCurveKey TEXT,           -- bondingCurve key
    vTokensInBondingCurve NUMERIC,  -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,     -- SOL in BondingCurve
    marketCapSol NUMERIC,           -- market cap in SOL
    name TEXT,                      -- token name
    symbol TEXT,                    -- token symbol
    uri TEXT,                       -- META URL
    website TEXT,                   -- website link, fetched from META URL
    telegram TEXT,                  -- telegram link, fetched from META URL
    twitter TEXT,                   -- twitter link, fetched from META URL
    socials_score INTEGER,          -- calculated social score
    socials_last_checked TIMESTAMP WITH TIME ZONE,  -- last try to fetch META URL
    sol_price_usd NUMERIC,                          -- SOL price at token creation
    is_active BOOLEAN DEFAULT TRUE,                 -- TRUE or FALLS for considering in check_buy_opportunities
    last_trade TIMESTAMP WITH TIME ZONE,            -- TIMESTAMP of the last Trade event, updated when a new TRADE is fetched
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- creation TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS tokens_backup (
    LIKE tokens INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE tokens_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 02_create_trades.sql

```sql
-- Create the trades table
CREATE TABLE IF NOT EXISTS trades (
    signature TEXT PRIMARY KEY,         -- signature of the token event
    mint TEXT,                          -- tokens mint address
    tx_type TEXT,                       -- event type 'buy' or 'sell'
    token_amount NUMERIC,               -- amount of tokens traded
    sol_amount NUMERIC,                 -- amount of SOL traded
    price NUMERIC,                      -- token price in SOL
    bondingCurveKey TEXT,               -- BondingCurve key
    vTokensInBondingCurve NUMERIC,      -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,         -- amount of SOL in BondingCurve
    marketCapSol NUMERIC,               -- market cap in SOL
    sol_price_usd NUMERIC,              -- actual SOL price in USD at the time of the trade event
    market_cap_calculated NUMERIC,      -- calculated market cap in USD
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of the trade event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS trades_backup (
    LIKE trades INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE trades_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE trades_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 03_create_rugcheck.sql

```sql
CREATE TABLE IF NOT EXISTS rugcheck (
    mint TEXT PRIMARY KEY REFERENCES tokens(mint) ON DELETE CASCADE,
    tokenProgram TEXT,
    creator TEXT,
    token_mintAuthority TEXT,
    token_supply NUMERIC,
    token_decimals INTEGER,
    token_isInitialized BOOLEAN,
    token_freezeAuthority TEXT,
    tokenMeta_name TEXT,
    tokenMeta_symbol TEXT,
    tokenMeta_uri TEXT,
    tokenMeta_mutable BOOLEAN,
    tokenMeta_updateAuthority TEXT,
    freezeAuthority TEXT,
    mintAuthority TEXT,
    risks TEXT,
    score INTEGER,
    fileMeta_description TEXT,
    fileMeta_name TEXT,
    fileMeta_symbol TEXT,
    fileMeta_image TEXT,
    totalMarketLiquidity NUMERIC,
    totalLPProviders INTEGER,
    rugged BOOLEAN,
    tokenType TEXT,
    transferFee_pct NUMERIC,
    transferFee_maxAmount NUMERIC,
    transferFee_authority TEXT,
    graphInsidersDetected INTEGER,
    detectedAt TIMESTAMP WITH TIME ZONE,
    full_data TEXT,
    last_checked TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS rugcheck_backup (
    LIKE rugcheck INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE rugcheck_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE rugcheck_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 04_create_portfolio.sql

```sql
-- Original portfolio table creation
CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    mint TEXT,
    tx_type TEXT,                     -- 'buy' or 'sell'
    price NUMERIC,                    -- Price per token at the time of tx
    market_cap NUMERIC,               -- Market cap at the time of tx
    sol_amount NUMERIC,               -- Gross SOL spent (buy) or received (sell, before fees)
    sol_price_usd NUMERIC,            -- SOL price in USD at the time of tx
    tokens NUMERIC,                   -- Number of tokens bought or sold in this tx
    fee NUMERIC,                      -- Fee associated with this tx
    tip NUMERIC,                      -- Tip associated with this tx
    profit NUMERIC,                   -- Profit/Loss for sell tx (net_sol_received - cost_basis)
    status TEXT,                      -- Status of the original buy position ('active', 'closed')
    reason TEXT,                      -- Reason for sell ('Stop Loss', 'First TP', 'Second TP', 'Trailing SL', 'Breakeven SL', etc.)

    -- Fields primarily relevant for the original 'buy' entry
    total_investment_sol NUMERIC,     -- Total SOL invested in this position (including fees)
    initial_tokens NUMERIC,           -- Total tokens acquired in the initial buy tx
    remaining_tokens NUMERIC,         -- Tokens currently held from the initial buy tx (updated on sells)
    highest_price NUMERIC NOT NULL DEFAULT 0.0, -- Highest price observed since the buy
    stop_loss_price NUMERIC,          -- Current active stop loss price level
    initial_tp_price NUMERIC,         -- Calculated price for the first take profit
    second_tp_price NUMERIC,          -- Calculated price for the second take profit
    first_tp_hit BOOLEAN NOT NULL DEFAULT FALSE, -- Flag indicating if the first TP has been triggered

    settings JSONB,                   -- Settings for this position (e.g. stop loss price)

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS portfolio_backup (
    LIKE portfolio INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE portfolio_backup ADD COLUMN IF NOT EXISTS backed_up TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE portfolio_backup ALTER COLUMN timestamp DROP DEFAULT;

```

---

### 📄 05_create_migrations.sql

```sql
CREATE TABLE IF NOT EXISTS migrations (
    signature TEXT PRIMARY KEY, -- signature of the token event
    mint TEXT,                  -- tokens mint address
    txType TEXT,                -- event type 'migrate'
    pool TEXT,                  -- migration pool
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of migration event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS migrations_backup (
    LIKE migrations INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE migrations_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE migrations_backup ALTER COLUMN timestamp DROP DEFAULT;
```

---

### 📄 06_create_creator_wallets.sql

```sql
CREATE TABLE IF NOT EXISTS creator_wallets (
    wallet_address TEXT PRIMARY KEY,
    token_count INTEGER DEFAULT 0,
    last_token_time TIMESTAMP WITH TIME ZONE
);
```

---

### 📄 07_create_sol_price_usd.sql

```sql
CREATE TABLE IF NOT EXISTS sol_price_usd (
    id SERIAL PRIMARY KEY,
    price  NUMERIC(15, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

### 📄 08_create_indexes.sql

```sql
-- *********************************************
-- INDEXES FOR BASE TABLES
-- *********************************************

-- Tokens Table
CREATE INDEX IF NOT EXISTS idx_tokens_mint ON tokens(mint);
CREATE INDEX IF NOT EXISTS idx_tokens_traderPublicKey ON tokens(traderPublicKey);
CREATE INDEX IF NOT EXISTS idx_tokens_socials_score ON tokens(socials_score);
CREATE INDEX IF NOT EXISTS idx_tokens_name ON tokens(name);
CREATE INDEX IF NOT EXISTS idx_tokens_is_active_timestamp ON tokens(is_active, timestamp DESC);

-- Trades Table
CREATE INDEX IF NOT EXISTS idx_trades_signature ON trades(signature);
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp ON trades(mint, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_mint_sol_amount ON trades(mint, sol_amount);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);

-- Portfolio Table
CREATE INDEX IF NOT EXISTS idx_portfolio_mint ON portfolio(mint);
CREATE INDEX IF NOT EXISTS idx_portfolio_active_buy 
ON portfolio(mint, tx_type, status)
WHERE status = 'active' AND tx_type = 'buy';

-- Rugcheck Table
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked ON rugcheck(mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_score ON rugcheck(score);

-- *********************************************
-- INDEXES FOR BACKUP TABLES (if actively queried)
-- *********************************************

-- Tokens Backup
CREATE INDEX IF NOT EXISTS idx_tokens_backup_mint ON tokens_backup(mint);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_socials_score ON tokens_backup(socials_score);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_name ON tokens_backup(name);

-- Trades Backup
CREATE INDEX IF NOT EXISTS idx_trades_backup_mint_timestamp ON trades_backup(mint, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_backup_signature ON trades_backup(signature);

-- Rugcheck Backup
CREATE INDEX IF NOT EXISTS idx_rugcheck_backup_mint_last_checked ON rugcheck_backup(mint, last_checked DESC);

-- *********************************************
-- SPECIALIZED INDEXES FOR VIEW QUERIES
-- *********************************************

-- For get_filtered_tokens (RecentVolume CTE)
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp_sol 
ON trades(mint, timestamp DESC, sol_amount);

-- For LatestRugcheck CTE in views
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked_desc 
ON rugcheck(mint, last_checked DESC);

-- For portfolio-related view joins
CREATE INDEX IF NOT EXISTS idx_portfolio_mint_status 
ON portfolio(mint, status);
```

---

### 📄 09_create_views.sql

```sql
-- sql/12_create_views.sql

-- View for combined tokens and tokens_backup
-- Prioritizes data from 'tokens' if a mint exists in both.
CREATE OR REPLACE VIEW v_tokens AS
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, is_active, last_trade, timestamp
FROM tokens
UNION ALL
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, FALSE AS is_active, last_trade, timestamp -- Treat backed up as inactive
FROM tokens_backup tb
WHERE NOT EXISTS (SELECT 1 FROM tokens t WHERE t.mint = tb.mint);

-- View for combined trades and trades_backup
CREATE OR REPLACE VIEW v_trades AS
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades
UNION ALL
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades_backup;

-- View for combined rugcheck and rugcheck_backup
-- Note: Getting the *latest* score per mint will be handled in the query using this view.
CREATE OR REPLACE VIEW v_rugcheck AS
SELECT mint, score, token_supply, last_checked FROM rugcheck
UNION ALL
SELECT mint, score, token_supply, last_checked FROM rugcheck_backup;
```

---

## 📂 (Root Files)

---

### 📄 utils.py

```python
"""
Helper functions and utilities for the trading bot.
Includes URL validation, audio alerts, and log formatting.
"""

import os
import asyncio # <-- Add if used implicitly by called async functions
import pandas as pd
import numpy as np
import json
from datetime import datetime, timezone, timedelta # <-- Added timedelta
from logger import logger
# Type hint for DatabaseClient without creating circular dependency
from typing import TYPE_CHECKING, Dict, Optional, Tuple, List
if TYPE_CHECKING:
    from database_handler import DatabaseClient, get_token_lifespan 
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
    min_data_points: int = 100 # Minimum *trades* required per token
) -> Optional[Tuple[Dict[str, Dict[str, pd.DataFrame]], Dict[str, Dict[str, datetime]]]]:
    """
    Loads historical data for tokens active within a date range, determines their
    lifespans, and splits tokens chronologically based on their *start time* into
    training, validation, and test sets. Ensures complete token lifecycles are
    assigned to splits.

    Args:
        db_client: Initialized DatabaseClient instance.
        start_date_dt: Overall start datetime for data consideration (UTC).
        end_date_dt: Overall end datetime for data consideration (UTC).
        data_split_config: Dictionary with 'training', 'validation', 'test' percentages.
        min_data_points: Minimum number of trades a token must have within the overall
                         period to be considered.

    Returns:
        A tuple containing:
        - historical_data_sets (dict): {'train': {mint: df}, 'validation': {mint: df}, 'test': {mint: df}}
        - token_lifespans (dict): {mint: {'start_ts': dt, 'end_ts': dt}} for all loaded tokens.
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

        # --- Fetch candidate mints AND their lifespans ---
        logger.info("Fetching mints and lifespans active within the period...")
        # Query to get mints with min trades and their first/last trade time within the period
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
            WHERE rt.rn_asc = 1 OR rt.rn_desc = 1 -- Optimization to only join needed rows
            GROUP BY mc.mint, mc.trade_count;
        """
        candidate_records = await db_client.pool.fetch(query_mints_lifespans, start_date, end_date, min_data_points)

        if not candidate_records:
            logger.error(f"No tokens found with at least {min_data_points} trades in the specified period.")
            return None

        token_lifespans_map: Dict[str, Dict[str, datetime]] = {}
        mints_to_load: List[str] = []
        for r in candidate_records:
            mint = r['mint']
            start_ts = r['first_trade_ts']
            end_ts = r['last_trade_ts']
            if mint and start_ts and end_ts:
                 # Ensure UTC
                start_ts = start_ts.replace(tzinfo=timezone.utc) if start_ts.tzinfo is None else start_ts.astimezone(timezone.utc)
                end_ts = end_ts.replace(tzinfo=timezone.utc) if end_ts.tzinfo is None else end_ts.astimezone(timezone.utc)
                # Add buffer to end_ts
                end_ts += timedelta(seconds=1)
                token_lifespans_map[mint] = {'start_ts': start_ts, 'end_ts': end_ts}
                mints_to_load.append(mint)
            else:
                 logger.warning(f"Missing lifespan info for mint {mint} in query result. Skipping.")


        if not mints_to_load:
            logger.error("No valid mints with lifespans found after processing query results.")
            return None

        logger.info(f"Found {len(mints_to_load)} candidate mints with lifespan info. Fetching detailed data...")

        # --- Fetch detailed historical data for these mints ---
        # Fetch data slightly wider than the lifespan range just in case? No, fetch exact range needed.
        all_historical_data = await db_client.get_historical_data_for_backtesting(mints_to_load, start_date, end_date)

        if not all_historical_data:
            logger.error("Failed to fetch any historical data for the candidate mints.")
            return None
        logger.info(f"Successfully fetched detailed data for {len(all_historical_data)} tokens.")

        # --- Filter data based on fetched lifespans (ensure consistency) ---
        filtered_historical_data = {}
        final_token_lifespans = {}
        for mint, df in all_historical_data.items():
             if mint not in token_lifespans_map: continue # Should not happen

             lifespan = token_lifespans_map[mint]
             df_filtered = df[(df.index >= lifespan['start_ts']) & (df.index <= lifespan['end_ts'])]

             if not df_filtered.empty:
                 filtered_historical_data[mint] = df_filtered
                 final_token_lifespans[mint] = lifespan # Keep lifespan info for valid tokens
             else:
                  logger.warning(f"Data for mint {mint} became empty after filtering by its lifespan. Skipping.")

        if not filtered_historical_data:
             logger.error("No data remained after filtering tokens by their calculated lifespans.")
             return None

        # --- Split tokens into sets based on their START time ---
        # Sort tokens by their start time
        sorted_mints = sorted(final_token_lifespans.keys(), key=lambda m: final_token_lifespans[m]['start_ts'])

        n_tokens = len(sorted_mints)
        n_train = int(n_tokens * data_split_config['training'])
        n_val = int(n_tokens * data_split_config['validation'])
        # Ensure calculation handles potential rounding issues if percentages don't sum perfectly
        n_test = n_tokens - n_train - n_val

        logger.info(f"Assigning tokens to splits: Train={n_train}, Validation={n_val}, Test={n_test}")

        historical_data_sets: Dict[str, Dict[str, pd.DataFrame]] = {'train': {}, 'validation': {}, 'test': {}}

        for i, mint in enumerate(sorted_mints):
            df = filtered_historical_data[mint] # Get the filtered df
            if i < n_train:
                historical_data_sets['train'][mint] = df
            elif i < n_train + n_val:
                historical_data_sets['validation'][mint] = df
            else:
                # Only assign to test if n_test > 0
                if n_test > 0 and i < n_train + n_val + n_test :
                     historical_data_sets['test'][mint] = df
                # Handle cases where sum might be slightly off due to int conversion
                # elif n_test <= 0 and i >= n_train + n_val:
                #      logger.warning(f"Token {mint} (index {i}) falls outside calculated splits. Assigning to validation as fallback.")
                #      historical_data_sets['validation'][mint] = df


        # Log split sizes
        logger.info(f"Data split complete. Training tokens: {len(historical_data_sets['train'])}, Validation tokens: {len(historical_data_sets['validation'])}, Test tokens: {len(historical_data_sets['test'])}")

        # Basic check if training set is populated
        if not historical_data_sets['train']:
             logger.error("Training set is empty after chronological splitting!")
             return None

        # Return both the split datasets and the lifespan map for all loaded tokens
        return historical_data_sets, final_token_lifespans

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
```

---

## 📂 web_app

---

### 📄 app copy.py

```python
from flask import Flask, jsonify, render_template
import os
import subprocess
import signal
import threading

app = Flask(__name__)

bot_process = None

def start_bot():
    global bot_process
    bot_process = subprocess.Popen(['python', '../main.py'])

def stop_bot():
    global bot_process
    if bot_process:
        bot_process.send_signal(signal.SIGINT)
        bot_process.wait()
        bot_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def logs():
    log_file_path = os.path.join('..', 'log', '__log-files_')
    with open(log_file_path, 'r') as file:
        log_content = file.readlines()
    return jsonify({'logs': ''.join(log_content)})

@app.route('/start_bot', methods=['POST'])
def start_bot_route():
    threading.Thread(target=start_bot).start()
    return jsonify({'status': 'Bot started'})

@app.route('/stop_bot', methods=['POST'])
def stop_bot_route():
    stop_bot()
    return jsonify({'status': 'Bot stopped'})

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, jsonify, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def logs():
    log_file_path = os.path.join('..', 'log', '__log-files_')
    with open(log_file_path, 'r') as file:
        log_content = file.readlines()
    return jsonify({'logs': ''.join(log_content)})

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def logs():
    log_file_path = os.path.join('..', 'log', 'bot.log')  # Adjust the path as necessary
    with open(log_file_path, 'r') as log_file:
        logs = log_file.read()
    return jsonify({'logs': logs})

if __name__ == '__main__':
    app.run(debug=True)
import os
import asyncio
import signal
import threading
from flask import Flask, jsonify, render_template
from main import TradingBot

app = Flask(__name__)

# Global variable to manage the bot's state and lifecycle
bot_instance = None
bot_thread = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/log_file')
def log_file():
    log_path = os.path.join('..', 'log', '__log-files_')
    try:
        with open(log_path, 'r') as file:
            logs = file.readlines()
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/start_bot')
def start_bot():
    global bot_instance, bot_thread
    if bot_instance is None:
        bot_instance = TradingBot()
        bot_thread = threading.Thread(target=bot_instance.loop.run_until_complete, args=(bot_instance.main(),))
        bot_thread.start()
        return jsonify({'status': 'Bot started'})
    else:
        return jsonify({'status': 'Bot is already running'})

@app.route('/stop_bot')
def stop_bot():
    global bot_instance, bot_thread
    if bot_instance is not None:
        bot_instance.state.trigger_shutdown()
        bot_thread.join()
        bot_instance = None
        bot_thread = None
        return jsonify({'status': 'Bot stopped'})
    else:
        return jsonify({'status': 'Bot is not running'})

if __name__ == '__main__':
    app.run(debug=True)
import os

from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/log_file')
def log_file():
    log_path = os.path.join('..', 'log', '__log-files_')
    try:
        with open(log_path, 'r') as file:
            logs = file.readlines()
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
import os
import threading
from main import TradingBot
import logging
import config
import sys
import asyncio
import pandas as pd
from flask import Flask, request, jsonify, render_template
import json         # For reading the price file
import requests     # For synchronous API fallback
import time         # For checking file age
import os           # For file path operations

# Add project root to the Python path to allow importing modules from the parent directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from database_handler import DatabaseClient
    from logger import logger # Assuming logger is configured similarly
    from config import SOL_PRICE_API_URL # Import the API URL
except ImportError as e:
    print(f"Error importing modules: {e}. Make sure you are running from the project root or the necessary modules are in the Python path.")
    sys.exit(1)


# Define the path for the shared SOL price file (must match state_manager.py)
SOL_PRICE_FILE = 'data/sol_price.json'
MAX_FILE_AGE_SECONDS = 3600 # 5 minutes - how old the file can be before we call the API

# Initialize Flask app
import threading
import queue
import logger

app = Flask(__name__)
log_queue = logger.log_queue

def run_bot():
    import main
    main.main()

bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

@app.route('/logs')
def logs():
    logs = []
    while not log_queue.empty():
        logs.append(log_queue.get())
    return jsonify(logs)

# Configure logging
log_file_path = os.path.join(config.LOG_STORAGE_PATH, f"{config.LOGGER_NAME}.log")
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/log_file')
def log_file():
    log_file_path = os.path.join(config.LOG_STORAGE_PATH, f"{config.LOGGER_NAME}.log")
    try:
        with open(log_file_path, 'r') as file:
            logs = file.readlines()
        return jsonify(logs)
    except FileNotFoundError:
        return jsonify({"error": "Log file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SOL Price Fetching Logic ---

def get_sol_price_from_file():
    """Tries to read the SOL price from the shared JSON file."""
    try:
        if os.path.exists(SOL_PRICE_FILE):
            file_mod_time = os.path.getmtime(SOL_PRICE_FILE)
            if (time.time() - file_mod_time) < MAX_FILE_AGE_SECONDS:
                with open(SOL_PRICE_FILE, 'r') as f:
                    data = json.load(f)
                    price = data.get("price")
                    if isinstance(price, (int, float)):
                        logger.info(f"Read SOL price {price} from file {SOL_PRICE_FILE}")
                        return float(price)
                    else:
                        logger.warning(f"Invalid price data type in {SOL_PRICE_FILE}")
            else:
                logger.warning(f"{SOL_PRICE_FILE} is older than {MAX_FILE_AGE_SECONDS} seconds.")
        else:
            logger.info(f"{SOL_PRICE_FILE} not found.") # Info level, as this is expected if main.py isn't running
    except (IOError, json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Error reading SOL price from {SOL_PRICE_FILE}: {e}")
    return None # Return None if file read fails or file is too old/missing

def get_sol_price_from_api():
    """Fetches the SOL price directly from the API (synchronous fallback)."""
    logger.info(f"Falling back to fetching SOL price directly from API: {SOL_PRICE_API_URL}")
    try:
        response = requests.get(SOL_PRICE_API_URL, timeout=10) # Add timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        price = data.get("solana", {}).get("usd")
        if isinstance(price, (int, float)):
            logger.info(f"Fetched SOL price {price} from API")
            return float(price)
        else:
            logger.error(f"Invalid price data type received from API: {price}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SOL price from API: {e}")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Error parsing SOL price API response: {e}")
    return None # Return None if API call fails

def get_current_sol_price():
    """Gets SOL price, preferring the file, falling back to API."""
    price = get_sol_price_from_file()
    if price is None:
        price = get_sol_price_from_api()
    return price

# --- End SOL Price Fetching Logic ---

# No global DB client instance for this simplified approach

# Helper function to manage DB connection per request
async def execute_db_query(query_func, *args):
    """Creates a connection, executes a query function, and closes."""
    db_client = DatabaseClient()
    try:
        await db_client.connect()
        logger.debug("DB connection established for request.")
        result = await query_func(db_client, *args)
        return result
    except Exception as e:
        logger.exception(f"Database query failed: {e}")
        raise # Re-raise the exception to be handled by the route
    finally:
        if db_client.pool:
            await db_client.close()
            logger.debug("DB connection closed for request.")

# Wrapper for the specific query needed by the API (trade history)
async def fetch_trade_history_query(db_client, mints):
    return await db_client.get_trade_history(mints)

# Wrapper for portfolio transactions query
async def fetch_portfolio_transactions_query(db_client, mints):
    return await db_client.get_portfolio_transactions(mints)
# Routes for the dashboard pages
@app.route('/')
@app.route('/charts')
async def index():
    """Renders the main charts page. Token list is loaded dynamically via JS."""
    # No initial token fetching here anymore
    return render_template('index.html') # Pass no token list initially

@app.route('/config')
async def configuration():
    """Renders the configuration page."""
    return render_template('configuration.html')

@app.route('/portfolio')
async def portfolio():
    """Renders the portfolio page."""
    return render_template('portfolio.html')

@app.route('/analytics')
async def analytics():
    """Renders the analytics page."""
    return render_template('analytics.html')

# API endpoint to get filtered tokens for the dropdown
@app.route('/api/filtered_tokens', methods=['GET'])
async def get_filtered_tokens_api():
    """API endpoint to fetch tokens based on filter criteria."""
    # Get filter parameters from query string, providing defaults
    max_socials = request.args.get('max_socials', default=100, type=int)
    max_rugcheck = request.args.get('max_rugcheck', default=10000, type=int)
    min_volume = request.args.get('min_volume', default=0, type=float)
    time_window_minutes = request.args.get('time_window', default=60, type=int) # e.g., 60, 360, 1440
    # Get portfolio_only flag, converting 'true'/'false' string to boolean
    portfolio_only = request.args.get('portfolio_only', default=False, type=lambda v: v.lower() == 'true')

    current_sol_price = get_current_sol_price()
    if current_sol_price is None:
         # Handle error: maybe return an error response or use a default SOL price
         logger.error("Could not get SOL price for volume conversion in /api/filtered_tokens")
         return jsonify({"error": "Could not determine SOL price"}), 503

    min_volume_sol = (min_volume / current_sol_price) if min_volume > 0 and current_sol_price > 0 else 0 # Convert to SOL, handle zero price

    logger.info(f"Received request for filtered tokens: socials<={max_socials}, rug<={max_rugcheck}, vol>={min_volume_sol} (last {time_window_minutes} min), portfolio_only={portfolio_only}") # Updated log

    # Wrapper for the specific query needed by this route
    async def fetch_filtered_tokens_query(db_client, ms, mr, mv, tw, po): # Added po
        return await db_client.get_filtered_tokens(max_socials=ms, max_rugcheck=mr, min_volume_sol=mv, time_window_minutes=tw, portfolio_only=po) # Pass po

    try:
        # Execute the query using the helper
        filtered_tokens = await execute_db_query(
            fetch_filtered_tokens_query,
            max_socials,
            max_rugcheck,
            min_volume_sol,
            time_window_minutes,
            portfolio_only # Pass portfolio_only
        )
        logger.info(f"Returning {len(filtered_tokens)} tokens matching filters.")
        return jsonify(filtered_tokens)
    except Exception as e:
        # Error already logged by execute_db_query
        logger.error(f"Failed to fetch filtered tokens for API request.")
        return jsonify({"error": "Failed to fetch filtered tokens"}), 500

# API endpoint to get token chart data (remains largely the same)
@app.route('/api/token_chart_data', methods=['POST'])
async def get_token_chart_data():
    """API endpoint to fetch and process trade and portfolio data for charting."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    mints = data.get('mints')

    if not mints or not isinstance(mints, list):
        return jsonify({"error": "Missing or invalid 'mints' list in request body"}), 400

    logger.info(f"Received request for chart data for mints: {mints}")

    try:
        # Execute the trade history query
        trade_history = await execute_db_query(fetch_trade_history_query, mints)
        # Execute the portfolio transactions query
        portfolio_transactions = await execute_db_query(fetch_portfolio_transactions_query, mints)

        if not trade_history:
            logger.warning(f"No trade history found for mints: {mints}")
            # Still return portfolio data if it exists, even without trade history
            # The frontend will need to handle cases where only portfolio markers are available
            processed_portfolio_data = {}
            if portfolio_transactions:
                 # Process portfolio timestamps relative to *something* if no trade history
                 # For simplicity, let's just return the raw portfolio data here if no trades
                 # Or maybe calculate elapsed time from the *first* portfolio event?
                 # Let's return it for now, frontend needs adjustment.
                 # A better approach might be to find the earliest timestamp across both datasets.
                 # For now, returning raw portfolio data if no trade history.
                 logger.warning(f"Returning only portfolio data as trade history is missing for {mints}")
                 # Convert timestamps to Unix ms for JS compatibility before returning
                 for mint_key, data_val in portfolio_transactions.items():
                     for tx_type in ['buys', 'sells']:
                         if tx_type in data_val:
                             for event in data_val[tx_type]:
                                 # Assuming event['timestamp'] is a datetime object from DB
                                 event['time'] = int(pd.to_datetime(event['timestamp']).timestamp() * 1000)
                                 del event['timestamp'] # Remove original datetime object
                 return jsonify(portfolio_transactions) # Adjust frontend to handle this structure
            else:
                 return jsonify({}) # Return empty if neither trade nor portfolio data exists


        # Fetch the current SOL price
        sol_price_usd = get_current_sol_price()
        if sol_price_usd is None:
            logger.error("Failed to obtain SOL price. Cannot calculate USD prices.")
            return jsonify({"error": "Could not determine SOL price"}), 503

        logger.info(f"Using SOL price: {sol_price_usd} USD for calculations.")

        # Process trade data with pandas
        df = pd.DataFrame(trade_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price_sol'] = pd.to_numeric(df['price'])
        df['price_usd'] = df['price_sol'] * sol_price_usd

        chart_data = {}
        grouped = df.groupby('mint')

        # Find the overall minimum timestamp across all requested mints in trade history
        # This ensures consistent x-axis (elapsed time) across multiple charts if displayed together
        # If only one mint is requested, this is just the min timestamp for that mint.
        overall_min_timestamp = df['timestamp'].min()
        logger.debug(f"Overall minimum timestamp for relative calculation: {overall_min_timestamp}")


        for mint, group in grouped:
            if group.empty:
                continue

            group = group.sort_values(by='timestamp')
            # Use the overall min timestamp for consistent elapsed time calculation
            group['elapsed_minutes'] = (group['timestamp'] - overall_min_timestamp).dt.total_seconds() / 60.0

            # Prepare trade data
            mint_chart_data = {
                'time': group['elapsed_minutes'].round(2).tolist(),
                'price_usd': group['price_usd'].round(4).tolist(),
                'buys': [],
                'sells': []
            }

            # Process portfolio data for this mint
            if mint in portfolio_transactions:
                mint_portfolio = portfolio_transactions[mint]
                for buy_event in mint_portfolio.get('buys', []):
                    buy_timestamp = pd.to_datetime(buy_event['timestamp'])
                    elapsed_minutes = (buy_timestamp - overall_min_timestamp).total_seconds() / 60.0
                    price_usd = buy_event['price'] * sol_price_usd # Assume portfolio price is SOL, convert to USD
                    mint_chart_data['buys'].append({
                        'time': round(elapsed_minutes, 2),
                        'price_usd': round(price_usd, 4)
                    })
                for sell_event in mint_portfolio.get('sells', []):
                    sell_timestamp = pd.to_datetime(sell_event['timestamp'])
                    elapsed_minutes = (sell_timestamp - overall_min_timestamp).total_seconds() / 60.0
                    price_usd = sell_event['price'] * sol_price_usd # Assume portfolio price is SOL, convert to USD
                    mint_chart_data['sells'].append({
                        'time': round(elapsed_minutes, 2),
                        'price_usd': round(price_usd, 4)
                    })
                logger.debug(f"Processed {len(mint_chart_data['buys'])} buys and {len(mint_chart_data['sells'])} sells for mint: {mint}")


            chart_data[mint] = mint_chart_data
            logger.debug(f"Processed chart data (trades + portfolio) for mint: {mint}, {len(group)} trade points")

        return jsonify(chart_data)

    except Exception as e:
        # Error already logged by execute_db_query if it was a DB error
        logger.error(f"Error processing chart data request for mints {mints}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error processing request"}), 500

# Optional: Add a shutdown hook to close the DB connection pool gracefully
# This requires a more complex setup with signals or a different web server like gunicorn
# For simplicity with Flask's built-in server, we might omit explicit pool closing on exit.

if __name__ == '__main__':
    # Port can be changed here or via environment variable if needed
    # Keeping port 89 as manually set by the user previously.
    port = int(os.environ.get("FLASK_PORT", 89))
    logger.info(f"Starting Flask development server on port {port}...")

# Global variable to hold the bot thread
bot_thread = None

@app.route('/start_bot', methods=['POST'])
def start_bot():
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=lambda: TradingBot().loop.run_until_complete(TradingBot().main()))
        bot_thread.start()
        logger.info("Bot started.")
        return jsonify({"status": "Bot started"}), 200
    else:
        logger.info("Bot is already running.")
        return jsonify({"status": "Bot is already running"}), 200

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    global bot_thread
    if bot_thread is not None and bot_thread.is_alive():
        TradingBot().loop.call_soon_threadsafe(TradingBot().state.trigger_shutdown)
        bot_thread.join(timeout=10)
        TradingBot().loop.run_until_complete(TradingBot().shutdown())
        logger.info("Bot stopped.")
        return jsonify({"status": "Bot stopped"}), 200
    else:
        logger.info("Bot is not running.")
        return jsonify({"status": "Bot is not running"}), 200

# Ensure only one instance of TradingBot is created
bot_instance = TradingBot()

@app.route('/start_bot', methods=['POST'])
def start_bot():
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=lambda: bot_instance.loop.run_until_complete(bot_instance.main()))
        bot_thread.start()
        logger.info("Bot started.")
        return jsonify({"status": "Bot started"}), 200
    else:
        logger.info("Bot is already running.")
        return jsonify({"status": "Bot is already running"}), 200

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    global bot_thread
    if bot_thread is not None and bot_thread.is_alive():
        bot_instance.loop.call_soon_threadsafe(bot_instance.state.trigger_shutdown)
        bot_thread.join(timeout=10)
        bot_instance.loop.run_until_complete(bot_instance.shutdown())
        logger.info("Bot stopped.")
        return jsonify({"status": "Bot stopped"}), 200
    else:
        logger.info("Bot is not running.")
        return jsonify({"status": "Bot is not running"}), 200
    # Removed explicit asyncio event loop handling - Flask/Werkzeug handles it.
    app.run(debug=True, port=port)
```

---

### 📄 app.py

```python
import os
import threading
import queue
import sys
import asyncio
import pandas as pd
from flask import Flask, request, jsonify, render_template
import json         # For reading the price file
import requests     # For synchronous API fallback
import time         # For checking file age
import os           # For file path operations
from datetime import datetime, timezone
import numpy as np

# Add project root to the Python path to allow importing modules from the parent directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from database_handler import DatabaseClient
    from trading_bot import TradingBot
    from state_manager import GlobalState
    # Only import log_queue, not the logger instance or setup function from logger.py
    from logger import log_queue
    import config  # Import the API URL
except ImportError as e:
    print(f"Error importing modules: {e}. Make sure you are running from the project root or the necessary modules are in the Python path.")
    sys.exit(1)


# Define the path for the shared SOL price file (must match state_manager.py)
SOL_PRICE_FILE = 'data/sol_price.json'
MAX_FILE_AGE_SECONDS = 3600 # 5 minutes - how old the file can be before we call the API

# Removed global setup_logging() call. Bot will configure its own logging.
app = Flask(__name__)
# Removed redirection of Flask logger to keep logs separate
# Flask logs will go to console by default

db_client = DatabaseClient()

# Define paths for communication files relative to project root
COMMAND_FILE = os.path.join(project_root, 'data', 'bot_command.txt')
STATUS_FILE = os.path.join(project_root, 'data', 'bot_status.txt')
LOG_FILE = os.path.join(project_root, config.LOG_STORAGE_PATH, f"{config.LOGGER_NAME}.log")

async def get_db():
    if not db_client.pool:
        await db_client.connect()
    return db_client

# --- Helper Functions for File Flags ---
def write_command(command):
    """Writes a command (START/STOP) to the command file."""
    try:
        with open(COMMAND_FILE, 'w') as f:
            f.write(command.upper())
        app.logger.info(f"Wrote command '{command}' to {COMMAND_FILE}")
    except IOError as e:
        app.logger.error(f"Error writing command file {COMMAND_FILE}: {e}")

def read_status():
    """Reads the status (RUNNING/STOPPED) from the status file."""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r') as f:
                status = f.read().strip().upper()
                # Basic validation
                if status in ["RUNNING", "STOPPED", "STARTING", "STOPPING", "ERROR"]:
                     return status
                else:
                     app.logger.warning(f"Read invalid status '{status}' from {STATUS_FILE}. Defaulting to STOPPED.")
                     return "STOPPED" # Default to STOPPED if file content is invalid
        else:
            # If status file doesn't exist, assume stopped
            return "STOPPED"
    except IOError as e:
        app.logger.error(f"Error reading status file {STATUS_FILE}: {e}")
        return "ERROR" # Indicate an error reading the status

def convert_datetime(o):
    """Helper to serialize datetime objects."""
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Type {type(o)} not serializable")
# --- End Helper Functions ---

# Removed redundant /log_file endpoint. /logs now reads from the file.
# --- SOL Price Fetching Logic ---
def get_sol_price_from_file():
    """Tries to read the SOL price from the shared JSON file."""
    try:
        if os.path.exists(SOL_PRICE_FILE):
            file_mod_time = os.path.getmtime(SOL_PRICE_FILE)
            if (time.time() - file_mod_time) < MAX_FILE_AGE_SECONDS:
                with open(SOL_PRICE_FILE, 'r') as f:
                    data = json.load(f)
                    price = data.get("price")
                    if isinstance(price, (int, float)):
                        app.logger.info(f"Read SOL price {price} from file {SOL_PRICE_FILE}") # Use app.logger
                        return float(price)
                    else:
                        app.logger.warning(f"Invalid price data type in {SOL_PRICE_FILE}") # Use app.logger
            else:
                app.logger.warning(f"{SOL_PRICE_FILE} is older than {MAX_FILE_AGE_SECONDS} seconds.") # Use app.logger
        else:
            app.logger.info(f"{SOL_PRICE_FILE} not found.") # Use app.logger
    except (IOError, json.JSONDecodeError, KeyError, TypeError) as e:
        app.logger.error(f"Error reading SOL price from {SOL_PRICE_FILE}: {e}") # Use app.logger
    return None # Return None if file read fails or file is too old/missing

def get_sol_price_from_api():
    """Fetches the SOL price directly from the API (synchronous fallback)."""
    app.logger.info(f"Falling back to fetching SOL price directly from API: {config.SOL_PRICE_API_URL}") # Use app.logger
    try:
        response = requests.get(config.SOL_PRICE_API_URL, timeout=10) # Add timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        price = data.get("solana", {}).get("usd")
        if isinstance(price, (int, float)):
            app.logger.info(f"Fetched SOL price {price} from API") # Use app.logger
            return float(price)
        else:
            app.logger.error(f"Invalid price data type received from API: {price}") # Use app.logger
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching SOL price from API: {e}") # Use app.logger
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        app.logger.error(f"Error parsing SOL price API response: {e}") # Use app.logger
    return None # Return None if API call fails

def get_current_sol_price():
    """Gets SOL price, preferring the file, falling back to API."""
    price = get_sol_price_from_file()
    if price is None:
        price = get_sol_price_from_api()
    return price
# --- End SOL Price Fetching Logic ---

# Helper function to manage DB connection per request
async def execute_db_query(query_func, *args):
    """Creates a connection, executes a query function, and closes."""
    try:
        await db_client.connect()
        app.logger.debug("DB connection established for request.") # Use app.logger
        result = await query_func(db_client, *args)
        return result
    except Exception as e:
        app.logger.exception(f"Database query failed: {e}") # Use app.logger
        raise # Re-raise the exception to be handled by the route
    finally:
        if db_client.pool:
            await db_client.close()
            app.logger.debug("DB connection closed for request.") # Use app.logger

# Wrapper for the specific query needed by the API (trade history)
async def fetch_trade_history_query(db_client, mints):
    return await db_client.get_trade_history(mints)

# Wrapper for portfolio transactions query
async def fetch_portfolio_transactions_query(db_client, mints):
    return await db_client.get_portfolio_transactions(mints)
# Routes for the dashboard pages



@app.route('/logs')
def logs():
    """Reads the last N lines from the TradingBot log file."""
    MAX_LOG_LINES = 100 # Adjust as needed
    try:
        if not os.path.exists(LOG_FILE):
            return jsonify([]) # Return empty list if log file doesn't exist yet

        # Explicitly specify UTF-8 encoding and ignore errors
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            # Read all lines and take the last N
            lines = f.readlines()
            log_content = lines[-MAX_LOG_LINES:]
        # Strip newline characters for cleaner JSON output
        log_content = [line.strip() for line in log_content]
        return jsonify(log_content)
    except IOError as e:
        app.logger.error(f"Error reading log file {LOG_FILE}: {e}")
        return jsonify({"error": f"Could not read log file: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error reading log file {LOG_FILE}: {e}")
        return jsonify({"error": f"Unexpected error reading log file: {e}"}), 500
    
@app.route('/')
@app.route('/charts')
async def index():
    """Renders the main charts page. Token list is loaded dynamically via JS."""
    # No initial token fetching here anymore
    return render_template('token_price_analysis.html') # Pass no token list initially

@app.route('/config')
async def configuration():
    """Renders the configuration page."""
    return render_template('configuration.html')

@app.route('/portfolio')
async def portfolio():
    """Renders the portfolio page."""

    # Fetch all tracked tokens
    async def fetch_tracked_tokens_query(db_client, bc): # Added po
        return await db_client.get_total_tracked_tokens(backedup=bc) # Pass po

    try:
        # Execute the query using the helper
        fetched_tokens = await execute_db_query(
            fetch_tracked_tokens_query,
            False
        )
        app.logger.info(f"Returning {len(fetched_tokens)} tokens matching filters.") # Use app.logger
        print(fetched_tokens) # Debug print to check the data structure

        total_tracked_tokens = fetched_tokens
    
    except Exception as e:
        # Error already logged by execute_db_query
        app.logger.error(f"Failed to fetch filtered tokens for API request.") # Use app.logger
        return jsonify({"error": "Failed to fetch filtered tokens"}), 500
    
    return render_template('portfolio.html')

@app.route('/analytics')
async def analytics():
    """Renders the analytics page."""
    return render_template('analytics.html')

# API endpoint to get filtered tokens for the dropdown
@app.route('/api/filtered_tokens', methods=['GET'])
async def get_filtered_tokens_api():
    """API endpoint to fetch tokens based on filter criteria."""
    # Get filter parameters from query string, providing defaults
    max_socials = request.args.get('max_socials', default=100, type=int)
    max_rugcheck = request.args.get('max_rugcheck', default=10000, type=int)
    min_volume = request.args.get('min_volume', default=0, type=float)
    time_window_minutes = request.args.get('time_window', default=60, type=int) # e.g., 60, 360, 1440
    # Get portfolio_only flag, converting 'true'/'false' string to boolean
    portfolio_only = request.args.get('portfolio_only', default=False, type=lambda v: v.lower() == 'true')
    # Get volume aggregation type, default to 'avg'

    current_sol_price = get_current_sol_price()
    if current_sol_price is None:
         # Handle error: maybe return an error response or use a default SOL price
         app.logger.error("Could not get SOL price for volume conversion in /api/filtered_tokens") # Use app.logger
         return jsonify({"error": "Could not determine SOL price"}), 503

    min_volume_sol = (min_volume / current_sol_price) if min_volume > 0 and current_sol_price > 0 else 0 # Convert to SOL, handle zero price

    app.logger.info(f"Received request for filtered tokens: socials<={max_socials}, rug<={max_rugcheck}, vol>={min_volume_sol} (last {time_window_minutes} min), portfolio_only={portfolio_only}") # Use app.logger

    # Wrapper for the specific query needed by this route
    async def fetch_filtered_tokens_query(db_client, ms, mr, mv, tw, po): # Added po
        return await db_client.get_filtered_tokens(max_socials=ms, max_rugcheck=mr, min_volume_sol=mv, time_window_minutes=tw, portfolio_only=po) # Pass po

    try:
        # Execute the query using the helper
        filtered_tokens = await execute_db_query(
            fetch_filtered_tokens_query,
            max_socials,
            max_rugcheck,
            min_volume_sol,
            time_window_minutes,
            portfolio_only
        )
        app.logger.info(f"Returning {len(filtered_tokens)} tokens matching filters.") # Use app.logger
        return jsonify(filtered_tokens)
    except Exception as e:
        # Error already logged by execute_db_query
        app.logger.error(f"Failed to fetch filtered tokens for API request.") # Use app.logger
        return jsonify({"error": "Failed to fetch filtered tokens"}), 500

# API endpoint to get token chart data (remains largely the same)
@app.route('/api/token_chart_data', methods=['POST'])
async def get_token_chart_data():
    """API endpoint to fetch and process trade and portfolio data for charting."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    mints = data.get('mints')

    if not mints or not isinstance(mints, list):
        return jsonify({"error": "Missing or invalid 'mints' list in request body"}), 400

    app.logger.info(f"Received request for chart data for mints: {mints}") # Use app.logger

    try:
        # Execute the trade history query
        trade_history = await execute_db_query(fetch_trade_history_query, mints)
        # Execute the portfolio transactions query
        portfolio_transactions = await execute_db_query(fetch_portfolio_transactions_query, mints)

        if not trade_history:
            app.logger.warning(f"No trade history found for mints: {mints}") # Use app.logger
            # Still return portfolio data if it exists, even without trade history
            # The frontend will need to handle cases where only portfolio markers are available
            processed_portfolio_data = {}
            if portfolio_transactions:
                 # Process portfolio timestamps relative to *something* if no trade history
                 # For simplicity, let's just return the raw portfolio data here if no trades
                 # Or maybe calculate elapsed time from the *first* portfolio event?
                 # Let's return it for now, frontend needs adjustment.
                 # A better approach might be to find the earliest timestamp across both datasets.
                 # For now, returning raw portfolio data if no trade history.
                 app.logger.warning(f"Returning only portfolio data as trade history is missing for {mints}") # Use app.logger
                 # Convert timestamps to Unix ms for JS compatibility before returning
                 for mint_key, data_val in portfolio_transactions.items():
                     for tx_type in ['buys', 'sells']:
                         if tx_type in data_val:
                             for event in data_val[tx_type]:
                                 # Assuming event['timestamp'] is a datetime object from DB
                                 event['time'] = int(pd.to_datetime(event['timestamp']).timestamp() * 1000)
                                 del event['timestamp'] # Remove original datetime object
                 return jsonify(portfolio_transactions) # Adjust frontend to handle this structure
            else:
                 return jsonify({}) # Return empty if neither trade nor portfolio data exists


        # Fetch the current SOL price
        sol_price_usd = get_current_sol_price()
        if sol_price_usd is None:
            app.logger.error("Failed to obtain SOL price. Cannot calculate USD prices.") # Use app.logger
            return jsonify({"error": "Could not determine SOL price"}), 503

        app.logger.info(f"Using SOL price: {sol_price_usd} USD for calculations.") # Use app.logger

        # Process trade data with pandas
        df = pd.DataFrame(trade_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price_sol'] = pd.to_numeric(df['price'])
        df['price_usd'] = df['price_sol'] * sol_price_usd

        chart_data = {}
        grouped = df.groupby('mint')

        # Find the overall minimum timestamp across all requested mints in trade history
        # This ensures consistent x-axis (elapsed time) across multiple charts if displayed together
        # If only one mint is requested, this is just the min timestamp for that mint.
        overall_min_timestamp = df['timestamp'].min()
        app.logger.debug(f"Overall minimum timestamp for relative calculation: {overall_min_timestamp}") # Use app.logger


        for mint, group in grouped:
            if group.empty:
                continue

            group = group.sort_values(by='timestamp')
            # Use the overall min timestamp for consistent elapsed time calculation
            group['elapsed_minutes'] = (group['timestamp'] - overall_min_timestamp).dt.total_seconds() / 60.0

            # Prepare trade data
            mint_chart_data = {
                'time': group['elapsed_minutes'].round(2).tolist(),
                'price_usd': group['price_usd'].round(4).tolist(),
                'buys': [],
                'sells': []
            }

            # Process portfolio data for this mint
            if mint in portfolio_transactions:
                mint_portfolio = portfolio_transactions[mint]
                for buy_event in mint_portfolio.get('buys', []):
                    buy_timestamp = pd.to_datetime(buy_event['timestamp'])
                    elapsed_minutes = (buy_timestamp - overall_min_timestamp).total_seconds() / 60.0
                    price_usd = buy_event['price'] * sol_price_usd # Assume portfolio price is SOL, convert to USD
                    mint_chart_data['buys'].append({
                        'time': round(elapsed_minutes, 2),
                        'price_usd': round(price_usd, 4)
                    })
                for sell_event in mint_portfolio.get('sells', []):
                    sell_timestamp = pd.to_datetime(sell_event['timestamp'])
                    elapsed_minutes = (sell_timestamp - overall_min_timestamp).total_seconds() / 60.0
                    price_usd = sell_event['price'] * sol_price_usd # Assume portfolio price is SOL, convert to USD
                    mint_chart_data['sells'].append({
                        'time': round(elapsed_minutes, 2),
                        'price_usd': round(price_usd, 4)
                    })
                app.logger.debug(f"Processed {len(mint_chart_data['buys'])} buys and {len(mint_chart_data['sells'])} sells for mint: {mint}") # Use app.logger


            chart_data[mint] = mint_chart_data
            app.logger.debug(f"Processed chart data (trades + portfolio) for mint: {mint}, {len(group)} trade points") # Use app.logger

        return jsonify(chart_data)

    except Exception as e:
        # Error already logged by execute_db_query if it was a DB error
        app.logger.error(f"Error processing chart data request for mints {mints}: {e}", exc_info=True) # Use app.logger
        return jsonify({"error": "Internal server error processing request"}), 500

@app.route('/start_bot', methods=['POST'])
def start_bot():
    """Signals the external bot process to start by writing to the command file."""
    app.logger.info("Received request to start bot via command file.")
    write_command("START")
    # We don't know the exact status immediately, client JS should poll /api/bot_status
    return jsonify({"status": "START command issued"}), 200

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    """Signals the external bot process to stop by writing to the command file."""
    app.logger.info("Received request to stop bot via command file.")
    write_command("STOP")
    # We don't know the exact status immediately, client JS should poll /api/bot_status
    return jsonify({"status": "STOP command issued"}), 200

@app.route('/api/bot_status', methods=['GET'])
def bot_status():
    """Reads the status file written by the bot process."""
    status = read_status()
    app.logger.debug(f"Reporting bot status as: {status}")
    return jsonify({"status": status}), 200

# --- Serve the Charts Page ---
@app.route('/traidng_view')
async def charts_page():
    """Renders the main charts page."""
    db = await get_db()
    try:
        # Fetch all unique tokens for the dropdown menu
        tokens = await db.get_all_unique_mints_with_names()
        # Sort tokens alphabetically by name for the dropdown
        tokens_sorted = sorted(tokens, key=lambda x: x.get('name', '').lower())
    except Exception as e:
        print(f"Error fetching token list for charts page: {e}") # Use print or app logger
        tokens_sorted = []
    return render_template('traidng_view.html', tokens=tokens_sorted)
# --------------------------------------
# --- NEW ROUTE: API Endpoint for Chart Data ---
@app.route('/api/traidng_view/<string:mint>')
async def get_chart_data(mint):
    """Provides trade history and portfolio data for a specific token."""
    db = await get_db()
    # Define the time window (e.g., last 24 hours)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - pd.Timedelta(days=1) # Example: Last 1 day
    
    try:
        # 1. Fetch OHLCV data using the backtesting data function
        ohlcv_data_dict = await db.get_historical_data_for_backtesting(
            mints=[mint],
            start_date=start_date,
            end_date=end_date
        )

        if not ohlcv_data_dict or mint not in ohlcv_data_dict:
            return jsonify({"error": "No OHLCV data found for this token in the time range."}), 404

        ohlcv_df = ohlcv_data_dict[mint]

        # Convert DataFrame to list of dictionaries suitable for Lightweight Charts
        # Ensure timestamp is in seconds (epoch time)
        ohlcv_formatted = []
        for timestamp, row in ohlcv_df.iterrows():
             ohlcv_formatted.append({
                 "time": int(timestamp.timestamp()), # Epoch time in seconds
                 "open": row.get('Open'),
                 "high": row.get('High'),
                 "low": row.get('Low'),
                 "close": row.get('Close'),
                 "value": row.get('Volume'), # For Volume series
                 "color": 'rgba(255, 82, 82, 0.5)' if row.get('Close', 0) < row.get('Open', 0) else 'rgba(0, 150, 136, 0.5)' # Volume bar color
             })


        # 2. Fetch portfolio transactions (buy/sell markers)
        portfolio_data = await db.get_portfolio_transactions(mints=[mint])
        portfolio_markers = []
        if mint in portfolio_data:
            for buy in portfolio_data[mint].get('buys', []):
                portfolio_markers.append({
                    "time": int(buy['timestamp'].timestamp()),
                    "position": 'belowBar',
                    "color": 'green',
                    "shape": 'arrowUp',
                    "text": f'Buy @ {buy["price"]:.6f}'
                })
            for sell in portfolio_data[mint].get('sells', []):
                portfolio_markers.append({
                    "time": int(sell['timestamp'].timestamp()),
                    "position": 'aboveBar',
                    "color": 'red',
                    "shape": 'arrowDown',
                    "text": f'Sell @ {sell["price"]:.6f}'
                })

        # Combine data
        chart_data = {
            "ohlcv": ohlcv_formatted,
            "markers": portfolio_markers
        }
        return jsonify(chart_data)

    except Exception as e:
        print(f"Error fetching chart data for mint {mint}: {e}") # Use print or app logger
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return jsonify({"error": "Failed to fetch chart data."}), 500
    
if __name__ == '__main__':
    # Port can be changed here or via environment variable if needed
    # Keeping port 89 as manually set by the user previously.
    port = int(os.environ.get("FLASK_PORT", 89))
    # Use Flask's logger for Flask-specific messages
    app.logger.info(f"Starting Flask development server on http://127.0.0.1:{port}...")
    app.run(debug=True, port=port)
```

---

## 📂 web_app\static\css

---

### 📄 dashboard.css

```css
/* Dashboard Sidebar Styles */
:root {
  --sidebar-width: 250px;
  --sidebar-collapsed-width: 70px;
  --primary-color: #0d6efd;
  --secondary-color: #6c757d;
  --dark-bg: #212529;
  --light-bg: #f8f9fa;
  --transition-speed: 0.3s;
}

body {
  overflow-x: hidden;
  padding-top: 0;
}

.dashboard-container {
  display: flex;
  min-height: 100vh;
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background-color: var(--dark-bg);
  color: white;
  transition: width var(--transition-speed);
  position: fixed;
  height: 100vh;
  z-index: 1000;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar-header {
  padding: 1.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.25rem;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar-toggle {
  background: transparent;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 1.25rem;
}

.sidebar-menu {
  padding: 1rem 0;
  list-style: none;
  margin: 0;
}

.sidebar-menu li {
  margin-bottom: 0.5rem;
}

.sidebar-menu a {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition: all var(--transition-speed);
  white-space: nowrap;
}

.sidebar-menu a:hover,
.sidebar-menu a.active {
  color: white;
  background-color: rgba(255, 255, 255, 0.1);
}

.sidebar-menu .icon {
  margin-right: 1rem;
  font-size: 1.25rem;
  min-width: 1.5rem;
  text-align: center;
}

.sidebar-menu .menu-text {
  overflow: hidden;
}

.sidebar.collapsed .menu-text,
.sidebar.collapsed .sidebar-header h3 {
  display: none;
}

.sidebar.collapsed .sidebar-menu a {
  justify-content: center;
  padding: 0.75rem 0;
}

.sidebar.collapsed .sidebar-menu .icon {
  margin-right: 0;
  font-size: 1.5rem;
}

/* Main Content */
.main-content {
  flex: 1;
  margin-left: var(--sidebar-width);
  transition: margin-left var(--transition-speed);
  width: calc(100% - var(--sidebar-width));
  padding: 1rem;
}

.main-content.expanded {
  margin-left: var(--sidebar-collapsed-width);
  width: calc(100% - var(--sidebar-collapsed-width));
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .sidebar {
    width: var(--sidebar-collapsed-width);
  }
  
  .sidebar .menu-text,
  .sidebar .sidebar-header h3 {
    display: none;
  }
  
  .sidebar .sidebar-menu a {
    justify-content: center;
    padding: 0.75rem 0;
  }
  
  .sidebar .sidebar-menu .icon {
    margin-right: 0;
    font-size: 1.5rem;
  }
  
  .main-content {
    margin-left: var(--sidebar-collapsed-width);
    width: calc(100% - var(--sidebar-collapsed-width));
  }
  
  .sidebar.expanded {
    width: var(--sidebar-width);
    position: absolute;
  }
  
  .sidebar.expanded .menu-text,
  .sidebar.expanded .sidebar-header h3 {
    display: block;
  }
  
  .sidebar.expanded .sidebar-menu a {
    justify-content: flex-start;
    padding: 0.75rem 1rem;
  }
  
  .sidebar.expanded .sidebar-menu .icon {
    margin-right: 1rem;
    font-size: 1.25rem;
  }
}
```

---

## 📂 web_app\static\js

---

### 📄 chart.js

```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Filter elements
    const applyFiltersBtn = document.getElementById('apply-filters-btn');
    const maxSocialsInput = document.getElementById('filter-max-socials');
    const maxRugcheckInput = document.getElementById('filter-max-rugcheck');
    const minVolumeInput = document.getElementById('filter-min-volume');
    const timeWindowSelect = document.getElementById('filter-time-window');
    const portfolioOnlyCheckbox = document.getElementById('filter-portfolio-only'); // Added

    // Chart elements
    const generateChartBtn = document.getElementById('generate-chart-btn');
    const tokenListContainer = document.getElementById('token-list-container'); // Changed from mints-select
    const chartDiv = document.getElementById('chart-div');
    const statusMessage = document.getElementById('status-message');

    // --- Filter Logic ---

    async function fetchAndPopulateTokens() {
        const maxSocials = maxSocialsInput.value;
        const maxRugcheck = maxRugcheckInput.value;
        const minVolume = minVolumeInput.value;
        const timeWindow = timeWindowSelect.value;
        const portfolioOnly = portfolioOnlyCheckbox.checked; // Added: Get checkbox state

        // Construct query parameters
        const queryParams = new URLSearchParams({
            max_socials: maxSocials,
            max_rugcheck: maxRugcheck,
            min_volume: minVolume,
            time_window: timeWindow,
            portfolio_only: portfolioOnly // Added: Include portfolio_only flag
        });

        statusMessage.textContent = 'Loading tokens based on filters...';
        tokenListContainer.innerHTML = '<div class="list-group-item">Loading...</div>'; // Clear and show loading

        try {
            const response = await fetch(`/api/filtered_tokens?${queryParams}`);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const tokens = await response.json();

            tokenListContainer.innerHTML = ''; // Clear loading/previous options

            if (tokens.length === 0) {
                tokenListContainer.innerHTML = '<div class="list-group-item">No tokens match the current filters.</div>';
                statusMessage.textContent = 'No tokens match the current filters.';
            } else {
                tokens.forEach(token => {
                    const listItem = document.createElement('label'); // Use label for better checkbox click handling
                    listItem.className = 'list-group-item d-flex justify-content-between align-items-center';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.className = 'form-check-input me-2';
                    checkbox.value = token.mint;
                    checkbox.setAttribute('data-token-name', token.name); // Store name for chart legend

                    const textContainer = document.createElement('div');
                    textContainer.style.flexGrow = '1'; // Allow text to take available space

                    const nameSpan = document.createElement('span');
                    nameSpan.textContent = `${token.name} `;
                    nameSpan.style.fontWeight = 'bold';

                    const detailsSpan = document.createElement('small');
                    const rugcheckScore = token.rugcheck !== null ? token.rugcheck : 'N/A';
                    const socialsScore = token.socials !== null ? token.socials : 'N/A';
                    detailsSpan.textContent = `(Socials: ${socialsScore}, Rug: ${rugcheckScore}, Vol: ${token.volume}) `;
                    detailsSpan.className = 'text-muted me-2';

                    const mintSpan = document.createElement('span');
                    mintSpan.textContent = token.mint;
                    mintSpan.className = 'badge bg-secondary copy-mint'; // Style as badge, add class for copy
                    mintSpan.style.cursor = 'pointer';
                    mintSpan.title = 'Click to copy mint address';
                    mintSpan.setAttribute('data-mint', token.mint); // Store mint in data attribute

                    // Add click listener for copying
                    mintSpan.addEventListener('click', (e) => {
                        e.preventDefault(); // Prevent label from toggling checkbox
                        e.stopPropagation(); // Prevent label from toggling checkbox
                        copyToClipboard(token.mint, mintSpan);
                    });

                    textContainer.appendChild(checkbox);
                    textContainer.appendChild(nameSpan);
                    textContainer.appendChild(detailsSpan);
                    textContainer.appendChild(mintSpan);

                    listItem.appendChild(textContainer);
                    tokenListContainer.appendChild(listItem);
                });
                statusMessage.textContent = `Loaded ${tokens.length} tokens. Check tokens and click 'Generate Chart'.`; // Updated status
            }

        } catch (error) {
            console.error('Error fetching filtered tokens:', error);
            tokenListContainer.innerHTML = '<div class="list-group-item">Error loading tokens.</div>';
            statusMessage.textContent = `Error loading tokens: ${error.message}`;
        }
    }

    // Event listener for the Apply Filters button
    applyFiltersBtn.addEventListener('click', fetchAndPopulateTokens);

    // Initial load of tokens when the page loads (using default filter values)
    fetchAndPopulateTokens();

    // --- Clipboard Copy Function ---
    async function copyToClipboard(text, element) {
        try {
            await navigator.clipboard.writeText(text);
            const originalText = element.textContent;
            element.textContent = 'Copied!';
            element.classList.remove('bg-secondary');
            element.classList.add('bg-success');
            setTimeout(() => {
                element.textContent = originalText;
                element.classList.remove('bg-success');
                element.classList.add('bg-secondary');
            }, 1500); // Revert after 1.5 seconds
        } catch (err) {
            console.error('Failed to copy: ', err);
            const originalText = element.textContent;
            element.textContent = 'Error!';
             element.classList.remove('bg-secondary');
            element.classList.add('bg-danger');
             setTimeout(() => {
                element.textContent = originalText;
                element.classList.remove('bg-danger');
                element.classList.add('bg-secondary');
            }, 1500);
        }
    }

    // --- Chart Generation Logic ---

    generateChartBtn.addEventListener('click', async () => {
        // Get selected mints from checked checkboxes
        const selectedCheckboxes = tokenListContainer.querySelectorAll('input[type="checkbox"]:checked');
        const mintsArray = Array.from(selectedCheckboxes).map(checkbox => checkbox.value);

        if (mintsArray.length === 0) {
            statusMessage.textContent = 'Please check at least one token from the list.';
            Plotly.purge(chartDiv); // Clear previous chart
            return;
        }

        statusMessage.textContent = 'Loading chart data...';
        Plotly.purge(chartDiv); // Clear previous chart while loading

        try {
            const response = await fetch('/api/token_chart_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mints: mintsArray }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Failed to parse error response' }));
                throw new Error(`HTTP error! Status: ${response.status} - ${errorData.error || 'Unknown error'}`);
            }

            const chartData = await response.json();

            if (Object.keys(chartData).length === 0) {
                statusMessage.textContent = 'No chart data (trades or portfolio) found for the selected mint(s).';
                return;
            }

            const dataTraces = [];
            let hasDataToPlot = false; // Flag to check if there's anything to plot

            for (const mint in chartData) {
                if (chartData.hasOwnProperty(mint)) {
                    const mintData = chartData[mint];
                    const timeData = mintData.time || [];
                    const priceData = mintData.price_usd || [];
                    const buys = mintData.buys || [];
                    const sells = mintData.sells || [];

                    // Find the corresponding checkbox to get the token name stored in data attribute
                    const selectedCheckbox = Array.from(selectedCheckboxes).find(cb => cb.value === mint);
                    let traceName = mint; // Fallback to mint
                    if (selectedCheckbox) {
                        traceName = selectedCheckbox.getAttribute('data-token-name') || mint;
                    }


                    // Add main price line trace if data exists
                    if (timeData.length > 0 && priceData.length > 0) {
                        dataTraces.push({
                            x: timeData,
                            y: priceData,
                            mode: 'lines',
                            name: traceName // Use extracted name for legend
                        });
                        hasDataToPlot = true;
                    } else {
                         console.warn(`No main price line data for mint: ${mint}`);
                    }

                    // Add Buy Markers Trace
                    if (buys.length > 0) {
                        dataTraces.push({
                            x: buys.map(b => b.time),
                            y: buys.map(b => b.price_usd),
                            mode: 'markers',
                            type: 'scatter',
                            name: `${traceName} - Buys`,
                            marker: {
                                color: 'green',
                                symbol: 'triangle-up',
                                size: 10
                            }
                        });
                        hasDataToPlot = true;
                    }

                    // Add Sell Markers Trace
                    if (sells.length > 0) {
                        dataTraces.push({
                            x: sells.map(s => s.time),
                            y: sells.map(s => s.price_usd),
                            mode: 'markers',
                            type: 'scatter',
                            name: `${traceName} - Sells`,
                            marker: {
                                color: 'red',
                                symbol: 'triangle-down',
                                size: 10
                            }
                        });
                        hasDataToPlot = true;
                    }
                }
            }

            if (!hasDataToPlot) {
                 statusMessage.textContent = 'No chart data (trades or portfolio markers) found for the selected mint(s).';
                 return; // Exit if nothing was added to dataTraces
            }

            const layout = {
                title: 'Token Price vs. Elapsed Time (with Portfolio Buys/Sells)', // Updated title
                xaxis: {
                    title: 'Elapsed Time (minutes since first trade)' // Clarified x-axis
                },
                yaxis: {
                    title: 'Price (USD)',
                    // type: 'log', // Uncomment for log scale if needed
                    autorange: true // Ensure y-axis adjusts automatically
                },
                hovermode: 'closest',
                legend: { // Adjust legend position if needed
                    // yanchor: "top",
                    // y: 0.99,
                    // xanchor: "left",
                    // x: 0.01
                }
            };

            Plotly.newPlot(chartDiv, dataTraces, layout);
            statusMessage.textContent = 'Chart generated successfully.'; // Update status on success

        } catch (error) {
            console.error('Error fetching or plotting chart data:', error);
            statusMessage.textContent = `Error generating chart: ${error.message}`;
            Plotly.purge(chartDiv); // Clear chart on error
        }
    });
});
```

---

### 📄 dashboard.js

```javascript
// Removed redundant log fetching logic. It's now handled in base.html
document.addEventListener('DOMContentLoaded', () => {
    // Get sidebar elements
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const mainContent = document.querySelector('.main-content');
    
    // Function to toggle sidebar
    function toggleSidebar() {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
        
        // Store the sidebar state in localStorage
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }
    
    // Add click event to sidebar toggle button
    sidebarToggle.addEventListener('click', toggleSidebar);
    
    // Check localStorage for saved sidebar state
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true') {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('expanded');
    }
    
    // Handle active menu items
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.sidebar-menu a');
    
    menuItems.forEach(item => {
        // Get the path from the href attribute
        const itemPath = item.getAttribute('href');
        
        // Check if the current path matches the menu item path
        // or if we're at root and this is the charts link
        if (itemPath === currentPath || 
            (currentPath === '/' && itemPath === '/charts')) {
            item.classList.add('active');
        }
    });
    
    // For mobile: close sidebar when clicking outside on small screens
    if (window.innerWidth <= 768) {
        document.addEventListener('click', (e) => {
            // If click is outside sidebar and sidebar is expanded
            if (!sidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target) && 
                sidebar.classList.contains('expanded')) {
                sidebar.classList.remove('expanded');
            }
        });
        
        // Toggle expanded class for mobile view
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('expanded');
        });
        
        // Add token filtering functionality
        document.addEventListener('DOMContentLoaded', () => {
            const applyFiltersBtn = document.getElementById('apply-filters-btn');
            const tokenListContainer = document.getElementById('token-list-container');
        
            applyFiltersBtn.addEventListener('click', async () => {
                const maxSocials = document.getElementById('filter-max-socials').value;
                const maxRugcheck = document.getElementById('filter-max-rugcheck').value;
                const minVolume = document.getElementById('filter-min-volume').value;
                const timeWindow = document.getElementById('filter-time-window').value;
                const portfolioOnly = document.getElementById('filter-portfolio-only').checked;
                const volumeAggregation = document.getElementById('filter-volume-aggregation').value;
        
                const params = new URLSearchParams({
                    max_socials: maxSocials,
                    max_rugcheck: maxRugcheck,
                    min_volume: minVolume,
                    time_window: timeWindow,
                    portfolio_only: portfolioOnly,
                    volume_aggregation: volumeAggregation
                }).toString();
        
                try {
                    const response = await fetch(`/api/filtered_tokens?${params}`);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const tokens = await response.json();
        
                    // Clear existing token list
                    tokenListContainer.innerHTML = '';
        
                    if (tokens.length === 0) {
                        tokenListContainer.innerHTML = '<div class="list-group-item">No tokens found with the selected filters.</div>';
                    } else {
                        tokens.forEach(token => {
                            const listItem = document.createElement('div');
                            listItem.classList.add('list-group-item');
                            listItem.textContent = `${token.name} (${token.symbol}) - ${token.mint} - Volume: ${token.volume}`;
                            listItem.addEventListener('click', () => {
                                navigator.clipboard.writeText(token.mint).then(() => {
                                    alert('Mint copied to clipboard!');
                                });
                            });
                            tokenListContainer.appendChild(listItem);
                        });
                    }
                } catch (error) {
                    console.error('Failed to fetch filtered tokens:', error);
                    tokenListContainer.innerHTML = '<div class="list-group-item">Failed to load tokens. Please check the console for errors.</div>';
                }
            });
        });
    }

    // --- Bot Control Logic ---
    const startButton = document.getElementById('start-bot-btn');
    const stopButton = document.getElementById('stop-bot-btn');
    let statusCheckInterval; // Variable to hold the interval ID

    // Function to update button visibility based on status
    function updateButtonStates(status) {
        console.log("Updating button states based on status:", status);
        switch (status) {
            case "RUNNING":
                startButton.style.display = 'none';
                stopButton.style.display = 'inline-block';
                startButton.disabled = true; // Disable start when running
                stopButton.disabled = false; // Enable stop when running
                break;
            case "STARTING":
                startButton.style.display = 'inline-block'; // Show start but disable
                stopButton.style.display = 'none';
                startButton.disabled = true;
                stopButton.disabled = true; // Disable stop while starting
                // Optionally update button text: startButton.textContent = 'Starting...';
                break;
            case "STOPPING":
                startButton.style.display = 'none';
                stopButton.style.display = 'inline-block'; // Show stop but disable
                startButton.disabled = true; // Disable start while stopping
                stopButton.disabled = true;
                // Optionally update button text: stopButton.textContent = 'Stopping...';
                break;
            case "STOPPED":
            case "ERROR": // Treat ERROR as STOPPED for button state
            default: // Default to stopped state
                startButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                startButton.disabled = false; // Enable start when stopped
                stopButton.disabled = true; // Disable stop when stopped
                // Reset button text if changed: startButton.textContent = 'Start Bot';
                break;
        }
    }

    // Function to fetch bot status
    async function checkBotStatus() {
        try {
            const response = await fetch('/api/bot_status');
            if (!response.ok) {
                console.error('Error fetching bot status:', response.statusText);
                updateButtonStates("ERROR"); // Assume error means stopped for UI
                return;
            }
            const data = await response.json();
            updateButtonStates(data.status);
        } catch (error) {
            console.error('Network error fetching bot status:', error);
            updateButtonStates("ERROR"); // Assume error means stopped for UI
        }
    }

    if (startButton && stopButton) {
        // Event listener for Start Button
        startButton.addEventListener('click', async () => {
            console.log('Start Bot button clicked - sending command');
            updateButtonStates("STARTING"); // Immediately reflect intent

            try {
                const response = await fetch('/start_bot', { method: 'POST' });
                const result = await response.json();
                console.log('Start Bot command response:', result);
                // No need to update buttons here, periodic check will handle it
                if (!response.ok) {
                    console.error("Start command failed:", result);
                    checkBotStatus(); // Re-check status immediately on failure
                }
            } catch (error) {
                console.error('Error sending start command:', error);
                checkBotStatus(); // Re-check status immediately on failure
            }
        });

        // Event listener for Stop Button
        stopButton.addEventListener('click', async () => {
            console.log('Stop Bot button clicked - sending command');
            updateButtonStates("STOPPING"); // Immediately reflect intent

            try {
                const response = await fetch('/stop_bot', { method: 'POST' });
                const result = await response.json();
                console.log('Stop Bot command response:', result);
                // No need to update buttons here, periodic check will handle it
                 if (!response.ok) {
                    console.error("Stop command failed:", result);
                    checkBotStatus(); // Re-check status immediately on failure
                }
            } catch (error) {
                console.error('Error sending stop command:', error);
                 checkBotStatus(); // Re-check status immediately on failure
            }
        });

        // Initial status check on page load
        checkBotStatus();

        // Periodically check status
        statusCheckInterval = setInterval(checkBotStatus, 5000); // Check every 5 seconds

    } else {
        console.warn('Start or Stop button not found in the DOM.');
    }
    // --- End Bot Control Logic ---

});
```

---

## 📂 web_app\templates

---

### 📄 analytics.html

```html
<!-- index.html -->
{% extends 'base.html' %}

{% block title %}Token Charts - Pump Trader{% endblock %}

{% block content %}
        <!-- Main Content -->
        <div class="main-content">
            <h1 class="mb-4">Analytics</h1>

            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            Market Analytics
                        </div>
                        <div class="card-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                This page is under development. Advanced analytics features will be available soon.
                            </div>
                            
                            <div class="row mt-4">
                                <div class="col-md-4">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">Total Tokens Tracked</h5>
                                            <h2 class="text-primary">{ total_tracked_tokens }</h2>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">24h Trading Volume</h5>
                                            <h2 class="text-primary">0.00 SOL</h2>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">Avg. Rugcheck Score</h5>
                                            <h2 class="text-primary">0.00</h2>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <h5 class="mt-4">Coming Soon:</h5>
                            <ul>
                                <li>Market trend analysis</li>
                                <li>Token performance comparisons</li>
                                <li>Volume and liquidity metrics</li>
                                <li>Social sentiment analysis</li>
                                <li>Historical data visualization</li>
                                <li>Predictive analytics</li>
                            </ul>
                            
                            <div class="mt-4">
                                <h5>Placeholder Chart</h5>
                                <div style="width: 100%; height: 300px; background-color: #f8f9fa; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center;">
                                    <p class="text-muted">Analytics charts will appear here</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div> <!-- /main-content -->
{% endblock %}
```

---

### 📄 base.html

```html
<!-- base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Token Price Analysis Dashboard{% endblock %}</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Include Plotly.js from CDN -->
    <script src='https://cdn.plot.ly/plotly-latest.min.js'></script>
    <!-- Custom Dashboard CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
    <style>
        /* Additional custom styles */
        .card {
            margin-bottom: 1.5rem;
        }
        #chart-div {
             width: 100%; /* Make chart responsive */
             height: 500px; /* Adjust height as needed */
             min-height: 400px; /* Ensure minimum height */
        }
        /* Footer styles */
        .log-footer {
            position: fixed;
            bottom: 0;
            left: 0; /* Adjust if sidebar width is fixed */
            width: 100%; /* Adjust if sidebar width is fixed */
            height: 150px; /* Adjust height as needed */
            background-color: #212529; /* Dark background */
            border-top: 1px solid #495057; /* Darker border */
            padding: 10px 20px; /* Add padding */
            z-index: 1000; /* Ensure it's above other content */
            overflow-y: scroll; /* Add scroll for overflow */
            font-family: monospace; /* Use monospace font for logs */
            font-size: 0.8em; /* Smaller font size */
            color: #f8f9fa; /* Light text color */
        }
        .log-footer pre {
            margin: 0;
            white-space: pre-wrap; /* Wrap long lines */
            word-wrap: break-word; /* Break words if necessary */
            color: #f8f9fa; /* Ensure pre text is also light */
        }
        /* Adjust main content padding to prevent overlap with footer */
        .main-content {
             padding-bottom: 170px; /* Footer height + some buffer */
        }
        #mints-select {
            min-height: 150px; /* Make select box taller */
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <!-- Sidebar -->
        {% include 'partials/sidebar.html' %}

        <!-- Main Content -->
        <div class="main-content">
            {% block content %}{% endblock %}
        </div>
        </div>
    </div>

    <!-- Log Footer -->
    <footer class="log-footer">
        <h6>Trading Bot Logs</h6>
        <pre id="log-output">Initializing log display...</pre>
    </footer>

    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
    <!-- Include custom JavaScript files -->
    <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
    <script src="{{ url_for('static', filename='js/chart.js') }}"></script>

    <!-- Log Fetching Script -->
    <script>
        const logOutput = document.getElementById('log-output');
        const MAX_LOG_ELEMENTS = 500; // Max number of log lines to keep in the display
        let isFetchingLogs = false; // Flag to prevent concurrent fetches

        async function fetchLogs() {
            if (isFetchingLogs) {
                // console.log("Log fetch already in progress, skipping.");
                return;
            }
            isFetchingLogs = true;
            // console.log("Fetching logs...");
            try {
                const response = await fetch('/logs'); // Use the /logs endpoint
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const logs = await response.json();
                if (logs && Array.isArray(logs) && logs.length > 0) {
                    // Trim old logs if exceeding limit BEFORE adding new ones
                    while (logOutput.childNodes.length >= MAX_LOG_ELEMENTS) {
                        logOutput.removeChild(logOutput.firstChild);
                    }

                    // Append new logs
                    logs.forEach(log => {
                        // Create a text node for each log line to prevent potential HTML injection
                        const logEntry = document.createTextNode(log + '\n'); // Add newline
                        logOutput.appendChild(logEntry);
                    });

                    // Auto-scroll to the bottom
                    // Auto-scroll to the bottom
                    logOutput.scrollTop = logOutput.scrollHeight;
                } else {
                    // console.log("No new logs received.");
                }
            } catch (error) {
                console.error("Error fetching logs:", error);
                // Optionally display an error message in the footer
                // logOutput.textContent += "\nError fetching logs. Check console.";
            } finally {
                 isFetchingLogs = false; // Reset flag
            }
        }

        // Initial fetch and set interval
        fetchLogs(); // Fetch immediately on load
        setInterval(fetchLogs, 3000); // Fetch every 3 seconds

        // Optional: Clear logs button or mechanism could be added here
    </script>
</body>
</html>
```

---

### 📄 configuration.html

```html
<!-- configuration.html -->
{% extends 'base.html' %}

{% block title %}Token Charts - Pump Trader{% endblock %}

{% block content %}
<h1 class="mb-4">Configuration</h1>

<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                System Settings
            </div>
            <div class="card-body">
                <form id="config-form">
                    <div class="mb-3">
                        <label for="sol-price-api" class="form-label">SOL Price API URL</label>
                        <input type="text" class="form-control" id="sol-price-api" placeholder="https://api.example.com/sol-price">
                        <div class="form-text">API endpoint for fetching SOL price data</div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="max-file-age" class="form-label">Max File Age (seconds)</label>
                        <input type="number" class="form-control" id="max-file-age" min="60" value="3600">
                        <div class="form-text">Maximum age of cached price data before refreshing</div>
                    </div>
                    
                    <h5 class="mt-4">Trading Parameters</h5>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="min-volume-threshold" class="form-label">Minimum Volume Threshold (SOL)</label>
                                <input type="number" class="form-control" id="min-volume-threshold" min="0" step="0.01" value="1.0">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="max-rugcheck-score" class="form-label">Maximum Rugcheck Score</label>
                                <input type="number" class="form-control" id="max-rugcheck-score" min="0" max="10000" value="5000">
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="enable-auto-trading">
                        <label class="form-check-label" for="enable-auto-trading">Enable Automated Trading</label>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Save Configuration</button>
                    <button type="button" class="btn btn-secondary ms-2">Reset to Defaults</button>
                </form>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                Notification Settings
            </div>
            <div class="card-body">
                <form id="notification-form">
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="enable-email-alerts" checked>
                        <label class="form-check-label" for="enable-email-alerts">Enable Email Alerts</label>
                    </div>
                    
                    <div class="mb-3">
                        <label for="email-address" class="form-label">Email Address</label>
                        <input type="email" class="form-control" id="email-address" placeholder="your@email.com">
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="enable-sound-alerts" checked>
                        <label class="form-check-label" for="enable-sound-alerts">Enable Sound Alerts</label>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Save Notification Settings</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 📄 index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Token Price Analysis Dashboard</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Include Plotly.js from CDN -->
    <script src='https://cdn.plot.ly/plotly-latest.min.js'></script>
    <!-- Custom Dashboard CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
    <style>
        /* Additional custom styles */
        .card {
            margin-bottom: 1.5rem;
        }
        #chart-div {
             width: 100%; /* Make chart responsive */
             height: 500px; /* Adjust height as needed */
             min-height: 400px; /* Ensure minimum height */
        }
        #mints-select {
            min-height: 150px; /* Make select box taller */
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>Pump Trader</h3>
                <button class="sidebar-toggle">
                    <i class="fas fa-bars"></i>
                </button>
            </div>
            <ul class="sidebar-menu">
                <li>
                    <a href="/" class="active">
                        <span class="icon"><i class="fas fa-chart-line"></i></span>
                        <span class="menu-text">Token Charts</span>
                    </a>
                </li>
                <li>
                    <a href="/config">
                        <span class="icon"><i class="fas fa-cog"></i></span>
                        <span class="menu-text">Configuration</span>
                    </a>
                </li>
                <li>
                    <a href="/portfolio">
                        <span class="icon"><i class="fas fa-wallet"></i></span>
                        <span class="menu-text">Portfolio</span>
                    </a>
                </li>
                <li>
                    <a href="/analytics">
                        <span class="icon"><i class="fas fa-chart-bar"></i></span>
                        <span class="menu-text">Analytics</span>
                    </a>
                </li>
            </ul>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <h1 class="mb-4">Token Price Analysis</h1>

            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            Filters
                        </div>
                        <div class="card-body">
                            <div class="row g-3 align-items-end">
                                <div class="col-md-auto">
                                    <label for="filter-max-socials" class="form-label">Max Socials (0-100):</label>
                                    <input type="number" class="form-control form-control-sm" id="filter-max-socials" value="100" min="0" max="100" style="width: 100px;">
                                </div>
                                <div class="col-md-auto">
                                    <label for="filter-max-rugcheck" class="form-label">Max Rugcheck (0-10000):</label>
                                    <input type="number" class="form-control form-control-sm" id="filter-max-rugcheck" value="10000" min="0" max="10000" style="width: 120px;">
                                </div>
                                <div class="col-md-auto">
                                    <label for="filter-min-volume" class="form-label">Min Volume (SOL):</label>
                                    <input type="number" class="form-control form-control-sm" id="filter-min-volume" value="0" min="0" step="0.01" style="width: 100px;">
                                </div>
                                <div class="col-md-auto">
                                    <label for="filter-time-window" class="form-label">Volume Time Window:</label>
                                    <select class="form-select form-select-sm" id="filter-time-window" style="width: 150px;">
                                        <option value="60" selected>Last 1 Hour</option>
                                        <option value="360">Last 6 Hours</option>
                                        <option value="1440">Last 24 Hours</option>
                                        <option value="10080">Last 7 Days</option>
                                    </select>
                                </div>
                                <div class="col-md-auto">
                                   <label for="filter-volume-aggregation" class="form-label">Volume Aggregation:</label>
                                   <select class="form-select form-select-sm" id="filter-volume-aggregation" style="width: 150px;">
                                       <option value="avg" selected>Average</option>
                                       <option value="max">Maximum</option>
                                       <option value="actual">Actual</option>
                                   </select>
                                </div>
                                <div class="col-md-auto">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="filter-portfolio-only">
                                        <label class="form-check-label" for="filter-portfolio-only">
                                            Portfolio Only
                                        </label>
                                    </div>
                                </div>
                                <div class="col-md-auto">
                                    <button id="apply-filters-btn" class="btn btn-secondary btn-sm">Apply Filters</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            Select Tokens (Click Mint to Copy)
                        </div>
                        <div class="card-body">
                            <div id="token-list-container" class="list-group" style="max-height: 300px; overflow-y: auto; margin-bottom: 1rem;">
                                <!-- Token list will be populated by JavaScript -->
                                <div class="list-group-item">Apply filters to load tokens...</div>
                            </div>
                            <button id="generate-chart-btn" class="btn btn-primary mt-3">Generate Chart</button>
                        </div>
                    </div>
                    <div id="status-message" class="mt-3 text-muted"></div>
                </div>
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">
                            Price Chart
                        </div>
                        <div class="card-body">
                            <div id="chart-div"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div> <!-- /main-content -->
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        Bot Control
                    </div>
                    <div class="card-body">
                        <button id="start-bot-btn" class="btn btn-success">Start Bot</button>
                        <button id="stop-bot-btn" class="btn btn-danger" style="display: none;">Stop Bot</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        Logs
                    </div>
                    <div class="card-body">
                        <pre id="logs" style="height: 300px; overflow-y: auto;"></pre>
                    </div>
                </div>
            </div>
        </div>
    </div> <!-- /dashboard-container -->

    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
    <!-- Include custom JavaScript files -->
    <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
    <script src="{{ url_for('static', filename='js/chart.js') }}"></script>
</body>
</html>
```

---

## 📂 web_app\templates\partials

---

### 📄 sidebar.html

```html
<!-- partials/sidebar.html -->
<div class="sidebar">
    <div class="sidebar-header">
        <h3>Pump Trader</h3>
        <button class="sidebar-toggle">
            <i class="fas fa-bars"></i>
        </button>
    </div>
    <ul class="sidebar-menu">
        <li>
            <a href="/" class="active">
                <span class="icon"><i class="fas fa-chart-line"></i></span>
                <span class="menu-text">Token Charts</span>
            </a>
        </li>
        <li>
            <a href="/config">
                <span class="icon"><i class="fas fa-cog"></i></span>
                <span class="menu-text">Configuration</span>
            </a>
        </li>
        <li>
            <a href="/portfolio">
                <span class="icon"><i class="fas fa-wallet"></i></span>
                <span class="menu-text">Portfolio</span>
            </a>
        </li>
        <li>
            <a href="/analytics">
                <span class="icon"><i class="fas fa-chart-bar"></i></span>
                <span class="menu-text">Analytics</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/traidng_view">
                <span class="icon"><i class="fas fa-chart-bar"></i></span>
                <span class="menu-text">TradingView</span>
            </a>            
        </li>
    </ul>
    <div class="sidebar-footer">
        <div class="card">
            <div class="card-header">
                Bot Control
            </div>
            <div class="card-body">
                <button id="start-bot-btn" class="btn btn-success">Start Bot</button>
                <button id="stop-bot-btn" class="btn btn-danger" style="display: none;">Stop Bot</button>
            </div>
        </div>
    </div>
</div>
```

---

## 📂 web_app\templates

---

### 📄 portfolio.html

```html
<!-- index.html -->
{% extends 'base.html' %}

{% block title %}Token Charts - Pump Trader{% endblock %}

{% block content %}
        <!-- Main Content -->
        <div class="main-content">
            <h1 class="mb-4">Portfolio</h1>

            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            Portfolio Overview
                        </div>
                        <div class="card-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                This page is under development. Portfolio management features will be available soon.
                            </div>
                            
                            <div class="row mt-4">
                                <div class="col-md-6">
                                    <div class="card bg-light">
                                        <div class="card-body">
                                            <h5 class="card-title">Total Portfolio Value</h5>
                                            <h2 class="text-primary">$0.00</h2>
                                            <p class="text-muted">0.00 SOL</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card bg-light">
                                        <div class="card-body">
                                            <h5 class="card-title">24h Change</h5>
                                            <h2 class="text-secondary">0.00%</h2>
                                            <p class="text-muted">$0.00</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <h5 class="mt-4">Coming Soon:</h5>
                            <ul>
                                <li>Portfolio tracking and management</li>
                                <li>Performance metrics and analytics</li>
                                <li>Transaction history</li>
                                <li>Profit/loss calculations</li>
                                <li>Portfolio diversification analysis</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div> <!-- /main-content -->
{% endblock %}
```

---

### 📄 token_price_analysis.html

```html
<!-- index.html -->
{% extends 'base.html' %}

{% block title %}Token Charts - Pump Trader{% endblock %}

{% block content %}
<h1 class="mb-4">Token Price Analysis</h1>

<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                Filters
            </div>
            <div class="card-body">
                <div class="row g-3 align-items-end">
                    <div class="col-md-auto">
                        <label for="filter-max-socials" class="form-label">Max Socials (0-100):</label>
                        <input type="number" class="form-control form-control-sm" id="filter-max-socials" value="100" min="0" max="100" style="width: 100px;">
                    </div>
                    <div class="col-md-auto">
                        <label for="filter-max-rugcheck" class="form-label">Max Rugcheck (0-10000):</label>
                        <input type="number" class="form-control form-control-sm" id="filter-max-rugcheck" value="10000" min="0" max="10000" style="width: 120px;">
                    </div>
                    <div class="col-md-auto">
                        <label for="filter-min-volume" class="form-label">Min Volume (SOL):</label>
                        <input type="number" class="form-control form-control-sm" id="filter-min-volume" value="15000" min="0" step="0.01" style="width: 100px;">
                    </div>
                    <div class="col-md-auto">
                        <label for="filter-time-window" class="form-label">Volume Time Window:</label>
                        <select class="form-select form-select-sm" id="filter-time-window" style="width: 150px;">
                            <option value="60" selected>Last 1 Hour</option>
                            <option value="360">Last 6 Hours</option>
                            <option value="1440">Last 24 Hours</option>
                            <option value="10080">Last 7 Days</option>
                        </select>
                    </div>
                    <div class="col-md-auto">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="filter-portfolio-only">
                            <label class="form-check-label" for="filter-portfolio-only">
                                Portfolio Only
                            </label>
                        </div>
                    </div>
                    <div class="col-md-auto">
                        <button id="apply-filters-btn" class="btn btn-secondary btn-sm">Apply Filters</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                Select Tokens (Click Mint to Copy)
            </div>
            <div class="card-body">
                <div id="token-list-container" class="list-group" style="max-height: 300px; overflow-y: auto; margin-bottom: 1rem;">
                    <!-- Token list will be populated by JavaScript -->
                    <div class="list-group-item">Apply filters to load tokens...</div>
                </div>
                <button id="generate-chart-btn" class="btn btn-primary mt-3">Generate Chart</button>
            </div>
        </div>
        <div id="status-message" class="mt-3 text-muted"></div>
    </div>
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                Price Chart
            </div>
            <div class="card-body">
                <div id="chart-div"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 📄 traidng_view.html

```html
{% extends 'base.html' %}

{% block title %}TradingView{% endblock %}

{% block content %}
<div class="container mt-4">
    <h1 class="mb-4">Token Trading Chart</h1>

    <div class="mb-3">
        <label for="tokenSelector" class="form-label">Select Token:</label>
        <select class="form-select" id="tokenSelector">
            <option selected disabled>Choose a token...</option>
            {% for token in tokens %}
            <option value="{{ token.mint }}">{{ token.name }} ({{ token.symbol }})</option>
            {% endfor %}
        </select>
        <label for="mintSearch" class="form-label mt-2">Search by Mint Address:</label>
        <input type="text" class="form-control" id="mintSearch" placeholder="Enter mint address...">
        <div class="col-md-auto">
            <button id="search-mint-btn" class="btn btn-secondary btn-sm">Load</button>
        </div>
    </div>

    <div id="chart-container" style="width: 100%; height: 600px; border: 1px solid #ccc;">
        </div>
     <div id="loading-indicator" style="display: none; text-align: center; padding: 20px;">
        Loading chart data...
    </div>
</div>

<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>

<script>
    const chartContainer = document.getElementById('chart-container');
    const tokenSelector = document.getElementById('tokenSelector');
    const mintSearch = document.getElementById('mintSearch');
    const searchMintBtn = document.getElementById('search-mint-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    let chart = null; // Variable to hold the chart instance
    let candlestickSeries = null;
    let volumeSeries = null;

    function createOrUpdateChart(mint) {
        if (!chartContainer) return;

        loadingIndicator.style.display = 'block'; // Show loading indicator
        chartContainer.style.display = 'none';   // Hide chart container

        // --- Chart Initialization ---
        // If chart exists, remove it before creating a new one
        if (chart) {
            chart.remove();
            chart = null;
        }

        chart = LightweightCharts.createChart(chartContainer, {
            width: chartContainer.clientWidth,
            height: 600, // Or chartContainer.clientHeight if you want it dynamic
            layout: {
                background: { type: 'solid', color: '#ffffff' },
                textColor: '#333',
            },
            grid: {
                vertLines: { color: '#e1e1e1' },
                horzLines: { color: '#e1e1e1' },
            },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            rightPriceScale: { // Main price scale
                borderColor: '#ccc',
            },
            timeScale: {
                borderColor: '#ccc',
                timeVisible: true, // Show time
                secondsVisible: true, // Show seconds if data is fine-grained enough
            },
        });

        // --- Candlestick Series ---
        candlestickSeries = chart.addSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderDownColor: '#ef5350',
            borderUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            wickUpColor: '#26a69a',
        });

         // --- Volume Series ---
         // Create volume series on a separate pane below the price scale
        volumeSeries = chart.addHistogramSeries({
            color: '#26a69a', // Default color, will be overridden by data
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '', // Set to '' to display the series on the price scale instead of the main one
        });
        // Set the pane location for the volume series (index 1 means the pane below the main pane 0)
        chart.priceScale('').applyOptions({
            scaleMargins: {
                top: 0.7, // Price scale margin (70% space for price)
                bottom: 0.1, // Volume scale margin (10% space for volume) - Adjust as needed
            },
        });
         volumeSeries.priceScale().applyOptions({
             scaleMargins: {
                 top: 0.9, // Adjust top margin for volume scale (e.g., 90% space above)
                 bottom: 0,
             }
         });


        // --- Fetch and Load Data ---
        fetch(`/api/trading_view/${mint}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                     console.error("Error fetching chart data:", data.error);
                     loadingIndicator.innerText = `Error loading data for ${mint}: ${data.error}`;
                     chartContainer.style.display = 'none'; // Keep chart hidden on error
                     loadingIndicator.style.display = 'block';
                     return; // Stop processing
                }

                console.log("Received OHLCV data:", data.ohlcv); // Debug log
                console.log("Received Marker data:", data.markers); // Debug log

                if (data.ohlcv && data.ohlcv.length > 0) {
                    // Filter out any entries with null/undefined essential values
                    const cleanOhlcvData = data.ohlcv.filter(d =>
                        d.time !== null && d.time !== undefined &&
                        d.open !== null && d.open !== undefined &&
                        d.high !== null && d.high !== undefined &&
                        d.low !== null && d.low !== undefined &&
                        d.close !== null && d.close !== undefined
                    );
                     const cleanVolumeData = data.ohlcv.filter(d =>
                         d.time !== null && d.time !== undefined &&
                         d.value !== null && d.value !== undefined
                    ).map(d => ({ time: d.time, value: d.value, color: d.color })); // Map to expected volume format


                    if (cleanOhlcvData.length > 0) {
                        candlestickSeries.setData(cleanOhlcvData);
                        volumeSeries.setData(cleanVolumeData); // Set volume data

                         // Add markers if available
                        if (data.markers && data.markers.length > 0) {
                            candlestickSeries.setMarkers(data.markers);
                        }

                        chart.timeScale().fitContent(); // Fit chart to data
                        chartContainer.style.display = 'block'; // Show chart
                        loadingIndicator.style.display = 'none'; // Hide loading
                    } else {
                         loadingIndicator.innerText = `No valid OHLCV data points found for ${mint}.`;
                         chartContainer.style.display = 'none';
                         loadingIndicator.style.display = 'block';
                    }

                } else {
                    loadingIndicator.innerText = `No OHLCV data returned for ${mint}.`;
                    chartContainer.style.display = 'none';
                    loadingIndicator.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Error fetching or processing chart data:', error);
                loadingIndicator.innerText = `Failed to load chart data for ${mint}. Check console for details.`;
                chartContainer.style.display = 'none'; // Keep chart hidden on fetch error
                loadingIndicator.style.display = 'block';
            });

        // Optional: Handle chart resize
        const resizeObserver = new ResizeObserver(entries => {
          if (entries.length > 0) {
            const { width, height } = entries[0].contentRect;
            chart.applyOptions({ width, height });
          }
        });
        resizeObserver.observe(chartContainer);
    }

    // --- Event Listener for Dropdown ---
    tokenSelector.addEventListener('change', function() {
        const selectedMint = this.value;
        if (selectedMint) {
            createOrUpdateChart(selectedMint);
        }
    });

    // Event listener for the Search Mint button
    searchMintBtn.addEventListener('click',  function() {
        const selectedMint = mintSearch.value;
        if (selectedMint) {
            createOrUpdateChart(selectedMint);
        }
    });

    // Optional: Load a default chart on page load?
    // const firstTokenMint = tokenSelector.options[1]?.value; // Get the first actual token
    // if (firstTokenMint) {
    //     createOrUpdateChart(firstTokenMint);
    // }

</script>
{% endblock %}
```

---

