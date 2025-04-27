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
from config import TOTAL_SUPPLY
from state_manager import GlobalState
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple # Added List, Tuple

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
            return result['total_supply'] if result else TOTAL_SUPPLY


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

    async def get_filtered_tokens(self, max_socials=100, max_rugcheck=10000, min_volume_sol=0, time_window_minutes=60, portfolio_only=False, volume_aggregation='avg'): # Added portfolio_only
        """
        Fetches tokens filtered by socials score, latest rugcheck score, recent trade volume,
        and optionally only tokens currently in the active portfolio.
        """
        # Ensure numeric types for parameters
        try:
            max_socials = int(max_socials)
            max_rugcheck = int(max_rugcheck)
            min_volume_sol = float(min_volume_sol)
            time_window_minutes = int(time_window_minutes)
            # portfolio_only is already boolean from Flask request parsing or default
        except (ValueError, TypeError):
            logger.error("Invalid filter parameter types received.")
            return [] # Return empty on invalid input types

        # Construct the interval string safely
        interval_str = timedelta(minutes=time_window_minutes)

        # Base query parts
        select_clause = """
            SELECT DISTINCT -- Use DISTINCT to avoid duplicates if a token has multiple active portfolio entries (shouldn't happen with good logic)
                vt.mint,
                COALESCE(vt.name, vt.mint) AS name,
                vt.socials_score,
                lr.score AS rugcheck_score,
                COALESCE(rv.volume_sol, 0) as recent_volume_sol
        """
        from_clause = """
            FROM v_tokens vt
            LEFT JOIN LatestRugcheck lr ON vt.mint = lr.mint AND lr.rn = 1
            LEFT JOIN RecentVolume rv ON vt.mint = rv.mint
        """
        where_clause = """
            WHERE
                vt.socials_score IS NOT NULL AND vt.socials_score <= $1
                AND (lr.score IS NULL OR lr.score <= $2)
        """
        order_by_clause = "ORDER BY name, vt.mint;"
        params = [max_socials, max_rugcheck, min_volume_sol, interval_str, volume_aggregation]

        # Add portfolio filter if requested
        if portfolio_only:
            # Join with portfolio table to filter for active positions
            from_clause += """
            INNER JOIN portfolio p ON vt.mint = p.mint
            """
            # where_clause += """
            # AND p.status = 'active' AND p.tx_type = 'buy' -- Ensure we link based on the active buy record
            # """
            logger.info("Filtering tokens to include only those in the active portfolio.")


        # Combine query parts
        query = f"""
            WITH LatestRugcheck AS (
                SELECT
                    mint,
                    score,
                    ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) as rn
                FROM v_rugcheck
            ), RecentVolume AS (
                SELECT
                    mint,
                    COALESCE(
                        CASE
                            WHEN $5 = 'avg' THEN AVG(sol_amount)
                            WHEN $5 = 'max' THEN MAX(sol_amount)
                            ELSE SUM(sol_amount) -- Default to SUM if invalid aggregation type
                        END, 0) as volume_sol
                FROM v_trades
                WHERE timestamp >= (NOW() - $4::INTERVAL)
                GROUP BY mint
        ),
        Params AS (
            SELECT
                $1 AS max_socials,
                $2 AS max_rugcheck,
                $3 AS min_volume_sol,
                $4 AS time_window,
                $5 AS volume_aggregation
        )
        {select_clause}
        {from_clause}
        {where_clause}
        AND CASE
            WHEN Params.volume_aggregation = 'avg' THEN COALESCE(rv.volume_sol, 0) >= Params.min_volume_sol
            WHEN Params.volume_aggregation = 'max' THEN COALESCE(rv.volume_sol, 0) >= Params.min_volume_sol
            ELSE COALESCE(rv.volume_sol, 0) >= Params.min_volume_sol -- Default to SUM if invalid aggregation type
        END
        {order_by_clause}
        """

        async with self.pool.acquire() as conn:
            try:
                logger.debug(f"Fetching filtered tokens with params: max_socials={max_socials}, max_rugcheck={max_rugcheck}, min_volume_sol={min_volume_sol}, interval_str={interval_str}, portfolio_only={portfolio_only}, volume_aggregation={volume_aggregation}")
                # Cast parameters to appropriate types to avoid type mismatch
                query = """
                    SELECT * FROM tokens
                    WHERE
                        COALESCE(CAST(max_rugcheck AS INTEGER), 0) >= $1::INTEGER AND
                        COALESCE(CAST(max_socials AS INTEGER), 0) >= $2::INTEGER AND
                        COALESCE(CAST(volume AS FLOAT), 0) >= $3::FLOAT AND
                        created_at >= NOW() - INTERVAL '1 day'
                """
                results = await conn.fetch(query, max_rugcheck, max_socials, min_volume_sol)
                # Return list of dictionaries including the scores and volume
                return [
                    {
                        'mint': row['mint'],
                        'name': row['name'],
                        'socials': row['socials_score'],
                        'rugcheck': row['rugcheck_score'], # Might be None
                        'volume': round(row['recent_volume_sol'], 4) # Format volume
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

    async def get_historical_data_for_backtesting(
            self,
            mints: List[str],
            start_date: datetime,
            end_date: datetime
        ) -> Dict[str, pd.DataFrame]:
            """
            Fetches comprehensive historical data for specified tokens within a date range,
            structured for backtesting. Includes pre-calculated USD market cap and ensures
            data consistency. Fetches data sequentially on a single connection.

            Args:
                mints: A list of token mint addresses.
                start_date: The start datetime (inclusive, UTC).
                end_date: The end datetime (exclusive, UTC).

            Returns:
                A dictionary where keys are mint addresses and values are pandas DataFrames.
                Each DataFrame contains time-series data (price, volume, market_cap_calculated,
                rugcheck_score, socials_score, token_creation_time, volatility [calculated later])
                indexed by a timezone-aware UTC DatetimeIndex. Returns empty dict on error or no data.
            """
            if not mints:
                logger.warning("get_historical_data_for_backtesting called with empty mints list.")
                return {}
            if not self.pool:
                logger.error("Database pool not initialized.")
                return {}

            # Ensure dates are timezone-aware (UTC)
            if start_date.tzinfo is None: start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None: end_date = end_date.replace(tzinfo=timezone.utc)

            logger.info(f"Fetching historical data for {len(mints)} tokens from {start_date.isoformat()} to {end_date.isoformat()}...")

            # --- Define Queries (same as before) ---
            trade_query = """
                SELECT
                    mint, timestamp, price, sol_amount AS volume, market_cap_calculated
                FROM v_trades -- Use view
                WHERE mint = ANY($1::text[])
                AND timestamp >= $2 AND timestamp < $3
                ORDER BY mint, timestamp;
            """
            rugcheck_query = """
                WITH RankedRugcheck AS (
                    SELECT
                        mint, last_checked AS timestamp, score AS rugcheck_score,
                        ROW_NUMBER() OVER (PARTITION BY mint ORDER BY last_checked DESC) as rn
                    FROM v_rugcheck -- Use view
                    WHERE mint = ANY($1::text[])
                    AND last_checked < $3
                )
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
                    FROM v_tokens -- Use view
                    WHERE mint = ANY($1::text[])
                    AND timestamp < $2
                )
                SELECT mint, token_creation_time, socials_score
                FROM LatestTokenInfo
                WHERE rn = 1;
            """

            results_dict = {}
            async with self.pool.acquire() as conn: # Acquire single connection
                try:
                    # --- Fetch data SEQUENTIALLY ---
                    logger.debug("Fetching trade data...")
                    trade_records_raw = await conn.fetch(trade_query, mints, start_date, end_date)
                    logger.debug(f"Fetched {len(trade_records_raw)} trades.")

                    logger.debug("Fetching rugcheck data...")
                    rugcheck_records_raw = await conn.fetch(rugcheck_query, mints, start_date, end_date)
                    logger.debug(f"Fetched {len(rugcheck_records_raw)} rugchecks.")

                    logger.debug("Fetching token info data...")
                    token_info_records_raw = await conn.fetch(token_info_query, mints, end_date)
                    logger.debug(f"Fetched {len(token_info_records_raw)} token infos.")
                    # --- End Sequential Fetch ---


                    # --- Process Trade Data (same as before) ---
                    if not trade_records_raw:
                        logger.warning("No trade records found for the specified mints and period.")
                        return {}

                    trades_df = pd.DataFrame(trade_records_raw, columns=['mint', 'timestamp', 'price', 'volume', 'market_cap_calculated'])
                    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], errors='coerce', utc=True)
                    trades_df.dropna(subset=['timestamp'], inplace=True)
                    trades_df.set_index('timestamp', inplace=True)
                    for col in ['price', 'volume', 'market_cap_calculated']:
                        trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
                    trades_df = trades_df.sort_index()

                    # --- Process RugCheck Data (same as before) ---
                    if rugcheck_records_raw:
                        rugcheck_df = pd.DataFrame(rugcheck_records_raw, columns=['mint', 'timestamp', 'rugcheck_score'])
                        rugcheck_df['timestamp'] = pd.to_datetime(rugcheck_df['timestamp'], errors='coerce', utc=True)
                        rugcheck_df.dropna(subset=['timestamp'], inplace=True)
                        rugcheck_df.set_index('timestamp', inplace=True)
                        rugcheck_df['rugcheck_score'] = pd.to_numeric(rugcheck_df['rugcheck_score'], errors='coerce')
                        rugcheck_df = rugcheck_df[['mint', 'rugcheck_score']]
                        rugcheck_df = rugcheck_df.sort_index()
                    else:
                        rugcheck_df = pd.DataFrame(columns=['mint', 'rugcheck_score']).set_index(pd.DatetimeIndex([], tz='UTC'))

                    # --- Process Token Info (same as before) ---
                    token_info = {}
                    if token_info_records_raw:
                        for r in token_info_records_raw:
                            mint = r['mint']
                            creation_time = pd.to_datetime(r['token_creation_time'], errors='coerce', utc=True)
                            socials = pd.to_numeric(r['socials_score'], errors='coerce')
                            if pd.notna(creation_time):
                                token_info[mint] = {'creation_time': creation_time, 'socials_score': socials}

                    # --- Combine data per mint (same logic using pd.merge_asof) ---
                    logger.info("Processing and combining data per mint...")
                    required_final_cols = ['price', 'volume', 'market_cap_calculated', 'rugcheck_score', 'socials_score', 'token_creation_time']

                    grouped_trades = trades_df.groupby('mint') if 'mint' in trades_df.columns else {}
                    grouped_rugcheck = rugcheck_df.groupby('mint') if 'mint' in rugcheck_df.columns else {}

                    for mint in grouped_trades.groups:
                        mint_trades = grouped_trades.get_group(mint)[['price', 'volume', 'market_cap_calculated']]
                        mint_rugcheck = grouped_rugcheck.get_group(mint)[['rugcheck_score']] if mint in grouped_rugcheck.groups else None

                        combined_df = mint_trades.copy()
                        if mint_rugcheck is not None and not mint_rugcheck.empty:
                            combined_df = pd.merge_asof(
                                combined_df.sort_index(),
                                mint_rugcheck.sort_index(),
                                left_index=True,
                                right_index=True,
                                direction='backward',
                                tolerance=pd.Timedelta('1d')
                            )
                        else:
                            combined_df['rugcheck_score'] = np.nan

                        mint_info_data = token_info.get(mint)
                        if mint_info_data:
                            combined_df['token_creation_time'] = mint_info_data['creation_time']
                            combined_df['socials_score'] = mint_info_data['socials_score']
                        else:
                            logger.warning(f"Missing token info for {mint}. Using defaults.")
                            combined_df['token_creation_time'] = pd.NaT
                            combined_df['socials_score'] = 100

                        combined_df['rugcheck_score'] = combined_df['rugcheck_score'].ffill().bfill()
                        combined_df['socials_score'] = combined_df['socials_score'].ffill().bfill()
                        numeric_cols = ['price', 'volume', 'market_cap_calculated']
                        for col in numeric_cols:
                            combined_df[col] = combined_df[col].fillna(0.0)
                        combined_df['rugcheck_score'] = combined_df['rugcheck_score'].fillna(10000).astype(int)
                        combined_df['socials_score'] = combined_df['socials_score'].fillna(100).astype(int)

                        for r_col in required_final_cols:
                            if r_col not in combined_df.columns:
                                logger.warning(f"Column '{r_col}' missing for {mint}. Adding default.")
                                if r_col == 'token_creation_time': combined_df[r_col] = pd.NaT
                                elif r_col in ['rugcheck_score', 'socials_score']: combined_df[r_col] = 100
                                else: combined_df[r_col] = 0.0

                        final_df = combined_df[(combined_df.index >= start_date) & (combined_df.index < end_date)]

                        if not final_df.empty and all(col in final_df.columns for col in required_final_cols):
                            results_dict[mint] = final_df[required_final_cols].copy()
                        else:
                            logger.warning(f"No valid data remained for {mint} after processing. Skipping.")

                    logger.info(f"Finished processing data for {len(results_dict)} tokens.")

                # Catch InterfaceError specifically if it happens elsewhere
                except asyncpg.exceptions.InterfaceError as iface_err:
                    logger.error(f"InterfaceError during historical data processing: {iface_err}", exc_info=True)
                    # This indicates a potential issue with connection state management, might need pool reset/reconnect logic
                    return {} # Return empty on this specific error too
                except Exception as e:
                    # Log the original error class name for better debugging
                    logger.error(f"Error processing historical data ({type(e).__name__}): {e}", exc_info=True)
                    # Log the traceback from the original exception
                    # import traceback
                    # logger.error(traceback.format_exc()) # Optional full traceback
                    return {} # Return empty dict on error

            logger.info(f"Successfully fetched and processed historical data for {len(results_dict)} tokens.")
            return results_dict

# Helper function moved outside class for potential reuse (optional)
async def get_token_lifespan(db_client: DatabaseClient, mint: str) -> Optional[Dict[str, datetime]]:
    """
    Fetches the approximate start and end timestamp of a token's activity
    based on its first and last trade records in the v_trades view.

    Args:
        db_client: An initialized DatabaseClient instance.
        mint: The mint address of the token.

    Returns:
        A dictionary {'start_ts': datetime, 'end_ts': datetime} if trades exist,
        otherwise None. Timestamps are timezone-aware (UTC).
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
                # Add a small buffer to end time to ensure last trade is included <= end_ts
                end_ts += timedelta(seconds=1)
                return {'start_ts': start_ts, 'end_ts': end_ts}
            else:
                logger.warning(f"No trade timestamps found for mint {mint} to determine lifespan.")
                return None
        except Exception as e:
            logger.error(f"Error fetching token lifespan for {mint}: {e}", exc_info=True)
            return None
