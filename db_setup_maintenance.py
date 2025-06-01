# db_setup_maintenance.py
import argparse
import asyncio
import os
import sys
import subprocess
import json
from datetime import datetime, timezone
import logging

from dotenv import load_dotenv

# Ensure project root is in sys.path if this script is in a subdirectory (though you plan it for root)
PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT_DIR not in sys.path:
    sys.path.append(PROJECT_ROOT_DIR)

from database_handler import DatabaseClient, _config_module_to_dict
import config as base_config_module # For initial dynamic_config.json

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
SQL_DIR = os.path.join(PROJECT_ROOT_DIR, 'sql') # Used by DatabaseClient.init_db()
BACKUP_DIR = os.path.join(PROJECT_ROOT_DIR, 'backups')

# Files to create/ensure
BOT_COMMAND_FILE = os.path.join(DATA_DIR, 'bot_command.txt')
BOT_STATUS_FILE = os.path.join(DATA_DIR, 'bot_status.json')
SOL_PRICE_FILE = os.path.join(DATA_DIR, 'sol_price.json')
SUBSCRIPTIONS_FILE = os.path.join(DATA_DIR, 'current_subscriptions.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR, 'dynamic_config.json')
CREATOR_WALLETS_BACKUP_FILE = os.path.join(DATA_DIR, 'creator_wallets_backup.json') # For ensuring it exists if needed by restore


def ensure_project_structure():
    """Creates necessary directories and empty/default files if they don't exist."""
    script_logger.info("Ensuring project directory structure and files...")
    os.makedirs(DATA_DIR, exist_ok=True)
    script_logger.info(f"Ensured directory: {DATA_DIR}")
    os.makedirs(LOG_DIR, exist_ok=True)
    script_logger.info(f"Ensured directory: {LOG_DIR}")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    script_logger.info(f"Ensured directory: {BACKUP_DIR}")

    if not os.path.exists(BOT_COMMAND_FILE):
        with open(BOT_COMMAND_FILE, 'w') as f:
            f.write("")
        script_logger.info(f"Created empty file: {BOT_COMMAND_FILE}")

    if not os.path.exists(BOT_STATUS_FILE):
        with open(BOT_STATUS_FILE, 'w') as f:
            json.dump({"bot_process_status": "STOPPED", "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=4)
        script_logger.info(f"Created default file: {BOT_STATUS_FILE}")

    if not os.path.exists(SOL_PRICE_FILE):
        with open(SOL_PRICE_FILE, 'w') as f:
            json.dump({"price": None}, f, indent=4)
        script_logger.info(f"Created default file: {SOL_PRICE_FILE}")

    if not os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'w') as f:
            json.dump([], f, indent=4) # Empty list for subscriptions
        script_logger.info(f"Created default file: {SUBSCRIPTIONS_FILE}")

    if not os.path.exists(DYNAMIC_CONFIG_FILE):
        try:
            default_dynamic_config = _config_module_to_dict(base_config_module)
            # Filter for JSON serializable if necessary, though _config_module_to_dict usually handles it
            serializable_config = {}
            for key, value in default_dynamic_config.items():
                if isinstance(value, set): # Convert sets to lists for JSON
                    serializable_config[key] = list(value)
                elif isinstance(value, (int, float, str, bool, list, dict)) or value is None:
                    serializable_config[key] = value
                else:
                    serializable_config[key] = str(value) # Convert other types to string

            with open(DYNAMIC_CONFIG_FILE, 'w') as f:
                json.dump(serializable_config, f, indent=4, sort_keys=True)
            script_logger.info(f"Created default file with base config: {DYNAMIC_CONFIG_FILE}")
        except Exception as e:
            script_logger.error(f"Could not create default {DYNAMIC_CONFIG_FILE}: {e}")

    # Check for creator_wallets_backup.json, create empty if not present, as restore_creator_wallets expects it
    if not os.path.exists(CREATOR_WALLETS_BACKUP_FILE):
        with open(CREATOR_WALLETS_BACKUP_FILE, 'w') as f:
            json.dump([], f, indent=4) # Empty list if no backup exists
        script_logger.info(f"Created empty template: {CREATOR_WALLETS_BACKUP_FILE} (fill if needed for restore)")
    script_logger.info("Project structure check complete.")


async def handle_init(db_client: DatabaseClient):
    """Initializes the database schema and populates creator_wallets."""
    script_logger.info("Starting database initialization (--init)...")
    ensure_project_structure() # Ensure files and folders are created first

    try:
        await db_client.connect()
        script_logger.info("Connected to the database.")

        script_logger.info("Initializing database schema from SQL files...")
        await db_client.init_db() # Creates tables, views, etc.
        script_logger.info("Database schema initialized.")

        script_logger.info("Restoring creator wallets...")
        await db_client.restore_creator_wallets() # Populates creator_wallets table
        script_logger.info("Creator wallets restored.")

        script_logger.info("Database initialization complete.")
    except Exception as e:
        script_logger.error(f"Error during database initialization: {e}", exc_info=True)
    finally:
        if db_client.pool:
            await db_client.close()
            script_logger.info("Database connection closed.")

def handle_backup():
    """Creates a full backup of the PostgreSQL database using pg_dump."""
    script_logger.info("Starting database backup (--backup)...")
    load_dotenv() # Ensure environment variables are loaded for pg_dump

    db_name = os.getenv("DB_DATABASE")
    db_user = os.getenv("DB_USER")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432") # Default PG port
    # PGPASSWORD should be set in the environment for pg_dump to pick it up automatically

    if not all([db_name, db_user, db_host]):
        script_logger.error("Database connection details (DB_DATABASE, DB_USER, DB_HOST) not found in .env file. Backup aborted.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(BACKUP_DIR, f"db_backup_{db_name}_{timestamp}.sql")

    pg_dump_path = "pg_dump" # Assumes pg_dump is in PATH, otherwise provide full path

    command = [
        pg_dump_path,
        "--host", db_host,
        "--port", db_port,
        "--username", db_user,
        "--dbname", db_name,
        "--format=plain",  # Plain SQL text file
        "--file", backup_file_path,
        "--no-password",   # Relies on PGPASSWORD env var or .pgpass
        "--verbose"
    ]

    script_logger.info(f"Executing pg_dump: {' '.join(command)} (excluding password)")
    try:
        # Set PGPASSWORD for the subprocess if it's in os.environ
        env = os.environ.copy()
        if "DB_PASSWORD" in env: # If your .env uses DB_PASSWORD
            env["PGPASSWORD"] = env["DB_PASSWORD"]

        process = subprocess.run(command, capture_output=True, text=True, check=True, env=env)
        script_logger.info(f"pg_dump output: {process.stdout}")
        if process.stderr:
            script_logger.warning(f"pg_dump errors/warnings: {process.stderr}")
        script_logger.info(f"Database backup successful: {backup_file_path}")
    except subprocess.CalledProcessError as e:
        script_logger.error(f"pg_dump failed with exit code {e.returncode}.")
        script_logger.error(f"Stdout: {e.stdout}")
        script_logger.error(f"Stderr: {e.stderr}")
        script_logger.error("Database backup failed.")
    except FileNotFoundError:
        script_logger.error(f"pg_dump command not found. Is PostgreSQL client tools installed and in PATH? Searched for '{pg_dump_path}'.")
        script_logger.error("Database backup failed.")
    except Exception as e:
        script_logger.error(f"An unexpected error occurred during backup: {e}", exc_info=True)
        script_logger.error("Database backup failed.")

async def handle_cleanup(db_client: DatabaseClient):
    """Backs up, cleans (drops tables), and re-initializes the database."""
    script_logger.info("Starting database cleanup (--cleanup)...")

    script_logger.info("Step 1: Performing backup before cleanup...")
    handle_backup() # Perform a backup first

    script_logger.info("Step 2: Cleaning up database (dropping tables)...")
    try:
        await db_client.connect()
        script_logger.info("Connected to the database for cleanup.")

        # The existing cleanup_db in DatabaseClient should drop known tables.
        # For a more thorough cleanup, one might drop the entire schema if it's dedicated,
        # or list all tables and views in the public schema and drop them.
        # The current `cleanup_db` uses `CASCADE` which is helpful.
        await db_client.cleanup_db(cleanup_flag=True)
        script_logger.info("Tables dropped successfully.")

        script_logger.info("Step 3: Re-initializing database schema...")
        await db_client.init_db() # Recreate tables and views
        script_logger.info("Database schema re-initialized.")

        script_logger.info("Step 4: Restoring creator wallets...")
        await db_client.restore_creator_wallets() # Repopulate creator_wallets
        script_logger.info("Creator wallets restored.")

        script_logger.info("Database cleanup and re-initialization complete.")
    except Exception as e:
        script_logger.error(f"Error during database cleanup and re-initialization: {e}", exc_info=True)
    finally:
        if db_client.pool:
            await db_client.close()
            script_logger.info("Database connection closed.")


async def main_async():
    load_dotenv() # Load .env file for database credentials

    parser = argparse.ArgumentParser(description="PumpTrader Database Setup and Maintenance Script")
    parser.add_argument("--init", action="store_true", help="Initialize database, create schema, and restore creator wallets. This is the default action if no flags are provided.")
    parser.add_argument("--backup", action="store_true", help="Create a full backup of the database.")
    parser.add_argument("--cleanup", action="store_true", help="Backup database, then drop all tables/views, and re-initialize the schema and creator wallets.")
    args = parser.parse_args()

    # Default action is --init if no other action is specified
    is_init = args.init
    is_backup = args.backup
    is_cleanup = args.cleanup

    if not is_init and not is_backup and not is_cleanup:
        script_logger.info("No specific action provided, defaulting to --init.")
        is_init = True

    db_client = DatabaseClient() # Uses config.py for its internal default config if needed

    if is_backup and not is_cleanup: # If only --backup is called
        handle_backup()
    elif is_init and not is_cleanup: # If only --init or default
        await handle_init(db_client)
    elif is_cleanup: # --cleanup includes backup and init steps
        await handle_cleanup(db_client)
    else:
        # This case should ideally not be reached if default action is handled
        script_logger.info("Please specify an action: --init, --backup, or --cleanup.")

if __name__ == "__main__":
    if os.name == 'nt': # Required for Windows if using asyncio.subprocess in some cases, though pg_dump here uses subprocess.run
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        script_logger.info("Script interrupted by user.")
    except Exception as e:
        script_logger.critical(f"A critical error occurred: {e}", exc_info=True)