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
import inquirer
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException
import tempfile
from datetime import datetime

# --- Set MLflow tracking URI at the beginning ---
mlflow.set_tracking_uri("file:./data/rl_runs")

# --- Constants for MLflow Experiment Names ---
MLFLOW_EXPERIMENT_TUNING = "PumpTrader.RL Hyperparameter Tuning"
MLFLOW_EXPERIMENT_TRAINING = "PumpTrader.RL PPO Training"
MLFLOW_EXPERIMENT_ANALYSIS = "PumpTrader.RL Feature Analysis"
MLFLOW_EXPERIMENT_DATASET = "PumpTrader.RL Dataset Generation"


# --- Helper Functions ---

def check_mlflow_ui():
    """Checks if the MLflow server is reachable."""
    try:
        MlflowClient().search_experiments()
        print("✅ MLflow Tracking Server is reachable.")
        return True
    except MlflowException:
        print("\n❌ Warning: The MLflow Tracking Server does not seem to be running.")
        print("   Please start it in a separate terminal with the command:")
        print("\n   mlflow ui --backend-store-uri file:./data/rl_runs\n")
        input("Press Enter to continue anyway...")
        return False
def run_command(command: list):
    """Executes a shell command and displays the output."""
    try:
        print("\n" + "="*60)
        print(f"🚀 Executing command:\n   {' '.join(command)}")
        print("="*60 + "\n")
        clean_env = os.environ.copy()
        if "MLFLOW_RUN_ID" in clean_env:
            del clean_env["MLFLOW_RUN_ID"]
        subprocess.run(command, check=True, env=clean_env)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {e}")
    except FileNotFoundError:
        print("❌ Command not found. Make sure Python is in the system path.")
def find_artifact_in_run(run_id: str, file_prefix: str, file_suffix: str = ".json") -> str | None:
    # ...
    client = MlflowClient()
    try:
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
def fetch_mlflow_parent_runs(experiment_name: str, num_runs: int = 15):
    # ...
    try:
        client = MlflowClient()
        experiment = client.get_experiment_by_name(experiment_name)
        if not experiment:
            print(f"⚠️ Experiment '{experiment_name}' not found.")
            return []
        
        all_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=["start_time DESC"],
            max_results=num_runs * 10 
        )
        
        parent_runs = [
            run for run in all_runs if 'mlflow.parentRunId' not in run.data.tags
        ]
        return parent_runs[:num_runs]
    except MlflowException as e:
        print(f"Error fetching MLflow runs: {e}")
        return []
def select_run_from_list(runs, message: str):
    """Displays a list of runs for selection and returns the selected run."""
    if not runs:
        print("No suitable runs found for selection.")
        return None
    choices = []
    for run in runs:
        run_name = run.data.tags.get('mlflow.runName', run.info.run_id[:8])
        start_time = datetime.fromtimestamp(run.info.start_time / 1000).strftime('%Y-%m-%d %H:%M')
        metric_val = (run.data.metrics.get('best_trial_value') or
                      run.data.metrics.get('eval_mean_reward') or
                      run.data.metrics.get('processed_token_count'))
        metric_display = f"{metric_val:.2f}" if metric_val is not None else "N/A"
        
        choice_str = f"[{start_time}] {run_name} (Metric: {metric_display}, ID: {run.info.run_id[:6]}...)"
        choices.append((choice_str, run.info.run_id))

    answer = inquirer.prompt([inquirer.List('run_id', message=message, choices=choices, carousel=True)])
    return answer['run_id'] if answer else None
def get_artifact_path(run_id: str, artifact_name: str, dst_path: str):
    """Gets the local path of an artifact from an MLflow run."""
    try:
        return mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path=artifact_name, dst_path=dst_path)
    except MlflowException as e:
        print(f"❌ Error downloading artifact '{artifact_name}': {e}")
        return None
def _select_dataset_run() -> str | None:
    # ...
    print("\n🔎 Please select a dataset to use for this action.")
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_DATASET)
    if not runs:
        print("No dataset runs found. Please generate one first.")
        return None
    run_id = select_run_from_list(runs, "Choose the dataset run:")
    if run_id: print(f"✅ Using dataset from run ID: {run_id[:8]}...")
    return run_id
    
# --- Main Menu Functions ---

def generate_dataset():
    """Starts the ETL process to generate a new feature store dataset."""
    print("\n--- Phase 0: Generate Feature Store (ETL) ---")
    questions = [
        inquirer.Text('start_date', message="Enter start date (e.g., 2025-06-26T00:00:00Z)", default="2025-06-26T00:00:00Z"),
        inquirer.Text('end_date', message="Enter end date (e.g., 2025-07-20T00:00:00Z)", default="2025-07-20T00:00:00Z"),
        # The version prompt is now removed
    ]
    answers = inquirer.prompt(questions)
    if not all(answers.values()):
        print("Aborted: All fields are required."); return
    
    # Command no longer includes the version argument
    command = ["python", "rl_agent/etl/prepare_rl_dataset.py", "--start-date", answers['start_date'], "--end-date", answers['end_date']]
    run_command(command)

# --- Main Menu Functions ---

def start_tuning():
    """Starts a new hyperparameter tuning run."""
    print("\n--- Phase 1: Hyperparameter Tuning ---")
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id: return
    command = ["python", "rl_agent/training/train.py", "tune", "--dataset-run-id", dataset_run_id]
    run_command(command)

def start_training():
    """Starts a new training based on the results of a tuning run."""
    print("\n--- Phase 2: Train New Model ---")
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id: return
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TUNING)
    if not runs: return
    run_id = select_run_from_list(runs, "Select a tuning run to source best parameters from:")
    if not run_id: return
    print(f"🔎 Searching for artifact starting with 'best_params' in run {run_id[:8]}...")
    params_artifact_name = find_artifact_in_run(run_id, file_prefix="best_params", file_suffix=".json")
    if not params_artifact_name:
        print(f"\n❌ FATAL ERROR: Could not find any artifact file starting with 'best_params' in the selected tuning run.")
        print("   This can happen with older runs if the artifact was not saved correctly.")
        print("   SOLUTION: Please try running a new 'Hyperparameter Tuning' job first.")
        return
    print(f"✅ Found artifact: '{params_artifact_name}'. Proceeding...")
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        params_path = get_artifact_path(run_id, params_artifact_name, dst_path=tmpdir)
        if not params_path: return
        answers = inquirer.prompt([inquirer.Text('name', message="Enter a name for this new training run")])
        if not answers or not answers.get('name'):
            print("Aborted: A name is required."); return
        model_name = answers['name']
        command = ["python", "rl_agent/training/train.py", "train", "--params-path", params_path, "--name", model_name, "--dataset-run-id", dataset_run_id]
        run_command(command)
def continue_or_finetune_training(action: str):
    # ...
    print(f"\n--- Phase 3/4: {action.capitalize()} Training ---")
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id: return
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs: return
    run_id = select_run_from_list(runs, f"Select a training run to {action}:")
    if not run_id: return
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        model_artifact_path = find_artifact_in_run(run_id, "best_model", ".zip") or find_artifact_in_run(run_id, "final_model", ".zip")
        if not model_artifact_path:
            print("❌ Could not find a model artifact in this run."); return
        model_path = get_artifact_path(run_id, model_artifact_path, dst_path=tmpdir)
        if not model_path: return
        parent_run_name = MlflowClient().get_run(run_id).data.tags.get('mlflow.runName', run_id[:8])
        suggested_name = f"{parent_run_name}_{action[:2]}"
        questions = [inquirer.Text('name', message=f"Enter name for this '{action}' run", default=suggested_name)]
        if action == 'finetune':
            questions.append(inquirer.Text('lr', message="New learning rate (optional, press Enter to keep existing)"))
        answers = inquirer.prompt(questions)
        if not answers or not answers['name']:
            print("Aborted."); return
        command = ["python", "rl_agent/training/train.py", action, "--model-path", model_path, "--parent-run-id", run_id, "--name", answers['name'], "--dataset-run-id", dataset_run_id]
        if action == 'finetune' and answers.get('lr'):
            command.extend(["--learning-rate", answers['lr']])
        run_command(command)
def start_feature_analysis():
    # ...
    print("\n--- Phase 5: Feature Importance Analysis ---")
    dataset_run_id = _select_dataset_run()
    if not dataset_run_id: return
    runs = fetch_mlflow_parent_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs: return
    run_id = select_run_from_list(runs, "Select the trained model to be analyzed:")
    if not run_id: return
    with tempfile.TemporaryDirectory(dir="./.rl_staging") as tmpdir:
        model_artifact_path = find_artifact_in_run(run_id, "best_model", ".zip") or find_artifact_in_run(run_id, "final_model", ".zip")
        if not model_artifact_path:
            print("❌ Could not find a model artifact for analysis."); return
        model_path = get_artifact_path(run_id, model_artifact_path, dst_path=tmpdir)
        if not model_path: return
        command = ["python", "rl_agent/evaluation/feature_importance.py", "--model-path", model_path, "--dataset-run-id", dataset_run_id]
        run_command(command)

# --- Main Workflow ---

def main_menu():
    """Displays the interactive main menu and controls the workflow."""
    while True:
        answers = inquirer.prompt([
            inquirer.List('action',
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
                carousel=True)
        ])
        
        action = answers['action'] if answers else 'exit'

        if action == 'exit': print("👋 Goodbye!"); break
        elif action == 'etl': generate_dataset()
        elif action == 'tune': start_tuning()
        elif action == 'train': start_training()
        elif action == 'continue': continue_or_finetune_training('continue')
        elif action == 'finetune': continue_or_finetune_training('finetune')
        elif action == 'analyze': start_feature_analysis()
        
        input("\nPress Enter to return to the main menu...")
        os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    os.makedirs("./.rl_staging", exist_ok=True)
    check_mlflow_ui()
    main_menu()