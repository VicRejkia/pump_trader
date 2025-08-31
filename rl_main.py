# rl_main.py
"""
Interactive command center for the Reinforcement Learning workflow.

This script serves as a central entry point for all phases of the
ML lifecycle, from hyperparameter search to analysis. It uses
MLflow in the background to manage experiments and provide the user with
context-aware choices.

Ensure the MLflow UI is running before starting this script:
    mlflow ui --backend-store-uri file:./data/rl_runs
"""

import os
import subprocess
import tempfile
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from rich.table import Table
from rich.console import Console
from rl_agent.utils.hardware_advisor import get_hardware_recommendations

import inquirer
from rich.console import Console
from rich.table import Table
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException

from rl_agent.utils.mlflow_utils import (
    start_mlflow_server,
    find_artifact_in_run,
    fetch_mlflow_parent_runs,
    get_artifact_path
)
from config.rl_config import RL_CONFIG

MLFLOW_EXPERIMENT_DATASET = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_DATASET"]
MLFLOW_EXPERIMENT_TRAINING = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TRAINING"]
MLFLOW_EXPERIMENT_TUNING = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TUNING"]


# --- MLflow Configuration & Console ---
mlflow.set_tracking_uri("file:./data/rl_runs")
console = Console()

# --- Helper Functions ---
def run_command(command: List[str]) -> None:
    """
    Execute a shell command and display the output.
    
    Args:
        command: List of command arguments to execute.
    """
    try:
        print("\n" + "=" * 60)
        print(f"🚀 Executing command:\n   {' '.join(command)}")
        print("=" * 60 + "\n")
        
        # Clean environment to avoid MLflow run ID conflicts
        clean_env = os.environ.copy()
        if "MLFLOW_RUN_ID" in clean_env:
            del clean_env["MLFLOW_RUN_ID"]
            
        subprocess.run(command, check=True, env=clean_env)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {e}")
    except FileNotFoundError:
        print("❌ Command not found. Make sure Python is in the system path.")


def select_run_from_list(runs: List[Any], message: str) -> Optional[str]:
    """
    Display a list of runs for user selection and return the selected run ID.
    
    Args:
        runs: List of MLflow run objects.
        message: Message to display to the user.
        
    Returns:
        str or None: Selected run ID if chosen, None otherwise.
    """
    if not runs:
        print("No suitable runs found for selection.")
        return None
    
    choices = []
    for run in runs:
        # Extract run information for display
        run_name = run.data.tags.get('mlflow.runName', run.info.run_id[:8])
        start_time = datetime.fromtimestamp(run.info.start_time / 1000).strftime('%Y-%m-%d %H:%M')
        
        # Try to get a meaningful metric value
        metric_val = (
            run.data.metrics.get('best_trial_value') or
            run.data.metrics.get('eval_mean_reward') or
            run.data.metrics.get('processed_token_count')
        )
        metric_display = f"{metric_val:.2f}" if metric_val is not None else "N/A"
        
        choice_str = (
            f"[{start_time}] {run_name} "
            f"(Metric: {metric_display}, ID: {run.info.run_id[:6]}...)"
        )
        choices.append((choice_str, run.info.run_id))

    answer = inquirer.prompt([
        inquirer.List('run_id', message=message, choices=choices, carousel=True)
    ])
    
    return answer['run_id'] if answer else None


def _select_dataset_run() -> Optional[str]:
    """
    Helper function to select a dataset run from available options.
    
    Returns:
        str or None: Selected dataset run ID if chosen, None otherwise.
    """
    print("\n🔎 Please select a dataset to use for this action.")
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_DATASET)
    
    if not runs:
        print("No dataset runs found. Please generate one first.")
        return None
    
    run_id = select_run_from_list(runs, "Choose the dataset run:")
    if run_id:
        print(f"✅ Using dataset from run ID: {run_id[:8]}...")
    
    return run_id


def run_hardware_advisor(dataset_run_id: str) -> Optional[Dict[str, Any]]:
    """Runs the hardware advisor directly and displays the results."""
    print("\n" + "="*60)
    print("🤖 Running Hardware Advisor...")
    print("="*60)
    
    try:
        results = get_hardware_recommendations(dataset_run_id)
        sys_info = results['system_info']
        recs = results['recommendations']

        # Display a summary table
        table = Table(title="Hardware Advisor Summary")
        table.add_column("Parameter", style="cyan")
        table.add_column("Detected / Recommended", style="magenta")

        table.add_row("Available RAM", f"{sys_info['ram']['available_gb']:.2f} GB")
        table.add_row("Physical CPU Cores", str(sys_info['cpu']['physical_cores']))
        table.add_row("CUDA Available", "Yes" if sys_info['cuda']['available'] else "No")
        table.add_row("Dataset Size", f"{results['dataset_gb']:.2f} GB")
        table.add_section()
        table.add_row("Recommended Device", recs.get('DEVICE', 'N/A'))
        table.add_row("Recommended N_CPU", str(recs.get('N_CPU', 'N/A')))
        
        console = Console()
        console.print(table)
        
        if recs.get('analysis_notes'):
            print(f"Note: {recs.get('analysis_notes')}")
        
        # Ask user to accept
        answer = inquirer.prompt([
            inquirer.Confirm('accept', message="Accept recommended settings?", default=True)
        ])

        if answer and answer['accept']:
            return {'DEVICE': recs.get('DEVICE'), 'N_CPU': recs.get('N_CPU')}
        else:
            print("Aborted by user.")
            return None

    except Exception as e:
        print(f"Error running hardware advisor: {e}")
        return None


# --- Main Menu Functions ---

def generate_dataset() -> None:
    """Start the ETL process to generate a new feature store dataset."""
    print("\n--- Phase 0: Generate Feature Store (ETL) ---")
    
    questions = [
        inquirer.Text(
            'start_date', 
            message="Enter start date (e.g., 2025-06-26T00:00:00Z)", 
            default="2025-06-26T00:00:00Z"
        ),
        inquirer.Text(
            'end_date', 
            message="Enter end date (e.g., 2025-07-20T00:00:00Z)", 
            default="2025-07-20T00:00:00Z"
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if not all(answers.values()):
        print("Aborted: All fields are required.")
        return
    
    command = [
        "python", 
        "rl_agent/etl/prepare_rl_dataset.py", 
        "--start-date", answers['start_date'], 
        "--end-date", answers['end_date']
    ]
    run_command(command)


def start_tuning() -> None:
    """Start a new hyperparameter tuning run."""
    print("\n--- Phase 1: Hyperparameter Tuning ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return

    hw_settings = _run_hardware_advisor_and_get_settings(dataset_run_id)
    if not hw_settings:
        print("Aborted due to hardware advisor issue.")
        return

    command = [
        "python", "rl_agent/training/train.py", "tune", 
        "--dataset-run-id", dataset_run_id,
        "--device", hw_settings['DEVICE'],
        "--n-cpu", str(hw_settings['N_CPU'])
    ]
    run_command(command)


def start_training() -> None:
    """Start a new training based on the results of a tuning run."""
    print("\n--- Phase 2: Train New Model ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return

    # --- INTEGRATION: Run advisor to get hardware settings ---
    hw_settings = run_hardware_advisor(dataset_run_id)
    if not hw_settings or hw_settings.get('N_CPU', 0) == 0:
        print("Aborted due to hardware advisor issue or insufficient resources.")
        return
        
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TUNING)
    if not runs:
        print("No tuning runs found. Please run hyperparameter tuning first.")
        return
    
    run_id = select_run_from_list(runs, "Select a tuning run to source best parameters from:")
    if not run_id:
        return
    
    params_artifact_name = find_artifact_in_run(run_id, file_prefix="best_params", file_suffix=".json")
    if not params_artifact_name:
        print(f"\n❌ FATAL: Could not find 'best_params.json' in the selected tuning run.")
        return
    
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        params_path = get_artifact_path(run_id, params_artifact_name, dst_path=tmpdir)
        if not params_path:
            return
        
        answers = inquirer.prompt([
            inquirer.Text('name', message="Enter a name for this new training run"),
            inquirer.Confirm('register', message="Register this model in MLflow?", default=True)
        ])
        if not answers or not answers.get('name'):
            print("Aborted: A name is required.")
            return
        
        model_name = answers['name']
        command = [
            "python", "rl_agent/training/train.py", "train", 
            "--params-path", params_path, 
            "--name", model_name, 
            "--dataset-run-id", dataset_run_id,
            # --- Pass hardware settings to the training script ---
            "--device", hw_settings['DEVICE'],
            "--n-cpu", str(hw_settings['N_CPU'])
        ]
        
        if answers.get('register'):
            command.extend(["--register-as", model_name])
            
        run_command(command)


def continue_or_finetune_training(action: str) -> None:
    """Continue or finetune an existing training run."""
    print(f"\n--- Phase 3/4: {action.capitalize()} Training ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return

    # --- INTEGRATION: Run advisor to get hardware settings ---
    hw_settings = run_hardware_advisor(dataset_run_id)
    if not hw_settings or hw_settings.get('N_CPU', 0) == 0:
        print("Aborted due to hardware advisor issue or insufficient resources.")
        return
    
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs:
        print("No previous training runs found to continue from.")
        return
    
    run_id = select_run_from_list(runs, f"Select a training run to {action}:")
    if not run_id:
        return
    
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        model_artifact_path = (
            find_artifact_in_run(run_id, "best_model", ".zip") or
            find_artifact_in_run(run_id, "final_model", ".zip")
        )
        
        if not model_artifact_path:
            print("❌ Could not find a model artifact in this run.")
            return
        
        model_path = get_artifact_path(run_id, model_artifact_path, dst_path=tmpdir)
        if not model_path:
            return
        
        parent_run = MlflowClient().get_run(run_id)
        parent_run_name = parent_run.data.tags.get('mlflow.runName', run_id[:8])
        registered_model_name = parent_run.data.tags.get("registered_model_name")
        suggested_name = f"{parent_run_name}_{action[:2]}"
        
        questions = [
            inquirer.Text('name', message=f"Enter a name for this '{action}' run", default=suggested_name),
            inquirer.Confirm('register', message="Register this new version under the same model name?", default=True)
        ]
        
        if action == 'finetune':
            questions.append(inquirer.Text('lr', message="New learning rate (optional, press Enter to keep existing)"))
        
        answers = inquirer.prompt(questions)
        if not answers or not answers['name']:
            print("Aborted.")
            return
        
        command = [
            "python", "rl_agent/training/train.py", action, 
            "--model-path", model_path, 
            "--parent-run-id", run_id, 
            "--name", answers['name'], 
            "--dataset-run-id", dataset_run_id,
            # --- Pass hardware settings to the training script ---
            "--device", hw_settings['DEVICE'],
            "--n-cpu", str(hw_settings['N_CPU'])
        ]
        
        if answers.get('register') and registered_model_name:
            command.extend(["--register-as", registered_model_name])
        elif answers.get('register'):
            print(f"⚠️ Parent model was not registered. This model will be registered as '{answers['name']}'.")
            command.extend(["--register-as", answers['name']])

        if action == 'finetune' and answers.get('lr'):
            command.extend(["--learning-rate", answers['lr']])
        
        run_command(command)


def start_feature_analysis() -> None:
    """Start feature importance analysis on a trained model."""
    print("\n--- Phase 5: Feature Importance Analysis ---")
    
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return
    
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs:
        print("No trained models found to analyze.")
        return
    
    run_id = select_run_from_list(runs, "Select the trained model to be analyzed:")
    if not run_id:
        return
    
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        model_artifact_path = (
            find_artifact_in_run(run_id, "best_model", ".zip") or
            find_artifact_in_run(run_id, "final_model", ".zip")
        )
        
        if not model_artifact_path:
            print("❌ Could not find a model artifact for analysis.")
            return
        
        model_path = get_artifact_path(run_id, model_artifact_path, dst_path=tmpdir)
        if not model_path:
            return
        
        command = [
            "python", 
            "rl_agent/evaluation/feature_importance.py", 
            "--model-run-id", run_id, 
            "--model-path", model_path, 
            "--dataset-run-id", dataset_run_id
        ]
        run_command(command)


# --- Main Workflow ---

def main_menu() -> None:
    """Display the interactive main menu and control the workflow."""
    while True:
        answers = inquirer.prompt([
            inquirer.List(
                'action',
                message="MLOps Command Center",
                choices=[
                    ('0) Generate New Dataset (ETL)', 'etl'),
                    ('1) Start Hyperparameter Tuning (Optuna)', 'tune'),
                    ('2) Train a New Model', 'train'),
                    ('3) Continue Training a Model', 'continue'),
                    ('4) Perform Model Fine-Tuning', 'finetune'),
                    ('5) Start Feature Importance Analysis', 'analyze'),
                    ('6) Exit', 'exit')
                ],
                carousel=True
            )
        ])
        
        action = answers['action'] if answers else 'exit'

        if action == 'exit':
            print("👋 Goodbye!")
            break
        elif action == 'etl':
            generate_dataset()
        elif action == 'tune':
            start_tuning()
        elif action == 'train':
            start_training()
        elif action == 'continue':
            continue_or_finetune_training('continue')
        elif action == 'finetune':
            continue_or_finetune_training('finetune')
        elif action == 'analyze':
            start_feature_analysis()
        
        input("\nPress Enter to return to the main menu...")
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == "__main__":
    os.makedirs("./.rl_staging", exist_ok=True)
    
    # Start MLflow Server and set tracking URI
    tracking_uri = start_mlflow_server(backend_store_uri="file:./data/rl_runs")
    mlflow.set_tracking_uri(tracking_uri)
    
    main_menu()