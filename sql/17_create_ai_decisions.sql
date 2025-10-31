-- sql/16_create_ai_decisions.sql

CREATE TABLE IF NOT EXISTS ai_decisions (
    id SERIAL PRIMARY KEY,
    mint TEXT NOT NULL,
    evaluation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_context TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('BUY', 'SELL', 'HOLD')),
    confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    explanation TEXT,
    prompt_hash TEXT,                          -- Optional
    data_snapshot JSONB,                       -- Optional

    CONSTRAINT fk_ai_decision_mint
        FOREIGN KEY(mint)
        REFERENCES tokens(mint)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ai_decisions_mint_timestamp ON ai_decisions(mint, evaluation_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_timestamp ON ai_decisions(evaluation_timestamp DESC);

-- Optional: Backup table (if desired for AI decisions)
CREATE TABLE IF NOT EXISTS ai_decisions_backup (
    LIKE ai_decisions INCLUDING ALL
);
ALTER TABLE ai_decisions_backup ADD COLUMN IF NOT EXISTS backup_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE ai_decisions_backup ALTER COLUMN evaluation_timestamp DROP DEFAULT; -- Remove default if copying data