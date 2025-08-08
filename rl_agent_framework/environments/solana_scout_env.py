# trading_rl_agent/environments/solana_scout_env.py
"""
Gymnasium environment for the Scout (Decision Gate) agent.

In this environment, the agent is presented with a potential trade opportunity
(a "decision point"). It must make a single, discrete choice: 'BUY' (1) or
'IGNORE' (0).

An episode consists of this single decision. If the agent chooses to buy, the
environment simulates the entire lifecycle of that trade using a predefined,
fixed stop-loss/take-profit strategy. The reward is the final realized PnL
of that simulated trade. If the agent ignores, the reward is zero.

The goal is for the agent to learn which token opportunities are likely to be
profitable under the fixed management strategy, acting as an intelligent filter.
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, Optional
import os

# Import from the new centralized config
from config import rl_config as cfg

class SolanaDecisionEnv(gym.Env):
    """
    An environment where the agent makes a single 'BUY' or 'IGNORE' decision
    for a given token opportunity. An episode simulates the entire lifecycle
    of that single trade.
    """
    def __init__(self, df: pd.DataFrame, ohlcv_data_dir: str):
        super().__init__()
        self.df = df # This is the dataframe of decision points
        self.ohlcv_data_dir = ohlcv_data_dir # Path to the directory with Parquet files

        # The observation space is a flat vector of token features
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(cfg.ScoutConfig.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )
        # The action space is a discrete choice: 0 for IGNORE, 1 for BUY
        self.action_space = spaces.Discrete(cfg.ScoutConfig.ACTION_SPACE_DIM)

        self._current_decision_idx = 0
        self._token_ohlcv = None
        self._simulation_step = 0

    def _get_observation(self) -> np.ndarray:
        """Extracts the features for the current decision point from the dataframe."""
        obs_series = self.df.iloc[self._current_decision_idx][cfg.ScoutConfig.OBSERVATION_FEATURES]
        return obs_series.to_numpy(dtype=np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> tuple:
        super().reset(seed=seed)
        # Move to a random decision point in the dataset for the start of a new episode
        self._current_decision_idx = self.np_random.integers(0, len(self.df))
        self.current_decision_info = self.df.iloc[self._current_decision_idx]
        
        # Load the full OHLCV data for the token in this decision
        mint = self.current_decision_info['mint']
        try:
            token_file_path = os.path.join(self.ohlcv_data_dir, f"{mint}.parquet")
            self._token_ohlcv = pd.read_parquet(token_file_path)
        except FileNotFoundError:
            # Handle cases where the file might not exist, though it should
            self._token_ohlcv = None

        self._simulation_step = 0
        return self._get_observation(), {}

    def step(self, action: int) -> tuple:
        """
        Executes the chosen action. The episode terminates immediately with a
        reward based on the trade's outcome.
        """
        terminated = True # Every episode is a single step from the agent's perspective

        # Case 1: Agent chose to IGNORE
        if action == 0 or self._token_ohlcv is None or self._token_ohlcv.empty:
            return self._get_observation(), 0.0, terminated, False, {}

        # Case 2: Agent chose to BUY - run the simulation
        reward = self._simulate_trade()
        return self._get_observation(), reward, terminated, False, {}

    def _simulate_trade(self) -> float:
        """
        Simulates a trade based on the bot's existing SL/TP logic.
        Returns the final realized PnL.
        """
        # Get the price data starting from the decision point
        decision_timestamp = self.current_decision_info['timestamp']
        trade_data = self._token_ohlcv[self._token_ohlcv.index >= decision_timestamp]

        if len(trade_data) < 2:
            return -cfg.ScoutConfig.SIMULATION_FAILURE_PENALTY # Immediate loss if no data to trade on

        buy_price = trade_data['Close'].iloc[0]
        if buy_price <= 0:
            return -cfg.ScoutConfig.SIMULATION_FAILURE_PENALTY 

        # Set SL/TP levels based on config
        stop_loss_price = buy_price * (1 - cfg.ScoutConfig.SIM_INITIAL_STOP_LOSS_PERCENT / 100.0)
        first_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_FIRST_SELL_PROFIT_MARGIN / 100.0)
        second_tp_price = buy_price * (1 + cfg.ScoutConfig.SIM_SECOND_TAKE_PROFIT_PERCENT / 100.0)
        
        highest_price = buy_price
        first_tp_hit = False
        
        # Iterate through the token's price history from the point of buying
        for i in range(1, min(len(trade_data), cfg.ScoutConfig.MAX_STEPS_PER_EPISODE)):
            self._simulation_step = i
            current_price = trade_data['Close'].iloc[i]
            highest_price = max(highest_price, current_price)

            # Check sell conditions in order of priority
            if current_price <= stop_loss_price:
                return (current_price - buy_price) / buy_price

            if current_price >= second_tp_price:
                return (current_price - buy_price) / buy_price

            if not first_tp_hit and current_price >= first_tp_price:
                first_tp_hit = True
                stop_loss_price = buy_price # Breakeven

            if first_tp_hit:
                trailing_sl = highest_price * (1 - cfg.ScoutConfig.SIM_TRAILING_STOP_LOSS_PERCENT / 100.0)
                if current_price <= trailing_sl:
                     return (current_price - buy_price) / buy_price
        
        last_price = trade_data['Close'].iloc[-1]
        pnl = (last_price - buy_price) / buy_price
        time_penalty = self._simulation_step * cfg.ScoutConfig.TIME_PENALTY_PER_STEP
        return pnl - time_penalty
