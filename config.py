"""
Configuration constants and settings for the trading bot.
"""

from datetime import timedelta

""" Configuration constants and settings for the trading bot. """
# PumpPortal
WS_HOST: str = "wss://pumpportal.fun/api/data"
MAX_SUBSCRIPTION_BATCH: int = 100  # For batch unsubscription

# Trading configuration
SOL_TO_BUY = 0.1                 # Amount of SOL to spend on each buy

# --- New Multi-Stage Sell Logic Configuration ---
INITIAL_STOP_LOSS_PERCENT = 50.0   # Initial SL as % below buy price (e.g., 25.0 for -25%)
INITIAL_TAKE_PROFIT_PERCENT = 50.0 # First TP as % above buy price (e.g., 50.0 for +50%)
FIRST_SELL_PERCENT = 50.0          # % of *initial* tokens to sell at First TP (e.g., 50.0 for 50%)
TRAILING_STOP_LOSS_PERCENT = 50.0  # Trailing SL % drop from highest price *after* First TP (e.g., 15.0 for -15%)
SECOND_TAKE_PROFIT_PERCENT = 200.0 # Second TP as % above buy price (e.g., 200.0 for +200%)

# --- Fees and Tips ---
DEFAULT_BUY_FEE = 0.001        # Fee for buying in SOL
DEFAULT_BUY_TIP = 0.001        # Tip for buying in SOL
DEFAULT_SELL_FEE = 0.001       # Fee for selling in SOL
DEFAULT_SELL_TIP = 0.001       # Tip for selling in SOL


# Trading thresholds
DEFAULT_RUGCHECK_SCORE_THRESHOLD = 600
DEFAULT_SOCIAL_SCORE_THRESHOLD = 50
DEFAULT_VOLUME_THRESHOLD = 10000
DEFAULT_MARKETCAP_THRESHOLD = 10000
MIN_VOLATILITY = 0.05       # Minimum volatility threshold in %
DEFAULT_TIME_INTERVALL = 10 # Time interval for checking volatility, volume and marketcap in minutes
MAX_DRAWDOWN_SOL = 10          # Maximum allowed 24h loss in SOL
DRAWDOWN_CHECK_INTERVAL = 3600  # Drawdown check interval (seconds)

# Database settings (Credentials moved to .env)

# UNSUBSCRIBING CONDITIONS
INACTIVITY_PERIOD = timedelta(minutes=5)
MIN_MARKET_CAP = 4000          # Minimum market cap (in USD)

# Subscription tracking
ACTIVE_SUBSCRIPTIONS = set()
NEW_TOKEN_SUBSCRIPTION = False

# Token and API configurations
TOTAL_SUPPLY = 1000000000   # Assumed total supply if not provided
PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"

RUGCHECK_AUTH_API = "https://api.rugcheck.xyz/auth/login/solana"
RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens"
RUGCHECK_RATE_LIMIT = 10       # 10 requests per minute
RUGCHECK_INTERVAL = 60         # 60 seconds interval for RugCheck checks
RUGCHECK_SCORE_THRESHOLD = 1000 # Score above which a token is considered high risk and deactivated

# SOL price configuration
SOL_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# Logging
LOGGER_NAME = "TradingBot"
LOG_LEVEL_CONSOLE: str = "DEBUG"
LOG_LEVEL_FILE: str = "DEBUG"
LOG_STORAGE_PATH = "data"



# Domains that are generally not acceptable as a primary project website
DISALLOWED_WEBSITE_DOMAINS = {
    "youtube.com", "youtu.be",
    "tiktok.com",
    "spotify.com",
    "soundcloud.com",
    "discord.com", "discord.gg", # Discord invite links are not websites
    "medium.com",
    "substack.com",
    "linktr.ee",
    "t.me", # Handled separately
    "twitter.com", "x.com", # Handled separately
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "twitch.tv",
    "kick.com",
    "google.com",
    # Add other generic platforms if needed
}
ALLOWED_NEWS_WEBSITE_DOMAINS = {
    "bbc.com",
    "cnn.com",
    "reuters.com",
    "apnews.com",  # Associated Press
    "nytimes.com",  # The New York Times
    "washingtonpost.com",
    "theguardian.com",
    "bloomberg.com",
    "forbes.com",
    "wsj.com",  # The Wall Street Journal
    "ft.com",  # Financial Times
    "npr.org",  # National Public Radio
    "cnbc.com",
    "abcnews.go.com",
    "nbcnews.com",
    "cbsnews.com",
    "latimes.com",  # Los Angeles Times
    "usatoday.com",
    "politico.com",
    "aljazeera.com",
    "theatlantic.com",
    "newsweek.com",
    "time.com",
    "economist.com",
    "sky.com",  # Sky News
    "independent.co.uk",
    "telegraph.co.uk",
    "dailymail.co.uk",
    "mirror.co.uk",
    "huffpost.com",  # Huffington Post
    "vox.com",
    "slate.com",
    "buzzfeednews.com",
    "axios.com",
    "thehill.com",
    "scmp.com",  # South China Morning Post
    "japantimes.co.jp",
    "hindustantimes.com",
    "indiatoday.in",
    "timesofindia.indiatimes.com",
    "straitstimes.com",
    "smh.com.au",  # Sydney Morning Herald
    "theage.com.au",
    "globalnews.ca",
    "cbc.ca",  # Canadian Broadcasting Corporation
    "bitcointalk.org",
    "cnbcnews.us",
    "truthsocial.com"
}