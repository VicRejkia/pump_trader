
"""
Custom MLflow pyfunc wrapper for Stable-Baselines3 PPO models so they can be
logged, versioned, and served via the MLflow Model Registry.

Usage:
    from rl_agent.mlflow_model import log_sb3_model
    log_sb3_model(model, run_name, signature_dict, input_example, extra_artifacts)
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import mlflow
from mlflow import pyfunc
from mlflow.models.signature import ModelSignature, infer_signature
from mlflow.types import Schema, ColSpec

from stable_baselines3 import PPO


class SB3PPOWrapper(pyfunc.PythonModel):
    """A minimal pyfunc wrapper that loads and predicts with a PPO .zip."""

    def load_context(self, context):  # type: ignore[override]
        model_path = os.path.join(context.artifacts["sb3_zip"])  # full path
        self.model = PPO.load(model_path, device="cpu")

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        """
        Generates predictions from the model. The input is passed directly
        to the wrapped SB3 model's predict method.
        """
        # The SB3 PPO model's predict method can handle both single observations
        # (e.g., a NumPy array) and batches (e.g., a DataFrame or 2D array).
        # We pass the input directly without iteration.
        action, _ = self.model.predict(model_input, deterministic=True)
        return action


def _ensure_signature(signature_dict: Optional[Dict[str, Any]], input_example) -> ModelSignature:
    if signature_dict:
        inputs = Schema([ColSpec(x["type"], x["name"]) for x in signature_dict["inputs"]])
        outputs = Schema([ColSpec(x["type"], x["name"]) for x in signature_dict["outputs"]])
        return ModelSignature(inputs=inputs, outputs=outputs)
    # Fallback: infer from example
    return infer_signature(input_example, np.zeros((len(getattr(input_example, "shape", [1])), 1)))


def log_sb3_model(
    model: PPO,
    run_name: str,
    signature_dict: Optional[Dict[str, Any]] = None,
    input_example: Optional[Any] = None,
    extra_artifacts: Optional[Dict[str, str]] = None,
    register_as: Optional[str] = None,
) -> str:
    """Logs a PPO model as an MLflow pyfunc and optionally registers it.

    Returns the `model_uri` (e.g., "runs:/<run_id>/model").
    """
    run = mlflow.active_run()
    if run is None:
        raise RuntimeError("log_sb3_model must be called inside an active MLflow run")

    with tempfile.TemporaryDirectory() as tmp:
        sb3_zip = os.path.join(tmp, "model.zip")
        model.save(sb3_zip)

        artifacts = {"sb3_zip": sb3_zip}
        if extra_artifacts:
            artifacts.update(extra_artifacts)

        signature = None
        if input_example is not None:
            signature = _ensure_signature(signature_dict, input_example)

        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=SB3PPOWrapper(),
            artifacts=artifacts,
            signature=signature,
            input_example=input_example,
        )

    model_uri = f"runs:/{run.info.run_id}/model"

    if register_as:
        mv = mlflow.register_model(model_uri, register_as)
        mlflow.set_tag("registered_model_name", register_as)
        mlflow.set_tag("registered_model_version", mv.version)
        return f"models:/{register_as}/{mv.version}"

    return model_uri
