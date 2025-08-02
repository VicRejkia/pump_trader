# FILE: trading_rl_agent/environments/solana_env.py

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from collections import deque

from trading_rl_agent import rl_config

class SolanaPortfolioEnv(gym.Env):
    """
    Custom Gymnasium Environment for training a Meta-Controller to manage a
    portfolio of Solana meme coins.

    - **Observation Space (Dict)**:
        - `token_data`: Time-series data for each token in the universe.
        - `global_data`: Vector of portfolio-wide and market-wide stats.
    - **Action Space (Box)**:
        - A continuous vector representing target portfolio weights for each
          token plus a cash (SOL) position. The action is normalized via softmax.
    - **Reward**:
        - A composite reward function including PnL, Sharpe ratio, drawdown,
          and penalties for turnover and holding.
    """
    metadata = {'render_modes': ['human']}

    def __init__(
        self,
        token_data_map: Dict[str, pd.DataFrame],
        initial_capital: float = rl_config.INITIAL_CAPITAL,
        max_steps: int = rl_config.MAX_STEPS_PER_EPISODE
    ):
        super().__init__()

        if not token_data_map:
            raise ValueError("token_data_map cannot be empty.")

        self.token_data_map = token_data_map
        self.available_mints = list(token_data_map.keys())
        self.initial_capital = initial_capital
        self._max_episode_steps = max_steps

        # --- Determine Simulation Time Range ---
        # Find the earliest start time and latest end time across all token dataframes.
        self.min_ts = min(df.index.min() for df in token_data_map.values())
        self.max_ts = max(df.index.max() for df in token_data_map.values())
        self.decision_freq = pd.Timedelta(rl_config.DECISION_FREQUENCY)

        # --- Define Observation and Action Spaces ---
        self.observation_space = spaces.Dict({
            "token_data": spaces.Box(
                low=-np.inf, high=np.inf,
                shape=(rl_config.MAX_TOKENS_IN_UNIVERSE, rl_config.TOKEN_HISTORY_LENGTH, rl_config.NUM_TOKEN_FEATURES),
                dtype=np.float32
            ),
            "global_data": spaces.Box(
                low=-np.inf, high=np.inf,
                shape=(rl_config.NUM_GLOBAL_FEATURES,),
                dtype=np.float32
            )
        })

        self.action_space = spaces.Box(
            low=0, high=1,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        
        # --- State Initialization ---
        self._initialize_state()

    def _initialize_state(self):
        """Initializes all simulation state variables for a new episode."""
        self.current_step = 0
        self.current_time = self.min_ts
        self.sol_balance = self.initial_capital
        self.portfolio_value = self.initial_capital
        
        # Map mints to a fixed index for the observation/action space
        self.mint_to_idx = {mint: i for i, mint in enumerate(self.available_mints) if i < rl_config.MAX_TOKENS_IN_UNIVERSE}
        self.idx_to_mint = {i: mint for mint, i in self.mint_to_idx.items()}
        
        # Portfolio state tracking
        self.current_weights = np.zeros(rl_config.ACTION_SPACE_DIM)
        self.current_weights[-1] = 1.0 # Start with 100% in SOL
        self.token_holdings = np.zeros(rl_config.MAX_TOKENS_IN_UNIVERSE)
        
        self.trade_history = []
        self.realized_pnl = 0.0
        
        # For reward calculation
        self.portfolio_values_history = deque(maxlen=self._max_episode_steps)
        self.portfolio_values_history.append(self.initial_capital)
        self.peak_portfolio_value = self.initial_capital

    def _get_observation(self) -> Dict[str, np.ndarray]:
        """Constructs the full observation dictionary for the current timestep."""
        # --- Token Data ---
        token_obs_array = np.zeros(self.observation_space["token_data"].shape, dtype=np.float32)
        
        for mint, idx in self.mint_to_idx.items():
            df = self.token_data_map[mint]
            # Get data up to the current time, then take the last N steps for history
            past_data = df.loc[df.index <= self.current_time].tail(rl_config.TOKEN_HISTORY_LENGTH)
            
            if not past_data.empty:
                # Ensure data has the correct features and handle missing columns
                feature_data = past_data[rl_config.TOKEN_FEATURES].values
                # Pad if history is shorter than required length
                padded_data = np.zeros((rl_config.TOKEN_HISTORY_LENGTH, rl_config.NUM_TOKEN_FEATURES))
                padded_data[-len(feature_data):] = feature_data
                token_obs_array[idx] = padded_data

        # --- Global Data ---
        global_features = np.zeros(rl_config.NUM_GLOBAL_FEATURES, dtype=np.float32)
        
        # Normalization factor for balances/values
        norm_factor = self.initial_capital * 2 
        
        global_features[0] = self.sol_balance / norm_factor
        global_features[1] = self.portfolio_value / norm_factor
        global_features[2] = self._calculate_unrealized_pnl()
        global_features[3] = np.count_nonzero(self.token_holdings)
        # Other global features (avg holding period, market trend, etc.) would be calculated here.
        # For brevity, they are left as zero for now.

        return {
            "token_data": token_obs_array,
            "global_data": global_features
        }

    def _calculate_unrealized_pnl(self) -> float:
        """Calculates the total unrealized profit or loss of current holdings."""
        total_pnl = 0.0
        # This requires tracking the cost basis of holdings, which adds complexity.
        # For now, we return a simplified metric or 0.
        return total_pnl

    def _apply_action(self, action: np.ndarray) -> tuple[float, float]:
        """
        Applies the agent's action (target weights) to the portfolio,
        simulating rebalancing trades and calculating costs.
        Returns the realized PnL from this step and the total turnover.
        """
        # --- FIX START: Ensure action is a flat numpy array ---
        # The action from the vec_env might be nested; flatten it.
        action = np.ravel(action)
        if action.shape[0] != rl_config.ACTION_SPACE_DIM:
            raise ValueError(f"Action shape mismatch. Got {action.shape}, expected {(rl_config.ACTION_SPACE_DIM,)}")
        # --- FIX END ---

        # Normalize action vector to ensure weights sum to 1 using softmax
        target_weights = np.exp(action - np.max(action)) / np.sum(np.exp(action - np.max(action)))
        
        # Calculate the current portfolio value *before* any trades
        current_holdings_value = 0.0
        for idx, mint in self.idx_to_mint.items():
            price = self._get_price_at_current_time(mint)
            current_holdings_value += self.token_holdings[idx] * price
        
        portfolio_value_before_trade = self.sol_balance + current_holdings_value
        
        # Determine target value for each asset
        target_asset_values = target_weights * portfolio_value_before_trade
        
        # --- DEFENSIVE CHECK ---
        if not isinstance(target_asset_values, np.ndarray) or target_asset_values.ndim == 0:
            raise TypeError(f"FATAL: target_asset_values is not an array. Value: {target_asset_values}")

        turnover_sol = 0
        realized_pnl_step = 0.0 # This remains 0 as PnL is tracked via portfolio value change

        # On the first step, initialize the cost basis tracker
        if not hasattr(self, 'cost_basis'):
            self.cost_basis = np.zeros(rl_config.MAX_TOKENS_IN_UNIVERSE)

        # Process trades
        for idx, mint in self.idx_to_mint.items():
            price = self._get_price_at_current_time(mint)
            current_token_value = self.token_holdings[idx] * price
            target_token_value = target_asset_values[idx] # This line was failing
            delta_value = target_token_value - current_token_value
            
            turnover_sol += abs(delta_value)
            
            if price > 0:
                self.sol_balance -= delta_value
                self.token_holdings[idx] += delta_value / price

        transaction_cost = turnover_sol * 0.002
        self.sol_balance -= transaction_cost
        self.current_weights = target_weights
        
        return realized_pnl_step, turnover_sol
    
    def _get_price_at_current_time(self, mint: str) -> float:
        """Gets the closing price for a mint at the current simulation time."""
        if mint not in self.token_data_map: return 0.0
        df = self.token_data_map[mint]
        try:
            # Use asof for efficient point-in-time lookup
            price = df.asof(self.current_time)['Close']
            return price if pd.notna(price) else 0.0
        except (KeyError, IndexError):
            return 0.0

    def step(self, action: np.ndarray) -> tuple:
        # --- FIX START ---
        # We now get turnover from the corrected apply_action
        realized_pnl, turnover = self._apply_action(action)
        self.realized_pnl += realized_pnl
        
        # Update time
        self.current_step += 1
        self.current_time += self.decision_freq
        
        # Update total portfolio value *after* rebalancing
        current_holdings_value = 0.0
        for idx, mint in self.idx_to_mint.items():
            price = self._get_price_at_current_time(mint)
            current_holdings_value += self.token_holdings[idx] * price
        self.portfolio_value = self.sol_balance + current_holdings_value
        # --- FIX END ---

        self.portfolio_values_history.append(self.portfolio_value)
        self.peak_portfolio_value = max(self.peak_portfolio_value, self.portfolio_value)
        
        # --- Calculate Composite Reward ---
        reward = self._calculate_reward(realized_pnl, turnover)
        
        # ... (the debugging block you added can remain here) ...
        termination_threshold = self.initial_capital * 0.2

        # DEBUGGING: Uncomment to see detailed step-by-step output

        # is_terminated = self.portfolio_value <= termination_threshold
        # print("\n" + "="*50)
        # print(f"DEBUGGING STEP: {self.current_step}")
        # print(f"  - Current Time: {self.current_time}")
        # print(f"  - Portfolio Value: {self.portfolio_value:.4f} SOL")
        # print(f"  - Realized PnL this step: {realized_pnl:.4f}")
        # print(f"  - Reward this step: {reward:.4f}")
        # print(f"  - Termination Check: Portfolio Value ({self.portfolio_value:.4f}) <= Threshold ({termination_threshold:.4f}) -> {is_terminated}")
        # if is_terminated:
        #     print(f"  - CAUSE: Portfolio value dropped below the 80% loss threshold.")
        # print("="*50 + "\n")

        # --- Check for Termination/Truncation ---
        terminated = self.portfolio_value <= self.initial_capital * 0.2 # Stop if 80% loss
        max_steps_reached = self.current_step >= self._max_episode_steps
        end_of_data = self.current_time >= self.max_ts
        truncated = max_steps_reached or end_of_data
        
        observation = self._get_observation()
        info = {'portfolio_value': self.portfolio_value, 'realized_pnl': self.realized_pnl}

        return observation, reward, terminated, truncated, info

    def _calculate_reward(self, realized_pnl: float, turnover: float) -> float:
        """Calculates the composite reward for the current step."""
        # 1. PnL Component
        pnl_reward = realized_pnl * rl_config.REWARD_PNL_WEIGHT
        
        # 2. Sharpe Ratio Component (simplified)
        returns = np.diff(list(self.portfolio_values_history))
        sharpe_reward = 0.0
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns)
            sharpe_reward = sharpe_ratio * rl_config.REWARD_SHARPE_WEIGHT
            
        # 3. Drawdown Penalty
        drawdown = (self.peak_portfolio_value - self.portfolio_value) / self.peak_portfolio_value
        drawdown_penalty = drawdown * rl_config.REWARD_DRAWDOWN_PENALTY
        
        # 4. Turnover Penalty
        turnover_penalty = (turnover / self.portfolio_value) * rl_config.REWARD_TURNOVER_PENALTY
        
        total_reward = pnl_reward + sharpe_reward - drawdown_penalty - turnover_penalty
        return total_reward

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> tuple:
        super().reset(seed=seed)
        self._initialize_state()
        return self._get_observation(), {}

    def render(self, mode='human'):
        if mode == 'human':
            print(
                f"Step: {self.current_step}/{self._max_episode_steps} | "
                f"Time: {self.current_time.strftime('%Y-%m-%d %H:%M')} | "
                f"Portfolio Value: {self.portfolio_value:.2f} SOL"
            )