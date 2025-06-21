import asyncio
import httpx
import json
import math
from datetime import datetime, timezone
from aiolimiter import AsyncLimiter

# Make sure to use your bot's logger
from bot_logger import logger
from state_manager import GlobalState
from database_handler import DatabaseClient

# --- API Configuration and Rate Limit Management ---
DEXSCREENER_API_BASE_URL = "https://api.dexscreener.com/tokens/v1/solana"
TARGET_RPM = 280
ADDRESS_BATCH_SIZE = 30
DEFAULT_WORKER_INTERVAL_SECONDS = 60
RATE_LIMIT_SAFETY_FACTOR = 1.1 

class DexscreenerFetcher:
    def __init__(self, state: GlobalState, db_client: DatabaseClient):
        self.state = state
        self.db = db_client
        self.limiter = AsyncLimiter(TARGET_RPM, 60)
        self.client = httpx.AsyncClient(timeout=20.0)

    async def _get_migrated_tokens(self) -> list[str]:
        query = "SELECT mint FROM tokens WHERE data_source = 'DEXSCREENER' AND is_active = TRUE"
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [row['mint'] for row in rows]

    async def _fetch_data_for_batch(self, token_batch: list[str]) -> list:
        if not token_batch:
            return []
        token_addresses = ",".join(token_batch)
        url = f"{DEXSCREENER_API_BASE_URL}/{token_addresses}"
        
        try:
            async with self.limiter:
                #logger.debug(f"Requesting DEX Screener URL: {url}")
                response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            else:
                logger.warning(f"DEX Screener response not in expected format. Response: {str(data)[:500]}")
                return []
        except httpx.HTTPStatusError as e:
            logger.error(f"DEXScreener API HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"DEXScreener API unexpected error: {e}", exc_info=True)
        return []

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
        logger.debug(f"Saved {len(parsed_data)} new snapshots from DEX Screener to database.")

    async def run(self):
        """The main worker loop with dynamic polling interval."""
        logger.info("🚀 DEX Screener Fetcher worker started.")
        while not self.state.shutdown_event.is_set():
            sleep_interval = DEFAULT_WORKER_INTERVAL_SECONDS
            try:
                migrated_tokens = await self._get_migrated_tokens()
                if migrated_tokens:
                    logger.info(f"DEXScreener Fetcher: Found {len(migrated_tokens)} migrated tokens to poll.")
                    num_batches = math.ceil(len(migrated_tokens) / ADDRESS_BATCH_SIZE)
                    if num_batches > 0:
                        cycles_per_minute = math.floor(TARGET_RPM / num_batches)
                        if cycles_per_minute > 0:
                            sleep_interval = (60 / cycles_per_minute) * RATE_LIMIT_SAFETY_FACTOR
                        else:
                            time_per_batch = 60 / TARGET_RPM
                            sleep_interval = (time_per_batch * num_batches) * RATE_LIMIT_SAFETY_FACTOR
                    
                    logger.info(f"Dynamic poll interval set to {sleep_interval:.2f} seconds for this cycle.")
                    current_sol_price = await self.state.get_sol_price()
                    if not current_sol_price:
                        logger.warning("DEXScreener Fetcher: Cannot get SOL price from state. Using 0.0.")
                        current_sol_price = 0.0

                    for i in range(0, len(migrated_tokens), ADDRESS_BATCH_SIZE):
                        batch = migrated_tokens[i:i + ADDRESS_BATCH_SIZE]
                        api_pairs_data = await self._fetch_data_for_batch(batch)
                        if not api_pairs_data: continue
                        
                        pairs_by_token = {}
                        for pair in api_pairs_data:
                            mint = pair.get('baseToken', {}).get('address')
                            if mint:
                                if mint not in pairs_by_token: pairs_by_token[mint] = []
                                pairs_by_token[mint].append(pair)
                        
                        db_records_to_insert = []
                        for mint, pairs in pairs_by_token.items():
                            if not pairs: continue
                            primary_pair = max(pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                            parsed_record = self._parse_pair_data(primary_pair, current_sol_price)
                            if parsed_record: db_records_to_insert.append(parsed_record)
                        
                        await self._insert_data_batch(db_records_to_insert)
            except Exception as e:
                logger.error(f"Error in DEX Screener Fetcher worker loop: {e}", exc_info=True)
            await asyncio.sleep(max(sleep_interval, 2.0))
            
        logger.info("🛑 DEX Screener Fetcher worker shutting down.")