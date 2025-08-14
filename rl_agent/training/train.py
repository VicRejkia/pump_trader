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
from datetime import datetime
from typing import Any, Dict, List

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import numpy as np
import optuna
import torch as th
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3 import PPO
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler

import config.rl_config as rl_cfg
import config.config as main_cfg
from bot_logger import logger, setup_logging
from database_handler import DatabaseClient
from rl_agent.agents.ppo_agent import create_ppo_agent
from rl_agent.data.data_manager import DataManager
from rl_agent.environments.meme_coin_env import MemeCoinEnv


def _valid_batch_sizes(n_steps: int, n_envs: int) -> List[int]:
    """Returns a list of valid batch sizes for PPO."""
    candidates = [32, 64, 128, 256, 512]
    total_steps = n_steps * n_envs
    return [b for b in candidates if total_steps % b == 0 and b <= total_steps]

def sample_ppo_params(trial: optuna.trial.Trial, n_envs: int) -> Dict[str, Any]:
    """Samples hyperparameters for a PPO agent using an Optuna trial."""
    n_steps = trial.suggest_categorical("n_steps", [1024, 2048, 4096])
    
    valid_bs = _valid_batch_sizes(n_steps, n_envs)
    if not valid_bs:
        raise optuna.exceptions.TrialPruned("No valid batch_size for the chosen n_steps.")
    
    batch_size = trial.suggest_categorical("batch_size", valid_bs)
    
    if batch_size > n_steps * n_envs:
        raise optuna.exceptions.TrialPruned(f"Constraint violated: batch_size > n_steps * n_envs")

    # Convert lists to tuples for Optuna's persistent storage requirement
    pi_layers_choices = (
        tuple([64, 64]), 
        tuple([128, 128]), 
        tuple([256, 256])
    )
    vf_layers_choices = (
        tuple([64, 64]), 
        tuple([128, 128]), 
        tuple([256, 256])
    )

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
            "activation_fn": th.nn.ReLU,
            "net_arch": {
                "pi": list(trial.suggest_categorical("pi_layers", pi_layers_choices)),
                "vf": list(trial.suggest_categorical("vf_layers", vf_layers_choices)),
            },
        },
    }
    return params

async def run_hyperparameter_tuning(rl_config: Dict[str, Any]):
    logger.info(f"Starting Hyperparameter Tuning Session with {rl_config['OPTUNA_N_TRIALS']} trials.")
    
    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=42, n_startup_trials=10),
        pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=rl_config['OPTUNA_PRUNER_N_WARMUP_STEPS'])
    )
    
    try:
        objective_func = lambda trial: objective_sync(trial, rl_config, main_cfg)
        await asyncio.to_thread(
            study.optimize,
            objective_func,
            n_trials=rl_config['OPTUNA_N_TRIALS'],
            timeout=rl_config['OPTUNA_TIMEOUT_SECONDS'],
            n_jobs=1,
            gc_after_trial=True
        )
    except Exception as e:
        logger.error(f"Optuna study failed: {e}", exc_info=True)
        return

    best_trial = study.best_trial
    best_params = best_trial.params
    if 'pi_layers' in best_params: best_params['pi_layers'] = list(best_params['pi_layers'])
    if 'vf_layers' in best_params: best_params['vf_layers'] = list(best_params['vf_layers'])

    params_path = os.path.join(rl_config['RL_MODELS_DIR'], f"best_params_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    with open(params_path, 'w') as f:
        json.dump(best_params, f, indent=4)
    
    logger.info("=" * 60)
    logger.info(f"✅ Optuna study complete. Best Trial: #{best_trial.number}")
    logger.info(f"  Value (Best Mean Reward): {best_trial.value:.4f}")
    logger.info(f"  💾 Best Hyperparameters saved to: {params_path}")
    logger.info("=" * 60)

async def run_model_training(db_client: DatabaseClient, rl_config: Dict[str, Any], args: argparse.Namespace):
    action_name = args.action
    timesteps = rl_config['PPO_FINAL_MODEL_TIMESTEPS']
    
    data_manager = DataManager(
        db_client,
        start_date=datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00")),
        end_date=datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
    )
    
    if not await data_manager.load_and_prepare_data():
        logger.error("Failed to load data for training. Aborting.")
        return

    data_manager.use_training_data()

    vec_env = make_vec_env(
        lambda: MemeCoinEnv(data_manager, rl_config),
        n_envs=rl_config['N_CPU'],
        vec_env_cls=SubprocVecEnv if rl_config['N_CPU'] > 1 else DummyVecEnv
    )

    device = rl_config['DEVICE'] if th.cuda.is_available() else 'cpu'
    reset_num_timesteps = True
    model = None

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    model_name = args.name if hasattr(args, 'name') and args.name else "PPO_Model"
    log_dir = os.path.join(rl_config['RL_LOGS_DIR'], f"{timestamp}_{model_name}")
    os.makedirs(log_dir, exist_ok=True)

    if action_name == 'train':
        logger.info(f"Starting new model training from hyperparameters at {args.params_path}")
        with open(args.params_path, 'r') as f:
            hyperparams = json.load(f)
        model = create_ppo_agent(vec_env, hyperparams, device=device, tensorboard_log_path=log_dir)
    
    elif action_name in ['continue', 'finetune']:
        logger.info(f"Loading model from {args.model_path} to {action_name} training.")
        model = PPO.load(args.model_path, env=vec_env, device=device)
        model.set_logger(type(model.logger)(log_dir, model.logger.output_formats))
        reset_num_timesteps = False
        if action_name == 'finetune' and hasattr(args, 'learning_rate') and args.learning_rate:
            new_lr = args.learning_rate
            logger.info(f"Fine-tuning: Adjusting learning rate to {new_lr}")
            model.learning_rate = new_lr

    if not model:
        logger.error("Model could not be created or loaded. Aborting.")
        return
        
    timesteps_str = f"{timesteps / 1_000_000:.1f}M" if timesteps >= 1_000_000 else f"{int(timesteps / 1000)}k"
    final_model_name = f"{timestamp}_{action_name}_{model_name}_{timesteps_str}.zip"
    final_model_path = os.path.join(rl_config['RL_MODELS_DIR'], final_model_name)
    
    checkpoint_callback = CheckpointCallback(
        save_freq=max(rl_config['PPO_EVAL_FREQ'] // rl_config['N_CPU'], 1),
        save_path=log_dir,
        name_prefix="checkpoint"
    )
    
    logger.info(f"🚀 Starting model training for {timesteps} timesteps...")
    logger.info(f"TensorBoard logs will be saved in: {log_dir}")
    logger.info(f"Final model will be saved to: {final_model_path}")
    
    try:
        model.learn(
            total_timesteps=timesteps,
            callback=checkpoint_callback,
            reset_num_timesteps=reset_num_timesteps
        )
    except KeyboardInterrupt:
        logger.warning("Training interrupted by user. Saving current model state...")
    finally:
        model.save(final_model_path)
        logger.info(f"✅ Training finished. Model saved to {final_model_path}")
        vec_env.close()

def objective_sync(trial: optuna.trial.Trial, rl_config: Dict, main_config_module: Any) -> float:
    logger.info(f"🚀 Starting Optuna Trial #{trial.number}...")
    return asyncio.run(_objective_async_for_optuna(trial, rl_config, main_config_module))

async def _objective_async_for_optuna(trial: optuna.trial.Trial, rl_config: Dict, main_config_module: Any) -> float:
    db_client_trial = None
    train_env, eval_env = None, None
    try:
        main_config_dict = {key: getattr(main_config_module, key) for key in dir(main_config_module) if key.isupper()}
        db_client_trial = DatabaseClient(config_dict=main_config_dict)
        await db_client_trial.connect()
        
        data_manager = DataManager(
            db_client_trial,
            start_date=datetime.fromisoformat(rl_config['DATA_START_DATE'].replace("Z", "+00:00")),
            end_date=datetime.fromisoformat(rl_config['DATA_END_DATE'].replace("Z", "+00:00"))
        )

        if not await data_manager.load_and_prepare_data():
            raise optuna.exceptions.TrialPruned("Failed to load and prepare data.")
        
        n_envs_tuning = 1
        
        data_manager.use_training_data()
        train_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(data_manager, rl_config))])
        train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0)

        data_manager.use_evaluation_data()
        eval_env = DummyVecEnv([lambda: Monitor(MemeCoinEnv(data_manager, rl_config))])
        eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, training=False, clip_obs=10.0, clip_reward=10.0)
        
        device = rl_config['DEVICE'] if th.cuda.is_available() else 'cpu'
        hyperparams = sample_ppo_params(trial, n_envs=n_envs_tuning)
        model = PPO("MlpPolicy", train_env, device=device, verbose=0, **hyperparams)
        
        eval_callback = EvalCallback(
            eval_env,
            n_eval_episodes=5,
            eval_freq=max(rl_config['PPO_EVAL_FREQ'] // n_envs_tuning, 1),
            deterministic=True,
            log_path=None, best_model_save_path=None, verbose=0
        )
        
        logger.info(f"Trial #{trial.number}: Starting training for {rl_config['PPO_TIMESTEPS_PER_TRIAL']} steps...")
        await asyncio.to_thread(
            model.learn,
            total_timesteps=rl_config['PPO_TIMESTEPS_PER_TRIAL'],
            callback=eval_callback
        )
        
        logger.info(f"Trial #{trial.number}: Training complete. Evaluating final model...")
        mean_reward, std_reward = await asyncio.to_thread(
            evaluate_policy, model, eval_env, n_eval_episodes=10, deterministic=True
        )
        logger.info(f"Trial #{trial.number}: Evaluation complete. Mean Reward: {mean_reward:.4f} +/- {std_reward:.4f}")
        
        if not np.isfinite(mean_reward):
            logger.warning(f"Trial {trial.number} resulted in non-finite reward ({mean_reward}). Pruning.")
            raise optuna.exceptions.TrialPruned()
            
        return float(mean_reward)

    except optuna.exceptions.TrialPruned as e:
        logger.warning(f"Trial #{trial.number} pruned. Reason: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error in Optuna trial #{trial.number}: {e}", exc_info=True)
        trial.set_user_attr("exception", repr(e))
        raise optuna.exceptions.TrialPruned()
    finally:
        if train_env: train_env.close()
        if eval_env: eval_env.close()
        if db_client_trial: await db_client_trial.close()

def safe_mean(arr: list) -> float:
    return float(sum(arr) / len(arr)) if len(arr) > 0 else 0.0

async def main():
    parser = argparse.ArgumentParser(description="RL Agent Training Workflow")
    subparsers = parser.add_subparsers(dest="action", required=True, help="Action to perform")
    subparsers.add_parser("tune", help="Run hyperparameter tuning with Optuna.")
    parser_train = subparsers.add_parser("train", help="Train a new model from scratch.")
    parser_train.add_argument("--params-path", type=str, required=True, help="Path to best_params.json.")
    parser_train.add_argument("--name", type=str, default="PPO_Model", help="Custom name for the training run.")
    parser_continue = subparsers.add_parser("continue", help="Continue training an existing model.")
    parser_continue.add_argument("--model-path", type=str, required=True, help="Path to the model .zip.")
    parser_finetune = subparsers.add_parser("finetune", help="Fine-tune an existing model.")
    parser_finetune.add_argument("--model-path", type=str, required=True, help="Path to the model .zip.")
    parser_finetune.add_argument("--learning-rate", type=float, help="Optional new learning rate.")
    args = parser.parse_args()

    rl_config_dict = {key: getattr(rl_cfg, key) for key in dir(rl_cfg) if key.isupper()}
    
    db_client = None
    try:
        main_config_dict = {key: getattr(main_cfg, key) for key in dir(main_cfg) if key.isupper()}
        
        if args.action == 'tune':
            await run_hyperparameter_tuning(rl_config_dict)
        else:
            db_client = DatabaseClient(config_dict=main_config_dict)
            await db_client.connect()
            await run_model_training(db_client, rl_config_dict, args)

    except Exception as e:
        logger.error(f"A critical error occurred in main: {e}", exc_info=True)
    finally:
        if db_client: await db_client.close()

if __name__ == "__main__":
    setup_logging(logger_name='rl_training')
    if sys.platform == 'win32':
        import multiprocessing
        multiprocessing.freeze_support()
        __spec__ = None 
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")