# trading_rl_agent/agent.py
"""
This file is part of the trading bot's Reinforcement Learning module.
It has been reviewed and requires no changes for the current refactoring task.
Its logic for loading a model and its associated normalization statistics is
generic and will work correctly with the new file structure created by the
training scripts.
"""

import os
import pandas as pd
from typing import Dict, Any
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from bot_logger import logger
from typing import Optional

# A dummy env is needed to load VecNormalize stats, it's not used for steps.
# This import path is now updated to the new structure.
from trading_rl_agent.environments.solana_decision_env import SolanaDecisionEnv

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
            self.model = PPO.load(self.model_path, device='cpu')
            logger.info(f"🧠 Successfully loaded RL agent from {self.model_path}")

            base_path = os.path.splitext(self.model_path)[0]
            base_path = base_path.replace('_final', '').replace('_best', '')
            vec_normalize_path = f"{base_path}_vecnormalize.pkl"

            if os.path.exists(vec_normalize_path):
                # The dummy env needs a valid, though empty, structure.
                dummy_env = DummyVecEnv([lambda: SolanaDecisionEnv(df=pd.DataFrame(), full_token_data={'dummy': pd.DataFrame()})])
                self.vec_normalize = VecNormalize.load(vec_normalize_path, dummy_env)
                
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
        """
        if not self.model:
            logger.error("Cannot predict: RL model is not loaded.")
            return None

        try:
            if self.vec_normalize:
                normalized_obs = self.vec_normalize.normalize_obs(observation)
            else:
                normalized_obs = observation
            
            action, _ = self.model.predict(normalized_obs, deterministic=True)
            return action

        except Exception as e:
            logger.error(f"Error during RL agent prediction: {e}", exc_info=True)
            return None
