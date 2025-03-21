"""
Manages WebSocket communication with the external PumpPortal API.
Handles incoming messages, token subscriptions, and graceful shutdown.
"""
import state
import asyncio
import json
import signal
from datetime import datetime, timezone
import aiosqlite
import websockets

from config import PUMPPORTAL_WS, INACTIVITY_PERIOD, MIN_MARKET_CAP, DB_NAME
from database import store_token, store_trade, backup_and_delete_token
from logger import logger
from trading import has_active_position

class WebSocketHandler:
    def __init__(self):
        self.websocket = None
        self.tasks = []

    async def connect(self):
        """Establishes a WebSocket connection and subscribes to new token events."""
        self.websocket = await websockets.connect(PUMPPORTAL_WS)
        logger.info("Connected to PumpPortal WebSocket")
        await self.websocket.send(json.dumps({"method": "subscribeNewToken"}))
        await state.state.set_new_token_subscription(True)
        logger.debug("Subscribed to new token events")

    async def monitor_connection(self):
        """Periodically pings the WebSocket to ensure the connection is alive.
        If no pong is received within timeout, reconnect and resubscribe."""
        while not await state.state.get_shutdown():
            try:
                pong_waiter = await self.websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
                logger.debug("WebSocket ping successful")
            except asyncio.TimeoutError:
                logger.warning("WebSocket ping timed out; initiating reconnection")
                await self.reconnect()
                break
            except Exception as e:
                logger.error(f"Error during ping/pong: {e}")
                await self.reconnect()
                break
            await asyncio.sleep(30)

    async def reconnect(self):
        """Handles reconnection logic: close current connection, reconnect,
        and resume subscriptions."""
        try:
            await self.websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket during reconnection: {e}")
        # Attempt reconnection
        logger.info("Reconnecting to WebSocket...")
        await self.connect()
        # Restart all tasks associated with the connection
        self.tasks = [
            asyncio.create_task(self.resume_subscriptions()),
            asyncio.create_task(self.message_handler()),
            asyncio.create_task(self.unsubscribe_checker()),
            asyncio.create_task(self.monitor_connection())
        ]

    async def message_handler(self):
        """Processes incoming messages from the WebSocket."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if 'message' in data:
                        logger.debug(f"WebSocket confirmation: {data['message']}")
                        continue
                    if 'mint' not in data:
                        logger.warning(f"Message missing 'mint': {data}")
                        continue
                    if 'name' in data:
                        # New token event
                        token_stored = await store_token(data)
                        if not token_stored:
                        # Suspicious wallet detected; trigger cleanup.
                            creator = data.get('traderPublicKey')
                            if creator:
                                logger.info(f"Initiating cleanup for suspicious wallet {creator}")
                                await self.unsubscribe_tokens_from_creator(creator)
                            continue
                        # Otherwise, subscribe to token trades.
                        payload = {"method": "subscribeTokenTrade", "keys": [data['mint']]}
                        await self.websocket.send(json.dumps(payload))
                        await state.state.add_subscription(data['mint'])
                        logger.debug(f"Subscribed to trades for {data['mint']}")
                    elif 'tokenAmount' in data:
                        # Trade event
                        await store_trade(data)
                except Exception as e:
                    logger.error(f"Message processing error: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.error("WebSocket connection closed unexpectedly")
            await self.reconnect()

    async def resume_subscriptions(self):
        """Resumes subscriptions for active tokens from the database."""
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT mint FROM tokens WHERE is_active = 1 AND mint NOT IN (SELECT mint FROM portfolio)") as cursor:
                rows = await cursor.fetchall()
                for (mint,) in rows:
                    if mint not in await state.state.get_subscriptions():
                        payload = {"method": "subscribeTokenTrade", "keys": [mint]}
                        await self.websocket.send(json.dumps(payload))
                        await state.state.add_subscription(mint)
                        await db.execute("UPDATE tokens SET last_trade = ? WHERE mint = ?", (datetime.utcnow(), mint))
                        logger.debug(f"Resubscribed to token trade for {mint}")
            await db.commit()

    async def unsubscribe_checker(self):
        """
        Periodically checks for inactive or risky tokens,
        unsubscribes from their updates, and backs up and deletes their data.
        """
        await asyncio.sleep(100)  # Initial delay
        while not await state.state.get_shutdown():
            try:
                async with aiosqlite.connect(DB_NAME) as db:
                    cutoff = datetime.now(timezone.utc) - INACTIVITY_PERIOD
                    query = '''SELECT mint FROM tokens 
                               WHERE (is_active = 0 OR last_trade < ? OR last_trade IS NULL OR marketCapSol < ?)
                               AND mint IN (SELECT mint FROM trades) AND mint NOT IN (SELECT mint FROM portfolio)'''
                    async with db.execute(query, (cutoff, MIN_MARKET_CAP)) as cursor:
                        rugged_tokens = await cursor.fetchall()
                        for (mint,) in rugged_tokens:
                            if mint in await state.state.get_subscriptions():
                                payload = {"method": "unsubscribeTokenTrade", "keys": [mint]}
                                await self.websocket.send(json.dumps(payload))
                                await state.state.remove_subscription(mint)
                                logger.debug(f"Unsubscribed from token trade: {mint}")
                            archived_at = datetime.utcnow().isoformat()
                            await backup_and_delete_token(mint, archived_at)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Unsubscribe checker error: {e}")
                await asyncio.sleep(30)

    async def unsubscribe_tokens_from_creator(self, creator: str):
        """
        Finds all tokens created by a suspicious wallet,
        unsubscribes from their updates (if subscribed), and
        performs backup and deletion for each token if no active position is found.
        """
        async with aiosqlite.connect(DB_NAME) as db:
            query = "SELECT mint FROM tokens WHERE traderPublicKey = ?"
            async with db.execute(query, (creator,)) as cursor:
                tokens = await cursor.fetchall()
                for (mint,) in tokens:
                    # Only delete if no active position
                    if not await has_active_position(mint) and mint in await state.state.get_subscriptions():
                        payload = {"method": "unsubscribeTokenTrade", "keys": [mint]}
                        await self.websocket.send(json.dumps(payload))
                        await state.state.remove_subscription(mint)
                        logger.info(f"Unsubscribed token {mint} from suspicious wallet {creator}")
                        # Backup and delete the token.
                        archived_at = datetime.utcnow().isoformat()
                        await backup_and_delete_token(mint, archived_at)
                        logger.info(f"Backed up and deleted token {mint} from suspicious wallet {creator}")

    async def shutdown(self):
        """Performs a graceful shutdown: unsubscribes and closes the WebSocket."""
        await state.state.set_shutdown(True)
        logger.info("Initiating graceful shutdown...")
        if await state.state.get_new_token_subscription():
            payload = {"method": "unsubscribeNewToken"}
            try:
                await self.websocket.send(json.dumps(payload))
                await state.state.set_new_token_subscription(False)
                logger.info("Unsubscribed from new token events.")
            except Exception as e:
                logger.error(f"Error unsubscribing from new token events: {e}")
        for mint in list(await state.state.get_subscriptions()):
            payload = {"method": "unsubscribeTokenTrade", "keys": [mint]}
            try:
                await self.websocket.send(json.dumps(payload))
                state.state.remove_subscription(mint)
                logger.info(f"Unsubscribed from token trade: {mint}")
            except Exception as e:
                logger.error(f"Error unsubscribing from {mint}: {e}")
        try:
            await self.websocket.close()
            logger.info("WebSocket connection closed.")
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")

    def start(self):
        """
        Initiates the WebSocket connection and starts all associated tasks.
        Returns the list of tasks.
        """
        loop = asyncio.get_running_loop()
        self.tasks = [
            loop.create_task(self.resume_subscriptions()),
            loop.create_task(self.message_handler()),
            loop.create_task(self.monitor_connection()),
            loop.create_task(self.unsubscribe_checker())
        ]
        # Register signal handler for graceful shutdown
        #signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.shutdown()))
        return self.tasks
