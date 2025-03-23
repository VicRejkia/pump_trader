"""
Handles external API interactions including fetching SOL price, RugCheck data,
and social data.
"""
import asyncio
import json
from datetime import datetime, timezone
from dateutil.parser import isoparse
import httpx
from aiolimiter import AsyncLimiter
import asyncpg

from config import RUGCHECK_RATE_LIMIT, SOL_PRICE_API_URL, RUGCHECK_API
from database import get_db
from logger import logger
from state import state
# from decimal import Decimal


# Rate limiter for RugCheck API calls
limiter = AsyncLimiter(max_rate=RUGCHECK_RATE_LIMIT, time_period=60)

async def update_sol_price():
    """Periodically fetches and updates the global SOL price from an external API."""
    while not await state.get_shutdown():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(SOL_PRICE_API_URL)
                if response.status_code == 200:
                    data = response.json()
                    new_price = data.get("solana", {}).get("usd")
                    await state.set_sol_price(new_price)
                    logger.info(f"✅ Updated Solana price: {new_price} USD")
                else:
                    logger.error(f"⚠ Error fetching Solana price: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Exception fetching Solana price: {e}")
        
        # 🚀 Sleep interruptibly
        await check_missing_rugcheck_data()
        await state.wait_or_interrupt(timeout=3600)

async def refresh_rugcheck_queue():
    """Refreshes the RugCheck queue with updated priorities using interruptible sleeping."""
    while not await state.get_shutdown():
        sol_price = await state.get_sol_price()
        if sol_price is None:
            logger.warning("⚠ SOL_PRICE not updated yet; skipping RugCheck queue refresh.")
            await state.wait_or_interrupt(timeout=5)
            continue

        queue = state.get_rugcheck_queue()
        logger.debug(f"Heartbeat: refresh_rugcheck_queue starting cycle; queue size: {queue.qsize()}")

        # Clear the current queue
        while not queue.empty():
            try:
                queue.get_nowait()
                queue.task_done()
            except asyncio.QueueEmpty:
                break

        async with (await get_db()).acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                    FROM tokens t
                    LEFT JOIN rugcheck r ON t.mint = r.mint
                    LEFT JOIN trades tr ON t.mint = tr.mint
                    WHERE r.mint IS NULL
                    GROUP BY t.mint
                    ORDER BY volume DESC
                """)

                if rows:
                    for row in rows:
                        mint = row["mint"]
                        volume = row["volume"]
                        priority = -float(volume)
                        v = float(volume) * float(sol_price)
                        logger.debug(f"🔄 Refreshing: Token {mint} missing RugCheck data with volume {v} SOL. Enqueuing with priority {priority}.")
                        await queue.put((priority, mint))
                else:
                    logger.debug("✅ All tokens have corresponding RugCheck data after refresh.")

        logger.debug("Heartbeat: refresh_rugcheck_queue cycle complete; sleeping 30s")
        # Instead of sleeping xx seconds straight, sleep interruptibly
        await state.wait_or_interrupt(timeout=30)

async def rugcheck_worker():
    """Worker task that processes tokens from the RugCheck queue."""
    queue = state.get_rugcheck_queue()
    while not await state.get_shutdown():
        try:
            current_size = queue.qsize()
            logger.debug(f"Rugcheck worker: Queue size before get: {current_size}")
            priority, mint = await queue.get()
            logger.debug(f"Rugcheck worker: Retrieved token {mint} with priority {priority} from queue")
            success = await fetch_rugcheck_data(mint)
            if not success:
                logger.info(f"🔄 Requeuing {mint} for RugCheck due to failure.")
                await state.wait_or_interrupt(timeout=5) 
                await queue.put((priority, mint))
            else:
                logger.debug(f"✅ Successfully processed RugCheck for {mint}.")
            queue.task_done()
        except Exception as e:
            logger.error(f"❌ RugCheck worker error: {e}")
            
        await state.wait_or_interrupt(timeout=1) 

async def check_missing_rugcheck_data():
    """Queries the database for tokens missing RugCheck data."""
    logger.debug("Checking for missing RugCheck data...")
    sol_price = await state.get_sol_price()
    if sol_price is None:
        logger.warning("⚠ SOL_PRICE not updated yet; skipping RugCheck prioritization.")
        await state.wait_or_interrupt(timeout=5) 
        return None

    async with (await get_db()).acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch("""
                SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                FROM tokens t
                LEFT JOIN rugcheck r ON t.mint = r.mint
                LEFT JOIN trades tr ON t.mint = tr.mint
                WHERE r.mint IS NULL
                GROUP BY t.mint
                ORDER BY volume DESC
            """)

            logger.debug(f"🔍 Found {len(rows)} tokens missing RugCheck data")
            if rows:
                for row in rows:
                    mint = row["mint"]
                    volume = row["volume"]
                    priority = -float(volume)
                    v = float(volume) * float(sol_price)
                    logger.info(f"🔍 Token {mint} missing RugCheck data with volume {v} SOL. Enqueuing with priority {priority}.")
                    await state.get_rugcheck_queue().put((priority, mint))
            else:
                logger.debug("✅ All tokens have corresponding RugCheck data.")


async def fetch_rugcheck_data(mint: str) -> bool:
    """Fetches and stores RugCheck data."""
    async with limiter:
        # Check if token still exists in the main tokens table
        async with (await get_db()).acquire() as conn:
            exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM tokens WHERE mint = $1)", mint)
            if not exists:
                logger.debug(f"TokenName {mint} no longer exists in tokens table. Skipping RugCheck.")
                return True
            
        try:
            logger.debug(f"Fetching RugCheck data for token {mint}...")
            # Specify a timeout (in seconds) for the HTTP call.
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"{RUGCHECK_API}/{mint}/report"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if not data or "score" not in data:
                        logger.warning(f"⚠ RugCheck data incomplete for {mint}")
                        return False

                    token = data.get("token") or {}
                    tokenMeta = data.get("tokenMeta") or {}
                    fileMeta = data.get("fileMeta") or {}
                    transferFee = data.get("transferFee") or {}
                    risks = json.dumps(data.get("risks", [])) if isinstance(data.get("risks"), list) else None
                    full_data = json.dumps(data)
                    detected_at_str = data.get("detectedAt")
                    detected_at_str = detected_at_str.replace('Z', '+00:00')
                    # Truncate to 6 fractional digits (microseconds)
                    if '.' in detected_at_str:
                        base, fraction = detected_at_str.split('.', 1)
                        detected_at_str = f"{base}.{fraction[:6]}"

                    detected_at = datetime.fromisoformat(detected_at_str)
                    detected_at = detected_at.astimezone(timezone.utc) 

                    async with (await get_db()).acquire() as conn:
                        async with conn.transaction():
                            await conn.execute('''
                                INSERT INTO rugcheck 
                                (mint, tokenProgram, creator, token_mintAuthority, token_supply,
                                token_decimals, token_isInitialized, token_freezeAuthority,
                                tokenMeta_name, tokenMeta_symbol, tokenMeta_uri, tokenMeta_mutable,
                                tokenMeta_updateAuthority, freezeAuthority, mintAuthority, risks,
                                score, fileMeta_description, fileMeta_name, fileMeta_symbol,
                                fileMeta_image, totalMarketLiquidity, totalLPProviders, rugged,
                                tokenType, transferFee_pct, transferFee_maxAmount, transferFee_authority,
                                graphInsidersDetected, detectedAt, full_data, last_checked)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 
                                        $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, 
                                        $27, $28, $29, $30, $31, NOW())
                                ON CONFLICT (mint) DO NOTHING
                            ''', 
                                mint, data.get("tokenProgram"), data.get("creator"),
                                token.get("mintAuthority"), token.get("supply"),
                                token.get("decimals"), token.get("isInitialized"),
                                token.get("freezeAuthority"), tokenMeta.get("name"),
                                tokenMeta.get("symbol"), tokenMeta.get("uri"),
                                tokenMeta.get("mutable"), tokenMeta.get("updateAuthority"),
                                data.get("freezeAuthority"), data.get("mintAuthority"),
                                risks, data.get("score"), fileMeta.get("description"),
                                fileMeta.get("name"), fileMeta.get("symbol"), fileMeta.get("image"),
                                data.get("totalMarketLiquidity"), data.get("totalLPProviders"),
                                data.get("rugged"), data.get("tokenType"),
                                transferFee.get("pct"), transferFee.get("maxAmount"),
                                transferFee.get("authority"), data.get("graphInsidersDetected"),
                                detected_at, full_data
                            )
                            logger.debug(f"✅ RugCheck data stored for {mint}")
                            return True
                else:
                    logger.warning(f"⚠ RugCheck API returned {response.status_code} for {mint}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error fetching RugCheck data for {mint}: {e}")
            return False

async def fetch_social_data(uri: str, token_name: str, token_symbol: str):
    """Fetches social data from a given URI and computes a social score."""
    from utils import calculate_social_score
    social_data = {"website": None, "telegram": None, "twitter": None}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(uri, timeout=10)
            if response.status_code == 200:
                data = response.json()
                social_data["website"] = data.get("website")
                social_data["telegram"] = data.get("telegram")
                social_data["twitter"] = data.get("twitter")
            else:
                logger.warning(f"⚠ Failed to fetch social data for URI {uri}: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error fetching social data for {uri}: {e}")
    social_score = calculate_social_score(social_data, token_name, token_symbol)
    return social_data, social_score

def calculate_market_cap(vTokensInBondingCurve: float, vSolInBondingCurve: float, totalSupply: float) -> float:
    """Calculates the market cap of a token using bonding curve data."""
    if vTokensInBondingCurve <= 0 or totalSupply <= 0:
        return 0.0
    price_per_token = vSolInBondingCurve / vTokensInBondingCurve
    return price_per_token * totalSupply

def calculate_social_score(social_data: dict, token_name: str, token_symbol: str) -> int:
    """Computes a social risk score based on provided social data."""
    total_penalty = 0
    token_name = (token_name or "").lower()
    token_symbol = (token_symbol or "").lower()
    website = social_data.get("website")
    if not website:
        total_penalty += 30
    else:
        from utils import is_valid_website
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
        from utils import is_valid_telegram
        if not is_valid_telegram(telegram):
            total_penalty += 10
    twitter = social_data.get("twitter")
    if not twitter:
        total_penalty += 20
    else:
        from utils import is_valid_twitter
        if not is_valid_twitter(twitter):
            total_penalty += 10
    return min(max(total_penalty, 0), 100)
