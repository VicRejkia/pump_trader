# rl_main.py
"""
Interactive command center for the Reinforcement Learning workflow.

This script serves as a central entry point for all phases of the
ML lifecycle, from hyperparameter search to analysis. It uses
MLflow in the background to manage experiments and provide the user with
context-aware choices.

Ensure the MLflow UI is running before starting this script:
    mlflow ui
"""

import os
import subprocess
import inquirer
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException

from datetime import datetime

# --- Constants for MLflow Experiment Names ---
# These names must match those in your training scripts
MLFLOW_EXPERIMENT_TUNING = "PumpTrader.RL Hyperparameter Tuning"
MLFLOW_EXPERIMENT_TRAINING = "PumpTrader.RL PPO Training"
MLFLOW_EXPERIMENT_ANALYSIS = "PumpTrader.RL Feature Analysis"



# --- Helper Functions ---

def check_mlflow_ui():
    """Checks if the MLflow server is reachable."""
    try:
        client = MlflowClient()
        # A simple call to test the connection
        # CORRECTED: The correct method is 'search_experiments'
        client.search_experiments()
        print("✅ MLflow Tracking Server is reachable.")
    except MlflowException:
        print("❌ Warning: The MLflow Tracking Server does not seem to be running.")
        print("   Please start it in a separate terminal with the command:")
        print("\n   mlflow ui\n")
        input("Press Enter to continue anyway...")

def run_command(command: list):
    """Executes a shell command and displays the output."""
    try:
        print("\n" + "="*60)
        print(f"🚀 Executing command:\n   {' '.join(command)}")
        print("="*60 + "\n")

        # Create a copy of the current environment variables.
        clean_env = os.environ.copy()

        # Unset MLFLOW_RUN_ID if it exists. This prevents the parent process's
        # MLflow context from "leaking" into the subprocess, which solves the
        # "run is already active" error.
        if "MLFLOW_RUN_ID" in clean_env:
            del clean_env["MLFLOW_RUN_ID"]

        # Execute the subprocess with the cleaned environment.
        subprocess.run(command, check=True, env=clean_env)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {e}")
    except FileNotFoundError:
        print("❌ Command not found. Make sure Python is in the system path.")

def find_params_artifact_path(run_id: str):
    """
    Lists artifacts in a run and finds the path to the best_params file,
    searching within the 'config' artifact subdirectory.
    """
    try:
        client = MlflowClient()
        # Search specifically within the 'config' directory where params are stored
        artifacts = client.list_artifacts(run_id, path="config")
        for artifact in artifacts:
            # The full path needed for download is the directory + filename
            if artifact.path.endswith(".json"):
                print(f"Found parameters file: {artifact.path}")
                return artifact.path
        print("❌ Error: No '.json' parameter artifact found in this run's 'config' directory.")
        return None
    except MlflowException as e:
        print(f"Error listing artifacts: {e}")
        return None
    
def fetch_mlflow_runs(experiment_name: str, num_runs: int = 10):
    """Fetches the last 'num_runs' runs from an MLflow experiment."""
    try:
        client = MlflowClient()
        experiment = client.get_experiment_by_name(experiment_name)
        if not experiment:
            print(f"⚠️ Experiment '{experiment_name}' not found in MLflow.")
            return []
        
        # 1. Fetch all recent runs without the problematic filter.
        #    We fetch more runs initially to ensure we find enough parent runs.
        all_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=num_runs * 1000 # Fetch more to account for child runs
        )
        
        # 2. Filter the results in Python to keep only the parent runs.
        parent_runs = [
            run for run in all_runs if 'mlflow.parentRunId' not in run.data.tags
        ]

        # 3. Return the desired number of parent runs.
        return parent_runs[:num_runs]
    except MlflowException as e:
        print(f"Error fetching MLflow runs: {e}")
        return []

def select_run_from_list(runs, message: str):
    """Displays a list of runs for selection and returns the selected run."""
    if not runs:
        print("No runs found for selection.")
        return None

    choices = []
    for run in runs:
        run_name = run.data.tags.get('mlflow.runName', run.info.run_id[:8])
        start_time_dt = datetime.fromtimestamp(run.info.start_time / 1000)
        start_time = start_time_dt.strftime('%Y-%m-%d %H:%M')

        # --- MODIFICATION START ---
        # Correctly search for the metric without short-circuiting
        metrics = run.data.metrics
        metric_val = metrics.get('best_trial_reward') or metrics.get('final_mean_reward') or metrics.get('eval_mean_reward') or metrics.get('best_trial_value')

        # Format the metric value after finding it
        if metric_val is not None:
            metric_display = f"{metric_val:.2f}"
        else:
            metric_display = "N/A"
        # --- MODIFICATION END ---
        
        choice_str = f"[{start_time}] {run_name} (Reward: {metric_display})" # Use the new display variable
        choices.append((choice_str, run.info.run_id))

    questions = [
        inquirer.List('run_id', message=message, choices=choices)
    ]
    answer = inquirer.prompt(questions)
    return answer['run_id'] if answer else None

def get_artifact_path(run_id: str, artifact_name: str):
    """Gets the local path of an artifact from an MLflow run."""
    try:
        local_path = mlflow.artifacts.download_artifacts(
            run_id=run_id,
            artifact_path=artifact_name
        )
        return local_path
    except MlflowException as e:
        print(f"❌ Error downloading artifact '{artifact_name}': {e}")
        return None

# --- Main Menu Functions ---

def start_tuning():
    """Starts a new hyperparameter tuning run."""
    print("\n--- Phase 1: Hyperparameter Tuning ---")
    command = ["python", "rl_agent/training/train.py", "tune"]
    run_command(command)

def start_training():
    """Starts a new training based on the results of a tuning run."""
    print("\n--- Phase 2: Train New Model ---")
    runs = fetch_mlflow_runs(MLFLOW_EXPERIMENT_TUNING) #
    if not runs: return

    run_id = select_run_from_list(runs, "Select a tuning run whose best parameters should be used:") #
    if not run_id: return

    # --- MODIFICATION START ---
    # Use the new function to find the artifact path dynamically
    params_artifact_name = find_params_artifact_path(run_id)
    if not params_artifact_name: return

    # Now, download the artifact using the dynamically found name
    params_path = get_artifact_path(run_id, params_artifact_name) #
    if not params_path: return
    # --- MODIFICATION END ---

    print(f"✅ Best parameters found at: {params_path}")
    model_name = input("Enter a name for this training run: ")
    if not model_name:
        print("Aborted: A name is required.")
        return

    command = ["python", "rl_agent/training/train.py", "train", "--params-path", params_path, "--name", model_name] #
    run_command(command)

def continue_or_finetune_training(action: str):
    """Continues a training or starts fine-tuning."""
    print(f"\n--- Phase 3/4: {'Continue' if action == 'continue' else 'Finetune'} Training ---")
    runs = fetch_mlflow_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs: return

    run_id = select_run_from_list(runs, "Select a training run to continue/finetune:")
    if not run_id: return

    # --- Fetch the parent run's name for the new naming convention ---
    client = MlflowClient()
    parent_run = client.get_run(run_id)
    parent_run_name = parent_run.data.tags.get('mlflow.runName', run_id)

    # --- Download artifacts (logic remains the same) ---
    model_artifact_path = "model/best_model.zip"
    model_path = get_artifact_path(run_id, model_artifact_path)
    if not model_path:
        model_artifact_path = "model/final_model.zip"
        model_path = get_artifact_path(run_id, model_artifact_path)
    
    params_artifact_path = find_params_artifact_path(run_id)

    if not model_path or not params_artifact_path:
        print("❌ Could not find a required model or parameter artifact in this run. Aborting.")
        return
    
    params_path = get_artifact_path(run_id, params_artifact_path)
    if not params_path: return

    print(f"✅ Model to continue found at: {model_path}")
    print(f"✅ Original parameters found at: {params_path}")

    # --- Interactively ask for the new run name with a helpful default ---
    action_suffix = "ct_v2" if action == "continue" else "ft_v2"
    suggested_name = f"{parent_run_name}_{action_suffix}"
    new_model_name = input(f"Enter a name for this '{action}' run (default: {suggested_name}): ")
    if not new_model_name:
        new_model_name = suggested_name


    # --- Add the params_path and parent_run_id to the command ---
    command = [
        "python", "rl_agent/training/train.py", action,
        "--model-path", model_path,
        "--params-path", params_path,
        "--parent-run-id", run_id,
        "--name", new_model_name 
    ]

    if action == 'finetune':
        lr = input("New learning rate for fine-tuning (optional, press Enter for no change): ")
        if lr:
            command.extend(["--learning-rate", lr])

    run_command(command)

def start_feature_analysis():
    """Starts a feature importance analysis for a trained model."""
    print("\n--- Phase 5: Feature Importance Analysis ---")
    runs = fetch_mlflow_runs(MLFLOW_EXPERIMENT_TRAINING)
    if not runs: return
    
    run_id = select_run_from_list(runs, "Select the model to be analyzed:")
    if not run_id: return

    model_path = get_artifact_path(run_id, "model/best_model.zip")
    if not model_path:
        model_path = get_artifact_path(run_id, "model/final_model.zip")

    if not model_path:
        print("Could not find a model artifact for analysis.")
        return

    print(f"✅ Model for analysis found at: {model_path}")
    command = ["python", "rl_agent/evaluation/feature_importance.py", "--model-path", model_path]
    run_command(command)


# --- Main Workflow ---

def main_menu():
    """Displays the interactive main menu and controls the workflow."""
    while True:
        questions = [
            inquirer.List('action',
                          message="MLOps Command Center - What would you like to do?",
                          choices=[
                              ('1) Start Hyperparameter Tuning (Optuna)', 'tune'),
                              ('2) Train a New Model', 'train'),
                              ('3) Continue Training a Model', 'continue'),
                              ('4) Perform Model Fine-Tuning', 'finetune'),
                              ('5) Start Feature Importance Analysis', 'analyze'),
                              ('6) Exit', 'exit')
                          ],
                          carousel=True
                          ),
        ]
        answer = inquirer.prompt(questions)
        action = answer['action'] if answer else 'exit'

        if action == 'tune':
            start_tuning()
        elif action == 'train':
            start_training()
        elif action == 'continue':
            continue_or_finetune_training('continue')
        elif action == 'finetune':
            continue_or_finetune_training('finetune')
        elif action == 'analyze':
            start_feature_analysis()
        elif action == 'exit':
            print("👋 Goodbye!")
            break
        
        input("\nPress Enter to return to the main menu...")
        # Clear screen for better user experience (optional)
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == "__main__":
    # Perform a quick check to remind the user to start the UI
    check_mlflow_ui()
    # Start the main menu
    main_menu()