"""
Manages WebSocket communication with the external PumpPortal API.
Handles incoming messages, token subscriptions, and graceful shutdown.
"""

import asyncio
import json
from datetime import datetime, timezone
import asyncpg
import websockets

from config import PUMPPORTAL_WS, INACTIVITY_PERIOD, MIN_MARKET_CAP
from database import store_token, store_trade, backup_and_delete_token, get_db
from logger import logger
from trading import has_active_position
from state import state

class WebSocketHandler:
    def __init__(self):
        self.websocket = None
        self.tasks = []

    async def connect(self):
        """Establishes a WebSocket connection and subscribes to new token events."""
        self.websocket = await websockets.connect(PUMPPORTAL_WS)
        logger.info("Connected to PumpPortal WebSocket")
        await self.websocket.send(json.dumps({"method": "subscribeNewToken"}))
        await state.set_new_token_subscription(True)
        logger.debug("Subscribed to new token events")

    async def monitor_connection(self):
        """Manages WebSocket keepalive and reconnection."""
        while not await state.get_shutdown():
            try:
                if self.websocket and self.websocket.open:
                    logger.debug("🔍 Sending WebSocket ping...")
                    pong_waiter = await self.websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                    logger.debug("✅ WebSocket ping successful")
                else:
                    logger.warning("⚠ WebSocket connection lost, reconnecting...")
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
            logger.error(f"❌ Error while closing WebSocket: {e}")

        attempt = 1
        max_attempts = 5  # Limit retries to avoid infinite loops

        while attempt <= max_attempts:
            try:
                await asyncio.sleep(attempt * 2)  # Exponential backoff (2, 4, 8, 16, 32 seconds)
                async with (await get_db()).acquire() as conn:
                    await conn.execute("SELECT 1")  # Ensure DB connection is alive
                await self.connect()  # Reconnect WebSocket

                # Restart tasks after successful reconnection
                self.tasks = [
                    asyncio.create_task(self.resume_subscriptions()),
                    asyncio.create_task(self.message_handler()),
                    asyncio.create_task(self.unsubscribe_checker()),
                    asyncio.create_task(self.monitor_connection())
                ]

                logger.info(f"✅ WebSocket reconnected successfully after {attempt} attempts")
                return  # Exit the function if reconnection succeeds
            except Exception as e:
                logger.warning(f"⚠ WebSocket reconnection attempt {attempt} failed: {e}")
                attempt += 1

        logger.error("❌ Failed to reconnect after multiple attempts. Initiating shutdown...")
        await state.set_shutdown(True)  # Gracefully shut down if reconnection fails

    async def message_handler(self):
        """Processes incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if 'message' in data:
                        logger.debug(f"WebSocket confirmation: {data['message']}")
                        continue
                    if 'mint' not in data:
                        logger.warning(f"Invalid message format: {data}")
                        continue

                    if 'name' in data:
                        token_stored = await store_token(data)
                        if not token_stored:
                            creator = data.get('traderPublicKey')
                            if creator:
                                await self.unsubscribe_tokens_from_creator(creator)
                            continue
                        await self.websocket.send(json.dumps({
                            "method": "subscribeTokenTrade",
                            "keys": [data['mint']]
                        }))
                        await state.add_subscription(data['mint'])
                        active_subs = list(await state.get_subscriptions())
                        logger.debug(f"✅ Subscribed to {data['mint']} --> {len(active_subs)} active subscriptions")
                    elif 'tokenAmount' in data:
                        #logger.debug(f"WebSocket got trade message: {data}")
                        await store_trade(data)
                except Exception as e:
                    logger.error(f"Message processing error: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.error("WebSocket connection closed, reconnecting...")
            await self.reconnect()

    async def resume_subscriptions(self):
        """Limits active subscriptions to prevent memory leaks."""
        async with (await get_db()).acquire() as conn:
            rows = await conn.fetch("SELECT mint FROM tokens WHERE is_active = TRUE LIMIT 100")  # Limit subscriptions
            for row in rows:
                mint = row['mint']
                if mint not in await state.get_subscriptions():
                    try:
                        await self.websocket.send(json.dumps({
                            "method": "subscribeTokenTrade",
                            "keys": [mint]
                        }))
                        await state.add_subscription(mint)
                        logger.debug(f"✅ Resubscribed to {mint}")
                    except Exception as e:
                        logger.error(f"❌ Failed to subscribe to {mint}: {e}")


    async def unsubscribe_checker(self):
        """Periodically checks for inactive or risky tokens."""
        await state.wait_or_interrupt(timeout=100) 
        while not await state.get_shutdown():
            try:
                async with (await get_db()).acquire() as conn:
                    cutoff = datetime.now(timezone.utc) - INACTIVITY_PERIOD
                    rows = await conn.fetch("""
                        SELECT mint FROM tokens 
                        WHERE (is_active = FALSE OR last_trade < $1 OR marketCapSol < $2)
                        AND mint NOT IN (SELECT mint FROM portfolio)
                    """, cutoff, MIN_MARKET_CAP)

                    for row in rows:
                        mint = row['mint']
                        async with state.lock:
                            if mint in await state.get_subscriptions():
                                await self.websocket.send(json.dumps({
                                    "method": "unsubscribeTokenTrade",
                                    "keys": [mint]
                                }))
                                await state.remove_subscription(mint)
                        await backup_and_delete_token(mint, datetime.now(timezone.utc))
                await state.wait_or_interrupt(timeout=30) 
            except Exception as e:
                logger.error(f"Unsubscribe checker error: {e}")
                await state.wait_or_interrupt(timeout=5) 

    async def unsubscribe_tokens_from_creator(self, creator: str):
        """Unsubscribes and removes tokens from a suspicious creator."""
        async with (await get_db()).acquire() as conn:
            rows = await conn.fetch("SELECT mint FROM tokens WHERE traderPublicKey = $1", creator)
            for row in rows:
                mint = row['mint']
                if not await has_active_position(mint):
                    if mint in await state.get_subscriptions():
                        await self.websocket.send(json.dumps({
                            "method": "unsubscribeTokenTrade",
                            "keys": [mint]
                        }))
                        await state.remove_subscription(mint)
                    await backup_and_delete_token(mint, datetime.now(timezone.utc))

    async def shutdown(self):
        """Graceful shutdown with explicit unsubscription from all events."""
        await state.set_shutdown(True)
        logger.info("🚀 Starting graceful shutdown sequence...")

        # Unsubscribe from new tokens first
        if await state.get_new_token_subscription():
            try:
                if self.websocket and self.websocket.open:
                    await self.websocket.send(json.dumps({
                        "method": "unsubscribeNewToken"
                    }))
                await state.set_new_token_subscription(False)
                logger.info("✅ Unsubscribed from new token events")
            except Exception as e:
                logger.error(f"❌ Failed to unsubscribe new tokens: {e}")

        # Process active subscriptions individually
        active_subs = list(await state.get_subscriptions())
        if active_subs:
            logger.info(f"🔄 Unsubscribing from {len(active_subs)} tokens...")
            for mint in active_subs:
                try:
                    await self.websocket.send(json.dumps({
                        "method": "unsubscribeTokenTrade",
                        "keys": [mint]  # Single-element array per request
                    }))
                    logger.debug(f"Unsubscribed from {mint}")
                except Exception as e:
                    logger.error(f"❌ Failed to unsubscribe {mint}: {e}")
                finally:
                    await state.remove_subscription(mint)
                # Short pause between unsubscribes if needed
                await asyncio.sleep(0.01)

        # Close WebSocket properly
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("🔌 WebSocket connection closed")
            except Exception as e:
                logger.error(f"❌ WebSocket closure failed: {e}")

        # Final cleanup
        logger.info("💾 Shutdown complete.")


    def start(self):
        """Starts all WebSocket tasks."""
        return [
            asyncio.create_task(self.resume_subscriptions(), name="ws_resume_subscriptions"),
            asyncio.create_task(self.message_handler(), name="ws_message_handler"),
            asyncio.create_task(self.monitor_connection(), name="ws_connection_monitor"),
            asyncio.create_task(self.unsubscribe_checker(), name="ws_unsubscribe_checker")
        ]
