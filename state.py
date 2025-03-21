"""
state.py - Centralized storage for dynamic global values.
Manages mutable global state such as SOL price, shutdown flag, active subscriptions, and API rate timestamps.
"""

import asyncio
from collections import deque

class GlobalState:
    """Singleton class to store dynamic global state variables."""
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalState, cls).__new__(cls)
            
            # Initialize dynamic variables
            cls._instance.sol_price = None                   # SOL price (updated every hour)
            cls._instance.shutdown = False                   # Shutdown flag
            cls._instance.active_subscriptions = set()       # Active token subscriptions
            cls._instance.new_token_subscription = False     # WebSocket subscription flag for new tokens
            cls._instance.request_timestamps = deque(maxlen=10)  # API request timestamps
            cls._instance.rugcheck_queue = asyncio.PriorityQueue()   # <-- Added: RugCheck API queue
            
            # Async lock for thread safety
            cls._instance.lock = asyncio.Lock()
        
        return cls._instance

    ## 🚀 SOL Price Methods
    async def set_sol_price(self, price: float):
        """Asynchronously update SOL price."""
        async with self.lock:
            self.sol_price = price

    async def get_sol_price(self) -> float:
        """Asynchronously retrieve the latest SOL price."""
        async with self.lock:
            return self.sol_price

    ## 🚀 Shutdown Flag Methods
    async def set_shutdown(self, status: bool):
        """Set shutdown flag."""
        async with self.lock:
            self.shutdown = status

    async def get_shutdown(self) -> bool:
        """Check if shutdown flag is set."""
        async with self.lock:
            return self.shutdown

    ## 🚀 Active Subscriptions Methods
    async def add_subscription(self, mint: str):
        """Add a new token mint to active subscriptions."""
        async with self.lock:
            self.active_subscriptions.add(mint)

    async def remove_subscription(self, mint: str):
        """Remove a token mint from active subscriptions."""
        async with self.lock:
            self.active_subscriptions.discard(mint)

    async def get_subscriptions(self):
        """Get the set of active subscriptions."""
        async with self.lock:
            return set(self.active_subscriptions)

    ## 🚀 WebSocket Subscription Flag
    async def set_new_token_subscription(self, status: bool):
        """Set the WebSocket new token subscription flag."""
        async with self.lock:
            self.new_token_subscription = status

    async def get_new_token_subscription(self) -> bool:
        """Get the WebSocket new token subscription flag."""
        async with self.lock:
            return self.new_token_subscription

    ## 🚀 API Rate Limiting Methods
    async def add_request_timestamp(self, timestamp):
        """Add a timestamp for API request tracking."""
        async with self.lock:
            self.request_timestamps.append(timestamp)

    async def get_request_timestamps(self):
        """Retrieve API request timestamps."""
        async with self.lock:
            return list(self.request_timestamps)

    ## 🚀 RugCheck Queue Accessor
    def get_rugcheck_queue(self) -> asyncio.Queue:
        """Return the RugCheck API request queue."""
        return self.rugcheck_queue

# Create the global state instance
state = GlobalState()
