# rl_agent/training/train.py
"""
Haupt-Skript für den RL-Agenten Trainings-Workflow.

Dieses Skript steuert den gesamten Prozess von der Hyperparameter-Suche (Tuning)
bis zum finalen Training, dem Fortsetzen und dem Fine-Tuning von Modellen.
Die Steuerung erfolgt über Kommandozeilen-Argumente.

--------------------------------------------------------------------------------------
ANLEITUNG / WORKFLOW
--------------------------------------------------------------------------------------

Der empfohlene Workflow ist in mehrere Phasen unterteilt:

PHASE 1: HYPERPARAMETER FINDEN (tune)
Zuerst werden mit Optuna die besten Einstellungen für das Modell gesucht.

    Befehl:
    python rl_agent/training/train.py tune

    Ergebnis:
    Eine '.json'-Datei mit den besten Parametern wird in 'data/rl_models/' gespeichert.
    (z.B. best_params_20250813-014530.json)


PHASE 2: NEUES MODELL TRAINIEREN (train)
Mit den besten Parametern aus Phase 1 wird ein neues Modell von Grund auf trainiert.

    Befehl:
    python rl_agent/training/train.py train --params-path <PFAD_ZUR_JSON_DATEI> --name <MODELL_NAME>

    Beispiel:
    python rl_agent/training/train.py train --params-path data/rl_models/best_params_20250813-014530.json --name "BaselineAgent_24h"

    Ergebnis:
    Ein fertiges Modell wird in 'data/rl_models/' gespeichert. Checkpoints und TensorBoard-Logs
    landen im Ordner 'data/rl_logs/'.

    **WICHTIG:** Der Trainingsfortschritt wird jetzt mit TensorBoard überwacht.
    Starten Sie es in einem separaten Terminal mit dem Befehl:
    tensorboard --logdir data/rl_logs


PHASE 3 (Optional): TRAINING FORTSETZEN (continue)
Wenn ein langes Training unterbrochen wurde, kann es hiermit fortgesetzt werden.

    Befehl:
    python rl_agent/training/train.py continue --model-path <PFAD_ZUM_MODELL.zip>

    Beispiel:
    python rl_agent/training/train.py continue --model-path data/rl_logs/TIMESTAMP_BaselineAgent_24h/checkpoint_250000_steps.zip


PHASE 4 (Optional): MODELL OPTIMIEREN (finetune)
Ein bereits gutes Modell kann mit angepassten Parametern (z.B. einer niedrigeren
Lernrate) weiter trainiert werden.

    Befehl:
    python rl_agent/training/train.py finetune --model-path <PFAD_ZUM_MODELL.zip> --learning-rate 0.00001

    Beispiel:
    python rl_agent/training/train.py finetune --model-path data/rl_models/final_model.zip --learning-rate 0.00001

--------------------------------------------------------------------------------------
"""
import asyncio
import json
import os
import sys
import argparse
import time
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
# ADD THIS IMPORT for the custom callback
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, EvalCallback, CallbackList
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3 import PPO
from optuna.samplers import TPESampler
from stable_baselines3.common.logger import configure

# --- MLflow Integration ---
import mlflow
#import mlflow.stable_baselines3

import nest_asyncio
nest_asyncio.apply()

import config.rl_config as rl_cfg
import config.config as main_cfg
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_agent.agents.ppo_agent import create_ppo_agent
from rl_agent.data.data_manager import DataManager
from rl_agent.data.cache_manager import CacheManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv


# ==============================================================================
# SECTION 2: CONSTANTS AND NEW CALLBACK CLASS
# ==============================================================================

# --- MLflow Experiment Names ---
MLFLOW_EXPERIMENT_TUNING = "MemeCoin Hyperparameter Tuning"
MLFLOW_EXPERIMENT_TRAINING = "MemeCoin PPO Training"

# --- MLflow Integration ---
import mlflow

import config.rl_config as rl_cfg
import config.config as main_cfg
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_agent.agents.ppo_agent import create_ppo_agent
from rl_agent.data.data_manager import DataManager
from rl_agent.data.cache_manager import CacheManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv

# --- MLflow Experiment Names ---
MLFLOW_EXPERIMENT_TUNING = "MemeCoin Hyperparameter Tuning"
MLFLOW_EXPERIMENT_TRAINING = "MemeCoin PPO Training"

class MLflowLoggingCallback(BaseCallback):
    """
    A custom callback to log evaluation metrics to MLflow during training.
    """
    def __init__(self, verbose=0):
        super(MLflowLoggingCallback, self).__init__(verbose)

    def _on_step(self) -> bool:
        # Check if evaluation results are in the logs
        if 'eval/mean_reward' in self.logger.name_to_value:
            mean_reward = self.logger.name_to_value['eval/mean_reward']
            mlflow.log_metric("eval_mean_reward", mean_reward, step=self.num_timesteps)
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
    """
    Optuna objective function with MLflow nested runs for each trial.
    Each trial is logged as a separate run within a parent "Optuna Study" run.
    """
    # Start a nested MLflow run for this specific trial
    with mlflow.start_run(nested=True):
        # Log the hyperparameters suggested by Optuna for this trial
        mlflow.log_params(trial.params)

        train_env, eval_env = None, None
        try:
            # The rest of the function's logic remains the same...
            SAMPLE_SIZE = 50
            EVAL_SAMPLE_SIZE = 10
            train_mints_subset = random.sample(train_mints, min(len(train_mints), SAMPLE_SIZE))
            eval_mints_subset = random.sample(eval_mints, min(len(eval_mints), EVAL_SAMPLE_SIZE))

            train_data_manager = DataManager(db_client=None, cache_manager=cache_manager)
            asyncio.run(train_data_manager.load_and_prepare_data(mints_to_load=train_mints_subset, verbose=False))
            
            train_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(train_data_manager, rl_config, silent=True))])
            train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.0)

            device = rl_config['DEVICE'] if th.cuda.is_available() else 'cpu'
            hyperparams = sample_ppo_params(trial, n_envs=1)
            
            if hyperparams["policy_kwargs"]["activation_fn"] == 'ReLU':
                hyperparams["policy_kwargs"]["activation_fn"] = th.nn.ReLU

            model = PPO("MlpPolicy", train_env, device=device, verbose=0, **hyperparams)
            model.learn(total_timesteps=rl_config['PPO_TIMESTEPS_PER_TRIAL'])
            
            train_env.save("temp_vec_normalize.pkl")
            
            eval_data_manager = DataManager(db_client=None, cache_manager=cache_manager)
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

            # Log the final metric for this trial to MLflow
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
            if os.path.exists("temp_vec_normalize.pkl"):
                os.remove("temp_vec_normalize.pkl")

async def run_hyperparameter_tuning(rl_config: Dict[str, Any]):
    logger.info("PHASE 1: Starting Hyperparameter Tuning with MLflow.")
    
    # Data preparation logic remains the same
    db_client = None
    try:
        start_ts = datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
        end_ts = datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
        cache_manager = CacheManager(None, start_ts, end_ts, verbose=False)

        if not await cache_manager.is_cache_valid(verbose=True):
            logger.info("Cache is not valid. Regenerating...")
            db_client = DatabaseClient()
            await db_client.connect()
            data_generator = DataManager(db_client, start_date=start_ts, end_date=end_ts)
            await data_generator.load_and_prepare_data()
        
        data_provider = DataManager(db_client=None, cache_manager=cache_manager)
        mints = data_provider.get_split_token_mints()
        if not mints:
            logger.error("Could not retrieve token mints from cache. Aborting.")
            return
        train_mints, eval_mints = mints
    finally:
        if db_client: await db_client.close()

    # Set the MLflow experiment for this entire tuning process
    mlflow.set_experiment(MLFLOW_EXPERIMENT_TUNING)
    # Start a parent run to contain all Optuna trials
    with mlflow.start_run(run_name=f"OptunaStudy_{datetime.now().strftime('%Y%m%d-%H%M%S')}"):
        mlflow.log_param("n_trials", rl_config['OPTUNA_N_TRIALS'])
        mlflow.log_param("timeout_seconds", rl_config['OPTUNA_TIMEOUT_SECONDS'])
        
        study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
        objective_with_args = partial(objective, rl_config=rl_config, cache_manager=cache_manager, train_mints=train_mints, eval_mints=eval_mints)
        
        study.optimize(objective_with_args, n_trials=rl_config['OPTUNA_N_TRIALS'], n_jobs=1, gc_after_trial=True)
        
        logger.info(f"Tuning finished. Best trial: #{study.best_trial.number} with reward: {study.best_trial.value:.4f}")
        
        # Log the best trial's information to the parent run
        mlflow.log_params(study.best_trial.params)
        mlflow.log_metric("best_trial_reward", study.best_trial.value)

        best_params = study.best_trial.params
        # Re-add policy_kwargs for saving, as Optuna flattens it
        if "pi_layers" in best_params and "vf_layers" in best_params:
            best_params["policy_kwargs"] = {
                "activation_fn": "ReLU",
                "net_arch": {
                    "pi": list(map(int, best_params.pop("pi_layers").split(','))),
                    "vf": list(map(int, best_params.pop("vf_layers").split(','))),
                }
            }

        params_filename = f"best_params_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        params_path = os.path.join(rl_config['RL_MODELS_DIR'], params_filename)
        os.makedirs(rl_config['RL_MODELS_DIR'], exist_ok=True)
        with open(params_path, 'w') as f:
            json.dump(best_params, f, indent=4)

        # Log the resulting best_params.json file as an artifact of the parent run
        mlflow.log_artifact(params_path)
        logger.info(f"✅ Best hyperparameters saved to: {params_path} and logged to MLflow.")



def make_env_lazy(rank: int, rl_config: Dict, mint_chunks: List[List[str]], seed: int = 0):
    def _init():
        start_ts = datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
        end_ts = datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
        data_manager = DataManager(start_date=start_ts, end_date=end_ts)
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
    
    # Set the experiment and start the run
    mlflow.set_experiment(MLFLOW_EXPERIMENT_TRAINING)
    with mlflow.start_run(run_name=run_name):
        logger.info(f"PHASE 2/3/4: Starting model '{action_name}' with MLflow run '{run_name}'.")
        
        # --- Log parameters and configs ---
        mlflow.log_param("action_type", action_name)
        mlflow.log_param("n_cpu", rl_config['N_CPU'])
        mlflow.log_param("device", rl_config['DEVICE'])
        mlflow.log_param("timesteps", rl_config['PPO_FINAL_MODEL_TIMESTEPS'])
        if action_name == 'finetune' and hasattr(args, 'learning_rate') and args.learning_rate:
            mlflow.log_param("finetune_learning_rate", args.learning_rate)

        # Log active features as a text artifact
        active_features = rl_cfg.get_active_features()
        mlflow.log_param("active_features_count", len(active_features))
        with open("active_features.txt", "w") as f:
            f.write("\n".join(active_features))
        mlflow.log_artifact("active_features.txt", "config")
        os.remove("active_features.txt")

        # Log config files for full reproducibility
        mlflow.log_artifact("config/rl_config.py", "config")
        if action_name == 'train':
            mlflow.log_artifact(args.params_path, "config")
        
        # Environment and data setup logic remains the same
        # ... (pasting the data setup logic from your script for completeness) ...
        db_client = None
        try:
            logger.info("Validating data cache and preparing token lists...")
            start_ts = datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00"))
            end_ts = datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
            cache_manager = CacheManager(None, start_ts, end_ts, verbose=False)
            
            if not await cache_manager.is_cache_valid(verbose=True):
                db_client = DatabaseClient()
                await db_client.connect()
                data_generator = DataManager(db_client, start_date=start_ts, end_date=end_ts)
                await data_generator.load_and_prepare_data()

            data_provider = DataManager(cache_manager=cache_manager)
            mints = data_provider.get_split_token_mints()
            train_mints, eval_mints = mints

            n_cpu = rl_config['N_CPU']
            mint_chunks = [c.tolist() for c in np.array_split(train_mints, n_cpu) if c.size > 0]
            n_cpu = len(mint_chunks)
            logger.info(f"Distributing training data across {n_cpu} CPU core(s).")

            vec_env_cls = SubprocVecEnv if n_cpu > 1 else DummyVecEnv
            vec_env = vec_env_cls([make_env_lazy(i, rl_config, mint_chunks) for i in range(n_cpu)])

            eval_mint_chunks = [c.tolist() for c in np.array_split(eval_mints, 1) if c.size > 0]
            eval_env = DummyVecEnv([make_env_lazy(0, rl_config, eval_mint_chunks)])


            device = rl_config['DEVICE'] if th.cuda.is_available() else 'cpu'
            reset_num_timesteps = True
            model = None

            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            model_name = args.name if hasattr(args, 'name') and args.name else "PPO_Model"
            log_dir = os.path.join(rl_config['RL_LOGS_DIR'], f"{timestamp}_{model_name}")
            os.makedirs(log_dir, exist_ok=True)

            if action_name == 'train':
                logger.info(f"Training new model from hyperparameters: {args.params_path}")
                with open(args.params_path, 'r') as f:
                    hyperparams = json.load(f)
                model = create_ppo_agent(vec_env, hyperparams, device=device, tensorboard_log_path=log_dir)
            
            elif action_name in ['continue', 'finetune']:
                logger.info(f"Loading model from {args.model_path} to '{action_name}' training.")
                model = PPO.load(args.model_path, env=vec_env, device=device)
                # --- FIX START ---
                # Create a new logger instance for the new training session.
                # Do not try to access model.logger as it does not exist after loading.
                new_logger = configure(log_dir, ["tensorboard"])
                model.set_logger(new_logger)
                # --- FIX END ---
                reset_num_timesteps = False
                if action_name == 'finetune' and hasattr(args, 'learning_rate') and args.learning_rate:
                    new_lr = args.learning_rate
                    logger.info(f"Fine-tuning: Adjusting learning rate to {new_lr}")
                    model.learning_rate = new_lr

            if not model:
                logger.error("Model could not be created or loaded. Aborting.")
                return
                
            # --- Callbacks with MLflow ---
            log_dir = os.path.join(rl_config['RL_LOGS_DIR'], mlflow.active_run().info.run_id)
            os.makedirs(log_dir, exist_ok=True)
            
            checkpoint_callback = CheckpointCallback(save_freq=max(rl_config['PPO_EVAL_FREQ'] // n_cpu, 1), save_path=log_dir, name_prefix="checkpoint")
            eval_callback = EvalCallback(eval_env, best_model_save_path=log_dir, log_path=log_dir, eval_freq=max(rl_config['PPO_EVAL_FREQ'] // n_cpu, 1))
            mlflow_callback = MLflowLoggingCallback()
            callback_list = CallbackList([checkpoint_callback, eval_callback, mlflow_callback])
            
            # --- Training ---
            logger.info(f"🚀 Starting model training...")
            model.learn(
                total_timesteps=rl_config['PPO_FINAL_MODEL_TIMESTEPS'],
                callback=callback_list,
                reset_num_timesteps=reset_num_timesteps
            )

            # --- Log Final Model and Best Model ---
            final_model_path = os.path.join(log_dir, "final_model.zip")
            model.save(final_model_path)
            mlflow.log_artifact(final_model_path, "model")

            best_model_path = os.path.join(log_dir, "best_model.zip")
            if os.path.exists(best_model_path):
                mlflow.log_artifact(best_model_path, "model")
            
            logger.info(f"✅ Training finished. Model and results logged to MLflow.")

        finally:
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
    
    parser_finetune = subparsers.add_parser("finetune", help="Fine-tune an existing model.")
    parser_finetune.add_argument("--model-path", type=str, required=True, help="Path to the final model .zip.")
    parser_finetune.add_argument("--learning-rate", type=float, help="Optional new learning rate for fine-tuning.")
    
    args = parser.parse_args()

    rl_config_dict = {key: getattr(rl_cfg, key) for key in dir(rl_cfg) if key.isupper()}
    
    try:
        if args.action == 'tune':
            await run_hyperparameter_tuning(rl_config_dict)
        else:
            await run_model_training(rl_config_dict, args)
    except Exception as e:
        logger.error(f"A critical error occurred in main: {e}", exc_info=True)


if __name__ == "__main__":
    setup_logging(logger_name='rl_training')
    
    if sys.platform in ['win32', 'darwin']:
        # This is the corrected line
        multiprocessing.freeze_support()
        __spec__ = None 
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")