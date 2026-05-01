# GlobalState Dependency Injection — Design Spec

**Phase:** 3A  
**Branch:** new branch from `fix/torch-version-constraint`  
**Date:** 2026-04-30

## Goal

Remove the `GlobalState` singleton and replace all `get_instance()` calls with explicit constructor / parameter injection. This is a prerequisite for Phase 3B (splitting `database_handler.py`) and 3C (splitting `trading_bot.py`), because files that call `get_instance()` internally cannot be tested or refactored in isolation.

## Scope

**In scope:** Path A — the working production path (`trading_bot.py __main__` → `TradingBot` → sub-components).

**Out of scope:** `api/main.py` and the `core/` module it references. That file already fails to import (non-existent `core.bot_service`, `core.database`, `config.loader`) and is a Phase 3B concern.

## Section 1 — `state_manager.py` changes

Remove from `GlobalState`:

- `_instance = None` (class attribute)
- `_lock = asyncio.Lock()` (class-level lock — only used by the singleton guard)
- `get_instance()` classmethod
- `if GlobalState._instance is not None: raise Exception(...)` guard in `__init__`

All fields, queues, events, and instance-level locks stay untouched. `GlobalState()` becomes a plain constructor that can be called multiple times.

## Section 2 — Constructor / parameter injection

### Entry point (`trading_bot.py __main__`, line 1654)

Inside `run_bot_async_wrapper()`, create state before constructing the bot:

```python
state = GlobalState()
bot_instance = TradingBot(
    state=state,
    cleanup=args.cleanup,
    backup=args.backup,
    params_file=args.params_file,
    no_log_rotate=args.no_log_rotate
)
```

Lines 1667–1672 that reference `bot_instance.state` need no change.

### Group A — signature changes

| File | Change |
|------|--------|
| `trading_bot.py:59` | Add `state: GlobalState` as first param to `TradingBot.__init__`; remove `GlobalState.get_instance()` on line 70 |
| `database_handler.py:68` | Add `state: GlobalState` as first param to `DatabaseClient.__init__`; remove `GlobalState.get_instance()` on line 71 |
| `trade_processor.py:15` | Add `state: GlobalState` as first param to `trade_worker()`; remove `GlobalState.get_instance()` on line 19 |
| `ai_decision_module/ai_data_assembler.py:293` | Add `state: GlobalState` as first param to `fetch_comprehensive_token_data()`; replace `GlobalState.get_instance()` at lines 364 and 534 with the param |

### Group B — secondary callers inside `TradingBot`

| Line | Before | After |
|------|--------|-------|
| 833 | `fetch_comprehensive_token_data(self.db_client, mint)` | `fetch_comprehensive_token_data(self.state, self.db_client, mint)` |
| 1515 | `DatabaseClient(config_dict=self.config)` | `DatabaseClient(state=self.state, config_dict=self.config)` |
| 1572 | `trade_worker(self.ws_handler.trade_queue)` | `trade_worker(self.state, self.ws_handler.trade_queue)` |

### Group C — standalone scripts

Each script creates its own `DatabaseClient()` for DB access only and has no shared state. Prepend `state = GlobalState()` before each `DatabaseClient()` call and pass `state` as first argument.

Files:
- `db_setup_maintenance.py:288`
- `generate_chart.py:49`
- `rl_agent_module/etl/prepare_rl_dataset.py:58`
- `web_app/app.py:102, 117`
- `ga_optimizer_module/ga_prepare_dataset.py:61`

`ai_decision_module/ai_data_assembler.py main()` (line 626) already has `state = GlobalState.get_instance()` — change to `GlobalState()`, pass `state` to the local `DatabaseClient()` at line 636 and to `fetch_comprehensive_token_data()` at line 655.

## Section 3 — Entry point detail

The full `__main__` block change is the two lines shown in Section 2 (entry point). No other changes to the `__main__` block are needed.

## Section 4 — Two-commit sequence

### Commit 1 — "add state injection, keep singleton"

Land all Group A, B, C, and entry-point changes. The singleton (`get_instance()`, `_instance`, `_lock`, the `__init__` guard) is **left in place**. The app runs via the updated injection path; no old code breaks because the singleton still compiles.

**Verification checkpoint before Commit 2:**

```bash
# 1. Confirm GlobalState() can be called once without error
python -c "from state_manager import GlobalState; s = GlobalState(); print('ok')"

# 2. No new lint errors
ruff check .

# 3. No new type errors on changed files
mypy trading_bot.py trade_processor.py database_handler.py ai_decision_module/ai_data_assembler.py

# 4. Bot starts in simulate mode
TRADING_MODE=simulate python trading_bot.py
# Expect: startup log lines, no crash; Ctrl-C to stop
```

Only proceed to Commit 2 if all four pass.

### Commit 2 — "delete singleton"

Apply Section 1 changes (remove `_instance`, `_lock`, `get_instance()`, `__init__` guard).

Pre-commit checks:

```bash
# Must return zero hits
grep -r "get_instance" . --include="*.py"

# Confirm two independent GlobalState() calls now work freely
python -c "from state_manager import GlobalState; s1 = GlobalState(); s2 = GlobalState(); print('ok')"
```

## Known pre-existing issues (out of scope)

- `api/main.py:58` passes `config=config` but `DatabaseClient.__init__` expects `config_dict` — existing bug, not introduced by this work.
- `api/main.py` imports `core.bot_service`, `core.database`, `config.loader` — none exist; already broken before Phase 3A.
