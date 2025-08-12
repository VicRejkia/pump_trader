# rl_agent/agents/ppo_agent.py
"""
Factory function for creating and configuring the PPO agent.

This module provides a centralized function to instantiate a Proximal Policy
Optimization (PPO) agent from the Stable Baselines 3 library, using
hyperparameters suggested by an Optuna trial.
"""

from typing import Dict, Any
import gymnasium as gym
import optuna
import torch as th
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy

def create_ppo_agent(
    env: gym.Env,
    trial: optuna.trial.Trial,
    device: str = 'cpu' #'cuda'
) -> PPO:
    """Creates a PPO agent with hyperparameters suggested by an Optuna trial.

    This function constructs the neural network architecture and sets the key
    PPO algorithm hyperparameters based on the ranges defined within the
    Optuna study, allowing for efficient hyperparameter optimization.

    Args:
        env: The OpenAI Gym environment the agent will be trained on.
        trial: The Optuna trial object that suggests hyperparameter values.
        device: The device to run the agent on ('cuda' or 'cpu').

    Returns:
        An initialized Stable Baselines 3 PPO agent instance.
    """
    # 1. Suggest Neural Network Architecture Parameters
    n_layers = trial.suggest_int('n_layers', 2, 4)
    layer_size = trial.suggest_categorical('layer_size', [64, 128, 256, 512])
    
    policy_kwargs: Dict[str, Any] = {
        "activation_fn": th.nn.ReLU,
        "net_arch": {
            "pi": [layer_size] * n_layers,  # Policy network
            "vf": [layer_size] * n_layers   # Value network
        }
    }

    # 2. Suggest Core RL Algorithm Hyperparameters
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    gamma = trial.suggest_float('gamma', 0.95, 0.999)
    n_steps = trial.suggest_categorical('n_steps', [1024, 2048, 4096, 8192])
    batch_size = trial.suggest_categorical('batch_size', [64, 128, 256])
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.02)  # Entropy coefficient for exploration
    clip_range = trial.suggest_categorical('clip_range', [0.1, 0.2, 0.3])
    gae_lambda = trial.suggest_float('gae_lambda', 0.9, 1.0) # GAE lambda for advantage estimation

    # Ensure batch_size is not greater than n_steps
    if batch_size > n_steps:
        # In Optuna, it's better to prune than to adjust. This trial is invalid.
        raise optuna.exceptions.TrialPruned(
            f"Pruning trial: batch_size ({batch_size}) > n_steps ({n_steps})."
        )
    
    # 3. Instantiate and return the PPO agent
    model = PPO(
        policy=ActorCriticPolicy,
        env=env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=10,  # Typically fixed at 10 for PPO
        gamma=gamma,
        gae_lambda=gae_lambda,
        clip_range=clip_range,
        ent_coef=ent_coef,
        policy_kwargs=policy_kwargs,
        tensorboard_log=None,  # Handled by the training script's callbacks
        verbose=0,             # Keep logs clean during HPO
        device=device
    )
    
    return model