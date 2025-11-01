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

PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR_BOT = os.path.join(PROJECT_ROOT_DIR, 'data')
COMMAND_FILE = os.path.join(DATA_DIR_BOT, 'bot_command.txt')
STATUS_FILE = os.path.join(DATA_DIR_BOT, 'bot_status.json')
DYNAMIC_CONFIG_FILE = os.path.join(DATA_DIR_BOT, 'dynamic_config.json')

class TradingBot:
    """Main class for running the trading bot."""

    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, no_log_rotate: bool = False):
        self.loop = None
        self.state = GlobalState.get_instance()
        self.cleanup = cleanup
        self.backup = backup
        self.no_log_rotate = no_log_rotate
        self.params_file = params_file
        self.db_client = None
        self.ws_handler = None
        self.tasks = []
        self.config = {}
        self.base_config = {}
        self._load_base_config()
        self.trading_manager = None
        self._last_dynamic_config_mtime = 0
        self.bot_start_time = datetime.now(timezone.utc)
        self.dexscreener_fetcher = None
        self.socials_proc = None
        self.rugchecker = None
        self.ai_decision_maker = None
        self.ai_semaphore = None 

        os.makedirs(DATA_DIR_BOT, exist_ok=True)
        self._write_status({"bot_process_status": "INITIALIZING", "timestamp": datetime.now(timezone.utc).isoformat()})

    async def _fetch_initial_sol_price(self) -> bool:
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

    def _filter_serializable_config(self, config_dict):
        serializable_config = {}
        for key, value in config_dict.items():
            if isinstance(value, set):
                serializable_config[key] = list(value)
            elif isinstance(value, timedelta):
                serializable_config[key] = str(value)
            elif isinstance(value, (int, float, str, bool, list, dict)) or value is None:
                serializable_config[key] = value
            else:
                serializable_config[key] = str(value)
        return serializable_config

    def _load_base_config(self):
        try:
            loaded_config = {}
            for key in dir(config_module):
                if key.isupper() and not key.startswith('_'):
                    value = getattr(config_module, key)
                    if not inspect.ismodule(value) and not inspect.isclass(value) and not inspect.isfunction(value):
                        loaded_config[key] = value
            self.base_config = loaded_config.copy()
            self.config = loaded_config.copy()
            log_info(":gear: Base configuration loaded successfully.")
            if not os.path.exists(DYNAMIC_CONFIG_FILE):
                with open(DYNAMIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self._filter_serializable_config(self.config), f, indent=4)
        except Exception as e:
            log_critical(f":x: [bold red]CRITICAL: Failed to load base configuration[/bold red]: {e}", exc_info=True)
            raise ValueError("Failed to load critical base configuration.") from e
        
    def register_signal_handlers(self):
        def signal_handler():
            log_info(":heavy_exclamation_mark: [bold red]Signal received[/bold red], initiating shutdown...")
            self.state.trigger_shutdown()
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, lambda *_: signal_handler())
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, lambda *_: signal_handler())

    async def config_updater(self):
        log_info(f"⚙️ Dynamic config updater started. Watching: {os.path.abspath(DYNAMIC_CONFIG_FILE)}")
        while not self.state.shutdown_event.is_set():
            await asyncio.sleep(10)
            try:
                if not os.path.exists(DYNAMIC_CONFIG_FILE): continue
                current_mtime = os.path.getmtime(DYNAMIC_CONFIG_FILE)
                if current_mtime > self._last_dynamic_config_mtime:
                    log_info(f"Detected change in {DYNAMIC_CONFIG_FILE}. Attempting to load updates.")
                    with open(DYNAMIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                        dynamic_conf = json.load(f)
                    updated_count = 0; changed_params = {}
                    for key, value in dynamic_conf.items():
                        key_upper = key.upper()
                        if key_upper in self.config and value != self.config[key_upper]:
                            self.config[key_upper] = value
                            changed_params[key_upper] = value
                            updated_count += 1
                    if updated_count > 0:
                        log_info(f"Applied {updated_count} configuration updates: {changed_params}")
                    self._last_dynamic_config_mtime = current_mtime
            except Exception as e:
                log_error(f":police_car_light: Error in config_updater loop: {e}", exc_info=True)
        log_info("⚙️ Dynamic config updater task shutting down.")

    def _write_status(self, status_data: dict):
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=4)
        except IOError as e:
            log_error(f":police_car_light: Error writing status file {STATUS_FILE}: {e}")

    async def ai_evaluation_worker(self):
        log_info("🤖 AI Evaluation Worker started.")
        if not self.ai_decision_maker or not self.db_client:
            log_critical("🤖 AI Worker cannot start: AIDecisionMaker or DatabaseClient not initialized.")
            return
        while not self.state.shutdown_event.is_set():
            mint = None
            try:
                priority, (mint, decision_context) = await asyncio.wait_for(
                    self.state.get_ai_evaluation_queue().get(), timeout=1.0
                )
                log_debug(f"🤖 AI Worker: Picked up {mint} (Context: {decision_context}, Prio: {priority})")
                async with self.ai_semaphore:
                    evaluation_start_time = time.monotonic()
                    comprehensive_data = await fetch_comprehensive_token_data(self.db_client, mint)
                    advice = await self.ai_decision_maker.get_trade_advice(comprehensive_data) 
                    eval_ts = datetime.now(timezone.utc)
                    prompt_hash = None; data_snapshot = comprehensive_data 
                    async with self.db_client.pool.acquire() as conn:
                        async with conn.transaction():
                            await self.db_client.insert_ai_decision(
                                mint=mint, context=decision_context,
                                decision=advice['decision'], confidence=advice['confidence'],
                                explanation=advice.get('explanation'),
                                data_snapshot=data_snapshot, prompt_hash=prompt_hash,
                                conn=conn
                            )
                            await self.db_client.update_token_ai_eval_timestamp(mint, eval_ts, conn=conn)
                    evaluation_duration = time.monotonic() - evaluation_start_time
                    log_info(f"🤖 AI eval complete for {mint} ({decision_context}) -> {advice['decision']} ({advice['confidence']}%) in {evaluation_duration:.2f}s")
                self.state.get_ai_evaluation_queue().task_done()
                mint = None 
            except asyncio.TimeoutError: continue
            except asyncio.CancelledError: log_info("🤖 AI Evaluation Worker task cancelled."); break
            except ValueError as ve: 
                log_error(f"🤖 AI Worker: Error fetching data for {mint} (likely deleted): {ve}")
                if mint:
                    try: self.state.get_ai_evaluation_queue().task_done()
                    except ValueError: pass
            except Exception as e:
                log_error(f"🚨 Unexpected error in AI Evaluation Worker: {e}", exc_info=True)
                if mint:
                    try: self.state.get_ai_evaluation_queue().task_done()
                    except ValueError: pass
                await asyncio.sleep(10)
        log_info("🤖 AI Evaluation Worker shutting down.")

    async def populate_ai_queue_periodic(self):
        log_info("📊 AI Queue Populator started.")
        while not self.state.shutdown_event.is_set():
            if not self.config.get('AI_DECISION_MAKING_ENABLED', False):
                await asyncio.sleep(60); continue
            q = self.state.get_ai_evaluation_queue()
            if q.full():
                log_warning("🤖 AI evaluation queue is full. Skipping population cycle.")
                await asyncio.sleep(30); continue
            max_q_size = self.config.get('AI_QUEUE_MAX_SIZE', 1000); added_count = 0
            try:
                portfolio_mints = await self.db_client.get_active_portfolio_for_ai_eval(
                    self.config.get('AI_REFRESH_INTERVAL_PORTFOLIO_MIN', 5)
                )
                for mint in portfolio_mints:
                    if q.qsize() < max_q_size: await q.put((-100, (mint, 'SELL/HOLD'))); added_count += 1
                    else: break
                if portfolio_mints: log_debug(f"🤖 AI Queue: Added {len(portfolio_mints)} portfolio tokens.")
                if q.qsize() < max_q_size:
                    pump_mints = await self.db_client.get_top_pump_momentum_for_ai_eval(
                        self.config.get('AI_MOMENTUM_TOP_N', 5), 30, self.config.get('AI_REFRESH_INTERVAL_MOMENTUM_MIN', 15)
                    )
                    for mint in pump_mints:
                        if q.qsize() < max_q_size:
                            past_pos_count = await self.db_client.pool.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
                            context = "REBUY" if past_pos_count > 0 else "INITIAL BUY"
                            await q.put((-50, (mint, context))); added_count += 1
                        else: break
                    if pump_mints: log_debug(f"🤖 AI Queue: Added {len(pump_mints)} PUMP momentum tokens.")
                if q.qsize() < max_q_size:
                    dex_mints = await self.db_client.get_top_dex_momentum_for_ai_eval(
                        self.config.get('AI_MOMENTUM_TOP_N', 5), 30, self.config.get('AI_REFRESH_INTERVAL_MOMENTUM_MIN', 15)
                    )
                    for mint in dex_mints:
                         if q.qsize() < max_q_size:
                            past_pos_count = await self.db_client.pool.fetchval("SELECT COUNT(*) FROM portfolio WHERE mint = $1", mint)
                            context = "REBUY" if past_pos_count > 0 else "INITIAL BUY"
                            await q.put((-45, (mint, context))); added_count += 1
                         else: break
                    if dex_mints: log_debug(f"🤖 AI Queue: Added {len(dex_mints)} DEX momentum tokens.")
                if q.qsize() < max_q_size:
                    event_mints = await self.db_client.get_tokens_with_recent_events_for_ai_eval(
                        200, 15, self.config.get('AI_REFRESH_INTERVAL_EVENT_MIN', 30)
                    )
                    for mint in event_mints:
                        if q.qsize() < max_q_size:
                            active_pos = await self.db_client.pool.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)
                            context = "SELL/HOLD" if active_pos else "REBUY"
                            await q.put((-25, (mint, context))); added_count += 1
                        else: break
                    if event_mints: log_debug(f"🤖 AI Queue: Added {len(event_mints)} event-triggered tokens.")
                if q.qsize() < max_q_size:
                    stale_mints = await self.db_client.get_stale_tokens_for_ai_eval(
                         self.config.get('AI_STALE_REFRESH_BATCH_SIZE', 5), self.config.get('AI_REFRESH_INTERVAL_STALE_MIN', 60)
                    )
                    for mint in stale_mints:
                        if q.qsize() < max_q_size:
                             active_pos = await self.db_client.pool.fetchval("SELECT 1 FROM portfolio WHERE mint = $1 AND status = 'active' AND tx_type = 'buy' LIMIT 1", mint)
                             context = "SELL/HOLD" if active_pos else "INITIAL BUY"
                             await q.put((50, (mint, context))); added_count += 1
                        else: break
                    if stale_mints: log_debug(f"🤖 AI Queue: Added {len(stale_mints)} stale tokens for refresh.")
                if added_count > 0:
                    log_info(f"AI Queue Populator added {added_count} tasks. Current size: {q.qsize()}.")
            except asyncio.CancelledError: log_info("📊 AI Queue Populator task cancelled."); break
            except Exception as e: log_error(f"🚨 Error in AI Queue Populator: {e}", exc_info=True)
            await asyncio.sleep(60)
        log_info("📊 AI Queue Populator shutting down.")

    async def status_updater(self):
        """
        [MODIFIED] Periodically gathers and writes detailed bot status to bot_status.json.
        Now includes AI queue size and worker status.
        """
        log_info(":rocket: Status updater task started.")
        while not self.state.shutdown_event.is_set():
            try:
                current_process_status = "RUNNING"
                if self.state.shutdown_event.is_set(): current_process_status = "STOPPING"
                
                uptime_seconds = (datetime.now(timezone.utc) - self.bot_start_time).total_seconds()
                active_subs = await self.state.get_token_subscriptions()
                sol_balance = await self.state.get_current_sol_balance()
                sol_price = await self.state.get_sol_price()
                sol_balance_usd = (sol_balance * sol_price) if sol_balance is not None and sol_price is not None else 0.0
                
                ws_summary = {}
                if self.ws_handler: ws_summary = self.ws_handler.get_status()

                # --- NEW AI STATUS ---
                ai_q_size = -1
                ai_workers_active = -1
                if self.config.get('AI_DECISION_MAKING_ENABLED', False) and self.ai_semaphore:
                    ai_q_size = self.state.get_ai_evaluation_queue().qsize()
                    
                    # --- FIX ---
                    # Get max_workers from the config, not a private attribute
                    max_workers = self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1)
                    # Access the (still private, but more stable) _value
                    active_workers = max_workers - self.ai_semaphore._value 
                    # --- END FIX ---

                    ai_workers_active = active_workers
                # --- END NEW AI STATUS ---

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
                    "ai_evaluation_queue_size": ai_q_size,    # <-- ADDED
                    "ai_workers_active": ai_workers_active, # <-- ADDED
                    "websocket_summary": ws_summary 
                }
                self._write_status(status_data)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                log_info(":stop_sign: Status updater task shutting down.")
                break
            except Exception as e:
                log_error(f":police_car_light: Error in status updater: {e}", exc_info=True)
                self._write_status({"bot_process_status": "ERROR_IN_STATUS_UPDATER", "error_message": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
                await asyncio.sleep(15)
        
        log_info("Status updater task finished. Writing final STOPPED status.")
        self._write_status({"bot_process_status": "STOPPED", "timestamp": datetime.now(timezone.utc).isoformat()})


    async def monitor_tasks(self):
        """
        [MODIFIED] Monitor and log the status of background tasks.
        Now includes AI worker status and queue size.
        """
        try:
            while not self.state.shutdown_event.is_set():
                sol_amount = await self.state.get_current_sol_balance() or 0.0
                sol_price_usd = await self.state.get_sol_price()
                sol_price_str = f"[bold green]${sol_price_usd:.4f}[/bold green]" if sol_price_usd else "[bold red]N/A[/red]"
                uptime = str(timedelta(seconds=int((datetime.now(timezone.utc) - self.bot_start_time).total_seconds())))
                open_trades_str = f"[yellow]{len(await self.db_client.get_active_buy_positions())}[/yellow]" if self.db_client and self.db_client.pool else "[dim]N/A[/dim]"

                ws_lines = []
                if self.ws_handler:
                    summary = self.ws_handler.get_status()
                    status = summary.get("connection_status", "Error"); style = "green" if status == "Connected" else "yellow" if status == "Reconnecting" else "red"
                    time_since = summary.get("time_since_last_message_s", -1)
                    if isinstance(time_since, (int, float)) and time_since > 60: status += f" (Stale: {time_since:.0f}s)"
                    ws_lines.append(f"[bold cyan]│[/bold cyan] :electric_plug: [bold]Websocket:[/bold] [{style}]{status}[/{style}]")
                    ws_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]NewToken Stream:[/bold] [{'green' if summary.get('new_token_subscribed') else 'red'}]Subscribed[/]")
                    ws_lines.append(f"[bold cyan]│  ├─ [/bold cyan][bold]Migration Stream:[/bold] [{'green' if summary.get('migration_subscribed') else 'red'}]Subscribed[/]")
                    ws_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Token Trades Subbed:[/bold] [magenta]{summary.get('trade_subscriptions_count', 0)}[/magenta]")
                    next_run = await self.state.get_ws_refresh_next_run_ts()
                    if next_run:
                        remaining = (next_run - datetime.now(timezone.utc)).total_seconds() / 60
                        timer = f"[yellow]{remaining:.1f} min[/yellow]" if remaining > 0 else "[yellow]Soon.[/yellow]"
                    else: timer = "[green]In Progress.[/green]"
                    ws_lines.append(f"[bold cyan]│  └─ [/bold cyan][bold]Next WS Refresh:[/bold] {timer}")

                task_lines = []; active_count = 0
                for task in self.tasks:
                    name = task.get_name(); status = "running"; style = "green"
                    if task.done(): status = "error" if task.exception() else "done"; style = "red"
                    else: active_count += 1
                    task_lines.append(f"[bold cyan]├──[/bold cyan] {name}: [bold {style}]{status}[/bold {style}]")

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
                ]
                
                # --- ADDED AI MONITORING SECTION ---
                ai_enabled = self.config.get('AI_DECISION_MAKING_ENABLED')
                ai_status_color = "green" if ai_enabled else "red"
                ai_status_text = "ENABLED" if ai_enabled else "DISABLED"
                log_parts.append(f"[bold cyan]│[/bold cyan] :brain: [bold]AI Status:[/bold] [bold {ai_status_color}]{ai_status_text}[/bold {ai_status_color}]")
                
                if ai_enabled and self.ai_semaphore:
                    # --- FIX ---
                    # Get max_workers from the config, not a private attribute
                    max_workers = self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1)
                    # Access the (still private, but more stable) _value
                    active_workers = max_workers - self.ai_semaphore._value 
                    # --- END FIX ---
                    ai_q_size = self.state.get_ai_evaluation_queue().qsize()
                    
                    log_parts.extend([
                        f"[bold cyan]│  ├─ [/bold cyan][bold]AI Queue:[/bold] [blue]{ai_q_size}[/blue]",
                        f"[bold cyan]│  └─ [/bold cyan][bold]Active Workers:[/bold] [magenta]{active_workers}/{max_workers}[/magenta]",
                    ])
                # --- END AI MONITORING SECTION ---

                log_parts.extend([
                    *ws_lines,
                    f"[bold cyan]│[/bold cyan] :gear: [bold]Managed Tasks:[/bold] {active_count}/{len(self.tasks)}",
                    "[bold cyan]│[/bold cyan] :clipboard: [bold]Tasks:[/bold]",
                    *task_lines,
                    "[bold cyan]└────────────────────────────────────[/bold cyan]"
                ])
                log_debug("\n".join(log_parts))
                
                await asyncio.sleep(self.config.get('MONITOR_TASK_INTERVAL_SECONDS', 30))
        except asyncio.CancelledError:
            log_info(":stop_sign: Monitor task shutting down.")
        except Exception as e:
            log_error(f":police_car_light: [bold red]FATAL error in Monitor task[/bold red]: {e}", exc_info=True)

    async def command_listener(self):
        last_command = None
        while not self.state.shutdown_event.is_set():
            try:
                if os.path.exists(COMMAND_FILE):
                    with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                        command = f.read().strip()
                    if command and command != last_command:
                        log_info(f"Received command: '{command}'")
                        last_command = command
                        if command.upper() == "RESTART_WEBSOCKET":
                            if self.ws_handler: self.ws_handler.start(); log_info("WebSocket-Neustart durch Befehl initiiert.")
                        elif command.upper() == "STOP": self.state.trigger_shutdown()
                        elif command.upper() == "STOP_BUYING": self.state.is_buying_enabled = False; log_info("Buying has been disabled.")
                        elif command.upper() == "START_BUYING": self.state.is_buying_enabled = True; log_info("Buying has been enabled.")
                        elif command.upper() == "SELL_ALL_IMMEDIATELY": asyncio.create_task(self.trading_manager.execute_manual_sell_all())
                        elif command.upper().startswith("SELL_"): mint = command[len("SELL_"):]; asyncio.create_task(self.trading_manager.execute_manual_sell(mint))
                        with open(COMMAND_FILE, 'w') as f: f.write("")
                await asyncio.sleep(5)
            except asyncio.CancelledError: log_info(":stop_sign: Command listener task shutting down."); break
            except Exception as e: log_error(f":police_car_light: Error in command listener: {e}", exc_info=True)
    
    async def shutdown(self):
        if getattr(self, '_shutdown_called', False): return
        self._shutdown_called = True
        log_info(":stop_button: [bold red]Shutdown initiated[/bold red]...")
        self.state.trigger_shutdown()
        if self.ws_handler: await self.ws_handler.shutdown()
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        if self.db_client and self.db_client.pool:
            await self.db_client.close()
        log_info(":checkered_flag: Bot shutdown complete.")

    async def main(self):
        self.loop = asyncio.get_running_loop()
        if threading.current_thread() is threading.main_thread():
            if not self.no_log_rotate:
                rotate_log_file()
            self.register_signal_handlers()
        
        setup_logging()
        
        try:
            self.db_client = DatabaseClient(config_dict=self.config)
            await self.db_client.connect()
            await self.state.set_db_client(self.db_client)
            if self.backup: await self.db_client.backup_db(True)
            if self.cleanup: await self.db_client.cleanup_db(True)
        except Exception as db_err:
            log_critical(f"CRITICAL: Failed database setup: {db_err}", exc_info=True)
            self._write_status({"bot_process_status": "ERROR_DB_SETUP", "error_message": str(db_err), "timestamp": datetime.now(timezone.utc).isoformat()})
            return        

        if not await self._fetch_initial_sol_price():
            log_critical("🔴 Failed to fetch initial SOL price. Functionality may be limited.")

        if self.config.get('AI_DECISION_MAKING_ENABLED', False):
            try:
                self.ai_decision_maker = AIDecisionMaker(config=self.config, db_client=self.db_client)
                log_info("✅ AI Decision Maker initialized successfully.")
                self.ai_semaphore = asyncio.Semaphore(self.config.get('AI_MAX_CONCURRENT_EVALUATIONS', 1))
            except Exception as ai_init_err:
                log_critical(f"CRITICAL: Failed to initialize AI Decision Maker: {ai_init_err}", exc_info=True)
                self.config['AI_DECISION_MAKING_ENABLED'] = False 
                log_warning("AI Decision Making has been DISABLED due to initialization error.")
        else:
            log_info("AI Decision Making is DISABLED by configuration.")

        self.ws_handler = WebSocketHandler(self.db_client, self.state, self.config)
        await self.state.set_websocket_handler(self.ws_handler)
        self.socials_proc = SocialsProcessor(state=self.state, db_client=self.db_client, config_dict=self.config)
        self.trading_manager = TradingManager(db_client=self.db_client, config_dict=self.config, state=self.state)
        self.dexscreener_fetcher = DexscreenerFetcher(state=self.state, db_client=self.db_client)
        self.rugchecker = Rugcheck(
            state=self.state, db_client=self.db_client,
            websocket_handler=self.ws_handler, 
            socials_processor=self.socials_proc,
            config_dict=self.config
        )

        self.ws_handler.start()

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
            self.rugchecker.start()
        ]
        if self.config.get('AI_DECISION_MAKING_ENABLED', False):
             self.tasks.append(asyncio.create_task(self.ai_evaluation_worker(), name="ai_evaluation_worker"))
             self.tasks.append(asyncio.create_task(self.populate_ai_queue_periodic(), name="ai_queue_populator"))
        
        log_info(":rocket: [bold green]Trading bot core components started.[/bold green]")
        try:
            await self.state.wait_for_shutdown()
        except Exception as e:
            log_critical(f":police_car_light: CRITICAL ERROR in bot's main execution: {e}", exc_info=True)
            self.state.trigger_shutdown()
        finally:
            log_info("Main execution loop ended. Proceeding to full shutdown.")

    async def run_heartbeat_emitter(self):
        log_debug("❤️ Heartbeat emitter started.")
        try:
            if self.db_client: await self.db_client.insert_heartbeat(event_type="STARTUP")
        except Exception as e:
            log_error(f":police_car_light: Error in heartbeat emitter: {e}", exc_info=True)
        while not self.state.shutdown_event.is_set():
            try:
                if self.db_client: await self.db_client.insert_heartbeat()
                await asyncio.sleep(self.config.get('HEARTBEAT_EMIT_INTERVAL_SECONDS', 60))
            except asyncio.CancelledError: break
            except Exception as e:
                log_error(f":police_car_light: Error in heartbeat emitter: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def run_buy_checks(self):
        log_info(":chart_with_upwards_trend: [bold]Starting buy opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: await self.trading_manager.check_trading_opportunities()
                await asyncio.sleep(self.config.get('BUY_CHECK_INTERVAL', 10))
            except asyncio.CancelledError: break
            except Exception as e:
                log_error(f":police_car_light: Error in buy checker loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def run_sell_checks(self):
        log_info(":chart_with_downwards_trend: [bold]Starting sell opportunity checker...[/bold]")
        while not self.state.shutdown_event.is_set():
            try:
                if self.trading_manager: await self.trading_manager.check_sell_opportunities()
                await asyncio.sleep(self.config.get('SELL_CHECK_INTERVAL', 3))
            except asyncio.CancelledError: break
            except Exception as e:
                log_error(f":police_car_light: Error in sell checker loop: {e}", exc_info=True)
                await asyncio.sleep(12)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting.")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file with GA parameters.")
    parser.add_argument("--no-log-rotate", action="store_true", help="Disable log rotation.")
    args = parser.parse_args()

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    bot_instance = None
    async def run_bot_async_wrapper():
        global bot_instance
        bot_instance = TradingBot(cleanup=args.cleanup, backup=args.backup, params_file=args.params_file, no_log_rotate=args.no_log_rotate)
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