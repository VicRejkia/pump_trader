-- Create the tokens table
CREATE TABLE IF NOT EXISTS tokens (
    mint TEXT PRIMARY KEY,          -- token mint
    traderPublicKey TEXT,           -- token creator's wallet address
    initialBuy NUMERIC,             -- initially buyed tokens
    solAmount NUMERIC,              -- initially spent amount of SOL
    bondingCurveKey TEXT,           -- bondingCurve key
    vTokensInBondingCurve NUMERIC,  -- tokens in BondingCurve
    vSolInBondingCurve NUMERIC,     -- SOL in BondingCurve
    marketCapSol NUMERIC,           -- market cap in SOL
    name TEXT,                      -- token name
    symbol TEXT,                    -- token symbol
    uri TEXT,                       -- META URL
    website TEXT,                   -- website link, fetched from META URL
    telegram TEXT,                  -- telegram link, fetched from META URL
    twitter TEXT,                   -- twitter link, fetched from META URL
    socials_score INTEGER,          -- calculated social score
    socials_last_checked TIMESTAMP WITH TIME ZONE,  -- last try to fetch META URL
    sol_price_usd NUMERIC,                          -- SOL price at token creation
    is_active BOOLEAN DEFAULT TRUE,                 -- TRUE or FALLS for considering in check_buy_opportunities
    last_trade TIMESTAMP WITH TIME ZONE,            -- TIMESTAMP of the last Trade event, updated when a new TRADE is fetched
    cooldown_until TIMESTAMP WITH TIME ZONE,        -- <<< ADD THIS LINE: Prevent re-buys until this time
    data_source TEXT DEFAULT 'PUMP', -- 'PUMP' for WebSocket, 'DEXSCREENER' for API
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- creation TIMESTAMP
);

-- Backup table creation
CREATE TABLE IF NOT EXISTS tokens_backup (
    LIKE tokens INCLUDING ALL
);

-- Add the `backed_up` column to the backup table
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_reason TEXT;
ALTER TABLE tokens_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
-- Remove the default value for the `timestamp` column in the backup table
ALTER TABLE tokens_backup ALTER COLUMN timestamp DROP DEFAULT;