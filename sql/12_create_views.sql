-- sql/12_create_views.sql

-- View for combined tokens and tokens_backup
-- Prioritizes data from 'tokens' if a mint exists in both.
CREATE OR REPLACE VIEW v_tokens AS
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, is_active, last_trade,
    cooldown_until,
    '' as backup_reason, timestamp
FROM tokens
UNION ALL
SELECT
    mint, traderPublicKey, initialBuy, solAmount, bondingCurveKey, vTokensInBondingCurve,
    vSolInBondingCurve, marketCapSol, name, symbol, uri, website, telegram, twitter,
    socials_score, socials_last_checked, sol_price_usd, FALSE AS is_active, last_trade,
    cooldown_until,
    backup_reason, timestamp
FROM tokens_backup tb
WHERE NOT EXISTS (SELECT 1 FROM tokens t WHERE t.mint = tb.mint);

-- View for combined trades and trades_backup
CREATE OR REPLACE VIEW v_trades AS
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades
UNION ALL
SELECT
    signature, mint, tx_type, token_amount, sol_amount, price, bondingCurveKey,
    vTokensInBondingCurve, vSolInBondingCurve, marketCapSol, sol_price_usd, market_cap_calculated, timestamp
FROM trades_backup;

-- View for combined rugcheck and rugcheck_backup
-- Note: Getting the *latest* score per mint will be handled in the query using this view.
CREATE OR REPLACE VIEW v_rugcheck AS
SELECT mint, score, token_supply, last_checked FROM rugcheck
UNION ALL
SELECT mint, score, token_supply, last_checked FROM rugcheck_backup;

-- View for combined migrations and migrations_backup
CREATE OR REPLACE VIEW v_migrations AS
SELECT 
    signature,
    mint,
    txType,
    pool,
    timestamp,
    NULL AS backup_timestamp,
    'active' AS record_source
FROM 
    migrations

UNION ALL

SELECT 
    signature,
    mint,
    txType,
    pool,
    timestamp,
    backup_timestamp,
    'backup' AS record_source
FROM 
    migrations_backup;


-- View for combined dexscreener_data and dexscreener_data_backup
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data
UNION ALL
SELECT
    id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd,
    liquidity_usd, market_cap, fdv,
    volume_m5, volume_h1, volume_h6, volume_h24,
    price_change_m5, price_change_h1, price_change_h6, price_change_h24,
    buys_m5, sells_m5, buys_h1, sells_h1,
    buys_h6, sells_h6, buys_h24, sells_h24,
    full_response
FROM dexscreener_data_backup;


-- Creates unified views for market data from both Pump.fun and DEX Screener.

-- First, a helper view for all Dexscreener data (live + backup).
CREATE OR REPLACE VIEW v_dexscreener_data AS
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data
UNION ALL
SELECT id, pair_address, mint_address, timestamp, price_usd, price_native, sol_price_usd, liquidity_usd, market_cap, fdv, volume_m5, volume_h1, volume_h6, volume_h24, price_change_m5, price_change_h1, price_change_h6, price_change_h24, buys_m5, sells_m5, buys_h1, sells_h1, buys_h6, sells_h6, buys_h24, sells_h24, full_response FROM dexscreener_data_backup;

-- ===================================================================================
--  HISTORICAL UNIFIED VIEW (Includes Backups via v_* views)
--  PURPOSE: For backtesting, GA/RL training, and full historical analysis.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_historical AS
SELECT mint, timestamp, tx_type, token_amount, sol_amount, price AS price_sol, marketCapSol AS market_cap_sol, market_cap_calculated as market_cap_usd, 'PUMP' AS data_source
FROM v_trades -- Querying backup-inclusive view
WHERE price IS NOT NULL AND price > 0 AND sol_amount > 0 AND token_amount > 0
UNION ALL
SELECT mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount, (market_cap / price_usd) * (price_usd / sol_price_usd) AS sol_amount, (price_usd / sol_price_usd) AS price_sol, (market_cap / sol_price_usd) AS market_cap_sol, market_cap AS market_cap_usd, 'DEXSCREENER' AS data_source
FROM v_dexscreener_data; -- Querying backup-inclusive view

-- ===================================================================================
--  LIVE-ONLY UNIFIED VIEW (Excludes Backups)
--  PURPOSE: For fast, forward-looking queries driving live trade decisions.
-- ===================================================================================
CREATE OR REPLACE VIEW v_unified_market_ticks_live AS
SELECT mint, timestamp, tx_type, token_amount, sol_amount, price AS price_sol, marketCapSol AS market_cap_sol, market_cap_calculated as market_cap_usd, 'PUMP' AS data_source
FROM trades -- Querying LIVE table
WHERE price IS NOT NULL AND price > 0 AND sol_amount > 0 AND token_amount > 0
UNION ALL
SELECT mint_address AS mint, timestamp, 'snapshot' AS tx_type, NULL AS token_amount, (market_cap / price_usd) * (price_usd / sol_price_usd) AS sol_amount, (price_usd / sol_price_usd) AS price_sol, (market_cap / sol_price_usd) AS market_cap_sol, market_cap AS market_cap_usd, 'DEXSCREENER' AS data_source
FROM dexscreener_data; -- Querying LIVE table