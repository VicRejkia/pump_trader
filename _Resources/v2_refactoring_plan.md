# **Project Refactor: `pump_trader` v3.0 Architecture**

## 1. Executive Summary: The Goal

The `pump_trader` project is a sophisticated Solana-based meme coin trading bot integrating rule-based logic, genetic algorithm (GA) optimization, reinforcement learning (RL), and generative AI decision-making. The current codebase, while functional, suffers from decentralization: multiple entry points (`main.py`, `rl_main.py`, `ga_optimizer.py`), fragile inter-process communication (e.g., `bot_command.txt`), duplicated data pipelines, and monolithic classes (e.g., `trading_bot.py`, `database_handler.py`). This leads to maintenance challenges, inconsistent data handling, and limited scalability.

This v3.0 refactor enhances the architecture with improved modularity, robustness, and extensibility. Key enhancements include:

- **Enhanced C&C Hub:** Add authentication, metrics, and hybrid REST/GraphQL API for flexibility.
- **Advanced Strategy Pattern:** Introduce dynamic plugin loading and simulation modes.
- **Optimized Data Pipeline:** Add real-time streaming and versioning to the feature store.
- **Redis Integration:** Use as a message queue and cache for live events, token data, market data, and portfolio management, with synchronization back to PostgreSQL (your 55GB primary database for historical data).
- **Hybrid Config Management:** Static vars in YAML/Pydantic; dynamics in PostgreSQL with Redis caching/pub/sub for runtime changes.
- **Creative Additions:** Message queuing for decoupled events and a testing framework.

The result: A **microservice-inspired, event-driven architecture** that's testable, deployable, and ready for production trading while supporting research (GA/RL). This directly addresses your concerns: centralization via the C&C server, performance via Redis caching (e.g., sub-millisecond access for live data), and config organization via the hybrid method to prevent "losing track" of variables.

-----

## 2. The Four Core Architectural Principles (The "Why")

This refactor builds on four core concepts to address the project's challenges.

### 1. The "Command & Control" (C&C) Hub (with Real-time WebSocket and Redis Queuing)

- **The Problem:** No central entry point; components communicate via fragile files like `bot_command.txt`.
- **The Solution:** A FastAPI web server as the single entry point, hosting REST API for commands (e.g., `/control/start`) and WebSockets for events (e.g., `/ws/updates`). Integrate Redis as a message queue for durable, asynchronous events (e.g., trade executions) and pub/sub broadcasting. Redis ensures events are queued and replayable (e.g., if a client disconnects), while WebSockets handle ephemeral UI updates. Add API authentication (JWT) for security and Prometheus metrics for monitoring (e.g., trade volume, bot health).
- **The Benefit:** Centralizes control, ensures no events are lost, and supports real-time interactivity. Redis offloads transient data from PostgreSQL, providing sub-millisecond access for live operations like token/market data caching.

### 2. The "Strategy-as-a-Plugin" Model

- **The Problem:** Decision logic is scattered across rule-based (`trading_logic.py`), AI (`ai_decision_module`), and RL (`rl_agent_module`), making it hard to manage or extend.
- **The Solution:** Define an `ITradingStrategy` interface for all "brains" (e.g., `async def get_buy_decision(...)`). Create wrappers: `RuleBasedStrategy`, `GenerativeAIStrategy`, `RLAgentStrategy`, and a `HybridStrategy` for orchestration (e.g., "Ask RL, confirm with AI"). Make strategies dynamically loadable via a plugin registry (using `importlib`). Add a "Simulation Mode" where strategies run on historical data without real trades. Include strategy-specific metrics (e.g., win rate) tracked via the C&C hub.
- **The Benefit:** Makes decision logic modular and configurable. Redis can cache strategy inputs (e.g., live market data) for faster evaluations. Users can add new strategies (e.g., a ML-based one) without restarting the bot.

### 3. The "Unified Feature Store" (with Redis Caching)

- **The Problem:** Duplicative data pipelines in GA (`ga_prepare_dataset.py`), RL (`prepare_rl_dataset.py`), and AI (`ai_data_assembler.py`), leading to inconsistency and inefficiency.
- **The Solution:** A master ETL script (`build_feature_store.py`) queries PostgreSQL once, pre-computes features (OHLCV, TA indicators, social scores), and saves to a central Parquet cache with Delta Lake for versioning and incremental updates. Add a real-time streaming layer via Redis streams for live features (e.g., updating TA indicators as trades arrive). ETL is schedulable via APScheduler.
- **The Benefit:** Ensures consistency across modules (GA/RL/AI train on the same data). Redis provides instant access to "hot" data, reducing PostgreSQL load while maintaining historical integrity through write-through syncing.

### 4. The "Resilient Data Pipeline" Principle

- **The Problem:** Live operations strain the large PostgreSQL database; no fault tolerance for transients like API failures.
- **The Solution:** Hybrid database approach: PostgreSQL for durable history, Redis for caching live events/data (e.g., token prices as hashes: `redis.hset("token:mint", {"price": 0.001})`). Implement circuit breakers (via `tenacity` lib) for external APIs (e.g., DexScreener) and auto-retries for tasks. Use Redis pub/sub to trigger syncs and events (e.g., new data → cache → async insert to PostgreSQL).
- **The Benefit:** Fault-tolerant system with high performance. Data flows from Redis (buffer for speed) to PostgreSQL (archive for persistence) asynchronously. This complements your 55GB DB without adding bloat.

-----

## 3. Target Architecture (The "What")

This structure refines the codebase with Redis integration and hybrid configs (tagged as `ENHANCED`, `NEW`, or `REFINED` where relevant).

```dir
.
├── api/                           <-- ENHANCED (C&C Hub with GraphQL, Metrics, Auth, Redis)
│   ├── __init__.py
│   ├── main.py                    <-- REFINED (Adds Redis, message queue)
│   ├── auth.py                    <-- NEW (JWT authentication)
│   ├── metrics.py                 <-- NEW (Prometheus exporter)
│   └── endpoints/                 <-- REFINED (Hybrid REST/GraphQL)
│       ├── __init__.py
│       ├── bot_control.py         <-- REFINED (Queues commands in Redis)
│       ├── charts.py              <-- REFINED (Supports live streaming from Redis)
│       ├── config.py              <-- NEW (CRUD for dynamic configs via DB/Redis)
│       ├── ga_module.py           <-- REFINED (Async job queuing via Redis)
│       ├── rl_module.py           <-- REFINED (Async job queuing via Redis)
│       └── features.py            <-- NEW (Query unified feature store/Redis)
│
├── config/                        <-- ENHANCED (Hybrid: YAML + Pydantic + DB/Redis)
│   ├── __init__.py
│   ├── schemas.py                 <-- NEW (Pydantic models for validation)
│   ├── loader.py                  <-- NEW (Hybrid load from YAML/DB/Redis)
│   ├── app.yaml                   <-- NEW (Static core configs)
│   ├── ga.yaml                    <-- NEW (Static GA configs)
│   └── rl.yaml                    <-- NEW (Static RL configs)
│
├── connectors/                    <-- REFINED (Add circuit breakers)
│   ├── __init__.py
│   ├── dexscreener_api.py
│   ├── rugcheck_handler.py
│   ├── sol_price_api.py
│   ├── telegram_monitor.py
│   └── websocket_handler.py
│
├── core/                          <-- ENHANCED (Add resilience with Redis)
│   ├── __init__.py
│   ├── bot_service.py             <-- REFINED (Task supervision with retries, Redis client)
│   ├── broadcaster.py             <-- REFINED (Hybrid with Redis queue)
│   ├── database.py                <-- REFINED (PostgreSQL connections)
│   ├── state_manager.py           <-- (Unchanged)
│   ├── repositories/              <-- REFINED (Add config_repository.py)
│   │   ├── __init__.py
│   │   ├── config_repository.py   <-- NEW (DB ops for dynamic configs)
│   │   ├── ai_memory_repository.py
│   │   ├── ga_repository.py
│   │   ├── portfolio_repository.py
│   │   ├── token_repository.py
│   │   └── ... (etc.)
│   └── tasks/                     <-- REFINED (Add error handling, config watcher)
│       ├── __init__.py
│       ├── config_watcher.py      <-- NEW (Monitors Redis for config changes)
│       ├── ai_tasks.py
│       ├── buy_checker.py
│       ├── sell_checker.py
│       ├── ipc_listeners.py
│       ├── status_updater.py
│       └── ... (trade_worker, sol_price_updater, etc.)
│
├── data/                          <-- (Unchanged, phased out for Redis/DB)
│   └── ...
│
├── etl/                           <-- ENHANCED (Versioning + Streaming via Redis)
│   ├── __init__.py
│   ├── build_feature_store.py     <-- REFINED (Incremental + Delta Lake, Redis live updates)
│   └── streamer.py                <-- NEW (Real-time feature updates to Redis)
│
├── integrations/                  <-- ENHANCED (Add more clients)
│   ├── __init__.py
│   ├── telegram_bot.py            <-- REFINED (Subscribes to Redis pub/sub)
│   └── slack_bot.py               <-- NEW (Optional alerting via Redis)
│
├── modules/                       <-- REFINED (Standardize interfaces, consume Redis)
│   ├── ai/                        <-- (From ai_decision_module/, consume feature store)
│   │   └── ...
│   ├── ga/                        <-- (From ga_optimizer_module/, consume feature store)
│   │   └── ...
│   └── rl/                        <-- (From rl_agent_module/, consume feature store)
│       └── ...
│
├── strategies/                    <-- ENHANCED (Dynamic loading)
│   ├── __init__.py
│   ├── base.py                    <-- (ITradingStrategy interface)
│   ├── generative_ai.py           <-- (Wraps ai_decision_maker)
│   ├── hybrid.py                  <-- REFINED (Configurable orchestration)
│   ├── rl_agent.py                <-- (Wraps rl_model_server)
│   ├── rule_based.py              <-- (From trading_logic.py)
│   └── plugin_registry.py         <-- NEW (Dynamic strategy loader)
│
├── ui/                            <-- ENHANCED (Add interactivity)
│   ├── __init__.py
│   └── dashboard.py               <-- REFINED (Streamlit with WebSocket/Redis sub)
│
├── tests/                         <-- NEW (Pytest framework)
│   ├── __init__.py
│   ├── test_strategies.py         <-- NEW
│   ├── test_configs.py            <-- NEW
│   ├── test_etl.py                <-- NEW
│   └── ... (others)
│
├── main.py                        <-- (Launches C&C server)
├── bot_logger.py                  <-- ENHANCED (Structured logging)
└── utils.py                       <-- (Unchanged)
```

-----

## 4. Module-by-Module Refactoring Plan (The "How" & "Why")

### 1. `main.py` (Root) & `api/` (C&C Hub)

- **Deletions:** Old `main.py`, `telegram_interface.py`, `generate_chart.py`.
- **Refactoring:**
  - **`main.py` (New):** Launches FastAPI: `uvicorn.run("api.main:app")`.
  - **`api/main.py` (Refined):** Initializes app, Redis client (`redis.Redis(host='localhost', port=6379)`), `BotService`. Adds GraphQL (via Strawberry: pip install strawberry-graphql) for complex queries (e.g., features + charts). Defines WebSocket; includes routers.
  - **`auth.py` (New):** JWT via `fastapi-jwt-auth` (pip install) for endpoints.
  - **`metrics.py` (New):** Expose `/metrics` with `prometheus-fastapi-instrumentator` (pip install) for trades/latencies.
  - **`api/endpoints/` (Refined):**
    - **`bot_control.py`:** `POST /control/stop_buying` queues in Redis.
    - **`charts.py`:** `GET /charts/ohlcv` queries PostgreSQL/Redis, processes with pandas-ta, returns JSON.
    - **`config.py` (New):** CRUD for dynamics (update DB/Redis, publish event).
    - **`features.py` (New):** GraphQL resolvers query feature store/Redis.
- **Why:** Centralizes control; Redis queuing ensures reliability; GraphQL for flexible queries; metrics for observability.

### 2. `config/` (Hybrid Config Management)

- **Refactoring:**
  - **`schemas.py` (New):** Pydantic models (e.g., `AppConfig` with validators/descriptions).
  - **`loader.py` (New):** Hybrid load: YAML for statics, PostgreSQL/Redis for dynamics; merge/validate.
  - YAML Files: Migrate `config.py` etc. to hierarchical YAML.
  - DB Table: Add to `sql/`:

    ```sql
    CREATE TABLE configurations (
        key TEXT PRIMARY KEY,
        value JSONB NOT NULL,
        type TEXT,
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_by TEXT
    );
    ```

  - Repository: `core/repositories/config_repository.py` for SQL ops.
- **Why:** Organizes vars; prevents confusion; DB for persistence/auditing/dashboard; Redis for fast runtime access.

### 3. `connectors/` (External APIs)

- **Refactoring:** Add circuit breakers/retries via `tenacity` (pip install) in each (e.g., `@retry` on API calls).
- **Why:** Resilience against failures (e.g., DexScreener timeouts).

### 4. `core/` (The Bot's Engine)

- **Deletions:** `trading_bot.py`, `database_handler.py`.
- **Refactoring:**
  - **`bot_service.py` (Refined):** Launches tasks with supervision (`asyncio.gather` with try/except); manages Redis.
  - **`broadcaster.py` (Refined):** Queue in Redis first, then WebSocket; subscribe for replays.
  - **`database.py` (Refined):** PostgreSQL pools (use asyncpg for async: pip install).
  - **`repositories/` (Refined):** Split methods; `config_repository.py` for dynamics.
  - **`tasks/` (Refined):** Add try/except with backoff; `config_watcher.py` subscribes to Redis "config_updated".
- **Why:** Breaks monoliths; Redis for caching (e.g., portfolio in hashes); resilience prevents crashes.

### 5. `etl/` (The Data Pipeline)

- **Refactoring:**
  - **`build_feature_store.py` (Refined):** Query PostgreSQL, save versioned Parquet (use deltalake: pip install); push increments to Redis.
  - **`streamer.py` (New):** Listen to DB changes/polling, update Redis streams; async sync to PostgreSQL.
- **Why:** Batch for history (GA/RL); streaming for live (AI decisions); versioning for reproducibility.

### 6. `integrations/` & `ui/` (The Clients)

- **Refactoring:**
  - **`telegram_bot.py` (Refined):** Subscribe to Redis for alerts (fallback to WebSocket).
  - **`slack_bot.py` (New):** Optional, similar to Telegram.
  - **`dashboard.py` (Refined):** Streamlit (pip install streamlit); real-time charts via Altair; edit configs via API (query DB/Redis).
- **Why:** Multi-channel notifications; dashboard as control center with live updates.

### 7. `modules/` (AI/GA/RL)

- **Refactoring:** Standardize to consume feature store/Redis (e.g., GA reads Parquet, caches live in Redis).
- **Why:** Eliminates duplication; consistency.

### 8. `strategies/` (The "Brains")

- **Refactoring:**
  - **`plugin_registry.py` (New):** Scans dir with `importlib` at startup.
  - **`hybrid.py` (Refined):** Load children dynamically from config.
  - Simulation: Add `simulate=True` param.
- **Why:** Extensibility; simulation for testing.

### 9. `tests/` (Testing Framework)

- **Refactoring:** Pytest suites (pip install pytest): configs (validation), strategies (mocks), ETL (data integrity).
- **Why:** Code quality.

-----

## 5. Key Scenarios in the New Architecture

- **Scenario 1: Runtime Config Change:** Dashboard updates threshold → API → DB insert + Redis set + publish → Watcher reloads → Strategies use new value.
- **Scenario 2: Live Token Update:** Websocket event → Redis cache/hash → Publish → Streamer syncs to PostgreSQL.
- **Scenario 3: Buy Decision:** Strategy queries Redis (cache hit) → If miss, PostgreSQL + cache.
- **Scenario 4: Event Broadcast:** Trade → Redis queue/publish → Subscribers (dashboard/Telegram) receive/replay.
- **Scenario 5: GA Run:** API queues in Redis → Worker picks up, consumes feature store → Results to DB/Redis.
