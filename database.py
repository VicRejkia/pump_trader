"""
Database operations for the trading bot using aiosqlite.
Provides functions to initialize the database, store tokens and trades,
and manage portfolio data including backups.
"""
import state
import aiosqlite
from datetime import datetime
from config import DB_NAME, TOTAL_SUPPLY
from logger import logger

async def init_db():
    """Initializes the SQLite database and creates necessary tables."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Main tables
        await db.execute('''CREATE TABLE IF NOT EXISTS tokens (
                              mint TEXT PRIMARY KEY, 
                              traderPublicKey TEXT,
                              initialBuy REAL,
                              solAmount REAL,
                              bondingCurveKey TEXT, 
                              vTokensInBondingCurve REAL, 
                              vSolInBondingCurve REAL,
                              marketCapSol REAL, 
                              name TEXT,
                              symbol TEXT,
                              uri TEXT,
                              market_cap_calculated REAL,
                              last_trade TIMESTAMP,
                              website TEXT,
                              telegram TEXT,
                              twitter TEXT,
                              socials_score INTEGER DEFAULT 0,
                              is_active INTEGER DEFAULT 1,
                              timestamp TIMESTAMP)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS trades (
                              signature TEXT PRIMARY KEY, 
                              mint TEXT, 
                              tx_type TEXT,
                              token_amount REAL, 
                              sol_amount REAL, 
                              price REAL,
                              bondingCurveKey TEXT,
                              vTokensInBondingCurve REAL,
                              vSolInBondingCurve REAL,
                              marketCapSol REAL,
                              market_cap_calculated REAL,
                              timestamp TIMESTAMP)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS rugcheck (
                              mint TEXT PRIMARY KEY,
                              tokenProgram TEXT,
                              creator TEXT,
                              token_mintAuthority TEXT,
                              token_supply REAL,
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
                              totalMarketLiquidity REAL,
                              totalLPProviders INTEGER,
                              rugged BOOLEAN,
                              tokenType TEXT,
                              transferFee_pct REAL,
                              transferFee_maxAmount REAL,
                              transferFee_authority TEXT,
                              graphInsidersDetected INTEGER,
                              detectedAt TEXT,
                              full_data TEXT,
                              last_checked TIMESTAMP,
                              FOREIGN KEY (mint) REFERENCES tokens (mint))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS portfolio (
                              id INTEGER PRIMARY KEY AUTOINCREMENT,
                              mint TEXT,
                              tx_type TEXT,
                              price REAL,
                              market_cap REAL,
                              sol_amount REAL,
                              tokens REAL,
                              fee REAL,
                              tip REAL,
                              profit REAL,
                              status TEXT,
                              reason TEXT,
                              remaining_tokens REAL,
                              highest_price REAL NOT NULL DEFAULT 0.0,
                              stop_loss_price REAL,
                              timestamp TIMESTAMP)''')
        # Backup tables
        await db.execute('''CREATE TABLE IF NOT EXISTS tokens_backup (
                              mint TEXT PRIMARY KEY, 
                              traderPublicKey TEXT,
                              initialBuy REAL,
                              solAmount REAL,
                              bondingCurveKey TEXT, 
                              vTokensInBondingCurve REAL, 
                              vSolInBondingCurve REAL,
                              marketCapSol REAL, 
                              name TEXT,
                              symbol TEXT,
                              uri TEXT,
                              market_cap_calculated REAL,
                              last_trade TIMESTAMP,
                              website TEXT,
                              telegram TEXT,
                              twitter TEXT,
                              socials_score INTEGER DEFAULT 0,
                              is_active INTEGER DEFAULT 1,
                              timestamp TIMESTAMP,
                              archived_at TIMESTAMP)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS trades_backup (
                              signature TEXT PRIMARY KEY, 
                              mint TEXT, 
                              tx_type TEXT,
                              token_amount REAL, 
                              sol_amount REAL, 
                              price REAL,
                              bondingCurveKey TEXT,
                              vTokensInBondingCurve REAL,
                              vSolInBondingCurve REAL,
                              marketCapSol REAL,
                              market_cap_calculated REAL,
                              timestamp TIMESTAMP,
                              archived_at TIMESTAMP)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS rugcheck_backup (
                              mint TEXT PRIMARY KEY,
                              tokenProgram TEXT,
                              creator TEXT,
                              token_mintAuthority TEXT,
                              token_supply REAL,
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
                              totalMarketLiquidity REAL,
                              totalLPProviders INTEGER,
                              rugged BOOLEAN,
                              tokenType TEXT,
                              transferFee_pct REAL,
                              transferFee_maxAmount REAL,
                              transferFee_authority TEXT,
                              graphInsidersDetected INTEGER,
                              detectedAt TEXT,
                              full_data TEXT,
                              last_checked TIMESTAMP,
                              archived_at TIMESTAMP)''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS creator_wallets (
                            wallet_address TEXT PRIMARY KEY,
                            token_count INTEGER DEFAULT 0,
                            last_token_time TIMESTAMP)''')
        
        await db.commit()
    logger.info("Database initialized.")

async def store_token(data: dict):
    """
    Inserts a new token record into the tokens table.
    Also checks the creator wallet activity and filters tokens from
    wallets that spawn tokens too frequently.
    
    Returns True if the token was stored, or False if skipped due to suspicious wallet.
    """

    creator = data.get('traderPublicKey')
    if creator:
        async with aiosqlite.connect(DB_NAME) as db:
            # Check if this creator wallet exists in our tracking table.
            async with db.execute("SELECT token_count, last_token_time FROM creator_wallets WHERE wallet_address = ?", (creator,)) as cursor:
                row = await cursor.fetchone()
            now = datetime.utcnow()
            if row:
                token_count, last_token_time = row
                # If the last token creation was within the last 7 days, increment; else, reset.
                if last_token_time and (now - datetime.fromisoformat(last_token_time)).total_seconds() < 604800:
                    token_count += 1
                else:
                    token_count = 1
                # Update the record.
                await db.execute("UPDATE creator_wallets SET token_count = ?, last_token_time = ? WHERE wallet_address = ?", 
                                 (token_count, now.isoformat(), creator))
                await db.commit()
                # If the threshold is exceeded, flag as suspicious.
                if token_count > 2:  # Example threshold.
                    logger.warning(f"Creator wallet {creator} flagged as suspicious with {token_count} tokens in 7 days.")
                    return False
            else:
                # First token from this creator.
                await db.execute("INSERT OR IGNORE INTO creator_wallets (wallet_address, token_count, last_token_time) VALUES (?, ?, ?)",
                                 (creator, 1, now.isoformat()))
                await db.commit()

    from api import calculate_market_cap  # Import here to avoid circular dependencies
    async with aiosqlite.connect(DB_NAME) as db:
        total_supply = TOTAL_SUPPLY  # Fallback if not provided elsewhere
        market_cap_calculated = calculate_market_cap(
            data.get('vTokensInBondingCurve', 0),
            data.get('vSolInBondingCurve', 0),
            total_supply
        )
        original_market_cap = data.get('marketCapSol')
        await db.execute('''INSERT OR IGNORE INTO tokens 
                            (mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, 
                             vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, name, symbol, uri, 
                             market_cap_calculated, timestamp, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''',
                         (data['mint'], data.get('traderPublicKey'), data.get('initialBuy'),
                          data.get('solAmount'), data.get('bondingCurveKey'),
                          data.get('vTokensInBondingCurve'), data.get('vSolInBondingCurve'),
                          original_market_cap, data.get('name'), data.get('symbol'),
                          data.get('uri'), market_cap_calculated, datetime.utcnow()))
        await db.commit()
    logger.debug(f"Stored new token: {data['mint']}")

    # Enqueue the token mint for RugCheck processing:
    await state.state.get_rugcheck_queue().put((0, data['mint']))
    return True

async def store_trade(data: dict):
    """
    Inserts a trade record into the trades table and updates the token's last_trade.
    """
    from api import calculate_market_cap  # Avoid circular dependencies
    async with aiosqlite.connect(DB_NAME) as db:
        total_supply = data.get('totalSupply', TOTAL_SUPPLY)
        market_cap_calculated = calculate_market_cap(
            data.get('vTokensInBondingCurve', 0),
            data.get('vSolInBondingCurve', 0),
            total_supply
        )
        original_market_cap = data.get('marketCapSol')
        trade_type = data.get('txType', 'unknown')
        token_amount = data.get('tokenAmount', 0)
        sol_amount = data.get('solAmount', 0)
        price = sol_amount / token_amount if token_amount != 0 else 0.0

        await db.execute('''INSERT OR IGNORE INTO trades 
                            (signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey, 
                             vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, market_cap_calculated, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (data['signature'], data['mint'], trade_type, token_amount, sol_amount, price,
                          data.get('bondingCurveKey'), data.get('vTokensInBondingCurve'),
                          data.get('vSolInBondingCurve'), original_market_cap, market_cap_calculated, datetime.utcnow()))
        await db.execute('''UPDATE tokens SET last_trade = ? WHERE mint = ?''',
                         (datetime.utcnow(), data['mint']))
        await db.commit()
    logger.debug(f"Stored trade for token: {data['mint']}")

async def get_total_supply(mint: str) -> float:
    """
    Retrieves the total token supply from the rugcheck table for the given mint.
    Returns the default TOTAL_SUPPLY if not available.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT token_supply FROM rugcheck WHERE mint = ?", (mint,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else TOTAL_SUPPLY

async def backup_and_delete_token(mint: str, archived_at: str):
    """
    Backs up token, trade, and rugcheck data for the given mint, then deletes live records.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("BEGIN")
            await db.execute('''INSERT OR REPLACE INTO tokens_backup 
                                SELECT *, ? FROM tokens WHERE mint = ?''', (archived_at, mint))
            await db.execute('''INSERT OR REPLACE INTO trades_backup 
                                SELECT *, ? FROM trades WHERE mint = ?''', (archived_at, mint))
            await db.execute('''INSERT OR REPLACE INTO rugcheck_backup 
                                SELECT *, ? FROM rugcheck WHERE mint = ?''', (archived_at, mint))
            await db.execute("DELETE FROM tokens WHERE mint = ?", (mint,))
            await db.execute("DELETE FROM trades WHERE mint = ?", (mint,))
            await db.execute("DELETE FROM rugcheck WHERE mint = ?", (mint,))
            await db.commit()
            logger.debug(f"Backup and deletion complete for {mint}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Transaction failed for {mint}: {e}")
