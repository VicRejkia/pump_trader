# telegram_interface.py
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from dotenv import load_dotenv
import os
import json
import subprocess # For starting the bot
from datetime import datetime, timezone
import time
import sys # For sys.executable
import re # For escaping markdown

load_dotenv()

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_ID = os.getenv("TG_CHAT_ID")

STATUS_FILE_CHECK_SECONDS = 10

# --- Directory Setup ---
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = CURRENT_SCRIPT_DIR # Assuming this script is in the project root
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

# Ensure data directory exists
if not os.path.exists(DATA_DIR_BOT):
    os.makedirs(DATA_DIR_BOT)
    print(f"Created data directory: {DATA_DIR_BOT}")

# --- Conversation States for Config Editing ---
CHOOSING_PARAM, TYPING_VALUE = range(2)
EDIT_CONFIG_PARAM_KEY = "edit_config_param_name"

# --- Markdown Escaping Helpers ---
def escape_markdown_v2_text(text: str) -> str:
    """Escapes text for general MarkdownV2 context."""
    # Characters to escape for MarkdownV2.
    # Note: '.' and '!' are only special if not part of a URL and might need context.
    # For broad safety, we escape them. Hyphen '-' is also critical.
    escape_chars = r'\_*[]()~`>#+-=|{}.!' # Removed '.' from here temporarily, handle manually. Added '-'
    # Escape hyphen first to avoid issues with it being in a range in char sets if not careful.
    # Simpler to just list it.
    processed_text = text
    for char in r'_*[]()~`>#+-=|{}.!': # Iterate and replace
        if char in processed_text: # Check if char exists to avoid unnecessary replaces
            processed_text = processed_text.replace(char, f'\\{char}')
    return processed_text


def escape_markdown_v2_text_for_code_block(text: str) -> str:
    """Escapes text specifically for placing inside MarkdownV2 inline code (`...`).
       According to PTB docs, only `\` and `` ` `` need escaping inside code.
    """
    processed_text = text.replace('\\', '\\\\') # Escape backslash first
    processed_text = processed_text.replace('`', '\\`')  # Then escape backtick
    return processed_text

# --- Helper Functions for Dynamic Config ---
def load_dynamic_config() -> dict:
    try:
        if os.path.exists(DYNAMIC_CONFIG_FILE):
            with open(DYNAMIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading {DYNAMIC_CONFIG_FILE}: {e}")
        return {}

def save_dynamic_config(config_data: dict) -> bool:
    try:
        with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, sort_keys=True)
        return True
    except IOError as e:
        print(f"Error saving {DYNAMIC_CONFIG_FILE}: {e}")
        return False

def get_type_hint(value) -> str:
    if isinstance(value, bool): return " (boolean: true/false)"
    if isinstance(value, int): return " (integer)"
    if isinstance(value, float): return " (float)"
    if isinstance(value, list):
        if value and all(isinstance(item, str) for item in value): # Check if list not empty
            return " (list of strings, comma-separated)"
        return " (list)"
    return " (string)"

# --- Telegram Bot Functions ---
async def send_telegram_message(message: str):
    try:
        bot = Bot(token=TG_TOKEN)
        await bot.send_message(chat_id=TG_ID, text=message)
        print(f"Telegram message sent: {message}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

async def get_bot_actual_status() -> str:
    try:
        if not os.path.exists(STATUS_FILE): return "UNKNOWN"
        with open(STATUS_FILE, 'r') as f: status_data = json.load(f)
        bot_process_status = status_data.get("bot_process_status", "UNKNOWN").upper()
        status_timestamp_str = status_data.get("timestamp")
        if not status_timestamp_str:
            return "STALE_RUNNING" if bot_process_status == "RUNNING" else (bot_process_status or "UNKNOWN")
        
        # Ensure status_dt is timezone-aware (UTC)
        status_dt_naive = datetime.fromisoformat(status_timestamp_str)
        status_dt = status_dt_naive.replace(tzinfo=status_dt_naive.tzinfo or timezone.utc)

        age_seconds = (datetime.now(timezone.utc) - status_dt).total_seconds()

        if bot_process_status == "RUNNING": return "RUNNING" if age_seconds <= STATUS_FILE_CHECK_SECONDS * 1.5 else "STALE_RUNNING"
        if bot_process_status == "STARTING": return "STARTING" if age_seconds <= STATUS_FILE_CHECK_SECONDS * 3 else "STALE_RUNNING"
        if bot_process_status == "STOPPING": return "STOPPING" if age_seconds <= STATUS_FILE_CHECK_SECONDS * 3 else "STOPPED"
        if bot_process_status in ["STOPPED", "ERROR_IN_STATUS_UPDATER", "ERROR_DB_SETUP", "CRASHED"]: return "STOPPED"
        return "UNKNOWN" if age_seconds > STATUS_FILE_CHECK_SECONDS * 2 else bot_process_status
    except (IOError, json.JSONDecodeError, ValueError) as e: print(f"Error reading status.json: {e}"); return "ERROR_READING_STATUS"
    except Exception as e: print(f"Unexpected error in get_bot_actual_status: {e}"); return "ERROR_READING_STATUS"


async def toggle_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE, force_start_flag: bool = False) -> None:
    current_bot_status = await get_bot_actual_status()
    keyboard = []
    message_text = ""
    if current_bot_status == "RUNNING":
        try:
            with open(COMMAND_FILE, 'w') as f: f.write("STOP")
            message_text = "🛑 STOP command sent to the trading bot."
            keyboard = [[InlineKeyboardButton("▶️ Start Trading Bot", callback_data='start_trading_bot')], [InlineKeyboardButton("🔄 Refresh Status", callback_data='refresh_status')]]
        except Exception as e: message_text = f"Error sending STOP: {e}"; keyboard = [[InlineKeyboardButton("⏹️ Stop (Retry)", callback_data='stop_trading_bot')]]
    elif force_start_flag or current_bot_status in ["STOPPED", "STALE_RUNNING", "ERROR_READING_STATUS", "UNKNOWN"]:
        can_start = True; detailed_reason = ""; message_text = "▶️ Attempting to start..."
        if force_start_flag: detailed_reason = "Force start."; message_text = "▶️ FORCE STARTING..."
        else:
            if os.path.exists(STATUS_FILE):
                try:
                    s = await get_bot_actual_status()
                    if s in ["RUNNING", "STARTING"]: can_start=False; detailed_reason=f"Bot is {s}."
                    elif s == "STOPPING": can_start=False; detailed_reason="Bot is STOPPING."
                except Exception as e: detailed_reason = f"Status check error: {e}."
        if can_start:
            try:
                if os.path.exists(COMMAND_FILE):
                    with open(COMMAND_FILE, 'w') as f: f.write("")
                scr, exe = os.path.join(PROJECT_ROOT_DIR, 'trading_bot.py'), sys.executable
                if not os.path.exists(scr): raise FileNotFoundError(f"Script not found: {scr}")
                subprocess.Popen([exe, scr], cwd=PROJECT_ROOT_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                keyboard = [[InlineKeyboardButton("⏹️ Stop Trading Bot", callback_data='stop_trading_bot')], [InlineKeyboardButton("🔄 Refresh Status", callback_data='refresh_status')]]
            except Exception as e: message_text = f"Start Error: {e}"; keyboard = [[InlineKeyboardButton("▶️ Start (Retry)", callback_data='start_trading_bot')]]
        else: message_text = f"⚠️ Cannot start. {detailed_reason} Status: {current_bot_status}."; keyboard = [[InlineKeyboardButton("▶️ Start (Force)", callback_data='start_trading_bot_force')], [InlineKeyboardButton("🔄 Refresh", callback_data='refresh_status')]]
    elif current_bot_status == "STARTING": message_text="⏳ Starting..."; keyboard = [[InlineKeyboardButton("⏹️ Stop", callback_data='stop_trading_bot')],[InlineKeyboardButton("🔄 Refresh",callback_data='refresh_status')]]
    elif current_bot_status == "STOPPING": message_text="⏳ Stopping..."; keyboard = [[InlineKeyboardButton("▶️ Start", callback_data='start_trading_bot')],[InlineKeyboardButton("🔄 Refresh",callback_data='refresh_status')]]
    else: message_text=f"Status: '{current_bot_status}'."; keyboard = [[InlineKeyboardButton("▶️ Start (Force)",callback_data='start_trading_bot_force')],[InlineKeyboardButton("🔄 Refresh",callback_data='refresh_status')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        try: await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
        except Exception as e: print(f"Edit error: {e}"); await update.effective_chat.send_message(text=message_text,reply_markup=reply_markup)
    else: await update.message.reply_text(text=message_text,reply_markup=reply_markup)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_bot_status = await get_bot_actual_status()
    start_stop_button_text,start_stop_callback_data,additional_buttons = "▶️ Start Bot","start_trading_bot",[]
    if current_bot_status=="RUNNING": start_stop_button_text,start_stop_callback_data="⏹️ Stop Bot","stop_trading_bot"
    elif current_bot_status=="STARTING": start_stop_button_text,start_stop_callback_data=f"⏳ Starting...","refresh_status"; additional_buttons.append(InlineKeyboardButton("⏹️ Stop (stuck?)",callback_data='stop_trading_bot'))
    elif current_bot_status=="STOPPING": start_stop_button_text,start_stop_callback_data=f"⏳ Stopping...","refresh_status"; additional_buttons.append(InlineKeyboardButton("▶️ Start (stuck?)",callback_data='start_trading_bot'))
    elif current_bot_status in ["STOPPED","STALE_RUNNING","ERROR_READING_STATUS","UNKNOWN"]:
        if current_bot_status!="STOPPED": additional_buttons.append(InlineKeyboardButton("▶️ Force Start",callback_data='start_trading_bot_force'))
    else: start_stop_button_text,start_stop_callback_data=f"Status: {current_bot_status}","refresh_status";additional_buttons.append(InlineKeyboardButton("▶️ Force Start",callback_data='start_trading_bot_force'))
    keyboard = [[InlineKeyboardButton("💰 SOL Amount",callback_data='get_sol_amount')],[InlineKeyboardButton("📊 Subscribed Tokens",callback_data='get_token_count')],[InlineKeyboardButton(start_stop_button_text,callback_data=start_stop_callback_data)],[InlineKeyboardButton("⚙️ Manage Dynamic Config",callback_data='manage_dynamic_config')]]
    if additional_buttons: keyboard.append(additional_buttons)
    if current_bot_status not in ["RUNNING","STARTING","STOPPING"] and start_stop_callback_data!="refresh_status" and not any(b.callback_data=='refresh_status' for b in additional_buttons): keyboard.append([InlineKeyboardButton("🔄 Refresh Status",callback_data='refresh_status')])
    reply_markup = InlineKeyboardMarkup(keyboard); message_text = 'Please choose an option:'
    
    target_message = update.message if update.message else update.callback_query.message
    
    if update.callback_query and (target_message.text != message_text or target_message.reply_markup != reply_markup): 
        await update.callback_query.edit_message_text(message_text,reply_markup=reply_markup)
    elif not update.callback_query : 
        await target_message.reply_text(message_text,reply_markup=reply_markup)


# --- Dynamic Config Management Functions ---
async def manage_dynamic_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query: await query.answer()
    keyboard = [
        [InlineKeyboardButton("👁️ View Current Config", callback_data='view_dynamic_config')],
        [InlineKeyboardButton("✏️ Edit Config Parameter", callback_data='edit_dynamic_config_start')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = "Dynamic Configuration Management:" # No special chars here
    
    target_message = update.message if update.message else query.message
    if query: await query.edit_message_text(message_text, reply_markup=reply_markup)
    elif target_message: await target_message.reply_text(message_text, reply_markup=reply_markup)


async def view_dynamic_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    config_data = load_dynamic_config()
    text_md = ""
    text_plain = ""

    if not config_data:
        text_md = escape_markdown_v2_text("Could not load dynamic_config.json or it's empty.")
        text_plain = "Could not load dynamic_config.json or it's empty."
    else:
        raw_json_content = json.dumps(config_data, indent=2, sort_keys=True)
        text_md = escape_markdown_v2_text("Current dynamic_config.json:") + "\n\n"
        text_md += "```json\n"
        text_md += raw_json_content # Content inside ```json should not be escaped for MarkdownV2
        text_md += "\n```"
        text_plain = "Current dynamic_config.json:\n\n" + raw_json_content

    keyboard = [[InlineKeyboardButton("🔙 Back to Config Menu", callback_data='manage_dynamic_config')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(text=text_md, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Markdown formatting error for view_dynamic_config: {e}. Sending as plain text.")
        await query.edit_message_text(text=text_plain, reply_markup=reply_markup)

async def edit_dynamic_config_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    config_data = load_dynamic_config()

    if not config_data:
        await query.edit_message_text(escape_markdown_v2_text("Dynamic config is empty or could not be loaded. Cannot edit."),
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Config Menu", callback_data='manage_dynamic_config')]]),
                                      parse_mode="MarkdownV2")
        return ConversationHandler.END

    params_list_md = [escape_markdown_v2_text("Available parameters to edit:")]
    params_list_plain = ["Available parameters to edit:"]

    for key, value in sorted(config_data.items()):
        key_for_code_block = escape_markdown_v2_text_for_code_block(key)
        json_value_for_code_block = escape_markdown_v2_text_for_code_block(json.dumps(value, ensure_ascii=False))
        type_hint_escaped = escape_markdown_v2_text(get_type_hint(value))
        
        params_list_md.append(f"- `{key_for_code_block}` (current: `{json_value_for_code_block}`){type_hint_escaped}")
        params_list_plain.append(f"- {key} (current: {json.dumps(value, ensure_ascii=False)}){get_type_hint(value)}")

    params_text_md = "\n".join(params_list_md)
    params_text_md += escape_markdown_v2_text("\n\nWhich parameter do you want to edit? (Type the exact name)")
    params_text_plain = "\n".join(params_list_plain)
    params_text_plain += "\n\nWhich parameter do you want to edit? (Type the exact name)"
    
    try:
        await query.edit_message_text(text=params_text_md, parse_mode="MarkdownV2",
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data='cancel_edit_config')]]))
    except Exception as e:
        print(f"Error displaying params for edit (MarkdownV2): {e}. Using plain text.")
        await query.edit_message_text(text=params_text_plain,
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data='cancel_edit_config')]]))
    return CHOOSING_PARAM

async def choose_param_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    param_name_unescaped = update.message.text.strip()
    config_data = load_dynamic_config()

    if param_name_unescaped not in config_data:
        await update.message.reply_text(
            escape_markdown_v2_text(f"Parameter '{param_name_unescaped}' not found. Please try again or use /cancel_edit."), # Added use
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data='cancel_edit_config')]]),
            parse_mode="MarkdownV2"
            )
        return CHOOSING_PARAM

    context.user_data[EDIT_CONFIG_PARAM_KEY] = param_name_unescaped
    current_value = config_data[param_name_unescaped]
    
    param_name_display_escaped = escape_markdown_v2_text(param_name_unescaped)
    current_value_for_code_block = escape_markdown_v2_text_for_code_block(json.dumps(current_value, ensure_ascii=False))
    type_hint_display_escaped = escape_markdown_v2_text(get_type_hint(current_value))

    text_to_send = f"Editing '{param_name_display_escaped}'\. Current value: `{current_value_for_code_block}`{type_hint_display_escaped}\.\n" \
                   f"Enter the new value for '{param_name_display_escaped}':"
    await update.message.reply_text(text_to_send, parse_mode="MarkdownV2")
    return TYPING_VALUE

async def typing_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    param_name = context.user_data.get(EDIT_CONFIG_PARAM_KEY)
    new_value_str = update.message.text.strip()
    config_data = load_dynamic_config()

    if not param_name or param_name not in config_data:
        await update.message.reply_text(escape_markdown_v2_text("Error: Parameter context lost. Please start over."),
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config Menu", callback_data='manage_dynamic_config')]]),
                                        parse_mode="MarkdownV2")
        if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
        return ConversationHandler.END

    original_value = config_data[param_name]
    parsed_value = None; parse_error = None
    try:
        if isinstance(original_value, bool):
            if new_value_str.lower() in ['true', '1', 'yes', 'on']: parsed_value = True
            elif new_value_str.lower() in ['false', '0', 'no', 'off']: parsed_value = False
            else: raise ValueError("Boolean must be true/false/1/0/yes/no/on/off")
        elif isinstance(original_value, int): parsed_value = int(new_value_str)
        elif isinstance(original_value, float): parsed_value = float(new_value_str)
        elif isinstance(original_value, list): 
            if original_value and all(isinstance(item, str) for item in original_value): # Check if not empty list of strings
                parsed_value = [s.strip() for s in new_value_str.split(',')]
            elif not original_value and ',' in new_value_str: # Handle empty list becoming list of strings
                 parsed_value = [s.strip() for s in new_value_str.split(',')]
            elif not original_value and new_value_str: # Handle empty list becoming list with one string
                 parsed_value = [new_value_str]
            elif not original_value and not new_value_str: # Handle empty list remaining empty
                 parsed_value = []
            else: # For other list types or if original list was empty, more complex parsing needed. Fallback.
                try: # Attempt to parse as JSON list if complex
                    parsed_value = json.loads(new_value_str)
                    if not isinstance(parsed_value, list): raise ValueError("Input was not a valid JSON list.")
                except (json.JSONDecodeError, ValueError):
                    parsed_value = new_value_str # Fallback to string if not list of strings and not valid JSON list
        else: parsed_value = new_value_str
    except ValueError as e: parse_error = str(e)

    if parse_error:
        param_name_display_escaped = escape_markdown_v2_text(param_name)
        type_hint_display_escaped = escape_markdown_v2_text(get_type_hint(original_value))
        error_message_escaped = escape_markdown_v2_text(parse_error)
        text_to_send = f"Error converting value '{escape_markdown_v2_text(new_value_str)}' for '{param_name_display_escaped}'\. Expected type like{type_hint_display_escaped}\. Error: {error_message_escaped}\n" \
                       f"Please enter the value again or use /cancel_edit\." # Added use
        await update.message.reply_text(text_to_send, parse_mode="MarkdownV2")
        return TYPING_VALUE

    config_data[param_name] = parsed_value
    param_name_display_escaped = escape_markdown_v2_text(param_name)
    parsed_value_for_code_block = escape_markdown_v2_text_for_code_block(json.dumps(parsed_value, ensure_ascii=False))

    if save_dynamic_config(config_data):
        confirmation_text = f"✅ Successfully updated '{param_name_display_escaped}' to `{parsed_value_for_code_block}`\.\n" \
                            "The trading bot should pick up this change shortly\."
        await update.message.reply_text(confirmation_text, parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(escape_markdown_v2_text(f"❌ Failed to save changes to {DYNAMIC_CONFIG_FILE}."), parse_mode="MarkdownV2")

    if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
    keyboard = [[InlineKeyboardButton("👁️ View Config", callback_data='view_dynamic_config')],
                [InlineKeyboardButton("✏️ Edit Another Parameter", callback_data='edit_dynamic_config_start')],
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]]
    await update.message.reply_text("Dynamic Configuration Management:", reply_markup=InlineKeyboardMarkup(keyboard)) # No MarkdownV2 for simple menu title
    return ConversationHandler.END

async def cancel_edit_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_to_edit = None; text_content = "Edit cancelled." # Plain text
    if update.callback_query: await update.callback_query.answer(text_content); message_to_edit = update.callback_query.message
    elif update.message: message_to_edit = update.message # If called by /cancel_edit command
    if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
    
    keyboard = [[InlineKeyboardButton("👁️ View Current Config", callback_data='view_dynamic_config')],[InlineKeyboardButton("✏️ Edit Config Parameter", callback_data='edit_dynamic_config_start')],[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard); 
    menu_text = "Dynamic Configuration Management (Cancelled):" # Plain text

    if message_to_edit:
        try: 
            if message_to_edit.text != menu_text or message_to_edit.reply_markup != reply_markup: # Avoid re-editing same content
                await message_to_edit.edit_text(menu_text, reply_markup=reply_markup)
        except Exception as e: 
            print(f"Error editing message on cancel: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=menu_text, reply_markup=reply_markup)
    else: 
         await context.bot.send_message(chat_id=update.effective_chat.id, text=text_content + " Back to config menu.", reply_markup=reply_markup)
    return ConversationHandler.END

async def fallback_edit_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(escape_markdown_v2_text("Sorry, I didn't understand that. If you're editing, please provide the value or use /cancel_edit to stop."), parse_mode="MarkdownV2")
    return


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data; text = "Processing..." 
    if command == 'get_sol_amount':
        try:
            if not os.path.exists(STATUS_FILE): text = "Status file not found."
            else:
                with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
                text = (f"💰 SOL: {bot_status.get('current_sol_balance', 'N/A')}\n"
                        f"💲 Price: ${bot_status.get('current_sol_price_usd', 'N/A')}\n"
                        f"💼 Value: ${bot_status.get('current_portfolio_value_usd', 'N/A')}\n"
                        f"🕒 Updated: {bot_status.get('timestamp', 'N/A')}")
        except Exception as e: text = f"Error: {e}"
        try: original_title=(query.message.text or "").splitlines(); original_title = original_title[0] if original_title else "Status"
        except: original_title = "Status"
        await query.edit_message_text(text=f"{original_title}\n\n{text}",reply_markup=query.message.reply_markup)
    elif command == 'get_token_count':
        try:
            if not os.path.exists(STATUS_FILE): text = "Status file not found."
            else:
                with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
                text = (f"📊 Subscribed Tokens: {bot_status.get('active_token_subscriptions_count', 'N/A')}\n"
                        f"🕒 Updated: {bot_status.get('timestamp', 'N/A')}")
        except Exception as e: text = f"Error: {e}"
        try: original_title=(query.message.text or "").splitlines(); original_title = original_title[0] if original_title else "Status"
        except: original_title = "Status"
        await query.edit_message_text(text=f"{original_title}\n\n{text}",reply_markup=query.message.reply_markup)
    elif command == 'start_trading_bot': await toggle_bot_command(update, context, force_start_flag=False)
    elif command == 'stop_trading_bot': await toggle_bot_command(update, context)
    elif command == 'start_trading_bot_force': await toggle_bot_command(update, context, force_start_flag=True)
    elif command == 'refresh_status' or command == 'main_menu':
        if query.message: await menu_command(query.message, context) # query.message is a Message object
    elif command == 'manage_dynamic_config': await manage_dynamic_config_command(update, context)
    elif command == 'view_dynamic_config': await view_dynamic_config_command(update, context)
    else: await query.edit_message_text(text=f"Unknown command: {command}")


def main_telegram_bot() -> None:
    print("Starting Telegram bot interface...")
    if not TG_TOKEN or not TG_ID: print("Error: Telegram env vars not set."); return
    application = Application.builder().token(TG_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_dynamic_config_start_command, pattern='^edit_dynamic_config_start$')],
        states={
            CHOOSING_PARAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_param_handler)],
            TYPING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, typing_value_handler)],
        },
        fallbacks=[CommandHandler('cancel_edit', cancel_edit_config_command), CallbackQueryHandler(cancel_edit_config_command, pattern='^cancel_edit_config$'), MessageHandler(filters.COMMAND, fallback_edit_config)],
        per_message=False
    )
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    async def start_command_tg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Welcome! Use /menu to see options.")
        await menu_command(update, context) # Call menu_command with update, not update.message
    application.add_handler(CommandHandler("start", start_command_tg))
    print("Telegram bot polling...")
    application.run_polling()

if __name__ == '__main__':
    main_telegram_bot()