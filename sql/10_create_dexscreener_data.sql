-- Table to store periodic data snapshots from the DEX Screener API for migrated tokens
CREATE TABLE IF NOT EXISTS dexscreener_data (
    id SERIAL PRIMARY KEY,
    pair_address TEXT NOT NULL,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price_usd NUMERIC,
    price_native NUMERIC,
    sol_price_usd NUMERIC, -- <<< ADDED THIS COLUMN
    liquidity_usd NUMERIC,
    market_cap NUMERIC,
    fdv NUMERIC,
    
    -- Volume Columns
    volume_m5 NUMERIC,
    volume_h1 NUMERIC,
    volume_h6 NUMERIC,
    volume_h24 NUMERIC,
    
    -- Price Change Columns
    price_change_m5 NUMERIC,
    price_change_h1 NUMERIC,
    price_change_h6 NUMERIC,
    price_change_h24 NUMERIC,

    -- Transaction Columns
    buys_m5 INTEGER,
    sells_m5 INTEGER,
    buys_h1 INTEGER,
    sells_h1 INTEGER,
    buys_h6 INTEGER,
    sells_h6 INTEGER,
    buys_h24 INTEGER,
    sells_h24 INTEGER,

    full_response JSONB
);

CREATE INDEX IF NOT EXISTS idx_dexscreener_data_mint_timestamp ON dexscreener_data(mint_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_pair_address ON dexscreener_data(pair_address);

-- Backup table creation
CREATE TABLE IF NOT EXISTS dexscreener_data_backup (
    LIKE dexscreener_data INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE dexscreener_data_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE dexscreener_data_backup ALTER COLUMN timestamp DROP DEFAULT;