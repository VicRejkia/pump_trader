"""
Manages WebSocket communication with the external PumpPortal API.
Handles incoming messages, token subscriptions, and graceful shutdown.
"""

import asyncio
from asyncio import Queue
import json
from datetime import datetime, timezone
import asyncpg
import websockets

from config import PUMPPORTAL_WS, INACTIVITY_PERIOD, MIN_MARKET_CAP
from database import DatabaseClient
from logger import logger
# from trading import has_active_position
from state import GlobalState
#from state import state

class WebSocketHandler:
    def __init__(self, db_client: DatabaseClient):
        self.state = GlobalState.get_instance() 
        self.db_client = db_client  # Store reference to the database client
        self.websocket = None
        self.tasks = []
        self.last_update_times = {}
        self.trade_queue = Queue()  # 🚀 Trade queue to buffer incoming trades

    async def connect(self):
        """Establishes a WebSocket connection and subscribes to new token events."""
        self.websocket = await websockets.connect(PUMPPORTAL_WS)
        logger.info("Connected to PumpPortal WebSocket")
        await self.websocket.send(json.dumps({"method": "subscribeNewToken"}))
        await self.state.set_new_token_subscription(True)
        await self.resume_subscriptions()  # One-time call on connect
        logger.debug("Subscribed to new token events")

    async def monitor_connection(self):
        """Manages WebSocket keepalive and reconnection."""
        while not self.state.shutdown_event.is_set():
            try:
                if self.websocket and self.websocket.open:
                    logger.debug("🔍 Sending WebSocket ping...")
                    pong_waiter = await self.websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                    logger.debug("✅ WebSocket ping successful")
                else:
                    logger.warning("⚠️ WebSocket connection lost, reconnecting...")
                    await self.reconnect()
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                logger.error("❌ WebSocket timeout or closure detected. Reconnecting...")
                await self.reconnect()
            await asyncio.sleep(60)  # Ping every x seconds

    async def reconnect(self):
        """Handles reconnection logic and resubscription with exponential backoff."""
        logger.warning("🔄 Attempting WebSocket reconnection...")

        try:
            if self.websocket:
                await self.websocket.close()
        except Exception as e:
            logger.error(f"❌ Error while closing WebSocket: {e}" , exc_info=True)

        attempt = 1
        max_attempts = 5  # Limit retries to avoid infinite loops

        while attempt <= max_attempts:
            logger.info(f"Reconnection attempt {attempt} starting")
            try:
                await asyncio.sleep(attempt * 2)  # Exponential backoff (2, 4, 8, 16, 32 seconds)
                await self.connect()  # Reconnect WebSocket

                await self.resume_subscriptions()  # One-time call on connect

                # Restart tasks after successful reconnection
                self.tasks = [
                    asyncio.create_task(self.message_handler()),
                    asyncio.create_task(self.unsubscribe_checker()),
                    asyncio.create_task(self.monitor_connection())
                ]

                logger.info(f"✅ WebSocket reconnected successfully after {attempt} attempts")
                return  # Exit the function if reconnection succeeds
            except Exception as e:
                logger.warning(f"⚠️ WebSocket reconnection attempt {attempt} failed: {e}" , exc_info=True)
                attempt += 1

        logger.error("❌ Failed to reconnect after multiple attempts. Initiating shutdown...")

    async def message_handler(self):
        """Processes incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Handle messages
                    if 'message' in data:
                        logger.info(f"📡 WebSocket confirmation: {data['message']}")
                        continue

                    # Handle new token events
                    if data['txType'] == "create":
                        try:
                            token_stored = await self.db_client.insert_token(data)
                            if not token_stored:
                                #logger.error(f"Token {data.get('mint')} failed to store (business rule violation).")
                                continue
                        except Exception as e:
                            logger.error(f"Unexpected error storing token {data.get('mint')}: {e}", exc_info=True)
                            # Handle or retry as needed
                            continue

                        await self.websocket.send(json.dumps({
                            "method": "subscribeTokenTrade",
                            "keys": [data['mint']]
                        }))
                        await self.state.add_token_subscription(data['mint'])
                        active_subs = list(await self.state.get_token_subscriptions())
                        logger.debug(f"✅ Subscribed to {data['mint']} --> {len(active_subs)} active subscriptions")

                    elif data["txType"] == "migrate":                        
                        await self.db_client.insert_migration(data)

                    elif data["txType"] == "buy" or data["txType"] == "sell": 
                        #logger.debug(f"📡 WebSocket trade received: {data}")
                        self.last_update_times[data['mint']] = datetime.now(timezone.utc)
                        await self.trade_queue.put(data) 
                    else:
                        logger.warning(f"WEBSOCKET - Unknown message type: {data}")                        

                except Exception as e:
                    logger.error(f"Message processing error: {e}" , exc_info=True)
        except websockets.exceptions.ConnectionClosed:
            logger.error("WebSocket connection closed, reconnecting...")
            await self.reconnect()
        except Exception as e:
            logger.error(f"Unexpected error in message_handler: {e}", exc_info=True)

    async def resume_subscriptions(self):
        """Resubscribes to all active tokens from the database (one-time operation)."""
        if not self.websocket or self.websocket.closed:
            logger.warning("WebSocket not connected, skipping resubscriptions")
            return

        try:
            rows = await self.db_client.get_active_tokens()
            for row in rows:
                mint = row['mint']
                if mint not in await self.state.get_token_subscriptions():
                    await self.websocket.send(json.dumps({
                        "method": "subscribeTokenTrade",
                        "keys": [mint]
                    }))
                    await self.state.add_token_subscription(mint)
                    logger.debug(f"✅ Resubscribed to {mint}")
        except Exception as e:
            logger.error(f"❌ Failed to resume subscriptions: {e}", exc_info=True)
            raise  # Let the task fail visibly for debugging

    async def unsubscribe_checker(self):
        """Periodically checks for inactive or risky tokens."""
        logger.debug("Starting unsubscribe checker")
        while not self.state.shutdown_event.is_set():
            if not self.websocket or self.websocket.closed:
                await asyncio.sleep(1)
                continue

            sol_price = await self.state.get_sol_price()
            if sol_price is None:
                await asyncio.sleep(5)
                continue
                
            try:
                rows = await self.db_client.get_tokens_to_unsubscribe(sol_price, MIN_MARKET_CAP)

                # Identify candidate mints from DB
                candidate_mints = [row['mint'] for row in rows]
                mints_to_process_batch = []

                # --- Critical section: Check and remove from shared state ---
                if candidate_mints:
                    async with self.state.lock:
                        for mint in candidate_mints:
                            if mint in self.state.active_token_subscriptions:
                                # Remove from shared state immediately while holding lock
                                self.state.active_token_subscriptions.discard(mint)
                                mints_to_process_batch.append(mint) # Add to batch for I/O ops
                # --- End Critical section ---

                # --- Perform slow I/O operations *outside* the lock ---
                if mints_to_process_batch:
                    # 1. Send batch unsubscribe message
                    try:
                        if self.websocket and self.websocket.open:
                            logger.info(f"👋 Unsubscribing batch of {len(mints_to_process_batch)} tokens...")
                            await self.websocket.send(json.dumps({
                                "method": "unsubscribeTokenTrade",
                                "keys": mints_to_process_batch
                            }))
                        else:
                            logger.warning(f"WebSocket closed, cannot send batch unsubscribe for {len(mints_to_process_batch)} tokens.")
                    except Exception as e:
                        logger.error(f"Failed to send batch unsubscribe message: {e}", exc_info=True)
                        # Note: Even if sending fails, we proceed to DB cleanup as the tokens
                        # are already removed from the in-memory active set.

                    # 2. Backup and delete from DB individually
                    deleted_count = 0
                    for mint in mints_to_process_batch:
                        try:
                            await self.db_client.backup_and_delete_token(mint, datetime.now(timezone.utc))
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"DB backup/delete failed for {mint}: {e}", exc_info=True)
                            # Log error and continue with the next mint

                    logger.info(f"💾 Processed unsubscribe batch: {deleted_count}/{len(mints_to_process_batch)} tokens backed up and cleaned from DB.")
                await self.state.wait_or_interrupt(timeout=30)
            except Exception as e:
                logger.error(f"Unsubscribe checker cycle failed: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=5)

    async def unsubscribe_tokens_from_creator(self, creator: str):
        """Unsubscribes and removes tokens from a suspicious creator."""
        async with (await get_db()).acquire() as conn:
            try:
                rows = await conn.fetch("SELECT mint FROM tokens WHERE traderPublicKey = $1", creator)
                for row in rows:
                    mint = row['mint']
                    if not await has_active_position(mint):
                        if mint in await self.state.get_token_subscriptions():
                            await self.websocket.send(json.dumps({
                                "method": "unsubscribeTokenTrade",
                                "keys": [mint]
                            }))
                            await self.state.remove_token_subscriptions(mint)
                        await backup_and_delete_token(mint, datetime.now(timezone.utc))
            except Exception as e:
                logger.error(f"unsubscribe_tokens_from_creator error: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=5)

    async def check_inactive_tokens(self):
        while not self.state.shutdown_event.is_set():  # Assuming state has a shutdown flag
            try:
                current_time = datetime.now(timezone.utc)
                inactive_tokens = []
                # Safely access shared state
                async with self.state.lock:  # Assuming state has a lock for thread safety
                    for mint, last_update in self.last_update_times.items():
                        if current_time - last_update > INACTIVITY_PERIOD:
                            inactive_tokens.append(mint)
                
                # Unsubscribe from inactive tokens
                for mint in inactive_tokens:
                    logger.info(f"Token {mint} inactive for over {INACTIVITY_PERIOD}. Unsubscribing...")
                    try:
                        await self.websocket.send(json.dumps({
                            "method": "unsubscribeTokenTrade",
                            "keys": [mint]
                        }))
                        async with self.state.lock:
                            self.state.active_subscriptions.discard(mint)  # Remove from active subscriptions
                            del self.last_update_times[mint]  # Remove from tracking
                        logger.debug(f"✅ Unsubscribed from inactive token {mint}")
                    except Exception as e:
                        logger.error(f"❌ Failed to unsubscribe from {mint}: {e}" , exc_info=True)
                
                # Wait before the next check
                await self.state.wait_or_interrupt(timeout=60)  # Check every 60 seconds
            except Exception as e:
                logger.error(f"Error in check_inactive_tokens: {e}" , exc_info=True)
                await self.state.wait_or_interrupt(timeout=5)  # Brief pause on error
    
    async def shutdown(self):
        """Gracefully shutdown the WebSocket connection, unsubscribing from new token events and token trade subscriptions with retries."""
        try:
            # Unsubscribe from new token subscription, if active.
            if await self.state.get_new_token_subscription() and self.websocket:
                retries = 2
                unsubscribed_new = False
                while retries > 0 and not unsubscribed_new:
                    try:
                        await self.websocket.send(json.dumps({
                            "method": "unsubscribeNewToken"
                        }))
                        await asyncio.sleep(0.5)  # brief wait for processing
                        await self.state.set_new_token_subscription(False)
                        logger.info("👋 Successfully unsubscribed from new token events.")
                        unsubscribed_new = True
                    except Exception as e:
                        logger.warning(f"Failed to unsubscribe from new token events (attempt {4 - retries}/3): {e}", exc_info=True)
                        retries -= 1
                        await asyncio.sleep(1)
                if not unsubscribed_new:
                    logger.error("Unable to unsubscribe from new token events after retries.")

            # Unsubscribe from all active token trade subscriptions regardless of websocket open state.
            active_subs = list(await self.state.get_token_subscriptions())
            if active_subs:
                batches = [active_subs[i:i+10] for i in range(0, len(active_subs), 10)]
                logger.info(f"Processing {len(batches)} unsubscribe batches for {len(active_subs)} tokens")
                
                for batch in batches:
                    retries = 1
                    unsubscribed = False
                    while retries > 0 and not unsubscribed:
                        try:
                            await self.websocket.send(json.dumps({
                                "method": "unsubscribeTokenTrade",
                                "keys": batch
                            }))
                            await asyncio.sleep(0.5)  # brief wait for processing
                            logger.info(f"👋 Successfully unsubscribed batch of {len(batch)} tokens")
                            unsubscribed = True
                        except Exception as e:
                            logger.warning(f"Failed to unsubscribe batch (attempt {2 - retries}/2): {e}", exc_info=True)
                            retries -= 1
                            await asyncio.sleep(0.1)
                    if not unsubscribed:
                        logger.error(f"Failed to unsubscribe batch after retries: {batch}")
                logger.info(f"Processed {len(active_subs)} token trade unsubscriptions.")
                # Clear active subscriptions regardless.
                async with self.state.lock:
                    self.state.active_token_subscriptions.clear()
            else:
                logger.info("No active token trade subscriptions found.")
        except Exception as e:
            logger.error(f"Unexpected error during unsubscribe: {e}", exc_info=True)
        finally:
            try:
                if self.websocket:
                    # Regardless of open state, try to close the websocket.
                    await self.websocket.close()
                    logger.info("WebSocket closed successfully.")
            except Exception as e:
                logger.error(f"Error while closing WebSocket: {e}", exc_info=True)

    def start(self):
        """Starts all WebSocket tasks."""
        return [
            asyncio.create_task(self.message_handler(), name="ws_message_handler"),
            asyncio.create_task(self.monitor_connection(), name="ws_connection_monitor"),
            asyncio.create_task(self.unsubscribe_checker(), name="ws_unsubscribe_checker")
        ]
