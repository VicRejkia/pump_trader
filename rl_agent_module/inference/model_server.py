# rl_agent_module/inference/model_server.py
"""
Manages the lifecycle of the production RL model for live inference.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import numpy as np
from stable_baselines3 import PPO

import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from bot_logger import logger


class RLModelServer:
    """
    A thread-safe server for loading a trained RL model and providing actions.

    This class encapsulates a Stable Baselines 3 model, providing a simple
    interface for getting predictions. It includes a crucial "hot-swap"
    feature to update the model on-the-fly without downtime, which is essential
    for continuous operation and retraining cycles.
    """

    def __init__(self, model_path: str, device: str = 'cpu'):
        """
        Initializes the RLModelServer.

        Args:
            model_path: The initial path to the trained model's .zip file.
            device: The computation device ('cpu' or 'cuda'). 'cpu' is
                    recommended for inference unless high throughput is needed.
        """
        self.model_path: Optional[str] = model_path
        self.device = device
        self.model: Optional[PPO] = None
        self.last_update_time: Optional[datetime] = None
        self.lock = asyncio.Lock()  # Lock to ensure atomic operations on the model

        self._load_initial_model()

    def _load_initial_model(self):
        """Loads the model specified during initialization."""
        logger.info(f"Attempting to load initial RL model from: {self.model_path}")
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Initial model file not found: {self.model_path}")
                return

            self.model = PPO.load(self.model_path, device=self.device)
            self.last_update_time = datetime.now(timezone.utc)
            logger.info(f"✅ Successfully loaded initial RL model. Ready for inference on '{self.device}'.")
        except Exception as e:
            logger.error(f"❌ Failed to load initial RL model from {self.model_path}: {e}", exc_info=True)
            self.model = None
            self.model_path = None

    async def get_action(self, observation: np.ndarray) -> Optional[np.ndarray]:
        """
        Predicts the next action for a given observation in a thread-safe manner.

        Args:
            observation: The current observation from the environment.

        Returns:
            The predicted action as a numpy array, or None if no model is loaded.
        """
        async with self.lock:
            if self.model is None:
                logger.warning("get_action called, but no model is loaded.")
                return None

            try:
                # Use deterministic=True for inference to get the most likely action
                action, _states = self.model.predict(observation, deterministic=True)
                return action
            except Exception as e:
                logger.error(f"Error during model prediction: {e}", exc_info=True)
                return None

    async def hot_swap_model(self, new_model_path: str) -> bool:
        """
        Atomically updates the currently loaded model with a new one from a file.

        This method is safe to call concurrently. It first loads the new model
        into memory. Only upon a successful load does it replace the existing
        model, ensuring the server remains operational even if the new model
        file is corrupted or invalid.

        Args:
            new_model_path: The file path to the new .zip model file.

        Returns:
            True if the model was successfully updated, False otherwise.
        """
        logger.info(f"Attempting to hot-swap model with: {new_model_path}")

        if not os.path.exists(new_model_path):
            logger.error(f"Hot-swap failed: New model file not found at '{new_model_path}'.")
            return False
            
        async with self.lock:
            if new_model_path == self.model_path:
                logger.warning("Hot-swap skipped: New model path is the same as the current one.")
                return True

            try:
                # Load the new model into a temporary variable first.
                # This is a critical safety check.
                new_model = PPO.load(new_model_path, device=self.device)

                # If loading succeeds, replace the old model and update metadata.
                self.model = new_model
                self.model_path = new_model_path
                self.last_update_time = datetime.now(timezone.utc)
                logger.info(f"✅ Model hot-swap successful. Now using model from '{new_model_path}'.")
                return True
            except Exception as e:
                logger.error(f"❌ Hot-swap failed: Could not load the new model. The server will continue using the old model. Error: {e}", exc_info=True)
                return False

    async def get_status(self) -> Dict[str, Any]:
        """
        Retrieves the current status of the model server in a thread-safe manner.

        Returns:
            A dictionary containing the server's status.
        """
        async with self.lock:
            return {
                "is_model_loaded": self.model is not None,
                "model_path": self.model_path,
                "device": self.device,
                "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None
            }