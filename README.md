# 🚀 Pump Trader - Solana Meme Coin Trading Bot 💸🐸

-----

## 🏷️ Badges

[](https://github.com/VicRejkia/pump_trader/blob/main/LICENSE)
[](https://www.google.com/search?q=%23demo)

-----

Welcome to Pump Trader, the bot that's bravely navigating the treacherous waters of Solana meme coins. It's aspiring to graduate from simple logic to the complex neural tapestries of Reinforcement Learning (RL) and the evolutionary chaos of Genetic Algorithms (GA) – all while trying *very* hard not to get distracted by shiny new tokens that promise the moon but usually deliver a spectacular faceplant. This is where ambition meets the blockchain, and occasionally, they don't immediately try to kill each other.

-----

## 🧭 Table of Contents

- [🎞️ Demo](https://www.google.com/search?q=%23%EF%B8%8F-demo)
- [💭 Why This Bot Exists (The Origin Story of Our Digital Anti-Hero)](https://www.google.com/search?q=%23-why-this-bot-exists-the-origin-story-of-our-digital-anti-hero)
- [🏁 Getting Started (For Those Who Read Manuals Last, If At All)](https://www.google.com/search?q=%23-getting-started-for-those-who-read-manuals-last-if-at-all)
- [🌍 Overview (What This Contraption Supposedly Does)](https://www.google.com/search?q=%23-overview-what-this-contraption-supposedly-does)
- [⚙️ Core Features (The Shiny Bits)](https://www.google.com/search?q=%23%EF%B8%8F-core-features-the-shiny-bits)
- [🏗️ Project Structure & Key Components (The Guts of the Beast)](https://www.google.com/search?q=%23%EF%B8%8F-project-structure--key-components-the-guts-of-the-beast)
- [🧬 Genetic Algorithm (GA) - Survival of the Fittest Configs](https://www.google.com/search?q=%23%EF%B8%8F-genetic-algorithm-ga---survival-of-the-fittest-configs)
- [🤖 Reinforcement Learning (RL) - Teaching an Old Bot New Tricks (Without Losing Your Shirt)](https://www.google.com/search?q=%23-reinforcement-learning-rl---teaching-an-old-bot-new-tricks-without-losing-your-shirt)
- [🔧 Installation (The "Please Work" Phase)](https://www.google.com/search?q=%23-installation-the-please-work-phase)
- [⚙️ Configuration (Twiddling the Knobs of Destiny)](https://www.google.com/search?q=%23%EF%B8%8F-configuration-twiddling-the-knobs-of-destiny)
  - [Environment Variables (`.env`) - The Secret Sauce](https://www.google.com/search?q=%23environment-variables-env---the-secret-sauce)
  - [Main Bot Configuration (`config.py`) - The Daily Grind Settings](https://www.google.com/search?q=%23main-bot-configuration-configpy---the-daily-grind-settings)
  - [Genetic Algorithm Configuration (`ga_config.py`) - Breeding Better Bots](https://www.google.com/search?q=%23genetic-algorithm-configuration-ga_configpy---breeding-better-bots)
  - [Reinforcement Learning Configuration (`rl_config.py`) - Bot Brain School](https://www.google.com/search?q=%23reinforcement-learning-configuration-rl_configpy---bot-brain-school)
  - [Dynamic Configuration (`data/dynamic_config.json`) - On-The-Fly Tweaks](https://www.google.com/search?q=%23dynamic-configuration-datadynamic_configjson---on-the-fly-tweaks)
- [🚀 Usage (Lighting the Fuse)](https://www.google.com/search?q=%23-usage-lighting-the-fuse)
  - [Running the Main Bot (with Telegram Control)](https://www.google.com/search?q=%23running-the-main-bot-with-telegram-control)
  - [Running the Genetic Algorithm Optimizer](https://www.google.com/search?q=%23running-the-genetic-algorithm-optimizer)
  - [Running the Reinforcement Learning Trainer](https://www.google.com/search?q=%23running-the-reinforcement-learning-trainer)
  - [Running the Web Application (The Future GUI)](https://www.google.com/search?q=%23running-the-web-application-the-future-gui)
- [🛠️ Development and Contributing (If You're Feeling Brave)](https://www.google.com/search?q=%23%EF%B8%8F-development-and-contributing-if-youre-feeling-brave)
- [🧪 Testing (The "Does it Explode?" Phase)](https://www.google.com/search?q=%23-testing-the-does-it-explode-phase)
- [📜 License](https://www.google.com/search?q=%23-license)
- [🙌 Acknowledgments (To Those Who Paved the Way With Rugpulls)](https://www.google.com/search?q=%23-acknowledgments-to-those-who-paved-the-way-with-rugpulls)

-----

## 🎞️ Demo

> *“A GIF is worth a thousand lines of panicked log output.” — Some dev, probably.*

Here’s Pump Trader heroically attempting to not lose all your SOL, set to a dramatic Lo-fi beat:

*(Imagine a super cool, dark-mode GIF here showing the bot doing smart things, or at least, things that *look* smart.)*
`![Pump Trader Demo - Dark Mode](httpss://via.placeholder.com/600x400.gif?text=Pump+Trader+Actually+Working)`

> ⚠️ Seriously, replace this with an actual GIF. Your credibility (and our amusement) depends on it.

-----

## 💭 Why This Bot Exists (The Origin Story of Our Digital Anti-Hero)

Let's be honest, you're here because:

- You've bought the top of a meme coin more times than you've had hot dinners.
- Your financial advice sources rhyme with "ShibaInuToTheMoon69" on Twitter.
- You suspect "diamond hands" might just be a fancy term for "too slow to sell."
- Manually tracking `pump.fun` is like trying to catch smoke with chopsticks.

**Pump Trader** is our valiant, if somewhat sarcastic, attempt to automate the chaos. It aims to:

- Sniff out rugpulls faster than a bloodhound with a crypto wallet  sniffing out free Wi-Fi. 🔍
- Gauge social sentiment (because if enough people say "WAGMI," it *must* be true, right?). 🤖
- Execute trades based on *actual logic* (a novel concept in meme coins, we know). 📈
- Eventually, use fancy AI like GA and RL to become self-improving, or at least, self-aware enough to apologize before losing your SOL.

It won’t make you a crypto god overnight (spoiler: nothing will), but it might just save you from becoming exit liquidity for the 17th time this week.

-----

## 🏁 Getting Started (For Those Who Read Manuals Last, If At All)

1. **Clone the repo** like you're grabbing the last donut in the breakroom:

    ```bash
    git clone [https://github.com/VicRejkia/pump_trader.git](https://github.com/VicRejkia/pump_trader.git)
    cd pump_trader
    ```

2. **Set up a virtual environment.** Don't be a hero. Just do it.

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install the legion of dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure your environment.** Copy `.env_sample` to `.env` and fill in your secrets. Don't commit your actual `.env` file unless you enjoy sharing your private keys with the internet.

    ```bash
    cp .env_sample .env # or 'copy' on Windows
    # Now edit .env with your details!
    ```

    Your `.env` should contain:

    ```ini
    DB_USER=your_db_username
    DB_PASSWORD=your_db_password
    DB_HOST=localhost_or_your_db_host
    DB_DATABASE=your_pump_trader_database_name
    SOLANA_PRIVATE_KEY=your_actual_solana_private_key_base58_encoded_for_trading
    TG_BOT_TOKEN=your_telegram_bot_token_from_botfather # Optional, for Telegram interface
    TG_CHAT_ID=your_telegram_chat_id # Optional, for Telegram interface
    ```

5. **Brave the `config.py` file.** This is where you tell the bot how reckless to be. You might also need to peek into `ga_config.py` and `rl_config.py` if you're feeling adventurous.
6. **Initialize the database schema.** The bot *should* do this on first run, but a manual run of the SQL scripts in the `sql/` directory against your PostgreSQL database won't hurt. Make sure they run in numerical order\!
7. **Run the main controller** (which in turn runs the bot and Telegram interface):

    ```bash
    python main.py
    ```

    Optional flags like `--backup` or `--cleanup` can be used if you're feeling particularly destructive or cautious.
8. Cross your fingers, make a small offering to the crypto gods, and monitor the logs. Try not to refresh Solscan every 3 seconds.

-----

## 🌍 Overview (What This Contraption Supposedly Does)

Pump Trader is designed as a multi-faceted system to engage with the fast-paced Solana meme coin ecosystem on `pump.fun`. Its core mission is to:

- 🔌 **Continuously Monitor Market Data:** Leverages WebSockets to get real-time information on new token creations and trades.
- 🚨 **Evaluate Token Risk:** Integrates with RugCheck.xyz to assess the initial safety of tokens. Sketchy tokens are given the cold shoulder.
- 🐦 **Analyze Social Signals:** Fetches and scores metadata (website, Twitter, Telegram) to gauge project legitimacy and community presence. Because a token with no website is basically a digital ghost.
- 🧠 **Trade Strategically:** Implements a multi-stage buy and sell logic, including initial stop-losses, take-profit levels, and trailing stop-losses. It's not just buying and praying.
- 🤖 **Evolve and Learn (Eventually™):**
  - **Genetic Algorithm (GA):** An optimizer (`ga_optimizer.py`) to find more robust trading parameters by simulating strategies on historical data.
  - **Reinforcement Learning (RL):** A trainer (`rl_trainer.py`) to develop an agent that learns optimal trading actions or parameter adjustments through interaction with a simulated environment.
- 💬 **Stay Connected:** Offers a Telegram interface (`telegram_interface.py`) for basic control and status updates.
- 📊 **Visualize (The Future is Now... Almost):** A Flask-based web application (`web_app/app.py`) is in development to provide a GUI for monitoring, configuration, and analytics.

-----

## ⚙️ Core Features (The Shiny Bits)

- ⚡ **Fully Asynchronous Stack:** Built with `asyncio`, `httpx`, `asyncpg`, and `websockets` for high-performance, non-blocking operations. Because in crypto, if you're slow, you're liquidated.
- 🛢️ **Robust PostgreSQL Integration:** All critical data – tokens, trades, portfolio, configurations – is stored and managed in a PostgreSQL database.
- 📜 **Rich & Detailed Logging:** Uses the `rich` library for beautiful, informative console logs, and detailed file logs. So you can forensically analyze how you lost money.
- 🧰 **Centralized & Dynamic Configuration:** Core settings in `config.py`, with support for dynamic updates via `data/dynamic_config.json` without restarting the main bot.
- 🧩 **Modular Architecture:** Designed to be somewhat understandable and extensible. Swap out parts, add new strategies, or just marvel at the spaghetti.
- 🧼 **Graceful Shutdown & Startup:** Handles signals for a clean exit, backs up creator wallet data, and attempts to manage its processes through `main.py`.
- 💾 **Database Management:** Includes options for pre-run database backup and cleanup.
- 🧐 **Advanced Risk Management:** Beyond simple price checks, incorporates RugCheck scores and a custom social media presence scoring system.
- 📈 **Multi-Stage Trading Logic:** Not just a simple buy/sell. Includes initial stop-loss, multiple take-profit levels, and a trailing stop-loss mechanism.
- 🔄 **Trend-Reversal Re-Buy Logic:** An attempt to intelligently re-enter positions after a stop-loss, based on configurable technical indicators.
- 🤖 **AI-Powered Optimization (Work in Progress):**
  - **Genetic Algorithm Optimizer:** To fine-tune a vast array of trading parameters.
  - **Reinforcement Learning Trainer:** To develop an agent capable of adapting its strategy or parameters.

-----

## 🏗️ Project Structure & Key Components (The Guts of the Beast)

- **`main.py`**: The grand conductor. Starts and (tries to) manage the `trading_bot.py` and `telegram_interface.py` processes.
- **`trading_bot.py`**: The main brain and brawn. Initializes all services, connects to WebSockets, processes data, and executes trading logic. This is where the magic (or misadventure) happens.
- **`config.py`**: Static configuration. Your first stop for tweaking basic bot behavior.
- **`ga_config.py`**: Configuration specific to the Genetic Algorithm optimizer.
- **`rl_config.py`**: Configuration specific to the Reinforcement Learning environment and agent.
- **`data/dynamic_config.json`**: Allows for on-the-fly parameter changes without restarting the bot. The bot periodically checks this file.
- **`database_handler.py`**: All things PostgreSQL. Manages connections, schema initialization, CRUD operations, and data fetching for backtesting/RL.
- **`websocket_handler.py`**: Handles the WebSocket connection to `pump.fun`, subscribes to new tokens and trades.
- **`trade_processor.py`**: Takes raw trade data from the WebSocket and batches it into the database.
- **`trading_logic.py`**: Contains the `TradingManager` class, which implements the core buy/sell decision-making, including stop-losses, take-profits, and emergency sells.
- **`rugcheck_handler.py`**: Interfaces with RugCheck.xyz to fetch and store token risk scores.
- **`socials_processor.py`**: Fetches token metadata (website, socials) and calculates a "social score."
- **`live_trader_pumpportal.py` / `live_trader_gmgn.py`**: Modules for executing actual trades via different APIs (PumpPortal's local API or GMGN). The bot can be configured to use one of these for paper/live trading.
- **`telegram_interface.py`**: A separate script that runs a Telegram bot, allowing you to send commands and get status updates from the main trading bot via a shared command file.
- **`ga_optimizer.py`**: The standalone script to run the Genetic Algorithm for optimizing parameters defined in `ga_config.py`. It uses `backtester.py`.
- **`backtester.py`**: The engine for simulating trading strategies on historical data. Used by the GA.
- **`rl_trainer.py`**: The standalone script to train a Reinforcement Learning agent using `rl_environment.py`.
- **`rl_environment.py`**: Defines the custom OpenAI Gym/Gymnasium environment for the RL agent to learn in.
- **`state_manager.py`**: Manages shared global state within the `trading_bot.py` process (e.g., SOL price, shutdown events, active subscriptions).
- **`logger.py`**: Configures logging with `rich` for pretty console output and file logging.
- **`utils.py`**: Miscellaneous helper functions (e.g., sound alerts, log formatting, data loading for GA/RL).
- **`web_app/`**: Directory for the Flask-based web application.
  - **`web_app/app.py`**: The Flask application script for the GUI.
  - **`web_app/static/`**: CSS and JavaScript for the web app.
  - **`web_app/templates/`**: HTML templates for the web app.
- **`sql/`**: Contains SQL scripts for database schema creation and indexing.
- **`data/`**: Default directory for runtime data like status files, command files, and potentially logs or backups.

-----

## 🧬 Genetic Algorithm (GA) - Survival of الFittest Configs

Tired of tweaking your `config.py` by hand like some kind of digital peasant? Fear not, for the GA optimizer (`ga_optimizer.py`) is here to automate the process of finding slightly less terrible trading configurations\!

### Purpose (Why does this exist?)

The GA optimizer's main job is to save you from yourself. Instead of you endlessly fiddling with settings hoping to strike gold, it systematically (and somewhat chaotically) tests out a gazillion different trading parameters using the `backtester.py`. Think of it as an army of digital monkeys banging on keyboards, but occasionally, one of them types out Shakespeare (or at least a config that doesn't immediately go broke).

### What Magical Knobs Does It Twiddle?

This ain't your grandma's config tuner. The GA, configured in `ga_config.py`, fiddles with the really important stuff defined in `OPTIMIZABLE_PARAMETERS`, such as:

- **How much SOL to YOLO:** (`SOL_TO_BUY`)
- **The "Nope\!" Threshold (Stop-Loss):** (`INITIAL_STOP_LOSS_PERCENT`)
- **Profit Snatching Levels:** (`FIRST_SELL_PROFIT_MARGIN`, `SECOND_TAKE_PROFIT_PERCENT`, `FIRST_SELL_PERCENT`)
- **Risk Appetite (Rug Score & Social Score):** (`DEFAULT_RUGCHECK_SCORE_THRESHOLD`, `DEFAULT_SOCIAL_SCORE_THRESHOLD`)
- **Volume & Market Cap Preferences:** (`DEFAULT_VOLUME_THRESHOLD`, `DEFAULT_MARKETCAP_THRESHOLD`)
- **Re-Buy Logic Parameters:** Various settings for trend reversal confirmation, cooldowns, and indicator periods (`USE_TREND_REVERSAL_CONFIRMATION`, `STOP_LOSS_COOLDOWN_MINUTES`, `RSI_PERIOD`, etc.).

It basically tries to find that elusive sweet spot between "too scared to trade" and "buys everything that wags its tail."

### How Does This Digital Darwinism Work? (The Gory Details, Simplified)

1. **The Primordial Ooze (Initial Population):** We start by generating a bunch of random trading configurations. Most are probably terrible.
2. **The Arena (Evaluation & Fitness):** Each configuration is unleashed upon historical data via the `backtester.py`. Its performance (e.g., `final_portfolio_value`) is its "fitness."
3. **Survival of the Richest (Selection):** The configurations that didn't lose all their money get to "pass on their genes."
4. **Making New Strats (Crossover & Mutation):** Chosen ones "breed," mixing parameters. Random mutations keep things spicy.
5. **The Next Generation:** These new offspring, plus some elite survivors, form the next wave.
6. **Rinse and Repeat:** For many "generations," hoping configurations evolve to be more profitable.

It's evolution, baby\! But for trading bot settings. And with more spreadsheets. Results are saved in the `ga_optimization_results` directory.

-----

## 🤖 Reinforcement Learning (RL) - Teaching an Old Bot New Tricks (Without Losing Your Shirt)

If the Genetic Algorithm is like breeding a slightly better species of trader, Reinforcement Learning (`rl_trainer.py`) is like sending that trader to a very confusing, very expensive digital boarding school where it only learns by repeatedly face-planting in a simulated environment (`rl_environment.py`).

### Purpose (Our Robot Overlord in Training)

The grand idea here is to let the bot teach *itself* how to make smarter trading decisions or, more accurately, how to choose better trading parameters dynamically. We throw it into a simulated crypto market (because real money is for HODLing, not for robot school fees) and reward it with digital treats when it doesn't lose everything, or punish it (gently, with negative numbers) when it buys yet another coin that plummets faster than a lead balloon. Over eons (or many CPU hours), it's *supposed* to learn what actions (parameter adjustments) lead to digital riches.

### What Does Our Little Bot-Brain Learn?

The RL agent, configured in `rl_config.py`, tries to determine the optimal set of trading parameters (`RL_TUNABLE_PARAMETERS`) based on the current market conditions it observes. It's less about "buy/sell now" and more about "what should my stop-loss or volume threshold be *right now*?"

### The Bot's "Senses" and "Actions" (Simplified for Humans)

- **Observation Space (What the Bot "Sees"):** This is the bot's window to the (simulated) world, defined by `OBSERVATION_FEATURES`. It includes:
  - Price trends (log returns over different periods).
  - Market indicators like volatility, market cap (normalized), volume.
  - Risk scores (RugCheck, socials).
  - Portfolio state (is it holding, current PnL, SOL balance).
  - Time-based features (day of the week, time of day).
- **Action Space (What the Bot Can "Do"):** These are the trading parameters the RL agent can adjust. The `rl_config.py` defines the range for each tunable parameter (e.g., `INITIAL_STOP_LOSS_PERCENT`, `DEFAULT_VOLUME_THRESHOLD`). The agent outputs a continuous value for each of these, which is then used by the simulated trading logic.

The goal is for the RL agent to learn a "policy" – a fancy word for a strategy – that maps what it *sees* (observations) to what trading parameters it *sets* (actions) in a way that maximizes its chances of getting those sweet, sweet (simulated) crypto gains. Trained models and TensorBoard logs are saved in `rl_trained_models/` and `rl_tensorboard_logs/` respectively.

-----

## 🔧 Installation (The "Please Work" Phase)

### 🧰 Prerequisites

- Python 3.11+ (Seriously, don't tempt the Python gods with older versions).
- PostgreSQL (Make sure it's running and you can connect to it). Docker is your friend here.
- Basic system build tools (for compiling some Python package dependencies).
- `venv` for virtual environments (it's built into Python, just use it).

### 📦 Dependencies

All the necessary Python packages are listed in `requirements.txt`. Install them with:

```bash
pip install -r requirements.txt
```

This includes goodies like: `asyncpg`, `httpx`, `aiolimiter`, `python-dotenv`, `rich`, `beautifulsoup4`, `pandas`, `numpy`, `websockets`, `pygad` (for GA), `stable-baselines3[extra]` (for RL), `Flask` (for the web app), and `gunicorn` or `hypercorn` (recommended for running the web app in a more production-like setting).

-----

## ⚙️ Configuration (Twiddling the Knobs of Destiny)

This is where the real fun begins. Or ends. Depending on how you set these. We've got a few layers to this onion of configurability: your environment secrets, the main bot's daily driver settings, and then the more... *experimental* settings for our GA and RL brainiacs.

### Environment Variables (`.env`) - The Secret Sauce

Create a `.env` file in the project root (you can copy `.env_sample`). This is where your sensitive information goes. Don't commit your actual `.env` file unless you enjoy sharing your private keys with the internet and waking up to a wallet balance that echoes the void.

```ini
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=localhost_or_your_db_host # e.g., localhost or an IP address
DB_DATABASE=your_pump_trader_database_name

SOLANA_PRIVATE_KEY=your_actual_solana_private_key_base58_encoded_for_trading # CRITICAL! This is your money, honey.

# Optional: For Telegram Bot Interface
TG_BOT_TOKEN=your_telegram_bot_token_from_botfather # Get this from BotFather on Telegram
TG_CHAT_ID=your_personal_telegram_chat_id_for_notifications # Your numerical Telegram user ID
```

**IMPORTANT**: `SOLANA_PRIVATE_KEY` is your actual wallet private key. Guard it like it's the One Ring. If this leaks, consider your SOL pre-donated to anonymous internet connoisseurs.

-----

### Main Bot Configuration (`config.py`) - The Daily Grind Settings

This file (`config.py`) is the primary control panel for the `trading_bot.py` when it's left to its own devices (i.e., not being puppeteered by the GA or RL agents). It dictates the default trading strategies, risk tolerances, API interactions, and how loudly it complains in the logs.

Here’s the grand tour of what you can (and probably will) mess up:

**Core Trading & Financials:**

- **`_INITIAL_SOL_BALANCE` (float):** How much SOL you *tell* the bot it started with for PnL tracking. It's like setting the high score on an arcade game before you even play. Purely for your own amusement or despair. Default: `100.0`.
- **`SOL_TO_BUY` (float):** The actual amount of SOL the bot will yeet into each new, promising (ha\!) meme coin. This is real SOL, so choose a number your therapist would approve of. Default: `0.5`.
- **`PLAY_BUY_SOUND` (bool):** Set to `True` if you want a delightful audio cue every time the bot makes a questionable investment. `False` for a more monastic, silent descent into crypto madness. Default: `False`.
- **`PLAY_SELL_SOUND` (bool):** Similar to above, but for sells. Could be the sweet sound of profit, or the mournful beep of a stop-loss. Default: `False`.
- **`TRADING_MODE` (str):** Critical\!
  - `"simulate"`: The bot just pretends to trade, logging what it *would* have done. No real money harmed. This is where you should live until you *really* trust this thing.
  - `"paper_trading"`: Calls live APIs, simulates fills, but doesn't actually send transactions to the network. Good for testing your "live" setup without live losses.
  - `"live"`: Full-send mode. Real trades, real SOL, real consequences. Make sure your `.env` is locked down and you've made peace with your choices. Default: `"simulate"`.
- **`DEFAULT_SLIPPAGE_PERCENT` (float):** Maximum price slippage you're willing to tolerate for trades. If the price moves too much between your order and execution, the trade might fail or fill at a worse price. Default: `15.0` (i.e., 15%).
- **`DEFAULT_BUY_POOL` (str):** Which liquidity pool to use for buys. `"auto"` lets the API decide. Default: `"auto"`.
- **`DEFAULT_SELL_POOL` (str):** Which liquidity pool to use for sells. `"auto"` is usually fine. Default: `"auto"`.

**The Art of Selling (Multi-Stage Logic):**

- **`FIRST_SELL_PROFIT_MARGIN` (float):** The percentage profit you want on your *initial investment for that portion of tokens* before the first partial sell (TP1) kicks in. E.g., if `FIRST_SELL_PERCENT` is 50%, and this is 70%, you're aiming for a 70% profit on the cost of those first 50% of tokens. Default: `70.0`.
- **`FIRST_SELL_PERCENT` (float):** What percentage of your *initial* token holdings to sell when `FIRST_SELL_PROFIT_MARGIN` is hit. Secures some profit and de-risks. Default: `35.0`.
- **`INITIAL_STOP_LOSS_PERCENT` (float):** Your "nope, I'm out\!" trigger. If the price drops this much below your buy price *before* any take-profits, the bot sells to cut losses. Default: `40.0`.
- **`TRAILING_STOP_LOSS_PERCENT` (float):** After your `FIRST_SELL_PERCENT` (TP1) has been hit, this is how far the price can drop from its new highest point before the remaining tokens are sold. Locks in profits as the price climbs. Default: `50.0`.
- **`SECOND_TAKE_PROFIT_PERCENT` (float):** The "moon target" for the remaining tokens. If the price goes up this much from your initial buy price, sell the rest and do a little dance. Default: `800.0`.

**Transaction Costs (The Necessary Evils):**

- **`DEFAULT_BUY_FEE` (float):** Assumed fee in SOL for buy transactions. Network gotta eat. Default: `0.001`.
- **`DEFAULT_BUY_TIP` (float):** Extra SOL to "tip" the network for faster buy transactions. Bribery, but make it blockchain. Default: `0.001`.
- **`DEFAULT_SELL_FEE` (float):** Assumed fee in SOL for sell transactions. Default: `0.001`.
- **`DEFAULT_SELL_TIP` (float):** Extra SOL tip for faster sell transactions. Default: `0.001`.

**Price Intelligence (Or Lack Thereof):**

- **`PRICE_DETERMINATION_METHOD` (str):** How the bot decides the "current price" for decision making. Options: `"VWAP"` (Volume Weighted Average Price), `"TWAP"` (Time Weighted Average Price), `"LATEST"` (last trade price), `"MEDIAN"` (median price over a window). Default: `"MEDIAN"`.
- **`PRICE_AVG_WINDOW_MINUTES` (int):** If using VWAP, TWAP, or MEDIAN, this is the lookback window in minutes. Default: `1`.
- **`TWAP_SUB_INTERVAL_SECONDS` (int):** For TWAP, the sub-interval for price sampling within the main window. Default: `60`.

**Risk & Quality Filters (The Bouncer Logic):**

- **`DEFAULT_RUGCHECK_SCORE_THRESHOLD` (int):** Maximum RugCheck.xyz score the bot will tolerate for new buys. Lower score = less sketchy. Default: `401`. *(See also `RUGCHECK_SCORE_THRESHOLD` for a stricter, deactivation-focused check).*
- **`DEFAULT_SOCIAL_SCORE_THRESHOLD` (int):** Maximum "socials" score (0-100, lower is better) based on website/TG/Twitter presence. Default: `100` (effectively lenient by default, assuming penalties will increase it).
- **`DEFAULT_VOLUME_THRESHOLD` (int):** Minimum recent trading volume in USD for a token to be considered for a buy. Filters out ghost towns. Default: `40000`.
- **`MIN_MARKETCAP_THRESHOLD` (int):** Absolute minimum market cap in USD. If a token you're holding drops below this, it's an emergency sell, no questions asked. Default: `3600`.
- **`DEFAULT_MARKETCAP_THRESHOLD` (int):** Minimum market cap in USD for a token to be considered for an initial buy. Avoids the nano-est of nano-caps. Default: `45000`.
- **`MIN_VOLATILITY` (float):** Minimum price volatility (as a percentage, e.g., 0.18 for 0.18%) required over `DEFAULT_TIME_INTERVALL` to consider a buy. If it's not moving, it's not interesting. Default: `0.18`.
- **`DEFAULT_TIME_INTERVALL` (int):** The time interval in minutes used for checking the `DEFAULT_VOLUME_THRESHOLD`, `DEFAULT_MARKETCAP_THRESHOLD`, and `MIN_VOLATILITY`. Default: `10`. (Note: The variable name has a typo "INTERVALL" in your code).
- **`MAX_TOKEN_COUNT_PER_CREATOR` (int):** Maximum number of tokens a single creator can launch within a certain period (7 days in current DB logic) before their new tokens are considered suspicious and ignored. Default: `10`.

**Re-Buy Logic (For When You Just Can't Quit That Coin):**

- **`USE_TREND_REVERSAL_CONFIRMATION` (bool):** Master switch. If `True`, after certain types of sells (like stop-loss), the bot will look for technical indicators suggesting a trend reversal before considering a re-buy. Default: `True`.
- **`STOP_LOSS_COOLDOWN_MINUTES` (int):** How long (in minutes) to put a token in "timeout" after it hits a stop-loss (or other reasons defined in `_APPLY_TREND_REVERSAL_ON_SELL_REASONS`) before the trend reversal logic even considers it for a re-buy. Default: `1`.
- **`MIN_CANDLE_DATA_FOR_INDICATORS` (int):** Minimum number of 5-second data points (candles) required to calculate the technical indicators for trend reversal. Default: `30`.
- **`TREND_REVERSAL_RECENCY_HOURS` (int):** How far back (in hours) the bot looks for a qualifying sell event to trigger the trend reversal check. Default: `6`.
- **`TREND_REVERSAL_RSI_NEUTRAL_LEVEL` (float):** If an RSI crossover isn't detected for Stage 1 of trend reversal, but the RSI is above this "neutral" level, Stage 1 might still pass. Default: `45.0`.
- **`INDICATOR_LOOKBACK_HOURS` (int):** How many hours of data to use when calculating indicators (RSI, BBands, EMAs, VWAP) for the trend reversal check. Default: `1`.
- **`_APPLY_TREND_REVERSAL_ON_SELL_REASONS` (list of str):** A list of sell reasons (e.g., `"🛑 Stop Loss"`, `"🆘 Emergency SL (MCap)"`) that, if they occur, will make the token eligible for the trend reversal re-buy logic and subject to `STOP_LOSS_COOLDOWN_MINUTES`.
- **Indicator Periods (Technical Analysis Nerd Stuff):**
  - **`RSI_PERIOD` (int):** Lookback period for calculating the Relative Strength Index (RSI). Default: `14`.
  - **`BBANDS_PERIOD` (int):** Lookback period for Bollinger Bands. Default: `20`.
  - **`BBANDS_STD_DEV` (float):** Number of standard deviations for the Bollinger Bands. Default: `2.0`.
  - **`FAST_EMA_PERIOD` (int):** Period for the fast Exponential Moving Average (EMA). Default: `9`.
  - **`SLOW_EMA_PERIOD` (int):** Period for the slow Exponential Moving Average (EMA). Default: `21`.

**Token Housekeeping (Unsubscribing Conditions):**

- **`INACTIVITY_PERIOD` (int):** If a token shows no trading activity for this many minutes, and it's older than `MIN_TOKEN_AGE`, it gets unsubscribed and archived. Default: `60`.
- **`MC_DROP_THRESHOLD` (int):** If a token's market cap drops by this percentage from its initial recorded market cap (when first seen by the bot), and it's older than `MIN_TOKEN_AGE`, it gets unsubscribed and archived. Default: `5` (i.e., 5% drop).
- **`MIN_TOKEN_AGE` (int):** Minimum age in minutes a token must reach before the `INACTIVITY_PERIOD` or `MC_DROP_THRESHOLD` rules apply. Gives new tokens a fighting chance. Default: `30`.

**System Internals & API Configs (Mostly Don't Touch Unless You Know Why):**

- **`_MAX_SUBSCRIPTION_BATCH` (int):** For batch unsubscribing tokens from the WebSocket. Internal detail. Default: `100`.
- **`_TOTAL_SUPPLY` (int):** An assumed total supply if the actual supply can't be fetched for a token. Default: `1000000000`.
- **`_PUMPPORTAL_WS` (str):** The WebSocket URL for `pump.fun`.
- **`_PUMPORTAL_LOCAL_API_URL` (str):** URL for the PumpPortal local trading API.
- **`_RUGCHECK_AUTH_API` (str):** RugCheck.xyz authentication API endpoint.
- **`_RUGCHECK_API` (str):** RugCheck.xyz main API endpoint for token reports.
- **`_RUGCHECK_RATE_LIMIT` (int):** Max requests per `_RUGCHECK_INTERVAL` to RugCheck. Default: `10`.
- **`_RUGCHECK_INTERVAL` (int):** Time period (seconds) for the RugCheck rate limit. Default: `60`.
- **`RUGCHECK_SCORE_THRESHOLD` (int):** A secondary, often stricter, RugCheck score. If a token's score *ever* exceeds this, it's marked inactive and potentially removed. This is distinct from `DEFAULT_RUGCHECK_SCORE_THRESHOLD` used for initial buy decisions. Default: `1002`. *(Yes, two RugCheck thresholds. For when you want to be absolutely, positively sure you're avoiding something... or just to keep things interesting).*
- **`_SOL_PRICE_API_URL` (str):** API endpoint to fetch the SOL/USD price.

**Logging & Bot Operation:**

- **`_LOGGER_NAME` (str):** Name for the logger.
- **`_LOG_LEVEL_CONSOLE` (str):** Log verbosity for the console (`"DEBUG"`, `"INFO"`, etc.).
- **`_LOG_LEVEL_FILE` (str):** Log verbosity for the log file.
- **`_LOG_STORAGE_PATH` (str):** Directory where log files are saved.
- **`TELEGRAM_INTERACTION` (bool):** Set to `True` to enable the Telegram bot interface. Requires `TG_BOT_TOKEN` and `TG_CHAT_ID` in `.env`. Default: `True`.

**Metadata & Socials Processing Configs:**

- **`HEARTBEAT_EMIT_INTERVAL_SECONDS` (int):** How often (in seconds) the bot logs a "heartbeat" to the database, indicating it's alive and kicking. Used to detect crashes or gaps in operation. Default: `60`.
- **`RESTART_GAP_THRESHOLD_SECONDS` (int):** If the bot restarts and detects a gap in heartbeats longer than this, it might treat some tokens differently (e.g., assume their lifecycle was interrupted). Default: `600`.
- **`SOCIALS_CHECK_REFRESH_INTERVAL` (int):** How often (in minutes) the bot will re-queue a token for a social media score check if it hasn't been checked recently. Default: `120`.
- **`SOCIALS_DISALLOWED_WEBSITE_DOMAINS` (set of str):** A list of website domains (e.g., `"linktr.ee"`, `"t.me"`) that, if used as a token's main website, will incur a penalty in the social score. These are typically generic platforms not indicative of a dedicated project.
- **`SOCIALS_ALLOWED_NEWS_DOMAINS` (set of str):** A list of reputable news domains. If a token's website is one of these, it might be treated neutrally or even slightly positively (though current bonus is 0).
- **Social Scoring Penalties & Bonuses (`SOCIALS_PENALTY_*`, `SOCIALS_BONUS_*`):** A detailed set of integer values that contribute to a token's "social score." Penalties are positive (bad), bonuses are negative (good). They cover aspects like:
  - Missing website, Telegram, or Twitter.
  - Invalid URL formats.
  - Website verification issues (timeouts, errors, no HTTPS).
  - Website content (no mention of token, common platform domain).
  - Duplicate social links.
  - Use of "action trigger" URLs (e.g., mailto, Twitter intents).
  - Bonus if the website domain matches the token name/symbol.
- **`SOCIALS_SCORE_FAILED_METADATA` (int):** The very high (bad) social score assigned if the bot fails to fetch or parse a token's metadata URI. Default: `100`.

-----

### Genetic Algorithm Configuration (`ga_config.py`) - Breeding Better Bots

This file (`ga_config.py`) controls the Genetic Algorithm optimizer (`ga_optimizer.py`). It's all about evolving better sets of trading parameters by simulating different configurations against historical data.

- **`OPTIMIZABLE_PARAMETERS` (list of dict):** This is the heart of the GA. It's a list where each entry defines a trading parameter (matching a key in `config.py`) that the GA will try to tune. For each parameter, you specify:
  - `"name"`: The exact parameter name (e.g., `"SOL_TO_BUY"`).
  - `"values"`: A list of discrete values the GA can pick from (e.g., `[0.1, 0.2, 0.3]`).
  - OR `"low"` and `"high"`: For continuous parameters, defining the lower and upper bounds of the range.
  - `"type"`: The data type (`float` or `int`).
- **GA Settings (The Evolutionary Engine):**
  - **`POPULATION_SIZE` (int):** How many different trading configurations (individuals) are in each "generation." More individuals mean more diversity but slower processing. Default: `60`.
  - **`NUM_GENERATIONS` (int):** How many cycles of selection, crossover, and mutation the GA will run. More generations give more time for good solutions to evolve. Default: `100`.
  - **`CROSSOVER_PROBABILITY` (float):** The chance that two "parent" configurations will mix their settings (genes) to create "offspring." Higher means more mixing. Default: `0.8`.
  - **`MUTATION_PROBABILITY` (float):** The chance that a parameter in a configuration will randomly change. Prevents the GA from getting stuck on local optima and encourages exploration. Default: `0.5`.
  - **`KEEP_ELITISM` (int):** How many of the absolute best-performing configurations from one generation are guaranteed to survive, unchanged, into the next. Preserves top performers. Default: `3`.
  - **`PARENT_SELECTION_TYPE` (str):** Method for choosing which configurations get to "reproduce." Options include `'sss'` (steady-state selection), `'rws'` (roulette wheel), `'tournament'`, etc. `'sss'` is a common choice for maintaining diversity. Default: `"sss"`.
  - **`CROSSOVER_TYPE` (str):** How parent configurations combine their parameters. `'single_point'` means swapping parameters after a random point. Other options: `'two_points'`, `'uniform'`. Default: `"single_point"`.
  - **`MUTATION_TYPE` (str):** Method for applying mutations. `'random'` randomly picks new values within allowed ranges/sets. Default: `"random"`.
- **Fitness Function Settings (How We Judge Success):**
  - **`FITNESS_METRIC` (str):** The specific performance metric from the backtest results that the GA will try to optimize (e.g., `"final_portfolio_value"`, `"total_pnl"`). Default: `"final_portfolio_value"`.
  - **`FITNESS_GOAL` (str):** Whether to `"max"` (maximize) or `"min"` (minimize) the `FITNESS_METRIC`. Default: `"max"`.
  - **`GA_FITNESS_SAMPLE_SIZE` (int or None):** To speed up evaluation, you can set this to a number (e.g., `15`) to test each configuration on a random sample of N tokens from the training set. If `0` or `None`, all tokens in the training set are used (more thorough, much slower). Default: `0`.
- **Data Settings (The Sandbox for Evolution):**
  - **`DATA_SPLIT` (dict):** Percentages to split the historical token data into `training`, `validation`, and `test` sets (e.g., `{"training": 0.6, "validation": 0.2, "test": 0.2}`). The GA trains on the training set.
  - **`HISTORICAL_DATA_START_TS` (datetime):** The overall start date and time for fetching historical data from the database for the GA process.
  - **`HISTORICAL_DATA_END_TS` (datetime):** The overall end date and time.
- **Backtester Settings (The Simulation Rules):**
  - **`BACKTEST_INITIAL_CAPITAL` (float):** The starting SOL amount for each backtest simulation run by the GA. Default: `100.0`.
- **Multiprocessing & Results:**
  - **`MULTIPROCESSING_CORES` (str or int):** Number of CPU cores to use for parallel fitness evaluations. `"auto"` tries to pick a sensible number, or you can specify an integer. Default: `"auto"`.
  - **`RESULTS_DIR` (str):** Directory where the GA will save its final results, including the best parameter set found and performance plots. Default: `"ga_optimization_results"`.

-----

### Reinforcement Learning Configuration (`rl_config.py`) - Bot Brain School

This file (`rl_config.py`) lays the groundwork for training an RL agent using `rl_trainer.py` and the custom `rl_environment.py`. It's about teaching the bot to make decisions by trial, error, and lots of simulated pain and gain.

- **General & Data Configuration:**
  - **`RL_HISTORICAL_DATA_START_TS` / `RL_HISTORICAL_DATA_END_TS` (datetime):** The date range for fetching historical OHLCV data used in the RL environment.
  - **`DATA_SET_KEY_TRAIN` / `DATA_SET_KEY_EVAL` (str):** Keys used by `load_and_split_data` to identify datasets for training episodes and periodic evaluation. Defaults: `'train'`, `'validation'`.
  - **`DATA_SPLIT_RL` (dict):** Percentage split for data (similar to GA's `DATA_SPLIT`).
- **Environment Configuration (The Simulated World):**
  - **`RL_INITIAL_CAPITAL` (float):** Starting SOL for each simulated trading episode. Default: `100.0`.
  - **`MAX_STEPS_PER_EPISODE` (int):** Maximum number of 5-second steps the agent can take in a single token simulation. Prevents infinite loops on zombie tokens. Default: `2880` (approx 4 hours).
  - **`OBSERVATION_PRICE_HISTORY_LENGTH` (int):** Number of past price steps to use for calculating features like log returns. Default: `15`.
  - **`OBSERVATION_FEATURES` (list of str):** The list of market and portfolio metrics the agent "sees" at each step (e.g., `'price_change_1'`, `'volatility'`, `'is_holding'`, `'sol_balance_norm'`). The order here is critical and must match the observation vector construction.
  - **`OBSERVATION_SPACE_DIM` (int):** Automatically calculated as `len(OBSERVATION_FEATURES)`.
  - **`OBSERVATION_LOW` / `OBSERVATION_HIGH` (float):** Defines the expected range of (normalized) observation values. Often `-np.inf` to `np.inf` as normalization is handled by `VecNormalize`.
- **Action Space Configuration (What the Agent Controls):**
  - **`RL_TUNABLE_PARAMETERS` (list of tuple):** This is key. It defines which trading parameters (from `config.py`) the RL agent learns to *set*. Each tuple is `('PARAMETER_NAME', low_bound, high_bound, type)`. The agent outputs a continuous value for each, which is then scaled and applied.
  - **`ACTION_SPACE_DIM` (int):** `len(RL_TUNABLE_PARAMETERS)`.
  - **`ACTION_LOW` / `ACTION_HIGH` (np.ndarray):** Arrays defining the min/max raw output values from the agent for each action dimension before they are scaled to the actual parameter bounds.
- **Reward Function (Carrots and Sticks):**
  - **`REWARD_PNL_MULTIPLIER` (float):** Scales the realized profit/loss from sells to form the primary reward. Default: `1.0`.
  - **`REWARD_DEATH_PENALTY` (float):** A significant negative reward if the agent is still holding a token when its data ends (simulating token death). Default: `-RL_INITIAL_CAPITAL * 0.5`.
  - **`REWARD_SL_HIT_PENALTY` (float):** Penalty for hitting a stop-loss. Default: `-0.5`.
  - **`REWARD_TP_HIT_BONUS` (float):** Bonus for hitting a take-profit. Default: `0.5`.
  - **`REWARD_HOLDING_PENALTY` (float):** Small penalty per step while holding a position, to discourage inaction. Default: `-0.001`.
- **Default Simulation Parameters (Fixed during RL episodes):**
  - `DEFAULT_BUY_FEE`, `DEFAULT_SELL_FEE`, etc.: Some parameters are fixed during an RL episode; the agent learns to set the `RL_TUNABLE_PARAMETERS` within this fixed context.
  - `MIN_MARKET_CAP_USD_FALLBACK` (int): An absolute USD MCap for emergency sells in the simulation.
  - `VOLATILITY_WINDOW` (int): Window size for volatility calculation *within the RL environment*.
- **RL Agent & Training (Stable Baselines3 Settings):**
  - **`RL_ALGORITHM` (str):** The RL algorithm to use (e.g., `"PPO"`, `"SAC"`). Default: `"PPO"`.
  - **`POLICY_KWARGS` (dict):** Configuration for the neural network architecture of the agent's policy and value functions (e.g., hidden layer sizes `net_arch=dict(pi=[128, 128], vf=[128, 128])`).
  - **`TOTAL_TIMESTEPS` (int):** Total number of simulation steps the agent will be trained for. Needs to be large (e.g., 1,000,000+).
  - **`N_ENVS` (int):** Number of parallel environments to run for faster data collection. Default: `8`.
  - **`TENSORBOARD_LOG_DIR` (str):** Path to save TensorBoard logs for monitoring training.
  - **`MODEL_SAVE_DIR` (str):** Path to save trained agent models and `VecNormalize` statistics.
  - **`EVAL_FREQ` (int):** How often (in total steps) to evaluate the agent's performance on a separate validation dataset.
  - **`N_EVAL_EPISODES` (int):** Number of episodes to run during each evaluation.
  - **`CHECKPOINT_FREQ` (int):** How often to save a checkpoint of the model during training.
- **Live Agent Configuration:**
  - **`AGENT_ACTION_INTERVAL_SECONDS` (int):** If a trained RL agent is deployed with the live bot, this is how often (in seconds) the live bot will query the agent for new parameter settings based on the current live observation. Default: `60`.

-----

### Dynamic Configuration (`data/dynamic_config.json`) - On-The-Fly Tweaks

To make life a tad easier (or more chaotic, depending on your perspective), the `trading_bot.py` supports dynamic configuration updates via a JSON file located at `data/dynamic_config.json`.

- **How it Works:** The bot periodically checks this file for changes. If modifications are detected, it attempts to load and apply the new parameter values to its *active configuration* without needing a full restart.
- **Precedence:** Values in `dynamic_config.json` will override those set in the base `config.py`.
- **Creation:** If this file doesn't exist when `trading_bot.py` starts, the bot will create it and populate it with the currently active (and JSON-serializable) parameters from its initial `config.py` load (and any GA/RL overrides if applied at startup).
- **Editing:** You can edit this file manually. The Web UI (once fully functional) will also provide an interface to modify these settings. The bot attempts to convert values to their expected types (e.g., string "true" to boolean `True`).
- **Persistence:** Changes saved to `dynamic_config.json` will persist across bot restarts, as the bot reads this file on startup to overlay its settings.

This is your go-to for fine-tuning the bot while it's running, perhaps in response to changing market vibes or after a particularly enlightening cup of coffee. Just remember to use valid JSON, or the bot might throw a digital tantrum.

-----

## 🚀 Usage (Lighting the Fuse)

How to unleash this magnificent (or terrifying) creation upon the unsuspecting Solana blockchain.

### Running the Main Bot (with Telegram Control)

This is the primary way to run the bot for active trading or simulation. The `main.py` script acts as a controller that starts and supervises both the main `trading_bot.py` and the `telegram_interface.py`.

1. **Ensure Prerequisites:** Python, PostgreSQL, `.env` file configured.

2. **Navigate to Project Root:** `cd pump_trader`

3. **Activate Virtual Environment:** `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)

4. **Run `main.py`**:

    ```bash
    python main.py
    ```

**Optional Flags for `main.py` (these are passed through to `trading_bot.py`):**

- `--cleanup`: Cleans the database (drops relevant tables) before starting. **USE WITH EXTREME CAUTION. DATA WILL BE GONE.**
- `--backup`: Backs up existing database tables before starting. A much safer choice.
- `--params-file path/to/your_ga_results.json`: Load optimized parameters found by a Genetic Algorithm run. The bot will use these instead of the defaults in `config.py`.
- `--rl-agent-path path/to/your_rl_model.zip`: Load a trained Reinforcement Learning agent model. If provided, the RL agent will dynamically adjust parameters, likely overriding both `config.py` defaults and any GA parameters from `--params-file`.

    The `main.py` controller will:

  - Start `trading_bot.py` in a new console/process. The `trading_bot.py` itself handles its own log rotation unless `--no-log-rotate` is passed (which `main.py` does by default when it launches the bot).
  - Start `telegram_interface.py` in a new console/process (if `TELEGRAM_INTERACTION` is `True` in `config.py` and `TG_BOT_TOKEN`/`TG_CHAT_ID` are set in `.env`).
  - Monitor the `trading_bot.py` process using the status written to `data/bot_status.json` and attempt restarts if it appears to have crashed.

    You can interact with the bot via the Telegram Bot (if enabled and configured). Send `/menu` to your bot in Telegram to see available commands.

### Running the Genetic Algorithm Optimizer

To let evolution (or something like it) try to find better trading parameters:

1. **Configure `ga_config.py`**: Define which parameters from `config.py` to optimize (`OPTIMIZABLE_PARAMETERS`), set GA hyperparameters (population size, generations, etc.), specify data ranges, and initial backtesting capital.
2. **Ensure Historical Data**: The GA optimizer (`ga_optimizer.py`) relies on historical trade data stored in your PostgreSQL database. The `trading_bot.py` populates this data during its normal operation. If you're starting with an empty database, you'll need to let the main bot run for a while to collect data covering the `HISTORICAL_DATA_START_TS` to `HISTORICAL_DATA_END_TS` range defined in `ga_config.py`. The `utils.load_and_split_data` function used by the GA will fetch and prepare OHLCV data based on these trades.
3. **Run `ga_optimizer.py`**:

    ```bash
    python ga_optimizer.py
    ```

    This process can be lengthy, as it involves running many backtests using `backtester.py`. Progress will be logged to the console. The best found parameter set and performance plots will be saved in the directory specified by `ga_config.RESULTS_DIR` (default: `ga_optimization_results/`).

### Running the Reinforcement Learning Trainer

To attempt to train an RL agent that learns to adjust trading parameters:

1. **Configure `rl_config.py`**: Set up the observation and action spaces, reward function components, RL agent hyperparameters (e.g., for PPO), and data ranges.
2. **Ensure Historical Data**: Like the GA, the RL trainer (`rl_trainer.py`) needs sufficient historical trade data in the database. The `utils.load_and_split_data` function will process this into OHLCV format for the `rl_environment.py`.
3. **Run `rl_trainer.py`**:

    ```bash
    python rl_trainer.py
    ```

    This is typically a very computationally intensive and time-consuming process. Training progress, including rewards and other metrics, can be monitored using TensorBoard:

    ```bash
    tensorboard --logdir ./rl_tensorboard_logs/
    ```

    Navigate to `http://localhost:6006` in your browser. Trained models (`.zip` files) and `VecNormalize` statistics (`.pkl` files) will be saved in the directory specified by `rl_config.MODEL_SAVE_DIR` (default: `rl_trained_models/`).

### Running the Web Application (The Future GUI)

The web application (`web_app/app.py`) is intended to provide a graphical interface for monitoring the bot, viewing charts, and managing configurations. It's currently under development.

1. **Navigate to Project Root:** `cd pump_trader` (if not already there).

2. **Activate Virtual Environment.**

3. **Run the Flask App (Development Server):**
    For development, the easiest way is often using the `flask` command:

    ```bash
    # Set the Flask app environment variable
    # On Linux/macOS:
    export FLASK_APP=web_app.app
    export FLASK_DEBUG=1 # Optional, enables debug mode and auto-reloader
    # On Windows (PowerShell):
    # $env:FLASK_APP = "web_app.app"
    # $env:FLASK_DEBUG = 1
    # On Windows (CMD):
    # set FLASK_APP=web_app.app
    # set FLASK_DEBUG=1

    flask run --host=0.0.0.0 --port=5001 # Or any other port you prefer (default is 5000)
    ```

    Alternatively, you can run the `app.py` script directly (as configured in your `app.py`'s `if __name__ == '__main__':` block, which currently uses port 89):

    ```bash
    python web_app/app.py
    ```

    Access the web interface by navigating to `http://localhost:5001` (or the port you configured) in your web browser.

    **Note for Production:** For deploying the web app more robustly, consider using a dedicated WSGI server like Gunicorn or an ASGI server like Hypercorn if the app evolves to be fully asynchronous. The current `web_app/app.py` uses an `async_adapter` for some database calls, indicating a mixed sync/async nature common when adding async capabilities to Flask.

-----

## 🛠️ Development and Contributing (If You're Feeling Brave)

### 🧼 Code Style

- **PEP8:** Please. My eyes thank you. If you don't know what it is, Google it before your code makes a linter cry.
- **Docstrings:** Write them. Explain your genius (or your madness). Future you (and probably current me, trying to understand your PR) will appreciate it. Assume the next person reading your code is a psychopath who knows where you live.
- **Logging:** Log like you mean it. `log_info("It did a thing")` is grounds for a sternly worded email. `log_debug(f"Token {mint} passed volume check ({volume} > {threshold})")` is the kind of detail that warms a troubleshooter's heart.
- **Type Hinting:** We're trying to be professionals here, amidst the chaos of meme coins. Use type hints. It helps. Really.

### 🔁 Local Setup

You already did this in "Getting Started," right? *Right?* If not, scroll up, or we're judging you. Silently.

```bash
# Make sure you're in the project root
python -m venv venv
source venv/bin/activate # or venv\Scripts\activate on Windows
pip install -r requirements.txt
# If there's a dev-requirements.txt for extra tools (linters, pytest plugins, etc.):
# pip install -r dev-requirements.txt
```

### 👾 Contributing

So, you've looked at the code and thought, "I can make this *even crazier* / *slightly less broken*"? Fantastic\!

1. **Fork it:** Click that button. It's like adopting a very needy, digital pet.
2. **Create your feature branch:** `git checkout -b feature/MyAwesomeProfitPrintingIdea` (Keep dreaming on the name, but make it descriptive).
3. **Commit your changes:** `git commit -am 'feat: Implemented a strategy that actually works (probably a fluke)'`. Meaningful commit messages, please.
4. **Push to the branch:** `git push origin feature/MyAwesomeProfitPrintingIdea`
5. **Open a Pull Request:** Brace yourself. Explain what you did and why it won't break everything. We appreciate well-documented attempts at glory.

We especially welcome contributions that improve stability, add genuinely useful features, or fix the parts that are currently held together by wishes and digital duct tape. Bonus points if you can explain it like we're five.

-----

## 🧪 Testing (The "Does it Explode?" Phase)

Do we have a sprawling, CI/CD-integrated, 100%-coverage test suite? Let's be honest, this is a rapidly evolving meme coin bot. "Comprehensive testing" is often a real-time event involving actual (simulated, hopefully) SOL.

But if *you've* written tests (you absolute legend\!), you can run them using:

```bash
pytest
```

Or, if you have specific test files:

```bash
python -m unittest discover tests
```

(Assuming your tests are in a `tests/` directory and follow standard Python `unittest` or `pytest` conventions).

**Database for Testing:** For the love of all that is holy, **DO NOT test on your production database** if you have any attachment to your funds. Spin up a separate, disposable test database. Using your live wallet or database for untested code is the crypto equivalent of juggling chainsaws while blindfolded. Fun to watch from a distance, disastrous to participate in.

-----

## 📜 License

[](https://github.com/VicRejkia/pump_trader/blob/main/LICENSE)

This project is licensed under the **Apache License 2.0**. This basically means you can do almost anything you want with the code: use it, abuse it, fork it, spoon it, build a rival bot that actually makes money (and then tell us how, please).

**The Catch?** Oh, there's always a catch, isn't there?
The big one is: **NO WARRANTY. AS IS. VOID WHERE PROHIBITED. YOUR MILEAGE MAY VARY. PAST PERFORMANCE IS NOT INDICATIVE OF FUTURE RESULTS (ESPECIALLY IF PAST PERFORMANCE WAS ACCIDENTALLY GOOD).**
If this bot decides your SOL would look better in someone else's wallet, or if it develops sentience and starts trading exclusively in Shiba-Elon-CumRocket-SafeMoon-Inu coins, that's a "you" problem. We provide the digital equivalent of a very sharp knife; how you wield it is your own adventure.

You can (and should, if you're bored) read the full, legally-binding, sleep-inducing text here:

> [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

**TL;DR (The "I Skipped Law School" Version):**

> It's free. It's (mostly) open. If it breaks your heart or your bank account, you get to keep both shattered pieces. If, by some miracle, it makes you rich, we accept donations in BTC, ETH, SOL, or high-quality memes. If it makes you poor, remember: it's only crypto (the money you *used* to have).

-----

## 🙌 Acknowledgments (To Those Who Paved the Way With Rugpulls)

- To the giants on whose shoulders this humble bot stands: the creators of `asyncpg`, `httpx`, `rich`, `pandas-ta`, `stable-baselines3`, `pygad`, `Flask`, and countless other open-source libraries that let us build cool (and occasionally disastrous) things.
- To the entire `pump.fun` ecosystem, for being a never-ending source of entertainment, education, and existential dread.
- To every "based dev" who promised a 1000x and delivered a -99% chart – you are the true educators in risk management. Your sacrifices (of other people's money) will not be forgotten.
- To the Telegram "alpha callers" who are somehow always right in retrospect. We see you.
- And, of course, to coffee. The fuel of late-night coding sessions, questionable life choices, and this bot. May our cups (and wallets) never be empty.

-----

*Trade responsibly. Or don't. We're a README, not your financial advisor. Just don't come crying to us when your $GMEPEPEWIFBONK coin turns into a very expensive lesson.* 🤖💰📉📈
