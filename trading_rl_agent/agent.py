# FILE: trading_rl_agent/agent.py

import os
import pandas as pd
from typing import Dict, Any
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from bot_logger import logger
from typing import Optional

# A dummy env is needed to load VecNormalize stats, it's not used for steps.
from trading_rl_agent.environments.solana_env import SolanaPortfolioEnv

class TradingAgent:
    """
    A synchronous wrapper for a trained Stable-Baselines3 agent to facilitate
    clean, non-blocking inference in the main asynchronous application.
    """
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"RL model file not found at: {model_path}")

        self.model_path = model_path
        self.model: Optional[PPO] = None
        self.vec_normalize: Optional[VecNormalize] = None
        self._load_model()

    def _load_model(self):
        """Loads the PPO model and its associated normalization statistics."""
        try:
            # Load the trained PPO agent
            self.model = PPO.load(self.model_path, device='cpu')
            logger.info(f"🧠 Successfully loaded RL agent from {self.model_path}")

            # Construct the path for the VecNormalize statistics
            # Assumes the naming convention from the training script
            base_path = os.path.splitext(self.model_path)[0]
            # Handle both '_final' and '_best' model naming conventions
            base_path = base_path.replace('_final', '').replace('_best', '')
            vec_normalize_path = f"{base_path}_vecnormalize.pkl"

            if os.path.exists(vec_normalize_path):
                # A dummy environment is required by SB3 to load VecNormalize stats
                dummy_env = DummyVecEnv([lambda: SolanaPortfolioEnv(token_data_map={'dummy': pd.DataFrame()})])
                self.vec_normalize = VecNormalize.load(vec_normalize_path, dummy_env)
                
                # Set to inference mode
                self.vec_normalize.training = False
                self.vec_normalize.norm_reward = False
                logger.info(f"✅ Loaded VecNormalize stats from: {vec_normalize_path}")
            else:
                logger.warning(f"⚠️ VecNormalize stats file not found at {vec_normalize_path}. Live observations will NOT be normalized.")

        except Exception as e:
            logger.critical(f"❌ Failed to load RL agent or its stats: {e}", exc_info=True)
            self.model = None
            self.vec_normalize = None

    def predict(self, observation: Dict[str, np.ndarray]) -> Optional[np.ndarray]:
        """
        Performs a synchronous prediction.
        This method is designed to be called via `asyncio.to_thread`.

        Args:
            observation: The raw observation dictionary from the live environment.

        Returns:
            The action (target portfolio weights) from the agent, or None if prediction fails.
        """
        if not self.model:
            logger.error("Cannot predict: RL model is not loaded.")
            return None

        try:
            # Normalize the observation if the VecNormalize object is available
            if self.vec_normalize:
                # SB3's normalize_obs expects a batch, so we add a leading dimension
                # and then remove it from the result.
                normalized_obs = self.vec_normalize.normalize_obs(observation)
            else:
                # If no normalizer, use the raw observation
                normalized_obs = observation
            
            # Get the deterministic action from the model
            action, _ = self.model.predict(normalized_obs, deterministic=True)
            return action

        except Exception as e:
            logger.error(f"Error during RL agent prediction: {e}", exc_info=True)
            return None