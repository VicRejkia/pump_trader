CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    mint TEXT,
    tx_type TEXT,                     -- 'buy' or 'sell'
    price NUMERIC,                    -- Price per token at the time of tx
    market_cap NUMERIC,               -- Market cap at the time of tx
    sol_amount NUMERIC,               -- Gross SOL spent (buy) or received (sell, before fees)
    tokens NUMERIC,                   -- Number of tokens bought or sold in this tx
    fee NUMERIC,                      -- Fee associated with this tx
    tip NUMERIC,                      -- Tip associated with this tx
    profit NUMERIC,                   -- Profit/Loss for sell tx (net_sol_received - cost_basis)
    status TEXT,                      -- Status of the original buy position ('active', 'closed')
    reason TEXT,                      -- Reason for sell ('Stop Loss', 'First TP', 'Second TP', 'Trailing SL', 'Breakeven SL', etc.)

    -- Fields primarily relevant for the original 'buy' entry
    total_investment_sol NUMERIC,     -- Total SOL invested in this position (including fees)
    initial_tokens NUMERIC,           -- Total tokens acquired in the initial buy tx
    remaining_tokens NUMERIC,         -- Tokens currently held from the initial buy tx (updated on sells)
    highest_price NUMERIC NOT NULL DEFAULT 0.0, -- Highest price observed since the buy
    stop_loss_price NUMERIC,          -- Current active stop loss price level
    initial_tp_price NUMERIC,         -- Calculated price for the first take profit
    second_tp_price NUMERIC,          -- Calculated price for the second take profit
    first_tp_hit BOOLEAN NOT NULL DEFAULT FALSE, -- Flag indicating if the first TP has been triggered

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Add indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_portfolio_mint_status ON portfolio (mint, status);
CREATE INDEX IF NOT EXISTS idx_portfolio_status_txtype ON portfolio (status, tx_type);
CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp ON portfolio (timestamp);