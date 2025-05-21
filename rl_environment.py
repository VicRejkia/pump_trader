# FILE: rl_environment.py (OHLCV Adapted & Refinements)

"""
Custom Gymnasium Environment for Training a Solana Pump.fun Trading Bot RL Agent.

This environment simulates the trading process based on historical OHLCV data, including
handling for token death and applying appropriate rewards/penalties.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import random
from collections import deque
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import timezone, datetime

# --- Project Modules ---
from logger import logger
import rl_config # Import RL specific configurations
from utils import calculate_volatility # Keep utility for potential recalculation

# --- Environment Class ---

class TradingEnv(gym.Env):
    """
    Custom Gymnasium Environment for Solana Pump Trading Simulation using OHLCV data.

    Action Space (Continuous):
        Box space representing tunable trading parameters (rl_config.RL_TUNABLE_PARAMETERS).

    Observation Space (Continuous):
        Box space representing market state and portfolio status from OHLCV data, normalized
        (rl_config.OBSERVATION_FEATURES).

    Reward:
        Combination of realized PnL, shaping rewards/penalties, and death penalty.
    """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}

    def __init__(
        self,
        historical_data_dict: Dict[str, pd.DataFrame], # Expects OHLCV data per mint
        token_lifespans: Dict[str, Dict[str, datetime]],
        initial_capital: float = rl_config.RL_INITIAL_CAPITAL,
        max_steps: int = rl_config.MAX_STEPS_PER_EPISODE
    ):
        """
        Initializes the Trading Environment with OHLCV data.

        Args:
            historical_data_dict: Dictionary mapping mints to their historical 5s OHLCV DataFrames.
                                  Indices MUST be timezone-aware UTC DatetimeIndex.
                                  Expected columns: 'Open', 'High', 'Low', 'Close', 'Volume',
                                                    'market_cap_calculated', 'rugcheck_score', 'socials_score',
                                                    'token_creation_time'.
                                  Note: Assumes a fixed step interval (e.g., 5 seconds) based on data frequency.
            token_lifespans: Dictionary mapping mints to their {'start_ts', 'end_ts'} (UTC).
            initial_capital: Starting SOL balance for each episode.
            max_steps: Maximum number of steps allowed per episode (truncation).
        """
        super().__init__()

        if not historical_data_dict:
            raise ValueError("Historical OHLCV data dictionary cannot be empty.")
        if not token_lifespans:
             raise ValueError("Token lifespans dictionary cannot be empty.")

        # --- Validate and Store OHLCV Data ---
        self.historical_data_dict = {}
        self.token_lifespans = {}
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'market_cap_calculated', 'rugcheck_score', 'socials_score', 'token_creation_time']

        for mint, df in historical_data_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty and isinstance(df.index, pd.DatetimeIndex):
                 if df.index.tz is None or str(df.index.tz).upper() != 'UTC':
                     logger.error(f"DataFrame index for mint {mint} is not timezone-aware UTC! Skipping.")
                     continue
                 if mint not in token_lifespans:
                      logger.warning(f"Lifespan info missing for mint {mint}. Skipping.")
                      continue

                 # Check for required OHLCV columns
                 missing_cols = [col for col in required_cols if col not in df.columns]
                 if missing_cols:
                     logger.error(f"Missing required OHLCV columns in data for mint {mint}: {missing_cols}. Skipping.")
                     continue

                 # Basic NaN check (more thorough checks happen in _get_observation)
                 if df[required_cols].isnull().values.any():
                      logger.warning(f"NaN values found in required columns for mint {mint}. Will attempt fill/clip later.")
                      # Consider attempting to fill NaNs here if preferred

                 self.historical_data_dict[mint] = df
                 self.token_lifespans[mint] = token_lifespans[mint]
            else:
                 logger.warning(f"Skipping invalid/empty DataFrame for mint: {mint}")

        self.available_mints = list(self.historical_data_dict.keys())
        if not self.available_mints:
            raise ValueError("No valid OHLCV DataFrames found after validation.")

        self.initial_capital = initial_capital
        self._max_episode_steps = max_steps

        # --- Define Action Space (Same as before) ---
        self.action_space = spaces.Box(
            low=rl_config.ACTION_LOW,
            high=rl_config.ACTION_HIGH,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        self._action_param_names = [p[0] for p in rl_config.RL_TUNABLE_PARAMETERS]

        # --- Define Observation Space (Same as before) ---
        self.observation_space = spaces.Box(
            low=rl_config.OBSERVATION_LOW,
            high=rl_config.OBSERVATION_HIGH,
            shape=(rl_config.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        # --- Internal State Variables (Same as before) ---
        self.current_step: int = 0
        self.current_sol: float = 0.0
        self.current_data_df: Optional[pd.DataFrame] = None
        self.current_mint: Optional[str] = None
        self.current_token_end_ts: Optional[datetime] = None
        self.active_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {}
        self.last_observation: np.ndarray = np.zeros(self.observation_space.shape, dtype=np.float32)
        # Use 'Close' price for history
        self._price_history: deque = deque(maxlen=rl_config.OBSERVATION_PRICE_HISTORY_LENGTH)
        self._previous_unrealized_pnl: float = 0.0
        self._last_step_processed_index = -1

        logger.info(f"TradingEnv (OHLCV) initialized. Observation space dim: {rl_config.OBSERVATION_SPACE_DIM}, Action space dim: {rl_config.ACTION_SPACE_DIM}")

    def _get_observation(self) -> np.ndarray:
        """
        Calculates and returns the raw observation vector using OHLCV data.
        Normalization is handled by the VecNormalize wrapper.
        """
        default_obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        if self.current_data_df is None or self._last_step_processed_index < 0 or self._last_step_processed_index >= len(self.current_data_df):
            return default_obs

        try:
            current_row = self.current_data_df.iloc[self._last_step_processed_index]
            current_timestamp = self.current_data_df.index[self._last_step_processed_index]
        except IndexError:
            logger.warning(f"IndexError getting observation at index {self._last_step_processed_index} (Step {self.current_step}) for mint {self.current_mint}. Returning zeros.")
            return default_obs

        # --- Update Price History (using Close price) ---
        current_price = current_row.get('Close', 0.0)
        if pd.notna(current_price) and isinstance(current_price, (int, float)):
            self._price_history.append(float(current_price))
        else:
            last_valid_price = self._price_history[-1] if self._price_history else 0.0
            self._price_history.append(last_valid_price) # Use last valid if current is NaN

        # --- Extract Base Features from OHLCV row ---
        try:
            market_cap_sol = float(current_row.get('market_cap_calculated', 0.0))
            volume = float(current_row.get('Volume', 0.0)) # Use 'Volume' column
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            creation_time_ts = current_row.get('token_creation_time', pd.NaT)
            # Use pre-calculated volatility if available, otherwise default to 0
            volatility = float(current_row.get('volatility', 0.0))
            if pd.isna(volatility): volatility = 0.0

            # Fill potential NaNs extracted (should ideally be handled in __init__ or data loading)
            market_cap_sol = 0.0 if pd.isna(market_cap_sol) else market_cap_sol
            volume = 0.0 if pd.isna(volume) else volume
            rugcheck_score = 10000 if pd.isna(rugcheck_score) else int(rugcheck_score)
            socials_score = 100 if pd.isna(socials_score) else int(socials_score)

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error accessing/converting OHLCV features at index {self._last_step_processed_index} for mint {self.current_mint}: {e}", exc_info=True)
            return default_obs

        # --- Calculate Derived Features (using Close price history) ---
        prices = np.array(self._price_history, dtype=np.float32)
        safe_prices = prices[prices > 1e-12]
        price_change_1 = np.log(safe_prices[-1] / safe_prices[-2]) if len(safe_prices) >= 2 else 0.0
        price_change_5 = np.log(safe_prices[-1] / safe_prices[-6]) if len(safe_prices) >= 6 else 0.0
        price_change_10 = np.log(safe_prices[-1] / safe_prices[-11]) if len(safe_prices) >= 11 else 0.0

        time_since_creation_seconds = 0.0
        if pd.notna(creation_time_ts) and isinstance(current_timestamp, pd.Timestamp):
            # Ensure creation_time_ts is timezone-aware for correct calculation
            if creation_time_ts.tzinfo is None: creation_time_ts = creation_time_ts.tz_localize('UTC')
            time_diff = current_timestamp - creation_time_ts
            time_since_creation_seconds = max(0.0, time_diff.total_seconds())

        is_holding = 1.0 if self.active_position else 0.0
        position_pnl_current_unrealized = 0.0
        time_holding_seconds = 0
        if self.active_position:
            buy_price = self.active_position['buy_price']
            rem_tokens = self.active_position['remaining_tokens']
            total_investment = self.active_position.get('total_investment_sol', 1.0)
            last_price = prices[-1] if prices.size > 0 else buy_price # Use last Close price
            current_value = last_price * rem_tokens
            initial_tokens = self.active_position.get('initial_tokens', rem_tokens)
            cost_fraction = rem_tokens / initial_tokens if initial_tokens > 0 else 1.0
            cost_basis_remaining = total_investment * cost_fraction
            position_pnl_current_unrealized = current_value - cost_basis_remaining
            entry_timestamp = self.active_position.get('entry_timestamp')
            if entry_timestamp:
                time_holding_seconds = max(0.0, (current_timestamp - entry_timestamp).total_seconds())

        # --- Calculate Time Features ---
        # Weekday: Monday=0, Sunday=6.
        weekday = float(current_timestamp.weekday())

        # Daytime: Hour of the day (0-23).
        hour = float(current_timestamp.hour)

        # --- Include Tunable Parameters ---
        tunable_params_values = []
        for param_name, _, _, p_type in rl_config.RL_TUNABLE_PARAMETERS:
             # Get current value from environment's parameters, use midpoint if not set
            # Find the index of the current parameter in RL_TUNABLE_PARAMETERS
            try:
                param_index = [j for j, p in enumerate(rl_config.RL_TUNABLE_PARAMETERS) if p[0] == param_name][0]
                current_val = self.current_parameters.get(param_name, (rl_config.ACTION_LOW[param_index] + rl_config.ACTION_HIGH[param_index]) / 2.0)
            except IndexError:
                logger.error(f"Parameter '{param_name}' not found in RL_TUNABLE_PARAMETERS. Cannot get default value.")
                current_val = 0.0 # Default to 0.0 or handle appropriately
            if p_type == int:
                 tunable_params_values.append(float(int(current_val)))
            else:
                 tunable_params_values.append(float(current_val))


        # --- Construct Raw Observation Vector (Order MUST match rl_config.OBSERVATION_FEATURES) ---
        observation_list = [
            price_change_1, price_change_5, price_change_10,
            volatility, market_cap_sol, volume,
            float(rugcheck_score), float(socials_score), time_since_creation_seconds,
            is_holding, position_pnl_current_unrealized, time_holding_seconds, self.current_sol,
            weekday, hour # Add raw time features
        ]
        # Add raw tunable parameters
        observation = np.array(observation_list, dtype=np.float32)

        # --- Final Validation ---
        if not np.all(np.isfinite(observation)):
            logger.warning(f"NaN/inf in raw OHLCV observation @ Index {self._last_step_processed_index}, Mint {self.current_mint}. Replacing with zeros. Raw Obs: {observation}")
            observation = default_obs
        elif observation.shape != self.observation_space.shape:
            logger.error(f"Raw OHLCV Observation shape mismatch! Expected {self.observation_space.shape}, got {observation.shape}. Returning zeros.")
            observation = default_obs

        self.last_observation = observation # Store raw observation
        self._previous_unrealized_pnl = position_pnl_current_unrealized
        return observation

    def _apply_action(self, action: np.ndarray):
        """Applies the agent's action."""
        new_params = {}
        clipped_action = np.clip(action, rl_config.ACTION_LOW, rl_config.ACTION_HIGH)
        for i, param_config in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            param_name, _, _, p_type = param_config
            val = clipped_action[i]
            new_params[param_name] = p_type(np.round(val)) if p_type == int else float(val)
        self.current_parameters = new_params

    def _run_trading_logic_step(self) -> Tuple[float, float]:
        """
        Simulates one step of the trading logic using OHLCV data.
        Returns realized PnL and any shaping bonuses/penalties for the step.
        """
        realized_pnl_this_step = 0.0
        reward_bonus_penalty = 0.0

        current_data_index = self.current_step
        if self.current_data_df is None or current_data_index >= len(self.current_data_df):
            logger.warning(f"Attempted to run trading logic at invalid step index {current_data_index}.")
            self._last_step_processed_index = -1
            return realized_pnl_this_step, reward_bonus_penalty

        self._last_step_processed_index = current_data_index

        try:
            current_row = self.current_data_df.iloc[current_data_index]
            current_timestamp = self.current_data_df.index[self._last_step_processed_index]
            # Use OHLCV columns
            price = float(current_row.get('Close', 0.0))
            volume = float(current_row.get('Volume', 0.0))
            high_price = float(current_row.get('High', 0.0))
            # ---
            market_cap_sol = float(current_row.get('market_cap_calculated', 0.0))

            if price <= 1e-12:
                return realized_pnl_this_step, reward_bonus_penalty

            # --- Get parameters (Agent's or Defaults) ---
            agent_params = self.current_parameters
            if not agent_params:
                agent_params = {p[0]: (p[1] + p[2]) / 2 for p in rl_config.RL_TUNABLE_PARAMETERS}

            initial_sl_percent = agent_params.get('INITIAL_STOP_LOSS_PERCENT', 50.0)
            first_sell_perc = agent_params.get('FIRST_SELL_PERCENT', 75.0) / 100.0
            trailing_sl_percent = agent_params.get('TRAILING_STOP_LOSS_PERCENT', 50.0)
            first_profit_margin = agent_params.get('FIRST_SELL_PROFIT_MARGIN', 100.0) / 100.0
            volume_thresh = agent_params.get('DEFAULT_VOLUME_THRESHOLD', 5000)
            mcap_thresh_buy = agent_params.get('DEFAULT_MARKETCAP_THRESHOLD', 10000)
            rug_thresh = agent_params.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 1000)
            social_thresh = agent_params.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100)
            volatility_thresh = agent_params.get('MIN_VOLATILITY', 0.0)
            buy_amount_sol = agent_params.get('SOL_TO_BUY', 0.1)
            second_tp_margin = agent_params.get('SECOND_TAKE_PROFIT_PERCENT', 550.0) / 100.0

            # Fixed simulation parameters (matching rl_config defaults)
            buy_fee = rl_config.DEFAULT_BUY_FEE
            buy_tip = rl_config.DEFAULT_BUY_TIP
            sell_fee = rl_config.DEFAULT_SELL_FEE
            sell_tip = rl_config.DEFAULT_SELL_TIP
            min_mcap_sell_usd = rl_config.MIN_MARKET_CAP # Use the uncommented value

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error getting data/params in trading logic at index {current_data_index}: {e}", exc_info=True)
            return realized_pnl_this_step, reward_bonus_penalty

        # --- Sell Logic (using Close price for checks, High for highest_price) ---
        if self.active_position:
            pos = self.active_position
            # Update highest price using the High of the current candle
            hp = max(pos['highest_price'], high_price)
            pos['highest_price'] = hp

            current_stop_loss_price = pos['stop_loss_price']
            initial_tp_price = pos['initial_tp_price']
            second_tp_price = pos['second_tp_price']
            first_tp_hit = pos['first_tp_hit']

            current_trailing_sl_price = 0.0
            if first_tp_hit: # Trailing SL is active only AFTER first TP
                current_trailing_sl_price = hp * (1.0 - trailing_sl_percent / 100.0)

            sell_reason = None
            sell_all = False; sell_partial = False
            sell_percentage = 0.0

            # Order of checks: SL > Second TP > First TP > Trailing SL > MCap SL (Matching trading_logic.py)
            if price <= current_stop_loss_price:
                sell_reason = "Stop Loss" if not first_tp_hit else "Breakeven SL"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif price >= second_tp_price:
                sell_reason = "Second TP"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif not first_tp_hit and price >= initial_tp_price:
                sell_reason = "First TP"; sell_partial = True; sell_percentage = first_sell_perc
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif first_tp_hit and price <= current_trailing_sl_price: # Trailing SL checked only if first TP hit
                sell_reason = "Trailing SL"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            # Emergency SL (MCap) - Added to match trading_logic.py
            elif market_cap_sol > 0 and (market_cap_sol * (self.current_sol / self.initial_capital)) < min_mcap_sell_usd: # Approximate USD MCap
                 sell_reason = "Emergency SL (MCap)"; sell_all = True; sell_percentage = 1.0
                 reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY


            if sell_reason:
                initial_tokens = pos['initial_tokens']
                remaining_tokens = pos['remaining_tokens']
                total_investment = pos['total_investment_sol']
                tokens_to_sell = 0.0

                if sell_partial:
                    tokens_to_sell = initial_tokens * sell_percentage
                    tokens_to_sell = min(tokens_to_sell, remaining_tokens)
                elif sell_all:
                    tokens_to_sell = remaining_tokens

                if tokens_to_sell > 1e-9:
                    # Execute sell using Close price
                    gross_sol = tokens_to_sell * price
                    net_sol = gross_sol - sell_fee - sell_tip
                    cost_basis = total_investment * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                    pnl = net_sol - cost_basis
                    realized_pnl_this_step += pnl

                    self.current_sol += net_sol
                    pos['remaining_tokens'] -= tokens_to_sell
                    self.trade_history.append({
                        'step': self.current_step, 'index': current_data_index, 'type': 'sell', 'price': price,
                        'tokens': tokens_to_sell, 'net_sol': net_sol, 'pnl': pnl, 'reason': sell_reason
                    })

                    if sell_partial:
                        pos['first_tp_hit'] = True
                        # In trading_logic.py, SL is adjusted to buy_price after TP1. Replicate this.
                        pos['stop_loss_price'] = pos['buy_price']

                    if pos['remaining_tokens'] < 1e-9:
                        self.active_position = None

        # --- Buy Logic (using OHLCV Volume) ---
        # The environment decides *when* a token is available (based on data).
        # The agent's parameters determine *if* the bot buys when presented with an opportunity.
        # The buy criteria here should match the thresholds used in trading_logic.py's find_trading_opportunities.
        if not self.active_position and self.current_sol >= (buy_amount_sol + buy_fee + buy_tip):
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            volatility = float(current_row.get('volatility', 0.0))

            meets_buy_criteria = (
                volume >= volume_thresh and # Use OHLCV Volume
                market_cap_sol >= mcap_thresh_buy and
                rugcheck_score < rug_thresh and
                socials_score < social_thresh and
                volatility >= volatility_thresh
            )

            # logger.debug(f"Buy criteria: Volume {volume} >= {volume_thresh}, Market Cap {market_cap_sol} >= {mcap_thresh_buy}, "
            #              f"RugCheck {rugcheck_score} < {rug_thresh}, Socials {socials_score} < {social_thresh}, "
            #              f"Volatility {volatility} >= {volatility_thresh}")

            if meets_buy_criteria:
                total_investment = buy_amount_sol + buy_fee + buy_tip
                tokens_bought = buy_amount_sol / price if price > 0 else 0

                if tokens_bought > 0:
                    self.current_sol -= total_investment

                    # Calculate initial SL/TPs using agent's CURRENT parameters and Close price
                    initial_sl_price = price * (1.0 - initial_sl_percent / 100.0)

                    # First Take Profit (TP1) Price Calculation (Net Income Approach - Matching trading_logic.py)
                    sell_fee_tp1 = float(rl_config.DEFAULT_SELL_FEE)
                    sell_tip_tp1 = float(rl_config.DEFAULT_SELL_TIP)
                    fees_for_tp1_sell = sell_fee_tp1 + sell_tip_tp1

                    profit_margin_tp1_fraction = float(agent_params.get('FIRST_SELL_PROFIT_MARGIN', 100.0)) / 100.0 # Use agent's param
                    sell_percent_tp1_fraction = float(agent_params.get('FIRST_SELL_PERCENT', 75.0)) / 100.0 # Use agent's param

                    tokens_to_sell_tp1 = tokens_bought * sell_percent_tp1_fraction
                    if tokens_to_sell_tp1 <= 1e-9:
                         # This case should ideally not happen if tokens_bought > 0 and sell_percent_tp1_fraction > 0
                         # but handle defensively.
                         initial_tp_price = float('inf') # Set TP1 very high if sell amount is negligible
                         logger.warning(f"Calculated tokens to sell at TP1 ({tokens_to_sell_tp1}) is negligible for mint {self.current_mint}. Setting TP1 price to infinity.")
                    else:
                        # Cost basis of the portion of tokens sold at TP1
                        cost_of_tp1_tokens_sold = total_investment * sell_percent_tp1_fraction
                        # Desired profit on this portion
                        desired_profit_on_tp1_tokens = cost_of_tp1_tokens_sold * profit_margin_tp1_fraction
                        # Total SOL needed from the gross sale at TP1 price
                        gross_sol_needed_from_tp1_sale = cost_of_tp1_tokens_sold + desired_profit_on_tp1_tokens + fees_for_tp1_sell
                        # TP1 Price calculation
                        initial_tp_price = gross_sol_needed_from_tp1_sale / tokens_to_sell_tp1


                    # Second Take Profit Price Calculation (Matching trading_logic.py)
                    second_tp_price = price * (1 + float(agent_params.get('SECOND_TAKE_PROFIT_PERCENT', 550.0)) / 100.0) # Use agent's param


                    self.active_position = {
                        'buy_price': price, 'initial_tokens': tokens_bought,
                        'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment,
                        'stop_loss_price': initial_sl_price, 'initial_tp_price': initial_tp_price,
                        'second_tp_price': second_tp_price, 'highest_price': price, # Use Close price as initial high
                        'first_tp_hit': False, 'entry_step': self.current_step,
                        'entry_timestamp': current_timestamp
                    }
                    self.trade_history.append({
                        'step': self.current_step, 'index': current_data_index, 'type': 'buy', 'price': price,
                        'tokens': tokens_bought, 'investment': total_investment
                    })

        return realized_pnl_this_step, reward_bonus_penalty

    def _calculate_reward(self, realized_pnl: float, bonus_penalty: float, is_token_death: bool) -> float:
        """Calculates reward (Same as before, includes death penalty)."""
        reward = realized_pnl * rl_config.REWARD_PNL_MULTIPLIER
        reward += bonus_penalty
        if self.active_position and rl_config.REWARD_HOLDING_PENALTY != 0:
            reward += rl_config.REWARD_HOLDING_PENALTY
        if is_token_death and self.active_position:
            reward += rl_config.REWARD_DEATH_PENALTY
            # logger.debug(f"Applied death penalty ({rl_config.REWARD_DEATH_PENALTY}) for holding {self.current_mint} at end.")
        return reward

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Executes one time step (Same logic as before, relies on updated internal methods)."""
        if self.current_data_df is None:
            logger.error("Environment not reset properly, cannot step.")
            obs = np.zeros(self.observation_space.shape, dtype=np.float32)
            return obs, 0.0, True, False, {"error": "Environment not reset"}

        self._apply_action(action)
        realized_pnl, bonus_penalty = self._run_trading_logic_step()
        self.current_step += 1

        terminated = self.current_sol <= 0
        end_of_data = self._last_step_processed_index >= len(self.current_data_df) - 1
        token_died = False
        if self.current_token_end_ts and self._last_step_processed_index >=0 :
             current_timestamp = self.current_data_df.index[self._last_step_processed_index]
             token_died = current_timestamp >= self.current_token_end_ts

        max_steps_reached = self.current_step >= self._max_episode_steps
        truncated = max_steps_reached or end_of_data or token_died
        is_token_death_event = end_of_data or token_died

        reward = self._calculate_reward(realized_pnl, bonus_penalty, is_token_death_event)
        observation = self._get_observation()

        info = {
            'mint': self.current_mint, 'step': self.current_step,
            'last_processed_index': self._last_step_processed_index,
            'sol_balance': self.current_sol, 'realized_pnl_step': realized_pnl,
            'reward_shaping_step': bonus_penalty,
            'is_holding': 1 if self.active_position else 0, 'raw_reward': reward
        }
        if self.active_position:
             info['position_entry_price'] = self.active_position['buy_price']
             info['position_remaining_tokens'] = self.active_position['remaining_tokens']

        if terminated or truncated:
             final_portfolio_value = self.current_sol
             if self.active_position:
                  # Use last Close price for final valuation
                  last_price = self._price_history[-1] if self._price_history else self.active_position['buy_price']
                  final_portfolio_value += self.active_position['remaining_tokens'] * last_price
             info['final_portfolio_value'] = final_portfolio_value
             info['total_steps_taken'] = self.current_step
             if terminated: info['episode_end_reason'] = "terminated (bankrupt)"
             elif max_steps_reached: info['episode_end_reason'] = "truncated (max_steps)"
             elif is_token_death_event: info['episode_end_reason'] = "truncated (token_death)"
             else: info['episode_end_reason'] = "truncated (unknown)"

        return observation, reward, terminated, truncated, info

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Resets the environment (Same logic, but uses OHLCV data)."""
        super().reset(seed=seed)

        self.current_mint = random.choice(self.available_mints)
        self.current_data_df = self.historical_data_dict[self.current_mint].copy()
        lifespan = self.token_lifespans.get(self.current_mint)
        if not lifespan:
             raise RuntimeError(f"Lifespan info missing for selected mint {self.current_mint} during reset.")
        self.current_token_end_ts = lifespan['end_ts']

        # --- Pre-calculate Volatility if missing (use Close price) ---
        if 'volatility' not in self.current_data_df.columns or self.current_data_df['volatility'].isnull().all():
            logger.debug(f"Calculating volatility for {self.current_mint} during reset (using Close price)...")
            if 'Close' in self.current_data_df.columns and not self.current_data_df['Close'].isnull().all():
                prices = pd.to_numeric(self.current_data_df['Close'], errors='coerce').ffill().bfill().fillna(0.0)
                if len(prices) > 1:
                    # Pass the Series with its DatetimeIndex
                    volatility_series = calculate_volatility(prices, window=rl_config.VOLATILITY_WINDOW)
                    self.current_data_df['volatility'] = volatility_series.fillna(0.0)
                else:
                    self.current_data_df['volatility'] = 0.0
            else:
                self.current_data_df['volatility'] = 0.0
        # Ensure volatility column exists even if calculation failed
        if 'volatility' not in self.current_data_df.columns:
            self.current_data_df['volatility'] = 0.0
        else:
            # Fill any remaining NaNs just in case
            self.current_data_df['volatility'] = self.current_data_df['volatility'].fillna(0.0)


        # --- Reset State Variables (Same as before) ---
        self.current_step = 0
        self._last_step_processed_index = -1
        self.current_sol = self.initial_capital
        self.active_position = None
        self.trade_history = []
        self.current_parameters = {}
        self._price_history.clear()
        self._previous_unrealized_pnl = 0.0
        self.last_observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        # Pre-fill initial price history using Close prices
        initial_steps_to_fill = min(len(self.current_data_df), self._price_history.maxlen)
        for i in range(initial_steps_to_fill):
            try:
                price = float(self.current_data_df.iloc[i].get('Close', 0.0)) # Use Close
                self._price_history.append(price if pd.notna(price) else 0.0)
            except (IndexError, ValueError, TypeError):
                 self._price_history.append(0.0)

        # Get initial observation
        if len(self.current_data_df) > 0:
            self._last_step_processed_index = 0
            observation = self._get_observation()
            self._last_step_processed_index = -1
        else:
            logger.error(f"DataFrame for mint {self.current_mint} is empty after reset. Cannot generate initial observation.")
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        info = {}
        return observation, info

    def render(self, mode='human'):
        """Renders the environment state (Same as before)."""
        if mode == 'ansi':
            output = f"--- Step: {self.current_step}/{self._max_episode_steps} (Index: {self._last_step_processed_index}) ---\n"
            output += f"Mint: {self.current_mint}\n"
            output += f"SOL Balance: {self.current_sol:.4f}\n"
            if self.active_position:
                pos = self.active_position
                pnl_norm = self.last_observation[rl_config.OBSERVATION_FEATURES.index('position_pnl_norm')]
                output += f"Holding: {pos['remaining_tokens']:.4f} tokens (Bought @ {pos['buy_price']:.9f})\n"
                output += f"  Norm PnL: {pnl_norm:.3f}, Highest Price: {pos['highest_price']:.9f}\n"
                output += f"  SL: {pos['stop_loss_price']:.9f}, TP1: {pos['initial_tp_price']:.9f}, TP2: {pos['second_tp_price']:.9f}\n"
            else:
                output += "Holding: None\n"
            output += f"Agent Params: {self.current_parameters}\n"
            # Add last Close price
            last_close = self._price_history[-1] if self._price_history else 'N/A'
            output += f"Last Close Price: {last_close}\n"
            return output
        elif mode == 'human':
            print(self.render(mode='ansi'))

    def close(self):
        """Cleans up environment resources."""
        pass
