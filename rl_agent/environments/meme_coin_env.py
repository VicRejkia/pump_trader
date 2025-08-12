# rl_agent/environments/meme_coin_env.py
"""
The core custom OpenAI Gym environment for trading Solana meme coins.
"""
import gymnasium as gym
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from gymnasium import spaces
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger
from rl_agent.data.data_manager import DataManager
from rl_agent.rewards.reward_function import RewardFunction

# Define the feature columns that will be used for the observation space.
# These must match the output of rl_agent/feature_engineering/features.py
FEATURE_COLUMNS = [
    'volume_usd', 'buy_volume_usd', 'sell_volume_usd', 'market_cap_sol', 'tx_buy_count', 
    'tx_sell_count', 'sol_price_avg', 'price_change_15s', 'price_change_30s', 
    'volume_change_15s', 'volatility_15s', 'buy_sell_ratio', 'buy_sell_ratio_15s', 
    'short_term_rsi', 'tx_buy_count_15s', 'tx_sell_count_15s', 'tx_total_count_15s', 
    'macd', 'macd_signal', 'macd_histogram', 'bollinger_upper', 'bollinger_lower', 
    'bollinger_width', 'ema_short', 'ema_long', 'adx_15s', 'obv', 
    'rugcheck_score', 'socials_score', 'token_age_seconds'
]

# Define how many of the top tokens (by volume) the agent should observe at each step.
NUM_TOP_TOKENS_TO_OBSERVE = 5

class MemeCoinEnv(gym.Env):
    """
    A multi-token, portfolio-based Gym environment for meme coin trading.
    It now uses a more sophisticated observation space to leverage all engineered features.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, data_manager: DataManager, config: Dict[str, Any], initial_balance: float = 100.0):
        super().__init__()
        self.data_manager = data_manager
        self.config = config
        self.initial_balance = initial_balance
        self.reward_function = RewardFunction(config)
        self.max_concurrent_positions = self.config.get('MAX_CONCURRENT_POSITIONS', 5)

        # --- Define Observation Space ---
        # The observation space is a flattened vector containing:
        # 1. Portfolio-level features (e.g., balance, value).
        # 2. Per-token features for the top N tokens.
        
        # 1. Portfolio features
        num_portfolio_features = 4  # balance, portfolio_value, num_positions, unrealized_pnl

        # 2. Per-token features (base data + position-specific data)
        num_base_token_features = len(FEATURE_COLUMNS)
        num_position_features = 5 # is_held, position_size_norm, unrealized_pnl_norm, time_in_position_norm, highest_price_ratio
        total_token_features = num_base_token_features + num_position_features

        # Total observation space size
        obs_space_size = num_portfolio_features + (NUM_TOP_TOKENS_TO_OBSERVE * total_token_features)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_space_size,), dtype=np.float32
        )
        
        # --- Define Action Space ---
        # A value for each of the top N observed tokens, from -1 (sell) to 1 (buy).
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(NUM_TOP_TOKENS_TO_OBSERVE,), dtype=np.float32
        )
        
        self.reset()

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        """Resets the environment to its initial state."""
        super().reset(seed=seed)
        self.data_manager.reset()
        
        self.balance = self.initial_balance
        self.portfolio_value = self.initial_balance
        # Positions: {mint: {'entry_price', 'size_sol', 'highest_price', 'timestamp'}}
        self.positions: Dict[str, Dict[str, Any]] = {} 
        self.current_step = 0
        self.trade_history = []
        
        # Advance to the first valid data point
        next_data = next(self.data_manager, None)
        while next_data is None:
            next_data = next(self.data_manager, None)
            if next_data is None: # Should not happen if data exists
                raise StopIteration("No data available in the data manager.")
        
        self.current_timestamp, self.current_data_point = next_data
        
        initial_obs = self._get_observation()
        return initial_obs, {}

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Executes one time step within the environment.
        Returns: observation, reward, terminated, truncated, info
        """
        # 1. Identify which tokens the actions correspond to
        observed_tokens = self._get_top_tokens()
        
        # 2. Execute Trades based on the action vector
        reward = 0.0
        
        # Execute sells first to free up capital
        reward += self._execute_sells(action, observed_tokens)
        
        # Execute buys with available capital
        reward += self._execute_buys(action, observed_tokens)

        # 3. Advance Time
        next_step_data = next(self.data_manager, None)
        terminated = next_step_data is None
        
        if terminated:
            # End of data, finalize episode
            obs = self._get_observation() # Get final observation
            return obs, reward, True, False, {}

        self.current_timestamp, self.current_data_point = next_step_data
        self.current_step += 1
        
        # 4. Update Portfolio & Calculate Step Reward
        self._update_portfolio()
        step_reward = self.reward_function.calculate_reward({}, self._get_current_global_state())
        reward += step_reward

        obs = self._get_observation()
        return obs, reward, False, False, {}


    def _get_top_tokens(self) -> List[pd.Series]:
        """Gets the top N tokens by volume at the current timestamp."""
        # The data manager now yields a timestamp and a DataFrame for that timestamp
        current_df = self.current_data_point
        if isinstance(current_df, pd.Series): # If only one token at timestamp
             current_df = current_df.to_frame().T
             
        top_tokens = current_df.sort_values('volume_usd', ascending=False).head(NUM_TOP_TOKENS_TO_OBSERVE)
        return [row for _, row in top_tokens.iterrows()]

    def _get_observation(self) -> np.ndarray:
        """Constructs the observation vector for the current state."""
        # 1. Portfolio Features
        balance_norm = self.balance / (self.portfolio_value + 1e-9)
        portfolio_value_norm = self.portfolio_value / self.initial_balance
        num_positions_norm = len(self.positions) / self.max_concurrent_positions
        
        unrealized_pnl = 0
        for mint, pos in self.positions.items():
            current_price = self._get_price_for_mint(mint)
            if current_price is not None:
                unrealized_pnl += (current_price - pos['entry_price']) * (pos['size_sol'] / pos['entry_price'])
        unrealized_pnl_norm = unrealized_pnl / self.initial_balance

        portfolio_features = np.array([
            balance_norm, portfolio_value_norm, num_positions_norm, unrealized_pnl_norm
        ], dtype=np.float32)

        # 2. Token Features
        top_tokens = self._get_top_tokens()
        token_features_list = []

        num_base_token_features = len(FEATURE_COLUMNS)
        num_position_features = 5
        
        for i in range(NUM_TOP_TOKENS_TO_OBSERVE):
            if i < len(top_tokens):
                token_data = top_tokens[i]
                mint = token_data['mint']
                
                # Base features from data
                base_features = token_data[FEATURE_COLUMNS].values.astype(np.float32)

                # Position-specific features
                if mint in self.positions:
                    pos = self.positions[mint]
                    is_held = 1.0
                    position_size_norm = pos['size_sol'] / self.portfolio_value
                    pnl_norm = (self._get_price_for_mint(mint) - pos['entry_price']) / pos['entry_price']
                    time_in_position = (self.current_timestamp - pos['timestamp']).total_seconds()
                    time_in_position_norm = min(time_in_position / (3600*4), 1.0) # Normalize by 4 hours
                    highest_price_ratio = self._get_price_for_mint(mint) / pos['highest_price']
                else:
                    is_held = 0.0
                    position_size_norm = 0.0
                    pnl_norm = 0.0
                    time_in_position_norm = 0.0
                    highest_price_ratio = 0.0
                
                position_features = np.array([
                    is_held, position_size_norm, pnl_norm, time_in_position_norm, highest_price_ratio
                ], dtype=np.float32)
                
                combined_features = np.concatenate([base_features, position_features])
                token_features_list.append(combined_features)
            else:
                # Pad with zeros if fewer than N tokens are available
                token_features_list.append(np.zeros(num_base_token_features + num_position_features, dtype=np.float32))
        
        # Flatten and combine
        full_observation = np.concatenate([portfolio_features] + token_features_list, axis=0)
        return full_observation.astype(np.float32)

    def _execute_sells(self, action: np.ndarray, observed_tokens: List[pd.Series]) -> float:
        """Processes sell orders and calculates rewards."""
        total_reward = 0
        for i, token_data in enumerate(observed_tokens):
            mint = token_data['mint']
            # Action value < -0.2 is a signal to sell
            if mint in self.positions and action[i] < -0.2:
                position = self.positions[mint]
                current_price = token_data['Close']
                
                # Sell the entire position for simplicity
                sell_amount_sol = position['size_sol'] * (current_price / position['entry_price'])
                self.balance += sell_amount_sol
                
                pnl = sell_amount_sol - position['size_sol']
                
                trade_result = {
                    'side': 'sell', 'pnl': pnl, 'mint': mint,
                    'sell_fraction': 1.0, # Full sell
                    'price_to_highest_ratio': current_price / position['highest_price']
                }
                total_reward += self.reward_function.calculate_reward(trade_result, self._get_current_global_state(token_data))
                
                del self.positions[mint]
                self.trade_history.append(trade_result)

        return total_reward

    def _execute_buys(self, action: np.ndarray, observed_tokens: List[pd.Series]) -> float:
        """Processes buy orders and calculates rewards."""
        # Action value > 0.2 is a signal to buy
        buy_signals = {
            observed_tokens[i]['mint']: action[i] 
            for i in range(len(observed_tokens)) 
            if action[i] > 0.2
        }
        if not buy_signals:
            return 0.0

        # Allocate capital only if there are open slots
        available_slots = self.max_concurrent_positions - len(self.positions)
        if available_slots <= 0:
            return 0.0
            
        capital_per_buy = self.balance / available_slots * 0.95 # Keep some buffer

        for mint, _ in buy_signals.items():
            if len(self.positions) >= self.max_concurrent_positions: break
            if mint in self.positions: continue # Don't buy if already held
            
            if self.balance >= capital_per_buy:
                self.balance -= capital_per_buy
                current_price = self._get_price_for_mint(mint, observed_tokens)
                
                self.positions[mint] = {
                    'entry_price': current_price,
                    'size_sol': capital_per_buy,
                    'highest_price': current_price,
                    'timestamp': self.current_timestamp
                }
        return 0.0 # No immediate reward for buying

    def _update_portfolio(self):
        """Updates the total value of the portfolio based on current prices."""
        held_value = 0
        mints_to_update = list(self.positions.keys())
        for mint in mints_to_update:
            current_price = self._get_price_for_mint(mint)
            if current_price is None:
                # Token data not available at this timestamp, assume value dropped to 0
                self.balance += self.positions[mint]['size_sol'] # Salvage what was invested
                del self.positions[mint]
                continue

            position = self.positions[mint]
            position_value = position['size_sol'] * (current_price / position['entry_price'])
            
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            held_value += position_value
        
        self.portfolio_value = self.balance + held_value
        
    def _get_price_for_mint(self, mint: str, token_list: Optional[List[pd.Series]] = None) -> Optional[float]:
        """Finds the current price for a specific mint."""
        # First check the currently observed tokens for efficiency
        if token_list:
            for token_data in token_list:
                if token_data['mint'] == mint:
                    return token_data['Close']
        
        # If not in the observed list, check the whole data point for the timestamp
        current_df = self.current_data_point
        if isinstance(current_df, pd.Series) and current_df['mint'] == mint:
            return current_df['Close']
        if isinstance(current_df, pd.DataFrame) and not current_df[current_df['mint'] == mint].empty:
            return current_df[current_df['mint'] == mint]['Close'].iloc[0]

        return None # Token not present at this timestamp

    def _get_current_global_state(self, token_data: Optional[pd.Series] = None) -> Dict:
        """Gets the current state for a token for the reward function."""
        if token_data is None:
            return {'unrealized_pnl': 0, 'rugcheck_score': 1.0, 'socials_score': 1.0}

        unrealized_pnl = 0
        if token_data['mint'] in self.positions:
            pos = self.positions[token_data['mint']]
            unrealized_pnl = (token_data['Close'] - pos['entry_price']) / pos['entry_price']

        return {
            'unrealized_pnl': unrealized_pnl,
            'rugcheck_score': token_data['rugcheck_score'],
            'socials_score': token_data['socials_score']
        }
        
    def render(self, mode='human'):
        """Renders the environment's state."""
        print(f"Step: {self.current_step}, Timestamp: {self.current_timestamp}, "
              f"Portfolio Value: {self.portfolio_value:.4f} SOL, "
              f"Positions: {len(self.positions)}")