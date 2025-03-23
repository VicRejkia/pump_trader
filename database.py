"""
Database operations for the trading bot using PostgreSQL.
Provides functions to initialize the database, store tokens and trades,
and manage portfolio data including backups.
"""

import asyncio
import asyncpg
from datetime import datetime, timezone
from config import DB_URL, TOTAL_SUPPLY
from logger import logger
from decimal import Decimal
# Database connection pool
_db_pool = None
#_trade_batch_queue = asyncio.Queue(maxsize=10_000)
#_batch_processor_started = False

def validate_timezone(func):
    def wrapper(*args, **kwargs):
        for arg in args:
            if isinstance(arg, datetime) and arg.tzinfo is None:
                raise ValueError(f"Naive datetime detected in {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

async def init_db():
    """Initialize PostgreSQL connection pool and create tables."""
    global _db_pool
    _db_pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=10)
    
    async with _db_pool.acquire() as conn:
        async with conn.transaction():
            await _create_tables(conn)

async def get_db():
    """Return the database connection pool."""
    return _db_pool

@validate_timezone
async def store_token(data: dict) -> bool:
    """Store token with creator wallet checks and market cap calculation."""
    async with _db_pool.acquire() as conn:
        async with conn.transaction():
            try:
                # === Creator wallet check ===
                creator = data.get('traderPublicKey')
                if creator:
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
                        logger.warning(f"Suspicious creator {creator} for token {data['mint']} with {token_count} tokens in 7 days")
                        return False
                
                from api import calculate_market_cap
                market_cap_calculated = calculate_market_cap(
                    data.get('vTokensInBondingCurve', 0),
                    data.get('vSolInBondingCurve', 0),
                    data.get('totalSupply', TOTAL_SUPPLY)
                )

                await conn.execute('''
                    INSERT INTO tokens (
                        mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey,
                        vTokensInBondingCurve, vSolInBondingCurve, marketCapSol,
                        name, symbol, uri, market_cap_calculated, timestamp, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, TRUE)
                    ON CONFLICT (mint) DO NOTHING
                ''', 
                    data['mint'],
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
                    market_cap_calculated,
                    datetime.now(timezone.utc)
                )

                return True
            except Exception as e:
                logger.error(f"Token storage failed for {data.get('mint')}: {e}")
                return False


# async def store_trade(data: dict):
#     """Enqueue trade for batch processing."""
#     # DEBUG
#     required_fields = {
#         'signature', 'mint', 'txtype', 'tokenAmount', 
#         'solAmount', 'bondingCurveKey',
#         'vTokensInBondingCurve', 'vSolInBondingCurve',
#         'marketCapSol'
#     }
#     missing = required_fields - data.keys()
#     if missing:
#         logger.error(f"Missing trade fields: {missing}")
#         return
#     # DEBUG END
#     await _trade_batch_queue.put(data)
@validate_timezone
async def store_trade(data: dict):
    from api import calculate_market_cap
    try:
        async with _db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO trades (
                    signature, mint, tx_type, token_amount, sol_amount, price,
                    bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
                    marketCapSol, market_cap_calculated, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (signature) DO NOTHING
            ''',
            data['signature'],
            data['mint'],
            data['txType'],  # Ensure matches column name case
            Decimal(str(data['tokenAmount'])),
            Decimal(str(data['solAmount'])),
            Decimal(str(data['solAmount'] / data['tokenAmount'])) if data['tokenAmount'] else 0,
            data['bondingCurveKey'],
            Decimal(str(data['vTokensInBondingCurve'])),
            Decimal(str(data['vSolInBondingCurve'])),
            Decimal(str(data['marketCapSol'])),
            calculate_market_cap(
                        data.get('vTokensInBondingCurve', 0),
                        data.get('vSolInBondingCurve', 0),
                        data.get('totalSupply', TOTAL_SUPPLY)
                    ),
            datetime.now(timezone.utc)
            )
            
            # Update tokens.last_trade
            await conn.execute('''
                UPDATE tokens SET last_trade = $1 WHERE mint = $2
            ''', datetime.now(timezone.utc), data['mint'])
            
            logger.debug(f"Stored {data['txType']} trade for {data['mint']}")
    except Exception as e:
        logger.error(f"Trade storage failed: {e}")
        raise

# async def _process_trade_batches():
#     """Background task to process trade batches efficiently."""
#     while True:
#         batch = []
#         try:
#             while len(batch) < 1000:
#                 batch.append(await asyncio.wait_for(_trade_batch_queue.get(), timeout=1.0))
#         except asyncio.TimeoutError:
#             pass
        
#         if batch:
#             async with _db_pool.acquire() as conn:
#                 async with conn.transaction():
#                     try:
#                         trade_params = []
#                         token_updates = {}

#                         for data in batch:
#                             from api import calculate_market_cap
#                             market_cap_calculated = calculate_market_cap(
#                                 data.get('vTokensInBondingCurve', 0),
#                                 data.get('vSolInBondingCurve', 0),
#                                 data.get('totalSupply', TOTAL_SUPPLY)
#                             )

#                             trade_params.append((
#                                 data['signature'],
#                                 data['mint'],
#                                 data.get('txType', 'unknown'),
#                                 data.get('tokenAmount', 0),
#                                 data.get('solAmount', 0),
#                                 (data['solAmount'] / data['tokenAmount']) if data.get('tokenAmount') else 0.0,
#                                 data.get('bondingCurveKey'),
#                                 data.get('vTokensInBondingCurve'),
#                                 data.get('vSolInBondingCurve'),
#                                 data.get('marketCapSol'),
#                                 market_cap_calculated,
#                                 datetime.now(timezone.utc)
#                             ))

#                             token_updates[data['mint']] = datetime.now(timezone.utc)

#                         await conn.executemany('''
#                             INSERT INTO trades (
#                                 signature, mint, tx_type, token_amount, sol_amount, price,
#                                 bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
#                                 marketCapSol, market_cap_calculated, timestamp
#                             ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
#                             ON CONFLICT (signature) DO NOTHING
#                         ''', trade_params)

#                         await conn.executemany('''
#                             UPDATE tokens SET last_trade = $1 WHERE mint = $2
#                         ''', [(ts, mint) for mint, ts in token_updates.items()])

#                         logger.info(f"✅ Processed {len(batch)} trades in batch")

#                     except Exception as e:
#                         logger.error(f"❌ Batch insert failed: {e}")
#                         for item in batch:
#                             await _trade_batch_queue.put(item)
#                         await asyncio.sleep(1)

async def get_total_supply(mint: str) -> float:
    """Get token supply from rugcheck table."""
    async with _db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT token_supply FROM rugcheck WHERE mint = $1", mint)
        return row[0] if row else TOTAL_SUPPLY

async def backup_and_delete_token(mint: str, archived_at: datetime):
    """Backup and delete token data across all tables."""
    async with _db_pool.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute('''
                    INSERT INTO tokens_backup SELECT *, $1 FROM tokens WHERE mint = $2
                ''', archived_at, mint)
                
                await conn.execute('''
                    INSERT INTO trades_backup SELECT *, $1 FROM trades WHERE mint = $2
                ''', archived_at, mint)

                await conn.execute('''
                    INSERT INTO rugcheck_backup SELECT *, $1 FROM rugcheck WHERE mint = $2
                ''', archived_at, mint)

                await conn.execute("DELETE FROM tokens WHERE mint = $1", mint)
                await conn.execute("DELETE FROM trades WHERE mint = $1", mint)
                await conn.execute("DELETE FROM rugcheck WHERE mint = $1", mint)

                logger.info(f"✅ Backup & deletion completed for {mint}")

            except Exception as e:
                logger.error(f"❌ Backup failed for {mint}: {e}")
                raise

async def _create_tables(conn):
    """Create PostgreSQL tables for the trading bot."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            mint TEXT PRIMARY KEY,
            traderPublicKey TEXT,
            initialBuy NUMERIC,
            solAmount NUMERIC,
            bondingCurveKey TEXT,
            vTokensInBondingCurve NUMERIC,
            vSolInBondingCurve NUMERIC,
            marketCapSol NUMERIC,
            name TEXT,
            symbol TEXT,
            uri TEXT,
            market_cap_calculated NUMERIC,
            last_trade TIMESTAMP WITH TIME ZONE,
            website TEXT,
            telegram TEXT,
            twitter TEXT,
            socials_score INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_tokens_last_trade ON tokens(last_trade);
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            signature TEXT PRIMARY KEY,
            mint TEXT REFERENCES tokens(mint) ON DELETE CASCADE,
            tx_type TEXT NOT NULL CHECK (tx_type IN ('buy', 'sell')),
            token_amount NUMERIC,
            sol_amount NUMERIC,
            price NUMERIC,
            bondingCurveKey TEXT,
            vTokensInBondingCurve NUMERIC,
            vSolInBondingCurve NUMERIC,
            marketCapSol NUMERIC,
            market_cap_calculated NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_trades_mint ON trades(mint);
    """)

    await conn.execute("""
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
            last_checked TIMESTAMP WITH TIME ZONE
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id SERIAL PRIMARY KEY,
            mint TEXT REFERENCES tokens(mint) ON DELETE CASCADE,
            tx_type TEXT,
            price NUMERIC,
            market_cap NUMERIC,
            sol_amount NUMERIC,
            tokens NUMERIC,
            fee NUMERIC,
            tip NUMERIC,
            profit NUMERIC,
            status TEXT,
            reason TEXT,
            remaining_tokens NUMERIC,
            highest_price NUMERIC NOT NULL DEFAULT 0.0,
            stop_loss_price NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens_backup (
            mint TEXT PRIMARY KEY,
            traderPublicKey TEXT,
            initialBuy NUMERIC,
            solAmount NUMERIC,
            bondingCurveKey TEXT,
            vTokensInBondingCurve NUMERIC,
            vSolInBondingCurve NUMERIC,
            marketCapSol NUMERIC,
            name TEXT,
            symbol TEXT,
            uri TEXT,
            market_cap_calculated NUMERIC,
            last_trade TIMESTAMP WITH TIME ZONE,
            website TEXT,
            telegram TEXT,
            twitter TEXT,
            socials_score INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            timestamp TIMESTAMP WITH TIME ZONE,
            archived_at TIMESTAMP WITH TIME ZONE
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS trades_backup (
            signature TEXT PRIMARY KEY,
            mint TEXT,
            tx_type TEXT,
            token_amount NUMERIC,
            sol_amount NUMERIC,
            price NUMERIC,
            bondingCurveKey TEXT,
            vTokensInBondingCurve NUMERIC,
            vSolInBondingCurve NUMERIC,
            marketCapSol NUMERIC,
            market_cap_calculated NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            archived_at TIMESTAMP WITH TIME ZONE
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS rugcheck_backup (
            mint TEXT PRIMARY KEY,
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
            archived_at TIMESTAMP WITH TIME ZONE
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS creator_wallets (
            wallet_address TEXT PRIMARY KEY,
            token_count INTEGER DEFAULT 0,
            last_token_time TIMESTAMP WITH TIME ZONE
        );
    """)
    logger.info("✅ PostgreSQL tables created successfully")

async def cleanup_db():
    """Truncate all relevant tables in the database."""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # List all tables you want to clear.
            # TRUNCATE ... CASCADE empties the table and dependent tables.
            await conn.execute("""
                TRUNCATE TABLE 
                tokens, 
                trades, 
                rugcheck, 
                portfolio, 
                tokens_backup, 
                trades_backup, 
                rugcheck_backup
                CASCADE;
            """)
            logger.info("✅ Database cleanup complete: all tables truncated.")
