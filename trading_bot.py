# path: trading_bot.py

import argparse
import asyncio
import signal
import traceback
import inspect
import threading
import os
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import httpx
from typing import Dict, Any, List, Optional
import random
import hashlib 

# --- Project Imports ---
import config.config as config_module
from database_handler import DatabaseClient
from trading_logic import TradingManager
from connectors.websocket_handler import WebSocketHandler 
from bot_logger import setup_logging, log_info, log_debug, log_error, log_warning, log_critical, rotate_log_file
from state_manager import GlobalState
from trade_processor import trade_worker
from connectors.sol_price_api import update_sol_price
from connectors.rugcheck_handler import Rugcheck
from socials_processor import SocialsProcessor
from utils import calculate_volatility 
from connectors.dexscreener_api import DexscreenerFetcher
from ai_decision_module.ai_decision_maker import AIDecisionMaker
from ai_decision_module.ai_data_assembler import fetch_comprehensive_token_data
from telegram_interface import send_telegram_message

from typing import Optional

# --- Constants for File-Based IPC ---
PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

class TradingBot:
    """
    Main class for running the trading bot.
    
    This class orchestrates all components, including:
    - Database connection
    - Configuration loading (base, dynamic, and params files)
    - WebSocket connection management
    - Core service tasks (trade processing, price updates, rug checks, etc.)
    - Dynamic AI module lifecycle management
    - Status reporting and command listening
    - Graceful shutdown
    """

    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, no_log_rotate: bool = False):
        """
        Initializes the TradingBot instance.
        
        Args:
            cleanup (bool): If True, cleans up the database on start.
            backup (bool): If True, backs up the database on start.
            params_file (str): Path to an optional JSON file for GA/RL parameters.
            no_log_rotate (bool): If True, disables log rotation (used when run by main.py).
        """
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.state = GlobalState.get_instance()
        self.cleanup = cleanup
        self.backup = backup
        self.no_log_rotate = no_log_rotate
        self.params_file = params_file
        self.db_client: Optional[DatabaseClient] = None
        self.ws_handler: Optional[WebSocketHandler] = None
        self.tasks: List[asyncio.Task] = []
        self.config: Dict[str, Any] = {}
        self.base_config: Dict[str, Any] = {}
        self._load_base_config()
        self.trading_manager: Optional[TradingManager] = None
        self._last_dynamic_config_mtime: float = 0.0
        self.bot_start_time = datetime.now(timezone.utc)
        self.dexscreener_fetcher: Optional[DexscreenerFetcher] = None
        self.socials_proc: Optional[SocialsProcessor] = None
        self.rugchecker: Optional[Rugcheck] = None

        # --- AI Component Placeholders (Dynamically Managed) ---
        # --- FIX: Renamed attributes to avoid conflict with method names ---
        self.ai_decision_maker: Optional[AIDecisionMaker] = None
        self.ai_semaphore: Optional[asyncio.Semaphore] = None
        self.ai_worker_task_handle: Optional[asyncio.Task] = None
        self.ai_populator_task_handle: Optional[asyncio.Task] = None
        self.ai_outcome_monitor_task_handle: Optional[asyncio.Task] = None
        self.ai_vector_maint_task_handle: Optional[asyncio.Task] = None
        # --- END FIX ---

        os.makedirs(DATA_DIR_BOT, exist_ok=True)
        self._write_status({"bot_process_status": "INITIALIZING", "timestamp": datetime.now(timezone.utc).isoformat()})

    async def _fetch_initial_sol_price(self) -> bool:
        """
        Fetches the SOL price once on startup to ensure the bot has a valid
        price before other services (like the price updater) start.
        """
        try:
            async with httpx.AsyncClient() as client:
                log_debug(f"Fetching initial SOL price from {config_module._SOL_PRICE_API_URL}")
                response = await client.get(config_module._SOL_PRICE_API_URL, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    new_price = data.get("solana", {}).get("usd")
                    if new_price is None or not isinstance(new_price, (int, float)):
                        log_error("Invalid or missing SOL price in initial API response.")
                        return False
                    # Set in-memory state and write to DB
                    await self.state.set_sol_price(new_price)
                    await self.db_client.insert_sol_price(new_price) 
                    log_info(f"✅ Initial SOL price successfully fetched and set: {new_price} USD")
                    return True
                else:
                    log_error(f":police_car_light: Error fetching initial SOL price. Status: {response.status_code}, Response: {response.text}")
                    return False
        except (httpx.TimeoutException, httpx.RequestError, Exception) as e:
            log_error(f"❌ Exception fetching initial SOL price: {e}", exc_info=True)
            return False

    def _filter_serializable_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Filters a config dict to only include JSON-serializable types."""
        serializable_config = {}
        for key, value in config_dict.items():
            if isinstance(value, set):
                serializable_config[key] = list(value)
            elif isinstance(value, timedelta):
                serializable_config[key] = str(value)
            elif isinstance(value, (int, float, str, bool, list, dict)) or value is None:
                serializable_config[key] = value
            else:
                # Fallback: convert unknown types to string
                serializable_config[key] = str(value)
        return serializable_config

    def _load_base_config(self):
        """
        Loads the base configuration from config/config.py and writes
        the first dynamic_config.json if it doesn't exist.
        """
        try:
            loaded_config = {}
            # Iterate over attributes in config_module
            for key in dir(config_module):
                # Load only uppercase variables that are not modules/classes/functions/private
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config_module, key)
                    if not inspect.ismodule(value) and not inspect.isclass(value) and not inspect.isfunction(value):
                        loaded_config[key] = value
            
            self.base_config = loaded_config.copy() # The immutable base
            self.config = loaded_config.copy()      # The mutable, active config
            log_info(":gear: Base configuration loaded successfully.")
            
            # Write the initial dynamic config file if it's missing
            if not os.path.exists(DYNAMIC_CONFIG_FILE):
                with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    # Filter for serializable types before dumping
                    json.dump(self._filter_serializable_config(self.config), f, indent=4)
                log_info(f"Initial '{DYNAMIC_CONFIG_FILE}' created from base config.")
                
        except Exception as e:
            log_critical(f":x: [bold red]CRITICAL: Failed to load base configuration[/bold red]: {e}", exc_info=True)
            raise ValueError("Failed to load critical base configuration.") from e
        
    def register_signal_handlers(self):
        """Registers OS signal handlers for graceful shutdown."""
        def signal_handler():
            log_info(":heavy_exclamation_mark: [bold red]Signal received[/bold red], initiating shutdown...")
            self.state.trigger_shutdown()
        
        if hasattr(signal, 'SIGINT'): # Handle Ctrl+C
            signal.signal(signal.SIGINT, lambda *_: signal_handler())
        if hasattr(signal, 'SIGTERM'): # Handle kill/system shutdown
            signal.signal(signal.SIGTERM, lambda *_: signal_handler())

    async def start_ai_services(self):
        """Initializes and starts all AI-related components and tasks."""
        if self.ai_decision_maker is not None:
            log_warning("AI services are already running. Start request ignored.")
            return

        log_info("🧠 [bold green]Starting AI services...[/bold green]")
        try:
            self.ai_decision_maker = AIDecisionMaker(config=self.config, db_client=self.db_client)
            log_info("✅ AI Decision Maker initialized successfully.")
            
            self.ai_semaphore = asyncio.Semaphore(self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1))
            
            # --- FIX: Call the methods, store in the renamed attributes ---
            self.ai_worker_task_handle = asyncio.create_task(self.ai_evaluation_worker(), name="ai_evaluation_worker")
            self.ai_populator_task_handle = asyncio.create_task(self.populate_ai_queue_periodic(), name="ai_queue_populator")
            self.ai_outcome_monitor_task_handle = asyncio.create_task(self.ai_outcome_monitor_task(), name="ai_outcome_monitor")
            self.ai_vector_maint_task_handle = asyncio.create_task(self.run_vector_index_maintenance(), name="vector_index_maintenance")
            # --- END FIX ---

            # Add new tasks to the main task list for monitoring
            self.tasks.extend([
                self.ai_worker_task_handle,
                self.ai_populator_task_handle,
                self.ai_outcome_monitor_task_handle,
                self.ai_vector_maint_task_handle
            ])
            
            # Update the TradingManager with the new AI instance
            if self.trading_manager:
                self.trading_manager.ai_decision_maker = self.ai_decision_maker
                
            log_info("🧠 AI tasks (worker, populator, outcome_monitor, vector_maint) have been started.")

        except Exception as ai_init_err:
            log_critical(f"CRITICAL: Failed to initialize AI Decision Maker: {ai_init_err}", exc_info=True)
            self.config['AI_DECISION_MAKING_ENABLED'] = False # Force disable in config
            log_warning("🧠 AI Decision Making has been DISABLED due to initialization error.")
            # Ensure partial cleanup
            self.ai_decision_maker = None
            self.ai_semaphore = None
            if self.trading_manager:
                self.trading_manager.ai_decision_maker = self.ai_decision_maker


    async def stop_ai_services(self):
        """Cancels all AI-related tasks and cleans up components."""
        if self.ai_decision_maker is None:
            log_debug("AI services are already stopped. Stop request ignored.")
            return

        log_info("🧠 [bold red]Stopping AI services...[/bold red]")
        
        # Update the TradingManager first
        if self.trading_manager:
            self.trading_manager.ai_decision_maker = self.ai_decision_maker
            
        # --- FIX: Use renamed task attributes ---
        ai_tasks = [
            self.ai_worker_task_handle, 
            self.ai_populator_task_handle, 
            self.ai_outcome_monitor_task_handle,
            self.ai_vector_maint_task_handle
        ]
        # --- END FIX ---
        
        for task in ai_tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                log_debug(f"AI task {task.get_name()} cancelled.")
            
            # Remove from the main self.tasks list
            if task in self.tasks:
                self.tasks.remove(task)

        # Clear components
        # --- FIX: Use renamed task attributes ---
        self.ai_decision_maker = None
        self.ai_semaphore = None
        self.ai_worker_task_handle = None
        self.ai_populator_task_handle = None
        self.ai_outcome_monitor_task_handle = None
        self.ai_vector_maint_task_handle = None
        # --- END FIX ---
        
        log_info("🧠 AI services have been stopped.")

    async def config_updater(self):
        """
        Periodically checks the dynamic_config.json file for changes and
        hot-reloads the bot's self.config.
        
        This task is now also responsible for starting/stopping AI services
        based on the `AI_DECISION_MAKING_ENABLED` flag.
        """
        log_info(f"⚙️ Dynamic config updater started. Watching: {os.path.abspath(DYNAMIC_CONFIG_FILE)}")
        while not self.state.shutdown_event.is_set():
            try:
                if not os.path.exists(DYNAMIC_CONFIG_FILE): 
                    log_warning(f"'{DYNAMIC_CONFIG_FILE}' not found. Will retry.")
                    await self.state.wait_or_interrupt(timeout=10)
                    continue
                
                # Check file modification time
                current_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
                if current_mtime > self._last_dynamic_config_mtime:
                    log_info(f"Detected change in {DYNAMIC_CONFIG_FILE}. Attempting to load updates.")
                    
                    # --- DYNAMIC AI LIFECYCLE LOGIC ---
                    # 1. Check AI state *before* loading new config
                    was_ai_enabled = bool(self.ai_decision_maker is not None)
                    
                    # 2. Load new config from file
                    with open(DYNAMIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                        dynamic_conf = json.load(f)
                        
                    # 3. Apply updates to self.config
                    updated_count = 0
                    changed_params = {}
                    for key, value in dynamic_conf.items():
                        key_upper = key.upper()
                        # Only update if key exists in base config and value is different
                        if key_upper in self.base_config and value != self.config.get(key_upper):
                            self.config[key_upper] = value
                            changed_params[key_upper] = value
                            updated_count += 1
                            
                    if updated_count > 0:
                        log_info(f"Applied {updated_count} configuration updates: {changed_params}")
                    
                    self._last_dynamic_config_mtime = current_mtime
                    
                    # 4. Check AI state *after* loading new config
                    is_ai_enabled_now = self.config.get('AI_DECISION_MAKING_ENABLED', False)

                    # 5. Start or stop AI services based on the state change
                    if is_ai_enabled_now and not was_ai_enabled:
                        log_info("Config change detected: ENABLING AI services...")
                        # Schedule the start, don't block the updater
                        asyncio.create_task(self.start_ai_services()) 
                    elif not is_ai_enabled_now and was_ai_enabled:
                        log_info("Config change detected: DISABLING AI services...")
                        # Schedule the stop, don't block the updater
                        asyncio.create_task(self.stop_ai_services())
                    # --- END DYNAMIC AI LIFECYCLE LOGIC ---
                        
                await self.state.wait_or_interrupt(timeout=10) # Poll every 10 seconds
                
            except asyncio.CancelledError: 
                break
            except json.JSONDecodeError as json_err:
                log_error(f":police_car_light: Error decoding {DYNAMIC_CONFIG_FILE}: {json_err}. Config not updated.")
                self._last_dynamic_config_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE) # Acknowledge mtime to avoid loop
            except Exception as e:
                log_error(f":police_car_light: Error in config_updater loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=30)
                
        log_info("⚙️ Dynamic config updater task shutting down.")

    def _write_status(self, status_data: dict):
        """Atomically writes the bot's current status to the JSON file."""
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=4)
        except IOError as e:
            log_error(f":police_car_light: Error writing status file {STATUS_FILE}: {e}")

    async def ai_evaluation_worker(self):
        """
        Continuously processes tokens from the AI evaluation queue.
        Fetches comprehensive data and calls AIDecisionMaker.get_trade_advice,
        which now handles its own database logging (RAG memory).
        """
        log_info("🧠 AI Evaluation Worker started.")
        if not self.db_client: # self.ai_decision_maker is checked in the loop
            log_critical("🧠 AI Worker cannot start: DatabaseClient not initialized.")
            return
            
        while not self.state.shutdown_event.is_set():
            mint = None
            try:
                # Check if AI is enabled at the start of the loop
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False):
                    await self.state.wait_or_interrupt(timeout=5)
                    continue
                    
                # 1. Get task from queue
                priority, (mint, decision_context) = await asyncio.wait_for(
                    self.state.get_ai_evaluation_queue().get(), timeout=1.0
                )
                
                log_debug(f"🧠 AI Worker: Picked up {mint} (Context: {decision_context}, Prio: {priority})")
                
                # 2. Acquire semaphore
                async with self.ai_semaphore:
                    # Re-check state after acquiring semaphore
                    if self.state.shutdown_event.is_set() or not self.ai_decision_maker: 
                        break
                        
                    evaluation_start_time = time.monotonic()
                    
                    # 3. Fetch data
                    comprehensive_data = await fetch_comprehensive_token_data(self.db_client, mint)
                    
                    # --- NEW LOGIC ---
                    # 4. Check if the token was backed up (race condition)
                    if comprehensive_data.get("status") == "INACTIVE_BACKED_UP":
                        log_info(f"🧠 AI Worker: Logging 'Dodged Bullet' for rugged/dead token {mint}.")
                        
                        # We don't need to call the LLM. Just format the outcome for RAG.
                        outcome_snapshot = {
                            "mint": mint, "source": "PUMP", # Source is unknown, but irrelevant
                            "timestamp": comprehensive_data['backup_timestamp'].isoformat(),
                            "decision_context": "NON_TRADE_OUTCOME",
                            "market_cap": 0, "volatility": 0, "token_age_minutes": 0,
                            "creator_history_summary": comprehensive_data.get('creator_history_summary', 'N/A'),
                            "uri_status": "N/A",
                            "market_dynamics_summary_str": f"Token rugged/dead. Reason: {comprehensive_data['backup_reason']}",
                            "trade_history_summary": "No trades by bot."
                        }
                        outcome_decision = {
                            "decision": "DODGED_BULLET (RUGGED)", "confidence": 100,
                            "explanation": f"Bot detected a rule-based buy opportunity, but the token was backed up (reason: {comprehensive_data['backup_reason']}) "
                                         f"before the AI could evaluate it. This log confirms the token was a bad buy."
                        }
                        
                        # Directly add this outcome to the RAG memory
                        await self.ai_decision_maker.add_decision_snapshot_to_memory(outcome_snapshot, outcome_decision)
                        
                        # We don't update the 'ai_last_evaluation_ts' on the (now deleted) token
                        # We just mark the queue task as done.
                    
                    else:
                        # --- ORIGINAL LOGIC (for active tokens) ---
                        
                        # 4b. Get AI Advice (this now *also* saves to ai_decision_memory)
                        advice = await self.ai_decision_maker.get_trade_advice(comprehensive_data) 
                        
                        eval_ts = datetime.now(timezone.utc)

                        # 5. Update the token's last evaluation timestamp
                        async with self.db_client.pool.acquire() as conn:
                            await self.db_client.update_token_ai_eval_timestamp(mint, eval_ts, conn=conn)

                        # Only act if it was an 'INITIAL BUY' check and the AI said to buy
                        if (comprehensive_data.get('decision_context') == 'INITIAL BUY' and 
                            advice['decision'] in ['BUY', 'REBUY']):
                            
                            buy_threshold = self.config.get('AI_CONFIDENCE_THRESHOLD_INITIAL_BUY', 90)
                            
                            if advice['confidence'] >= buy_threshold:
                                log_info(f"🧠 [bold green]AI-First Buy Triggered[/bold green] for {mint} (Confidence: {advice['confidence']} >= {buy_threshold}).")
                                
                                price_to_buy = comprehensive_data.get('price')
                                # execute_buy expects market_cap in SOL
                                mcap_to_buy = (comprehensive_data.get('market_cap', 0) / (await self.state.get_sol_price())) if await self.state.get_sol_price() else 0.0

                                if price_to_buy and mcap_to_buy and price_to_buy > 0 and mcap_to_buy > 0:
                                    if not self.state.is_buying_enabled:
                                        log_info(f"🧠 AI-First Buy for {mint} skipped: Buying is globally disabled.")
                                    else:
                                        # Call execute_buy from the trading_manager
                                        await self.trading_manager.execute_buy(
                                            mint=mint,
                                            trigger_price=price_to_buy,
                                            market_cap_sol_at_trigger=mcap_to_buy,
                                            buy_reason="AI-First (New Token)",
                                            ai_context=advice # Pass the full advice dict
                                        )
                                else:
                                    log_warning(f"🧠 AI-First Buy for {mint} skipped: Invalid price ({price_to_buy}) or mcap ({mcap_to_buy}).")
                            else:
                                log_debug(f"🧠 AI-First Buy: AI advised {advice['decision']} for {mint}, but confidence ({advice['confidence']}) was below threshold ({buy_threshold}).")

                        evaluation_duration = time.monotonic() - evaluation_start_time
                        
                        log_info(f"🧠 AI eval complete for {mint} ({decision_context}) -> {advice['decision']} ({advice['confidence']}%) in {evaluation_duration:.2f}s")
                    
                    # --- END OF LOGIC ---
                
                self.state.get_ai_evaluation_queue().task_done()
                mint = None # Clear mint on success
                
            except asyncio.TimeoutError: 
                continue # Queue was empty, loop again
            except asyncio.CancelledError: 
                log_info("🧠 AI Evaluation Worker task cancelled."); 
                break
            except ValueError as ve: 
                # This often happens if fetch_comprehensive_token_data fails (e.g., token deleted)
                log_error(f"🧠 AI Worker: Error fetching data for {mint} (likely deleted): {ve}")
                if mint:
                    try: self.state.get_ai_evaluation_queue().task_done()
                    except ValueError: pass
            except Exception as e:
                log_error(f"🚨 Unexpected error in AI Evaluation Worker: {e}", exc_info=True)
                if mint:
                    try: self.state.get_ai_evaluation_queue().task_done()
                    except ValueError: pass
                await self.state.wait_or_interrupt(timeout=10) # Pause on unexpected error
                
        log_info("🧠 AI Evaluation Worker shutting down.")

    async def populate_ai_queue_periodic(self):
        """Periodically scans the database for tokens that need AI evaluation and adds them to the queue."""
        log_info("📊 AI Queue Populator started.")
        while not self.state.shutdown_event.is_set():
            try:
                # Check if AI is enabled at the start of the loop
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False):
                    await self.state.wait_or_interrupt(timeout=60)
                    continue

                q = self.state.get_ai_evaluation_queue()
                if q.full():
                    log_warning("🧠 AI evaluation queue is full. Skipping population cycle.")
                    await self.state.wait_or_interrupt(timeout=30)
                    continue
                
                max_q_size = self.config.get('AI_QUEUE_MAX_SIZE', 1000)
                added_count = 0
                
                # --- Priority 1: Active Portfolio ---
                portfolio_mints = await self.db_client.get_active_portfolio_for_ai_eval(
                    self.config.get('AI_REFRESH_INTERVAL_PORTFOLIO_MIN', 5)
                )
                for mint in portfolio_mints:
                    if q.qsize() < max_q_size: 
                        await q.put((-100, (mint, 'SELL/HOLD')))
                        added_count += 1
                    else: break
                if portfolio_mints: log_debug(f"🧠 AI Queue: Added {len(portfolio_mints)} portfolio tokens.")
                
                # --- Priority 2: High Momentum (PUMP) ---
                if q.qsize() < max_q_size:
                    pump_mints = await self.db_client.get_top_pump_momentum_for_ai_eval(
                        self.config.get('AI_MOMENTUM_TOP_N', 5), 30, self.config.get('AI_REFRESH_INTERVAL_MOMENTUM_MIN', 15)
                    )
                    for mint in pump_mints:
                        if q.qsize() < max_q_size:
                            past_pos_count = await self.db_client.pool.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
                            context = "REBUY" if past_pos_count > 0 else "INITIAL BUY"
                            await q.put((-50, (mint, context)))
                            added_count += 1
                        else: break
                    if pump_mints: log_debug(f"🧠 AI Queue: Added {len(pump_mints)} PUMP momentum tokens.")

                # --- Priority 2: High Momentum (DEX) ---
                if q.qsize() < max_q_size:
                    dex_mints = await self.db_client.get_top_dex_momentum_for_ai_eval(
                        self.config.get('AI_MOMENTUM_TOP_N', 5), 30, self.config.get('AI_REFRESH_INTERVAL_MOMENTUM_MIN', 15)
                    )
                    for mint in dex_mints:
                         if q.qsize() < max_q_size:
                            past_pos_count = await self.db_client.pool.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
                            context = "REBUY" if past_pos_count > 0 else "INITIAL BUY"
                            await q.put((-45, (mint, context)))
                            added_count += 1
                         else: break
                    if dex_mints: log_debug(f"🧠 AI Queue: Added {len(dex_mints)} DEX momentum tokens.")
                
                # --- Priority 3: Events (Score changes, Migrations) ---
                if q.qsize() < max_q_size:
                    event_mints = await self.db_client.get_tokens_with_recent_events_for_ai_eval(
                        200, 15, self.config.get('AI_REFRESH_INTERVAL_EVENT_MIN', 30)
                    )
                    for mint in event_mints:
                        if q.qsize() < max_q_size:
                            active_pos = await self.db_client.pool.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)
                            context = "SELL/HOLD" if active_pos else "REBUY"
                            await q.put((-25, (mint, context)))
                            added_count += 1
                        else: break
                    if event_mints: log_debug(f"🧠 AI Queue: Added {len(event_mints)} event-triggered tokens.")

                # --- Priority 5: General Staleness Refresh ---
                if q.qsize() < max_q_size:
                    stale_mints = await self.db_client.get_stale_tokens_for_ai_eval(
                         self.config.get('AI_STALE_REFRESH_BATCH_SIZE', 5), self.config.get('AI_REFRESH_INTERVAL_STALE_MIN', 60)
                    )
                    for mint in stale_mints:
                        if q.qsize() < max_q_size:
                             active_pos = await self.db_client.pool.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)
                             context = "SELL/HOLD" if active_pos else "INITIAL BUY"
                             await q.put((50, (mint, context)))
                             added_count += 1
                        else: break
                    if stale_mints: log_debug(f"🧠 AI Queue: Added {len(stale_mints)} stale tokens for refresh.")
                
                if added_count > 0:
                    log_info(f"🧠 AI Queue Populator added {added_count} tasks. Current size: {q.qsize()}.")

            except asyncio.CancelledError: 
                log_info("📊 AI Queue Populator task cancelled.")
                break
            except Exception as e: 
                log_error(f"🚨 Error in AI Queue Populator: {e}", exc_info=True)
            
            await self.state.wait_or_interrupt(timeout=60) # Run once per minute
            
        log_info("📊 AI Queue Populator shutting down.")

    async def status_updater(self):
        """Periodically updates the bot_status.json file with key metrics."""
        log_info(":rocket: Status updater task started.")
        while not self.state.shutdown_event.is_set():
            try:
                current_process_status = "RUNNING"
                if self.state.shutdown_event.is_set(): 
                    current_process_status = "STOPPING"
                    
                uptime_seconds = (datetime.now(timezone.utc) - self.bot_start_time).total_seconds()
                active_subs = await self.state.get_token_subscriptions()
                sol_balance = await self.state.get_current_sol_balance()
                sol_price = await self.state.get_sol_price()
                sol_balance_usd = (sol_balance * sol_price) if sol_balance is not None and sol_price is not None else 0.0
                
                ws_summary = {}
                if self.ws_handler: 
                    ws_summary = self.ws_handler.get_status()

                # AI-specific stats
                ai_q_size = -1
                ai_workers_active = -1
                # Check if AI components are active
                if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_semaphore:
                    ai_q_size = self.state.get_ai_evaluation_queue().qsize()
                    max_workers = self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1)
                    # Read semaphore value to see how many workers are "out"
                    active_workers = max_workers - self.ai_semaphore._value 
                    ai_workers_active = active_workers

                status_data = {
                    "bot_process_status": current_process_status, 
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": int(uptime_seconds), 
                    "active_token_subscriptions_count": len(active_subs),
                    "current_sol_balance": round(sol_balance, 6) if sol_balance is not None else None,
                    "current_sol_price_usd": round(sol_price, 4) if sol_price is not None else None,
                    "current_portfolio_value_usd": round(sol_balance_usd, 2),
                    "rugcheck_queue_size": self.state.get_rugcheck_queue().qsize(),
                    "socialscheck_queue_size": self.state.get_socialscheck_queue().qsize(),
                    "ai_evaluation_queue_size": ai_q_size,
                    "ai_workers_active": ai_workers_active,
                    "websocket_summary": ws_summary 
                }
                self._write_status(status_data)
                
                await self.state.wait_or_interrupt(timeout=5) # Update status every 5s
                
            except asyncio.CancelledError:
                log_info(":stop_sign: Status updater task shutting down.")
                break
            except Exception as e:
                log_error(f":police_car_light: Error in status updater: {e}", exc_info=True)
                self._write_status({"bot_process_status": "ERROR_IN_STATUS_UPDATER", "error_message": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
                await self.state.wait_or_interrupt(timeout=15)
        
        log_info("Status updater task finished. Writing final STOPPED status.")
        self._write_status({"bot_process_status": "STOPPED", "timestamp": datetime.now(timezone.utc).isoformat()})

    async def monitor_tasks(self):
        """Periodically logs a rich status panel of all bot components and tasks."""
        try:
            while not self.state.shutdown_event.is_set():
                sol_amount = await self.state.get_current_sol_balance() or 0.0
                sol_price_usd = await self.state.get_sol_price()
                sol_price_str = f"[bold green]${sol_price_usd:.4f}[/bold green]" if sol_price_usd else "[bold red]N/A[/red]"
                uptime = str(timedelta(seconds=int((datetime.now(timezone.utc) - self.bot_start_time).total_seconds())))
                open_trades_str = f"[yellow]{len(await self.db_client.get_active_buy_positions())}[/yellow]" if self.db_client and self.db_client.pool else "[dim]N/A[/dim]"

                # WebSocket Status
                ws_lines = []
                if self.ws_handler:
                    summary = self.ws_handler.get_status()
                    status = summary.get("connection_status", "Error")
                    style = "green" if status == "Connected" else "yellow" if status == "Reconnecting" else "red"
                    time_since = summary.get("time_since_last_message_s", -1)
                    if isinstance(time_since, (int, float)) and time_since > 60: 
                        status += f" (Stale: {time_since:.0f}s)"
                        style = "red" # Mark stale as red
                    ws_lines.append(f"[bold cyan]│[/bold cyan] :electric_plug: [bold]Websocket:[/bold] [{style}]{status}[/{style}]")
                    ws_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]NewToken Stream:[/bold] [{'green' if summary.get('new_token_subscribed') else 'red'}]Subscribed[/]")
                    ws_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]Migration Stream:[/bold] [{'green' if summary.get('migration_subscribed') else 'red'}]Subscribed[/]")
                    ws_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Token Trades Subbed:[/bold] [magenta]{summary.get('trade_subscriptions_count', 0)}[/magenta]")
                    next_run = await self.state.get_ws_refresh_next_run_ts()
                    if next_run:
                        remaining = (next_run - datetime.now(timezone.utc)).total_seconds() / 60
                        timer = f"[yellow]{remaining:.1f} min[/yellow]" if remaining > 0 else "[yellow]Soon.[/yellow]"
                    else: 
                        timer = "[green]In Progress.[/green]"
                    ws_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Next WS Refresh:[/bold] {timer}")

                # --- MODIFIED AI Status ---
                ai_lines = []
                ai_enabled = self.config.get('AI_DECISION_MAKING_ENABLED', False)
                ai_status_color = "green" if ai_enabled else "red"
                ai_status_text = "ENABLED" if ai_enabled else "DISABLED"
                
                ai_model_name_str = ""
                # Only show model name if AI is enabled AND the maker is initialized
                if ai_enabled and self.ai_decision_maker:
                    model_name = self.config.get('AI_MODEL_NAME', 'N/A')
                    ai_model_name_str = f" [dim](Model: {model_name})[/dim]"

                ai_lines.append(f"[bold cyan]│[/bold cyan] :brain: [bold]AI Status:[/bold] [bold {ai_status_color}]{ai_status_text}[/bold {ai_status_color}]{ai_model_name_str}")
                
                if ai_enabled and self.ai_semaphore:
                    max_workers = self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1)
                    active_workers = max_workers - self.ai_semaphore._value 
                    ai_q_size = self.state.get_ai_evaluation_queue().qsize()
                    
                    ai_lines.extend([
                        f"[bold cyan]│  ├─ [/bold cyan][bold]AI Queue:[/bold] [blue]{ai_q_size}[/blue]",
                        f"[bold cyan]│  └─ [/bold cyan][bold]Active Workers:[/bold] [magenta]{active_workers}/{max_workers}[/magenta]",
                    ])
                # --- END MODIFIED AI Status ---

                # Task Status
                task_lines = []
                active_count = 0
                # --- MODIFIED: Show all tasks, including dynamic AI tasks ---
                all_tasks = self.tasks # self.tasks is now dynamically updated
                for task in all_tasks:
                    if not task: continue # Skip if a task handle is None
                    name = task.get_name()
                    status = "running"
                    style = "green"
                    if task.done(): 
                        status = "error" if task.exception() else "done"
                        style = "red"
                    else: 
                        active_count += 1
                    task_lines.append(f"[bold cyan]├──[/bold cyan] {name}: [bold {style}]{status}[/bold {style}]")

                # Assemble Log Panel
                log_parts = [
                    "\n[bold cyan]┌────────────────────────────────────[/bold cyan]",
                    "[bold cyan]│[/bold cyan] :robot: [bold magenta]Task Monitor[/bold magenta]",
                    "[bold cyan]│────────────────────────────────────[/bold cyan]",
                    f"[bold cyan]│[/bold cyan] :moneybag: [bold]SOL Balance:[/bold] {sol_amount:.4f}",
                    f"[bold cyan]│[/bold cyan] :timer_clock:  [bold]Uptime:[/bold]  {uptime}",
                    f"[bold cyan]│[/bold cyan] :heavy_dollar_sign: [bold]Actual SOL Price:[/bold] {sol_price_str}",
                    f"[bold cyan]│[/bold cyan] :bar_chart: [bold]Open Trades:[/bold] {open_trades_str}",
                    f"[bold cyan]│[/bold cyan] :recycle: [bold]RugCheck Queue:[/bold] [blue]{self.state.get_rugcheck_queue().qsize()}[/blue]",
                    f"[bold cyan]│[/bold cyan] :speech_balloon: [bold]Socials Queue:[/bold] [blue]{self.state.get_socialscheck_queue().qsize()}[/blue]",
                    *ai_lines,
                    *ws_lines,
                    f"[bold cyan]│[/bold cyan] :gear: [bold]Managed Tasks:[/bold] {active_count}/{len(all_tasks)}",
                    "[bold cyan]│[/bold cyan] :clipboard: [bold]Tasks:[/bold]",
                    *task_lines,
                    "[bold cyan]└────────────────────────────────────[/bold cyan]"
                ]
                log_debug("\n".join(log_parts))
                
                await self.state.wait_or_interrupt(timeout=self.config.get('MONITOR_TASK_INTERVAL_SECONDS', 30))
                
        except asyncio.CancelledError:
            log_info(":stop_sign: Monitor task shutting down.")
        except Exception as e:
            log_error(f":police_car_light: [bold red]FATAL error in Monitor task[/bold red]: {e}", exc_info=True)

    async def command_listener(self):
        """Listens for commands (e.g., 'STOP') from the main.py controller via a file."""
        last_command = None
        while not self.state.shutdown_event.is_set():
            try:
                if os.path.exists(COMMAND_FILE):
                    with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                        command = f.read().strip()
                    
                    if command and command != last_command:
                        log_info(f"Received command: '{command}'")
                        last_command = command
                        
                        # --- Process Commands ---
                        if command.upper() == "RESTART_WEBSOCKET":
                            if self.ws_handler: 
                                # Call start() on the handler; its internal supervisor will handle
                                # the reconnection logic.
                                self.ws_handler.start()
                                log_info("WebSocket restart initiated by command.")
                        elif command.upper() == "STOP": 
                            self.state.trigger_shutdown()
                        elif command.upper() == "STOP_BUYING": 
                            self.state.is_buying_enabled = False
                            log_info("Buying has been disabled by command.")
                        elif command.upper() == "START_BUYING": 
                            self.state.is_buying_enabled = True
                            log_info("Buying has been enabled by command.")
                        elif command.upper() == "SELL_ALL_IMMEDIATELY": 
                            if self.trading_manager:
                                asyncio.create_task(self.trading_manager.execute_manual_sell_all())
                        elif command.upper().startswith("SELL_"): 
                            mint = command[len("SELL_"):]
                            if self.trading_manager:
                                asyncio.create_task(self.trading_manager.execute_manual_sell(mint))
                        
                        # Clear the command file after processing
                        with open(COMMAND_FILE, 'w') as f: f.write("")
                        
                await self.state.wait_or_interrupt(timeout=5) # Poll for command every 5s
                
            except asyncio.CancelledError: 
                log_info(":stop_sign: Command listener task shutting down."); 
                break
            except Exception as e: 
                log_error(f":police_car_light: Error in command listener: {e}", exc_info=True)
    
    async def shutdown(self):
        """Performs a graceful shutdown of all bot components."""
        if getattr(self, '_shutdown_called', False): 
            return # Shutdown already in progress
        self._shutdown_called = True
        
        log_info(":stop_button: [bold red]Shutdown initiated[/bold red]...")
        self.state.trigger_shutdown() # Signal all tasks to stop
        
        # --- Explicitly stop dynamic services first ---
        log_info("Shutting down AI services...")
        await self.stop_ai_services()

        log_info("Shutting down WebSocket handler...")
        if self.ws_handler: 
            await self.ws_handler.shutdown()
            
        log_info("Cancelling all remaining tasks...")
        for task in self.tasks: 
            if task and not task.done():
                task.cancel()
                
        # Wait for all tasks to acknowledge cancellation
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        if self.db_client and self.db_client.pool:
            await self.db_client.close()
            
        log_info(":checkered_flag: Bot shutdown complete.")

    async def run_vector_index_maintenance(self):
        """Periodically runs VACUUM ANALYZE on the AI memory table."""
        await self.state.wait_or_interrupt(timeout=300) # Wait 5 mins after startup
        log_info("🔧 Vector Index Maintenance task started.")
        
        while not self.state.shutdown_event.is_set():
            try:
                log_info("🔧 Starting periodic VACUUM ANALYZE on ai_decision_memory...")
                async with self.db_client.pool.acquire() as conn:
                    # Set a statement timeout (e.g., 10 minutes)
                    await conn.execute("SET statement_timeout = 600000;")
                    await conn.execute("VACUUM ANALYZE ai_decision_memory;")
                    await conn.execute("RESET statement_timeout;")
                log_info("🔧 Vector index maintenance complete.")
                
                # Run every 6 hours
                await self.state.wait_or_interrupt(timeout=(6 * 60 * 60)) 
            
            except asyncio.CancelledError:
                log_info("🔧 Vector Index Maintenance task cancelled.")
                break
            except Exception as e:
                log_error(f":police_car_light: Error in vector index maintenance: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=3600) # Wait 1 hour on error
        
        log_info("🔧 Vector Index Maintenance task shutting down.")

    async def ai_outcome_monitor_task(self):
        """
        Periodically checks for outcomes (rugs, moons) of tokens the
        AI evaluated but the bot did not purchase. This feeds back into
        the RAG memory for future decisions.
        """
        await self.state.wait_or_interrupt(timeout=600) # Wait 10 mins after startup
        log_info("🧠 AI Outcome Monitor task started.")

        while not self.state.shutdown_event.is_set():
            try:
                # Check if AI is enabled in this loop iteration
                if not self.ai_decision_maker or not self.config.get('AI_DECISION_MAKING_ENABLED', False):
                    await self.state.wait_or_interrupt(timeout=1800) # Sleep 30 mins if AI is off
                    continue

                log_debug("🧠 AI Outcome Monitor: Checking for non-trade outcomes...")
                async with self.db_client.pool.acquire() as conn:
                    # 1. Get tokens AI has evaluated but bot doesn't own
                    tokens_to_check = await self.db_client.get_tokens_for_outcome_analysis(lookback_hours=24, conn=conn)
                    if not tokens_to_check:
                        log_debug("🧠 AI Outcome Monitor: No new non-portfolio tokens to analyze.")
                        await self.state.wait_or_interrupt(timeout=1800) # Sleep 30 mins
                        continue

                    log_info(f"🧠 AI Outcome Monitor: Found {len(tokens_to_check)} tokens to analyze for outcomes.")
                    
                    for record in tokens_to_check:
                        mint = record['mint']
                        last_decision = record['decision']
                        last_decision_ts = record['evaluation_timestamp']
                        last_metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                        price_at_decision = last_metadata.get('price', 0.0)

                        # 2. Check for "Dodged Bullet" (Rug)
                        rugged_record = await conn.fetchrow(
                            "SELECT backup_reason, backup_timestamp FROM tokens_backup WHERE mint = $1 AND backup_reason IN ('high_rugcheckscore', 'dead_token')",
                            mint
                        )
                        
                        outcome_snapshot = None
                        outcome_decision = None

                        if rugged_record:
                            # This token was rugged!
                            outcome_snapshot = {
                                "mint": mint, "source": last_metadata.get('source', 'PUMP'), "timestamp": rugged_record['backup_timestamp'].isoformat(),
                                "decision_context": "NON_TRADE_OUTCOME", "market_cap": 0, "volatility": 0,
                                "token_age_minutes": last_metadata.get('token_age_minutes', 0),
                                "is_prolific_creator": last_metadata.get('is_prolific_creator', False),
                                "uri_status": last_metadata.get('uri_status', 'N/A'),
                                "market_dynamics_summary_str": f"Token rugged. Reason: {rugged_record['backup_reason']}",
                                "trade_history_summary": "No trades by bot."
                            }
                            outcome_decision = {
                                "decision": "DODGED_BULLET (RUGGED)", "confidence": 100,
                                "explanation": f"AI previously decided '{last_decision}' at {last_decision_ts.isoformat()}.\n"
                                             f"Token was later rugged for reason: {rugged_record['backup_reason']} at {rugged_record['backup_timestamp'].isoformat()}.\n"
                                             f"This was a correct non-action."
                            }
                            log_info(f"🧠 AI Outcome: Logged DODGED_BULLET for {mint}.")

                        else:
                            # 3. Check for "Missed Opportunity" (Moon)
                            price_data = await self.db_client.get_price_and_market_cap_for_decision(mint, self.config, conn)
                            current_price = price_data.get('price')
                            
                            if current_price and price_at_decision > 0:
                                price_multiplier = current_price / price_at_decision
                                # Let's define "moon" as 10x (900% profit)
                                if price_multiplier >= 10.0:
                                    outcome_snapshot = {
                                        "mint": mint, "source": last_metadata.get('source', 'PUMP'), "timestamp": datetime.now(timezone.utc).isoformat(),
                                        "decision_context": "NON_TRADE_OUTCOME",
                                        "market_cap": price_data.get('market_cap', 0) * (await self.state.get_sol_price()),
                                        "volatility": 0, "token_age_minutes": last_metadata.get('token_age_minutes', 0),
                                        "is_prolific_creator": last_metadata.get('is_prolific_creator', False),
                                        "uri_status": last_metadata.get('uri_status', 'N/A'),
                                        "market_dynamics_summary_str": f"Token price increased {price_multiplier:.0f}x.",
                                        "trade_history_summary": "No trades by bot."
                                    }
                                    outcome_decision = {
                                        "decision": "MISSED_OPPORTUNITY (MOON)", "confidence": 100,
                                        "explanation": f"AI previously decided '{last_decision}' at price {price_at_decision:.9f} SOL.\n"
                                                     f"Token subsequently rose to {current_price:.9f} SOL ({price_multiplier:.0f}x increase).\n"
                                                     f"This was an incorrect non-action."
                                    }
                                    log_info(f"🧠 AI Outcome: Logged MISSED_OPPORTUNITY for {mint}.")

                        # 4. If an outcome was found, log it to RAG memory
                        if outcome_snapshot and outcome_decision and self.ai_decision_maker:
                            await self.ai_decision_maker.add_decision_snapshot_to_memory(outcome_snapshot, outcome_decision)

            except asyncio.CancelledError:
                log_info("🧠 AI Outcome Monitor task cancelled.")
                break
            except Exception as e:
                log_error(f":police_car_light: Error in AI Outcome Monitor: {e}", exc_info=True)
            
            # Sleep for 30 minutes before the next check
            await self.state.wait_or_interrupt(timeout=1800)
        
        log_info("🧠 AI Outcome Monitor task shutting down.")

    async def main(self):
        """The main entry point for the bot's asynchronous execution."""
        self.loop = asyncio.get_running_loop()
        
        # --- 1. Setup Logging & Signals ---
        if threading.current_thread() is threading.main_thread():
            if not self.no_log_rotate:
                rotate_log_file()
            self.register_signal_handlers()
        
        setup_logging()
        
        try:
            # --- 2. Initialize Database ---
            self.db_client = DatabaseClient(config_dict=self.config)
            await self.db_client.connect()
            await self.state.set_db_client(self.db_client)
            
            # --- 3. Handle DB Maintenance Flags ---
            if self.backup: 
                await self.db_client.backup_db(True)
            if self.cleanup: 
                await self.db_client.cleanup_db(True)
                
        except Exception as db_err:
            log_critical(f"CRITICAL: Failed database setup: {db_err}", exc_info=True)
            self._write_status({"bot_process_status": "ERROR_DB_SETUP", "error_message": str(db_err), "timestamp": datetime.now(timezone.utc).isoformat()})
            return        

        # --- 4. Fetch Initial Price ---
        if not await self._fetch_initial_sol_price():
            log_critical("🔴 Failed to fetch initial SOL price. Functionality may be limited.")

        # --- 5. Start AI Services (if enabled) ---
        if self.config.get('AI_DECISION_MAKING_ENABLED', False):
            log_info("Initial config is set to ENABLE AI. Starting services...")
            await self.start_ai_services() # This now populates self.ai_decision_maker
        else:
            log_info("🧠 AI Decision Making is DISABLED by initial configuration.")

        # --- 6. Initialize Core Components ---
        self.ws_handler = WebSocketHandler(self.db_client, self.state, self.config)
        await self.state.set_websocket_handler(self.ws_handler)
        self.socials_proc = SocialsProcessor(state=self.state, db_client=self.db_client, config_dict=self.config)
        
        # Pass the (potentially None) ai_decision_maker instance to TradingManager
        self.trading_manager = TradingManager(
            db_client=self.db_client, 
            config_dict=self.config, 
            state=self.state,
            ai_decision_maker=self.ai_decision_maker 
        )

        self.dexscreener_fetcher = DexscreenerFetcher(state=self.state, db_client=self.db_client)
        self.rugchecker = Rugcheck(
            state=self.state, db_client=self.db_client,
            websocket_handler=self.ws_handler, 
            socials_processor=self.socials_proc,
            config_dict=self.config
        )

        # --- 7. Start WebSocket and All Tasks ---
        self.ws_handler.start()

        # self.tasks now only contains non-AI tasks
        self.tasks = [
            asyncio.create_task(self.status_updater(), name="status_updater"),
            asyncio.create_task(self.config_updater(), name="config_updater"),
            asyncio.create_task(self.command_listener(), name="command_listener"),
            asyncio.create_task(self.monitor_tasks(), name="task_monitor"),
            asyncio.create_task(update_sol_price(self.state, self.db_client), name="sol_price_updater"),
            asyncio.create_task(trade_worker(self.ws_handler.trade_queue), name="trade_worker"),
            asyncio.create_task(self.dexscreener_fetcher.run(), name="dexscreener_fetcher"),
            *self.socials_proc.start(),
            asyncio.create_task(self.run_buy_checks(), name="buy_opportunity_checker"),
            asyncio.create_task(self.run_sell_checks(), name="sell_opportunity_checker"),
            asyncio.create_task(self.run_heartbeat_emitter(), name="heartbeat_emitter"),
            self.rugchecker.start(),
        ]
        
        log_info(":rocket: [bold green]Trading bot core components started.[/bold green]")
        
        # --- 8. Run Until Shutdown ---
        try:
            await self.state.wait_for_shutdown()
        except Exception as e:
            log_critical(f":police_car_light: CRITICAL ERROR in bot's main execution: {e}", exc_info=True)
            self.state.trigger_shutdown()
        finally:
            log_info("Main execution loop ended. Proceeding to full shutdown.")

    async def run_heartbeat_emitter(self):
        """Emits a periodic 'heartbeat' to the database to monitor bot liveness."""
        log_debug("❤️ Heartbeat emitter started.")
        try:
            if self.db_client: await self.db_client.insert_heartbeat(event_type="STARTUP")
        except Exception as e:
            log_error(f":police_car_light: Error in heartbeat emitter startup: {e}", exc_info=True)
            
        while not self.state.shutdown_event.is_set():
            try:
                if self.db_client: await self.db_client.insert_heartbeat()
                await self.state.wait_or_interrupt(timeout=self.config.get('HEARTBEAT_EMIT_INTERVAL_SECONDS', 60))
            except asyncio.CancelledError: 
                break
            except Exception as e:
                log_error(f":police_car_light: Error in heartbeat emitter: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=60)

    async def run_buy_checks(self):
        """Periodically runs the logic to check for new buy opportunities."""
        log_info(":chart_with_upwards_trend: [bold]Starting buy opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: 
                    await self.trading_manager.check_trading_opportunities()
                await self.state.wait_or_interrupt(timeout=self.config.get('BUY_CHECK_INTERVAL', 10))
            except asyncio.CancelledError: 
                break
            except Exception as e:
                log_error(f":police_car_light: Error in buy checker loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=30)

    async def run_sell_checks(self):
        """Periodically runs the logic to manage and sell active positions."""
        log_info(":chart_with_downwards_trend: [bold]Starting sell opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: 
                    await self.trading_manager.check_sell_opportunities()
                await self.state.wait_or_interrupt(timeout=self.config.get('SELL_CHECK_INTERVAL', 3))
            except asyncio.CancelledError: 
                break
            except Exception as e:
                log_error(f":police_car_light: Error in sell checker loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=12)

# --- Main Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting.")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file with GA parameters.")
    parser.add_argument("--no-log-rotate", action="store_true", help="Disable log rotation (used by main.py).")
    # --- NEW: Add --rl-agent-path argument ---
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")

    args = parser.parse_args()

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    bot_instance = None
    async def run_bot_async_wrapper():
        """Async wrapper to create, run, and shut down the bot instance."""
        global bot_instance
        bot_instance = TradingBot(
            cleanup=args.cleanup, 
            backup=args.backup, 
            params_file=args.params_file, 
            no_log_rotate=args.no_log_rotate
        )
        try:
            await bot_instance.main()
        except (KeyboardInterrupt, SystemExit):
            log_info("Interrupted. Triggering shutdown...")
            if bot_instance and not bot_instance.state.shutdown_event.is_set():
                bot_instance.state.trigger_shutdown()
        except Exception as e:
            log_critical(f":police_car_light: Unexpected error in bot's main execution: {e}", exc_info=True)
            if bot_instance and not bot_instance.state.shutdown_event.is_set():
                 bot_instance.state.trigger_shutdown()
        finally:
            if bot_instance:
                await bot_instance.shutdown()

    try:
        asyncio.run(run_bot_async_wrapper())
    except KeyboardInterrupt:
        log_info("Top-level KeyboardInterrupt.")
    finally:
        log_info("Trading Bot script finished.")