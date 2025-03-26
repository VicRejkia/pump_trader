"""
Handles trading logic including buy/sell decision making, volatility calculation, 
emergency sell triggers, and portfolio management.
"""
import asyncio
import numpy as np
import json
from datetime import datetime, timezone

from config import (SOL_TO_BUY, DEFAULT_STOP_LOSS, DEFAULT_TRAILING_TP, DEFAULT_BUY_FEE, 
                    DEFAULT_BUY_TIP, DEFAULT_SELL_FEE, DEFAULT_SELL_TIP, DEFAULT_VOLUME_THRESHOLD,
                    DEFAULT_MARKETCAP_THRESHOLD, MIN_VOLATILITY, DEFAULT_SCORE_THRESHOLD)
from database import get_total_supply, get_db
from api import calculate_market_cap
from logger import logger
from utils import play_buy_opportunity_sound, play_sell_sl_sound_async, play_sell_tp_sound_async, calculate_social_score

async def calculate_volatility(mint: str) -> float:
    """Calculates price volatility over the last hour"""
    async with (await get_db()).acquire() as conn:
        rows = await conn.fetch('''
            SELECT price FROM trades 
            WHERE mint = $1 
            AND timestamp > NOW() - INTERVAL '1 hour'
            ORDER BY timestamp
        ''', mint)
        prices = [row['price'] for row in rows]
    return np.std(prices) if len(prices) > 1 else 0.0

async def emergency_sell_all():
    """Sells all positions during critical drawdown"""
    async with (await get_db()).acquire() as conn:
        rows = await conn.fetch('''
            SELECT mint, SUM(remaining_tokens) AS total_tokens 
            FROM portfolio 
            WHERE tx_type = 'buy' AND status = 'active'
            GROUP BY mint
        ''')

        for row in rows:
            mint = row['mint']
            tokens = row['total_tokens']

            mcap_entry = await conn.fetchrow('''
                SELECT market_cap_calculated FROM trades 
                WHERE mint = $1 
                ORDER BY timestamp DESC LIMIT 1
            ''', mint)

            if mcap_entry:
                market_cap_sol = mcap_entry['market_cap_calculated']
                total_supply = await get_total_supply(mint)
                price = market_cap_sol / total_supply
                await execute_sell(mint, price, market_cap_sol, reason="Emergency Sell")

async def has_active_position(mint: str) -> bool:
    """Check for active positions"""
    async with (await get_db()).acquire() as conn:
        count = await conn.fetchval('''
            SELECT COUNT(*) FROM portfolio 
            WHERE mint = $1 AND status = 'active'
        ''', mint)
        return count > 0

async def check_trading_opportunities(websocket, state):
    """Check buy opportunities"""
    while not await state.get_shutdown():
        try:
            sol_price = await state.get_sol_price()
            if sol_price is None:
                logger.warning("SOL_PRICE not updated yet; skipping buy check.")
                await state.wait_or_interrupt(timeout=5) 
                continue

            async with (await get_db()).acquire() as conn:
                async with conn.transaction():
                    try:
                        rows = await asyncio.wait_for(conn.fetch('''
                            WITH LatestMarketCap AS (
                                SELECT 
                                    mint, marketCapSol, vTokensInBondingCurve, vSolInBondingCurve,
                                    ROW_NUMBER() OVER (PARTITION BY mint ORDER BY timestamp DESC) AS rn
                                FROM trades
                            )
                            SELECT 
                                t.mint, 
                                t.marketCapSol AS initial_market_cap,
                                t.vTokensInBondingCurve AS initial_v_tokens,
                                t.vSolInBondingCurve AS initial_v_sol,
                                SUM(CASE WHEN tr.tx_type = 'buy' THEN tr.sol_amount ELSE 0 END) AS total_buys,
                                SUM(CASE WHEN tr.tx_type = 'sell' THEN tr.sol_amount ELSE 0 END) AS total_sells,
                                COALESCE(SUM(CASE WHEN tr.timestamp > NOW() - INTERVAL '5 minutes' THEN tr.sol_amount ELSE 0 END), 0) AS volume,
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
                                t.is_active = TRUE AND
                                r.score IS NOT NULL AND
                                t.mint NOT IN (SELECT mint FROM portfolio WHERE status = 'active')
                            GROUP BY t.mint
                            HAVING 
                                (COALESCE(SUM(CASE WHEN tr.timestamp > NOW() - INTERVAL '5 minutes' THEN tr.sol_amount ELSE 0 END), 0) * $1) > $2 AND
                                (COALESCE(MAX(lmc.marketCapSol), 0) * $1) > $3
                            ORDER BY total_buys DESC;
                        ''', sol_price, DEFAULT_VOLUME_THRESHOLD, DEFAULT_MARKETCAP_THRESHOLD), timeout=10)
                    except asyncio.TimeoutError:
                        logger.error("⏳ Trading query timed out! Possible database lock?")
                        continue

                    logger.debug(f"Found {len(rows)} trading opportunities.")
                    for row in rows:
                        mint = row['mint']
                        initial_market_cap = float(row['initial_market_cap'])
                        initial_v_tokens = float(row['initial_v_tokens'])
                        initial_v_sol = float(row['initial_v_sol'])
                        latest_market_cap_sol = float(row['latest_marketcapsol'])
                        latest_v_tokens = float(row['latest_vtokens'])
                        latest_v_sol = float(row['latest_vsol'])
                        token_name = row['name']
                        token_symbol = row['symbol']
                        rugcheck_score = row['rugcheck_score']
                        website = row['website']
                        telegram = row['telegram']
                        twitter = row['twitter']

                        total_supply = float(await get_total_supply(mint))
                        if latest_market_cap_sol is None:
                            latest_market_cap_sol = calculate_market_cap(latest_v_tokens or initial_v_tokens or 0.0, latest_v_sol or initial_v_sol or 0.0, total_supply)

                        volatility = await calculate_volatility(mint)
                        if volatility < MIN_VOLATILITY:
                            continue

                        social_data = {"website": website, "telegram": telegram, "twitter": twitter}
                        social_score = calculate_social_score(social_data, token_name, token_symbol)
                        combined_score = rugcheck_score + social_score if rugcheck_score is not None else 1001

                        if combined_score > DEFAULT_SCORE_THRESHOLD:
                            await conn.execute("UPDATE tokens SET is_active = FALSE WHERE mint = $1", mint)
                            if mint in await state.get_subscriptions():
                                try:
                                    await asyncio.wait_for(websocket.send(json.dumps({
                                        "method": "unsubscribeTokenTrade",
                                        "keys": [row['mint']]
                                    })), timeout=5)  # ⏳ Timeout added

                                    logger.debug(f"✅ Unsubscribed {row['mint']} successfully")
                                except asyncio.TimeoutError:
                                    logger.error(f"⏳ WebSocket send timeout for {row['mint']}")
                                    continue
                                await state.remove_subscription(mint)
                            continue

                        price_per_token_sol = latest_market_cap_sol / total_supply
                        tokens_bought = (SOL_TO_BUY - DEFAULT_BUY_FEE - DEFAULT_BUY_TIP) / price_per_token_sol

                        await conn.execute('''
                            INSERT INTO portfolio 
                            (mint, tx_type, price, market_cap, sol_amount, tokens, 
                            fee, tip, remaining_tokens, stop_loss_price, highest_price, status, timestamp)
                            VALUES ($1, 'buy', $2, $3, $4, $5, $6, $7, $8, $9, $10, 'active', $11)
                        ''', mint, price_per_token_sol, latest_market_cap_sol, SOL_TO_BUY,
                            tokens_bought, DEFAULT_BUY_FEE, DEFAULT_BUY_TIP, tokens_bought, 
                            price_per_token_sol * (1 - DEFAULT_STOP_LOSS), price_per_token_sol, datetime.now(timezone.utc))

                        asyncio.create_task(play_buy_opportunity_sound())

            await state.wait_or_interrupt(timeout=3)

        except Exception as e:
            logger.error(f"check_trading_opportunities error: {e}")
            await state.wait_or_interrupt(timeout=5)

async def check_sell_opportunities():
    """Check sell conditions with connection pooling"""
    async with (await get_db()).acquire() as conn:
        async with conn.transaction():
            positions = await conn.fetch('''
                SELECT id, mint, price, tokens, highest_price, stop_loss_price, remaining_tokens 
                FROM portfolio 
                WHERE status = 'active'
            ''')

            for position in positions:
                pos_id = position['id']
                mint = position['mint']
                buy_price = position['price']
                tokens_held = position['tokens']
                highest_price = position['highest_price']
                stop_loss_price = position['stop_loss_price']
                remaining = position['remaining_tokens']

                mcap_entry = await conn.fetchrow('''
                    SELECT market_cap_calculated 
                    FROM trades 
                    WHERE mint = $1 
                    ORDER BY timestamp DESC LIMIT 1
                ''', mint)

                if not mcap_entry:
                    continue

                market_cap = mcap_entry['market_cap_calculated']
                total_supply = await get_total_supply(mint)
                current_price = market_cap / total_supply

                if current_price > highest_price:
                    await conn.execute('''
                        UPDATE portfolio 
                        SET highest_price = $1 
                        WHERE id = $2
                    ''', current_price, pos_id)

                trailing_stop_price = highest_price * (1 - DEFAULT_TRAILING_TP)
                if current_price <= stop_loss_price or current_price <= trailing_stop_price:
                    await execute_sell(mint, current_price, market_cap, 
                        "Stop Loss" if current_price <= stop_loss_price else "Trailing TP")

async def execute_sell(mint: str, current_price: float, market_cap_sol: float, reason: str) -> float:
    """Execute sell orders with transaction management"""
    async with (await get_db()).acquire() as conn:
        async with conn.transaction():
            try:
                buy_entries = await conn.fetch('''
                    SELECT id, price, tokens, remaining_tokens 
                    FROM portfolio 
                    WHERE mint = $1 AND tx_type = 'buy' AND status = 'active' 
                    ORDER BY timestamp ASC
                ''', mint)

                total_sold = 0
                total_profit = 0
                updates = []
                inserts = []

                for entry in buy_entries:
                    entry_id = entry['id']
                    buy_price = entry['price']
                    remaining = entry['remaining_tokens']

                    sell_amount = min(remaining, remaining - total_sold)
                    if sell_amount <= 0:
                        continue

                    gross_sol = sell_amount * current_price
                    total_buy_tokens = sum(e['remaining_tokens'] for e in buy_entries)
                    sell_fee = DEFAULT_SELL_FEE * (sell_amount / total_buy_tokens)
                    sell_tip = DEFAULT_SELL_TIP * (sell_amount / total_buy_tokens)
                    net_sol = gross_sol - sell_fee - sell_tip
                    buy_cost = (buy_price * sell_amount) + (DEFAULT_BUY_FEE + DEFAULT_BUY_TIP) * (sell_amount / total_buy_tokens)
                    profit = net_sol - buy_cost

                    new_remaining = remaining - sell_amount
                    status = 'active' if new_remaining > 0 else 'closed'

                    updates.append((new_remaining, status, entry_id))
                    inserts.append((
                        mint, current_price, market_cap_sol, net_sol, sell_amount, 
                        sell_fee, sell_tip, profit, reason, datetime.now(timezone.utc)
                    ))

                    total_sold += sell_amount
                    total_profit += profit
                    if total_sold >= sum(e['remaining_tokens'] for e in buy_entries):
                        break

                if updates:
                    await conn.executemany('''
                        UPDATE portfolio 
                        SET remaining_tokens = $1, status = $2 
                        WHERE id = $3
                    ''', updates)

                if inserts:
                    await conn.executemany('''
                        INSERT INTO portfolio 
                        (mint, tx_type, price, market_cap, sol_amount, tokens, fee, tip, profit, 
                        remaining_tokens, status, reason, timestamp)
                        VALUES ($1, 'sell', $2, $3, $4, $5, $6, $7, $8, 0, 'closed', $9, $10)
                    ''', inserts)

                logger.info(f"✅ Sold {total_sold} tokens of {mint} for {total_profit:.4f} SOL profit ({reason})")

                if reason == "Stop Loss":
                    asyncio.create_task(play_sell_sl_sound_async())
                elif reason == "Trailing TP":
                    asyncio.create_task(play_sell_tp_sound_async())

                return total_profit

            except Exception as e:
                logger.error(f"❌ Sell execution failed for {mint}: {e}")
                return 0.0
