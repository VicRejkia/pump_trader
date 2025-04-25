# FILE: rl_environment.py

"""
Custom Gymnasium Environment for Training the Trading Bot RL Agent.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import random
from collections import deque

from logger import logger
import rl_config # Import RL specific configurations

# Try importing backtester logic - may need adjustment based on final backtester structure
try:
    from backtester import calculate_volatility # Assuming this is usable
except ImportError:
    logger.error("Could not import calculate_volatility from backtester. Ensure backtester.py is accessible.")
    # Define a placeholder if import fails to allow environment structure definition
    def calculate_volatility(prices, window=10): return pd.Series(0.0, index=prices.index)


class TradingEnv(gym.Env):
    """
    Custom Gymnasium Environment for Solana Pump Trading.

    Action Space (Option A - Parameter Tuning): Box space with values for key trading parameters.
    Observation Space: Box space with market indicators and portfolio status.
    """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}

    def __init__(self, historical_data_dict: dict, initial_capital: float, max_steps: int = rl_config.MAX_STEPS_PER_EPISODE):
        super().__init__()

        if not historical_data_dict:
            raise ValueError("Historical data dictionary cannot be empty.")

        self.historical_data_dict = historical_data_dict
        self.available_mints = list(historical_data_dict.keys())
        if not self.available_mints:
             raise ValueError("No valid mints found in the historical data dictionary.")

        self.initial_capital = initial_capital
        self.max_steps = max_steps

        # --- Define Action Space (Parameter Tuning) ---
        self.action_low = rl_config.ACTION_LOW
        self.action_high = rl_config.ACTION_HIGH
        self.action_space = spaces.Box(
            low=self.action_low,
            high=self.action_high,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        # Store parameter names for easy mapping
        self._action_param_names = [p[0] for p in rl_config.RL_TUNABLE_PARAMETERS]

        # --- Define Observation Space ---
        self.obs_low = np.full(rl_config.OBSERVATION_SPACE_DIM, rl_config.OBSERVATION_LOW, dtype=np.float32)
        self.obs_high = np.full(rl_config.OBSERVATION_SPACE_DIM, rl_config.OBSERVATION_HIGH, dtype=np.float32)
        self.observation_space = spaces.Box(
            low=self.obs_low,
            high=self.obs_high,
            shape=(rl_config.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        # --- Internal State ---
        self.current_step = 0
        self.current_sol = 0.0
        self.current_data_df = None
        self.current_mint = None
        self.active_position = None # Stores info like buy_price, tokens_held, etc.
        self.trade_history = []
        self.current_parameters = {} # Parameters chosen by the agent
        self.last_observation = None
        self._price_history = deque(maxlen=15) # Store recent prices for features
        self._volume_history = deque(maxlen=15) # Store recent volumes for features

        logger.info(f"TradingEnv initialized. Observation space dim: {rl_config.OBSERVATION_SPACE_DIM}, Action space dim: {rl_config.ACTION_SPACE_DIM}")


    def _get_observation(self):
        if self.current_data_df is None or self.current_step >= len(self.current_data_df):
            return np.zeros(self.observation_space.shape, dtype=np.float32)

        try:
            current_row = self.current_data_df.iloc[self.current_step]
            # Ensure required columns exist, use .get() with defaults
            current_price = current_row.get('price', 0.0)
            market_cap = current_row.get('market_cap_calculated', 0.0) # Assuming this is SOL based
            volume = current_row.get('volume', 0.0)
            rugcheck_score = current_row.get('rugcheck_score', 10000)
            socials_score = current_row.get('socials_score', 100)
            creation_time = current_row.get('token_creation_time', pd.NaT)
            # Assuming 'volatility' is pre-calculated or calculated here
            volatility = current_row.get('volatility', 0.0)
            if pd.isna(volatility): volatility = 0.0 # Handle potential NaN

        except IndexError:
            logger.warning(f"IndexError at step {self.current_step} for mint {self.current_mint}. Returning zero obs.")
            return np.zeros(self.observation_space.shape, dtype=np.float32)
        except KeyError as e:
            logger.warning(f"KeyError '{e}' accessing data at step {self.current_step}. Mint: {self.current_mint}. Returning zero obs.")
            return np.zeros(self.observation_space.shape, dtype=np.float32)

        # --- Calculate Price Change Features ---
        # Use self._price_history deque
        prices = np.array(self._price_history)
        price_change_1 = np.log(prices[-1] / prices[-2]) if len(prices) >= 2 and prices[-2] > 1e-9 else 0.0
        price_change_5 = np.log(prices[-1] / prices[-6]) if len(prices) >= 6 and prices[-6] > 1e-9 else 0.0
        price_change_10 = np.log(prices[-1] / prices[-11]) if len(prices) >= 11 and prices[-11] > 1e-9 else 0.0

        # --- Calculate Time Since Creation ---
        time_since_creation_seconds = 0
        current_timestamp = self.current_data_df.index[self.current_step]
        if pd.notna(creation_time) and isinstance(current_timestamp, pd.Timestamp):
            # Ensure both are timezone-aware (assuming UTC)
            if creation_time.tzinfo is None: creation_time = creation_time.tz_localize('UTC')
            if current_timestamp.tzinfo is None: current_timestamp = current_timestamp.tz_localize('UTC')
            time_diff = current_timestamp - creation_time
            time_since_creation_seconds = max(0, time_diff.total_seconds()) # Ensure non-negative

        # --- Calculate Portfolio Features ---
        is_holding = 1.0 if self.active_position else 0.0
        position_pnl_norm = 0.0
        steps_holding = 0
        if self.active_position:
            buy_price = self.active_position['buy_price']
            rem_tokens = self.active_position['remaining_tokens']
            total_investment = self.active_position.get('total_investment_sol', 1.0) or 1.0 # Avoid zero investment

            # Calculate unrealized PnL percentage relative to initial investment
            current_value = current_price * rem_tokens
            initial_cost_for_remaining = buy_price * rem_tokens # Cost basis for remaining tokens
            unrealized_pnl = current_value - initial_cost_for_remaining
            position_pnl_norm = unrealized_pnl / total_investment # Normalize by total initial buy cost

            steps_holding = self.current_step - self.active_position['entry_step']

        # --- Normalization (CRITICAL - MATCH TRAINING) ---
        # These need refinement based on actual data ranges observed during exploration/analysis
        norm_price_change_1 = np.clip(price_change_1 * 20, -1, 1) # Scale more for smaller intervals
        norm_price_change_5 = np.clip(price_change_5 * 10, -1, 1)
        norm_price_change_10 = np.clip(price_change_10 * 5, -1, 1)
        norm_volatility = np.clip(volatility * 10, 0, 1) # Scale volatility
        norm_market_cap = np.clip(np.log10(market_cap + 1e-9) / 7, -1, 1) # Assumes max ~10M SOL cap log10(10M)=7
        norm_volume = np.clip(np.log10(volume + 1e-9) / 5, -1, 1) # Assumes max ~100k SOL volume log10(100k)=5
        norm_rugcheck = np.clip(1.0 - (rugcheck_score / 1000.0), 0, 1) # Higher score = lower value (0-1)
        norm_socials = np.clip(1.0 - (socials_score / 100.0), 0, 1) # Higher score = lower value (0-1)
        norm_time_creation = np.clip(np.log10(time_since_creation_seconds + 1) / 6, 0, 1) # log10(1M seconds ~ 11 days) = 6
        norm_pos_pnl = np.clip(position_pnl_norm, -1, 1) # PnL as fraction of investment, clipped
        norm_steps_held = np.clip(steps_holding / float(self.max_steps), 0, 1) # Fraction of max episode duration
        norm_sol_balance = np.clip(self.current_sol / (self.initial_capital * 2.0), 0, 1) # Normalize based on potential doubling

        # --- Construct observation vector ---
        # Match the order defined in rl_config.OBSERVATION_FEATURES
        observation = np.array([
            norm_price_change_1, norm_price_change_5, norm_price_change_10,
            norm_volatility, norm_market_cap, norm_volume,
            norm_rugcheck, norm_socials, norm_time_creation,
            is_holding, norm_pos_pnl, norm_steps_held, norm_sol_balance
        ], dtype=np.float32)

        # --- Final Checks ---
        if not np.all(np.isfinite(observation)):
            logger.warning(f"NaN/inf in observation @ step {self.current_step}. Mint: {self.current_mint}. Clipping. Obs: {observation}")
            observation = np.nan_to_num(observation, nan=0.0, posinf=1.0, neginf=-1.0)
            observation = np.clip(observation, self.obs_low, self.obs_high)

        if observation.shape != self.observation_space.shape:
            logger.error(f"Observation shape mismatch! Expected {self.observation_space.shape}, got {observation.shape}. Returning zeros.")
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        self.last_observation = observation
        return observation

    def _apply_action(self, action):
        """
        Applies the action (sets the trading parameters for the next step).
        Also performs clipping/scaling if needed.
        """
        # Action is expected to be a numpy array from the agent
        # Map action values to the parameter dictionary
        new_params = {}
        for i, param_name in enumerate(self._action_param_names):
            # Ensure action value is within defined bounds (agent might output slightly outside)
            val = np.clip(action[i], self.action_low[i], self.action_high[i])
            # Convert to correct type if needed (e.g., int for thresholds)
            param_config = next((p for p in rl_config.RL_TUNABLE_PARAMETERS if p[0] == param_name), None)
            if param_config and param_config[3] == int:
                new_params[param_name] = int(round(val))
            else:
                new_params[param_name] = float(val)

        self.current_parameters = new_params
        #logger.debug(f"Step {self.current_step}: Agent chose parameters: {self.current_parameters}")

    def _run_trading_step(self):
        """
        Simulates one step of the trading logic using self.current_parameters.
        Updates portfolio state (self.active_position, self.current_sol).
        Returns realized PnL for this step and any shaping bonuses/penalties.
        """
        realized_pnl_this_step = 0.0
        reward_bonus_penalty = 0.0 # For shaping rewards like SL/TP hits

        if self.current_step >= len(self.current_data_df):
            return realized_pnl_this_step, reward_bonus_penalty # End of data

        try:
            current_row = self.current_data_df.iloc[self.current_step]
            price = current_row.get('price', 0.0)
            if price <= 1e-12: # Skip step if price is effectively zero
                return realized_pnl_this_step, reward_bonus_penalty
            # Use market_cap_sol if available, otherwise calculate (assuming SOL price = 1 in env?)
            market_cap_sol = current_row.get('market_cap_calculated', 0.0)

            # --- Get parameters chosen by the agent for this step ---
            agent_params = self.current_parameters
            # Provide defaults if agent hasn't chosen yet (first step?)
            initial_sl_percent = agent_params.get('INITIAL_STOP_LOSS_PERCENT', 50.0)
            first_sell_perc = agent_params.get('FIRST_SELL_PERCENT', 75.0) / 100.0
            trailing_sl_percent = agent_params.get('TRAILING_STOP_LOSS_PERCENT', 50.0)
            first_profit_margin = agent_params.get('FIRST_SELL_PROFIT_MARGIN', 30.0) / 100.0
            # Get fixed fees from rl_config (or main config if consistent)
            buy_fee = rl_config.DEFAULT_BUY_FEE
            buy_tip = rl_config.DEFAULT_BUY_TIP
            sell_fee = rl_config.DEFAULT_SELL_FEE
            sell_tip = rl_config.DEFAULT_SELL_TIP
            # Get fixed thresholds from rl_config (unless agent tunes them)
            volume_thresh = rl_config.DEFAULT_VOLUME_THRESHOLD
            mcap_thresh_buy = rl_config.DEFAULT_MARKETCAP_THRESHOLD
            rug_thresh = rl_config.DEFAULT_RUGCHECK_SCORE_THRESHOLD
            social_thresh = rl_config.DEFAULT_SOCIAL_SCORE_THRESHOLD
            volatility_thresh = rl_config.MIN_VOLATILITY
            min_mcap_sell = rl_config.MIN_MARKET_CAP

        except (IndexError, KeyError) as e:
            logger.warning(f"Error accessing data/params at step {self.current_step}. Mint: {self.current_mint}. Error: {e}")
            return realized_pnl_this_step, reward_bonus_penalty

        # --- Sell Logic Simulation (Adapting from trading_logic.py) ---
        if self.active_position:
            # Update highest price
            hp = max(self.active_position['highest_price'], price)
            self.active_position['highest_price'] = hp

            # Calculate current trigger prices based on *agent's chosen parameters*
            buy_price = self.active_position['buy_price']
            initial_tokens = self.active_position['initial_tokens']
            total_investment = self.active_position['total_investment_sol']

            # --- Recalculate SL/TPs using agent_params ---
            current_stop_loss_price = buy_price * (1 - initial_sl_percent / 100.0)
            if self.active_position['first_tp_hit']:
                current_stop_loss_price = buy_price # Breakeven

            total_cost_base_tp1 = total_investment + sell_fee + sell_tip
            target_net_sol_return_tp1 = total_cost_base_tp1 * (1 + first_profit_margin)
            target_gross_sol_return_tp1 = target_net_sol_return_tp1 + sell_fee + sell_tip
            tokens_to_sell_tp1 = initial_tokens * first_sell_perc
            current_initial_tp_price = (target_gross_sol_return_tp1 / tokens_to_sell_tp1) if tokens_to_sell_tp1 > 1e-9 else float('inf')

            # Assuming second TP is fixed for now, get from rl_config or main config
            # If agent tuned it, get from agent_params
            second_tp_price = buy_price * (1 + rl_config.SECOND_TAKE_PROFIT_PERCENT / 100.0)

            current_trailing_sl_price = 0.0
            if self.active_position['first_tp_hit']:
                current_trailing_sl_price = hp * (1 - trailing_sl_percent / 100.0)
            # --- End Recalculation ---


            # --- Check Sell Conditions (using calculated trigger prices) ---
            sell_reason = None
            sell_all = False
            sell_partial = False
            sell_percentage = 0.0
            # Use calculated current_stop_loss_price, current_initial_tp_price, etc.
            if price <= current_stop_loss_price:
                sell_reason = "Stop Loss" if not self.active_position['first_tp_hit'] else "Breakeven SL"
                sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif price >= second_tp_price: # Using fixed second TP here
                sell_reason = "Second TP"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS # Bonus for TP2
            elif not self.active_position['first_tp_hit'] and price >= current_initial_tp_price:
                sell_reason = "First TP"; sell_partial = True; sell_percentage = first_sell_perc
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif self.active_position['first_tp_hit'] and price <= current_trailing_sl_price:
                sell_reason = "Trailing SL"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY # Penalty for trailing SL hit
            # Add Emergency SL check (Requires SOL price - tricky in isolated env)
            # sol_price_usd = current_row.get('sol_price_usd', 1.0) # Need SOL price history
            # current_market_cap_usd = market_cap_sol * sol_price_usd
            # if current_market_cap_usd < min_mcap_sell:
            #     sell_reason = "Emergency SL"; sell_all = True; sell_percentage = 1.0
            #     reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY * 2 # Heavier penalty?


            # --- Execute Simulated Sell ---
            if sell_reason:
                tokens_to_sell = 0.0
                if sell_partial: tokens_to_sell = initial_tokens * sell_percentage
                elif sell_all: tokens_to_sell = self.active_position['remaining_tokens']
                tokens_to_sell = min(tokens_to_sell, self.active_position['remaining_tokens'])

                if tokens_to_sell > 1e-9:
                    gross_sol = tokens_to_sell * price
                    net_sol = gross_sol - sell_fee - sell_tip
                    cost_basis = total_investment * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                    pnl = net_sol - cost_basis
                    realized_pnl_this_step += pnl

                    self.current_sol += net_sol
                    self.active_position['remaining_tokens'] -= tokens_to_sell
                    self.trade_history.append({'step': self.current_step, 'type': 'sell', 'price': price, 'tokens': tokens_to_sell, 'net_sol': net_sol, 'pnl': pnl, 'reason': sell_reason})

                    if sell_partial: self.active_position['first_tp_hit'] = True
                    if self.active_position['remaining_tokens'] < 1e-9: self.active_position = None


        # --- Buy Logic Simulation (Adapting from trading_logic.py/backtester.py) ---
        # Use fixed buy amount from rl_config for simplicity now
        buy_amount_sol = rl_config.DEFAULT_BUY_SOL_AMOUNT # Or get from agent if tuning SOL_TO_BUY
        if not self.active_position and self.current_sol >= (buy_amount_sol + buy_fee + buy_tip):
            # --- Check Buy Conditions (using fixed thresholds for now) ---
            # These thresholds could also be part of the agent's action space
            volume = current_row.get('volume', 0.0)
            market_cap_buy_check = market_cap_sol # Assume MC check is in SOL for env
            rugcheck_score = current_row.get('rugcheck_score', 10000)
            socials_score = current_row.get('socials_score', 100)
            volatility = current_row.get('volatility', 0.0)

            # Note: In environment, SOL price is not directly available unless passed in data.
            # We might need to simplify thresholds or pass SOL price history. Assuming checks are vs SOL values here.
            meets_buy_criteria = (
                volume >= volume_thresh # Assuming threshold is SOL volume? Or needs USD calc?
                and market_cap_buy_check >= mcap_thresh_buy # Assuming SOL threshold
                and rugcheck_score < rug_thresh
                and socials_score < social_thresh
                and volatility >= volatility_thresh
            )
            # --- End Buy Condition Check ---

            if meets_buy_criteria:
                total_investment = buy_amount_sol + buy_fee + buy_tip
                tokens_bought = buy_amount_sol / price if price > 0 else 0

                if tokens_bought > 0:
                    self.current_sol -= total_investment
                    # Store params used for this buy (could be useful for analysis)
                    buy_params_snapshot = self.current_parameters.copy()

                    self.active_position = {
                        'buy_price': price, 'initial_tokens': tokens_bought,
                        'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment,
                        'highest_price': price, 'first_tp_hit': False,
                        'entry_step': self.current_step, 'buy_parameters': buy_params_snapshot
                    }
                    self.trade_history.append({'step': self.current_step, 'type': 'buy', 'price': price, 'tokens': tokens_bought, 'investment': total_investment})

        return realized_pnl_this_step, reward_bonus_penalty

    def _calculate_reward(self, realized_pnl, shaping_bonus_penalty):
        reward = (realized_pnl * rl_config.REWARD_PNL_MULTIPLIER) + shaping_bonus_penalty

        # Add holding penalty
        if self.active_position and rl_config.REWARD_SHAPING_HOLDING_PENALTY != 0:
            reward += rl_config.REWARD_SHAPING_HOLDING_PENALTY

        # Optional: Add unrealized PnL shaping (example)
        if self.active_position and rl_config.REWARD_SHAPING_UNREALIZED_PNL != 0:
            # Calculate current unrealized pnl (similar to _get_observation)
            # Compare with unrealized pnl from the *previous* step (need to store it)
            # Add reward proportional to the *change* in unrealized PnL
            pass # Implement if desired, requires storing previous state info

        # Clip reward to prevent extreme values? Optional.
        # reward = np.clip(reward, -10, 10)
        return reward


    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        # Select a random mint and its data for the new episode
        self.current_mint = random.choice(self.available_mints)
        self.current_data_df = self.historical_data_dict[self.current_mint].copy()
        # Pre-calculate volatility if not already present
        if 'volatility' not in self.current_data_df.columns:
             logger.debug(f"Calculating volatility for {self.current_mint}...")
             # Ensure price column exists and is numeric
             if 'price' in self.current_data_df.columns:
                  prices = pd.to_numeric(self.current_data_df['price'], errors='coerce').fillna(0.0)
                  self.current_data_df['volatility'] = calculate_volatility(prices) # Adjust window if needed
                  self.current_data_df['volatility'] = self.current_data_df['volatility'].fillna(0.0) # Fill NaNs from rolling window start
             else:
                  logger.warning(f"Price column missing for {self.current_mint}, cannot calculate volatility.")
                  self.current_data_df['volatility'] = 0.0


        # Reset state variables
        self.current_step = 0
        self.current_sol = self.initial_capital
        self.active_position = None
        self.trade_history = []
        self.current_parameters = {} # Reset agent parameters
        self._price_history.clear()
        self._volume_history.clear()

        # Get initial observation
        observation = self._get