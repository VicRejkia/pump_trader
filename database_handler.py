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
from typing import Dict, Optional, List, Tuple # Added List, Tuple
from utils import calculate_volatility
import inspect 
from typing import Optional

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

    async def get_tokens_to_unsubscribe(self, mc_drop_threshold, inactivity_period):
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
                AND t.timestamp <= NOW() - INTERVAL '15 minutes'
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
            ORDER BY t.timestamp DESC;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, mc_drop_threshold, inactivity_period)

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

        if reason == "rugged_dead":
                # Get this from your bot's configuration system
                # Example: RESTART_GAP_THRESHOLD_SECONDS = self.config.get('RESTART_GAP_THRESHOLD_SECONDS', 600)
                # Ensure self.config is available or pass the value directly.
                # For this example, let's assume it's accessed via self.config.
                if not hasattr(self, 'config') or '_RESTART_GAP_THRESHOLD_SECONDS' not in self.config:
                    logger.warning("RESTART_GAP_THRESHOLD_SECONDS not found in config. Using default of 600s.")
                    RESTART_GAP_THRESHOLD_SECONDS = 600 # Default to 10 minutes
                else:
                    RESTART_GAP_THRESHOLD_SECONDS = self.config['_RESTART_GAP_THRESHOLD_SECONDS']


                if await self.check_for_data_gap_on_restart(archived_at, RESTART_GAP_THRESHOLD_SECONDS):
                    logger.info(f"Token {mint} ({reason}) archived at {archived_at}. Pre-archival data gap detected. "
                                f"Changing reason to 'interrupted_gap_fill'.")
                    final_reason = "interrupted_gap_fill"
                else:
                    logger.info(f"Token {mint} ({reason}) archived at {archived_at}. No significant pre-archival data gap. Reason remains '{final_reason}'.")



        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await conn.execute('''
                            INSERT INTO tokens_backup SELECT *, $1, NOW() FROM tokens WHERE mint = $2
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

    async def get_vwap_price(self, mint: str, window_minutes: int, conn=None) -> float | None:
        query = """
            SELECT SUM(td.sol_amount) / SUM(td.token_amount) AS vwap
            FROM trades td
            WHERE td.mint = $1
            AND td.timestamp >= NOW() - ($2 || ' minutes')::interval
            AND td.token_amount > 0;
        """
        connection = conn or await self.pool.acquire()
        try:
            result = await connection.fetchval(query, mint, str(window_minutes))
            return float(result) if result is not None else None
        except Exception as e:
            logger.error(f"Error calculating VWAP for {mint}: {e}", exc_info=True)
            return None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    # TWAP would be more involved, potentially fetching rows and processing in Python
    async def get_twap_price(self, mint: str, window_minutes: int, interval_seconds: int, conn=None) -> float | None:
        # 1. Fetch trades for the window
        query_trades = """
            SELECT timestamp, price  -- price is sol_amount / token_amount
            FROM trades
            WHERE mint = $1
            AND timestamp >= NOW() - ($2 || ' minutes')::interval
            AND token_amount > 0 -- ensure valid price calculation
            ORDER BY timestamp ASC;
        """
        connection = conn or await self.pool.acquire()
        try:
            trade_records = await connection.fetch(query_trades, mint, str(window_minutes))
            if not trade_records:
                return None

            # 2. Process in Python (example using pandas for simplicity)
            import pandas as pd # Make sure pandas is available
            df = pd.DataFrame(trade_records, columns=['timestamp', 'price'])
            df['price'] = pd.to_numeric(df['price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')

            if df.empty:
                return None

            # Resample into intervals and take the median price of each interval
            # 'L' offset for 'last' value in interval, 'min_count=1' ensures NaN if no trades
            interval_prices = df['price'].resample(f'{interval_seconds}S').median(numeric_only=True)
            
            # Drop intervals with no trades (NaNs) and calculate the mean of the interval medians
            valid_interval_prices = interval_prices.dropna()
            if valid_interval_prices.empty:
                return None
                
            twap = valid_interval_prices.mean()
            return float(twap) if pd.notnull(twap) else None

        except Exception as e:
            logger.error(f"Error calculating TWAP for {mint}: {e}", exc_info=True)
            return None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

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
                    time_interval_minutes = self.config['DEFAULT_TIME_INTERVALL'] # Get from config
                    time_interval_minutes = self.config['DEFAULT_TIME_INTERVALL'] # Get from config
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

                        # ---> FIX: Call infer_objects() before interpolating <---
                        # group_resampled = group_df.reindex(full_range).interpolate(method='time')
                        # Reindex first, creating the DataFrame that might have object dtypes due to NaNs
                        group_reindexed = group_df.reindex(full_range)

                        try:
                            # Attempt to convert columns to more specific dtypes (e.g., float, int)
                            # copy=False modifies inplace if possible, potentially saving memory
                            group_reindexed = group_reindexed.infer_objects(copy=False)
                        except Exception as e:
                            # Log if infer_objects fails, but proceed cautiously
                            logger.warning(f"Failed to infer objects for {mint_name} before interpolation: {e}")

                        # Reindex and interpolate within the group's actual range
                        # Now interpolate. This should operate on more appropriate dtypes.
                        group_resampled = group_reindexed.interpolate(method='time')
                        # ---> END FIX <---
                        
                       
                       
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
