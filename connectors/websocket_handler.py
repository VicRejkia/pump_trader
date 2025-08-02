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

# Assuming these are in your project structure
from config.config import _PUMPPORTAL_WS, _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED, _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES
from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState

# SIZE OF BATCHES TO UNSUBSCRIBE DURING SHUTDOWN
UNSUBSCRIBE_BATCH_COUNT = 15


class WebSocketHandler:
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state_manager: GlobalState):
        self.state = state_manager
        self.db_client = db_client
        self.config = config_dict
        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.tasks: list[asyncio.Task] = []
        self.trade_queue = Queue()
        self._reconnect_lock = asyncio.Lock()
        self._is_shutting_down = False
        self.last_message_timestamp: Optional[float] = None

    async def _cleanup_connection(self):
        """Cleanly closes the websocket connection and cancels its tasks."""
        # Cancel any running internal tasks
        if self.tasks:
            for task in self.tasks:
                task.cancel()
            # Wait for tasks to finish cancellation
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()

        # Close the websocket connection if it exists and is open
        if self.websocket and self.websocket.open:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"RECONNECT: Error closing old websocket: {e}")
        self.websocket = None

    async def connect_and_run(self):
        """
        Main entry point. Connects to the WebSocket and starts managing tasks.
        This method will run until the bot is shut down.
        """
        logger.info("WebSocket services starting...")
        while not self.state.shutdown_event.is_set():
            try:
                # --- Connection Phase ---
                logger.info("WS: Attempting to connect...")
                # Connect with keepalive pings enabled
                self.websocket = await websockets.connect(_PUMPPORTAL_WS, ping_interval=20, ping_timeout=15)
                logger.info("✅ WS: Connection established.")

                # --- Subscription Phase ---
                await self.subscribe_new_token_stream()
                await self.subscribe_to_migrations()
                await self.resume_subscriptions()

                # --- Task Running Phase ---
                # Create and manage the tasks that use the connection
                self.tasks = [
                    asyncio.create_task(self.message_handler(), name="ws_message_handler"),
                    asyncio.create_task(self.monitor_connection(), name="ws_connection_monitor"),
                    asyncio.create_task(self.unsubscribe_checker(), name="ws_unsubscribe_checker"),
                ]
                if _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED:
                    self.tasks.append(asyncio.create_task(self.subscription_refresher(), name="ws_subscription_refresher"))
                
                
                # Wait for any of the tasks to finish. If one finishes,
                # it's likely due to an error or a disconnection.
                done, pending = await asyncio.wait(self.tasks, return_when=asyncio.FIRST_COMPLETED)

                # Log why the task(s) finished
                for task in done:
                    try:
                        result = task.result()
                        logger.warning(f"WS: Task {task.get_name()} finished unexpectedly with result: {result}.")
                    except asyncio.CancelledError:
                        logger.info(f"WS: Task {task.get_name()} was cancelled.")
                    except Exception as e:
                        logger.error(f"WS: Task {task.get_name()} failed with exception: {e}", exc_info=True)

            except websockets.exceptions.ConnectionClosed as e:
                logger.error(f"WS: Connection closed during connect/run phase: {e}")
            except Exception as e:
                logger.error(f"WS: An unexpected error occurred in connect_and_run: {e}", exc_info=True)

            # --- Cleanup and Backoff Phase ---
            if self.state.shutdown_event.is_set():
                logger.info("WS: Shutdown signal received, exiting connect_and_run loop.")
                break

            logger.warning("WS: Connection or tasks failed. Cleaning up and preparing to reconnect...")
            await self._cleanup_connection()
            backoff_seconds = 5
            logger.info(f"WS: Waiting {backoff_seconds} seconds before attempting to reconnect.")
            await asyncio.sleep(backoff_seconds)
        
        # Final cleanup on shutdown
        await self._cleanup_connection()
        logger.info("WebSocket services have been shut down.")


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

                        # Check if the token is one we are actively tracking
                        is_tracked = await self.db_client.is_token_active_in_db(mint_to_flag)

                        if is_tracked:
                            logger.info(f"✅ Migration event for tracked token {mint_to_flag}. Processing...")
                            # Set the data_source to 'DEXSCREENER' to switch to API polling
                            await self.db_client.mark_token_as_migrated(mint_to_flag)
                            # Store the migration event for historical reference
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
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"Message handler: Connection closed (Reason: {e}). Exiting handler task.")
        except asyncio.CancelledError:
            logger.info("✉️ Message handler task cancelled.")
        finally:
            logger.info("✉️ Message handler task stopped.")

    async def monitor_connection(self):
        """Monitors connection health. Exits if connection appears stale or is closed."""
        logger.info("📡 WebSocket connection monitor started.")
        max_silence_seconds = self.config.get('WEBSOCKET_MAX_SILENCE_SECONDS', 180)
        
        while not self.state.shutdown_event.is_set():
            try:
                await asyncio.sleep(30) # Check interval

                if not self.websocket.open:
                    logger.warning("Monitor: Detected websocket is not open. Exiting monitor task.")
                    break

                if self.last_message_timestamp:
                    time_since_last_msg = asyncio.get_event_loop().time() - self.last_message_timestamp
                    if time_since_last_msg > max_silence_seconds:
                        logger.error(f"Monitor: No messages for {time_since_last_msg:.0f}s. Connection is stale. Exiting monitor task.")
                        break # Exit the loop, causing the main connect_and_run loop to restart everything
                else:
                    # This case can happen if the connection is open but no message (even a confirmation) has arrived.
                    # It might be useful to have a timeout for this initial state.
                    if asyncio.get_event_loop().time() - self.websocket.open_timestamp > 60: # Example: 60s timeout after opening
                         logger.error("Monitor: Connection open for over 60s with no initial messages. Forcing reconnect.")
                         break
            except asyncio.CancelledError:
                logger.info("📡 Monitor task cancelled.")
                break
        logger.info("📡 WebSocket connection monitor stopped.")

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
                # <<< CHANGE: Update the state manager on successful subscription >>>
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
                # --- MODIFICATION: Set next run timestamp before sleeping ---
                next_run_ts = datetime.now(timezone.utc) + timedelta(seconds=refresh_interval_seconds)
                await self.state.set_ws_refresh_next_run_ts(next_run_ts)
                # --- END MODIFICATION ---

                # Wait for the specified interval, but allow for early exit on shutdown.
                await self.state.wait_or_interrupt(timeout=refresh_interval_seconds)
                if self.state.shutdown_event.is_set():
                    break
                
                # --- START: THE FIX ---
                # Before starting the refresh logic, check if the connection is still valid.
                # This prevents the race condition if the connection dropped during the await.
                if not (self.websocket and self.websocket.open):
                    logger.warning("Subscription refresher: WebSocket not open. Skipping refresh cycle.")
                    continue
                # --- END: THE FIX ---
                
                # --- MODIFICATION: Clear timestamp to indicate "In Progress" ---
                await self.state.set_ws_refresh_next_run_ts(None)
                # --- END MODIFICATION ---

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
            except Exception as e:
                logger.error(f"Error in subscription_refresher loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=60)
                
        # On shutdown, clear the timestamp
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
        #logger.debug(f"Processing unsubscription for all tokens from suspicious creator: {creator}")
        try:
            # Get all tokens by this creator that are NOT in an active portfolio
            tokens_to_process = await self.db_client.fetch_tokens_by_creator(creator, respect_portfolio=True)
            
            if not tokens_to_process:
                logger.debug(f"No non-portfolio tokens found for suspicious creator {creator} to unsubscribe.")
                return

            mints_to_unsubscribe = [row['mint'] for row in tokens_to_process]
            
            logger.warning(f"Found {len(mints_to_unsubscribe)} tokens from suspicious creator '{creator}' to unsubscribe and backup.")
            
            # Use the existing batch unsubscribe method for consistency
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
            except Exception as e:
                logger.error(f"Failed to send batch unsubscribe message: {e}")

        # A set of reasons that should NOT trigger a database backup/delete.
        reasons_to_skip_db_backup = {"shutdown", "periodic_refresh"}

        # Update state and DB regardless of whether send succeeded, as we no longer want to track them.
        for mint in mints:
            await self.state.remove_token_subscription(mint) # This also saves state to file
            if reason not in reasons_to_skip_db_backup:
                await self.db_client.backup_and_delete_token(mint, datetime.now(timezone.utc), reason)

    async def unsubscribe_new_tokens(self):
        """Sends a request to unsubscribe from the newToken stream."""
        current_state = await self.state.get_new_token_subscription()
        if not current_state:
            logger.info("Already unsubscribed from newToken stream. No action needed.")
            return

        if self.websocket and self.websocket.open:
            try:
                payload = json.dumps({"method": "unsubscribeNewToken"})
                await asyncio.wait_for(self.websocket.send(payload), timeout=10.0)
                # Assuming successful send means unsubscription on the server side
                await self.state.set_new_token_subscription(False)
                logger.info("✅ Successfully sent unsubscribe request for newToken stream.")
                # Reset the flag in config.py directly (if still needed elsewhere, though state manager is better)
                # Be cautious modifying config directly, state manager is preferred.
                # config.NEW_TOKEN_SUBSCRIPTION = False

            except websockets.exceptions.ConnectionClosed:
                logger.error("❌ Cannot unsubscribe from newToken: WebSocket connection is closed.")
                # Optionally update state anyway, as we can't be subscribed if disconnected
                await self.state.set_new_token_subscription(False)
                # config.NEW_TOKEN_SUBSCRIPTION = False
            except asyncio.TimeoutError:
                logger.error("⏳ Timeout sending unsubscribe request for newToken stream.")
                # State remains true, maybe retry later? Or set false optimistically?
                # For now, let's keep state as true, indicating we *think* we are still subscribed.
            except Exception as e:
                logger.error(f"❌ Error sending unsubscribe request for newToken: {e}", exc_info=True)
                # State remains true
        else:
            logger.warning("⚠️ Cannot unsubscribe from newToken: WebSocket is not connected or not initialized.")
            # If not connected, we are effectively unsubscribed, so update state
            await self.state.set_new_token_subscription(False)
            # config.NEW_TOKEN_SUBSCRIPTION = False

    async def shutdown(self):
        """Gracefully shuts down the WebSocket connection and all related tasks."""
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        logger.info("Initiating WebSocketHandler shutdown sequence...")

        # Signal all internal tasks to stop by closing the main loop
        # The main connect_and_run loop will handle cleaning up tasks and the connection.
        # This shutdown method becomes simpler.
        
        # Unsubscribe from everything as a final cleanup step
        if self.websocket and self.websocket.open:
            active_subs = list(await self.state.get_token_subscriptions())
            if active_subs:
                logger.info(f"Sending final unsubscribe for {len(active_subs)} tokens.")
                await self.unsubscribe_token_trades_batch(active_subs, "shutdown")
            
            if await self.state.get_new_token_subscription():
                try:
                    await self.websocket.send(json.dumps({"method": "unsubscribeNewToken"}))
                    await self.state.set_new_token_subscription(False)
                except Exception as e:
                    logger.warning(f"Failed to send final unsubscribeNewToken message: {e}")
        
        await self._cleanup_connection()
        logger.info("WebSocketHandler shutdown sequence complete.")

    def get_internal_task_statuses(self) -> list[tuple[str, str]]:
        """Returns the status of internal WebSocket handler tasks."""
        statuses = []
        if not self.tasks:
            return [("internal_tasks", "not started")]
            
        for task in self.tasks:
            name = task.get_name().replace("ws_", "") # Shorten name for display
            status_str = "unknown"
            if task.cancelled():
                status_str = "cancelled"
            elif task.done():
                exc = task.exception()
                status_str = f"error ({type(exc).__name__})" if exc else "done"
            else:
                status_str = "running"
            statuses.append((name, status_str))
        return statuses

    async def get_connection_summary(self) -> dict:
        """Gathers a summary of the WebSocket connection status for monitoring."""
        status_summary = {
            "connection_status": "Not Initialized",
            "new_token_subscribed": False,
            "migration_subscribed": False,
            "trade_subscriptions_count": 0,
            "time_since_last_message_s": -1.0
        }

        if self.state.shutdown_event.is_set():
            status_summary["connection_status"] = "Shutting Down"
        elif self.websocket and self.websocket.open:
            status_summary["connection_status"] = "Connected"
        elif self._reconnect_lock.locked():
            status_summary["connection_status"] = "Reconnecting..."
        else:
            status_summary["connection_status"] = "Disconnected"

        status_summary["new_token_subscribed"] = await self.state.get_new_token_subscription()
        status_summary["migration_subscribed"] = await self.state.get_migration_subscription()
        active_subs = await self.state.get_token_subscriptions()
        status_summary["trade_subscriptions_count"] = len(active_subs)
        
        if self.last_message_timestamp:
            status_summary["time_since_last_message_s"] = asyncio.get_event_loop().time() - self.last_message_timestamp

        return status_summary