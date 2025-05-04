from typing import Optional, Dict, Any
import logging
import os
import traceback
import numpy as np
import config
import rl_config

logger = logging.getLogger(__name__)

try:
    import stable_baselines3
    from stable_baselines3 import PPO
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False

class RLAgentManager:
    """
    Manages RL agent lifecycle including loading, updating, and applying actions
    """
    
    def __init__(self, state, db_client):
        self.state = state
        self.db_client = db_client
        self.rl_agent = None
        self.last_observation = None
        self.rl_initialized = False
        self.enabled = False
        
        # RL parameter tracking
        self.param_history = []
        self.last_action = None
        
        logger.info(":robot: RL Agent Manager initialized")
    
    def load_agent(self, model_path: str) -> bool:
        """
        Load RL agent from specified model path
        Returns True if successful, False otherwise
        """
        if not RL_AVAILABLE:
            logger.warning(":warning: RL dependencies not available")
            return False
            
        if not model_path or not os.path.exists(model_path):
            logger.warning(f":warning: RL model path invalid: {model_path}")
            return False
            
        try:
            logger.info(f":brain: Loading RL agent from {model_path}")
            self.rl_agent = PPO.load(model_path)
            self.enabled = True
            logger.info(":white_check_mark: RL agent loaded successfully")
            return True
        except Exception as e:
            logger.error(f":x: Failed to load RL agent: {e}\n{traceback.format_exc()}")
            self.enabled = False
            return False
    
    async def get_observation(self) -> Optional[np.ndarray]:
        """
        Get current observation from environment
        Returns observation array or None if failed
        """
        if not self.enabled:
            return None
            
        try:
            # Get observation from environment
            observation = await self._build_observation()
            if observation is None:
                return None
                
            self.last_observation = observation
            return observation
        except Exception as e:
            logger.error(f":x: Error getting observation: {e}", exc_info=True)
            return None
    
    async def _build_observation(self) -> Optional[np.ndarray]:
        """
        Build observation vector from current market data
        Returns numpy array or None if data not available
        """
        try:
            # Get current market data from state
            market_data = await self._get_market_data()
            if not market_data:
                return None
                
            # Build observation vector based on RL config
            observation = np.zeros(rl_config.OBSERVATION_SPACE_SIZE)
            
            # Fill observation with market data according to feature mapping
            for feature_name, index in rl_config.OBSERVATION_FEATURES.items():
                if feature_name in market_data:
                    observation[index] = market_data[feature_name]
                    
            return observation
        except Exception as e:
            logger.error(f":x: Error building observation: {e}", exc_info=True)
            return None
    
    async def _get_market_data(self) -> Dict[str, Any]:
        """
        Get current market data from state and database
        Returns dictionary of market features
        """
        try:
            # Shortened timeframes for meme coin volatility (1h instead of 24h)
            timeframe = 3600  # 1 hour in seconds
            market_data = {
                'current_price': await self.state.get_current_sol_price(),
                'portfolio_value': await self.state.get_portfolio_value(),
                'token_count': len(await self.state.get_active_positions()),
                'volume': await self.db_client.get_volume(timeframe),  # Shorter volume window
                'market_cap': await self.db_client.get_market_cap(timeframe),  # Recent market cap
                'liquidity_score': await self.db_client.get_liquidity_score(timeframe),
                'social_score': await self.db_client.get_social_score(timeframe),
                'price_change_1h': await self.db_client.get_price_change(timeframe),  # Unified timeframe
                'volatility': await self.db_client.get_volatility(timeframe),
                'buy_pressure': await self.db_client.get_buy_pressure(timeframe),
                'sell_pressure': await self.db_client.get_sell_pressure(timeframe),
                'rugpull_risk': await self.db_client.get_rugpull_risk(timeframe)
            }
            
            # Validate and normalize data
            for key, value in market_data.items():
                if value is None or not isinstance(value, (int, float)):
                    market_data[key] = 0.0
                else:
                    market_data[key] = float(value)
                    
            return market_data
        except Exception as e:
            logger.error(f":x: Error getting market data: {e}", exc_info=True)
            return {}
    
    def get_action(self, observation: np.ndarray) -> Optional[np.ndarray]:
        """
        Get action from RL agent based on observation
        Returns action array or None if failed
        """
        if not self.enabled or self.rl_agent is None:
            return None
            
        try:
            action, _states = self.rl_agent.predict(observation, deterministic=True)
            self.last_action = action
            return action
        except Exception as e:
            logger.error(f":x: Error getting RL action: {e}", exc_info=True)
            return None
    
    def apply_action(self, action: np.ndarray) -> Dict[str, Any]:
        """
        Apply RL action to update trading parameters
        Returns dictionary of updated parameters
        """
        if not self.enabled or not action.any():
            return {}
            
        try:
            # Validate action against parameter constraints
            validated = self._validate_action(action)
            
            # Convert action to parameter updates
            updates = self._action_to_parameters(validated)
            
            # Store in history
            self.param_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': action.tolist(),
                'updates': updates,
                'last_config': self.state.get_config()
            })
            
            logger.debug(f":chart_with_upwards_trend: Applied RL action: {updates}")
            return updates
        except Exception as e:
            logger.error(f":x: Error applying RL action: {e}", exc_info=True)
            return {}
    
    def _validate_action(self, action: np.ndarray) -> np.ndarray:
        """
        Validate and clip action values to valid ranges
        """
        if not RL_AVAILABLE or not rl_config.RL_ACTION_BOUNDS:
            return action
            
        # Clip action values to valid ranges
        for i, (low, high) in enumerate(rl_config.RL_ACTION_BOUNDS):
            action[i] = np.clip(action[i], low, high)
            
        return action
    
    def _action_to_parameters(self, action: np.ndarray) -> Dict[str, Any]:
        """
        Convert RL action vector to configuration parameters
        """
        parameters = {}
        
        # Map action values to parameter names based on RL config
        for i, (param_name, default, low, high) in enumerate(rl_config.RL_TUNABLE_PARAMETERS):
            try:
                # Scale action value to parameter range
                normalized = action[i]
                value = low + (normalized - rl_config.ACTION_MIN) * (high - low) / (rl_config.ACTION_MAX - rl_config.ACTION_MIN)
                
                # Apply type conversion
                if isinstance(default, int):
                    value = int(round(value))
                elif isinstance(default, bool):
                    value = bool(value > 0.5)
                    
                parameters[param_name] = value
            except Exception as e:
                logger.error(f":x: Error converting action {i} to parameter {param_name}: {e}")
                continue
                
        return parameters
    
    async def update_configuration(self) -> None:
        """
        Get observation, predict action, and update configuration
        """
        if not self.enabled:
            return
            
        observation = await self.get_observation()
        if observation is None:
            return
            
        action = self.get_action(observation)
        if not action.any():
            return
            
        updates = self.apply_action(action)
        if updates:
            # Update global configuration
            self.state.update_config(updates)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current RL agent status and statistics
        """
        return {
            'enabled': self.enabled,
            'initialized': self.rl_initialized,
            'agent_loaded': self.rl_agent is not None,
            'last_action': self.last_action.tolist() if self.last_action is not None else None,
            'last_observation': self.last_observation.tolist() if self.last_observation is not None else None,
            'param_history_size': len(self.param_history),
            'config': self.state.get_config(['RL_*'])
        }