-- Create the configurations table
CREATE TABLE IF NOT EXISTS configurations (
    key TEXT PRIMARY KEY,
    value TEXT,
    type TEXT NOT NULL CHECK (type IN ('int', 'float', 'bool', 'str', 'list')),
    description TEXT, -- Optional: for human-readable descriptions
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Trigger to update last_updated timestamp automatically
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.last_updated = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_configurations_last_updated
BEFORE UPDATE ON configurations
FOR EACH ROW
EXECUTE FUNCTION update_last_updated_column();

CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations(key);