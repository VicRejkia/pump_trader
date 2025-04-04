CREATE TABLE IF NOT EXISTS migrations (
    signature TEXT PRIMARY KEY, -- Use signature as the primary key
    mint TEXT,
    txType TEXT,
    pool TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);