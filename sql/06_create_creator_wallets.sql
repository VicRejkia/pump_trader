CREATE TABLE IF NOT EXISTS creator_wallets (
    wallet_address TEXT PRIMARY KEY,
    token_count INTEGER DEFAULT 0,
    last_token_time TIMESTAMP WITH TIME ZONE
);