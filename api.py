"""
Handles external API interactions including fetching SOL price, RugCheck data,
and social data.
"""
import state
import asyncio
import json
from datetime import datetime
import httpx
from aiolimiter import AsyncLimiter
import aiosqlite

from config import RUGCHECK_RATE_LIMIT, SOL_PRICE_API_URL, RUGCHECK_API, DB_NAME
from logger import logger

# Rate limiter for RugCheck API calls
limiter = AsyncLimiter(max_rate=RUGCHECK_RATE_LIMIT, time_period=60)

async def update_sol_price():
    """
    Periodically fetches and updates the global SOL price from an external API.
    """
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(SOL_PRICE_API_URL)
                if response.status_code == 200:
                    data = response.json()
                    new_price = data.get("solana", {}).get("usd")
                    await state.state.set_sol_price(new_price)
                    logger.info(f"Updated Solana price: {await state.state.get_sol_price()} USD")
                else:
                    logger.error(f"Error fetching Solana price: {response.status_code}")
        except Exception as e:
            logger.error(f"Exception fetching Solana price: {e}")
        await asyncio.sleep(3600)


async def check_missing_rugcheck_data():
    """
    Queries the database for tokens that do not have corresponding RugCheck data,
    orders them by total trading volume (SOL amount) in descending order,
    and enqueues those token mints for RugCheck processing using a priority queue.
    """
    sol_price = await state.state.get_sol_price()
    if sol_price is None:
            logger.warning("SOL_PRICE not updated yet; skipping rugcheck prioritizing.")
            await asyncio.sleep(5)
            return None
    
    async with aiosqlite.connect(DB_NAME) as db:
        query = """
        SELECT t.mint, IFNULL(SUM(tr.sol_amount), 0) AS volume
        FROM tokens t
        LEFT JOIN rugcheck r ON t.mint = r.mint
        LEFT JOIN trades tr ON t.mint = tr.mint
        WHERE r.mint IS NULL
        GROUP BY t.mint
        ORDER BY volume DESC
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            if rows:
                for (mint, volume) in rows:
                    # Use negative volume so that higher volumes yield a higher priority.
                    priority = -volume
                    v = volume * sol_price
                    logger.info(f"Token {mint} missing RugCheck data with volume {v} SOL. Enqueuing with priority {priority}.")
                    await state.state.get_rugcheck_queue().put((priority, mint))
            else:
                logger.debug("All tokens have corresponding RugCheck data.")

async def rugcheck_worker():
    """
    Worker task that processes tokens from the RugCheck queue.
    For each token mint, fetches RugCheck data and stores it.
    If the fetch fails, the token is requeued for another attempt.
    """
    queue = state.state.get_rugcheck_queue()
    while not await state.state.get_shutdown():
        try:
            # Unpack the tuple: (priority, mint)
            priority, mint = await queue.get()
            success = await fetch_rugcheck_data(mint)
            if not success:
                logger.info(f"Requeuing {mint} for RugCheck due to failure.")
                await asyncio.sleep(5)
                # Requeue using the same priority or adjust if needed
                await queue.put((priority, mint))
            else:
                logger.debug(f"Successfully processed RugCheck for {mint}.")
            queue.task_done()
        except Exception as e:
            logger.error(f"RugCheck worker error: {e}")
            await asyncio.sleep(1)

async def refresh_rugcheck_queue():
    """
    Periodically refresh the RugCheck queue by clearing out any outdated entries and 
    re-inserting tokens missing RugCheck data with updated priorities based on current volume.
    """
    while not await state.state.get_shutdown():
        sol_price = await state.state.get_sol_price()
        if sol_price is None:
            logger.warning("SOL_PRICE not updated yet; skipping refresh of rugcheck queue.")
            await asyncio.sleep(5)
            continue

        queue = state.state.get_rugcheck_queue()
        
        # Clear the current queue
        while not queue.empty():
            try:
                queue.get_nowait()
                queue.task_done()
            except asyncio.QueueEmpty:
                break

        # Re-query the database for tokens missing RugCheck data
        async with aiosqlite.connect(DB_NAME) as db:
            query = """
            SELECT t.mint, IFNULL(SUM(tr.sol_amount), 0) AS volume
            FROM tokens t
            LEFT JOIN rugcheck r ON t.mint = r.mint
            LEFT JOIN trades tr ON t.mint = tr.mint
            WHERE r.mint IS NULL
            GROUP BY t.mint
            ORDER BY volume DESC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                if rows:
                    for (mint, volume) in rows:
                        # Use negative volume so that higher volume tokens have higher priority.
                        priority = -volume
                        v = volume * sol_price
                        logger.info(f"Refreshing: Token {mint} missing RugCheck data with volume {v} SOL. Enqueuing with priority {priority}.")
                        await queue.put((priority, mint))
                else:
                    logger.debug("All tokens have corresponding RugCheck data after refresh.")

        # Sleep for a set interval before the next refresh
        await asyncio.sleep(30)  # Adjust the refresh interval as needed


async def fetch_rugcheck_data(mint: str) -> bool:
    """
    Fetches RugCheck data for a given token and stores it in the database.
    Returns True if data was successfully stored, False otherwise.
    """
    async with limiter:
        try:
            async with httpx.AsyncClient() as client:
                url = f"{RUGCHECK_API}/{mint}/report"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    # You can add extra checks here if needed:
                    if not data or "score" not in data:
                        logger.warning(f"RugCheck data incomplete for {mint}")
                        return False

                    token = data.get("token") or {}
                    tokenMeta = data.get("tokenMeta") or {}
                    fileMeta = data.get("fileMeta") or {}
                    transferFee = data.get("transferFee") or {}
                    risks = data.get("risks", [])
                    if risks and isinstance(risks, list):
                        if isinstance(risks[0], dict):
                            risks = json.dumps(risks)
                        else:
                            risks = ",".join(risks)
                    else:
                        risks = None
                    full_data = json.dumps(data)
                    async with aiosqlite.connect(DB_NAME) as db:
                        await db.execute('''INSERT OR REPLACE INTO rugcheck 
                                            (mint, tokenProgram, creator, token_mintAuthority, token_supply,
                                             token_decimals, token_isInitialized, token_freezeAuthority,
                                             tokenMeta_name, tokenMeta_symbol, tokenMeta_uri, tokenMeta_mutable,
                                             tokenMeta_updateAuthority, freezeAuthority, mintAuthority, risks,
                                             score, fileMeta_description, fileMeta_name, fileMeta_symbol,
                                             fileMeta_image, totalMarketLiquidity, totalLPProviders, rugged,
                                             tokenType, transferFee_pct, transferFee_maxAmount, transferFee_authority,
                                             graphInsidersDetected, detectedAt, full_data, last_checked)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                            (mint,
                                             data.get("tokenProgram"),
                                             data.get("creator"),
                                             token.get("mintAuthority"),
                                             token.get("supply"),
                                             token.get("decimals"),
                                             token.get("isInitialized"),
                                             token.get("freezeAuthority"),
                                             tokenMeta.get("name"),
                                             tokenMeta.get("symbol"),
                                             tokenMeta.get("uri"),
                                             tokenMeta.get("mutable"),
                                             tokenMeta.get("updateAuthority"),
                                             data.get("freezeAuthority"),
                                             data.get("mintAuthority"),
                                             risks,
                                             data.get("score"),
                                             fileMeta.get("description"),
                                             fileMeta.get("name"),
                                             fileMeta.get("symbol"),
                                             fileMeta.get("image"),
                                             data.get("totalMarketLiquidity"),
                                             data.get("totalLPProviders"),
                                             data.get("rugged"),
                                             data.get("tokenType"),
                                             transferFee.get("pct"),
                                             transferFee.get("maxAmount"),
                                             transferFee.get("authority"),
                                             data.get("graphInsidersDetected"),
                                             data.get("detectedAt"),
                                             full_data,
                                             datetime.now().isoformat()))
                        await db.commit()
                    logger.debug(f"RugCheck data stored for {mint}")
                    return True
                else:
                    logger.warning(f"RugCheck API returned {response.status_code} for {mint}")
                    return False
        except Exception as e:
            logger.error(f"Error fetching RugCheck data for {mint}: {e}")
            return False

async def fetch_social_data(uri: str, token_name: str, token_symbol: str):
    """
    Fetches social data from a given URI and computes a social score.
    Returns a tuple: (social_data, social_score)
    """
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
                logger.warning(f"Failed to fetch social data for URI {uri}: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching social data for {uri}: {e}")
    social_score = calculate_social_score(social_data, token_name, token_symbol)
    return social_data, social_score

def calculate_market_cap(vTokensInBondingCurve: float, vSolInBondingCurve: float, totalSupply: float) -> float:
    """
    Calculates the market cap of a token using bonding curve data.
    """
    if vTokensInBondingCurve <= 0 or totalSupply <= 0:
        return 0.0
    price_per_token = vSolInBondingCurve / vTokensInBondingCurve
    return price_per_token * totalSupply

def calculate_social_score(social_data: dict, token_name: str, token_symbol: str) -> int:
    """
    Computes a social risk score based on provided social data.
    Lower scores indicate better social presence.
    """
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
