"""
state.py - Centralized storage for dynamic global values.
Manages mutable global state such as SOL price, shutdown flag, active subscriptions, and API rate timestamps.
"""
import asyncio
from asyncio import Queue
from collections import deque
import config # Import config to access INITIAL_SOL_BALANCE
import json # Added for file writing
from bot_logger import logger
import os

# Define the path for the shared SOL price file
SOL_PRICE_FILE = 'data/sol_price.json'
SUBSCRIPTIONS_FILE = 'data/current_subscriptions.json'

class GlobalState:
    """Thread-safe Singleton class to store global state variables."""
    _instance = None
    _lock = asyncio.Lock()  # Ensures only one instance is created

    def __init__(self):
        if GlobalState._instance is not None:
            raise Exception("This class is a singleton!")

        """Initialize state variables."""
        self.shutdown_event = asyncio.Event()  # 🚀 Interruptible sleep support
        self.websocket_handler = None  # 🚀 Store WebSocketHandler instance
        self.new_token_subscription = False  # WebSocket subscription status
        self.migration_stream_subscribed = False  # Migration stream subscription status 
        self.active_token_subscriptions = set()  # Active token subscriptions
        self.sol_price = None          # SOL price (updated hourly)
        self.db_client = None          # Database client instance
        self.is_buying_enabled = True # ADDED: Flag to control buy orders

        # API rate limiting
        self.request_timestamps = deque(maxlen=10)  # API request tracker

        # PnL Tracking
        self.current_sol_balance = float(config._INITIAL_SOL_BALANCE) # Initialize from config

        # Queues
        self.rugcheck_queue = asyncio.PriorityQueue()  # RugCheck processing queue
        self.socialscheck_queue = asyncio.PriorityQueue()  # SocialsCheck processing queue
        self.enrichment_queue = asyncio.Queue() # Transaction enrichment queue

        # Concurrency control
        self.lock = asyncio.Lock()  # General state lock
        self.db_write_lock = asyncio.Lock()  # Database write lock

    def _load_subscriptions_from_file(self):
        """Load active token subscriptions from file if it exists."""
        try:
            if os.path.exists(SUBSCRIPTIONS_FILE):
                with open(SUBSCRIPTIONS_FILE, 'r') as f:
                    return set(json.load(f))
            else:
                return set()
        except Exception as e:
            logger.error(f"Error loading subscriptions from file: {e}")
            return set()

    def _save_subscriptions_to_file(self):
        """Save current active token subscriptions to file atomically."""
        # Ensure data directory exists (it's created in TradingBot, but good to be robust)
        data_dir = os.path.dirname(SUBSCRIPTIONS_FILE)
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
            except OSError as e:
                logger.error(f"Could not create data directory {data_dir}: {e}")
                return # Cannot proceed if directory cannot be created

        temp_file_path = SUBSCRIPTIONS_FILE + ".tmp"
        try:
            # The self.active_token_subscriptions set is already under self.lock in the calling methods
            # So, here we just perform the file operation.
            with open(temp_file_path, 'w') as f:
                json.dump(list(self.active_token_subscriptions), f, indent=2)
            os.replace(temp_file_path, SUBSCRIPTIONS_FILE) # Atomic rename
            # logger.debug(f"Saved {len(self.active_token_subscriptions)} subscriptions to {SUBSCRIPTIONS_FILE}")
        except Exception as e:
            logger.error(f"Error saving subscriptions to file {SUBSCRIPTIONS_FILE}: {e}")
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as ose:
                    logger.error(f"Error removing temporary subscription file {temp_file_path}: {ose}")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def wait_for_shutdown(self):
        await self.shutdown_event.wait()

    def trigger_shutdown(self):
        self.shutdown_event.set()

    async def set_websocket_handler(self, handler):
        async with self.lock:
            self.websocket_handler = handler

    async def set_db_client(self, client):
        async with self.lock:
            self.db_client = client

    ## 🚀 SOL Price Management
    async def set_sol_price(self, price: float):
        """Sets the in-memory SOL price and writes it to a shared file."""
        if price is None:
            logger.warning("Attempted to set SOL price to None. Skipping file write.")
            return
            
        async with self.lock:
            self.sol_price = price
            # Also write to the shared file for the web app process
            try:
                # Use 'w' to overwrite the file completely each time
                with open(SOL_PRICE_FILE, 'w') as f:
                    json.dump({"price": price}, f)
                # logger.debug(f"Wrote SOL price {price} to {SOL_PRICE_FILE}") # Optional: debug log
            except IOError as e:
                logger.error(f"Failed to write SOL price to {SOL_PRICE_FILE}: {e}")
            except Exception as e: # Catch potential JSON errors too
                logger.error(f"Unexpected error writing SOL price to {SOL_PRICE_FILE}: {e}")

    async def get_sol_price(self) -> float:
        async with self.lock:
            return self.sol_price

    async def wait_or_interrupt(self, timeout: float):
        """Waits for a given timeout, but exits early if shutdown is triggered."""
        # logger.debug(f"wait_or_interrupt: waiting for {timeout} seconds")
        try:
            await asyncio.wait_for(self.shutdown_event.wait(), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            #logger.debug("wait_or_interrupt: timeout expired normally")
            pass  # This is expected if the timeout expires normally

    ## 🚀 Subscription Management
    async def add_token_subscription(self, mint: str):
        async with self.lock:
            self.active_token_subscriptions.add(mint)
        self._save_subscriptions_to_file()

    async def remove_token_subscription(self, mint: str):
        async with self.lock:
            self.active_token_subscriptions.discard(mint)
        self._save_subscriptions_to_file()

    async def get_token_subscriptions(self):
        async with self.lock:
            return set(self.active_token_subscriptions)

    ## 🚀 WebSocket Subscription Flag
    async def set_new_token_subscription(self, status: bool):
        async with self.lock:
            self.new_token_subscription = status

    async def get_new_token_subscription(self) -> bool:
        async with self.lock:
            return self.new_token_subscription
        
    async def set_migration_subscription(self, status: bool):
        async with self.lock:
            self.migration_stream_subscribed = status

    async def get_migration_subscription(self) -> bool:
        async with self.lock:
            return self.migration_stream_subscribed

    ## 🚀 API Rate Limiting
    async def add_request_timestamp(self, timestamp):
        async with self.lock:
            self.request_timestamps.append(timestamp)

    async def get_request_timestamps(self):
        async with self.lock:
            return list(self.request_timestamps)

    ## 🚀 Queue Accessors
    def get_rugcheck_queue(self) -> asyncio.PriorityQueue:
        return self.rugcheck_queue

    def get_socialscheck_queue(self) -> asyncio.PriorityQueue:
        return self.socialscheck_queue
    
    def get_enrichment_queue(self) -> asyncio.Queue: # <<< ADD THIS
        return self.enrichment_queue

    def get_db_write_lock(self):
        return self.db_write_lock

    ## 🚀 PnL Tracking
    async def get_current_sol_balance(self) -> float:
        """Get the current tracked SOL balance."""
        async with self.lock:
            #logger.info(f"💰 Current SOL Balance: {self.current_sol_balance:.6f} SOL")
            return self.current_sol_balance

    async def update_sol_balance(self, change: float):
        """Update the SOL balance by adding the change (can be negative)."""
        async with self.lock:
            self.current_sol_balance += change
            logger.info(f"💰 Updated SOL Balance: {self.current_sol_balance:.6f} SOL (Change: {change:+.6f} SOL)")