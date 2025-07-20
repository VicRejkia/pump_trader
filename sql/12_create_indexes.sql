-- *********************************************
-- INDEXES FOR BASE TABLES
-- *********************************************

-- Tokens Table
CREATE INDEX IF NOT EXISTS idx_tokens_is_active_timestamp ON public.tokens USING btree (is_active, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_tokens_mint ON public.tokens USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_name ON public.tokens USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_socials_score ON public.tokens USING btree (socials_score);
CREATE INDEX IF NOT EXISTS idx_tokens_traderpublickey ON public.tokens USING btree (traderpublickey);

-- Trades Table
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp ON trades(mint, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_mint_timestamp_sol ON trades(mint, timestamp DESC, sol_amount); -- For View Queries

-- Portfolio Table
CREATE INDEX IF NOT EXISTS idx_portfolio_active_buy ON portfolio USING btree (mint, tx_type, status) WHERE ((status = 'active'::text) AND (tx_type = 'buy'::text));
CREATE INDEX IF NOT EXISTS idx_portfolio_mint ON portfolio USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_portfolio_mint_status ON portfolio USING btree (mint, status);

-- Rugcheck Table
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked ON rugcheck(mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_mint_last_checked_desc ON rugcheck USING btree (mint, last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_rugcheck_score ON rugcheck USING btree (score);

-- Dexscreener_data Table
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_mint_timestamp ON dexscreener_data USING btree (mint_address, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_dexscreener_data_pair_address ON dexscreener_data USING btree (pair_address);

-- bot_heartbeat Table
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_event_type ON bot_heartbeat USING btree (event_type);
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_timestamp ON bot_heartbeat USING btree ("timestamp" DESC);

-- configurations Table
CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations USING btree (key);

-- *********************************************
-- INDEXES FOR BACKUP TABLES
-- *********************************************

-- Tokens Backup
CREATE INDEX IF NOT EXISTS idx_tokens_backup_mint ON tokens_backup USING btree (mint);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_name ON tokens_backup USING btree (name);
CREATE INDEX IF NOT EXISTS idx_tokens_backup_socials_score ON tokens_backup USING btree (socials_score);

-- Trades Backup
CREATE INDEX IF NOT EXISTS idx_trades_backup_mint_timestamp ON trades_backup(mint, timestamp DESC);

-- Rugcheck Backup
CREATE INDEX IF NOT EXISTS idx_rugcheck_backup_mint_last_checked ON rugcheck_backup USING btree (mint, last_checked DESC);

-- Dexscreener_data Backup
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_mint_address_timestamp_idx ON dexscreener_data_backup USING btree (mint_address, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS dexscreener_data_backup_pair_address_idx ON dexscreener_data_backup USING btree (pair_address);