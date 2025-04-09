CREATE TABLE IF NOT EXISTS migrations (
    signature TEXT PRIMARY KEY, -- Use signature as the primary key
    mint TEXT,
    txType TEXT,
    pool TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS migrations_backup (
    LIKE migrations INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE migrations_backup ADD COLUMN backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE migrations_backup ALTER COLUMN timestamp DROP DEFAULT;