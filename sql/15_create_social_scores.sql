-- sql/15_create_social_scores.sql

-- Create a table to store historical and detailed social scoring data
CREATE TABLE IF NOT EXISTS social_scores (
    id SERIAL PRIMARY KEY,
    mint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score_type TEXT NOT NULL, -- e.g., 'INITIAL', 'TELEGRAM_UPDATE', 'WEBSITE_UPDATE'
    score_value INTEGER NOT NULL,
    details JSONB, -- For storing specific metrics like member count, online count, etc.
    CONSTRAINT fk_mint
        FOREIGN KEY(mint)
        REFERENCES tokens(mint)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_social_scores_mint_timestamp ON social_scores(mint, timestamp DESC);

-- Create the backup table for social_scores
CREATE TABLE IF NOT EXISTS social_scores_backup (
    id INTEGER NOT NULL,
    mint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    score_type TEXT NOT NULL,
    score_value INTEGER NOT NULL,
    details JSONB,
    backup_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(id) -- Primary key to handle conflicts on backup
);

-- Add indexes for querying backups
CREATE INDEX IF NOT EXISTS idx_social_scores_backup_mint_timestamp ON social_scores_backup(mint, timestamp DESC);

-- View to combine live and backed-up social score entries
CREATE OR REPLACE VIEW v_social_scores AS
SELECT
    id,
    mint,
    timestamp,
    score_type,
    score_value,
    details,
    NULL AS backup_timestamp,
    'active' as record_source
FROM
    social_scores

UNION ALL

SELECT
    id,
    mint,
    timestamp,
    score_type,
    score_value,
    details,
    backup_timestamp,
    'backup' as record_source
FROM
    social_scores_backup;