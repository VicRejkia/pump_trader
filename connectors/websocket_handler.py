# path: connectors/websocket_handler.py

"""
Manages all WebSocket communication with the PumpPortal API.
This class is designed as a robust, self-healing supervisor that ensures a
persistent connection, manages subscriptions, and provides a clean
interface for the rest of the application.
"""

import asyncio
import json
import random
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List

import websockets
from websockets import exceptions as ws_exceptions

from bot_logger import logger
from state_manager import GlobalState
from database_handler import DatabaseClient
from config.config import (
    _PUMPPORTAL_WS,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES,
    WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS,
    WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS,
    WEBSOCKET_SUBSCRIPTION_BATCH_SIZE,
    WEBSOCKET_BATCH_DELAY,
)

class ConnectionStatus(Enum):
    """Defines the possible states of the WebSocket connection."""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    SHUTTING_DOWN = "Shutting Down"

class WebSocketHandler:
    """A supervisor for managing a persistent WebSocket connection."""

    def __init__(self, db_client: DatabaseClient, state_manager: GlobalState, config: dict):
        """
        Initializes the WebSocketHandler.

        Args:
            db_client: An instance of the DatabaseClient for database operations.
            state_manager: The global state manager instance.
            config: The application's configuration dictionary.
        """
        self.db_client = db_client
        self.state = state_manager
        self.config = config
        self.trade_queue = asyncio.Queue()

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._status = ConnectionStatus.DISCONNECTED
        self._reconnect_delay = WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS
        self._last_message_time: float = 0.0

        # Stores the status of global, non-token-specific subscriptions.
        self._subscribed_to_new_token = False
        self._subscribed_to_migration = False

        # The main task that manages the connection lifecycle.
        self._manager_task: Optional[asyncio.Task] = None

    def start(self):
        """Starts the connection manager as a background task."""
        if self._manager_task is None or self._manager_task.done():
            self._manager_task = asyncio.create_task(self._connection_supervisor(), name="websocket_supervisor")
            logger.info(":rocket: WebSocket Connection Supervisor started.")
        else:
            logger.warning("WebSocket Connection Supervisor is already running.")

    async def shutdown(self):
        """Gracefully shuts down the WebSocket connection and all associated tasks."""
        if self._status == ConnectionStatus.SHUTTING_DOWN:
            return
            
        logger.info("🔌 Shutting down WebSocket handler...")
        self._set_status(ConnectionStatus.SHUTTING_DOWN)

        # Unsubscribe from all active token trades before closing.
        if self._ws and self._ws.open:
            logger.debug("Unsubscribing from all open token trades before shutdown.")
            all_subs = list(await self.state.get_token_subscriptions())
            await self._unsubscribe_in_batches(all_subs, "shutdown")
            self._subscribed_to_new_token = False
            self._subscribed_to_migration = False

        # Cancel the main manager task.
        if self._manager_task and not self._manager_task.done():
            self._manager_task.cancel()
            try:
                await self._manager_task
            except asyncio.CancelledError:
                pass # This is expected on cancellation.

        # Perform final connection cleanup.
        await self._close_connection("Shutdown requested")
        logger.info("✅ WebSocket handler has been shut down successfully.")

    # --- Public Methods for Other Modules ---

    async def unsubscribe_from_trades(self, mints: List[str], reason: str):
        """
        Public method to unsubscribe from token trades for a list of mints.
        Used by modules like `rugcheck_handler` and the `_dead_token_monitor`.

        Args:
            mints: A list of mint addresses to unsubscribe from.
            reason: A string explaining why the unsubscription is happening (for logging).
        """
        if not mints:
            return
        
        #logger.info(f"Request received to unsubscribe from {len(mints)} tokens (Reason: {reason}).")
        await self._unsubscribe_in_batches(mints, reason)

    def get_status(self) -> dict:
        """
        Provides a detailed status report for monitoring purposes (e.g., `monitor_tasks`).

        Returns:
            A dictionary containing the current connection status and health metrics.
        """
        now = asyncio.get_event_loop().time()
        time_since_last_msg = now - self._last_message_time if self._last_message_time > 0 else -1

        return {
            "connection_status": self._status.value,
            "is_connected": self._ws is not None and self._ws.open,
            "new_token_subscribed": self._subscribed_to_new_token,
            "migration_subscribed": self._subscribed_to_migration,
            "trade_subscriptions_count": len(self.state.active_token_subscriptions),
            "time_since_last_message_s": round(time_since_last_msg, 1),
            "time_since_last_pong_s": -1.0, # Kept for backward compatibility in status logs.
        }
        
    # --- Internal Logic: Connection Supervisor ---

    def _set_status(self, new_status: ConnectionStatus):
        """Atomically updates the connection status and logs the change."""
        if self._status != new_status:
            logger.info(f":satellite: WebSocket status changed: {self._status.value} -> {new_status.value}")
            self._status = new_status

    async def _connection_supervisor(self):
        """
        The main supervisor loop that ensures the WebSocket is always connected.
        It handles connection attempts, disconnects, and reconnection with
        exponential backoff and jitter to avoid spamming the server.
        """
        while self._status != ConnectionStatus.SHUTTING_DOWN:
            try:
                self._set_status(ConnectionStatus.CONNECTING)
                # We disable the library's automatic pinging (`ping_interval=None`)
                # in favor of our own application-level pinger, which is more reliable
                # for custom WebSocket APIs.
                async for websocket in websockets.connect(
                    _PUMPPORTAL_WS,
                    ping_interval=None, 
                    open_timeout=20,
                    extra_headers={"Origin": "https://pumpportal.fun"}
                ):
                    self._ws = websocket
                    self._set_status(ConnectionStatus.CONNECTED)
                    logger.info("✅ WebSocket connection established successfully.")
                    # Reset the reconnect delay upon a successful connection.
                    self._reconnect_delay = WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS
                    
                    # Start the session handler which manages the active connection.
                    await self._session_handler()
            
            except ws_exceptions.WebSocketException as e:
                logger.warning(f":police_car_light: WebSocket connection error: {e}. Attempting to reconnect.")
            except asyncio.CancelledError:
                logger.info(":stop_sign: Connection supervisor task was cancelled.")
                break
            except Exception as e:
                logger.error(f":police_car_light: Unexpected error in connection supervisor: {e}", exc_info=True)

            if self._status == ConnectionStatus.SHUTTING_DOWN:
                break
            
            # If the loop breaks for any reason other than shutdown, initiate reconnection.
            self._set_status(ConnectionStatus.RECONNECTING)
            
            # Calculate wait time with jitter to prevent synchronized reconnect storms.
            jitter = random.uniform(0.5, 1.5)
            wait_time = min(self._reconnect_delay * jitter, WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS)
            logger.info(f":stopwatch: Waiting {wait_time:.2f} seconds before next connection attempt...")
            
            await asyncio.sleep(wait_time)
            # Increase the delay for the next potential attempt.
            self._reconnect_delay = min(self._reconnect_delay * 2, WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS)

        logger.info("🛑 WebSocket Connection Supervisor has shut down.")

    # --- Internal Logic: Session and Message Handling ---

    async def _session_handler(self):
        """
        Manages an active WebSocket session by running all necessary background tasks
        like message receiving, health checks, and subscription management. The session
        ends if any of these tasks fail, which triggers the supervisor to reconnect.
        """
        if not self._ws: return

        self._last_message_time = asyncio.get_event_loop().time()

        # Create all tasks that should run during an active session.
        session_tasks = [
            asyncio.create_task(self._message_receiver(), name="ws_receiver"),
            asyncio.create_task(self._health_checker(), name="ws_health_checker"),
            asyncio.create_task(self._application_pinger(), name="ws_app_pinger"),
            asyncio.create_task(self._subscription_refresher(), name="ws_subscription_refresher"),
            asyncio.create_task(self._dead_token_monitor(), name="ws_dead_token_monitor")
        ]
        
        try:
            # Subscribe to all required streams at the start of the session.
            await self._initialize_subscriptions()
            
            # Wait for the first task to complete, which indicates the session has ended.
            done, pending = await asyncio.wait(session_tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Log why the session ended.
            for task in done:
                if task.exception():
                    logger.warning(f"WebSocket session ended because task '{task.get_name()}' failed with error: {task.exception()}")
                else:
                    logger.warning(f"WebSocket session ended because task '{task.get_name()}' finished unexpectedly.")
            
            # Cancel all other running session tasks.
            for task in pending:
                task.cancel()

        except Exception as e:
            logger.error(f":police_car_light: Error during WebSocket session handling: {e}", exc_info=True)
        finally:
            await self._close_connection("Session ended")

    async def _message_receiver(self):
        """Continuously listens for incoming messages and dispatches them."""
        if not self._ws: return
        try:
            async for message in self._ws:
                # Update the timestamp of the last message to keep the health check happy.
                self._last_message_time = asyncio.get_event_loop().time()
                await self._handle_incoming(message)
        except asyncio.CancelledError:
            pass # Normal shutdown procedure.
        except ws_exceptions.ConnectionClosed as e:
            logger.warning(f"Connection closed in receiver: {e.code} {e.reason}")
            raise ConnectionError(f"Connection closed: {e.code}") # Raise to terminate the session.
        except Exception as e:
            logger.error(f":police_car_light: Error in message receiver: {e}", exc_info=True)
            raise # Raise to terminate the session.

    async def _handle_incoming(self, raw_message: str):
        """
        Processes the logic for a single incoming message, similar to the old implementation.
        """
        try:
            data = json.loads(raw_message)
            tx_type = data.get("txType")

            if tx_type == "create":
                mint = data.get("mint")
                if not mint: return
                
                # The logic to insert into DB and check creator limits is encapsulated in `insert_token`.
                # It returns `True` if the token is new and meets all criteria.
                is_new_and_valid = await self.db_client.insert_token(data)
                
                if is_new_and_valid:
                    logger.info(f":heavy_plus_sign: New valid token detected: {mint}. Subscribing to trades.")
                    await self._send_json({"method": "subscribeTokenTrade", "keys": [mint]})
                    await self.state.add_token_subscription(mint)

                    # <<< ADD TO AI QUEUE (Priority 4 Sampling) >>>
                    if self.config.get('AI_DECISION_MAKING_ENABLED', False):
                        sample_rate = self.config.get('AI_NEW_TOKEN_SAMPLE_RATE', 0.02)
                        if random.random() < sample_rate:
                            ai_q = self.state.get_ai_evaluation_queue()
                            if not ai_q.full():
                                await ai_q.put((0, (mint, 'INITIAL BUY'))) # Priority 0
                                logger.debug(f"AI Queue: Added new token {mint} via sampling.")
                            else:
                                logger.warning(f"AI Queue is full, could not add sampled new token {mint}.")
                    # <<< END AI QUEUE ADDITION >>>

            elif tx_type == "migrate":
                mint = data.get("mint")
                if mint and await self.db_client.is_token_active_in_db(mint):
                    await self.db_client.mark_token_as_migrated(mint)
                    await self.db_client.insert_migration(data)
                    # <<< Optional: Trigger AI eval on migration (Priority 3) >>>
                    # You could add logic here to put the migrated token
                    # into the AI queue if desired, similar to the event checker.
                    # ai_q = self.state.get_ai_evaluation_queue()
                    # if not ai_q.full():
                    #    await ai_q.put((-25, (mint, 'SELL/HOLD' or 'REBUY'))) # Adjust context

            elif tx_type in ["buy", "sell"]:
                await self.trade_queue.put(data)
                
        except json.JSONDecodeError:
            logger.debug(f"Received non-JSON message: {raw_message[:100]}")
        except Exception as e:
            logger.error(f":police_car_light: Error processing incoming message: {e}", exc_info=True)

    # --- Internal Logic: Subscriptions & Health Checks ---

    async def _application_pinger(self):
        """Periodically sends an application-level ping message to keep the connection alive."""
        while self._status == ConnectionStatus.CONNECTED:
            try:
                await asyncio.sleep(20) # Send a ping every 20 seconds.
                await self._send_json({"method": "ping"})
                logger.debug("Application-level ping sent.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Failed to send application-level ping: {e}")
                break # Failure to send means the connection is likely dead; break to trigger a reconnect.

    async def _health_checker(self):
        """
        Monitors connection health by checking if any message (including responses to our pings)
        has been received recently.
        """
        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(30) # Check every 30 seconds.
            
            time_since_last_message = asyncio.get_event_loop().time() - self._last_message_time
            
            # If we haven't received ANY message for 60 seconds (despite sending a ping every 20s),
            # the connection is considered stale/dead.
            if time_since_last_message > 60:
                logger.warning(f"No message received for {time_since_last_message:.0f}s. Connection is considered stale.")
                raise ConnectionError("Stale connection")
    
    async def _initialize_subscriptions(self):
        """Subscribes to all necessary streams when a new connection is established."""
        logger.info("Initializing subscriptions...")
        
        # Global streams
        await self._send_json({"method": "subscribeNewToken"})
        self._subscribed_to_new_token = True
        logger.debug("-> 'subscribeNewToken' message sent.")
        
        await self._send_json({"method": "subscribeMigration"})
        self._subscribed_to_migration = True
        logger.debug("-> 'subscribeMigration' message sent.")

        # Subscriptions for existing active tokens from the database
        active_tokens = await self.db_client.get_active_tokens()
        mints_to_subscribe = [record["mint"] for record in active_tokens]
        
        if mints_to_subscribe:
            logger.info(f"Resuming {len(mints_to_subscribe)} existing token subscriptions...")
            await self._subscribe_in_batches(mints_to_subscribe)
            
        logger.info("✅ All initial subscriptions have been sent.")

    async def _subscribe_in_batches(self, mints: List[str]):
        """Subscribes to a list of mints in batches to avoid overwhelming the API."""
        for i in range(0, len(mints), WEBSOCKET_SUBSCRIPTION_BATCH_SIZE):
            if self._status != ConnectionStatus.CONNECTED: break
            batch = mints[i:i + WEBSOCKET_SUBSCRIPTION_BATCH_SIZE]
            await self._send_json({"method": "subscribeTokenTrade", "keys": batch})
            for mint in batch:
                await self.state.add_token_subscription(mint)
            logger.debug(f"Sent subscription batch for {len(batch)} tokens.")
            await asyncio.sleep(WEBSOCKET_BATCH_DELAY)

    async def _unsubscribe_in_batches(self, mints: List[str], reason: str):
        """Unsubscribes from mints in batches and updates the state accordingly."""
        for i in range(0, len(mints), WEBSOCKET_SUBSCRIPTION_BATCH_SIZE):
            batch = mints[i:i + WEBSOCKET_SUBSCRIPTION_BATCH_SIZE]
            
            # Send unsubscribe message if connected.
            if self._ws and self._ws.open:
                await self._send_json({"method": "unsubscribeTokenTrade", "keys": batch})
            
            # Always update the local state.
            for mint in batch:
                await self.state.remove_token_subscription(mint)

            logger.debug(f"Sent unsubscription batch for {len(batch)} tokens (Reason: {reason}).")
            
            # If the reason is terminal (e.g., dead token), also archive/delete from DB.
            if reason in ["dead_token", "high_rugcheckscore"]:
                for mint in batch:
                    await self.db_client.backup_and_delete_token(
                        mint=mint, 
                        archived_at=datetime.now(timezone.utc),
                        reason=reason
                    )
            
            await asyncio.sleep(WEBSOCKET_BATCH_DELAY)

    async def _subscription_refresher(self):
        """Periodically refreshes all `subscribeTokenTrade` subscriptions to prevent them from going stale."""
        if not _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED:
            logger.info("Automatic subscription refresher is disabled.")
            return

        interval = _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES * 60
        logger.info(f"🔄 Subscription refresher started. Interval: {interval / 60} minutes.")

        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(interval)
            logger.info("Starting periodic subscription refresh...")
            
            # Unsubscribe from all currently tracked tokens.
            current_subs = list(await self.state.get_token_subscriptions())
            if current_subs:
                await self._unsubscribe_in_batches(current_subs, "periodic_refresh")
                
            await asyncio.sleep(2) # Brief pause before re-subscribing.
            
            # Get the latest list of active tokens from the database and re-subscribe.
            active_tokens_now = await self.db_client.get_active_tokens()
            mints_to_resubscribe = [r["mint"] for r in active_tokens_now]
            
            if mints_to_resubscribe:
                await self._subscribe_in_batches(mints_to_resubscribe)
            
            logger.info(f"✅ Periodic refresh complete. {len(mints_to_resubscribe)} subscriptions are now active.")
        
        logger.info("Subscription refresher stopped because connection was lost.")

    async def _dead_token_monitor(self):
        """
        Periodically checks the database for tokens that have become inactive or "dead"
        and unsubscribes from their trade streams.
        """
        # Check at half the inactivity period to be proactive.
        interval = 60
        logger.info(f"🗑️ Dead token monitor started. Check interval: {interval / 60:.1f} minutes.")
        
        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(interval)
            try:
                tokens_to_unsub = await self.db_client.get_tokens_to_unsubscribe(
                    self.config["MC_DROP_THRESHOLD"],
                    self.config["INACTIVITY_PERIOD"],
                    self.config["MIN_TOKEN_AGE"]
                )
                
                if tokens_to_unsub:
                    mints = [record["mint"] for record in tokens_to_unsub]
                    logger.info(f"Found {len(mints)} dead/inactive tokens. Unsubscribing.")
                    await self.unsubscribe_from_trades(mints, "dead_token")

            except Exception as e:
                logger.error(f":police_car_light: Error in dead token monitor: {e}", exc_info=True)
                
        logger.info("Dead token monitor stopped because connection was lost.")

    # --- Helper Functions ---

    async def _send_json(self, data: dict):
        """Safely sends a JSON payload over the WebSocket."""
        if self._ws and self._ws.open:
            try:
                await self._ws.send(json.dumps(data))
            except ws_exceptions.ConnectionClosed:
                logger.warning("Attempted to send on a closed connection.")
                raise ConnectionError("Connection closed during send")
            except Exception as e:
                logger.error(f"Failed to send data: {e}")
                raise
        else:
            logger.warning("Attempted to send but WebSocket is not connected.")
            raise ConnectionError("WebSocket is not open")

    async def _close_connection(self, reason: str):
        """Closes the WebSocket connection if it exists."""
        if self._ws:
            logger.debug(f"Closing WebSocket connection (Reason: {reason})...")
            try:
                await self._ws.close(code=1000, reason=reason)
            except Exception as e:
                # This can happen if the connection is already dead, which is fine.
                logger.debug(f":police_car_light: Error while closing WebSocket connection (may be expected): {e}")
            finally:
                self._ws = None
                self._set_status(ConnectionStatus.DISCONNECTED)