CREATE TABLE IF NOT EXISTS portfolio (
            id SERIAL PRIMARY KEY,
            mint TEXT REFERENCES tokens(mint) ON DELETE CASCADE,
            tx_type TEXT,
            price NUMERIC,
            market_cap NUMERIC,
            sol_amount NUMERIC,
            tokens NUMERIC,
            fee NUMERIC,
            tip NUMERIC,
            profit NUMERIC,
            status TEXT,
            reason TEXT,
            initial_tokens NUMERIC,
            remaining_tokens NUMERIC,
            highest_price NUMERIC NOT NULL DEFAULT 0.0,
            stop_loss_price NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );