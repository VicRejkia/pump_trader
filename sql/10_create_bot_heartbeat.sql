-- sql/10_create_bot_heartbeat.sql
CREATE TABLE IF NOT EXISTS bot_heartbeat (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    event_type TEXT DEFAULT 'heartbeat', -- e.g., 'heartbeat', 'config_update', 'shutdown_signal'
    details JSONB -- Optional: for storing details about the event, like which config was updated
);

CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_timestamp ON bot_heartbeat(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bot_heartbeat_event_type ON bot_heartbeat(event_type);