# FILE: trading_rl_agent/policies/custom_nets.py

import gymnasium as gym
import torch
from torch import nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from typing import Dict

class CustomCombinedExtractor(BaseFeaturesExtractor):
    """
    Custom feature extractor for the hierarchical trading agent.
    It processes a dictionary observation space containing:
    1. `token_data`: A time-series of market data for each token in the universe.
    2. `global_data`: A flat vector of portfolio and aggregate market stats.

    An LSTM is used to create a meaningful embedding of the `token_data` history,
    which is then concatenated with the `global_data` to form the final feature
    vector for the actor-critic policy networks.
    """
    def __init__(
        self,
        observation_space: gym.spaces.Dict,
        token_features_dim: int,
        global_features_dim: int,
        lstm_hidden_size: int = 128,
        combined_features_dim: int = 256,
    ):
        # The output dimension of this extractor will be the size of the combined features.
        super().__init__(observation_space, features_dim=combined_features_dim)

        self.token_features_dim = token_features_dim
        self.global_features_dim = global_features_dim
        self.lstm_hidden_size = lstm_hidden_size

        # --- Layer for processing token time-series data ---
        # The LSTM processes the history of each token independently.
        self.lstm = nn.LSTM(
            input_size=token_features_dim,
            hidden_size=lstm_hidden_size,
            num_layers=2, # Use a 2-layer LSTM for more complex pattern recognition
            batch_first=True, # Input tensor shape: (batch, seq, feature)
            dropout=0.1
        )

        # Flattening the LSTM outputs for all tokens into a single vector.
        # The observation space for token_data has shape (max_tokens, history_len, features).
        max_tokens = observation_space["token_data"].shape[0]
        lstm_output_flattened_dim = max_tokens * lstm_hidden_size

        # --- Linear layers to combine features ---
        # This layer combines the processed token data and the global data.
        self.combined_network = nn.Sequential(
            nn.Linear(lstm_output_flattened_dim + global_features_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, combined_features_dim),
            nn.ReLU()
        )

    def forward(self, observations: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Defines the forward pass of the feature extractor.
        """
        # --- Process Token Data with LSTM ---
        # Shape of token_data: (batch_size, max_tokens, history_len, token_features)
        token_data = observations["token_data"]
        batch_size = token_data.shape[0]
        max_tokens = token_data.shape[1]

        # Reshape for LSTM: (batch_size * max_tokens, history_len, token_features)
        # This processes all tokens in the universe in one go.
        token_data_reshaped = token_data.view(-1, token_data.shape[2], token_data.shape[3])
        
        # The LSTM outputs the sequence of hidden states and the final hidden/cell state.
        # We only need the final hidden state as the embedding of the sequence.
        _, (hidden_state, _) = self.lstm(token_data_reshaped)
        
        # The hidden_state has shape (num_layers, batch*max_tokens, hidden_size).
        # We take the output of the last layer.
        last_layer_hidden_state = hidden_state[-1] # Shape: (batch*max_tokens, hidden_size)

        # Reshape back to separate tokens: (batch_size, max_tokens, hidden_size)
        token_embeddings = last_layer_hidden_state.view(batch_size, max_tokens, self.lstm_hidden_size)
        
        # Flatten the embeddings into a single vector per batch item
        # Shape: (batch_size, max_tokens * hidden_size)
        flattened_token_embeddings = token_embeddings.reshape(batch_size, -1)

        # --- Concatenate with Global Data ---
        global_data = observations["global_data"]
        
        # Combine the processed token embeddings with the global features.
        combined_input = torch.cat([flattened_token_embeddings, global_data], dim=1)

        # --- Pass through the final linear network ---
        final_features = self.combined_network(combined_input)
        
        return final_features