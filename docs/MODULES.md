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
