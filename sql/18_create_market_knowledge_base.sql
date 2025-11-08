CREATE TABLE IF NOT EXISTS market_knowledge_base (
    id SERIAL PRIMARY KEY,
    mint TEXT UNIQUE,
    summary TEXT,
    embedding vector(384), -- Same dimension as ai_decision_memory
    metadata JSONB, -- Store creator, reason, max_mcap, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mkt_kb_embedding_ivfflat ON market_knowledge_base 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);