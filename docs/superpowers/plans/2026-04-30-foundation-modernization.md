# Foundation Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a working local dev toolchain (ruff, mypy, pytest) and fix the known `asyncpg` duplicate in `requirements.txt`, without disrupting the existing dual-file dependency strategy.

**Architecture:** Four new/modified files only — `requirements.txt` (bug fix), `pyproject.toml` (tool config), `requirements-dev.txt` (dev deps), `tests/conftest.py` (scaffold). No source code changes. `requirements.txt` stays the canonical dep file; `pyproject.toml` holds ruff/mypy/pytest config only.

**Tech Stack:** Python 3.11, ruff 0.6.9, mypy 1.11.2, pytest 8.3.5, pytest-asyncio 0.24.0

**Spec:** `docs/superpowers/specs/2026-04-30-foundation-modernization-design.md`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `requirements.txt` | Modify | Remove duplicate `asyncpg` from PostgreSQL block |
| `pyproject.toml` | Create | Tool config: ruff, mypy, pytest |
| `requirements-dev.txt` | Create | Pinned dev deps |
| `tests/conftest.py` | Create | Pytest asyncio scaffold |
| `docs/DEVELOPMENT.md` | Modify | Add dev tools section, fix constraints note, remove resolved TODO |

---

## Task 1: Fix duplicate `asyncpg` in `requirements.txt`

**Files:**
- Modify: `requirements.txt`

**Context:** `asyncpg` appears twice — at line 3 (correct, in the core async block) and again inside the `# PostgreSQL Integration` block (wrong, should be `psycopg2-binary` only). Remove the second one.

- [ ] **Step 1: Confirm the duplicate**

```bash
grep -n asyncpg requirements.txt
```

Expected output:
```
3:asyncpg
31:asyncpg
```

- [ ] **Step 2: Remove the duplicate**

Open `requirements.txt`. Find the `# PostgreSQL Integration` block (around line 30):

```
# PostgreSQL Integration
asyncpg
psycopg2-binary
```

Remove the `asyncpg` line, leaving:

```
# PostgreSQL Integration
psycopg2-binary
```

Do NOT touch line 3 (`asyncpg` in the core async block at the top of the file).

- [ ] **Step 3: Verify only one asyncpg remains**

```bash
grep -n asyncpg requirements.txt
```

Expected output:
```
3:asyncpg
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "fix: remove duplicate asyncpg from requirements.txt"
```

---

## Task 2: Create `pyproject.toml`

**Files:**
- Create: `pyproject.toml` (project root)

**Context:** No `pyproject.toml` exists today. This file holds tool configuration only — ruff (linter), mypy (type checker), pytest (test runner). It does NOT replace `requirements.txt` as the dep source.

- [ ] **Step 1: Create the file**

Create `/path/to/project/pyproject.toml` with this exact content:

```toml
[project]
name = "pump-trader"
version = "3.0.0"
requires-python = ">=3.11"

[tool.ruff]
line-length = 120
target-version = "py311"
exclude = ["venv", ".venv", "data", "ga_optimization_results"]

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
warn_unused_ignores = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Rule explanation:**
- `E` / `W` — pycodestyle errors and warnings
- `F` — Pyflakes: undefined names, unused imports
- `I` — isort: import ordering
- `E501` ignored — line length is soft-enforced at 120 via `line-length`, not hard-blocked
- `ignore_missing_imports = true` — avoids mypy failures on untyped packages like torch, asyncpg stubs

- [ ] **Step 2: Verify the TOML parses cleanly**

```bash
python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
```

Expected: no output (silent success). Any output means a syntax error — fix before continuing.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: add pyproject.toml with ruff, mypy, and pytest config"
```

---

## Task 3: Create `requirements-dev.txt`

**Files:**
- Create: `requirements-dev.txt` (project root)

**Context:** No dev-only dep file exists today. This file is installed separately from `requirements.txt` — it's never needed to run the bot, only to develop and test it.

- [ ] **Step 1: Create the file**

Create `requirements-dev.txt` with this exact content:

```
# Dev tools — not needed to run the bot
# Install after requirements.txt:
#   pip install -r requirements-dev.txt
pytest==8.3.5
pytest-asyncio==0.24.0
pytest-mock==3.14.0
mypy==1.11.2
ruff==0.6.9
```

- [ ] **Step 2: Install and verify**

```bash
pip install -r requirements-dev.txt
```

Expected: all 5 packages install (or are already satisfied) without errors.

Verify the tools are callable:

```bash
ruff --version
mypy --version
pytest --version
```

Expected output (versions may be slightly different if already installed):
```
ruff 0.6.9
mypy 1.11.2
pytest 8.3.5
```

- [ ] **Step 3: Commit**

```bash
git add requirements-dev.txt
git commit -m "build: add requirements-dev.txt with pytest, mypy, and ruff"
```

---

## Task 4: Create `tests/conftest.py`

**Files:**
- Create: `tests/conftest.py` (new directory)

**Context:** No test suite exists. This task creates the scaffold — just enough for `pytest` to run cleanly. Real tests are Phase 3. The `asyncio_mode = "auto"` setting in `pyproject.toml` means async test functions work without `@pytest.mark.asyncio` decorators.

- [ ] **Step 1: Create the directory and file**

```bash
mkdir -p tests
```

Create `tests/conftest.py` with this content:

```python
import pytest

# asyncio_mode = "auto" is set in pyproject.toml — no per-test decorator needed
```

- [ ] **Step 2: Run pytest and verify the scaffold works**

```bash
pytest
```

Expected output:
```
=================== no tests ran in 0.XXs ====================
```

If you see an error instead (import error, config error), fix it before continuing.

- [ ] **Step 3: Verify ruff doesn't choke on the new file**

```bash
ruff check tests/
```

Expected output: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add pytest scaffold with asyncio mode configured"
```

---

## Task 5: Update `docs/DEVELOPMENT.md`

**Files:**
- Modify: `docs/DEVELOPMENT.md`

**Context:** `docs/DEVELOPMENT.md` has three issues to fix now that this phase is complete:
1. The setup block at line 19 only shows `pip install -r requirements.txt` — doesn't mention `constraints-macos12.txt` (macOS 12 users need this)
2. A TODO at the bottom (line 119) says "No pytest setup. No requirements-dev.txt." — now resolved
3. A TODO on line 50 mentions "Until `requirements-dev.txt`... exists" — the condition is now met, so that clause should be removed
4. No section on running dev tools (ruff, mypy, pytest)

- [ ] **Step 1: Update the install step in the Setup block**

Find this in the Setup block (around line 19):

```bash
# 2. Install dependencies
pip install -r requirements.txt
```

Replace with:

```bash
# 2. Install dependencies
pip install -r requirements.txt                              # macOS 13+ / Linux / Windows
# pip install -r requirements.txt -c constraints-macos12.txt  # macOS 12 only

# 2b. Install dev tools (linter, type checker, test runner)
pip install -r requirements-dev.txt
```

- [ ] **Step 2: Update the env vars TODO (line 50)**

Find:

```
> **TODO:** Several optional variables are not in `.env_sample` — notably `REDIS_HOST`, `REDIS_PORT`, Ollama endpoint, and logging overrides. Until `requirements-dev.txt` and a config schema exist, check `config/config.py` for the full list of hardcoded defaults.
```

Replace with:

```
> **TODO:** Several optional variables are not in `.env_sample` — notably `REDIS_HOST`, `REDIS_PORT`, Ollama endpoint, and logging overrides. Until a config schema exists, check `config/config.py` for the full list of hardcoded defaults.
```

- [ ] **Step 3: Add a "Dev Tools" section after the Setup section**

After the closing ` ``` ` of the Setup code block (line 36 in `docs/DEVELOPMENT.md`), insert a new `## Dev Tools` section between Setup and Environment Variables. The section content:

    ## Dev Tools

    Run these commands from the project root with the virtual environment active.

    ```bash
    ruff check .                   # lint the entire codebase
    ruff check . --fix             # auto-fix safe issues (unused imports, ordering)
    mypy state_manager.py          # type-check a single file (start here)
    pytest                         # run tests (currently: "no tests ran" is correct)
    pytest -v                      # verbose output
    ```

    On macOS 12, `ruff` and `mypy` work without any platform-specific flags.

- [ ] **Step 4: Remove the resolved TODO at the bottom**

Find and remove this entire line (near the end of the file):

```
> **TODO:** No `pytest` setup. No `requirements-dev.txt`. These are needed before writing any automated tests. `asyncpg` also appears twice in `requirements.txt` (lines 4 and 31) — remove the duplicate.
```

- [ ] **Step 5: Verify the file reads cleanly**

```bash
python3 -c "
with open('docs/DEVELOPMENT.md') as f:
    content = f.read()
assert 'requirements-dev.txt' in content, 'dev tools section missing'
assert 'constraints-macos12.txt' in content, 'constraints note missing'
assert 'No pytest setup' not in content, 'old TODO not removed'
print('DEVELOPMENT.md looks good')
"
```

Expected output:
```
DEVELOPMENT.md looks good
```

- [ ] **Step 6: Commit**

```bash
git add docs/DEVELOPMENT.md
git commit -m "docs: update DEVELOPMENT.md with dev tools section and constraints-macos12 install note"
```

---

## Final Verification

After all tasks are committed, run a full toolchain check:

```bash
ruff check .
pytest
python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('pyproject.toml OK')"
grep -c asyncpg requirements.txt  # should print 1
```

Expected:
- `ruff check .` — outputs 0 errors or known pre-existing warnings (do not fix pre-existing issues)
- `pytest` — `no tests ran`
- `pyproject.toml OK`
- `1` (one asyncpg entry)
