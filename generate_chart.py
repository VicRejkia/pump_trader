"""
Pump.fun Trader - Advanced Charting Dashboard

This script launches a Dash web application to visualize trading data
for tokens in the active portfolio. It connects to the bot's PostgreSQL database,
fetches token data, generates OHLCV candles for all tokens, calculates indicators,
and displays an interactive, multi-paned chart that accurately reflects the bot's trading logic.

This script is designed to be run from the root of your project directory.
"""
import os
from dotenv import load_dotenv
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from psycopg2.extras import DictCursor

# --- Load Environment Variables ---
load_dotenv()

# --- Project-Specific Imports ---
try:
    from bot_logger import logger, setup_logging
    from database_handler import DatabaseClient
    from config.config import (
        RSI_PERIOD, TREND_REVERSAL_RSI_NEUTRAL_LEVEL, ADAPTIVE_RSI_STRONG_LEVEL, ADAPTIVE_RSI_EXTREME_LEVEL,
        BBANDS_PERIOD, BBANDS_STD_DEV,
        FAST_EMA_PERIOD, SLOW_EMA_PERIOD, ADAPTIVE_ATR_PERIOD,
        MIN_CANDLE_DATA_FOR_INDICATORS
    )
    from utils import calculate_trend_indicators
except ImportError as e:
    print(f"Error: Could not import necessary modules. {e}")
    print("Please ensure this script is run from the root directory of the pump_trader project.")
    exit(1)

# --- Logger and DB Client Initialization ---
setup_logging()
db_client = DatabaseClient()
db_pool = db_client.get_sync_connection_pool()


# --- Database & Data Functions ---

def get_active_portfolio_tokens():
    """Fetches a list of unique tokens currently active in the portfolio."""
    query = """
    SELECT DISTINCT
        p.mint AS token_address,
        COALESCE(t.symbol, t.name, p.mint) AS token_symbol,
        p.mint
    FROM portfolio p
    LEFT JOIN tokens t ON p.mint = t.mint
    WHERE p.status = 'active'
    ORDER BY token_symbol;
    """
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query)
            tokens = cursor.fetchall()
            return [dict(t) for t in tokens]
    except Exception as e:
        logger.error(f"Error fetching active portfolio tokens: {e}", exc_info=True)
        return []
    finally:
        if conn:
            db_pool.putconn(conn)

def get_all_trades_for_token(token_address):
    """Fetches all buy and sell transactions for a token from the portfolio table."""
    query = "SELECT timestamp, price AS price_sol, tx_type AS trade_type FROM portfolio WHERE mint = %s ORDER BY timestamp;"
    conn = None
    try:
        conn = db_pool.getconn()
        df = pd.read_sql_query(query, conn, params=(token_address,))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price_sol'] = pd.to_numeric(df['price_sol'], errors='coerce')
        return df
    except Exception as e:
        logger.error(f"Error fetching portfolio trades for {token_address}: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn:
            db_pool.putconn(conn)

def check_if_migrated(token_address):
    """Checks if a token's data_source is 'DEXSCREENER'."""
    query = "SELECT data_source FROM tokens WHERE mint = %s LIMIT 1"
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, (token_address,))
            result = cursor.fetchone()
            return result and result['data_source'] == 'DEXSCREENER'
    except Exception as e:
        logger.error(f"Error checking migration status for {token_address}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            db_pool.putconn(conn)

def get_trade_ticks(token_address, is_migrated):
    """Fetches raw trade ticks from the appropriate source."""
    if is_migrated:
        query = "SELECT timestamp, price_native AS price, (volume_m5 / sol_price_usd) AS volume FROM dexscreener_data WHERE mint_address = %s AND sol_price_usd > 0 ORDER BY timestamp"
    else:
        query = "SELECT timestamp, price, sol_amount as volume FROM trades WHERE mint = %s ORDER BY timestamp"
    
    conn = None
    try:
        conn = db_pool.getconn()
        df = pd.read_sql_query(query, conn, params=(token_address,))
        if df.empty: return pd.DataFrame()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df.dropna(subset=['price', 'volume'], inplace=True)
        return df
    except Exception as e:
        logger.error(f"Error fetching trade ticks for {token_address}: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if conn:
            db_pool.putconn(conn)

def generate_ohlcv_from_ticks(df_ticks, timeframe='1Min'):
    """Generates an OHLCV DataFrame from a tick data DataFrame."""
    if df_ticks.empty or 'price' not in df_ticks.columns:
        return pd.DataFrame()
    df_ticks = df_ticks.set_index('timestamp')
    ohlc = df_ticks['price'].resample(timeframe).ohlc()
    volume = df_ticks['volume'].resample(timeframe).sum()
    df_ohlcv = pd.concat([ohlc, volume], axis=1)
    df_ohlcv.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    df_ohlcv.reset_index(inplace=True)
    df_ohlcv.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
    return df_ohlcv

# --- Dash App Layout ---
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
app.title = "Pump.fun Trader Dashboard"
app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#AAAAAA'}, children=[
    dcc.Store(id='selected-token-store', data=None),
    dcc.Interval(id='token-list-interval', interval=30 * 1000, n_intervals=0),
    html.Div([html.H1('Pump.fun Trader - Chart Analysis', style={'textAlign': 'center', 'color': '#FFFFFF', 'margin': '20px'})]),
    html.Div(className='row', style={'margin': '10px'}, children=[
        html.Div(className='three columns', style={'padding': '10px', 'backgroundColor': '#1E1E1E', 'borderRadius': '5px'}, children=[
            html.H4('Active Portfolio', style={'color': '#FFFFFF', 'borderBottom': '1px solid #444444', 'paddingBottom': '10px'}),
            dcc.RadioItems(id='token-list', options=[], value=None, labelStyle={'display': 'block', 'padding': '5px', 'cursor': 'pointer', 'borderBottom': '1px solid #333333'}, style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #444444', 'borderRadius': '5px'}),
            html.H4('Indicator Settings', style={'color': '#FFFFFF', 'marginTop': '30px', 'borderBottom': '1px solid #444444', 'paddingBottom': '10px'}),
            html.Div(id='indicator-settings-display', style={'fontSize': '12px', 'lineHeight': '1.6', 'wordBreak': 'break-all'})
        ]),
        html.Div(className='nine columns', children=[dcc.Graph(id='main-chart', figure={}, config={'responsive': True}, style={'height': '80vh'})])
    ])
])

# --- Callbacks ---
@app.callback(
    [Output('token-list', 'options'), Output('token-list', 'value'), Output('selected-token-store', 'data')],
    Input('token-list-interval', 'n_intervals'),
    State('selected-token-store', 'data')
)
def update_token_list(n_intervals, stored_token_address):
    logger.info("Refreshing active token list...")
    tokens = get_active_portfolio_tokens()
    if not tokens:
        logger.info("No active tokens found.")
        return [], None, None
    options = [{'label': f"{t.get('token_symbol', '???')} ({t.get('mint')})", 'value': t['token_address']} for t in tokens]
    active_addresses = [t['token_address'] for t in tokens]
    new_selected_value = stored_token_address if stored_token_address and stored_token_address in active_addresses else (options[0]['value'] if options else None)
    return options, new_selected_value, new_selected_value

@app.callback(
    Output('selected-token-store', 'data', allow_duplicate=True),
    Input('token-list', 'value'),
    prevent_initial_call=True
)
def store_selected_token(selected_token_address):
    return selected_token_address

@app.callback(
    [Output('main-chart', 'figure'), Output('indicator-settings-display', 'children')],
    Input('selected-token-store', 'data')
)
def update_chart(selected_token_address):
    if not selected_token_address:
        return go.Figure().update_layout(title="Please select a token", template='plotly_dark'), "Select a token."

    logger.info(f"Generating chart for token: {selected_token_address}")
    
    config_params = {
        'RSI_PERIOD': RSI_PERIOD, 'BBANDS_PERIOD': BBANDS_PERIOD, 'BBANDS_STD_DEV': BBANDS_STD_DEV,
        'FAST_EMA_PERIOD': FAST_EMA_PERIOD, 'SLOW_EMA_PERIOD': SLOW_EMA_PERIOD,
        'ADAPTIVE_ATR_PERIOD': ADAPTIVE_ATR_PERIOD, 'MIN_CANDLE_DATA_FOR_INDICATORS': MIN_CANDLE_DATA_FOR_INDICATORS
    }
    
    settings_display = [
        html.P(f"Token: {selected_token_address}", style={'color': '#FFFFFF', 'fontWeight': 'bold'}),
        html.H5("Trend Reversal (Buy)", style={'color': '#4682B4', 'marginTop': '10px'}),
        html.P(f"BBands: ({BBANDS_PERIOD}, {BBANDS_STD_DEV})"),
        html.P(f"EMA Cross: ({FAST_EMA_PERIOD}, {SLOW_EMA_PERIOD})"),
        html.P("VWAP (if calculated)"),
        html.H5("Dynamic Selling & Logic", style={'color': '#FFD700', 'marginTop': '10px'}),
        html.P(f"EMA Cross: ({FAST_EMA_PERIOD}, {SLOW_EMA_PERIOD})"),
        html.P(f"RSI-Adaptive ATR: ({ADAPTIVE_ATR_PERIOD})"),
        html.P(f"RSI Levels (Neutral/Strong/Extreme): {TREND_REVERSAL_RSI_NEUTRAL_LEVEL} / {ADAPTIVE_RSI_STRONG_LEVEL} / {ADAPTIVE_RSI_EXTREME_LEVEL}")
    ]
    
    is_migrated = check_if_migrated(selected_token_address)
    df_ticks = get_trade_ticks(selected_token_address, is_migrated)
    
    if df_ticks.empty:
        return go.Figure().update_layout(title=f"No trade data found for token: {selected_token_address}", template='plotly_dark'), settings_display

    df_ohlcv = generate_ohlcv_from_ticks(df_ticks, timeframe='1Min')
    df_indicators = calculate_trend_indicators(df_ohlcv.copy(), config_params)
    df_trades = get_all_trades_for_token(selected_token_address)

    chart_title = "Price & Trend Indicators"
    if not is_migrated:
        chart_title += " (Pre-Migration)"
    
    fig = build_unified_chart(df_indicators if not df_indicators.empty else df_ohlcv, df_trades, config_params, selected_token_address, chart_title)
        
    return fig, settings_display

def build_unified_chart(df, df_trades, settings, token_address, chart_title):
    """Builds a unified, multi-pane chart for any token with OHLCV data."""
    row_config, row_heights, subplot_titles = {'main': 1}, [0.6], [chart_title]
    rows_total = 1
    
    if 'Volume' in df.columns and not df['Volume'].empty:
        rows_total += 1; row_config['volume'] = rows_total; row_heights.append(0.1); subplot_titles.append("Volume")
    
    rsi_col = f'RSI_{settings["RSI_PERIOD"]}'
    if rsi_col in df.columns:
        rows_total += 1; row_config['rsi'] = rows_total; row_heights.append(0.15); subplot_titles.append("RSI")
        
    atr_col = f'ATRr_{settings["ADAPTIVE_ATR_PERIOD"]}'
    if atr_col in df.columns:
        rows_total += 1; row_config['atr'] = rows_total; row_heights.append(0.15); subplot_titles.append("ATR (for Dynamic Sell Logic)")
        
    fig = make_subplots(rows=rows_total, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights, subplot_titles=subplot_titles)
    
    main_row = row_config['main']
    fig.add_trace(go.Candlestick(x=df['timestamp'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Candles'), row=main_row, col=1)
    
    bb_lower_col = f'BBL_{settings["BBANDS_PERIOD"]}_{settings["BBANDS_STD_DEV"]}'
    bb_upper_col = f'BBU_{settings["BBANDS_PERIOD"]}_{settings["BBANDS_STD_DEV"]}'
    if bb_lower_col in df.columns and bb_upper_col in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[bb_upper_col], name='BB Upper', line=dict(color='rgba(100, 100, 255, 0.4)', width=1)), row=main_row, col=1)
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[bb_lower_col], name='BB Lower', line=dict(color='rgba(100, 100, 255, 0.4)', width=1), fill='tonexty', fillcolor='rgba(100, 100, 255, 0.05)'), row=main_row, col=1)
    
    if 'EMA_fast' in df.columns: fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_fast'], name=f'EMA {settings["FAST_EMA_PERIOD"]}', line=dict(color='aqua', width=1.5)), row=main_row, col=1)
    if 'EMA_slow' in df.columns: fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_slow'], name=f'EMA {settings["SLOW_EMA_PERIOD"]}', line=dict(color='magenta', width=1.5)), row=main_row, col=1)
    if 'VWAP' in df.columns: fig.add_trace(go.Scatter(x=df['timestamp'], y=df['VWAP'], name='VWAP', line=dict(color='orange', width=1, dash='dot')), row=main_row, col=1)

    if not df_trades.empty:
        buys, sells = df_trades[df_trades['trade_type'] == 'buy'], df_trades[df_trades['trade_type'] == 'sell']
        fig.add_trace(go.Scatter(x=buys['timestamp'], y=buys['price_sol'], name='Buys', mode='markers', marker=dict(color='lime', symbol='triangle-up', size=10, line=dict(width=1, color='DarkGreen'))), row=main_row, col=1)
        fig.add_trace(go.Scatter(x=sells['timestamp'], y=sells['price_sol'], name='Sells', mode='markers', marker=dict(color='red', symbol='triangle-down', size=10, line=dict(width=1, color='DarkRed'))), row=main_row, col=1)
    
    if 'volume' in row_config:
        fig.add_trace(go.Bar(x=df['timestamp'], y=df['Volume'], name='Volume', marker=dict(color='rgba(255, 255, 255, 0.5)')), row=row_config['volume'], col=1)
    
    if 'rsi' in row_config:
        rs_row = row_config['rsi']
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[rsi_col], name='RSI', line=dict(color='cyan')), row=rs_row, col=1)
        fig.add_hline(y=ADAPTIVE_RSI_EXTREME_LEVEL, line=dict(color='red', dash='dot', width=1), annotation_text="Extreme", annotation_position="bottom right", row=rs_row, col=1)
        fig.add_hline(y=ADAPTIVE_RSI_STRONG_LEVEL, line=dict(color='orange', dash='dot', width=1), annotation_text="Strong", annotation_position="bottom right", row=rs_row, col=1)
        fig.add_hline(y=TREND_REVERSAL_RSI_NEUTRAL_LEVEL, line=dict(color='green', dash='dot', width=1), annotation_text="Neutral", annotation_position="bottom right", row=rs_row, col=1)
        fig.update_yaxes(range=[0, 100], row=rs_row, col=1)
    
    if 'atr' in row_config:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[atr_col], name='ATR', line=dict(color='goldenrod')), row=row_config['atr'], col=1)

    fig.update_layout(title_text=f"Chart for {token_address}", xaxis_rangeslider_visible=False, template='plotly_dark', height=850, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    for i in range(1, rows_total + 1): fig.update_yaxes(autorange=True, fixedrange=False, row=i, col=1)
    if rows_total > 1: fig.update_xaxes(showticklabels=False, row=1, col=1)
    return fig

# --- Run the App ---
if __name__ == '__main__':
    logger.info("Starting Dash server on http://127.0.0.1:8050")
    app.run(debug=True, port=8050)