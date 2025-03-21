"""
Entry point for the trading bot.
Initializes the database, starts SOL price updates, WebSocket communication,
and trading tasks.
"""

import asyncio
from database import init_db
from api import update_sol_price, rugcheck_worker, check_missing_rugcheck_data, refresh_rugcheck_queue
from trading import check_trading_opportunities
from websocket_handler import WebSocketHandler
from logger import setup_logging, logger

async def main():
    setup_logging(debug=True)
    await init_db()
    ws_handler = WebSocketHandler()
    await ws_handler.connect()
    
    tasks = [
        asyncio.create_task(update_sol_price()),
        asyncio.create_task(check_trading_opportunities(ws_handler.websocket)),
        asyncio.create_task(rugcheck_worker()),
        asyncio.create_task(check_missing_rugcheck_data()),
        asyncio.create_task(refresh_rugcheck_queue()) 
    ]
    tasks.extend(ws_handler.start())
    
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Tasks cancelled. Exiting gracefully.")
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")
        # Initiate shutdown in the websocket handler
        await ws_handler.shutdown()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
