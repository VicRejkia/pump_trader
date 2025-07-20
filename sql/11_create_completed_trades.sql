CREATE TABLE completed_trades (
    trade_id SERIAL PRIMARY KEY,
    token_address VARCHAR(44) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('buy', 'sell')),

    -- Amounts and Prices
    amount_in_sol NUMERIC NOT NULL,
    amount_out_tokens NUMERIC NOT NULL,
    fill_price NUMERIC NOT NULL,

    -- Context and Fees
    market_cap_at_trade NUMERIC,
    tx_fee_sol NUMERIC, -- The base network fee
    tip_sol NUMERIC DEFAULT 0, -- The priority fee (Jito tip, etc.)
    slippage_percent NUMERIC,

    -- RL Context
    trade_context JSONB, -- For storing other metadata like stop-loss settings, etc.

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);