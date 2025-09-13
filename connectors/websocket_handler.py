# path: connectors/websocket_handler.py

"""
Manages WebSocket communication with the external PumpPortal API.
Handles incoming messages, token subscriptions, and graceful shutdown.
"""

import asyncio
from asyncio import Queue
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
import websockets

from config.config import _PUMPPORTAL_WS, _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED, _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES
from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState

UNSUBSCRIBE_BATCH_COUNT = 15


class WebSocketHandler:
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state_manager: GlobalState):
        self.state = state_manager
        self.db_client = db_client
        self.config = config_dict
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.tasks: list[asyncio.Task] = []
        self.trade_queue = Queue()
        self.last_message_timestamp: Optional[float] = None
        # Event to signal a requested shutdown, breaking the main connection loop.
        self._shutdown_requested = asyncio.Event()

    async def manage_connection(self):
        """
        The main, long-running supervisor task for this class.
        Manages the connection lifecycle, including reconnections.
        """
        logger.info("🚀 WebSocket connection manager started.")
        while not self._shutdown_requested.is_set():
            try:
                # _connect_and_run_session will run until a connection error
                # causes it to raise an exception.
                await self._connect_and_run_session()

            except asyncio.CancelledError:
                logger.info("Connection manager task cancelled.")
                break
            except Exception as e:
                # This block now correctly catches ConnectionClosed and other
                # fatal session errors propagated from _connect_and_run_session.
                logger.error(f"WebSocket session failed: {type(e).__name__} - {e}. The supervisor will attempt to reconnect.")

            if not self._shutdown_requested.is_set():
                logger.info("Will attempt to reconnect in 5 seconds...")
                await asyncio.sleep(5)
        
        logger.info("🛑 WebSocket connection manager has shut down.")

    async def _cleanup_tasks_and_socket(self):
        """Cleanly closes the websocket connection and cancels its tasks."""
        if self.tasks:
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()

        if self.websocket and self.websocket.open:
            try:
                await self.websocket.close()
            except websockets.exceptions.ConnectionClosed:
                pass 
            except Exception as e:
                logger.error(f"Error closing old websocket: {e}")
        self.websocket = None
        self.last_message_timestamp = None
        await self.state.set_ws_refresh_next_run_ts(None)

    async def _connect_and_run_session(self):
        """
        Establishes a single WebSocket session and runs until it's disconnected.
        This function DOES NOT handle connection errors; it lets them propagate
        to the supervisor (manage_connection).
        """
        try:
            logger.info(f"WS: Attempting to connect to {_PUMPPORTAL_WS}...")
            self.websocket = await websockets.connect(
                _PUMPPORTAL_WS,
                ping_interval=20,
                ping_timeout=30
            )
            logger.info("✅ WS: Connection established.")
            self.last_message_timestamp = asyncio.get_event_loop().time()

            await self.subscribe_new_token_stream()
            await self.subscribe_to_migrations()
            await self.resume_subscriptions()

            handler_task = asyncio.create_task(self.message_handler(), name="ws_message_handler")
            self.tasks = [
                handler_task,
                asyncio.create_task(self.unsubscribe_checker(), name="ws_unsubscribe_checker"),
            ]
            if _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED:
                self.tasks.append(asyncio.create_task(self.subscription_refresher(), name="ws_subscription_refresher"))

            # Await the handler task. If it fails (e.g., ConnectionClosed),
            # the exception will propagate out of this function and be
            # caught by the supervisor loop in manage_connection.
            await handler_task

        finally:
            # This cleanup runs whenever this function exits, for any reason,
            # ensuring a clean state before the supervisor attempts to reconnect.
            logger.warning("WS Session: Session ended. Performing cleanup...")
            await self._cleanup_tasks_and_socket()

    async def message_handler(self):
        """Processes incoming WebSocket messages. Exits on connection closed."""
        logger.info("✉️ WebSocket message handler started.")
        try:
            async for message in self.websocket:
                self.last_message_timestamp = asyncio.get_event_loop().time()
                try:
                    data = json.loads(message)
                    if 'message' in data:
                        logger.debug(f"📡 WebSocket confirmation: {data['message']}")
                        continue

                    if data.get('txType') == "create":
                        mint = data.get('mint', 'N/A')
                        logger.debug(f"➕ Received 'new token': {mint}")
                        token_stored = await self.db_client.insert_token(data)
                        if not token_stored:
                            creator = data.get('traderPublicKey')
                            if await self.db_client.is_suspicious_creator(creator):
                                await self.unsubscribe_tokens_from_creator(creator)
                            continue
                        
                        await self.websocket.send(json.dumps({
                            "method": "subscribeTokenTrade",
                            "keys": [data['mint']]
                        }))
                        await self.state.add_token_subscription(data['mint'])
                        active_subs_count = len(await self.state.get_token_subscriptions())
                        logger.debug(f"✅ Subscribed to {data['mint']} --> {active_subs_count} active subscriptions")

                    elif data.get("txType") == "migrate":
                        mint_to_flag = data.get('mint')
                        if not mint_to_flag:
                            logger.warning("Migration event received with no mint address. Discarding.")
                            continue
                        is_tracked = await self.db_client.is_token_active_in_db(mint_to_flag)
                        if is_tracked:
                            logger.info(f"✅ Migration event for tracked token {mint_to_flag}. Processing...")
                            await self.db_client.mark_token_as_migrated(mint_to_flag)
                            await self.db_client.insert_migration(data)
                        else:
                            logger.debug(f"ℹ️ Migration event for untracked or backed-up token {mint_to_flag}. Ignoring.")
                    elif data.get("txType") in ["buy", "sell"]:
                        await self.trade_queue.put(data)
                    else:
                        logger.warning(f"❔ WEBSOCKET - Unknown message type: {data}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON message: {message[:200]}...")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("✉️ Message handler task cancelled.")
        finally:
            logger.info("✉️ Message handler task stopped.")
    
    async def unsubscribe_checker(self):
        """Periodically checks for and unsubscribes from inactive tokens."""
        logger.info("🗑️ WebSocket unsubscribe_checker started.")
        unsubscribe_interval = self.config.get('UNSUBSCRIBE_CHECKER_INTERVAL', 30)

        while not self.state.shutdown_event.is_set():
            try:
                await asyncio.sleep(unsubscribe_interval)

                if not (self.websocket and self.websocket.open):
                    logger.warning("Unsubscribe checker: WebSocket not open. Skipping cycle.")
                    continue
                
                rows = await self.db_client.get_tokens_to_unsubscribe(
                    self.config['MC_DROP_THRESHOLD'], self.config['INACTIVITY_PERIOD'], self.config['MIN_TOKEN_AGE']
                )
                if rows:
                    mints_to_process = [row['mint'] for row in rows]
                    await self.unsubscribe_token_trades_batch(mints_to_process, "rugged_dead")

            except asyncio.CancelledError:
                logger.info("🗑️ Unsubscribe checker task cancelled.")
                break
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Unsubscribe checker: Connection closed during operation. Exiting.")
                break
            except Exception as e:
                logger.error(f"Error in unsubscribe_checker loop: {e}", exc_info=True)
                await asyncio.sleep(5)
        logger.info("🗑️ WebSocket unsubscribe_checker task stopped.")
    
    async def subscribe_new_token_stream(self):
        """Sends a request to subscribe to the newToken stream."""
        if self.websocket and self.websocket.open:
            logger.info("Subscribing to new token stream...")
            await self.websocket.send(json.dumps({"method": "subscribeNewToken"}))
            await self.state.set_new_token_subscription(True)
        else:
            logger.error("Cannot subscribe to new tokens: WebSocket not connected.")
        
    async def subscribe_to_migrations(self):
        """Sends a request to subscribe to the migration event stream."""
        if self.websocket and self.websocket.open:
            try:
                await self.websocket.send(json.dumps({"method": "subscribeMigration"}))
                await self.state.set_migration_subscription(True)
                logger.debug("Successfully sent migration subscription request.")
            except Exception as e:
                logger.error(f"Failed to send migration subscription request: {e}", exc_info=True)
                await self.state.set_migration_subscription(False)
        else:
            await self.state.set_migration_subscription(False)

    async def subscription_refresher(self):
        """
        Periodically refreshes all active token trade subscriptions to prevent desync.
        """
        logger.info("🔄 WebSocket subscription refresher task started.")
        refresh_interval_seconds = _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES * 60

        while not self.state.shutdown_event.is_set():
            try:
                next_run_ts = datetime.now(timezone.utc) + timedelta(seconds=refresh_interval_seconds)
                await self.state.set_ws_refresh_next_run_ts(next_run_ts)
                
                await self.state.wait_or_interrupt(timeout=refresh_interval_seconds)
                if self.state.shutdown_event.is_set():
                    break
                
                if not (self.websocket and self.websocket.open):
                    logger.warning("Subscription refresher: WebSocket not open. Skipping refresh cycle.")
                    continue
                
                await self.state.set_ws_refresh_next_run_ts(None)
                logger.info("🔄 Starting periodic WebSocket subscription refresh...")

                subs_to_refresh = list(await self.state.get_token_subscriptions())
                
                if not subs_to_refresh:
                    logger.info("Subscription refresher: No active subscriptions to refresh. Skipping cycle.")
                    continue

                logger.info(f"Refreshing {len(subs_to_refresh)} token trade subscriptions.")
                await self.unsubscribe_token_trades_batch(subs_to_refresh, "periodic_refresh")
                await asyncio.sleep(2)
                await self.resume_subscriptions()
                logger.info("✅ Periodic WebSocket subscription refresh complete.")

            except asyncio.CancelledError:
                logger.info("🔄 Subscription refresher task cancelled.")
                break
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Subscription refresher: Connection closed during refresh. Exiting task.")
                break 
            except Exception as e:
                logger.error(f"Error in subscription_refresher loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=60)
                
        await self.state.set_ws_refresh_next_run_ts(None)
        logger.info("🔄 WebSocket subscription refresher task stopped.")

    async def resume_subscriptions(self):
        """Resubscribes to all active tokens from the database."""
        if not (self.websocket and self.websocket.open):
            logger.warning("WebSocket not connected, skipping resubscriptions.")
            return
        
        try:
            active_tokens = await self.db_client.get_active_tokens()
            mints_to_subscribe = [row['mint'] for row in active_tokens]
            
            if mints_to_subscribe:
                logger.info(f"Resuming {len(mints_to_subscribe)} active token subscriptions...")
                await self.websocket.send(json.dumps({
                    "method": "subscribeTokenTrade",
                    "keys": mints_to_subscribe
                }))
                for mint in mints_to_subscribe:
                    await self.state.add_token_subscription(mint)
            else:
                logger.info("No active tokens to resume subscriptions for.")
        except Exception as e:
            logger.error(f"Failed to resume subscriptions: {e}", exc_info=True)

    async def unsubscribe_tokens_from_creator(self, creator: str):
        """
        Unsubscribes from all tokens associated with a given creator wallet,
        if they are not part of an active portfolio position.
        """
        try:
            tokens_to_process = await self.db_client.fetch_tokens_by_creator(creator, respect_portfolio=True)
            if not tokens_to_process:
                logger.debug(f"No non-portfolio tokens found for suspicious creator {creator} to unsubscribe.")
                return
            mints_to_unsubscribe = [row['mint'] for row in tokens_to_process]
            logger.warning(f"Found {len(mints_to_unsubscribe)} tokens from suspicious creator '{creator}' to unsubscribe and backup.")
            await self.unsubscribe_token_trades_batch(mints_to_unsubscribe, "suspicious_creator")
        except Exception as e:
            logger.error(f"Error during unsubscribe_tokens_from_creator for {creator}: {e}", exc_info=True)

    async def unsubscribe_token_trades_batch(self, mints: list[str], reason: str):
        """Handles unsubscribing from a batch of tokens and cleaning up the database."""
        if not mints:
            return
        
        logger.info(f"Processing unsubscribe batch of {len(mints)} tokens. Reason: {reason}")
        if self.websocket and self.websocket.open:
            try:
                await self.websocket.send(json.dumps({"method": "unsubscribeTokenTrade", "keys": mints}))
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Could not send unsubscribe batch, connection is already closed.")
            except Exception as e:
                logger.error(f"Failed to send batch unsubscribe message: {e}")

        reasons_to_skip_db_backup = {"shutdown", "periodic_refresh"}
        for mint in mints:
            await self.state.remove_token_subscription(mint)
            if reason not in reasons_to_skip_db_backup:
                await self.db_client.backup_and_delete_token(mint, datetime.now(timezone.utc), reason)

    async def unsubscribe_new_tokens(self):
        """Sends a request to unsubscribe from the newToken stream."""
        if not await self.state.get_new_token_subscription():
            logger.info("Already unsubscribed from newToken stream.")
            return

        if self.websocket and self.websocket.open:
            try:
                await self.websocket.send(json.dumps({"method": "unsubscribeNewToken"}))
                await self.state.set_new_token_subscription(False)
                logger.info("✅ Sent unsubscribe request for newToken stream.")
            except Exception as e:
                logger.error(f"❌ Error sending unsubscribe request for newToken: {e}", exc_info=True)
        else:
            logger.warning("⚠️ Cannot unsubscribe from newToken: WebSocket is not connected.")
            await self.state.set_new_token_subscription(False)

    async def shutdown(self):
        """Gracefully shuts down the WebSocket connection and all related tasks."""
        logger.info("Initiating WebSocketHandler shutdown sequence...")
        self._shutdown_requested.set()

        if self.websocket and self.websocket.open:
            active_subs = list(await self.state.get_token_subscriptions())
            if active_subs:
                logger.info(f"Sending final unsubscribe for {len(active_subs)} tokens.")
                for i in range(0, len(active_subs), UNSUBSCRIBE_BATCH_COUNT):
                    batch = active_subs[i:i + UNSUBSCRIBE_BATCH_COUNT]
                    await self.unsubscribe_token_trades_batch(batch, "shutdown")
                    await asyncio.sleep(0.2)
        
        await self._cleanup_tasks_and_socket()
        logger.info("WebSocketHandler shutdown sequence complete.")

    def get_internal_task_statuses(self) -> list[tuple[str, str]]:
        """Returns the status of internal WebSocket handler tasks."""
        if not self.tasks:
            return [("internal_tasks", "not started")]
        statuses = []
        for task in self.tasks:
            name = task.get_name().replace("ws_", "")
            status_str = "running"
            if task.done():
                status_str = "error" if task.exception() else "done"
            if task.cancelled():
                status_str = "cancelled"
            statuses.append((name, status_str))
        return statuses

    async def get_connection_summary(self) -> dict:
        """Gathers a summary of the WebSocket connection status for monitoring."""
        status_summary = {
            "connection_status": "Disconnected",
            "new_token_subscribed": False,
            "migration_subscribed": False,
            "trade_subscriptions_count": 0,
            "time_since_last_message_s": -1.0
        }

        if self.state.shutdown_event.is_set():
            status_summary["connection_status"] = "Shutting Down"
        elif self.websocket and self.websocket.open:
            status_summary["connection_status"] = "Connected"
        
        status_summary["new_token_subscribed"] = await self.state.get_new_token_subscription()
        status_summary["migration_subscribed"] = await self.state.get_migration_subscription()
        active_subs = await self.state.get_token_subscriptions()
        status_summary["trade_subscriptions_count"] = len(active_subs)
        
        if self.last_message_timestamp:
            time_since_last = asyncio.get_event_loop().time() - self.last_message_timestamp
            status_summary["time_since_last_message_s"] = round(time_since_last, 1)

        return status_summary