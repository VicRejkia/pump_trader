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
    market_cap_calculated NUMERIC,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS trades_backup (
    LIKE trades INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE trades_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE trades_backup ALTER COLUMN timestamp DROP DEFAULT;