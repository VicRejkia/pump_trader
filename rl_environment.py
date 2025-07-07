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
from bot_logger import logger
import rl_config # Import RL specific configurations
from utils import calculate_volatility, calculate_trend_indicators # Keep utility for potential recalculation

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
        dexscreener_snapshot_data: Dict[str, pd.DataFrame],
        initial_capital: float = rl_config.RL_INITIAL_CAPITAL,
        max_steps: int = rl_config.MAX_STEPS_PER_EPISODE,
        render_mode: Optional[str] = None
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

        # These are the columns expected in the DataFrame for each mint
        required_cols = [
            'Open', 'High', 'Low', 'Close', 'Volume',
            'market_cap_calculated',     # Live USD MC
            'marketCapSol',              # Live SOL MC
            'creation_init_market_cap_sol', # Creation-time SOL MC
            'volatility', 'rugcheck_score', 'socials_score',
            'token_creation_time'
        ]

        for mint, df in historical_data_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty and isinstance(df.index, pd.DatetimeIndex):
                 if df.index.tz is None or str(df.index.tz).upper() != 'UTC':
                     logger.error(f"DataFrame index for mint {mint} is not timezone-aware UTC! Skipping.")
                     continue
                 if mint not in token_lifespans:
                      logger.warning(f"Lifespan info missing for mint {mint}. Skipping.")
                      continue
                 missing_cols_check = [col for col in required_cols if col not in df.columns]
                 if missing_cols_check:
                     logger.error(f"Missing required OHLCV columns in data for mint {mint}: {missing_cols_check}. Skipping.")
                     continue
                 if df[required_cols].isnull().values.any():
                      logger.warning(f"NaN values found in required columns for mint {mint}. Will attempt fill/clip later.")
                 self.historical_data_dict[mint] = df
                 self.token_lifespans[mint] = token_lifespans[mint]
            else:
                 logger.warning(f"Skipping invalid/empty DataFrame for mint: {mint}")

        # Store the snapshot data
        self.dexscreener_snapshot_data = dexscreener_snapshot_data

        self.available_mints = list(self.historical_data_dict.keys())
        if not self.available_mints:
            raise ValueError("No valid OHLCV DataFrames found after validation.")

        self.initial_capital = initial_capital
        self._max_episode_steps = max_steps

        self.action_space = spaces.Box(
            low=rl_config.ACTION_LOW,
            high=rl_config.ACTION_HIGH,
            shape=(rl_config.ACTION_SPACE_DIM,),
            dtype=np.float32
        )
        self._action_param_names = [p[0] for p in rl_config.RL_TUNABLE_PARAMETERS]

        self.observation_space = spaces.Box(
            low=rl_config.OBSERVATION_LOW, # Using -np.inf
            high=rl_config.OBSERVATION_HIGH, # Using np.inf
            shape=(rl_config.OBSERVATION_SPACE_DIM,),
            dtype=np.float32
        )

        self.current_step: int = 0
        self.current_sol: float = 0.0
        self.current_data_df: Optional[pd.DataFrame] = None
        self.current_mint: Optional[str] = None
        self.current_token_end_ts: Optional[datetime] = None
        self.initial_creation_market_cap_sol: Optional[float] = None # For MC drop %
        self.active_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {}
        self.last_observation: np.ndarray = np.zeros(self.observation_space.shape, dtype=np.float32)
        self._price_history: deque = deque(maxlen=rl_config.OBSERVATION_PRICE_HISTORY_LENGTH)
        self._previous_unrealized_pnl: float = 0.0
        self._last_step_processed_index = -1
        self.current_snapshot_df: Optional[pd.DataFrame] = None # Add state for current snapshot df

        logger.info(f"TradingEnv (OHLCV) initialized. Observation space dim: {rl_config.OBSERVATION_SPACE_DIM}, Action space dim: {rl_config.ACTION_SPACE_DIM}")


    def _get_observation(self) -> np.ndarray:
        default_obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        if self.current_data_df is None or self._last_step_processed_index < 0 or self._last_step_processed_index >= len(self.current_data_df):
            return default_obs
        try:
            current_row = self.current_data_df.iloc[self._last_step_processed_index]
            current_timestamp = self.current_data_df.index[self._last_step_processed_index]
        except IndexError: return default_obs

        current_price = current_row.get('Close', 0.0)
        self._price_history.append(float(current_price) if pd.notna(current_price) and isinstance(current_price, (int, float)) else (self._price_history[-1] if self._price_history else 0.0))

        try:
            live_usd_market_cap = float(current_row.get('market_cap_calculated', 0.0))
            live_sol_market_cap = float(current_row.get('marketCapSol', 0.0)) # Live SOL MC
            volume = float(current_row.get('Volume', 0.0))
            rugcheck_score = int(current_row.get('rugcheck_score', 10000))
            socials_score = int(current_row.get('socials_score', 100))
            creation_time_ts = current_row.get('token_creation_time', pd.NaT)
            volatility = float(current_row.get('volatility', 0.0))

            live_usd_market_cap = 0.0 if pd.isna(live_usd_market_cap) else live_usd_market_cap
            live_sol_market_cap = 0.0 if pd.isna(live_sol_market_cap) else live_sol_market_cap
            volume = 0.0 if pd.isna(volume) else volume
            rugcheck_score = 10000 if pd.isna(rugcheck_score) else int(rugcheck_score)
            socials_score = 100 if pd.isna(socials_score) else int(socials_score)
            volatility = 0.0 if pd.isna(volatility) else volatility

        except (KeyError, ValueError, TypeError) as e: return default_obs

        prices_arr = np.array(self._price_history, dtype=np.float32)
        safe_prices = prices_arr[prices_arr > 1e-12]
        price_change_1 = np.log(safe_prices[-1] / safe_prices[-2]) if len(safe_prices) >= 2 else 0.0
        price_change_5 = np.log(safe_prices[-1] / safe_prices[-6]) if len(safe_prices) >= 6 else 0.0
        price_change_10 = np.log(safe_prices[-1] / safe_prices[-11]) if len(safe_prices) >= 11 else 0.0

        time_since_creation_seconds = 0.0
        if pd.notna(creation_time_ts) and isinstance(current_timestamp, pd.Timestamp):
            ct_ts_aware = creation_time_ts.tz_localize('UTC') if creation_time_ts.tzinfo is None else creation_time_ts.astimezone(timezone.utc)
            time_diff = current_timestamp - ct_ts_aware
            time_since_creation_seconds = max(0.0, time_diff.total_seconds())

        is_holding = 1.0 if self.active_position else 0.0
        position_pnl_current_unrealized = 0.0
        time_holding_seconds = 0.0
        if self.active_position:
            buy_p = self.active_position['buy_price']
            rem_t = self.active_position['remaining_tokens']
            total_inv = self.active_position.get('total_investment_sol', 1.0)
            last_p = prices_arr[-1] if prices_arr.size > 0 else buy_p
            curr_val = last_p * rem_t
            init_t = self.active_position.get('initial_tokens', rem_t)
            cost_frac = rem_t / init_t if init_t > 0 else 1.0
            cost_basis_rem = total_inv * cost_frac
            position_pnl_current_unrealized = curr_val - cost_basis_rem
            entry_ts = self.active_position.get('entry_timestamp')
            if entry_ts: time_holding_seconds = max(0.0, (current_timestamp - entry_ts).total_seconds())
        
        weekday = float(current_timestamp.weekday())
        hour = float(current_timestamp.hour)

        # These are raw values; VecNormalize will handle scaling
        observation_list = [
            price_change_1, price_change_5, price_change_10,
            volatility,
            live_sol_market_cap,    # For 'live_market_cap_sol_norm'
            live_usd_market_cap,    # For 'live_market_cap_usd_norm'
            volume,
            float(rugcheck_score), 
            float(socials_score), 
            time_since_creation_seconds,
            is_holding, 
            position_pnl_current_unrealized, 
            time_holding_seconds, 
            self.current_sol,
            weekday, 
            hour
        ]
        
        observation = np.array(observation_list, dtype=np.float32)
        if not np.all(np.isfinite(observation)): observation = default_obs
        elif observation.shape != self.observation_space.shape: observation = default_obs
        
        self.last_observation = observation
        self._previous_unrealized_pnl = position_pnl_current_unrealized
        return observation

    def _apply_action(self, action: np.ndarray):
        new_params = {}
        clipped_action = np.clip(action, rl_config.ACTION_LOW, rl_config.ACTION_HIGH)
        for i, param_config in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            param_name, _, _, p_type = param_config
            val = clipped_action[i]
            if param_name == "USE_TREND_REVERSAL_CONFIRMATION":
                # Convert float action (0.0-1.0) to boolean for this parameter
                new_params[param_name] = bool(val > 0.5)
            else:
                new_params[param_name] = p_type(np.round(val)) if p_type == int else float(val)
        self.current_parameters = new_params

    def _run_trading_logic_step(self) -> Tuple[float, float]:
        """
        [REWRITTEN] Simulates one step of the trading logic using OHLCV data.
        This now includes the complete, source-aware trend reversal logic to match the backtester.
        Returns realized PnL and any shaping bonuses/penalties for the step.
        """
        realized_pnl_this_step = 0.0
        reward_bonus_penalty = 0.0

        current_data_index = self.current_step
        self._last_step_processed_index = current_data_index

        if self.current_data_df is None or current_data_index >= len(self.current_data_df):
            return realized_pnl_this_step, reward_bonus_penalty

        # --- Get Current State and Parameters ---
        try:
            current_row = self.current_data_df.iloc[current_data_index]
            current_timestamp = self.current_data_df.index[current_data_index]
            
            price = float(current_row.get('Close', 0.0))
            volume_ohlcv = float(current_row.get('Volume', 0.0))
            high_price = float(current_row.get('High', 0.0))
            
            current_live_sol_mc = float(current_row.get('marketCapSol', 0.0))
            current_live_usd_mc = float(current_row.get('market_cap_calculated', 0.0))
            
            rugcheck_val = int(current_row.get('rugcheck_score', 10000))
            socials_val = int(current_row.get('socials_score', 100))
            volatility_val = float(current_row.get('volatility', 0.0))

            if price <= 1e-12:
                return realized_pnl_this_step, reward_bonus_penalty

            agent_params = self.current_parameters
            initial_sl_percent = agent_params.get('INITIAL_STOP_LOSS_PERCENT', 40.0)
            first_sell_perc_fraction = agent_params.get('FIRST_SELL_PERCENT', 35.0) / 100.0
            trailing_sl_percent = agent_params.get('TRAILING_STOP_LOSS_PERCENT', 50.0)
            first_profit_margin_fraction = agent_params.get('FIRST_SELL_PROFIT_MARGIN', 70.0) / 100.0
            second_tp_margin_fraction = agent_params.get('SECOND_TAKE_PROFIT_PERCENT', 800.0) / 100.0
            
            volume_thresh_usd = agent_params.get('DEFAULT_VOLUME_THRESHOLD', 40000)
            mcap_thresh_buy_usd = agent_params.get('DEFAULT_MARKETCAP_THRESHOLD', 45000)
            rug_thresh_agent = agent_params.get('DEFAULT_RUGCHECK_SCORE_THRESHOLD', 401)
            social_thresh_agent = agent_params.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100)
            volatility_thresh_agent = agent_params.get('MIN_VOLATILITY', 0.18)
            buy_amount_sol_agent = agent_params.get('SOL_TO_BUY', 0.5)
            mc_drop_threshold_param = agent_params.get('MC_DROP_THRESHOLD_RL', 70.0)
            use_trend_reversal = agent_params.get('USE_TREND_REVERSAL_CONFIRMATION', False)

            buy_fee = rl_config.DEFAULT_BUY_FEE
            buy_tip = rl_config.DEFAULT_BUY_TIP
            sell_fee = rl_config.DEFAULT_SELL_FEE
            sell_tip = rl_config.DEFAULT_SELL_TIP
            min_mcap_usd_fallback = rl_config.MIN_MARKET_CAP_USD_FALLBACK

        except (KeyError, ValueError, TypeError, IndexError) as e:
            logger.error(f"RL Env: Error getting data/params at step {self.current_step}: {e}", exc_info=False)
            return realized_pnl_this_step, reward_bonus_penalty
        
        # --- Sell Logic (No change to this block) ---
        if self.active_position:
            pos = self.active_position
            pos['highest_price'] = max(pos['highest_price'], high_price)

            active_sl_price = pos['stop_loss_price']
            initial_tp_price = pos['initial_tp_price']
            second_tp_price = pos['second_tp_price']
            is_first_tp_hit = pos['first_tp_hit']
            
            current_trailing_sl_price = 0.0
            if is_first_tp_hit:
                current_trailing_sl_price = pos['highest_price'] * (1.0 - trailing_sl_percent / 100.0)

            sell_reason = None; sell_all = False; sell_partial = False; sell_percentage = 0.0

            if price <= active_sl_price:
                sell_reason = "Stop Loss" if not is_first_tp_hit else "Breakeven SL"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif price >= second_tp_price:
                sell_reason = "Second TP"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif not is_first_tp_hit and price >= initial_tp_price:
                sell_reason = "First TP"; sell_partial = True; sell_percentage = first_sell_perc_fraction
                reward_bonus_penalty += rl_config.REWARD_TP_HIT_BONUS
            elif is_first_tp_hit and current_trailing_sl_price > 0 and price <= current_trailing_sl_price:
                sell_reason = "Trailing SL"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif self.initial_creation_market_cap_sol is not None and self.initial_creation_market_cap_sol > 1e-9 and current_live_sol_mc > 0 and current_live_sol_mc < (self.initial_creation_market_cap_sol * (1.0 - (mc_drop_threshold_param / 100.0))):
                sell_reason = f"Emergency SL (MCap % Drop > {mc_drop_threshold_param:.1f}%)"; sell_all = True; sell_percentage = 1.0
                reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            elif current_live_usd_mc > 0 and current_live_usd_mc < min_mcap_usd_fallback:
                 sell_reason = f"Emergency SL (Abs USD MCap < {min_mcap_usd_fallback})"; sell_all = True; sell_percentage = 1.0
                 reward_bonus_penalty += rl_config.REWARD_SL_HIT_PENALTY
            
            if sell_reason:
                initial_tokens = pos['initial_tokens']
                remaining_tokens = pos['remaining_tokens']
                total_investment_sol_for_pos = pos['total_investment_sol']
                tokens_to_sell = min(initial_tokens * sell_percentage, remaining_tokens) if sell_partial else remaining_tokens
                
                if tokens_to_sell > 1e-9:
                    gross_sol_recv = tokens_to_sell * price
                    net_sol_recv = gross_sol_recv - sell_fee - sell_tip
                    cost_basis_sold = total_investment_sol_for_pos * (tokens_to_sell / initial_tokens) if initial_tokens > 0 else 0
                    pnl = net_sol_recv - cost_basis_sold
                    realized_pnl_this_step += pnl
                    self.current_sol += net_sol_recv
                    pos['remaining_tokens'] -= tokens_to_sell
                    self.trade_history.append({'step': self.current_step, 'type': 'sell', 'price': price, 'tokens': tokens_to_sell, 'pnl': pnl, 'reason': sell_reason})
                    if sell_partial:
                        pos['first_tp_hit'] = True
                        pos['stop_loss_price'] = pos['buy_price']
                    if pos['remaining_tokens'] < 1e-9:
                        self.active_position = None
        
        # --- Buy Logic ---
        if not self.active_position and self.current_sol >= (buy_amount_sol_agent + buy_fee + buy_tip):
            meets_standard_criteria = (
                volume_ohlcv >= volume_thresh_usd and
                current_live_usd_mc >= mcap_thresh_buy_usd and
                rugcheck_val < rug_thresh_agent and
                socials_val < social_thresh_agent and
                volatility_val >= volatility_thresh_agent
            )

            proceed_with_buy_attempt = False

            if not meets_standard_criteria:
                proceed_with_buy_attempt = False
            elif use_trend_reversal:
                was_recently_sold_for_reversal_reason = False
                if self.trade_history:
                    recency_hours = agent_params.get('TREND_REVERSAL_RECENCY_HOURS', 6)
                    applicable_reasons = ["Stop Loss", "Emergency SL", "Trailing SL", "Breakeven SL"]
                    for trade in reversed(self.trade_history):
                        if trade.get('type') == 'sell':
                            time_since_last_sell = current_timestamp - self.current_data_df.index[trade['step']]
                            if time_since_last_sell <= pd.Timedelta(hours=recency_hours):
                                if any(reason in trade.get('reason', '') for reason in applicable_reasons):
                                    was_recently_sold_for_reversal_reason = True
                            break 
                
                if was_recently_sold_for_reversal_reason:
                    is_migrated_token = self.current_snapshot_df is not None and not self.current_snapshot_df.empty
                    
                    if is_migrated_token:
                        # --- DEXSCREENER REVERSAL LOGIC ---
                        lookback_minutes = agent_params.get('DEX_REVERSAL_LOOKBACK_MINUTES', 15)
                        min_snapshots = agent_params.get('DEX_REVERSAL_MIN_SNAPSHOTS', 3)
                        min_liquidity = agent_params.get('DEX_REVERSAL_MIN_LIQUIDITY_USD', 5000)
                        min_ratio = agent_params.get('DEX_REVERSAL_MIN_BUY_SELL_RATIO', 1.5)
                        min_confirmations = agent_params.get('DEX_REVERSAL_MIN_CONFIRMATIONS', 2)
                        
                        snapshots = self.current_snapshot_df[self.current_snapshot_df.index <= current_timestamp].last(f'{lookback_minutes}min')

                        if len(snapshots) < min_snapshots or float(snapshots.iloc[-1]['liquidity_usd']) < min_liquidity:
                            proceed_with_buy_attempt = False
                        else:
                            count = sum(1 for _, s in snapshots.iterrows() if s.get('buys_m5', 0) > 0 and (s.get('sells_m5', 0) == 0 or (s.get('buys_m5') / s.get('sells_m5')) >= min_ratio))
                            proceed_with_buy_attempt = count >= min_confirmations
                    else:
                        # --- PUMP.FUN REVERSAL LOGIC (TA INDICATORS) ---
                        lookback_h = agent_params.get('INDICATOR_LOOKBACK_HOURS', 1)
                        candles_needed = int(lookback_h * 3600 / 5)
                        start_idx = max(0, self.current_step - candles_needed + 1)
                        
                        min_candles_cfg = rl_config.MIN_CANDLE_DATA_FOR_INDICATORS
                        if (self.current_step - start_idx + 1) >= min_candles_cfg:
                            indicator_config = {k: agent_params.get(k, v) for k, v in {'RSI_PERIOD': 14, 'BBANDS_PERIOD': 20, 'BBANDS_STD_DEV': 2.0, 'FAST_EMA_PERIOD': 9, 'SLOW_EMA_PERIOD': 21}.items()}
                            indicator_config['MIN_CANDLE_DATA_FOR_INDICATORS'] = min_candles_cfg
                            df_inds = calculate_trend_indicators(self.current_data_df.iloc[start_idx : self.current_step + 1].copy(), indicator_config)

                            if not df_inds.empty and len(df_inds) >= 2:
                                latest = df_inds.iloc[-1]; prev = df_inds.iloc[-2]
                                rsi_neutral = agent_params.get('TREND_REVERSAL_RSI_NEUTRAL_LEVEL', 45)
                                bbl_col = f"BBL_{indicator_config['BBANDS_PERIOD']}_{indicator_config['BBANDS_STD_DEV']}"
                                stage1 = (latest.get('RSI', 50) > 30 and prev.get('RSI', 50) <= 30) or \
                                         (latest.get('Close', 0) > latest.get(bbl_col, float('inf')) and prev.get('Close', 0) <= prev.get(bbl_col, float('inf'))) or \
                                         (latest.get('RSI', 0) > rsi_neutral)
                                stage2 = (latest.get('Close', 0) > latest.get('VWAP', float('-inf'))) and (latest.get('EMA_fast', 0) > latest.get('EMA_slow', float('inf')))
                                proceed_with_buy_attempt = stage1 and stage2
                            else:
                                proceed_with_buy_attempt = False
                        else:
                            proceed_with_buy_attempt = False
                else:
                    proceed_with_buy_attempt = meets_standard_criteria
            else:
                proceed_with_buy_attempt = meets_standard_criteria

            if proceed_with_buy_attempt:
                total_investment = buy_amount_sol_agent + buy_fee + buy_tip
                tokens_bought = buy_amount_sol_agent / price
                self.current_sol -= total_investment
                sl_price = price * (1.0 - initial_sl_percent / 100.0)
                cost_tp1 = total_investment * first_sell_perc_fraction
                profit_tp1 = cost_tp1 * first_profit_margin_fraction
                gross_sol_tp1 = cost_tp1 + profit_tp1 + (sell_fee + sell_tip)
                tp1_price = gross_sol_tp1 / (tokens_bought * first_sell_perc_fraction) if (tokens_bought * first_sell_perc_fraction) > 1e-9 else float('inf')
                tp2_price = price * (1.0 + second_tp_margin_fraction)

                self.active_position = {'buy_price': price, 'initial_tokens': tokens_bought, 'remaining_tokens': tokens_bought, 'total_investment_sol': total_investment, 'stop_loss_price': sl_price, 'initial_tp_price': tp1_price, 'second_tp_price': tp2_price, 'highest_price': price, 'first_tp_hit': False, 'entry_timestamp': current_timestamp}
                self.trade_history.append({'step': self.current_step, 'type': 'buy', 'price': price, 'tokens': tokens_bought})
        
        return realized_pnl_this_step, reward_bonus_penalty

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        if self.current_data_df is None:
            obs = np.zeros(self.observation_space.shape, dtype=np.float32)
            return obs, 0.0, True, False, {"error": "Environment not reset"}

        self._apply_action(action) # Agent sets self.current_parameters
        realized_pnl, bonus_penalty = self._run_trading_logic_step()
        
        terminated = self.current_sol <= 0
        
        # Check if EOD or token death, current_step has not yet been incremented for next state
        # So current_data_index is self.current_step
        current_data_idx_for_check = self.current_step 
        end_of_data = current_data_idx_for_check >= len(self.current_data_df) -1 # Ran out of candles for current token
        
        token_died_this_step = False
        if self.current_token_end_ts and current_data_idx_for_check < len(self.current_data_df):
            current_candle_timestamp = self.current_data_df.index[current_data_idx_for_check]
            if current_candle_timestamp >= self.current_token_end_ts:
                token_died_this_step = True
        
        max_steps_reached = (self.current_step + 1) >= self._max_episode_steps # Check against NEXT step
        
        truncated = max_steps_reached or end_of_data or token_died_this_step
        is_token_death_event_for_reward = end_of_data or token_died_this_step # For death penalty

        reward = self._calculate_reward(realized_pnl, bonus_penalty, is_token_death_event_for_reward)
        
        self.current_step += 1 # Increment step *before* getting observation for the *next* state

        # Get observation for the *next* state (S_t+1)
        # If truncated/terminated, the next observation might not be valid or used,
        # but SB3 expects it. _get_observation handles boundary conditions.
        if not (terminated or truncated):
             self._last_step_processed_index = self.current_step # Update for next obs
        else: # If episode ends, obs might be from last valid point or zeros
             self._last_step_processed_index = min(self.current_step, len(self.current_data_df) -1) if len(self.current_data_df) > 0 else -1


        observation = self._get_observation()

        info = {
            'mint': self.current_mint, 'step': self.current_step -1, # Step that just finished
            'sol_balance': self.current_sol, 'realized_pnl_step': realized_pnl,
            'is_holding': 1 if self.active_position else 0, 'raw_reward': reward
        }
        if terminated or truncated:
            final_val = self.current_sol
            if self.active_position and self._price_history:
                final_val += self.active_position['remaining_tokens'] * self._price_history[-1]
            info['final_portfolio_value'] = final_val
            info['total_steps_taken'] = self.current_step # Current_step is already next step number
            if terminated: info['episode_end_reason'] = "terminated (bankrupt)"
            elif token_died_this_step: info['episode_end_reason'] = "truncated (token_death)"
            elif end_of_data: info['episode_end_reason'] = "truncated (end_of_data)"
            elif max_steps_reached: info['episode_end_reason'] = "truncated (max_steps)"
            else: info['episode_end_reason'] = "truncated (unknown)"
            
        return observation, reward, terminated, truncated, info

    def _calculate_reward(self, realized_pnl: float, bonus_penalty: float, is_token_death_event: bool) -> float:
        reward = realized_pnl * rl_config.REWARD_PNL_MULTIPLIER
        reward += bonus_penalty
        if self.active_position and rl_config.REWARD_HOLDING_PENALTY != 0:
            reward += rl_config.REWARD_HOLDING_PENALTY
        if is_token_death_event and self.active_position: # Apply penalty if holding when token dies/data ends
            reward += rl_config.REWARD_DEATH_PENALTY
        return reward

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)

        self.current_mint = random.choice(self.available_mints)
        self.current_data_df = self.historical_data_dict[self.current_mint].copy()
        # ADDED: Set the snapshot dataframe for the chosen mint
        self.current_snapshot_df = self.dexscreener_snapshot_data.get(self.current_mint)
        
        lifespan = self.token_lifespans.get(self.current_mint)
        if not lifespan:
             raise RuntimeError(f"Lifespan info missing for selected mint {self.current_mint} during reset.")
        self.current_token_end_ts = lifespan['end_ts']

        # Set initial_creation_market_cap_sol for the episode
        self.initial_creation_market_cap_sol = None 
        if not self.current_data_df.empty and 'creation_init_market_cap_sol' in self.current_data_df.columns:
            val_series = pd.to_numeric(self.current_data_df['creation_init_market_cap_sol'], errors='coerce')
            first_valid_val = val_series.dropna().iloc[0] if not val_series.dropna().empty else np.nan
            
            if pd.notna(first_valid_val) and first_valid_val > 0:
                self.initial_creation_market_cap_sol = float(first_valid_val)
                # logger.debug(f"Episode for {self.current_mint}: Initial CREATION marketCapSol set to {self.initial_creation_market_cap_sol}")
            else:
                logger.warning(f"Episode for {self.current_mint}: Invalid or non-positive initial creation_init_market_cap_sol. Value: {first_valid_val if pd.notna(first_valid_val) else 'NaN/Empty'}")
        else:
            logger.warning(f"Episode for {self.current_mint}: 'creation_init_market_cap_sol' column missing or DF empty. Cannot set initial creation MC.")

        if 'volatility' not in self.current_data_df.columns or self.current_data_df['volatility'].isnull().all():
            if 'Close' in self.current_data_df.columns and not self.current_data_df['Close'].isnull().all():
                prices = pd.to_numeric(self.current_data_df['Close'], errors='coerce').ffill().bfill().fillna(0.0)
                if len(prices) > 1:
                    self.current_data_df['volatility'] = calculate_volatility(prices, window=rl_config.VOLATILITY_WINDOW).fillna(0.0)
                else: self.current_data_df['volatility'] = 0.0
            else: self.current_data_df['volatility'] = 0.0
        if 'volatility' not in self.current_data_df.columns: self.current_data_df['volatility'] = 0.0
        else: self.current_data_df['volatility'] = self.current_data_df['volatility'].fillna(0.0)
        
        self.current_step = 0
        self._last_step_processed_index = -1
        self.current_sol = self.initial_capital
        self.active_position = None
        self.trade_history = []
        self.current_parameters = {}
        self._price_history.clear()
        self._previous_unrealized_pnl = 0.0
        self.last_observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        initial_steps_to_fill = min(len(self.current_data_df), self._price_history.maxlen)
        for i in range(initial_steps_to_fill):
            try:
                price = float(self.current_data_df.iloc[i].get('Close', 0.0))
                self._price_history.append(price if pd.notna(price) else 0.0)
            except (IndexError, ValueError, TypeError): self._price_history.append(0.0)

        if len(self.current_data_df) > 0:
            self._last_step_processed_index = 0
            observation = self._get_observation()
            self._last_step_processed_index = -1 
        else:
            logger.error(f"DataFrame for mint {self.current_mint} is empty after reset. Cannot get obs.")
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)
        return observation, {}

    def render(self, mode='human'):
        # ... (render method can remain largely the same, ensure it accesses correct variables) ...
        # Example:
        if mode == 'ansi':
            output = f"--- Step: {self.current_step}/{self._max_episode_steps} (Data Index: {self._last_step_processed_index}) ---\n"
            output += f"Mint: {self.current_mint}\n"
            output += f"SOL Balance: {self.current_sol:.4f}\n"
            output += f"Initial Creation SOL MC: {self.initial_creation_market_cap_sol}\n"
            if self.active_position:
                pos = self.active_position
                output += f"Holding: {pos['remaining_tokens']:.4f} tokens (Bought @ {pos['buy_price']:.9f})\n"
                # ... more details ...
            else:
                output += "Holding: None\n"
            output += f"Agent Params: {self.current_parameters}\n"
            last_close = self._price_history[-1] if self._price_history else 'N/A'
            output += f"Last Close Price: {last_close}\n"
            if self.last_observation is not None and len(self.last_observation) > 0:
                 try:
                    live_sol_mc_norm_idx = rl_config.OBSERVATION_FEATURES.index('live_market_cap_sol_norm')
                    live_usd_mc_norm_idx = rl_config.OBSERVATION_FEATURES.index('live_market_cap_usd_norm')
                    output += f"  Norm Live SOL MC: {self.last_observation[live_sol_mc_norm_idx]:.3f}\n"
                    output += f"  Norm Live USD MC: {self.last_observation[live_usd_mc_norm_idx]:.3f}\n"
                 except (ValueError, IndexError): pass # In case features are not found or obs is not ready
            return output
        elif mode == 'human':
            print(self.render(mode='ansi'))

    def close(self):
        """Cleans up environment resources."""
        pass

    def set_render_mode(self, render_mode: Optional[str]):
        """Sets the render mode for the environment."""
        self.render_mode = render_mode
