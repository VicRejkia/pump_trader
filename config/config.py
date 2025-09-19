"""
Configuration constants and settings for the trading bot.
"""
import datetime

# Trading configuration
_INITIAL_SOL_BALANCE = 100.0                # Starting SOL balance for PnL tracking
SOL_TO_BUY = 0.5                            # Amount of SOL to spend on each buy
PLAY_BUY_SOUND = False                      # Play the buy sound when a buy is made
PLAY_SELL_SOUND = False                     # Play the sell sound when a sell is made

# --- NEW TRADING MODE ---
# Options: "simulate", "paper_trading", "live"
# "simulate": Records trades to DB as if they happened, no external calls for execution.
# "paper_trading": Calls live execution APIs, signs transactions, but DOES NOT send to network. Simulates fills.
# "live": Full live trading, sends transactions to the network.
TRADING_MODE = "simulate"                   # <<< SET YOUR DEFAULT MODE HERE (e.g., "simulate" for safety)
DEFAULT_SLIPPAGE_PERCENT = 15.0                # Default slippage percentage for trades (e.g., 1.0 for 1%)
DEFAULT_BUY_POOL = "auto"
DEFAULT_SELL_POOL = "auto"

# --- New Multi-Stage Sell Logic Configuration ---
FIRST_SELL_PROFIT_MARGIN = 80.0             # Desired profit margin % on the *total initial investment* for the first TP sell
FIRST_SELL_PERCENT = 35.0                   # % of *initial* tokens to sell at First TP (e.g., 50.0 for 50%)
INITIAL_STOP_LOSS_PERCENT = 40.0            # Initial SL as % below buy price (e.g., 25.0 for -25%)
TRAILING_STOP_LOSS_PERCENT = 10.0           # Trailing SL % drop from highest price *after* First TP (e.g., 15.0 for -15%)
SECOND_TAKE_PROFIT_PERCENT = 450.0          # Second TP as % above buy price (e.g., 200.0 for +200%)

# --- Fees and Tips ---
DEFAULT_BUY_FEE = 0.001                     # Fee for buying in SOL
DEFAULT_BUY_TIP = 0.001                     # Tip for buying in SOL
DEFAULT_SELL_FEE = 0.001                    # Fee for selling in SOL
DEFAULT_SELL_TIP = 0.001                    # Tip for selling in SOL

# Price determination strategy
PRICE_DETERMINATION_METHOD = "MEDIAN"       # Options: "VWAP", "TWAP", "LATEST", "MEDIAN" (Applies to chosen source)
TWAP_SUB_INTERVAL_SECONDS = 15              # Sub-interval for TWAP calculation (if TWAP is used) in seconds
PRICE_AVG_WINDOW_MINUTES = 0.25           # You mentioned you already set this to 0.25 (15 seconds) - keep it

# --- NEW: Price Calculation Strategy Control ---
# Determines the primary source for decision price and market cap.
# "direct_price": Calculates robust price from trades (sol_amount/token_amount), then derives MC.
# "market_cap": Calculates robust MC from trades (marketCapSol), then derives price.
PRICE_SOURCE_METHOD = "direct_price"  # Default, Options: "direct_price", "market_cap"

# Determines how the lookback window for price/MC calculation is defined.
# "time": Uses PRICE_AVG_WINDOW_MINUTES.
# "count": Uses PRICE_AVG_TRADE_COUNT.
PRICE_WINDOW_TYPE = "count"  # Default, Options: "time", "count"
PRICE_AVG_TRADE_COUNT = 15  # Number of trades for window if PRICE_WINDOW_TYPE is "count" (e.g., last 20 trades)


# Trading thresholds
DEFAULT_RUGCHECK_SCORE_THRESHOLD = 501      # No trading if Rugcheck score is equal or above this threshold
DEFAULT_SOCIAL_SCORE_THRESHOLD = 100        # No trading if Social score is equal or above this threshold
DEFAULT_VOLUME_THRESHOLD = 40000            # Minimum volume threshold in USD
MIN_MARKETCAP_THRESHOLD = 4000              # Minimum market cap threshold in USD to make emergency sell
DEFAULT_MARKETCAP_THRESHOLD = 20000         # Minimum market cap threshold in USD to search for buy opportunities
MIN_VOLATILITY = 0.18                       # Minimum volatility threshold in % to search for buy opportunities
DEFAULT_TIME_INTERVAL = 10                 # Time interval for checking volatility, volume and marketcap in minutes
MAX_TOKEN_COUNT_PER_CREATOR = 50            # Maximum number of tokens per creator to consider token as safe

# --- Re-Buy Logic Configuration ---
USE_TREND_REVERSAL_CONFIRMATION = True      # Master switch to enable/disable this feature
STOP_LOSS_COOLDOWN_MINUTES = 1              # How long a token is ignored after a Stop Loss
MIN_CANDLE_DATA_FOR_INDICATORS = 30         # Min 5-second data points required to calculate indicators
TREND_REVERSAL_RECENCY_HOURS = 6 
TREND_REVERSAL_RSI_NEUTRAL_LEVEL = 45.0     # RSI level considered neutral for trend reversal
INDICATOR_LOOKBACK_HOURS = 1                # Lookback period for indicators in hours

# Indicator Time Periods
APPLY_TREND_REVERSAL_ON_SELL_REASONS = ["🛑 Stop Loss", "🆘 Emergency SL (MCap)", "🆘 Emergency SL (No Volume)", "↘️ Trailing SL", "🛡️ Breakeven SL", "manual_override"]
RSI_PERIOD = 14
BBANDS_PERIOD = 20
BBANDS_STD_DEV = 2.0
FAST_EMA_PERIOD = 9
SLOW_EMA_PERIOD = 21

# --- DexScreener Trend Reversal Configuration ---
DEX_REVERSAL_LOOKBACK_MINUTES = 15          # How many minutes of snapshot data to analyze.
DEX_REVERSAL_MIN_SNAPSHOTS = 3              # Minimum number of snapshots required within the lookback window.
DEX_REVERSAL_MIN_LIQUIDITY_USD = 5000       # Minimum liquidity in USD for the token to be considered viable for a re-buy.
DEX_REVERSAL_MIN_PRICE_CHANGE_M5 = 2.0      # The m5 price change must be at least +2.0% to be counted as a positive signal.
DEX_REVERSAL_MIN_BUY_SELL_RATIO = 1.5       # Ratio of buys to sells must be at least 1.5 for a strong buying pressure signal.
DEX_REVERSAL_MIN_CONFIRMATIONS = 2          # How many snapshots must show strong buying pressure to confirm the trend.
DEXSCREENER_MIGRATION_GRACE_PERIOD_MINUTES = 5 # How many minutes after migration to ignore stale volume checks. # <<< ADD THIS LINE


# UNSUBSCRIBING CONDITIONS
INACTIVITY_PERIOD = 60                      # Inactivity period in minutes before unsubscribing & backup
MC_DROP_THRESHOLD = 2                       # Market cap drop threshold (in %) under creation MC - for unsubscription & backup
MIN_TOKEN_AGE = 30                          # Minimum token age in minutes before possible unsubscription & backup


# PumpPortal
_TOTAL_SUPPLY = 1000000000                   # Assumed total supply if not provided
_PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"
_PUMPORTAL_LOCAL_API_URL = "https://pumpportal.fun/api/trade-local"
_WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED = True       # Enable periodic refresh of all trade subscriptions
_WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES = 240 # Interval in minutes to perform the refresh

# --- WebSocket Stability ---
WEBSOCKET_MAX_SUBSCRIPTIONS = 3000  # Cap to avoid server limits
WEBSOCKET_PING_INTERVAL_SECONDS = 30  # Send ping every 30s
WEBSOCKET_PONG_TIMEOUT_SECONDS = 20  # Expect pong within 10s or reconnect
WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS = 1  # Exponential backoff start
WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS = 60  # Max delay
INACTIVITY_UNSUBSCRIBE_MINUTES = 60  # Unsub tokens inactive > this (from existing INACTIVITY_PERIOD)
WEBSOCKET_HEALTH_CHECK_INTERVAL = 10  # seconds
WEBSOCKET_SUBSCRIPTION_BATCH_SIZE = 100
WEBSOCKET_BATCH_DELAY = 0.5  # seconds between batches

_RUGCHECK_AUTH_API = "https://api.rugcheck.xyz/auth/login/solana"
_RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens"
_RUGCHECK_RATE_LIMIT = 10                    # 10 requests per minute
_RUGCHECK_INTERVAL = 60                      # 60 seconds interval for RugCheck checks
RUGCHECK_SCORE_THRESHOLD = 10000             # Score above which a token is considered high risk and deactivated
RUGCHECK_REQUEUE_PRIORITY_BOOST_PURCHASED = 1000.0 # High priority boost for purchased tokens
RUGCHECK_REQUEUE_INTERVAL_MINUTES = 5 # How often to check for requeue opportunities

# SOL price configuration
_SOL_PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

# --- Solana RPC ---
_SOLANA_RPC_ENDPOINT = "https://solana.drpc.org"
_DRPC_ENDPOINT = "https://lb.drpc.org/ogrpc?network=solana"

# "https://api.mainnet-beta.solana.com" # A public endpoint
# Alternative free endpoints:
# "https://solana-mainnet.g.alchemy.com/v2/YOUR_API_KEY" (requires free sign-up)
# "https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY" (requires free sign-up)

# Logging
_LOGGER_NAME = "TradingBot"
_LOG_LEVEL_CONSOLE: str = "DEBUG"
_LOG_LEVEL_FILE: str = "DEBUG"
_LOG_STORAGE_PATH: str = "log"

# Backup
_BACKUP_STORAGE_PATH: str = "backups"  # Directory for backups

# Telegram
TELEGRAM_INTERACTION = True

# --- Metadata Processor Configuration ---
HEARTBEAT_EMIT_INTERVAL_SECONDS = 60  # Interval for emitting heartbeat messages in seconds
RESTART_GAP_THRESHOLD_SECONDS = 600  # Threshold for restart gap in seconds
# --- Metadata Processor Configuration ---

# --- Socials Processor Configuration ---
SOCIALS_CHECK_REFRESH_INTERVAL = 120                  # Timeout for requeing socials check in minutes
SOCIALS_DISALLOWED_WEBSITE_DOMAINS = {
    "youtube.com", "youtu.be", "tiktok.com", "spotify.com", "soundcloud.com",
    "discord.com", "discord.gg", "medium.com", "substack.com", "linktr.ee",
    "t.me", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "reddit.com", "twitch.tv", "kick.com", "google.com",
    "example.com",
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

# --- DYNAMIC SOCIALS SCORING ---
SOCIALS_SCORE_TYPE_INITIAL = 'INITIAL_METADATA'
SOCIALS_SCORE_TYPE_TELEGRAM = 'TELEGRAM_UPDATE'
SOCIALS_SCORE_TYPE_WEBSITE = 'WEBSITE_UPDATE'
SOCIALS_TELEGRAM_UPDATE_INTERVAL_MINUTES = 15 # How often to re-check telegram stats for active tokens

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
SOCIALS_BONUS_TG_HIGH_MEMBERS = -10             # Bonus for having a large number of members
SOCIALS_THRESHOLD_TG_HIGH_MEMBERS = 2000        # Threshold above which high member bonus applies
SOCIALS_BONUS_TG_HIGH_ONLINE_RATIO = -5         # Bonus for a healthy online-to-member ratio
SOCIALS_THRESHOLD_TG_HIGH_ONLINE_RATIO = 0.10   # Ratio (10%) above which the high online ratio bonus applies

# Default Scores
SOCIALS_SCORE_FAILED_METADATA = 100             # Score assigned if metadata fetch fails
