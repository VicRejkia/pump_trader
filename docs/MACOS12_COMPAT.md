# macOS 12 Compatibility Notes

This document tracks changes made to get the project running on a temporary
**macOS 12 Monterey / iMac** development machine. It distinguishes between
permanent fixes that should be kept everywhere and temporary workarounds that
must be reverted when moving to a proper environment.

---

## Target Environment

| Property | Value |
|---|---|
| OS | macOS 13+ or Linux |
| Python | 3.11+ (3.12 preferred for full pandas-ta support) |
| PostgreSQL | 18.x with pgvector extension |
| PyTorch | CPU-only (no CUDA on macOS) |

---

## Temporary Workarounds — REVERT WHEN MOVING TO A NEW MACHINE

These are package version caps forced by macOS 12's pip only serving older
wheels. On macOS 13+ or Linux, restore to the latest versions.

### `requirements.txt`

| Package | macOS 12 (current) | Target (restore to) |
|---|---|---|
| `torch` | `>=2.2.0` | `>=2.6.0` |
| `stable-baselines3` | `>=2.3.0,<2.6.0` | `>=2.6.0` |
| `gymnasium` | `>=0.29.1,<1.1.0` | `>=1.1.1` |

**Why:** PyTorch dropped macOS 12 wheel builds after 2.2.2. stable-baselines3
2.6.0+ requires torch>=2.3, and gymnasium 1.1.x+ is required by SB3 2.6+.

### pgvector Installation

On macOS 12 with the EnterpriseDB PostgreSQL 18 installer, pgvector must be
compiled from source with SDK workarounds:

```bash
# One-time system fix (SDK version mismatch between PG18 binary and macOS 12)
sudo ln -s /Library/Developer/CommandLineTools/SDKs/MacOSX13.sdk \
           /Library/Developer/CommandLineTools/SDKs/MacOSX14.sdk

# Build and install pgvector v0.8.2
cd /tmp
git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git
cd pgvector
make PG_CONFIG=/Library/PostgreSQL/18/bin/pg_config OPTFLAGS=""
sudo make install PG_CONFIG=/Library/PostgreSQL/18/bin/pg_config
```

On a proper machine, use the EnterpriseDB Stack Builder or a package manager.

---

## Permanent Fixes — Keep on All Machines

These were genuine bugs or dead dependencies found during the macOS 12 setup.
They apply regardless of OS.

### `pandas-ta` replaced by `ta`

The `pandas-ta` PyPI package and its GitHub repository have been deleted by the
maintainer. It is permanently unavailable. Replaced with the `ta` library.

**Code change:** [utils.py](../utils.py) — `calculate_indicators()` function
rewrites the pandas accessor calls (`df.ta.xxx`) to the `ta` library API while
producing **identical column names** so all downstream code is unaffected:

| Column | Produced by |
|---|---|
| `BBL_{period}_{std}`, `BBM_…`, `BBU_…` | `ta.volatility.BollingerBands` |
| `RSI_{period}` | `ta.momentum.RSIIndicator` |
| `EMA_fast`, `EMA_slow` | `ta.trend.EMAIndicator` |
| `ATRr_{period}` | `ta.volatility.AverageTrueRange` |
| `VWAP` | `ta.volume.VolumeWeightedAveragePrice` |

Parabolic SAR was dropped — it was calculated but never read by any downstream
code.

### `shap` removed

`shap` was listed in requirements but is not imported anywhere in the codebase.
It pulled in `numba` → `llvmlite` → LLVM build toolchain. Removed.

### `stable-baselines3[extra]` → `stable-baselines3`

The `[extra]` variant pulls in `ale-py` (Atari) and `numba`, neither of which
are used. Switched to the base package and added `tensorboard` explicitly since
that is used for RL training monitoring.

### Missing dependencies added to `requirements.txt`

The following packages were imported in the codebase but missing from
requirements.txt. Added:

`aiofiles`, `fastapi`, `uvicorn`, `strawberry-graphql[fastapi]`, `websockets`,
`sentence-transformers`, `ollama`, `mlflow`, `inquirer`, `solana`, `solders`,
`dash`, `streamlit`, `telethon`, `redis`, `tensorboard`

### `winsound` guard in `utils.py`

`winsound` is a Windows-only stdlib module. The import now uses a try/except
guard so the bot starts on macOS and Linux. Sound playback is silently skipped
on non-Windows platforms.

### SQL sequence fix — `sql/11_create_completed_trades.sql`

`completed_trades` referenced `completed_trades_trade_id_seq` in its `DEFAULT`
clause but the sequence was never created. Added `CREATE SEQUENCE IF NOT EXISTS`
before the table definition.
