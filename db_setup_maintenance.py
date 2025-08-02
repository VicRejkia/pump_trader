# db_setup_maintenance.py
import argparse
import asyncio
import os
import sys
import subprocess
import json
from datetime import datetime, timezone
import logging
from typing import List

from dotenv import load_dotenv, find_dotenv

# Ensure project root is in sys.path if this script is in a subdirectory
PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT_DIR not in sys.path:
    sys.path.append(PROJECT_ROOT_DIR)

from database_handler import DatabaseClient
import config.config as base_config_module

# --- Basic Logger Setup for this script ---
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
script_logger = logging.getLogger("DBSetupMaintenance")
script_logger.addHandler(handler)
script_logger.setLevel(logging.INFO)

# --- Configuration ---
DATA_DIR = os.path.join(PROJECT_ROOT_DIR, 'data')
LOG_DIR = os.path.join(PROJECT_ROOT_DIR, getattr(base_config_module, '_LOG_STORAGE_PATH', 'log'))
BACKUP_DIR = os.path.join(PROJECT_ROOT_DIR, getattr(base_config_module, '_BACKUP_STORAGE_PATH', 'backups'))
SQL_DIR = os.path.join(PROJECT_ROOT_DIR, 'sql')

# Files to create/ensure
BOT_COMMAND_FILE = os.path.join(DATA_DIR, 'bot_command.txt')
BOT_STATUS_FILE = os.path.join(DATA_DIR, 'bot_status.json')
SOL_PRICE_FILE = os.path.join(DATA_DIR, 'sol_price.json')
SUBSCRIPTIONS_FILE = os.path.join(DATA_DIR, 'current_subscriptions.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR, 'dynamic_config.json')
CREATOR_WALLETS_BACKUP_FILE = os.path.join(DATA_DIR, 'creator_wallets_backup.json')

# --- Helper function to manage pg_dump path in .env file ---

def update_env_file(key_to_update: str, new_value: str) -> bool:
    """
    Updates or appends a key-value pair to the .env file.
    Wraps the value in quotes if it contains spaces.
    """
    env_path = find_dotenv()
    if not env_path:
        env_path = os.path.join(PROJECT_ROOT_DIR, '.env')
        script_logger.info("No .env file found. Creating one.")

    if ' ' in new_value and not (new_value.startswith('"') and new_value.endswith('"')):
        new_value = f'"{new_value}"'

    new_line = f"{key_to_update}={new_value}"
    
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
        key_found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key_to_update}="):
                lines[i] = new_line + '\n'
                key_found = True
                break
        
        if not key_found:
            if lines and not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append(new_line + '\n')

        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        return True
    except IOError as e:
        script_logger.error(f"Failed to write to .env file at {env_path}: {e}")
        return False

def prompt_and_save_to_env() -> str | None:
    """Prompts the user for the path to pg_dump.exe, validates it, and saves it to the .env file."""
    while True:
        script_logger.warning("Could not find 'pg_dump'.")
        user_input_path = input(
            "Please enter the full, absolute path to your 'pg_dump.exe' file and press Enter:\n"
            r"(e.g., C:\Program Files\PostgreSQL\16\bin\pg_dump.exe)"
            "\n> "
        ).strip()

        if user_input_path.startswith('"') and user_input_path.endswith('"'):
            user_input_path = user_input_path[1:-1]

        normalized_path = user_input_path.replace('\\', '/')

        if os.path.exists(normalized_path) and os.path.isfile(normalized_path) and 'pg_dump' in os.path.basename(normalized_path).lower():
            script_logger.info(f"Path validated: {normalized_path}")
            if update_env_file('PG_DUMP_PATH', normalized_path):
                script_logger.info("Successfully saved pg_dump path to .env file for future use.")
                load_dotenv(override=True)
            return normalized_path
        else:
            script_logger.error(f"Invalid path: '{user_input_path}'. Please ensure the path is correct and points to the 'pg_dump.exe' file.")
            retry = input("Try again? (y/n): ").lower()
            if retry != 'y':
                return None


# --- (The rest of the file remains unchanged until handle_backup) ---

def ensure_project_structure():
    """Creates necessary directories and empty/default files if they don't exist."""
    script_logger.info("Ensuring project directory structure and files...")
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.path.exists(BOT_COMMAND_FILE):
        with open(BOT_COMMAND_FILE, 'w', encoding='utf-8') as f: f.write("")
        script_logger.info(f"Created empty file: {BOT_COMMAND_FILE}")
    if not os.path.exists(BOT_STATUS_FILE):
        with open(BOT_STATUS_FILE, 'w', encoding='utf-8') as f: json.dump({"bot_process_status": "STOPPED", "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=4)
        script_logger.info(f"Created default file: {BOT_STATUS_FILE}")
    if not os.path.exists(SOL_PRICE_FILE):
        with open(SOL_PRICE_FILE, 'w', encoding='utf-8') as f: json.dump({"price": None}, f, indent=4)
        script_logger.info(f"Created default file: {SOL_PRICE_FILE}")
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f: json.dump([], f, indent=4)
        script_logger.info(f"Created default file: {SUBSCRIPTIONS_FILE}")
    if not os.path.exists(DYNAMIC_CONFIG_FILE):
        try:
            from database_handler import _config_module_to_dict
            default_dynamic_config = _config_module_to_dict(base_config_module)
            serializable_config = {}
            for key, value in default_dynamic_config.items():
                if isinstance(value, set): serializable_config[key] = list(value)
                elif isinstance(value, (int, float, str, bool, list, dict)) or value is None: serializable_config[key] = value
                else: serializable_config[key] = str(value)
            with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(serializable_config, f, indent=4, sort_keys=True)
            script_logger.info(f"Created default file with base config: {DYNAMIC_CONFIG_FILE}")
        except Exception as e:
            script_logger.error(f"Could not create default {DYNAMIC_CONFIG_FILE}: {e}")
    if not os.path.exists(CREATOR_WALLETS_BACKUP_FILE):
        with open(CREATOR_WALLETS_BACKUP_FILE, 'w', encoding='utf-8') as f: json.dump([], f, indent=4)
        script_logger.info(f"Created empty template: {CREATOR_WALLETS_BACKUP_FILE} (fill if needed for restore)")
    script_logger.info("Project structure check complete.")


async def handle_init(db_client: DatabaseClient):
    """Initializes the database schema and populates creator_wallets."""
    script_logger.info("Starting database initialization (--init)...")
    ensure_project_structure()
    try:
        await db_client.connect()
        script_logger.info("Connected to the database.")
        script_logger.info("Initializing database schema from SQL files...")
        await db_client.init_db()
        script_logger.info("Database schema initialized.")
        script_logger.info("Restoring creator wallets from backup file...")
        await db_client.restore_creator_wallets()
        script_logger.info("Creator wallets restored.")
        script_logger.info("Database initialization complete.")
    except Exception as e:
        script_logger.error(f"Error during database initialization: {e}", exc_info=True)
    finally:
        if db_client.pool: await db_client.close(); script_logger.info("Database connection closed.")

def handle_backup():
    """Creates a full backup of the PostgreSQL database using pg_dump."""
    script_logger.info("Starting database backup (--backup)...")
    load_dotenv(override=True)
    db_name = os.getenv("DB_DATABASE")
    db_user = os.getenv("DB_USER")
    db_host_raw = os.getenv("DB_HOST")
    db_port_raw = os.getenv("DB_PORT", "5432")

    if not all([db_name, db_user, db_host_raw]):
        script_logger.error("Database connection details (DB_DATABASE, DB_USER, DB_HOST) not found in .env file. Backup aborted.")
        return

    if ':' in db_host_raw:
        parts = db_host_raw.split(':')
        db_host = parts[0]
        db_port = parts[1]
        script_logger.warning(f"Host '{db_host_raw}' contains a port. Splitting into host='{db_host}' and port='{db_port}'.")
    else:
        db_host = db_host_raw
        db_port = db_port_raw

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # --- START OF CHANGE ---
    # Change the filename extension to .backup to reflect the new format.
    backup_file_path = os.path.join(BACKUP_DIR, f"db_backup_{db_name}_{timestamp}.backup")
    # --- END OF CHANGE ---

    pg_dump_path = os.getenv('PG_DUMP_PATH', 'pg_dump')
    
    command = [
        pg_dump_path, "--host", db_host, "--port", db_port, "--username", db_user,
        "--dbname", db_name,
        # --- START OF CHANGE ---
        # Change the format from 'plain' to 'custom' for a compressed binary backup.
        "--format=custom", 
        # --- END OF CHANGE ---
        "--file", backup_file_path, "--no-password", "--verbose"
    ]

    script_logger.info(f"Attempting to execute pg_dump using path: '{pg_dump_path}'")
    try:
        env = os.environ.copy()
        if "DB_PASSWORD" in env: env["PGPASSWORD"] = env["DB_PASSWORD"]
        process = subprocess.run(command, capture_output=True, text=True, check=True, env=env)
        if process.stdout: script_logger.info(f"pg_dump output: {process.stdout}")
        if process.stderr: script_logger.warning(f"pg_dump errors/warnings: {process.stderr}")
        script_logger.info(f"Database backup successful: {backup_file_path}")
        script_logger.info("IMPORTANT: To restore this file, you must use the 'pg_restore' utility.")

    except FileNotFoundError:
        new_path = prompt_and_save_to_env()
        if new_path:
            script_logger.info("Retrying backup with the newly provided path...")
            handle_backup()
        else:
            script_logger.error("Database backup failed. Path to 'pg_dump' was not provided.")
    except subprocess.CalledProcessError as e:
        if "fe_sendauth: no password supplied" in e.stderr:
             script_logger.error("pg_dump failed: Authentication error. Ensure DB_PASSWORD is set correctly in your .env file.")
        else:
            script_logger.error(f"pg_dump failed with exit code {e.returncode}.\nStdout: {e.stdout}\nStderr: {e.stderr}")
        script_logger.error("Database backup failed.")
    except Exception as e:
        script_logger.error(f"An unexpected error occurred during backup: {e}", exc_info=True)
        script_logger.error("Database backup failed.")

async def handle_cleanup(db_client: DatabaseClient):
    """Backs up, cleans tables, and re-initializes the database."""
    script_logger.info("Starting database cleanup (--cleanup)...")
    script_logger.info("Step 1: Performing backup before cleanup...")
    handle_backup()
    script_logger.info("Step 2: Cleaning up database (dropping all application tables)...")
    try:
        await db_client.connect()
        script_logger.info("Connected to the database for cleanup.")
        tables_to_drop = [
            'tokens', 'trades', 'rugcheck', 'portfolio', 'migrations',
            'dexscreener_data', 'sol_price_usd', 'creator_wallets',
            'bot_heartbeat', 'configurations',
            'tokens_backup', 'trades_backup', 'rugcheck_backup',
            'portfolio_backup', 'migrations_backup', 'dexscreener_data_backup'
        ]
        async with db_client.pool.acquire() as conn:
            for table in tables_to_drop:
                try:
                    await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                    script_logger.info(f"🗑️ Dropped table {table}")
                except Exception as e:
                    script_logger.error(f"Error dropping table {table}: {e}", exc_info=False)
        script_logger.info("All known application tables dropped successfully.")
        script_logger.info("Step 3: Re-initializing database schema...")
        await db_client.init_db()
        script_logger.info("Database schema re-initialized.")
        script_logger.info("Step 4: Restoring creator wallets...")
        await db_client.restore_creator_wallets()
        script_logger.info("Creator wallets restored.")
        script_logger.info("Database cleanup and re-initialization complete.")
    except Exception as e:
        script_logger.error(f"Error during database cleanup and re-initialization: {e}", exc_info=True)
    finally:
        if db_client.pool: await db_client.close(); script_logger.info("Database connection closed.")

async def main_async():
    load_dotenv()
    parser = argparse.ArgumentParser(description="PumpTrader Database Setup and Maintenance Script")
    parser.add_argument("--init", action="store_true", help="Initialize database, create schema, and restore creator wallets. Default action.")
    parser.add_argument("--backup", action="store_true", help="Create a full backup of the database.")
    parser.add_argument("--cleanup", action="store_true", help="Backup, drop all tables, and re-initialize the schema.")
    args = parser.parse_args()
    is_init, is_backup, is_cleanup = args.init, args.backup, args.cleanup
    if not any([is_init, is_backup, is_cleanup]):
        script_logger.info("No specific action provided, defaulting to --init.")
        is_init = True
    db_client = DatabaseClient()
    if is_cleanup: await handle_cleanup(db_client)
    elif is_backup: handle_backup()
    elif is_init: await handle_init(db_client)
    else: script_logger.info("Please specify an action: --init, --backup, or --cleanup.")

if __name__ == "__main__":
    if os.name == 'nt': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        script_logger.info("Script interrupted by user.")
    except Exception as e:
        script_logger.critical(f"A critical error occurred: {e}", exc_info=True)