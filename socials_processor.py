# socials_processor.py
"""
Handles fetching, scoring, and storing social media links for tokens.
"""

import asyncio
import json
import traceback
from urllib.parse import urlparse
import httpx

from database import DatabaseClient
from logger import logger
from state import GlobalState
# Assuming these validation functions exist in utils.py
from utils import is_valid_website, is_valid_telegram, is_valid_twitter

class SocialsProcessor:
    def __init__(self, state: GlobalState, db_client: DatabaseClient):
        self.state = state
        self.db_client = db_client
        logger.info("SocialsProcessor initialized.")

    async def _fetch_metadata(self, uri: str) -> dict | None:
        """Fetches JSON metadata from a given URI."""
        if not uri or not uri.startswith('http'):
            logger.debug(f"Invalid or missing URI for social metadata: {uri}")
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                # Use GET, respecting redirects
                response = await client.get(uri)
                response.raise_for_status() # Raise HTTPStatusError for bad responses (4xx or 5xx)
                # Check content type - be lenient but prefer application/json
                content_type = response.headers.get('content-type', '').lower()
                if 'application/json' in content_type:
                     metadata = response.json()
                     logger.debug(f"Successfully fetched JSON metadata from {uri}")
                     return metadata
                else:
                    logger.warning(f"Unexpected content type '{content_type}' received from metadata URI {uri}. Expected JSON.")
                    # Attempt to parse anyway, might be mislabeled
                    try:
                        metadata = response.json()
                        logger.debug(f"Successfully parsed non-JSON labeled metadata from {uri}")
                        return metadata
                    except json.JSONDecodeError:
                         logger.error(f"Failed to decode non-JSON content from {uri}. Content: {response.text[:200]}...")
                         return None

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching social metadata from {uri}: {e.response.status_code} {e.response.reason_phrase}")
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching social metadata from {uri}")
        except httpx.RequestError as e:
            logger.warning(f"Request error fetching social metadata from {uri}: {e}")
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON from {uri}: {e}. Response text: {response.text[:200]}...")
        except Exception as e:
            logger.error(f"Unexpected error fetching social metadata from {uri}: {e}", exc_info=True)

        return None

    def _calculate_social_score(self, social_data: dict, token_name: str | None, token_symbol: str | None) -> int:
        """
        Computes a social risk score based on provided social data.
        Lower score is better (less penalty). Max penalty is 100.
        """
        total_penalty = 0
        token_name = (token_name or "").lower()
        token_symbol = (token_symbol or "").lower()

        # --- Website Check ---
        website = social_data.get("website") or social_data.get("homepage") or social_data.get("url") # Common keys
        if not website:
            total_penalty += 30 # Major penalty for no website
            logger.debug("Social Score Penalty: +30 (No Website)")
        elif not isinstance(website, str):
             total_penalty += 30 # Invalid type
             logger.debug(f"Social Score Penalty: +30 (Invalid Website type: {type(website)})")
        elif not is_valid_website(website):
            total_penalty += 20 # Penalty for invalid format/URL
            logger.debug(f"Social Score Penalty: +20 (Invalid Website URL: {website})")
        else:
            # Bonus for domain matching name/symbol (simple check)
            try:
                parsed = urlparse(website)
                domain = parsed.netloc.lower().replace('www.', '') # Normalize domain
                if token_name and (domain.startswith(token_name) or token_name in domain):
                     total_penalty -= 5 # Small bonus
                     logger.debug(f"Social Score Bonus: -5 (Website domain '{domain}' matches name '{token_name}')")
                elif token_symbol and (domain.startswith(token_symbol) or token_symbol in domain):
                     total_penalty -= 5 # Small bonus
                     logger.debug(f"Social Score Bonus: -5 (Website domain '{domain}' matches symbol '{token_symbol}')")
            except Exception:
                pass # Ignore parsing errors for bonus check

        # --- Telegram Check ---
        telegram = social_data.get("telegram") or social_data.get("tg") # Common keys
        if not telegram:
            total_penalty += 20
            logger.debug("Social Score Penalty: +20 (No Telegram)")
        elif not isinstance(telegram, str):
             total_penalty += 20 # Invalid type
             logger.debug(f"Social Score Penalty: +20 (Invalid Telegram type: {type(telegram)})")
        elif not is_valid_telegram(telegram):
            total_penalty += 10 # Penalty for invalid format/URL
            logger.debug(f"Social Score Penalty: +10 (Invalid Telegram URL: {telegram})")

        # --- Twitter Check ---
        twitter = social_data.get("twitter") or social_data.get("x") # Common keys
        if not twitter:
            total_penalty += 20
            logger.debug("Social Score Penalty: +20 (No Twitter/X)")
        elif not isinstance(twitter, str):
             total_penalty += 20 # Invalid type
             logger.debug(f"Social Score Penalty: +20 (Invalid Twitter type: {type(twitter)})")
        elif not is_valid_twitter(twitter):
            total_penalty += 10 # Penalty for invalid format/URL
            logger.debug(f"Social Score Penalty: +10 (Invalid Twitter URL: {twitter})")

        # --- External Links Check (Common in Metaplex standard) ---
        external_url = social_data.get("external_url")
        if external_url and website and external_url != website:
             # If external_url exists and differs from website, it might be slightly suspicious or just redundant
             total_penalty += 5
             logger.debug(f"Social Score Penalty: +5 (external_url differs from website)")
        elif external_url and not website:
             # If external_url exists but website doesn't, treat external_url as website for scoring
             if not isinstance(external_url, str):
                 total_penalty += 30
                 logger.debug(f"Social Score Penalty: +30 (Invalid external_url type: {type(external_url)})")
             elif not is_valid_website(external_url):
                 total_penalty += 20
                 logger.debug(f"Social Score Penalty: +20 (Invalid external_url: {external_url})")


        # Ensure score is within 0-100 range
        final_score = min(max(total_penalty, 0), 100)
        logger.debug(f"Calculated Social Score (Penalty): {final_score}")
        return final_score

    async def _update_token_socials(self, mint: str, website: str | None, telegram: str | None, twitter: str | None, score: int):
        """Updates the token record in the database with social info."""
        try:
            async with self.db_client.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tokens
                    SET website = $2,
                        telegram = $3,
                        twitter = $4,
                        socials_score = $5,
                        socials_last_checked = NOW()
                    WHERE mint = $1
                """, mint, website, telegram, twitter, score)
            logger.info(f"💾 Updated socials for {mint}. Score: {score} (Website: {'Y' if website else 'N'}, TG: {'Y' if telegram else 'N'}, TW: {'Y' if twitter else 'N'})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update socials in DB for {mint}: {e}", exc_info=True)
            return False

    async def process_token(self, mint: str):
        """Fetches, scores, and updates social info for a given token mint."""
        logger.debug(f"Processing socials for token: {mint}")
        token_info = None
        try:
            # 1. Fetch token URI, name, symbol from DB
            async with self.db_client.pool.acquire() as conn:
                # Fetch uri, name, symbol from tokens table
                # Use COALESCE for name/symbol in case they are NULL in DB
                token_info = await conn.fetchrow("""
                    SELECT uri, COALESCE(name, '') as name, COALESCE(symbol, '') as symbol
                    FROM tokens
                    WHERE mint = $1
                """, mint)

            if not token_info:
                logger.warning(f"Token {mint} not found in DB for social processing.")
                return
            if not token_info['uri']:
                logger.debug(f"Token {mint} has no metadata URI. Skipping social processing.")
                # Optionally update DB to mark as checked with no URI?
                # await self._update_token_socials(mint, None, None, None, 100) # Max penalty if no URI? Or specific score?
                return

            # 2. Fetch metadata from URI
            metadata = await self._fetch_metadata(token_info['uri'])
            if not metadata:
                logger.warning(f"Could not fetch or parse metadata for {mint} from {token_info['uri']}. Cannot process socials.")
                 # Update DB to mark as checked but failed? Score as high penalty?
                await self._update_token_socials(mint, None, None, None, 90) # High penalty for failed fetch
                return

            # 3. Extract social links (handle different possible keys)
            social_links = {
                "website": metadata.get("website") or metadata.get("homepage") or metadata.get("url") or metadata.get("external_url"),
                "telegram": metadata.get("telegram") or metadata.get("tg"),
                "twitter": metadata.get("twitter") or metadata.get("x")
            }
            # Basic type validation
            for key, value in social_links.items():
                if value is not None and not isinstance(value, str):
                    logger.warning(f"Invalid type for social link '{key}' in metadata for {mint}: {type(value)}. Treating as null.")
                    social_links[key] = None


            # 4. Calculate score
            social_score = self._calculate_social_score(
                social_links,
                token_info['name'],
                token_info['symbol']
            )

            # 5. Update DB
            await self._update_token_socials(
                mint,
                social_links["website"],
                social_links["telegram"],
                social_links["twitter"],
                social_score
            )

        except Exception as e:
            logger.error(f"💥 Unexpected error processing socials for {mint}: {e}", exc_info=True)