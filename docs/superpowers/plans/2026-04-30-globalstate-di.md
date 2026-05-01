# GlobalState Dependency Injection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the `GlobalState` singleton and replace all `get_instance()` calls with explicit constructor/parameter injection across Path A (the working production path).

**Architecture:** Two-commit strangler-fig — Commit 1 adds `state` params everywhere while the singleton remains compilable; Commit 2 deletes the singleton machinery. After Commit 1, every call site passes state explicitly; `get_instance()` is never invoked at runtime.

**Tech Stack:** Python asyncio, `state_manager.GlobalState`, `ruff`, `mypy`

---

## File Map

| File | What changes |
|------|-------------|
| `database_handler.py` | Add `state: GlobalState` as first param to `DatabaseClient.__init__`; remove `get_instance()` call |
| `trading_bot.py` | Add `state: GlobalState` to `TradingBot.__init__`; update internal callers at lines 833, 1515, 1572; update `__main__` entry |
| `trade_processor.py` | Add `state: GlobalState` as first param to `trade_worker()` |
| `ai_decision_module/ai_data_assembler.py` | Add `state: GlobalState` to `fetch_comprehensive_token_data()`; update callers in same file; update `main()` |
| `db_setup_maintenance.py` | Add import + `state = GlobalState()` before `DatabaseClient()` |
| `generate_chart.py` | Add import + `state = GlobalState()` before `DatabaseClient()` |
| `rl_agent_module/etl/prepare_rl_dataset.py` | Add import + `state = GlobalState()` before `DatabaseClient()` |
| `web_app/app.py` | Add import + `state = GlobalState()` before each `DatabaseClient()` |
| `ga_optimizer_module/ga_prepare_dataset.py` | Add import + `state = GlobalState()` before `DatabaseClient()` |
| `state_manager.py` | **Commit 2 only:** Remove `_instance`, class-level `_lock`, `get_instance()`, singleton guard in `__init__`; update docstring |

---

### Task 1: Create branch

**Files:** none

- [ ] **Step 1: Create and check out branch**

```bash
git checkout fix/torch-version-constraint
git checkout -b feature/phase3a-globalstate-di
```

- [ ] **Step 2: Verify starting point**

```bash
git log --oneline -3
# Should show the docs commit for the design spec at the top
```

---

### Task 2: Fix `DatabaseClient` and all its callers (Commit A)

**Files:**
- Modify: `database_handler.py:68-71`
- Modify: `trading_bot.py:1515`
- Modify: `ai_decision_module/ai_data_assembler.py:636`
- Modify: `db_setup_maintenance.py` (import + line 288)
- Modify: `generate_chart.py` (import + line 49)
- Modify: `rl_agent_module/etl/prepare_rl_dataset.py` (import + line 58)
- Modify: `web_app/app.py` (import + lines 102, 117)
- Modify: `ga_optimizer_module/ga_prepare_dataset.py` (import + line 61)

**Context:** The singleton stays untouched in this commit. Standalone scripts will call `GlobalState()` directly (not `get_instance()`), which works because the singleton guard only raises when `_instance is not None` — and standalone scripts never call `get_instance()` to set `_instance`.

- [ ] **Step 1: Update `DatabaseClient.__init__` signature**

In `database_handler.py`, replace lines 68-71:

```python
# Before
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict
        self.pool = None
        self.state = GlobalState.get_instance()

# After
    def __init__(self, state: GlobalState, config_dict: Optional[dict] = None):
        self.state = state
        self.config = config_dict
        self.pool = None
```

- [ ] **Step 2: Update `DatabaseClient` caller in `trading_bot.py`**

In `trading_bot.py`, line 1515:

```python
# Before
            self.db_client = DatabaseClient(config_dict=self.config)

# After
            self.db_client = DatabaseClient(state=self.state, config_dict=self.config)
```

- [ ] **Step 3: Update `DatabaseClient` caller in `ai_data_assembler.py`**

In `ai_decision_module/ai_data_assembler.py`, line 636:

```python
# Before
    db = DatabaseClient(config_dict=loaded_config)

# After
    db = DatabaseClient(state=state, config_dict=loaded_config)
```

Note: `state` is already defined at line 626 as `GlobalState.get_instance()` — that stays unchanged until Task 5.

- [ ] **Step 4: Update `db_setup_maintenance.py`**

Add import after the existing `from database_handler import DatabaseClient` line (~line 20):

```python
from state_manager import GlobalState
```

Then update line 288:

```python
# Before
    db_client = DatabaseClient()

# After
    state = GlobalState()
    db_client = DatabaseClient(state=state)
```

- [ ] **Step 5: Update `generate_chart.py`**

Add import inside the `try` block with the other project imports (~line 40, after `from database_handler import DatabaseClient`):

```python
from state_manager import GlobalState
```

Then update lines 48-49:

```python
# Before
setup_logging()
db_client = DatabaseClient()

# After
setup_logging()
state = GlobalState()
db_client = DatabaseClient(state=state)
```

- [ ] **Step 6: Update `rl_agent_module/etl/prepare_rl_dataset.py`**

Locate where `from database_handler import DatabaseClient` is imported and add after it:

```python
from state_manager import GlobalState
```

Then update line 58:

```python
# Before
            db_client = DatabaseClient()

# After
            state = GlobalState()
            db_client = DatabaseClient(state=state)
```

- [ ] **Step 7: Update `web_app/app.py`**

Add import inside the `try` block after `from database_handler import DatabaseClient` (~line 18):

```python
from state_manager import GlobalState
```

Then update line 102:

```python
# Before
    db = DatabaseClient()

# After
    state = GlobalState()
    db = DatabaseClient(state=state)
```

And line 117:

```python
# Before
    db = DatabaseClient()

# After
    state = GlobalState()
    db = DatabaseClient(state=state)
```

- [ ] **Step 8: Update `ga_optimizer_module/ga_prepare_dataset.py`**

Add import after `from database_handler import DatabaseClient` (~line 31):

```python
from state_manager import GlobalState
```

Then update line 61:

```python
# Before
        db_client = DatabaseClient()

# After
        state = GlobalState()
        db_client = DatabaseClient(state=state)
```

- [ ] **Step 9: Quick lint check**

```bash
ruff check database_handler.py trading_bot.py ai_decision_module/ai_data_assembler.py \
  db_setup_maintenance.py generate_chart.py rl_agent_module/etl/prepare_rl_dataset.py \
  web_app/app.py ga_optimizer_module/ga_prepare_dataset.py
# Expected: no errors
```

- [ ] **Step 10: Commit**

```bash
git add database_handler.py trading_bot.py ai_decision_module/ai_data_assembler.py \
  db_setup_maintenance.py generate_chart.py rl_agent_module/etl/prepare_rl_dataset.py \
  web_app/app.py ga_optimizer_module/ga_prepare_dataset.py
git commit -m "refactor: inject state into DatabaseClient and update all callers"
```

---

### Task 3: Fix `trade_worker` and its caller (Commit B)

**Files:**
- Modify: `trade_processor.py:15,19`
- Modify: `trading_bot.py:1572`

- [ ] **Step 1: Update `trade_worker` signature**

In `trade_processor.py`, lines 15 and 19:

```python
# Before
async def trade_worker(trade_queue: asyncio.Queue):
    """
    Processes trade messages from the provided queue and writes them in batches to the database.
    """
    state = GlobalState.get_instance()

# After
async def trade_worker(state: GlobalState, trade_queue: asyncio.Queue):
    """
    Processes trade messages from the provided queue and writes them in batches to the database.
    """
```

- [ ] **Step 2: Update `trade_worker` caller in `trading_bot.py`**

In `trading_bot.py`, line 1572:

```python
# Before
            asyncio.create_task(trade_worker(self.ws_handler.trade_queue), name="trade_worker"),

# After
            asyncio.create_task(trade_worker(self.state, self.ws_handler.trade_queue), name="trade_worker"),
```

- [ ] **Step 3: Quick lint check**

```bash
ruff check trade_processor.py trading_bot.py
# Expected: no errors
```

- [ ] **Step 4: Commit**

```bash
git add trade_processor.py trading_bot.py
git commit -m "refactor: inject state into trade_worker and update caller"
```

---

### Task 4: Fix `fetch_comprehensive_token_data` and its callers (Commit C)

**Files:**
- Modify: `ai_decision_module/ai_data_assembler.py:293,364,534,655`
- Modify: `trading_bot.py:833`

- [ ] **Step 1: Update `fetch_comprehensive_token_data` signature**

In `ai_decision_module/ai_data_assembler.py`, line 293:

```python
# Before
async def fetch_comprehensive_token_data(db: DatabaseClient, mint: str) -> dict:

# After
async def fetch_comprehensive_token_data(state: GlobalState, db: DatabaseClient, mint: str) -> dict:
```

- [ ] **Step 2: Replace `GlobalState.get_instance()` at line 364**

In `ai_decision_module/ai_data_assembler.py`, line 364:

```python
# Before
        sol_price = await GlobalState.get_instance().get_sol_price()

# After
        sol_price = await state.get_sol_price()
```

- [ ] **Step 3: Replace `GlobalState.get_instance()` at line 534**

In `ai_decision_module/ai_data_assembler.py`, line 534:

```python
# Before
        market_regime = await GlobalState.get_instance().get_market_regime()

# After
        market_regime = await state.get_market_regime()
```

- [ ] **Step 4: Update call site in `ai_data_assembler.py` `main()`**

In `ai_decision_module/ai_data_assembler.py`, line 655:

```python
# Before
        current_data = await fetch_comprehensive_token_data(db, mint)

# After
        current_data = await fetch_comprehensive_token_data(state, db, mint)
```

- [ ] **Step 5: Update call site in `trading_bot.py`**

In `trading_bot.py`, line 833:

```python
# Before
                    comprehensive_data = await fetch_comprehensive_token_data(self.db_client, mint)

# After
                    comprehensive_data = await fetch_comprehensive_token_data(self.state, self.db_client, mint)
```

- [ ] **Step 6: Quick lint check**

```bash
ruff check ai_decision_module/ai_data_assembler.py trading_bot.py
# Expected: no errors
```

- [ ] **Step 7: Commit**

```bash
git add ai_decision_module/ai_data_assembler.py trading_bot.py
git commit -m "refactor: inject state into fetch_comprehensive_token_data and update callers"
```

---

### Task 5: Fix `TradingBot.__init__` and the entry point (Commit D)

**Files:**
- Modify: `trading_bot.py:59,70,1657-1662`
- Modify: `ai_decision_module/ai_data_assembler.py:626`

After this commit, **zero** production code paths call `get_instance()`. Commit 1 (spec language) is now complete.

- [ ] **Step 1: Update `TradingBot.__init__` signature**

In `trading_bot.py`, line 59:

```python
# Before
    def __init__(self, cleanup: bool = False, backup: bool = False, params_file: str = None, no_log_rotate: bool = False):

# After
    def __init__(self, state: GlobalState, cleanup: bool = False, backup: bool = False, params_file: str = None, no_log_rotate: bool = False):
```

- [ ] **Step 2: Replace `get_instance()` in `TradingBot.__init__`**

In `trading_bot.py`, line 70:

```python
# Before
        self.state = GlobalState.get_instance()

# After
        self.state = state
```

- [ ] **Step 3: Update `__main__` entry point**

In `trading_bot.py`, inside `run_bot_async_wrapper()` (around line 1656):

```python
# Before
        bot_instance = TradingBot(
            cleanup=args.cleanup,
            backup=args.backup,
            params_file=args.params_file,
            no_log_rotate=args.no_log_rotate
        )

# After
        state = GlobalState()
        bot_instance = TradingBot(
            state=state,
            cleanup=args.cleanup,
            backup=args.backup,
            params_file=args.params_file,
            no_log_rotate=args.no_log_rotate
        )
```

- [ ] **Step 4: Update `ai_data_assembler.py` `main()` to stop using `get_instance()`**

In `ai_decision_module/ai_data_assembler.py`, line 626:

```python
# Before
    state = GlobalState.get_instance()

# After
    state = GlobalState()
```

- [ ] **Step 5: Verify zero `get_instance()` calls remain in production path**

```bash
grep -rn "get_instance" . --include="*.py" | grep -v "__pycache__" | grep -v "api/main.py" | grep -v "state_manager.py"
# Expected: zero results
```

If any hits appear that are not `api/main.py` or `state_manager.py` itself, fix them before continuing.

- [ ] **Step 6: Quick lint check**

```bash
ruff check trading_bot.py ai_decision_module/ai_data_assembler.py
# Expected: no errors
```

- [ ] **Step 7: Commit**

```bash
git add trading_bot.py ai_decision_module/ai_data_assembler.py
git commit -m "refactor: inject state into TradingBot and wire __main__ as sole creation point"
```

---

### Task 6: Verification checkpoint (before deleting the singleton)

**Files:** none — read-only verification

- [ ] **Step 1: Confirm `GlobalState()` can be called once without error**

```bash
python -c "from state_manager import GlobalState; s = GlobalState(); print('ok')"
# Expected: ok
```

- [ ] **Step 2: Run ruff across the full codebase**

```bash
ruff check .
# Expected: no errors (same baseline as before this work)
```

- [ ] **Step 3: Run mypy on changed files**

```bash
mypy trading_bot.py trade_processor.py database_handler.py ai_decision_module/ai_data_assembler.py
# Expected: no new errors introduced by this work
# (Existing mypy errors in the codebase are pre-existing and not your concern here)
```

- [ ] **Step 4: Smoke-test the bot in simulate mode**

```bash
TRADING_MODE=simulate python trading_bot.py
# Expected: startup log lines appear, no crash or TypeError
# Ctrl-C after ~5 seconds to stop
```

If any step fails, fix the issue before proceeding to Task 7.

---

### Task 7: Delete the singleton (Commit 2)

**Files:**
- Modify: `state_manager.py:21-27,131-135`

- [ ] **Step 1: Update the `GlobalState` class docstring**

In `state_manager.py`, line 21:

```python
# Before
class GlobalState:
    """Thread-safe Singleton class to store global state variables."""
    _instance = None
    _lock = asyncio.Lock()  # Ensures only one instance is created

# After
class GlobalState:
    """Global state container. Create one instance per process root and inject it explicitly."""
```

- [ ] **Step 2: Remove the singleton guard from `__init__`**

In `state_manager.py`, lines 26-27:

```python
# Before
    def __init__(self):
        if GlobalState._instance is not None:
            raise Exception("This class is a singleton!")

        """Initialize state variables."""

# After
    def __init__(self):
        """Initialize state variables."""
```

- [ ] **Step 3: Remove the `get_instance()` classmethod**

In `state_manager.py`, lines 131-135:

```python
# Before
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

# After
    # (delete these lines entirely)
```

- [ ] **Step 4: Confirm zero `get_instance()` calls remain anywhere**

```bash
grep -rn "get_instance" . --include="*.py" | grep -v "__pycache__"
# Expected: zero results
# (api/main.py still has calls but api/main.py cannot be imported anyway — pre-existing issue)
```

If `api/main.py` shows up and you want to be precise: that file fails to import today (missing `core/` module) so its `get_instance()` calls are never reached at runtime. They are excluded from scope per the spec.

- [ ] **Step 5: Confirm two independent `GlobalState()` calls now work**

```bash
python -c "from state_manager import GlobalState; s1 = GlobalState(); s2 = GlobalState(); print('ok')"
# Expected: ok
```

- [ ] **Step 6: Run ruff and mypy**

```bash
ruff check state_manager.py
mypy state_manager.py
# Expected: no errors
```

- [ ] **Step 7: Final smoke test**

```bash
TRADING_MODE=simulate python trading_bot.py
# Expected: startup log lines, no crash; Ctrl-C after ~5 seconds
```

- [ ] **Step 8: Commit**

```bash
git add state_manager.py
git commit -m "refactor: remove GlobalState singleton — injection complete"
```

---

### Task 8: Open PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin feature/phase3a-globalstate-di
```

- [ ] **Step 2: Open PR against `fix/torch-version-constraint`** (not `main`)

```bash
gh pr create \
  --base fix/torch-version-constraint \
  --title "Phase 3A: GlobalState dependency injection" \
  --body "Removes the GlobalState singleton and replaces all get_instance() calls with explicit constructor injection across Path A (trading_bot.py → TradingBot → sub-components). api/main.py is out of scope (pre-existing import failure). Prerequisite for Phase 3B (splitting database_handler.py)."
```
