-- path: sql/04_create_portfolio.sql

-- Original portfolio table creation
CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    mint TEXT,
    tx_type TEXT,                     -- 'buy' or 'sell'
    price NUMERIC,                    -- Price per token at the time of tx
    market_cap NUMERIC,               -- Market cap at the time of tx
    sol_amount NUMERIC,               -- Gross SOL spent (buy) or received (sell, before fees)
    sol_price_usd NUMERIC,            -- SOL price in USD at the time of tx
    tokens NUMERIC,                   -- Number of tokens bought or sold in this tx
    fee NUMERIC,                      -- Fee associated with this tx
    tip NUMERIC,                      -- Tip associated with this tx
    profit NUMERIC,                   -- Profit/Loss for sell tx (net_sol_received - cost_basis)
    status TEXT,                      -- Status of the original buy position ('active', 'closed')
    reason TEXT,                      -- Reason for sell ('Stop Loss', 'First TP', etc.)
    buy_reason TEXT,                  -- <<< ADD THIS LINE: Reason for buy ('Rule-Based', 'AI-Advised')

    -- Fields primarily relevant for the original 'buy' entry
    total_investment_sol NUMERIC,     -- Total SOL invested in this position (including fees)
    initial_tokens NUMERIC,           -- Total tokens acquired in the initial buy tx
    remaining_tokens NUMERIC,         -- Tokens currently held from the initial buy tx (updated on sells)
    highest_price NUMERIC NOT NULL DEFAULT 0.0, -- Highest price observed since the buy
    stop_loss_price NUMERIC,          -- Current active stop loss price level
    initial_tp_price NUMERIC,         -- Calculated price for the first take profit
    second_tp_price NUMERIC,          -- Calculated price for the second take profit
    first_tp_hit BOOLEAN NOT NULL DEFAULT FALSE, -- Flag indicating if the first TP has been triggered

    settings JSONB,                   -- Settings for this position (e.g. stop loss price)

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