# telegram_interface.py
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from typing import Union
import asyncio
from dotenv import load_dotenv
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta 
import math
import sys
import re
import asyncpg

load_dotenv()

# --- Environment Variables ---
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_ID = os.getenv("TG_CHAT_ID")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?options=-c%20timezone%3Dutc"


# --- Constants ---
STATUS_FILE_CHECK_SECONDS = 10
ITEMS_PER_PAGE_CONFIG = 7
ITEMS_PER_PAGE_TRADES = 5
BULLX_URL_BASE = "https://neo.bullx.io/terminal?chainId=1399811149&address=" # Added BullX base URL

# --- Directory Setup ---
# ... (remains the same)
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = CURRENT_SCRIPT_DIR
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

os.makedirs(DATA_DIR_BOT, exist_ok=True)

# --- Conversation States ---
# ... (remains the same)
CHOOSING_PARAM, TYPING_VALUE = range(2)
EDIT_CONFIG_PARAM_KEY = "edit_config_param_name"
CONFIG_PAGE_KEY = "config_page_key"
ASK_MINT_FOR_SELL, ASK_MINT_FOR_UNSUB = range(2, 4)
COMMAND_TYPE_KEY = "command_type_key"
OPEN_TRADES_PAGE_KEY = "open_trades_page"

# --- Callback Data Constants ---
# ... (remains the same)
CB_MAIN_MENU = "main_menu"
CB_GET_SOL_AMOUNT = "get_sol_amount"
CB_GET_TOKEN_COUNT = "get_token_count"
CB_VIEW_OPEN_TRADES = "view_open_trades"
CB_MANAGE_DYNAMIC_CONFIG = "manage_dynamic_config"
CB_BOT_CONTROL_MENU = "bot_control_menu"
CB_REFRESH_STATUS = "refresh_status"
CB_START_BOT = "start_trading_bot"
CB_START_BOT_FORCE = "start_trading_bot_force"
CB_STOP_BOT = "stop_trading_bot"
CB_STOP_BUYING = "stop_buying_command"
CB_START_BUYING = "start_buying_command"
CB_UNSUB_NEWTOKEN = "unsub_newtoken_command"
CB_SELL_TOKEN_PROMPT = "sell_token_prompt"
CB_UNSUB_TOKEN_PROMPT = "unsub_token_prompt"
CB_VIEW_DYNAMIC_CONFIG = "view_dynamic_config"
CB_EDIT_DYNAMIC_CONFIG_START = "edit_dynamic_config_start"
CB_CANCEL_EDIT_CONFIG = "cancel_edit_config"
CB_CONFIG_PAGE_PREFIX = "config_page_"
CB_OPEN_TRADES_PAGE_PREFIX = "open_trades_page_"
CB_SELL_NOW_PREFIX = "sell_now_" 

def get_sol_price_from_status_file() -> float | None:
    # ... (remains the same)
    try:
        if not os.path.exists(STATUS_FILE):
            print("Status file not found for SOL price.")
            return None
        with open(STATUS_FILE, 'r') as f:
            status_data = json.load(f)
        sol_price = status_data.get("current_sol_price_usd")
        if sol_price is not None:
            return float(sol_price)
        return None
    except (IOError, json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"Error reading SOL price from status.json: {e}")
        return None

async def send_telegram_message(message: str):
    # ... (remains the same)
    if not TG_TOKEN or not TG_ID:
        print("Error: Telegram token or chat ID is not configured for send_telegram_message.")
        return
    try:
        bot = Bot(token=TG_TOKEN)
        await bot.send_message(chat_id=str(TG_ID), text=message)
    except Exception as e:
        print(f"Error in send_telegram_message: {e}")

# --- Markdown Escaping Helpers ---
# ... (escape_markdown_v2_text and escape_markdown_v2_text_for_code_block remain the same) ...
def escape_markdown_v2_text(text: str) -> str:
    processed_text = text
    for char in r'\\_*[]()~`>#+-=|{}.!':
        if char in processed_text:
            processed_text = processed_text.replace(char, f'\\{char}')
    return processed_text

def escape_markdown_v2_text_for_code_block(text: str) -> str:
    processed_text = text.replace('\\', '\\\\\\\\') 
    processed_text = processed_text.replace('`', '\\`')
    return processed_text

def escape_url_for_markdownv2_link(url: str) -> str:
    """
    Escapes a URL specifically for the URL part of a MarkdownV2 link [text](url).
    According to Telegram Bot API documentation for MarkdownV2:
    "Inside () part of inline link definition, all ')' and '\' characters 
    must be escaped with a preceding '\' character."
    """
    # First, escape backslashes (as they are used for escaping other characters)
    temp_url = url.replace('\\', '\\\\')
    # Then, escape closing parentheses
    temp_url = temp_url.replace(')', '\\)')
    return temp_url

# --- IPC Helper ---
# ... (write_bot_command remains the same) ...
def write_bot_command(command: str):
    try:
        with open(COMMAND_FILE, 'w', encoding='utf-8') as f:
            f.write(command)
        print(f"Sent command to bot: {command}")
        return True
    except IOError as e:
        print(f"Error writing command file: {e}")
        return False

# --- Helper Functions for Dynamic Config ---
# ... (load_dynamic_config, save_dynamic_config, get_type_hint remain the same) ...
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
        if value and all(isinstance(item, str) for item in value):
            return " (list of strings, comma-separated)"
        return " (list, JSON format e.g. [\"a\", \"b\"] or [1, 2])"
    return " (string)"

# --- Telegram Bot Status & Control Functions ---
# ... (get_bot_actual_status, toggle_bot_process_command, send_simple_bot_command remain the same) ...
async def get_bot_actual_status() -> str:
    try:
        if not os.path.exists(STATUS_FILE): return "UNKNOWN (No Status File)"
        with open(STATUS_FILE, 'r') as f: status_data = json.load(f)
        bot_process_status = status_data.get("bot_process_status", "UNKNOWN").upper()
        status_timestamp_str = status_data.get("timestamp")

        if not status_timestamp_str:
            return "STALE (No Timestamp)"

        status_dt_naive = datetime.fromisoformat(status_timestamp_str)
        status_dt = status_dt_naive.replace(tzinfo=status_dt_naive.tzinfo or timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - status_dt).total_seconds()
        stale_threshold = STATUS_FILE_CHECK_SECONDS * 2.5

        if bot_process_status in ["RUNNING", "STARTING"] and age_seconds > stale_threshold:
            return f"STALE ({bot_process_status})"
        elif bot_process_status == "STOPPING" and age_seconds > stale_threshold * 2:
             return "STOPPED (Stale Stopping)"
        return bot_process_status
    except (IOError, json.JSONDecodeError, ValueError) as e:
        print(f"Error reading status.json: {e}")
        return "ERROR_READING_STATUS"
    except Exception as e:
        print(f"Unexpected error in get_bot_actual_status: {e}")
        return "ERROR_UNEXPECTED_STATUS_READ"

async def toggle_bot_process_command(update: Update, context: ContextTypes.DEFAULT_TYPE, force_start_flag: bool = False) -> None:
    query = update.callback_query
    if query: await query.answer()
    message_text = ""
    current_bot_status = await get_bot_actual_status() 

    if query and query.data == CB_STOP_BOT: 
        if write_bot_command("STOP"):
            message_text = "🛑 STOP command sent to the trading bot. It may take a moment to fully stop."
        else:
            message_text = "⚠️ Error sending STOP command to the trading bot."
    elif query and (query.data == CB_START_BOT or query.data == CB_START_BOT_FORCE):
        try:
            if os.path.exists(COMMAND_FILE):
                with open(COMMAND_FILE, 'w') as f: f.write("")
            main_script_path = os.path.join(PROJECT_ROOT_DIR, 'main.py')
            python_executable = sys.executable
            if not os.path.exists(main_script_path):
                raise FileNotFoundError(f"Main controller script not found: {main_script_path}")
            subprocess.Popen([python_executable, main_script_path], cwd=PROJECT_ROOT_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            message_text = "🚀 Main controller (and trading bot) initiated. Check status shortly."
        except Exception as e:
            message_text = f"❌ Error starting main controller: {e}"
    else: 
        message_text = f"Unhandled toggle action. Current status: {current_bot_status}"
    if query:
        await menu_command(update, context) 
        await context.bot.send_message(chat_id=update.effective_chat.id, text=escape_markdown_v2_text(message_text), parse_mode="MarkdownV2")
    elif update.message:
        await menu_command(update, context)
        await update.message.reply_text(text=escape_markdown_v2_text(message_text), parse_mode="MarkdownV2")

async def send_simple_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, friendly_name: str) -> None:
    query = update.callback_query
    if query: await query.answer()
    if write_bot_command(command):
        response_text = f"✅ Command '{friendly_name}' sent to the bot."
    else:
        response_text = f"⚠️ Error sending '{friendly_name}' command."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=escape_markdown_v2_text(response_text), parse_mode="MarkdownV2")
    await menu_command(update, context)

# --- Main Menu ---
# ... (menu_command remains the same) ...
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query: 
        await query.answer()
        target_message_for_edit = query.message
    else: 
        target_message_for_edit = update.message

    current_bot_status = await get_bot_actual_status()
    status_emoji = "🟢" if current_bot_status == "RUNNING" else \
                   "🟡" if current_bot_status == "STARTING" else \
                   "🟠" if "STALE" in current_bot_status else \
                   "🔴" if current_bot_status == "STOPPED" else \
                   "🟣" if current_bot_status == "STOPPING" else \
                   "⚠️" 

    menu_text = f"{status_emoji} Bot Status: *{escape_markdown_v2_text(current_bot_status)}*\nChoose an option:"
    keyboard = [
        [InlineKeyboardButton("💰 Bot Wallet Info", callback_data=CB_GET_SOL_AMOUNT)],
        [InlineKeyboardButton("📊 Subscribed Tokens Count", callback_data=CB_GET_TOKEN_COUNT)],
        [InlineKeyboardButton("📈 View Open Trades", callback_data=CB_VIEW_OPEN_TRADES)],
        [InlineKeyboardButton("⚙️ Dynamic Config", callback_data=CB_MANAGE_DYNAMIC_CONFIG)],
        [InlineKeyboardButton("🤖 Bot Control", callback_data=CB_BOT_CONTROL_MENU)],
        [InlineKeyboardButton("🔄 Refresh Status", callback_data=CB_REFRESH_STATUS)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        if query : 
             if target_message_for_edit.text != menu_text or target_message_for_edit.reply_markup != reply_markup :
                await target_message_for_edit.edit_text(menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
        else: 
            await target_message_for_edit.reply_text(menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Error updating menu: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

# --- Bot Control Submenu ---
# ... (bot_control_menu_command remains the same) ...
async def bot_control_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    current_bot_status = await get_bot_actual_status()
    start_stop_button_text = "▶️ Start Trading Bot"
    start_stop_callback = CB_START_BOT

    if current_bot_status == "RUNNING":
        start_stop_button_text = "⏹️ Stop Trading Bot"
        start_stop_callback = CB_STOP_BOT
    elif current_bot_status == "STARTING":
        start_stop_button_text = "⏳ Starting..."
        start_stop_callback = CB_REFRESH_STATUS 
    elif "STALE" in current_bot_status or current_bot_status == "ERROR_READING_STATUS":
         start_stop_button_text = "▶️ Force Start Controller"
         start_stop_callback = CB_START_BOT_FORCE
    keyboard = [
        [InlineKeyboardButton(start_stop_button_text, callback_data=start_stop_callback)],
        [
            InlineKeyboardButton("🚫 Stop Buys", callback_data=CB_STOP_BUYING),
            InlineKeyboardButton("✅ Start Buys", callback_data=CB_START_BUYING)
        ],
        [InlineKeyboardButton("🔕 Unsub New Tokens Stream", callback_data=CB_UNSUB_NEWTOKEN)],
        [
            InlineKeyboardButton("💸 Sell Token", callback_data=CB_SELL_TOKEN_PROMPT),
            InlineKeyboardButton("🔕 Unsub Token Trades", callback_data=CB_UNSUB_TOKEN_PROMPT)
        ],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = escape_markdown_v2_text("🤖 Bot Control Panel:")
    await query.message.edit_text(text=message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

# --- Dynamic Config Management ---
# ... (manage_dynamic_config_command, view_dynamic_config_command, edit_dynamic_config_start_command, choose_param_handler, typing_value_handler, cancel_edit_config_command, fallback_edit_config remain the same, using the last corrected versions)
async def manage_dynamic_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query: await query.answer()
    context.user_data[CONFIG_PAGE_KEY] = 0 
    keyboard = [
        [InlineKeyboardButton("👁️ View Current Config", callback_data=CB_VIEW_DYNAMIC_CONFIG)],
        [InlineKeyboardButton("✏️ Edit Config Parameter", callback_data=CB_EDIT_DYNAMIC_CONFIG_START)],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = escape_markdown_v2_text("⚙️ Dynamic Configuration Management:")
    target_message = query.message if query else update.message
    if query: await target_message.edit_text(message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    elif target_message: await target_message.reply_text(message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

async def view_dynamic_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    config_data = load_dynamic_config()
    if not config_data:
        text_md = escape_markdown_v2_text("Could not load dynamic_config.json or it's empty.")
    else:
        sorted_config_data = dict(sorted(config_data.items()))
        raw_json_content = json.dumps(sorted_config_data, indent=2)
        text_md = escape_markdown_v2_text("Current dynamic_config.json:") + "\n\n"
        text_md += "```json\n" + raw_json_content + "\n```"
    keyboard = [[InlineKeyboardButton("🔙 Back to Config Menu", callback_data=CB_MANAGE_DYNAMIC_CONFIG)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.message.edit_text(text=text_md, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Markdown formatting error for view_dynamic_config: {e}. Sending as plain text.")
        plain_text = "Current dynamic_config.json:\n\n" + json.dumps(config_data, indent=2) if config_data else "Config empty."
        await query.message.edit_text(text=plain_text, reply_markup=reply_markup)

async def edit_dynamic_config_start_command(
    update_or_cb_query: Union[Update, CallbackQuery], 
    context: ContextTypes.DEFAULT_TYPE, 
    page: int = 0
) -> int:
    actual_query_object: CallbackQuery | None = None
    if isinstance(update_or_cb_query, Update):
        actual_query_object = update_or_cb_query.callback_query
        if not actual_query_object:
            print("Error: edit_dynamic_config_start_command (as Update) did not find a callback_query.")
            if update_or_cb_query.effective_chat:
                await context.bot.send_message(
                    chat_id=update_or_cb_query.effective_chat.id,
                    text="Error processing request. Please try returning to the main menu."
                )
            return ConversationHandler.END
    elif isinstance(update_or_cb_query, CallbackQuery):
        actual_query_object = update_or_cb_query
    else:
        print(f"Error: edit_dynamic_config_start_command received unexpected type: {type(update_or_cb_query)}")
        return ConversationHandler.END
    await actual_query_object.answer()
    target_message_to_edit = actual_query_object.message
    context.user_data[CONFIG_PAGE_KEY] = page
    config_data = load_dynamic_config()
    sorted_config_items = sorted(config_data.items())
    if not sorted_config_items:
        await target_message_to_edit.edit_text(
            escape_markdown_v2_text("Dynamic config is empty or could not be loaded. Cannot edit."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Config Menu", callback_data=CB_MANAGE_DYNAMIC_CONFIG)]]),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    start_index = page * ITEMS_PER_PAGE_CONFIG
    end_index = start_index + ITEMS_PER_PAGE_CONFIG
    current_page_items = sorted_config_items[start_index:end_index]
    params_list_md_parts = [escape_markdown_v2_text(f"Available parameters (Page {page + 1}/{ (len(sorted_config_items) -1) // ITEMS_PER_PAGE_CONFIG + 1 }):")]
    for key, value in current_page_items:
        raw_key = key
        raw_value_json_str = json.dumps(value, ensure_ascii=False)
        raw_type_hint = get_type_hint(value)
        line_part_1_bullet = escape_markdown_v2_text("- ")
        line_part_2_key_code = f"`{escape_markdown_v2_text_for_code_block(raw_key)}`"
        line_part_3_current_literal = escape_markdown_v2_text(" (current: ")
        line_part_4_value_code = f"`{escape_markdown_v2_text_for_code_block(raw_value_json_str)}`"
        line_part_5_closing_paren_literal = escape_markdown_v2_text(")")
        line_part_6_type_hint_escaped = escape_markdown_v2_text(raw_type_hint)
        full_line = (line_part_1_bullet + line_part_2_key_code + line_part_3_current_literal + 
                     line_part_4_value_code + line_part_5_closing_paren_literal + line_part_6_type_hint_escaped)
        params_list_md_parts.append(full_line)
    params_text_md = "\n".join(params_list_md_parts)
    params_text_md += "\n\n" + escape_markdown_v2_text("Which parameter do you want to edit? (Type the exact name)")
    pagination_buttons = []
    if page > 0: pagination_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"{CB_CONFIG_PAGE_PREFIX}{page-1}"))
    if end_index < len(sorted_config_items): pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{CB_CONFIG_PAGE_PREFIX}{page+1}"))
    keyboard_layout = []
    if pagination_buttons: keyboard_layout.append(pagination_buttons)
    keyboard_layout.append([InlineKeyboardButton("🔙 Cancel Edit", callback_data=CB_CANCEL_EDIT_CONFIG)])
    reply_markup = InlineKeyboardMarkup(keyboard_layout)
    try:
        if target_message_to_edit.text != params_text_md or target_message_to_edit.reply_markup != reply_markup :
            await target_message_to_edit.edit_text(text=params_text_md, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Error displaying params for edit (MarkdownV2, Page {page}): {e}.")
        plain_text_parts = [f"Parameters (Page {page + 1}/{ (len(sorted_config_items) -1) // ITEMS_PER_PAGE_CONFIG + 1 }):"]
        for key, value in current_page_items: plain_text_parts.append(f"- {key} (current: {json.dumps(value, ensure_ascii=False)}) {get_type_hint(value)}")
        plain_text_parts.append("\nWhich parameter to edit? (Type exact name)")
        if target_message_to_edit.text != "\n".join(plain_text_parts) or target_message_to_edit.reply_markup != reply_markup:
            await target_message_to_edit.edit_text(text="\n".join(plain_text_parts), reply_markup=reply_markup)
    return CHOOSING_PARAM

async def choose_param_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    param_name_unescaped = update.message.text.strip()
    config_data = load_dynamic_config()
    if param_name_unescaped not in config_data:
        await update.message.reply_text(
            escape_markdown_v2_text(f"Parameter '{param_name_unescaped}' not found. Please try again or /cancel_edit_config."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel Edit", callback_data=CB_CANCEL_EDIT_CONFIG)]]),
            parse_mode="MarkdownV2"
        )
        return CHOOSING_PARAM 
    context.user_data[EDIT_CONFIG_PARAM_KEY] = param_name_unescaped
    current_value = config_data[param_name_unescaped]
    param_name_display_escaped = escape_markdown_v2_text(param_name_unescaped)
    current_value_for_code_block = escape_markdown_v2_text_for_code_block(json.dumps(current_value, ensure_ascii=False))
    type_hint_display_escaped = escape_markdown_v2_text(get_type_hint(current_value))
    text_to_send = f"Editing `{param_name_display_escaped}`\\. Current value: `{current_value_for_code_block}`{type_hint_display_escaped}\\.\n" \
                   f"Enter the new value for `{param_name_display_escaped}`:"
    await update.message.reply_text(text_to_send, parse_mode="MarkdownV2")
    return TYPING_VALUE

async def typing_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    param_name = context.user_data.get(EDIT_CONFIG_PARAM_KEY)
    new_value_str = update.message.text.strip()
    config_data = load_dynamic_config()
    if not param_name or param_name not in config_data:
        await update.message.reply_text(
            escape_markdown_v2_text("Error: Parameter context lost. Please start over."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config Menu", callback_data=CB_MANAGE_DYNAMIC_CONFIG)]]),
            parse_mode="MarkdownV2"
        )
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
            try: 
                parsed_value = json.loads(new_value_str)
                if not isinstance(parsed_value, list): raise ValueError("Input was not a valid JSON list.")
            except json.JSONDecodeError: 
                if original_value and all(isinstance(item, str) for item in original_value):
                    parsed_value = [s.strip() for s in new_value_str.split(',')]
                elif not original_value: 
                     parsed_value = [s.strip() for s in new_value_str.split(',')] if new_value_str else []
                else: raise ValueError("List format is complex. Provide valid JSON list (e.g., [\"item1\"] or [1, 2]).")
        else: parsed_value = new_value_str
    except ValueError as e: parse_error = str(e)
    if parse_error:
        param_name_display_escaped = escape_markdown_v2_text(param_name)
        type_hint_display_escaped = escape_markdown_v2_text(get_type_hint(original_value))
        error_message_escaped = escape_markdown_v2_text(parse_error)
        text_to_send = f"Error converting value '{escape_markdown_v2_text(new_value_str)}' for `{param_name_display_escaped}`\\. Expected type like{type_hint_display_escaped}\\. Error: {error_message_escaped}\n" \
                       f"Please enter the value again or /cancel_edit_config\\."
        await update.message.reply_text(text_to_send, parse_mode="MarkdownV2")
        return TYPING_VALUE
    config_data[param_name] = parsed_value
    param_name_display_escaped = escape_markdown_v2_text(param_name)
    parsed_value_for_code_block = escape_markdown_v2_text_for_code_block(json.dumps(parsed_value, ensure_ascii=False))
    if save_dynamic_config(config_data):
        confirmation_text = f"✅ Successfully updated `{param_name_display_escaped}` to `{parsed_value_for_code_block}`\\.\n" \
                            "The trading bot should pick up this change shortly\\."
        await update.message.reply_text(confirmation_text, parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(escape_markdown_v2_text(f"❌ Failed to save changes to {DYNAMIC_CONFIG_FILE}."), parse_mode="MarkdownV2")
    if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
    await manage_dynamic_config_command(update, context)
    return ConversationHandler.END

async def cancel_edit_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query: await query.answer("Edit cancelled.")
    if EDIT_CONFIG_PARAM_KEY in context.user_data: del context.user_data[EDIT_CONFIG_PARAM_KEY]
    if query: await manage_dynamic_config_command(update, context) 
    elif update.message: 
        await update.message.reply_text("Edit cancelled.")
        await manage_dynamic_config_command(update, context) 
    return ConversationHandler.END

async def fallback_edit_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        escape_markdown_v2_text("Sorry, I didn't understand that. If you're editing, please provide the value or use /cancel_edit_config to stop."),
        parse_mode="MarkdownV2"
    )
    return 

# --- Bot Command Handling (with arguments) ---
# ... (prompt_mint_address, process_mint_address_command, cancel_mint_command remain the same) ...
async def prompt_mint_address(update: Update, context: ContextTypes.DEFAULT_TYPE, command_type: str) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[COMMAND_TYPE_KEY] = command_type
    action_text = "sell" if command_type == "SELL" else "unsubscribe from"
    await query.message.edit_text(
        text=escape_markdown_v2_text(f"Please enter the MINT address of the token you want to {action_text}:"),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data=CB_BOT_CONTROL_MENU)]])
    )
    return ASK_MINT_FOR_SELL if command_type == "SELL" else ASK_MINT_FOR_UNSUB

async def process_mint_address_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mint_address = update.message.text.strip()
    command_type = context.user_data.get(COMMAND_TYPE_KEY)
    if not mint_address: 
        await update.message.reply_text("No mint address provided. Please try again or cancel.")
        return ASK_MINT_FOR_SELL if command_type == "SELL" else ASK_MINT_FOR_UNSUB
    final_command = ""; friendly_action = ""
    if command_type == "SELL":
        final_command = f"SELL_{mint_address}"
        friendly_action = f"Sell {mint_address}"
    elif command_type == "UNSUB_TRADES":
        final_command = f"UNSUB_TOKEN_TRADES_{mint_address}"
        friendly_action = f"Unsubscribe from {mint_address} trades"
    if final_command:
        if write_bot_command(final_command):
            await update.message.reply_text(escape_markdown_v2_text(f"✅ Command '{friendly_action}' sent to the bot."), parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(escape_markdown_v2_text(f"⚠️ Error sending '{friendly_action}' command."), parse_mode="MarkdownV2")
    else: await update.message.reply_text("Internal error: Unknown command type.")
    del context.user_data[COMMAND_TYPE_KEY]
    await bot_control_menu_command(update, context) 
    return ConversationHandler.END

async def cancel_mint_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Operation cancelled.")
    if COMMAND_TYPE_KEY in context.user_data: del context.user_data[COMMAND_TYPE_KEY]
    await bot_control_menu_command(update, context)
    return ConversationHandler.END

# --- View Open Trades ---
async def get_token_name(conn: asyncpg.Connection, mint: str) -> str:
    """Fetches the token name from v_tokens, falling back to mint address."""
    try:
        row = await conn.fetchrow("SELECT name FROM v_tokens WHERE mint = $1 LIMIT 1", mint)
        if row and row['name'] and row['name'].strip():
            return row['name'].strip()
        return mint # Fallback to mint address
    except Exception as e:
        print(f"Error fetching token name for {mint}: {e}")
        return mint # Fallback

async def get_current_market_data(conn: asyncpg.Connection, mint: str) -> dict | None:
    query = """
        SELECT price, marketcapsol AS market_cap_sol 
        FROM v_trades 
        WHERE mint = $1
        ORDER BY timestamp DESC
        LIMIT 1;
    """
    try:
        row = await conn.fetchrow(query, mint)
        if row:
            return {
                "current_price_sol": float(row["price"]) if row["price"] is not None else 0.0,
                "current_market_cap_sol": float(row["market_cap_sol"]) if row["market_cap_sol"] is not None else 0.0,
            }
        return None
    except Exception as e:
        print(f"Error fetching current market data for {mint}: {e}")
        return None
    
def format_open_trade_display(trade_data: dict, sol_usd_price: float | None) -> str:
    """Formats a single open trade for display with BullX link and token name."""
    mint = trade_data['mint']
    # Token name is expected to be passed in trade_data from view_open_trades_command
    token_name = trade_data.get('token_name', mint) 
    buy_price_sol = float(trade_data['buy_price'])
    initial_tokens = float(trade_data['initial_tokens'])
    remaining_tokens = float(trade_data['remaining_tokens'])
    total_investment_sol = float(trade_data['total_investment_sol'])
    buy_timestamp = trade_data['timestamp'] # Already a datetime object
    
    current_price_sol = float(trade_data.get('current_price_sol', 0.0))
    current_market_cap_sol = float(trade_data.get('current_market_cap_sol', 0.0))

    # Calculate Age
    age_delta = datetime.now(timezone.utc) - buy_timestamp
    days, remainder = divmod(age_delta.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    age_str_raw = ""
    if days > 0: age_str_raw += f"{int(days)}d "
    if hours > 0 or days > 0: age_str_raw += f"{int(hours)}h "
    age_str_raw += f"{int(minutes)}m"
    age_str_raw = age_str_raw.strip() if age_str_raw else "0m"

    # Calculate PnL
    unrealized_pnl_sol = 0.0
    current_value_sol = current_price_sol * remaining_tokens
    cost_basis_remaining_sol = 0.0
    if initial_tokens > 1e-9: # Avoid division by zero
        cost_basis_remaining_sol = (total_investment_sol / initial_tokens) * remaining_tokens
    
    if not math.isclose(remaining_tokens, 0.0, abs_tol=1e-9): # only if tokens remain
        unrealized_pnl_sol = current_value_sol - cost_basis_remaining_sol
    
    pnl_emoji = "📈" if unrealized_pnl_sol >= 0 else "📉"
    profit_percentage_raw = ((unrealized_pnl_sol / cost_basis_remaining_sol) * 100) if cost_basis_remaining_sol > 1e-9 else 0.0

    # --- Prepare components for Markdown ---
    mint_for_code = escape_markdown_v2_text_for_code_block(mint)
    buy_price_for_code = escape_markdown_v2_text_for_code_block(f"{buy_price_sol:.8f}")
    current_price_for_code = escape_markdown_v2_text_for_code_block(f"{current_price_sol:.8f}")
    remaining_tokens_for_code = escape_markdown_v2_text_for_code_block(f"{remaining_tokens:.3f}")
    initial_tokens_for_code = escape_markdown_v2_text_for_code_block(f"{initial_tokens:.3f}")
    pnl_sol_for_code = escape_markdown_v2_text_for_code_block(f"{unrealized_pnl_sol:+.4f}")
    profit_percentage_for_code = escape_markdown_v2_text_for_code_block(f"{profit_percentage_raw:+.2f}%")
    current_mc_sol_for_code = escape_markdown_v2_text_for_code_block(f"{current_market_cap_sol:,.0f}")
    age_md = escape_markdown_v2_text(age_str_raw)
    
    # Display Name Logic for Markdown
    display_name_md_parts = []
    # Ensure token_name is a string before calling lower() or comparing
    token_name_str = str(token_name) if token_name is not None else ""
    mint_str = str(mint) if mint is not None else ""

    if token_name_str and token_name_str.lower() != mint_str.lower():
        display_name_md_parts.append(escape_markdown_v2_text(token_name_str))
        display_name_md_parts.append(escape_markdown_v2_text(" ("))
        display_name_md_parts.append(f"`{mint_for_code}`") 
        display_name_md_parts.append(escape_markdown_v2_text(")"))
    else:
        display_name_md_parts.append(f"`{mint_for_code}`")
    display_name_final_md = "".join(display_name_md_parts)

    # BullX Link Construction
    bullx_url_raw = f"{BULLX_URL_BASE}{mint_str}" # Use mint_str here
    escaped_bullx_url_for_link_part = escape_url_for_markdownv2_link(bullx_url_raw)
    link_text_md = escape_markdown_v2_text("BullX") # Text part of the link
    link_final_md = f"[{link_text_md}]({escaped_bullx_url_for_link_part})"

    # USD Strings
    pnl_usd_str_md = ""
    current_mc_usd_str_md = ""
    if sol_usd_price and sol_usd_price > 0:
        unrealized_pnl_usd = unrealized_pnl_sol * sol_usd_price
        current_market_cap_usd = current_market_cap_sol * sol_usd_price
        pnl_usd_str_md = escape_markdown_v2_text(f" (${unrealized_pnl_usd:+.2f} USD)")
        current_mc_usd_str_md = escape_markdown_v2_text(f" (${current_market_cap_usd:,.0f} USD)")

    # Assemble the final message string
    line1 = escape_markdown_v2_text("🔵 ") + display_name_final_md + escape_markdown_v2_text(" ") + link_final_md + escape_markdown_v2_text("\n")
    line2 = escape_markdown_v2_text('  Age: ') + age_md + escape_markdown_v2_text("\n")
    line3 = escape_markdown_v2_text('  Bought at: ') + f"`{buy_price_for_code}`" + escape_markdown_v2_text(' SOL\n')
    line4 = escape_markdown_v2_text('  Current Price: ') + f"`{current_price_for_code}`" + escape_markdown_v2_text(' SOL\n')
    line5 = escape_markdown_v2_text('  Tokens (Rem/Initial): ') + f"`{remaining_tokens_for_code}`" + escape_markdown_v2_text('/') + f"`{initial_tokens_for_code}`" + escape_markdown_v2_text("\n")
    line6 = escape_markdown_v2_text(f'  Unrealized PnL {pnl_emoji}: ') + f"`{pnl_sol_for_code}`" + escape_markdown_v2_text(' SOL ') + f"`{profit_percentage_for_code}`" + pnl_usd_str_md + escape_markdown_v2_text("\n")
    line7 = escape_markdown_v2_text('  Current MC: ') + f"`{current_mc_sol_for_code}`" + escape_markdown_v2_text(' SOL') + current_mc_usd_str_md
    
    return line1 + line2 + line3 + line4 + line5 + line6 + line7

async def view_open_trades_command(actual_callback_query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    await actual_callback_query.answer()
    context.user_data[OPEN_TRADES_PAGE_KEY] = page
    sol_usd_price = get_sol_price_from_status_file()

    if not sol_usd_price:
        await actual_callback_query.message.edit_text(
            text=escape_markdown_v2_text("⚠️ Could not retrieve current SOL/USD price. Please try again later."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)]]),
            parse_mode="MarkdownV2"
        )
        return

    conn = None
    open_trades_for_keyboard = [] # Store mint and short name for buttons
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        offset = page * ITEMS_PER_PAGE_TRADES
        count_query = "SELECT COUNT(*) FROM portfolio WHERE status = 'active' AND tx_type = 'buy';"
        total_items_record = await conn.fetchrow(count_query)
        total_trades = total_items_record['count'] if total_items_record else 0
        
        portfolio_query = """
            SELECT id, mint, price AS buy_price, initial_tokens, remaining_tokens, 
                   total_investment_sol, timestamp
            FROM portfolio
            WHERE status = 'active' AND tx_type = 'buy'
            ORDER BY timestamp DESC
            LIMIT $1 OFFSET $2;
        """
        open_trades_base = await conn.fetch(portfolio_query, ITEMS_PER_PAGE_TRADES, offset)

        page_count = (total_trades -1) // ITEMS_PER_PAGE_TRADES + 1 if total_trades > 0 else 1
        message_text_parts = [escape_markdown_v2_text(f"📈 Open Trades (Page {page + 1}/{ page_count }):")]

        if not open_trades_base and page == 0:
            message_text_parts.append(escape_markdown_v2_text("\nNo open trades found."))
        elif not open_trades_base and page > 0:
             message_text_parts.append(escape_markdown_v2_text("\nNo more trades on this page."))
        else:
            for base_trade_row in open_trades_base:
                base_trade = dict(base_trade_row)
                token_name = await get_token_name(conn, base_trade['mint'])
                market_data = await get_current_market_data(conn, base_trade['mint'])
                
                full_trade_data = {**base_trade, "token_name": token_name}
                if market_data:
                    full_trade_data.update(market_data)
                
                # Store info needed for the sell button for this trade
                open_trades_for_keyboard.append({
                    "mint": base_trade['mint'],
                    "display_name": token_name if token_name and token_name.lower() != base_trade['mint'].lower() else base_trade['mint']
                })
                
                message_text_parts.append("\n" + format_open_trade_display(full_trade_data, sol_usd_price))
                message_text_parts.append(escape_markdown_v2_text("➖" * 20)) # Separator

        if message_text_parts and message_text_parts[-1] == escape_markdown_v2_text("➖" * 20):
            message_text_parts.pop() # Remove last separator

    except Exception as e:
        print(f"Error processing open trades view: {e}")
        message_text_parts = [escape_markdown_v2_text("An error occurred while fetching open trades.")]
        total_trades = 0 
        open_trades_for_keyboard = [] # Clear on error
    finally:
        if conn:
            await conn.close()
    
    message_text = "\n".join(message_text_parts)
    
    # --- Keyboard Construction ---
    keyboard_layout = []
    
    # Add Sell buttons for each trade shown on the page
    # We'll try to fit 2 sell buttons per row if names are short enough
    current_sell_button_row = []
    for trade_info in open_trades_for_keyboard:
        # Create a short display name for the button
        btn_text_raw = trade_info['display_name']
        if len(btn_text_raw) > 12: # If name is long, use first few chars of mint
            btn_text_raw = trade_info['mint'][:6] + "..."
        elif btn_text_raw == trade_info['mint']: # If name is mint, shorten mint
             btn_text_raw = trade_info['mint'][:6] + "..."

        sell_button = InlineKeyboardButton(f"🚨 Sell {btn_text_raw}", callback_data=f"{CB_SELL_NOW_PREFIX}{trade_info['mint']}")
        
        if len(current_sell_button_row) < 2: # Max 2 sell buttons per row for better layout
            current_sell_button_row.append(sell_button)
        else:
            keyboard_layout.append(current_sell_button_row)
            current_sell_button_row = [sell_button]
            
    if current_sell_button_row: # Add any remaining buttons in the last row
        keyboard_layout.append(current_sell_button_row)

    # Pagination buttons
    pagination_buttons_row = []
    if page > 0:
        pagination_buttons_row.append(InlineKeyboardButton("⬅️ Prev Page", callback_data=f"{CB_OPEN_TRADES_PAGE_PREFIX}{page-1}"))
    if (page + 1) * ITEMS_PER_PAGE_TRADES < total_trades:
        pagination_buttons_row.append(InlineKeyboardButton("Next Page ➡️", callback_data=f"{CB_OPEN_TRADES_PAGE_PREFIX}{page+1}"))
    
    if pagination_buttons_row:
        keyboard_layout.append(pagination_buttons_row)

    keyboard_layout.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data=CB_MAIN_MENU)])
    reply_markup = InlineKeyboardMarkup(keyboard_layout)
    
    target_message = actual_callback_query.message
    try:
        # Only edit if content or markup has changed to prevent "Message not modified" error
        if target_message.text != message_text or target_message.reply_markup != reply_markup:
            await target_message.edit_text(text=message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except Exception as e_edit:
        print(f"Error editing open trades message: {e_edit}")
        # Fallback to sending a new message if editing fails
        await context.bot.send_message(chat_id=actual_callback_query.message.chat_id, text=message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

# --- General Button Callback Handler ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query: CallbackQuery = update.callback_query
    # It's better to answer selectively in handlers that might take time or edit messages
    # await query.answer() 
    command = query.data

    if command == CB_GET_SOL_AMOUNT:
        await query.answer()
        try:
            if not os.path.exists(STATUS_FILE): text = "Status file not found."
            else:
                with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
                text = (f"💰 SOL: {bot_status.get('current_sol_balance', 'N/A')}\n"
                        f"💲 Price: ${bot_status.get('current_sol_price_usd', 'N/A')}\n"
                        f"💼 Value: ${bot_status.get('current_portfolio_value_usd', 'N/A')}\n"
                        f"🕒 Updated: {bot_status.get('timestamp', 'N/A')}")
        except Exception as e: text = f"Error: {e}"
        try: 
            original_title = (query.message.text or "").splitlines()
            original_title = original_title[0] if original_title else "Bot Wallet Info"
            await query.edit_message_text(text=f"{escape_markdown_v2_text(original_title)}\n\n{escape_markdown_v2_text(text)}", reply_markup=query.message.reply_markup, parse_mode="MarkdownV2")
        except Exception as e_edit:
            print(f"Error editing for SOL amount: {e_edit}")
            await query.message.reply_text(escape_markdown_v2_text(text), parse_mode="MarkdownV2") 

    elif command == CB_GET_TOKEN_COUNT:
        await query.answer()
        try:
            if not os.path.exists(STATUS_FILE): text = "Status file not found."
            else:
                with open(STATUS_FILE, 'r') as f: bot_status = json.load(f)
                text = (f"📊 Subscribed Tokens: {bot_status.get('active_token_subscriptions_count', 'N/A')}\n"
                        f"🕒 Updated: {bot_status.get('timestamp', 'N/A')}")
        except Exception as e: text = f"Error: {e}"
        try:
            original_title = (query.message.text or "").splitlines()
            original_title = original_title[0] if original_title else "Token Count"
            await query.edit_message_text(text=f"{escape_markdown_v2_text(original_title)}\n\n{escape_markdown_v2_text(text)}", reply_markup=query.message.reply_markup, parse_mode="MarkdownV2")
        except Exception as e_edit:
            print(f"Error editing for token count: {e_edit}")
            await query.message.reply_text(escape_markdown_v2_text(text), parse_mode="MarkdownV2")

    elif command == CB_VIEW_OPEN_TRADES:
        await view_open_trades_command(query, context, page=0) 
    elif command.startswith(CB_OPEN_TRADES_PAGE_PREFIX):
        page = int(command.split('_')[-1])
        await view_open_trades_command(query, context, page=page)
    elif command == CB_START_BOT or command == CB_STOP_BOT or command == CB_START_BOT_FORCE:
        await toggle_bot_process_command(update, context) 
    elif command == CB_REFRESH_STATUS or command == CB_MAIN_MENU:
        await menu_command(update, context) 
    elif command == CB_MANAGE_DYNAMIC_CONFIG:
        await manage_dynamic_config_command(update, context) 
    elif command == CB_VIEW_DYNAMIC_CONFIG:
        await view_dynamic_config_command(update, context) 
    elif command == CB_BOT_CONTROL_MENU:
        await bot_control_menu_command(update, context)
    elif command == CB_STOP_BUYING:
        await send_simple_bot_command(update, context, "STOP_BUYING", "Stop Buys")
    elif command == CB_START_BUYING:
        await send_simple_bot_command(update, context, "START_BUYING", "Start Buys")
    elif command == CB_UNSUB_NEWTOKEN:
        await send_simple_bot_command(update, context, "UNSUB_NEWTOKEN", "Unsubscribe New Tokens")
    elif command == CB_SELL_TOKEN_PROMPT:
        pass 
    elif command == CB_UNSUB_TOKEN_PROMPT:
        pass 
    elif command.startswith(CB_CONFIG_PAGE_PREFIX): 
        page = int(command.split('_')[-1])
        await edit_dynamic_config_start_command(query, context, page=page)
    elif command.startswith(CB_SELL_NOW_PREFIX):
        await query.answer() # Answer button press immediately
        mint_to_sell = command[len(CB_SELL_NOW_PREFIX):]
        sell_command_str = f"SELL_{mint_to_sell}"
        
        # Prepare components for the confirmation message
        mint_for_code_block = escape_markdown_v2_text_for_code_block(mint_to_sell)

        if write_bot_command(sell_command_str):
            # Construct confirmation_text by escaping literal parts
            part1 = escape_markdown_v2_text("✅ Sell command for token ")
            # The part in backticks is already correctly escaped for its context
            code_part = f"`{mint_for_code_block}`" 
            part2 = escape_markdown_v2_text(" sent to the bot.") # This will escape the trailing dot
            confirmation_text = part1 + code_part + part2
            
            await query.edit_message_reply_markup(reply_markup=None) # Remove buttons from trade list after action
                                                                    # Or refresh the list if preferred
            
        else:
            # Construct error message similarly
            part1 = escape_markdown_v2_text("⚠️ Error sending sell command for token ")
            code_part = f"`{mint_for_code_block}`"
            part2 = escape_markdown_v2_text(".") # Escape the trailing dot
            confirmation_text = part1 + code_part + part2
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=confirmation_text,
            parse_mode="MarkdownV2"
        )
        # Optional: Refresh the open trades view or main menu
        # current_page = context.user_data.get(OPEN_TRADES_PAGE_KEY, 0)
        # await view_open_trades_command(query, context, page=current_page) 
        # For now, sending a message and letting user manually navigate back or refresh.

    else:
        await query.answer("Unknown command.")
        await query.edit_message_text(text=f"Unknown command: {escape_markdown_v2_text(command)}", parse_mode="MarkdownV2")

# --- Main Function ---
# ... (main_telegram_bot and if __name__ == '__main__': remain the same) ...
def main_telegram_bot() -> None:
    print("Starting Telegram bot interface...")
    if not TG_TOKEN or not TG_ID:
        print("Error: Telegram environment variables (TG_BOT_TOKEN, TG_CHAT_ID) not set.")
        return
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_DATABASE]):
        print("Error: Database environment variables not fully set for Telegram interface.")

    application = Application.builder().token(TG_TOKEN).build()
    edit_config_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_dynamic_config_start_command, pattern=f"^{CB_EDIT_DYNAMIC_CONFIG_START}$")],
        states={
            CHOOSING_PARAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_param_handler)],
            TYPING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, typing_value_handler)],
        },
        fallbacks=[
            CommandHandler('cancel_edit_config', cancel_edit_config_command), 
            CallbackQueryHandler(cancel_edit_config_command, pattern=f"^{CB_CANCEL_EDIT_CONFIG}$"),
            MessageHandler(filters.COMMAND, fallback_edit_config) 
        ],
        per_message=False
    )
    mint_command_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lambda u, c: prompt_mint_address(u, c, "SELL"), pattern=f"^{CB_SELL_TOKEN_PROMPT}$"),
            CallbackQueryHandler(lambda u, c: prompt_mint_address(u, c, "UNSUB_TRADES"), pattern=f"^{CB_UNSUB_TOKEN_PROMPT}$"),
        ],
        states={
            ASK_MINT_FOR_SELL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_mint_address_command)],
            ASK_MINT_FOR_UNSUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_mint_address_command)],
        },
        fallbacks=[
            CommandHandler('cancel_mint_command', cancel_mint_command),
            CallbackQueryHandler(cancel_mint_command, pattern=f"^{CB_BOT_CONTROL_MENU}$"), 
            MessageHandler(filters.COMMAND, fallback_edit_config) 
        ],
         per_message=False
    )
    application.add_handler(CommandHandler("start", menu_command)) 
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(edit_config_conv_handler)
    application.add_handler(mint_command_conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback_handler)) 
    print("Telegram bot polling...")
    try:
        application.run_polling()
    except Exception as e:
        print(f"Telegram bot failed to start or polling error: {e}")

if __name__ == '__main__':
    main_telegram_bot()