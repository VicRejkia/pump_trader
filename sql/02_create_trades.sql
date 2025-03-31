-- Create the trades table
CREATE TABLE IF NOT EXISTS trades (
    signature TEXT PRIMARY KEY,
    mint TEXT,
    tx_type TEXT,
    token_amount NUMERIC,
    sol_amount NUMERIC,
    price NUMERIC,
    bondingCurveKey TEXT,
    vTokensInBondingCurve NUMERIC,
    vSolInBondingCurve NUMERIC,
    marketCapSol NUMERIC,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index to speed up queries filtering by token mint
CREATE INDEX IF NOT EXISTS idx_trades_mint ON trades (mint);
