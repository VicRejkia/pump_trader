# 🚀 Pump Trader - Solana Meme Coin Trading Bot 💸🐸

---

## 🏷️ Badges

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/VicRejkia/pump_trader/blob/main/LICENSE)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Made with ❤️](https://img.shields.io/badge/made%20with-%F0%9F%92%96-red)
![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-ff69b4)
[![Demo](https://img.shields.io/badge/demo-👀-yellow)](#demo)

---

## 🧭 Table of Contents

- [🎞️ Demo](#️-demo)
- [💭 Why This Bot Exists](#-why-this-bot-exists)
- [🏁 Getting Started (for the impatient)](#-getting-started-for-the-impatient)
- [🌍 Overview](#-overview)
- [⚙️ Features](#️-features)
- [🏗️ Architecture](#️-architecture)
- [🔧 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [🚀 Usage](#-usage)
- [🛠️ Development and Contributing](#️-development-and-contributing)
- [🧪 Testing](#-testing)
- [📜 License](#-license)
- [🙌 Acknowledgments](#-acknowledgments)

---

## 🎞️ Demo

> *“Show, don’t tell” — your lead dev, probably.*

Here’s Pump Trader doing its thing — scraping WebSockets, ducking rugs, and making trades like a caffeinated Wall Street intern:

![Pump Trader Demo - Dark Mode](https://github.com/yourusername/pump-trader/blob/main/assets/demo_dark.gif)

> ⚠️ Replace this URL with your actual dark-mode GIF (e.g., `/assets/demo_dark.gif`). Transparent background = extra points.

---

## 💭 Why This Bot Exists

Because you're tired of:

- Buying into meme coins right before the rug yank
- Getting financial advice from people named "Elon420Xx"
- Spending 6 hours on Telegram wondering if that chart is bullish or just a sad camel

**Pump Trader** was built to automate the pain away:

- Detect risks early 🔍
- Read social hype like a hypebeast 🤖
- Trade with logic (not vibes) 📈

It won’t make you a millionaire overnight, but hey — at least it won’t shill $RUGZ.

---

## 🏁 Getting Started (for the impatient)

1. **Clone the repo** like it’s a new L1 airdrop:

    ```bash
    git clone https://github.com/VicRejkia/pump_trader.git
    cd pump_trader
    ```

2. **Create your virtual environment** (yes, really — do it):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install all dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up your environment config**:

    We’ve included a sample config called `.env_sample`. Just rename it:

    ```bash
    mv .env_sample .env
    ```

    The file includes everything you need:

    ```ini
    DB_USER=your_db_username
    DB_PASSWORD=your_db_password
    DB_HOST=localhost
    DB_DATABASE=your_database

    SOLANA_PRIVATE_KEY=your_solana_private_key
    ```

5. **Tweak your settings** in `config.py`:
    - Trade amounts
    - Risk thresholds
    - Logging verbosity
    - Meme tolerance level (okay, not that yet)

6. **Run the bot** (optional flag: `--backup` or `--cleanup`):

    ```bash
    python main.py
    ```

7. Sit back, sip some coffee, and *hope it doesn’t FOMO into $DOGEWIFHAT2*.

---

## 🌍 Overview

Pump Trader is built to:

- 🔌 **Continuously Monitor Market Data** via real-time WebSockets.
- 🚨 **Evaluate Token Risk** with RugCheck. If it's sketchy, it's nuked.
- 🐦 **Analyze Social Signals** — because sometimes memes really do matter.
- 🧠 **Trade Intelligently** using configurable multi-stage logic.

---

## ⚙️ Features

- ⚡ **Full Async Stack**: High-performance and low-latency because speed ≠ rekt.
- 🛢️ **PostgreSQL Integration** with asyncpg (aka your trading brain).
- 📜 **Detailed Logging** with `rich` so you can actually debug your bad ideas.
- 🧰 **Centralized Configs** via `config.py`.
- 🧩 **Modular Structure**: Tinker, swap, or throw out entire parts.
- 🧼 **Graceful Shutdown**: No dirty exits. No DB corruption.
- 💾 **Backup & Cleanup Options**: Optional CLI flags for pre-run rituals.

---

## 🏗️ Architecture

Here's a quick peek behind the curtains:

- 🧾 **`config.py`**: Master config file — you’ll be in here a lot.
- 🐍 **`main.py` TradingBot**: The heart of the beast.
- 📡 **`websocket_handler.py` WebSocketHandler**: Talks to the PumpPortal API.
- 🗃️ **`database.py` DatabaseClient**: Handles DB connections, migrations, and backups.
- 🧠 **`trading.py` Trading Manager**: Implements buy/sell logic with multi-stage checks.
- 🧪 **`rugcheck.py` Rugcheck**: Calls RugCheck API, evaluates token sketchiness.
- 🫵 **`socials_processor.py` SocialsProcessor**: Scores social metadata and link quality.

---

## 🔧 Installation

### 🧰 Prerequisites

- Python 3.11+ (don’t test fate with older versions)
- PostgreSQL instance (or Docker container)
- Basic build tools for packages like `httpx`, `asyncpg`, etc.

### 📦 Dependencies

```bash
pip install -r requirements.txt
```

Sample `requirements.txt` includes:

- `asyncpg`
- `httpx`
- `aiolimiter`
- `python-dotenv`
- `rich`
- `beautifulsoup4`

---

## ⚙️ Configuration

### 🌱 Environment Variables

These go in your freshly renamed `.env` file:

```ini
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_DATABASE=your_database
SOLANA_PRIVATE_KEY=your_solana_private_key
```

### 🧙 Application Settings

Inside `config.py`, you’ll find various settings to customize the bot's behavior. Here's a breakdown of the key constants:

#### PumpPortal Settings

- **`WS_HOST`**:  WebSocket host for live market data from PumpPortal. Default: `"wss://pumpportal.fun/api/data"`.
- **`MAX_SUBSCRIPTION_BATCH`**: Maximum number of tokens to unsubscribe from in a single batch to avoid overloading the WebSocket connection. Default: `100`.

#### Trading Configuration

- **`SOL_TO_BUY`**: The amount of SOL (Solana cryptocurrency) to spend on each buy order.  This determines the size of each trade. Default: `0.1` SOL.
- **`INITIAL_SOL_BALANCE`**:  The initial SOL balance used for calculating Profit and Loss (PnL). This is for tracking purposes and doesn't affect actual trading. Default: `2.0` SOL.

#### Multi-Stage Sell Logic

- **`INITIAL_STOP_LOSS_PERCENT`**:  The initial Stop Loss (SL) level, set as a percentage below the buy price.  If the price drops by this percentage, a sell order is triggered to limit losses. Default: `50.0` (i.e., 50% below buy price).
- **`FIRST_SELL_PERCENT`**: The percentage of the initially bought tokens to sell at the First Take Profit (TP1) level.  This takes partial profit and reduces risk. Default: `50.0` (i.e., 50% of initial tokens).
- **`TRAILING_STOP_LOSS_PERCENT`**:  The Trailing Stop Loss (TSL) percentage. After TP1 is hit, the stop loss starts trailing the price upwards, locking in profits. This percentage is the drop from the highest price reached after TP1. Default: `50.0`.
- **`SECOND_TAKE_PROFIT_PERCENT`**: The Second Take Profit (TP2) level, set as a percentage above the initial buy price.  If the price reaches this level, the remaining tokens are sold for maximum profit. Default: `200.0` (i.e., 200% above buy price).
- **`FIRST_SELL_PROFIT_MARGIN`**: The desired profit margin percentage on the *total initial investment* that triggers the First Take Profit (TP1) sell. This ensures the first sell covers costs and secures a profit. Default: `10.0`.

#### Fees and Tips

- **`DEFAULT_BUY_FEE`**, **`DEFAULT_BUY_TIP`**, **`DEFAULT_SELL_FEE`**, **`DEFAULT_SELL_TIP`**: Default fees and tips (in SOL) to include in buy and sell transactions. These are small amounts to speed up transaction processing.  Defaults: `0.001` SOL for each.

#### Trading Thresholds

- **`DEFAULT_RUGCHECK_SCORE_THRESHOLD`**:  The maximum allowed RugCheck score for a token to be considered tradable. RugCheck is an API that assesses the risk of rug pulls (scams). Higher scores indicate higher risk. Default: `600`.
- **`DEFAULT_SOCIAL_SCORE_THRESHOLD`**: The maximum allowed social score for a token to be considered tradable. This score reflects the quality and risk associated with the token's social media presence. Higher scores indicate higher risk. Default: `50`.
- **`DEFAULT_VOLUME_THRESHOLD`**: The minimum 24-hour trading volume in USD for a token to be considered tradable.  This filters out illiquid tokens. Default: `5000` USD.
- **`MIN_MARKETCAP_THRESHOLD`**: The minimum market cap in USD that triggers a sell order. This triggers the sale of tokens with extremely low market capitalization. Default: `4000` USD.
- **`DEFAULT_MARKETCAP_THRESHOLD`**: The minimum market capitalization in USD for a token to be considered for buying. This focuses the bot on tokens with a reasonable market presence. Default: `10000` USD.
- **`MIN_VOLATILITY`**: The minimum volatility percentage required for a token to be considered tradable. Volatility is calculated over `DEFAULT_TIME_INTERVALL`. Default: `0.05` (i.e., 5% volatility).
- **`DEFAULT_TIME_INTERVALL`**: The time interval (in minutes) over which volatility, volume, and market cap are checked. Default: `10` minutes.

#### RugCheck API Configuration

- **`RUGCHECK_AUTH_API`**:  API endpoint for authenticating with the RugCheck API. Default: `"https://api.rugcheck.xyz/auth/login/solana"`.
- **`RUGCHECK_API`**: Base API endpoint for fetching token risk scores from RugCheck. Default: `"https://api.rugcheck.xyz/v1/tokens"`.
- **`RUGCHECK_RATE_LIMIT`**:  Maximum number of requests per minute allowed to the RugCheck API to avoid rate limiting. Default: `10` requests/minute.
- **`RUGCHECK_INTERVAL`**:  Interval (in seconds) between checks to the RugCheck API. Default: `60` seconds.
- **`RUGCHECK_SCORE_THRESHOLD`**:  Score above which a token is considered high risk by RugCheck and trading is deactivated for that token. Default: `1000`.

#### SOL Price API

- **`SOL_PRICE_API_URL`**: API URL to fetch the current price of SOL in USD, used for calculating trade values and thresholds in USD. Default: `"https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"`.

#### Logging

- **`LOGGER_NAME`**:  The name of the logger used throughout the bot. Default: `"TradingBot"`.
- **`LOG_LEVEL_CONSOLE`**:  Logging level for console output. Options include `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`. Default: `"DEBUG"`.
- **`LOG_LEVEL_FILE`**: Logging level for log file output.  Same options as `LOG_LEVEL_CONSOLE`. Default: `"DEBUG"`.
- **`LOG_STORAGE_PATH`**:  Path to the directory where log files are stored. Default: `"log"`.

#### Socials Processor Configuration

- **`SOCIALS_DISALLOWED_WEBSITE_DOMAINS`**:  A set of website domains that are penalized by the social score processor. These are typically common platforms that don't provide unique token-specific information.
- **`SOCIALS_ALLOWED_NEWS_DOMAINS`**: A set of website domains that are considered news sources and are treated neutrally by the social score processor (neither penalized nor bonus).

#### Socials Penalties and Bonuses

These constants define penalties and bonuses applied by the `SocialsProcessor` to assess the quality of a token's social media presence. Higher penalties (positive values) worsen the social score, while bonuses (negative values) improve it.

- **`SOCIALS_PENALTY_NO_WEBSITE`**: Penalty if no website link is found in token metadata. Default: `40`.
- **`SOCIALS_PENALTY_INVALID_WEBSITE_TYPE`**: Penalty for an invalid website type. Default: `35`.
- **`SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED`**: Penalty if website verification is skipped. Default: `35`.
- **`SOCIALS_PENALTY_WEBSITE_INVALID_URL`**: Penalty for an invalid website URL. Default: `35`.
- **`SOCIALS_PENALTY_WEBSITE_TIMEOUT`**: Penalty if website verification times out. Default: `35`.
- **`SOCIALS_PENALTY_WEBSITE_HTTP_ERROR`**: Penalty if website verification returns an HTTP error. Default: `35`.
- **`SOCIALS_PENALTY_WEBSITE_OTHER_ERROR`**: Penalty for other website verification errors. Default: `35`.
- **`SOCIALS_PENALTY_NO_HTTPS`**: Penalty if the website does not use HTTPS. Default: `10`.
- **`SOCIALS_PENALTY_WEBSITE_NO_MENTION`**: Penalty if the token name or symbol is not mentioned on the website. Default: `10`.
- **`SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE`**: Penalty for using common platforms like YouTube or TikTok as the primary website. Default: `25`.
- **`SOCIALS_PENALTY_NO_TELEGRAM`**: Penalty if no Telegram link is found. Default: `25`.
- **`SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE`**: Penalty for an invalid Telegram link type. Default: `25`.
- **`SOCIALS_PENALTY_INVALID_TELEGRAM_URL`**: Penalty for an invalid Telegram URL. Default: `25`.
- **`SOCIALS_PENALTY_NO_TWITTER`**: Penalty if no Twitter (X) link is found. Default: `25`.
- **`SOCIALS_PENALTY_INVALID_TWITTER_TYPE`**: Penalty for an invalid Twitter link type. Default: `25`.
- **`SOCIALS_PENALTY_INVALID_TWITTER_URL`**: Penalty for an invalid Twitter URL. Default: `25`.
- **`SOCIALS_PENALTY_DUPLICATE_LINKS`**: Penalty for duplicate links in metadata. Default: `15`.
- **`SOCIALS_PENALTY_ACTION_TRIGGER_URL`**: Penalty for action trigger URLs in metadata (potentially risky). Default: `15`.
- **`SOCIALS_BONUS_DOMAIN_MATCH`**: Bonus if the token name or symbol is part of the website domain. Default: `-10`.
- **`SOCIALS_BONUS_NEWS_GOV_WEBSITE`**: No bonus or penalty currently applied for news or government websites. Default: `0`.

- **`SOCIALS_SCORE_FAILED_METADATA`**: Default social score assigned if fetching token metadata fails. Default: `100`.

---

## 🚀 Usage

To summon the trading beast:

```bash
python main.py
```

### Optional Flags

- `--backup` : Make a DB backup before starting
- `--cleanup` : Drop all app tables (because YOLO?)

---

## 🛠️ Development and Contributing

### 🧼 Code Style

- PEP8, please 🙏
- Use docstrings — future-you will thank you
- Log meaningfully. Not just “something happened”.

### 🔁 Local Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 👾 Contributing

1. Fork it
2. Branch it
3. Test it
4. PR it
5. Profit

---

## 🧪 Testing

If you’ve added tests (legend):

```bash
pytest
```

Need a test DB? Spin one up. Do not test on production unless you're into chaos speedruns.

---

## 📜 License

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/VicRejkia/pump_trader/blob/main/LICENSE)

This project is licensed under the **Apache License 2.0**. You can basically do whatever you want, except sue us if your bot buys $RUG2.0 at the top. You can read the legal stuff here:

> [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

TL;DR:
> No warranty. No guarantees. No crying in crypto.

---

## 🙌 Acknowledgments

- Built on the backs of open-source legends: `asyncpg`, `httpx`, `rich`, and friends.
- Inspired by countless Telegram scams, rugged devs, and the eternal hope of making it.
- Dedicated to the ones who bought the top so others may live.

---

*Trade responsibly. Or just embrace the chaos.* 🤖💰
