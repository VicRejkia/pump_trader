# rl_agent/agents/ppo_agent.py
from typing import Dict, Any, Optional
import gymnasium as gym
import torch as th
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy

def create_ppo_agent(
    env: gym.Env,
    hyperparams: Dict[str, Any],
    device: str = 'cpu',
    tensorboard_log_path: Optional[str] = None
) -> PPO:
    """
    Creates a PPO agent from a dictionary of hyperparameters.
    This is used for final model training after tuning.
    """
    # Create a deep copy to avoid modifying the original dictionary
    agent_params = hyperparams.copy()

    # Extract policy_kwargs from the main hyperparams dict, or create a default
    policy_kwargs = agent_params.pop("policy_kwargs", {})
    if not policy_kwargs:
        # Define a default architecture if not specified in the params file
        pi_layers = agent_params.pop("pi_layers", [256, 256])
        vf_layers = agent_params.pop("vf_layers", [256, 256])
        policy_kwargs = {
            "activation_fn": th.nn.ReLU,
            "net_arch": {"pi": pi_layers, "vf": vf_layers}
        }
    else:
        # Ensure nested dicts like activation_fn are handled if they are strings
        if isinstance(policy_kwargs.get("activation_fn"), str):
             # For now, we only support ReLU, but this could be expanded
            if policy_kwargs["activation_fn"].lower() == 'relu':
                policy_kwargs["activation_fn"] = th.nn.ReLU
            else:
                policy_kwargs["activation_fn"] = th.nn.ReLU # Default fallback

    # Remove any lingering architecture keys from the top level
    agent_params.pop("pi_layers", None)
    agent_params.pop("vf_layers", None)
    agent_params.pop("pi_vf_layers", None)
    
    # Instantiate and return the PPO agent
    model = PPO(
        policy=ActorCriticPolicy,
        env=env,
        policy_kwargs=policy_kwargs,
        tensorboard_log=tensorboard_log_path,
        verbose=0,
        device=device,
        **agent_params  # Pass the rest of the hyperparameters
    )
    
    return model