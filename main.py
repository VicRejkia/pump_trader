import argparse
from trading_bot import TradingBot
from logger import setup_logging, log_info, log_debug, log_error, rotate_log_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file containing optimized parameters from GA.")
    args = parser.parse_args()

    bot = TradingBot(cleanup=args.cleanup, backup=args.backup, params_file=args.params_file)
    try:
        bot.loop.run_until_complete(bot.main())
    except (KeyboardInterrupt, SystemExit):
        log_info(":stop_button: [bold red]Interrupted by user.[/bold red] Exiting.")
    except Exception as e:
        log_error(f":x: Unexpected error: {e}", exc_info=True)
    finally:
        bot.loop.run_until_complete(bot.shutdown())
        bot.loop.close()
