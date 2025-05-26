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
from config import _TOTAL_SUPPLY
import config as base_config_module
from state_manager import GlobalState
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple, Any
from utils import calculate_volatility
import inspect 
from typing import Optional
import statistics 

# Load environment variables from .env file
load_dotenv()

# Construct the database URL from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?options=-c%20timezone%3Dutc"

# --- Helper Function to Convert Module to Dict ---
# (Place this helper function outside the class, near the imports)
def _config_module_to_dict(module) -> dict:
    """Converts public, uppercase attributes of a module into a dictionary."""
    config_dict = {}
    for key in dir(module):
        # Load only uppercase variables that are not modules/classes/functions/private
        if key.isupper() and not key.startswith('_'):
            value = getattr(module, key)
            # Check type to exclude modules etc.
            if not inspect.ismodule(value) and \
               not inspect.isclass(value) and \
               not inspect.isfunction(value):
                config_dict[key] = value
    logger.debug(f"Converted config module to dict: {list(config_dict.keys())}")
    return config_dict

# --- Helper Function to Sanitize Strings ---
def _sanitize_string(value: Any) -> Optional[str]:
    """Removes null bytes from strings and ensures the value is a string or None."""
    if isinstance(value, str):
        return value.replace('\x00', '')
    return None if value is None else str(value) # Convert other types to string, handle None
class DatabaseClient:
    """Client to manage database connections and operations."""
 
    _DEFAULT_CONFIG = _config_module_to_dict(base_config_module)
    
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict
        self.pool = None
        self.state = GlobalState.get_instance()

        # Use the provided config_dict if available, otherwise use the class default
        if config_dict is not None:
            self.config = config_dict
            logger.debug("DatabaseClient initialized with provided config_dict.")
        else:
            # Use a copy of the default to prevent modifications affecting others
            self.config = self._DEFAULT_CONFIG.copy()
            logger.debug("DatabaseClient initialized with default config from config.py.")

        # Ensure self.config is always a dictionary
        if not isinstance(self.config, dict):
             logger.error(f"DatabaseClient self.config is not a dict! Type: {type(self.config)}. Falling back to default.")
             self.config = self._DEFAULT_CONFIG.copy() # Fallback just in case

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
                        _sanitize_string(data.get('name')),
                        _sanitize_string(data.get('symbol')), 
                        _sanitize_string(data.get('uri')),
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

    async def get_tokens_to_unsubscribe(self, mc_drop_threshold, inactivity_period, min_token_age):
        """Fetch tokens to unsubscribe based on market cap drop and inactivity."""
        query = """
            SELECT t.mint
            FROM tokens t
            INNER JOIN (
                SELECT mint, marketCapSol, timestamp,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM trades
            ) latest ON t.mint = latest.mint AND latest.rn = 1
            WHERE 
                (
                    (latest.marketCapSol * 100.0 / t.marketCapSol) < (100 - $1)
                    OR
                    latest.timestamp <= NOW() - (INTERVAL '1 minute' * $2)
                )
                AND t.timestamp <= NOW() - (INTERVAL '1 minute' * $3)
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
            ORDER BY t.timestamp DESC;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, mc_drop_threshold, inactivity_period, min_token_age)

    async def get_active_tokens(self, limit: int = 20000):
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
            return result['total_supply'] if result else _TOTAL_SUPPLY


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
                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') AND
                (t.cooldown_until IS NULL OR t.cooldown_until < NOW())
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
                    marketCapSol, -- This is 'marketcapsol' in your DB schema
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                FROM trades
                WHERE mint = ANY($1::text[])
            )
            SELECT mint, price, marketCapSol FROM LatestTrades WHERE rn = 1
        '''
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, mints)
            results = {}
            for row in rows:
                mint = row['mint']
                price_val = float(row['price']) if row['price'] is not None else None
                market_cap_val = float(row['marketcapsol']) if row['marketcapsol'] is not None else None # Ensure marketcapsol from DB

                # Store market cap if it's valid, regardless of price for now
                # Store price only if it's valid and positive
                current_data = {'price': None, 'market_cap': None}

                if market_cap_val is not None and market_cap_val > 0: # Require positive MC
                    current_data['market_cap'] = market_cap_val
                
                if price_val is not None and price_val > 0:
                    current_data['price'] = price_val
                
                # Only add to results if we have at least a valid market_cap or a valid price
                if current_data['market_cap'] is not None or current_data['price'] is not None:
                    results[mint] = current_data
                else:
                    logger.warning(f"For mint {mint}, latest trade had invalid price ({row['price']}) AND invalid marketcap ({row['marketcapsol']}). Not returning data.")
            return results
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

    async def get_last_trade_timestamp(self, mint: str) -> Optional[datetime]:
        """Get the timestamp of the last trade for a given mint."""
        query = "SELECT timestamp FROM trades WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, mint)
            return row['timestamp'] if row else None

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

    async def backup_and_delete_token(self, mint: str, archived_at: datetime, reason: str=None):
        """Backup core table data to a corresponding backup table."""
        final_reason = reason # Initialize final_reason with the provided reason
 
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                                    INSERT INTO tokens_backup (
                                        mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
                                        vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
                                        socials_score, socials_last_checked, sol_price_usd, is_active, last_trade, timestamp,
                                        cooldown_until,
                                        backup_reason, backup_timestamp
                                    )
                                    SELECT
                                        mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
                                        vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
                                        socials_score, socials_last_checked, sol_price_usd, is_active, last_trade, timestamp,
                                        cooldown_until,
                                        $1, NOW()
                                    FROM tokens
                                    WHERE mint = $2
                                ''', final_reason, mint)
                        
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
        backup_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "data", 
            "creator_wallets_backup.json"
        ))

        if not os.path.exists(backup_path):
            logger.warning("Backup file not found: %s", backup_path)
            return

        try:
            with open(backup_path, "r") as f:
                data = json.load(f)

            # Convert JSON data into tuples for faster insertion
            records = [
                (
                    record["wallet_address"],
                    record["token_count"],
                    datetime.fromisoformat(record["last_token_time"]) if record.get("last_token_time") else None
                )
                for record in data
            ]

            # Batch size
            BATCH_SIZE = 100

            # Insert using batches
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]
                sql = """
                    INSERT INTO creator_wallets (wallet_address, token_count, last_token_time)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (wallet_address) DO UPDATE SET
                        token_count = GREATEST(creator_wallets.token_count, EXCLUDED.token_count),
                        last_token_time = CASE
                            WHEN EXCLUDED.token_count > creator_wallets.token_count THEN EXCLUDED.last_token_time
                            ELSE creator_wallets.last_token_time
                        END;
                """
                async with self.pool.acquire() as conn:
                    await conn.executemany(sql, batch)

            logger.info("Loaded backup data from %s (%d records)", backup_path, len(records))

        except Exception as e:
            logger.exception("Error loading backup data: %s", e)
            raise

    # --- START: Refactored Price Calculation Logic ---
    async def _get_raw_trades_for_window(self, mint: str, window_minutes: int, conn) -> List[Dict[str, Any]]:
        """Fetches raw trades (timestamp, sol_amount, token_amount) for a given window."""
        query = """
            SELECT timestamp, sol_amount, token_amount
            FROM trades
            WHERE mint = $1
            AND timestamp >= NOW() - ($2 || ' minutes')::interval
            AND token_amount > 0 AND sol_amount > 0 -- Ensure valid amounts for price calculation
            ORDER BY timestamp ASC;
        """
        return await conn.fetch(query, mint, str(window_minutes))

    def _apply_iqr_to_trades(self, trade_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates prices for trades and applies IQR filtering.
        Returns a list of trade records that are considered inliers.
        """
        if not trade_records:
            return []

        prices = []
        for r in trade_records:
            try:
                price = float(r['sol_amount']) / float(r['token_amount'])
                prices.append(price)
            except (TypeError, ValueError, ZeroDivisionError):
                prices.append(None) # Mark invalid prices

        # Filter out None prices before IQR
        valid_prices_for_iqr = [p for p in prices if p is not None]
        if not valid_prices_for_iqr:
            logger.warning("No valid prices to apply IQR filtering.")
            return [] # Return all trades if no valid prices for IQR

        q1 = np.percentile(valid_prices_for_iqr, 25)
        q3 = np.percentile(valid_prices_for_iqr, 75)
        iqr_val = q3 - q1
        lower_bound = q1 - 1.5 * iqr_val
        upper_bound = q3 + 1.5 * iqr_val

        inlier_trades = []
        for i, r in enumerate(trade_records):
            price = prices[i]
            if price is not None and lower_bound <= price <= upper_bound:
                # Add the calculated price to the trade record for convenience
                r_copy = dict(r) # Create a copy to avoid modifying the original record list
                r_copy['price'] = price
                inlier_trades.append(r_copy)

        if not inlier_trades:
            logger.warning("All trades filtered out as outliers by IQR. No inlier trades to use.")
            # Fallback: could return unfiltered trades or a subset based on other criteria
            # For now, returning empty list, forcing price calculation to fail or use other fallbacks.
            return []
        return inlier_trades

    async def _calculate_median_price_with_iqr(self, mint: str, window_minutes: int, conn) -> float | None:
        """Calculates median price with IQR filtering."""
        trade_records = await self._get_raw_trades_for_window(mint, window_minutes, conn)
        if not trade_records:
            logger.debug(f"No trades found for {mint} in the last {window_minutes} minutes for median calculation.")
            return None

        # Prices are calculated and IQR applied within _apply_iqr_to_trades
        # Here, we just need the prices from the inlier trades
        inlier_trades = self._apply_iqr_to_trades(trade_records) # this adds 'price' key
        if not inlier_trades:
            # Attempt fallback to unfiltered median if all were outliers
            all_prices = [float(r['sol_amount'])/float(r['token_amount']) for r in trade_records if r['token_amount'] and r['sol_amount']]
            if all_prices:
                 logger.warning(f"All prices for {mint} filtered out as outliers. Falling back to unfiltered median for median calculation.")
                 return statistics.median(all_prices)
            logger.warning(f"No inlier trades for {mint} after IQR for median calculation, and no fallback possible.")
            return None

        inlier_prices = [float(trade['price']) for trade in inlier_trades]
        return statistics.median(inlier_prices) if inlier_prices else None

    async def _calculate_vwap_price_with_iqr(self, mint: str, window_minutes: int, conn) -> float | None:
        """Calculates VWAP with IQR filtering on individual trade prices."""
        trade_records = await self._get_raw_trades_for_window(mint, window_minutes, conn)
        if not trade_records:
            logger.debug(f"No trades found for {mint} in the last {window_minutes} minutes for VWAP calculation.")
            return None

        inlier_trades = self._apply_iqr_to_trades(trade_records)
        if not inlier_trades:
            logger.warning(f"No inlier trades for {mint} after IQR for VWAP calculation.")
            return None # Or implement fallback to unfiltered VWAP

        total_sol_inliers = sum(float(trade['sol_amount']) for trade in inlier_trades)
        total_tokens_inliers = sum(float(trade['token_amount']) for trade in inlier_trades)

        if total_tokens_inliers == 0:
            logger.warning(f"Total token amount for inliers is zero for {mint}. Cannot calculate VWAP.")
            return None
        return total_sol_inliers / total_tokens_inliers

    async def _calculate_twap_price_with_iqr(self, mint: str, window_minutes: int, interval_seconds: int, conn) -> float | None:
        """Calculates TWAP with IQR filtering on individual trade prices before resampling."""
        trade_records = await self._get_raw_trades_for_window(mint, window_minutes, conn)
        if not trade_records:
            logger.debug(f"No trades found for {mint} in the last {window_minutes} minutes for TWAP calculation.")
            return None

        inlier_trades_with_price = self._apply_iqr_to_trades(trade_records) # This adds 'price' to each dict
        if not inlier_trades_with_price:
            logger.warning(f"No inlier trades for {mint} after IQR for TWAP calculation.")
            return None

        # Create DataFrame from inlier trades with their calculated (inlier) prices and original timestamps
        df_data = [{'timestamp': pd.to_datetime(trade['timestamp']), 'price': float(trade['price'])} for trade in inlier_trades_with_price]
        df = pd.DataFrame(df_data)

        if df.empty:
            return None

        df = df.set_index('timestamp')
        # Resample into intervals and take the median price of each interval (using inlier prices)
        interval_prices = df['price'].resample(f'{interval_seconds}S').median(numeric_only=True)
        valid_interval_prices = interval_prices.dropna()

        if valid_interval_prices.empty:
            return None

        twap = valid_interval_prices.mean()
        return float(twap) if pd.notnull(twap) else None

    async def get_price_and_market_cap_for_decision(self, mint: str, config: dict, conn) -> Dict[str, Optional[float]]:
        """
        Centralized function to get the decision price and latest market cap for a token.
        The decision price is determined by PRICE_DETERMINATION_METHOD.
        The market cap is always from the single latest trade.
        """
        decision_price: Optional[float] = None
        latest_market_cap_sol: Optional[float] = None
        raw_latest_price: Optional[float] = None

        # 1. Fetch the absolute latest trade for market_cap and raw_latest_price
        latest_trade_query = """
            SELECT price, marketCapSol
            FROM trades
            WHERE mint = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        latest_trade_record = await conn.fetchrow(latest_trade_query, mint)

        if latest_trade_record:
            raw_latest_price = float(latest_trade_record['price']) if latest_trade_record['price'] is not None else None
            latest_market_cap_sol = float(latest_trade_record['marketcapsol']) if latest_trade_record['marketcapsol'] is not None else None
            # Ensure market_cap is positive, otherwise treat as None for safety
            if latest_market_cap_sol is not None and latest_market_cap_sol <= 0:
                latest_market_cap_sol = None
            if raw_latest_price is not None and raw_latest_price <=0:
                raw_latest_price = None # Don't use non-positive as raw latest price
        else:
            logger.warning(f"No trades found at all for {mint} to determine latest market cap or price.")
            return {'price': None, 'market_cap': None}

        # 2. Determine the decision_price based on the configured method
        method = config.get("PRICE_DETERMINATION_METHOD", "LATEST")
        window_minutes = config.get("PRICE_AVG_WINDOW_MINUTES", 3) # Default to 3 mins from config.py

        try:
            if method == "LATEST":
                decision_price = raw_latest_price
            elif method == "MEDIAN":
                decision_price = await self._calculate_median_price_with_iqr(mint, window_minutes, conn)
            elif method == "VWAP":
                decision_price = await self._calculate_vwap_price_with_iqr(mint, window_minutes, conn)
            elif method == "TWAP":
                interval_seconds = config.get("TWAP_SUB_INTERVAL_SECONDS", 60)
                decision_price = await self._calculate_twap_price_with_iqr(mint, window_minutes, interval_seconds, conn)
            else:
                logger.warning(f"Unknown PRICE_DETERMINATION_METHOD: {method}. Defaulting to LATEST.")
                decision_price = raw_latest_price

            # Fallback: If chosen method fails to return a price, but raw_latest_price is available, use it.
            if decision_price is None and raw_latest_price is not None:
                logger.warning(f"Price determination method '{method}' for {mint} resulted in None. Falling back to raw latest price: {raw_latest_price}.")
                decision_price = raw_latest_price
            elif decision_price is not None and decision_price <= 0:
                 logger.warning(f"Price determination method '{method}' for {mint} resulted in non-positive price: {decision_price}. Attempting fallback to raw_latest_price.")
                 decision_price = raw_latest_price if raw_latest_price is not None and raw_latest_price > 0 else None


        except Exception as e:
            logger.error(f"Error during price determination for {mint} with method {method}: {e}", exc_info=True)
            decision_price = raw_latest_price # Fallback to raw latest on error if available

        if decision_price is None:
            logger.error(f"Could not determine a valid price for {mint} using method '{method}' and fallback failed.")


        logger.debug(f"Price decision for {mint}: Method='{method}', DecidedPrice={decision_price}, LatestMC={latest_market_cap_sol}, RawLatestPrice={raw_latest_price}")
        return {'price': decision_price, 'market_cap': latest_market_cap_sol}

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

    async def insert_heartbeat(self, event_type: str = 'heartbeat', details: Optional[dict] = None):
        """Insert a new heartbeat or event into the bot_heartbeat table."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO bot_heartbeat (event_type, details) VALUES ($1, $2)",
                    event_type, json.dumps(details) if details else None
                )
            # logger.debug(f"Heartbeat event '{event_type}' inserted.") # Optional logging
        except Exception as e:
            logger.error(f"Error inserting heartbeat event: {e}", exc_info=True)
            # Decide if you want to raise, as heartbeat failure could be critical

    async def get_last_heartbeat_before(self, timestamp: datetime) -> Optional[datetime]:
        """Get the last heartbeat recorded before a given timestamp."""
        query = "SELECT timestamp FROM bot_heartbeat WHERE timestamp < $1 ORDER BY timestamp DESC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, timestamp)
            return row['timestamp'] if row else None

    async def get_first_heartbeat_after(self, timestamp: datetime) -> Optional[datetime]:
        """Get the first heartbeat recorded after a given timestamp."""
        query = "SELECT timestamp FROM bot_heartbeat WHERE timestamp > $1 ORDER BY timestamp ASC LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, timestamp)
            return row['timestamp'] if row else None

    async def check_for_data_gap_on_restart(self,
                                            archived_at: datetime,
                                            gap_detection_threshold_seconds: int) -> bool:
        """
        Checks if there was a significant gap in bot operation (missing heartbeats)
        immediately before the 'archived_at' timestamp.
        """
        try:
            query = """
                SELECT timestamp FROM bot_heartbeat
                WHERE timestamp < $1
                ORDER BY timestamp DESC
                LIMIT 1;
            """
            # Ensure self.pool is the correct way to get a connection
            # This might be self.db_pool or similar depending on your class structure
            async with self.pool.acquire() as conn:
                last_heartbeat_record = await conn.fetchrow(query, archived_at)

            if not last_heartbeat_record:
                # No heartbeats recorded before this token's archival.
                # Check if any heartbeats exist at all to distinguish a new bot from a long-dead one.
                async with self.pool.acquire() as conn: # Re-acquire if needed, or use existing conn if scope allows
                    first_ever_heartbeat = await conn.fetchval("SELECT MIN(timestamp) FROM bot_heartbeat")
                
                if first_ever_heartbeat and first_ever_heartbeat < archived_at:
                    # Heartbeats exist in the table, but none before the current archival time.
                    # This implies the bot was down for the entire period leading up to 'archived_at'.
                    logger.warning(f"No heartbeats found before {archived_at}, but older heartbeats exist. Gap detected.")
                    return True
                elif not first_ever_heartbeat:
                    logger.info(f"No heartbeats found in bot_heartbeat table. Cannot determine gap for token archived at {archived_at}. Assuming no gap for safety.")
                    return False # Cannot determine, conservatively assume no gap.
                else: # Should not happen if archived_at is current time and heartbeats exist after.
                    logger.debug(f"First heartbeat {first_ever_heartbeat} is after {archived_at}. No gap determined.")
                    return False

            last_heartbeat_ts = last_heartbeat_record['timestamp']
            # Ensure archived_at is offset-aware if last_heartbeat_ts is, or vice-versa.
            # If one is naive and the other is aware, comparison will raise an error.
            # Assuming both are consistently offset-aware (e.g., UTC from TIMESTAMPTZ).
            time_since_last_heartbeat_seconds = (archived_at - last_heartbeat_ts).total_seconds()

            logger.debug(f"Token archived_at: {archived_at}, Last heartbeat: {last_heartbeat_ts}, "
                        f"Duration since last heartbeat: {time_since_last_heartbeat_seconds:.2f}s, "
                        f"Gap threshold: {gap_detection_threshold_seconds}s")

            if time_since_last_heartbeat_seconds > gap_detection_threshold_seconds:
                logger.info(f"Data gap detected: Last heartbeat was {time_since_last_heartbeat_seconds:.2f}s ago "
                            f"(threshold: {gap_detection_threshold_seconds}s). Token lifecycle likely interrupted.")
                return True
            
            logger.debug("No significant pre-archival data gap detected based on heartbeats.")
            return False

        except Exception as e:
            logger.error(f"Error in check_for_data_gap_on_restart: {e}", exc_info=True)
            return False # Fail safe

    async def check_for_data_gap(self, token_start_time: datetime, token_end_time: datetime, gap_threshold_seconds: int = 300) -> bool:
        """
        Checks for significant data gaps in bot_heartbeat table during the token's active period.
        A gap is significant if the time between two consecutive heartbeats exceeds gap_threshold_seconds.
        """
        last_hb_before_token_end = await self.get_last_heartbeat_before(token_end_time)
        first_hb_after_token_start = await self.get_first_heartbeat_after(token_start_time)

        if not last_hb_before_token_end or not first_hb_after_token_start:
            # If no heartbeats surround the token's activity, assume a potential gap (conservative approach)
            # This might happen if the token's entire lifecycle was during a bot downtime.
            logger.warning(f"Heartbeat data missing around token activity ({token_start_time} - {token_end_time}). Assuming potential data gap.")
            return True

        # Check gap between the heartbeat just before the token died (or script stopped)
        # and the heartbeat just after the script restarted (which would be after the token_start_time if it was an existing token)

        # Scenario 1: Gap *during* the token's recorded lifecycle
        # This requires iterating heartbeats within the token_start_time and token_end_time,
        # but a simpler proxy is to check the continuity around the point of potential script failure.

        # Let's refine: We are interested if the bot was down for a period that *ended*
        # shortly before token_end_time (when it was marked dead).
        # And this downtime started *after* token_start_time.

        query_heartbeats_in_range = """
            SELECT timestamp FROM bot_heartbeat
            WHERE timestamp >= $1 AND timestamp <= $2
            ORDER BY timestamp ASC;
        """
        async with self.pool.acquire() as conn:
            heartbeats = await conn.fetch(query_heartbeats_in_range, token_start_time, token_end_time)

        if not heartbeats: # No heartbeats during the token's entire active period
            logger.debug(f"No bot heartbeats found during token {token_start_time} - {token_end_time} lifecycle. Likely a gap.")
            return True

        previous_hb_ts = None
        for record in heartbeats:
            current_hb_ts = record['timestamp']
            if previous_hb_ts:
                if (current_hb_ts - previous_hb_ts).total_seconds() > gap_threshold_seconds:
                    logger.info(f"Data gap detected for token: {previous_hb_ts} to {current_hb_ts} ({(current_hb_ts - previous_hb_ts).total_seconds()}s)")
                    return True
            previous_hb_ts = current_hb_ts

        # Also check the gap between the last known heartbeat *before* the token ended its lifecycle
        # and the token's end time. This covers the case where the bot stopped *while* this token was live.
        if previous_hb_ts and (token_end_time - previous_hb_ts).total_seconds() > gap_threshold_seconds:
            logger.info(f"Data gap detected leading up to token end: last heartbeat at {previous_hb_ts}, token ended at {token_end_time}")
            return True

        return False
    
    async def set_token_cooldown(self, mint: str, cooldown_minutes: int):
        """Sets a cooldown period on a token to prevent immediate re-buys."""
        if cooldown_minutes <= 0:
            return # No cooldown to set

        cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes)
        query = "UPDATE tokens SET cooldown_until = $1 WHERE mint = $2"
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, cooldown_until, mint)
            logger.info(f"Token {mint} is on a re-buy cooldown until {cooldown_until.strftime('%Y-%m-%d %H:%M:%S')} UTC.")
        except Exception as e:
            logger.error(f"Failed to set cooldown for token {mint}: {e}", exc_info=True)

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
                        logger.info("🗄️ Backing up table %s", table)

                        if table == 'tokens':
                            # Handle the 'tokens' table as a special case with explicit columns
                            await conn.execute("""
                                INSERT INTO tokens_backup (
                                    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey,
                                    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri,
                                    website, telegram, twitter, socials_score, socials_last_checked,
                                    sol_price_usd, is_active, last_trade, timestamp,
                                    cooldown_until,
                                    backup_reason, backup_timestamp
                                )
                                SELECT
                                    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey,
                                    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri,
                                    website, telegram, twitter, socials_score, socials_last_checked,
                                    sol_price_usd, is_active, last_trade, timestamp,
                                    cooldown_until,
                                    'manual_backup', NOW()
                                FROM tokens
                                ON CONFLICT (mint) DO NOTHING;
                            """)
                        else:
                            # Original logic for other tables (assuming their backup tables have identical columns)
                            # NOTE: This generic logic is still fragile. Explicit columns are always better.
                            conflict_key_map = {
                                'trades': 'signature',
                                'rugcheck': 'mint',
                                'migrations': 'signature',
                                'portfolio': 'id'
                            }
                            conflict_key = conflict_key_map.get(table)
                            if conflict_key:
                                await conn.execute(f"INSERT INTO {table}_backup SELECT * FROM {table} ON CONFLICT ({conflict_key}) DO NOTHING;")
                            else:
                                logger.warning(f"No conflict key defined for table '{table}' in backup_db. Skipping backup.")
                                continue

                        logger.info("🧹 Truncating table %s", table)
                        await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")

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

    def ohlcv_sql_like(self, df_group: pd.DataFrame) -> pd.Series:
        df = df_group 
        if df.empty:
            return pd.Series({
                'Open': np.nan, 'High': np.nan, 'Low': np.nan, 'Close': np.nan,
                'Volume': 0.0,
                'market_cap_calculated': np.nan, 
                'marketCapSol': np.nan,          
                'volatility': 0.0
            })

        last_rolling_volume = df['rolling_volume_sql'].iloc[-1] if 'rolling_volume_sql' in df.columns and not df['rolling_volume_sql'].empty else 0.0
        last_rolling_volatility = df['rolling_volatility_sql'].iloc[-1] if 'rolling_volatility_sql' in df.columns and not df['rolling_volatility_sql'].empty else 0.0
        
        last_market_cap_usd = df['market_cap_calculated'].iloc[-1] if 'market_cap_calculated' in df.columns and not df['market_cap_calculated'].isnull().all() else np.nan
        last_market_cap_sol_live = df['marketcapsol'].iloc[-1] if 'marketcapsol' in df.columns and not df['marketcapsol'].empty and pd.notna(df['marketcapsol'].iloc[-1]) else np.nan

        return pd.Series({
            'Open': df['price'].iloc[0] if 'price' in df.columns and not df['price'].empty else np.nan,
            'High': df['price'].max() if 'price' in df.columns and not df['price'].empty else np.nan,
            'Low': df['price'].min() if 'price' in df.columns and not df['price'].empty else np.nan,
            'Close': df['price'].iloc[-1] if 'price' in df.columns and not df['price'].empty else np.nan,
            'Volume': last_rolling_volume,
            'market_cap_calculated': last_market_cap_usd,
            'marketCapSol': last_market_cap_sol_live, 
            'volatility': last_rolling_volatility
        })

    # In database_handler.py, replace the whole function with this:

    async def get_historical_data_for_backtesting(
            self,
            mints: List[str],
            start_date: datetime,
            end_date: datetime
        ) -> Dict[str, pd.DataFrame]:
            if not mints:
                logger.warning("get_historical_data_for_backtesting called with empty mints list.")
                return {}
            if not self.pool:
                logger.error("Database pool not initialized.")
                return {}

            start_date = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date.astimezone(timezone.utc)
            end_date = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date.astimezone(timezone.utc)

            trade_query = """
                SELECT
                    mint, timestamp, price, (sol_amount*sol_price_usd) AS volume,
                    market_cap_calculated,
                    marketCapSol AS live_market_cap_sol
                FROM v_trades
                WHERE mint = ANY($1::text[])
                AND timestamp >= $2 AND timestamp < $3
                AND price > 0 AND sol_amount IS NOT NULL AND price IS NOT NULL
                ORDER BY mint, timestamp;
            """

            rugcheck_query = """
                WITH RankedRugcheck AS (
                    SELECT mint, last_checked AS timestamp, score AS rugcheck_score,
                           ROW_NUMBER() OVER (PARTITION BY mint ORDER BY last_checked DESC) as rn
                    FROM v_rugcheck WHERE mint = ANY($1::text[]) AND last_checked < $3
                )
                SELECT mint, timestamp, rugcheck_score FROM RankedRugcheck WHERE rn = 1 OR timestamp >= $2;
            """

            token_info_query = """
                WITH TokenCreationData AS (
                    SELECT
                        mint, socials_score, timestamp AS token_creation_time,
                        marketCapSol AS creation_init_market_cap_sol,
                        ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp ASC) as rn
                    FROM v_tokens vt WHERE mint = ANY($1::text[])
                )
                SELECT mint, token_creation_time, socials_score, creation_init_market_cap_sol
                FROM TokenCreationData WHERE rn = 1;
            """

            results_dict = {}
            async with self.pool.acquire() as conn:
                try:
                    trade_records_raw = await conn.fetch(trade_query, mints, start_date, end_date)
                    rugcheck_records_raw = await conn.fetch(rugcheck_query, mints, start_date, end_date)
                    token_info_records_raw = await conn.fetch(token_info_query, mints)

                    if not trade_records_raw:
                        logger.warning("No trade records found for the specified mints and period.")
                        return {}

                    trade_records_list_of_dicts = [dict(rec) for rec in trade_records_raw]
                    trades_df = pd.DataFrame(trade_records_list_of_dicts)
                    
                    trades_df.columns = [str(col).lower() for col in trades_df.columns]
                    
                    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], errors='coerce', utc=True)
                    trades_df.dropna(subset=['timestamp'], inplace=True)
                    
                    numeric_cols_from_trades = ['price', 'volume', 'market_cap_calculated', 'live_market_cap_sol']
                    for col in numeric_cols_from_trades:
                        if col in trades_df.columns:
                            trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
                        else:
                            logger.error(f"Critical: Column '{col}' expected from trades query but missing. DataFrame columns: {list(trades_df.columns)}")
                            trades_df[col] = 0.0
                    trades_df.dropna(subset=['price', 'volume'], inplace=True)

                    all_processed_trades = []
                    time_interval_minutes = self.config.get('DEFAULT_TIME_INTERVALL', 10)
                    window_duration = f"{time_interval_minutes}min"

                    for mint_name, mint_df_group in trades_df.groupby('mint'):
                        mint_df = mint_df_group.sort_values('timestamp').copy()
                        mint_df_indexed = mint_df.set_index('timestamp')
                        mint_df['rolling_volume_sql'] = mint_df_indexed['volume'].rolling(window_duration, closed='left').sum().fillna(0.0).values
                        
                        if 'live_market_cap_sol' in mint_df.columns:
                           mint_df.rename(columns={'live_market_cap_sol': 'marketcapsol'}, inplace=True)

                        prices_series = mint_df['price']
                        if len(prices_series) > 1:
                            log_returns = np.log(prices_series / prices_series.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
                            rolling_obj = log_returns.set_axis(mint_df['timestamp']).rolling(window_duration, closed='left')
                            rolling_std = rolling_obj.std().fillna(0.0)
                            rolling_count = rolling_obj.count().fillna(0.0)
                            volatility_sql = rolling_std.astype(float) * np.sqrt(np.maximum(rolling_count.astype(float), 1.0))
                            mint_df['rolling_volatility_sql'] = volatility_sql.where(rolling_count > 5, 0.0).values
                        else:
                            mint_df['rolling_volatility_sql'] = 0.0
                        mint_df['rolling_volatility_sql'] = mint_df['rolling_volatility_sql'].fillna(0.0)
                        all_processed_trades.append(mint_df)

                    if not all_processed_trades: return {}
                    processed_trades_df = pd.concat(all_processed_trades)

                    ohlcv_df = processed_trades_df.groupby(['mint', pd.Grouper(key='timestamp', freq='5s')])\
                                                .apply(self.ohlcv_sql_like).reset_index()
                    
                    ohlcv_df.dropna(subset=['mint', 'timestamp'], inplace=True)
                    ohlc_cols = ['Open', 'High', 'Low', 'Close']
                    ohlcv_df[ohlc_cols] = ohlcv_df.groupby('mint')[ohlc_cols].ffill().bfill().fillna(0.0)
                    
                    cols_to_fill_ohlcv = ['Volume', 'volatility', 'market_cap_calculated', 'marketCapSol']
                    for col in cols_to_fill_ohlcv:
                        if col in ohlcv_df.columns: ohlcv_df[col] = ohlcv_df[col].fillna(0.0)
                        else: ohlcv_df[col] = 0.0
                    
                    ohlcv_df = ohlcv_df.set_index('timestamp')
                    if ohlcv_df.index.has_duplicates: ohlcv_df = ohlcv_df.loc[~ohlcv_df.index.duplicated(keep='last')]
                    
                    resampled_ohlcv_list = []
                    for mint_name, group_df in ohlcv_df.groupby('mint'):
                        if group_df.index.has_duplicates: 
                            group_df = group_df.loc[~group_df.index.duplicated(keep='last')]
                        
                        min_ts, max_ts = group_df.index.min(), group_df.index.max()
                        if pd.isna(min_ts) or pd.isna(max_ts): 
                            logger.warning(f"Skipping mint {mint_name} due to NaT in min/max timestamp for reindexing.")
                            continue
                            
                        full_range = pd.date_range(start=min_ts, end=max_ts, freq='5s', tz='UTC')
                        group_reindexed = group_df.reindex(full_range)

                        # --- FINAL, ROBUST FIX ---
                        # Interpolate each numeric column individually to avoid the warning.
                        cols_to_interpolate = [
                            'Open', 'High', 'Low', 'Close', 'Volume',
                            'market_cap_calculated', 'marketCapSol', 'volatility'
                        ]
                        
                        for col in cols_to_interpolate:
                            if col in group_reindexed.columns:
                                group_reindexed[col] = pd.to_numeric(group_reindexed[col], errors='coerce').interpolate(method='time')

                        group_resampled = group_reindexed
                        # --- END FIX ---
                        
                        group_resampled['mint'] = mint_name
                        resampled_ohlcv_list.append(group_resampled)

                    if not resampled_ohlcv_list: 
                        logger.warning("No data after resampling for any mints.")
                        return {}
                    
                    resampled_ohlcv_df = pd.concat(resampled_ohlcv_list)
                    if resampled_ohlcv_df.index.name != 'timestamp': resampled_ohlcv_df.index.name = 'timestamp'

                    if rugcheck_records_raw:
                        rugcheck_list_of_dicts = [dict(rec) for rec in rugcheck_records_raw]
                        rugcheck_df = pd.DataFrame(rugcheck_list_of_dicts)
                        rugcheck_df.columns = [str(col).lower() for col in rugcheck_df.columns]
                        if 'timestamp' in rugcheck_df.columns:
                            rugcheck_df['timestamp'] = pd.to_datetime(rugcheck_df['timestamp'], errors='coerce', utc=True)
                            rugcheck_df.dropna(subset=['timestamp'], inplace=True)
                            rugcheck_df = rugcheck_df.sort_values(['mint', 'timestamp']).drop_duplicates(subset=['mint', 'timestamp'], keep='last')
                            rugcheck_df.set_index('timestamp', inplace=True)
                            rugcheck_df['rugcheck_score'] = pd.to_numeric(rugcheck_df.get('rugcheck_score'), errors='coerce')
                            rugcheck_df = rugcheck_df[['mint', 'rugcheck_score']]
                        else:
                            logger.warning("Rugcheck data missing 'timestamp' column.")
                            rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))
                    else:
                        rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], name='timestamp', tz='UTC'))

                    token_info_map = {}
                    if token_info_records_raw:
                        for r_rec in token_info_records_raw:
                            r_dict = dict(r_rec)
                            mint_val, creation_time_val, socials_val, creation_mc_sol_val = r_dict.get('mint'), r_dict.get('token_creation_time'), r_dict.get('socials_score'), r_dict.get('creation_init_market_cap_sol')
                            creation_time, socials, creation_mc_sol = pd.to_datetime(creation_time_val, errors='coerce', utc=True), pd.to_numeric(socials_val, errors='coerce'), pd.to_numeric(creation_mc_sol_val, errors='coerce')
                            if mint_val and pd.notna(creation_time):
                                token_info_map[mint_val] = {'creation_time': creation_time, 'socials_score': socials, 'creation_init_market_cap_sol': creation_mc_sol}
                    
                    required_final_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'creation_init_market_cap_sol', 'volatility', 'rugcheck_score', 'socials_score', 'token_creation_time']
                    
                    grouped_ohlcv = resampled_ohlcv_df.groupby('mint')
                    for mint_name in grouped_ohlcv.groups:
                        mint_ohlcv_group = grouped_ohlcv.get_group(mint_name)
                        cols_to_select_from_ohlcv = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'volatility']
                        existing_cols_in_group = [col for col in cols_to_select_from_ohlcv if col in mint_ohlcv_group.columns]
                        if not all(c in existing_cols_in_group for c in ['market_cap_calculated', 'marketCapSol']):
                            logger.warning(f"Mint {mint_name} group missing essential live market cap columns. Columns present: {list(mint_ohlcv_group.columns)}. Skipping.")
                            continue
                        combined_df = mint_ohlcv_group[existing_cols_in_group].copy()

                        mint_rugcheck_data = rugcheck_df[rugcheck_df['mint'] == mint_name][['rugcheck_score']] if not rugcheck_df.empty else None
                        if mint_rugcheck_data is not None and not mint_rugcheck_data.empty:
                            combined_df = combined_df.sort_index()
                            mint_rugcheck_data = mint_rugcheck_data.sort_index()
                            if mint_rugcheck_data.index.has_duplicates: mint_rugcheck_data = mint_rugcheck_data.loc[~mint_rugcheck_data.index.duplicated(keep='last')]
                            combined_df = pd.merge_asof(combined_df, mint_rugcheck_data, left_index=True, right_index=True, direction='backward', tolerance=pd.Timedelta('1d'))
                        else: combined_df['rugcheck_score'] = np.nan

                        mint_specific_info = token_info_map.get(mint_name)
                        if mint_specific_info:
                            combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'] = mint_specific_info['creation_time'], mint_specific_info['socials_score'], mint_specific_info.get('creation_init_market_cap_sol', np.nan)
                        else:
                            combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'] = pd.NaT, 100, np.nan
                        
                        for r_col in required_final_cols:
                            if r_col not in combined_df.columns: combined_df[r_col] = np.nan 

                        for col in ['rugcheck_score', 'socials_score', 'token_creation_time', 'creation_init_market_cap_sol']: combined_df[col] = combined_df[col].ffill().bfill()
                        
                        combined_df['rugcheck_score'] = combined_df['rugcheck_score'].fillna(10000).astype(int)
                        combined_df['socials_score'] = combined_df['socials_score'].fillna(100).astype(int)
                        combined_df['creation_init_market_cap_sol'] = pd.to_numeric(combined_df['creation_init_market_cap_sol'], errors='coerce').fillna(0.0)

                        for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'volatility']:
                            combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0.0)
                        
                        final_df = combined_df[(combined_df.index >= start_date) & (combined_df.index < end_date)].copy()

                        if not final_df.empty and all(col in final_df.columns for col in required_final_cols):
                            astype_dict = {'Open': float, 'High': float, 'Low': float, 'Close': float, 'Volume': float, 'market_cap_calculated': float, 'marketCapSol': float, 'creation_init_market_cap_sol': float, 'volatility': float, 'rugcheck_score': int, 'socials_score': int}
                            final_df = final_df[required_final_cols].astype(astype_dict)
                            final_df.index = pd.to_datetime(final_df.index, utc=True)
                            results_dict[mint_name] = final_df
                        else:
                            logger.warning(f"No valid data or missing columns for {mint_name} after final processing. Skipping.")
                
                except Exception as e:
                    logger.error(f"Error processing historical data ({type(e).__name__}): {e}", exc_info=True)
                    return {}

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
