"""
Handles trading logic including buy/sell decision making, volatility calculation, 
emergency sell triggers, and portfolio management.
"""
import state
import asyncio
import numpy as np
from datetime import datetime
import aiosqlite
import json
from utils import play_sell_sl_sound_async, play_sell_tp_sound_async

from config import (SOL_TO_BUY, DEFAULT_STOP_LOSS, DEFAULT_TRAILING_TP, DEFAULT_BUY_FEE, 
                    DEFAULT_BUY_TIP, DEFAULT_SELL_FEE, DEFAULT_SELL_TIP, DEFAULT_VOLUME_THRESHOLD,
                    DEFAULT_MARKETCAP_THRESHOLD, MIN_VOLATILITY, DEFAULT_SCORE_THRESHOLD, DB_NAME)
from database import get_total_supply
from api import calculate_market_cap
from logger import logger
from utils import play_buy_opportunity_sound, calculate_social_score

async def calculate_volatility(mint: str) -> float:
    """
    Calculates the standard deviation of token prices over the last hour.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        query = '''SELECT price FROM trades 
                   WHERE mint = ? 
                   AND timestamp > datetime('now', '-1 hour')
                   ORDER BY timestamp'''
        async with db.execute(query, (mint,)) as cursor:
            prices = [row[0] for row in await cursor.fetchall()]
    return np.std(prices) if len(prices) > 1 else 0.0

async def emergency_sell_all():
    """
    Sells all active positions if a critical drawdown is detected.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        query = '''SELECT mint, SUM(remaining_tokens) 
                   FROM portfolio 
                   WHERE tx_type = 'buy' AND status = 'active'
                   GROUP BY mint'''
        async with db.execute(query) as cursor:
            positions = await cursor.fetchall()

        for mint, tokens in positions:
            async with db.execute('''SELECT market_cap_calculated 
                                      FROM trades 
                                      WHERE mint = ? 
                                      ORDER BY timestamp DESC LIMIT 1''', (mint,)) as mcap_cursor:
                mcap_entry = await mcap_cursor.fetchone()
            if mcap_entry:
                market_cap_sol = mcap_entry[0]
                total_supply = await get_total_supply(mint)
                price = market_cap_sol / total_supply
                await execute_sell(mint, price, market_cap_sol, reason="Emergency Sell")
            else:
                logger.error(f"No market data for emergency sell of {mint}")

async def has_active_position(mint: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        query = "SELECT COUNT(*) FROM portfolio WHERE mint = ? AND status = 'active'"
        async with db.execute(query, (mint,)) as cursor:
            count = await cursor.fetchone()
            return count[0] > 0                

async def check_trading_opportunities(websocket):
    """
    Checks for tokens that meet buy criteria and places buy orders.
    """
    while not await state.state.get_shutdown():
        sol_price = await state.state.get_sol_price()  # ✅ Get latest SOL price

        if sol_price is None:
            logger.warning("SOL_PRICE not updated yet; skipping buy opportunities check.")
            await asyncio.sleep(5)
            continue

        try:
            async with aiosqlite.connect(DB_NAME) as db:
                query = """
                        WITH LatestMarketCap AS (
                            SELECT 
                                mint,
                                marketCapSol,
                                vTokensInBondingCurve,
                                vSolInBondingCurve,
                                ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                            FROM trades
                        )
                        SELECT 
                            t.mint,
                            SUM(CASE WHEN tr.tx_type = 'buy' THEN tr.sol_amount ELSE 0 END) AS total_buys,
                            SUM(CASE WHEN tr.tx_type = 'sell' THEN tr.sol_amount ELSE 0 END) AS total_sells,
                            COALESCE(SUM(CASE WHEN tr.timestamp > datetime('now', '-5 minutes') THEN tr.sol_amount ELSE 0 END), 0) AS volume,
                            MAX(lmc.marketCapSol) AS latest_marketCapSol,
                            MAX(lmc.vTokensInBondingCurve) AS latest_vTokens,  
                            MAX(lmc.vSolInBondingCurve) AS latest_vSol, 
                            MAX(r.tokenMeta_name) AS name,
                            MAX(r.tokenMeta_symbol) AS symbol,
                            MAX(r.score) AS rugcheck_score,
                            MAX(t.website) AS website,
                            MAX(t.telegram) AS telegram,
                            MAX(t.twitter) AS twitter
                        FROM tokens AS t
                        LEFT JOIN rugcheck AS r ON t.mint = r.mint
                        LEFT JOIN trades AS tr ON t.mint = tr.mint
                        LEFT JOIN LatestMarketCap AS lmc ON t.mint = lmc.mint AND lmc.rn = 1
                        WHERE 
                            t.is_active = 1 AND
                            r.score IS NOT NULL AND
                            t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
                        GROUP BY t.mint
                        HAVING 
                            (COALESCE(SUM(CASE WHEN tr.timestamp > datetime('now', '-5 minutes') THEN tr.sol_amount ELSE 0 END), 0) * ?) > ? AND
                            (COALESCE(MAX(lmc.marketCapSol), 0) * ?) > ?
                        ORDER BY total_buys DESC;
                    """
                params = (sol_price, DEFAULT_VOLUME_THRESHOLD, sol_price, DEFAULT_MARKETCAP_THRESHOLD)

                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    logger.debug(f"Found {len(rows)} potential tokens to evaluate for buying")
                    if rows and rows[0] is not None:
                        for row in rows:
                            mint = row[0]
                            volume = row[3]
                            latest_market_cap_sol = row[4]
                            latest_v_tokens = row[5] 
                            latest_v_sol = row[6]    
                            token_name = row[7]
                            token_symbol = row[8]
                            rugcheck_score = row[9]
                            website = row[10]
                            telegram = row[11]
                            twitter = row[12]

                            total_supply = await get_total_supply(mint)

                            # If market cap is missing, calculate using latest trade data:
                            if latest_market_cap_sol is None:
                                try:
                                    latest_market_cap_sol = calculate_market_cap(
                                        latest_v_tokens or 0,  # Use latest values from trades
                                        latest_v_sol or 0,
                                        total_supply
                                    )
                                    logger.info(f"Calculated market cap for {mint}: {latest_market_cap_sol} SOL")
                                except Exception as e:
                                    logger.error(f"Failed to calculate market cap for {mint}: {e}")
                                    continue

                            # ✅ Calculate volatility
                            volatility = await calculate_volatility(mint)
                            if volatility < MIN_VOLATILITY:
                                logger.debug(f"Skipping {mint} due to low volatility: {volatility}")
                                continue

                            # ✅ Handle missing RugCheck score
                            if rugcheck_score is None:
                                logger.warning(f"Skipping {mint} - RugCheck data not available")
                                continue

                            # ✅ Calculate social score
                            social_data = {"website": website, "telegram": telegram, "twitter": twitter}
                            social_score = calculate_social_score(social_data, token_name, token_symbol)

                            # ✅ Combine scores (lower is better)
                            combined_score = rugcheck_score + social_score

                            if combined_score > DEFAULT_SCORE_THRESHOLD:
                                logger.debug(f"Skipping {mint} due to high combined risk score: {combined_score}. Archiving token.")
                                await db.execute("UPDATE tokens SET is_active = 0 WHERE mint = ?", (mint,))
                                
                                # ✅ Unsubscribe from token trades if currently subscribed
                                active_subs = await state.state.get_subscriptions()
                                if mint in active_subs:
                                    payload = {"method": "unsubscribeTokenTrade", "keys": [mint]}
                                    await websocket.send(json.dumps(payload))
                                    await state.state.remove_subscription(mint)  # ✅ Remove from state
                                    logger.debug(f"Unsubscribed from {mint} due to high risk score.")
                                continue

                            # ✅ Calculate price per token and amount to buy
                            price_per_token_sol = latest_market_cap_sol / total_supply
                            tokens_bought = (SOL_TO_BUY - DEFAULT_BUY_FEE - DEFAULT_BUY_TIP) / price_per_token_sol

                            # ✅ Insert into portfolio
                            await db.execute('''
                                INSERT INTO portfolio 
                                (mint, tx_type, price, market_cap, sol_amount, tokens, 
                                fee, tip, remaining_tokens, stop_loss_price, highest_price, status, timestamp)
                                VALUES (?, 'buy', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                            ''', (
                                    mint,
                                    price_per_token_sol,              # price
                                    latest_market_cap_sol,            # market_cap
                                    SOL_TO_BUY,                       # sol_amount
                                    tokens_bought,                    # tokens
                                    DEFAULT_BUY_FEE,                  # fee
                                    DEFAULT_BUY_TIP,                  # tip
                                    tokens_bought,                    # remaining_tokens
                                    price_per_token_sol * (1 - DEFAULT_STOP_LOSS),  # stop_loss_price
                                    price_per_token_sol,              # highest_price
                                    datetime.utcnow()                 # timestamp
                                ))
                            await db.commit()

                            # ✅ Log buy order
                            price_usd = price_per_token_sol * sol_price
                            market_cap_usd = latest_market_cap_sol * sol_price
                            logger.info(f"""
★★★ BUY Order ★★★
│ SYMBOL: {token_symbol} | Name: {token_name} | Token: {mint}
│ Price: {price_per_token_sol:.8f} SOL (${price_usd:.8f} USD) | Market Cap: {latest_market_cap_sol:,.2f} SOL (${market_cap_usd:,.2f} USD)
│ Tokens Bought: {tokens_bought}
                                """)

                            # ✅ Play buy alert sound (async)
                            asyncio.create_task(play_buy_opportunity_sound())

                # ✅ Check sell opportunities
                await check_sell_opportunities()

        except Exception as e:
            logger.error(f"Error checking trade opportunities: {e}")

        # ✅ Check frequently (e.g., every 3 seconds)
        await asyncio.sleep(3)

async def check_sell_opportunities():
    """
    Checks active portfolio positions and executes sell orders if stop loss or take profit conditions are met.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, mint, price, tokens, highest_price, stop_loss_price, remaining_tokens FROM portfolio WHERE status = 'active'") as cursor:
            positions = await cursor.fetchall()
        for position in positions:
            pos_id, mint, buy_price, tokens_held, highest_price, stop_loss_price, remaining = position

            if highest_price is None:
                highest_price = buy_price  # Fallback to purchase price
                async with db.execute('''
                    UPDATE portfolio 
                    SET highest_price = ? 
                    WHERE id = ?
                ''', (highest_price, pos_id)):
                    await db.commit()

            # Get latest market cap
            async with db.execute('''SELECT market_cap_calculated FROM trades 
                                       WHERE mint = ? ORDER BY timestamp DESC LIMIT 1''', (mint,)) as cur:
                row = await cur.fetchone()
                if not row or row[0] is None:
                    continue
                market_cap = row[0]

            total_supply = await get_total_supply(mint)
            if total_supply is None or total_supply <= 0:
                continue

            current_price = market_cap / total_supply

            # Update highest_price if current price is higher
            if highest_price is None or current_price > highest_price:
                highest_price = current_price
                async with db.execute('''
                    UPDATE portfolio 
                    SET highest_price = ? 
                    WHERE id = ?
                ''', (highest_price, pos_id)):
                    await db.commit()

            if current_price > (highest_price or buy_price):
                highest_price = current_price
                await db.execute("UPDATE portfolio SET highest_price = ? WHERE id = ?", (highest_price, pos_id))
            trailing_stop_price = highest_price * (1 - DEFAULT_TRAILING_TP)
            if current_price <= stop_loss_price:
                await execute_sell(mint, current_price, row[0], reason="Stop Loss")
            elif current_price <= trailing_stop_price:
                await execute_sell(mint, current_price, row[0], reason="Trailing TP")
            new_stop_loss = current_price * (1 - DEFAULT_STOP_LOSS)
            if new_stop_loss > stop_loss_price:
                await db.execute("UPDATE portfolio SET stop_loss_price = ? WHERE id = ?", (new_stop_loss, pos_id))
            await db.commit()

async def execute_sell(mint: str, current_price: float, market_cap_sol: float, reason: str) -> float:
    """
    Executes sell orders for a given token based on a specified reason.
    Returns the total profit from the sell transactions.
    """
    total_sold = 0
    total_profit = 0
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''SELECT id, price, tokens, remaining_tokens FROM portfolio 
                                  WHERE mint = ? AND tx_type = 'buy' AND status = 'active' 
                                  ORDER BY timestamp ASC''', (mint,)) as cursor:
            buy_entries = await cursor.fetchall()
        async with db.execute("SELECT SUM(sol_amount) FROM portfolio WHERE mint = ? AND tx_type = 'buy'", (mint,)) as inv_cursor:
            total_investment = (await inv_cursor.fetchone())[0] or 0
        tokens_to_sell = sum(entry[3] for entry in buy_entries)
        for entry in buy_entries:
            entry_id, buy_price, _, remaining = entry
            sell_amount = min(remaining, tokens_to_sell - total_sold)
            if sell_amount <= 0:
                continue
            gross_sol = sell_amount * current_price
            total_buy_tokens = sum(entry[3] for entry in buy_entries)
            sell_fee = DEFAULT_SELL_FEE * (sell_amount / total_buy_tokens)
            sell_tip = DEFAULT_SELL_TIP * (sell_amount / total_buy_tokens)
            net_sol = gross_sol - sell_fee - sell_tip
            buy_cost = (buy_price * sell_amount) + (DEFAULT_BUY_FEE + DEFAULT_BUY_TIP) * (sell_amount / total_buy_tokens)
            profit = net_sol - buy_cost
            new_remaining = remaining - sell_amount
            status = 'active' if new_remaining > 0 else 'closed'
            await db.execute("UPDATE portfolio SET remaining_tokens = ?, status = ? WHERE id = ?", (new_remaining, status, entry_id))
            await db.execute('''INSERT INTO portfolio 
                                (mint, tx_type, price, market_cap, sol_amount, tokens, fee, tip, profit, remaining_tokens, status, reason, timestamp)
                                VALUES (?, 'sell', ?, ?, ?, ?, ?, ?, ?, 0, 'closed', ?, ?)''',
                             (mint, current_price, market_cap_sol, net_sol, sell_amount, sell_fee, sell_tip, profit, reason, datetime.utcnow()))
            total_sold += sell_amount
            total_profit += profit
            if total_sold >= tokens_to_sell:
                break
        await db.commit()
    logger.info(f"Executed sell for {mint}: Sold {total_sold} tokens, Profit: {total_profit:.4f} SOL")
    # Play corresponding sound based on reason:
    if reason == "Stop Loss":
        # Play stop-loss sound asynchronously
        asyncio.create_task(play_sell_sl_sound_async())
    elif reason == "Trailing TP":
        # Play take profit sound asynchronously
        asyncio.create_task(play_sell_tp_sound_async())
    return total_profit
