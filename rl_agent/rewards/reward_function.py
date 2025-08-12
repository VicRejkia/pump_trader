# rl_agent/rewards/reward_function.py
"""
Implements the multi-objective reward function for the RL agent.
"""
import numpy as np
from typing import Dict, Any

class RewardFunction:
    """
    Calculates the reward for the agent based on a weighted sum of different objectives.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def calculate_reward(self, trade_result: Dict, current_state: Dict) -> float:
        """
        Calculates the total reward for a completed trade or a timestep.

        Args:
            trade_result: A dictionary containing details of the executed trade.
                          Should be empty if no trade occurred this step.
            current_state: The current state of the environment/token.

        Returns:
            The calculated scalar reward.
        """
        if not trade_result:
            # Penalize for holding a losing position
            pnl = current_state.get('unrealized_pnl', 0.0)
            holding_penalty = -0.001 if pnl < 0 else 0.0
            return holding_penalty

        # 1. Primary PnL component
        pnl = trade_result.get('pnl', 0.0)
        max_pnl = self.config.get('MAX_EXPECTED_PNL_PER_TRADE_SOL', 1.0)
        pnl_component = np.tanh(pnl / max_pnl)

        # 2. Risk management component
        risk_component = self._calculate_risk_adjusted_reward(trade_result, current_state)

        # 3. Position management component
        pos_mgmt_component = self._calculate_position_management_reward(trade_result)
        
        # 4. Execution quality component
        exec_component = self._calculate_execution_quality_reward(trade_result)

        # Combine with configurable weights
        total_reward = (
            self.config.get('REWARD_PNL_WEIGHT', 0.5) * pnl_component +
            self.config.get('REWARD_RISK_WEIGHT', 0.2) * risk_component +
            self.config.get('REWARD_POSITION_MANAGEMENT_WEIGHT', 0.2) * pos_mgmt_component +
            self.config.get('REWARD_EXECUTION_WEIGHT', 0.1) * exec_component
        )
        return total_reward

    def _calculate_risk_adjusted_reward(self, trade_result: Dict, state: Dict) -> float:
        """Penalizes trades on high-risk tokens."""
        pnl = trade_result.get('pnl', 0.0)
        # Remember: Lower scores are BETTER for rugcheck and socials
        rugcheck_risk = state.get('rugcheck_score', 1.0)  # Normalized 0-1
        social_risk = state.get('socials_score', 1.0)    # Normalized 0-1
        
        combined_risk = (rugcheck_risk * 0.7) + (social_risk * 0.3)
        
        if pnl > 0:
            # Reduce reward for profits made on risky assets
            return -pnl * combined_risk * 0.5
        else:
            # Amplify penalty for losses on risky assets
            return pnl * (1 + combined_risk) # pnl is already negative

    def _calculate_position_management_reward(self, trade_result: Dict) -> float:
        """Rewards flexible and effective position management."""
        if trade_result['side'] == 'sell':
            price_to_highest = trade_result.get('price_to_highest_ratio', 1.0)
            
            # Reward selling near the peak
            profit_timing_reward = 1.0 - abs(0.9 - price_to_highest) # Peak reward at 90% of high
            
            # Reward partial profit-taking
            sell_fraction = trade_result.get('sell_fraction', 1.0)
            size_reward = 0.5 if 0.1 < sell_fraction < 0.9 else -0.1
            
            return (profit_timing_reward * 0.7) + (size_reward * 0.3)
            
        elif trade_result['side'] == 'buy' and trade_result.get('rebuy', False):
            # Reward buying back after a significant dip from the sell price
            price_drop_pct = (trade_result['price'] / trade_result['previous_sell_price']) - 1
            if -0.3 <= price_drop_pct < -0.1: # Ideal 10-30% dip
                return 0.8
            else:
                return -0.2 # Penalize buying back too soon or too late

        return 0

    def _calculate_execution_quality_reward(self, trade_result: Dict) -> float:
        """Rewards low slippage and efficient fee usage."""
        slippage = trade_result.get('slippage_percent', 0.0)
        slippage_penalty = - (slippage / self.config.get('DEFAULT_SLIPPAGE_PERCENT', 15.0))
        return slippage_penalty