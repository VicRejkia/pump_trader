# FILE: GA_Optimizer/ga_dashboard.py
# **FIX:** This version corrects a NumPy data type error and uses the
# correct parameter for stretching dataframes to the full container width.
# Make sure to have 'psycopg2-binary' installed: pip install psycopg2-binary

# run it with: streamlit run GA_Optimizer/ga_dashboard.py

import os
from pathlib import Path
import json

import psycopg2
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="GA Optimizer Dashboard")

# --- Database Connection (Synchronous with psycopg2) ---
@st.cache_resource
def init_connection():
    """Initializes a connection to the PostgreSQL database."""
    script_location = Path(__file__).resolve().parent
    project_root = script_location.parent
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    raw_db_host = os.getenv("DB_HOST")
    db_host_val, db_port_val = (None, 5432)
    if raw_db_host:
        if ":" in raw_db_host:
            host, port_str = raw_db_host.split(":")
            db_host_val, db_port_val = (host, int(port_str))
        else:
            db_host_val = raw_db_host
    
    conn = psycopg2.connect(
        host=db_host_val,
        port=db_port_val,
        dbname=os.getenv("DB_DATABASE"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

# --- Data Fetching Functions (Synchronous) ---
# No changes needed in the data fetching functions themselves
def get_runs(conn):
    """Fetches all run_ids from the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT run_id, created_at FROM ga_runs ORDER BY created_at DESC")
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

def get_ranked_solutions(conn, run_id):
    """Fetches and ranks all solutions for a given run by their average performance."""
    query = """
    SELECT
        s.id as solution_id, s.generation, AVG(b.final_portfolio_value) as avg_portfolio,
        AVG(b.win_rate) as avg_win_rate, AVG(b.profit_factor) as avg_profit_factor,
        SUM(b.total_trades) as total_trades, COUNT(b.id) as backtest_count, s.parameters
    FROM ga_solutions s JOIN ga_backtests b ON s.id = b.solution_id
    WHERE s.run_id = %s AND b.status = 'success'
    GROUP BY s.id, s.generation, s.parameters ORDER BY avg_portfolio DESC;
    """
    with conn.cursor() as cur:
        cur.execute(query, (run_id,))
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

def get_solution_backtests(conn, solution_id):
    """Fetches all individual backtest results for a specific solution."""
    query = """
    SELECT id as backtest_id, mint_tested, final_portfolio_value, win_rate, profit_factor, total_trades
    FROM ga_backtests WHERE solution_id = %s AND status = 'success' ORDER BY final_portfolio_value DESC;
    """
    with conn.cursor() as cur:
        cur.execute(query, (solution_id,))
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

def get_trade_history(conn, backtest_id):
    """Fetches the complete trade history for a single backtest."""
    query = 'SELECT "timestamp", "type", price, amount_sol, amount_tokens, reason, pnl FROM ga_trades WHERE backtest_id = %s ORDER BY "timestamp" ASC;'
    with conn.cursor() as cur:
        cur.execute(query, (backtest_id,))
        records = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(records, columns=columns)

# --- Main Application Logic ---
def main():
    st.title("📈 Genetic Algorithm Performance Dashboard")

    conn = init_connection()
    runs_df = get_runs(conn)

    if runs_df.empty:
        st.error("No runs found in the database. Please run the optimizer first.")
        st.stop()

    st.sidebar.header("Navigation")
    runs_df['display'] = runs_df.apply(lambda row: f"{row['created_at'].strftime('%Y-%m-%d %H:%M')} ({str(row['run_id'])[:8]})", axis=1)
    selected_display = st.sidebar.selectbox("Select Optimization Run", runs_df['display'])
    
    selected_run_id = runs_df[runs_df['display'] == selected_display]['run_id'].iloc[0]

    st.header(f"Run Overview: {str(selected_run_id)[:8]}...")
    
    with st.spinner("Fetching optimization data..."):
        solutions_df = get_ranked_solutions(conn, selected_run_id)

    if solutions_df.empty:
        st.warning("This run has no successful backtests to analyze.")
        st.stop()

    best_solution = solutions_df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Top Portfolio Value", f"{float(best_solution['avg_portfolio']):.2f} SOL")
    col2.metric("Total Solutions Tested", f"{len(solutions_df)}")
    col3.metric("Best Solution's Win Rate", f"{float(best_solution['avg_win_rate']):.2f}%")

    st.subheader("Ranked Strategies")
    st.info("Click on any row in the table below to load its details.")
    
    display_cols = ['solution_id', 'generation', 'avg_portfolio', 'avg_win_rate', 'avg_profit_factor', 'total_trades', 'backtest_count']
    
    # **FIX:** Use `width='stretch'` to make the dataframe stretch to the full width.
    st.dataframe(
        solutions_df[display_cols],
        width='stretch',
        on_select="rerun",
        selection_mode="single-row",
        key="ranked_strategies_df"
    )

    selection = st.session_state.ranked_strategies_df.selection

    selected_solution_id = None
    if selection["rows"]:
        selected_index = selection["rows"][0]
        # **FIX:** Cast the numpy.int64 to a standard Python int.
        selected_solution_id = int(solutions_df.iloc[selected_index]['solution_id'])
    else:
        # **FIX:** Cast this default value as well for consistency.
        selected_solution_id = int(best_solution['solution_id'])

    st.subheader("Strategy Deep Dive")
    st.markdown(f"#### Details for Solution ID: `{selected_solution_id}`")

    if selected_solution_id:
        solution_params = solutions_df.loc[solutions_df['solution_id'] == selected_solution_id, 'parameters'].iloc[0]
        
        with st.expander(f"Parameters", expanded=True):
            st.json(solution_params)

        st.write("**Individual Backtest Performance** (one test per token)")
        backtests_df = get_solution_backtests(conn, selected_solution_id)
        st.dataframe(backtests_df, width='stretch')

        if not backtests_df.empty:
            selected_backtest_id = st.selectbox(
                "Select a 'backtest_id' to view its trade history:",
                backtests_df['backtest_id']
            )
            if selected_backtest_id:
                st.write(f"**Trade History for Backtest ID {selected_backtest_id}**")
                # **FIX:** Cast the selected backtest ID to int before passing it to the database function.
                trades_df = get_trade_history(conn, int(selected_backtest_id))
                st.dataframe(trades_df, width='stretch')

if __name__ == "__main__":
    main()