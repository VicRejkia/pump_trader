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

- [🎞️ Demo](#️demo)
- [💭 Why This Bot Exists](#-why-this-bot-exists)
- [🏁 Getting Started (for the impatient)](#-getting-started-for-the-impatient)
- [🌍 Overview](#-overview)
- [⚙️ Features](#️features)
- [🏗️ Architecture](#️architecture)
- [🔧 Installation](#-installation)
- [⚙️ Configuration](#️configuration)
- [🚀 Usage](#-usage)
- [🛠️ Development and Contributing](#️development-and-contributing)
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
- 🗃️ **`database.py` DatabaseClient**: Handles DB connections, migrations, and backups.
- 🧠 **`trading.py` Trading Manager**: Implements buy/sell logic with multi-stage checks.
- 🧪 **`rugcheck.py` Rugcheck**: Calls RugCheck API, evaluates token sketchiness.
- 📡 **`socials_processor.py` SocialsProcessor**: Scores social metadata and link quality.

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

Inside `config.py`, you’ll find:
- Trade thresholds
- RugCheck API endpoints
- Logging levels
- Meme resistance dial (okay still not real but someday...)

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

```
http://www.apache.org/licenses/LICENSE-2.0
```

TL;DR:
> No warranty. No guarantees. No crying in crypto.

---

## 🙌 Acknowledgments

- Built on the backs of open-source legends: `asyncpg`, `httpx`, `rich`, and friends.
- Inspired by countless Telegram scams, rugged devs, and the eternal hope of making it.
- Dedicated to the ones who bought the top so others may live.

---

*Trade responsibly. Or just embrace the chaos.* 🤖💰
