async def fetch_social_data(uri: str, token_name: str, token_symbol: str):
    """Fetches social data from a given URI and computes a social score."""
    from utils import calculate_social_score
    social_data = {"website": None, "telegram": None, "twitter": None}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(uri, timeout=10)
            if response.status_code == 200:
                data = response.json()
                social_data["website"] = data.get("website")
                social_data["telegram"] = data.get("telegram")
                social_data["twitter"] = data.get("twitter")
            else:
                logger.warning(f"⚠ Failed to fetch social data for URI {uri}: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error fetching social data for {uri}: {e}", exc_info=True)
    social_score = calculate_social_score(social_data, token_name, token_symbol)
    return social_data, social_score

def calculate_social_score(social_data: dict, token_name: str, token_symbol: str) -> int:
    """Computes a social risk score based on provided social data."""
    total_penalty = 0
    token_name = (token_name or "").lower()
    token_symbol = (token_symbol or "").lower()
    website = social_data.get("website")
    if not website:
        total_penalty += 30
    else:
        from utils import is_valid_website
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
        from utils import is_valid_telegram
        if not is_valid_telegram(telegram):
            total_penalty += 10
    twitter = social_data.get("twitter")
    if not twitter:
        total_penalty += 20
    else:
        from utils import is_valid_twitter
        if not is_valid_twitter(twitter):
            total_penalty += 10
    return min(max(total_penalty, 0), 100)
