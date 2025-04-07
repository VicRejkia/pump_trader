-- Create the trades_backup table with an extra column for the backup timestamp
CREATE TABLE IF NOT EXISTS trades_backup (
    signature TEXT PRIMARY KEY, -- Add PRIMARY KEY constraint
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
    timestamp TIMESTAMP WITH TIME ZONE,
    backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional index on backup_timestamp
CREATE INDEX IF NOT EXISTS idx_trades_backup_timestamp ON trades_backup (backup_timestamp);
