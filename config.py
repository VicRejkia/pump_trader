"""
Configuration constants and settings for the trading bot.
"""

from datetime import timedelta

# Trading configuration
SOL_TO_BUY = 0.1
DEFAULT_STOP_LOSS = 0.45       # 45% stop loss threshold
DEFAULT_TRAILING_TP = 0.75     # 75% trailing take profit threshold
FIRST_SELL_PERCENT = 0.3       # Sell 30% of tokens initially
PROFIT_MARGIN = 0.10           # 10% profit target
DEFAULT_BUY_FEE = 0.001        # Fee for buying in SOL
DEFAULT_BUY_TIP = 0.001        # Tip for buying in SOL
DEFAULT_SELL_FEE = 0.001       # Fee for selling in SOL
DEFAULT_SELL_TIP = 0.001       # Tip for selling in SOL

# Database settings
DB_URL = "postgresql://bot_user:tr4d1ng_b0t_us3r@localhost:5432/trading_bot?options=-c%20timezone%3Dutc"

INACTIVITY_PERIOD = timedelta(minutes=5)
MIN_MARKET_CAP = 5.0           # Minimum market cap (in SOL)

# Subscription tracking
ACTIVE_SUBSCRIPTIONS = set()
NEW_TOKEN_SUBSCRIPTION = False

# Token and API configurations
TOTAL_SUPPLY = 1000000000   # Assumed total supply if not provided
PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"
RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens"
RUGCHECK_RATE_LIMIT = 10       # 10 requests per minute
RUGCHECK_INTERVAL = 60         # 60 seconds interval for RugCheck checks

# SOL price configuration
SOL_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# Trading thresholds
DEFAULT_SCORE_THRESHOLD = 581
DEFAULT_VOLUME_THRESHOLD = 10000
DEFAULT_MARKETCAP_THRESHOLD = 10000
MIN_VOLATILITY = 0.00000001       # Minimum volatility threshold
MAX_DRAWDOWN_SOL = 10          # Maximum allowed 24h loss in SOL
DRAWDOWN_CHECK_INTERVAL = 3600  # Drawdown check interval (seconds)
