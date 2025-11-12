"""
Database module.
Handles PostgreSQL connections and CRUD operations.
"""

import os
import io
import csv
import glob
from datetime import datetime, timezone,timedelta
import asyncio
import asyncpg
import aiofiles
import json
import pandas as pd
from dotenv import load_dotenv
from bot_logger import logger
from config.config import _TOTAL_SUPPLY
import config.config as base_config_module
from state_manager import GlobalState
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from utils import calculate_volatility
import inspect 
from typing import Optional
import statistics 
from decimal import Decimal

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

    def get_sync_connection_pool(self):
        """
        Creates and returns a synchronous connection pool for psycopg2.
        This version correctly parses the host and port.
        """
        from psycopg2.pool import SimpleConnectionPool
        import os

        if hasattr(self, '_sync_pool') and self._sync_pool:
            return self._sync_pool

        # --- START FIX ---
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_database = os.getenv("DB_DATABASE")
        db_host_raw = os.getenv("DB_HOST")

        db_host = db_host_raw
        db_port = None

        # Check if the host string contains a port and split it if it does
        if db_host_raw and ':' in db_host_raw:
            parts = db_host_raw.split(':')
            db_host = parts[0]
            db_port = parts[1]

        # Build the DSN string component by component
        dsn_parts = [
            f"dbname={db_database}",
            f"user={db_user}",
            f"password={db_password}",
            f"host={db_host}"
        ]
        if db_port:
            dsn_parts.append(f"port={db_port}")

        dsn = " ".join(dsn_parts)
        # --- END FIX ---
        
        self._sync_pool = SimpleConnectionPool(minconn=1, maxconn=5, dsn=dsn)
        return self._sync_pool

    async def connect(self):
        """Establish a connection pool to the PostgreSQL database."""
        try:
            # Use the DB_URL constructed from environment variables
            self.pool = await asyncpg.create_pool(dsn=DB_URL)
            logger.info(":handshake: Connected to the database successfully.")
        except Exception as e:
            logger.exception(":police_car_light: Errorconnecting to the database: %s", e)
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
                    logger.exception(":exclamation: Errorexecuting SQL file %s: %s", os.path.basename(file_path), e)
                    raise

    async def insert_sol_price(self, price: float, timestamp: datetime = datetime.now(timezone.utc)):
        """Insert a new SOL price into the database."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO sol_price_usd (price, timestamp) VALUES ($1, $2)", price, timestamp)
        except Exception as e:
            logger.exception(":exclamation: Errorinserting SOL price into the database: %s", e)
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

                    if token_count > self.config.get('MAX_TOKEN_COUNT_PER_CREATOR', 100):
                            logger.debug(f"🤬 [bold red]Suspicious creator[/bold red] %s for token %s with %s tokens. Skipping.", creator, data['mint'], token_count)
                            return False

                    sol_price = await self.state.get_sol_price()
                    if sol_price is None or sol_price <= 0:
                        logger.warning(f"⚠ Invalid SOL_PRICE ({sol_price}); skipping insert token operation.")
                        return False # Cannot proceed without valid SOL price
                    
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
                logger.exception(":exclamation: Errorinserting token data: %s", e)
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
            logger.error(f":police_car_light: Error on storing migration: {e}", exc_info=True)
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
                            signature, mint, trader_pubkey, tx_type, token_amount, sol_amount, price,
                            bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
                            marketCapSol,sol_price_usd, market_cap_calculated, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
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
                    logger.error(f":police_car_light: Error during batch trade insert: {e}", exc_info=True)
                    # The transaction will be rolled back automatically
                    raise # Re-raise the exception so the caller knows about the failure

    async def get_tokens_to_unsubscribe(self, mc_drop_threshold, inactivity_period, min_token_age):
        """Fetch tokens to unsubscribe based on market cap drop and inactivity."""
        query = """
            SELECT t.mint
            FROM tokens t
            LEFT JOIN (
                -- Subquery to find the very latest trade tick for each token
                SELECT mint, market_cap_sol, timestamp,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM v_unified_market_ticks_live
            ) latest ON t.mint = latest.mint AND latest.rn = 1
            WHERE
                -- Condition 1: The token must be older than the minimum age.
                t.timestamp <= NOW() - (INTERVAL '1 minute' * $3) -- $3 = min_token_age
                
                -- Condition 2: The token must not have an active position in the portfolio.
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
                
                -- Condition 3: The token must meet one of the "dead" criteria.
                AND (
                    -- Criteria A: The token HAS trades but is inactive or has crashed.
                    (
                        latest.mint IS NOT NULL AND (
                            -- Market cap has dropped below the threshold.
                            (latest.market_cap_sol * 100.0 / t.marketCapSol) < (100 - $1) -- $1 = mc_drop_threshold
                            OR
                            -- The last trade was longer ago than the inactivity period.
                            latest.timestamp <= NOW() - (INTERVAL '1 minute' * $2) -- $2 = inactivity_period
                        )
                    )
                    OR
                    -- Criteria B: The token has NO trades at all.
                    (latest.mint IS NULL)
                )
            ORDER BY t.timestamp DESC;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, mc_drop_threshold, inactivity_period, min_token_age)
        
    async def get_social_check_count(self, mint: str, conn=None) -> int:
        """Counts how many times a social check has been performed for a token."""
        query = "SELECT COUNT(*) FROM social_scores WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            count = await connection.fetchval(query, mint)
            return count if count is not None else 0
        finally:
            if not conn and connection:
                await self.pool.release(connection)

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
        
    async def get_total_supply(self, mint: str): #
        """Fetch the total supply of a token (RAW units) from rugcheck table.
           NOTE: For price calculations, use _get_latest_token_info which also gets decimals.
        """
        query = "SELECT token_supply FROM rugcheck WHERE mint = $1" #
        async with self.pool.acquire() as conn: #
            result = await conn.fetchrow(query, mint) #
            # Ensure _TOTAL_SUPPLY is fetched from self.config
            default_supply = self.config.get('_TOTAL_SUPPLY', 1_000_000_000) #
            return result['token_supply'] if result and result['token_supply'] is not None else default_supply #

    async def find_trading_opportunities(self, sol_price: float, volume_threshold: float, marketcap_threshold: float, rugcheck_threshold: int, social_score_threshold: int, time_interval_minutes: int, min_volatility: float): 
        """
        [MODIFIED] Identifies potential token buy opportunities, ensuring only the latest rugcheck score is used.
        - Volume Calculation is source-aware:
            - PUMP: SUMs all individual trade sol_amounts.
            - DEXSCREENER: Takes only the SINGLE LATEST volume snapshot to prevent duplicate counting.
        - Volatility is calculated ONLY from high-frequency PUMP trades for accuracy.
        """
        
        query = """
            WITH LatestTickData AS (
                -- This correctly gets the latest price/MC from either source
                SELECT
                    mint,
                    price_sol,
                    market_cap_sol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                FROM v_unified_market_ticks_live -- Uses LIVE view, which is correct
                WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
            ),
            -- START OF FIX: Add a CTE to get only the latest rugcheck score per mint
            LatestRugcheck AS (
                SELECT
                    mint,
                    score,
                    tokenMeta_name,
                    tokenMeta_symbol,
                    ROW_NUMBER() OVER(PARTITION BY mint ORDER BY last_checked DESC) as rn
                FROM rugcheck
            ),
            -- END OF FIX
            RecentMetrics AS (
                -- THIS CTE IS NOW SOURCE-AWARE TO PREVENT DOUBLE-COUNTING VOLUME
                SELECT
                    mint,
                    SUM(calculated_volume) AS volume_recent_sol
                FROM (
                    -- 1. Sum up all individual Pump.fun trades from the 'trades' table
                    SELECT
                        mint,
                        sol_amount AS calculated_volume
                    FROM trades -- Use base table for PUMP data
                    WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval

                    UNION ALL

                    -- 2. Get only the LATEST 5-minute volume for migrated tokens
                    SELECT
                        mint_address AS mint,
                        (volume_m5 / sol_price_usd) AS calculated_volume
                    FROM (
                        SELECT
                            mint_address,
                            volume_m5,
                            sol_price_usd,
                            ROW_NUMBER() OVER(PARTITION BY mint_address ORDER BY timestamp DESC) as rn
                        FROM dexscreener_data -- Use base table for DEXSCREENER data
                        WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
                          AND sol_price_usd > 0 -- Avoid division by zero
                    ) AS ranked_dex
                    WHERE rn = 1
                ) AS combined_volume_sources
                GROUP BY mint
            ),
            VolatilityData AS (
                -- THIS CTE IS NOW MODIFIED TO ONLY USE PUMP.FUN TRADES FOR RELIABLE CALCULATION
                SELECT
                    mint,
                    -- The volatility formula remains the same
                    STDDEV(log_return) * SQRT(GREATEST(COUNT(*), 1)) AS volatility
                FROM (
                    SELECT
                        mint,
                        -- Use price_sol from the unified view
                        LN(price_sol / LAG(price_sol) OVER (PARTITION BY mint ORDER BY timestamp)) AS log_return
                    -- <<< CHANGE: Use 'v_unified_market_ticks_historical' view instead of 'trades'
                    FROM v_unified_market_ticks_live
                    WHERE timestamp >= NOW() - ($6::text || ' minutes')::interval
                      -- <<< CHANGE: Use 'price_sol' column from the view
                      AND price_sol > 0
                ) sub
                WHERE log_return IS NOT NULL
                    AND log_return > '-Infinity'::double precision
                    AND log_return < 'Infinity'::double precision
                GROUP BY mint
                HAVING COUNT(*) > 5
            )
            SELECT
                t.mint, ltd.price_sol AS latest_price, ltd.market_cap_sol AS latest_market_cap_sol,
                COALESCE(rm.volume_recent_sol, 0) AS volume_in_interval,
                COALESCE(vd.volatility, 0) AS volatility_in_interval,
                lrc.tokenMeta_name AS name, lrc.tokenMeta_symbol AS symbol, -- FIX: Use new CTE alias
                lrc.score AS rugcheck_score, t.socials_score -- FIX: Use new CTE alias
            FROM tokens AS t
            -- FIX: Join with the new LatestRugcheck CTE instead of the raw table
            INNER JOIN LatestRugcheck AS lrc ON t.mint = lrc.mint AND lrc.rn = 1
            INNER JOIN LatestTickData AS ltd ON t.mint = ltd.mint AND ltd.rn = 1
            LEFT JOIN RecentMetrics AS rm ON t.mint = rm.mint
            LEFT JOIN VolatilityData AS vd ON t.mint = vd.mint
            WHERE
                t.is_active = TRUE AND
                lrc.score IS NOT NULL AND lrc.score <= $4 AND -- FIX: Use new CTE alias
                t.socials_score IS NOT NULL AND t.socials_score <= $5 AND
                (COALESCE(rm.volume_recent_sol, 0) * $1) >= $2 AND
                (ltd.market_cap_sol * $1) >= $3 AND
                COALESCE(vd.volatility, 0) >= $7 AND
                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') AND
                (t.cooldown_until IS NULL OR t.cooldown_until < NOW())
            ORDER BY rm.volume_recent_sol DESC;
        """
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch(query, sol_price, volume_threshold, marketcap_threshold, rugcheck_threshold, social_score_threshold, str(time_interval_minutes), min_volatility)
            except Exception as e:
                logger.error(f":police_car_light: Error finding trading opportunities: {e}", exc_info=True)
                return []

    async def get_active_buy_positions(self, conn=None):
        """Fetches active buy positions from the portfolio."""
        query = '''
            SELECT p.id, p.mint, p.price AS buy_price, p.initial_tokens, p.remaining_tokens, p.total_investment_sol,
                p.stop_loss_price, p.highest_price, p.initial_tp_price, p.second_tp_price, p.first_tp_hit,
                t.marketCapSol as initial_market_cap_sol, t.data_source,
                p.timestamp, p.volume_stale_since
            FROM portfolio p
            JOIN tokens t ON p.mint = t.mint
            WHERE p.status = 'active' AND p.tx_type = 'buy'
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
                    price_sol AS price,
                    market_cap_sol AS marketCapSol,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) as rn
                FROM v_unified_market_ticks_live
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

    async def get_primary_dex_id_for_migrated_token(self, mint: str, conn=None) -> str | None:
        """
        Fetches the dexId of the highest-liquidity pair for a migrated token
        from the most recent dexscreener_data entry.
        """
        query = """
            SELECT full_response
            FROM dexscreener_data
            WHERE mint_address = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            latest_record = await connection.fetchrow(query, mint)
            if latest_record and latest_record['full_response']:
                try:
                    # The full_response is stored as a JSON string, so we load it
                    pair_data = json.loads(latest_record['full_response'])
                    dex_id = pair_data.get('dexId')
                    if dex_id:
                        logger.debug(f"Found primary dexId '{dex_id}' for migrated token {mint}.")
                        return dex_id
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse dexId from full_response for {mint}: {e}")
            return None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    # --- NEW METHODS for AI Integration ---

    # async def insert_ai_decision(self, mint: str, context: str, decision: str, confidence: int, explanation: Optional[str] = None, data_snapshot: Optional[dict] = None, prompt_hash: Optional[str] = None, conn=None):
    #     """Inserts a new AI decision record."""
    #     query = """
    #         INSERT INTO ai_decisions
    #         (mint, decision_context, decision, confidence, explanation, data_snapshot, prompt_hash)
    #         VALUES ($1, $2, $3, $4, $5, $6, $7)
    #     """
    #     connection = conn or await self.pool.acquire()
    #     try:
    #         # Convert data_snapshot dict to JSON string if provided
    #         data_snapshot_json = json.dumps(data_snapshot, default=str) if data_snapshot else None
    #         await connection.execute(query, mint, context, decision, confidence, explanation, data_snapshot_json, prompt_hash)
    #         logger.debug(f"Stored AI decision for {mint}: {decision} ({confidence}%)")
    #     except Exception as e:
    #         logger.error(f":police_car_light: Error inserting AI decision for {mint}: {e}", exc_info=True)
    #         if not conn: raise # Re-raise if we acquired the connection here
    #     finally:
    #         if not conn and connection:
    #             await self.pool.release(connection)

    async def update_token_ai_eval_timestamp(self, mint: str, timestamp: datetime, conn=None):
        """Updates the ai_last_evaluation_ts for a token."""
        query = "UPDATE tokens SET ai_last_evaluation_ts = $1 WHERE mint = $2"
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, timestamp, mint)
        except Exception as e:
            logger.error(f":police_car_light: Error updating AI eval timestamp for {mint}: {e}", exc_info=True)
            if not conn: raise
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_latest_ai_decision(self, mint: str, conn=None) -> Optional[asyncpg.Record]:
        """Fetches the most recent AI decision record for a given mint."""
        query = """
            SELECT decision, confidence, evaluation_timestamp
            FROM ai_decision_memory
            WHERE mint = $1
                AND decision_context IN ('INITIAL BUY', 'SELL/HOLD', 'REBUY') -- Only get actionable contexts
            ORDER BY evaluation_timestamp DESC
            LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetchrow(query, mint)
        except Exception as e:
            logger.error(f":police_car_light: Error fetching latest AI decision for {mint}: {e}", exc_info=True)
            return None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_tokens_for_outcome_analysis(self, lookback_hours: int, conn=None) -> List[asyncpg.Record]:
        """
        Fetches tokens that the AI has evaluated but the bot does not own,
        and which have not had an "outcome" logged yet.
        """
        query = """
            WITH LastDecision AS (
                -- 1. Find the *last* decision the AI made for each mint
                SELECT
                    mint,
                    decision,
                    evaluation_timestamp,
                    metadata,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY evaluation_timestamp DESC) as rn
                FROM
                    ai_decision_memory
                WHERE
                    -- Only look at decisions that were NOT buys
                    decision != 'BUY' 
                    AND evaluation_timestamp >= NOW() - ($1 || ' hours')::interval
            ),
            LastOutcome AS (
                -- 2. Find the last *outcome* we logged for each mint
                SELECT
                    mint,
                    evaluation_timestamp AS last_outcome_ts
                FROM
                    ai_decision_memory
                WHERE
                    decision_context = 'NON_TRADE_OUTCOME'
            )
            -- 3. Return tokens that meet the criteria
            SELECT
                ld.mint,
                ld.decision,
                ld.evaluation_timestamp,
                ld.metadata
            FROM
                LastDecision ld
            WHERE
                ld.rn = 1 -- It's the most recent decision
                -- 4. And is not in the active portfolio
                AND ld.mint NOT IN (SELECT p.mint FROM portfolio p WHERE p.status = 'active')
                -- 5. And we have *never* logged an outcome for it, OR
                --    the last decision is *newer* than the last outcome we logged
                AND (
                    ld.mint NOT IN (SELECT lo.mint FROM LastOutcome lo)
                    OR
                    ld.evaluation_timestamp > (SELECT lo.last_outcome_ts FROM LastOutcome lo WHERE lo.mint = ld.mint ORDER BY lo.last_outcome_ts DESC LIMIT 1)
                );
        """
        connection = conn or await self.pool.acquire()
        try:
            return await connection.fetch(query, str(lookback_hours))
        except Exception as e:
            logger.error(f":police_car_light: Error fetching tokens for outcome analysis: {e}", exc_info=True)
            return []
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def get_active_portfolio_for_ai_eval(self, staleness_minutes: int, conn=None):
        """Fetches active portfolio mints needing AI evaluation."""
        query = """
            SELECT p.mint
            FROM portfolio p JOIN tokens t ON p.mint = t.mint
            WHERE p.status = 'active' AND p.tx_type = 'buy'
              AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($1 || ' minutes')::interval);
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
            if not conn and connection: await self.pool.release(connection)

    async def get_top_pump_momentum_for_ai_eval(self, top_n: int, window_minutes: int, staleness_minutes: int, conn=None):
        """Fetches top N PUMP tokens by recent volume needing AI eval."""
        query = f"""
            SELECT
                t.mint,
                SUM(td.sol_amount) AS recent_pump_volume
            FROM
                tokens t JOIN trades td ON t.mint = td.mint
            WHERE
                td.timestamp >= NOW() - ($2 || ' minutes')::interval
                AND t.data_source = 'PUMP'
                AND t.is_active = TRUE
                AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') -- Exclude held tokens
                AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($3 || ' minutes')::interval)
            GROUP BY t.mint
            ORDER BY recent_pump_volume DESC
            LIMIT $1;
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, top_n, str(window_minutes), str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
            if not conn and connection: await self.pool.release(connection)

    async def get_top_dex_momentum_for_ai_eval(self, top_n: int, window_minutes: int, staleness_minutes: int, conn=None):
        """Fetches top N DEX tokens by latest volume needing AI eval."""
        query = f"""
            WITH RankedDexVolume AS (
                SELECT
                    dsd.mint_address,
                    dsd.volume_m5,
                    t.ai_last_evaluation_ts,
                    ROW_NUMBER() OVER (PARTITION BY dsd.mint_address ORDER BY dsd.timestamp DESC) as rn
                FROM
                    dexscreener_data dsd JOIN tokens t ON dsd.mint_address = t.mint
                WHERE
                    dsd.timestamp >= NOW() - ($2 || ' minutes')::interval -- Ensure snapshot is recent
                    AND t.data_source = 'DEXSCREENER'
                    AND t.is_active = TRUE
                    AND t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active') -- Exclude held tokens
                    AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($3 || ' minutes')::interval)
            )
            SELECT
                mint_address AS mint,
                volume_m5 AS latest_dex_volume_m5
            FROM
                RankedDexVolume
            WHERE
                rn = 1
            ORDER BY
                latest_dex_volume_m5 DESC NULLS LAST
            LIMIT $1;
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, top_n, str(window_minutes), str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
             if not conn and connection: await self.pool.release(connection)

    async def get_tokens_with_recent_events_for_ai_eval(self, rug_change_threshold: int, social_change_threshold: int, staleness_minutes: int, conn=None):
        """Fetches tokens with significant score changes or migration needing AI eval."""
        # This query is complex. It finds tokens that migrated recently OR had significant score changes.
        query = f"""
            WITH RecentScoreChanges AS (
                -- Find latest and previous Rugcheck scores
                SELECT mint, score, last_checked,
                       LAG(score) OVER (PARTITION BY mint ORDER BY last_checked) as prev_score
                FROM v_rugcheck
                WHERE last_checked >= NOW() - INTERVAL '1 hour' -- Look at recent score history
            ),
            SignificantRugChange AS (
                SELECT DISTINCT mint
                FROM RecentScoreChanges
                WHERE ABS(score - prev_score) >= $1
            ),
            RecentSocialChanges AS (
                -- Find latest and previous Social scores
                SELECT mint, score_value, timestamp,
                       LAG(score_value) OVER (PARTITION BY mint ORDER BY timestamp) as prev_score
                FROM v_social_scores
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            ),
            SignificantSocialChange AS (
                SELECT DISTINCT mint
                FROM RecentSocialChanges
                WHERE ABS(score_value - prev_score) >= $2
            ),
            RecentMigrations AS (
                SELECT DISTINCT mint
                FROM v_migrations
                WHERE txType = 'migrate' AND timestamp >= NOW() - INTERVAL '1 hour'
            )
            -- Combine tokens with events and filter by staleness
            SELECT t.mint
            FROM tokens t
            WHERE t.is_active = TRUE
              AND (t.mint IN (SELECT mint FROM SignificantRugChange) OR
                   t.mint IN (SELECT mint FROM SignificantSocialChange) OR
                   t.mint IN (SELECT mint FROM RecentMigrations))
              AND (t.ai_last_evaluation_ts IS NULL OR t.ai_last_evaluation_ts < NOW() - ($3 || ' minutes')::interval);
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, rug_change_threshold, social_change_threshold, str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
             if not conn and connection: await self.pool.release(connection)

    async def get_stale_tokens_for_ai_eval(self, batch_size: int, staleness_minutes: int, conn=None):
        """Fetches the oldest evaluated active tokens needing AI refresh."""
        query = f"""
            SELECT mint
            FROM tokens
            WHERE is_active = TRUE
              AND (ai_last_evaluation_ts IS NULL OR ai_last_evaluation_ts < NOW() - ($2 || ' minutes')::interval)
            ORDER BY ai_last_evaluation_ts ASC NULLS FIRST -- Oldest first
            LIMIT $1;
        """
        connection = conn or await self.pool.acquire()
        try:
            rows = await connection.fetch(query, batch_size, str(staleness_minutes))
            return [row['mint'] for row in rows]
        finally:
             if not conn and connection: await self.pool.release(connection)

    # --- (End of new methods) ---

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

    async def insert_portfolio_sell_record(self, mint: str, current_price: float, market_cap_sol: float, net_sol_received: float, sol_price_usd: float, tokens_sold: float, sell_fee: float, sell_tip: float, profit: float, reason: str, timestamp: datetime, settings: dict, ai_context: Optional[dict] = None, conn=None):
        """Inserts a sell transaction record into the portfolio, including settings."""
        query = '''
            INSERT INTO portfolio
            (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, tokens, fee, tip, profit, total_investment_sol,
             remaining_tokens, status, reason, timestamp, initial_tokens, stop_loss_price, highest_price, settings)
            VALUES ($1, 'sell', $2, $3, $4, $5, $6, $7, $8, $9, 0, 0, 'closed', $10, $11, 0, 0, 0, $12)
        '''
        connection = conn or await self.pool.acquire()
        try:
            if ai_context:
                settings['ai_advice_at_sell'] = ai_context # Add AI info
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

    async def insert_portfolio_buy_record(self, mint: str, current_price: float, market_cap_sol: float, sol_base_amount: float, sol_price_usd: float, total_sol_investment: float, tokens_bought: float, buy_fee: float, buy_tip: float, initial_stop_loss_price: float, initial_tp_price: float, second_tp_price: float, timestamp: datetime, settings: dict, buy_reason: str, ai_context: Optional[dict] = None, conn=None): # <<< 1. ADD buy_reason: str
        """Inserts a buy transaction record into the portfolio, including settings."""
        query = """
            INSERT INTO portfolio
                (mint, tx_type, price, market_cap, sol_amount, sol_price_usd, total_investment_sol, tokens,
                 fee, tip, remaining_tokens, stop_loss_price, highest_price,
                 initial_tp_price, second_tp_price, first_tp_hit,
                 status, timestamp, initial_tokens, settings, buy_reason) -- <<< 2. ADD buy_reason
            VALUES ($1, 'buy', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, FALSE, 'active', $15, $16, $17, $18) -- <<< 3. ADD $18
        """
        connection = conn or await self.pool.acquire()
        try:
            if ai_context:
                settings['ai_advice_at_buy'] = ai_context
            settings_json = json.dumps(settings) # Convert dict to JSON string
            await connection.execute(query, mint, current_price, market_cap_sol, sol_base_amount, sol_price_usd, total_sol_investment, tokens_bought,
                                   buy_fee, buy_tip, tokens_bought, # remaining_tokens = initial_tokens
                                   initial_stop_loss_price, current_price, # highest_price = current_price
                                   initial_tp_price, second_tp_price,
                                   timestamp, tokens_bought, # initial_tokens
                                   settings_json, buy_reason) # <<< 4. PASS buy_reason
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
        query = "SELECT timestamp FROM v_unified_market_ticks_live WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1"
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
            SELECT mint, price_sol as price, timestamp
            FROM v_unified_market_ticks_historical -- CORRECT: Uses HISTORICAL view
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
                logger.error(f":police_car_light: Error fetching trade history for mints {mints}: {e}", exc_info=True)
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
                logger.error(f":police_car_light: Error fetching unique mints with names: {e}", exc_info=True)
                return []
            
    async def get_all_migrated_tokens(self) -> List[str]:
        """Fetches all active tokens that have been marked as migrated to DEXScreener."""
        query = "SELECT mint FROM tokens WHERE data_source = 'DEXSCREENER' AND is_active = TRUE ORDER BY timestamp DESC"
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [row['mint'] for row in rows]
        except Exception as e:
            logger.error(f":police_car_light: Error fetching migrated tokens: {e}", exc_info=True)
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
                logger.error(f":police_car_light: Error fetching filtered tokens: {e}", exc_info=True)
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
                logger.error(f":police_car_light: Error fetching portfolio transactions for mints {mints}: {e}", exc_info=True)
                return {} # Return empty dict on error
            
    # In class DatabaseClient:

    async def get_creator_history_summary(self, creator_wallet: str, current_mint: str) -> Tuple[str, dict]:
        """
        [REFACTORED]
        Analyzes a creator's past tokens and generates a summary string AND
        a structured metadata dictionary for the AI.
        """
        if not creator_wallet:
            return "Creator wallet not specified.", {}

        query = """
        WITH PastTokens AS (
            SELECT
                t.mint,
                t.marketCapSol AS creation_mcap,
                (SELECT MAX(tr.marketCapSol) FROM v_trades tr WHERE tr.mint = t.mint) AS max_mcap,
                ( (SELECT MAX(tr.timestamp) FROM v_trades tr WHERE tr.mint = t.mint) -
                  (SELECT MIN(tr.timestamp) FROM v_trades tr WHERE tr.mint = t.mint) ) AS lifespan,
                tb.backup_reason
            FROM v_tokens t
            LEFT JOIN tokens_backup tb ON t.mint = tb.mint
            WHERE t.traderPublicKey = $1 AND t.mint != $2
        )
        SELECT * FROM PastTokens WHERE max_mcap IS NOT NULL OR backup_reason IS NOT NULL;
        """
        
        summary_dict = {
            "creator_total_launches": 0,
            "creator_rug_count": 0,
            "creator_rug_rate": 0.0,
            "creator_good_runs_count": 0,
            "creator_avg_lifespan_minutes": 0.0
        }

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, creator_wallet, current_mint)

            if not rows:
                return "This is the creator's first token.", summary_dict

            total_tokens = len(rows)
            rugged_count = 0
            good_runs_count = 0
            total_lifespan_minutes = 0
            lifespan_count = 0

            # Define "rugged"
            rug_reasons = {'high_rugcheckscore', 'dead_token'}

            for row in rows:
                if row['backup_reason'] in rug_reasons:
                    rugged_count += 1
                
                # Define "good run" (e.g., > 10x MCap from creation)
                if row['max_mcap'] and row['creation_mcap'] and row['max_mcap'] > (row['creation_mcap'] * 10):
                    good_runs_count += 1
                
                if row['lifespan']:
                    total_lifespan_minutes += row['lifespan'].total_seconds() / 60
                    lifespan_count += 1

            avg_lifespan_str = "N/A"
            avg_lifespan_minutes_val = 0.0
            if lifespan_count > 0:
                avg_lifespan_minutes_val = total_lifespan_minutes / lifespan_count
                if avg_lifespan_minutes_val < 120:
                    avg_lifespan_str = f"{avg_lifespan_minutes_val:.0f} minutes"
                else:
                    avg_lifespan_str = f"{avg_lifespan_minutes_val / 60:.1f} hours"

            summary_string = (
                f"Creator has {total_tokens} past tokens. "
                f"{rugged_count} were rugged. "
                f"{good_runs_count} achieved >10x MCap. "
                f"Average lifespan: {avg_lifespan_str}."
            )
            
            summary_dict = {
                "creator_total_launches": total_tokens,
                "creator_rug_count": rugged_count,
                "creator_rug_rate": (rugged_count / total_tokens) if total_tokens > 0 else 0.0,
                "creator_good_runs_count": good_runs_count,
                "creator_avg_lifespan_minutes": avg_lifespan_minutes_val
            }
            
            return summary_string, summary_dict

        except Exception as e:
            logger.error(f"Error generating creator history summary for {creator_wallet}: {e}", exc_info=True)
            return "Error generating creator history.", summary_dict

    async def backup_and_delete_token(self, mint: str, archived_at: datetime, reason: str=None):
        """Backup core table data to a corresponding backup table."""

        # --- START: ADD THIS SAFETY CHECK BLOCK ---
        try:
            async with self.pool.acquire() as conn:
                is_active_in_portfolio = await conn.fetchval(
                    "SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' LIMIT 1",
                    mint
                )
                if is_active_in_portfolio:
                    logger.critical(
                        f"CRITICAL SAFEGUARD: Prevented backup/deletion of token {mint} because it has an ACTIVE position in the portfolio. Reason for attempted deletion: '{reason}'."
                    )
                    # Deactivate the token in the 'tokens' table so it's not picked up by other processes,
                    # but DO NOT delete it, allowing the sell logic to continue managing the position.
                    await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                    return # Exit the function immediately.
        except Exception as e:
            logger.error(f":police_car_light: Error during safety check in backup_and_delete_token for {mint}: {e}", exc_info=True)
            return # Exit on error to be safe
        # --- END: ADD THIS SAFETY CHECK BLOCK ---
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

                        await conn.execute('''
                            INSERT INTO social_scores_backup (id, mint, timestamp, score_type, score_value, details, backup_timestamp)
                            SELECT id, mint, timestamp, score_type, score_value, details, NOW() FROM social_scores WHERE mint = $1
                        ''', mint)
 
                        # Backup migrations, ignoring conflicts on the primary key
                        await conn.execute('''
                            INSERT INTO migrations_backup SELECT *, NOW() FROM migrations WHERE mint = $1
                            ON CONFLICT (signature) DO NOTHING -- Conflict check on signature
                        ''', mint)

                        await conn.execute('''
                            INSERT INTO dexscreener_data_backup SELECT *, NOW() FROM dexscreener_data WHERE mint_address = $1
                        ''', mint)
 
                        await conn.execute("DELETE FROM tokens WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM trades WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM rugcheck WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM social_scores WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM migrations WHERE mint = $1", mint)
                        await conn.execute("DELETE FROM dexscreener_data WHERE mint_address = $1", mint)
 
                        logger.debug(f"🧹 Backup & deletion completed for {mint}")
 
                    except Exception as e:
                        logger.error(f"❌ Backup failed for {mint}: {e}", exc_info=True)
                        raise
        except Exception as e:
            logger.error(f":police_car_light: backup_and_delete_token: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def backup_creator_wallets(self):
        """Dumps the creator_wallets table to a JSON file."""
        backup_file_path = os.path.join(os.path.dirname(__file__), self.config.get("_BACKUP_STORAGE_PATH", "backups"), "creator_wallets_backup.json")
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
            logger.exception(f":police_car_light: Error backing up creator_wallets table: {e}")
            # Decide if we should raise or just log


    async def restore_creator_wallets(self):
        backup_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            self.config.get("_BACKUP_STORAGE_PATH", "backups"), 
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
            logger.exception(":police_car_light: Error loading backup data: %s", e)
            raise

    # --- START: Refactored Price Calculation Logic ---
    async def _get_raw_trades_for_window(self, mint: str, window_minutes: float, conn) -> List[Dict[str, Any]]:
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
    
    async def _get_latest_token_info(self, mint: str, conn) -> Dict[str, Optional[float]]:
        """
        Fetches the latest token_supply and token_decimals for a mint.
        It queries rugcheck and rugcheck_backup directly as v_rugcheck might not have token_decimals.
        """
        query = """
            SELECT
                token_supply,
                token_decimals
            FROM (
                SELECT
                    token_supply,
                    token_decimals,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY COALESCE(last_checked, '1970-01-01'::timestamptz) DESC) as rn
                FROM (
                    SELECT mint, token_supply, token_decimals, last_checked FROM rugcheck WHERE mint = $1
                    UNION ALL
                    SELECT mint, token_supply, token_decimals, last_checked FROM rugcheck_backup WHERE mint = $1
                ) combined_rugcheck_data
                WHERE token_supply IS NOT NULL AND token_supply > 0
                  AND token_decimals IS NOT NULL AND token_decimals >= 0
            ) ranked_supply_info
            WHERE rn = 1;
        """
        record = await conn.fetchrow(query, mint)
        if record:
            return {'token_supply': float(record['token_supply']), 'token_decimals': int(record['token_decimals'])}
        else:
            logger.warning(f"No token_supply/decimals found in rugcheck/rugcheck_backup for {mint}. Using default supply from config.")
            # Using _TOTAL_SUPPLY and assuming default decimals (e.g., 9, or make it configurable)
            # For this example, let's assume a common default like 6 if not found, or make it part of config
            default_decimals = self.config.get('_DEFAULT_DECIMALS_FOR_MISSING', 6) # Add to config if needed
            return {'token_supply': float(self.config.get('_TOTAL_SUPPLY', 1_000_000_000)), 'token_decimals': default_decimals}


    # --- START: MODIFIED/NEW Price Calculation Helper Logic ---

    async def _get_raw_trades_for_price_calc(self, mint: str, config_params: dict, conn) -> List[Dict[str, Any]]:
        """
        Fetches raw trades (timestamp, sol_amount, token_amount) for a given window,
        supporting both time-based and count-based windows.
        """
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        # Common base of the query selecting necessary columns and initial filters
        query_select_cols = "SELECT timestamp, sol_amount, token_amount, price_sol"
        query_from_where = """
            FROM v_unified_market_ticks_live -- <<< CHANGE TO LIVE VIEW
            WHERE mint = $1
            AND sol_amount IS NOT NULL AND sol_amount > 0 
            AND token_amount IS NOT NULL AND token_amount > 0
        """
        params = [mint]
        final_query: str

        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            # For time window, order by timestamp ascending directly
            final_query = query_select_cols + query_from_where + f" AND timestamp >= NOW() - ($2::text || ' minutes')::interval ORDER BY timestamp ASC;"
            params.append(window_minutes)
        elif window_type == "count":
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            # For count window:
            # 1. Subquery selects the latest N trades.
            # 2. Outer query orders these N trades by timestamp ascending.
            final_query = f"""
                SELECT timestamp, sol_amount, token_amount, price_sol
                FROM (
                    {query_select_cols}
                    {query_from_where} 
                    ORDER BY timestamp DESC
                    LIMIT $2 
                ) AS latest_n_trades
                ORDER BY timestamp ASC;
            """
            # Parameter $1 is mint, $2 is trade_count
            params.append(trade_count)
        else:
            logger.warning(f"Unknown PRICE_WINDOW_TYPE: {window_type}. Defaulting to time window of 1 min.")
            final_query = query_select_cols + query_from_where + " AND timestamp >= NOW() - INTERVAL '1 minute' ORDER BY timestamp ASC;"
        
        return await conn.fetch(final_query, *params)

    async def _get_raw_marketcaps_for_calc(self, mint: str, config_params: dict, conn) -> List[Dict[str, Any]]:
        """
        Fetches raw marketCapSol values from trades for a given window,
        supporting both time-based and count-based windows.
        """
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        query_select_cols = "SELECT timestamp, market_cap_sol"
        query_from_where = """
            FROM v_unified_market_ticks_live -- <<< CHANGE TO LIVE VIEW
            WHERE mint = $1
            AND market_cap_sol IS NOT NULL AND market_cap_sol > 0
        """
        params = [mint]
        final_query: str

        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            final_query = query_select_cols + query_from_where + f" AND timestamp >= NOW() - ($2::text || ' minutes')::interval ORDER BY timestamp ASC;"
            params.append(window_minutes)
        elif window_type == "count":
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            final_query = f"""
                SELECT *
                FROM (
                    {query_select_cols}
                    {query_from_where}
                    ORDER BY timestamp DESC
                    LIMIT $2
                ) AS latest_n_marketcaps
                ORDER BY timestamp ASC;
            """
            params.append(trade_count)
        else:
            logger.warning(f"Unknown PRICE_WINDOW_TYPE: {window_type}. Defaulting to time window of 1 min for MC calc.")
            final_query = query_select_cols + query_from_where + " AND timestamp >= NOW() - INTERVAL '1 minute' ORDER BY timestamp ASC;"
                
        return await conn.fetch(final_query, *params)

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
    
    def _apply_iqr_to_values(self, values: List[float]) -> List[float]: #
        if not values or len(values) < 4: #
            return values #

        try:
            q1 = np.percentile(values, 25) #
            q3 = np.percentile(values, 75) #
            iqr_val = q3 - q1 #
            
            if iqr_val == 0: #
                return values #

            lower_bound = q1 - 1.5 * iqr_val #
            upper_bound = q3 + 1.5 * iqr_val #
            inliers = [v for v in values if lower_bound <= v <= upper_bound] #
            
            if not inliers: #
                logger.warning("IQR filtering removed all values. Returning original values as fallback.") #
                return values #
            return inliers #
        except Exception as e:
            logger.error(f":police_car_light: Error during IQR calculation for values: {e}. Returning original values.", exc_info=True) #
            return values #

    async def _calculate_median_price_with_iqr(self, mint: str, config_params: dict, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades: #
            all_prices = [float(r['sol_amount'])/float(r['token_amount']) for r in trade_records if r.get('token_amount') and float(r['token_amount']) > 0 and r.get('sol_amount') is not None] #
            if all_prices: #
                 logger.warning(f"All prices for {mint} filtered by IQR. Falling back to unfiltered median for price calc.") #
                 return statistics.median(all_prices) #
            return None #

        inlier_prices = [float(trade['price']) for trade in inlier_trades] #
        return statistics.median(inlier_prices) if inlier_prices else None #

    async def _calculate_vwap_price_with_iqr(self, mint: str, config_params: dict, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades: #
            # Could add fallback to unfiltered VWAP here if desired
            logger.warning(f"No inlier trades for {mint} after IQR for VWAP calculation.") #
            return None #

        total_sol_inliers = sum(float(trade['sol_amount']) for trade in inlier_trades) #
        total_tokens_inliers = sum(float(trade['token_amount']) for trade in inlier_trades) #

        if total_tokens_inliers == 0: #
            return None #
        return total_sol_inliers / total_tokens_inliers #

    async def _calculate_twap_price_with_iqr(self, mint: str, config_params: dict, interval_seconds: int, conn) -> float | None: #
        trade_records = await self._get_raw_trades_for_price_calc(mint, config_params, conn) # # Uses new helper
        if not trade_records: #
            return None #

        inlier_trades_with_price = self._apply_iqr_to_trades(trade_records) #
        if not inlier_trades_with_price: #
            return None #

        df_data = [{'timestamp': pd.to_datetime(trade['timestamp'], utc=True), 'price': float(trade['price'])} for trade in inlier_trades_with_price] #
        df = pd.DataFrame(df_data) #
        if df.empty: return None #
        df = df.set_index('timestamp') #
        
        interval_prices = df['price'].resample(f'{interval_seconds}S').median(numeric_only=True) #
        valid_interval_prices = interval_prices.dropna() #
        if valid_interval_prices.empty: return None #
        
        twap = valid_interval_prices.mean() #
        return float(twap) if pd.notnull(twap) else None #

    # New helper for robust median market cap
    async def _calculate_median_marketcap_with_iqr(self, mint: str, config_params: dict, conn) -> float | None:
        trade_records_for_mc = await self._get_raw_marketcaps_for_calc(mint, config_params, conn)
        # logger.debug(f"Fetched {len(trade_records_for_mc)} market cap records for {mint}.")
        # logger.debug(f"First 5 records: {trade_records_for_mc[:5]}") # Debugging output)
        if not trade_records_for_mc:
            logger.debug(f"No market cap records found for {mint}. Cannot calculate median market cap.")
            return None

        market_caps = [float(r['market_cap_sol']) for r in trade_records_for_mc if r.get('market_cap_sol') is not None] #
        if not market_caps:
            logger.debug(f"No valid market caps found for {mint}. Cannot calculate median market cap.")
            return None #

        inlier_market_caps = self._apply_iqr_to_values(market_caps) #
        if not inlier_market_caps:
            logger.warning(f"All market caps for {mint} filtered by IQR. Falling back to unfiltered median for MC calc.") #
            return statistics.median(market_caps) if market_caps else None #
        
        return statistics.median(inlier_market_caps) if inlier_market_caps else None


    async def _get_migration_timestamp(self, mint: str, conn) -> Optional[datetime]:
        """Fetches the timestamp of when a token was migrated."""
        query = "SELECT timestamp FROM migrations WHERE mint = $1 ORDER BY timestamp DESC LIMIT 1"
        migration_ts = await conn.fetchval(query, mint)
        return migration_ts

    async def _get_latest_price_from_dexscreener(self, mint: str, conn) -> Dict[str, Optional[float]]:
        """
        [MODIFIED] Fetches the single latest price snapshot for a migrated token,
        with a grace period for newly migrated tokens to allow for data aggregation.
        """
        query = """
            SELECT price_usd, market_cap, sol_price_usd, volume_m5, price_native
            FROM dexscreener_data
            WHERE mint_address = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        record = await conn.fetchrow(query, mint)

        # --- START OF FIX ---
        # Initial checks for fundamental data validity.
        if not record or not record['price_usd'] or not record['sol_price_usd'] or record['sol_price_usd'] <= 0:
            logger.warning(f"DEXScreener data for {mint} is missing critical price data. Treating as invalid.")
            return {'price': None, 'market_cap': None}

        # Now check for staleness (0 volume), but apply a grace period for newly migrated tokens.
        is_stale_by_volume = float(record['volume_m5']) <= 0
        is_within_grace_period = False

        # Check migration timestamp to determine if we are in the grace period.
        migration_ts = await self._get_migration_timestamp(mint, conn)
        if migration_ts:
            grace_period_minutes = self.config.get('DEXSCREENER_MIGRATION_GRACE_PERIOD_MINUTES', 5)
            time_since_migration = datetime.now(timezone.utc) - migration_ts
            if time_since_migration < timedelta(minutes=grace_period_minutes):
                is_within_grace_period = True
                logger.debug(f"Token {mint} is within the {grace_period_minutes}-minute migration grace period ({time_since_migration.total_seconds():.0f}s ago). Stale volume check will be bypassed.")

        # The price is considered invalid ONLY IF it's stale by volume AND we are NOT within the grace period.
        # If the volume is stale and we are outside the grace period, the price is invalid.
        # However, we MUST still return the last known market cap.
        if is_stale_by_volume and not is_within_grace_period:
            logger.warning(f"DEXScreener data for {mint} is stale (0 volume in m5). Price is invalid, but using latest market cap for safety checks.")
            # Calculate the market cap in SOL from the USD values in the record
            market_cap_usd = float(record['market_cap'])
            sol_price_usd = float(record['sol_price_usd'])
            market_cap_sol = market_cap_usd / sol_price_usd
            price = float(record['price_native'])
            # Return a valid market cap but an invalid price
            return {'price': price, 'market_cap': market_cap_sol}

        price_usd = float(record['price_usd'])
        market_cap_usd = float(record['market_cap'])
        sol_price_usd = float(record['sol_price_usd'])

        # Convert to SOL-denominated values for consistency
        price_sol = price_usd / sol_price_usd
        market_cap_sol = market_cap_usd / sol_price_usd

        return {'price': price_sol, 'market_cap': market_cap_sol}

    async def _get_robust_price_from_pump(self, mint: str, config_params: dict, conn) -> Dict[str, Optional[float]]:
        """
        MODIFIED LOGIC: Calculates robust price ONLY from Pump.fun trades.
        This re-uses your existing median/vwap/twap logic but on a clean data source.
        """
        # Note: Your existing helper functions like _calculate_median_price_with_iqr,
        # _calculate_vwap_price_with_iqr, and their own helpers (_get_raw_trades_for_price_calc)
        # would need to be modified to query the `trades` table directly instead of `v_unified_market_ticks_live`.
        # For simplicity, we will implement the MEDIAN calculation directly here.
        
        window_type = config_params.get("PRICE_WINDOW_TYPE", "time")
        
        # Build query to fetch raw trades only from the `trades` table
        params = [mint]
        if window_type == "time":
            window_minutes = str(config_params.get("PRICE_AVG_WINDOW_MINUTES", 1.0))
            query = """
                SELECT price, marketCapSol FROM trades
                WHERE mint = $1 AND timestamp >= NOW() - ($2::text || ' minutes')::interval
                ORDER BY timestamp DESC;
            """
            params.append(window_minutes)
        else: # 'count'
            trade_count = config_params.get("PRICE_AVG_TRADE_COUNT", 20)
            query = """
                SELECT price, marketCapSol FROM trades
                WHERE mint = $1 ORDER BY timestamp DESC LIMIT $2;
            """
            params.append(trade_count)

        trade_records = await conn.fetch(query, *params)
        if not trade_records:
            return {'price': None, 'market_cap': None}

        # Apply IQR outlier removal and calculate median
        prices = [float(r['price']) for r in trade_records if r.get('price') is not None]
        market_caps = [float(r['marketcapsol']) for r in trade_records if r.get('marketcapsol') is not None]

        if not prices:
             return {'price': None, 'market_cap': None}

        # Using your _apply_iqr_to_values helper for simplicity
        inlier_prices = self._apply_iqr_to_values(prices)
        inlier_market_caps = self._apply_iqr_to_values(market_caps)

        final_price = statistics.median(inlier_prices) if inlier_prices else None
        final_market_cap = statistics.median(inlier_market_caps) if inlier_market_caps else None
        
        return {'price': final_price, 'market_cap': final_market_cap}

    async def get_price_and_market_cap_for_decision(self, mint: str, config_from_caller: dict, conn) -> Dict[str, Optional[float]]:
        """
        [MODIFIED] Centralized function to get the decision price and market cap for a token.
        If a token is marked as migrated ('DEXSCREENER') but its Dexscreener data is invalid
        (e.g., no recent volume, or no data yet), it will temporarily fall back to using
        its last known Pump.fun data if the migration occurred within a grace period.
        """
        # 1. Determine the data source for the token
        token_record = await conn.fetchrow("SELECT data_source FROM tokens WHERE mint = $1", mint)

        if not token_record:
            logger.warning(f":triangular_flag: Could not find token {mint} in 'tokens' table to determine data source.")
            return {'price': None, 'market_cap': None}

        data_source = token_record['data_source']
        #logger.debug(f":bar_chart: Getting price for {mint}. Primary source: {data_source}")

        # 2. Branch logic based on the data source
        if data_source == 'DEXSCREENER':
            # For migrated tokens, first attempt to get the latest clean price from dexscreener_data
            price_data = await self._get_latest_price_from_dexscreener(mint, conn)

            # --- START: FALLBACK SECURITY LAYER ---
            # If Dexscreener data is invalid (e.g., stale volume, or no data yet),
            # check if we are within the migration grace period.
            if price_data.get('price') is None:
                migration_ts = await self._get_migration_timestamp(mint, conn)
                if migration_ts:
                    grace_period_minutes = self.config.get('DEXSCREENER_MIGRATION_GRACE_PERIOD_MINUTES', 5)
                    time_since_migration = datetime.now(timezone.utc) - migration_ts
                    
                    if time_since_migration < timedelta(minutes=grace_period_minutes):
                        logger.info(
                            f"DEXScreener price for {mint} is invalid, but token is within the {grace_period_minutes}-minute "
                            f"migration grace period ({time_since_migration.total_seconds():.0f}s ago). "
                            f"Attempting to fall back to last known Pump.fun data."
                        )
                        # Fall back to using robust calculation on its (now historical) Pump.fun trades.
                        return await self._get_robust_price_from_pump(mint, config_from_caller, conn)
            # --- END: FALLBACK SECURITY LAYER ---

            # If not in grace period or if Dexscreener data was valid, return the original result.
            return price_data
            
        else: # 'PUMP'
            # For non-migrated tokens, use the robust calculation to handle outliers
            return await self._get_robust_price_from_pump(mint, config_from_caller, conn)


    async def analyze_dexscreener_trend(self, mint: str, lookback_minutes: int, conn) -> list:
        """
        Fetches recent dexscreener_data snapshots for trend analysis.
        """
        query = """
            SELECT
                price_change_m5,
                buys_m5,
                sells_m5,
                liquidity_usd,
                timestamp
            FROM dexscreener_data
            WHERE mint_address = $1
              AND timestamp >= NOW() - ($2::text || ' minutes')::interval
            ORDER BY timestamp DESC;
        """
        try:
            return await conn.fetch(query, mint, str(lookback_minutes))
        except Exception as e:
            logger.error(f":police_car_light: Error fetching DexScreener trend data for {mint}: {e}", exc_info=True)
            return []

    async def get_latest_dexscreener_response(self, mint: str, conn=None) -> str | None:
        """Fetches the 'full_response' JSON string of the most recent entry for a mint."""
        query = """
            SELECT full_response FROM dexscreener_data
            WHERE mint_address = $1 ORDER BY timestamp DESC LIMIT 1;
        """
        connection = conn or await self.pool.acquire()
        try:
            record = await connection.fetchval(query, mint)
            return record
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
                logger.error(f":police_car_light: Error fetching total tracked tokens: {e}", exc_info=True)
                return 0

    async def load_all_configurations(self) -> Dict[str, Any]:
        """Loads all configuration parameters from the database."""
        query = "SELECT key, value, type FROM configurations"
        config_data = {}
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                for row in rows:
                    key, str_value, value_type = row['key'], row['value'], row['type']
                    try:
                        if value_type == 'int':
                            config_data[key] = int(str_value)
                        elif value_type == 'float':
                            config_data[key] = float(str_value)
                        elif value_type == 'bool':
                            config_data[key] = str_value.lower() == 'true'
                        elif value_type == 'list':
                            config_data[key] = json.loads(str_value) # Assuming lists are stored as JSON strings
                        elif value_type == 'str':
                            config_data[key] = str_value
                        else:
                            logger.warning(f"Unknown configuration type '{value_type}' for key '{key}'. Storing as string.")
                            config_data[key] = str_value
                    except (ValueError, TypeError, json.JSONDecodeError) as e:
                        logger.error(f":police_car_light: Error converting configuration value for key '{key}' (type: {value_type}, value: '{str_value}'): {e}. Storing as raw string or None.")
                        config_data[key] = str_value # Fallback to string
                logger.info(f"Loaded {len(config_data)} configurations from database.")
                return config_data
        except Exception as e:
            logger.error(f":police_car_light: Error loading configurations from database: {e}", exc_info=True)
            return {} # Return empty dict on error

    async def save_configuration_parameter(self, key: str, value: Any, value_type: str, description: Optional[str] = None):
        """Saves or updates a single configuration parameter in the database."""
        query = """
            INSERT INTO configurations (key, value, type, description, last_updated)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                type = EXCLUDED.type,
                description = EXCLUDED.description,
                last_updated = NOW();
        """
        str_value = ""
        if value_type == 'bool':
            str_value = 'true' if value else 'false'
        elif value_type == 'list':
            str_value = json.dumps(value) # Store lists as JSON strings
        elif value is None: # Handle None explicitly for other types
            str_value = None # Store as NULL in DB if appropriate, or handle as empty string
        else:
            str_value = str(value)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, key, str_value, value_type, description)
            logger.debug(f"Saved configuration: {key} = {value} (Type: {value_type})")
        except Exception as e:
            logger.error(f":police_car_light: Error saving configuration parameter {key}: {e}", exc_info=True)

    async def get_python_type_string(self, value: Any) -> str:
        """Determines the storable type string for a Python value."""
        if isinstance(value, bool): return 'bool'
        if isinstance(value, int): return 'int'
        if isinstance(value, float): return 'float'
        if isinstance(value, list): return 'list'
        if isinstance(value, str): return 'str'
        # Fallback for other types, or raise error
        logger.warning(f"Unsupported type for config persistence: {type(value)} for value '{value}'. Defaulting to 'str'.")
        return 'str'

    async def get_configuration_parameter(self, key: str) -> Optional[Any]:
        """Fetches a single configuration parameter from the database."""
        # This method might not be strictly necessary if all configs are loaded at once,
        # but can be useful for specific lookups.
        all_configs = await self.load_all_configurations()
        return all_configs.get(key)

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
            logger.error(f":police_car_light: Error inserting heartbeat event: {e}", exc_info=True)
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
            logger.error(f":police_car_light: Error in check_for_data_gap_on_restart: {e}", exc_info=True)
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

    async def is_token_active_in_db(self, mint: str, conn=None) -> bool:
        """
        Checks if a token exists in the primary 'tokens' table (i.e., it has not been backed up).
        Returns True if the token exists, False otherwise.
        """
        query = "SELECT 1 FROM tokens WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            result = await connection.fetchval(query, mint)
            return result is not None
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def mark_token_as_migrated(self, mint: str, conn=None):
        """Updates the data_source for a token to 'DEXSCREENER'."""
        logger.info(f":twisted_rightwards_arrows: Flagging token {mint} as migrated. Switching data source to DEXScreener.")
        query = "UPDATE tokens SET data_source = 'DEXSCREENER' WHERE mint = $1"
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(query, mint)
        finally:
            if not conn and connection:
                await self.pool.release(connection)

    async def cleanup_db(self, cleanup_flag: bool):
        """Drop all application tables if cleanup_flag is True."""
        if cleanup_flag:
            logger.warning(":police_car_light: Starting full database cleanup - Dropping all application tables...")
            async with self.pool.acquire() as conn:
                # List all known application tables (main and backup)
                # Add any other tables managed by the application if necessary (e.g., creator_wallets)
                tables_to_drop = [
                    'configurations',     # Add the new table
                    'portfolio',
                    'rugcheck',           # Depends on tokens
                    'trades',             # No explicit FK, but related to tokens
                    'migrations',         # Standalone or related? Assuming standalone for drop order
                    'tokens',             # Drop after dependents
                    'social_scores_backup',
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
                        logger.error(f":police_car_light: Error dropping table {table}: {e}", exc_info=False) # Keep log concise

            logger.warning("✅ Full database cleanup finished.")

    async def backup_db(self, backup_flag: bool):
        """Backup tables based on backup_flag."""
        if backup_flag:
            async with self.pool.acquire() as conn:
                try:
                    tables_to_backup = [
                        'tokens', 'trades', 'rugcheck', 'migrations', 'portfolio', 'social_scores'
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
                        elif table == 'social_scores':
                            await conn.execute("""
                                INSERT INTO social_scores_backup (id, mint, timestamp, score_type, score_value, details, backup_timestamp)
                                SELECT id, mint, timestamp, score_type, score_value, details, NOW()
                                FROM social_scores
                                ON CONFLICT (id) DO NOTHING;
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
                    logger.exception(":police_car_light: Error during database backup: %s", e)
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
            FROM v_unified_market_ticks_historical
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
                logger.error(f":police_car_light: Error fetching token lifespan for {mint}: {e}", exc_info=True)
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

    async def get_historical_data_for_backtesting(
        self,
        mints: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> Dict[str, pd.DataFrame]:
        """
        [MODIFIED] Fetches historical OHLCV data for a list of mints.
        The date range is now optional. If start_date and end_date are None,
        it fetches the complete history for the given mints.
        """
        if not mints:
            logger.warning("get_historical_data_for_backtesting called with empty mints list.")
            return {}
        if not self.pool:
            logger.error("Database pool not initialized.")
            return {}

        # Ensure dates are UTC if provided
        start_date_utc = start_date.astimezone(timezone.utc) if start_date and start_date.tzinfo else start_date
        end_date_utc = end_date.astimezone(timezone.utc) if end_date and end_date.tzinfo else end_date

        # --- Build Trade Query with Optional Date Filters ---
        trade_query_parts = [
            "SELECT mint, timestamp, price_sol AS price, volume_usd AS volume,",
            "market_cap_usd AS market_cap_calculated, market_cap_sol AS live_market_cap_sol",
            "FROM v_unified_market_ticks_historical",
            "WHERE mint = ANY($1::text[]) AND price_sol > 0"
        ]
        trade_params = [mints]
        if start_date_utc:
            trade_params.append(start_date_utc)
            trade_query_parts.append(f"AND timestamp >= ${len(trade_params)}")
        if end_date_utc:
            trade_params.append(end_date_utc)
            trade_query_parts.append(f"AND timestamp < ${len(trade_params)}")
        trade_query_parts.append("ORDER BY mint, timestamp;")
        trade_query = " ".join(trade_query_parts)

        # --- Build Rugcheck Query with Optional Date Filters ---
        rugcheck_query_parts = [
            "WITH RankedRugcheck AS (",
            "SELECT mint, last_checked AS timestamp, score AS rugcheck_score, ROW_NUMBER() OVER (PARTITION BY mint ORDER BY last_checked DESC) as rn",
            "FROM v_rugcheck WHERE mint = ANY($1::text[])"
        ]
        rugcheck_params = [mints]
        if end_date_utc:
            rugcheck_params.append(end_date_utc)
            rugcheck_query_parts.append(f"AND last_checked < ${len(rugcheck_params)}")
        rugcheck_query_parts.append(")")
        rugcheck_query_parts.append("SELECT mint, timestamp, rugcheck_score FROM RankedRugcheck WHERE rn = 1")
        if start_date_utc:
            rugcheck_params.append(start_date_utc)
            rugcheck_query_parts.append(f"OR timestamp >= ${len(rugcheck_params)}")
        rugcheck_query = " ".join(rugcheck_query_parts) + ";"

        # --- Token Info Query (no date filter needed) ---
        token_info_query = """
            WITH TokenCreationData AS (
                SELECT
                    mint, socials_score, timestamp AS token_creation_time,
                    marketCapSol AS creation_init_market_cap_sol,
                    cooldown_until,
                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp ASC) as rn
                FROM v_tokens vt WHERE mint = ANY($1::text[])
            )
            SELECT mint, token_creation_time, socials_score, creation_init_market_cap_sol, cooldown_until
            FROM TokenCreationData WHERE rn = 1;
        """

        results_dict = {}
        async with self.pool.acquire() as conn:
            try:
                # --- Execute Queries ---
                trade_records_raw = await conn.fetch(trade_query, *trade_params)
                rugcheck_records_raw = await conn.fetch(rugcheck_query, *rugcheck_params)
                token_info_records_raw = await conn.fetch(token_info_query, mints)

                if not trade_records_raw:
                    logger.warning("No trade records found for the specified mints and period.")
                    return {}

                # --- Process Data (same logic as before) ---
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
                time_interval_minutes = self.config.get('DEFAULT_TIME_INTERVAL', 10)
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

                    cols_to_interpolate = [
                        'Open', 'High', 'Low', 'Close', 'Volume',
                        'market_cap_calculated', 'marketCapSol', 'volatility'
                    ]
                    
                    for col in cols_to_interpolate:
                        if col in group_reindexed.columns:
                            group_reindexed[col] = pd.to_numeric(group_reindexed[col], errors='coerce').interpolate(method='time')

                    group_resampled = group_reindexed
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
                        mint_val = r_dict.get('mint')
                        creation_time_val = r_dict.get('token_creation_time')
                        socials_val = r_dict.get('socials_score')
                        creation_mc_sol_val = r_dict.get('creation_init_market_cap_sol')
                        cooldown_until_val = r_dict.get('cooldown_until')

                        creation_time = pd.to_datetime(creation_time_val, errors='coerce', utc=True)
                        socials = pd.to_numeric(socials_val, errors='coerce')
                        creation_mc_sol = pd.to_numeric(creation_mc_sol_val, errors='coerce')
                        cooldown_until_ts = pd.to_datetime(cooldown_until_val, errors='coerce', utc=True)

                        if mint_val and pd.notna(creation_time):
                            token_info_map[mint_val] = {'creation_time': creation_time, 
                                                        'socials_score': socials, 
                                                        'creation_init_market_cap_sol': creation_mc_sol,
                                                        'cooldown_until': cooldown_until_ts
                                                        }
                
                required_final_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'creation_init_market_cap_sol', 'volatility', 'rugcheck_score', 'socials_score', 'token_creation_time', 'cooldown_until']
                
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
                        combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'], combined_df['cooldown_until'] = mint_specific_info['creation_time'], mint_specific_info['socials_score'], mint_specific_info.get('creation_init_market_cap_sol', np.nan), mint_specific_info.get('cooldown_until', pd.NaT)
                    else:
                        combined_df['token_creation_time'], combined_df['socials_score'], combined_df['creation_init_market_cap_sol'], combined_df['cooldown_until'] = pd.NaT, 100, np.nan, pd.NaT
                    
                    for r_col in required_final_cols:
                        if r_col not in combined_df.columns: combined_df[r_col] = np.nan 

                    for col in ['rugcheck_score', 'socials_score', 'token_creation_time', 'creation_init_market_cap_sol', 'cooldown_until']: combined_df[col] = combined_df[col].ffill().bfill()
                    
                    combined_df['rugcheck_score'] = combined_df['rugcheck_score'].fillna(10000).astype(int)
                    combined_df['socials_score'] = combined_df['socials_score'].fillna(100).astype(int)
                    combined_df['creation_init_market_cap_sol'] = pd.to_numeric(combined_df['creation_init_market_cap_sol'], errors='coerce').fillna(0.0)
                    combined_df['cooldown_until'] = pd.to_datetime(combined_df['cooldown_until'], errors='coerce', utc=True) 

                    for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'marketCapSol', 'volatility']:
                        combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0.0)
                    
                    final_df = combined_df.copy()
                    # If dates were provided, filter the final combined data at the end
                    if start_date_utc:
                        final_df = final_df[final_df.index >= start_date_utc]
                    if end_date_utc:
                        final_df = final_df[final_df.index < end_date_utc]

                    if not final_df.empty and all(col in final_df.columns for col in required_final_cols):
                        astype_dict = {
                            'Open': float, 'High': float, 'Low': float, 'Close': float, 
                            'Volume': float, 'market_cap_calculated': float, 
                            'marketCapSol': float, 'creation_init_market_cap_sol': float, 
                            'volatility': float, 'rugcheck_score': int, 'socials_score': int
                        }
                        cols_for_astype = [col for col in required_final_cols if col in astype_dict]
                        final_df[cols_for_astype] = final_df[cols_for_astype].astype(astype_dict)
                        
                        final_df.index = pd.to_datetime(final_df.index, utc=True)
                        results_dict[mint_name] = final_df[required_final_cols]
                    else:
                        logger.warning(f"No valid data or missing columns for {mint_name} after final processing. Skipping.")
            
            except Exception as e:
                logger.error(f":police_car_light: Error processing historical data ({type(e).__name__}): {e}", exc_info=True)
                return {}

        return results_dict
    
    async def get_raw_data_for_rl(
        self,
        start_date: datetime,
        end_date: datetime,
        min_trade_count: int
    ) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
        """
        [NEW & OPTIMIZED] Fetches all the necessary raw, time-series data for the RL
        feature engineering script. It does not perform any calculations and cleanly
        separates Pump.fun trades from DexScreener data.
        """
        if not self.pool:
            logger.error("Database pool not initialized.")
            return None

        mints_query = """
            SELECT mint FROM (
                SELECT mint, COUNT(signature) as trade_count
                FROM v_trades
                WHERE timestamp >= $1 AND timestamp < $2
                GROUP BY mint
            ) AS trade_counts
            WHERE trade_count >= $3;
        """
        
        try:
            eligible_mint_records = await self.pool.fetch(mints_query, start_date, end_date, min_trade_count)
            if not eligible_mint_records:
                logger.warning(f"No tokens found in the date range with at least {min_trade_count} trades.")
                return None
            
            mints = [r['mint'] for r in eligible_mint_records]
            logger.info(f"Found {len(mints)} eligible tokens. Fetching their full raw data...")

            # --- THIS IS THE FIX ---
            # Query v_trades for Pump.fun data, not the unified view.
            # We also calculate volume_usd directly here AND FETCH TX_TYPE.
            trade_query = """
                SELECT 
                    t.mint, t.timestamp, t.price AS price_sol, t.marketCapSol AS market_cap_sol,
                    (t.sol_amount * t.sol_price_usd) AS volume_usd, t.tx_type, sol_price_usd AS sol_price_usd
                FROM v_trades t
                WHERE t.mint = ANY($1::text[]);
            """
            # --- END OF FIX ---
            
            rugcheck_query = "SELECT mint, last_checked AS timestamp, score AS rugcheck_score FROM v_rugcheck WHERE mint = ANY($1::text[]) ORDER BY timestamp;"
            token_info_query = "SELECT mint, socials_score, socials_last_checked, timestamp AS token_creation_time FROM v_tokens WHERE mint = ANY($1::text[]);"
            dexscreener_query = "SELECT mint_address as mint, timestamp, liquidity_usd, buys_m5, sells_m5, volume_m5, price_change_m5 FROM v_dexscreener_data WHERE mint_address = ANY($1::text[]) ORDER BY timestamp;"

            results = await asyncio.gather(
                self.pool.fetch(trade_query, mints),
                self.pool.fetch(rugcheck_query, mints),
                self.pool.fetch(token_info_query, mints),
                self.pool.fetch(dexscreener_query, mints)
            )

            trades_df = pd.DataFrame([dict(r) for r in results[0]])
            rugcheck_df = pd.DataFrame([dict(r) for r in results[1]])
            token_info_df = pd.DataFrame([dict(r) for r in results[2]])
            dexscreener_df = pd.DataFrame([dict(r) for r in results[3]])

            return trades_df, rugcheck_df, token_info_df, dexscreener_df

        except Exception as e:
            logger.error(f":police_car_light: Error fetching raw data for RL: {e}", exc_info=True)
            return None

    # --- NEW METHOD FOR RL FEEDBACK LOOP ---
    async def log_completed_trade(
        self,
        token_address: str,
        side: str,
        amount_in_sol: float,
        amount_out_tokens: float,
        fill_price: float,
        market_cap_at_trade: Optional[float],
        tx_fee_sol: Optional[float],
        tip_sol: Optional[float],
        slippage_percent: Optional[float],
        trade_context: Optional[Dict[str, Any]],
        conn=None
    ):
        """
        Logs a detailed record of a completed trade to the `completed_trades` table.
        This serves as the foundational feedback loop for the RL agent's learning process.

        Args:
            token_address (str): The mint address of the token traded.
            side (str): The side of the trade, must be 'buy' or 'sell'.
            amount_in_sol (float): The amount of SOL involved in the trade.
            amount_out_tokens (float): The amount of tokens involved in the trade.
            fill_price (float): The actual executed price of the trade in SOL per token.
            market_cap_at_trade (Optional[float]): The market cap in SOL at the time of the trade.
            tx_fee_sol (Optional[float]): The base network fee for the transaction in SOL.
            tip_sol (Optional[float]): The priority fee (Jito tip) for the transaction in SOL.
            slippage_percent (Optional[float]): The slippage percentage experienced.
            trade_context (Optional[Dict[str, Any]]): A JSONB field for storing other metadata.
            conn: An optional existing database connection or transaction.
        """
        if side not in ('buy', 'sell'):
            raise ValueError("The 'side' parameter must be either 'buy' or 'sell'.")

        query = """
            INSERT INTO completed_trades (
                token_address, side, amount_in_sol, amount_out_tokens, fill_price,
                market_cap_at_trade, tx_fee_sol, tip_sol, slippage_percent, trade_context
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);
        """
        
        # Convert trade_context dict to a JSON string if it exists
        trade_context_json = json.dumps(trade_context) if trade_context else None
        
        connection = conn or await self.pool.acquire()
        try:
            await connection.execute(
                query, token_address, side, amount_in_sol, amount_out_tokens, fill_price,
                market_cap_at_trade, tx_fee_sol, tip_sol, slippage_percent, trade_context_json
            )
            logger.debug(f"Logged completed '{side}' trade for {token_address} to feedback table.")
        except Exception as e:
            logger.error(f"Failed to log completed trade for {token_address}: {e}", exc_info=True)
            # Re-raise if not using an external transaction, so the caller can handle it.
            if not conn:
                raise
        finally:
            # Release connection only if it was acquired here
            if not conn and connection:
                await self.pool.release(connection)

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
            logger.error(f":police_car_light: Error fetching token lifespan for {mint}: {e}", exc_info=True)
            return None
