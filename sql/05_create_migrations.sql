CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            signature TEXT,
            mint TEXT,
            txType TEXT,
            pool TEXT,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );