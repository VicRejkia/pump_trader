"""
Configuration constants and settings for the trading bot.
"""

# Trading configuration
SOL_TO_BUY = 0.5                            # Amount of SOL to spend on each buy
_INITIAL_SOL_BALANCE = 100.0                  # Starting SOL balance for PnL tracking
PLAY_BUY_SOUND = False                      # Play the buy sound when a buy is made
PLAY_SELL_SOUND = False                     # Play the sell sound when a sell is made

# --- New Multi-Stage Sell Logic Configuration ---
FIRST_SELL_PROFIT_MARGIN = 70.0             # Desired profit margin % on the *total initial investment* for the first TP sell
FIRST_SELL_PERCENT = 35.0                   # % of *initial* tokens to sell at First TP (e.g., 50.0 for 50%)
INITIAL_STOP_LOSS_PERCENT = 40.0            # Initial SL as % below buy price (e.g., 25.0 for -25%)
TRAILING_STOP_LOSS_PERCENT = 50.0           # Trailing SL % drop from highest price *after* First TP (e.g., 15.0 for -15%)
SECOND_TAKE_PROFIT_PERCENT = 800.0          # Second TP as % above buy price (e.g., 200.0 for +200%)

# --- Fees and Tips ---
DEFAULT_BUY_FEE = 0.001                     # Fee for buying in SOL
DEFAULT_BUY_TIP = 0.001                     # Tip for buying in SOL
DEFAULT_SELL_FEE = 0.001                    # Fee for selling in SOL
DEFAULT_SELL_TIP = 0.001                    # Tip for selling in SOL

# Price determination strategy
PRICE_DETERMINATION_METHOD = "MEDIAN"  # Options: "VWAP", "TWAP", "LATEST", "MEDIAN"
PRICE_AVG_WINDOW_MINUTES = 3         # Lookback window for VWAP/TWAP in minutes
TWAP_SUB_INTERVAL_SECONDS = 60       # Sub-interval for TWAP calculation (if TWAP is used) in seconds

# Trading thresholds
DEFAULT_RUGCHECK_SCORE_THRESHOLD = 401      # No trading if Rugcheck score is equal or above this threshold
DEFAULT_SOCIAL_SCORE_THRESHOLD = 100        # No trading if Social score is equal or above this threshold
DEFAULT_VOLUME_THRESHOLD = 40000            # Minimum volume threshold in USD
MIN_MARKETCAP_THRESHOLD = 3600              # Minimum market cap threshold in USD to make emergency sell
DEFAULT_MARKETCAP_THRESHOLD = 45000         # Minimum market cap threshold in USD to search for buy opportunities
MIN_VOLATILITY = 0.18                       # Minimum volatility threshold in % to search for buy opportunities
DEFAULT_TIME_INTERVALL = 30                 # Time interval for checking volatility, volume and marketcap in minutes
#MAX_DRAWDOWN_SOL = 10                       # Maximum allowed 24h loss in SOL (not integrated)
#DRAWDOWN_CHECK_INTERVAL = 3600              # Drawdown check interval (seconds) (not integrated)

# UNSUBSCRIBING CONDITIONS
INACTIVITY_PERIOD = 30                      # Inactivity period in minutes before unsubscribing & backup
MIN_MARKET_CAP = 3600                       # Minimum market cap (in USD) - for unsubscription & backup
MC_DROP_THRESHOLD = 5                       # Market cap drop threshold (in %) - for unsubscription & backup

# Subscription tracking
#ACTIVE_SUBSCRIPTIONS = set()                # leave it alone ... can be deleted?
#NEW_TOKEN_SUBSCRIPTION = False              # leave it alone ... can be deleted?

# PumpPortal
_MAX_SUBSCRIPTION_BATCH: int = 100           # For batch unsubscription ... can be deleted?
_TOTAL_SUPPLY = 1000000000                   # Assumed total supply if not provided
_PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"

_RUGCHECK_AUTH_API = "https://api.rugcheck.xyz/auth/login/solana"
_RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens"
_RUGCHECK_RATE_LIMIT = 10                    # 10 requests per minute
_RUGCHECK_INTERVAL = 60                      # 60 seconds interval for RugCheck checks
RUGCHECK_SCORE_THRESHOLD = 1002             # Score above which a token is considered high risk and deactivated

# SOL price configuration
_SOL_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# Logging
_LOGGER_NAME = "TradingBot"
_LOG_LEVEL_CONSOLE: str = "DEBUG"
_LOG_LEVEL_FILE: str = "DEBUG"
_LOG_STORAGE_PATH: str = "log"

# Telegram
TELEGRAM_INTERACTION = True

# --- Metadata Processor Configuration ---
HEARTBEAT_EMIT_INTERVAL_SECONDS = 60  # Interval for emitting heartbeat messages in seconds
RESTART_GAP_THRESHOLD_SECONDS = 300  # Threshold for restart gap in seconds
# --- Metadata Processor Configuration ---

# --- Socials Processor Configuration ---
SOCIALS_CHECK_REFRESH_INTERVAL = 120                  # Timeout for requeing socials check in minutes
SOCIALS_DISALLOWED_WEBSITE_DOMAINS = {
    "youtube.com", "youtu.be", "tiktok.com", "spotify.com", "soundcloud.com",
    "discord.com", "discord.gg", "medium.com", "substack.com", "linktr.ee",
    "t.me", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "reddit.com", "twitch.tv", "kick.com", "google.com",
}
SOCIALS_ALLOWED_NEWS_DOMAINS = {
    "bbc.com", "cnn.com", "reuters.com", "apnews.com", "nytimes.com",
    "washingtonpost.com", "theguardian.com", "bloomberg.com", "forbes.com",
    "wsj.com", "ft.com", "npr.org", "cnbc.com", "abcnews.go.com",
    "nbcnews.com", "cbsnews.com", "latimes.com", "usatoday.com",
    "politico.com", "aljazeera.com", "theatlantic.com", "newsweek.com",
    "time.com", "economist.com", "sky.com", "independent.co.uk",
    "telegraph.co.uk", "dailymail.co.uk", "mirror.co.uk", "huffpost.com",
    "vox.com", "slate.com", "buzzfeednews.com", "axios.com", "thehill.com",
    "scmp.com", "japantimes.co.jp", "hindustantimes.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "straitstimes.com", "smh.com.au",
    "theage.com.au", "globalnews.ca", "cbc.ca", "bitcointalk.org",
    "cnbcnews.us", "truthsocial.com"
}

# Penalties (Higher = Worse)
SOCIALS_PENALTY_NO_WEBSITE = 40
SOCIALS_PENALTY_INVALID_WEBSITE_TYPE = 35
SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED = 35
SOCIALS_PENALTY_WEBSITE_INVALID_URL = 35
SOCIALS_PENALTY_WEBSITE_TIMEOUT = 35
SOCIALS_PENALTY_WEBSITE_HTTP_ERROR = 35
SOCIALS_PENALTY_WEBSITE_OTHER_ERROR = 35
SOCIALS_PENALTY_NO_HTTPS = 10
SOCIALS_PENALTY_WEBSITE_NO_MENTION = 10         # No mention of token name or symbol in website
SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE = 25    # Common platforms like Youtube, TikTok, etc. 'SOCIALS_DISALLOWED_WEBSITE_DOMAINS'
SOCIALS_PENALTY_NO_TELEGRAM = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE = 25
SOCIALS_PENALTY_INVALID_TELEGRAM_URL = 25
SOCIALS_PENALTY_NO_TWITTER = 25
SOCIALS_PENALTY_INVALID_TWITTER_TYPE = 25
SOCIALS_PENALTY_INVALID_TWITTER_URL = 25
SOCIALS_PENALTY_DUPLICATE_LINKS = 15            # Duplicate links in metadata
SOCIALS_PENALTY_ACTION_TRIGGER_URL = 15         # Action trigger URL in metadata

# Bonuses (Negative = Better)
SOCIALS_BONUS_DOMAIN_MATCH = -10                # Bonus if domain mentions token name or symbol
SOCIALS_BONUS_NEWS_GOV_WEBSITE = 0              # No penalty/bonus currently applied for news/gov sites in 'SOCIALS_ALLOWED_NEWS_DOMAINS'

# Default Scores
SOCIALS_SCORE_FAILED_METADATA = 100             # Score assigned if metadata fetch fails