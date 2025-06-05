"""
Manages WebSocket communication with the external PumpPortal API.
Handles incoming messages, token subscriptions, and graceful shutdown.
"""

import asyncio
from asyncio import Queue
import json
from datetime import datetime, timezone, timedelta
import asyncpg # Retained, though not directly used in this snippet. Assume DB interactions are correct.
import websockets
from typing import Optional
from config import _PUMPPORTAL_WS
from database_handler import DatabaseClient # For type hinting mainly
from bot_logger import logger
from state_manager import GlobalState

# SIZE OF BATCHES TO UNSUBSCRIBE DURING SHUTDOWN
UNSUBSCRIBE_BATCH_COUNT = 15


class WebSocketHandler:
    def __init__(self, db_client: DatabaseClient, config_dict: dict, state_manager: GlobalState):
        self.state = state_manager
        self.db_client = db_client
        self.config = config_dict
        self.websocket: websockets.WebSocketClientProtocol | None = None # Explicitly None initially
        self.tasks: list[asyncio.Task] = [] # For managing message_handler, monitor, unsubscribe_checker
        self.last_update_times = {}
        self.trade_queue = Queue()
        self._reconnect_lock = asyncio.Lock() # Ensures only one reconnect process runs at a time
        self._is_shutting_down = False # Flag to prevent reconnection during shutdown
        self.last_message_timestamp: Optional[float] = None 

    async def _ensure_internal_tasks_stopped(self):
        if self.tasks:
            logger.info("ENSURE_TASKS_STOPPED: Stopping internal WebSocket tasks...") #
            for task in self.tasks:
                if task and not task.done():
                    logger.debug(f"ENSURE_TASKS_STOPPED: Cancelling task: {task.get_name()}") #
                    task.cancel()
            
            awaitable_tasks = [t for t in self.tasks if t and not t.done()]
            if awaitable_tasks:
                logger.debug(f"ENSURE_TASKS_STOPPED: Gathering {len(awaitable_tasks)} tasks for completion...") #
                try:
                    results = await asyncio.wait_for(asyncio.gather(*awaitable_tasks, return_exceptions=True), timeout=15.0) # Increased timeout slightly
                    logger.info("ENSURE_TASKS_STOPPED: Gather results:") #
                    for i, result in enumerate(results):
                        task_name = awaitable_tasks[i].get_name() if hasattr(awaitable_tasks[i], 'get_name') else f"Task-{i}"
                        if isinstance(result, asyncio.CancelledError):
                            logger.info(f"  - Task {task_name}: Confirmed CancelledError in gather result.") #
                        elif isinstance(result, Exception):
                            logger.error(f"  - Task {task_name}: Returned exception in gather: {type(result).__name__}: {result}", exc_info=result) #
                        else:
                            logger.info(f"  - Task {task_name}: Completed without exception in gather. Result: {type(result)}") #
                except asyncio.TimeoutError:
                    logger.warning("ENSURE_TASKS_STOPPED: Timeout waiting for internal tasks to complete gather. Some tasks might not have terminated cleanly.") #
                except Exception as e: # Other unexpected errors during gather itself
                    logger.error(f"ENSURE_TASKS_STOPPED: Unexpected error during asyncio.gather: {e}", exc_info=True) #
            else:
                logger.info("ENSURE_TASKS_STOPPED: No awaitable (not done) tasks to gather.") #

            logger.info("ENSURE_TASKS_STOPPED: Clearing internal task list.") #
            self.tasks.clear()
        else:
            logger.info("ENSURE_TASKS_STOPPED: No internal tasks were active to stop.") #

    async def _start_internal_tasks(self):
        await self._ensure_internal_tasks_stopped() # This now logs its own start/finish

        if not (self.websocket and self.websocket.open):
            logger.error("START_INTERNAL_TASKS: Cannot start - WebSocket not connected or not open.")
            return

        logger.info("START_INTERNAL_TASKS: Attempting to start internal WebSocket tasks...")
        self.tasks = [ # Re-assign to self.tasks
            asyncio.create_task(self.message_handler(), name="ws_message_handler"),
            asyncio.create_task(self.monitor_connection(), name="ws_connection_monitor"),
            asyncio.create_task(self.unsubscribe_checker(), name="ws_unsubscribe_checker")
        ]
        if self.tasks:
            task_names = [t.get_name() for t in self.tasks if hasattr(t, 'get_name')]
            logger.info(f"START_INTERNAL_TASKS: Successfully created {len(self.tasks)} tasks: {task_names}.")
        else:
            logger.warning("START_INTERNAL_TASKS: Task list is empty after attempting to start.")


    async def connect(self):
        """
        Establishes a WebSocket connection and subscribes to new token events.
        This method should ensure self.websocket is valid and open on success, or None on failure.
        """
        if self._is_shutting_down:
            logger.info("Connect called during shutdown, aborting.")
            return

        if self.websocket and self.websocket.open:
            logger.warning("Connect called but WebSocket appears to be already open. Closing existing one first.")
            try:
                await self.websocket.close()
            except Exception:
                pass # Ignore errors during preemptive close
            self.websocket = None

        logger.info(f"Attempting to connect to WebSocket: {_PUMPPORTAL_WS}")
        try:
            # For a new connection, always try to establish fresh
            # Added ping_interval and ping_timeout for keepalive handled by the library
            self.websocket = await websockets.connect(_PUMPPORTAL_WS, ping_interval=20, ping_timeout=15)
            logger.info("Successfully connected to PumpPortal WebSocket.")

            # Subscribe to new token events
            await self.websocket.send(json.dumps({"method": "subscribeNewToken"}))
            await self.state.set_new_token_subscription(True) # Mark that we've attempted/sent subscription
            logger.debug("Sent subscribeNewToken request.")

        except Exception as e:
            logger.error(f"WebSocket connection or initial subscription failed: {e}", exc_info=True)
            if self.websocket: # If connect created an object but failed later
                try:
                    await self.websocket.close()
                except Exception:
                    pass
            self.websocket = None # Ensure it's None on any connection failure
            raise # Re-raise the exception so the calling context (e.g., reconnect loop) handles it

    async def reconnect(self):
        if self._is_shutting_down:
            logger.info("RECONNECT_LOG: Aborted - Shutdown in progress.")
            return
        if self._reconnect_lock.locked():
            logger.info("RECONNECT_LOG: Aborted - Reconnection already in progress by another task.")
            return

        logger.info("RECONNECT_LOG: Initiating sequence, attempting to acquire _reconnect_lock...")
        async with self._reconnect_lock:
            logger.info("RECONNECT_LOG: _reconnect_lock acquired.")
            if self._is_shutting_down:
                logger.info("RECONNECT_LOG: Aborted - Shutdown occurred while waiting for lock.")
                return

            logger.warning("🔄 WebSocket Reconnection Sequence Started...")
            
            logger.info("RECONNECT_LOG: Stopping internal tasks...")
            await self._ensure_internal_tasks_stopped()
            logger.info("RECONNECT_LOG: Internal tasks stopped.")

            if self.websocket:
                ws_state_before_close = self.websocket.state_name if hasattr(self.websocket, 'state_name') else 'N/A'
                logger.info(f"RECONNECT_LOG: Closing existing WebSocket object (State: {ws_state_before_close}, Open: {self.websocket.open})...")
                try:
                    await self.websocket.close()
                    logger.info("RECONNECT_LOG: Existing WebSocket object closed.")
                except Exception as e:
                    logger.error(f"RECONNECT_LOG: Error closing existing WebSocket: {e}", exc_info=True)
                self.websocket = None

            attempt = 1
            max_attempts = 10

            while attempt <= max_attempts and not self.state.shutdown_event.is_set():
                logger.info(f"RECONNECT_LOG: Attempt {attempt}/{max_attempts} starting...")
                try:
                    # Exponential backoff, ensure it's interruptible by shutdown
                    backoff_time = min(attempt * attempt, 30) # Capped at 30s
                    logger.info(f"RECONNECT_LOG: Waiting {backoff_time}s before connect attempt {attempt}.")
                    await self.state.wait_or_interrupt(timeout=backoff_time)
                    if self.state.shutdown_event.is_set():
                         logger.info("RECONNECT_LOG: Shutdown triggered during backoff. Aborting.")
                         break

                    logger.info(f"RECONNECT_LOG: Attempt {attempt} - Calling self.connect().")
                    await self.connect() # This sets self.websocket

                    if self.websocket and self.websocket.open:
                        logger.info(f"RECONNECT_LOG: Attempt {attempt} - Connect successful. WS Open: True.")
                        logger.info(f"RECONNECT_LOG: Attempt {attempt} - Calling self.resume_subscriptions().")
                        await self.resume_subscriptions()
                        logger.info(f"RECONNECT_LOG: Attempt {attempt} - Resumed subscriptions. Calling self._start_internal_tasks().")
                        await self._start_internal_tasks()
                        logger.info(f"RECONNECT_LOG: Attempt {attempt} - Internal tasks started.")
                        logger.info(f"✅ WebSocket reconnected and tasks restarted successfully after {attempt} attempts.")
                        return
                    else:
                        logger.warning(f"RECONNECT_LOG: Attempt {attempt} - Connect method finished but WebSocket is not open.")
                        # Ensure websocket is None if connect didn't open it properly
                        if self.websocket: await self.websocket.close(); self.websocket = None

                except Exception as e_connect_attempt:
                    logger.warning(f"RECONNECT_LOG: ⚠️ WebSocket reconnection attempt {attempt} failed: {e_connect_attempt}", exc_info=True)
                    if self.websocket: # Defensive close if connect created an object but failed
                        try: await self.websocket.close()
                        except: pass
                        self.websocket = None
                finally:
                    attempt += 1
            
            # Loop finished
            if not self.state.shutdown_event.is_set():
                logger.critical("RECONNECT_LOG: ❌ Failed to reconnect WebSocket after multiple attempts. Triggering bot shutdown.")
                self.state.trigger_shutdown()
            else:
                logger.info("RECONNECT_LOG: Reconnection attempts ended due to shutdown signal.")
        
        logger.info("RECONNECT_LOG: Sequence finished, _reconnect_lock released.")


    async def monitor_connection(self):
        logger.info("📡 WebSocket connection monitor started.") #
        monitor_loop_interval_seconds = 30
        max_silence_seconds = self.config.get('WEBSOCKET_MAX_SILENCE_SECONDS', 180) # Make configurable

        # Initial grace period, also interruptible
        try:
            await self.state.wait_or_interrupt(timeout=10) #
        except asyncio.CancelledError:
            logger.info("📡 WebSocket connection monitor cancelled during initial grace period.") #
            return # Exit if cancelled early
        finally:
            if not self.state.shutdown_event.is_set() and not self._is_shutting_down : #
                logger.debug("📡 WebSocket connection monitor initial grace period ended or was interrupted.") #

        try: # Outer try to catch CancelledError for the whole task
            while not self.state.shutdown_event.is_set() and not self._is_shutting_down:
                # Check for cancellation at the beginning of each loop iteration
                if asyncio.current_task().cancelled():
                    logger.info("📡 Monitor task: Detected cancellation at loop start.") #
                    break 

                # Inner try-except for operations within one loop iteration
                try:
                    await self.state.wait_or_interrupt(timeout=monitor_loop_interval_seconds) #
                    # Re-check conditions after sleep/wait, as state might have changed
                    if self._is_shutting_down or self.state.shutdown_event.is_set() or asyncio.current_task().cancelled():
                        logger.info("📡 Monitor task: Shutdown, or cancellation detected after wait. Exiting loop.") #
                        break
                    
                    issue_detected = False
                    reason_for_reconnect = ""

                    if not (self.websocket and self.websocket.open):
                        issue_detected = True
                        reason_for_reconnect = "websocket_not_open_or_none"
                        logger.warning(f"Monitor: WebSocket reported as not open or is None.") #
                    else: 
                        if self.last_message_timestamp:
                            time_since_last_msg = asyncio.get_event_loop().time() - self.last_message_timestamp
                            if time_since_last_msg > max_silence_seconds:
                                logger.warning(f"Monitor: No messages received for {time_since_last_msg:.0f}s (threshold {max_silence_seconds}s). Stale connection suspected.") #
                                issue_detected = True
                                reason_for_reconnect = "prolonged_message_silence"
                        elif self.websocket and self.websocket.open: 
                            logger.debug("Monitor: Connection open, but no messages received yet (last_message_timestamp is None).") #

                    if issue_detected:
                        logger.warning(f"⚠️ WebSocket monitor detected issue ({reason_for_reconnect}).") #
                        if not self._is_shutting_down:
                            if not self._reconnect_lock.locked():
                                logger.info("Monitor: Triggering reconnect due to detected issue.") #
                                await self.reconnect() 
                            else:
                                logger.info("Monitor: Reconnect already in progress, skipping redundant trigger by monitor.") #
                    else:
                        logger.debug("Monitor: Connection appears healthy (passed monitor's checks). Library pings are primary.") #

                except asyncio.CancelledError: 
                    logger.info("📡 Monitor task: Cancellation caught during an operation or sleep. Exiting loop.") #
                    break # Exit the while loop
                except Exception as e_loop:
                    logger.error(f"Error in monitor_connection inner loop: {e_loop}", exc_info=True) #
                    # Prevent rapid looping on unexpected error; use interruptible sleep
                    try:
                        await self.state.wait_or_interrupt(timeout=5) #
                    except asyncio.CancelledError:
                        logger.info("📡 Monitor task: Cancelled during error recovery sleep.") #
                        break # Exit loop

        except asyncio.CancelledError: 
            logger.info("📡 WebSocket connection monitor task was explicitly cancelled (outer).") #
        except Exception as e_outer_monitor: # Should not be reached if inner errors are handled
            logger.critical(f"CRITICAL unhandled error in monitor_connection outer scope: {e_outer_monitor}", exc_info=True) #
        finally:
            logger.info("📡 WebSocket connection monitor task stopped.") #

    async def message_handler(self):
        """Processes incoming WebSocket messages."""
        logger.info("✉️ WebSocket message handler started.")
        try:
            while not self.state.shutdown_event.is_set() and not self._is_shutting_down:
                if not (self.websocket and self.websocket.open):
                    logger.warning("Message handler: WebSocket not open. Attempting reconnect.")
                    if not self._is_shutting_down: await self.reconnect()
                    if not (self.websocket and self.websocket.open):
                        logger.error("Message handler: Reconnect failed. Stopping message handler.")
                        break
                    else:
                        continue # Re-check loop condition with new connection

                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=60.0) # Timeout for recv
                    self.last_message_timestamp = asyncio.get_event_loop().time() # <<< --- UPDATE TIMESTAMP HERE
                except asyncio.TimeoutError:
                    logger.warning("WebSocket recv timed out. Connection might be stale.")
                    # If recv times out, the connection might be dead.
                    # Trigger a reconnect if not already shutting down.
                    if self.websocket and self.websocket.open:
                        try:
                            await asyncio.wait_for(self.websocket.ping(), timeout=10.0) # Shorter timeout for explicit ping
                        except Exception as ping_exc: # Catches TimeoutError from ping, ConnectionClosed, etc.
                            logger.warning(f"Explicit ping failed after recv timeout: {ping_exc}. Triggering reconnect.")
                            if not self._is_shutting_down: await self.reconnect()
                    else: # WebSocket closed during or before our explicit ping
                         if not self._is_shutting_down: await self.reconnect()
                    continue # Back to the start of the while loop to re-evaluate connection
                except websockets.exceptions.ConnectionClosed as e_closed:
                    logger.error(f"Message handler: WebSocket connection closed (Type: {type(e_closed).__name__}, Details: {e_closed}). Attempting reconnect.")
                    if not self._is_shutting_down: await self.reconnect()
                    if not (self.websocket and self.websocket.open): # If reconnect failed
                        logger.error("Message handler: Reconnect failed after ConnectionClosed. Stopping message handler.")
                        break
                    else:
                        continue 

                try:
                    data = json.loads(message)
                    if 'message' in data:
                        logger.debug(f"📡 WebSocket confirmation: {data['message']}")
                        continue

                    if data.get('txType') == "create":
                        mint = data.get('mint', 'N/A')
                        logger.debug(f"➕ Received 'new token': {mint}")
                        token_stored = await self.db_client.insert_token(data) # type: ignore
                        if not token_stored:
                            creator = data.get('traderPublicKey')
                            if await self.db_client.is_suspicious_creator(creator): # type: ignore
                                await self.unsubscribe_tokens_from_creator(creator)
                            continue
                        if self.websocket and self.websocket.open: # Check before sending
                            await self.websocket.send(json.dumps({
                                "method": "subscribeTokenTrade",
                                "keys": [data['mint']]
                            }))
                        await self.state.add_token_subscription(data['mint'])
                        active_subs_count = len(await self.state.get_token_subscriptions())
                        logger.debug(f"✅ Subscribed to {data['mint']} --> {active_subs_count} active subscriptions")

                    elif data.get("txType") == "migrate":
                        await self.db_client.insert_migration(data) # type: ignore
                    elif data.get("txType") in ["buy", "sell"]:
                        self.last_update_times[data['mint']] = datetime.now(timezone.utc)
                        await self.trade_queue.put(data)
                    else:
                        logger.warning(f"❔ WEBSOCKET - Unknown message type: {data}")

                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to decode JSON message: {str(message)[:200]}... Error: {json_err}")
                except Exception as e_proc:
                    logger.error(f"Error processing WebSocket message: {e_proc}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("✉️ WebSocket message handler task cancelled.")
        except Exception as e:
            logger.critical(f"CRITICAL error in message_handler outer loop: {e}", exc_info=True)
            if not self._is_shutting_down and not self.state.shutdown_event.is_set():
                await self.reconnect()
        finally:
            logger.info("✉️ WebSocket message handler stopped.")

    async def resume_subscriptions(self):
        """Resubscribes to all active tokens from the database."""
        if not (self.websocket and self.websocket.open):
            logger.warning("WebSocket not connected or not open, skipping resubscriptions.")
            return

        try:
            startup_time = datetime.now(timezone.utc)
            last_bot_activity_time = await self.db_client.get_last_heartbeat_before(startup_time) # type: ignore

            RESTART_GAP_THRESHOLD_SECONDS = self.config.get('RESTART_GAP_THRESHOLD_SECONDS', 600) # type: ignore

            active_tokens_from_db = await self.db_client.get_active_tokens() # type: ignore
            mints_to_subscribe = []

            for row in active_tokens_from_db:
                mint = row['mint']
                last_trade_timestamp = await self.db_client.get_last_trade_timestamp(mint) # type: ignore
                has_active_buy_order = await self.db_client.has_active_buy_order(mint) # type: ignore

                is_gap_filled_candidate = False
                if last_trade_timestamp is not None and last_bot_activity_time is not None:
                    gap_duration = startup_time - last_bot_activity_time
                    if last_trade_timestamp < last_bot_activity_time and gap_duration.total_seconds() > RESTART_GAP_THRESHOLD_SECONDS:
                        is_gap_filled_candidate = True

                if is_gap_filled_candidate and not has_active_buy_order:
                    logger.info(f"Detected potential gap-filled token {mint}. Last trade: {last_trade_timestamp}, Last bot activity: {last_bot_activity_time}. Backing up with 'interrupted_gap_fill' reason.")
                    try:
                        await self.db_client.backup_and_delete_token(mint=mint, archived_at=startup_time, reason="interrupted_gap_fill") # type: ignore
                    except Exception as e_bd:
                        logger.error(f"Error backing up gap-filled token {mint}: {e_bd}", exc_info=True)
                else:
                    mints_to_subscribe.append(mint)

            if mints_to_subscribe:
                logger.info(f"Attempting to resubscribe to {len(mints_to_subscribe)} active tokens.")
                if self.websocket and self.websocket.open :
                    await self.websocket.send(json.dumps({
                        "method": "subscribeTokenTrade",
                        "keys": mints_to_subscribe
                    }))
                    async with self.state.lock: # type: ignore
                        for mint_to_add in mints_to_subscribe:
                            self.state.active_token_subscriptions.add(mint_to_add) # type: ignore
                        self.state._save_subscriptions_to_file() # type: ignore
                    logger.debug(f"🔄 Resubscribed to {len(mints_to_subscribe)} tokens.")
                else:
                    logger.warning("Cannot resubscribe, WebSocket connection is not open.")
            else:
                logger.info("No active tokens found in DB to resubscribe to, or all were gap-filled.")
        except Exception as e_resume:
            logger.error(f"❌ Failed to resume subscriptions: {e_resume}", exc_info=True)

    async def unsubscribe_checker(self):
        """
        Periodically checks for inactive or risky tokens to unsubscribe from,
        with robust handling for task cancellation.
        """
        logger.info("🗑️ WebSocket unsubscribe_checker started.") #
        # Get interval from config, use a default if not found
        unsubscribe_interval = self.config.get('UNSUBSCRIBE_CHECKER_INTERVAL', 30) # Default to 30 seconds
                                                                                   # (Assuming UNSUBSCRIBE_CHECKER_INTERVAL is in config)

        try: # Outer try to catch CancelledError for the whole task
            while not self.state.shutdown_event.is_set() and not self._is_shutting_down:
                # Check for cancellation at the beginning of each loop iteration
                if asyncio.current_task().cancelled():
                    logger.info("🗑️ Unsubscribe checker: Detected cancellation at loop start.") #
                    break 

                # Inner try-except for operations within one loop iteration
                try:
                    await self.state.wait_or_interrupt(timeout=unsubscribe_interval) #
                    # Re-check conditions after sleep/wait, as state might have changed
                    if self._is_shutting_down or self.state.shutdown_event.is_set() or asyncio.current_task().cancelled():
                        logger.info("🗑️ Unsubscribe checker: Shutdown or cancellation after wait. Exiting loop.") #
                        break
                    
                    if not (self.websocket and self.websocket.open):
                        logger.warning("Unsubscribe checker: WebSocket not open. Skipping check cycle.") #
                        continue

                    sol_price = await self.state.get_sol_price() #
                    if sol_price is None or sol_price <=0: #
                        logger.warning(f"Unsubscribe checker: Invalid SOL price ({sol_price}). Skipping check cycle.") #
                        # Use wait_or_interrupt for the shorter sleep as well
                        try:
                            await self.state.wait_or_interrupt(timeout=5) #
                        except asyncio.CancelledError:
                            logger.info("🗑️ Unsubscribe checker: Cancelled during SOL price error recovery sleep.") #
                            break # Exit outer loop if cancelled here
                        continue
                    
                    # Actual unsubscribing logic
                    try:
                        rows = await self.db_client.get_tokens_to_unsubscribe(self.config['MC_DROP_THRESHOLD'], self.config['INACTIVITY_PERIOD'], self.config['MIN_TOKEN_AGE']) #

                        candidate_mints = [row['mint'] for row in rows] #
                        mints_to_process_batch = []

                        if candidate_mints:
                            async with self.state.lock: #
                                for mint_check in candidate_mints:
                                    if mint_check in self.state.active_token_subscriptions: #
                                        self.state.active_token_subscriptions.discard(mint_check) #
                                        mints_to_process_batch.append(mint_check) #
                        
                        if mints_to_process_batch:
                            if self.websocket and self.websocket.open:
                                logger.debug(f"👋 Unsubscribing batch of {len(mints_to_process_batch)} tokens...") #
                                await self.websocket.send(json.dumps({
                                    "method": "unsubscribeTokenTrade",
                                    "keys": mints_to_process_batch
                                })) #
                                async with self.state.lock: #
                                    self.state._save_subscriptions_to_file() #
                            else:
                                logger.warning(f"WebSocket closed, cannot send batch unsubscribe for {len(mints_to_process_batch)} tokens during checker.") #
                            
                            deleted_count = 0
                            for mint_del in mints_to_process_batch:
                                try:
                                    await self.db_client.backup_and_delete_token(mint=mint_del, archived_at=datetime.now(timezone.utc), reason="rugged_dead") #
                                    deleted_count += 1
                                except Exception as e_bd:
                                    logger.error(f"DB backup/delete failed for {mint_del} in checker: {e_bd}", exc_info=True) #
                            logger.debug(f"🧹 Processed unsubscribe batch by checker: {deleted_count}/{len(mints_to_process_batch)} tokens backed up.") #
                    except Exception as e_unsub_check_logic: # Catch errors from the unsubscribing logic
                        logger.error(f"Unsubscribe checker cycle's main logic failed: {e_unsub_check_logic}", exc_info=True) #
                        # Fall through to the main loop's wait_or_interrupt for the next cycle

                except asyncio.CancelledError: 
                    logger.info("🗑️ Unsubscribe checker: Cancellation caught during an operation or sleep. Exiting loop.") #
                    break # Exit the while loop
                except Exception as e_loop_unsub: # Catch other unexpected errors in the inner try
                    logger.error(f"Error in unsubscribe_checker inner loop: {e_loop_unsub}", exc_info=True) #
                    try:
                        await self.state.wait_or_interrupt(timeout=5) # Avoid rapid looping
                    except asyncio.CancelledError:
                        logger.info("🗑️ Unsubscribe checker: Cancelled during error recovery sleep.") #
                        break # Exit loop

        except asyncio.CancelledError: 
            logger.info("🗑️ WebSocket unsubscribe_checker task was explicitly cancelled (outer).") #
        except Exception as e_outer_unsub: # Should ideally not be reached if inner errors are handled
            logger.critical(f"CRITICAL unhandled error in unsubscribe_checker outer scope: {e_outer_unsub}", exc_info=True) #
        finally:
            logger.info("🗑️ WebSocket unsubscribe_checker task stopped.") #

    async def start_websocket_services(self):
        """Connects to WebSocket and starts all internal handling tasks."""
        if self._is_shutting_down: return # Don't start if already shutting down

        logger.info("Attempting to start WebSocket services...")
        try:
            await self.connect() # Initial connection attempt
            if self.websocket and self.websocket.open:
                await self.resume_subscriptions() # Resume subscriptions on initial connect
                await self._start_internal_tasks() # Start handlers
                logger.info("WebSocket services started successfully.")
            else: # connect() failed
                logger.error("Failed to connect WebSocket during initial startup. Monitor task will attempt to reconnect.")
                # If connect fails, it raises an exception, so this 'else' might not be hit if connect() is robust.
                # However, if connect() could return without an open websocket (e.g., silent failure), then:
                if not self._is_shutting_down :
                    await self._ensure_internal_tasks_stopped() # Clean slate
                    # Start only the monitor if connection failed, it will drive reconnections
                    self.tasks = [asyncio.create_task(self.monitor_connection(), name="ws_connection_monitor")]
                    logger.info("Started WebSocket connection monitor to handle reconnections after initial connect failure.")

        except Exception as e: # Catch errors from self.connect()
            logger.error(f"Critical error during WebSocket service startup (initial connect phase): {e}", exc_info=True)
            if not self._is_shutting_down: # Start monitor to attempt recovery if not already shutting down
                logger.info("Attempting to start connection monitor for recovery...")
                await self._ensure_internal_tasks_stopped() # Clean slate
                self.tasks = [asyncio.create_task(self.monitor_connection(), name="ws_connection_monitor")]


    async def shutdown(self):
        """Gracefully shuts down the WebSocket connection and all related tasks."""
        if self._is_shutting_down:
            logger.info("Shutdown already in progress for WebSocketHandler.")
            return
        self._is_shutting_down = True
        logger.info("Initiating WebSocketHandler shutdown sequence...")

        await self._ensure_internal_tasks_stopped()

        if await self.state.get_new_token_subscription() and self.websocket and self.websocket.open:
            try:
                logger.info("Attempting to unsubscribe from new token stream...")
                await asyncio.wait_for(
                    self.websocket.send(json.dumps({"method": "unsubscribeNewToken"})),
                    timeout=5.0
                )
                await self.state.set_new_token_subscription(False)
                logger.info("👋 Successfully unsubscribed from new token events during shutdown.")
            except Exception as e:
                logger.warning(f"Failed to unsubscribe from new token events during shutdown: {e}", exc_info=True)
        else:
            logger.info("Not subscribed to new token stream or WebSocket not open; skipping new token unsubscription.")

        active_subs = list(await self.state.get_token_subscriptions())
        if active_subs and self.websocket and self.websocket.open:
            logger.info(f"Attempting to unsubscribe from {len(active_subs)} active token trades during shutdown...")
            batches = [active_subs[i:i + UNSUBSCRIBE_BATCH_COUNT] for i in range(0, len(active_subs), UNSUBSCRIBE_BATCH_COUNT)]
            for i, batch in enumerate(batches):
                try:
                    logger.debug(f"Sending unsubscribe for batch {i+1}/{len(batches)} ({len(batch)} tokens)...")
                    await asyncio.wait_for(
                        self.websocket.send(json.dumps({"method": "unsubscribeTokenTrade", "keys": batch})),
                        timeout=5.0
                    )
                    logger.info(f"👋 Successfully sent unsubscribe for batch {i+1} of token trades.")
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.warning(f"Failed to send unsubscribe for token trade batch {i+1}: {e}", exc_info=True)
        elif active_subs:
             logger.warning("WebSocket not open during shutdown; cannot send token trade unsubscriptions.")

        if active_subs:
            async with self.state.lock: # type: ignore
                self.state.active_token_subscriptions.clear() # type: ignore
                self.state._save_subscriptions_to_file() # type: ignore
            logger.info("Cleared and saved active subscriptions state during shutdown.")

        if self.websocket:
            try:
                logger.info("Closing WebSocket connection...")
                await asyncio.wait_for(self.websocket.close(), timeout=5.0)
                logger.info("WebSocket connection closed successfully.")
            except asyncio.TimeoutError:
                logger.warning("Timeout while closing WebSocket connection.")
            except Exception as e:
                logger.error(f"Error while closing WebSocket connection: {e}", exc_info=True)
            self.websocket = None

        logger.info("WebSocketHandler shutdown sequence complete.")

    async def unsubscribe_tokens_from_creator(self, creator: str):
        try:
            tokens_to_unsubscribe = []
            # Assuming db_client methods are async and correctly defined
            all_tokens_by_creator = await self.db_client.fetch_tokens_by_creator(creator) # type: ignore
            for token_data in all_tokens_by_creator:
                mint = token_data['mint']
                active_buy_order = await self.db_client.has_active_buy_order(mint) # type: ignore
                if not active_buy_order:
                    tokens_to_unsubscribe.append(mint)

            if tokens_to_unsubscribe:
                logger.info(f"Found {len(tokens_to_unsubscribe)} tokens from suspicious creator '{creator}' to process.")
                if self.websocket and self.websocket.open:
                    try:
                        await self.websocket.send(json.dumps({
                            "method": "unsubscribeTokenTrade",
                            "keys": tokens_to_unsubscribe
                        }))
                        logger.debug(f"Sent unsubscribe request for {len(tokens_to_unsubscribe)} tokens from creator {creator}.")
                    except Exception as e_send:
                        logger.error(f"Failed to send unsubscribe for creator {creator}'s tokens: {e_send}")
                else:
                    logger.warning(f"WebSocket not open, cannot send unsubscribe for creator {creator}'s tokens.")

                for mint_unsub in tokens_to_unsubscribe:
                    await self.state.remove_token_subscription(mint_unsub)
                for mint_backup in tokens_to_unsubscribe:
                    await self.db_client.backup_and_delete_token(mint=mint_backup, archived_at=datetime.now(timezone.utc),reason="suspicious_creator") # type: ignore
                logger.info(f"Processed {len(tokens_to_unsubscribe)} tokens for suspicious creator {creator}.")
        except Exception as e_unsub_creator:
            logger.error(f"unsubscribe_tokens_from_creator error for {creator}: {e_unsub_creator}", exc_info=True)

    async def unsubscribe_token_trades(self, mint: str, reason: str | None = None):
        try:
            should_unsubscribe = False
            active_buy_order = await self.db_client.has_active_buy_order(mint) # type: ignore
            if not active_buy_order:
                should_unsubscribe = True

            if should_unsubscribe:
                logger.info(f"Processing unsubscription for token {mint}, reason: {reason or 'manual_unsubscribe'}.")
                if self.websocket and self.websocket.open:
                    try:
                        await self.websocket.send(json.dumps({
                            "method": "unsubscribeTokenTrade",
                            "keys": [mint] # Send as a list
                        }))
                        logger.debug(f"Sent unsubscribe request for token {mint}.")
                    except Exception as e_send:
                        logger.error(f"Failed to send unsubscribe for token {mint}: {e_send}")
                else:
                    logger.warning(f"WebSocket not open, cannot send unsubscribe for token {mint}.")

                await self.state.remove_token_subscription(mint)
                final_reason = reason if reason else "manual_unsubscribe"
                await self.db_client.backup_and_delete_token(mint=mint, archived_at=datetime.now(timezone.utc), reason=final_reason) # type: ignore
                logger.debug(f"Successfully processed unsubscription and backup for token {mint} with reason '{final_reason}'.")
            else:
                logger.info(f"Token {mint} has an active buy order. Skipping unsubscription requested for reason: {reason or 'manual_unsubscribe'}.")
        except Exception as e_unsub_trade:
            logger.error(f"unsubscribe_token_trades error for {mint}: {e_unsub_trade}", exc_info=True)

    def get_internal_task_statuses(self) -> list[tuple[str, str]]:
        """
        Returns a list of (task_name, status_string) for internally managed WebSocket tasks.
        This method is not async as it's reading existing task states.
        """
        statuses = []
        # self.tasks refers to the WebSocketHandler's internal list of tasks
        # (ws_message_handler, ws_connection_monitor, ws_unsubscribe_checker)

        if not hasattr(self, 'tasks') or not self.tasks: # self.tasks is the list populated by _start_internal_tasks
            if self._is_shutting_down:
                return [("WebSocket_Core_Tasks", "Shutting Down")]
            elif self._reconnect_lock.locked(): 
                return [("WebSocket_Core_Tasks", "Reconnecting...")]
            elif self.websocket and self.websocket.open and not self.tasks:
                return [("WebSocket_Core_Tasks", "Pending Start/Restart")]
            else:
                return [("WebSocket_Core_Tasks", "Not Active/Initialized")]

        for task in self.tasks: # Iterate over the WebSocketHandler's own task list
            name = task.get_name() if hasattr(task, 'get_name') else "Unnamed_WS_Task"
            
            current_status_str = ""
            if task.cancelled():
                current_status_str = "cancelled"
            elif task.done():
                if task.exception():
                    # Attempt to get a more specific error type name
                    exc = task.exception()
                    exc_name = type(exc).__name__ if exc else "UnknownException"
                    current_status_str = f"error ({exc_name})"
                else:
                    current_status_str = "done (completed)"
            else: # Not done
                current_status_str = "running"
            statuses.append((name, current_status_str))
        
        if not statuses : # If after iterating tasks, statuses is still empty
             if self.websocket and self.websocket.open:
                 return [("WebSocket_Core_Tasks", "Initializing/Tasks_Pending")]
             elif self._is_shutting_down: # Re-check specific states
                 return [("WebSocket_Core_Tasks", "Shutting_Down_EmptyTasks")]
             elif self._reconnect_lock.locked():
                 return [("WebSocket_Core_Tasks", "Reconnecting_EmptyTasks")]
             else:
                 return [("WebSocket_Core_Tasks", "Stopped/Cleared_EmptyTasks")]

        return statuses
    
    async def get_connection_summary(self) -> dict:
        """
        Gathers a summary of the WebSocket connection and subscription status.
        """
        summary = {
            "connection_status": "N/A",
            "new_token_subscribed": await self.state.get_new_token_subscription(), # From GlobalState
            "trade_subscriptions_count": len(await self.state.get_token_subscriptions()) # From GlobalState
        }

        if self._is_shutting_down: # Internal flag in WebSocketHandler
            summary["connection_status"] = "Shutting Down"
        elif self._reconnect_lock.locked(): # Internal flag in WebSocketHandler
            summary["connection_status"] = "Reconnecting..."
        elif self.websocket and self.websocket.open:
            summary["connection_status"] = "Connected"
        elif self.websocket and hasattr(self.websocket, 'state_name') and self.websocket.state_name == "CONNECTING": # websockets library specific
            summary["connection_status"] = "Connecting..."
        elif self.websocket and (self.websocket.closed or (hasattr(self.websocket, 'state_name') and self.websocket.state_name == "CLOSED")):
            summary["connection_status"] = "Closed"
        elif not self.websocket:
            summary["connection_status"] = "Not Initialized"
        else: # Fallback for other potential states from the websockets library
            summary["connection_status"] = self.websocket.state_name if hasattr(self.websocket, 'state_name') else "Unknown"
            
        return summary