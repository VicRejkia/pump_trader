# Pump Trader - Solana Meme Coin Trading Bot

## LICENSE  

[![GitHub](https://img.shields.io/github/license/VicRejkia/pump_trader)](https://github.com/VicRejkia/pump_trader/LICENSE)


   Copyright 2025 - Vic Rejkia

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

---



Pump Trader is an advanced, asynchronous Python trading bot designed to monitor market trends, evaluate token risk using external APIs, and execute buy/sell decisions based on sophisticated multi-stage trading logic. The project features real-time WebSocket data ingestion, PostgreSQL database integration, robust logging, and advanced risk assessment using third-party services like RugCheck and social media analysis.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development and Contributing](#development-and-contributing)
- [Testing](#testing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview

Pump Trader is built to:
- **Continuously Monitor Market Data:** Connects to a real-time WebSocket API for trading data.
- **Evaluate Token Risk:** Integrates with the RugCheck API to fetch risk scores and automatically deactivates tokens that exceed a defined risk threshold.
- **Execute Multi-Stage Trading Strategies:** Uses a configurable multi-stage buy and sell logic with stop-loss, take-profit, and trailing stop parameters.
- **Analyze Social Media Signals:** Processes social data from various sources to adjust risk scoring and trading decisions.

## Features

- **Asynchronous Processing:** Leverages Python’s `asyncio` for non-blocking operations and high performance.
- **Database Integration:** Uses PostgreSQL (with asyncpg) to store tokens, trades, migrations, and risk evaluation data.
- **Robust Logging:** Implements detailed logging (with rotating log files) using the Python `logging` module and `rich` for enhanced console output.
- **Configurable Parameters:** All trading parameters, API endpoints, and risk thresholds are defined in a centralized configuration module.
- **Modular Design:** Key components (e.g., database operations, WebSocket handling, trade management, RugCheck integration, social media processing) are separated into independent modules.
- **Graceful Shutdown:** Supports signal handling to safely terminate and clean up running tasks and connections.
- **Backup & Cleanup Options:** Provides command-line flags to backup the database or cleanup existing data before starting the bot.

## Architecture

The project is organized into several core modules:

- **Configuration (`config.py`):** Stores all constant settings including API endpoints, trading thresholds, fees, and other parameters.
- **Database (`database.py`):** Manages PostgreSQL connections and CRUD operations, including token backups and migrations.
- **Logging (`logger.py`):** Sets up file and console logging with customizable levels and log rotation.
- **Main Bot (`main.py`):** Bootstraps the application, handles signal registration, and coordinates background tasks (e.g., trading checks, price updates, WebSocket connection).
- **Trading Manager:** Implements the buy/sell strategy logic with multi-stage trading checks.
- **Risk Assessment (`rugcheck.py`):** Integrates with the RugCheck API for fetching and processing token risk data.
- **Socials Processor (`socials_processor.py`):** Processes and scores social media links and metadata to refine token risk evaluation.

This modular structure ensures maintainability and scalability, allowing new features or risk factors to be integrated seamlessly.

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database instance
- Required system libraries for building Python packages (e.g., for asyncpg and httpx)

### Dependencies

Install the required packages via pip:

```bash
pip install -r requirements.txt
```

A sample `requirements.txt` might include:
- `asyncpg`
- `httpx`
- `aiolimiter`
- `python-dotenv`
- `rich`
- `beautifulsoup4`

### Clone the Repository

Clone the project repository from GitHub:

```bash
git clone https://github.com/yourusername/pump-trader.git
cd pump-trader
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables (adjust the values as needed):

```ini
# Database configuration
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_DATABASE=your_database

# Solana wallet configuration for RugCheck authentication
SOLANA_PRIVATE_KEY=your_solana_private_key

# Additional configuration can be defined here if needed
```

### Application Settings

The `config.py` file contains important parameters, such as:
- Trading amounts and thresholds (e.g., `SOL_TO_BUY`, `INITIAL_SOL_BALANCE`)
- API endpoints (e.g., WebSocket URL, RugCheck API URLs)
- Risk and social scoring thresholds
- Logging settings

Review and modify `config.py` to fine-tune your trading strategy and risk evaluation parameters.

## Usage

### Running the Bot

To start the trading bot, simply run:

```bash
python main.py
```

You can also use command-line arguments:
- `--cleanup` : Drop application tables before startup.
- `--backup` : Backup database tables before startup.

For example:

```bash
python main.py --backup
```

### Graceful Shutdown

The bot listens for `SIGINT` (Ctrl+C) or `SIGTERM` signals and will gracefully shut down, ensuring that all tasks are cancelled and resources are released properly.

## Development and Contributing

### Code Style

- Follow PEP 8 style guidelines.
- Write comprehensive docstrings for modules and functions.
- Ensure logging statements provide sufficient context for debugging.

### Setting Up a Development Environment

It is recommended to create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Contributing Guidelines

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write tests for new functionality.
4. Submit a pull request with a clear description of your changes.

## Testing

To run tests (if available), you might use:

```bash
pytest
```

Ensure that you have set up a testing database if your tests require database interaction.

## License

This project is licensed under the [MIT License](LICENSE). See the LICENSE file for more details.

## Acknowledgments

- Special thanks to the contributors of open-source libraries such as `asyncpg`, `httpx`, and `rich`.
- Inspired by innovative trading strategies and risk assessment methods.

---
