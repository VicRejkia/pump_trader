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

This is where the real fun begins. Or ends. Depending on how you set these.

### Environment Variables (`.env`) - The Secret Sauce

Create a `.env` file in the project root (you can copy `.env_sample`). This is where your sensitive information goes:

```ini
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=localhost_or_your_db_host # e.g., localhost or an IP address
DB_DATABASE=your_pump_trader_database_name

SOLANA_PRIVATE_KEY=your_actual_solana_private_key_base58_encoded_for_trading # CRITICAL!

# Optional: For Telegram Bot Interface
TG_BOT_TOKEN=your_telegram_bot_token_from_botfather
TG_CHAT_ID=your_personal_telegram_chat_id_for_notifications
```

**IMPORTANT**: `SOLANA_PRIVATE_KEY` is your actual wallet private key. Guard it like it's the last Bitcoin. If this leaks, say goodbye to your funds.

### Main Bot Configuration (`config.py`) - The Daily Grind Settings

This file (`config.py`) is the primary configuration for the `trading_bot.py`. It defines the default trading strategies, risk parameters, API endpoints, and more. When the GA or RL agent isn't actively overriding parameters, these are the values the bot falls back on.

Key sections include:

- **Trading Configuration:** `SOL_TO_BUY`, `TRADING_MODE` (simulate, paper, live), slippage.
- **Multi-Stage Sell Logic:** `FIRST_SELL_PROFIT_MARGIN`, `FIRST_SELL_PERCENT`, `INITIAL_STOP_LOSS_PERCENT`, `TRAILING_STOP_LOSS_PERCENT`, `SECOND_TAKE_PROFIT_PERCENT`. These define how the bot takes profits and cuts losses.
- **Fees and Tips:** `DEFAULT_BUY_FEE`, `DEFAULT_SELL_FEE`, etc. For transaction priority.
- **Price Determination:** `PRICE_DETERMINATION_METHOD` (VWAP, LATEST, etc.) for deciding the current price.
- **Trading Thresholds:** `DEFAULT_RUGCHECK_SCORE_THRESHOLD`, `DEFAULT_SOCIAL_SCORE_THRESHOLD`, `DEFAULT_VOLUME_THRESHOLD`, `DEFAULT_MARKETCAP_THRESHOLD`, `MIN_VOLATILITY`. These are crucial for filtering which tokens to consider.
- **Re-Buy Logic Configuration:** `USE_TREND_REVERSAL_CONFIRMATION`, `STOP_LOSS_COOLDOWN_MINUTES`, `TREND_REVERSAL_RECENCY_HOURS`, indicator periods (`RSI_PERIOD`, `BBANDS_PERIOD`, etc.). For attempting smarter re-entries.
- **Unsubscribing Conditions:** `INACTIVITY_PERIOD`, `MC_DROP_THRESHOLD`. To prune dead or dying tokens.
- **API Endpoints:** For PumpPortal, RugCheck, SOL price.
- **Logging Configuration:** Log levels and paths.
- **Socials Processor Configuration:** Penalties and bonuses for website/social media link quality.

*Refer to the extensive comments within `config.py` for a detailed explanation of each parameter.* It's your bot's DNA; mutate with caution\!

### Genetic Algorithm Configuration (`ga_config.py`) - Breeding Better Bots

This file (`ga_config.py`) controls the Genetic Algorithm optimizer (`ga_optimizer.py`).

- **`OPTIMIZABLE_PARAMETERS`**: A list defining which parameters from `config.py` the GA should try to tune, along with their possible value ranges or discrete choices. This is the gene pool.
- **GA Settings:** `POPULATION_SIZE`, `NUM_GENERATIONS`, `CROSSOVER_PROBABILITY`, `MUTATION_PROBABILITY`, `PARENT_SELECTION_TYPE`, etc. These control the mechanics of the evolutionary process.
- **Fitness Function Settings:** `FITNESS_METRIC` (e.g., 'final\_portfolio\_value') and `FITNESS_GOAL` ('max' or 'min') define what the GA strives for. `GA_FITNESS_SAMPLE_SIZE` determines how many tokens are used to evaluate each candidate strategy.
- **Data Settings:** `DATA_SPLIT` (train/validation/test percentages), `HISTORICAL_DATA_START_TS`, `HISTORICAL_DATA_END_TS` for fetching data for backtesting.
- **Backtester Settings:** `BACKTEST_INITIAL_CAPITAL` for simulations.
- **Other Settings:** `MULTIPROCESSING_CORES` for parallel evaluation, `RESULTS_DIR` for saving findings.

*Consult `ga_config.py` for the full list and detailed comments.*

### Reinforcement Learning Configuration (`rl_config.py`) - Bot Brain School

This file (`rl_config.py`) configures the RL training process (`rl_trainer.py`) and the trading environment (`rl_environment.py`).

- **General Configuration:** `RL_HISTORICAL_DATA_START_TS`, `RL_HISTORICAL_DATA_END_TS` for the data range.
- **Environment Configuration:** `RL_INITIAL_CAPITAL`, `MAX_STEPS_PER_EPISODE`.
- **Observation Space:** `OBSERVATION_FEATURES` (e.g., price changes, market cap, volume, risk scores) defining what the agent "sees."
- **Action Space:** `RL_TUNABLE_PARAMETERS` defining which trading parameters the agent can learn to adjust, along with their bounds (`ACTION_LOW`, `ACTION_HIGH`).
- **Reward Function:** `REWARD_PNL_MULTIPLIER`, `REWARD_DEATH_PENALTY`, shaping rewards/penalties like `REWARD_SL_HIT_PENALTY`. This is how the agent learns if it's being a "good bot" or a "wallet-destroyer."
- **RL Agent & Training:** `RL_ALGORITHM` (PPO, SAC, etc.), `POLICY_KWARGS` (neural network architecture), `TOTAL_TIMESTEPS`, `N_ENVS` (parallel environments), paths for `TENSORBOARD_LOG_DIR` and `MODEL_SAVE_DIR`.
- **Live Agent Configuration:** `AGENT_ACTION_INTERVAL_SECONDS` for how often a deployed agent updates parameters.

*Dive into `rl_config.py` for the full set of brain-building parameters.*

### Dynamic Configuration (`data/dynamic_config.json`) - On-The-Fly Tweaks

The `trading_bot.py` can load certain parameters from `data/dynamic_config.json`. This file allows you to change many of the settings found in `config.py` *without restarting the bot*. The bot periodically checks this file for modifications.

  - **How it works:** If `data/dynamic_config.json` exists, the bot merges its values with the base `config.py` settings, with `dynamic_config.json` taking precedence.
  - **Creation:** If it doesn't exist on first bot run, `trading_bot.py` will create it, populating it with serializable values from the current `config.py`.
  - **Updates:** You can edit this JSON file directly. The `config_updater` task in `trading_bot.py` will pick up changes. The web app also provides an interface to modify this file.
  - **Persistence:** Changes made here are written to the file and will persist across bot restarts unless the file is deleted (in which case it would be recreated from `config.py`).

This is super handy for live tuning without interrupting the bot's operation. Just be careful – with great power comes great responsibility (to not typo your JSON).

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

   **Optional Flags for `main.py` (passed to `trading_bot.py`):**

      * `--cleanup`: Cleans the database (drops tables) before starting. **Use with extreme caution.**
      * `--backup`: Backs up existing database tables before starting.
      * `--params-file path/to/your_ga_results.json`: Load optimized parameters from a GA run.
      * `--rl-agent-path path/to/your_rl_model.zip`: Load a trained RL agent model. This will override `--params-file` if both are provided, as the RL agent will dynamically set parameters.

    The `main.py` controller will:

      * Start `trading_bot.py` in a new console/process.
      * Start `telegram_interface.py` in a new console/process (if `TELEGRAM_INTERACTION` is `True` in `config.py`).
      * Monitor the `trading_bot.py` process and attempt restarts if it crashes, based on status written to `data/bot_status.json`.

    You can interact with the bot via the Telegram Bot set up by `telegram_interface.py`. Use the `/menu` command in your Telegram chat with the bot.

### Running the Genetic Algorithm Optimizer

To find (hopefully) better trading parameters using genetic evolution:

1. **Configure `ga_config.py`**: Set up the parameters you want to optimize, GA settings, data ranges, etc.
2. **Ensure Historical Data**: The GA needs historical trade data in your database for the specified date range. The `trading_bot.py` populates this over time, or you might need a separate data ingestion process if starting fresh.
3. **Run `ga_optimizer.py`**:
    ```bash
    python ga_optimizer.py
    ```
    This will take a while, depending on your population size, number of generations, and the amount of historical data. Results (best parameters, plots) will be saved to the directory specified in `ga_config.RESULTS_DIR` (default: `ga_optimization_results`).

### Running the Reinforcement Learning Trainer

To train an RL agent to dynamically adjust trading parameters:

1. **Configure `rl_config.py`**: Define the observation/action spaces, reward function, agent hyperparameters, and data ranges.
2. **Ensure Historical Data**: Similar to GA, RL training requires historical OHLCV data. The `load_and_split_data` utility (called by `rl_trainer.py`) will fetch and prepare this from your database.
3. **Run `rl_trainer.py`**:
    ```bash
    python rl_trainer.py
    ```
    This is also a lengthy process. Training progress can be monitored via TensorBoard:
    ```bash
    tensorboard --logdir ./rl_tensorboard_logs/
    ```
    Trained models and VecNormalize statistics will be saved to `rl_trained_models/`.

### Running the Web Application (The Future GUI)

The web application provides a graphical interface for monitoring and potentially controlling the bot. It's still under development.

1. **Navigate to Project Root:** `cd pump_trader`

2. **Activate Virtual Environment.**

3. **Run the Flask App (Development Server):**
    There are a couple of ways to run a Flask development server:
   **Option A (Using `flask run` - Recommended for dev):**

    ```bash
    # Set the Flask app environment variable
    # On Linux/macOS:
    export FLASK_APP=web_app.app
    export FLASK_DEBUG=1 # Optional, for debug mode
    # On Windows (PowerShell):
    # $env:FLASK_APP = "web_app.app"
    # $env:FLASK_DEBUG = 1
    # On Windows (CMD):
    # set FLASK_APP=web_app.app
    # set FLASK_DEBUG=1

    flask run --host=0.0.0.0 --port=5001 # Or your desired port
    ```

   **Option B (Directly running `app.py` - Simpler, might have limitations):**

    ```bash
    python web_app/app.py
    ```

    This will typically start the web server on `http://0.0.0.0:89` (as configured in `web_app/app.py`). Access it via your web browser.

   **Note:** For production, deploy the Flask app using a proper WSGI server like Gunicorn or an ASGI server like Hypercorn (if you evolve it to be fully async). The `web_app/app.py` currently uses `async_adapter` for some database calls, hinting at mixed sync/async operations common in Flask when integrating async libraries.

-----

## 🛠️ Development and Contributing (If You're Feeling Brave)

### 🧼 Code Style

  - **PEP8:** Please. My eyes thank you.
  - **Docstrings:** Write them. Explain your genius (or your madness). Future you (and probably current me) will appreciate it.
  - **Logging:** Log like you mean it. `log_info("It did a thing")` is not helpful. `log_debug(f"Token {mint} passed volume check ({volume} > {threshold})")` is much better.
  - **Type Hinting:** We're trying to be grown-ups here. Use type hints.

### 🔁 Local Setup

You already did this in "Getting Started," right? *Right?*

```bash
python -m venv venv
source venv/bin/activate # or venv\Scripts\activate
pip install -r requirements.txt
# Potentially install dev requirements if you have a dev-requirements.txt
# pip install -r dev-requirements.txt
```

### 👾 Contributing

So you want to wrestle with the beast? Bold.

1. **Fork it:** Like it's a hot potato, but you actually want this one.
2. **Create your feature branch:** `git checkout -b feature/ActuallyMakeProfit`
3. **Commit your changes:** `git commit -m 'feat: Implement actual profit-making strategy (lol)'`
4. **Push to the branch:** `git push origin feature/ActuallyMakeProfit`
5. **Open a Pull Request:** And pray.

We appreciate contributions, especially if they fix the parts that are currently held together by digital duct tape and optimism.

-----

## 🧪 Testing (The "Does it Explode?" Phase)

Do we have comprehensive tests? Let's be real, this is a meme coin bot. But if *you've* added tests (you legend\!), run them with:

```bash
pytest
```

**Database for Testing:** Please, for the love of all that is holy, DO NOT test on your production database if you value your SOL. Spin up a separate test database. Messing with live funds during testing is how you end up writing sad blog posts, not Lambo purchase orders.

-----

## 📜 License

[](https://github.com/VicRejkia/pump_trader/blob/main/LICENSE)

This project is licensed under the **Apache License 2.0**. This means you can pretty much do whatever your heart desires with it – use it, modify it, build your own crypto empire (or elaborate birdhouse) with it.

**The Catch?** There's always a catch.
The main one is: **NO WARRANTY.** If this bot decides to trade your life savings for a coin that's literally a picture of a potato and then that potato coin goes to zero, well, that's on you. We provide the tools, you provide the risk assessment (and the therapy fund).

You can read the full, legally-binding, snooze-inducing text here:

> [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

**TL;DR (Lawyer-Free Version):**

> It's free. It's open. If it breaks, you get to keep both pieces. If it makes you rich, send us a postcard from your yacht. If it makes you poor, remember: it's only money (that you don't have anymore).

-----

## 🙌 Acknowledgments (To Those Who Paved the Way With Rugpulls)

  - To the brilliant minds behind `asyncpg`, `httpx`, `rich`, `pandas-ta`, `stable-baselines3`, `pygad`, `Flask`, and all the other open-source libraries that make this kind of glorious mess possible.
  - To the entire `pump.fun` ecosystem, for providing an endless stream of... opportunities.
  - To every "dev" who ever launched a coin with "SAFE" in the name right before pulling the liquidity – you are the cautionary tales that inspire us.
  - To the brave souls in Telegram chats who call bottoms at -90% and tops at +5%. Your service is noted.
  - And finally, to caffeine. The true MVP of any coding project.

-----

*Trade responsibly. Or don't. What are we, your mom? Just don't blame us when your $PEPEWIFHAT coin turns into $DUST.* 🤖💰📉📈