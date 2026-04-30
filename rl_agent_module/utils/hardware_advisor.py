import argparse
import json
import os
import platform
import sys
from urllib.parse import urlparse

try:
    import psutil
except ImportError:
    print("psutil not installed. Please install it via pip install psutil.")
    raise

try:
    import torch
except ImportError:
    print("torch not installed. Please install it via pip install torch.")
    raise

import mlflow
from mlflow.tracking import MlflowClient

# --- Project Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from config.rl_config import FEATURE_GROUPS, get_active_features

# Dynamically create the reverse mapping
FEATURE_TO_GROUP_MAP = {
    feature: group_name
    for group_name, features in FEATURE_GROUPS.items()
    for feature in features
}

class SystemInfoCollector:
    # ... (This class is unchanged)
    def __init__(self):
        self.data = {}
    def collect_cpu_info(self):
        self.data['cpu'] = {'physical_cores': psutil.cpu_count(logical=False)}
    def collect_ram_info(self):
        vm = psutil.virtual_memory()
        self.data['ram'] = {'total_gb': round(vm.total / (1024 ** 3), 2), 'available_gb': round(vm.available / (1024 ** 3), 2)}
    def collect_cuda_info(self):
        cuda_available = torch.cuda.is_available()
        self.data['cuda'] = {'available': cuda_available}
        if cuda_available:
            self.data['cuda']['device_count'] = torch.cuda.device_count()
            self.data['cuda']['devices'] = [{'name': torch.cuda.get_device_properties(i).name} for i in range(torch.cuda.device_count())]
    def collect_all(self) -> dict:
        self.collect_cpu_info()
        self.collect_ram_info()
        self.collect_cuda_info()
        return self.data

class RLHardwareAdvisor:
    # ... (This class is unchanged)
    IN_MEMORY_FACTOR = 2.5
    PROCESS_OVERHEAD_GB = 0.7
    def __init__(self, sys_info: dict, dataset_gb: float, safety_margin: float):
        self.sys_info = sys_info
        self.dataset_gb = dataset_gb
        self.safety_margin = safety_margin
        self.recommendations = {}
    def analyze(self):
        self._recommend_device()
        self._recommend_n_cpu()
        return self.recommendations
    def _recommend_device(self):
        if self.sys_info.get('cuda', {}).get('available'): self.recommendations['DEVICE'] = 'cuda'
        else: self.recommendations['DEVICE'] = 'cpu'
    def _recommend_n_cpu(self):
        usable_ram = self.sys_info['ram']['available_gb'] * self.safety_margin
        physical_cores = self.sys_info['cpu']['physical_cores']
        total_data_in_memory_gb = self.dataset_gb * self.IN_MEMORY_FACTOR
        self.recommendations['breakdown'] = []
        safe_cpu_options = []
        for n_cpu in range(1, physical_cores + 1):
            total_estimated_ram = total_data_in_memory_gb + (self.PROCESS_OVERHEAD_GB * n_cpu)
            status = "✅ OK" if total_estimated_ram < usable_ram else "❌ TOO HIGH"
            self.recommendations['breakdown'].append({"N_CPU": n_cpu, "Total_Est_RAM_GB": total_estimated_ram, "Status": status})
            if status == "✅ OK": safe_cpu_options.append(n_cpu)
        if safe_cpu_options: self.recommendations['N_CPU'] = max(safe_cpu_options)
        else:
            self.recommendations['N_CPU'] = 0
            if total_data_in_memory_gb > usable_ram: self.recommendations['analysis_notes'] = "WARNING: Dataset too large for available RAM."
            else: self.recommendations['analysis_notes'] = "WARNING: Not enough RAM for even one process."

def get_feature_store_path(dataset_run_id: str) -> str | None:
    # ... (This function is unchanged)
    try:
        client = MlflowClient()
        run = client.get_run(dataset_run_id)
        artifact_uri = run.info.artifact_uri
        parsed_uri = urlparse(artifact_uri)
        if parsed_uri.scheme == 'file':
            local_root = parsed_uri.path
            if platform.system() == "Windows" and local_root.startswith('/'): local_root = local_root[1:]
            return os.path.join(local_root, "feature_store")
        else: return None
    except Exception: return None

def calculate_data_size(feature_store_path: str) -> float:
    # ... (This function is unchanged)
    if not os.path.isdir(feature_store_path): return 0.0
    dummy_config = {"FEATURES_CONFIG": {f: True for f in FEATURE_TO_GROUP_MAP.keys()}}
    active_features = get_active_features(dummy_config)
    groups_to_load = { 'base_ohlcv' } | {FEATURE_TO_GROUP_MAP.get(f) for f in active_features if f in FEATURE_TO_GROUP_MAP}
    total_size_bytes = 0
    for group in groups_to_load:
        group_path = os.path.join(feature_store_path, f"group={group}")
        if os.path.isdir(group_path):
            for root, _, files in os.walk(group_path):
                for f in files:
                    if f.endswith(".parquet"): total_size_bytes += os.path.getsize(os.path.join(root, f))
    return total_size_bytes / (1024**3)

# --- NEW: Importable function that returns results as a dictionary ---
def get_hardware_recommendations(dataset_run_id: str, safety_margin: float = 0.9) -> dict:
    """Collects hardware info, analyzes dataset size, and returns recommendations."""
    # 1. Collect System Info
    sys_collector = SystemInfoCollector()
    sys_info = sys_collector.collect_all()

    # 2. Analyze Dataset Size
    feature_store_path = get_feature_store_path(dataset_run_id)
    total_data_gb = 0
    if feature_store_path:
        total_data_gb = calculate_data_size(feature_store_path)

    # 3. Get Recommendations
    advisor = RLHardwareAdvisor(sys_info, total_data_gb, safety_margin)
    recommendations = advisor.analyze()

    # 4. Combine all info into a single dictionary and return it
    return {
        "system_info": sys_info,
        "dataset_gb": total_data_gb,
        "recommendations": recommendations
    }


def display_advisor_results(results: dict):
    """Takes the results dictionary and prints a formatted summary."""
    sys_info = results['system_info']
    dataset_gb = results['dataset_gb']
    recs = results['recommendations']

    logger.info("--- Hardware Detection ---")
    logger.info(f"🖥️  CPU Cores: {sys_info['cpu']['physical_cores']} Physical")
    logger.info(f"🧠 RAM: {sys_info['ram']['available_gb']:.2f} GB Available / {sys_info['ram']['total_gb']:.2f} GB Total")
    if sys_info['cuda']['available']:
        logger.info(f"🚀 GPU: Found {sys_info['cuda']['device_count']} CUDA device(s) ({sys_info['cuda']['devices'][0]['name']})")
    else:
        logger.info("⚪️ GPU: No CUDA devices found.")

    logger.info("--- Dataset Analysis ---")
    logger.info(f"📊 Total on-disk size of dataset: {dataset_gb:.2f} GB")
    logger.info(f"📈 Estimated in-memory data size: {dataset_gb * RLHardwareAdvisor.IN_MEMORY_FACTOR:.2f} GB")

    logger.info("--- Recommendations ---")
    logger.info(f"Optimal Device: {recs['DEVICE']}")
    if recs['N_CPU'] > 0:
        logger.info(f"Optimal N_CPU (Sweet Spot): {recs['N_CPU']}")
    else:
        logger.warning(f"Optimal N_CPU: ⚠️ {recs.get('analysis_notes', 'Not enough RAM.')}")

    logger.info("="*70)
    logger.info("💡 Total System RAM Usage Calculation")
    logger.info("="*70)
    logger.info(f"{'N_CPU':>6} | {'Total Est. RAM (GB)':>25} | {'Status':>15}")
    logger.info("-"*70)
    for item in recs.get('breakdown', []):
        logger.info(f"{item['N_CPU']:>6} | {item['Total_Est_RAM_GB']:>25.2f} | {item['Status']:>15}")
    logger.info("-"*70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Training Hardware Advisor")
    parser.add_argument("--dataset-run-id", required=True)
    parser.add_argument("--output-file", help="Optional: Path to save recommended settings.")
    parser.add_argument("--safety-margin", type=float, default=0.9)
    parser.add_argument("--tracking-uri", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    # Setup logger and MLflow URI
    if not os.path.exists("log"): os.makedirs("log")
    setup_logging(logger_name='hardware_advisor', log_level_console='INFO')
    mlflow.set_tracking_uri(args.tracking_uri)

    # Get results by calling the new function
    results = get_hardware_recommendations(args.dataset_run_id, args.safety_margin)

    # Display the results
    display_advisor_results(results)

    # Save output if requested
    if args.output_file:
        settings_to_save = results['recommendations']
        with open(args.output_file, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        logger.info(f"✅ Recommended settings saved to {args.output_file}")
