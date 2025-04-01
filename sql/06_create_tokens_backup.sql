-- Create the tokens_backup table with an extra column for the backup timestamp
CREATE TABLE IF NOT EXISTS tokens_backup (
    mint TEXT,
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
    socials_last_checked TIMESTAMP,
    is_active BOOLEAN,
    last_trade TIMESTAMP,
    timestamp TIMESTAMP,
    backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional index on backup_timestamp for fast lookup on backup timing
CREATE INDEX IF NOT EXISTS idx_tokens_backup_timestamp ON tokens_backup (backup_timestamp);
