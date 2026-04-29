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
