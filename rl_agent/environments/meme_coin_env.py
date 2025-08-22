# rl_agent/environments/meme_coin_env.py
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
from config.rl_config import get_active_features

# --- NEW: Stability constants ---
EPS = 1e-9  # Epsilon for safe division
MAX_STEPS_PER_EPISODE = 5000  # Ensures episodes finish, e.g., ~7 hours of 5s ticks
WARMUP_STEPS = 200 # Approx. 17 mins of 5s ticks to let indicators build up

class MemeCoinEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, data_manager: DataManager, rl_config: Dict[str, Any], silent: bool = False):
        super().__init__()
        self.data_manager = data_manager
        self.rl_config = rl_config
        self.reward_function = RewardFunction(self.rl_config)
        self.silent = silent # MODIFIED: Use the passed argument

        self.feature_columns = get_active_features(self.rl_config)
        
        # --- Load parameters from the config dictionary ---
        self.initial_balance = self.rl_config.get('ENV_INITIAL_BALANCE', 100.0)
        self.max_concurrent_positions = self.rl_config.get('ENV_MAX_CONCURRENT_POSITIONS', 5)
        self.num_top_tokens_to_observe = self.rl_config.get('ENV_NUM_TOP_TOKENS_TO_OBSERVE', 5)
        self.time_norm_seconds = self.rl_config.get('ENV_TIME_IN_POSITION_NORM_SECONDS', 14400.0)

        # Observation Space
        num_portfolio_features = 4
        num_base_token_features = len(self.feature_columns)
        num_position_features = 5
        total_token_features = num_base_token_features + num_position_features
        obs_space_size = num_portfolio_features + (self.num_top_tokens_to_observe * total_token_features)
        
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_space_size,), dtype=np.float32)
        
        # Action Space
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(self.num_top_tokens_to_observe,), dtype=np.float32)
        
        # Initialize state variables
        self.balance = self.initial_balance
        self.portfolio_value = self.initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.current_step = 0
        self.current_timestamp = None
        self.current_data_point = None
        self._steps = 0
        self._warmup_left = 0
        # --- NEW: Episode stats for logging ---
        self.episode_buys = 0
        self.episode_sells = 0

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.data_manager.reset()
        
        self.balance = self.initial_balance
        self.portfolio_value = self.initial_balance
        self.positions = {}
        self.current_step = 0
        self.reward_function.reset(self.initial_balance)
        self._steps = 0
        self._warmup_left = WARMUP_STEPS
        self.episode_buys = 0
        self.episode_sells = 0
        
        next_data = next(self.data_manager, None)
        if next_data is None: raise StopIteration("No data available in DataManager.")
        self.current_timestamp, self.current_data_point = next_data
        
        obs = self._get_observation()
        obs = np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6)
        obs = np.clip(obs, -10.0, 10.0)
        return obs, {}

    def _log_episode_end(self, reason: str):
        """Helper to log a summary when an episode finishes."""
        # MODIFICATION: Only log if not in silent mode
        if not self.silent:
            final_pnl = self.portfolio_value - self.initial_balance
            final_pnl_pct = (final_pnl / self.initial_balance) * 100
            logger.info(f"--- Episode End: {reason} ---")
            logger.info(f"Duration: {self._steps} steps ({self.current_timestamp})")
            logger.info(f"Final Portfolio: {self.portfolio_value:.2f} SOL (PnL: {final_pnl:.2f} SOL, {final_pnl_pct:.2f}%)")
            logger.info(f"Trades: {self.episode_buys} Buys, {self.episode_sells} Sells")
            logger.info("-" * (25 + len(reason)))


    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self._steps += 1

        if self._warmup_left > 0:
            self._warmup_left -= 1
            next_step_data = next(self.data_manager, None)
            terminated = next_step_data is None
            if not terminated:
                self.current_timestamp, self.current_data_point = next_step_data
                self._update_portfolio()
            else:
                self._log_episode_end("Data ended during warmup")
            
            obs = self._get_observation()
            return obs, 0.0, terminated, False, {}

        observed_tokens = self._get_top_tokens()
        self._execute_sells(action, observed_tokens)
        self._execute_buys(action, observed_tokens)

        next_step_data = next(self.data_manager, None)
        terminated = next_step_data is None
        truncated = self._steps >= MAX_STEPS_PER_EPISODE
        
        if not terminated:
            self.current_timestamp, self.current_data_point = next_step_data
            self.current_step += 1
        
        self._update_portfolio()
        
        if self.portfolio_value < (self.initial_balance * 0.5):
            terminated = True
            truncated = False
            self._log_episode_end("Bankrupted (portfolio < 50%)")

        if terminated and not truncated:
             self._log_episode_end("End of dataset reached")
        if truncated:
             self._log_episode_end("Max episode steps reached")

        reward = self.reward_function.calculate_reward({}, self._get_current_global_state(), self.portfolio_value)
        reward = float(np.nan_to_num(reward, nan=-1e-3, posinf=-1e-3, neginf=-1e-3))

        obs = self._get_observation()
        return obs, reward, terminated, truncated, {}

    def _get_top_tokens(self) -> List[pd.Series]:
        current_df = self.current_data_point
        if isinstance(current_df, pd.Series): current_df = current_df.to_frame().T
        if 'volume_usd' in current_df.columns:
            top_tokens = current_df.sort_values('volume_usd', ascending=False).head(self.num_top_tokens_to_observe)
            return [row for _, row in top_tokens.iterrows()]
        return []

    def _get_observation(self) -> np.ndarray:
        balance_norm = self.balance / max(self.portfolio_value, EPS)
        portfolio_value_norm = self.portfolio_value / max(self.initial_balance, EPS)
        num_positions_norm = len(self.positions) / self.max_concurrent_positions
        
        unrealized_pnl = sum(
            (self._get_price_for_mint(mint) - pos['entry_price']) * (pos['size_sol'] / max(pos['entry_price'], EPS))
            for mint, pos in self.positions.items() if self._get_price_for_mint(mint) is not None
        )
        unrealized_pnl_norm = unrealized_pnl / max(self.initial_balance, EPS)

        portfolio_features = np.array([balance_norm, portfolio_value_norm, num_positions_norm, unrealized_pnl_norm], dtype=np.float32)

        top_tokens = self._get_top_tokens()
        token_features_list = []
        num_base_token_features = len(self.feature_columns)
        num_position_features = 5
        
        for i in range(self.num_top_tokens_to_observe):
            if i < len(top_tokens):
                token_data = top_tokens[i]
                mint = token_data.get('mint', 'unknown')
                base_features = token_data[self.feature_columns].values.astype(np.float32)

                if mint in self.positions:
                    pos = self.positions[mint]
                    price = self._get_price_for_mint(mint)
                    time_in_pos = (self.current_timestamp - pos['timestamp']).total_seconds() if self.current_timestamp else 0
                    pnl_ratio = (price - pos['entry_price']) / max(pos['entry_price'], EPS) if price is not None else 0
                    highest_price_ratio = price / max(pos['highest_price'], EPS) if price is not None else 1.0

                    position_features = np.array([
                        1.0, 
                        pos['size_sol'] / max(self.portfolio_value, EPS),
                        pnl_ratio,
                        min(time_in_pos / self.time_norm_seconds, 1.0),
                        highest_price_ratio
                    ], dtype=np.float32)
                else:
                    position_features = np.zeros(num_position_features, dtype=np.float32)
                
                token_features_list.append(np.concatenate([base_features, position_features]))
            else:
                token_features_list.append(np.zeros(num_base_token_features + num_position_features, dtype=np.float32))
        
        obs = np.concatenate([portfolio_features] + token_features_list, axis=0).astype(np.float32)
        
        obs = np.nan_to_num(obs, nan=0.0, posinf=10.0, neginf=-10.0)
        obs = np.clip(obs, -10.0, 10.0)
        
        return obs

    def _execute_sells(self, action: np.ndarray, observed_tokens: List[pd.Series]):
        sell_threshold = self.rl_config.get('ENV_ACTION_SELL_THRESHOLD', -0.2)
        for i, token_data in enumerate(observed_tokens):
            mint = token_data.get('mint')
            if mint in self.positions and action[i] < sell_threshold:
                position = self.positions[mint]
                current_price = token_data.get('Close')
                if current_price is None: continue

                sell_value_sol = position['size_sol'] * (current_price / max(position['entry_price'], EPS))
                pnl = sell_value_sol - position['size_sol']
                self.balance += sell_value_sol
                del self.positions[mint]
                self.episode_sells += 1
                # MODIFICATION: Only log if not in silent mode
                if not self.silent:
                    logger.debug(f"SELL: {mint[:6]} at price {current_price:.6f}. PnL: {pnl:.4f} SOL. Balance: {self.balance:.2f} SOL.")


    def _execute_buys(self, action: np.ndarray, observed_tokens: List[pd.Series]):
        buy_threshold = self.rl_config.get('ENV_ACTION_BUY_THRESHOLD', 0.2)
        capital_pct = self.rl_config.get('ENV_CAPITAL_PER_BUY_PERCENT', 0.95)

        for i, token_data in enumerate(observed_tokens):
            mint = token_data.get('mint')
            if action[i] > buy_threshold and mint not in self.positions and len(self.positions) < self.max_concurrent_positions:
                available_slots = self.max_concurrent_positions - len(self.positions)
                capital_per_buy = (self.balance / available_slots) * capital_pct
                current_price = token_data.get('Close')
                if current_price is None or current_price <= 0: continue
                
                if self.balance >= capital_per_buy > 0:
                    self.balance -= capital_per_buy
                    self.positions[mint] = {
                        'entry_price': current_price,
                        'size_sol': capital_per_buy,
                        'highest_price': current_price,
                        'timestamp': self.current_timestamp
                    }
                    self.episode_buys += 1
                    # MODIFICATION: Only log if not in silent mode
                    if not self.silent:
                        logger.debug(f"BUY: {mint[:6]} for {capital_per_buy:.4f} SOL at price {current_price:.6f}. Balance: {self.balance:.2f} SOL.")

    def _update_portfolio(self):
        held_value = 0
        for mint, position in self.positions.items():
            current_price = self._get_price_for_mint(mint)
            if current_price is None:
                held_value += 0 
                continue

            position['highest_price'] = max(position['highest_price'], current_price)
            held_value += position['size_sol'] * (current_price / max(position['entry_price'], EPS))
        
        self.portfolio_value = self.balance + held_value
        
    def _get_price_for_mint(self, mint: str) -> Optional[float]:
        if self.current_data_point is None: return None
        if isinstance(self.current_data_point, pd.Series):
            return self.current_data_point['Close'] if self.current_data_point.get('mint') == mint else None
        
        token_row = self.current_data_point[self.current_data_point['mint'] == mint]
        return token_row['Close'].iloc[0] if not token_row.empty else None

    def _get_current_global_state(self) -> Dict:
        return {}
        
    def render(self, mode='human'):
        logger.info(f"Step: {self.current_step}, Timestamp: {self.current_timestamp}, "
              f"Portfolio Value: {self.portfolio_value:.4f} SOL, Positions: {len(self.positions)}")