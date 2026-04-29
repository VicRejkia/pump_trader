# Architecture

## Startup Path

```
main.py
  └─ FastAPI/Uvicorn (port 8000)
       └─ api/main.py → BotService
            └─ trading_bot.py → TradingBot.__init__
                 └─ run() spawns all async tasks
```

## Async Task Table

All tasks are created in `TradingBot.run()` (`trading_bot.py:1567`).

| Task name | Entry point | Responsibility |
|-----------|-------------|----------------|
| `status_updater` | `trading_bot.py` | Writes `data/bot_status.json` periodically |
| `config_updater` | `trading_bot.py` | Polls `data/dynamic_config.json` for runtime config changes |
| `command_listener` | `trading_bot.py` | Reads `data/bot_command.txt` for Telegram / API commands |
| `task_monitor` | `trading_bot.py` | Restarts crashed tasks; logs task health |
| `sol_price_updater` | `connectors/sol_price_api.py:update_sol_price` | Refreshes SOL/USD price hourly |
| `trade_worker` | `trade_processor.py:trade_worker` | Buffers up to 100 trade events (or 5 s) then bulk-inserts to DB |
| `dexscreener_fetcher` | `connectors/dexscreener_api.py:DexscreenerFetcher.run` | Fetches trend reversal data; result cached, stale data tolerated |
| `socials_proc` (multiple) | `socials_processor.py:SocialsProcessor.start` | Website/Telegram/Twitter presence scoring |
| `buy_opportunity_checker` | `trading_bot.py:run_buy_checks` | Scores new tokens (rugcheck + socials + AI), executes buys |
| `sell_opportunity_checker` | `trading_bot.py:run_sell_checks` | Evaluates stop-loss, take-profit, trailing stop on held positions |
| `heartbeat_emitter` | `trading_bot.py:run_heartbeat_emitter` | Writes heartbeat row to DB; used to detect crashes |
| `rugchecker` | `connectors/rugcheck_handler.py:Rugcheck.start` | Rate-limited risk-score fetching (10 req/60 s) via deferred queue |

**AI tasks** — started/stopped dynamically via `TradingBot.start_ai_services()` / `stop_ai_services()` (`trading_bot.py:202`):

| Task name | Entry point | Responsibility |
|-----------|-------------|----------------|
| `ai_evaluation_worker` | `trading_bot.py:ai_evaluation_worker` | Dequeues tokens and runs LLM evaluation |
| `ai_queue_populator` | `trading_bot.py:populate_ai_queue_periodic` | Periodically adds candidates to the AI evaluation queue |
| `ai_outcome_monitor` | `trading_bot.py:ai_outcome_monitor_task` | Tracks AI decision outcomes for feedback |
| `vector_index_maintenance` | `trading_bot.py:run_vector_index_maintenance` | Runs pgvector index VACUUM/ANALYZE on schedule |
| `knowledge_base_builder` | `trading_bot.py:knowledge_base_builder` | Builds RAG knowledge base from trade history |
| `migration_knowledge_builder` | `trading_bot.py:migration_knowledge_builder_task` | Builds migration-specific knowledge entries |

## Data Flow

```
pump.fun WebSocket
     │
     ▼
connectors/websocket_handler.py
     │  emits new-token and trade events onto queues
     ▼
trade_processor.py              ──────────────────────────────► PostgreSQL
     │  batch inserts (≤100 events or 5 s)                          │
     │                                                               │
     ▼                                                               │
TradingManager (trading_logic.py)  ◄────────────────────────── DB reads
     │  evaluates stop-loss, take-profit, trailing stop
     ▼
AIDecisionMaker (ai_decision_module/ai_decision_maker.py)
     │  builds context → renders YAML prompt → calls Ollama
     │  confidence > AI_DECISION_THRESHOLD (default 50%) → acts
     ▼
pgvector RAG (ai_decision_memory table)
     │
     ▼
Executors:  simulate  |  paper_trading  |  live (PumpPortal / GMGN)
```

## Shared State

`GlobalState` in `state_manager.py` is a singleton passed everywhere. Rules:
- Never introduce module-level mutable state. Add fields to `GlobalState` only.
- Locks already defined: `state.lock`, `state.db_write_lock`, `state.market_regime_lock`. Use them for shared mutable fields.
- Access pattern: `state = GlobalState.get_instance()` in `__init__`, then pass `state` as argument.

## Inter-Process Communication (IPC)

| Channel | File | Direction | Used for |
|---------|------|-----------|----------|
| Commands | `data/bot_command.txt` | API/Telegram → bot | Start/stop AI, manual sells |
| Status | `data/bot_status.json` | bot → clients | Bot health, portfolio snapshot |
| Dynamic config | `data/dynamic_config.json` | operator → bot | Runtime config changes (no restart needed) |

> **TODO:** File-based IPC via `data/bot_command.txt` is fragile — no delivery guarantee, no acknowledgement, race conditions under concurrent writers. Redis Streams or Pub/Sub is the intended replacement. See `docs/ROADMAP.md`.
