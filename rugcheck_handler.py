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

from config import (
    _RUGCHECK_AUTH_API, _RUGCHECK_RATE_LIMIT, _RUGCHECK_API, _RUGCHECK_INTERVAL,
    RUGCHECK_SCORE_THRESHOLD # Import the threshold
)
from database_handler import DatabaseClient
from logger import logger
from state_manager import GlobalState
from websocket_handler import WebSocketHandler
from socials_processor import SocialsProcessor # Import the SocialsProcessor

# --- Configuration for Retries ---
MAX_FETCH_ATTEMPTS = 2 # Allow 2 attempts (initial + 1 retry)
DEPRIORITIZED_PRIORITY = float('inf') # Very low priority for requeueing after max attempts
RUGCHECK_REQUEST_TIMEOUT = 20.0 # Increased timeout for RugCheck API calls

class Rugcheck:
    # Accept SocialsProcessor instance during initialization
    def __init__(self, state: GlobalState, db_client: DatabaseClient, websocket_handler: WebSocketHandler, socials_processor: SocialsProcessor, config_dict: dict):
        self.state = state
        self.db_client = db_client
        self.websocket_handler = websocket_handler
        self.config = config_dict
        self.limiter = AsyncLimiter(max_rate=_RUGCHECK_RATE_LIMIT, time_period=_RUGCHECK_INTERVAL)
        self.queue = self.state.get_rugcheck_queue()
        #self.socials_processor = socials_processor
        self.fetch_attempts = {}
        self.jwt_token: str | None = None
        self.wallet: Keypair | None = None

        # Load wallet from environment variable
        load_dotenv()
        private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
        if private_key_str:
            try:
                self.wallet = Keypair.from_base58_string(private_key_str)
                logger.info("🔑 Solana wallet loaded successfully for RugCheck authentication.")
            except Exception as e:
                logger.error(f"❌ Failed to load Solana wallet from private key: {e}")
                self.wallet = None # Ensure wallet is None if loading fails
        else:
            logger.warning("⚠️ SOLANA_PRIVATE_KEY not set. RugCheck API calls will be unauthenticated.")

    # --- Authentication Methods ---

    def _sign_message(self, message: str) -> dict | None:
        """Signs a message using the loaded Solana wallet."""
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
        """Logs into RugCheck API using Solana wallet signature and stores the JWT."""
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

            if not signature:
                return False # Signing failed

            payload = {
                "signature": signature,
                "wallet": str(self.wallet.pubkey()),
                "message": message_data,
            }
            login_url = _RUGCHECK_AUTH_API
            logger.debug(f"🔑 Signing message for RugCheck login: {message_json}")

            async with httpx.AsyncClient(timeout=RUGCHECK_REQUEST_TIMEOUT) as client:
                response = await client.post(
                    login_url,
                    headers={"Content-Type": "application/json"},
                    json=payload, # Use json parameter for automatic serialization
                )

            if response.status_code == 200:
                response_data = response.json()
                self.jwt_token = response_data.get("token")
                if self.jwt_token:
                    logger.info("✅ RugCheck API login successful.")
                    return True
                else:
                    logger.error("❌ RugCheck login response missing token.")
                    self.jwt_token = None
                    return False
            else:
                logger.error(f"❌ Failed to login to RugCheck API: {response.status_code} - {response.text}")
                self.jwt_token = None
                return False
        except httpx.TimeoutException:
             logger.error(f"⏳ Timeout during RugCheck API login.")
             self.jwt_token = None
             return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during RugCheck API login: {e}", exc_info=True)
            self.jwt_token = None
            return False
        
    async def _refresh_queue(self):
        """Refreshes the RugCheck priority queue based on token volume."""
        try:
            sol_price = await self.state.get_sol_price()
            if sol_price is None:
                logger.warning("⚠ SOL_PRICE not updated yet; skipping RugCheck queue refresh.")
                return False # Indicate refresh skipped

            # Clear the current queue before repopulating
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.error(f"Error clearing rugcheck queue item: {e}")


            async with self.db_client.pool.acquire() as conn:
                # Fetch tokens that are active but don't have rugcheck data yet, ordered by volume
                # Note: Volatility isn't directly calculated here, using volume as proxy per original code.
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                    FROM tokens t
                    LEFT JOIN rugcheck r ON t.mint = r.mint
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour' -- Consider recent volume
                    WHERE t.is_active = TRUE AND r.mint IS NULL
                    GROUP BY t.mint
                    ORDER BY volume DESC
                """)

                logger.debug(f"🔍 Found {len(rows)} active tokens missing RugCheck data for refresh.")

                if rows:
                    tokens_added = 0 # Initialize counter
                    for row in rows:
                        mint = row["mint"]
                        volume = row["volume"] or Decimal(0)
                        priority = -float(volume)
                        current_attempts = self.fetch_attempts.get(mint, 0)

                        # Only add if not already deprioritized (reached max attempts)
                        if current_attempts < MAX_FETCH_ATTEMPTS:
                             await self.queue.put((priority, mint))
                             tokens_added += 1
                        # else:
                        #      logger.debug(f"Token {mint} previously reached max fetch attempts ({current_attempts}), not adding during refresh.")

                    logger.debug(f"🔄 Refreshed RugCheck queue. Added {tokens_added} tokens (current size: {self.queue.qsize()}).")
                #else:
                    # logger.debug("✅ No active tokens found needing RugCheck data during refresh.")
            return True # Indicate refresh completed

        except Exception as e:
            logger.error(f"❌ Critical error in _refresh_queue: {e}", exc_info=True)
            return False # Indicate refresh failed

    # --- Data Fetching and Processing ---

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
                if not data or "score" not in data: # Basic validation
                    logger.warning(f"⚠ RugCheck data incomplete or invalid for {mint}. Response: {data}")
                    return None # Treat incomplete data as a general error for now

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
                    return None # Indicate failure

            elif response.status_code == 404:
                logger.warning(f"❓ RugCheck API returned 404 (Not Found) for {mint}. Maybe too new?")
                return 'NOT_FOUND' # Specific status for 404
            elif response.status_code in [401, 403]: # Unauthorized or Forbidden
                 logger.warning(f"🔑 RugCheck API returned {response.status_code} (Authorization Error) for {mint}. Attempting re-login.")
                 self.jwt_token = None # Clear potentially invalid token
                 if not is_retry:
                     login_success = await self._login_to_rugcheck()
                     if login_success:
                         logger.info(f"Re-login successful. Retrying fetch for {mint}.")
                         return await self._fetch_and_store_data(mint, is_retry=True) # Retry once
                     else:
                         logger.error(f"Re-login failed. Cannot fetch authenticated data for {mint}.")
                         return None # Indicate failure after failed re-login
                 else:
                     logger.error(f"Authorization error persisted after re-login attempt for {mint}.")
                     return None # Indicate failure after retry
            else:
                logger.warning(f"⚠ RugCheck API returned {response.status_code} for {mint}. Response: {response.text}")
                return None # Indicate general API failure

        except httpx.TimeoutException:
            logger.error(f"⏳ Timeout fetching RugCheck data for {mint} after {RUGCHECK_REQUEST_TIMEOUT}s")
            return 'TIMEOUT' # Specific status for timeout
        except httpx.RequestError as req_err:
            logger.error(f"❌ HTTP Request Error fetching RugCheck for {mint}: {req_err}", exc_info=True)
            return None
        except json.JSONDecodeError as json_err:
            # Need access to response variable here, ensure it's defined even on error
            response_text = "N/A"
            if response: # Check if response object exists
                try:
                    response_text = response.text
                except Exception:
                    pass # Handle potential issues accessing response.text
            logger.error(f"❌ JSON Decode Error for RugCheck response {mint}: {json_err}. Response: {response_text}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected Error fetching RugCheck data for {mint}: {e}", exc_info=True)
            return None

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

        if fetch_result == 'NOT_FOUND':
            return 'NOT_FOUND' # Propagate the specific status
        if fetch_result == 'TIMEOUT':
            return 'TIMEOUT' # Propagate the specific status

        if fetch_result is None:
            logger.warning(f"Processing failed for {mint}: Could not fetch/store RugCheck data due to an error (not 404 or timeout).")
            return False # Indicate general failure

        # --- Score Check and Deactivation ---
        # --- Score Check and Deactivation (only if data was fetched successfully) ---
        fetched_data = fetch_result # We know it's a dict here
        score = fetched_data.get("score")
        if score is not None and score > self.config['RUGCHECK_SCORE_THRESHOLD']:
            logger.debug(f"🚨 High RugCheck score ({score} > {self.config['RUGCHECK_SCORE_THRESHOLD']}) for {mint}. Deactivating and unsubscribing.")
            try:
                # 1. Deactivate in DB
                async with self.db_client.pool.acquire() as conn:
                    await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                logger.debug(f"🔒 Deactivated token {mint} in DB due to high score.")

                # 2. Unsubscribe via WebSocket
                unsubscribed_ws = False
                if self.websocket_handler.websocket and self.websocket_handler.websocket.open:
                    is_subscribed = False
                    async with self.state.lock:
                         is_subscribed = mint in self.state.active_token_subscriptions
                         if is_subscribed:
                             self.state.active_token_subscriptions.discard(mint)

                    if is_subscribed:
                        try:
                            await asyncio.wait_for(self.websocket_handler.websocket.send(json.dumps({
                                "method": "unsubscribeTokenTrade",
                                "keys": [mint]
                            })), timeout=5.0)
                            # logger.debug(f"🌶️ TOO SPICY: Sent unsubscribe request for token {mint}")
                            logger.debug(f"[bold]:hot_pepper:  Too spicy:[/bold] Sent unsubscribe request for token {mint}")
                            unsubscribed_ws = True
                        except asyncio.TimeoutError:
                            logger.error(f"⏳ Timeout sending unsubscribe for high-score token {mint}.")
                        except Exception as ws_err:
                            logger.error(f"❌ Error sending unsubscribe for high-score token {mint}: {ws_err}", exc_info=True)
                    else:
                         logger.debug(f"Token {mint} already removed from active subscriptions, skipping WS unsubscribe.")

                # 3. Backup and Delete
                await self.db_client.backup_and_delete_token(mint, datetime.now(timezone.utc))
                #logger.debug(f"🧹 Backed up and deleted high-score token {mint}.")

                # Even if unsubscribe fails, we consider processing successful as it's deactivated in DB
                return True # Indicate success (deactivation handled)

            except Exception as deactivation_err:
                logger.error(f"❌ Error during deactivation/unsubscription for high-score token {mint}: {deactivation_err}", exc_info=True)
                # Still return True because the main goal (fetching/storing) succeeded,
                # but the deactivation part failed. Requeueing might not help here.
                return True
        else:
            # Score is acceptable or not present
            logger.debug(f"✅ RugCheck score OK for {mint} (Score: {score})")

            # --- Process Socials AFTER successful RugCheck (if score is OK) ---
            # if self.socials_processor:
            #     # logger.debug(f"Triggering socials processing for {mint} after successful RugCheck.")
            #     # Run social processing in the background to avoid blocking the rugcheck worker
            #     asyncio.create_task(self.socials_processor.process_token(mint))
            # else:
            #     # This case should ideally not happen if initialized correctly in main.py
            #     logger.warning("Socials processor not available in Rugcheck class.")

            return True # Indicate success

    async def _worker(self):
        """Worker task that processes tokens from the RugCheck queue with rate limiting."""
        logger.info("🚀 RugCheck worker started.")
        last_refresh_time = 0
        refresh_interval = 30 # Refresh queue every 30 seconds

        # --- Initial Login Attempt ---
        if self.wallet:
            await self._login_to_rugcheck()
        # Continue even if login fails, will use unauthenticated requests

        while not self.state.shutdown_event.is_set():
            try:
                # --- Refresh Queue Periodically ---
                current_time = asyncio.get_event_loop().time()
                if self.queue.empty() or (current_time - last_refresh_time > refresh_interval):
                    logger.debug("🔄 Triggering RugCheck queue refresh...")
                    refreshed = await self._refresh_queue()
                    if refreshed:
                        last_refresh_time = current_time
                    else:
                        # Avoid busy-looping if refresh fails repeatedly
                        await self.state.wait_or_interrupt(timeout=5)
                        continue # Skip to next iteration if refresh failed

                # --- Get Token from Queue ---
                if self.queue.empty():
                    # logger.debug("RugCheck queue is empty, waiting...")
                    await self.state.wait_or_interrupt(timeout=5) # Wait if queue is empty
                    continue

                try:
                    # Get highest priority item (lowest negative volume)
                    priority, mint = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    # logger.debug(f"Processing {mint} from RugCheck queue (Priority: {priority})")
                except asyncio.TimeoutError:
                    # logger.debug("RugCheck queue.get() timed out, queue might be empty or contested.")
                    continue # Try again next loop
                except Exception as q_err:
                     logger.error(f"Error getting item from rugcheck queue: {q_err}")
                     continue


                # --- Rate Limit Check ---
                async with self.limiter:
                    # --- Process Token ---
                    task_completed = False # Flag to ensure task_done is called correctly
                    try:
                        # Check if token still exists and is active before fetching
                        async with self.db_client.pool.acquire() as conn:
                            is_active = await conn.fetchval("SELECT is_active FROM tokens WHERE mint = $1", mint)

                        if is_active is None:
                            logger.debug(f"Token {mint} no longer exists. Skipping RugCheck.")
                            self.queue.task_done()
                            task_completed = True
                            self.fetch_attempts.pop(mint, None) # Clear attempts
                            continue
                        if not is_active:
                             logger.debug(f"Token {mint} is no longer active. Skipping RugCheck.")
                             self.queue.task_done()
                             task_completed = True
                             self.fetch_attempts.pop(mint, None) # Clear attempts
                             continue

                        # Fetch, store, check score, etc.
                        process_status = await self._process_token(mint)

                        # --- Handle Retry/Deprioritize Logic ---
                        if process_status in ['NOT_FOUND', 'TIMEOUT']:
                            status_reason = "404 (Not Found)" if process_status == 'NOT_FOUND' else "Timeout"
                            current_attempts = self.fetch_attempts.get(mint, 0) + 1
                            self.fetch_attempts[mint] = current_attempts
                            logger.warning(f"🔄 RugCheck API failed for {mint} ({status_reason}). Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")

                            if current_attempts < MAX_FETCH_ATTEMPTS:
                                # Requeue with original priority for retry
                                await self.queue.put((priority, mint))
                                logger.info(f"Retrying {mint} later (attempt {current_attempts}).")
                            else:
                                # Max attempts reached, requeue with very low priority
                                await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                                logger.warning(f"Max fetch attempts ({MAX_FETCH_ATTEMPTS}) reached for {mint} due to {status_reason}. Deprioritizing.")
                                # Keep attempt count high so refresh doesn't re-add with high priority

                        elif process_status is False:
                            # General processing error (not 404 or timeout)
                            logger.warning(f"📉 RugCheck processing failed for {mint} (not 404/timeout). Requeuing with original priority.")
                            await self.queue.put((priority, mint)) # Requeue
                            self.fetch_attempts.pop(mint, None) # Clear attempts counter

                        else: # process_status is True (Success)
                            logger.debug(f"✅ Successfully processed RugCheck for {mint}.")
                            self.fetch_attempts.pop(mint, None)

                        # Mark task as done regardless of outcome (requeueing handles retries)
                        self.queue.task_done()
                        task_completed = True

                    except Exception as proc_err:
                        logger.error(f"❌ Unexpected error processing token {mint}: {proc_err}", exc_info=True)
                        # Requeue on unexpected errors during processing block
                        await self.queue.put((priority, mint))
                        # Clear fetch attempts counter as it was an unexpected error
                        self.fetch_attempts.pop(mint, None)

                    finally:
                         # Ensure task_done is called even if processing fails, unless already called
                         if not task_completed:
                             try:
                                self.queue.task_done()
                             except ValueError:
                                 logger.warning(f"Task_done already called for {mint} in finally block?")
                             except Exception as td_err:
                                 logger.error(f"Error calling task_done for {mint} in finally block: {td_err}")


            except asyncio.CancelledError:
                logger.info("⏹ RugCheck worker task cancelled.")
                break # Exit loop cleanly on cancellation
            except Exception as e:
                logger.error(f"💥 Unexpected error in RugCheck worker main loop: {e}", exc_info=True)
                # Avoid busy-looping on persistent errors
                await self.state.wait_or_interrupt(timeout=10)

        logger.info("🛑 RugCheck worker shutting down.")

    def start(self) -> asyncio.Task:
        """Creates and returns the asyncio task for the RugCheck worker."""
        logger.info("Creating RugCheck background task...")
        # Ensure worker starts after initial setup (like wallet loading) is done
        return asyncio.create_task(self._worker(), name="rugcheck_worker")