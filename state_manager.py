"""
state.py - Centralized storage for dynamic global values.
Manages mutable global state such as SOL price, shutdown flag, active subscriptions, and API rate timestamps.
"""
import asyncio
from asyncio import Queue
from collections import deque
import config # Import config to access INITIAL_SOL_BALANCE
from logger import logger

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
        self.active_token_subscriptions = set()  # Active token subscriptions
        self.sol_price = None          # SOL price (updated hourly)
        self.db_client = None          # Database client instance

        # API rate limiting
        self.request_timestamps = deque(maxlen=10)  # API request tracker

        # PnL Tracking
        self.current_sol_balance = float(config.INITIAL_SOL_BALANCE) # Initialize from config

        # Queues
        self.rugcheck_queue = asyncio.PriorityQueue()  # RugCheck processing queue

        # Concurrency control
        self.lock = asyncio.Lock()  # General state lock
        self.db_write_lock = asyncio.Lock()  # Database write lock

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
        async with self.lock:
            self.sol_price = price

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

    async def remove_token_subscription(self, mint: str):
        async with self.lock:
            self.active_token_subscriptions.discard(mint)

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
