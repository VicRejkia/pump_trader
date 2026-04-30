# rl_agent_module/rewards/reward_function.py
"""
Implements the multi-objective reward function for the RL agent.
"""
from typing import Any, Dict

import numpy as np


class RewardFunction:
    """
    Calculates the reward for the agent based on a weighted sum of different objectives.
    Combines a dense, step-wise reward with sparse rewards on completed trades.
    """
    def __init__(self, config: Dict[str, Any]):
        self.rl_config = config
        # Use a small epsilon to avoid division by zero
        self.epsilon = 1e-9
        self.previous_portfolio_value = self.rl_config.get('ENV_INITIAL_BALANCE', 100.0)

    def calculate_reward(self, trade_result: Dict, current_state: Dict, current_portfolio_value: float) -> float:
        """
        Calculates the total reward for a completed trade or a timestep.
        """
        # --- 1. Dense Reward (Portfolio Value Change) ---
        # This provides a continuous feedback signal at every step.
        portfolio_change_pct = (current_portfolio_value / max(self.previous_portfolio_value, self.epsilon)) - 1.0
        dense_reward = portfolio_change_pct * self.rl_config.get('REWARD_DENSE_WEIGHT', 1.0)
        self.previous_portfolio_value = current_portfolio_value

        # --- 2. Sparse Reward (On Completed Trades) ---
        sparse_reward = 0.0
        if trade_result:
            pnl_component = self._calculate_pnl_reward(trade_result)
            risk_component = self._calculate_risk_adjusted_reward(trade_result, current_state)
            pos_mgmt_component = self._calculate_position_management_reward(trade_result)
            exec_component = self._calculate_execution_quality_reward(trade_result)

            sparse_reward = (
                self.rl_config.get('REWARD_PNL_WEIGHT', 0.5) * pnl_component +
                self.rl_config.get('REWARD_RISK_WEIGHT', 0.2) * risk_component +
                self.rl_config.get('REWARD_POSITION_MANAGEMENT_WEIGHT', 0.2) * pos_mgmt_component +
                self.rl_config.get('REWARD_EXECUTION_WEIGHT', 0.1) * exec_component
            )

        # --- 3. Combine Rewards ---
        total_reward = dense_reward + (sparse_reward * self.rl_config.get('REWARD_SPARSE_WEIGHT', 0.2))
        return total_reward

    def _calculate_pnl_reward(self, trade_result: Dict) -> float:
        """Calculates reward based on the profit and loss of a trade."""
        pnl = trade_result.get('pnl', 0.0)
        max_pnl = self.rl_config.get('MAX_EXPECTED_PNL_PER_TRADE_SOL', 1.0)
        return np.tanh(pnl / max(max_pnl, self.epsilon))

    def _calculate_risk_adjusted_reward(self, trade_result: Dict, state: Dict) -> float:
        """Penalizes trades on high-risk tokens."""
        pnl = trade_result.get('pnl', 0.0)
        rugcheck_risk = state.get('rugcheck_score', 1.0)
        social_risk = state.get('socials_score', 1.0)
        combined_risk = (rugcheck_risk * 0.7) + (social_risk * 0.3)

        if pnl > 0:
            return -pnl * combined_risk * 0.5
        else:
            return pnl * (1 + combined_risk)

    def _calculate_position_management_reward(self, trade_result: Dict) -> float:
        """Rewards effective position management."""
        if trade_result.get('side') == 'sell':
            price_to_highest = trade_result.get('price_to_highest_ratio', 1.0)
            profit_timing_reward = 1.0 - abs(0.9 - price_to_highest)
            return profit_timing_reward
        return 0

    def _calculate_execution_quality_reward(self, trade_result: Dict) -> float:
        """Penalizes for high slippage."""
        # This is a placeholder as slippage is not yet in trade_result
        return 0.0

    def reset(self, initial_portfolio_value: float):
        """Resets the internal state of the reward function for a new episode."""
        self.previous_portfolio_value = initial_portfolio_value
