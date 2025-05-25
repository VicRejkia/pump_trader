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

Welcome to Pump Trader, the bot that's aspiring to graduate from simple logic to complex AI like Reinforcement Learning (RL) and Genetic Algorithms (GA) – just as soon as it stops getting distracted by shiny new tokens that rug pull in five minutes.

---

## 🧭 Table of Contents

- [🎞️ Demo](#️-demo)
- [💭 Why This Bot Exists](#-why-this-bot-exists)
- [🏁 Getting Started (for the impatient)](#-getting-started-for-the-impatient)
- [🌍 Overview](#-overview)
- [⚙️ Features](#️-features)
- [🧬 Genetic Algorithm (GA) - Survival of the Fittest Configs](#️-genetic-algorithm-ga---survival-of-the-fittest-configs)
- [🤖 Reinforcement Learning (RL) - Teaching a Bot to Fish (for Profits, Not Rugs)](#-reinforcement-learning-rl---teaching-a-bot-to-fish-for-profits-not-rugs)
- [🏗️ Architecture](#️-architecture)
- [🔧 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [⚙️ Configuration Parameters - The Nitty Gritty (and Potentially Wallet-Crushing) Details](#️-configuration-parameters---the-nitty-gritty-and-potentially-wallet-crushing-details)
- [🚀 Usage](#-usage)
- [🛠️ Development and Contributing](#️-development-and-contributing)
- [🧪 Testing](#-testing)
- [📜 License](#-license)
- [🙌 Acknowledgments](#-acknowledgments)

---

## 🎞️ Demo

> *“Show, don’t tell” — your lead dev, probably.*

Here’s Pump Trader doing its thing — scraping WebSockets, ducking rugs, and making trades like a caffeinated Wall Street intern:

![Pump Trader Demo - Dark Mode](https://via.placeholder.com/600x400.gif?text=Pump+Trader+Demo)

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

    We’veincluded a sample config called `.env_sample`. Just rename it:

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
- 🧠 **Trade Intelligently** using configurable multi-stage logic (and it's gradually learning to incorporate Reinforcement Learning and Genetic Algorithms, mostly by observing what *not* to do).

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

## 🧬 Genetic Algorithm (GA) - Survival of the Fittest Configs

Tired of tweaking your `config.py` by hand like some kind of digital peasant? Fear not, for the GA optimizer is here to automate the process of finding slightly less terrible trading configurations!

### Purpose (Why does this exist?)

The GA optimizer's main job is to save you from yourself. Instead of you endlessly fiddling with settings hoping to strike gold, it systematically (and somewhat chaotically) tests out a gazillion different trading parameters. Think of it as an army of digital monkeys banging on keyboards, but occasionally, one of them types out Shakespeare (or at least a config that doesn't immediately go broke).

### What Magical Knobs Does It Twiddle?

This ain't your grandma's config tuner. The GA fiddles with the really important stuff, like:

- **How much SOL to YOLO:** Decides the optimal amount of SOL to throw at a new, shiny meme coin. (See: `SOL_TO_BUY` in what will eventually be `ga_config.py`)
- **The "Nope!" Threshold (Stop-Loss):** Figures out the perfect moment to dramatically exit stage left when a trade goes sour. (Corresponds to `INITIAL_STOP_LOSS_PERCENT`)
- **Profit Snatching Levels:** Determines when to cash in those sweet, sweet gains before they vanish into the crypto ether. (Relates to `FIRST_SELL_PROFIT_MARGIN`, `SECOND_TAKE_PROFIT_PERCENT`)
- **Risk Appetite (Rug Score & Social Score):** Adjusts how much sketchiness the bot is willing to tolerate from RugCheck and social media scores. (Think `DEFAULT_RUGCHECK_SCORE_THRESHOLD`, `DEFAULT_SOCIAL_SCORE_THRESHOLD`)
- **Volume & Market Cap Preferences:** Decides if it's going for the big fish or the bottom feeders by tweaking volume and market cap thresholds. (Related to `DEFAULT_VOLUME_THRESHOLD`, `DEFAULT_MARKETCAP_THRESHOLD`)

It basically tries to find that elusive sweet spot between "too scared to trade" and "buys everything that wags its tail."

### How Does This Digital Darwinism Work? (The Gory Details, Simplified)

1.  **The Primordial Ooze (Initial Population):** We start by generating a bunch of random trading configurations (a "population"). Most of them are probably terrible. That's okay.
2.  **The Arena (Evaluation & Fitness):** Each configuration is let loose on historical data (or simulated trades if we're feeling fancy) to see how much (or how little) profit it makes. This is its "fitness" score – basically, did it make bank or go bust?
3.  **Survival of the Richest (Selection):** The configurations that didn't lose all their money (the "fittest") get selected to, ahem, "pass on their genes." The ones that faceplanted are sent to the digital glue factory.
4.  **Making New Strats (Crossover & Mutation):** The chosen ones "breed," mixing their parameters (crossover) to create new offspring configurations. To keep things spicy, we also throw in some random changes (mutation) – maybe a slightly higher stop-loss here, a dash more SOL there.
5.  **The Next Generation:** These new offspring, along with some of the elite survivors, form the next generation.
6.  **Rinse and Repeat:** We do this over and over for many "generations." The hope is that, through this relentless process of digital natural selection, the configurations will gradually evolve to become more profitable... or at least less hilariously bad.

It's evolution, baby! But for trading bot settings. And with more spreadsheets.

---

## 🤖 Reinforcement Learning (RL) - Teaching a Bot to Fish (for Profits, Not Rugs)

If the Genetic Algorithm is like breeding a slightly better species of trader, Reinforcement Learning is like sending that trader to a very confusing, very expensive boarding school where it only learns by repeatedly face-planting.

### Purpose (Our Robot Overlord in Training)

The grand idea behind RL here is to let the bot teach *itself* how to make smarter trading decisions. We throw it into a simulated crypto market (because real money is for HODLing, not for robot school fees) and reward it with digital treats when it doesn't lose everything, or punish it (gently, with negative numbers) when it buys yet another coin that plummets faster than a lead balloon. Over eons (or many CPU hours), it's *supposed* to learn what actions lead to digital riches.

### What Does Our Little Bot-Brain Learn?

Essentially, the RL agent tries to answer the age-old crypto questions:

-   "Is this coin about to moon, or is that just a picture of a cat going slightly up?"
-   "Should I HODL through this dip, or is this the financial equivalent of the Titanic?"
-   "How much FOMO is *too* much FOMO before I become exit liquidity again?"
-   "When is the right time to take profits, instead of waiting for them to turn into a distant, beautiful memory?"

It does this by trying to figure out the optimal trading actions or parameter adjustments based on what it's currently seeing in the market.

### The Bot's "Senses" and "Actions" (Simplified for Humans)

To make this magic (or madness) happen, we define a couple of things:

-   **Observation Space (What the Bot "Sees"):** This is the bot's window to the world. Think of it as the data we feed it so it can (hopefully) make a good decision. This includes vital signs like:
    -   Current price trends (Is it going up, down, or just scribbling nonsense?).
    -   How much money it hasn't lost *yet*.
    -   The current risk score of a token (Is it a solid project or drawn by a 5-year-old on a napkin?).
    -   Whether the token's social media is more red flags than a bullfighting convention.
    -   Its own current trading parameters (because sometimes the problem is *you*, bot).

-   **Action Space (What the Bot Can "Do"):** These are the levers our bot can pull. It's not quite launching rockets, but it can:
    -   Decide to **buy, sell, or HODL** (the classic crypto dilemma).
    -   Tweak its own trading parameters: "Maybe if I just adjust my stop-loss by 0.1%, I'll finally beat the market!" (Narrator: It usually doesn't, but it *learns*).
    -   Adjust the amount of SOL it's willing to risk on the next "guaranteed" 100x coin.

The goal is for the RL agent to learn a "policy" – a fancy word for a strategy – that maps what it *sees* (observations) to what it *does* (actions) in a way that maximizes its chances of getting those sweet, sweet (simulated) crypto gains. Or, at the very least, to not embarrass itself too badly.

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

## ⚙️ Configuration Parameters - The Nitty Gritty (and Potentially Wallet-Crushing) Details

Alright, brave adventurer, welcome to the engine room! This is where you get to twiddle the knobs and pull the levers that dictate whether Pump Trader becomes a financial wizard or just a very efficient way to set your SOL on fire. Proceed with caution, a sense of humor, and maybe a stiff drink.

### Main Configuration (`config.py`)

This is your main control panel. Most of these settings define the bot's day-to-day trading behavior when it's not being bossed around by our more "intelligent" (read: experimental) GA or RL overlords.

**Core Trading Settings:**
*   **`_INITIAL_SOL_BALANCE`**: How much SOL you *pretend* to start with for PnL calculations. Doesn't actually mean you have it, like that Lambo you keep talking about.
*   **`SOL_TO_BUY`**: The actual amount of SOL you're willing to gamble on each meme coin. Choose wisely, or choose to cry.
*   **`PLAY_BUY_SOUND`**: Want a delightful 'ka-ching' when you buy? Or prefer silent despair? `True` for sound, `False` for quiet regret.
*   **`PLAY_SELL_SOUND`**: Similarly, a sound for selling. Could be 'Hallelujah!' or 'Oh no, not again!'

**Multi-Stage Sell Logic:**
*   **`FIRST_SELL_PROFIT_MARGIN`**: The profit percentage you're aiming for on your *initial bet* before you consider taking some chips off the table. Greed is good, but pigs get slaughtered.
*   **`FIRST_SELL_PERCENT`**: If you hit that first profit margin, what percentage of your tokens do you sell? All of it? Half? Just a nibble?
*   **`INITIAL_STOP_LOSS_PERCENT`**: The point at which you admit defeat and sell if the price tanks right after you buy. How much pain can you tolerate?
*   **`TRAILING_STOP_LOSS_PERCENT`**: After you've made some profit, this is how far the price can drop from its peak before you sell. Don't let those paper gains turn to dust!
*   **`SECOND_TAKE_PROFIT_PERCENT`**: If the coin *really* moons, this is the percentage above your buy price where you sell the rest. Aka the 'sell and brag' level.

**Fees & Tips:**
*   **`DEFAULT_BUY_FEE`**: Little bribes (fees and tips) to the Solana network to process your buy transactions. Gotta grease the wheels.
*   **`DEFAULT_BUY_TIP`**: Extra little bribes (tips) for buy transactions. Because miners love tips.
*   **`DEFAULT_SELL_FEE`**: Little bribes (fees and tips) to the Solana network to process your sell transactions. Hopefully, these are profit-taking sells!
*   **`DEFAULT_SELL_TIP`**: An extra little something for the network when you sell. Make it snappy!

**Price Determination:**
*   **`PRICE_DETERMINATION_METHOD`**: How the bot decides the 'current price'. VWAP, TWAP, LATEST, MEDIAN - pick your favorite flavor of price sorcery.
*   **`PRICE_AVG_WINDOW_MINUTES`**: If using an averaging method for price, this is the lookback window. How long is your price memory?
*   **`TWAP_SUB_INTERVAL_SECONDS`**: For TWAP, how often to sample price within the window. More samples, more... data.

**Trading Thresholds:**
*   **`DEFAULT_RUGCHECK_SCORE_THRESHOLD`**: Max RugCheck score you'll tolerate. Higher means riskier. How brave (or foolish) are you?
*   **`DEFAULT_SOCIAL_SCORE_THRESHOLD`**: Max social media sketchiness score. If it looks like a rug, smells like a rug... it's probably a rug.
*   **`DEFAULT_VOLUME_THRESHOLD`**: Minimum 24hr trading volume (USD) for a token to be even considered. No trading dust.
*   **`MIN_MARKETCAP_THRESHOLD`**: If market cap drops below this (USD), it's an emergency sell. Abandon ship!
*   **`DEFAULT_MARKETCAP_THRESHOLD`**: Minimum market cap (USD) to consider buying. Filters out the nano-cap nightmares.
*   **`MIN_VOLATILITY`**: Minimum price movement percentage needed. If it's not wiggling, it's not interesting.
*   **`DEFAULT_TIME_INTERVALL`**: How often (minutes) to check volatility, volume, and market cap (Note the typo 'INTERVALL'). Don't spam the APIs too much.

**Re-Buy Logic:**
*   **`USE_TREND_REVERSAL_CONFIRMATION`**: Enable to try and be smart about re-buys after a stop-loss, using fancy indicators. Or disable and just YOLO.
*   **`STOP_LOSS_COOLDOWN_MINUTES`**: After a stop-loss, how long to ignore that token. Give it time to think about what it did.
*   **`MIN_CANDLE_DATA_FOR_INDICATORS`**: How many data points (candles) needed before trying to calculate indicators for re-buys.
*   **`TREND_REVERSAL_RECENCY_HOURS`**: How far back to look for trend reversal signals.
*   **`TREND_REVERSAL_RSI_NEUTRAL_LEVEL`**: RSI level considered 'meh' for trend reversal.
*   **`INDICATOR_LOOKBACK_HOURS`**: General lookback period for these fancy indicators.
*   **`APPLY_TREND_REVERSAL_ON_SELL_REASONS`**: Which types of sells should trigger the trend reversal logic (e.g. 'Stop Loss', 'Trailing SL').
*   **`RSI_PERIOD`, `BBANDS_PERIOD`, `BBANDS_STD_DEV`, `FAST_EMA_PERIOD`, `SLOW_EMA_PERIOD`**: Parameters for the various technical indicators (RSI, Bollinger Bands, EMAs) used in the re-buy logic. If these look like alphabet soup to you, it's probably best to leave them to their default values or let the GA/RL try to figure them out.

**Unsubscribing Conditions:**
*   **`INACTIVITY_PERIOD`**: If a token just sits there doing nothing for this many minutes, unsubscribe and back it up.
*   **`MC_DROP_THRESHOLD`**: Percentage market cap drop that triggers unsubscription. Another 'abandon ship' signal.
*   **`MIN_TOKEN_AGE`**: Minimum age in minutes before a token is unsubscribed due to inactivity/MC drop. Give the newborns a chance.

**API and System Internals:**
*   **`_MAX_SUBSCRIPTION_BATCH`**: How many tokens to unsubscribe in one go. Mostly internal plumbing.
*   **`_TOTAL_SUPPLY`**: Assumed total supply if the API is being shy. A big number, like your hopes for these coins.
*   **`_PUMPPORTAL_WS`**: The WebSocket URL for PumpPortal. Don't change unless they tell you to.
*   **`_RUGCHECK_AUTH_API`**: URLs for RugCheck API. Sacred text.
*   **`_RUGCHECK_API`**: URLs for RugCheck API. Sacred text.
*   **`_RUGCHECK_RATE_LIMIT`**: How often you can politely ask RugCheck about a token without getting yelled at.
*   **`_RUGCHECK_INTERVAL`**: How often you can politely ask RugCheck about a token without getting yelled at.
*   **`RUGCHECK_SCORE_THRESHOLD`**: Another RugCheck score threshold, this one for deactivating trading if it's *really* bad. Yes, there are two, for extra caution/confusion.
*   **`_SOL_PRICE_API_URL`**: Where to get the SOL price in USD. Crucial for knowing how much you're *actually* losing.
*   **`_LOGGER_NAME`**: Logging stuff. How loud and where the bot scribbles its thoughts.
*   **`_LOG_LEVEL_CONSOLE`**: Logging stuff. How loud and where the bot scribbles its thoughts.
*   **`_LOG_LEVEL_FILE`**: Logging stuff. How loud and where the bot scribbles its thoughts.
*   **`_LOG_STORAGE_PATH`**: Logging stuff. How loud and where the bot scribbles its thoughts.
*   **`TELEGRAM_INTERACTION`**: Set to `True` if you want the bot to try and chat with you on Telegram. Or `False` for the strong silent type.

**Metadata & Socials Processing:**
*   **`HEARTBEAT_EMIT_INTERVAL_SECONDS`**: How often the bot reminds itself that it's still alive.
*   **`RESTART_GAP_THRESHOLD_SECONDS`**: If there's a gap in heartbeats longer than this, it might indicate a restart.
*   **`SOCIALS_CHECK_REFRESH_INTERVAL`**: How often (minutes) to re-check a token's social media score. Because Twitter never sleeps.
*   **`SOCIALS_DISALLOWED_WEBSITE_DOMAINS`**: Lists of website domains that either get penalized or treated neutrally when checking a token's website quality. Helps sort the wheat from the chaff (or the Linktrees from actual project sites).
*   **`SOCIALS_ALLOWED_NEWS_DOMAINS`**: Lists of website domains that either get penalized or treated neutrally when checking a token's website quality. Helps sort the wheat from the chaff (or the Linktrees from actual project sites).
*   **`SOCIALS_PENALTY_NO_WEBSITE`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_INVALID_WEBSITE_TYPE`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_WEBSITE_INVALID_URL`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_WEBSITE_TIMEOUT`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_WEBSITE_HTTP_ERROR`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_WEBSITE_OTHER_ERROR`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_NO_HTTPS`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_WEBSITE_NO_MENTION`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_NO_TELEGRAM`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_INVALID_TELEGRAM_URL`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_NO_TWITTER`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_INVALID_TWITTER_TYPE`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_INVALID_TWITTER_URL`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_DUPLICATE_LINKS`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_PENALTY_ACTION_TRIGGER_URL`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_BONUS_DOMAIN_MATCH`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_BONUS_NEWS_GOV_WEBSITE`**: The nitty-gritty scores for social media checks. Lots of ways to get penalized (no website, bad links, common platforms), a few ways to get a small bonus. Basically, a system for quantifying digital sketchiness.
*   **`SOCIALS_SCORE_FAILED_METADATA`**: Default high social score if metadata fetching fails. Assume the worst.

### Genetic Algorithm Configuration (`ga_config.py`)

This is where the magic of evolution (or at least, what we tell ourselves is evolution) happens for our trading configurations. The GA tries to "breed" better settings by throwing a bunch of them into a digital Hunger Games.

*   **`OPTIMIZABLE_PARAMETERS`**: The list of trading parameters from `config.py` that the GA will try to tweak (e.g., `SOL_TO_BUY`, `INITIAL_STOP_LOSS_PERCENT`, etc.). It's like telling the monkeys which typewriter keys to focus on.
*   **`POPULATION_SIZE`**: How many candidate trading strategies (individuals) are in each generation. More individuals, more chaos, more potential.
*   **`NUM_GENERATIONS`**: How many rounds of 'evolution' the GA will run. Patience, young grasshopper.
*   **`CROSSOVER_PROBABILITY`**: Chance that two 'parent' strategies will combine their 'genes' (settings) to create 'offspring' strategies.
*   **`MUTATION_PROBABILITY`**: Chance that a strategy's settings will randomly change. Keeps things interesting and prevents getting stuck.
*   **`KEEP_ELITISM`**: How many of the absolute best strategies from one generation are guaranteed to survive to the next. No mercy for the weak, except these few.
*   **`PARENT_SELECTION_TYPE`**: How the GA picks 'parents' to breed. 'sss' for steady-state, or imagine a very complicated dating show for algorithms.
*   **`CROSSOVER_TYPE`**: The method for combining parent genes. 'single_point' is like swapping half their DNA.
*   **`MUTATION_TYPE`**: How mutations happen. 'random' is like cosmic rays hitting the code.
*   **`FITNESS_METRIC`**: What the GA is trying to maximize (e.g., 'final_portfolio_value'). The ultimate measure of a strategy's worthiness.
*   **`FITNESS_GOAL`**: 'max' to maximize the metric, or 'min' if you're optimizing for, say, 'number of heart attacks induced'.
*   **`GA_FITNESS_SAMPLE_SIZE`**: How many random tokens to test each strategy against. 0 means use all tokens, which is slower but more thorough, like a very pedantic driving instructor.
*   **`DATA_SPLIT`**: How the historical data is split for training, validation, and testing the GA. Can't let it cheat by seeing the answers!
*   **`HISTORICAL_DATA_START_TS`**: The date range of past pump-and-dumps the GA will learn from for this run.
*   **`HISTORICAL_DATA_END_TS`**: The date range of past pump-and-dumps the GA will learn from for this run.
*   **`BACKTEST_INITIAL_CAPITAL`**: How much play money (SOL) each GA strategy gets in the backtester.
*   **`MULTIPROCESSING_CORES`**: How many CPU cores to throw at the GA. 'auto' tries to be smart, or you can specify a number if you want to make your computer sweat.
*   **`RESULTS_DIR`**: Where the GA thoughtfully deposits its findings (and probably a lot of confusing charts).

### Reinforcement Learning Configuration (`rl_config.py`)

If GA is evolution, RL is sending your bot to a brutal, expensive school where it learns by trial, error, and repeated digital face-plants. The goal? To build a bot brain that *actually* gets smarter. Maybe.

*   **`RL_HISTORICAL_DATA_START_TS`**: The thrilling historical sagas of token pumps and dumps the RL agent will use for its education for this run.
*   **`RL_HISTORICAL_DATA_END_TS`**: The thrilling historical sagas of token pumps and dumps the RL agent will use for its education for this run.
*   **`DATA_SET_KEY_TRAIN`**: Keys to label the training and evaluation datasets. Like naming your lab rats.
*   **`DATA_SET_KEY_EVAL`**: Keys to label the training and evaluation datasets. Like naming your lab rats.
*   **`RL_INITIAL_CAPITAL`**: The amount of SOL the RL agent starts with in its simulated world. Monopoly money, but with more algorithms.
*   **`MAX_STEPS_PER_EPISODE`**: Max number of decisions (steps) the agent can make for a single token's simulation. Prevents it from HODLing into infinity.
*   **`OBSERVATION_PRICE_HISTORY_LENGTH`**: How many past price points the agent 'sees' to get a feel for trends. Like a goldfish, but hopefully with a slightly longer memory.
*   **`OBSERVATION_FEATURES`**: The list of things the RL agent 'observes' at each step (price changes, market cap, volume, risk scores, portfolio status, etc.). All normalized, because numbers are hard.
*   **`OBSERVATION_SPACE_DIM`**: The number of features above. How many dials on the dashboard.
*   **`OBSERVATION_LOW`**: Expected range of normalized observation values. Usually -1 to 1, or -infinity to +infinity if you're feeling adventurous.
*   **`OBSERVATION_HIGH`**: Expected range of normalized observation values. Usually -1 to 1, or -infinity to +infinity if you're feeling adventurous.
*   **`RL_TUNABLE_PARAMETERS`**: The trading parameters the RL agent gets to fiddle with (e.g. `INITIAL_STOP_LOSS_PERCENT`, `SOL_TO_BUY`, etc.). It's trying to learn the 'best' settings for these by trial and error.
*   **`ACTION_SPACE_DIM`**: How many parameters the agent can tune. More levers to pull!
*   **`ACTION_LOW`**: The minimum and maximum values the agent can choose for each tunable parameter.
*   **`ACTION_HIGH`**: The minimum and maximum values the agent can choose for each tunable parameter.
*   **`REWARD_PNL_MULTIPLIER`**: Factor to scale the profit or loss when calculating rewards. Bigger number, bigger carrot/stick.
*   **`REWARD_DEATH_PENALTY`**: Ouch! Penalty if the agent holds a token until it 'dies' (end of data). Discourages excessive attachment.
*   **`REWARD_SL_HIT_PENALTY`**: Penalty for hitting a stop-loss. Learn from your mistakes, little bot.
*   **`REWARD_TP_HIT_BONUS`**: Bonus for successfully taking profit. Good bot!
*   **`REWARD_HOLDING_PENALTY`**: Small nudge to discourage just sitting there doing nothing. Action is (usually) better.
*   **`DEFAULT_BUY_FEE`**: Default values for simulation, some mirroring `config.py`. These are fixed during an RL episode; the agent learns to set the `RL_TUNABLE_PARAMETERS` around these defaults.
*   **`DEFAULT_SELL_FEE`**: Default values for simulation, some mirroring `config.py`. These are fixed during an RL episode; the agent learns to set the `RL_TUNABLE_PARAMETERS` around these defaults.
*   **`MIN_MARKET_CAP_USD_FALLBACK`**: Default values for simulation, some mirroring `config.py`. These are fixed during an RL episode; the agent learns to set the `RL_TUNABLE_PARAMETERS` around these defaults.
*   **`VOLATILITY_WINDOW`**: Window for calculating volatility within the RL environment.
*   **`RL_ALGORITHM`**: The chosen RL algorithm (e.g., 'PPO'). The secret sauce that dictates how the agent learns.
*   **`POLICY_KWARGS`**: Settings for the neural network that acts as the agent's 'brain'. How many neurons does a bot brain need?
*   **`TOTAL_TIMESTEPS`**: Total number of learning steps the agent will go through. Needs to be a LOT to learn anything useful.
*   **`N_ENVS`**: Number of parallel simulated environments for the agent to learn in. More environments = faster (but more chaotic) learning.
*   **`TENSORBOARD_LOG_DIR`**: Where the RL agent logs its homework and saves its trained 'brain'.
*   **`MODEL_SAVE_DIR`**: Where the RL agent logs its homework and saves its trained 'brain'.
*   **`EVAL_FREQ`**: How often to check if the agent is learning anything (in total steps).
*   **`N_EVAL_EPISODES`**: How often to check if the agent is learning anything (in total steps).
*   **`CHECKPOINT_FREQ`**: How often to check if the agent is learning anything (in total steps).
*   **`DATA_SPLIT_RL`**: How data is split for RL training/validation. Similar to GA, no peeking at the exam answers.
*   **`AGENT_ACTION_INTERVAL_SECONDS`**: When a trained RL agent is live, how often it re-evaluates and potentially changes its chosen parameters.

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
