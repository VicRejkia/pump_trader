# In telegram_interface.py (or a new utils_telegram.py)
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from dotenv import load_dotenv
import os
import json
import subprocess # For starting the bot
from datetime import datetime, timezone
import time

load_dotenv()

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_ID = os.getenv("TG_CHAT_ID")

STATUS_FILE_CHECK_SECONDS = 10 

PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) # Or however you define your project root
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
# Change to JSON for structured status
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

async def send_telegram_message(message: str):
    try:
        bot = Bot(token=TG_TOKEN)
        await bot.send_message(chat_id=TG_ID, text=message)
        # Consider adding logging here from your logger.py
    except Exception as e:
        # Log error
        print(f"Error sending Telegram message: {e}") # Replace with your logger

# --- Menu Definition ---
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the main menu."""
    keyboard = [
        [InlineKeyboardButton("💰 SOL Amount", callback_data='get_sol_amount')],
        [InlineKeyboardButton("📊 Subscribed Tokens", callback_data='get_token_count')],
        [InlineKeyboardButton("▶️ Start Trading Bot", callback_data='start_trading_bot')],
        [InlineKeyboardButton("⏹️ Stop Trading Bot", callback_data='stop_trading_bot')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)

# --- Callback Query Handlers for Menu Buttons ---
async def get_bot_actual_status() -> str:
    """
    Checks bot_status.json to determine if the bot is likely running, stopped, or in an error state.
    Returns one of "RUNNING", "STOPPED", "ERROR", "STARTING", "STOPPING", "UNKNOWN".
    """
    try:
        if not os.path.exists(STATUS_FILE):
            return "UNKNOWN" # Or "STOPPED" if you prefer

        # Check modification time first for a quick heuristic
        mtime = os.path.getmtime(STATUS_FILE)
        if (time.time() - mtime) > STATUS_FILE_CHECK_SECONDS * 2: # If file is much older than expected update interval
             # It might be stale, but let's check its content.
             pass

        with open(STATUS_FILE, 'r') as f:
            status_data = json.load(f)
        
        bot_process_status = status_data.get("bot_process_status", "UNKNOWN").upper()
        
        # More refined check based on the content of bot_status.json
        if bot_process_status == "RUNNING":
            # Double check timestamp from file content if available
            status_timestamp_str = status_data.get("timestamp")
            if status_timestamp_str:
                status_dt = datetime.fromisoformat(status_timestamp_str)
                # Ensure it's offset-aware for comparison with now(timezone.utc)
                if status_dt.tzinfo is None:
                    status_dt = status_dt.replace(tzinfo=timezone.utc)
                
                if (datetime.now(timezone.utc) - status_dt).total_seconds() <= STATUS_FILE_CHECK_SECONDS:
                    return "RUNNING"
                else:
                    # Content says RUNNING, but timestamp is old
                    return "STALE_RUNNING" # A new state to indicate it was running but might be dead
            return "RUNNING" # Fallback if timestamp missing but status is RUNNING
        elif bot_process_status in ["STOPPED", "ERROR_IN_STATUS_UPDATER", "ERROR_DB_SETUP"]:
            return "STOPPED" # Treat errors also as not actively running for start/stop logic
        elif bot_process_status == "STOPPING":
            return "STOPPING"
        elif bot_process_status == "STARTING":
            return "STARTING"
        
        return "UNKNOWN"

    except (IOError, json.JSONDecodeError, ValueError) as e:
        # logger.error(f"Error reading or parsing bot_status.json: {e}") # Use your logger
        print(f"Error reading or parsing bot_status.json: {e}")
        return "ERROR_READING_STATUS" # A specific error state

async def toggle_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the combined Start/Stop Bot command."""
    current_bot_status = await get_bot_actual_status()
    keyboard = []
    message_text = ""

    if current_bot_status == "RUNNING":
        # Offer to Stop
        try:
            with open(COMMAND_FILE, 'w') as f:
                f.write("STOP")
            message_text = "🛑 STOP command sent to the trading bot. It should shut down shortly."
            keyboard = [[InlineKeyboardButton("▶️ Start Trading Bot", callback_data='start_trading_bot')]]
        except Exception as e:
            message_text = f"Error sending STOP command: {e}"
            # Keep stop button if error, or refresh status?
            keyboard = [[InlineKeyboardButton("⏹️ Stop Trading Bot (Retry)", callback_data='stop_trading_bot')]]

    elif current_bot_status in ["STOPPED", "STALE_RUNNING", "ERROR_READING_STATUS", "UNKNOWN"]:
        # Offer to Start
        # Safety check using file modification time
        can_start = True
        detailed_reason = ""
        if os.path.exists(STATUS_FILE):
            try:
                mtime = os.path.getmtime(STATUS_FILE)
                file_age_seconds = time.time() - mtime
                
                # Additionally check the timestamp *inside* the JSON if status is RUNNING or STALE_RUNNING
                if current_bot_status in ["RUNNING", "STALE_RUNNING"]: # Should not happen if get_bot_actual_status is correct, but defensive
                    with open(STATUS_FILE, 'r') as f:
                        status_data_check = json.load(f)
                    status_timestamp_str_check = status_data_check.get("timestamp")
                    if status_timestamp_str_check:
                        status_dt_check = datetime.fromisoformat(status_timestamp_str_check)
                        if status_dt_check.tzinfo is None: status_dt_check = status_dt_check.replace(tzinfo=timezone.utc)
                        file_age_seconds = (datetime.now(timezone.utc) - status_dt_check).total_seconds()

                if file_age_seconds <= STATUS_FILE_CHECK_SECONDS:
                    can_start = False
                    detailed_reason = f"Status file was updated {file_age_seconds:.0f}s ago. Bot might still be running or shutting down."

            except (IOError, json.JSONDecodeError) as e:
                detailed_reason = f"Could not accurately check status file age due to error: {e}. Proceed with caution."
                # Potentially set can_start = False here too, or let user decide.

        if can_start:
            try:
                # Ensure command file is clear before starting
                if os.path.exists(COMMAND_FILE):
                    with open(COMMAND_FILE, 'w') as f: f.write("")

                # Path to your main trading bot script
                # Ensure PROJECT_ROOT_DIR points to the root of your 'pump_trader' project
                main_bot_script = os.path.join(PROJECT_ROOT_DIR, 'trading_bot.py') # Or 'trading_bot.py' if that's your entry point
                
                # Using subprocess.Popen to start the bot in the background
                # Ensure the Python interpreter used by Popen is the correct one (e.g., from your venv)
                # For simplicity, this assumes 'python' is the correct interpreter in PATH.
                # You might need to specify the full path to your venv's python executable.
                print(f"Attempting to start bot script: {main_bot_script}") # For debugging
                subprocess.Popen(['python', main_bot_script], cwd=PROJECT_ROOT_DIR, shell=True)
                
                message_text = "▶️ Attempting to start the trading bot... Please check status shortly."
                keyboard = [[InlineKeyboardButton("⏹️ Stop Trading Bot", callback_data='stop_trading_bot')]]
            except FileNotFoundError:
                message_text = f"Error: Bot script '{main_bot_script}' not found. Cannot start."
                keyboard = [[InlineKeyboardButton("▶️ Start Trading Bot (Retry)", callback_data='start_trading_bot')]]
            except Exception as e:
                message_text = f"Error attempting to start trading bot: {e}"
                keyboard = [[InlineKeyboardButton("▶️ Start Trading Bot (Retry)", callback_data='start_trading_bot')]]
        else:
            message_text = f"⚠️ Cannot start bot. {detailed_reason} Current reported status: {current_bot_status}."
            keyboard = [[InlineKeyboardButton("▶️ Start Trading Bot (Force - if sure)", callback_data='start_trading_bot_force')]] # Optional force start

    elif current_bot_status == "STOPPING":
        message_text = "⏳ Bot is currently stopping. Please wait."
        # Potentially offer a "Refresh Status" button or just wait for it to stop
        keyboard = [[InlineKeyboardButton("🔄 Refresh Status", callback_data='refresh_status')]]
    elif current_bot_status == "STARTING":
        message_text = "⏳ Bot is currently starting. Please wait."
        keyboard = [[InlineKeyboardButton("🔄 Refresh Status", callback_data='refresh_status')]]
    else: # Should ideally not be reached if get_bot_actual_status is comprehensive
        message_text = f"Bot status is '{current_bot_status}'. Unsure whether to start or stop."
        keyboard = [[InlineKeyboardButton("🔄 Refresh Status", callback_data='refresh_status')]]


    reply_markup = InlineKeyboardMarkup(keyboard)
    # If called via callback query (button press)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
    # If called via command
    else:
        await update.message.reply_text(text=message_text, reply_markup=reply_markup)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the main menu with a dynamic Start/Stop button."""
    current_bot_status = await get_bot_actual_status()
    
    start_stop_button_text = "▶️ Start Trading Bot"
    start_stop_callback_data = "start_trading_bot"

    if current_bot_status == "RUNNING":
        start_stop_button_text = "⏹️ Stop Trading Bot"
        start_stop_callback_data = "stop_trading_bot"
    elif current_bot_status == "STARTING" or current_bot_status == "STOPPING":
        start_stop_button_text = f"⏳ Bot is {current_bot_status.lower()}..."
        start_stop_callback_data = "refresh_status" # Or a disabled state

    keyboard = [
        [InlineKeyboardButton("💰 SOL Amount", callback_data='get_sol_amount')],
        [InlineKeyboardButton("📊 Subscribed Tokens", callback_data='get_token_count')],
        [InlineKeyboardButton(start_stop_button_text, callback_data=start_stop_callback_data)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)

# Modify button_callback_handler to call toggle_bot_command for start/stop
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text or triggers actions."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press

    command = query.data
    message_text = "Processing..." # Default message

    if command == 'get_sol_amount':
        # ... (your existing get_sol_amount logic) ...
        # Example:
        try:
            with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
            sol_balance = bot_status.get("current_sol_balance", "N/A")
            sol_price_usd = bot_status.get("current_sol_price_usd", "N/A")
            portfolio_usd = bot_status.get("current_portfolio_value_usd", "N/A")
            message_text = (
                f"💰 SOL: {sol_balance if isinstance(sol_balance, (int, float)) else 'N/A':.4f}\n"
                f"💲 Price: ${sol_price_usd if isinstance(sol_price_usd, (int, float)) else 'N/A':.2f}\n"
                f"💼 Value: ${portfolio_usd if isinstance(portfolio_usd, (int, float)) else 'N/A':.2f}"
            )
        except Exception as e: message_text = f"Error: {e}"
        await query.edit_message_text(text=message_text, reply_markup=query.message.reply_markup) # Keep original menu

    elif command == 'get_token_count':
        # ... (your existing get_token_count logic) ...
        # Example:
        try:
            with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
            count = bot_status.get("active_token_subscriptions_count", "N/A")
            message_text = f"📊 Subscribed Tokens: {count}"
        except Exception as e: message_text = f"Error: {e}"
        await query.edit_message_text(text=message_text, reply_markup=query.message.reply_markup) # Keep original menu

    elif command == 'start_trading_bot' or command == 'stop_trading_bot' or command == 'start_trading_bot_force':
        # Call the unified toggle function. It will determine the actual action.
        # Note: 'start_trading_bot_force' is not explicitly handled by get_bot_actual_status in this example yet,
        # but toggle_bot_command structure allows for it.
        await toggle_bot_command(update, context) # Pass the update to allow editing the message

    elif command == 'refresh_status':
        # Re-display the menu, which will fetch the current status
        await menu_command(update.callback_query.message, context) # Use query.message for original message
        # Delete the "⏳ Bot is stopping..." message after refresh.
        # This might be tricky if the menu is edited. Simpler to just let the menu update itself.
        # await query.delete_message() # Optional: if you want to remove the status message

    else:
        await query.edit_message_text(text=f"Unknown command: {command}")


def main_telegram_bot() -> None:
    application = Application.builder().token(TG_TOKEN).build()

    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    # Add other direct command handlers (like /start_bot, /stop_bot if preferred over menu)

    application.run_polling()

if __name__ == '__main__':
    # Ensure environment variables for token and chat ID are set
    if not TG_TOKEN or not TG_ID:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables not set.")
    else:
        main_telegram_bot()