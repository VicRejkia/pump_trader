# Foundation Modernization — Design Spec

**Date:** 2026-04-30
**Phase:** 2 of 4 (follows Documentation Layer)
**Branch:** fix/torch-version-constraint

---

## Goal

Establish a working local dev toolchain (ruff, mypy, pytest) and fix the known `asyncpg` duplicate in `requirements.txt`, without disrupting the existing dual-file dependency strategy (`requirements.txt` + `constraints-macos12.txt`).

---

## Context

- Python 3.11.15 on macOS 12 (temporary dev machine, CPU-only)
- `requirements.txt` is the canonical dep file for Windows/Linux/macOS 13+
- `constraints-macos12.txt` pins `torch==2.2.2`, `stable-baselines3==2.5.0`, `gymnasium==1.0.0` for macOS 12 compat; applied with `pip install -r requirements.txt -c constraints-macos12.txt`
- No `pyproject.toml`, `setup.py`, or `setup.cfg` exists today
- No test suite, no linter config, no type-checker config

---

## Out of Scope

- GitHub Actions CI (separate sub-project, after real tests exist)
- Moving deps into `pyproject.toml [project.dependencies]`
- Writing actual test cases (Phase 3 — requires GlobalState → DI refactor first)
- Mypy enforcement / type-hint fixes (Phase 3)
- Adding a numpy pin or other dep changes beyond the asyncpg duplicate fix

---

## Deliverables

### 1. Fix duplicate `asyncpg` in `requirements.txt`

Remove the second `asyncpg` entry (line 31, inside the `# PostgreSQL Integration` block). The entry at line 3 (in the core async block) is canonical and stays. The `# PostgreSQL Integration` block becomes `psycopg2-binary` only.

No other changes to `requirements.txt`.

---

### 2. `pyproject.toml` (project root)

Tool configuration only — no `[project.dependencies]`. `requirements.txt` remains the dep source of truth.

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

**Ruff rules:**
- `E` / `W` — pycodestyle errors and warnings
- `F` — Pyflakes (undefined names, unused imports)
- `I` — isort (import ordering)
- `E501` ignored — line length is noted but not enforced (120 char soft limit via formatter)

**Mypy:** permissive baseline — `ignore_missing_imports = true` avoids failures on untyped third-party packages (torch, asyncpg stubs, etc.). Strictness added progressively in Phase 3.

---

### 3. `requirements-dev.txt` (project root)

```
# Dev tools — install after requirements.txt
# pip install -r requirements-dev.txt
pytest==8.3.5
pytest-asyncio==0.24.0
pytest-mock==3.14.0
mypy==1.11.2
ruff==0.6.9
```

Pinned to tested versions to avoid setup drift across machines. Not affected by `constraints-macos12.txt` (these are dev tools, not ML deps).

---

### 4. `tests/conftest.py`

```python
import pytest

# asyncio_mode = "auto" is configured in pyproject.toml
# No per-test @pytest.mark.asyncio decorator needed
```

`tests/` directory created with `conftest.py` only. Running `pytest` reports "no tests ran" — correct baseline. Real tests added in Phase 3.

---

## Installation (updated)

**macOS 12:**
```bash
pip install -r requirements.txt -c constraints-macos12.txt
pip install -r requirements-dev.txt
```

**macOS 13+ / Linux / Windows:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**Verify toolchain:**
```bash
ruff check .          # should report 0 errors (or known pre-existing issues)
mypy state_manager.py # should complete without crash
pytest                # should report "no tests ran"
```

---

## Files Modified / Created

| File | Action |
|------|--------|
| `requirements.txt` | Remove duplicate `asyncpg` (line 31) |
| `pyproject.toml` | Create |
| `requirements-dev.txt` | Create |
| `tests/conftest.py` | Create (new directory) |

---

## What This Does NOT Change

- `requirements.txt` dep list (other than asyncpg duplicate removal)
- `constraints-macos12.txt` — untouched
- Any source code files
- `docs/DEVELOPMENT.md` — will need a small update to document the new install step and tool commands (included as a task in the implementation plan)
