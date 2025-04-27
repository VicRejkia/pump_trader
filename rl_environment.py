# FILE: rl_environment.py (Added Death Penalty & Refinements)

"""
Custom Gymnasium Environment for Training a Solana Pump.fun Trading Bot RL Agent.

This environment simulates the trading process based on historical data, including
handling for token death and applying appropriate rewards/penalties.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import random
from collections import deque
from typing import Dict, List, Optional, Tuple, Any, Union # Added Union
from datetime import timezone, datetime # Added datetime

# --- Project Modules ---
from logger import logger
import rl_config # Import RL specific configurations
from utils import calculate_volatility

# --- Environment Class ---

class TradingEnv(gym.Env):
    """
    Custom Gymnasium Environment for Solana Pump Trading Simulation.

    Action Space (Continuous):
        Box space representing tunable trading parameters (rl_config.RL_TUNABLE_PARAMETERS).
        Agent outputs values for these parameters.

    Observation Space (Continuous):
        Box space representing market state and portfolio status, normalized
        (rl_config.OBSERVATION_FEATURES).

    Reward:
        Combination of realized PnL, shaping rewards/penalties, and a significant
        penalty for holding through token death (rl_config reward settings).
    """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}

    def __init__(
        self,
        historical_data_dict: Dict[str, pd.DataFrame],
        token_lifespans: Dict[str, Dict[str, datetime]], # Add token lifespans
        initial_capital: float = rl_config.RL_INITIAL_CAPITAL,
        max_steps: int = rl_config.MAX_STEPS_PER_EPISODE
    ):
        """
        Initializes the Trading Environment.

        Args:
            historical_data_dict: Dictionary mapping mints to their historical data DataFrames.
                                  Indices MUST be timezone-aware UTC DatetimeIndex.
            token_lifespans: Dictionary mapping mints to their {'start_ts', 'end_ts'} (UTC).
            initial_capital: Starting SOL balance for each episode.
            max_steps: Maximum number of steps allowed per episode (truncation).
        """
        super().__init__()

        if not historical_data_dict:
            raise ValueError("Historical data dictionary cannot be empty.")
        if not token_lifespans:
             raise ValueError("Token lifespans dictionary cannot be empty.")

        # Filter data and ensure timezone awareness (should be handled by loader now)
        self.historical_data_dict = {}
        self.token_lifespans = {} # Store lifespans relevant to the provided data
        for mint, df in historical_data_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty and isinstance(df.index, pd.DatetimeIndex):
                 if df.index.tz is None or str(df.index.tz).upper() != 'UTC':
                     logger.error(f"DataFrame index for mint {mint} is not timezone-aware UTC! Skipping.")
                     continue
                 if mint in token_lifespans:
                     self.historical_data_dict[mint] = df
                     self.token_lifespans[mint] = token_lifespans[mint] # Store lifespan if data is valid
                 else:
                      logger.warning(f"Lifespan info missing for mint {mint} with valid data. Skipping.")
            else:
                 logger.warning(f"Skipping invalid/empty DataFrame for mint: {mint}")

        self.available_mints = list(self.historical_data_dict.keys())
        if not self.available_mints:
            raise ValueError("No valid (non-empty, UTC DatetimeIndexed, with lifespan) DataFrames found.")

        self.initial_capital = initial_capital
        self._max_episode_steps = max_steps

        # --- Define Action Space ---
        self.action_space = spaces.Box(
            low=rl_config.ACTION_LOW,
            high=rl_config.ACTION_HIGH,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        self._action_param_names = [p[0] for p in rl_config.RL_TUNABLE_PARAMETERS]

        # --- Define Observation Space ---
        self.observation_space = spaces.Box(
            low=rl_config.OBSERVATION_LOW,
            high=rl_config.OBSERVATION_HIGH,
            shape=(rl_config.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        # --- Internal State Variables ---
        self.current_step: int = 0
        self.current_sol: float = 0.0
        self.current_data_df: Optional[pd.DataFrame] = None
        self.current_mint: Optional[str] = None
        self.current_token_end_ts: Optional[datetime] = None # Store the death time for current token
        self.active_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {}
        self.last_observation: np.ndarray = np.zeros(self.observation_space.shape, dtype=np.float32)
        self._price_history: deque = deque(maxlen=rl_config.OBSERVATION_PRICE_HISTORY_LENGTH)
        self._previous_unrealized_pnl: float = 0.0
        self._last_step_processed_index = -1 # Track index to avoid double processing

        logger.info(f"TradingEnv initialized. Observation space dim: {rl_config.OBSERVATION_SPACE_DIM}, Action space dim: {rl_config.ACTION_SPACE_DIM}")

    def _get_observation(self) -> np.ndarray:
        """
        Calculates and returns the normalized observation vector for the current step.

        Returns:
            A numpy array representing the normalized observation, or zeros if invalid state.
        """
        default_obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        # Use _last_step_processed_index which points to the actual data index used
        if self.current_data_df is None or self._last_step_processed_index < 0 or self._last_step_processed_index >= len(self.current_data_df):
            # logger.warning(f"Invalid state for observation. Data: {self.current_data_df is not None}, Step Index: {self._last_step_processed_index}. Returning zeros.")
            return default_obs

        try:
            # Use the correct index that was processed in the step
            current_row = self.current_data_df.iloc[self._last_step_processed_index]
            current_timestamp = self.current_data_df.index[self._last_step_processed_index]
        except IndexError:
            logger.warning(f"IndexError getting observation at index {self._last_step_processed_index} (Step {self.current_step}) for mint {self.current_mint}. Returning zeros.")
            return default_obs

        # --- Update Price History ---
        current_price = current_row.get('price', 0.0)
        if pd.notna(current_price) and isinstance(current_price, (int, float)):
            self._price_history.append(float(current_price))
        else:
            last_valid_price = self._price_history[-1] if self._price_history else 0.0
            self._price_history.append(last_valid_price)

        # --- Extract Base Features ---
        try:
            market_cap_sol = float(current_row.get('market_cap_calculated', 0.0))
            volume_sol = float(current_row.get('volume', 0.0))
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            creation_time_ts = current_row.get('token_creation_time', pd.NaT)
            volatility = float(current_row.get('volatility', 0.0))
            if pd.isna(volatility): volatility = 0.0
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error accessing/converting base features at index {self._last_step_processed_index} for mint {self.current_mint}: {e}", exc_info=True)
            return default_obs

        # --- Calculate Derived Features ---
        prices = np.array(self._price_history, dtype=np.float32)
        safe_prices = prices[prices > 1e-12]
        price_change_1 = np.log(safe_prices[-1] / safe_prices[-2]) if len(safe_prices) >= 2 else 0.0
        price_change_5 = np.log(safe_prices[-1] / safe_prices[-6]) if len(safe_prices) >= 6 else 0.0
        price_change_10 = np.log(safe_prices[-1] / safe_prices[-11]) if len(safe_prices) >= 11 else 0.0

        time_since_creation_seconds = 0.0
        if pd.notna(creation_time_ts) and isinstance(current_timestamp, pd.Timestamp):
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
            last_price = prices[-1] if prices.size > 0 else buy_price
            current_value = last_price * rem_tokens
            initial_tokens = self.active_position.get('initial_tokens', rem_tokens)
            cost_fraction = rem_tokens / initial_tokens if initial_tokens > 0 else 1.0
            cost_basis_remaining = total_investment * cost_fraction
            position_pnl_current_unrealized = current_value - cost_basis_remaining
            # Calculate time held in seconds
            entry_timestamp = self.active_position.get('entry_timestamp')
            if entry_timestamp:
                time_holding_seconds = max(0.0, (current_timestamp - entry_timestamp).total_seconds())


        # --- Normalization ---
        # Use small epsilon to avoid log(0)
        epsilon = 1e-9
        norm_price_change_1 = np.clip(price_change_1 * 20, -1, 1)
        norm_price_change_5 = np.clip(price_change_5 * 10, -1, 1)
        norm_price_change_10 = np.clip(price_change_10 * 5, -1, 1)
        norm_volatility = np.clip(volatility, 0, 1) # Assuming volatility is already 0-1
        norm_market_cap = np.clip(np.log10(market_cap_sol + epsilon) / 7, 0, 1) # Log scale 0 to 10M
        norm_volume = np.clip(np.log10(volume_sol + epsilon) / 5, 0, 1) # Log scale 0 to 100k
        norm_rugcheck = np.clip(1.0 - (float(rugcheck_score) / 10000.0), 0, 1)
        norm_socials = np.clip(1.0 - (float(socials_score) / 100.0), 0, 1)
        norm_time_creation = np.clip(np.log10(time_since_creation_seconds + 1) / 6, 0, 1) # 1s to ~1M seconds (approx 11 days)
        norm_pos_pnl = np.clip(position_pnl_current_unrealized / (total_investment if self.active_position else 1.0), -1, 5) # -100% to +500% PnL
        # Normalize time held based on max episode duration (in seconds)
        max_duration_seconds = self._max_episode_steps * 5 # Assuming 5s per step approx
        norm_time_held = np.clip(time_holding_seconds / (max_duration_seconds + epsilon), 0, 1)
        norm_sol_balance = np.clip(self.current_sol / (self.initial_capital * 2.0), 0, 1)

        # --- Construct Observation Vector (Order MUST match rl_config.OBSERVATION_FEATURES) ---
        observation = np.array([
            norm_price_change_1, norm_price_change_5, norm_price_change_10,
            norm_volatility, norm_market_cap, norm_volume, # Renamed norm vars
            norm_rugcheck, norm_socials, norm_time_creation,
            is_holding, norm_pos_pnl, norm_time_held, norm_sol_balance # Use norm_time_held
        ], dtype=np.float32)

        # --- Final Validation ---
        if not np.all(np.isfinite(observation)):
            logger.warning(f"NaN/inf in observation @ Index {self._last_step_processed_index}, Mint {self.current_mint}. Replacing with zeros. Raw Obs: {observation}")
            observation = default_obs
        elif observation.shape != self.observation_space.shape:
            logger.error(f"Observation shape mismatch! Expected {self.observation_space.shape}, got {observation.shape}. Returning zeros.")
            observation = default_obs
        else:
            observation = np.clip(observation, rl_config.OBSERVATION_LOW, rl_config.OBSERVATION_HIGH)

        self.last_observation = observation
        self._previous_unrealized_pnl = position_pnl_current_unrealized # Store for reward shaping
        return observation

    def _apply_action(self, action: np.ndarray):
        """Applies the agent's action by updating internal trading parameters."""
        new_params = {}
        clipped_action = np.clip(action, rl_config.ACTION_LOW, rl_config.ACTION_HIGH)

        for i, param_config in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            param_name, _, _, p_type = param_config
            val = clipped_action[i]
            new_params[param_name] = p_type(np.round(val)) if p_type == int else float(val) # Round if int

        self.current_parameters = new_params

    def _run_trading_logic_step(self) -> Tuple[float, float]:
        """
        Simulates one step of the trading logic using agent's parameters.
        Returns realized PnL and any shaping bonuses/penalties for the step.
        """
        realized_pnl_this_step = 0.0
        reward_bonus_penalty = 0.0

        # Use the index for the current step
        current_data_index = self.current_step
        if self.current_data_df is None or current_data_index >= len(self.current_data_df):
            logger.warning(f"Attempted to run trading logic at invalid step index {current_data_index}.")
            self._last_step_processed_index = -1 # Indicate invalid step
            return realized_pnl_this_step, reward_bonus_penalty

        # Record the index being processed *before* potential errors
        self._last_step_processed_index = current_data_index

        try:
            current_row = self.current_data_df.iloc[current_data_index]
            current_timestamp = self.current_data_df.index[current_data_index] # Get timestamp for position entry
            price = float(current_row.get('price', 0.0))
            market_cap_sol = float(current_row.get('market_cap_calculated', 0.0))

            if price <= 1e-12: # Cannot trade if price is zero
                return realized_pnl_this_step, reward_bonus_penalty

            # --- Get parameters (Agent's or Defaults) ---
            agent_params = self.current_parameters
            if not agent_params: # Fallback if agent hasn't acted yet (first step)
                agent_params = {p[0]: (p[1] + p[2]) / 2 for p in rl_config.RL_TUNABLE_PARAMETERS}

            initial_sl_percent = agent_params.get('INITIAL_STOP_LOSS_PERCENT', 50.0)
            first_sell_perc = agent_params.get('FIRST_SELL_PERCENT', 75.0) / 100.0
            trailing_sl_percent = agent_params.get('TRAILING_STOP_LOSS_PERCENT', 50.0)
            first_profit_margin = agent_params.get('FIRST_SELL_PROFIT_MARGIN', 100.0) / 100.0

            # Fixed simulation parameters
            buy_fee = rl_config.DEFAULT_BUY_FEE
            buy_tip = rl_config.DEFAULT_BUY_TIP
            sell_fee = rl_config.DEFAULT_SELL_FEE
            sell_tip = rl_config.DEFAULT_SELL_TIP
            buy_amount_sol = rl_config.DEFAULT_BUY_SOL_AMOUNT
            volume_thresh = rl_config.DEFAULT_VOLUME_THRESHOLD
            mcap_thresh_buy = rl_config.DEFAULT_MARKETCAP_THRESHOLD
            rug_thresh = rl_config.DEFAULT_RUGCHECK_SCORE_THRESHOLD
            social_thresh = rl_config.DEFAULT_SOCIAL_SCORE_THRESHOLD
            volatility_thresh = rl_config.MIN_VOLATILITY
            min_mcap_sell_usd = rl_config.MIN_MARKET_CAP # Requires SOL price (not directly used here)

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error getting data/params in trading logic at index {current_data_index}: {e}", exc_info=True)
            return realized_pnl_this_step, reward_bonus_penalty

        # --- Sell Logic ---
        if self.active_position:
            pos = self.active_position
            hp = max(pos['highest_price'], price)
            pos['highest_price'] = hp # Update highest price seen

            current_stop_loss_price = pos['stop_loss_price']
            initial_tp_price = pos['initial_tp_price']
            second_tp_price = pos['second_tp_price']
            first_tp_hit = pos['first_tp_hit']

            current_trailing_sl_price = 0.0
            if first_tp_hit:
                current_trailing_sl_price = hp * (1.0 - trailing_sl_percent / 100.0)

            sell_reason = None
            sell_all = False
            sell_partial = False
            sell_percentage = 0.0

            if price <= current_stop_loss_price:
                sell_reason = "Stop Loss" if not first_tp_hit else "Breakeven SL"
                sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif price >= second_tp_price:
                sell_reason = "Second TP"
                sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif not first_tp_hit and price >= initial_tp_price:
                sell_reason = "First TP"
                sell_partial = True; sell_percentage = first_sell_perc
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif first_tp_hit and price <= current_trailing_sl_price:
                sell_reason = "Trailing SL"
                sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            # Emergency SL (Simplified - assumes SOL price is 1 for check, needs proper integration if used)
            # elif (market_cap_sol * 1.0) < min_mcap_sell_usd:
            #     sell_reason = "Emergency SL"; sell_all = True; sell_percentage = 1.0
            #     reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY # Penalize emergency exits

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
                        pos['stop_loss_price'] = pos['buy_price'] # Move SL to breakeven

                    if pos['remaining_tokens'] < 1e-9:
                        self.active_position = None # Close position fully

        # --- Buy Logic ---
        if not self.active_position and self.current_sol >= (buy_amount_sol + buy_fee + buy_tip):
            # Check fixed buy criteria
            volume = float(current_row.get('volume', 0.0))
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            volatility = float(current_row.get('volatility', 0.0))

            meets_buy_criteria = (
                volume >= volume_thresh and
                market_cap_sol >= mcap_thresh_buy and
                rugcheck_score < rug_thresh and
                socials_score < social_thresh and
                volatility >= volatility_thresh
            )

            if meets_buy_criteria:
                total_investment = buy_amount_sol + buy_fee + buy_tip
                tokens_bought = buy_amount_sol / price if price > 0 else 0

                if tokens_bought > 0:
                    self.current_sol -= total_investment

                    # Calculate initial SL/TPs using agent's CURRENT parameters
                    initial_sl_price = price * (1.0 - initial_sl_percent / 100.0)

                    sell_fee_tp1 = float(rl_config.DEFAULT_SELL_FEE)
                    sell_tip_tp1 = float(rl_config.DEFAULT_SELL_TIP)
                    total_cost_base_tp1 = total_investment + sell_fee_tp1 + sell_tip_tp1
                    target_net_sol_return_tp1 = total_cost_base_tp1 * (1.0 + first_profit_margin)
                    target_gross_sol_return_tp1 = target_net_sol_return_tp1 + sell_fee_tp1 + sell_tip_tp1
                    tokens_to_sell_tp1 = tokens_bought * first_sell_perc
                    initial_tp_price = (target_gross_sol_return_tp1 / tokens_to_sell_tp1) if tokens_to_sell_tp1 > 1e-9 else float('inf')

                    second_tp_price = price * (1.0 + rl_config.SECOND_TAKE_PROFIT_PERCENT / 100.0)

                    self.active_position = {
                        'buy_price': price, 'initial_tokens': tokens_bought,
                        'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment,
                        'stop_loss_price': initial_sl_price, 'initial_tp_price': initial_tp_price,
                        'second_tp_price': second_tp_price, 'highest_price': price,
                        'first_tp_hit': False, 'entry_step': self.current_step,
                        'entry_timestamp': current_timestamp # Store entry timestamp
                    }
                    self.trade_history.append({
                        'step': self.current_step, 'index': current_data_index, 'type': 'buy', 'price': price,
                        'tokens': tokens_bought, 'investment': total_investment
                    })

        return realized_pnl_this_step, reward_bonus_penalty

    def _calculate_reward(self, realized_pnl: float, bonus_penalty: float, is_token_death: bool) -> float:
        """
        Calculates the reward, including a penalty for holding through token death.

        Args:
            realized_pnl: Profit/loss realized from sales in this step.
            bonus_penalty: Sum of bonuses (TP hit) and penalties (SL hit).
            is_token_death: Flag indicating if the episode ended due to end of token data.

        Returns:
            The calculated reward value for the step.
        """
        reward = realized_pnl * rl_config.REWARD_PNL_MULTIPLIER
        reward += bonus_penalty

        # Apply holding penalty if configured
        if self.active_position and rl_config.REWARD_HOLDING_PENALTY != 0:
            reward += rl_config.REWARD_HOLDING_PENALTY

        # --- Apply Death Penalty ---
        if is_token_death and self.active_position:
            # Apply penalty only if holding when token dies
            reward += rl_config.REWARD_DEATH_PENALTY
            logger.debug(f"Applied death penalty ({rl_config.REWARD_DEATH_PENALTY}) for holding {self.current_mint} at end.")

        return reward


    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Executes one time step within the environment.

        Args:
            action: The action provided by the RL agent (parameter values).

        Returns:
            A tuple containing:
            - observation (np.ndarray): Observation for the *next* state.
            - reward (float): Reward received for the *current* step.
            - terminated (bool): Whether the episode ended due to bankruptcy.
            - truncated (bool): Whether the episode ended due to max steps, end of data, or token death.
            - info (dict): Auxiliary information.
        """
        if self.current_data_df is None:
            logger.error("Environment not reset properly, cannot step.")
            obs = np.zeros(self.observation_space.shape, dtype=np.float32)
            return obs, 0.0, True, False, {"error": "Environment not reset"}

        # 1. Apply Action
        self._apply_action(action)

        # 2. Simulate Trading Logic for the current step index
        realized_pnl, bonus_penalty = self._run_trading_logic_step()

        # 3. Advance the time step counter
        self.current_step += 1

        # 4. Determine Termination and Truncation Conditions
        terminated = self.current_sol <= 0 # Bankrupt

        # Check for end of available data for this token
        end_of_data = self._last_step_processed_index >= len(self.current_data_df) - 1
        # Check if the current step's timestamp exceeds the known end time for the token
        token_died = False
        if self.current_token_end_ts and self._last_step_processed_index >=0 : # Check if index is valid
             current_timestamp = self.current_data_df.index[self._last_step_processed_index]
             token_died = current_timestamp >= self.current_token_end_ts

        # Check if max episode steps reached
        max_steps_reached = self.current_step >= self._max_episode_steps

        # Truncation occurs if max steps reached OR end of data reached/token died
        truncated = max_steps_reached or end_of_data or token_died
        # Flag specifically for reward calculation if truncation was due to token death/end of data
        is_token_death_event = end_of_data or token_died

        # 5. Calculate Reward (passing the death event flag)
        reward = self._calculate_reward(realized_pnl, bonus_penalty, is_token_death_event)

        # 6. Get Observation for the *Next* State (uses _last_step_processed_index)
        # If truncated/terminated, the next observation doesn't strictly matter but compute it anyway.
        observation = self._get_observation()

        # 7. Populate Info Dictionary
        info = {
            'mint': self.current_mint,
            'step': self.current_step,
            'last_processed_index': self._last_step_processed_index,
            'sol_balance': self.current_sol,
            'realized_pnl_step': realized_pnl,
            'reward_shaping_step': bonus_penalty, # Renamed for clarity
            'is_holding': 1 if self.active_position else 0,
            'raw_reward': reward
        }
        if self.active_position:
             info['position_entry_price'] = self.active_position['buy_price']
             info['position_remaining_tokens'] = self.active_position['remaining_tokens']

        if terminated or truncated:
             final_portfolio_value = self.current_sol
             if self.active_position:
                  last_price = self._price_history[-1] if self._price_history else self.active_position['buy_price']
                  final_portfolio_value += self.active_position['remaining_tokens'] * last_price
             info['final_portfolio_value'] = final_portfolio_value
             info['total_steps_taken'] = self.current_step
             if terminated: info['episode_end_reason'] = "terminated (bankrupt)"
             elif max_steps_reached: info['episode_end_reason'] = "truncated (max_steps)"
             elif is_token_death_event: info['episode_end_reason'] = "truncated (token_death)"
             else: info['episode_end_reason'] = "truncated (unknown)" # Should not happen
             # Optional: Log episode end summary
             # logger.debug(f"Ep End ({self.current_mint}): {info['episode_end_reason']}, Steps={info['total_steps_taken']}, FinalVal={final_portfolio_value:.4f}, Reward={reward:.4f}")


        return observation, reward, terminated, truncated, info

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """
        Resets the environment for a new episode, selecting a new token and lifespan.
        """
        super().reset(seed=seed)

        # Select a random mint WITH VALID DATA AND LIFESPAN
        self.current_mint = random.choice(self.available_mints)
        self.current_data_df = self.historical_data_dict[self.current_mint].copy()
        # Get and store the end timestamp for this token
        lifespan = self.token_lifespans.get(self.current_mint)
        if not lifespan:
             # This should not happen if constructor filtering worked
             raise RuntimeError(f"Lifespan info missing for selected mint {self.current_mint} during reset.")
        self.current_token_end_ts = lifespan['end_ts']
        # logger.debug(f"Resetting Env. Mint: {self.current_mint}, DataLen: {len(self.current_data_df)}, EndTS: {self.current_token_end_ts}")


        # --- Pre-calculate Volatility if missing ---
        if 'volatility' not in self.current_data_df.columns:
            # logger.debug(f"Calculating volatility for {self.current_mint} during reset...")
            if 'price' in self.current_data_df.columns and not self.current_data_df['price'].isnull().all():
                prices = pd.to_numeric(self.current_data_df['price'], errors='coerce').ffill().bfill().fillna(0.0)
                if len(prices) > 1:
                    # calculate_volatility expects a Series with a DatetimeIndex
                    volatility_series = calculate_volatility(prices.set_axis(self.current_data_df.index), window=rl_config.VOLATILITY_WINDOW)
                    self.current_data_df['volatility'] = volatility_series.fillna(0.0)
                else:
                    self.current_data_df['volatility'] = 0.0
            else:
                self.current_data_df['volatility'] = 0.0

        # --- Reset State Variables ---
        self.current_step = 0
        self._last_step_processed_index = -1 # Reset processed index tracker
        self.current_sol = self.initial_capital
        self.active_position = None
        self.trade_history = []
        self.current_parameters = {}
        self._price_history.clear()
        self._previous_unrealized_pnl = 0.0
        self.last_observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        # Pre-fill initial price history
        initial_steps_to_fill = min(len(self.current_data_df), self._price_history.maxlen)
        for i in range(initial_steps_to_fill):
            try:
                price = float(self.current_data_df.iloc[i].get('price', 0.0))
                self._price_history.append(price)
            except (IndexError, ValueError, TypeError):
                 self._price_history.append(0.0)

        # --- Set Step Index Correctly for First Observation ---
        # _get_observation uses _last_step_processed_index. For the initial state,
        # we consider the state *before* the first step (index -1 effectively),
        # but we need data from index 0 to compute the observation.
        # So, temporarily set the index to 0 for the first observation calculation.
        if len(self.current_data_df) > 0:
            self._last_step_processed_index = 0 # Use index 0 for the initial obs
            observation = self._get_observation()
            self._last_step_processed_index = -1 # Reset it after getting obs, ready for step 0
        else:
            # Handle case where DataFrame might be empty after filtering (shouldn't happen with checks)
            logger.error(f"DataFrame for mint {self.current_mint} is empty after reset. Cannot generate initial observation.")
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)


        info = {}
        # logger.debug("Environment reset complete.")
        return observation, info

    def render(self, mode='human'):
        """Renders the environment state (optional)."""
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
            return output
        elif mode == 'human':
            print(self.render(mode='ansi'))

    def close(self):
        """Cleans up environment resources."""
        # logger.debug(f"Closing TradingEnv for mint {self.current_mint}")
        pass