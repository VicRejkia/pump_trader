# socials_processor.py
"""
Handles fetching, scoring, and storing social media links for tokens.
"""

import asyncio
import json
import traceback
from urllib.parse import urlparse, urlsplit
import httpx
from bs4 import BeautifulSoup # Added for HTML parsing

from database import DatabaseClient
from logger import logger
from state import GlobalState
# Assuming these validation functions exist in utils.py
from utils import is_valid_website, is_valid_telegram, is_valid_twitter

# Domain lists and scoring values are now loaded from config in __init__

class SocialsProcessor:
    def __init__(self, state: GlobalState, db_client: DatabaseClient, config: dict):
        self.state = state
        self.db_client = db_client
        self.config = config # Store config

        # Load scoring values from config
        self.penalty_no_website = config.get('SOCIALS_PENALTY_NO_WEBSITE', 40)
        self.penalty_invalid_website_type = config.get('SOCIALS_PENALTY_INVALID_WEBSITE_TYPE', 35)
        self.penalty_website_verify_skipped = config.get('SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED', 35)
        self.penalty_website_invalid_url = config.get('SOCIALS_PENALTY_WEBSITE_INVALID_URL', 35)
        self.penalty_website_timeout = config.get('SOCIALS_PENALTY_WEBSITE_TIMEOUT', 35)
        self.penalty_website_http_error = config.get('SOCIALS_PENALTY_WEBSITE_HTTP_ERROR', 35)
        self.penalty_website_other_error = config.get('SOCIALS_PENALTY_WEBSITE_OTHER_ERROR', 35)
        self.penalty_no_https = config.get('SOCIALS_PENALTY_NO_HTTPS', 10)
        self.penalty_website_no_mention = config.get('SOCIALS_PENALTY_WEBSITE_NO_MENTION', 15)
        self.penalty_common_platform_website = config.get('SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE', 10)
        self.penalty_no_telegram = config.get('SOCIALS_PENALTY_NO_TELEGRAM', 20)
        self.penalty_invalid_telegram_type = config.get('SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE', 20)
        self.penalty_invalid_telegram_url = config.get('SOCIALS_PENALTY_INVALID_TELEGRAM_URL', 10)
        self.penalty_no_twitter = config.get('SOCIALS_PENALTY_NO_TWITTER', 30)
        self.penalty_invalid_twitter_type = config.get('SOCIALS_PENALTY_INVALID_TWITTER_TYPE', 20)
        self.penalty_invalid_twitter_url = config.get('SOCIALS_PENALTY_INVALID_TWITTER_URL', 20)
        self.penalty_duplicate_links = config.get('SOCIALS_PENALTY_DUPLICATE_LINKS', 15)

        self.bonus_domain_match = config.get('SOCIALS_BONUS_DOMAIN_MATCH', -10)
        # self.bonus_news_gov_website = config.get('SOCIALS_BONUS_NEWS_GOV_WEBSITE', 0) # Currently 0 in config

        self.score_failed_metadata = config.get('SOCIALS_SCORE_FAILED_METADATA', 90)

        # Load domain sets from config
        self.disallowed_domains = config.get('SOCIALS_DISALLOWED_WEBSITE_DOMAINS', set())
        self.allowed_news_domains = config.get('SOCIALS_ALLOWED_NEWS_DOMAINS', set())

        # Shared HTTP client for website verification
        self._verify_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, limits=httpx.Limits(max_connections=5))

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

    async def _verify_website_details(self, url: str, token_name: str, token_symbol: str) -> dict:
        """Attempts to verify website reachability, security, and relevance."""
        results = {'uses_https': False, 'is_reachable': False, 'mentions_token': False, 'error': None}
        token_name_lower = (token_name or "").lower()
        token_symbol_lower = (token_symbol or "").lower()

        try:
            # Basic URL format check
            parsed_url = urlsplit(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                 results['error'] = "Invalid URL format"
                 logger.debug(f"Website Verify Fail ({url}): Invalid URL format")
                 return results

            results['uses_https'] = parsed_url.scheme == 'https'

            # Attempt connection
            logger.debug(f"Attempting to verify website: {url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'} # Basic user agent
            response = await self._verify_client.get(url, headers=headers)
            response.raise_for_status() # Check for 4xx/5xx errors

            results['is_reachable'] = True
            logger.debug(f"Website Verify Success ({url}): Reachable (Status: {response.status_code})")

            # Basic content check (if HTML)
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                page_content = ""
                if soup.title and soup.title.string:
                    page_content += soup.title.string.lower() + " "
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    page_content += meta_desc['content'].lower()

                # Check if token name or symbol appears (simple check)
                if token_name_lower and token_name_lower in page_content:
                    results['mentions_token'] = True
                    logger.debug(f"Website Verify Success ({url}): Found token name in title/desc.")
                elif token_symbol_lower and token_symbol_lower in page_content:
                     results['mentions_token'] = True
                     logger.debug(f"Website Verify Success ({url}): Found token symbol in title/desc.")
                else:
                     logger.debug(f"Website Verify Info ({url}): Token name/symbol not found in title/desc.")
            else:
                 logger.debug(f"Website Verify Info ({url}): Content type '{content_type}' not HTML, skipping content check.")


        except httpx.HTTPStatusError as e:
            results['error'] = f"HTTP Error {e.response.status_code}"
            logger.warning(f"Website Verify Fail ({url}): HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            results['error'] = "Timeout"
            logger.warning(f"Website Verify Fail ({url}): Timeout")
        except httpx.RequestError as e:
            # Covers connection errors, DNS errors etc.
            results['error'] = f"Request Error: {type(e).__name__}"
            logger.warning(f"Website Verify Fail ({url}): Request Error ({type(e).__name__})")
        except ImportError:
             results['error'] = "Missing 'beautifulsoup4' library"
             logger.error("Dependency missing: Please install 'beautifulsoup4' (`pip install beautifulsoup4`) for website content checking.")
        except Exception as e:
            results['error'] = f"Unexpected Error: {type(e).__name__}"
            logger.error(f"Website Verify Fail ({url}): Unexpected error: {e}", exc_info=True)

        return results

    # Added verification_results parameter
    def _calculate_social_score(self, social_data: dict, token_name: str | None, token_symbol: str | None, verification_results: dict | None) -> int:
        """
        Computes a social risk score based on social data and website verification.
        Lower score is better (less penalty). Max penalty is 100.
        """
        total_penalty = 0
        token_name = (token_name or "").lower()
        token_symbol = (token_symbol or "").lower()

        logger.debug(f"Social Links: {social_data}")

        # --- Website Check ---
        website = social_data.get("website") or social_data.get("homepage") or social_data.get("url") or social_data.get("external_url") # Consolidate check
        is_disallowed_website = False
        parsed_domain = None

        if not website:
            total_penalty += self.penalty_no_website
            logger.debug(f"Social Score Penalty: +{self.penalty_no_website} (No Website URL provided)")
        elif not isinstance(website, str):
            total_penalty += self.penalty_invalid_website_type
            logger.debug(f"Social Score Penalty: +{self.penalty_invalid_website_type} (Invalid Website type: {type(website)})")
        else:
            # 1. Parse domain and check if disallowed FIRST
            try:
                parsed_domain = urlparse(website).netloc.lower().replace('www.', '')
                if parsed_domain: # Ensure domain was parsed
                    is_disallowed_website = any(parsed_domain == disallowed or parsed_domain.endswith('.' + disallowed) for disallowed in self.disallowed_domains)
                    if is_disallowed_website:
                        total_penalty += self.penalty_common_platform_website
                        logger.debug(f"Social Score Penalty: +{self.penalty_common_platform_website} (Website URL domain '{parsed_domain}' is disallowed, skipping further checks)")
                else:
                    logger.warning(f"Could not parse domain from website URL: {website}")
                    # Treat as invalid URL? Apply penalty? For now, just log.
                    # total_penalty += self.penalty_website_invalid_url # Or a specific penalty for parsing failure

            except Exception as e:
                 logger.warning(f"Error parsing website URL '{website}' for disallowed check: {e}")
                 # Apply penalty? For now, just log.
                 # total_penalty += self.penalty_website_invalid_url

            # 2. If NOT disallowed, proceed with verification results
            if not is_disallowed_website:
                if verification_results is None:
                    # Should not happen if website URL exists and isn't disallowed, but handle defensively
                    total_penalty += self.penalty_website_verify_skipped
                    logger.warning(f"Social Score Penalty: +{self.penalty_website_verify_skipped} (Website verification skipped for {website})")
                elif verification_results['error']:
                    # Add penalty based on error type
                    if "Invalid URL" in verification_results['error']:
                        total_penalty += self.penalty_website_invalid_url
                    elif "Timeout" in verification_results['error']:
                        total_penalty += self.penalty_website_timeout
                    elif "HTTP Error" in verification_results['error']:
                        total_penalty += self.penalty_website_http_error
                    else: # Other request errors, unexpected errors
                        total_penalty += self.penalty_website_other_error
                    logger.debug(f"Social Score Penalty: +{total_penalty} (Website verification failed: {verification_results['error']})")
                else:
                    # Website is reachable, apply finer penalties/bonuses
                    if not verification_results['uses_https']:
                        total_penalty += self.penalty_no_https
                        logger.debug(f"Social Score Penalty: +{self.penalty_no_https} (Website does not use HTTPS)")
                    if not verification_results['mentions_token']:
                        total_penalty += self.penalty_website_no_mention
                        logger.debug(f"Social Score Penalty: +{self.penalty_website_no_mention} (Website does not mention token name/symbol)")

                    # Bonus for domain matching (only if not disallowed)
                    try:
                        # Domain already parsed as parsed_domain
                        if parsed_domain:
                            if token_name and (parsed_domain.startswith(token_name) or token_name in parsed_domain):
                                total_penalty += self.bonus_domain_match
                                logger.debug(f"Social Score Bonus: {self.bonus_domain_match} (Website domain '{parsed_domain}' matches name '{token_name}')")
                            elif token_symbol and (parsed_domain.startswith(token_symbol) or token_symbol in parsed_domain):
                                total_penalty += self.bonus_domain_match
                                logger.debug(f"Social Score Bonus: {self.bonus_domain_match} (Website domain '{parsed_domain}' matches symbol '{token_symbol}')")
                    except Exception:
                        pass # Ignore errors during bonus check

            # 3. Check for allowed news/gov domains (runs regardless of disallowed status)
            if parsed_domain: # Only check if domain was successfully parsed
                try:
                    is_allowed_news_gov = (
                        any(parsed_domain == allowed or parsed_domain.endswith('.' + allowed) for allowed in self.allowed_news_domains)
                        or parsed_domain.endswith('.gov')
                    )
                    if is_allowed_news_gov:
                        # total_penalty += self.bonus_news_gov_website # Apply bonus/penalty if configured
                        logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is an allowed news/gov domain.")
                    # else: # Optional: Log if domain is NOT allowed news/gov
                    #    logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is not in allowed news/gov list.")
                except Exception:
                    pass # Ignore parsing errors for this check too

            # Bonus if website is from major news outlet
            try:
                parsed_domain = urlparse(website).netloc.lower().replace('www.', '')
                # Check against base domains
                # Check against allowed news/gov domains
                is_allowed_news_gov = (
                    any(parsed_domain == allowed or parsed_domain.endswith('.' + allowed) for allowed in self.allowed_news_domains)
                    or parsed_domain.endswith('.gov')
                )
                if is_allowed_news_gov:
                    # total_penalty += self.bonus_news_gov_website # Apply bonus/penalty if configured
                    logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is an allowed news/gov domain.")
                # else: # Optional: Log if domain is NOT allowed news/gov
                #    logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is not in allowed news/gov list.")
            except Exception:
                pass # Ignore parsing errors for this check too

        # --- Telegram Check ---
        telegram = social_data.get("telegram") or social_data.get("tg") # Common keys
        if not telegram:
            total_penalty += self.penalty_no_telegram
            logger.debug(f"Social Score Penalty: +{self.penalty_no_telegram} (No Telegram)")
        elif not isinstance(telegram, str):
             total_penalty += self.penalty_invalid_telegram_type
             logger.debug(f"Social Score Penalty: +{self.penalty_invalid_telegram_type} (Invalid Telegram type: {type(telegram)})")
        elif not is_valid_telegram(telegram):
            total_penalty += self.penalty_invalid_telegram_url
            logger.debug(f"Social Score Penalty: +{self.penalty_invalid_telegram_url} (Invalid Telegram URL: {telegram})")

        # --- Twitter Check ---
        twitter = social_data.get("twitter") or social_data.get("x") # Common keys
        if not twitter:
            total_penalty += self.penalty_no_twitter
            logger.debug(f"Social Score Penalty: +{self.penalty_no_twitter} (No Twitter/X)")
        elif not isinstance(twitter, str):
             total_penalty += self.penalty_invalid_twitter_type
             logger.debug(f"Social Score Penalty: +{self.penalty_invalid_twitter_type} (Invalid Twitter type: {type(twitter)})")
        elif not is_valid_twitter(twitter):
            total_penalty += self.penalty_invalid_twitter_url
            logger.debug(f"Social Score Penalty: +{self.penalty_invalid_twitter_url} (Invalid Twitter URL: {twitter})")

        # --- Duplicate Link Check ---
        valid_links = [link for link in [website, telegram, twitter] if link] # Get non-null links
        if len(valid_links) > len(set(valid_links)): # Check if number of links > number of unique links
            total_penalty += self.penalty_duplicate_links
            logger.debug(f"Social Score Penalty: +{self.penalty_duplicate_links} (Duplicate URLs found for different social types)")

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
                await self._update_token_socials(mint, None, None, None, self.score_failed_metadata)
                return

            # 3. Extract social links (handle different possible keys)
            website_url = metadata.get("website") or metadata.get("homepage") or metadata.get("url") or metadata.get("external_url")
            telegram_url = metadata.get("telegram") or metadata.get("tg")
            twitter_url = metadata.get("twitter") or metadata.get("x")

            # Basic type validation
            if website_url is not None and not isinstance(website_url, str):
                logger.warning(f"Invalid type for website link in metadata for {mint}: {type(website_url)}. Treating as null.")
                website_url = None
            if telegram_url is not None and not isinstance(telegram_url, str):
                logger.warning(f"Invalid type for telegram link in metadata for {mint}: {type(telegram_url)}. Treating as null.")
                telegram_url = None
            if twitter_url is not None and not isinstance(twitter_url, str):
                logger.warning(f"Invalid type for twitter link in metadata for {mint}: {type(twitter_url)}. Treating as null.")
                twitter_url = None

            social_links_for_scoring = {
                "website": website_url,
                "telegram": telegram_url,
                "twitter": twitter_url
            }
            # 4. Check if website is disallowed and Verify Details (if applicable)
            verification_results = None
            is_disallowed_website = False
            parsed_domain = None # Define parsed_domain here for broader scope

            if website_url:
                # Parse domain and check if disallowed FIRST
                try: # Inner try for parsing
                    parsed_domain = urlparse(website_url).netloc.lower().replace('www.', '')
                    if parsed_domain: # Ensure domain was parsed
                        is_disallowed_website = any(parsed_domain == disallowed or parsed_domain.endswith('.' + disallowed) for disallowed in self.disallowed_domains)
                        if is_disallowed_website:
                             logger.debug(f"Website domain '{parsed_domain}' is disallowed for {mint}. Skipping verification.")
                    else:
                        logger.warning(f"Could not parse domain from website URL for {mint}: {website_url}")
                except Exception as e: # Inner except for parsing
                    logger.warning(f"Error parsing website URL '{website_url}' for disallowed check for {mint}: {e}")

                # Log the decision logic
                #logger.debug(f"Disallowed check for {mint}: URL='{website_url}', Parsed Domain='{parsed_domain}', Is Disallowed={is_disallowed_website}")

                # Only verify if the website exists AND it's NOT disallowed
                if not is_disallowed_website:
                    logger.debug(f"Executing website verification for {mint} (URL: {website_url})")
                    # Correctly indented under the outer `if website_url:`
                    verification_results = await self._verify_website_details(website_url, token_info['name'], token_info['symbol'])
                else:
                     logger.debug(f"Skipping website verification for {mint} as domain '{parsed_domain}' is disallowed.")

            # 5. Calculate score (passing verification results)
            # Correctly indented under the main `try:`
            social_score = self._calculate_social_score(
                social_links_for_scoring,
                token_info['name'],
                token_info['symbol'],
                verification_results # Pass verification results
            )

            # 6. Update DB
            # Correctly indented under the main `try:`
            await self._update_token_socials(
                mint,
                website_url, # Use validated/extracted URLs
                telegram_url,
                twitter_url,
                social_score
            )
        # Correctly aligned with the main `try:` at line 338
        except Exception as e:
            # Correctly indented under the `except:`
            logger.error(f"💥 Unexpected error processing socials for {mint}: {e}", exc_info=True)