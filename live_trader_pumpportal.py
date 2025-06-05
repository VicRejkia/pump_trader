import os
import httpx
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client as SolanaClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed

from bot_logger import logger
# Import your main config module to access TRADING_MODE and other settings
import config as bot_config # Use an alias to avoid confusion if config is passed

load_dotenv()

PRIVATE_KEY_STRING = os.getenv("SOLANA_PRIVATE_KEY")
RPC_ENDPOINT = os.getenv("RPC_ENDPOINT")

WALLET_KEYPAIR = None
WALLET_PUBLIC_KEY = None
SOLANA_CLIENT = None

# Initialize wallet and client only if essential keys are present
# This allows the module to be imported even if keys are not set (e.g., for pure "simulate" mode)
if PRIVATE_KEY_STRING:
    try:
        WALLET_KEYPAIR = Keypair.from_base58_string(PRIVATE_KEY_STRING)
        WALLET_PUBLIC_KEY = str(WALLET_KEYPAIR.pubkey())
    except Exception as e:
        logger.error(f"Failed to load Solana wallet from private key: {e}")
        # Bot should not proceed to live/paper if wallet fails
        WALLET_KEYPAIR = None 
        WALLET_PUBLIC_KEY = None

if RPC_ENDPOINT:
    SOLANA_CLIENT = SolanaClient(RPC_ENDPOINT)
else:
    if bot_config.TRADING_MODE in ["paper_trading", "live"]:
        logger.warning("RPC_ENDPOINT not found in .env. 'paper_trading' and 'live' modes will fail to send transactions.")

PUMPORTAL_LOCAL_API_URL = bot_config._PUMPORTAL_LOCAL_API_URL

async def execute_live_pumpportal_trade(
    # Pass the specific price that triggered the buy/sell for paper trading simulation
    trigger_price: float,
    action: str,
    mint_address: str,
    amount_str: str, # Amount as a string (SOL or token units)
    denominated_in_sol: bool,
    slippage_percent: int,
    priority_fee_sol: float,
    pool: str = "auto"
):
    """
    Handles interaction with PumpPortal Local API for paper and live trading.
    Returns a dictionary:
    {
        "success": bool,
        "mode": str ("paper_trading" or "live"),
        "signature": str or None,
        "executed_price": float (actual or simulated),
        "quantity_exchanged": float (tokens bought/sold, or SOL received),
        "error": str or None
    }
    """
    # Use TRADING_MODE from the global bot_config
    current_trading_mode = bot_config.TRADING_MODE

    if current_trading_mode not in ["paper_trading", "live"]:
        logger.error(f"execute_live_pumpportal_trade called with invalid mode: {current_trading_mode}")
        return {"success": False, "mode": current_trading_mode, "error": "Invalid trading mode for live execution function"}

    if not WALLET_KEYPAIR or not WALLET_PUBLIC_KEY:
        logger.error(f"[{current_trading_mode.upper()} MODE] Wallet not loaded. Cannot execute trade.")
        return {"success": False, "mode": current_trading_mode, "error": "Wallet not loaded"}

    if current_trading_mode == "live" and not SOLANA_CLIENT:
        logger.error(f"[LIVE MODE] Solana client (RPC) not initialized. Cannot send transaction.")
        return {"success": False, "mode": "live", "error": "RPC client not initialized"}

    payload = {
        "publicKey": WALLET_PUBLIC_KEY,
        "action": action,
        "mint": mint_address,
        "amount": amount_str,
        "denominatedInSol": "true" if denominated_in_sol else "false",
        "slippage": slippage_percent,
        "priorityFee": priority_fee_sol,
        "pool": pool
    }

    logger.debug(f"[{current_trading_mode.upper()} MODE] Preparing API call to PumpPortal: {payload}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(PUMPORTAL_LOCAL_API_URL, data=payload) # Assuming form data
            response.raise_for_status()
        
        raw_tx_bytes = response.content
        unsigned_tx = VersionedTransaction.from_bytes(raw_tx_bytes)
        signed_tx = WALLET_KEYPAIR.sign_transaction(unsigned_tx)
        tx_signature_str = str(signed_tx.signatures[0])

        if current_trading_mode == "paper_trading":
            logger.info(f"[PAPER TRADING] Prepared TX for {action} on {mint_address}. Sig_prefix: {tx_signature_str[:10]}... NOT SENDING.")
            
            # Simulate fill for paper trading:
            # Use the trigger_price as the basis for simulation.
            # This is a simplified simulation. A real paper trader might fetch fresh quotes.
            quantity_exchanged_simulated = 0.0
            if denominated_in_sol and action == "buy": # Buying tokens with SOL
                if trigger_price > 0:
                    quantity_exchanged_simulated = float(amount_str) / trigger_price # Tokens bought
            elif not denominated_in_sol and action == "sell": # Selling tokens for SOL
                quantity_exchanged_simulated = float(amount_str) * trigger_price # SOL received
            else: # Selling SOL for tokens (less common for this param structure) or buying tokens with tokens
                 logger.warning(f"[PAPER TRADING] Complex simulation for {action} where denominatedInSol={denominated_in_sol}. Using 0 for quantity_exchanged.")


            return {
                "success": True, "mode": "paper_trading", "signature": f"PAPER_{tx_signature_str}",
                "executed_price": trigger_price, # Assume filled at the price that triggered the logic
                "quantity_exchanged": quantity_exchanged_simulated,
                "error": None
            }

        elif current_trading_mode == "live":
            if not SOLANA_CLIENT: # Should have been caught earlier, but double check
                return {"success": False, "mode": "live", "error": "RPC client not initialized for sending"}

            logger.info(f"[LIVE TRADING] Sending TX for {action} on {mint_address}. Sig: {tx_signature_str}")
            # Using skip_preflight=False for safety, you can change it
            options = TxOpts(skip_preflight=False, preflight_commitment=Confirmed) # Use preflight for safety
            
            tx_receipt = SOLANA_CLIENT.send_raw_transaction(txn=bytes(signed_tx), opts=options)
            actual_tx_signature = str(tx_receipt.value)
            
            logger.info(f"Live {action} submitted. Signature: {actual_tx_signature}")
            logger.info(f"Track on Solscan: https://solscan.io/tx/{actual_tx_signature}")

            # TODO: Implement robust transaction confirmation polling here.
            # TODO: After confirmation, fetch transaction details to get *actual* fill price and amounts.
            # This is critical for accurate P&L in live mode.
            # For now, we'll return success upon sending and use trigger_price as a placeholder.
            
            # Placeholder: In a real system, these would come from confirmed transaction details
            # If denominated_in_sol (buy with SOL): quantity_exchanged = tokens received
            # If not denominated_in_sol (sell tokens): quantity_exchanged = SOL received
            live_quantity_exchanged = 0.0
            if denominated_in_sol and action == "buy":
                 if trigger_price > 0: live_quantity_exchanged = float(amount_str) / trigger_price # Approx tokens
            elif not denominated_in_sol and action == "sell":
                 live_quantity_exchanged = float(amount_str) * trigger_price # Approx SOL

            return {
                "success": True, "mode": "live", "signature": actual_tx_signature,
                "executed_price": trigger_price, # Placeholder: replace with actual fill price
                "quantity_exchanged": live_quantity_exchanged, # Placeholder: replace with actual quantity
                "error": None
            }

    except httpx.HTTPStatusError as e:
        error_message = f"HTTP Error: {e.response.status_code} - {e.response.text}"
        logger.error(f"[{current_trading_mode.upper()} MODE] {error_message}", exc_info=True)
        return {"success": False, "mode": current_trading_mode, "error": error_message}
    except Exception as e:
        logger.error(f"[{current_trading_mode.upper()} MODE] Error: {e}", exc_info=True)
        return {"success": False, "mode": current_trading_mode, "error": str(e)}