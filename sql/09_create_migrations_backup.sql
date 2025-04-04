CREATE TABLE IF NOT EXISTS migrations_backup (
    signature TEXT PRIMARY KEY, -- Use signature as the primary key
    mint TEXT,
    txType TEXT,
    pool TEXT,
    timestamp TIMESTAMP, -- Original timestamp from migrations table
    backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);