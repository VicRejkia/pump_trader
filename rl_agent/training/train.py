# rl_agent/training/train.py
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

    Command:
    python rl_agent/etl/prepare_rl_dataset.py --start-date <START> --end-date <END> --output-version 1.0

PHASE 1: HYPERPARAMETER TUNING (tune)
Find the best model settings using Optuna, with all trials logged to MLflow.

    Command:
    python rl_agent/training/train.py tune

PHASE 2: NEW MODEL TRAINING (train)
Train a new model from scratch using the best parameters from a tuning run.

    Command:
    python rl_agent/training/train.py train --params-path <PATH_TO_DOWNLOADED_JSON> --name <MODEL_NAME>

PHASE 3 & 4: CONTINUE OR FINETUNE
Resume a previous training run or fine-tune an existing model.

    Command:
    python rl_agent/training/train.py continue --model-path <PATH_TO_MODEL.zip> --parent-run-id <RUN_ID> --name <NEW_NAME>
"""
import asyncio
import json
import os
import sys
import argparse
import time
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List
from functools import partial
import pandas as pd
import multiprocessing
import random

# --- Project Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Third-Party Imports ---
import numpy as np
import optuna
import torch as th
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, CallbackList
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.evaluation import evaluate_policy
from optuna.samplers import TPESampler
from stable_baselines3.common.logger import configure

# --- MLflow Integration ---
import mlflow
from mlflow.tracking import MlflowClient
from rl_agent.mlflow_model import log_sb3_model

# --- Local Application Imports ---
import nest_asyncio
from config.rl_config import get_config_for_mode, get_active_features
from bot_logger import logger, setup_logging
from rl_agent.agents.ppo_agent import create_ppo_agent
from rl_agent.data.data_manager import DataManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv

# Apply asyncio patch for environments that use it internally
nest_asyncio.apply()


# ==============================================================================
# MLflow and Experiment Constants
# ==============================================================================
MLFLOW_EXPERIMENT_TUNING = "PumpTrader.RL Hyperparameter Tuning"
MLFLOW_EXPERIMENT_TRAINING = "PumpTrader.RL PPO Training"
MLFLOW_EXPERIMENT_DATASET = "PumpTrader.RL Dataset Generation"


# ==============================================================================
# Helper Functions & Callbacks
# ==============================================================================

class AdvancedMlflowCallback(EvalCallback):
    """Logs key training and evaluation metrics to MLflow during the training loop."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_eval_reward = -np.inf

    def _on_step(self) -> bool:
        # Log training loss from the SB3 logger buffer
        for key in ["train/entropy_loss", "train/value_loss", "train/policy_gradient_loss", "train/approx_kl", "train/clip_fraction", "train/learning_rate"]:
            if key in self.logger.name_to_value:
                mlflow.log_metric(key.replace("/", "_"), self.logger.name_to_value[key], step=self.num_timesteps)

        # Log mean reward and length for episodes completed during training rollouts
        for info in self.locals.get("infos", []):
            if "episode" in info:
                mlflow.log_metric("rollout_ep_rew_mean", info["episode"]["r"], step=self.num_timesteps)
                mlflow.log_metric("rollout_ep_len_mean", info["episode"]["l"], step=self.num_timesteps)
        
        # Trigger the parent class's evaluation logic
        if not super()._on_step():
            return False

        # Log evaluation metrics only when a new evaluation has been performed
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
            logger.error(f"MLflow experiment '{MLFLOW_EXPERIMENT_DATASET}' not found.")
            return None
        
        # Search for the latest run that was successful
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

def objective(trial: optuna.trial.Trial, rl_config: Dict, train_mints: List[str], eval_mints: List[str]) -> float:
    """An Optuna objective function that trains and evaluates a model for one trial."""
    with mlflow.start_run(nested=True):
        train_env, eval_env = None, None
        try:
            # Create a DataManager for a small, random subset of tokens to speed up tuning
            train_subset = random.sample(train_mints, min(len(train_mints), 50))
            eval_subset = random.sample(eval_mints, min(len(eval_mints), 10))
            train_dm = DataManager(rl_config)
            train_dm.load_and_prepare_data(mints_to_load=train_subset, verbose=False)
            train_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(train_dm, rl_config, silent=True))])
            
            # Sample hyperparameters and log them
            params = sample_ppo_params(trial, n_envs=1)
            if params["policy_kwargs"]["activation_fn"] == 'ReLU':
                params["policy_kwargs"]["activation_fn"] = th.nn.ReLU
            mlflow.log_params(params)
            
            # Train the model
            model = PPO("MlpPolicy", train_env, device=rl_config.get('DEVICE', 'cpu'), verbose=0, **params)
            model.learn(total_timesteps=rl_config['PPO_TIMESTEPS_PER_TRIAL'])
            
            # Evaluate the model
            eval_dm = DataManager(rl_config)
            eval_dm.load_and_prepare_data(mints_to_load=eval_subset, verbose=False)
            eval_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(eval_dm, rl_config, silent=True))])
            
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

async def run_hyperparameter_tuning(rl_config: Dict[str, Any]):
    """Orchestrates the Optuna hyperparameter tuning process."""
    logger.info("PHASE 1: Starting Hyperparameter Tuning.")
    
    # Load all available mints and split them for the tuning study
    data_provider = DataManager(rl_config=rl_config)
    if not data_provider.load_and_prepare_data():
        logger.error("Failed to load data from feature store. Aborting tuning."); return
    train_mints, eval_mints = data_provider.get_split_token_mints()

    mlflow.set_experiment(MLFLOW_EXPERIMENT_TUNING)
    with mlflow.start_run(run_name=f"OptunaStudy_{datetime.now().strftime('%Y%m%d-%H%M%S')}"):
        mlflow.log_params({"n_trials": rl_config['OPTUNA_N_TRIALS'], "timeout": rl_config['OPTUNA_TIMEOUT_SECONDS']})
        
        # Create and run the Optuna study
        study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
        objective_with_args = partial(objective, rl_config=rl_config, train_mints=train_mints, eval_mints=eval_mints)
        study.optimize(objective_with_args, n_trials=rl_config['OPTUNA_N_TRIALS'], n_jobs=1, gc_after_trial=True)

        logger.info(f"Tuning finished. Best trial: #{study.best_trial.number} with reward: {study.best_trial.value:.4f}")
        mlflow.log_params(study.best_trial.params)
        mlflow.log_metric("best_trial_value", study.best_trial.value)
        
        # Save the best parameters as a JSON artifact in MLflow
        best_params = study.best_trial.params
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp:
            json.dump(best_params, tmp, indent=4); tmp_path = tmp.name
        try:
            mlflow.log_artifact(tmp_path, artifact_path="best_params.json")
            logger.info("✅ Best hyperparameters logged to MLflow.")
        finally: os.remove(tmp_path)

def make_env_lazy(rank: int, rl_config: Dict, mint_chunks: List[List[str]], seed: int = 0):
    """Factory function to create a lazy-loading environment for a subprocess."""
    def _init():
        data_manager = DataManager(rl_config=rl_config)
        # Each subprocess loads only its assigned slice of data
        data_manager.load_and_prepare_data(mints_to_load=mint_chunks[rank], verbose=False)
        env = MemeCoinEnv(data_manager, rl_config, silent=True)
        env.reset(seed=seed + rank)
        return Monitor(env)
    return _init

async def run_model_training(rl_config: Dict[str, Any], args: argparse.Namespace):
    """Orchestrates the main model training, continuation, or fine-tuning process."""
    mlflow.set_experiment(MLFLOW_EXPERIMENT_TRAINING)
    
    with mlflow.start_run(run_name=f"{args.name}-{args.action}") as run:
        logger.info(f"Starting model '{args.action}' with MLflow run '{run.info.run_name}'.")
        # Create a temporary local directory for this run's artifacts
        staging_dir = os.path.abspath(f"./.rl_staging/{run.info.run_id}")
        os.makedirs(staging_dir, exist_ok=True)
        
        vec_env, eval_env = None, None  # Define to ensure they exist for the finally block
        try:
            # --- 1. Log Run Parameters & Configs ---
            mlflow.log_params(rl_config)
            mlflow.log_param("action", args.action)
            if hasattr(args, 'parent_run_id') and args.parent_run_id:
                mlflow.set_tag("continued_from", args.parent_run_id)
            if hasattr(args, 'params_path') and args.params_path:
                mlflow.log_artifact(args.params_path, "config")
            
            # --- 2. Log Dataset as Input (Best Practice) ---
            logger.info("Finding and logging input dataset from ETL run...")
            dataset_run = find_latest_dataset_run()
            if dataset_run:
                # This creates a traceable link between this training run and the data it used
                mlflow.log_input(mlflow.get_run(dataset_run.info.run_id).inputs.dataset_inputs[0].dataset)
            else:
                logger.error("No dataset found from ETL runs. Please run the ETL first. Aborting.")
                return

            # --- 3. Prepare Data & Environments ---
            logger.info("Loading data from feature store and preparing environments...")
            data_manager = DataManager(rl_config)
            if not data_manager.load_and_prepare_data(): return
            train_mints, eval_mints = data_manager.get_split_token_mints()

            # Distribute training tokens across available CPU cores for parallelization
            n_cpu = rl_config['N_CPU']
            mint_chunks = [c.tolist() for c in np.array_split(train_mints, n_cpu) if c.size > 0]
            vec_env = SubprocVecEnv([make_env_lazy(i, rl_config, mint_chunks) for i in range(len(mint_chunks))])
            eval_env = DummyVecEnv([make_env_lazy(0, rl_config, [eval_mints])])

            # --- 4. Initialize or Load Model ---
            model, reset_num_timesteps = None, True
            tensorboard_log_path = os.path.join(staging_dir, "tensorboard_logs")

            if args.action == 'train':
                with open(args.params_path, 'r') as f: hyperparams = json.load(f)
                model = create_ppo_agent(vec_env, hyperparams, rl_config['DEVICE'], tensorboard_log_path)
            elif args.action in ['continue', 'finetune']:
                model = PPO.load(args.model_path, env=vec_env, device=rl_config['DEVICE'])
                model.set_logger(configure(tensorboard_log_path, ["tensorboard"]))
                reset_num_timesteps = False
                if args.action == 'finetune' and hasattr(args, 'learning_rate') and args.learning_rate:
                    model.learning_rate = args.learning_rate
            if not model: logger.error("Model could not be initialized. Aborting."); return

            # --- 5. Set Up Callbacks & Start Training ---
            chk_cb = CheckpointCallback(max(rl_config['PPO_EVAL_FREQ']//n_cpu,1), os.path.join(staging_dir, "models"), "checkpoint")
            adv_cb = AdvancedMlflowCallback(eval_env, best_model_save_path=os.path.join(staging_dir, "models"), log_path=os.path.join(staging_dir, "logs"), eval_freq=max(rl_config['PPO_EVAL_FREQ']//n_cpu,1))
            
            logger.info("🚀 Starting model training...")
            model.learn(total_timesteps=rl_config['PPO_FINAL_MODEL_TIMESTEPS'], callback=CallbackList([chk_cb, adv_cb]), reset_num_timesteps=reset_num_timesteps)

            # --- 6. Save, Log, and Register Final Model ---
            final_model_path = os.path.join(staging_dir, "models", "final_model.zip")
            model.save(final_model_path)
            mlflow.log_artifacts(staging_dir, artifact_path="training_outputs") # Log all artifacts

            # Load the best performing model for registration
            best_model_path = os.path.join(staging_dir, "models", "best_model.zip")
            model_to_log = PPO.load(best_model_path if os.path.exists(best_model_path) else final_model_path)
            
            # Log the model to MLflow in the pyfunc format for serving
            obs = eval_env.reset()
            input_example = np.asarray(obs[0] if isinstance(obs, np.ndarray) and obs.ndim > 1 else obs)
            log_sb3_model(model_to_log, args.name, input_example=input_example, staging_path=staging_dir)

            logger.info("✅ Training finished. Model and results logged to MLflow.")
        finally:
            # --- 7. Cleanup ---
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
    
    subparsers.add_parser("tune", help="Run hyperparameter tuning.")
    p_train = subparsers.add_parser("train", help="Train a new model.")
    p_train.add_argument("--params-path", required=True); p_train.add_argument("--name", default="PPO_Model")
    
    p_cont = subparsers.add_parser("continue", help="Continue training.")
    p_cont.add_argument("--model-path", required=True); p_cont.add_argument("--parent-run-id", required=True); p_cont.add_argument("--name", default="PPO_Model")

    p_fine = subparsers.add_parser("finetune", help="Fine-tune a model.")
    p_fine.add_argument("--model-path", required=True); p_fine.add_argument("--parent-run-id", required=True); p_fine.add_argument("--name", default="PPO_Model"); p_fine.add_argument("--learning-rate", type=float)
    
    args = parser.parse_args()
    rl_config = get_config_for_mode(args.action)

    if args.action == 'tune': await run_hyperparameter_tuning(rl_config)
    else: await run_model_training(rl_config, args)

if __name__ == "__main__":
    setup_logging(logger_name='rl_training')
    mlflow.set_tracking_uri("file:./data/rl_runs")
    if sys.platform in ['win32', 'darwin']: multiprocessing.freeze_support()
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("Process interrupted by user.")