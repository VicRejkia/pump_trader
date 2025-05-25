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