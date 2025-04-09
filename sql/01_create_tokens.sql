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
    socials_last_checked TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    last_trade TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS tokens_backup (
    LIKE tokens INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE tokens_backup ADD COLUMN backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE tokens_backup ALTER COLUMN timestamp DROP DEFAULT;