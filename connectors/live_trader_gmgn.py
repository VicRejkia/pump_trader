# live_trader.py (GMGN API Version)

import os
import httpx # Using httpx for async requests
import base64
import time
import asyncio
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
# We won't use SolanaClient here as GMGN has its own send_transaction endpoint
# from solana.rpc.api import Client as SolanaClient
# from solana.rpc.types import TxOpts
# from solana.rpc.commitment import Confirmed

from bot_logger import logger
# Import your main config module to access TRADING_MODE and other settings
import config.config as bot_config # Use an alias

load_dotenv()

PRIVATE_KEY_STRING = os.getenv("SOLANA_PRIVATE_KEY")
# RPC_ENDPOINT is not directly used for sending if using GMGN's send_transaction,
# but good to have for other potential Solana interactions or if you choose to send yourself.
# RPC_ENDPOINT = os.getenv("RPC_ENDPOINT")

WALLET_KEYPAIR = None
WALLET_PUBLIC_KEY_STR = None

if PRIVATE_KEY_STRING:
    try:
        WALLET_KEYPAIR = Keypair.from_base58_string(PRIVATE_KEY_STRING)
        WALLET_PUBLIC_KEY_STR = str(WALLET_KEYPAIR.pubkey())
    except Exception as e:
        logger.error(f"Failed to load Solana wallet from private key: {e}")
        WALLET_KEYPAIR = None
        WALLET_PUBLIC_KEY_STR = None
else:
    if bot_config.TRADING_MODE in ["paper_trading", "live"]:
        logger.critical("SOLANA_PRIVATE_KEY not found in .env. 'paper_trading' and 'live' modes WILL FAIL.")


GMGN_API_HOST = "https://gmgn.ai"
GMGN_GET_SWAP_ROUTE_ENDPOINT = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/get_swap_route"
GMGN_SEND_TRANSACTION_ENDPOINT = f"{GMGN_API_HOST}/txproxy/v1/send_transaction"
GMGN_GET_TRANSACTION_STATUS_ENDPOINT = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/get_transaction_status"


async def get_gmgn_swap_transaction(
    token_in_address: str,
    token_out_address: str,
    in_amount_lamports: str, # Amount in lamports as string
    from_address: str,
    slippage_percent: float, # e.g., 10 for 10%
    fee_sol: float,          # e.g., 0.006 SOL
    is_anti_mev: bool = True # Default to true as it's a feature
):
    """
    Fetches the swap route and unsigned transaction from GMGN API.
    Returns the API response data or None on error.
    """
    params = {
        "token_in_address": token_in_address,
        "token_out_address": token_out_address,
        "in_amount": in_amount_lamports,
        "from_address": from_address,
        "slippage": slippage_percent,
        "fee": fee_sol, # Network priority fees and PRC node tip fees.
        "is_anti_mev": str(is_anti_mev).lower() # API expects bool as string 'true' or 'false'
    }
    logger.debug(f"GMGN get_swap_route params: {params}")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client: # Increased timeout
            response = await client.get(GMGN_GET_SWAP_ROUTE_ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"GMGN get_swap_route HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"GMGN get_swap_route Error: {e}", exc_info=True)
        return None


async def send_gmgn_signed_transaction(signed_tx_base64: str, is_anti_mev: bool = True):
    """
    Submits a signed transaction to GMGN's send_transaction endpoint.
    Returns the API response data or None on error.
    """
    payload = {
        "chain": "sol",
        "signedTx": signed_tx_base64,
        "isAntiMev": is_anti_mev # Optional, set 'true' when swap with JITO Anti-MEV.
    }
    logger.debug(f"GMGN send_transaction payload (signedTx omitted for brevity)")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client: # Increased timeout
            response = await client.post(GMGN_SEND_TRANSACTION_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"GMGN send_transaction HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"GMGN send_transaction Error: {e}", exc_info=True)
        return None


async def get_gmgn_transaction_status(tx_hash: str, last_valid_block_height: int):
    """
    Queries the status of a submitted transaction.
    Returns the API response data or None on error.
    """
    params = {
        "hash": tx_hash,
        "last_valid_height": last_valid_block_height
    }
    logger.debug(f"GMGN get_transaction_status params: {params}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(GMGN_GET_TRANSACTION_STATUS_ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"GMGN get_transaction_status HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"GMGN get_transaction_status Error: {e}", exc_info=True)
        return None


async def execute_live_gmgn_trade(
    trigger_price: float, # Price that triggered the trade logic, for paper trading simulation
    action: str, # "buy" or "sell"
    input_token_address: str, # e.g., SOL mint for a buy
    output_token_address: str, # e.g., Meme coin mint for a buy
    # Amount is of the input_token_address, in lamports if SOL or base units if token
    in_amount_lamports_str: str,
    slippage_percent: float, # e.g., 10 for 10%
    # Fee for GMGN API is network priority + RPC tip. We'll use your bot's "tip" config for this.
    network_and_tip_fee_sol: float,
    is_anti_mev: bool = True
):
    """
    Handles trade execution via GMGN API for paper and live modes.
    Returns a dictionary like the previous execute_live_pumpportal_trade.
    """
    current_trading_mode = bot_config.TRADING_MODE.lower()

    if current_trading_mode not in ["paper_trading", "live"]:
        logger.error(f"execute_live_gmgn_trade called with invalid mode: {current_trading_mode}")
        return {"success": False, "mode": current_trading_mode, "error": "Invalid trading mode"}

    if not WALLET_KEYPAIR or not WALLET_PUBLIC_KEY_STR:
        logger.error(f"[{current_trading_mode.upper()} MODE] Wallet not loaded. Cannot execute GMGN trade.")
        return {"success": False, "mode": current_trading_mode, "error": "Wallet not loaded"}

    # Step 1: Get Swap Route and Unsigned Transaction from GMGN
    route_response = await get_gmgn_swap_transaction(
        token_in_address=input_token_address,
        token_out_address=output_token_address,
        in_amount_lamports=in_amount_lamports_str,
        from_address=WALLET_PUBLIC_KEY_STR,
        slippage_percent=slippage_percent,
        fee_sol=network_and_tip_fee_sol,
        is_anti_mev=is_anti_mev
    )

    if not route_response or route_response.get("code") != 0 or "data" not in route_response or "raw_tx" not in route_response["data"]:
        error_msg = route_response.get("msg", "Failed to get swap route from GMGN") if route_response else "No response from GMGN get_swap_route"
        logger.error(f"[{current_trading_mode.upper()} MODE] GMGN API Error: {error_msg}. Full response: {route_response}")
        return {"success": False, "mode": current_trading_mode, "error": error_msg}

    try:
        # Extract unsigned transaction and necessary details
        raw_tx_data = route_response["data"]["raw_tx"]
        swap_transaction_b64 = raw_tx_data["swapTransaction"] # This is base64 encoded
        last_valid_block_height = raw_tx_data["lastValidBlockHeight"] # For status query
        # recent_blockhash = raw_tx_data["recentBlockhash"] # Available if needed

        quote_data = route_response["data"].get("quote", {})
        expected_out_amount_lamports_str = quote_data.get("outAmount", "0")
        
        # Decode and deserialize the transaction
        swap_transaction_bytes = base64.b64decode(swap_transaction_b64)
        unsigned_tx = VersionedTransaction.deserialize(swap_transaction_bytes) # Deserialize from bytes

        # Sign the transaction
        unsigned_tx.sign([WALLET_KEYPAIR]) # Sign with your Keypair object
        signed_tx_bytes = unsigned_tx.serialize()
        signed_tx_b64 = base64.b64encode(signed_tx_bytes).decode('utf-8') # Encode to base64 string for sending
        
        tx_signature_str_from_local_signing = str(unsigned_tx.signatures[0])


        if current_trading_mode == "paper_trading":
            logger.info(f"[PAPER TRADING] GMGN: Prepared TX for {action} {input_token_address} -> {output_token_address}. Sig_prefix: {tx_signature_str_from_local_signing[:10]}... NOT SENDING.")
            
            # Simulate fill:
            # Use the expected_out_amount from the quote for paper trading.
            # If buying tokens (output is token), quantity_exchanged is tokens.
            # If selling tokens (output is SOL), quantity_exchanged is SOL.
            quantity_exchanged_simulated = 0.0
            try:
                quantity_exchanged_simulated = int(expected_out_amount_lamports_str)
                # Convert to human-readable units if needed for P&L (e.g., SOL or token decimals)
                # Assuming trigger_price is price of output_token in terms of input_token_units (e.g. lamports_in / tokens_out)
                # Or, if it's SOL/Token, and input is SOL, then expected_out_amount is tokens.
                # Price is input_amount / output_amount
                # If action is "buy", input is SOL, output is TOKEN. executed_price is SOL_per_TOKEN.
                # Price = in_amount_lamports / expected_out_amount_tokens
                if action == "buy" and input_token_address == "So11111111111111111111111111111111111111112": # Buying with SOL
                    if quantity_exchanged_simulated > 0: # quantity_exchanged_simulated is tokens
                        sim_executed_price_sol_per_token = int(in_amount_lamports_str) / quantity_exchanged_simulated
                    else: sim_executed_price_sol_per_token = trigger_price # Fallback
                elif action == "sell" and output_token_address == "So11111111111111111111111111111111111111112": # Selling for SOL
                    # quantity_exchanged_simulated is SOL lamports. input_amount_lamports_str is token units.
                    if int(in_amount_lamports_str) > 0:
                         sim_executed_price_sol_per_token = quantity_exchanged_simulated / int(in_amount_lamports_str)
                    else: sim_executed_price_sol_per_token = trigger_price # Fallback
                else:
                    sim_executed_price_sol_per_token = trigger_price # Fallback for other cases

            except ValueError:
                logger.warning("[PAPER TRADING] Could not parse expected_out_amount for simulation.")
                sim_executed_price_sol_per_token = trigger_price

            return {
                "success": True, "mode": "paper_trading", "signature": f"PAPER_{tx_signature_str_from_local_signing}",
                "executed_price": sim_executed_price_sol_per_token,
                "quantity_exchanged": quantity_exchanged_simulated, # This is in lamports/base units of output_token
                "error": None, "last_valid_block_height": last_valid_block_height
            }

        elif current_trading_mode == "live":
            logger.info(f"[LIVE TRADING] GMGN: Sending signed TX for {action} {input_token_address} -> {output_token_address}. Local Sig: {tx_signature_str_from_local_signing}")
            
            send_response = await send_gmgn_signed_transaction(signed_tx_b64, is_anti_mev)

            if not send_response or send_response.get("code") != 0 or "data" not in send_response or not send_response["data"].get("hash"):
                error_msg = send_response.get("msg", "Failed to send transaction via GMGN") if send_response else "No response from GMGN send_transaction"
                logger.error(f"[LIVE TRADING] GMGN send_transaction API Error: {error_msg}. Full response: {send_response}")
                return {"success": False, "mode": "live", "error": error_msg}

            actual_tx_hash_from_gmgn = send_response["data"]["hash"]
            logger.info(f"Live {action} submitted via GMGN. GMGN Hash: {actual_tx_hash_from_gmgn}")
            logger.info(f"Track on Solscan (using GMGN hash): https://solscan.io/tx/{actual_tx_hash_from_gmgn}")
            logger.info(f"Original local signature was: {tx_signature_str_from_local_signing}")


            # --- Transaction Confirmation Polling ---
            confirmed = False
            expired = False
            poll_attempts = 0
            max_poll_attempts = 60 # Poll for up to 60 seconds (60 * 1s sleep)

            while not confirmed and not expired and poll_attempts < max_poll_attempts:
                await asyncio.sleep(1) # Wait 1 second between status checks
                poll_attempts += 1
                logger.debug(f"Polling GMGN tx status for {actual_tx_hash_from_gmgn}, attempt {poll_attempts}")
                status_response = await get_gmgn_transaction_status(actual_tx_hash_from_gmgn, last_valid_block_height)

                if status_response and status_response.get("code") == 0 and "data" in status_response:
                    status_data = status_response["data"]
                    if status_data.get("success") is True: # Transaction successfully added to the blockchain
                        confirmed = True
                        logger.info(f"✅ GMGN Transaction Confirmed: {actual_tx_hash_from_gmgn}")
                    elif status_data.get("expired") is True: # Transaction expired
                        expired = True
                        logger.warning(f"⚠️ GMGN Transaction Expired: {actual_tx_hash_from_gmgn}. Needs resubmission.")
                    elif status_data.get("failed") is True: # Transaction failed on-chain
                        expired = True # Treat as terminal
                        logger.error(f"❌ GMGN Transaction Failed on-chain: {actual_tx_hash_from_gmgn}. Details: {status_data}")
                    else:
                        logger.debug(f"GMGN Tx {actual_tx_hash_from_gmgn} status pending...")
                else:
                    logger.warning(f"Could not get valid status for GMGN tx {actual_tx_hash_from_gmgn}. Response: {status_response}")
            
            if not confirmed and not expired:
                 logger.warning(f"GMGN Tx {actual_tx_hash_from_gmgn} status unclear after {max_poll_attempts} attempts. Assuming not confirmed for now.")


            # For live mode, ideally, you'd parse the confirmed transaction from Solana chain
            # to get actual in/out amounts. GMGN quote gives `expected_out_amount`.
            live_quantity_exchanged = 0.0
            live_executed_price = trigger_price # Fallback
            if confirmed:
                try:
                    live_quantity_exchanged = int(expected_out_amount_lamports_str) # Use the quoted out amount
                    if action == "buy" and input_token_address == "So11111111111111111111111111111111111111112":
                        if live_quantity_exchanged > 0: live_executed_price = int(in_amount_lamports_str) / live_quantity_exchanged
                except ValueError:
                    logger.warning("[LIVE TRADING] Could not parse expected_out_amount for confirmed trade.")
            
            return {
                "success": confirmed, "mode": "live", "signature": actual_tx_hash_from_gmgn,
                "executed_price": live_executed_price, # This is an estimate based on quote
                "quantity_exchanged": live_quantity_exchanged, # Lamports/base units of output token, from quote
                "error": "Transaction expired or failed on-chain" if expired and not confirmed else ("Polling timed out" if not confirmed and not expired else None),
                "last_valid_block_height": last_valid_block_height
            }

    except Exception as e:
        logger.error(f"[{current_trading_mode.upper()} MODE] GMGN Unhandled Error in execute_live_gmgn_trade: {e}", exc_info=True)
        return {"success": False, "mode": current_trading_mode, "error": str(e)}