import asyncio
import httpx
import json
import time
from datetime import datetime, timezone
from aiolimiter import AsyncLimiter
from typing import List

# Make sure to use your bot's logger
from bot_logger import logger
from state_manager import GlobalState
from database_handler import DatabaseClient

# --- API Configuration ---
# CORRECTED: Using the correct multi-token endpoint as per documentation
DEXSCREENER_API_BASE_URL = "https://api.dexscreener.com/tokens/v1/solana"
# DexScreener allows up to 30 token addresses per batch request
DEXSCREENER_BATCH_SIZE = 30

# --- Rate Limit and Cooldown Management ---
TARGET_RPM = 280  # Target requests per minute, well within typical limits
CONSECUTIVE_429_THRESHOLD = 3  # Lowered threshold for faster cooldown activation
COOLDOWN_MINUTES = 3
POLLING_INTERVAL_SECONDS = 30.0 # Interval between full polling cycles

class DexscreenerFetcher:
    def __init__(self, state: GlobalState, db_client: DatabaseClient):
        self.state = state
        self.db = db_client
        self.limiter = AsyncLimiter(TARGET_RPM, 60)
        self.client = httpx.AsyncClient(timeout=20.0)
        self._consecutive_429_errors = 0
        self._cooldown_until_timestamp = 0

    def _sanitize_for_comparison(self, data: dict) -> dict:
        """
        Removes volatile, non-market data keys from a response dictionary
        to allow for a meaningful comparison of market state.
        """
        sanitized_data = data.copy()
        # The 'info' key contains URLs with changing timestamps (e.g., for images),
        # which are not relevant for detecting a change in core market data.
        sanitized_data.pop('info', None)
        return sanitized_data

    async def _fetch_data_for_batch(self, token_batch: List[str]) -> List | None:
        """
        Fetches data for a batch of token addresses in a single API call.
        """
        if not token_batch:
            return None
        
        # Construct the URL with comma-separated token addresses
        url = f"{DEXSCREENER_API_BASE_URL}/{','.join(token_batch)}"
        
        try:
            async with self.limiter:
                response = await self.client.get(url)
            
            if response.status_code == 429:
                logger.warning(f"DEXScreener API returned HTTP 429 (Rate Limited) for batch starting with {token_batch[0]}.")
                self._consecutive_429_errors += 1
                return None

            response.raise_for_status()
            
            # Reset error count on a successful request
            self._consecutive_429_errors = 0
            
            data = response.json()
            
            # CORRECTED: The batch API returns a direct list of pair objects
            if isinstance(data, list):
                return data
            # Fallback for old endpoint format, just in case
            elif isinstance(data, dict) and "pairs" in data and isinstance(data["pairs"], list):
                logger.warning("DEXScreener API returned a dictionary with a 'pairs' key, but expected a direct list. Processing 'pairs' list anyway.")
                return data["pairs"]
            else:
                logger.warning(f"DEX Screener batch response not in expected list format. Response: {str(data)[:500]}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"DEXScreener API HTTP error for batch: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"DEXScreener API unexpected error for batch: {e}", exc_info=True)
        
        return None

    def _parse_pair_data(self, pair: dict, sol_price_usd: float) -> tuple | None:
        """
        Parses a single pair dictionary from the API response into a tuple for DB insertion.
        """
        try:
            base_token = pair.get('baseToken', {})
            mint_address = base_token.get('address')
            if not mint_address: return None
            
            txns = pair.get('txns', {})
            volume = pair.get('volume', {})
            price_change = pair.get('priceChange', {})
            liquidity = pair.get('liquidity', {})
            
            m5 = txns.get('m5', {})
            h1 = txns.get('h1', {})
            h6 = txns.get('h6', {})
            h24 = txns.get('h24', {})
            
            return (
                pair.get('pairAddress'), mint_address, datetime.now(timezone.utc),
                float(pair.get('priceUsd', 0)), float(pair.get('priceNative', 0)), sol_price_usd,
                liquidity.get('usd', 0), pair.get('marketCap', 0), pair.get('fdv', 0),
                volume.get('m5', 0), volume.get('h1', 0), volume.get('h6', 0), volume.get('h24', 0),
                price_change.get('m5', 0), price_change.get('h1', 0), price_change.get('h6', 0), price_change.get('h24', 0),
                m5.get('buys', 0), m5.get('sells', 0), h1.get('buys', 0), h1.get('sells', 0),
                h6.get('buys', 0), h6.get('sells', 0), h24.get('buys', 0), h24.get('sells', 0),
                json.dumps(pair) # Store the full original response
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error parsing pair data for mint {pair.get('baseToken',{}).get('address')}: {e}")
            return None

    async def _insert_data_batch(self, parsed_data: list):
        """
        Inserts a batch of parsed data into the dexscreener_data table.
        """
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

    async def _process_batch_response(self, pairs: List[dict]):
        """
        Processes a list of pairs from a batch API response, handling de-duplication
        and preparing data for insertion.
        """
        current_sol_price = await self.state.get_sol_price()
        if not current_sol_price:
            logger.warning("DEXScreener Processor: Cannot get SOL price from state. Using 0.0 for this batch.")
            current_sol_price = 0.0
            
        records_to_insert = []
        for pair_data in pairs:
            mint_address = pair_data.get('baseToken', {}).get('address')
            if not mint_address:
                continue

            # --- De-duplication Logic ---
            last_stored_response_str = await self.db.get_latest_dexscreener_response(mint_address)
            has_changed = True # Default to true if no previous data exists
            if last_stored_response_str:
                try:
                    last_stored_dict = json.loads(last_stored_response_str)
                    sanitized_last = self._sanitize_for_comparison(last_stored_dict)
                    sanitized_new = self._sanitize_for_comparison(pair_data)
                    if sanitized_last == sanitized_new:
                        has_changed = False
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse stored JSON for {mint_address}. Assuming data has changed.")

            if has_changed:
                #logger.debug(f"Data for {mint_address} has changed. Preparing for DB insert.")
                parsed_record = self._parse_pair_data(pair_data, current_sol_price)
                if parsed_record:
                    records_to_insert.append(parsed_record)
            # else:
            #     logger.debug(f"No meaningful data change for {mint_address}. Skipping database insert.")

        if records_to_insert:
            await self._insert_data_batch(records_to_insert)

    async def run(self):
        """The main worker loop that polls migrated tokens in batches."""
        logger.info("🚀 DEX Screener Fetcher worker started (Mode: Batch Processing).")

        while not self.state.shutdown_event.is_set():
            try:
                # --- Cooldown Check ---
                if time.time() < self._cooldown_until_timestamp:
                    cooldown_remaining = self._cooldown_until_timestamp - time.time()
                    logger.info(f"DEX Screener is in cooldown due to rate-limiting. Resuming in {cooldown_remaining:.0f} seconds.")
                    await self.state.wait_or_interrupt(timeout=cooldown_remaining)
                    continue

                # --- Fetch Tokens to Poll ---
                migrated_tokens = await self.db.get_all_migrated_tokens()
                
                if not migrated_tokens:
                    logger.debug("DEX Screener: No migrated tokens found. Waiting before next check.")
                    await self.state.wait_or_interrupt(timeout=POLLING_INTERVAL_SECONDS)
                    continue

                logger.debug(f"DEXScreener Fetcher: Starting new batch cycle for {len(migrated_tokens)} migrated tokens.")
                
                # --- Create Batches ---
                token_batches = [migrated_tokens[i:i + DEXSCREENER_BATCH_SIZE] for i in range(0, len(migrated_tokens), DEXSCREENER_BATCH_SIZE)]

                # --- Process Batches ---
                for batch in token_batches:
                    if self.state.shutdown_event.is_set():
                        break

                    # Check for cooldown activation before fetching
                    if self._consecutive_429_errors >= CONSECUTIVE_429_THRESHOLD:
                        self._cooldown_until_timestamp = time.time() + (COOLDOWN_MINUTES * 60)
                        logger.error(f"DEXScreener API rate limit threshold reached ({self._consecutive_429_errors} consecutive 429s). Entering cooldown for {COOLDOWN_MINUTES} minutes.")
                        self._consecutive_429_errors = 0
                        break # Break out of the batch loop to start cooldown

                    batch_pairs = await self._fetch_data_for_batch(batch)
                    
                    if batch_pairs:
                        await self._process_batch_response(batch_pairs)
                    else:
                        logger.debug(f"No pairs returned from API for batch starting with {batch[0]}. Skipping batch.")

                # --- Wait for Next Cycle ---
                if not (time.time() < self._cooldown_until_timestamp):
                    logger.debug(f"DEX Screener batch cycle complete. Waiting {POLLING_INTERVAL_SECONDS}s.")
                    await self.state.wait_or_interrupt(timeout=POLLING_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in DEX Screener Fetcher worker loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=60) # Longer wait on unexpected error
            
        logger.info("🛑 DEX Screener Fetcher worker shutting down.")
