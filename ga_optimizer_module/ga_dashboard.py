# FILE: ga_optimizer_module/ga_dashboard.py
# **MODIFIED:** This version adds a 'Run' axis to the parameter plot for easy
# identification, improves the layout, and uses the latest Streamlit APIs.

import os
from pathlib import Path
import json

import psycopg2
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go 

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

# --- Data Fetching Functions (Unchanged) ---
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
        st.error("No runs found in the database. Please run the optimizer and ingestion script first.")
        st.stop()
        
    runs_df['display'] = runs_df.apply(lambda row: f"{row['created_at'].strftime('%Y-%m-%d %H:%M')} ({str(row['run_id'])[:8]})", axis=1)

    # --- TABS FOR SINGLE AND COMPARISON VIEWS ---
    tab1, tab2 = st.tabs(["Single Run Analysis", "Cross-Run Comparison"])

    # --- TAB 1: ORIGINAL SINGLE RUN ANALYSIS VIEW ---
    with tab1:
        st.header("Single Run Deep Dive")
        selected_display = st.selectbox("Select Optimization Run", runs_df['display'])
        
        selected_run_id = runs_df[runs_df['display'] == selected_display]['run_id'].iloc[0]

        st.info(f"Analyzing Run ID: `{selected_run_id}`")
        
        with st.spinner("Fetching optimization data for selected run..."):
            solutions_df = get_ranked_solutions(conn, selected_run_id)

        if solutions_df.empty:
            st.warning("This run has no successful backtests to analyze.")
        else:
            best_solution = solutions_df.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Top Portfolio Value", f"{float(best_solution['avg_portfolio']):.2f} SOL")
            col2.metric("Total Solutions Tested", f"{len(solutions_df)}")
            col3.metric("Best Solution's Win Rate", f"{float(best_solution['avg_win_rate']):.2f}%")

            st.subheader("Ranked Strategies")
            st.text("Click on any row to load its details below.")
            
            display_cols = ['solution_id', 'generation', 'avg_portfolio', 'avg_win_rate', 'avg_profit_factor', 'total_trades', 'backtest_count']
            
            st.dataframe(
                solutions_df[display_cols],
                width='stretch',
                on_select="rerun",
                selection_mode="single-row",
                key="ranked_strategies_df"
            )

            selection = st.session_state.get('ranked_strategies_df', {}).get('selection', {})
            selected_solution_id = None
            if selection and selection.get("rows"):
                selected_index = selection["rows"][0]
                selected_solution_id = int(solutions_df.iloc[selected_index]['solution_id'])
            else:
                selected_solution_id = int(best_solution['solution_id'])

            st.subheader(f"Strategy Deep Dive (Solution ID: `{selected_solution_id}`)")

            if selected_solution_id:
                solution_params = solutions_df.loc[solutions_df['solution_id'] == selected_solution_id, 'parameters'].iloc[0]
                
                with st.expander(f"View Parameters", expanded=False):
                    st.json(solution_params)

                st.write("**Individual Backtest Performance**")
                backtests_df = get_solution_backtests(conn, selected_solution_id)
                st.dataframe(backtests_df, width='stretch')

                if not backtests_df.empty:
                    selected_backtest_id = st.selectbox(
                        "Select a 'backtest_id' to view trade history:",
                        backtests_df['backtest_id']
                    )
                    if selected_backtest_id:
                        st.write(f"**Trade History for Backtest ID {selected_backtest_id}**")
                        trades_df = get_trade_history(conn, int(selected_backtest_id))
                        st.dataframe(trades_df, width='stretch')

    # --- TAB 2: NEW CROSS-RUN COMPARISON VIEW ---
    with tab2:
        st.header("Compare Multiple Optimization Runs")
        selected_run_displays = st.multiselect(
            "Select 2 or more runs to compare:", 
            runs_df['display'],
            max_selections=5
        )

        if len(selected_run_displays) < 2:
            st.info("Please select at least two runs to generate a comparison.")
        else:
            run_ids_to_compare = runs_df[runs_df['display'].isin(selected_run_displays)]['run_id'].tolist()
            
            all_solutions_list = []
            best_solutions_data = [] 
            with st.spinner("Fetching and aggregating data for comparison..."):
                for run_id, display_name in zip(run_ids_to_compare, selected_run_displays):
                    run_solutions_df = get_ranked_solutions(conn, run_id)
                    if not run_solutions_df.empty:
                        run_solutions_df['run_display_name'] = display_name
                        all_solutions_list.append(run_solutions_df)
                        best_solution = run_solutions_df.iloc[0].to_dict()
                        best_solution['run_display_name'] = display_name
                        best_solutions_data.append(best_solution)

            if not all_solutions_list:
                st.warning("Could not fetch valid data for the selected runs.")
            else:
                st.subheader("Performance Distribution")
                st.markdown("This plot shows the distribution of the final portfolio value for all solutions in each run. It helps identify which run was consistently better, not just lucky with one outlier.")
                
                combined_df = pd.concat(all_solutions_list, ignore_index=True)
                fig_box = px.box(
                    combined_df, 
                    x='run_display_name', y='avg_portfolio', color='run_display_name',
                    points="all", title="Distribution of Average Portfolio Value Across Runs",
                    labels={"run_display_name": "Optimization Run", "avg_portfolio": "Average Final Portfolio (SOL)"}
                )
                st.plotly_chart(fig_box, use_container_width=True)

                st.subheader("Best Solution Parameter Comparison")
                st.markdown("This chart compares the best strategies found in each run. Each line represents a run, colored by its final portfolio value. Use the 'Run' axis on the left to identify which line corresponds to which run.")
                
                best_solutions_df = pd.DataFrame(best_solutions_data)
                params_unpacked = best_solutions_df['parameters'].apply(pd.Series)
                plot_df = pd.concat([best_solutions_df[['run_display_name', 'avg_portfolio']], params_unpacked], axis=1)

                all_possible_params = sorted([col for col in params_unpacked.columns if plot_df[col].nunique() > 1])
                default_params = [
                    'INITIAL_STOP_LOSS_PERCENT', 'FIRST_SELL_PERCENT', 'FIRST_SELL_PROFIT_MARGIN',
                    'TRAILING_STOP_LOSS_PERCENT', 'SECOND_TAKE_PROFIT_PERCENT', 'USE_DYNAMIC_SECOND_TP',
                    'MIN_VOLATILITY', 'DEFAULT_RUGCHECK_SCORE_THRESHOLD'
                ]
                default_selection = [p for p in default_params if p in all_possible_params]

                params_to_display = st.multiselect(
                    "Select parameters to display on the chart:",
                    options=all_possible_params,
                    default=default_selection
                )

                if params_to_display:
                    # --- NEW: Create a categorical axis for the Run Name ---
                    run_names = plot_df['run_display_name'].unique()
                    run_name_map = {name: i for i, name in enumerate(run_names)}
                    plot_df['run_idx'] = plot_df['run_display_name'].map(run_name_map)
                    
                    dimensions = [
                        {
                            'label': 'Run',
                            'tickvals': list(run_name_map.values()),
                            'ticktext': list(run_name_map.keys()),
                            'values': plot_df['run_idx']
                        }
                    ]
                    # Add the numeric parameter dimensions after the run name
                    dimensions.extend([{'label': param, 'values': plot_df[param]} for param in params_to_display])
                    
                    fig_parallel = go.Figure(data=
                        go.Parcoords(
                            line = dict(
                                color = plot_df['avg_portfolio'],
                                colorscale = 'Electric',
                                showscale = True,
                                colorbar = {'title': 'Avg Portfolio'},
                                cmin = plot_df['avg_portfolio'].min(),
                                cmax = plot_df['avg_portfolio'].max()
                            ),
                            dimensions = list(dimensions)
                        )
                    )
                    
                    fig_parallel.update_layout(
                        title='Comparison of Best Parameters by Performance',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        margin=dict(l=80, r=80, t=100, b=40) # Increased margins
                    )

                    st.plotly_chart(fig_parallel, use_container_width=True)
                else:
                    st.warning("Please select at least one parameter to display.")

if __name__ == "__main__":
    main()

