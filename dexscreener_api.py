import asyncio
import httpx
import json
import time
from datetime import datetime, timezone
from aiolimiter import AsyncLimiter

# Make sure to use your bot's logger
from bot_logger import logger
from state_manager import GlobalState
from database_handler import DatabaseClient

# --- API Configuration and Rate Limit Management ---
DEXSCREENER_API_BASE_URL = "https://api.dexscreener.com/token-pairs/v1/solana"
TARGET_RPM = 280
RATE_LIMIT_SAFETY_FACTOR = 1.1

# --- Cooldown Logic Constants ---
CONSECUTIVE_429_THRESHOLD = 5
COOLDOWN_MINUTES = 3

# --- START OF CHANGE ---
# The minimum time to wait between the end of one polling cycle and the start of the next.
MIN_CYCLE_WAIT_SECONDS = 5.0
# --- END OF CHANGE ---

class DexscreenerFetcher:
    def __init__(self, state: GlobalState, db_client: DatabaseClient):
        self.state = state
        self.db = db_client
        self.limiter = AsyncLimiter(TARGET_RPM, 60)
        self.client = httpx.AsyncClient(timeout=20.0)

        self._consecutive_429_errors = 0
        self._cooldown_until_timestamp = 0

    async def _get_migrated_tokens(self) -> list[str]:
        query = "SELECT mint FROM tokens WHERE data_source = 'DEXSCREENER' AND is_active = TRUE"
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [row['mint'] for row in rows]

    async def _fetch_data_for_token(self, token_address: str) -> list | None:
        if not token_address:
            return None
        
        url = f"{DEXSCREENER_API_BASE_URL}/{token_address}"
        
        try:
            async with self.limiter:
                response = await self.client.get(url)
            
            if response.status_code == 429:
                logger.warning(f"DEXScreener API returned HTTP 429 (Rate Limited) for {token_address}.")
                self._consecutive_429_errors += 1
                return None

            response.raise_for_status()
            
            self._consecutive_429_errors = 0
            
            data = response.json()
            
            pairs = None
            if isinstance(data, dict):
                pairs = data.get("pairs")
            elif isinstance(data, list):
                #logger.debug(f"API for {token_address} returned a direct list. Using it as the pairs data.")
                pairs = data

            if isinstance(pairs, list):
                return pairs
            else:
                logger.warning(f"DEX Screener response for {token_address} not in expected format or no pairs found. Response: {str(data)[:500]}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"DEXScreener API HTTP error for {token_address}: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"DEXScreener API unexpected error for {token_address}: {e}", exc_info=True)
        
        return None

    def _parse_pair_data(self, pair: dict, sol_price_usd: float) -> tuple | None:
        try:
            base_token = pair.get('baseToken', {})
            mint_address = base_token.get('address')
            if not mint_address: return None
            
            txns, volume, price_change, liquidity = (pair.get(k, {}) for k in ['txns', 'volume', 'priceChange', 'liquidity'])
            m5, h1, h6, h24 = (txns.get(k, {}) for k in ['m5', 'h1', 'h6', 'h24'])
            
            return (
                pair.get('pairAddress'), mint_address, datetime.now(timezone.utc),
                float(pair.get('priceUsd', 0)), float(pair.get('priceNative', 0)), sol_price_usd,
                liquidity.get('usd', 0), pair.get('marketCap', 0), pair.get('fdv', 0),
                volume.get('m5', 0), volume.get('h1', 0), volume.get('h6', 0), volume.get('h24', 0),
                price_change.get('m5', 0), price_change.get('h1', 0), price_change.get('h6', 0), price_change.get('h24', 0),
                m5.get('buys', 0), m5.get('sells', 0), h1.get('buys', 0), h1.get('sells', 0),
                h6.get('buys', 0), h6.get('sells', 0), h24.get('buys', 0), h24.get('sells', 0),
                json.dumps(pair)
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error parsing pair data for mint {pair.get('baseToken',{}).get('address')}: {e}")
            return None

    async def _insert_data_batch(self, parsed_data: list):
        if not parsed_data: return
        query = """
            INSERT INTO dexscreener_data (
                pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
                liquidity_usd, market_cap, fdv,
                volume_m5, volume_h1, volume_h6, volume_h24,
                price_change_m5, price_change_h1, price_change_h6, price_change_h24,
                buys_m5, sells_m5, buys_h1, sells_h1,
                buys_h6, sells_h6, buys_h24, sells_h24,
                full_response
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26)
        """
        async with self.db.pool.acquire() as conn:
            await conn.executemany(query, parsed_data)
        #logger.debug(f"Saved {len(parsed_data)} new snapshots from DEX Screener to database.")

    async def run(self):
        """The main worker loop that polls each migrated token individually and handles rate-limiting with a cooldown."""
        logger.info("🚀 DEX Screener Fetcher worker started (Mode: Continuous Polling with Cooldown).")

        while not self.state.shutdown_event.is_set():
            try:
                # Cooldown Check
                if time.time() < self._cooldown_until_timestamp:
                    cooldown_remaining = self._cooldown_until_timestamp - time.time()
                    logger.info(f"DEX Screener is in cooldown due to rate-limiting. Resuming in {cooldown_remaining:.0f} seconds.")
                    await self.state.wait_or_interrupt(timeout=cooldown_remaining)
                    continue

                migrated_tokens = await self._get_migrated_tokens()
                
                if migrated_tokens:
                    logger.info(f"DEXScreener Fetcher: Starting new polling cycle for {len(migrated_tokens)} migrated tokens.")
                    
                    current_sol_price = await self.state.get_sol_price()
                    if not current_sol_price:
                        logger.warning("DEXScreener Fetcher: Cannot get SOL price from state. Using 0.0 for this cycle.")
                        current_sol_price = 0.0

                    for token_address in migrated_tokens:
                        if self.state.shutdown_event.is_set():
                            break

                        # Check for cooldown activation
                        if self._consecutive_429_errors >= CONSECUTIVE_429_THRESHOLD:
                            self._cooldown_until_timestamp = time.time() + (COOLDOWN_MINUTES * 60)
                            logger.error(f"DEXScreener API rate limit threshold reached ({self._consecutive_429_errors} consecutive 429s). Entering cooldown for {COOLDOWN_MINUTES} minutes.")
                            self._consecutive_429_errors = 0
                            break

                        all_pairs = await self._fetch_data_for_token(token_address)
                        
                        if not all_pairs:
                            logger.debug(f"No pairs returned from API for {token_address}. Skipping.")
                            continue
                        
                        valid_pairs_with_liquidity = [p for p in all_pairs if p.get('liquidity', {}).get('usd') is not None]

                        if not valid_pairs_with_liquidity:
                            logger.warning(f"No pairs with liquidity data found for {token_address} to determine primary pool.")
                            continue

                        primary_pair = max(valid_pairs_with_liquidity, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                        
                        logger.debug(f"Selected primary pair {primary_pair.get('pairAddress')} for {token_address} with ${primary_pair.get('liquidity',{}).get('usd',0):,.2f} liquidity.")

                        parsed_record = self._parse_pair_data(primary_pair, current_sol_price)
                        if parsed_record:
                             await self._insert_data_batch([parsed_record])
                else:
                    logger.debug("DEX Screener: No migrated tokens found to poll in this cycle.")

            except Exception as e:
                logger.error(f"Error in DEX Screener Fetcher worker loop: {e}", exc_info=True)
            
            if not (time.time() < self._cooldown_until_timestamp):
                # --- START OF CHANGE ---
                logger.debug(f"DEX Screener cycle complete. Waiting {MIN_CYCLE_WAIT_SECONDS}s before starting the next.")
                await self.state.wait_or_interrupt(timeout=MIN_CYCLE_WAIT_SECONDS)
                # --- END OF CHANGE ---
            
        logger.info("🛑 DEX Screener Fetcher worker shutting down.")