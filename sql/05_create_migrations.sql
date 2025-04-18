CREATE TABLE IF NOT EXISTS migrations (
    signature TEXT PRIMARY KEY, -- signature of the token event
    mint TEXT,                  -- tokens mint address
    txType TEXT,                -- event type 'migrate'
    pool TEXT,                  -- migration pool
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- TIMESTAMP of migration event
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS migrations_backup (
    LIKE migrations INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE migrations_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE migrations_backup ALTER COLUMN timestamp DROP DEFAULT;