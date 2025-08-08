# rl_tools/feature_engineering.py
"""
Shared utility function for RL data feature engineering.
"""
import pandas as pd
import numpy as np

def generate_feature_rich_ohlcv(
    mint: str,
    mint_trades: pd.DataFrame,
    rugcheck_df: pd.DataFrame,
    token_info_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Takes raw data for a SINGLE token and processes it into a feature-rich
    OHLCV format, correctly handling time-aware joins.
    """
    if mint_trades.empty:
        return pd.DataFrame()
        
    mint_trades = mint_trades.set_index('timestamp').sort_index()

    # Resample to 5s OHLCV
    resampler = mint_trades.resample('5s')
    ohlc = resampler['price_sol'].ohlc()
    volume = resampler['volume_usd'].sum()
    market_cap = resampler['market_cap_sol'].last()
    
    df = pd.concat([ohlc, volume, market_cap], axis=1)
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'marketCapSol']
    
    # Using modern assignment to avoid SettingWithCopyWarning
    df = df.interpolate(method='time')
    df.loc[:, 'Volume'] = df['Volume'].fillna(0)
    df.dropna(subset=['Close'], inplace=True)
    if df.empty:
        return pd.DataFrame()

    # Calculate Volatility
    log_returns = np.log(df['Close'] / df['Close'].shift(1))
    df['volatility'] = log_returns.rolling(window=12*5, min_periods=12).std() * np.sqrt(12*5)
    df['volatility'] = df['volatility'].fillna(0)

    # Time-aware merge for scores
    mint_rugcheck = rugcheck_df[rugcheck_df['mint'] == mint].set_index('timestamp').sort_index().drop_duplicates()
    if not mint_rugcheck.empty:
        df = pd.merge_asof(df, mint_rugcheck[['rugcheck_score']], left_index=True, right_index=True, direction='backward')
    else:
        df['rugcheck_score'] = np.nan

    mint_info_row = token_info_df[token_info_df['mint'] == mint]
    if not mint_info_row.empty:
        mint_info = mint_info_row.iloc[0]
        # Handle socials score with its own timestamp
        if 'socials_last_checked' in mint_info.index and pd.notna(mint_info['socials_last_checked']):
            socials_event = pd.DataFrame({'socials_score': [mint_info['socials_score']]}, index=[mint_info['socials_last_checked']])
            df = pd.merge_asof(df, socials_event, left_index=True, right_index=True, direction='backward')
        else:
            df['socials_score'] = np.nan
        # Handle token creation time
        if 'token_creation_time' in mint_info.index and pd.notna(mint_info['token_creation_time']):
            df['token_creation_time'] = mint_info['token_creation_time']
        else:
            df['token_creation_time'] = df.index.min() # Fallback
    else:
        df['socials_score'] = np.nan
        df['token_creation_time'] = df.index.min() # Fallback

    return df