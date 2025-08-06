# trading_rl_agent/environments/solana_management_env.py
"""
Gymnasium environment for the Manager (Trade Management) agent.

This environment simulates the lifecycle of a single, already open trade.
At each step (a 5-second interval), the agent receives an observation about the
current state of the trade (e.g., PnL, time in trade) and must decide to either
'HOLD' (0) or 'SELL' (1).

The episode continues until the agent decides to sell, or until the available
historical data for that trade runs out. The reward is structured to incentivize
maximizing profit while penalizing prolonged holding, especially in losing positions.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, Optional

from config import rl_config as cfg

class SolanaManagementEnv(gym.Env):
    """
    An environment representing the lifecycle of a single open trade.
    The agent's goal is to decide the optimal point to sell a token
    that has already been bought by the Scout agent.
    """
    def __init__(self, trade_lifecycles: Dict[str, pd.DataFrame]):
        super().__init__()
        self.trade_lifecycles = trade_lifecycles
        self.trade_ids = list(self.trade_lifecycles.keys())

        self.observation_space = spaces.Box(
            low=np.array([-1.0, 0, 0, -1.0, -1.0], dtype=np.float32),
            high=np.array([np.inf, np.inf, np.inf, np.inf, np.inf], dtype=np.float32),
            shape=(cfg.ManagerConfig.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        self.action_space = spaces.Discrete(cfg.ManagerConfig.ACTION_SPACE_DIM)

        self._current_trade_id: Optional[str] = None
        self._current_trade_data: Optional[pd.DataFrame] = None
        self._current_step: int = 0
        self._buy_price: float = 0.0
        self._buy_market_cap: float = 0.0
        self._highest_pnl: float = 0.0
        self._time_of_buy: Optional[pd.Timestamp] = None

    def _get_observation(self) -> np.ndarray:
        if self._current_trade_data is None or self._current_step >= len(self._current_trade_data):
            return np.zeros(self.observation_space.shape, dtype=np.float32)

        current_row = self._current_trade_data.iloc[self._current_step]
        current_price = current_row['Close']
        current_market_cap = current_row['marketCapSol']
        
        current_pnl = (current_price - self._buy_price) / self._buy_price if self._buy_price > 0 else 0.0
        current_timestamp = self._current_trade_data.index[self._current_step]
        time_in_trade = (current_timestamp - self._time_of_buy).total_seconds()
        volatility = current_row['volatility']
        mc_change_pct = (current_market_cap - self._buy_market_cap) / self._buy_market_cap if self._buy_market_cap > 0 else 0.0
        self._highest_pnl = max(self._highest_pnl, current_pnl)

        return np.array([
            current_pnl, time_in_trade, volatility, mc_change_pct, self._highest_pnl
        ], dtype=np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> tuple:
        super().reset(seed=seed)
        self._current_trade_id = self.np_random.choice(self.trade_ids)
        self._current_trade_data = self.trade_lifecycles[self._current_trade_id]
        self._current_step = 0
        initial_state = self._current_trade_data.iloc[0]
        self._buy_price = initial_state['Close']
        self._buy_market_cap = initial_state['marketCapSol']
        self._time_of_buy = self._current_trade_data.index[0]
        self._highest_pnl = 0.0
        return self._get_observation(), {}

    def step(self, action: int) -> tuple:
        """Advances the environment by one time step based on the agent's action."""
        terminated = False
        truncated = False
        
        current_price = self._current_trade_data.iloc[self._current_step]['Close']
        current_pnl = (current_price - self._buy_price) / self._buy_price if self._buy_price > 0 else 0.0

        if action == 1:  # SELL_NOW
            terminated = True
            # The final reward is the realized PnL of the trade.
            reward = current_pnl
        else:  # HOLD
            # --- MODIFIED REWARD LOGIC ---
            # Provide step-by-step feedback.
            if current_pnl > 0:
                # Small reward for holding a profitable position.
                reward = 0.0005
            else:
                # Larger penalty for holding a losing position.
                reward = -0.001
            # --- END MODIFICATION ---

            self._current_step += 1
            if self._current_step >= len(self._current_trade_data):
                truncated = True
                # If truncated, the final reward is the PnL at the last known data point.
                reward = current_pnl

        return self._get_observation(), reward, terminated, truncated, {}
