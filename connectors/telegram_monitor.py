import re
from bs4 import BeautifulSoup
import httpx
import asyncio

async def check_telegram_channel(tg_url: str) -> dict:
    """
    Checks a Telegram channel link for validity and extracts info.
    Works for both public (/s/) and private-style pages.

    Args:
        tg_url: The URL of the Telegram channel to check.

    Returns:
        A dictionary containing channel information.
    """
    result = {
        "valid": False,
        "title": None,
        "members": None,
        "online": None,
        "public_preview": False,
        "message_count": None,
        "error": None
    }

    # 1. Validate the link format
    match = re.search(r"t\.me/([a-zA-Z0-9_]+)", tg_url)
    if not match:
        result["error"] = "Invalid Telegram link format"
        return result

    username = match.group(1)
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # 2. Scrape the main channel page for basic info
        try:
            main_url = f"https://t.me/{username}"
            resp = await client.get(main_url, headers=headers)

            if resp.status_code != 200:
                result["error"] = f"HTTP Error: {resp.status_code}"
                return result

            soup = BeautifulSoup(resp.text, "html.parser")

            title_tag = soup.find("div", {"class": "tgme_page_title"})
            extra_tag = soup.find("div", {"class": "tgme_page_extra"})

            if not title_tag or not extra_tag:
                result["error"] = "Channel not found or page structure is unexpected."
                return result

            result["title"] = title_tag.get_text(strip=True)
            extra_text = extra_tag.get_text(strip=True).lower()

            # Updated regex to find 'members' or 'subscribers'
            member_match = re.search(r"([\d\s,]+)(?:members|subscribers)", extra_text.replace('\n', ' '))
            if member_match:
                result["members"] = int(re.sub(r"[\s,]", "", member_match.group(1)))

            online_match = re.search(r"([\d\s,]+)online", extra_text.replace('\n', ' '))
            if online_match:
                result["online"] = int(re.sub(r"[\s,]", "", online_match.group(1)))

            if result["title"] and result["members"] is not None:
                result["valid"] = True

        except httpx.RequestError as e:
            result["error"] = f"Network error while checking main link: {e}"
            return result
        except Exception as e:
            result["error"] = f"An unexpected error occurred: {e}"
            return result

        # 3. Scrape the public preview (/s/) page for message count
        if result["valid"]:
            try:
                public_url = f"https://t.me/s/{username}"
                resp_pub = await client.get(public_url, headers=headers)
                if resp_pub.status_code == 200:
                    soup_pub = BeautifulSoup(resp_pub.text, "html.parser")
                    
                    # FIX: A public preview only exists if message containers are found.
                    messages = soup_pub.find_all("div", {"class": "tgme_widget_message_wrap"})
                    if messages:
                        result["public_preview"] = True
                        result["message_count"] = len(messages)
            except Exception:
                # Silently fail if the public page can't be checked
                pass

    return result

def main():
    # Example usage
    #url = "https://t.me/flashorca"
    #url = "https://t.me/db_butt_token"  # Change to test different channels
    #url = "https://t.me/homelessdegens"  # Change to test different channels
    #url = "https://t.me/frogwifhat_FWIF"  # Change to test different channels
    url = "https://t.me/adzillaofficial"  # Change to test different channels
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(check_telegram_channel(url))
    print(result)

if __name__ == "__main__":
    main()
    