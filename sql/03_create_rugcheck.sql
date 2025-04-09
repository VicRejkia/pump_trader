CREATE TABLE IF NOT EXISTS rugcheck (
    mint TEXT PRIMARY KEY REFERENCES tokens(mint) ON DELETE CASCADE,
    tokenProgram TEXT,
    creator TEXT,
    token_mintAuthority TEXT,
    token_supply NUMERIC,
    token_decimals INTEGER,
    token_isInitialized BOOLEAN,
    token_freezeAuthority TEXT,
    tokenMeta_name TEXT,
    tokenMeta_symbol TEXT,
    tokenMeta_uri TEXT,
    tokenMeta_mutable BOOLEAN,
    tokenMeta_updateAuthority TEXT,
    freezeAuthority TEXT,
    mintAuthority TEXT,
    risks TEXT,
    score INTEGER,
    fileMeta_description TEXT,
    fileMeta_name TEXT,
    fileMeta_symbol TEXT,
    fileMeta_image TEXT,
    totalMarketLiquidity NUMERIC,
    totalLPProviders INTEGER,
    rugged BOOLEAN,
    tokenType TEXT,
    transferFee_pct NUMERIC,
    transferFee_maxAmount NUMERIC,
    transferFee_authority TEXT,
    graphInsidersDetected INTEGER,
    detectedAt TIMESTAMP WITH TIME ZONE,
    full_data TEXT,
    last_checked TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS rugcheck_backup (
    LIKE rugcheck INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE rugcheck_backup ADD COLUMN backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE rugcheck_backup ALTER COLUMN timestamp DROP DEFAULT;