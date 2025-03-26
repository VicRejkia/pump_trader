async def trade_worker(state):
    """Processes trade messages from queue and writes them in batches to the database."""
    while not await state.get_shutdown():
        logger.debug("💚 trade_worker: still running")
        try:
            queue = state.websocket_handler.trade_queue
            BATCH_SIZE = 50  # Increased batch size for efficiency

            # Collect batch with timeout
            batch = []
            for _ in range(BATCH_SIZE):
                try:
                    trade = await asyncio.wait_for(queue.get(), timeout=2)
                    batch.append(trade)
                except asyncio.TimeoutError:
                    break

            if not batch:
                await asyncio.sleep(0.1)
                continue

            # Prepare parameters for batch insert
            trade_params = []
            mints = []
            from api import calculate_market_cap

            for data in batch:
                mint = data['mint']
                if mint not in await state.get_subscriptions():
                    queue.task_done()
                    continue

                mints.append(mint)
                trade_params.append((
                    data['signature'],
                    mint,
                    data['txType'],
                    Decimal(str(data['tokenAmount'])),
                    Decimal(str(data['solAmount'])),
                    Decimal(str(data['solAmount'] / data['tokenAmount'])) if data['tokenAmount'] else 0,
                    data['bondingCurveKey'],
                    Decimal(str(data['vTokensInBondingCurve'])),
                    Decimal(str(data['vSolInBondingCurve'])),
                    Decimal(str(data['marketCapSol'])),
                    calculate_market_cap(
                        data.get('vTokensInBondingCurve', 0),
                        data.get('vSolInBondingCurve', 0),
                        data.get('totalSupply', TOTAL_SUPPLY)
                    ),
                    datetime.now(timezone.utc)
                ))

            if not trade_params:
                continue

            async with _db_pool.acquire() as conn:
                async with conn.transaction():
                    # Batch insert trades
                    await conn.executemany('''
                        INSERT INTO trades (
                            signature, mint, tx_type, token_amount, sol_amount, price,
                            bondingCurveKey, vTokensInBondingCurve, vSolInBondingCurve,
                            marketCapSol, market_cap_calculated, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (signature) DO NOTHING
                    ''', trade_params)

                    # Batch update last_trade timestamps
                    if mints:
                        await conn.execute('''
                            UPDATE tokens 
                            SET last_trade = NOW() 
                            WHERE mint = ANY($1)
                        ''', mints)

            # Mark all processed tasks as done
            for _ in batch:
                queue.task_done()

            logger.debug(f"✅ Processed {len(trade_params)} trades in batch")

        except Exception as e:
            logger.error(f"🚨 Trade worker error: {e}")
            await asyncio.sleep(5)