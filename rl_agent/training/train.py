# rl_agent/training/train.py
"""
Main script for the RL agent training workflow, centered around MLflow.

This script orchestrates the entire process from hyperparameter tuning to final
model training, continuation, and fine-tuning. It relies on MLflow as the
single source of truth for all experiment artifacts.

--------------------------------------------------------------------------------------
WORKFLOW INSTRUCTIONS
--------------------------------------------------------------------------------------

PHASE 1: HYPERPARAMETER TUNING (tune)
Find the best model settings using Optuna, with all trials logged to MLflow.

    Command:
    python rl_agent/training/train.py tune

    Result:
    The best parameter set is logged as a 'best_params.json' artifact in the
    parent MLflow run for the tuning study.


PHASE 2: NEW MODEL TRAINING (train)
Train a new model from scratch using the best parameters from a tuning run.

    Command:
    python rl_agent/training/train.py train --params-path <PATH_TO_DOWNLOADED_JSON> --name <MODEL_NAME>

    Example:
    python rl_agent/training/train.py train --params-path /tmp/tmpxxxxxx/best_params.json --name "BaselineAgent_v1"

    Result:
    A new MLflow run is created. All outputs (checkpoints, TensorBoard logs, final model)
    are saved as artifacts within this run. The local filesystem remains clean.

    **IMPORTANT:** To monitor training, find the run in the MLflow UI, go to its
    artifacts, and find the TensorBoard log directory. Point TensorBoard to it:
    tensorboard --logdir <path_to_mlflow_run_artifacts>/training_outputs/tensorboard_logs


PHASE 3 & 4: CONTINUE OR FINETUNE
Resume a previous training run or fine-tune an existing model.

    Command:
    python rl_agent/training/train.py continue --model-path <PATH_TO_DOWNLOADED_MODEL.zip> --params-path <PATH_TO_JSON> --parent-run-id <RUN_ID> --name <NEW_NAME>

--------------------------------------------------------------------------------------
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

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import numpy as np
import optuna
import torch as th
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, CallbackList
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3 import PPO
from optuna.samplers import TPESampler
from stable_baselines3.common.logger import configure

# --- MLflow Integration ---
import mlflow
from mlflow.tracking import MlflowClient

from rl_agent.mlflow_model import log_sb3_model

import nest_asyncio
nest_asyncio.apply()

from config.rl_config import get_config_for_mode, get_active_features
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_agent.agents.ppo_agent import create_ppo_agent
from rl_agent.data.data_manager import DataManager
from rl_agent.data.cache_manager import CacheManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv


# ==============================================================================
# SECTION 2: CONSTANTS AND CALLBACKS
# ==============================================================================

MLFLOW_EXPERIMENT_TUNING = "PumpTrader.RL Hyperparameter Tuning"
MLFLOW_EXPERIMENT_TRAINING = "PumpTrader.RL PPO Training"

class AdvancedMlflowCallback(EvalCallback):
    """
    A custom callback that extends EvalCallback to log all key metrics
    directly to MLflow at the correct time in the training loop.
    """
    def __init__(self, *args, **kwargs):
        super(AdvancedMlflowCallback, self).__init__(*args, **kwargs)
        # Keep track of the last logged evaluation reward to avoid duplicate logging
        self._last_eval_reward = -np.inf

    def _on_step(self) -> bool:
        # --- 1. Log Training & Rollout Metrics ---
        # These are logged on every single step.

        # Log training loss metrics from the SB3 logger.
        # These values are from the *previous* training update, which is a known
        # limitation of SB3 callbacks, but they should now appear as step-plots
        # instead of flat lines.
        for key in [
            "train/entropy_loss", "train/value_loss", "train/policy_gradient_loss",
            "train/approx_kl", "train/clip_fraction", "train/learning_rate"
        ]:
            if key in self.logger.name_to_value:
                mlflow.log_metric(key.replace("/", "_"), self.logger.name_to_value[key], step=self.num_timesteps)

        # Log rollout metrics, which are available after an episode ends during training.
        for info in self.locals.get("infos", []):
            if "episode" in info:
                ep_info = info["episode"]
                mlflow.log_metric("rollout_ep_rew_mean", ep_info["r"], step=self.num_timesteps)
                mlflow.log_metric("rollout_ep_len_mean", ep_info["l"], step=self.num_timesteps)
        
        # --- 2. Run Evaluation & Log Metrics ---
        # This part runs the evaluation periodically (controlled by `eval_freq`).
        # The parent's _on_step() handles the evaluation logic.
        continue_training = super()._on_step()
        if continue_training is False:
            return False # Stop training if the parent callback requests it

        # Log evaluation metrics ONLY when a new evaluation has been performed.
        # We check if the `last_mean_reward` has changed since our last log.
        if self.last_mean_reward != self._last_eval_reward:
            mlflow.log_metric("eval_mean_reward", self.last_mean_reward, step=self.num_timesteps)
            
            # Safely get episode lengths from the monitor wrapper
            episode_lengths_list = self.eval_env.get_attr("episode_lengths")
            if episode_lengths_list and episode_lengths_list[0]:
                 mlflow.log_metric("eval_mean_ep_length", np.mean(episode_lengths_list[0]), step=self.num_timesteps)
            
            # Update our tracker
            self._last_eval_reward = self.last_mean_reward

        return True


def _valid_batch_sizes(n_steps: int, n_envs: int) -> List[int]:
    candidates = [32, 64, 128, 256, 512, 1024]
    total_steps = n_steps * n_envs
    return [b for b in candidates if total_steps % b == 0 and b <= total_steps]

def sample_ppo_params(trial: optuna.trial.Trial, n_envs: int) -> Dict[str, Any]:
    n_steps = trial.suggest_categorical("n_steps", [1024, 2048, 4096])
    valid_bs = _valid_batch_sizes(n_steps, n_envs)
    if not valid_bs:
        raise optuna.exceptions.TrialPruned("No valid batch_size for the chosen n_steps.")
    batch_size = trial.suggest_categorical("batch_size", valid_bs)
    if batch_size > n_steps * n_envs:
        raise optuna.exceptions.TrialPruned(f"Constraint violated: batch_size > n_steps * n_envs")
    pi_layers_str = trial.suggest_categorical("pi_layers", ["64,64", "128,128", "256,256"])
    vf_layers_str = trial.suggest_categorical("vf_layers", ["64,64", "128,128", "256,256"])
    params = {
        "n_steps": n_steps,
        "batch_size": batch_size,
        "gamma": trial.suggest_float("gamma", 0.95, 0.9999, log=False),
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "ent_coef": trial.suggest_float("ent_coef", 1e-6, 1e-2, log=True),
        "gae_lambda": trial.suggest_float("gae_lambda", 0.8, 0.99, log=False),
        "clip_range": trial.suggest_float("clip_range", 0.1, 0.3, log=False),
        "vf_coef": trial.suggest_float("vf_coef", 0.5, 1.0, log=False),
        "max_grad_norm": trial.suggest_float("max_grad_norm", 0.3, 1.0, log=False),
        "policy_kwargs": {
            "activation_fn": "ReLU",
            "net_arch": {
                "pi": list(map(int, pi_layers_str.split(','))),
                "vf": list(map(int, vf_layers_str.split(','))),
            },
        },
    }
    return params


def objective(trial: optuna.trial.Trial, rl_config: Dict, cache_manager: CacheManager, train_mints: List[str], eval_mints: List[str]) -> float:
    with mlflow.start_run(nested=True):
        train_env, eval_env = None, None
        try:
            SAMPLE_SIZE = 50
            EVAL_SAMPLE_SIZE = 10
            train_mints_subset = random.sample(train_mints, min(len(train_mints), SAMPLE_SIZE))
            eval_mints_subset = random.sample(eval_mints, min(len(eval_mints), EVAL_SAMPLE_SIZE))

            train_data_manager = DataManager(rl_config, db_client=None, cache_manager=cache_manager)
            asyncio.run(train_data_manager.load_and_prepare_data(mints_to_load=train_mints_subset, verbose=False))

            train_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(train_data_manager, rl_config, silent=True))])

            device = rl_config['DEVICE'] if th.cuda.is_available() else 'cpu'
            hyperparams = sample_ppo_params(trial, n_envs=1)

            if hyperparams["policy_kwargs"]["activation_fn"] == 'ReLU':
                hyperparams["policy_kwargs"]["activation_fn"] = th.nn.ReLU

            mlflow.log_params(hyperparams)

            model = PPO("MlpPolicy", train_env, device=device, verbose=0, **hyperparams)
            model.learn(total_timesteps=rl_config['PPO_TIMESTEPS_PER_TRIAL'])
            
            train_env.save("temp_vec_normalize.pkl")
            
            eval_data_manager = DataManager(rl_config, db_client=None, cache_manager=cache_manager)
            cached_sets = cache_manager.load_from_cache(verbose=False)
            evaluation_set_data = cached_sets.get('evaluation_set', {})

            valid_eval_dfs = [evaluation_set_data[m] for m in eval_mints_subset if m in evaluation_set_data]

            if not valid_eval_dfs:
                raise optuna.exceptions.TrialPruned("No valid evaluation data found for the selected subset of tokens.")

            eval_data_manager.training_data = pd.concat(valid_eval_dfs).sort_index()

            eval_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(eval_data_manager, rl_config, silent=True))])
            eval_env = VecNormalize.load("temp_vec_normalize.pkl", eval_env)
            eval_env.training = False
            eval_env.norm_reward = False
            
            mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=5, deterministic=True)

            if not np.isfinite(mean_reward):
                raise optuna.exceptions.TrialPruned("Reward is not finite.")

            mlflow.log_metric("final_mean_reward", float(mean_reward))
            return float(mean_reward)

        except optuna.exceptions.TrialPruned as e:
            raise e
        except Exception as e:
            logger.error(f"Error in trial #{trial.number}: {e}", exc_info=True)
            raise optuna.exceptions.TrialPruned(f"Unhandled exception: {e}")
        finally:
            if train_env: train_env.close()
            if eval_env: eval_env.close()

async def run_hyperparameter_tuning(rl_config: Dict[str, Any]):
    logger.info("PHASE 1: Starting Hyperparameter Tuning with MLflow.")
    db_client = None
    try:
        start_ts = datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
        end_ts = datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
        cache_manager = CacheManager(None, start_ts, end_ts, rl_config=rl_config, verbose=False)

        if not await cache_manager.is_cache_valid(verbose=True):
            logger.info("Cache is not valid. Regenerating...")
            db_client = DatabaseClient()
            await db_client.connect()
            data_generator = DataManager(rl_config, db_client, start_date=start_ts, end_date=end_ts)
            await data_generator.load_and_prepare_data()

        data_provider = DataManager(rl_config=rl_config, db_client=None, cache_manager=cache_manager)
        await data_provider.load_and_prepare_data()

        mints = data_provider.get_split_token_mints()
        if not mints:
            logger.error("Could not retrieve token mints from cache. Aborting.")
            return
        train_mints, eval_mints = mints
    finally:
        if db_client: await db_client.close()

    mlflow.set_experiment(MLFLOW_EXPERIMENT_TUNING)
    with mlflow.start_run(run_name=f"OptunaStudy_{datetime.now().strftime('%Y%m%d-%H%M%S')}"):
        mlflow.log_params({
            "n_trials": rl_config['OPTUNA_N_TRIALS'],
            "timeout": rl_config['OPTUNA_TIMEOUT_SECONDS'],
            "dataset_cache_name": os.path.basename(cache_manager.cache_dir)
        })

        # Now that the DataFrames are populated, we can safely get them for MLflow
        training_df = data_provider.get_training_data()
        if training_df is not None and not training_df.empty:
            # FIX: Use the actual directory path as the source
            input_data_train = mlflow.data.from_pandas(training_df)
            mlflow.log_input(input_data_train, context="training")
        else:
            logger.warning("Training data is empty, skipping MLflow input logging.")

        evaluation_df = data_provider.get_evaluation_data()
        if evaluation_df is not None and not evaluation_df.empty:
            # FIX: Use the actual directory path as the source
            input_data_eval = mlflow.data.from_pandas(evaluation_df)
            mlflow.log_input(input_data_eval, context="evaluation")
        else:
            logger.warning("Evaluation data is empty, skipping MLflow input logging.")

        
        study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
        objective_with_args = partial(objective, rl_config=rl_config, cache_manager=cache_manager, train_mints=train_mints, eval_mints=eval_mints)

        study.optimize(objective_with_args, n_trials=rl_config['OPTUNA_N_TRIALS'], n_jobs=1, gc_after_trial=True, timeout=rl_config['OPTUNA_TIMEOUT_SECONDS'])

        logger.info(f"Tuning finished. Best trial: #{study.best_trial.number} with reward: {study.best_trial.value:.4f}")

        mlflow.log_params(study.best_trial.params)
        mlflow.log_metric("best_trial_value", study.best_trial.value)

        best_params = study.best_trial.params
        if "pi_layers" in best_params and "vf_layers" in best_params:
            best_params["policy_kwargs"] = {
                "activation_fn": "ReLU",
                "net_arch": {
                    "pi": list(map(int, best_params.pop("pi_layers").split(','))),
                    "vf": list(map(int, best_params.pop("vf_layers").split(','))),
                }
            }

        staging_dir = os.path.abspath("./.rl_staging") # Define staging dir
        os.makedirs(staging_dir, exist_ok=True)      # Ensure it exists

        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False, dir=staging_dir) as tmp:
            json.dump(best_params, tmp, indent=4)
            tmp_path = tmp.name

        try:
            # Log the temp file as an artifact
            mlflow.log_artifact(tmp_path, artifact_path=f"best_params_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
            logger.info(f"✅ Best hyperparameters logged to MLflow as an artifact.")
        finally:
            # Ensure the temporary file is removed
            os.remove(tmp_path)


def make_env_lazy(rank: int, rl_config: Dict, mint_chunks: List[List[str]], seed: int = 0):
    def _init():
        start_ts = datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
        end_ts = datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
        data_manager = DataManager(rl_config=rl_config, start_date=start_ts, end_date=end_ts)
        mints_for_this_process = mint_chunks[rank]
        asyncio.run(data_manager.load_and_prepare_data(mints_to_load=mints_for_this_process, verbose=False))
        env = MemeCoinEnv(data_manager, rl_config, silent=True)
        env.reset(seed=seed + rank)
        return Monitor(env)
    return _init

async def run_model_training(rl_config: Dict[str, Any], args: argparse.Namespace):
    action_name = args.action
    model_name = args.name if hasattr(args, 'name') and args.name else "PPO_Model"
    run_name = f"{model_name}_{action_name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    mlflow.set_experiment(MLFLOW_EXPERIMENT_TRAINING)
    with mlflow.start_run(run_name=f"{model_name}-{args.action}") as run:
        logger.info(f"PHASE 2/3/4: Starting model '{action_name}' with MLflow run '{run_name}'.")

        # --- REFACTORED: Create a run-specific staging directory ---
        staging_dir = os.path.abspath(f"./.rl_staging/{run.info.run_id}")
        os.makedirs(staging_dir, exist_ok=True)
        logger.info(f"Using local staging directory: {staging_dir}")

        db_client = None
        try:
            # --- Log parameters and configs ---
            mlflow.log_param("timesteps", rl_config['PPO_FINAL_MODEL_TIMESTEPS'])
            if hasattr(args, 'parent_run_id') and args.parent_run_id:
                mlflow.set_tag("continued_from", args.parent_run_id)
            mlflow.set_tags({"project": "PumpTrader.RL", "phase": action_name})
            mlflow.log_param("action", args.action)
            mlflow.log_params(rl_config)
            if hasattr(args, 'params_path') and args.params_path:
                mlflow.log_artifact(args.params_path, "config")

            # --- Data setup ---
            # Log active features as a text artifact
            active_features = get_active_features(rl_config)
            mlflow.log_param("active_features_count", len(active_features))
            with open("active_features.txt", "w") as f:
                f.write("\n".join(active_features))
            mlflow.log_artifact("active_features.txt", "config")
            os.remove("active_features.txt")

            # Log config files for full reproducibility
            mlflow.log_artifact("config/rl_config.py", "config")

            logger.info("Validating data cache and preparing token lists...")
            start_ts = datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
            end_ts = datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
            
            # 1. Create the database client and connect
            db_client = DatabaseClient()
            await db_client.connect()

            # 2. Create a single, authoritative DataManager instance
            data_manager = DataManager(rl_config, db_client=db_client, start_date=start_ts, end_date=end_ts)

            # 3. This one call now handles everything: it will check the cache,
            #    and if it's invalid, it will use its db_client to build a new one.
            await data_manager.load_and_prepare_data()

            # 4. Log the cache manifest for reproducibility
            if data_manager.cache_manager:
                mlflow.log_param("dataset_cache_name", os.path.basename(data_manager.cache_manager.cache_dir))
                manifest_path = data_manager.cache_manager.manifest_path
                if os.path.exists(manifest_path):
                    mlflow.log_artifact(manifest_path, artifact_path="data_cache")

            # 5. Log the datasets to MLflow
            training_df = data_manager.get_training_data()
            if training_df is not None and not training_df.empty:
                input_data_train = mlflow.data.from_pandas(training_df)
                mlflow.log_input(input_data_train, context="training")
            else:
                logger.warning("Training data is empty, skipping MLflow input logging.")

            evaluation_df = data_manager.get_evaluation_data()
            if evaluation_df is not None and not evaluation_df.empty:
                input_data_eval = mlflow.data.from_pandas(evaluation_df)
                mlflow.log_input(input_data_eval, context="evaluation")
            else:
                logger.warning("Evaluation data is empty, skipping MLflow input logging.")

            # 6. Get the token mints from the now-populated data_manager
            mints = data_manager.get_split_token_mints()
            if mints is None:
                logger.error("Failed to get token mints after data preparation. Aborting.")
                return # Gracefully exit if no tokens were found/processed
            
            train_mints, eval_mints = mints

            n_cpu = rl_config['N_CPU']
            mint_chunks = [c.tolist() for c in np.array_split(train_mints, n_cpu) if c.size > 0]
            n_cpu = len(mint_chunks)
            logger.info(f"Distributing training data across {n_cpu} CPU core(s).")
            vec_env = (SubprocVecEnv if n_cpu > 1 else DummyVecEnv)([make_env_lazy(i, rl_config, mint_chunks) for i in range(n_cpu)])
            eval_mint_chunks = [c.tolist() for c in np.array_split(eval_mints, 1) if c.size > 0]
            eval_env = DummyVecEnv([make_env_lazy(0, rl_config, eval_mint_chunks)])

            # --- Model setup ---
            device = rl_config['DEVICE'] if th.cuda.is_available() else 'cpu'
            reset_num_timesteps = True
            model = None
            tensorboard_log_path = os.path.join(staging_dir, "tensorboard_logs")

            if action_name == 'train':
                # --- FIX for PermissionError on Windows ---
                # Copy the params file passed from the main script into the local staging
                # directory. This avoids cross-process file permission issues with temp files.
                try:
                    local_params_path = os.path.join(staging_dir, "hyperparams.json")
                    shutil.copy(args.params_path, local_params_path)
                    logger.info(f"Copied hyperparameters to local staging: {local_params_path}")
                    with open(local_params_path, 'r') as f:
                        hyperparams = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to copy or read hyperparameters from {args.params_path}: {e}", exc_info=True)
                    raise # Stop the training run if params can't be loaded

                model = create_ppo_agent(vec_env, hyperparams, device=device, tensorboard_log_path=tensorboard_log_path)
            elif action_name in ['continue', 'finetune']:
                model = PPO.load(args.model_path, env=vec_env, device=device)
                new_logger = configure(tensorboard_log_path, ["tensorboard"])
                model.set_logger(new_logger)
                reset_num_timesteps = False
                if action_name == 'finetune' and hasattr(args, 'learning_rate') and args.learning_rate:
                    model.learning_rate = args.learning_rate

            if not model:
                logger.error("Model could not be created or loaded. Aborting.")
                return

            # --- Callbacks ---
            checkpoint_callback = CheckpointCallback(
                save_freq=max(rl_config['PPO_EVAL_FREQ'] // n_cpu, 1),
                save_path=os.path.join(staging_dir, "models"),
                name_prefix="checkpoint"
            )
            advanced_mlflow_callback = AdvancedMlflowCallback(
                eval_env,
                best_model_save_path=os.path.join(staging_dir, "models"),
                log_path=os.path.join(staging_dir, "logs"),
                eval_freq=max(rl_config['PPO_EVAL_FREQ'] // n_cpu, 1)
            )
            callback_list = CallbackList([checkpoint_callback, advanced_mlflow_callback])

            # --- Training ---
            logger.info(f"🚀 Starting model training...")
            model.learn(
                total_timesteps=rl_config['PPO_FINAL_MODEL_TIMESTEPS'],
                callback=callback_list,
                reset_num_timesteps=reset_num_timesteps
            )

            # --- Save final model to staging dir ---
            final_model_path = os.path.join(staging_dir, "models", "final_model.zip")
            model.save(final_model_path)

            # --- Log entire staging directory to MLflow ---
            logger.info("Logging all training outputs from staging directory to MLflow...")
            mlflow.log_artifacts(staging_dir, artifact_path="training_outputs")

            # --- Log pyfunc model for registry/serving ---
            best_model_path = os.path.join(staging_dir, "models", "best_model.zip")
            model_to_log = PPO.load(best_model_path if os.path.exists(best_model_path) else final_model_path)

            #input_example = np.asarray(obs[0] if isinstance(obs, np.ndarray) and obs.ndim > 1 else obs)
            input_example = None
            try:
                # FIX 1: A VecEnv's reset() returns only the observation, not (obs, info)
                obs = eval_env.reset()
                if isinstance(obs, np.ndarray) and obs.ndim > 1:
                    obs = obs[0] # Handle VecEnv case by taking the first observation
                input_example = np.asarray(obs)
                logger.info(f"Successfully created input_example from live environment sample with shape: {input_example.shape}")

            except Exception as e:
                # FIX 2: Log the error and create a fallback placeholder
                logger.error(f"Could not sample observation from env, creating a dummy example from the observation space instead. Error: {e}", exc_info=False)
                if hasattr(eval_env, 'observation_space') and hasattr(eval_env.observation_space, 'sample'):
                    # This is the most reliable way to create a valid example
                    input_example = eval_env.observation_space.sample()
                    logger.info(f"Successfully created fallback input_example with shape: {input_example.shape}")

            model_uri = log_sb3_model(
                model_to_log,
                run_name=run_name,
                input_example=input_example,
                register_as=rl_config.get('MLFLOW_REGISTERED_MODEL_NAME'),
                staging_path=staging_dir,
            )
            mlflow.log_param("model_uri", model_uri)

            # If registered, optionally move to Staging automatically
            reg_name = rl_config.get('MLFLOW_REGISTERED_MODEL_NAME')
            if reg_name:
                try:
                    client = MlflowClient()
                    mv = client.get_latest_versions(reg_name, stages=["None"]) or []
                    # Transition the latest version created in this run
                    for v in mv:
                        if v.run_id == run.info.run_id:
                            client.transition_model_version_stage(reg_name, v.version, stage="Staging")
                            mlflow.set_tag("model_stage", "Staging")
                            break
                except Exception:
                    pass

            
            logger.info(f"✅ Training finished. Model and results logged to MLflow.")

        finally:
            # --- CRUCIAL: Cleanup the local staging directory ---
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)
                logger.info(f"Successfully cleaned up local staging directory: {staging_dir}")
            if db_client: await db_client.close()
            if 'vec_env' in locals() and vec_env: vec_env.close()
            if 'eval_env' in locals() and eval_env: eval_env.close()


async def main():
    parser = argparse.ArgumentParser(description="RL Agent Training Workflow")
    subparsers = parser.add_subparsers(dest="action", required=True, help="Action to perform")

    subparsers.add_parser("tune", help="Run hyperparameter tuning with Optuna.")

    parser_train = subparsers.add_parser("train", help="Train a new model from scratch.")
    parser_train.add_argument("--params-path", type=str, required=True, help="Path to best_params.json.")
    parser_train.add_argument("--name", type=str, default="PPO_Model", help="Custom name for the training run.")

    parser_continue = subparsers.add_parser("continue", help="Continue training an existing model.")
    parser_continue.add_argument("--model-path", type=str, required=True, help="Path to the model .zip checkpoint.")
    parser_continue.add_argument("--params-path", type=str, required=True, help="Path to the original best_params.json.")
    parser_continue.add_argument("--parent-run-id", type=str, required=True, help="MLflow run ID of the model being continued.")
    parser_continue.add_argument("--name", type=str, default="PPO_Model", help="Custom name for the new training run.")

    parser_finetune = subparsers.add_parser("finetune", help="Fine-tune an existing model.")
    parser_finetune.add_argument("--model-path", type=str, required=True, help="Path to the final model .zip.")
    parser_finetune.add_argument("--params-path", type=str, required=True, help="Path to the original best_params.json.")
    parser_finetune.add_argument("--parent-run-id", type=str, required=True, help="MLflow run ID of the model being fine-tuned.")
    parser_finetune.add_argument("--name", type=str, default="PPO_Model", help="Custom name for the new training run.")
    parser_finetune.add_argument("--learning-rate", type=float, help="Optional new learning rate for fine-tuning.")

    args = parser.parse_args()
    try:
        rl_config = get_config_for_mode(args.action)
    except ValueError as e:
        logger.error(e)
        return

    try:
        if args.action == 'tune':
            await run_hyperparameter_tuning(rl_config)
        else:
            await run_model_training(rl_config, args)
    except Exception as e:
        logger.error(f"A critical error occurred in main: {e}", exc_info=True)


if __name__ == "__main__":
    setup_logging(logger_name='rl_training')
    if sys.platform in ['win32', 'darwin']:
        multiprocessing.freeze_support()
        __spec__ = None

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
