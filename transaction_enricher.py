# transaction_enricher.py

import os
import asyncio
import httpx
from dotenv import load_dotenv
from bot_logger import logger
from config import _DRPC_ENDPOINT
from state_manager import GlobalState
from database_handler import DatabaseClient

# Load environment variables from .env
load_dotenv()
DRPC_API_KEY = os.getenv("DRPC_API_KEY")
if not DRPC_API_KEY:
    logger.error("DRPC_API_KEY not set in environment.")

async def transaction_enricher_worker(state: GlobalState, db_client: DatabaseClient):
    """
    Pulls transaction signatures from a queue, fetches their statuses in batch
    via dRPC, filters confirmed ones, then fetches their details and updates
    the database with the trader's wallet address.

    Uses query-param authentication (`dkey`) with dRPC Solana RPC endpoint.
    Assumes _DRPC_ENDPOINT is configured like:
      'https://lb.drpc.org/ogrpc?network=solana'
    """
    logger.info("🚀 Transaction Enricher worker started.")
    enrichment_queue = state.get_enrichment_queue()
    BATCH_SIZE = 100       # Number of signatures per batch
    BATCH_TIMEOUT = 10     # Seconds to wait for queue items

    # Append API key as query parameter
    endpoint = f"{_DRPC_ENDPOINT}&dkey={DRPC_API_KEY}"
    HEADERS = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(headers=HEADERS, timeout=45.0) as client:
        while not state.shutdown_event.is_set():
            # 1. Collect signatures
            signatures = []
            try:
                start = asyncio.get_event_loop().time()
                while len(signatures) < BATCH_SIZE:
                    remaining = BATCH_TIMEOUT - (asyncio.get_event_loop().time() - start)
                    if remaining <= 0:
                        break
                    sig = await asyncio.wait_for(enrichment_queue.get(), timeout=remaining)
                    signatures.append(sig)
                    enrichment_queue.task_done()
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                logger.info("Transaction Enricher cancelled during fetch.")
                break
            except Exception as exc:
                logger.error(f"Error reading queue: {exc}")
                await asyncio.sleep(5)
                continue

            if not signatures:
                await asyncio.sleep(1)
                continue

            # 2. Batch getSignatureStatuses
            status_payload = [
                {"jsonrpc": "2.0", "id": idx+1, "method": "getSignatureStatuses",
                 "params": [[sig], {"searchTransactionHistory": True}]}
                for idx, sig in enumerate(signatures)
            ]
            try:
                resp = await client.post(endpoint, json=status_payload)
                resp.raise_for_status()
                status_results = resp.json()
            except Exception as exc:
                logger.error(f"Error fetching signature statuses: {exc}")
                await asyncio.sleep(2)
                continue

            # Filter confirmed signatures
            confirmed_sigs = [
                signatures[res['id'] - 1]
                for res in status_results
                if res.get('result') and res['result'].get('value')
            ]
            if not confirmed_sigs:
                continue

            # 3. Batch getTransaction for confirmed signatures
            tx_payload = [
                {"jsonrpc": "2.0", "id": idx+1, "method": "getTransaction",
                 "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]}
                for idx, sig in enumerate(confirmed_sigs)
            ]
            try:
                resp = await client.post(endpoint, json=tx_payload)
                resp.raise_for_status()
                tx_results = resp.json()
            except Exception as exc:
                logger.error(f"Error fetching transactions: {exc}")
                await asyncio.sleep(2)
                continue

            # 4. Parse responses and prepare DB updates
            update_params = []
            for res in tx_results:
                if res.get('result'):
                    try:
                        # First account key is fee payer (trader)
                        payer = res['result']['transaction']['message']['accountKeys'][0]['pubkey']
                        sig = confirmed_sigs[res['id'] - 1]
                        update_params.append((payer, sig))
                    except Exception as exc:
                        logger.warning(f"Parse error for tx id {res.get('id')}: {exc}")
                elif res.get('error'):
                    logger.warning(f"RPC error for tx id {res.get('id')}: {res['error']}" )

            # 5. Update DB
            if update_params:
                try:
                    async with db_client.pool.acquire() as conn:
                        await conn.executemany(
                            "UPDATE trades SET trader_pubkey = $1 WHERE signature = $2",
                            update_params
                        )
                    logger.info(f"Enriched {len(update_params)} trades with wallet addresses.")
                except Exception as exc:
                    logger.error(f"DB update error: {exc}")

            # Respect rate limits
            await asyncio.sleep(1.5)

    logger.info("🛑 Transaction Enricher worker shutting down.")