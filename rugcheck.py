"""
rugcheck.py - Manages fetching RugCheck data, prioritization, and processing.
"""

import asyncio
import json
from datetime import datetime, timezone
import traceback
import httpx
from aiolimiter import AsyncLimiter
from decimal import Decimal

from config import (
    RUGCHECK_RATE_LIMIT, RUGCHECK_API, RUGCHECK_INTERVAL,
    RUGCHECK_SCORE_THRESHOLD # Import the threshold
)
from database import DatabaseClient
from logger import logger
from state import GlobalState
from websocket_handler import WebSocketHandler
from socials_processor import SocialsProcessor # Import the SocialsProcessor

class Rugcheck:
    # Accept SocialsProcessor instance during initialization
    def __init__(self, state: GlobalState, db_client: DatabaseClient, websocket_handler: WebSocketHandler, socials_processor: SocialsProcessor):
        self.state = state
        self.db_client = db_client
        self.websocket_handler = websocket_handler
        # Rate limiter: RUGCHECK_RATE_LIMIT calls per RUGCHECK_INTERVAL seconds
        self.limiter = AsyncLimiter(max_rate=RUGCHECK_RATE_LIMIT, time_period=RUGCHECK_INTERVAL)
        self.queue = self.state.get_rugcheck_queue() # Use the queue from GlobalState
        self.socials_processor = socials_processor # Store socials processor instance

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
                    for row in rows:
                        mint = row["mint"]
                        volume = row["volume"] or Decimal(0)
                        # Higher volume = lower negative number = higher priority
                        priority = -float(volume)
                        # logger.debug(f"🔄 Refreshing Queue: Token {mint}, Volume: {volume:.4f} SOL, Priority: {priority}")
                        await self.queue.put((priority, mint))
                    logger.debug(f"🔄 Refreshed RugCheck queue with {len(rows)} tokens.")
                else:
                    logger.debug("✅ No active tokens found needing RugCheck data during refresh.")
            return True # Indicate refresh completed

        except Exception as e:
            logger.error(f"❌ Critical error in _refresh_queue: {e}", exc_info=True)
            return False # Indicate refresh failed

    async def _fetch_and_store_data(self, mint: str) -> dict | None:
        """Fetches RugCheck data from the API and stores it in the database."""
        url = f"{RUGCHECK_API}/{mint}/report"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client: # Increased timeout slightly
                logger.debug(f"📡 Fetching RugCheck for {mint}")
                response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                if not data or "score" not in data: # Basic validation
                    logger.warning(f"⚠ RugCheck data incomplete or invalid for {mint}. Response: {data}")
                    return None

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
                # Consider storing a minimal record indicating 'not found' or 'pending'
                # For now, treat as failure to fetch valid data.
                return None
            else:
                logger.warning(f"⚠ RugCheck API returned {response.status_code} for {mint}. Response: {response.text}")
                return None # Indicate failure

        except httpx.TimeoutException:
            logger.error(f"⏳ Timeout fetching RugCheck data for {mint} from {url}")
            return None
        except httpx.RequestError as req_err:
            logger.error(f"❌ HTTP Request Error fetching RugCheck for {mint}: {req_err}", exc_info=True)
            return None
        except json.JSONDecodeError as json_err:
            logger.error(f"❌ JSON Decode Error for RugCheck response {mint}: {json_err}. Response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected Error fetching RugCheck data for {mint}: {e}", exc_info=True)
            return None

    async def _process_token(self, mint: str) -> bool:
        """Fetches, stores, and processes RugCheck data for a single token, including score check."""
        fetched_data = await self._fetch_and_store_data(mint)

        if fetched_data is None:
            logger.warning(f"Processing failed for {mint}: Could not fetch/store RugCheck data.")
            return False # Indicate failure for potential requeueing

        # --- Score Check and Deactivation ---
        score = fetched_data.get("score")
        if score is not None and score > RUGCHECK_SCORE_THRESHOLD:
            logger.debug(f"🚨 High RugCheck score ({score} > {RUGCHECK_SCORE_THRESHOLD}) for {mint}. Deactivating and unsubscribing.")
            try:
                # 1. Deactivate in DB
                async with self.db_client.pool.acquire() as conn:
                    await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                logger.debug(f"🔒 Deactivated token {mint} in DB due to high score.")

                # 2. Unsubscribe via WebSocket (if connected and subscribed)
                unsubscribed_ws = False
                if self.websocket_handler.websocket and self.websocket_handler.websocket.open:
                     # Check if we are actually subscribed before trying to unsubscribe
                    is_subscribed = False
                    async with self.state.lock:
                         is_subscribed = mint in self.state.active_token_subscriptions
                         if is_subscribed:
                             self.state.active_token_subscriptions.discard(mint) # Remove optimistically

                    if is_subscribed:
                        try:
                            await asyncio.wait_for(self.websocket_handler.websocket.send(json.dumps({
                                "method": "unsubscribeTokenTrade",
                                "keys": [mint]
                            })), timeout=5.0)
                            logger.debug(f"👋 Sent unsubscribe request for high-score token {mint}.")
                            unsubscribed_ws = True
                        except asyncio.TimeoutError:
                            logger.error(f"⏳ Timeout sending unsubscribe for high-score token {mint}.")
                        except Exception as ws_err:
                            logger.error(f"❌ Error sending unsubscribe for high-score token {mint}: {ws_err}", exc_info=True)
                    else:
                         logger.debug(f"Token {mint} already removed from active subscriptions, skipping WS unsubscribe.")

                # 3. Backup and Delete (Optional - consider if needed immediately)
                # This was in the original code, but might be redundant if unsubscribe_checker handles it
                await self.db_client.backup_and_delete_token(mint, datetime.now(timezone.utc))
                logger.debug(f"🧹 Backed up and deleted high-score token {mint}.")

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
            if self.socials_processor:
                logger.debug(f"Triggering socials processing for {mint} after successful RugCheck.")
                # Run social processing in the background to avoid blocking the rugcheck worker
                asyncio.create_task(self.socials_processor.process_token(mint))
            else:
                # This case should ideally not happen if initialized correctly in main.py
                logger.warning("Socials processor not available in Rugcheck class.")

            return True # Indicate success

    async def _worker(self):
        """Worker task that processes tokens from the RugCheck queue with rate limiting."""
        logger.info("🚀 RugCheck worker started.")
        last_refresh_time = 0
        refresh_interval = 30 # Refresh queue every 30 seconds if needed

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
                    try:
                        # Check if token still exists and is active before fetching
                        async with self.db_client.pool.acquire() as conn:
                            is_active = await conn.fetchval("SELECT is_active FROM tokens WHERE mint = $1", mint)

                        if is_active is None:
                            logger.debug(f"Token {mint} no longer exists in tokens table. Skipping RugCheck.")
                            self.queue.task_done()
                            continue
                        if not is_active:
                             logger.debug(f"Token {mint} is no longer active. Skipping RugCheck.")
                             self.queue.task_done()
                             continue

                        # Fetch, store, check score, potentially deactivate/unsubscribe
                        success = await self._process_token(mint)

                        if not success:
                            logger.warning(f"🔄 RugCheck processing failed for {mint}. Requeuing might be needed if it was temporary.")
                            # Simple Requeue Logic (Consider adding max retries)
                            # await self.queue.put((priority, mint)) # Be careful with infinite requeues
                        else:
                            logger.debug(f"✅ Successfully processed RugCheck for {mint}.")

                    except Exception as proc_err:
                        logger.error(f"❌ Unexpected error processing token {mint}: {proc_err}", exc_info=True)
                        # Consider requeueing or moving to a dead-letter queue
                        # await self.queue.put((priority, mint)) # Example requeue

                    finally:
                         # Ensure task_done is called even if processing fails
                         try:
                            self.queue.task_done()
                         except ValueError:
                             logger.warning(f"Task_done already called for item related to {mint}?")
                         except Exception as td_err:
                             logger.error(f"Error calling task_done for {mint}: {td_err}")


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
        logger.info("Starting RugCheck background task...")
        return asyncio.create_task(self._worker(), name="rugcheck_worker")