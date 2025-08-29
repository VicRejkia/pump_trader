# utils/mlflow_utils.py or similar

import os
import subprocess
import socket
import time
import logging
from typing import List, Tuple
import mlflow
from mlflow.entities import RunStatus
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException


logger = logging.getLogger(__name__)

def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use (to avoid starting multiple servers)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def start_mlflow_server(
    backend_store_uri: str = "file:./data/rl_runs",
    artifact_root: str = "./artifacts",
    host: str = "127.0.0.1",
    port: int = 8080,
    wait_time: int = 5
) -> str:
    """
    Starts an MLflow tracking server (if not already running) and sets the tracking URI.
    Returns the tracking URI.
    """
    tracking_uri = f"http://{host}:{port}"

    if _is_port_in_use(port, host):
        logger.info(f"MLflow server already running at {tracking_uri}")
    else:
        cmd = [
            "mlflow", "server",
            "--backend-store-uri", backend_store_uri,
            "--default-artifact-root", artifact_root,
            "--host", host,
            "--port", str(port)
        ]
        logger.info(f"Starting MLflow server with: {' '.join(cmd)}")
        subprocess.Popen(cmd)

        # Give it a few seconds to boot
        time.sleep(wait_time)
        if _is_port_in_use(port, host):
            logger.info(f"✅ MLflow server is up at {tracking_uri}")
        else:
            logger.warning(f"⚠️ Could not verify MLflow server at {tracking_uri} after {wait_time}s")

    # Set MLflow tracking URI globally
    mlflow.set_tracking_uri(tracking_uri)
    logger.info(f"MLflow tracking URI set to {tracking_uri}")
    return tracking_uri

def check_mlflow_ui() -> bool:
    """
    Check if the MLflow server is reachable.
    
    Returns:
        bool: True if MLflow server is reachable, False otherwise.
    """
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


def start_mlflow_ui(backend_store_uri: str = "file:./data/rl_runs", port: int = 5000):
    """
    Optionally: lightweight mode to just start the UI for visualization.
    """
    if _is_port_in_use(port):
        logger.info(f"MLflow UI already running at http://127.0.0.1:{port}")
    else:
        cmd = [
            "mlflow", "ui",
            "--backend-store-uri", backend_store_uri,
            "--port", str(port)
        ]
        logger.info(f"Starting MLflow UI with: {' '.join(cmd)}")
        subprocess.Popen(cmd)
        time.sleep(2)
        logger.info(f"MLflow UI available at http://127.0.0.1:{port}")

def find_mlflow_entity_by_run_id(run_id: str) -> mlflow.entities.Run | None:
    client = MlflowClient()
    try:
        return client.get_run(run_id)
    except Exception as e:
        logger.error(f"Could not fetch MLflow entity by run_id: {e}", exc_info=True)
        return None

def get_parent_run_info(run_id: str, client: MlflowClient) -> List[Tuple[str, str]]:
    """
    Recursively collects parent run info by traversing 'continued_from' tags.
    Returns list of (run_name, run_id), ordered from oldest ancestor to direct parent.
    """
    parent_infos = []
    current_run_id = run_id

    while current_run_id:
        try:
            run = client.get_run(current_run_id)
            if run.info.status != RunStatus.FINISHED:
                logger.warning(f"Run {current_run_id} is not FINISHED (status: {run.info.status})")

            run_name = run.data.tags.get("mlflow.runName", f"model_{current_run_id}")
            parent_infos.append((run_name, current_run_id))

            # Move to parent
            current_run_id = run.data.tags.get("continued_from")

        except Exception as e:
            logger.warning(f"Failed to retrieve parent run {current_run_id}: {e}")
            break

    return list(reversed(parent_infos))  # Oldest first


def build_tensorboard_command(
    current_run_id: str,
    current_run_name: str,
    parent_run_infos: List[Tuple[str, str]],
    current_tensorboard_path: str,
    client: MlflowClient,
    use_forward_slashes: bool = True
) -> str:
    """
    Builds a tensorboard --logdir command using given paths.
    current_tensorboard_path: local or final URI (e.g., staging or artifact URI)
    """
    logdir_entries = []

    # Add parents
    for parent_name, parent_id in parent_run_infos:
        try:
            parent_run = client.get_run(parent_id)
            parent_uri = parent_run.info.artifact_uri.rstrip("/").lstrip("file:///")
            tb_path = f"{parent_uri}/training_outputs/tensorboard_logs"
            if use_forward_slashes:
                tb_path = tb_path.replace("\\", "/")
            logdir_entries.append(f"{parent_name}:{tb_path}")
        except Exception as e:
            logger.warning(f"Could not resolve tensorboard path for parent {parent_id}: {e}")

    # Add current run
    safe_name = current_run_name.replace(" ", "_").replace(":", "-")
    tb_path = current_tensorboard_path.rstrip("/").lstrip("file:///")
    if use_forward_slashes:
        tb_path = tb_path.replace("\\", "/")
    logdir_entries.append(f"{safe_name}:{tb_path}")

    logdir_arg = ",".join(logdir_entries)
    return f"tensorboard --logdir_spec={logdir_arg}"