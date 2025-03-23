"""
state.py - Centralized storage for dynamic global values.
Manages mutable global state such as SOL price, shutdown flag, active subscriptions, and API rate timestamps.
"""
import asyncio
from collections import deque
from logger import logger

class GlobalState:
    """Thread-safe Singleton class to store global state variables."""
    _instance = None
    _lock = asyncio.Lock()  # Ensures only one instance is created

    def __init__(self):
        """Initialize state variables."""
        self.sol_price = None          # SOL price (updated hourly)
        self.shutdown = False          # Global shutdown flag
        self.shutdown_event = asyncio.Event()  # 🚀 Interruptible sleep support
        self.active_subscriptions = set()  # Active token subscriptions
        self.new_token_subscription = False  # WebSocket subscription status

        # API rate limiting
        self.request_timestamps = deque(maxlen=10)  # API request tracker

        # Queues
        self.rugcheck_queue = asyncio.PriorityQueue()  # RugCheck processing queue

        # Concurrency control
        self.lock = asyncio.Lock()  # General state lock
        self.db_write_lock = asyncio.Lock()  # Database write lock

    @staticmethod
    async def get_instance():
        """Returns a singleton instance of GlobalState."""
        async with GlobalState._lock:
            if GlobalState._instance is None:
                GlobalState._instance = GlobalState()
        return GlobalState._instance

    ## 🚀 SOL Price Management
    async def set_sol_price(self, price: float):
        async with self.lock:
            self.sol_price = price

    async def get_sol_price(self) -> float:
        async with self.lock:
            return self.sol_price

    ## 🚀 Shutdown Control
    async def set_shutdown(self, status: bool):
        """Set shutdown flag and notify all sleeping tasks."""
        async with self.lock:
            self.shutdown = status
            if status:
                self.shutdown_event.set()  # 🚀 Wake up all sleeping tasks immediately

    async def get_shutdown(self) -> bool:
        async with self.lock:
            return self.shutdown

    async def wait_or_interrupt(self, timeout: float):
        """Waits for a given timeout, but exits early if shutdown is triggered."""
        # logger.debug(f"wait_or_interrupt: waiting for {timeout} seconds")
        try:
            await asyncio.wait_for(self.shutdown_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.debug("wait_or_interrupt: timeout expired normally")
            pass  # This is expected if the timeout expires normally

    ## 🚀 Subscription Management
    async def add_subscription(self, mint: str):
        async with self.lock:
            self.active_subscriptions.add(mint)

    async def remove_subscription(self, mint: str):
        async with self.lock:
            self.active_subscriptions.discard(mint)

    async def get_subscriptions(self):
        async with self.lock:
            return set(self.active_subscriptions)

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

# Singleton instance
state = asyncio.run(GlobalState.get_instance())
