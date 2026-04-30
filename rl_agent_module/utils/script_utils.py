# utils/script_utils.py

import json
import os


def generate_tensorboard_launch_scripts(
    command: str,
    output_dir: str
):
    """
    Generates both .sh and .bat launch scripts in the given directory.
    Uses UTF-8 encoding for future-proofing.
    """
    os.makedirs(output_dir, exist_ok=True)

    sh_path = os.path.join(output_dir, "launch_tensorboard.sh")
    with open(sh_path, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\n")
        f.write("# Launch TensorBoard with full training lineage\n")
        f.write(f"{command}\n")
    os.chmod(sh_path, 0o755)

    bat_path = os.path.join(output_dir, "launch_tensorboard.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write(":: Launch TensorBoard with full training lineage\n")
        f.write(f"{command}\n")


def generate_readme(
    command: str,
    output_dir: str
):
    """
    Generates a README.md with instructions, using UTF-8 encoding for emojis and special chars.
    """
    os.makedirs(output_dir, exist_ok=True)
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# Model Training Artifacts\n\n")
        f.write("## 📊 Visualize Training with TensorBoard\n\n")
        f.write("This model was trained with lineage from parent models. ")
        f.write("Use the command below or the provided scripts to launch TensorBoard:\n\n")
        f.write("```bash\n")
        f.write(f"{command}\n")
        f.write("```\n\n")
        f.write("### 🚀 Launch Scripts\n\n")
        f.write("- `launch_tensorboard.sh` — for Linux/macOS\n")
        f.write("- `launch_tensorboard.bat` — for Windows\n\n")
        f.write("### 📁 Log Directories Mapped:\n")
        f.write("Each entry is in `name:path` format:\n")
        for part in command.split("--logdir=")[-1].split(","):
            if ":" in part:
                name, path = part.split(":", 1)
                f.write(f"- `{name}` → `{path}`\n")
        f.write("\n> 💡 Tip: Run `pip install tensorboard` if not already installed.\n")

def generate_config_json(
    rl_config: dict,
    output_dir: str
):
    """
    Generates a README.md with instructions, using UTF-8 encoding for emojis and special chars.
    """
    os.makedirs(output_dir, exist_ok=True)
    rl_config_path = os.path.join(output_dir, "rl_config.json")
    with open(rl_config_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rl_config, indent=4))
        f.write("\n")
