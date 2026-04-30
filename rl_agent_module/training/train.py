# rl_agent_module/training/train.py
"""
Main script for the RL agent training workflow, centered around MLflow.

This script orchestrates the entire process from hyperparameter tuning to final
model training, continuation, and fine-tuning. It relies on MLflow as the
single source of truth for all experiment artifacts.

--------------------------------------------------------------------------------------
WORKFLOW INSTRUCTIONS
--------------------------------------------------------------------------------------
PRE-REQUISITE: DATA PREPARATION
Before running any training, the feature store must be populated using the ETL script.
This creates a dataset run in MLflow.

    Command (via rl_main.py):
    > 0) Generate/Update Feature Store (ETL)

PHASE 1: HYPERPARAMETER TUNING (tune)
Find the best model settings using Optuna, with all trials logged to MLflow.
Requires a dataset run ID to source the data.

    Command (via rl_main.py):
    > 1) Start Hyperparameter Tuning (Optuna)

PHASE 2: NEW MODEL TRAINING (train)
Train a new model from scratch using the best parameters from a tuning run.

    Command (via rl_main.py):
    > 2) Train a New Model

PHASE 3 & 4: CONTINUE OR FINETUNE
Resume a previous training run or fine-tune an existing model.

    Command (via rl_main.py):
    > 3) Continue Training a Model
    > 4) Perform Model Fine-Tuning
"""
import argparse
import asyncio
import json
import multiprocessing
import os
import random
import shutil
import sys
import tempfile
import time
from datetime import datetime
from functools import partial
from typing import Any, Dict, List

import pandas as pd

# --- Project Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Third-Party Imports ---
# --- MLflow Integration ---
import mlflow

# --- Local Application Imports ---
import nest_asyncio
import numpy as np
import optuna
import torch as th
from mlflow.data.pandas_dataset import PandasDataset
from mlflow.entities import RunStatus
from mlflow.tracking import MlflowClient
from optuna.samplers import TPESampler
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback, EvalCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.logger import configure
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from bot_logger import logger, setup_logging
from config.rl_config import RL_CONFIG, get_config_for_mode
from rl_agent_module.agents.ppo_agent import create_ppo_agent
from rl_agent_module.data.data_manager import DataManager
from rl_agent_module.environments.meme_coin_env import MemeCoinEnv
from rl_agent_module.mlflow_model import log_sb3_model
from rl_agent_module.utils.mlflow_utils import (
    build_tensorboard_command,
    find_mlflow_entity_by_run_id,
    get_parent_run_info,
)
from rl_agent_module.utils.script_utils import (
    generate_config_json,
    generate_readme,
    generate_tensorboard_launch_scripts,
)

# Apply asyncio patch for environments that use it internally
nest_asyncio.apply()

MLFLOW_EXPERIMENT_DATASET = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_DATASET"]



# ==============================================================================
# Helper Functions & Callbacks
# ==============================================================================

class AdvancedMlflowCallback(EvalCallback):
    """Logs key training and evaluation metrics to MLflow during the training loop."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_eval_reward = -np.inf

    def _on_step(self) -> bool:
        for key in ["train/entropy_loss", "train/value_loss", "train/policy_gradient_loss", "train/approx_kl", "train/clip_fraction", "train/learning_rate"]:
            if key in self.logger.name_to_value:
                mlflow.log_metric(key.replace("/", "_"), self.logger.name_to_value[key], step=self.num_timesteps)

        for info in self.locals.get("infos", []):
            if "episode" in info:
                mlflow.log_metric("rollout_ep_rew_mean", info["episode"]["r"], step=self.num_timesteps)
                mlflow.log_metric("rollout_ep_len_mean", info["episode"]["l"], step=self.num_timesteps)

        if not super()._on_step():
            return False

        if self.last_mean_reward != self._last_eval_reward:
            mlflow.log_metric("eval_mean_reward", self.last_mean_reward, step=self.num_timesteps)
            ep_lengths = self.eval_env.get_attr("episode_lengths")
            if ep_lengths and ep_lengths[0]:
                 mlflow.log_metric("eval_mean_ep_length", np.mean(ep_lengths[0]), step=self.num_timesteps)
            self._last_eval_reward = self.last_mean_reward
        return True


def find_latest_dataset_run() -> mlflow.entities.Run | None:
    """Finds the most recent successful MLflow run from the dataset generation experiment."""
    client = MlflowClient()
    try:
        exp = client.get_experiment_by_name(MLFLOW_EXPERIMENT_DATASET)
        if not exp:
            logger.error(f"MLflow experiment '{ MLFLOW_EXPERIMENT_DATASET }' not found.")
            return None

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=["start_time DESC"],
            max_results=1
        )
        return runs[0] if runs else None
    except Exception as e:
        logger.error(f"Could not fetch dataset run from MLflow: {e}", exc_info=True)
        return None


# ==============================================================================
# Optuna Objective for Hyperparameter Tuning
# ==============================================================================

def _valid_batch_sizes(n_steps: int, n_envs: int) -> List[int]:
    """Calculates valid batch sizes for PPO."""
    candidates = [32, 64, 128, 256, 512, 1024]
    total = n_steps * n_envs
    return [b for b in candidates if total % b == 0 and b <= total]

def sample_ppo_params(trial: optuna.trial.Trial, n_envs: int) -> Dict[str, Any]:
    """Defines the hyperparameter search space for Optuna."""
    n_steps = trial.suggest_categorical("n_steps", [1024, 2048, 4096])
    valid_bs = _valid_batch_sizes(n_steps, n_envs)
    if not valid_bs: raise optuna.exceptions.TrialPruned("No valid batch_size.")

    batch_size = trial.suggest_categorical("batch_size", valid_bs)
    pi_vf_layers = trial.suggest_categorical("pi_vf_layers", ["64,64", "128,128", "256,256"])

    return {
        "n_steps": n_steps, "batch_size": batch_size,
        "gamma": trial.suggest_float("gamma", 0.95, 0.9999),
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "ent_coef": trial.suggest_float("ent_coef", 1e-6, 1e-2, log=True),
        "gae_lambda": trial.suggest_float("gae_lambda", 0.8, 0.99),
        "clip_range": trial.suggest_float("clip_range", 0.1, 0.3),
        "vf_coef": trial.suggest_float("vf_coef", 0.5, 1.0),
        "max_grad_norm": trial.suggest_float("max_grad_norm", 0.3, 1.0),
        "policy_kwargs": {
            "activation_fn": "ReLU",
            "net_arch": {
                "pi": list(map(int, pi_vf_layers.split(','))),
                "vf": list(map(int, pi_vf_layers.split(',')))
            }
        },
    }

def objective(trial: optuna.trial.Trial, rl_config: Dict, train_mints: List[str], eval_mints: List[str], dataset_run_id: str) -> float:
    """An Optuna objective function that trains and evaluates a model for one trial."""
    with mlflow.start_run(nested=True, log_system_metrics=True):
        train_env, eval_env = None, None
        try:
            mlflow.log_params(rl_config)
            mlflow.log_param("action", "tuning")

            train_subset = random.sample(train_mints, min(len(train_mints), 50))
            eval_subset = random.sample(eval_mints, min(len(eval_mints), 10))

            train_dm = DataManager(rl_config, dataset_run_id=dataset_run_id)
            train_dm.load_and_prepare_data(mints_to_load=train_subset, verbose=False)
            train_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(train_dm, rl_config, silent=True))])

            params = sample_ppo_params(trial, n_envs=1)
            if params["policy_kwargs"]["activation_fn"] == 'ReLU':
                params["policy_kwargs"]["activation_fn"] = th.nn.ReLU
            mlflow.log_params(params)

            model = PPO("MlpPolicy", train_env, device=rl_config.get('DEVICE', 'cpu'), verbose=0, **params)
            model.learn(total_timesteps=rl_config['PPO_TIMESTEPS_PER_TRIAL'])

            eval_dm = DataManager(rl_config, dataset_run_id=dataset_run_id)
            eval_dm.load_and_prepare_data(mints_to_load=eval_subset, verbose=False)
            eval_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(eval_dm, rl_config, silent=True))])

            datasets, contexts, tags_list = [], [], []

            training_data = train_dm.get_training_data()
            if training_data is not None and not training_data.empty:
                train_dataset: PandasDataset = mlflow.data.from_pandas(training_data, name=f"training_set")
                datasets.append(train_dataset)
                contexts.append(f"training_set")
                tags_list.append({"num_tokens": str(len(train_mints))})

            eval_data = eval_dm.get_evaluation_data()
            if eval_data is not None and not eval_data.empty:
                eval_dataset: PandasDataset = mlflow.data.from_pandas(eval_data, name=f"evaluation_set")
                datasets.append(eval_dataset)
                contexts.append(f"evaluation_set")
                tags_list.append({"num_tokens": str(len(eval_mints))})

            if datasets:
                mlflow.log_inputs(
                    datasets=datasets,
                    contexts=contexts,
                    tags_list=tags_list
                )

            mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=5, deterministic=True)
            if not np.isfinite(mean_reward):
                raise optuna.exceptions.TrialPruned("Reward is not finite.")

            mlflow.log_metric("final_mean_reward", float(mean_reward))
            return float(mean_reward)
        except optuna.exceptions.TrialPruned as e:
            raise e
        finally:
            if train_env: train_env.close()
            if eval_env: eval_env.close()

# ==============================================================================
# Main Workflow Functions
# ==============================================================================

async def run_hyperparameter_tuning(rl_config: Dict[str, Any], dataset_run_id: str):
    """Orchestrates the Optuna hyperparameter tuning process."""
    logger.info("PHASE 1: Starting Hyperparameter Tuning.")

    data_provider = DataManager(rl_config=rl_config, dataset_run_id=dataset_run_id)
    if not data_provider.load_and_prepare_data():
        logger.error("Failed to load data. Aborting tuning."); return
    train_mints, eval_mints = data_provider.get_split_token_mints()

    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TUNING"])
    with mlflow.start_run(run_name=f"OptunaStudy_{datetime.now().strftime('%Y%m%d-%H%M%S')}", log_system_metrics=True):
        mlflow.log_params({"n_trials": rl_config['OPTUNA_N_TRIALS'], "timeout": rl_config['OPTUNA_TIMEOUT_SECONDS']})
        mlflow.set_tag("source_dataset_run_id", dataset_run_id)

        study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
        objective_with_args = partial(objective, rl_config=rl_config, train_mints=train_mints, eval_mints=eval_mints, dataset_run_id=dataset_run_id)
        study.optimize(objective_with_args, n_trials=rl_config['OPTUNA_N_TRIALS'], n_jobs=1, gc_after_trial=True)

        logger.info(f"Tuning finished. Best trial: #{study.best_trial.number} with reward: {study.best_trial.value:.4f}")
        mlflow.log_params(study.best_trial.params)
        mlflow.log_metric("best_trial_value", study.best_trial.value)

        best_params = study.best_trial.params
        if 'policy_kwargs' in best_params and 'activation_fn' in best_params['policy_kwargs']:
            if not isinstance(best_params['policy_kwargs']['activation_fn'], str):
                 best_params['policy_kwargs']['activation_fn'] = 'ReLU'

        mlflow.log_dict(best_params, "best_params.json")
        logger.info("✅ Best hyperparameters logged to MLflow as 'best_params.json'.")


def make_env_lazy(rank: int, rl_config: Dict, mint_chunks: List[List[str]], dataset_run_id: str, seed: int = 0):
    """Factory function to create a lazy-loading environment for a subprocess."""
    def _init():
        data_manager = DataManager(rl_config=rl_config, dataset_run_id=dataset_run_id)
        data_manager.load_and_prepare_data(mints_to_load=mint_chunks[rank], verbose=False)
        env = MemeCoinEnv(data_manager, rl_config, silent=True)
        env.reset(seed=seed + rank)
        return Monitor(env)
    return _init

async def run_model_training(rl_config: Dict[str, Any], args: argparse.Namespace):
    """Orchestrates the main model training, continuation, or fine-tuning process."""
    mlflow.set_experiment(RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TRAINING"])
    client = MlflowClient()

    with mlflow.start_run(run_name=f"{args.name}-{args.action}", log_system_metrics=True) as run:
        logger.info(f"Starting model '{args.action}' with MLflow run '{run.info.run_name}'.")
        staging_dir = os.path.abspath(f"./.rl_staging/{run.info.run_id}")
        os.makedirs(staging_dir, exist_ok=True)

        vec_env, eval_env = None, None
        try:

            mlflow.log_params(rl_config)

            srl_config_staging = os.path.join(staging_dir, "config")
            generate_config_json(rl_config, srl_config_staging)
            mlflow.log_artifacts(srl_config_staging, artifact_path="config")

            mlflow.log_param("action", args.action)

            current_run_name = run.data.tags.get("mlflow.runName", f"model_{run.info.run_id}")
            tensorboard_staging_path = os.path.join(staging_dir, "tensorboard_logs")

            parent_run_infos = []
            if hasattr(args, 'parent_run_id') and args.parent_run_id:
                parent_run_infos = get_parent_run_info(args.parent_run_id, client)

            initial_cmd = build_tensorboard_command(
                current_run_id=run.info.run_id,
                current_run_name=current_run_name,
                parent_run_infos=parent_run_infos,
                current_tensorboard_path=tensorboard_staging_path,
                client=client
            )
            logger.info(f"Run the Training TensorBoard UI with this command:\n`cmd:{initial_cmd}`")
            print(initial_cmd)

            mlflow.set_tag("source_dataset_run_id", args.dataset_run_id)

            if hasattr(args, 'parent_run_id') and args.parent_run_id:
                mlflow.set_tag("continued_from", args.parent_run_id)
            if hasattr(args, 'params_path') and args.params_path:
                mlflow.log_artifact(args.params_path, "config")

            dataset_run = find_mlflow_entity_by_run_id(args.dataset_run_id)
            if not dataset_run:
                logger.error("No dataset run found with ID: %s. Aborting.", args.dataset_run_id)
                return

            datasets, contexts, tags_list = [], [], []

            data_manager = DataManager(rl_config, dataset_run_id=args.dataset_run_id)
            if not data_manager.load_and_prepare_data(): return

            train_mints, eval_mints = data_manager.get_split_token_mints()

            training_data = data_manager.get_training_data()
            if training_data is not None and not training_data.empty:
                train_dataset: PandasDataset = mlflow.data.from_pandas(training_data, name=f"training_set")
                datasets.append(train_dataset)
                contexts.append(f"training_set")
                tags_list.append({"num_tokens": str(len(train_mints))})

            eval_data = data_manager.get_evaluation_data()
            if eval_data is not None and not eval_data.empty:
                eval_dataset: PandasDataset = mlflow.data.from_pandas(eval_data, name=f"evaluation_set")
                datasets.append(eval_dataset)
                contexts.append(f"evaluation_set")
                tags_list.append({"num_tokens": str(len(eval_mints))})

            if datasets:
                mlflow.log_inputs(
                    datasets=datasets,
                    contexts=contexts,
                    tags_list=tags_list
                )

            n_cpu = rl_config['N_CPU']
            mint_chunks = [c.tolist() for c in np.array_split(train_mints, n_cpu) if c.size > 0]

            # --- SAFETY CHECK: Ensure N_CPU is not too high for the dataset size ---
            if not mint_chunks:
                logger.error(f"Cannot train with N_CPU={n_cpu} as there are not enough tokens to split ({len(train_mints)} available).")
                logger.error("Please reduce N_CPU or use a larger dataset.")
                return

            vec_env = SubprocVecEnv([make_env_lazy(i, rl_config, mint_chunks, args.dataset_run_id) for i in range(len(mint_chunks))])
            eval_env = DummyVecEnv([make_env_lazy(0, rl_config, [eval_mints], args.dataset_run_id)])

            model, reset_num_timesteps = None, True

            if args.action == 'train':
                with open(args.params_path, 'r') as f: hyperparams = json.load(f)
                model = create_ppo_agent(vec_env, hyperparams, rl_config['DEVICE'], tensorboard_staging_path)
            elif args.action in ['continue', 'finetune']:
                model = PPO.load(args.model_path, env=vec_env, device=rl_config['DEVICE'])
                model.set_logger(configure(tensorboard_staging_path, ["tensorboard"]))
                reset_num_timesteps = False
                if args.action == 'finetune' and hasattr(args, 'learning_rate') and args.learning_rate:
                    model.learning_rate = args.learning_rate

            if not model:
                logger.error("Model could not be initialized. Aborting.")
                return

            chk_cb = CheckpointCallback(max(rl_config['PPO_EVAL_FREQ']//n_cpu,1), os.path.join(staging_dir, "models"), "checkpoint")
            adv_cb = AdvancedMlflowCallback(eval_env, best_model_save_path=os.path.join(staging_dir, "models"), log_path=os.path.join(staging_dir, "logs"), eval_freq=max(rl_config['PPO_EVAL_FREQ']//n_cpu,1))

            logger.info("🚀 Starting model training...")
            model.learn(
                total_timesteps=rl_config['PPO_FINAL_MODEL_TIMESTEPS'],
                callback=CallbackList([chk_cb, adv_cb]),
                reset_num_timesteps=reset_num_timesteps,
                tb_log_name=args.name
            )

            final_model_path = os.path.join(staging_dir, "models", "final_model.zip")
            model.save(final_model_path)

            for item in os.listdir(staging_dir):
                item_path = os.path.join(staging_dir, item)
                if os.path.isdir(item_path):
                    mlflow.log_artifacts(item_path, artifact_path=item)

            current_artifact_uri = run.info.artifact_uri.rstrip("/")
            final_tensorboard_path = f"{current_artifact_uri}/tensorboard_logs"

            final_cmd = build_tensorboard_command(
                current_run_id=run.info.run_id,
                current_run_name=current_run_name,
                parent_run_infos=parent_run_infos,
                current_tensorboard_path=final_tensorboard_path,
                client=client
            )

            mlflow.log_param("tensorboard_log_command", final_cmd)

            scripts_staging = os.path.join(staging_dir, "scripts")
            generate_tensorboard_launch_scripts(final_cmd, scripts_staging)
            generate_readme(final_cmd, scripts_staging)
            mlflow.log_artifacts(scripts_staging, artifact_path="scripts")

            best_model_path = os.path.join(staging_dir, "models", "best_model.zip")
            model_to_log = PPO.load(best_model_path if os.path.exists(best_model_path) else final_model_path)

            obs = eval_env.reset()
            input_example = np.asarray(obs[0] if isinstance(obs, np.ndarray) and obs.ndim > 1 else obs)

            log_sb3_model(
                model_to_log,
                args.name,
                input_example=input_example,
                staging_path=staging_dir,
                register_as=args.register_as
            )

            logger.info("✅ Training finished. Model and results logged to MLflow.")
        finally:
            if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
            if vec_env: vec_env.close()
            if eval_env: eval_env.close()

# ==============================================================================
# Script Entry Point
# ==============================================================================
async def main():
    """Parses command-line arguments and calls the appropriate workflow function."""
    parser = argparse.ArgumentParser(description="RL Agent Training Workflow")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # --- Shared parser for hardware and common training arguments ---
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--dataset-run-id", required=True, help="MLflow run ID of the dataset to use.")
    common_parser.add_argument("--register-as", help="If provided, registers the model with this name.")
    common_parser.add_argument("--device", type=str, help="Override the computation device (e.g., 'cuda', 'cpu').")
    common_parser.add_argument("--n-cpu", type=int, help="Override the number of CPU cores to use.")

    p_tune = subparsers.add_parser("tune", help="Run hyperparameter tuning.")
    p_tune.add_argument("--dataset-run-id", required=True, help="MLflow run ID of the dataset to use.")

    p_train = subparsers.add_parser("train", help="Train a new model.", parents=[common_parser])
    p_train.add_argument("--params-path", required=True); p_train.add_argument("--name", default="PPO_Model")

    p_cont = subparsers.add_parser("continue", help="Continue training.", parents=[common_parser])
    p_cont.add_argument("--model-path", required=True); p_cont.add_argument("--parent-run-id", required=True); p_cont.add_argument("--name", default="PPO_Model")

    p_fine = subparsers.add_parser("finetune", help="Fine-tune a model.", parents=[common_parser])
    p_fine.add_argument("--model-path", required=True); p_fine.add_argument("--parent-run-id", required=True); p_fine.add_argument("--name", default="PPO_Model"); p_fine.add_argument("--learning-rate", type=float)

    args = parser.parse_args()
    rl_config = get_config_for_mode(args.action)

    # --- Override config with command-line arguments if provided ---
    # This logic is now centralized here for all workflows
    if hasattr(args, 'device') and args.device:
        rl_config['DEVICE'] = args.device
        logger.info(f"Overriding DEVICE with command-line value: '{args.device}'")
    if hasattr(args, 'n_cpu') and args.n_cpu is not None:
        rl_config['N_CPU'] = args.n_cpu
        logger.info(f"Overriding N_CPU with command-line value: {args.n_cpu}")

    if args.action == 'tune':
        await run_hyperparameter_tuning(rl_config, args.dataset_run_id)
    else:
        await run_model_training(rl_config, args)

if __name__ == "__main__":
    setup_logging(logger_name='rl_training')
    mlflow.set_tracking_uri("http://127.0.0.1:8080")
    if sys.platform in ['win32', 'darwin']: multiprocessing.freeze_support()
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("Process interrupted by user.")
