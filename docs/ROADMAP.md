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
