"""
rugcheck.py - Manages fetching RugCheck data, prioritization, and processing.
"""

import asyncio
import os
import json
import time
from datetime import datetime, timezone
import traceback
import httpx
import base58
from dotenv import load_dotenv
from aiolimiter import AsyncLimiter
from decimal import Decimal
from solders.keypair import Keypair # type: ignore

from config.config import (
    _RUGCHECK_AUTH_API, _RUGCHECK_RATE_LIMIT, _RUGCHECK_API, _RUGCHECK_INTERVAL,
    RUGCHECK_SCORE_THRESHOLD
)
from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState
from connectors.websocket_handler import WebSocketHandler
from socials_processor import SocialsProcessor

# --- Configuration for Retries & Maintenance ---
MAX_FETCH_ATTEMPTS = 2  # Initial attempt + 1 retry
DEPRIORITIZED_PRIORITY = float('inf')
DEPRIORITIZED_TOKEN_MAX_AGE_SECONDS = 3600 # e.g., 1 hour: Time after which a deprioritized token might be culled
DEPRIORITIZED_TOKEN_MAX_REPROCESS_ATTEMPTS = 3 # Max times a deprioritized token can be picked from queue and re-attempted before culling
RUGCHECK_REQUEST_TIMEOUT = 20.0
RUGCHECK_MAINTENANCE_URL = "https://api.rugcheck.xyz/v1/maintenance"
MAINTENANCE_CHECK_TIMEOUT = 10.0
CONSECUTIVE_API_ERROR_LIMIT_FOR_MAINTENANCE_CHECK = 5 # How many /report errors trigger maintenance check
MAINTENANCE_MODE_RECHECK_INTERVAL_SECONDS = 600  # 5 minutes
MAINTENANCE_ENDPOINT_FAILURES_THRESHOLD = 3 # How many times maintenance endpoint must fail to assume active maintenance

class Rugcheck:
    def __init__(self, state: GlobalState, db_client: DatabaseClient, websocket_handler: WebSocketHandler, socials_processor: SocialsProcessor, config_dict: dict):
        self.state = state
        self.config = config_dict
        self.db_client = db_client
        self.websocket_handler = websocket_handler
        self.limiter = AsyncLimiter(max_rate=_RUGCHECK_RATE_LIMIT, time_period=_RUGCHECK_INTERVAL)
        self.queue = self.state.get_rugcheck_queue()
        self.fetch_attempts = {}
        self.deprioritized_tokens_tracker = {} # Stores {mint: {'first_deprio_timestamp': datetime, 'reprocess_count': int}}
        self.jwt_token: str | None = None
        self.wallet: Keypair | None = None

        # --- NEW State Variables for Maintenance Handling ---
        self.maintenance_mode_active = False
        self.consecutive_api_errors = 0 # For the main /report endpoint
        self.consecutive_maintenance_check_failures = 0
        # ---

        load_dotenv()
        private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
        if private_key_str:
            try:
                self.wallet = Keypair.from_base58_string(private_key_str)
                logger.info("🔑 Solana wallet loaded successfully for RugCheck authentication.")
            except Exception as e:
                logger.error(f"❌ Failed to load Solana wallet from private key: {e}")
                self.wallet = None
        else:
            logger.warning("⚠️ SOLANA_PRIVATE_KEY not set. RugCheck API calls will be unauthenticated.")

    def _sign_message(self, message: str) -> dict | None:
        if not self.wallet:
            logger.error("Cannot sign message: Wallet not loaded.")
            return None
        try:
            message_bytes = message.encode("utf-8")
            signature = self.wallet.sign_message(message_bytes)
            signature_base58 = str(signature)
            signature_data = list(base58.b58decode(signature_base58))
            return {
                "data": signature_data,
                "type": "ed25519",
            }
        except Exception as e:
            logger.error(f"❌ Error signing message: {e}", exc_info=True)
            return None

    async def _login_to_rugcheck(self) -> bool:
        if not self.wallet:
            logger.warning("Skipping RugCheck login: Wallet not loaded.")
            return False
        logger.info("🔑 Attempting to login to RugCheck API...")
        try:
            message_data = {
                "message": "Sign-in to Rugcheck.xyz",
                "timestamp": int(time.time() * 1000),
                "publicKey": str(self.wallet.pubkey()),
            }
            message_json = json.dumps(message_data, separators=(',', ':'))
            signature = self._sign_message(message_json)
            if not signature: return False
            payload = {"signature": signature, "wallet": str(self.wallet.pubkey()), "message": message_data}
            async with httpx.AsyncClient(timeout=RUGCHECK_REQUEST_TIMEOUT) as client:
                response = await client.post(_RUGCHECK_AUTH_API, headers={"Content-Type": "application/json"}, json=payload)
            if response.status_code == 200:
                self.jwt_token = response.json().get("token")
                if self.jwt_token:
                    logger.info("✅ RugCheck API login successful.")
                    return True
                logger.error("❌ RugCheck login response missing token.")
            else:
                logger.error(f"❌ Failed to login to RugCheck API: {response.status_code} - {response.text}")
            self.jwt_token = None
            return False
        except httpx.TimeoutException:
             logger.error(f"⏳ Timeout during RugCheck API login.")
        except Exception as e:
            logger.error(f"❌ Unexpected error during RugCheck API login: {e}", exc_info=True)
        self.jwt_token = None
        return False

    async def _check_api_maintenance_status(self):
        """Checks the RugCheck API maintenance status."""
        logger.debug("Checking RugCheck API maintenance status...")
        try:
            async with httpx.AsyncClient(timeout=MAINTENANCE_CHECK_TIMEOUT) as client:
                response = await client.get(RUGCHECK_MAINTENANCE_URL)

            # According to user's example, 200 OK with empty body means "pong" (service up)
            if response.status_code == 200: # Allow empty body or specific message
                try:
                    data = response.json() # Try to parse JSON
                    message = data.get("message", "")
                    logger.info(f"RugCheck API maintenance check OK (Status: {response.status_code}, Message: '{message}'). Service is responsive.")
                except json.JSONDecodeError: # Handle empty body case
                    if response.headers.get('content-length') == '0':
                         logger.info(f"RugCheck API maintenance check OK (Status: {response.status_code}, Empty Body). Service is responsive.")
                    else: # Non-empty but invalid JSON
                        logger.warning(f"RugCheck API maintenance check returned 200 but with invalid JSON body: {response.text[:100]}")
                        # Treat as a failure for our check
                        self.consecutive_maintenance_check_failures += 1

                if self.consecutive_maintenance_check_failures == 0 or response.status_code == 200 : # if it was a json error above, but status 200, still reset
                    self.maintenance_mode_active = False
                    self.consecutive_maintenance_check_failures = 0

            else: # Any other status code is treated as a potential issue
                logger.warning(f"RugCheck API maintenance check failed or indicated issue: Status {response.status_code} - {response.text}")
                self.consecutive_maintenance_check_failures += 1

        except httpx.TimeoutException:
            logger.error("⏳ Timeout checking RugCheck API maintenance status.")
            self.consecutive_maintenance_check_failures += 1
        except httpx.RequestError as e:
            logger.error(f"❌ Request error checking RugCheck API maintenance status: {e}")
            self.consecutive_maintenance_check_failures += 1
        except Exception as e:
            logger.error(f"❌ Unexpected error checking RugCheck API maintenance status: {e}", exc_info=True)
            self.consecutive_maintenance_check_failures += 1

        if self.consecutive_maintenance_check_failures >= MAINTENANCE_ENDPOINT_FAILURES_THRESHOLD:
            if not self.maintenance_mode_active: # Log only when it transitions to active
                logger.error(f"🚨 RugCheck API assumed to be in maintenance/unavailable after {self.consecutive_maintenance_check_failures} failed checks to maintenance endpoint. Pausing Rugcheck tasks.")
            self.maintenance_mode_active = True
        elif self.maintenance_mode_active and self.consecutive_maintenance_check_failures == 0 : # If it was active, but now check passes
            logger.info("✅ RugCheck API maintenance mode appears to have ended.")
            self.maintenance_mode_active = False


    # async def _refresh_queue(self):
    #     try:
    #         # (Existing refresh queue logic - seems okay, respects MAX_FETCH_ATTEMPTS)
    #         # ... (ensure it's the same as in the provided code)
    #         sol_price = await self.state.get_sol_price()
    #         if sol_price is None:
    #             logger.warning("⚠ SOL_PRICE not updated yet; skipping RugCheck queue refresh.")
    #             return False

    #         while not self.queue.empty():
    #             try:
    #                 self.queue.get_nowait()
    #                 self.queue.task_done()
    #             except asyncio.QueueEmpty: break
    #             except Exception as e: logger.error(f"Error clearing rugcheck queue item: {e}")

    #         async with self.db_client.pool.acquire() as conn:
    #             rows = await conn.fetch("""
    #                 SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
    #                 FROM tokens t
    #                 LEFT JOIN rugcheck r ON t.mint = r.mint
    #                 LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '15 minutes'
    #                 WHERE t.is_active = TRUE AND r.mint IS NULL
    #                 GROUP BY t.mint
    #                 ORDER BY volume DESC
    #             """)
    #             logger.debug(f"🔍 Found {len(rows)} active tokens missing RugCheck data for refresh.")
    #             if rows:
    #                 tokens_added = 0
    #                 for row in rows:
    #                     mint, volume = row["mint"], row["volume"] or Decimal(0)
    #                     priority = -float(volume)
    #                     current_attempts = self.fetch_attempts.get(mint, 0)
    #                     if current_attempts < MAX_FETCH_ATTEMPTS: # Respect MAX_FETCH_ATTEMPTS for high priority
    #                          await self.queue.put((priority, mint))
    #                          tokens_added += 1
    #                 logger.debug(f"🔄 Refreshed RugCheck queue. Added {tokens_added} tokens (current size: {self.queue.qsize()}).")
    #         return True
    #     except Exception as e:
    #         logger.error(f"❌ Critical error in _refresh_queue: {e}", exc_info=True)
    #         return False
    async def _refresh_queue(self):
        try:
            sol_price = await self.state.get_sol_price()
            if sol_price is None:
                logger.warning("⚠ SOL_PRICE not updated yet; skipping RugCheck queue refresh.")
                return False

            # Clear existing queue
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except asyncio.QueueEmpty: 
                    break
                except Exception as e: 
                    logger.error(f"Error clearing rugcheck queue item: {e}")

            async with self.db_client.pool.acquire() as conn:
                # Updated query with new priority formula
                rows = await conn.fetch("""
                    WITH ranked_tokens AS (
                        SELECT 
                            t.mint,
                            t.timestamp,
                            COALESCE(SUM(tr.sol_amount), 0) AS total_volume,
                            COALESCE(SUM(CASE WHEN tr.tx_type = 'buy' THEN tr.sol_amount END), 0) AS buy_volume,
                            ROW_NUMBER() OVER (ORDER BY t.timestamp ASC) AS row_num
                        FROM tokens t
                        LEFT JOIN rugcheck r ON t.mint = r.mint
                        LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '15 minutes'
                        WHERE t.is_active = TRUE AND r.mint IS NULL
                        GROUP BY t.mint, t.timestamp
                    )

                    SELECT 
                        mint,
                        (total_volume + buy_volume + (1.0 - row_num * 0.001)) AS priority_score
                    FROM ranked_tokens;
                """)
                
                logger.debug(f"🔍 Found {len(rows)} active tokens missing RugCheck data for refresh.")
                if rows:
                    tokens_added = 0
                    for row in rows:
                        mint = row["mint"]
                        priority_score = row["priority_score"] or Decimal(0)
                        
                        # Convert to negative for min-heap priority queue
                        # Higher priority_score = higher urgency = more negative value
                        priority = -float(priority_score)
                        
                        current_attempts = self.fetch_attempts.get(mint, 0)
                        if current_attempts < MAX_FETCH_ATTEMPTS:
                            await self.queue.put((priority, mint))
                            tokens_added += 1
                            
                    logger.debug(f"🔄 Refreshed RugCheck queue. Added {tokens_added} tokens (current size: {self.queue.qsize()}).")
            return True
        except Exception as e:
            logger.error(f"❌ Critical error in _refresh_queue: {e}", exc_info=True)
            return False

    async def _fetch_and_store_data(self, mint: str, is_retry: bool = False) -> dict | None | str:
        """
        Fetches RugCheck data from the API and stores it in the database.
        Returns:
            - dict: The fetched data on success.
            - 'NOT_FOUND': If the API returns 404.
            - 'TIMEOUT': If the API request times out.
            - None: On other errors (invalid JSON, DB error, other HTTP errors, etc.).
        """
        url = f"{_RUGCHECK_API}/{mint}/report"
        response = None # Define response outside try block
        headers = {}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        else:
            logger.debug(f"Making unauthenticated RugCheck request for {mint}")

        try:
            async with httpx.AsyncClient(timeout=RUGCHECK_REQUEST_TIMEOUT) as client:
                logger.debug(f"📡 Fetching RugCheck for {mint} from {url}")
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data.get("error") == "failed to generate report cached": # Specific error check
                    logger.warning(f"⚠ RugCheck API for {mint} reported: failed to generate report cached.")
                    return 'GENERATION_ERROR'
                if not data or "score" not in data: # Basic validation
                    logger.warning(f"⚠ RugCheck data incomplete or invalid for {mint}. Response: {data}")
                    return 'GENERATION_ERROR' # Treat as generation error if data is bad

                # --- Store data in DB ---
                try:
                    token = data.get("token") or {}
                    tokenMeta = data.get("tokenMeta") or {}
                    fileMeta = data.get("fileMeta") or {}
                    transferFee = data.get("transferFee") or {}
                    # Ensure risks is stored as JSON string or NULL
                    risks_list = data.get("risks", [])
                    risks_json = json.dumps(risks_list) if isinstance(risks_list, list) else None
                    full_data_json = json.dumps(data) # Store the full response

                    detected_at = None
                    detected_at_str = data.get("detectedAt")
                    if detected_at_str:
                        try:
                            # Handle 'Z' and potential extra precision
                            detected_at_str = detected_at_str.replace('Z', '+00:00')
                            if '.' in detected_at_str:
                                base, fraction = detected_at_str.split('.', 1)
                                tz_part = ""
                                if '+' in fraction:
                                    fraction, tz_part = fraction.split('+', 1)
                                    tz_part = '+' + tz_part
                                elif '-' in fraction:
                                     fraction, tz_part = fraction.split('-', 1)
                                     tz_part = '-' + tz_part
                                detected_at_str = f"{base}.{fraction[:6]}{tz_part}" # Truncate microseconds
                            detected_at = datetime.fromisoformat(detected_at_str).astimezone(timezone.utc)
                        except ValueError as date_err:
                            logger.warning(f"Could not parse detectedAt '{data.get('detectedAt')}' for {mint}: {date_err}")
                            detected_at = datetime.now(timezone.utc) # Fallback

                    async with self.db_client.pool.acquire() as conn:
                        async with conn.transaction():
                            # --- START OF FIX ---
                            # This check runs *after* the API call and immediately before the insert,
                            # guaranteeing the token exists at the moment of the transaction.
                            token_exists = await conn.fetchval(
                                "SELECT 1 FROM tokens WHERE mint = $1", mint
                            )

                            if not token_exists:
                                logger.info(
                                    f"Token {mint} was deleted from DB while its RugCheck data was being fetched. Aborting DB storage."
                                )
                                return 'TOKEN_DELETED_MID_FETCH' # Return a specific status
                            # --- END OF FIX ---
                            # 
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
                                ON CONFLICT (mint) DO UPDATE SET
                                    tokenProgram = EXCLUDED.tokenProgram, creator = EXCLUDED.creator,
                                    token_mintAuthority = EXCLUDED.token_mintAuthority, token_supply = EXCLUDED.token_supply,
                                    token_decimals = EXCLUDED.token_decimals, token_isInitialized = EXCLUDED.token_isInitialized,
                                    token_freezeAuthority = EXCLUDED.token_freezeAuthority, tokenMeta_name = EXCLUDED.tokenMeta_name,
                                    tokenMeta_symbol = EXCLUDED.tokenMeta_symbol, tokenMeta_uri = EXCLUDED.tokenMeta_uri,
                                    tokenMeta_mutable = EXCLUDED.tokenMeta_mutable, tokenMeta_updateAuthority = EXCLUDED.tokenMeta_updateAuthority,
                                    freezeAuthority = EXCLUDED.freezeAuthority, mintAuthority = EXCLUDED.mintAuthority,
                                    risks = EXCLUDED.risks, score = EXCLUDED.score, fileMeta_description = EXCLUDED.fileMeta_description,
                                    fileMeta_name = EXCLUDED.fileMeta_name, fileMeta_symbol = EXCLUDED.fileMeta_symbol,
                                    fileMeta_image = EXCLUDED.fileMeta_image, totalMarketLiquidity = EXCLUDED.totalMarketLiquidity,
                                    totalLPProviders = EXCLUDED.totalLPProviders, rugged = EXCLUDED.rugged,
                                    tokenType = EXCLUDED.tokenType, transferFee_pct = EXCLUDED.transferFee_pct,
                                    transferFee_maxAmount = EXCLUDED.transferFee_maxAmount, transferFee_authority = EXCLUDED.transferFee_authority,
                                    graphInsidersDetected = EXCLUDED.graphInsidersDetected, detectedAt = EXCLUDED.detectedAt,
                                    full_data = EXCLUDED.full_data, last_checked = NOW()
                            ''',
                                mint, data.get("tokenProgram"), data.get("creator"),
                                token.get("mintAuthority"), token.get("supply"),
                                token.get("decimals"), token.get("isInitialized"),
                                token.get("freezeAuthority"), tokenMeta.get("name"),
                                tokenMeta.get("symbol"), tokenMeta.get("uri"),
                                tokenMeta.get("mutable"), tokenMeta.get("updateAuthority"),
                                data.get("freezeAuthority"), data.get("mintAuthority"),
                                risks_json, data.get("score"), fileMeta.get("description"),
                                fileMeta.get("name"), fileMeta.get("symbol"), fileMeta.get("image"),
                                data.get("totalMarketLiquidity"), data.get("totalLPProviders"),
                                data.get("rugged"), data.get("tokenType"),
                                transferFee.get("pct"), transferFee.get("maxAmount"),
                                transferFee.get("authority"), data.get("graphInsidersDetected"),
                                detected_at, full_data_json
                            )
                    logger.debug(f"💾 RugCheck data stored/updated for {mint}")
                    return data # Return fetched data for score checking
                except Exception as db_err:
                    logger.error(f"❌ DB Error storing RugCheck for {mint}: {db_err}", exc_info=True)
                    return 'DB_INSERT_ERROR'

            elif response.status_code == 404:
                logger.warning(f"❓ RugCheck API returned 404 (Not Found) for {mint}. Maybe too new?")
                return 'NOT_FOUND' # Specific status for 404
            elif response.status_code in [401, 403]:
                 logger.warning(f"🔑 RugCheck API returned {response.status_code} (Authorization Error) for {mint}.")
                 self.jwt_token = None
                 if not is_retry: # Only attempt re-login once per call chain
                     if await self._login_to_rugcheck():
                         logger.info(f"Re-login successful. Retrying fetch for {mint} (original attempt).")
                         return await self._fetch_and_store_data(mint, is_retry=True) # Mark as retry within this fetch
                 return 'AUTH_ERROR' # Persistent auth error
            else: # Other HTTP errors (e.g., 5xx)
                logger.warning(f"⚠ RugCheck API returned HTTP {response.status_code} for {mint}. Response: {response.text}")
                return 'HTTP_ERROR'

        except httpx.TimeoutException:
            logger.error(f"⏳ Timeout fetching RugCheck data for {mint}")
            return 'TIMEOUT'
        except httpx.RequestError as req_err: # Covers connection errors, DNS errors etc.
            logger.error(f"❌ HTTP Request Error fetching RugCheck for {mint}: {req_err}")
            return 'REQUEST_ERROR'
        except json.JSONDecodeError as json_err:
            response_text = response.text if response else "N/A"
            logger.error(f"❌ JSON Decode Error for RugCheck response {mint}: {json_err}. Response: {response_text[:100]}")
            return 'GENERATION_ERROR' # Treat as bad data from API
        except Exception as e:
            logger.error(f"❌ Unexpected Error fetching RugCheck data for {mint}: {e}", exc_info=True)
            return None # Unexpected internal error

    async def _process_token(self, mint: str) -> bool | str:
        """
        Fetches, stores, and processes RugCheck data for a single token.
        Returns:
            - True: If processing was successful (data fetched/stored, score checked, deactivation handled).
            - 'NOT_FOUND': If the fetch attempt resulted in a 404 from the API.
            - 'TIMEOUT': If the fetch attempt resulted in a timeout.
            - False: If there was another error during fetching, storing, or processing.
        """
        fetch_result = await self._fetch_and_store_data(mint)

        if isinstance(fetch_result, str): # 'NOT_FOUND', 'TIMEOUT', 'GENERATION_ERROR', etc.
            return fetch_result # Propagate API/fetch error status

        if fetch_result is None or fetch_result == 'DB_INSERT_ERROR': # Unexpected internal error or DB error
            logger.warning(f"Processing failed for {mint}: Could not fetch/store RugCheck data due to error: {fetch_result}")
            return False # Indicate unrecoverable internal/DB error for this attempt

        # --- Score Check and Deactivation (if data was fetched successfully as dict) ---
        fetched_data = fetch_result # Known to be a dict here
        score = fetched_data.get("score")
        # RUGCHECK_SCORE_THRESHOLD is from config.py, accessed via self.config
        if score is not None and score > self.config.get('RUGCHECK_SCORE_THRESHOLD', 1002):
            logger.debug(f"🚨 High RugCheck score ({score} > {self.config['RUGCHECK_SCORE_THRESHOLD']}) for {mint}. Deactivating.")
            try:
                async with self.db_client.pool.acquire() as conn:
                    await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                if self.websocket_handler.websocket and self.websocket_handler.websocket.open:
                    is_subscribed = mint in self.state.active_token_subscriptions
                    if is_subscribed:
                        await self.state.remove_token_subscription(mint) # Updates state and file
                        await asyncio.wait_for(self.websocket_handler.websocket.send(json.dumps({
                            "method": "unsubscribeTokenTrade", "keys": [mint]
                        })), timeout=5.0)
                        logger.debug(f"[bold]:hot_pepper: Too spicy:[/bold] Sent unsubscribe for high-score token {mint}")
                await self.db_client.backup_and_delete_token(mint=mint, archived_at=datetime.now(timezone.utc), reason="high_rugcheckscore")
                return True # Processed successfully (even if deactivation had minor issue, fetch was good)
            except Exception as deactivation_err:
                logger.error(f"❌ Error during deactivation for high-score token {mint}: {deactivation_err}", exc_info=True)
                return True # Still return True as fetch/store part was okay for the token itself
        else:
            logger.debug(f"✅ RugCheck score OK for {mint} (Score: {score})")
            # Socials processing can be triggered here if needed, or remain separate
            return True # Processed successfully

    async def _worker(self):
        logger.info("🚀 RugCheck worker started.")
        last_refresh_time = 0
        refresh_interval = self.config.get('_RUGCHECK_INTERVAL', _RUGCHECK_INTERVAL) / 2

        if self.wallet:
            await self._login_to_rugcheck()

        while not self.state.shutdown_event.is_set():
            task_completed_in_loop = False
            priority = None
            mint = None
            try:
                if self.maintenance_mode_active:
                    logger.info(f"🚨 RugCheck worker paused due to active maintenance mode. Re-checking API status in {MAINTENANCE_MODE_RECHECK_INTERVAL_SECONDS}s.")
                    await self.state.wait_or_interrupt(timeout=MAINTENANCE_MODE_RECHECK_INTERVAL_SECONDS)
                    await self._check_api_maintenance_status()
                    continue

                current_time_loop_start = asyncio.get_event_loop().time()
                if self.queue.empty() or (current_time_loop_start - last_refresh_time > refresh_interval):
                    logger.debug("🔄 Triggering RugCheck queue refresh...")
                    if await self._refresh_queue():
                        last_refresh_time = current_time_loop_start
                    else:
                        await self.state.wait_or_interrupt(timeout=5)
                        continue

                if self.queue.empty():
                    await self.state.wait_or_interrupt(timeout=1)
                    continue

                try:
                    priority, mint = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                except Exception as q_err:
                    logger.error(f"Error getting item from rugcheck queue: {q_err}"); continue

                # --- CULLING LOGIC FOR DEPRIORITIZED TOKENS ---
                if priority == DEPRIORITIZED_PRIORITY and mint in self.deprioritized_tokens_tracker:
                    tracker_entry = self.deprioritized_tokens_tracker[mint]
                    tracker_entry['reprocess_count'] += 1 # Increment reprocess attempts for this deprioritized token
                    age_seconds = (datetime.now(timezone.utc) - tracker_entry['first_deprio_timestamp']).total_seconds()

                    cull_reason = None
                    if age_seconds > DEPRIORITIZED_TOKEN_MAX_AGE_SECONDS:
                        cull_reason = f"exceeded max age ({DEPRIORITIZED_TOKEN_MAX_AGE_SECONDS}s)"
                    elif tracker_entry['reprocess_count'] > DEPRIORITIZED_TOKEN_MAX_REPROCESS_ATTEMPTS:
                        cull_reason = f"exceeded max reprocess attempts ({DEPRIORITIZED_TOKEN_MAX_REPROCESS_ATTEMPTS})"

                    if cull_reason:
                        logger.warning(f"🧹 Culling deprioritized token {mint} due to {cull_reason} for RugCheck.")
                        # Perform culling actions
                        try:
                            if self.websocket_handler and self.websocket_handler.websocket and self.websocket_handler.websocket.open:
                                async with self.state.lock: # Ensure atomicity for subscription state
                                    if mint in self.state.active_token_subscriptions:
                                        self.state.active_token_subscriptions.discard(mint)
                                        self.state._save_subscriptions_to_file()
                                try: # Send unsubscribe even if state update fails, though unlikely
                                    await asyncio.wait_for(self.websocket_handler.websocket.send(json.dumps({
                                        "method": "unsubscribeTokenTrade", "keys": [mint]
                                    })), timeout=5.0)
                                    logger.info(f"🧹 Culled {mint}: Unsubscribed from WebSocket due to persistent RugCheck issues.")
                                except Exception as ws_err:
                                    logger.error(f"Error unsubscribing culled token {mint} from WebSocket: {ws_err}")

                            await self.db_client.backup_and_delete_token(mint=mint, archived_at=datetime.now(timezone.utc), reason="rugcheck_error_culled")
                            logger.info(f"🧹 Culled {mint}: Backed up and deleted from DB with reason 'rugcheck_error_culled'.")
                        except Exception as e:
                            logger.error(f"Error during culling operations for deprioritized token {mint}: {e}", exc_info=True)
                        finally:
                            self.fetch_attempts.pop(mint, None) # Clean up attempt counter
                            self.deprioritized_tokens_tracker.pop(mint, None) # Clean up tracker
                            self.queue.task_done(); task_completed_in_loop = True
                            continue # Move to the next token

                # --- REGULAR PROCESSING ---
                async with self.limiter:
                    async with self.db_client.pool.acquire() as conn: # Use specific connection for DB check
                        is_active = await conn.fetchval("SELECT is_active FROM tokens WHERE mint = $1", mint)

                    if not is_active:
                        logger.debug(f"Token {mint} no longer active or exists. Skipping RugCheck.")
                        self.fetch_attempts.pop(mint, None)
                        self.deprioritized_tokens_tracker.pop(mint, None) # Also remove from deprio tracker if it became inactive
                        self.queue.task_done(); task_completed_in_loop = True
                        continue

                    process_status = await self._process_token(mint)
                    task_completed_in_loop = True

                    retryable_api_error_statuses = ['TIMEOUT', 'GENERATION_ERROR', 'HTTP_ERROR', 'REQUEST_ERROR']

                    if process_status is True:
                        self.fetch_attempts.pop(mint, None)
                        self.deprioritized_tokens_tracker.pop(mint, None) # Remove if successfully processed
                        self.consecutive_api_errors = 0
                    elif process_status in retryable_api_error_statuses:
                        self.consecutive_api_errors += 1
                        if self.consecutive_api_errors >= CONSECUTIVE_API_ERROR_LIMIT_FOR_MAINTENANCE_CHECK:
                            logger.warning(f"{self.consecutive_api_errors} consecutive API errors on /report. Checking API maintenance status...")
                            await self._check_api_maintenance_status()

                        current_attempts = self.fetch_attempts.get(mint, 0) + 1
                        self.fetch_attempts[mint] = current_attempts
                        logger.warning(f"🔄 RugCheck API failed for {mint} ({process_status}). Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")
                        if current_attempts < MAX_FETCH_ATTEMPTS:
                            await self.queue.put((priority, mint))
                        else: # Max attempts reached for this error type
                            await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                            logger.warning(f"Max fetch attempts ({MAX_FETCH_ATTEMPTS}) reached for {mint} due to {process_status}. Deprioritizing.")
                            if mint not in self.deprioritized_tokens_tracker: # Start tracking for culling
                                self.deprioritized_tokens_tracker[mint] = {'first_deprio_timestamp': datetime.now(timezone.utc), 'reprocess_count': 0}
                    elif process_status == 'NOT_FOUND':
                        current_attempts = self.fetch_attempts.get(mint, 0) + 1
                        self.fetch_attempts[mint] = current_attempts
                        logger.warning(f"❓ RugCheck API 404 for {mint}. Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")
                        if current_attempts < MAX_FETCH_ATTEMPTS:
                            await self.queue.put((priority, mint))
                        else:
                            await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                            logger.warning(f"Max 404 attempts for {mint}. Deprioritizing.")
                            if mint not in self.deprioritized_tokens_tracker: # Start tracking for culling
                                self.deprioritized_tokens_tracker[mint] = {'first_deprio_timestamp': datetime.now(timezone.utc), 'reprocess_count': 0}
                        self.consecutive_api_errors = 0
                    elif process_status == 'AUTH_ERROR':
                        logger.error(f"🔑 Persistent RugCheck Auth Error for {mint}. Deprioritizing and marking max attempts.")
                        await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                        self.fetch_attempts[mint] = MAX_FETCH_ATTEMPTS
                        if mint not in self.deprioritized_tokens_tracker: # Start tracking for culling
                            self.deprioritized_tokens_tracker[mint] = {'first_deprio_timestamp': datetime.now(timezone.utc), 'reprocess_count': 0}
                        self.consecutive_api_errors = 0
                    elif process_status is False or process_status == 'DB_INSERT_ERROR':
                        logger.error(f"📉 RugCheck processing internal/DB error for {mint} (Status: {process_status}). Requeuing with original priority.")
                        await self.queue.put((priority, mint))
                        self.fetch_attempts.pop(mint, None) # Not an API fetch issue for this token
                        self.deprioritized_tokens_tracker.pop(mint, None) # Remove if it was being tracked

                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("⏹ RugCheck worker task cancelled.")
                if mint: 
                    try: self.queue.task_done()
                    except ValueError: pass
                break
            except Exception as e:
                logger.error(f"💥 Unexpected error in RugCheck worker main loop: {e}", exc_info=True)
                if mint and not task_completed_in_loop:
                    try: self.queue.task_done()
                    except ValueError: pass
                await self.state.wait_or_interrupt(timeout=10)

        logger.info("🛑 RugCheck worker shutting down.")
            
    def start(self) -> asyncio.Task:
        """Creates and returns the asyncio task for the RugCheck worker."""
        logger.info("Creating RugCheck background task...")
        # Ensure worker starts after initial setup (like wallet loading) is done
        return asyncio.create_task(self._worker(), name="rugcheck_worker")