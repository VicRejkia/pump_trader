-- Create the trades table
CREATE TABLE IF NOT EXISTS trades (
    signature TEXT PRIMARY KEY,         -- signature of the token event
    mint TEXT,                          -- tokens mint address
    tx_type TEXT,                       -- event type 'buy' or 'sell'
    token_amount NUMERIC,               -- amount of tokens traded
    sol_amount NUMERIC,                 -- amount of SOL traded
    price NUMERIC,                      -- token price in SOL
    bondingCurveKey TEXT,               -- BondingCurve key
    vTokensInBondingCurve NUMERIC,      -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,         -- amount of SOL in BondingCurve
    marketCapSol NUMERIC,               -- market cap in SOL
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