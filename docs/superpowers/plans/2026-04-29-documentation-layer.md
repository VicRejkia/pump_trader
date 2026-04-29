# Documentation Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `CLAUDE.md` as a lean navigation index and create a `docs/` folder with five focused documents that capture current state with explicit gap annotations.

**Architecture:** `CLAUDE.md` becomes a ~2 KB index of key invariants and a navigation table. Five markdown files in `docs/` each own one concern: architecture, database, modules, development setup, and roadmap. All files use `> **TODO:**` blockquotes to flag known gaps so Claude never assumes something is implemented that isn't.

**Tech Stack:** Markdown only. No code changes, no new dependencies, no test suite required.

---

### Task 1: Create `docs/ARCHITECTURE.md`

**Files:**
- Create: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Write the file**

```markdown
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
```

- [ ] **Step 2: Verify the file exists and is non-empty**

Run: `ls -lh docs/ARCHITECTURE.md && grep -c "TODO" docs/ARCHITECTURE.md`
Expected: file shown with size > 0, count ≥ 1

- [ ] **Step 3: Commit**

```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: add ARCHITECTURE.md with async task table and data flow"
```

---

### Task 2: Create `docs/DATABASE.md`

**Files:**
- Create: `docs/DATABASE.md`

- [ ] **Step 1: Write the file**

```markdown
# Database

## Setup

- PostgreSQL 12+ required
- **pgvector extension is required** before first run:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- All access is async via `asyncpg` through `database_handler.py`
- Connection pool is managed by `DatabaseClient` in `database_handler.py`

## Connection — `.env` variables

| Variable | Default | Required |
|----------|---------|----------|
| `DB_USER` | — | Yes |
| `DB_PASSWORD` | — | Yes |
| `DB_HOST` | `localhost:5432` | Yes |
| `DB_DATABASE` | — | Yes |

## Migrations

18 numbered SQL scripts in `sql/`, applied sequentially by `database_handler.py` on startup:

```
sql/01_create_tokens.sql
sql/02_create_trades.sql
sql/03_create_rugcheck.sql
sql/04_create_portfolio.sql
sql/05_create_migrations.sql          ← tracking table for applied migrations
sql/06_create_creator_wallets.sql
sql/07_create_sol_price_usd.sql
sql/08_create_bot_heartbeat.sql
sql/09_create_configuration.sql
sql/10_create_dexscreener_data.sql
sql/11_create_completed_trades.sql
sql/12_create_indexes.sql
sql/13_create_views.sql
sql/14_create_rl_tables.sql
sql/15_create_social_scores.sql
sql/16_create_ga_tables.sql
sql/17_create_ai_decision_memory.sql  ← pgvector table
sql/18_create_market_knowledge_base.sql
```

The `applied_migrations` table (created by `05_create_migrations.sql`) tracks which scripts have run. `database_handler.py` skips already-applied scripts on restart.

> **WARNING:** Never renumber or delete existing migration files. The tracking table uses filenames as keys; renaming breaks idempotency.

> **TODO:** No rollback mechanism. A migration that partially fails on startup leaves the schema in an unknown state. Manual intervention (inspect `applied_migrations`, fix the SQL, re-run) is required.

## Key Tables

| Table | Purpose |
|-------|---------|
| `tokens` | All tokens seen via pump.fun WebSocket |
| `trades` | Every individual trade event received |
| `portfolio` | Currently held positions |
| `completed_trades` | Closed positions with PnL |
| `rugcheck` | RugCheck.xyz risk scores per token |
| `socials_scores` | Website/Telegram/Twitter presence scores |
| `ai_decision_memory` | pgvector embeddings for RAG; stores past AI decisions and outcomes |
| `market_knowledge_base` | Built by knowledge base builder task; feeds RAG context |
| `ga_optimization_results` | GA optimizer run outputs |
| `rl_training_logs` | RL training episode logs |
| `bot_heartbeat` | Single-row liveness ping; updated by `heartbeat_emitter` task |
| `sol_price_usd` | SOL/USD price history |
| `creator_wallets` | Wallet → token creator mapping |
| `dexscreener_data` | Cached DexScreener API responses |

## database_handler.py

All database operations go through `DatabaseClient` in `database_handler.py`. This is the only place raw SQL should appear.

> **TODO:** `database_handler.py` is 2,801 lines — a god object that mixes schema migrations, CRUD operations, analytics queries, views, and connection management. In a future architecture phase, this should be split into focused repository classes (e.g., `TokenRepository`, `TradeRepository`, `PortfolioRepository`). **Do not add new methods to `database_handler.py`** — create new focused files instead.
```

- [ ] **Step 2: Verify**

Run: `ls -lh docs/DATABASE.md && grep -c "TODO\|WARNING" docs/DATABASE.md`
Expected: file shown, count ≥ 2

- [ ] **Step 3: Commit**

```bash
git add docs/DATABASE.md
git commit -m "docs: add DATABASE.md with schema, migration, and table reference"
```

---

### Task 3: Create `docs/MODULES.md`

**Files:**
- Create: `docs/MODULES.md`

- [ ] **Step 1: Write the file**

```markdown
# Modules

Quick reference for each major subsystem: what it does, which files matter, and known gaps.

---

## connectors/

**Responsibility:** All external API integrations. Each connector is a standalone class or module.

| File | Purpose |
|------|---------|
| `websocket_handler.py` | Persistent pump.fun WebSocket connection; emits events onto queues; reconnects with exponential backoff |
| `rugcheck_handler.py` | RugCheck.xyz risk scores; rate-limited (10 req/60 s) via internal deferred queue |
| `dexscreener_api.py` | DexScreener trend reversal data; responses cached, stale data tolerated |
| `sol_price_api.py` | SOL/USD price; single `update_sol_price()` coroutine called as a task |
| `live_trader_pumpportal.py` | Live trade execution via PumpPortal API |
| `live_trader_gmgn.py` | Live trade execution via GMGN API |

> **TODO:** `connectors/live_trader_pumpportal.py` has two unimplemented TODOs: (1) robust transaction confirmation polling and (2) fetching the actual fill price after confirmation. Both are marked in the file. **Do not enable live mode until these are resolved** — simulated PnL will not match real execution.

---

## trading_bot.py + trading_logic.py

**Responsibility:** Core async orchestration (`trading_bot.py`) and portfolio management (`trading_logic.py`).

- `TradingBot` (in `trading_bot.py`) — creates all async tasks, manages lifecycle, handles commands
- `TradingManager` (in `trading_logic.py`) — evaluates stop-loss, take-profit, trailing stop, trend reversal on held positions; calls `AIDecisionMaker` for sell advice

Key entry points:
- `TradingBot.run()` — starts everything (`trading_bot.py:1567`)
- `TradingBot.run_buy_checks()` — scores new tokens, executes buys
- `TradingBot.run_sell_checks()` — evaluates positions, executes sells
- `TradingManager.evaluate_position()` — per-position sell logic (`trading_logic.py`)

> **TODO:** `trading_bot.py` is 1,682 lines and `trading_logic.py` is 1,127 lines. Both violate single responsibility. A future architecture phase will split them (buy logic, sell logic, position manager, task orchestrator). Do not add new top-level methods to either file without discussion.

---

## ai_decision_module/

**Responsibility:** LLM-based buy/sell/re-buy decisions using local Ollama + pgvector RAG.

| File | Purpose |
|------|---------|
| `ai_decision_maker.py` | Main decision class; builds context, calls Ollama, parses confidence score |
| `ai_data_assembler.py` | Fetches and assembles token context data for prompts |
| `prompts/buy.yaml` | Prompt template for buy decisions |
| `prompts/sell.yaml` | Prompt template for sell decisions |
| `prompts/rebuy.yaml` | Prompt template for re-buy decisions |
| `prompts/base.yaml` | Shared base prompt context |

Decision flow:
1. `ai_data_assembler.py` fetches token data + portfolio history
2. `ai_decision_maker.py` queries pgvector for nearest-neighbor past decisions (RAG)
3. Renders the appropriate YAML prompt template
4. Calls Ollama locally (`ollama serve` must be running)
5. Parses confidence score; acts only if confidence > `AI_DECISION_THRESHOLD` (default 50%, in `config/config.py`)
6. Stores embedding in `ai_decision_memory` table for future RAG lookups

> **TODO:** If Ollama is unavailable the bot degrades to rule-based logic — but this degradation is not always clean. Error recovery paths in `ai_decision_maker.py` should be reviewed before production use.

---

## rl_agent_module/

**Responsibility:** PPO reinforcement learning agent (Stable-Baselines3) that learns to adjust trading parameters dynamically.

Entry point: `rl_main.py` (interactive menu) or `python main.py --rl-agent-path <path>`

Key subdirectories:
- `agents/` — PPO agent wrappers
- `training/train.py` — training loop; MLflow tracking
- `environments/` — Gym environment wrapping the trading simulator
- `inference/` — loads trained checkpoint, runs inference during live trading
- `feature_engineering/` — builds feature vectors from token/trade data
- `utils/hardware_advisor.py` — detects CPU/RAM, recommends safe multiprocessing config

Training output: checkpoints in `data/rl_runs/`, MLflow metadata, TensorBoard logs in `data/rl_tensorboard_logs/`

> **NOTE (macOS 12):** Training is CPU-only (no CUDA). Reduce episode counts significantly or load a pre-trained checkpoint from the Windows machine. Monitor RAM usage via `hardware_advisor.py` recommendations.

> **TODO:** No module-level README or training guide. The RL training pipeline is the most complex subsystem and the hardest to onboard without documentation.

---

## ga_optimizer_module/

**Responsibility:** Genetic Algorithm (PyGAD) that evolves trading parameter combinations against historical OHLCV backtests.

Entry point: `python ga_optimizer_module/ga_optimizer.py`

| File | Purpose |
|------|---------|
| `ga_optimizer.py` | Main GA loop; evolves parameter genes |
| `ga_backtester.py` | Runs backtest simulation for a given parameter set |
| `ga_prepare_dataset.py` | Prepares historical OHLCV data for backtesting |
| `ga_ingest_data.py` | Ingests data from PostgreSQL into GA-ready format |
| `ga_dashboard.py` | Visualization dashboard for GA results |

Output: best parameter set saved as JSON; loaded via `python main.py --params-file <path>`

> **TODO:** GA and RL each have their own data ingestion pipeline (`ga_prepare_dataset.py` vs `rl_agent_module/feature_engineering/`). These pipelines are partially duplicated. A future "Unified Feature Store" should consolidate them.

---

## web_app/

**Responsibility:** Flask dashboard on port 5001 for human monitoring. Separate from the FastAPI C&C hub on port 8000.

Entry point: `python web_app/app.py`

This is a read-only monitoring UI — it does not issue commands to the bot. Commands go through the FastAPI hub (`api/`) or Telegram.

---

## socials_processor.py + trade_processor.py

**Responsibility:** Supporting async processors for the main trading loop.

- `SocialsProcessor` — fetches and scores Website/Telegram/Twitter presence for new tokens; writes scores to `socials_scores` table
- `trade_worker()` in `trade_processor.py` — buffers up to 100 trade events (or 5 s timeout), then bulk-inserts to DB

---

## Supporting files

| File | Purpose |
|------|---------|
| `state_manager.py` | `GlobalState` singleton — shared state for all async tasks |
| `utils.py` | General helper functions (25 KB) |
| `bot_logger.py` | `rich`-based logging setup; file rotation |
| `db_setup_maintenance.py` | Manual schema/index management utility (run standalone) |
| `telegram_interface.py` | Telegram bot integration for alerts and commands (1,015 lines) |

> **TODO:** No test suite exists for any module. Use `TRADING_MODE="simulate"` in `config/config.py` for all manual verification.
```

- [ ] **Step 2: Verify**

Run: `ls -lh docs/MODULES.md && grep -c "TODO\|NOTE\|WARNING" docs/MODULES.md`
Expected: file shown, count ≥ 4

- [ ] **Step 3: Commit**

```bash
git add docs/MODULES.md
git commit -m "docs: add MODULES.md with per-subsystem reference and known gaps"
```

---

### Task 4: Create `docs/DEVELOPMENT.md`

**Files:**
- Create: `docs/DEVELOPMENT.md`

- [ ] **Step 1: Write the file**

```markdown
# Development Setup & Workflow

## Prerequisites

- Python 3.11+
- PostgreSQL 12+ with the `pgvector` extension
- Ollama (for AI features): https://ollama.ai — run `ollama serve` before starting the bot
- Redis (optional but recommended): non-critical, bot continues without it

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up PostgreSQL + pgvector
# Install pgvector for your PostgreSQL version, then:
psql -U postgres -c "CREATE DATABASE your_db_name;"
psql -U postgres -d your_db_name -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 4. Copy and fill in .env
cp .env_sample .env
# Edit .env — see variable reference below

# 5. (Optional) Start Ollama for AI features
ollama serve
ollama pull mistral   # or whichever model you use

# 6. Run the bot in simulate mode
python main.py
```

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DB_USER` | Yes | — | PostgreSQL username |
| `DB_PASSWORD` | Yes | — | PostgreSQL password |
| `DB_HOST` | Yes | `localhost:5432` | PostgreSQL host:port |
| `DB_DATABASE` | Yes | — | Database name |
| `SOLANA_PRIVATE_KEY` | Live only | — | Wallet private key for on-chain transactions |
| `TG_BOT_TOKEN` | Optional | — | Telegram bot token for alerts |
| `TG_CHAT_ID` | Optional | — | Telegram chat ID for alerts |

> **TODO:** Several optional variables are not in `.env_sample` — notably `REDIS_HOST`, `REDIS_PORT`, Ollama endpoint, and logging overrides. Until `requirements-dev.txt` and a config schema exist, check `config/config.py` for the full list of hardcoded defaults.

## Configuration Hierarchy

Three levels; later levels override earlier ones:

**Level 1 — `config/config.py`** (static defaults)
Edit the file to change defaults. Requires restart. Contains ~80 parameters: trading thresholds, profit margins, stop-loss levels, AI flags, logging levels. Example:
```python
TRADING_MODE = "simulate"          # "simulate" | "paper_trading" | "live"
AI_DECISION_MAKING_ENABLED = True
AI_DECISION_THRESHOLD = 50.0       # min confidence % to act on AI advice
```

**Level 2 — `data/dynamic_config.json`** (runtime overrides)
Polled every few seconds; changes apply without restart. Use this to toggle AI on/off, change buy amounts, etc., while the bot is running.

**Level 3 — CLI flags** (ML-optimized runs)
```bash
python main.py --params-file path/to/ga_params.json   # load GA-optimized parameters
python main.py --rl-agent-path path/to/checkpoint     # load trained RL agent
```
CLI flags override both Level 1 and Level 2 for the affected parameters.

Additional configs: `config/ga_config.py` (GA hyperparameters), `config/rl_config.py` (RL/PPO hyperparameters).

## Trading Modes

Always develop and test in `simulate` mode. Never commit code with `TRADING_MODE` set to `live`.

| Mode | What it does |
|------|-------------|
| `simulate` | Records trades to DB as if real; no external calls for execution. Safe for development. |
| `paper_trading` | Calls live execution APIs, signs transactions, but does NOT submit to network. Simulates fills. |
| `live` | Full live trading — real on-chain transactions via PumpPortal or GMGN. Requires `SOLANA_PRIVATE_KEY`. |

## CLI Options

```bash
python main.py                    # normal start
python main.py --cleanup          # wipe DB before start (DESTRUCTIVE — dev only)
python main.py --backup           # snapshot DB before start
python main.py --params-file      # load GA-optimized parameters from JSON
python main.py --rl-agent-path    # load trained RL agent checkpoint
```

## Optional Subsystems

```bash
python ga_optimizer_module/ga_optimizer.py   # Genetic Algorithm parameter optimizer
python rl_main.py                            # RL training interactive menu
python web_app/app.py                        # Flask dashboard (port 5001)
python db_setup_maintenance.py               # Schema/index management utility
tensorboard --logdir ./data/rl_tensorboard_logs/   # RL training monitor
```

## Logging

- Console: `rich`-formatted with emoji markers (may not render in non-TTY environments)
- Files: rotating daily logs in `log/`
- Levels: `_LOG_LEVEL_CONSOLE` and `_LOG_LEVEL_FILE` in `config/config.py`
- AI traces: set `AI_LOG_VERBOSE = True` in `config/config.py` for full LLM input/output

## macOS 12 Notes

> **NOTE (macOS 12):** Torch 2.2.2 is installed with a native macOS build but is CPU-only — no CUDA/GPU acceleration. The Windows asyncio event loop policy guard at `trading_bot.py:1651` (`asyncio.WindowsSelectorEventLoopPolicy`) is platform-conditional and must remain.

> **NOTE (macOS 12):** RL training will be significantly slower without CUDA. Use `hardware_advisor.py` recommendations for multiprocessing limits, or load a pre-trained checkpoint from the original Windows machine.

> **TODO:** No `pytest` setup. No `requirements-dev.txt`. These are needed before writing any automated tests. `asyncpg` also appears twice in `requirements.txt` (lines 4 and 31) — remove the duplicate.
```

- [ ] **Step 2: Verify**

Run: `ls -lh docs/DEVELOPMENT.md && grep -c "TODO\|NOTE\|WARNING" docs/DEVELOPMENT.md`
Expected: file shown, count ≥ 3

- [ ] **Step 3: Commit**

```bash
git add docs/DEVELOPMENT.md
git commit -m "docs: add DEVELOPMENT.md with full setup, config hierarchy, and macOS notes"
```

---

### Task 5: Create `docs/ROADMAP.md`

**Files:**
- Create: `docs/ROADMAP.md`

- [ ] **Step 1: Write the file**

```markdown
# Roadmap & Known Gaps

This document tracks where the codebase is today vs. where it needs to go. When in doubt about whether something is implemented, start here.

## Platform History

- **Original platform:** Windows 10 (development + testing)
- **Current platform:** macOS 12 (old iMac — temporary, CPU-only, no CUDA)
- **Target platform:** macOS/Linux (production)

Windows-specific guards exist in the code (asyncio event loop policy, subprocess creation flags) — these must remain for portability.

## Known Gaps — By Priority

### 1. Test Suite (Critical)
No `pytest` setup. No `requirements-dev.txt`. Zero test coverage across all modules.
- **Impact:** No safety net for refactoring; bugs in async logic are invisible until runtime.
- **Fix:** Add `pytest`, `pytest-asyncio`, `pytest-mock`. Start with unit tests for `trading_logic.py` sell decision paths.

### 2. Type Hints (High)
~35–40% of functions have return type annotations. `database_handler.py` and `trading_logic.py` are the worst offenders.
- **Impact:** Poor IDE support, harder to reason about data flow, mypy can't help.
- **Fix:** Enable `mypy` in strict mode progressively. Start with `state_manager.py` and `trading_logic.py`.

### 3. GlobalState → Dependency Injection (High)
`GlobalState.get_instance()` is called everywhere. This makes unit testing nearly impossible (can't mock/inject state).
- **Impact:** Circular dependencies, difficult to test individual components.
- **Fix:** Pass `state` explicitly to constructors instead of calling `get_instance()` inside methods. `TradingBot.__init__` already does this correctly — propagate the pattern.

### 4. Split Monolithic Files (High)
Three files that are too large to reason about:
- `database_handler.py` — 2,801 lines (migrations + CRUD + analytics + connection management)
- `trading_bot.py` — 1,682 lines (orchestration + buy logic + sell logic + AI lifecycle + IPC)
- `trading_logic.py` — 1,127 lines (position management + trend reversal + stop-loss logic)

**Do not add new methods to these files.** Create new focused files instead.

### 5. Structured Logging (Medium)
Current logging uses `rich` with emoji markers. Emoji breaks log aggregation tools and non-TTY environments.
- **Fix:** Add JSON structured logging as a second handler. Keep `rich` for development console.

### 6. Redis Streams for IPC (Medium)
File-based IPC (`data/bot_command.txt`) has no delivery guarantee and races under concurrent writers.
- **Fix:** Use Redis Streams for commands (already partially used elsewhere). See `_Resources/v2_refactoring_plan.md` for full design.

### 7. Config Schema Validation (Low)
No Pydantic schema for config. Missing variables silently get Python defaults.
- **Fix:** Add `config/schemas.py` with Pydantic models. Validate on startup.

### 8. Duplicate Data Pipelines (Low)
GA (`ga_prepare_dataset.py`) and RL (`rl_agent_module/feature_engineering/`) each have their own data ingestion pipeline. They are partially duplicated and can diverge.
- **Fix:** Unified Feature Store (see `_Resources/v2_refactoring_plan.md`, Section 3).

## Don't-Touch List

These must not be changed without careful cross-codebase review:

| Thing | Why |
|-------|-----|
| `TRADING_MODE = "simulate"` in committed code | Prevents accidental live trading |
| SQL migration numbering (`01_` through `18_`) | Tracking table uses filenames as keys |
| `asyncio.WindowsSelectorEventLoopPolicy` guards | Required for Windows portability |
| `pgvector` table schema in `sql/17_create_ai_decision_memory.sql` | Embedding dimension changes break the index |

## Architecture Vision

A detailed v3.0 architecture proposal (event-driven, Redis-integrated, strategy-as-plugin) is in `_Resources/v2_refactoring_plan.md`. This is aspirational — none of it is implemented yet. The document is a useful reference for the direction of major refactoring.
```

- [ ] **Step 2: Verify**

Run: `ls -lh docs/ROADMAP.md && grep -c "TODO\|Critical\|High\|Medium" docs/ROADMAP.md`
Expected: file shown, count ≥ 4

- [ ] **Step 3: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs: add ROADMAP.md with prioritized gap list and don't-touch list"
```

---

### Task 6: Restructure `CLAUDE.md` as lean index

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace the entire file content**

The new content removes the detailed async task table, config hierarchy, AI flow, ML descriptions, and external deps table (all now in `docs/`). It keeps the Commands block, startup path, and adds Key Invariants + Navigation index.

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env_sample .env  # fill in DB_USER, DB_PASSWORD, DB_HOST, DB_DATABASE, SOLANA_PRIVATE_KEY, TG_BOT_TOKEN, TG_CHAT_ID

# Run the main trading bot (FastAPI C&C Hub on port 8000)
python main.py
python main.py --cleanup      # wipe DB before start (destructive)
python main.py --backup       # snapshot DB before start
python main.py --params-file  # load GA-optimized parameters
python main.py --rl-agent-path  # load trained RL agent

# Optional subsystems
python ga_optimizer_module/ga_optimizer.py   # Genetic Algorithm parameter optimizer
python rl_main.py                            # RL training interactive menu
python web_app/app.py                        # Flask dashboard (port 5001)
python db_setup_maintenance.py               # Schema/index management
tensorboard --logdir ./data/rl_tensorboard_logs/  # RL training monitor

# No test suite — use TRADING_MODE="simulate" in config for safe testing
```

## Architecture Overview

Pump Trader v3.0 is an async Python trading bot for Solana meme coins on pump.fun, combining rule-based logic, AI-advised decisions (Ollama LLM + pgvector RAG), and optional ML parameter optimization (GA + RL).

**Startup path:** `main.py` → FastAPI/Uvicorn → `api/main.py` → `BotService` → `TradingBot` (`trading_bot.py`) → spawns all concurrent async tasks via `TradingBot.run()`.

## Key Invariants

Rules that must never be violated regardless of context:

- **GlobalState only.** Never introduce module-level mutable state. Add fields to `GlobalState` in `state_manager.py` and pass `state` explicitly to constructors.
- **Always simulate.** Always develop and test in `TRADING_MODE = "simulate"`. Never commit live-mode changes.
- **No new methods on `database_handler.py`.** It is already 2,801 lines. Create new focused repository files for new DB operations.
- **macOS 12 constraint.** Torch is CPU-only (no CUDA). The `asyncio.WindowsSelectorEventLoopPolicy()` guard at `trading_bot.py:1651` must remain — it is platform-conditional and required for Windows portability.
- **Never renumber migrations.** SQL migration files in `sql/` use filenames as tracking keys. Renaming or reordering breaks idempotent startup.

## Navigation

| Task | Read this |
|------|-----------|
| Understanding system design and async tasks | `docs/ARCHITECTURE.md` |
| Working with the database or migrations | `docs/DATABASE.md` |
| Adding or modifying a module | `docs/MODULES.md` |
| Setting up the environment or understanding config | `docs/DEVELOPMENT.md` |
| Understanding what's not yet implemented | `docs/ROADMAP.md` |
```

- [ ] **Step 2: Verify size**

Run: `wc -c CLAUDE.md`
Expected: output shows fewer than 2500 bytes (e.g., `2341 CLAUDE.md`)

- [ ] **Step 3: Verify docs/ folder is complete**

Run: `ls -lh docs/`
Expected: 5 files listed — `ARCHITECTURE.md`, `DATABASE.md`, `DEVELOPMENT.md`, `MODULES.md`, `ROADMAP.md` — plus `superpowers/` directory

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: restructure CLAUDE.md as lean index with invariants and navigation"
```

---

### Task 7: Final verification

**Files:** (no changes)

- [ ] **Step 1: Check CLAUDE.md size**

Run: `wc -c CLAUDE.md`
Expected: < 2,500 bytes

- [ ] **Step 2: Check all docs/ files have TODO annotations**

Run: `for f in docs/ARCHITECTURE.md docs/DATABASE.md docs/MODULES.md docs/DEVELOPMENT.md docs/ROADMAP.md; do echo "$f: $(grep -c 'TODO\|WARNING\|NOTE' $f) annotations"; done`
Expected: each file shows ≥ 1 annotation

- [ ] **Step 3: Verify design spec was committed**

Run: `ls -lh docs/superpowers/specs/ docs/superpowers/plans/`
Expected: `2026-04-29-documentation-layer-design.md` and `2026-04-29-documentation-layer.md` listed

- [ ] **Step 4: Final commit with spec and plan files**

```bash
git add docs/superpowers/
git commit -m "docs: add design spec and implementation plan to docs/superpowers/"
```
