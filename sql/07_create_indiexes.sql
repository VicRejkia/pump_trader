-- *********************************************
-- INDEXES FOR BASE TABLES
-- *********************************************

-- Tokens Table
CREATE INDEX idx_tokens_mint ON tokens(mint);
CREATE INDEX idx_tokens_traderPublicKey ON tokens(traderPublicKey);
CREATE INDEX idx_tokens_socials_score ON tokens(socials_score);
CREATE INDEX idx_tokens_name ON tokens(name);
CREATE INDEX idx_tokens_is_active_timestamp ON tokens(is_active, timestamp DESC);

-- Trades Table
CREATE INDEX idx_trades_signature ON trades(signature);
CREATE INDEX idx_trades_mint_timestamp ON trades(mint, timestamp DESC);
CREATE INDEX idx_trades_mint_sol_amount ON trades(mint, sol_amount);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);

-- Portfolio Table
CREATE INDEX idx_portfolio_mint ON portfolio(mint);
CREATE INDEX idx_portfolio_active_buy 
ON portfolio(mint, tx_type, status)
WHERE status = 'active' AND tx_type = 'buy';

-- Rugcheck Table
CREATE INDEX idx_rugcheck_mint_last_checked ON rugcheck(mint, last_checked DESC);
CREATE INDEX idx_rugcheck_score ON rugcheck(score);

-- *********************************************
-- INDEXES FOR BACKUP TABLES (if actively queried)
-- *********************************************

-- Tokens Backup
CREATE INDEX idx_tokens_backup_mint ON tokens_backup(mint);
CREATE INDEX idx_tokens_backup_socials_score ON tokens_backup(socials_score);
CREATE INDEX idx_tokens_backup_name ON tokens_backup(name);

-- Trades Backup
CREATE INDEX idx_trades_backup_mint_timestamp ON trades_backup(mint, timestamp DESC);
CREATE INDEX idx_trades_backup_signature ON trades_backup(signature);

-- Rugcheck Backup
CREATE INDEX idx_rugcheck_backup_mint_last_checked ON rugcheck_backup(mint, last_checked DESC);

-- *********************************************
-- SPECIALIZED INDEXES FOR VIEW QUERIES
-- *********************************************

-- For get_filtered_tokens (RecentVolume CTE)
CREATE INDEX idx_trades_mint_timestamp_sol 
ON trades(mint, timestamp DESC, sol_amount);

-- For LatestRugcheck CTE in views
CREATE INDEX idx_rugcheck_mint_last_checked_desc 
ON rugcheck(mint, last_checked DESC);

-- For portfolio-related view joins
CREATE INDEX idx_portfolio_mint_status 
ON portfolio(mint, status);