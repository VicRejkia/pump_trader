-- Create the tokens table
CREATE TABLE IF NOT EXISTS tokens (
    mint TEXT PRIMARY KEY,
    traderPublicKey TEXT,
    initialBuy NUMERIC,
    solAmount NUMERIC,
    bondingCurveKey TEXT,
    vTokensInBondingCurve NUMERIC,
    vSolInBondingCurve NUMERIC,
    marketCapSol NUMERIC,
    name TEXT,
    symbol TEXT,
    uri TEXT,
    website TEXT,
    telegram TEXT,
    twitter TEXT,
    socials_score INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    last_trade TIMESTAMP,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index to improve queries on the last_trade column
CREATE INDEX IF NOT EXISTS idx_tokens_last_trade ON tokens (last_trade);
