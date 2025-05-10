import argparse
import asyncio
import os
import sys
from trading_bot import TradingBot
from logger import setup_logging, log_info, log_debug, log_error, rotate_log_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PumpTrader Bot")
    parser.add_argument("--cleanup", action="store_true", help="Clean up database before starting the bot. Deletes data permanently!")
    parser.add_argument("--backup", action="store_true", help="Backup database before starting the bot.")
    parser.add_argument("--params-file", type=str, default=None, help="Path to JSON file containing optimized parameters from GA.")
    parser.add_argument("--rl-agent-path", type=str, default=None, help="Path to the trained RL agent model file (e.g., .zip for SB3). Overrides --params-file.")

    args = parser.parse_args()

    # Set policy for Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def run_bot():
        bot = TradingBot(
            cleanup=args.cleanup,
            backup=args.backup,
            params_file=args.params_file,
            rl_agent_path=args.rl_agent_path
        )
        try:
            await bot.main()
        except (KeyboardInterrupt, SystemExit):
            log_info(":stop_button: [bold red]Interrupted by user.[/bold red] Exiting.")
        except Exception as e:
            log_error(f":x: Unexpected error: {e}", exc_info=True)
        finally:
            await bot.shutdown()

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nShutdown requested by user...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Bot shutdown complete.")