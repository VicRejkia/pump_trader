-- Table to track training sessions and their outcomes
CREATE TABLE IF NOT EXISTS rl_training_sessions (
    session_id UUID PRIMARY KEY,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    hyperparameters JSONB,
    final_metrics JSONB,
    model_path TEXT,
    notes TEXT -- For manual notes on the training run
);

-- Table for detailed performance logging of the agent's actions
-- Partitioning by time is crucial for performance with large datasets
CREATE TABLE IF NOT EXISTS rl_agent_performance (
    timestamp TIMESTAMPTZ NOT NULL,
    token_mint TEXT NOT NULL,
    action_taken JSONB,
    reward REAL,
    observation JSONB,
    session_id UUID REFERENCES rl_training_sessions(session_id)
) PARTITION BY RANGE (timestamp);

-- Optional: Create partitions for the next few months as an example
-- In a production PostgreSQL environment, you would automate this process.
CREATE TABLE rl_agent_performance_y2025m08 PARTITION OF rl_agent_performance
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE rl_agent_performance_y2025m09 PARTITION OF rl_agent_performance
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

-- Create an index on the partitioned table
CREATE INDEX IF NOT EXISTS idx_rl_agent_performance_timestamp ON rl_agent_performance(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_rl_agent_performance_token_mint ON rl_agent_performance(token_mint);