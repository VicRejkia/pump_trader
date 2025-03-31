CREATE TABLE IF NOT EXISTS migrations_backup (
            id SERIAL PRIMARY KEY,
            signature TEXT,
            mint TEXT,
            txType TEXT,
            pool TEXT,
            timestamp TIMESTAMP,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );