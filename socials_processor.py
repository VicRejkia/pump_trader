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
from datetime import datetime, timezone, timedelta
import asyncpg

from database_handler import DatabaseClient
from bot_logger import logger
from state_manager import GlobalState
from utils import is_valid_website, is_valid_telegram, is_valid_twitter
from connectors.telegram_monitor import check_telegram_channel


# --- Configuration for Retries ---
MAX_FETCH_ATTEMPTS = 3
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
        self.penalty_action_trigger_url = self.config['SOCIALS_PENALTY_ACTION_TRIGGER_URL']
        self.penalty_duplicate_links = self.config['SOCIALS_PENALTY_DUPLICATE_LINKS']
        self.penalty_tg_no_public_preview = self.config.get('SOCIALS_PENALTY_TG_NO_PUBLIC_PREVIEW', 5)
        self.penalty_tg_low_members = self.config.get('SOCIALS_PENALTY_TG_LOW_MEMBERS', 20)
        self.threshold_tg_low_members = self.config.get('SOCIALS_THRESHOLD_TG_LOW_MEMBERS', 100)
        self.penalty_tg_low_online_ratio = self.config.get('SOCIALS_PENALTY_TG_LOW_ONLINE_RATIO', 15)
        self.threshold_tg_low_online_ratio = self.config.get('SOCIALS_THRESHOLD_TG_LOW_ONLINE_RATIO', 0.02)


        self.bonus_domain_match = self.config['SOCIALS_BONUS_DOMAIN_MATCH']
        self.bonus_news_gov_website = self.config.get('SOCIALS_BONUS_NEWS_GOV_WEBSITE', 0)
        self.bonus_tg_high_members = self.config.get('SOCIALS_BONUS_TG_HIGH_MEMBERS', -10)
        self.threshold_tg_high_members = self.config.get('SOCIALS_THRESHOLD_TG_HIGH_MEMBERS', 2000)
        self.bonus_tg_high_online_ratio = self.config.get('SOCIALS_BONUS_TG_HIGH_ONLINE_RATIO', -5)
        self.threshold_tg_high_online_ratio = self.config.get('SOCIALS_THRESHOLD_TG_HIGH_ONLINE_RATIO', 0.10)


        self.score_failed_metadata = self.config['SOCIALS_SCORE_FAILED_METADATA']

        # Load domain sets from config
        self.disallowed_domains = self.config['SOCIALS_DISALLOWED_WEBSITE_DOMAINS']
        self.allowed_news_domains = self.config['SOCIALS_ALLOWED_NEWS_DOMAINS']

        # Shared HTTP client for website verification
        self._verify_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, limits=httpx.Limits(max_connections=5))

    async def _fetch_metadata(self, uri: str) -> dict | str | None:
        if not uri or not uri.startswith('http'):
            logger.debug(f"Invalid or missing URI for social metadata: {uri}")
            return "Error InvalidURI"

        response_obj_for_logging = None
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(uri)
                response_obj_for_logging = response

                content_type = response.headers.get('content-type', '').lower()
                # Check for non-JSON content types before attempting to parse
                if not ('application/json' in content_type or 'text/json' in content_type or not content_type): # Allow empty content type for some misconfigured servers
                    if content_type.startswith('image/') or content_type.startswith('application/octet-stream') or content_type.startswith('text/html'): # More specific checks
                        logger.warning(f"Metadata fetch for {uri} returned non-JSON content-type: {content_type}. Response text: {response.text[:200]}...")
                        return f"Error NotJSONContentType: {content_type}"

                response.raise_for_status() # Raise HTTPStatusError for bad responses (4xx or 5xx)

                try:
                    metadata = response.json()
                    logger.debug(f"Successfully fetched and parsed JSON metadata from {uri} (Content-Type: {content_type})")
                    return metadata
                except json.JSONDecodeError as e_initial:
                    if "Invalid control character" in str(e_initial):
                        logger.warning(f"Initial JSON parsing for {uri} failed due to control characters: {e_initial}. Attempting with strict=False.")
                        try:
                            metadata_strict_false = json.loads(response.text, strict=False)
                            logger.debug(f"Successfully parsed JSON from {uri} with strict=False.")
                            return metadata_strict_false
                        except json.JSONDecodeError as e_strict:
                            logger.error(f"Failed to decode JSON from {uri} even with strict=False. Error: {e_strict}. Response text: {response.text[:200]}...")
                            return "Error DecodeFailedStrict"
                    else:
                        logger.error(f"Failed to decode JSON from {uri} (Content-Type: {content_type}). Error: {e_initial}. Response text: {response.text[:200]}...")
                        return "Error DecodeGeneral"

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"HTTP error fetching social metadata from {uri}: {status_code} {e.response.reason_phrase}")
            return f"Error HTTP {status_code}"
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching social metadata from {uri}")
            return "Error Timeout"
        except httpx.RequestError as e:
            logger.warning(f"Request error fetching social metadata from {uri}: {e}")
            return "Error Request"
        except Exception as e:
            try:
                response_text_snippet = response_obj_for_logging.text[:200] if response_obj_for_logging and hasattr(response_obj_for_logging, 'text') else 'Response text not available'
                logger.error(f"Unexpected error processing social metadata from {uri}: {e}. Response text: {response_text_snippet}...", exc_info=True)
            except:
                logger.error(f"Unexpected error processing social metadata from {uri}: {e}. Response text could not be retrieved.", exc_info=True)
            return "Error UnknownFetch"

        logger.error(f"Reached unexpected end of _fetch_metadata for {uri}. This indicates a logic error.")
        return "Error FallbackFetch"

    async def _verify_website_details(self, url: str, token_name: str, token_symbol: str) -> dict:
        """Attempts to verify website reachability, security, and relevance."""
        results = {'uses_https': False, 'is_reachable': False, 'mentions_token': False, 'error': None}
        token_name_lower = (token_name or "").lower()
        token_symbol_lower = (token_symbol or "").lower()

        try:
            parsed_url = urlsplit(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                 results['error'] = "Invalid URL format"
                 logger.debug(f"Website Verify Fail ({url}): Invalid URL format")
                 return results

            results['uses_https'] = parsed_url.scheme == 'https'
            logger.debug(f"Attempting to verify website: {url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await self._verify_client.get(url, headers=headers)
            response.raise_for_status()

            results['is_reachable'] = True
            logger.debug(f"Website Verify Success ({url}): Reachable (Status: {response.status_code})")

            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                page_content = ""
                if soup.title and soup.title.string:
                    page_content += soup.title.string.lower() + " "
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    page_content += meta_desc['content'].lower()

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
            logger.debug(f"Website Verify Fail ({url}): HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            results['error'] = "Timeout"
            logger.debug(f"Website Verify Fail ({url}): Timeout")
        except httpx.RequestError as e:
            results['error'] = f"Request Error: {type(e).__name__}"
            logger.debug(f"Website Verify Fail ({url}): Request Error ({type(e).__name__})")
        except ImportError:
             results['error'] = "Missing 'beautifulsoup4' library"
             logger.error("Dependency missing: Please install 'beautifulsoup4' (`pip install beautifulsoup4`) for website content checking.")
        except Exception as e:
            results['error'] = f"Unexpected Error: {type(e).__name__}"
            logger.error(f"Website Verify Fail ({url}): Unexpected error: {e}", exc_info=True)
        return results

    def _calculate_social_score(self, social_data: dict, token_name: str | None, token_symbol: str | None, verification_results: dict | None, telegram_results: dict | None) -> int:
        """
        Computes a social risk score based on social data, website verification, and telegram stats.
        Lower score is better.
        """
        total_penalty = 0
        token_name = (token_name or "").lower()
        token_symbol = (token_symbol or "").lower()

        log_str = f"Social Score Calculation for token '{token_name if token_name else token_symbol}': \n"
        log_str += f" Website: {social_data.get('website')}\n Telegram: {social_data.get('telegram')}\n Twitter: {social_data.get('twitter')}\n"

        # --- Website Scoring ---
        website = social_data.get("website")
        if not website:
            total_penalty += self.penalty_no_website
            log_str += f"\tPenalty: +{self.penalty_no_website} (No Website URL provided)\n"
        elif not isinstance(website, str):
            total_penalty += self.penalty_invalid_website_type
            log_str += f"\tPenalty: +{self.penalty_invalid_website_type} (Invalid Website type: {type(website)})\n"
        else:
            try:
                parsed_domain_obj = urlparse(website)
                parsed_domain = parsed_domain_obj.netloc.lower().replace('www.', '')
                if parsed_domain: 
                    is_disallowed_website = any(parsed_domain == disallowed or parsed_domain.endswith('.' + disallowed) for disallowed in self.disallowed_domains)
                    if is_disallowed_website:
                        total_penalty += self.penalty_common_platform_website
                        log_str += f"\tPenalty: +{self.penalty_common_platform_website} (Website URL domain '{parsed_domain}' is disallowed)\n"
                else: # Invalid URL structure if no netloc
                    logger.warning(f"Could not parse domain from website URL: {website} (likely invalid structure)")
                    total_penalty += self.penalty_website_invalid_url 
                    log_str += f"\tPenalty: +{self.penalty_website_invalid_url} (Website URL '{website}' could not be parsed for domain)\n"
                    is_disallowed_website = True # Treat as disallowed if unparsable to prevent further checks

            except Exception as e:
                 logger.warning(f"Error parsing website URL '{website}' for disallowed check: {e}")
                 total_penalty += self.penalty_website_invalid_url # Penalize if parsing fails
                 log_str += f"\tPenalty: +{self.penalty_website_invalid_url} (Error parsing website URL '{website}')\n"
                 is_disallowed_website = True # Treat as disallowed to prevent further checks


            if not is_disallowed_website: # Only proceed if website is structurally valid and not disallowed
                if verification_results is None:
                    total_penalty += self.penalty_website_verify_skipped
                    log_str += f"\tPenalty: +{self.penalty_website_verify_skipped} (Website verification skipped)\n"
                elif verification_results['error']:
                    error_penalty_map = {
                        "Invalid URL format": self.penalty_website_invalid_url,
                        "Timeout": self.penalty_website_timeout,
                        # Add more specific HTTP error messages if needed, or handle generally
                        "HTTP Error 404": self.penalty_website_http_error, # Example specific
                        "HTTP Error 403": self.penalty_website_http_error, # Example specific
                        "HTTP Error": self.penalty_website_http_error # General HTTP error
                        # Add other specific error strings from _verify_website_details if needed
                    }
                    penalty_to_add = self.penalty_website_other_error # Default penalty

                    # Iterate to find the most specific match for the error string
                    for error_key_fragment, specific_penalty_value in error_penalty_map.items():
                        if error_key_fragment in verification_results['error']:
                            penalty_to_add = specific_penalty_value
                            break # Found a specific penalty, use it
                    
                    total_penalty += penalty_to_add
                    log_str += f"\tPenalty: +{penalty_to_add} (Website verification failed: {verification_results['error']})\n"
                else: # Website is reachable
                    if not verification_results['uses_https']:
                        total_penalty += self.penalty_no_https
                        log_str += f"\tPenalty: +{self.penalty_no_https} (Website does not use HTTPS)\n"
                    if not verification_results['mentions_token']:
                        total_penalty += self.penalty_website_no_mention
                        log_str += f"\tPenalty: +{self.penalty_website_no_mention} (Website does not mention token name/symbol)\n"

                    if parsed_domain: # Bonus only if domain was parsed and website is not disallowed
                        if token_name and (parsed_domain.startswith(token_name) or token_name in parsed_domain):
                            total_penalty += self.bonus_domain_match
                            log_str += f"\tBonus: {self.bonus_domain_match} (Website domain '{parsed_domain}' matches name '{token_name}')\n"
                        elif token_symbol and (parsed_domain.startswith(token_symbol) or token_symbol in parsed_domain):
                            total_penalty += self.bonus_domain_match
                            log_str += f"\tBonus: {self.bonus_domain_match} (Website domain '{parsed_domain}' matches symbol '{token_symbol}')\n"
            
            # Allowed News/Gov Domains (runs if website URL was valid enough to parse domain)
            if parsed_domain:
                is_allowed_news_gov = (
                    any(parsed_domain == allowed or parsed_domain.endswith('.' + allowed) for allowed in self.allowed_news_domains)
                    or parsed_domain.endswith('.gov')
                )
                if is_allowed_news_gov:
                    total_penalty += self.bonus_news_gov_website 
                    log_str += f"\tBonus: {self.bonus_news_gov_website} (Website URL domain '{parsed_domain}' is an allowed news/gov domain)\n"

        # --- Telegram Check ---
        telegram = social_data.get("telegram") or social_data.get("tg")
        if not telegram:
            total_penalty += self.penalty_no_telegram
            log_str += f"\tPenalty: +{self.penalty_no_telegram} (No Telegram)\n"
        elif not isinstance(telegram, str):
            total_penalty += self.penalty_invalid_telegram_type
            log_str += f"\tPenalty: +{self.penalty_invalid_telegram_type} (Invalid Telegram type: {type(telegram)})\n"
        elif not is_valid_telegram(telegram):
            total_penalty += self.penalty_invalid_telegram_url
            log_str += f"\tPenalty: +{self.penalty_invalid_telegram_url} (Invalid Telegram URL: {telegram})\n"
        elif telegram_results:
            if telegram_results.get('valid'):
                # FIX: Coalesce None to 0 to prevent TypeError.
                members = telegram_results.get('members') or 0
                online = telegram_results.get('online') or 0

                if not telegram_results.get('public_preview'):
                    total_penalty += self.penalty_tg_no_public_preview

                if members < self.threshold_tg_low_members:
                    total_penalty += self.penalty_tg_low_members
                elif members > self.threshold_tg_high_members:
                    total_penalty += self.bonus_tg_high_members

                if members > 0:
                    # This calculation is now safe because 'online' is guaranteed to be an integer.
                    online_ratio = online / members
                    if online_ratio < self.threshold_tg_low_online_ratio:
                        total_penalty += self.penalty_tg_low_online_ratio
                    elif online_ratio > self.threshold_tg_high_online_ratio:
                        total_penalty += self.bonus_tg_high_online_ratio
            else:
                # Still penalize if the valid link from metadata leads to an invalid channel
                total_penalty += self.penalty_invalid_telegram_url


        # --- Twitter Scoring ---
        twitter = social_data.get("twitter") or social_data.get("x")
        if not twitter:
            total_penalty += self.penalty_no_twitter
            log_str += f"\tPenalty: +{self.penalty_no_twitter} (No Twitter/X)\n"
        elif not isinstance(twitter, str):
            total_penalty += self.penalty_invalid_twitter_type
            log_str += f"\tPenalty: +{self.penalty_invalid_twitter_type} (Invalid Twitter type: {type(twitter)})\n"
        elif not is_valid_twitter(twitter):
            total_penalty += self.penalty_invalid_twitter_url
            log_str += f"\tPenalty: +{self.penalty_invalid_twitter_url} (Invalid Twitter URL: {twitter})\n"

        # --- Action Trigger URL Check ---
        action_trigger_penalty_applied = False
        for link_type, link_url_val in [("Website", website), ("Telegram", telegram), ("Twitter", twitter)]:
            if link_url_val and isinstance(link_url_val, str):
                try:
                    parsed = urlparse(link_url_val)
                    is_action_link = parsed.scheme in ['mailto', 'tel', 'sms'] or \
                                     (parsed.netloc in ('twitter.com', 'x.com') and parsed.path.startswith('/intent/'))
                    if is_action_link and not action_trigger_penalty_applied:
                        total_penalty += self.penalty_action_trigger_url
                        log_str += f"\tPenalty: +{self.penalty_action_trigger_url} ({link_type} URL is an action trigger: {link_url_val})\n"
                        action_trigger_penalty_applied = True
                except Exception as e:
                    logger.warning(f"Could not parse URL for action trigger check ({link_type}: {link_url_val}): {e}")

        # --- Duplicate Link Check ---
        valid_links = [link for link in [website, telegram, twitter] if isinstance(link, str) and link]
        if len(valid_links) > len(set(valid_links)):
            total_penalty += self.penalty_duplicate_links
            log_str += f"\tPenalty: +{self.penalty_duplicate_links} (Duplicate URLs found for different social types)\n"

        final_score = min(max(total_penalty, 0), 100)
        log_str += f"\tFinal Score: {final_score}\n"
        logger.debug(log_str)
        return final_score


    async def _update_token_socials(self, mint: str, website: str | None, telegram: str | None, twitter: str | None, score: int, score_type: str, details: dict | None):
        """
        Updates the main socials_score in the tokens table and logs a detailed entry in the social_scores table.
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                async with conn.transaction():
                    # --- FIX: Add check for token existence inside the transaction ---
                    # This prevents a race condition where a token is deleted after being
                    # pulled from the queue but before this database transaction begins.
                    token_exists = await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint)
                    if not token_exists:
                        logger.warning(f"Token {mint} was deleted from DB before socials could be updated. Aborting storage.")
                        # Return True to signify that this 'task' is complete and should not be retried.
                        return True
                    # --- END OF FIX ---

                    # 1. Update the primary tokens table with the latest overall score
                    await conn.execute("""
                        UPDATE tokens
                        SET website = COALESCE($2, website),
                            telegram = COALESCE($3, telegram),
                            twitter = COALESCE($4, twitter),
                            socials_score = $5,
                            socials_last_checked = NOW()
                        WHERE mint = $1
                    """, mint, website, telegram, twitter, score)

                    # 2. Insert a detailed record into the new social_scores table
                    await conn.execute("""
                        INSERT INTO social_scores (mint, score_type, score_value, details)
                        VALUES ($1, $2, $3, $4)
                    """, mint, score_type, score, json.dumps(details) if details else None)

            logger.debug(f"💾 Updated socials for {mint}. Score: {score}, Type: {score_type}. Logged detailed entry.")
            return True
        except asyncpg.exceptions.ForeignKeyViolationError as fk_error:
            # This is now a fallback, but good to have. If we get here, it means the token was
            # deleted in the tiny window between our check and the INSERT/UPDATE.
            logger.warning(f"Caught a Foreign Key violation for {mint} despite the pre-check, indicating a very close race condition. Aborting storage. Details: {fk_error}")
            # We return True because the token is gone, so there's no point retrying.
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update socials in DB for {mint}: {e}", exc_info=True)
            return False

    async def process_token(self, mint: str) -> str | bool:
        logger.debug(f"Processing socials for token: {mint}")
        token_info = None
        primary_uri = None
        token_name = ''
        token_symbol = ''
        metadata_fetch_error = None

        try:
            async with self.db_client.pool.acquire() as conn:
                token_info_row = await conn.fetchrow("""
                    SELECT uri, COALESCE(name, '') as name, COALESCE(symbol, '') as symbol, telegram
                    FROM tokens WHERE mint = $1
                """, mint)

            if not token_info_row:
                logger.warning(f"Token {mint} not found in DB for social processing.")
                return "NOT_FOUND"

            primary_uri = token_info_row['uri']
            token_name = token_info_row['name']
            token_symbol = token_info_row['symbol']
            existing_telegram_url = token_info_row['telegram']

            # --- Initial URI Check ---
            if not primary_uri or not primary_uri.strip(): # Check for empty or whitespace-only string
                logger.debug(f"Token {mint} has no valid primary metadata URI. Attempting fallback.")
                metadata_fetch_error = "NO_PRIMARY_URI" # Specific status
                metadata = None # No metadata from primary URI
            else:
                metadata = await self._fetch_metadata(primary_uri)

            # --- Fallback to Rugcheck URI if primary failed ---
            if isinstance(metadata, str) or metadata is None: # Primary fetch failed or URI was invalid
                if isinstance(metadata, str): metadata_fetch_error = metadata # Store error from primary attempt
                
                logger.info(f"Primary URI for {mint} failed ({metadata_fetch_error}). Checking rugcheck for tokenMeta_uri.")
                async with self.db_client.pool.acquire() as conn:
                    rugcheck_uri_row = await conn.fetchrow("SELECT tokenMeta_uri FROM rugcheck WHERE mint = $1", mint)
                
                if rugcheck_uri_row and rugcheck_uri_row['tokenmeta_uri'] and rugcheck_uri_row['tokenmeta_uri'].strip() and rugcheck_uri_row['tokenmeta_uri'] != primary_uri:
                    secondary_uri = rugcheck_uri_row['tokenmeta_uri']
                    logger.info(f"Found secondary URI for {mint} from rugcheck: {secondary_uri}. Fetching...")
                    metadata = await self._fetch_metadata(secondary_uri)
                    if isinstance(metadata, str) or metadata is None: # Secondary also failed
                         if isinstance(metadata, str): metadata_fetch_error = metadata # Store error from secondary attempt
                         logger.warning(f"Secondary URI fetch for {mint} also failed ({metadata_fetch_error}).")
                else:
                    logger.info(f"No valid secondary URI found in rugcheck for {mint} or it's same as primary.")
                    # metadata_fetch_error already holds the error from primary URI or "NO_PRIMARY_URI"

            # --- Process metadata if successfully fetched ---
            if isinstance(metadata, dict): # Successfully fetched metadata
                website_url = metadata.get("website") or metadata.get("homepage") or metadata.get("url") or metadata.get("external_url")
                telegram_url = metadata.get("telegram") or metadata.get("tg")
                twitter_url = metadata.get("twitter") or metadata.get("x")
                

                website_url = str(website_url) if website_url is not None and isinstance(website_url, (str, int, float)) else None
                # --- Telegram Check ---
                telegram_results = None
                if telegram_url and is_valid_telegram(telegram_url):
                    telegram_results = await check_telegram_channel(telegram_url)
                    
                twitter_url = str(twitter_url) if twitter_url is not None and isinstance(twitter_url, (str, int, float)) else None
                
                social_links_for_scoring = {"website": website_url, "telegram": telegram_url, "twitter": twitter_url}

                verification_results = None
                if website_url:
                    try:
                        parsed_domain_val_obj = urlparse(website_url)
                        parsed_domain_val = parsed_domain_val_obj.netloc.lower().replace('www.', '')
                        if parsed_domain_val:
                            is_disallowed_website = any(parsed_domain_val == disallowed or parsed_domain_val.endswith('.' + disallowed) for disallowed in self.disallowed_domains)
                        else: # Invalid structure
                            is_disallowed_website = True 
                    except Exception: # Parsing error
                        is_disallowed_website = True
                    
                    if not is_disallowed_website:
                        verification_results = await self._verify_website_details(website_url, token_name, token_symbol)

                social_score = self._calculate_social_score(social_links_for_scoring, token_name, token_symbol, verification_results, telegram_results)
                
                details = {
                    "metadata_source": "primary_uri",
                    "website_verification": verification_results,
                    "telegram_stats": telegram_results
                }
                
                await self._update_token_socials(mint, website_url, telegram_url, twitter_url, social_score, self.config['SOCIALS_SCORE_TYPE_INITIAL'], details)
                return True
            else: # Metadata fetch failed
                # Even if metadata fails, check existing telegram URL for updates
                if existing_telegram_url and is_valid_telegram(existing_telegram_url):
                    telegram_results = await check_telegram_channel(existing_telegram_url)
                    if telegram_results and telegram_results.get('valid'):
                         # We don't have other links, so we can't do a full score,
                         # but we can log the TG update as a separate entry
                         tg_details = {"metadata_source": "existing_db_link", "telegram_stats": telegram_results}
                         # We pass a score of 0 because this isn't a full recalculation, just a data log event
                         await self._update_token_socials(mint, None, None, None, self.score_failed_metadata, self.config['SOCIALS_SCORE_TYPE_TELEGRAM'], tg_details)

                final_error_reason = metadata_fetch_error if metadata_fetch_error else "FAILED_METADATA_UNKNOWN"
                await self._update_token_socials(mint, None, None, None, self.score_failed_metadata, "METADATA_FETCH_FAILURE", {"error": final_error_reason})
                return final_error_reason

        except Exception as e:
            logger.error(f"💥 Unexpected error processing socials for {mint}: {e}", exc_info=True)
            try:
                await self._update_token_socials(mint, None, None, None, self.score_failed_metadata, "PROCESSING_ERROR", {"error": str(e)})
            except Exception as db_e:
                logger.error(f"Failed to update socials_last_checked for {mint} after unexpected error: {db_e}")
            return "Error UnhandledProcessToken"

    async def _telegram_update_worker(self):
        """
        A separate worker that periodically re-checks Telegram statistics for active, non-migrated tokens
        and logs new social score entries.
        """
        logger.info("🚀 Telegram stats update worker started.")
        interval = self.config.get('SOCIALS_TELEGRAM_UPDATE_INTERVAL_MINUTES', 15) * 60

        while not self.state.shutdown_event.is_set():
            try:
                await self.state.wait_or_interrupt(timeout=interval)
                if self.state.shutdown_event.is_set(): break

                logger.debug("Running periodic Telegram stats update...")
                async with self.db_client.pool.acquire() as conn:
                    # Get active tokens that are still on pump.fun and have a valid telegram link
                    tokens_to_check = await conn.fetch("""
                        SELECT mint, telegram, socials_score
                        FROM tokens
                        WHERE is_active = TRUE
                          AND data_source = 'PUMP'
                          AND telegram IS NOT NULL AND telegram != ''
                    """)

                for token in tokens_to_check:
                    if self.state.shutdown_event.is_set(): break
                    
                    mint, telegram_url, old_score = token['mint'], token['telegram'], token['socials_score']
                    
                    if is_valid_telegram(telegram_url):
                        telegram_results = await check_telegram_channel(telegram_url)
                        if telegram_results and telegram_results.get('valid'):
                            # For simplicity, we'll just log the new data. A more complex system
                            # could recalculate the entire score.
                            details = {"telegram_stats": telegram_results, "previous_score": old_score}
                            
                            # We can log this as a new event without changing the main score,
                            # or we could implement a recalculation logic. Let's log it.
                            await self._update_token_socials(mint, None, None, None, old_score, self.config['SOCIALS_SCORE_TYPE_TELEGRAM'], details)
                            logger.debug(f"Logged Telegram stats update for {mint}.")
                        await asyncio.sleep(1) # Small delay between checks
            
            except asyncio.CancelledError:
                logger.info("⏹ Telegram stats update worker task cancelled.")
                break
            except Exception as e:
                logger.error(f"💥 Unexpected error in Telegram stats update worker: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=60) # Longer wait on error

        logger.info("🛑 Telegram stats update worker shutting down.")


    async def _refresh_queue(self):
        """Refreshes the Socials Check priority queue based on token volume."""
        try:
            sol_price = await self.state.get_sol_price()
            if sol_price is None:
                logger.warning("⚠ SOL_PRICE not updated yet; skipping Socials check queue refresh.")
                return False

            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done() # Important to call task_done for each get
                except asyncio.QueueEmpty:
                    break
                except Exception as e: # Catch any other error during queue clear
                    logger.error(f"Error clearing item from socials check queue: {e}")
                    # If task_done fails or other error, break to prevent potential infinite loop here
                    break


            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND (t.socials_score IS NULL OR t.socials_last_checked < NOW() - ($1 || ' minutes')::interval)
                    GROUP BY t.mint
                    ORDER BY volume DESC
                """, str(self.config['SOCIALS_CHECK_REFRESH_INTERVAL']))

                logger.debug(f"🔍 Found {len(rows)} active tokens potentially needing Socials Check for refresh.")

                tokens_added = 0
                if rows:
                    for row in rows:
                        mint = row["mint"]
                        volume = row["volume"] or Decimal(0)
                        priority = -float(volume)
                        current_attempts = self.fetch_attempts.get(mint, 0)

                        # Only add if not already reached max attempts (deprioritized)
                        if current_attempts < MAX_FETCH_ATTEMPTS:
                             await self.queue.put((priority, mint))
                             tokens_added += 1
                        else:
                             logger.debug(f"Token {mint} previously reached max fetch attempts ({current_attempts}), not re-adding during this refresh cycle.")
                    logger.debug(f"🔄 Refreshed Socials Check queue. Added {tokens_added} tokens (current size: {self.queue.qsize()}).")
            return True

        except Exception as e:
            logger.error(f"❌ Critical error in _refresh_queue: {e}", exc_info=True)
            return False

    async def _worker(self):
        logger.info("🚀 Socials worker started.")
        last_refresh_time = 0
        queue_refresh_interval = 30

        while not self.state.shutdown_event.is_set():
            try:
                current_time = asyncio.get_event_loop().time()
                if self.queue.empty() or (current_time - last_refresh_time > queue_refresh_interval):
                    logger.debug("🔄 Triggering Socials Check queue refresh...")
                    refreshed = await self._refresh_queue()
                    if refreshed:
                        last_refresh_time = current_time
                    else:
                        await self.state.wait_or_interrupt(timeout=5)
                        continue

                if self.queue.empty():
                    await self.state.wait_or_interrupt(timeout=5)
                    continue

                priority, mint = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                task_completed_flag = False
                try:
                    async with self.db_client.pool.acquire() as conn: # Check if token still exists and is active
                        token_status = await conn.fetchrow("SELECT is_active, socials_last_checked FROM tokens WHERE mint = $1", mint)

                    if not token_status or not token_status['is_active']:
                        logger.debug(f"Token {mint} no longer exists or is inactive. Skipping Socials Check.")
                        self.queue.task_done()
                        task_completed_flag = True
                        self.fetch_attempts.pop(mint, None)
                        continue

                    # Check if recently processed to avoid immediate re-processing due to queue race conditions
                    if token_status['socials_last_checked']:
                        time_since_last_check = datetime.now(timezone.utc) - token_status['socials_last_checked'].replace(tzinfo=timezone.utc)
                        if time_since_last_check < timedelta(minutes=self.config['SOCIALS_CHECK_REFRESH_INTERVAL'] / 2): # Check if processed in less than half refresh interval
                            logger.debug(f"Token {mint} was checked very recently ({time_since_last_check}). Skipping this queue item.")
                            self.queue.task_done()
                            task_completed_flag = True
                            continue


                    process_status = await self.process_token(mint) # This now updates DB for failures too

                    if process_status is True:
                        logger.debug(f"✅ Successfully processed Socials Check for {mint}.")
                        self.fetch_attempts.pop(mint, None)
                    # "NO_URI", "NOT_FOUND" are permanent issues handled by process_token updating DB.
                    # "Error InvalidURI" is also permanent.
                    elif process_status in ["NO_PRIMARY_URI", "NOT_FOUND", "Error InvalidURI"]:
                        logger.warning(f"Socials Check for {mint} failed with permanent error: {process_status}. It's now marked in DB and deprioritized.")
                        self.fetch_attempts[mint] = MAX_FETCH_ATTEMPTS
                        await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                    # Other error strings from _fetch_metadata or process_token are transient or specific.
                    elif isinstance(process_status, str) and process_status.startswith("Error"):
                        current_attempts = self.fetch_attempts.get(mint, 0) + 1
                        self.fetch_attempts[mint] = current_attempts
                        logger.warning(f"🔄 Socials Check failed for {mint} ({process_status}). Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")

                        if current_attempts < MAX_FETCH_ATTEMPTS:
                            await self.queue.put((priority, mint)) # Requeue with original priority
                            logger.info(f"Retrying Socials Check for {mint} later (attempt {current_attempts}).")
                        else:
                            await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                            logger.warning(f"Max socials check fetch attempts ({MAX_FETCH_ATTEMPTS}) reached for {mint} due to {process_status}. Deprioritizing. It's marked in DB.")
                    elif process_status is False: # Generic internal error in process_token not returning specific string
                        logger.warning(f"📉 Socials Check processing failed generally for {mint}. Requeuing with original priority for now.")
                        await self.queue.put((priority, mint))
                        self.fetch_attempts.pop(mint, None) # Reset attempts for general error for now

                    self.queue.task_done()
                    task_completed_flag = True

                except asyncio.TimeoutError:
                    logger.debug("Socials Check queue.get() timed out.")
                    # Do not call task_done if get() times out, as no item was retrieved.
                except Exception as proc_err:
                    logger.error(f"❌ Unexpected error processing socials check item for token {mint if 'mint' in locals() else 'UNKNOWN'}: {proc_err}", exc_info=True)
                    if 'mint' in locals() and 'priority' in locals() : # If mint and priority were obtained
                         await self.queue.put((priority, mint)) # Requeue on unexpected errors
                         self.fetch_attempts.pop(mint, None)
                finally:
                    if not task_completed_flag and 'mint' in locals(): # Ensure task_done is called if an error happened after .get() but before explicit task_done
                        try:
                            self.queue.task_done()
                        except ValueError: # If already done by preceding logic
                            pass
                        except Exception as td_err:
                            logger.error(f"Error calling task_done for {mint} in worker's finally block: {td_err}")
            except asyncio.CancelledError:
                logger.info("⏹ Socials Check worker task cancelled.")
                break
            except Exception as e:
                logger.error(f"💥 Unexpected error in Socials Check worker main loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=10)
        logger.info("🛑 Socials check worker shutting down.")

    def start(self) -> list[asyncio.Task]:
        logger.info("Creating Socials Check background tasks...")
        return [
            asyncio.create_task(self._worker(), name="socialscheck_worker"),
            asyncio.create_task(self._telegram_update_worker(), name="telegram_update_worker")
        ]
