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
from decimal import Decimal

from database_handler import DatabaseClient
from logger import logger
from state_manager import GlobalState
# Assuming these validation functions exist in utils.py
from utils import is_valid_website, is_valid_telegram, is_valid_twitter

# --- Configuration for Retries ---
MAX_FETCH_ATTEMPTS = 4 # Allow 2 attempts (initial + 1 retry)
DEPRIORITIZED_PRIORITY = float('inf') # Very low priority for requeueing after max attempts

class SocialsProcessor:
    def __init__(self, state: GlobalState, db_client: DatabaseClient, config_dict: dict):
        self.state = state
        self.db_client = db_client
        self.config = config_dict # Store config
        self.queue = self.state.get_socialscheck_queue()
        self.fetch_attempts = {}

        # Load scoring values from config
        self.penalty_no_website = self.config['SOCIALS_PENALTY_NO_WEBSITE']
        self.penalty_invalid_website_type = self.config['SOCIALS_PENALTY_INVALID_WEBSITE_TYPE']
        self.penalty_website_verify_skipped = self.config['SOCIALS_PENALTY_WEBSITE_VERIFY_SKIPPED']
        self.penalty_website_invalid_url = self.config['SOCIALS_PENALTY_WEBSITE_INVALID_URL']
        self.penalty_website_timeout = self.config['SOCIALS_PENALTY_WEBSITE_TIMEOUT']
        self.penalty_website_http_error = self.config['SOCIALS_PENALTY_WEBSITE_HTTP_ERROR']
        self.penalty_website_other_error = self.config['SOCIALS_PENALTY_WEBSITE_OTHER_ERROR']
        self.penalty_no_https = self.config['SOCIALS_PENALTY_NO_HTTPS']
        self.penalty_website_no_mention = self.config['SOCIALS_PENALTY_WEBSITE_NO_MENTION']
        self.penalty_common_platform_website = self.config['SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE']
        self.penalty_no_telegram = self.config['SOCIALS_PENALTY_NO_TELEGRAM']
        self.penalty_invalid_telegram_type = self.config['SOCIALS_PENALTY_INVALID_TELEGRAM_TYPE']
        self.penalty_invalid_telegram_url = self.config['SOCIALS_PENALTY_INVALID_TELEGRAM_URL']
        self.penalty_no_twitter = self.config['SOCIALS_PENALTY_NO_TWITTER']
        self.penalty_invalid_twitter_type = self.config['SOCIALS_PENALTY_INVALID_TWITTER_TYPE']
        self.penalty_invalid_twitter_url = self.config['SOCIALS_PENALTY_INVALID_TWITTER_URL']
        self.penalty_action_trigger_url = self.config['SOCIALS_PENALTY_ACTION_TRIGGER_URL'] # New penalty
        self.penalty_duplicate_links = self.config['SOCIALS_PENALTY_DUPLICATE_LINKS']

        self.bonus_domain_match = self.config['SOCIALS_BONUS_DOMAIN_MATCH']
        # self.bonus_news_gov_website = self.config['SOCIALS_BONUS_NEWS_GOV_WEBSITE'] # Currently 0 in config

        self.score_failed_metadata = self.config['SOCIALS_SCORE_FAILED_METADATA']

        # Load domain sets from config
        self.disallowed_domains = self.config['SOCIALS_DISALLOWED_WEBSITE_DOMAINS']
        self.allowed_news_domains = self.config['SOCIALS_ALLOWED_NEWS_DOMAINS']

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
                         return "Error :" + response.text[:200]

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"HTTP error fetching social metadata from {uri}: {status_code} {e.response.reason_phrase}")
            if 400 <= status_code < 500:
                return f"Error {status_code}" # Client-side error (e.g., 404)
            elif 500 <= status_code < 600:
                return f"Error {status_code}" # Server-side error
            else:
                return f"Error {status_code}" # Other HTTP error
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching social metadata from {uri}")
            return "Error Timeout"
        except httpx.RequestError as e:
            # Includes connection errors, DNS errors, etc.
            logger.warning(f"Request error fetching social metadata from {uri}: {e}")
            return "Error Request"
        except json.JSONDecodeError as e:
            # Use response variable safely, might not be defined if request failed earlier
            response_text = getattr(e, 'response', None) and getattr(e.response, 'text', '')
            logger.error(f"Failed to decode JSON from {uri}: {e}. Response text: {response_text[:200]}...")
            return "Error Decode"
        except Exception as e:
            logger.error(f"Unexpected error fetching social metadata from {uri}: {e}", exc_info=True)
            return "Error Unknown"
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

        log_str = "Social Score Calculation: \n"
        log_str += f" Website: {social_data.get('website')}\n Telegram: {social_data.get('telegram')}\n Twitter: {social_data.get('twitter')}\n"

        # --- Website Check ---
        website = social_data.get("website") or social_data.get("homepage") or social_data.get("url") or social_data.get("external_url") # Consolidate check
        is_disallowed_website = False
        parsed_domain = None

        if not website:
            total_penalty += self.penalty_no_website
            # logger.debug(f"Social Score Penalty: +{self.penalty_no_website} (No Website URL provided)")
            log_str += f"\tPenalty: +{self.penalty_no_website} (No Website URL provided)\n"
        elif not isinstance(website, str):
            total_penalty += self.penalty_invalid_website_type
            # logger.debug(f"Social Score Penalty: +{self.penalty_invalid_website_type} (Invalid Website type: {type(website)})")
            log_str += f"\tPenalty: +{self.penalty_invalid_website_type} (Invalid Website type: {type(website)})\n"
        else:
            # 1. Parse domain and check if disallowed FIRST
            try:
                parsed_domain = urlparse(website).netloc.lower().replace('www.', '')
                if parsed_domain: # Ensure domain was parsed
                    is_disallowed_website = any(parsed_domain == disallowed or parsed_domain.endswith('.' + disallowed) for disallowed in self.disallowed_domains)
                    if is_disallowed_website:
                        total_penalty += self.penalty_common_platform_website
                        # logger.debug(f"Social Score Penalty: +{self.penalty_common_platform_website} (Website URL domain '{parsed_domain}' is disallowed, skipping further checks)")
                        log_str += f"\tPenalty: +{self.penalty_common_platform_website} (Website URL domain '{parsed_domain}' is disallowed)\n"
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
                    # logger.warning(f"Social Score Penalty: +{self.penalty_website_verify_skipped} (Website verification skipped for {website})")
                    log_str += f"\tPenalty: +{self.penalty_website_verify_skipped} (Website verification skipped)\n"
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
                    # logger.debug(f"Social Score Penalty: +{total_penalty} (Website verification failed: {verification_results['error']})")
                    log_str += f"\tPenalty: +{total_penalty} (Website verification failed: {verification_results['error']})\n"
                else:
                    # Website is reachable, apply finer penalties/bonuses
                    if not verification_results['uses_https']:
                        total_penalty += self.penalty_no_https
                        # logger.debug(f"Social Score Penalty: +{self.penalty_no_https} (Website does not use HTTPS)")
                        log_str += f"\tPenalty: +{self.penalty_no_https} (Website does not use HTTPS)\n"
                    if not verification_results['mentions_token']:
                        total_penalty += self.penalty_website_no_mention
                        #logger.debug(f"Social Score Penalty: +{self.penalty_website_no_mention} (Website does not mention token name/symbol)")
                        log_str += f"\tPenalty: +{self.penalty_website_no_mention} (Website does not mention token name/symbol)\n"

                    # Bonus for domain matching (only if not disallowed)
                    try:
                        # Domain already parsed as parsed_domain
                        if parsed_domain:
                            if token_name and (parsed_domain.startswith(token_name) or token_name in parsed_domain):
                                total_penalty += self.bonus_domain_match
                                # logger.debug(f"Social Score Bonus: {self.bonus_domain_match} (Website domain '{parsed_domain}' matches name '{token_name}')")
                                log_str += f"\tBonus: +{self.bonus_domain_match} (Website domain '{parsed_domain}' matches name '{token_name}')\n"
                            elif token_symbol and (parsed_domain.startswith(token_symbol) or token_symbol in parsed_domain):
                                total_penalty += self.bonus_domain_match
                                # logger.debug(f"Social Score Bonus: {self.bonus_domain_match} (Website domain '{parsed_domain}' matches symbol '{token_symbol}')")
                                log_str += f"\tBonus: +{self.bonus_domain_match} (Website domain '{parsed_domain}' matches symbol '{token_symbol}')\n"
                    except Exception:
                        pass # Ignore errors during bonus check

            # 3. Check for allowed news/gov domains (runs regardless of disallowed status)
            # if parsed_domain: # Only check if domain was successfully parsed
            #     try:
            #         is_allowed_news_gov = (
            #             any(parsed_domain == allowed or parsed_domain.endswith('.' + allowed) for allowed in self.allowed_news_domains)
            #             or parsed_domain.endswith('.gov')
            #         )
            #         if is_allowed_news_gov:
            #             # total_penalty += self.bonus_news_gov_website # Apply bonus/penalty if configured
            #             # logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is an allowed news/gov domain.")
            #             log_str += f"\tInfo: Website URL domain '{parsed_domain}' is an allowed news/gov domain.\n"
            #         # else: # Optional: Log if domain is NOT allowed news/gov
            #         #    logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is not in allowed news/gov list.")
            #     except Exception:
            #         pass # Ignore parsing errors for this check too

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
                    total_penalty += self.bonus_news_gov_website # Apply bonus/penalty if configured
                    # logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is an allowed news/gov domain.")
                    log_str += f"\tBonus: +{self.bonus_news_gov_website} (Website URL domain '{parsed_domain}' is an allowed news/gov domain)\n"
                # else: # Optional: Log if domain is NOT allowed news/gov
                #    logger.debug(f"Social Score Info: Website URL domain '{parsed_domain}' is not in allowed news/gov list.")
            except Exception:
                pass # Ignore parsing errors for this check too

        # --- Telegram Check ---
        telegram = social_data.get("telegram") or social_data.get("tg") # Common keys
        if not telegram:
            total_penalty += self.penalty_no_telegram
            # logger.debug(f"Social Score Penalty: +{self.penalty_no_telegram} (No Telegram)")
            log_str += f"\tPenalty: +{self.penalty_no_telegram} (No Telegram)\n"
        elif not isinstance(telegram, str):
            total_penalty += self.penalty_invalid_telegram_type
            # logger.debug(f"Social Score Penalty: +{self.penalty_invalid_telegram_type} (Invalid Telegram type: {type(telegram)})")
            log_str += f"\tPenalty: +{self.penalty_invalid_telegram_type} (Invalid Telegram type: {type(telegram)})\n"
        elif not is_valid_telegram(telegram):
            total_penalty += self.penalty_invalid_telegram_url
            # logger.debug(f"Social Score Penalty: +{self.penalty_invalid_telegram_url} (Invalid Telegram URL: {telegram})")
            log_str += f"\tPenalty: +{self.penalty_invalid_telegram_url} (Invalid Telegram URL: {telegram})\n"

        # --- Twitter Check ---
        twitter = social_data.get("twitter") or social_data.get("x") # Common keys
        if not twitter:
            total_penalty += self.penalty_no_twitter
            #logger.debug(f"Social Score Penalty: +{self.penalty_no_twitter} (No Twitter/X)")
            log_str += f"\tPenalty: +{self.penalty_no_twitter} (No Twitter/X)\n"
        elif not isinstance(twitter, str):
            total_penalty += self.penalty_invalid_twitter_type
            # logger.debug(f"Social Score Penalty: +{self.penalty_invalid_twitter_type} (Invalid Twitter type: {type(twitter)})")
            log_str += f"\tPenalty: +{self.penalty_invalid_twitter_type} (Invalid Twitter type: {type(twitter)})\n"
        elif not is_valid_twitter(twitter):
            total_penalty += self.penalty_invalid_twitter_url
            # logger.debug(f"Social Score Penalty: +{self.penalty_invalid_twitter_url} (Invalid Twitter URL: {twitter})")
            log_str += f"\tPenalty: +{self.penalty_invalid_twitter_url} (Invalid Twitter URL: {twitter})\n"

        # --- Action Trigger URL Check ---
        action_trigger_penalty_applied = False # Flag to apply penalty only once even if multiple links trigger it
        for link_type, link_url in [("Website", website), ("Telegram", telegram), ("Twitter", twitter)]:
            if link_url and isinstance(link_url, str):
                try:
                    parsed = urlparse(link_url)
                    # Check for mailto links
                    if parsed.scheme == 'mailto':
                        if not action_trigger_penalty_applied:
                            total_penalty += self.penalty_action_trigger_url
                            log_str += f"\tPenalty: +{self.penalty_action_trigger_url} ({link_type} URL is a mailto link: {link_url})\n"
                            action_trigger_penalty_applied = True
                        continue # No need for further checks on this link

                    # Check for tel: links
                    if parsed.scheme == 'tel':
                        if not action_trigger_penalty_applied:
                            total_penalty += self.penalty_action_trigger_url
                            log_str += f"\tPenalty: +{self.penalty_action_trigger_url} ({link_type} URL is a tel link: {link_url})\n"
                            action_trigger_penalty_applied = True
                        continue

                    # Check for sms: links
                    if parsed.scheme == 'sms':
                        if not action_trigger_penalty_applied:
                            total_penalty += self.penalty_action_trigger_url
                            log_str += f"\tPenalty: +{self.penalty_action_trigger_url} ({link_type} URL is an sms link: {link_url})\n"
                            action_trigger_penalty_applied = True
                        continue

                    # Check for Twitter/X intent links
                    if parsed.netloc in ('twitter.com', 'x.com') and parsed.path.startswith('/intent/'):
                         if not action_trigger_penalty_applied:
                            total_penalty += self.penalty_action_trigger_url
                            log_str += f"\tPenalty: +{self.penalty_action_trigger_url} ({link_type} URL is a Twitter/X intent link: {link_url})\n"
                            action_trigger_penalty_applied = True
                        # continue # Might add other checks later

                except Exception as e:
                    logger.warning(f"Could not parse URL for action trigger check ({link_type}: {link_url}): {e}")

        # --- Duplicate Link Check ---
        valid_links = [link for link in [website, telegram, twitter] if link] # Get non-null links
        if len(valid_links) > len(set(valid_links)): # Check if number of links > number of unique links
            total_penalty += self.penalty_duplicate_links
            #logger.debug(f"Social Score Penalty: +{self.penalty_duplicate_links} (Duplicate URLs found for different social types)")
            log_str += f"\tPenalty: +{self.penalty_duplicate_links} (Duplicate URLs found for different social types)\n"

        # Ensure score is within 0-100 range
        final_score = min(max(total_penalty, 0), 100)
        #logger.debug(f"Calculated Social Score (Penalty): {final_score}")
        log_str += f"\tFinal Score: {final_score}\n"
        logger.debug(log_str)
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
            logger.debug(f"💾 Updated socials for {mint}. Score: {score} (Website: {'Y' if website else 'N'}, TG: {'Y' if telegram else 'N'}, TW: {'Y' if twitter else 'N'})")
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
                return "NOT_FOUND"
            
            if not token_info['uri']:
                logger.debug(f"Token {mint} has no metadata URI. Skipping social processing.")
                # Optionally update DB to mark as checked with no URI?
                # await self._update_token_socials(mint, None, None, None, 100) # Max penalty if no URI? Or specific score?
                return "NO_URI"

            # 2. Fetch metadata from URI
            metadata = await self._fetch_metadata(token_info['uri'])
            # Check if metadata fetch failed (returned None or an error string)
            if metadata is None or (isinstance(metadata, str) and metadata.startswith("Error")):
                error_reason = metadata if metadata else "Unknown fetch failure" # Use specific error or default
                logger.warning(f"Metadata fetch failed for {mint} from {token_info['uri']}: {error_reason}. Cannot process socials.")
                # Update DB to mark as checked but failed, using high penalty score
                await self._update_token_socials(mint, None, None, None, self.score_failed_metadata)
                # Return the specific error reason for retry logic
                return error_reason if isinstance(metadata, str) else "FAILED_METADATA_UNKNOWN" # Propagate specific error

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

            return True # Indicate success
        # Correctly aligned with the main `try:` at line 338
        except Exception as e:
            # Correctly indented under the `except:`
            logger.error(f"💥 Unexpected error processing socials for {mint}: {e}", exc_info=True)

    async def _refresh_queue(self):
        """Refreshes the Socials Check priority queue based on token volume."""
        try:
            sol_price = await self.state.get_sol_price()
            if sol_price is None:
                logger.warning("⚠ SOL_PRICE not updated yet; skipping RSocials check queue refresh.")
                return False # Indicate refresh skipped

            # Clear the current queue before repopulating
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.error(f"Error clearing socials heck queue item: {e}")


            async with self.db_client.pool.acquire() as conn:
                # Fetch tokens that are active but don't have Socials Check data yet, ordered by volume
                # Note: Volatility isn't directly calculated here, using volume as proxy per original code.
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour' -- Consider recent volume
                    WHERE t.is_active = TRUE AND (t.socials_score IS NULL OR t.socials_last_checked < NOW() - ($1 || ' minutes')::interval) -- Select tokens not checked recently
                    GROUP BY t.mint
                    ORDER BY volume DESC
                """, str(self.config['SOCIALS_CHECK_REFRESH_INTERVAL'])) # Use refresh interval from config

                logger.debug(f"🔍 Found {len(rows)} active tokens missing Socials Check data for refresh.")

                if rows:
                    tokens_added = 0 # Initialize counter
                    for row in rows:
                        mint = row["mint"]
                        volume = row["volume"] or Decimal(0)
                        priority = -float(volume)
                        current_attempts = self.fetch_attempts.get(mint, 0)

                        # Only add if not already deprioritized (reached max attempts)
                        if current_attempts < MAX_FETCH_ATTEMPTS:
                             await self.queue.put((priority, mint))
                             tokens_added += 1
                        # else:
                        #      logger.debug(f"Token {mint} previously reached max fetch attempts ({current_attempts}), not adding during refresh.")

                    logger.debug(f"🔄 Refreshed Socials Check queue. Added {tokens_added} tokens (current size: {self.queue.qsize()}).")
                #else:
                    # logger.debug("✅ No active tokens found needing Socials Check data during refresh.")
            return True # Indicate refresh completed

        except Exception as e:
            logger.error(f"❌ Critical error in _refresh_queue: {e}", exc_info=True)
            return False # Indicate refresh failed
        
    async def _worker(self):
        """Worker task that processes tokens from the Socials Check queue with rate limiting."""
        logger.info("🚀 Socials worker started.")
        last_refresh_time = 0
        refresh_interval = 30 # Refresh queue every 30 seconds

        while not self.state.shutdown_event.is_set():
            try:
                # --- Refresh Queue Periodically ---
                current_time = asyncio.get_event_loop().time()
                if self.queue.empty() or (current_time - last_refresh_time > refresh_interval):
                    logger.debug("🔄 Triggering Socials Check queue refresh...")
                    refreshed = await self._refresh_queue()
                    if refreshed:
                        last_refresh_time = current_time
                    else:
                        # Avoid busy-looping if refresh fails repeatedly
                        await self.state.wait_or_interrupt(timeout=5)
                        continue # Skip to next iteration if refresh failed

                # --- Get Token from Queue ---
                if self.queue.empty():
                    # logger.debug("Socials Check queue is empty, waiting...")
                    await self.state.wait_or_interrupt(timeout=5) # Wait if queue is empty
                    continue

                try:
                    # Get highest priority item (lowest negative volume)
                    priority, mint = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    # logger.debug(f"Processing {mint} from Socials Check queue (Priority: {priority})")
                except asyncio.TimeoutError:
                    # logger.debug("Socials Check queue.get() timed out, queue might be empty or contested.")
                    continue # Try again next loop
                except Exception as q_err:
                     logger.error(f"Error getting item from socials check queue: {q_err}")
                     continue
                
                # --- Process Token ---
                task_completed = False # Flag to ensure task_done is called correctly
                try:
                    # Check if token still exists and is active before fetching
                    async with self.db_client.pool.acquire() as conn:
                        is_active = await conn.fetchval("SELECT is_active FROM tokens WHERE mint = $1", mint)

                    if is_active is None:
                        logger.debug(f"Token {mint} no longer exists. Skipping Socials Check.")
                        self.queue.task_done()
                        task_completed = True
                        self.fetch_attempts.pop(mint, None) # Clear attempts
                        continue
                    if not is_active:
                            logger.debug(f"Token {mint} is no longer active. Skipping Socials Check.")
                            self.queue.task_done()
                            task_completed = True
                            self.fetch_attempts.pop(mint, None) # Clear attempts
                            continue

                    # Fetch, store, check score, etc.
                    process_status = await self.process_token(mint)

                    # --- Handle Retry/Deprioritize Logic ---
                    # process_status can now be True, False, "NO_URI", "NOT_FOUND", or specific error strings like "Error 404", "Error Timeout", etc.
                    if process_status is True: # Success
                        logger.debug(f"✅ Successfully processed Socials Check for {mint}.")
                        async with self.db_client.pool.acquire() as conn:
                            try:
                                await conn.execute('''
                                    UPDATE tokens SET socials_last_checked = NOW() WHERE mint = $1
                                ''', mint)
                                logger.debug(f"Updated socials_last_checked for {mint} to NOW()")
                            except Exception as e:
                                logger.error(f"Error updating socials_last_checked for {mint}: {e}", exc_info=True)
                        self.fetch_attempts.pop(mint, None) # Clear attempts on success

                    elif process_status in ["NO_URI", "NOT_FOUND"] or (isinstance(process_status, str) and process_status.startswith("Error 4")): # No URI, Token Gone, or Client Error (4xx)
                        status_reason = process_status
                        logger.warning(f"Socials Check for {mint} failed with likely permanent error: {status_reason}. Deprioritizing immediately.")
                        # Deprioritize immediately by setting attempts high and requeueing low
                        self.fetch_attempts[mint] = MAX_FETCH_ATTEMPTS # Mark as max attempts reached
                        await self.queue.put((DEPRIORITIZED_PRIORITY, mint))

                    elif process_status is False or (isinstance(process_status, str) and process_status.startswith("Error")): # General error or Transient Error (Timeout, Request, 5xx, Decode, Unknown)
                        status_reason = process_status if isinstance(process_status, str) else "General processing error"
                        current_attempts = self.fetch_attempts.get(mint, 0) + 1
                        self.fetch_attempts[mint] = current_attempts
                        logger.warning(f"🔄 Socials Check failed for {mint} ({status_reason}). Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")

                        if current_attempts < MAX_FETCH_ATTEMPTS:
                            # Requeue with original priority for retry
                            await self.queue.put((priority, mint))
                            logger.info(f"Retrying Socials Check for {mint} later (attempt {current_attempts}).")
                        else:
                            # Max attempts reached for transient error, deprioritize
                            await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                            logger.warning(f"Max socials check fetch attempts ({MAX_FETCH_ATTEMPTS}) reached for {mint} due to {status_reason}. Deprioritizing.")
                            # Keep attempt count high so refresh doesn't re-add with high priority

                    elif process_status is False:
                        # General processing error (not 404 or timeout)
                        logger.warning(f"📉 Socials Check processing failed for {mint} (not 404/timeout). Requeuing with original priority.")
                        await self.queue.put((priority, mint)) # Requeue
                        self.fetch_attempts.pop(mint, None) # Clear attempts counter

                    # else block removed as logic is now handled within the elif conditions above
                    

                    # Mark task as done regardless of outcome (requeueing handles retries)
                    self.queue.task_done()
                    task_completed = True


                except Exception as proc_err:
                    logger.error(f"❌ Unexpected error processing socials check for token {mint}: {proc_err}", exc_info=True)
                    # Requeue on unexpected errors during processing block
                    await self.queue.put((priority, mint))
                    # Clear fetch attempts counter as it was an unexpected error
                    self.fetch_attempts.pop(mint, None)

                finally:
                    # Ensure task_done is called even if processing fails, unless already called
                    if not task_completed:
                        try:
                            self.queue.task_done()
                        except ValueError:
                            logger.warning(f"Task_done already called for {mint} in finally block?")
                        except Exception as td_err:
                            logger.error(f"Error calling task_done for {mint} in finally block: {td_err}")


            except asyncio.CancelledError:
                logger.info("⏹ Socials Check worker task cancelled.")
                break # Exit loop cleanly on cancellation
            except Exception as e:
                logger.error(f"💥 Unexpected error in Socials Check worker main loop: {e}", exc_info=True)
                # Avoid busy-looping on persistent errors
                await self.state.wait_or_interrupt(timeout=10)

        logger.info("🛑 Socials heck worker shutting down.")

    def start(self) -> asyncio.Task:
        """Creates and returns the asyncio task for the Socials Check worker."""
        logger.info("Creating Socials Check background task...")
        # Ensure worker starts after initial setup (like wallet loading) is done
        return asyncio.create_task(self._worker(), name="socialscheck_worker")