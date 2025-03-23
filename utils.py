"""
Helper functions and utilities for the trading bot.
Includes URL validation, audio alerts, and log formatting.
"""

import os
import winsound
from urllib.parse import urlparse

def is_valid_telegram(url: str) -> bool:
    """Validates if the provided URL is a valid Telegram link."""
    return url.startswith("https://t.me/") and "/joinchat/" not in url

def is_valid_twitter(url: str) -> bool:
    """Validates if the provided URL is a valid Twitter link."""
    return url.startswith(("https://twitter.com/", "https://x.com/"))

def is_valid_website(url: str) -> bool:
    """Validates if the provided URL is a proper website URL (not a social media domain)."""
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc not in ["x.com", "t.me", "telegram.org"]

def play_wav(file_path: str):
    """Synchronously plays a WAV file using winsound."""
    try:
        winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing the file {file_path}: {e}")

async def play_buy_opportunity_sound():
    """Asynchronously plays an alert sound for a buy opportunity."""
    import asyncio
    loop = asyncio.get_running_loop()
    wav_file = "assets/alert.wav"
    if not os.path.exists(wav_file):
        print(f"Sound file not found: {wav_file}")
        return
    await loop.run_in_executor(None, play_wav, wav_file)

def play_sell_sl_sound():
    """Synchronously play the stop-loss sell sound."""
    try:
        winsound.PlaySound("assets/hupe.wav", winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing sell SL sound: {e}")

def play_sell_tp_sound():
    """Synchronously play the take profit sell sound."""
    try:
        winsound.PlaySound("assets/ka_ching.wav", winsound.SND_FILENAME | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Error playing sell TP sound: {e}")

async def play_sell_sl_sound_async():
    """Asynchronously play the stop-loss sell sound."""
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, play_sell_sl_sound)

async def play_sell_tp_sound_async():
    """Asynchronously play the take profit sell sound."""
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, play_sell_tp_sound)

def format_buy_order_log(mint: str, price_per_token: float, tokens_bought: float, market_cap: float) -> str:
    """Formats the log message for a buy order."""
    from config import SOL_PRICE
    if SOL_PRICE:
        price_usd = price_per_token * SOL_PRICE
        market_cap_usd = market_cap * SOL_PRICE
        return (
            f"★★★ BUY Order ★★★\n"
            f"│ Token: {mint}\n"
            f"│ Price: {price_per_token:.8f} SOL (${price_usd:.8f} USD)\n"
            f"│ Market Cap: {market_cap:,.2f} SOL (${market_cap_usd:,.2f} USD)\n"
            f"│ Tokens Bought: {tokens_bought}\n"
        )
    else:
        return (
            f"★★★ BUY Order ★★★\n"
            f"│ Token: {mint}\n"
            f"│ Price: {price_per_token:.8f} SOL\n"
            f"│ Market Cap: {market_cap:,.2f} SOL\n"
            f"│ Tokens Bought: {tokens_bought}\n"
        )

def calculate_social_score(social_data: dict, token_name: str, token_symbol: str) -> int:
    """Computes a social risk score based on provided social data."""
    total_penalty = 0
    token_name = (token_name or "").lower()
    token_symbol = (token_symbol or "").lower()
    
    website = social_data.get("website")
    if not website:
        total_penalty += 30
    else:
        if not is_valid_website(website):
            total_penalty += 20
        else:
            from urllib.parse import urlparse
            parsed = urlparse(website)
            domain = parsed.netloc
            if domain.endswith(f".{token_name}") or domain.endswith(f".{token_symbol}"):
                total_penalty -= 5
    
    telegram = social_data.get("telegram")
    if not telegram:
        total_penalty += 20
    else:
        if not is_valid_telegram(telegram):
            total_penalty += 10
    
    twitter = social_data.get("twitter")
    if not twitter:
        total_penalty += 20
    else:
        if not is_valid_twitter(twitter):
            total_penalty += 10
            
    return min(max(total_penalty, 0), 100)
