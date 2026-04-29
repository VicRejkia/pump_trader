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

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DB_USER` | Yes | — | PostgreSQL username |
| `DB_PASSWORD` | Yes | — | PostgreSQL password |
| `DB_HOST` | Yes | `localhost:5432` | PostgreSQL host:port |
| `DB_DATABASE` | Yes | — | Database name |

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
