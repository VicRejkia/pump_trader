-- init.sql: Combined schema for pump_trader_v2
-- This file combines all the individual SQL schema files into one for initialization.

-- *********************************************
-- EXTENSIONS
-- *********************************************

-- Required for vector storage (used in AI decision memory and market knowledge base)
CREATE EXTENSION IF NOT EXISTS vector;

-- *********************************************
-- TABLES
-- *********************************************

-- 01_create_tokens.sql
-- Table to store token information
CREATE TABLE IF NOT EXISTS tokens (
    mint TEXT PRIMARY KEY,                          -- token mint
    trader_public_key TEXT,                         -- token creator's wallet address
    initial_buy NUMERIC,                            -- initially bought tokens
    sol_amount NUMERIC,                             -- initially spent amount of SOL
    bonding_curve_key TEXT,                         -- bonding Curve key
    v_tokens_in_bonding_curve NUMERIC,              -- tokens in BondingCurve
    v_sol_in_bonding_curve NUMERIC,                 -- SOL in BondingCurve
    market_cap_sol NUMERIC,                         -- market cap in SOL
    name TEXT,                                      -- token name
    symbol TEXT,                                    -- token symbol
    uri TEXT,                                       -- META URL
    website TEXT,                                   -- website link, fetched from META URL
    telegram TEXT,                                  -- telegram link, fetched from META URL
    twitter TEXT,                                   -- twitter link, fetched from META URL
    socials_score INTEGER,                          -- calculated social score
    socials_last_checked TIMESTAMP WITH TIME ZONE,  -- last try to fetch META URL
    sol_price_usd NUMERIC,                          -- SOL price at token creation
    is_active BOOLEAN DEFAULT TRUE,                 -- TRUE or FALSE for considering in check_buy_opportunities
    last_trade TIMESTAMP WITH TIME ZONE,            -- TIMESTAMP of the last Trade event, updated when a new TRADE is fetched
    cooldown_until TIMESTAMP WITH TIME ZONE,        -- Prevent re-buys until this time
    data_source TEXT DEFAULT 'PUMP',                -- 'PUMP' for WebSocket, 'DEXSCREENER' for API
    ai_last_evaluation_ts TIMESTAMPTZ,              -- Timestamp of the last AI evaluation
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- creation TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS tokens_backup (
    LIKE tokens INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS ai_last_evaluation_ts TIMESTAMPTZ;
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_reason TEXT;
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE tokens_backup ALTER COLUMN timestamp DROP DEFAULT;

-- 02_create_trades.sql
-- Table to store trade events
CREATE TABLE IF NOT EXISTS trades (
    signature TEXT PRIMARY KEY,         -- signature of the token event
    mint TEXT,                          -- tokens mint address
    trader_pubkey TEXT,                 -- The wallet address of the trader
    tx_type TEXT,                       -- event type 'buy' or 'sell'
    token_amount NUMERIC,               -- amount of tokens traded
    sol_amount NUMERIC,                 -- amount of SOL traded
    price NUMERIC,                      -- token price in SOL
    bonding_curve_key TEXT,             -- BondingCurve key
    v_tokens_in_bonding_curve NUMERIC,  -- tokens in BondingCurve
    v_sol_in_bonding_curve NUMERIC,     -- amount of SOL in BondingCurve
    market_cap_sol NUMERIC,             -- market cap in SOL
    sol_price_usd NUMERIC,              -- actual SOL price in USD at the time of the trade event
    market_cap_calculated NUMERIC,      -- calculated market cap in USD
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of the trade event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS trades_backup (
    LIKE trades INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE trades_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE trades_backup ALTER COLUMN timestamp DROP DEFAULT;

-- 03_create_rugcheck.sql
-- Table to store rugpull check results
CREATE TABLE IF NOT EXISTS rugcheck (
    id SERIAL PRIMARY KEY, -- Use a serial ID as the primary key
    mint TEXT REFERENCES tokens(mint) ON DELETE CASCADE, -- Mint is no longer primary, but still references tokens
    token_program TEXT,
    creator TEXT,
    token_mint_authority TEXT,
    token_supply NUMERIC,
    token_decimals INTEGER,
    token_is_initialized BOOLEAN,
    token_freeze_authority TEXT,
    token_meta_name TEXT,
    token_meta_symbol TEXT,
    token_meta_uri TEXT,
    token_meta_mutable BOOLEAN,
    token_meta_update_authority TEXT,
    freeze_authority TEXT,
    mint_authority TEXT,
    risks TEXT,
    score INTEGER,
    file_meta_description TEXT,
    file_meta_name TEXT,
    file_meta_symbol TEXT,
    file_meta_image TEXT,
    total_market_liquidity NUMERIC,
    total_lp_providers INTEGER,
    rugged BOOLEAN,
    token_type TEXT,
    transfer_fee_pct NUMERIC,
    transfer_fee_max_amount NUMERIC,
    transfer_fee_authority TEXT,
    graph_insiders_detected INTEGER,
    detected_at TIMESTAMP WITH TIME ZONE,
    full_data TEXT,
    last_checked TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS rugcheck_backup (
    LIKE rugcheck INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE rugcheck_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE rugcheck_backup ALTER COLUMN timestamp DROP DEFAULT;

-- 04_create_portfolio.sql
-- Table to store portfolio positions
CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    mint TEXT,
    tx_type TEXT,                      -- 'buy' or 'sell'
    price NUMERIC,                     -- Price per token at the time of tx
    market_cap NUMERIC,                -- Market cap at the time of tx
    sol_amount NUMERIC,                -- Gross SOL spent (buy) or received (sell, before fees)
    sol_price_usd NUMERIC,             -- SOL price in USD at the time of tx
    tokens NUMERIC,                    -- Number of tokens bought or sold in this tx
    fee NUMERIC,                       -- Fee associated with this tx
    tip NUMERIC,                       -- Tip associated with this tx
    profit NUMERIC,                    -- Profit/Loss for sell tx (net_sol_received - cost_basis)
    status TEXT,                       -- Status of the original buy position ('active', 'closed')
    reason TEXT,                       -- Reason for sell ('Stop Loss', 'First TP', etc.)
    buy_reason TEXT,                   -- Reason for buy ('Rule-Based', 'AI-Advised')

    -- Fields primarily relevant for the original 'buy' entry
    total_investment_sol NUMERIC,      -- Total SOL invested in this position (including fees)
    initial_tokens NUMERIC,            -- Total tokens acquired in the initial buy tx
    remaining_tokens NUMERIC,          -- Tokens currently held from the initial buy tx (updated on sells)
    highest_price NUMERIC NOT NULL DEFAULT 0.0, -- Highest price observed since the buy
    stop_loss_price NUMERIC,           -- Current active stop loss price level
    initial_tp_price NUMERIC,          -- Calculated price for the first take profit
    second_tp_price NUMERIC,           -- Calculated price for the second take profit
    first_tp_hit BOOLEAN NOT NULL DEFAULT FALSE, -- Flag indicating if the first TP has been triggered

    settings JSONB,                    -- Settings for this position (e.g. stop loss price)

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS portfolio_backup (
     LIKE portfolio INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE portfolio_backup ADD COLUMN IF NOT EXISTS backed_up TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE portfolio_backup ALTER COLUMN timestamp DROP DEFAULT;

-- 05_create_migrations.sql
-- Table to store migration events
CREATE TABLE IF NOT EXISTS migrations (
    signature TEXT PRIMARY KEY, -- signature of the token event
    mint TEXT,                  -- tokens mint address
    tx_type TEXT,               -- event type 'migrate'
    pool TEXT,                  -- migration pool
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of migration event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS migrations_backup (
    LIKE migrations INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE migrations_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE migrations_backup ALTER COLUMN timestamp DROP DEFAULT;

-- 06_create_creator_wallets.sql
-- Table to store information about token creators
CREATE TABLE IF NOT EXISTS creator_wallets (
    wallet_address TEXT PRIMARY KEY,
    token_count INTEGER DEFAULT 0,
    last_token_time TIMESTAMP WITH TIME ZONE
);

-- 07_create_sol_price_usd.sql
-- Table to store historical SOL price in USD
CREATE TABLE IF NOT EXISTS sol_price_usd (
    id SERIAL PRIMARY KEY,
    price NUMERIC(15, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 08_create_bot_heartbeat.sql
-- Table to store bot heartbeat and status events
CREATE TABLE IF NOT EXISTS bot_heartbeat (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    event_type TEXT DEFAULT 'heartbeat', -- e.g., 'heartbeat', 'config_update', 'shutdown_signal'
    details JSONB -- Optional: for storing details about the event, like which config was updated
);

-- 09_create_configuration.sql
-- Table to store configuration parameters
CREATE TABLE IF NOT EXISTS configurations (
    key TEXT PRIMARY KEY,
    value TEXT,
    type TEXT NOT NULL CHECK (type IN ('int', 'float', 'bool', 'str', 'list')),
    description TEXT, -- Optional: for human-readable descriptions
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Trigger to update last_updated timestamp automatically
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.last_updated = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_configurations_last_updated
BEFORE UPDATE ON configurations
FOR EACH ROW
EXECUTE FUNCTION update_last_updated_column();

-- 10_create_dexscreener_data.sql
-- Table to store periodic data snapshots from the DEX Screener API for migrated tokens
CREATE TABLE IF NOT EXISTS dexscreener_data (
    id SERIAL PRIMARY KEY,
    pair_address TEXT NOT NULL,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price_usd NUMERIC,
    price_native NUMERIC,
    sol_price_usd NUMERIC, -- Added for SOL price in USD
    liquidity_usd NUMERIC,
    market_cap NUMERIC,
    fdv NUMERIC,
    
    -- Volume Columns
    volume_m5 NUMERIC,
    volume_h1 NUMERIC,
    volume_h6 NUMERIC,
    volume_h24 NUMERIC,
    
    -- Price Change Columns
    price_change_m5 NUMERIC,
    price_change_h1 NUMERIC,
    price_change_h6 NUMERIC,
    price_change_h24 NUMERIC,

    -- Transaction Columns
    buys_m5 INTEGER,
    sells_m5 INTEGER,
    buys_h1 INTEGER,
    sells_h1 INTEGER,
    buys_h6 INTEGER,
    sells_h6 INTEGER,
    buys_h24 INTEGER,
    sells_h24 INTEGER,

    full_response JSONB
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS dexscreener_data_backup (
    LIKE dexscreener_data INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE dexscreener_data_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE dexscreener_data_backup ALTER COLUMN timestamp DROP DEFAULT;

-- 11_create_completed_trades.sql
-- Table to store completed trades
CREATE TABLE IF NOT EXISTS completed_trades
(
    trade_id integer NOT NULL DEFAULT nextval('completed_trades_trade_id_seq'::regclass),
    token_address character varying(44) COLLATE pg_catalog."default" NOT NULL,
    side character varying(4) COLLATE pg_catalog."default" NOT NULL,
    amount_in_sol numeric NOT NULL,
    amount_out_tokens numeric NOT NULL,
    fill_price numeric NOT NULL,
    market_cap_at_trade numeric,
    tx_fee_sol numeric,
    tip_sol numeric DEFAULT 0,
    slippage_percent numeric,
    trade_context jsonb,
    created_at timestamp with time zone DEFAULT now(),
    social_velocity double precision,
    volatility_at_entry double precision,
    rugcheck_score_at_entry integer,
    market_regime text COLLATE pg_catalog."default",
    crossed_cooldown_boundary boolean,
    sell_fraction double precision,
    rebuy boolean DEFAULT false,
    CONSTRAINT completed_trades_pkey PRIMARY KEY (trade_id),
    CONSTRAINT completed_trades_side_check CHECK (side::text = ANY (ARRAY['buy'::character varying, 'sell'::character varying]::text[]))
);

-- 14_create_rl_tables.sql
-- Tables for Reinforcement Learning agent performance tracking
-- Table to track training sessions and their outcomes
CREATE TABLE IF NOT EXISTS rl_training_sessions (
    session_id UUID PRIMARY KEY,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    hyperparameters JSONB,
    final_metrics JSONB,
    model_path TEXT,
    notes TEXT -- For manual notes on the training run
);

-- Table for detailed performance logging of the agent's actions
-- Partitioning by time is crucial for performance with large datasets
CREATE TABLE IF NOT EXISTS rl_agent_performance (
    timestamp TIMESTAMPTZ NOT NULL,
    token_mint TEXT NOT NULL,
    action_taken JSONB,
    reward REAL,
    observation JSONB,
    session_id UUID REFERENCES rl_training_sessions(session_id)
) PARTITION BY RANGE (timestamp);

-- Optional: Create partitions for the next few months as an example
-- In a production PostgreSQL environment, you would automate this process.
CREATE TABLE IF NOT EXISTS rl_agent_performance_y2025m08 PARTITION OF rl_agent_performance
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS rl_agent_performance_y2025m09 PARTITION OF rl_agent_performance
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

-- 15_create_social_scores.sql
-- Table to store historical and detailed social scoring data
CREATE TABLE IF NOT EXISTS social_scores (
    id SERIAL PRIMARY KEY,
    mint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score_type TEXT NOT NULL, -- e.g., 'INITIAL', 'TELEGRAM_UPDATE', 'WEBSITE_UPDATE'
    score_value INTEGER NOT NULL,
    details JSONB, -- For storing specific metrics like member count, online count, etc.
    CONSTRAINT fk_mint
        FOREIGN KEY(mint)
        REFERENCES tokens(mint)
        ON DELETE CASCADE
);

-- Create the backup table for social_scores
CREATE TABLE IF NOT EXISTS social_scores_backup (
    id INTEGER NOT NULL,
    mint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    score_type TEXT NOT NULL,
    score_value INTEGER NOT NULL,
    details JSONB,
    backup_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(id) -- Primary key to handle conflicts on backup
);

-- 16_create_ga_tables.sql
-- Tables for Genetic Algorithm optimizer results
-- Table to track each individual execution of the optimizer.
CREATE TABLE IF NOT EXISTS ga_runs (
    run_id UUID PRIMARY KEY,
    -- The timestamp when this run was first recorded in the database.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table to store each unique solution (parameter set) for a given run.
CREATE TABLE IF NOT EXISTS ga_solutions (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES ga_runs(run_id) ON DELETE CASCADE,
    generation INT NOT NULL,
    solution_idx INT NOT NULL,
    -- Using JSONB is highly efficient for storing and querying parameter sets.
    parameters JSONB NOT NULL,
    -- Ensures that each solution within a generation is unique for a given run.
    UNIQUE(run_id, generation, solution_idx)
);

-- Table to store the results of a backtest for a given solution on a specific token.
CREATE TABLE IF NOT EXISTS ga_backtests (
    id SERIAL PRIMARY KEY,
    solution_id INT NOT NULL REFERENCES ga_solutions(id) ON DELETE CASCADE,
    mint_tested TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT, -- Populated only if status is 'failed'
    
    -- Performance Metrics
    final_portfolio_value NUMERIC(20, 10),
    total_pnl NUMERIC(20, 10),
    total_return_pct NUMERIC(20, 10),
    win_rate NUMERIC(10, 5),
    profit_factor NUMERIC(20, 10),
    max_drawdown NUMERIC(10, 5),
    total_trades INT,
    
    -- Simulation Metadata
    simulation_start_ts TIMESTAMPTZ,
    simulation_end_ts TIMESTAMPTZ,
    simulation_end_reason TEXT,
    
    -- Ensures a solution is only tested once per mint.
    UNIQUE(solution_id, mint_tested)
);

-- Table to store every individual trade from a backtest.
CREATE TABLE IF NOT EXISTS ga_trades (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INT NOT NULL REFERENCES ga_backtests(id) ON DELETE CASCADE,
    
    -- Trade Details
    timestamp TIMESTAMPTZ NOT NULL,
    type TEXT NOT NULL, -- 'buy' or 'sell'
    price NUMERIC(30, 20) NOT NULL,
    amount_sol NUMERIC(20, 10),
    amount_tokens NUMERIC(30, 10),
    reason TEXT,
    pnl NUMERIC(20, 10)
);

-- 17_create_ai_decision_memory.sql
-- Table to store AI decision snapshots for RAG
CREATE TABLE IF NOT EXISTS ai_decision_memory (
    id SERIAL PRIMARY KEY,
    mint TEXT NOT NULL,
    evaluation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_context TEXT,
    decision TEXT,
    confidence INTEGER,
    model_name TEXT, -- Added column for model name
    explanation TEXT,
    
    -- This is the document that gets queried (the text summary)
    situation_summary TEXT, 
    
    -- This is the vector embedding for the summary
    -- all-MiniLM-L6-v2 produces 384-dimensional vectors
    embedding vector(384), 
    
    -- Store source, mcap, volatility etc. as structured data
    metadata JSONB 
);

-- 18_create_market_knowledge_base.sql
-- Table to store market knowledge base for RAG
CREATE TABLE IF NOT EXISTS market_knowledge_base (
    id SERIAL PRIMARY KEY,
    mint TEXT UNIQUE,
    summary TEXT,
    embedding vector(384), -- Same dimension as ai_decision_memory
    metadata JSONB, -- Store creator, reason, max_mcap, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- *********************************************
-- VIEWS
-- *********************************************

-- 13_create_views.sql
-- View for combined tokens and tokens_backup
-- Prioritizes data from 'tokens' if a mint exists in both.
CREATE OR REPLACE VIEW v_tokens AS
SELECT
    mint, trader_public_key, initial_buy, sol_amount, bonding_curve_key, v_tokens_in_bonding_curve,
    v_sol_in_bonding_curve, market_cap_sol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, is_active, last_trade,
    cooldown_until,
    '' as backup_reason, timestamp
FROM tokens
UNION ALL
SELECT
    mint, trader_public_key, initial_buy, sol_amount, bonding_curve_key, v_tokens_in_bonding_curve,
    v_sol_in_bonding_curve, market_cap_sol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, FALSE AS is_active, last_trade,
    cooldown_until,
    backup_reason, timestamp
FROM tokens_backup tb
WHERE NOT EXISTS (SELECT 1 FROM tokens t WHERE t.mint = tb.mint);

-- View for combined trades and trades_backup
CREATE OR REPLACE VIEW v_trades AS
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bonding_curve_key,
    v_tokens_in_bonding_curve, v_sol_in_bonding_curve, market_cap_sol, sol_price_usd, market_cap_calculated, timestamp
FROM trades
UNION ALL
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bonding_curve_key,
    v_tokens_in_bonding_curve, v_sol_in_bonding_curve, market_cap_sol, sol_price_usd, market_cap_calculated, timestamp
FROM trades_backup;

-- View for combined rugcheck and rugcheck_backup
-- Note: Getting the *latest* score per mint will be handled in the query using this view.
CREATE OR REPLACE VIEW v_rugcheck AS
SELECT mint, score, token_supply, last_checked, timestamp FROM rugcheck
UNION ALL
SELECT mint, score, token_supply, last_checked, timestamp FROM rugcheck_backup;

-- View for combined migrations and migrations_backup
CREATE OR REPLACE VIEW v_migrations AS
SELECT 
    signature,
    mint,
    tx_type,
    pool,
    timestamp,
    NULL AS backup_timestamp,
    'active' AS record_source
FROM 
    migrations

UNION ALL

SELECT 
    signature,
    mint,
    tx_type,
    pool,
    timestamp,
    backup_timestamp,
    'backup' AS record_source
FROM 
    migrations_backup;

-- View for combined dexscreener_data and dexscreener_data_backup
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data
UNION ALL
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data_backup;

-- Creates unified views for market data from both Pump.fun and DEX Screener.

-- First, a helper view for all Dexscreener data (live + backup).
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data
UNION ALL
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data_backup;

-- ===================================================================================
--  HISTORICAL UNIFIED VIEW (Includes Backups via v_* views)
--  PURPOSE: For backtesting, GA/RL training, and full historical analysis.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_historical AS
SELECT
    mint, timestamp, tx_type, token_amount, sol_amount,
    price AS price_sol, market_cap_sol AS market_cap_sol, market_cap_calculated as market_cap_usd,
    (sol_amount * sol_price_usd) AS volume_usd, --  Added: Unified USD volume
    'PUMP' AS data_source
FROM v_trades -- Querying backup-inclusive view
WHERE price IS NOT NULL AND price  > 0 AND sol_amount  > 0 AND token_amount  > 0
UNION ALL
SELECT
    mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount,
    (volume_m5 / sol_price_usd) AS sol_amount,      --  Corrected: This is now SOL volume
    (price_usd / sol_price_usd) AS price_sol,
    (market_cap / sol_price_usd) AS market_cap_sol,
    market_cap AS market_cap_usd,
    volume_m5 AS volume_usd,                        --  Added: Unified USD volume
    'DEXSCREENER' AS data_source
FROM v_dexscreener_data; -- Querying backup-inclusive view

-- ===================================================================================
--  LIVE-ONLY UNIFIED VIEW (Excludes Backups)
--  PURPOSE: For fast, forward-looking queries driving live trade decisions.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_live AS
SELECT
    mint, timestamp, tx_type, token_amount, sol_amount,
    price AS price_sol, market_cap_sol AS market_cap_sol, market_cap_calculated as market_cap_usd,
    (sol_amount * sol_price_usd) AS volume_usd, --  Added: Unified USD volume
    'PUMP' AS data_source
FROM trades -- Querying LIVE table
WHERE price IS NOT NULL AND price  > 0 AND sol_amount  > 0 AND token_amount  > 0
UNION ALL
SELECT
    mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount,
    (volume_m5 / sol_price_usd) AS sol_amount,      --  Corrected: This is now SOL volume
    (price_usd / sol_price_usd) AS price_sol,
    (market_cap / sol_price_usd) AS market_cap_sol,
    market_cap AS market_cap_usd,
    volume_m5 AS volume_usd,                        --  Added: Unified USD volume
    'DEXSCREENER' AS data_source
FROM dexscreener_data; -- Querying LIVE table

-- View to combine live and backed-up social score entries
CREATE OR REPLACE VIEW v_social_scores AS
SELECT
    id,
    mint,
    timestamp,
    score_type,
    score_value,
    details,
    NULL AS backup_timestamp,
    'active' as record_source
FROM
    social_scores

UNION ALL

SELECT
    id,
    mint,
    timestamp,
    score_type,
    score_value,
    details,
    backup_timestamp,
    'backup' as record_source
FROM
    social_scores_backup;

-- *********************************************
-- INDEXES
-- *********************************************

-- 12_create_indexes.sql
-- *********************************************
-- INDEXES FOR BASE TABLES
-- *********************************************

-- Tokens Table
CREATE INDEX IF NOT EXISTS idx_tokens_is_active_timestamp ON public.tokens USING btree (is_active, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tokens_mint ON public.tokens USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_name ON public.tokens USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_socials_score ON public.tokens USING btree (socials_score);
CREATE INDEX IF NOT EXISTS idx_tokens_trader_public_key ON public.tokens USING btree (trader_public_key);

-- Trades Table
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp ON trades(mint, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp_sol ON trades(mint, timestamp DESC, sol_amount); -- For View Queries

-- Portfolio Table
CREATE INDEX IF NOT EXISTS idx_portfolio_active_buy ON portfolio USING btree (mint, tx_type, status) WHERE ((status = 'active'::text) AND (tx_type = 'buy'::text));
CREATE INDEX IF NOT EXISTS idx_portfolio_mint ON portfolio USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_portfolio_mint_status ON portfolio USING btree (mint, status);

-- Rugcheck Table
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked ON rugcheck(mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked_desc ON rugcheck USING btree (mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_score ON rugcheck USING btree (score);

-- Dexscreener_data Table
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_mint_timestamp ON dexscreener_data USING btree (mint_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_pair_address ON dexscreener_data USING btree (pair_address);

-- bot_heartbeat Table
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_event_type ON bot_heartbeat USING btree (event_type);
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_timestamp ON bot_heartbeat USING btree (timestamp DESC);

-- configurations Table
CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations USING btree (key);

-- *********************************************
-- INDEXES FOR BACKUP TABLES
-- *********************************************

-- Tokens Backup
CREATE INDEX IF NOT EXISTS idx_tokens_backup_mint ON tokens_backup USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_name ON tokens_backup USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_socials_score ON tokens_backup USING btree (socials_score);

-- Trades Backup
CREATE INDEX IF NOT EXISTS idx_trades_backup_mint_timestamp ON trades_backup(mint, timestamp DESC);

-- Rugcheck Backup
CREATE INDEX IF NOT EXISTS idx_rugcheck_backup_mint_last_checked ON rugcheck_backup USING btree (mint, last_checked DESC);

-- Dexscreener_data Backup
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_mint_address_timestamp_idx ON dexscreener_data_backup USING btree (mint_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_pair_address_idx ON dexscreener_data_backup USING btree (pair_address);

-- Social Scores Table
CREATE INDEX IF NOT EXISTS idx_social_scores_mint_timestamp ON social_scores(mint, timestamp DESC);

-- Social Scores Backup Table
CREATE INDEX IF NOT EXISTS idx_social_scores_backup_mint_timestamp ON social_scores_backup(mint, timestamp DESC);

-- GA Tables
CREATE INDEX IF NOT EXISTS idx_ga_solutions_run_id ON ga_solutions(run_id);
CREATE INDEX IF NOT EXISTS idx_ga_solutions_parameters_gin ON ga_solutions USING GIN(parameters);
CREATE INDEX IF NOT EXISTS idx_ga_backtests_solution_id ON ga_backtests(solution_id);
CREATE INDEX IF NOT EXISTS idx_ga_backtests_final_portfolio_value ON ga_backtests(final_portfolio_value DESC);
CREATE INDEX IF NOT EXISTS idx_ga_trades_backtest_id ON ga_trades(backtest_id);
CREATE INDEX IF NOT EXISTS idx_ga_trades_timestamp ON ga_trades(timestamp DESC);

-- RL Tables
CREATE INDEX IF NOT EXISTS idx_rl_agent_performance_timestamp ON rl_agent_performance(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_rl_agent_performance_token_mint ON rl_agent_performance(token_mint);

-- AI Decision Memory Table
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_mint ON ai_decision_memory(mint);
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_timestamp ON ai_decision_memory(evaluation_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_embedding_ivfflat ON ai_decision_memory 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Market Knowledge Base Table
CREATE INDEX IF NOT EXISTS idx_mkt_kb_embedding_ivfflat ON market_knowledge_base 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);