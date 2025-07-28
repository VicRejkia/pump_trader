# FILE: rl_environment.py (Refactored for Portfolio Simulation)

"""
Custom Gymnasium Environment for training an RL agent to OPTIMIZE PARAMETERS
for a Solana Pump.fun Trading Bot.

This environment simulates the entire trading bot's portfolio management over a
historical period, rather than the lifecycle of a single token. At each step,
the agent provides a full set of trading parameters, and the environment
simulates the bot's core logic using those parameters against the market
data for that time interval.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import random
from typing import Dict, List, Optional, Tuple, Any

# --- Project Modules ---
from bot_logger import logger
import rl_config
from utils import calculate_trend_indicators # For simulation

class TradingEnv(gym.Env):
    """
    Custom Gymnasium Environment for Solana Pump Trading Simulation.

    Action Space (Continuous):
        A vector of tunable trading parameters (rl_config.RL_TUNABLE_PARAMETERS).

    Observation Space (Continuous):
        A fixed-size vector representing an aggregate view of the market state
        and the bot's overall portfolio status (rl_config.OBSERVATION_FEATURES).

    Reward:
        Primarily based on the realized PnL from simulated sell transactions.
        Includes shaping penalties for holding and for tokens dying while in portfolio.
    """
    metadata = {'render_modes': ['human']}

    def __init__(
        self,
        historical_data_dict: Dict[str, pd.DataFrame],
        token_lifespans: Dict[str, Dict[str, pd.Timestamp]],
        initial_capital: float = rl_config.RL_INITIAL_CAPITAL,
        max_steps: int = rl_config.MAX_STEPS_PER_EPISODE,
    ):
        super().__init__()

        if not historical_data_dict:
            raise ValueError("Historical data dictionary cannot be empty.")

        self.historical_data_dict = historical_data_dict
        self.token_lifespans = token_lifespans
        self.available_mints = list(self.historical_data_dict.keys())

        # Determine the simulation time range from the provided data
        self.min_ts = min(lifespan['start_ts'] for lifespan in token_lifespans.values())
        self.max_ts = max(lifespan['end_ts'] for lifespan in token_lifespans.values())
        self.simulation_step_interval = pd.Timedelta(seconds=5) # Matches data frequency

        self.initial_capital = initial_capital
        self._max_episode_steps = max_steps

        # --- Define Action and Observation Spaces from rl_config ---
        self.action_space = spaces.Box(
            low=rl_config.ACTION_LOW, high=rl_config.ACTION_HIGH,
            shape=(rl_config.ACTION_SPACE_DIM,), dtype=np.float32
        )
        self.observation_space = spaces.Box(
            low=rl_config.OBSERVATION_LOW, high=rl_config.OBSERVATION_HIGH,
            shape=(rl_config.OBSERVATION_SPACE_DIM,), dtype=np.float32
        )

        # --- Initialize Simulation State ---
        self.current_step: int = 0
        self.current_time: pd.Timestamp = self.min_ts
        self.sol_balance: float = self.initial_capital
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {}
        self.realized_pnl_since_last_step: float = 0.0

        logger.info(
            f"TradingEnv (Portfolio Sim) initialized. "
            f"Obs dim: {rl_config.OBSERVATION_SPACE_DIM}, "
            f"Action dim: {rl_config.ACTION_SPACE_DIM}, "
            f"Simulating {len(self.available_mints)} tokens."
        )

    def _apply_action(self, action: np.ndarray):
        """Maps the agent's action vector to the bot's configuration."""
        self.current_parameters = {}
        clipped_action = np.clip(action, rl_config.ACTION_LOW, rl_config.ACTION_HIGH)
        for i, param_config in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            param_name, _, _, p_type = param_config
            val = clipped_action[i]
            if param_name == "USE_TREND_REVERSAL_CONFIRMATION":
                self.current_parameters[param_name.upper()] = bool(val > 0.5)
            else:
                final_val = p_type(np.round(val)) if p_type == int else float(val)
                self.current_parameters[param_name.upper()] = final_val

    def _get_observation(self) -> np.ndarray:
        """
        Constructs the aggregate observation vector for the current state.
        """
        # Initialize observation map with default zero values
        obs_map = {feat: 0.0 for feat in rl_config.OBSERVATION_FEATURES}
        params = self.current_parameters

        # --- Portfolio State ---
        obs_map['sol_balance_norm'] = self.sol_balance
        obs_map['num_active_positions'] = len(self.active_positions)

        total_unrealized_pnl = 0.0
        total_holding_time = 0.0
        portfolio_holdings_value = 0.0

        if self.active_positions:
            for mint, pos in self.active_positions.items():
                # Get current price for PnL calculation
                market_data = self._get_market_data_at_time(mint, self.current_time)
                current_price = market_data.get('Close', pos['buy_price'])

                # Unrealized PnL
                current_value = current_price * pos['remaining_tokens']
                cost_basis = pos['total_investment_sol'] * (pos['remaining_tokens'] / pos['initial_tokens'])
                total_unrealized_pnl += current_value - cost_basis
                portfolio_holdings_value += current_value

                # Holding Time
                total_holding_time += (self.current_time - pos['entry_timestamp']).total_seconds()

            obs_map['portfolio_pnl_unrealized_total'] = total_unrealized_pnl
            obs_map['avg_time_holding_norm'] = total_holding_time / len(self.active_positions)

        obs_map['portfolio_value_norm'] = self.sol_balance + portfolio_holdings_value

        # --- Aggregate Market Features ---
        active_market_tokens_data = []
        for mint in self.available_mints:
            if self.token_lifespans[mint]['start_ts'] <= self.current_time <= self.token_lifespans[mint]['end_ts']:
                market_data = self._get_market_data_at_time(mint, self.current_time)
                if market_data:
                    active_market_tokens_data.append(market_data)

        if active_market_tokens_data:
            obs_map['market_volatility_avg'] = np.mean([d.get('volatility', 0) for d in active_market_tokens_data])
            obs_map['market_volume_sol_avg'] = np.mean([d.get('Volume', 0) for d in active_market_tokens_data])
            obs_map['active_tokens_rug_score_avg'] = np.mean([d.get('rugcheck_score', 10000) for d in active_market_tokens_data])
            obs_map['active_tokens_social_score_avg'] = np.mean([d.get('socials_score', 100) for d in active_market_tokens_data])

        one_hour_ago = self.current_time - pd.Timedelta(hours=1)
        obs_map['new_tokens_last_hour'] = sum(
            1 for m in self.available_mints if one_hour_ago < self.token_lifespans[m]['start_ts'] <= self.current_time
        )

        # --- Time Features ---
        obs_map['weekday'] = float(self.current_time.weekday())
        obs_map['daytime'] = float(self.current_time.hour)

        # Assemble final vector in correct order
        obs_vector = np.array([obs_map[feat] for feat in rl_config.OBSERVATION_FEATURES], dtype=np.float32)
        if not np.all(np.isfinite(obs_vector)):
            return np.zeros_like(obs_vector) # Return zeros if any value is invalid
        return obs_vector

    def _get_market_data_at_time(self, mint: str, timestamp: pd.Timestamp) -> Optional[Dict[str, Any]]:
        """Efficiently retrieves a single row of market data for a mint at a specific time."""
        df = self.historical_data_dict.get(mint)
        if df is None or df.empty:
            return None
        try:
            # Use asof for efficient point-in-time lookup
            row = df.asof(timestamp)
            if pd.isna(row.name): # asof returns all NaNs if no data is available at or before timestamp
                return None
            return row.to_dict()
        except KeyError:
            return None # Timestamp is before the start of the dataframe

    def _simulate_trading_logic(self):
        """
        Simulates one time step of the TradingManager's buy and sell logic
        using the parameters provided by the agent.
        """
        self.realized_pnl_since_last_step = 0.0
        death_penalty_this_step = 0.0
        params = self.current_parameters

        # --- 1. Simulate Sell Logic for Active Positions ---
        positions_to_close = []
        for mint, pos in list(self.active_positions.items()):
            market_data = self._get_market_data_at_time(mint, self.current_time)
            
            # Check for token death
            if not market_data or self.current_time >= self.token_lifespans[mint]['end_ts']:
                death_penalty_this_step += rl_config.REWARD_DEATH_PENALTY
                positions_to_close.append(mint)
                continue

            current_price = market_data.get('Close', 0.0)
            high_price = market_data.get('High', 0.0)
            
            # Update highest price for trailing stop loss
            pos['highest_price'] = max(pos.get('highest_price', current_price), high_price)

            # Simplified sell logic matching trading_logic.py
            sell_reason = None
            if current_price <= pos['stop_loss_price']:
                sell_reason = "Stop Loss" if not pos['first_tp_hit'] else "Breakeven SL"
            elif current_price >= pos['second_tp_price']:
                sell_reason = "Second TP"
            elif not pos['first_tp_hit'] and current_price >= pos['initial_tp_price']:
                sell_reason = "First TP"
            elif pos['first_tp_hit']:
                trailing_sl_price = pos['highest_price'] * (1.0 - params.get('TRAILING_STOP_LOSS_PERCENT', 15.0) / 100.0)
                if current_price <= trailing_sl_price:
                    sell_reason = "Trailing SL"
            
            if sell_reason:
                # Execute simulated sell
                tokens_to_sell = pos['remaining_tokens']
                if sell_reason == "First TP":
                    tokens_to_sell = min(pos['initial_tokens'] * (params.get('FIRST_SELL_PERCENT', 50.0) / 100.0), pos['remaining_tokens'])
                
                if tokens_to_sell > 1e-9:
                    net_sol_received = tokens_to_sell * current_price # Simplified fees
                    cost_basis = pos['total_investment_sol'] * (tokens_to_sell / pos['initial_tokens'])
                    pnl = net_sol_received - cost_basis
                    self.realized_pnl_since_last_step += pnl
                    self.sol_balance += net_sol_received
                    
                    pos['remaining_tokens'] -= tokens_to_sell
                    self.trade_history.append({'time': self.current_time, 'type': 'sell', 'pnl': pnl})
                    
                    if sell_reason == "First TP":
                        pos['first_tp_hit'] = True
                        pos['stop_loss_price'] = pos['buy_price'] # Breakeven

                    if pos['remaining_tokens'] < 1e-9:
                        positions_to_close.append(mint)

        for mint in positions_to_close:
            del self.active_positions[mint]

        # --- 2. Simulate Buy Logic for All Available Tokens ---
        sol_to_buy = params.get('SOL_TO_BUY', 0.5)
        if self.sol_balance > sol_to_buy:
            for mint in self.available_mints:
                if mint not in self.active_positions and self.token_lifespans[mint]['start_ts'] <= self.current_time < self.token_lifespans[mint]['end_ts']:
                    market_data = self._get_market_data_at_time(mint, self.current_time)
                    if not market_data: continue

                    # Simplified buy criteria matching trading_logic.py
                    meets_criteria = (
                        market_data.get('Volume', 0) * 170 > params.get('DEFAULT_VOLUME_THRESHOLD', 40000) and # Simplified USD conversion
                        market_data.get('marketCapSol', 0) * 170 > params.get('DEFAULT_MARKETCAP_THRESHOLD', 20000) and
                        market_data.get('rugcheck_score', 10000) < params.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 401) and
                        market_data.get('socials_score', 100) < params.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100) and
                        market_data.get('volatility', 0) >= params.get('MIN_VOLATILITY', 0.18)
                    )

                    if meets_criteria:
                        buy_price = market_data.get('Close')
                        if buy_price and buy_price > 1e-12:
                            total_investment = sol_to_buy
                            tokens_bought = total_investment / buy_price
                            self.sol_balance -= total_investment

                            sl_price = buy_price * (1.0 - params.get('INITIAL_STOP_LOSS_PERCENT', 40.0) / 100.0)
                            tp1_price = buy_price * (1.0 + params.get('FIRST_SELL_PROFIT_MARGIN', 70.0) / 100.0)
                            tp2_price = buy_price * (1.0 + params.get('SECOND_TAKE_PROFIT_PERCENT', 450.0) / 100.0)
                            
                            self.active_positions[mint] = {
                                'buy_price': buy_price,
                                'initial_tokens': tokens_bought,
                                'remaining_tokens': tokens_bought,
                                'total_investment_sol': total_investment,
                                'stop_loss_price': sl_price,
                                'initial_tp_price': tp1_price,
                                'second_tp_price': tp2_price,
                                'highest_price': buy_price,
                                'first_tp_hit': False,
                                'entry_timestamp': self.current_time
                            }
                            self.trade_history.append({'time': self.current_time, 'type': 'buy'})
                            # Stop after one buy per step to be conservative
                            break

        return death_penalty_this_step

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        self._apply_action(action)
        death_penalty = self._simulate_trading_logic()

        # Calculate reward
        reward = (self.realized_pnl_since_last_step * rl_config.REWARD_PNL_MULTIPLIER) + death_penalty
        reward += len(self.active_positions) * rl_config.REWARD_HOLDING_PENALTY

        # Update time and step count
        self.current_step += 1
        self.current_time += self.simulation_step_interval

        # Check for termination/truncation
        terminated = self.sol_balance <= 0
        max_steps_reached = self.current_step >= self._max_episode_steps
        end_of_data = self.current_time >= self.max_ts
        truncated = max_steps_reached or end_of_data

        observation = self._get_observation()
        info = {'sol_balance': self.sol_balance, 'pnl_step': self.realized_pnl_since_last_step}
        if truncated or terminated:
            info['final_portfolio_value'] = self.sol_balance # Can be improved to include holdings value

        return observation, reward, terminated, truncated, info

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)

        self.current_step = 0
        self.current_time = self.min_ts
        self.sol_balance = self.initial_capital
        self.active_positions = {}
        self.trade_history = []
        self.current_parameters = {}
        self.realized_pnl_since_last_step = 0.0
        
        # Apply a random action to initialize parameters for the first observation
        self._apply_action(self.action_space.sample())

        return self._get_observation(), {}

    def render(self, mode='human'):
        if mode == 'human':
            pnl_total = sum(t.get('pnl', 0) for t in self.trade_history if t['type'] == 'sell')
            print(
                f"Step: {self.current_step}/{self._max_episode_steps} | "
                f"Time: {self.current_time.strftime('%Y-%m-%d %H:%M')} | "
                f"SOL: {self.sol_balance:.2f} | "
                f"Positions: {len(self.active_positions)} | "
                f"Total PnL: {pnl_total:.2f}"
            )

    def close(self):
        pass