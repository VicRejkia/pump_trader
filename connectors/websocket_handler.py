# path: connectors/websocket_handler.py

"""
Manages WebSocket communication with the external PumpPortal API.
Handles incoming messages, token subscriptions, reconnections, and shutdown.
"""

import asyncio
from asyncio import Queue
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
import random
import websockets
from websockets import exceptions as ws_exceptions
from enum import Enum

from config.config import (
    _PUMPPORTAL_WS,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES,
)
from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState

UNSUBSCRIBE_BATCH_COUNT = 15


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    SHUTTING_DOWN = "shutting_down"


class WebSocketHandler:
    _WS_STALE_THRESHOLD_SECONDS = 25  # 20% below server-side timeout
    _CONNECTION_TIMEOUT = 45.0
    _HEALTH_CHECK_INTERVAL = 8
    _STABLE_CONNECTION_RESET_MINUTES = 5  # Reset backoff after sustained connection
    _WS_GRACEFUL_CLOSE_TIMEOUT = 5.0
    _PING_INTERVAL = 15  # More frequent pings
    _PING_TIMEOUT = 10
    _MAX_RECONNECT_DELAY = 60.0
    _INITIAL_RECONNECT_DELAY = 1.0

    def __init__(self, db_client: DatabaseClient, config_dict: dict, state_manager: GlobalState):
        self.state = state_manager
        self.db_client = db_client
        self.config = config_dict

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.tasks: list[asyncio.Task] = []
        self.trade_queue = Queue()
        self.last_message_timestamp: Optional[float] = None
        self.last_pong_timestamp: Optional[float] = None

        self._shutdown_requested = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self._connection_state = ConnectionState.DISCONNECTED
        self._connection_state_lock = asyncio.Lock()
        self._reconnect_delay = self._INITIAL_RECONNECT_DELAY
        
        # Track connection attempts for debugging
        self._connection_attempts = 0
        self._last_connection_attempt = None

        self._last_healthy_message = None  # Track last healthy message
        self._manager_task: Optional[asyncio.Task] = None # <-- ADD THIS

    # -------------------------
    # Connection State Management
    # -------------------------
    async def _set_connection_state(self, new_state: ConnectionState):
        """Safely update connection state"""
        async with self._connection_state_lock:
            old_state = self._connection_state
            self._connection_state = new_state
            if old_state != new_state:
                logger.info(f"WebSocket state transition: {old_state.value} -> {new_state.value}")

    async def _get_connection_state(self) -> ConnectionState:
        """Get current connection state"""
        async with self._connection_state_lock:
            return self._connection_state

    def _is_websocket_open(self) -> bool:
        """Check if WebSocket is truly open and usable"""
        if not self.websocket:
            return False
        
        # Check WebSocket state enum directly
        try:
            from websockets.protocol import State
            return (
                self.websocket.state == State.OPEN and 
                not self.websocket.closed
            )
        except (AttributeError, ImportError):
            # Fallback for older websockets versions
            return bool(self.websocket.open)

    # -------------------------
    # Supervisor loop
    # -------------------------
    async def manage_connection(self):
        """Supervisor loop that manages connection lifecycle"""
        logger.info("🚀 WebSocket connection manager started.")
        self._manager_task = asyncio.current_task()
        
        while not self._shutdown_requested.is_set():
            try:
                current_state = await self._get_connection_state()
                
                if current_state == ConnectionState.SHUTTING_DOWN:
                    break

                # Smart delay reset logic
                if self._last_connection_attempt:
                    time_since_last = datetime.now(timezone.utc) - self._last_connection_attempt
                    if time_since_last > timedelta(minutes=10):
                        self._reconnect_delay = self._INITIAL_RECONNECT_DELAY
                        logger.info("🔄 Reset reconnect delay after prolonged downtime")
                
                # Track connection attempt with detailed logging
                self._connection_attempts += 1
                self._last_connection_attempt = datetime.now(timezone.utc)
                logger.info(
                    f"🔌 Connection attempt #{self._connection_attempts} "
                    f"(delay: {self._reconnect_delay:.1f}s, "
                    f"state: {current_state.value})"
                )
                
                # Set state to connecting
                await self._set_connection_state(ConnectionState.CONNECTING)
                
                try:
                    # Establish connection with detailed timeout handling
                    connection_successful = await asyncio.wait_for(
                        self._connect_and_run_session(),
                        timeout=self._CONNECTION_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.error("⌛ Connection attempt timed out")
                    connection_successful = False
                
                if connection_successful:
                    # Reset reconnect delay on successful connection
                    self._reconnect_delay = self._INITIAL_RECONNECT_DELAY
                else:
                    # Connection failed, prepare for reconnect
                    await self._set_connection_state(ConnectionState.RECONNECTING)
                    
                    if not self._shutdown_requested.is_set():
                        # Exponential backoff with jitter
                        jitter = random.uniform(0, self._reconnect_delay * 0.1)
                        sleep_time = min(self._reconnect_delay + jitter, self._MAX_RECONNECT_DELAY)
                        
                        logger.info(f"Reconnecting in {sleep_time:.1f}s (attempt #{self._connection_attempts + 1})")
                        
                        try:
                            await asyncio.wait_for(
                                self._shutdown_requested.wait(), 
                                timeout=sleep_time
                            )
                        except asyncio.TimeoutError:
                            pass
                        
                        # Increase delay for next attempt
                        self._reconnect_delay = min(
                            self._reconnect_delay * 2, 
                            self._MAX_RECONNECT_DELAY
                        )
                
            except asyncio.CancelledError:
                logger.info("Connection manager task cancelled.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in connection manager: {e}", exc_info=True)
                await asyncio.sleep(5)

        # Final cleanup
        await self._set_connection_state(ConnectionState.SHUTTING_DOWN)
        await self._cleanup_connection()
        logger.info("🛑 WebSocket connection manager has shut down.")

    # -------------------------
    # Session lifecycle
    # -------------------------
    async def _connect_and_run_session(self) -> bool:
        """
        Establish connection and run session.
        Returns True if session ended cleanly, False if it failed.
        """
        session_successful = False
        
        try:
            # Clean up any previous connection
            await self._cleanup_connection()
            
            if self._shutdown_requested.is_set():
                return False
            
            # Establish new connection
            logger.info(f"Connecting to {_PUMPPORTAL_WS}...")
            
            self.websocket = await websockets.connect(
                _PUMPPORTAL_WS,
                ping_interval=self._PING_INTERVAL,
                ping_timeout=self._PING_TIMEOUT,
                close_timeout=self._WS_GRACEFUL_CLOSE_TIMEOUT,
                max_queue=1024,
                read_limit=2**20,
                write_limit=2**20,
                origin="https://pumpportal.com",
                compression="deflate",
                open_timeout=self._CONNECTION_TIMEOUT,
                extra_headers={
                    "User-Agent": "PumpTraderBot/1.0",
                    "Accept-Encoding": "gzip, deflate",
                    "Cache-Control": "no-cache"
                }
            )
            logger.debug(f"WebSocket connected with protocol: {self.websocket.subprotocol}")
            
            logger.info("✅ WebSocket connected successfully.")
            await self._set_connection_state(ConnectionState.CONNECTED)
            
            # Initialize timestamps
            current_time = asyncio.get_event_loop().time()
            self.last_message_timestamp = current_time
            self.last_pong_timestamp = current_time
            
            # Initialize subscriptions with enhanced logging
            logger.debug("Starting subscription initialization")
            try:
                # Initialize subscriptions with retry logic
                await self._retry_subscriptions()
                logger.info("Subscription initialization completed successfully")
                
                # Update activity timestamps after successful setup
                current_time = asyncio.get_event_loop().time()
                self.last_message_timestamp = current_time
                self.last_pong_timestamp = current_time
                
                # Immediate health check after subscriptions
                await self._health_monitor()
                
            except Exception as e:
                logger.error(f"Subscription initialization failed: {str(e)}", exc_info=True)
                raise ConnectionError("Critical subscription failure") from e
            
            # Create session tasks
            session_tasks = [
                asyncio.create_task(self._message_handler(), name="ws_message_handler"),
                asyncio.create_task(self._health_monitor(), name="ws_health_monitor"),
                asyncio.create_task(self.unsubscribe_checker(), name="ws_unsubscribe_checker"),
            ]
            
            if _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED:
                session_tasks.append(
                    asyncio.create_task(self.subscription_refresher(), name="ws_subscription_refresher")
                )
            
            self.tasks = session_tasks
            
            # Wait for any task to complete (indicates session end)
            done, pending = await asyncio.wait(
                session_tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Check if session ended due to shutdown
            if self._shutdown_requested.is_set():
                session_successful = True
            else:
                # Check what caused the session to end
                for task in done:
                    if task.exception():
                        logger.error(f"Session task {task.get_name()} failed: {task.exception()}")
                        session_successful = False
                        break
                else:
                    # Task completed normally (shouldn't happen for infinite loops)
                    session_successful = True
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
            
            # Wait for all tasks to complete
            await asyncio.gather(*pending, return_exceptions=True)
            
        except asyncio.TimeoutError:
            logger.error("Connection attempt timed out.")
            session_successful = False
        except ws_exceptions.InvalidURI:
            logger.error(f"Invalid WebSocket URI: {_PUMPPORTAL_WS}")
            session_successful = False
        except ws_exceptions.InvalidHandshake as e:
            logger.error(f"WebSocket handshake failed: {e}")
            session_successful = False
        except ConnectionRefusedError:
            logger.error("Connection refused by server.")
            session_successful = False
        except OSError as e:
            logger.error(f"Network error: {e}")
            session_successful = False
        except Exception as e:
            logger.error(f"Unexpected error during session: {e}", exc_info=True)
            session_successful = False
        finally:
            # Clean up connection
            await self._cleanup_connection()
            await self._set_connection_state(ConnectionState.DISCONNECTED)
        
        return session_successful

    # -------------------------
    # Connection cleanup
    # -------------------------
    async def _cleanup_connection(self):
        """Clean up WebSocket connection and associated tasks"""
        # Cancel all tasks
        if self.tasks:
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()
        
        # Close WebSocket connection
        if self.websocket:
            try:
                # Try graceful close first
                await asyncio.wait_for(
                    self.websocket.close(),
                    timeout=self._WS_GRACEFUL_CLOSE_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning("WebSocket close timed out, forcing close...")
                # Force close by closing transport
                if hasattr(self.websocket, 'transport') and self.websocket.transport:
                    self.websocket.transport.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            finally:
                self.websocket = None
        
        # Reset timestamps
        self.last_message_timestamp = None
        self.last_pong_timestamp = None
        
        # Clear state
        await self.state.set_ws_refresh_next_run_ts(None)

    # -------------------------
    # Message handling
    # -------------------------
    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        logger.info("✉️ WebSocket message handler started.")
        
        try:
            while not self._shutdown_requested.is_set():
                if not self._is_websocket_open():
                    logger.warning("WebSocket not open in message handler.")
                    break
                
                try:
                    # Use wait_for to prevent infinite blocking
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=self._WS_STALE_THRESHOLD_SECONDS
                    )
                    
                    # Update timestamp
                    self.last_message_timestamp = asyncio.get_event_loop().time()
                    
                    # Process message
                    await self._handle_incoming(message)
                    
                except asyncio.TimeoutError:
                    # No message received within timeout
                    logger.warning(f"No message received for {self._WS_STALE_THRESHOLD_SECONDS}s")
                    raise ConnectionError("Receive timeout")
                except ws_exceptions.ConnectionClosed as e:
                    logger.warning(f"WebSocket connection closed: {e.code} - {e.reason}")
                    if e.code == 1006:
                        logger.error("🚨 Abnormal closure detected - performing full reset")
                        self.last_message_timestamp = None
                        self.last_pong_timestamp = None
                        await self._cleanup_connection()
                        await self._set_connection_state(ConnectionState.DISCONNECTED)
                        logger.debug("Full connection state reset completed")
                        raise ConnectionError("Abnormal closure (1006)") from e
                except Exception as e:
                    logger.error(f"Error receiving message: {e}", exc_info=True)
                    break
                    
        except asyncio.CancelledError:
            logger.info("Message handler cancelled.")
            raise
        finally:
            logger.info("✉️ Message handler stopped.")

    async def _handle_incoming(self, raw: str):
        """Process incoming message"""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Not JSON, might be a ping/pong or other protocol message
            await self.trade_queue.put({"raw": raw})
            return

        # Handle different message types
        if data.get("txType") == "create":
            mint = data.get("mint")
            logger.debug(f"➕ New token: {mint}")
            stored = await self.db_client.insert_token(data)
            if stored:
                try:
                    await self.safe_send(json.dumps({"method": "subscribeTokenTrade", "keys": [mint]}))
                    await self.state.add_token_subscription(mint)
                except Exception as e:
                    logger.error(f"Failed to subscribe token {mint}: {e}")
                    
        elif data.get("txType") == "migrate":
            mint = data.get("mint")
            if mint and await self.db_client.is_token_active_in_db(mint):
                await self.db_client.mark_token_as_migrated(mint)
                await self.db_client.insert_migration(data)
                
        elif data.get("txType") in ["buy", "sell"]:
            await self.trade_queue.put(data)

    # -------------------------
    # Health monitoring
    # -------------------------
    async def _health_monitor(self):
        """Monitor connection health and trigger reconnection if needed"""
        logger.info("🏥 Health monitor started.")
        
        try:
            while not self._shutdown_requested.is_set():
                await asyncio.sleep(10)  # Check every 10 seconds
                
                if not self._is_websocket_open():
                    logger.warning("WebSocket not open, triggering reconnection...")
                    raise ConnectionError("WebSocket not open")

                # Check for stale connection
                if self.last_message_timestamp:
                    elapsed = asyncio.get_event_loop().time() - self.last_message_timestamp
                    if elapsed > self._WS_STALE_THRESHOLD_SECONDS:
                        logger.warning(f"Connection stale for {elapsed:.1f}s, triggering reconnection...")
                        raise ConnectionError("Connection stale")
                
                # Manual ping check
                try:
                    pong_waiter = await self.websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                    self.last_pong_timestamp = asyncio.get_event_loop().time()
                except asyncio.TimeoutError:
                    logger.warning("⌛ Ping timeout - No response from server")
                    raise ConnectionError("Ping timeout") from None
                except Exception as e:
                    logger.warning(f"Ping failed: {e}")
                    raise
                    
        except asyncio.CancelledError:
            logger.info("Health monitor cancelled.")
            raise
        finally:
            logger.info("🏥 Health monitor stopped.")

    # -------------------------
    # Safe send helper
    # -------------------------
    async def safe_send(self, message: str, wait_timeout: float = 5.0):
        """Safely send message through WebSocket"""
        async with self._send_lock:
            if not self._is_websocket_open():
                raise RuntimeError("WebSocket not connected.")
            
            try:
                await asyncio.wait_for(
                    self.websocket.send(message), 
                    timeout=wait_timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Send timeout after {wait_timeout}s")
                raise
            except ws_exceptions.ConnectionClosed as e:
                logger.error(f"Connection closed during send: {e}")
                raise
            except Exception as e:
                logger.error(f"Send failed: {e}", exc_info=True)
                raise

    # -------------------------
    # Subscription management
    # -------------------------
    async def _retry_subscriptions(self, max_attempts=3):
        """Retry subscriptions with backoff"""
        attempt = 0
        while attempt < max_attempts and not self._shutdown_requested.is_set():
            try:
                if not self._is_websocket_open():
                    raise ConnectionError("WebSocket not open for subscriptions")
                
                logger.debug(f"Attempting subscriptions (try {attempt+1}/{max_attempts})")
                await self.subscribe_new_token_stream()
                await self.subscribe_to_migrations()
                await self.resume_subscriptions()
                logger.info("All subscriptions established successfully")
                return
            except Exception as e:
                attempt += 1
                wait_time = min(2 ** attempt, 10)  # Exponential backoff capped at 10s
                logger.warning(f"Subscription failed (attempt {attempt}): {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
        
        logger.error("Failed to establish subscriptions after multiple attempts")
        raise ConnectionError("Subscription setup failed")

    async def subscribe_new_token_stream(self):
        """Subscribe to new token stream with confirmation"""
        if self._is_websocket_open():
            try:
                sub_id = f"sub-new-{datetime.now().timestamp()}"
                sub_msg = json.dumps({
                    "method": "subscribeNewToken",
                    "id": sub_id
                })
                
                await self.safe_send(sub_msg)
                logger.debug(f"Sent subscription request: {sub_id}")
                
                # Wait for confirmation
                # Get and parse response
                raw_response = await asyncio.wait_for(self.websocket.recv(), timeout=15)
                ack = json.loads(raw_response)
                
                # Validate acknowledgement
                if not isinstance(ack, dict) or ack.get("id") != sub_id or not ack.get("success", False):
                    raise ConnectionError(f"Subscription failed: {ack.get('error', 'Unknown error')}")
                
                await self.state.set_new_token_subscription(True)
                logger.info(f"✅ Verified new token subscription ({sub_id})")
                # Update activity timestamps
                current_time = asyncio.get_event_loop().time()
                self.last_message_timestamp = current_time
                self.last_pong_timestamp = current_time
            except Exception as e:
                logger.error(f"Failed to subscribe to new tokens: {e}")
                await self.state.set_new_token_subscription(False)

    async def subscribe_to_migrations(self):
        """Subscribe to migration stream"""
        if self._is_websocket_open():
            try:
                await self.safe_send(json.dumps({"method": "subscribeMigration"}))
                await self.state.set_migration_subscription(True)
                logger.info("Subscribed to migration stream")
            except Exception as e:
                logger.error(f"Failed to subscribe to migrations: {e}")
                await self.state.set_migration_subscription(False)

    async def resume_subscriptions(self):
        """Resume token trade subscriptions"""
        if not self._is_websocket_open():
            return
            
        active_tokens = await self.db_client.get_active_tokens()
        mints = [r["mint"] for r in active_tokens]
        
        if mints:
            # Subscribe in batches to avoid overwhelming the server
            batch_size = 100
            for i in range(0, len(mints), batch_size):
                batch = mints[i:i+batch_size]
                try:
                    await self.safe_send(json.dumps({"method": "subscribeTokenTrade", "keys": batch}))
                    for mint in batch:
                        await self.state.add_token_subscription(mint)
                    logger.info(f"Resumed {len(batch)} token subscriptions")
                    await asyncio.sleep(0.5)  # Small delay between batches
                except Exception as e:
                    logger.error(f"Failed to resume subscription batch: {e}")

    # -------------------------
    # Maintenance tasks
    # -------------------------
    async def unsubscribe_checker(self):
        """Periodically check for tokens to unsubscribe"""
        logger.info("🗑️ Unsubscribe checker started.")
        interval = self.config.get("UNSUBSCRIBE_CHECKER_INTERVAL", 30)
        
        try:
            while not self._shutdown_requested.is_set():
                await asyncio.sleep(interval)
                
                if not self._is_websocket_open():
                    continue
                
                try:
                    rows = await self.db_client.get_tokens_to_unsubscribe(
                        self.config["MC_DROP_THRESHOLD"],
                        self.config["INACTIVITY_PERIOD"],
                        self.config["MIN_TOKEN_AGE"]
                    )
                    
                    if rows:
                        mints = [r["mint"] for r in rows]
                        await self.unsubscribe_token_trades_batch(mints, "rugged_dead")
                        
                except Exception as e:
                    logger.error(f"Error in unsubscribe checker: {e}", exc_info=True)
                    
        except asyncio.CancelledError:
            logger.info("Unsubscribe checker cancelled.")
            raise
        finally:
            logger.info("🗑️ Unsubscribe checker stopped.")

    async def subscription_refresher(self):
        """Periodically refresh all subscriptions"""
        logger.info("🔄 Subscription refresher started.")
        interval = _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES * 60
        
        try:
            while not self._shutdown_requested.is_set():
                await self.state.wait_or_interrupt(timeout=interval)
                
                if self._shutdown_requested.is_set():
                    break
                
                if not self._is_websocket_open():
                    continue
                
                try:
                    subs = list(await self.state.get_token_subscriptions())
                    if subs:
                        logger.info(f"Refreshing {len(subs)} subscriptions...")
                        await self.unsubscribe_token_trades_batch(subs, "periodic_refresh")
                        await asyncio.sleep(2)
                        await self.resume_subscriptions()
                        
                except Exception as e:
                    logger.error(f"Error in subscription refresher: {e}", exc_info=True)
                    
        except asyncio.CancelledError:
            logger.info("Subscription refresher cancelled.")
            raise
        finally:
            logger.info("🔄 Subscription refresher stopped.")

    async def unsubscribe_token_trades_batch(self, mints: list[str], reason: str):
        """Unsubscribe from multiple token trades"""
        if not mints:
            return
            
        if self._is_websocket_open():
            # Unsubscribe in batches
            batch_size = 100
            for i in range(0, len(mints), batch_size):
                batch = mints[i:i+batch_size]
                try:
                    await self.safe_send(json.dumps({"method": "unsubscribeTokenTrade", "keys": batch}))
                    logger.info(f"Unsubscribed from {len(batch)} tokens (reason: {reason})")
                    await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"Failed to unsubscribe batch: {e}")

        # Update state regardless of WebSocket status
        for mint in mints:
            await self.state.remove_token_subscription(mint)
            if reason not in {"shutdown", "periodic_refresh"}:
                await self.db_client.backup_and_delete_token(
                    mint, 
                    datetime.now(timezone.utc), 
                    reason
                )

    # -------------------------
    # Public interface
    # -------------------------
    async def force_reconnect(self):
        """Public method to manually trigger a reconnection."""
        logger.info("Manual WebSocket reconnection triggered by command.")
        if self._manager_task and not self._manager_task.done():
            # Cancelling the session tasks will cause the _connect_and_run_session
            # to exit, which in turn causes the manage_connection loop to restart.
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            logger.info("Cancelled active session tasks to force reconnection loop.")
        else:
            logger.warning("Could not force reconnect: Manager task is not running.")


    async def shutdown(self):
        """Gracefully shutdown the WebSocket handler"""
        logger.info("Shutting down WebSocket handler...")
        self._shutdown_requested.set()
        await self._set_connection_state(ConnectionState.SHUTTING_DOWN)
        
        # Give tasks a moment to notice shutdown flag
        await asyncio.sleep(0.5)
        
        # Clean up connection
        await self._cleanup_connection()
        
        logger.info("WebSocket handler shutdown complete.")

    async def get_connection_summary(self) -> dict:
        """Get connection status summary"""
        summary = {
            "connection_status": (await self._get_connection_state()).value,
            "websocket_open": self._is_websocket_open(),
            "new_token_subscribed": await self.state.get_new_token_subscription(),
            "migration_subscribed": await self.state.get_migration_subscription(),
            "trade_subscriptions_count": len(await self.state.get_token_subscriptions()),
            "time_since_last_message_s": -1.0,
            "time_since_last_pong_s": -1.0,
            "connection_attempts": self._connection_attempts,
            "last_connection_attempt": self._last_connection_attempt.isoformat() if self._last_connection_attempt else None,
        }
        
        if self.last_message_timestamp:
            elapsed = asyncio.get_event_loop().time() - self.last_message_timestamp
            summary["time_since_last_message_s"] = round(elapsed, 1)
            
        if self.last_pong_timestamp:
            elapsed = asyncio.get_event_loop().time() - self.last_pong_timestamp
            summary["time_since_last_pong_s"] = round(elapsed, 1)
            
        return summary