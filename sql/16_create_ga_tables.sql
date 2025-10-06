-- FILE: schema.sql
--
-- This script sets up the database schema for storing results from the
-- Genetic Algorithm (GA) optimizer. It's designed for PostgreSQL.

-- Drop existing tables in reverse order of dependency to avoid foreign key errors.
/* 
DROP TABLE IF EXISTS ga_trades;
DROP TABLE IF EXISTS ga_backtests;
DROP TABLE IF EXISTS ga_solutions;
DROP TABLE IF EXISTS ga_runs;
*/

-- =================================================================
-- Table to track each individual execution of the optimizer.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_runs (
    run_id UUID PRIMARY KEY,
    -- The timestamp when this run was first recorded in the database.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE ga_runs IS 'Stores metadata for each complete execution of the GA optimizer.';
COMMENT ON COLUMN ga_runs.run_id IS 'Unique identifier for the optimization run.';


-- =================================================================
-- Table to store each unique solution (parameter set) for a given run.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_solutions (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES ga_runs(run_id) ON DELETE CASCADE,
    generation INT NOT NULL,
    solution_idx INT NOT NULL,
    -- Using JSONB is highly efficient for storing and querying parameter sets.
    parameters JSONB NOT NULL,
    -- Ensures that each solution within a generation is unique for a given run.
    UNIQUE(run_id, generation, solution_idx)
);

COMMENT ON TABLE ga_solutions IS 'Represents a single individual (a set of parameters) within a generation.';
COMMENT ON COLUMN ga_solutions.run_id IS 'Foreign key linking to the specific optimization run.';
COMMENT ON COLUMN ga_solutions.parameters IS 'The complete set of parameters for this solution.';

-- Index for quickly finding all solutions for a specific run.
CREATE INDEX IF NOT EXISTS idx_ga_solutions_run_id ON ga_solutions(run_id);
-- A GIN index allows for efficient querying of the JSONB parameter data.
CREATE INDEX IF NOT EXISTS idx_ga_solutions_parameters_gin ON ga_solutions USING GIN(parameters);


-- =================================================================
-- Table to store the results of a backtest for a given solution on a specific token.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_backtests (
    id SERIAL PRIMARY KEY,
    solution_id INT NOT NULL REFERENCES ga_solutions(id) ON DELETE CASCADE,
    mint_tested TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT, -- Populated only if status is 'failed'
    
    -- Performance Metrics
    final_portfolio_value NUMERIC(20, 10),
    total_pnl NUMERIC(20, 10),
    total_return_pct NUMERIC(20, 10),
    win_rate NUMERIC(10, 5),
    profit_factor NUMERIC(20, 10),
    max_drawdown NUMERIC(10, 5),
    total_trades INT,
    
    -- Simulation Metadata
    simulation_start_ts TIMESTAMPTZ,
    simulation_end_ts TIMESTAMPTZ,
    simulation_end_reason TEXT,
    
    -- Ensures a solution is only tested once per mint.
    UNIQUE(solution_id, mint_tested)
);

COMMENT ON TABLE ga_backtests IS 'Stores the summary results of a single backtest simulation.';
COMMENT ON COLUMN ga_backtests.solution_id IS 'Foreign key linking to the solution that was tested.';
COMMENT ON COLUMN ga_backtests.mint_tested IS 'The token mint address used in this backtest.';

-- Index for quickly finding all backtests for a given solution.
CREATE INDEX IF NOT EXISTS idx_ga_backtests_solution_id ON ga_backtests(solution_id);
-- Index for quickly finding high-performing backtests.
CREATE INDEX IF NOT EXISTS idx_ga_backtests_final_portfolio_value ON ga_backtests(final_portfolio_value DESC);


-- =================================================================
-- Table to store every individual trade from a backtest.
-- =================================================================
CREATE TABLE IF NOT EXISTS ga_trades (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INT NOT NULL REFERENCES ga_backtests(id) ON DELETE CASCADE,
    
    -- Trade Details
    "timestamp" TIMESTAMPTZ NOT NULL,
    "type" TEXT NOT NULL, -- 'buy' or 'sell'
    price NUMERIC(30, 20) NOT NULL,
    amount_sol NUMERIC(20, 10),
    amount_tokens NUMERIC(30, 10),
    reason TEXT,
    pnl NUMERIC(20, 10)
);

COMMENT ON TABLE ga_trades IS 'Stores every individual trade action from all backtest histories.';
COMMENT ON COLUMN ga_trades.backtest_id IS 'Foreign key linking to the backtest this trade belongs to.';

-- Index for quickly retrieving all trades for a specific backtest.
CREATE INDEX IF NOT EXISTS idx_ga_trades_backtest_id ON ga_trades(backtest_id);
-- Index for time-series analysis of trades.
CREATE INDEX IF NOT EXISTS idx_ga_trades_timestamp ON ga_trades("timestamp" DESC);