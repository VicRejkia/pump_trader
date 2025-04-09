"""
Database module.
Handles PostgreSQL connections and CRUD operations.
"""

import os
import glob
from datetime import datetime, timezone,timedelta
import asyncio
import asyncpg
import aiofiles # <-- Add this import
import json # <-- Add this import
from dotenv import load_dotenv
from logger import logger
from config import TOTAL_SUPPLY

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
        from the 'sql' subfolder.
        """
        sql_folder = os.path.join(os.path.dirname(__file__), "sql")
        sql_files = sorted(glob.glob(os.path.join(sql_folder, "*.sql")))
        
        async with self.pool.acquire() as conn:
            for file_path in sql_files:
                try:
                    with open(file_path, "r") as f:
                        sql = f.read()
                    await conn.execute(sql)
                    logger.info("Executed SQL file: %s", os.path.basename(file_path))
                except Exception as e:
                    logger.exception("Error executing SQL file %s: %s", os.path.basename(file_path), e)
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

                    # 3. Insert/update token
                    await conn.execute("""
                        INSERT INTO tokens(mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, 
                            vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri, 
                            is_active, timestamp)
                        VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, True, NOW());
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
                        data.get('uri')
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
                            marketCapSol, market_cap_calculated, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
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
        """Fetches potential trading opportunities based on multiple criteria."""
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

    async def insert_portfolio_sell_record(self, mint: str, current_price: float, market_cap_sol: float, net_sol_received: float, tokens_sold: float, sell_fee: float, sell_tip: float, profit: float, reason: str, timestamp: datetime, settings: dict, conn=None):
        """Inserts a sell transaction record into the portfolio, including settings."""
        query = '''
            INSERT INTO portfolio
            (mint, tx_type, price, market_cap, sol_amount, tokens, fee, tip, profit, total_investment_sol,
             remaining_tokens, status, reason, timestamp, initial_tokens, stop_loss_price, highest_price, settings)
            VALUES ($1, 'sell', $2, $3, $4, $5, $6, $7, $8, 0, 0, 'closed', $9, $10, 0, 0, 0, $11)
        '''
        connection = conn or await self.pool.acquire()
        try:
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, net_sol_received, tokens_sold,
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

    async def insert_portfolio_buy_record(self, mint: str, current_price: float, market_cap_sol: float, sol_base_amount: float, total_sol_investment: float, tokens_bought: float, buy_fee: float, buy_tip: float, initial_stop_loss_price: float, initial_tp_price: float, second_tp_price: float, timestamp: datetime, settings: dict, conn=None):
        """Inserts a buy transaction record into the portfolio, including settings."""
        query = """
            INSERT INTO portfolio
                (mint, tx_type, price, market_cap, sol_amount, total_investment_sol, tokens,
                 fee, tip, remaining_tokens, stop_loss_price, highest_price,
                 initial_tp_price, second_tp_price, first_tp_hit,
                 status, timestamp, initial_tokens, settings)
            VALUES ($1, 'buy', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, FALSE, 'active', $14, $15, $16)
        """
        connection = conn or await self.pool.acquire()
        try:
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, sol_base_amount, total_sol_investment, tokens_bought,
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
                    ROW_NUMBER() OVER(PARTITION BY mint ORDER BY timestamp DESC) as rn
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

    async def get_filtered_tokens(self, max_socials=100, max_rugcheck=10000, min_volume_sol=0, time_window_minutes=60, portfolio_only=False): # Added portfolio_only
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
                AND COALESCE(rv.volume_sol, 0) >= $3
        """
        order_by_clause = "ORDER BY name, vt.mint;"
        params = [max_socials, max_rugcheck, min_volume_sol, interval_str]

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
                    COALESCE(SUM(sol_amount), 0) as volume_sol
                FROM v_trades
                WHERE timestamp >= (NOW() - $4::INTERVAL)
                GROUP BY mint
            )
            {select_clause}
            {from_clause}
            {where_clause}
            {order_by_clause}
        """

        async with self.pool.acquire() as conn:
            try:
                logger.debug(f"Fetching filtered tokens with params: max_socials={max_socials}, max_rugcheck={max_rugcheck}, min_volume_sol={min_volume_sol}, interval_str={interval_str}, portfolio_only={portfolio_only}")
                results = await conn.fetch(query, *params) # Use *params to unpack
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
        """Dumps the creator_wallets table to an SQL file."""
        backup_file_path = os.path.join(os.path.dirname(__file__), "data", "creator_wallets_backup.sql")
        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True) # Ensure data directory exists

        logger.info("Backing up creator_wallets table...")
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT wallet_address, token_count, last_token_time FROM creator_wallets")
                async with aiofiles.open(backup_file_path, "w") as f:
                    for row in rows:
                        wallet_address = row['wallet_address']
                        token_count = row['token_count']
                        # Format timestamp correctly for SQL, handle None
                        last_token_time_str = f"'{row['last_token_time'].isoformat()}'" if row['last_token_time'] else "NULL"

                        # Use INSERT OR IGNORE equivalent for PostgreSQL: ON CONFLICT DO NOTHING
                        sql_line = (
                            f"INSERT INTO creator_wallets (wallet_address, token_count, last_token_time) "
                            f"VALUES ('{wallet_address}', {token_count}, {last_token_time_str}) "
                            f"ON CONFLICT (wallet_address) DO NOTHING;\n"
                        )
                        await f.write(sql_line)
            logger.info(f"✅ Successfully backed up {len(rows)} creator wallets to {backup_file_path}")
        except Exception as e:
            logger.exception(f"Error backing up creator_wallets table: {e}")
            # Decide if we should raise or just log

    async def restore_creator_wallets(self):
        """Restores creator_wallets from the SQL backup file if it exists."""
        backup_file_path = os.path.join(os.path.dirname(__file__), "data", "creator_wallets_backup.sql")
        if not os.path.exists(backup_file_path):
            logger.info("No creator_wallets backup file found. Skipping restore.")
            return

        logger.info(f"Restoring creator_wallets table from {backup_file_path}...")
        try:
            async with aiofiles.open(backup_file_path, "r") as f:
                sql_script = await f.read()

            if not sql_script.strip():
                logger.info("Creator wallets backup file is empty. Skipping restore.")
                return

            async with self.pool.acquire() as conn:
                # Execute the entire script. The ON CONFLICT clause handles duplicates.
                await conn.execute(sql_script)
            logger.info("✅ Successfully restored creator wallets.")
        except Exception as e:
            logger.exception(f"Error restoring creator_wallets table: {e}")
            # Decide if we should raise or just log

    async def cleanup_db(self, cleanup_flag: bool):
        """Drop all application tables if cleanup_flag is True."""
        if cleanup_flag:
            logger.warning("🚨 Starting full database cleanup - Dropping all application tables...")
            async with self.pool.acquire() as conn:
                # List all known application tables (main and backup)
                # Add any other tables managed by the application if necessary (e.g., creator_wallets)
                tables_to_drop = [
                    'rugcheck',           # Depends on tokens
                    'trades',             # No explicit FK, but related to tokens
                    'migrations',         # Standalone or related? Assuming standalone for drop order
                    'tokens',             # Drop after dependents
                    'portfolio',          # Assuming this is a standalone table
                    'portfolio_backup',          # Assuming this is a standalone table
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
