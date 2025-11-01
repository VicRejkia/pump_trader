-- Creates the extension if it doesn't exist (you've already done this, but it's safe to include)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the table to store AI decision snapshots for RAG
CREATE TABLE IF NOT EXISTS ai_decision_memory (
    id SERIAL PRIMARY KEY,
    mint TEXT NOT NULL,
    evaluation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_context TEXT,
    decision TEXT,
    confidence INTEGER,
    explanation TEXT,
    
    -- This is the document that gets queried (the text summary)
    situation_summary TEXT, 
    
    -- This is the vector embedding for the summary
    -- all-MiniLM-L6-v2 produces 384-dimensional vectors
    embedding vector(384), 
    
    -- Store source, mcap, volatility etc. as structured data
    metadata JSONB 
);

-- Index for fast retrieval by mint
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_mint ON ai_decision_memory(mint);

-- Index for fast retrieval by timestamp
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_timestamp ON ai_decision_memory(evaluation_timestamp DESC);

-- Create a vector index for fast similarity search (ANN)
-- This is crucial for performance.
-- We use an IVFFlat index, a good all-around choice.
-- 'lists = 100' is a good starting point if you expect < 1 million records.
-- You can tune this later.
CREATE INDEX IF NOT EXISTS idx_ai_decision_memory_embedding_ivfflat ON ai_decision_memory 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Note: Building the index can take time. You may need to run
-- VACUUM ANALYZE ai_decision_memory;
-- periodically after large inserts.