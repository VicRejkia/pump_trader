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
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

import inquirer
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException

from rl_agent.utils.mlflow_utils import start_mlflow_server
from config.rl_config import RL_CONFIG

MLFLOW_EXPERIMENT_DATASET = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_DATASET"]
MLFLOW_EXPERIMENT_TRAINING = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TRAINING"]
MLFLOW_EXPERIMENT_TUNING = RL_CONFIG["common"]["MLFLOW_EXPERIMENT_TUNING"]


# --- MLflow Configuration ---
mlflow.set_tracking_uri("file:./data/rl_runs")




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


def find_artifact_in_run(
    run_id: str, 
    file_prefix: str, 
    file_suffix: str = ".json"
) -> Optional[str]:
    """
    Search for an artifact file in an MLflow run by prefix and suffix.
    
    Args:
        run_id: MLflow run ID to search in.
        file_prefix: Prefix of the artifact file name.
        file_suffix: Suffix of the artifact file name.
        
    Returns:
        str or None: Path to the artifact if found, None otherwise.
    """
    client = MlflowClient()
    try:
        # Use DFS to search through all artifact directories
        stack = [""]
        
        while stack:
            current_path = stack.pop()
            artifacts = client.list_artifacts(run_id, path=current_path)
            
            for artifact in artifacts:
                if artifact.is_dir:
                    stack.append(artifact.path)
                else:
                    basename = os.path.basename(artifact.path)
                    if basename.startswith(file_prefix) and basename.endswith(file_suffix):
                        return artifact.path
        
        return None
        
    except MlflowException as e:
        print(f"❌ MLflow error while searching for artifact starting with '{file_prefix}': {e}")
        return None


def fetch_mlflow_parent_runs(
    experiment_name: str, 
    num_runs: int = 15
) -> List[Any]:
    """
    Fetch parent runs (non-child runs) from an MLflow experiment.
    
    Args:
        experiment_name: Name of the MLflow experiment.
        num_runs: Maximum number of runs to return.
        
    Returns:
        List of MLflow run objects.
    """
    try:
        client = MlflowClient()
        experiment = client.get_experiment_by_name(experiment_name)
        
        if not experiment:
            print(f"⚠️ Experiment '{experiment_name}' not found.")
            return []
        
        # Get all finished runs, ordered by start time (newest first)
        all_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=["start_time DESC"],
            max_results=num_runs * 10  # Get more to filter out child runs
        )
        
        # Filter to only include parent runs (no mlflow.parentRunId tag)
        parent_runs = [
            run for run in all_runs 
            if 'mlflow.parentRunId' not in run.data.tags
        ]
        
        return parent_runs[:num_runs]
        
    except MlflowException as e:
        print(f"Error fetching MLflow runs: {e}")
        return []


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


def get_artifact_path(run_id: str, artifact_name: str, dst_path: str) -> Optional[str]:
    """
    Download and get the local path of an artifact from an MLflow run.
    
    Args:
        run_id: MLflow run ID.
        artifact_name: Name/path of the artifact to download.
        dst_path: Destination path for download.
        
    Returns:
        str or None: Local path to downloaded artifact if successful, None otherwise.
    """
    try:
        return mlflow.artifacts.download_artifacts(
            run_id=run_id, 
            artifact_path=artifact_name, 
            dst_path=dst_path
        )
    except MlflowException as e:
        print(f"❌ Error downloading artifact '{artifact_name}': {e}")
        return None


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
    
    command = [
        "python", 
        "rl_agent/training/train.py", 
        "tune", 
        "--dataset-run-id", dataset_run_id
    ]
    run_command(command)


def start_training() -> None:
    """Start a new training based on the results of a tuning run."""
    print("\n--- Phase 2: Train New Model ---")
    
    # Select dataset to use
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return
    
    # Select tuning run to get parameters from
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TUNING)
    if not runs:
        return
    
    run_id = select_run_from_list(
        runs, 
        "Select a tuning run to source best parameters from:"
    )
    if not run_id:
        return
    
    # Find the best parameters artifact
    print(f"🔎 Searching for artifact starting with 'best_params' in run {run_id[:8]}...")
    params_artifact_name = find_artifact_in_run(
        run_id, 
        file_prefix="best_params", 
        file_suffix=".json"
    )
    
    if not params_artifact_name:
        print(f"\n❌ FATAL ERROR: Could not find any artifact file starting with 'best_params' "
              f"in the selected tuning run.")
        print("   This can happen with older runs if the artifact was not saved correctly.")
        print("   SOLUTION: Please try running a new 'Hyperparameter Tuning' job first.")
        return
    
    print(f"✅ Found artifact: '{params_artifact_name}'. Proceeding...")
    
    # Download parameters and start training
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        params_path = get_artifact_path(run_id, params_artifact_name, dst_path=tmpdir)
        if not params_path:
            return
        
        # Get training run name from user
        answers = inquirer.prompt([
            inquirer.Text('name', message="Enter a name for this new training run")
        ])
        if not answers or not answers.get('name'):
            print("Aborted: A name is required.")
            return
        
        model_name = answers['name']
        command = [
            "python", 
            "rl_agent/training/train.py", 
            "train", 
            "--params-path", params_path, 
            "--name", model_name, 
            "--dataset-run-id", dataset_run_id
        ]
        run_command(command)


def continue_or_finetune_training(action: str) -> None:
    """
    Continue or finetune an existing training run.
    
    Args:
        action: Either 'continue' or 'finetune'.
    """
    print(f"\n--- Phase 3/4: {action.capitalize()} Training ---")
    
    # Select dataset to use
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return
    
    # Select training run to continue/finetune
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs:
        return
    
    run_id = select_run_from_list(runs, f"Select a training run to {action}:")
    if not run_id:
        return
    
    # Download model artifact
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        # Look for best_model first, then final_model as fallback
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
        
        # Generate suggested name based on parent run
        parent_run_name = MlflowClient().get_run(run_id).data.tags.get(
            'mlflow.runName', run_id[:8]
        )
        suggested_name = f"{parent_run_name}_{action[:2]}"
        
        # Collect user input
        questions = [
            inquirer.Text(
                'name', 
                message=f"Enter name for this '{action}' run", 
                default=suggested_name
            )
        ]
        
        # Add learning rate question for finetuning
        if action == 'finetune':
            questions.append(
                inquirer.Text(
                    'lr', 
                    message="New learning rate (optional, press Enter to keep existing)"
                )
            )
        
        answers = inquirer.prompt(questions)
        if not answers or not answers['name']:
            print("Aborted.")
            return
        
        # Build command
        command = [
            "python", 
            "rl_agent/training/train.py", 
            action, 
            "--model-path", model_path, 
            "--parent-run-id", run_id, 
            "--name", answers['name'], 
            "--dataset-run-id", dataset_run_id
        ]
        
        # Add learning rate if provided for finetuning
        if action == 'finetune' and answers.get('lr'):
            command.extend(["--learning-rate", answers['lr']])
        
        run_command(command)


def start_feature_analysis() -> None:
    """Start feature importance analysis on a trained model."""
    print("\n--- Phase 5: Feature Importance Analysis ---")
    
    # Select dataset to use
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id:
        return
    
    # Select trained model for analysis
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs:
        return
    
    run_id = select_run_from_list(runs, "Select the trained model to be analyzed:")
    if not run_id:
        return
    
    # Download model artifact for analysis
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        # Look for best_model first, then final_model as fallback
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
        # Display menu options
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


        # Execute selected action
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
        
        # Wait for user before returning to menu
        input("\nPress Enter to return to the main menu...")
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == "__main__":
    # Create staging directory if it doesn't exist
    os.makedirs("./.rl_staging", exist_ok=True)
    
    # --- Start MLflow Server ---
    # This will start the server if not running and set the tracking URI for this script.
    # Child processes (train.py, etl.py) will be configured to connect to this server.
    start_mlflow_server(backend_store_uri="file:./data/rl_runs")
    
    # Start the main menu
    main_menu()