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
            logger.debug(f"🚩 Invalid or missing URI for social metadata: {uri}")
            return "Error InvalidURI"

        response_obj_for_logging = None
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(uri)
                response_obj_for_logging = response

                content_type = response.headers.get('content-type', '').lower()
                if not ('application/json' in content_type or 'text/json' in content_type or not content_type):
                    if content_type.startswith('image/') or content_type.startswith('application/octet-stream') or content_type.startswith('text/html'):
                        logger.warning(f"🚩 Metadata fetch for {uri} returned non-JSON content-type: {content_type}.")
                        return f"Error NotJSONContentType: {content_type}"

                response.raise_for_status()

                try:
                    metadata = response.json()
                    return metadata
                except json.JSONDecodeError as e_initial:
                    if "Invalid control character" in str(e_initial):
                        logger.warning(f"🚩 Initial JSON parsing for {uri} failed. Attempting with strict=False.")
                        try:
                            metadata_strict_false = json.loads(response.text, strict=False)
                            return metadata_strict_false
                        except json.JSONDecodeError as e_strict:
                            logger.error(f"🚩 Failed to decode JSON from {uri} even with strict=False. Error: {e_strict}. Response text: {response.text[:200]}...")
                            return "Error DecodeFailedStrict"
                    else:
                        logger.error(f"🚩 Failed to decode JSON from {uri}. Error: {e_initial}. Response text: {response.text[:200]}...")
                        return "Error DecodeGeneral"

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"🚩 HTTP error fetching social metadata from {uri}: {status_code} {e.response.reason_phrase}")
            return f"Error HTTP {status_code}"
        except httpx.TimeoutException:
            logger.warning(f"🚩 Timeout fetching social metadata from {uri}")
            return "Error Timeout"
        except httpx.RequestError as e:
            logger.warning(f"🚩 Request error fetching social metadata from {uri}: {e}")
            return "Error Request"
        except Exception as e:
            response_text_snippet = response_obj_for_logging.text[:200] if response_obj_for_logging and hasattr(response_obj_for_logging, 'text') else 'N/A'
            logger.error(f"🚩 Unexpected error processing social metadata from {uri}: {e}. Response text: {response_text_snippet}...", exc_info=True)
            return "Error UnknownFetch"

    async def _verify_website_details(self, url: str, token_name: str, token_symbol: str) -> dict:
        results = {'uses_https': False, 'is_reachable': False, 'mentions_token': False, 'error': None}
        token_name_lower = (token_name or "").lower()
        token_symbol_lower = (token_symbol or "").lower()

        try:
            parsed_url = urlsplit(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                 results['error'] = "Invalid URL format"
                 return results

            results['uses_https'] = parsed_url.scheme == 'https'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = await self._verify_client.get(url, headers=headers)
            response.raise_for_status()
            results['is_reachable'] = True

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
                elif token_symbol_lower and token_symbol_lower in page_content:
                     results['mentions_token'] = True
            
        except httpx.HTTPStatusError as e:
            results['error'] = f"HTTP Error {e.response.status_code}"
        except httpx.TimeoutException:
            results['error'] = "Timeout"
        except httpx.RequestError as e:
            results['error'] = f"Request Error: {type(e).__name__}"
        except ImportError:
             results['error'] = "Missing 'beautifulsoup4' library"
             logger.error("🚨 Dependency missing: Please install 'beautifulsoup4' (`pip install beautifulsoup4`) for website content checking.")
        except Exception as e:
            results['error'] = f"Unexpected Error: {type(e).__name__}"
            logger.error(f"🚩 Website Verify Fail ({url}): Unexpected error: {e}", exc_info=True)
        return results

    def _calculate_social_score(self, social_data: dict, token_name: str | None, token_symbol: str | None, verification_results: dict | None, telegram_results: dict | None) -> int:
        total_penalty = 0
        reasons = []
        token_name = (token_name or "").lower()
        token_symbol = (token_symbol or "").lower()

        website = social_data.get("website")
        if not website:
            total_penalty += self.penalty_no_website
            reasons.append(f"No Website: +{self.penalty_no_website}")
        elif not isinstance(website, str):
            total_penalty += self.penalty_invalid_website_type
            reasons.append(f"Invalid Website Type: +{self.penalty_invalid_website_type}")
        else:
            try:
                parsed_domain_obj = urlparse(website)
                parsed_domain = parsed_domain_obj.netloc.lower().replace('www.', '')
                is_disallowed_website = False
                if parsed_domain:
                    if any(parsed_domain == d or parsed_domain.endswith('.' + d) for d in self.disallowed_domains):
                        total_penalty += self.penalty_common_platform_website
                        reasons.append(f"Disallowed Domain: +{self.penalty_common_platform_website}")
                        is_disallowed_website = True
                else:
                    total_penalty += self.penalty_website_invalid_url
                    reasons.append(f"Invalid URL: +{self.penalty_website_invalid_url}")
                    is_disallowed_website = True

                if not is_disallowed_website:
                    if verification_results and verification_results['error']:
                        error_str = verification_results['error']
                        if "Timeout" in error_str:
                            total_penalty += self.penalty_website_timeout
                            reasons.append(f"Website Timeout: +{self.penalty_website_timeout}")
                        elif "HTTP Error" in error_str:
                            total_penalty += self.penalty_website_http_error
                            reasons.append(f"HTTP Error: +{self.penalty_website_http_error}")
                        else:
                            total_penalty += self.penalty_website_other_error
                            reasons.append(f"Website Error: +{self.penalty_website_other_error}")
                    elif verification_results:
                        if not verification_results['uses_https']:
                            total_penalty += self.penalty_no_https
                            reasons.append(f"No HTTPS: +{self.penalty_no_https}")
                        if not verification_results['mentions_token']:
                            total_penalty += self.penalty_website_no_mention
                            reasons.append(f"No Token Mention: +{self.penalty_website_no_mention}")
                        if parsed_domain:
                            if token_name and (token_name in parsed_domain):
                                total_penalty += self.bonus_domain_match
                                reasons.append(f"Domain Match: {self.bonus_domain_match}")
                            elif token_symbol and (token_symbol in parsed_domain):
                                total_penalty += self.bonus_domain_match
                                reasons.append(f"Domain Match: {self.bonus_domain_match}")
            except Exception as e:
                total_penalty += self.penalty_website_invalid_url
                reasons.append(f"URL Parse Error: +{self.penalty_website_invalid_url}")

        telegram = social_data.get("telegram") or social_data.get("tg")
        if not telegram:
            total_penalty += self.penalty_no_telegram
            reasons.append(f"No Telegram: +{self.penalty_no_telegram}")
        elif not isinstance(telegram, str) or not is_valid_telegram(telegram):
            total_penalty += self.penalty_invalid_telegram_url
            reasons.append(f"Invalid TG URL: +{self.penalty_invalid_telegram_url}")
        elif telegram_results and telegram_results.get('valid'):
            members = telegram_results.get('members') or 0
            online = telegram_results.get('online') or 0
            if members > self.threshold_tg_high_members:
                total_penalty += self.bonus_tg_high_members
                reasons.append(f"High TG Members: {self.bonus_tg_high_members}")
            if members > 0:
                online_ratio = online / members
                if online_ratio > self.threshold_tg_high_online_ratio:
                    total_penalty += self.bonus_tg_high_online_ratio
                    reasons.append(f"High Online Ratio: {self.bonus_tg_high_online_ratio}")
        
        twitter = social_data.get("twitter") or social_data.get("x")
        if not twitter:
            total_penalty += self.penalty_no_twitter
            reasons.append(f"No Twitter/X: +{self.penalty_no_twitter}")
        elif not isinstance(twitter, str) or not is_valid_twitter(twitter):
            total_penalty += self.penalty_invalid_twitter_url
            reasons.append(f"Invalid Twitter URL: +{self.penalty_invalid_twitter_url}")

        valid_links = [link for link in [website, telegram, twitter] if isinstance(link, str) and link]
        if len(valid_links) > len(set(valid_links)):
            total_penalty += self.penalty_duplicate_links
            reasons.append(f"Duplicate Links: +{self.penalty_duplicate_links}")

        final_score = min(max(total_penalty, 0), 100)
        display_name = token_name if token_name else token_symbol
        logger.debug(f"📊 Socials Score for '{display_name}': {final_score} (Reasons: {', '.join(reasons)})")
        return final_score

    async def _update_token_socials(self, mint: str, website: str | None, telegram: str | None, twitter: str | None, score: int, score_type: str, details: dict | None):
        try:
            async with self.db_client.pool.acquire() as conn:
                async with conn.transaction():
                    token_exists = await conn.fetchval("SELECT 1 FROM tokens WHERE mint = $1", mint)
                    if not token_exists:
                        logger.warning(f"🚩 Token {mint} was deleted from DB before socials could be updated. Aborting storage.")
                        return True

                    await conn.execute("""
                        UPDATE tokens
                        SET website = COALESCE($2, website),
                            telegram = COALESCE($3, telegram),
                            twitter = COALESCE($4, twitter),
                            socials_score = $5,
                            socials_last_checked = NOW()
                        WHERE mint = $1
                    """, mint, website, telegram, twitter, score)

                    await conn.execute("""
                        INSERT INTO social_scores (mint, score_type, score_value, details)
                        VALUES ($1, $2, $3, $4)
                    """, mint, score_type, score, json.dumps(details) if details else None)

            logger.debug(f"💾 Updated socials for {mint}. Score: {score}, Type: {score_type}.")
            return True
        except asyncpg.exceptions.ForeignKeyViolationError as fk_error:
            logger.warning(f"🚩 Caught a Foreign Key violation for {mint} despite the pre-check. Aborting. Details: {fk_error}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update socials in DB for {mint}: {e}", exc_info=True)
            return False

    async def process_token(self, mint: str) -> str | bool:
        logger.debug(f"🔍 Processing socials for token: {mint}")
        metadata_fetch_error = None

        try:
            async with self.db_client.pool.acquire() as conn:
                token_info_row = await conn.fetchrow("""
                    SELECT uri, COALESCE(name, '') as name, COALESCE(symbol, '') as symbol, telegram
                    FROM tokens WHERE mint = $1
                """, mint)

            if not token_info_row:
                logger.warning(f"🚩 Token {mint} not found in DB for social processing.")
                return "NOT_FOUND"

            primary_uri = token_info_row['uri']
            token_name = token_info_row['name']
            token_symbol = token_info_row['symbol']
            existing_telegram_url = token_info_row['telegram']

            metadata = None
            if not primary_uri or not primary_uri.strip():
                metadata_fetch_error = "NO_PRIMARY_URI"
            else:
                metadata = await self._fetch_metadata(primary_uri)

            if isinstance(metadata, str) or metadata is None:
                if isinstance(metadata, str): metadata_fetch_error = metadata
                logger.info(f"Primary URI for {mint} failed ({metadata_fetch_error}). Checking rugcheck for fallback.")
                async with self.db_client.pool.acquire() as conn:
                    rugcheck_uri_row = await conn.fetchrow("SELECT tokenMeta_uri FROM rugcheck WHERE mint = $1", mint)
                
                if rugcheck_uri_row and rugcheck_uri_row['tokenmeta_uri'] and rugcheck_uri_row['tokenmeta_uri'].strip() and rugcheck_uri_row['tokenmeta_uri'] != primary_uri:
                    secondary_uri = rugcheck_uri_row['tokenmeta_uri']
                    logger.info(f"Found fallback URI from rugcheck: {secondary_uri}. Fetching...")
                    metadata = await self._fetch_metadata(secondary_uri)
                    if isinstance(metadata, str) or metadata is None:
                         if isinstance(metadata, str): metadata_fetch_error = metadata
                         logger.warning(f"Fallback URI fetch for {mint} also failed ({metadata_fetch_error}).")
                else:
                    logger.info(f"No valid fallback URI found in rugcheck for {mint}.")

            if isinstance(metadata, dict):
                website_url = metadata.get("website") or metadata.get("homepage") or metadata.get("url") or metadata.get("external_url")
                telegram_url = metadata.get("telegram") or metadata.get("tg")
                twitter_url = metadata.get("twitter") or metadata.get("x")
                
                telegram_results = None
                if telegram_url and is_valid_telegram(telegram_url):
                    telegram_results = await check_telegram_channel(telegram_url)
                    
                social_links = {"website": str(website_url) if website_url else None, "telegram": telegram_url, "twitter": str(twitter_url) if twitter_url else None}

                verification_results = None
                if social_links["website"]:
                    verification_results = await self._verify_website_details(social_links["website"], token_name, token_symbol)

                social_score = self._calculate_social_score(social_links, token_name, token_symbol, verification_results, telegram_results)
                details = {"metadata_source": primary_uri, "website_verification": verification_results, "telegram_stats": telegram_results}
                await self._update_token_socials(mint, social_links["website"], social_links["telegram"], social_links["twitter"], social_score, self.config['SOCIALS_SCORE_TYPE_INITIAL'], details)
                return True
            else:
                if existing_telegram_url and is_valid_telegram(existing_telegram_url):
                    telegram_results = await check_telegram_channel(existing_telegram_url)
                    if telegram_results and telegram_results.get('valid'):
                         tg_details = {"metadata_source": "existing_db_link", "telegram_stats": telegram_results}
                         await self._update_token_socials(mint, None, None, None, self.score_failed_metadata, self.config['SOCIALS_SCORE_TYPE_TELEGRAM'], tg_details)

                final_error_reason = metadata_fetch_error if metadata_fetch_error else "FAILED_METADATA_UNKNOWN"
                await self._update_token_socials(mint, None, None, None, self.score_failed_metadata, "METADATA_FETCH_FAILURE", {"error": final_error_reason})
                return final_error_reason

        except Exception as e:
            logger.error(f"🚨 Unexpected error processing socials for {mint}: {e}", exc_info=True)
            try:
                await self._update_token_socials(mint, None, None, None, self.score_failed_metadata, "PROCESSING_ERROR", {"error": str(e)})
            except Exception as db_e:
                logger.error(f"🚨 Failed to update socials_last_checked for {mint} after unexpected error: {db_e}")
            return "Error UnhandledProcessToken"

    async def _requeue_telegram_updates(self):
        """Re-queues active tokens for a Telegram stats update."""
        try:
            async with self.db_client.pool.acquire() as conn:
                requeue_interval_minutes = self.config.get('SOCIALS_TELEGRAM_UPDATE_INTERVAL_MINUTES', 15)
                tokens_to_recheck = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS recent_volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE
                      AND t.data_source = 'PUMP'
                      AND t.telegram IS NOT NULL AND t.telegram != ''
                      AND t.socials_last_checked < NOW() - ($1 || ' minutes')::interval
                    GROUP BY t.mint
                    ORDER BY recent_volume DESC;
                """, str(requeue_interval_minutes))
            
            if tokens_to_recheck:
                for token in tokens_to_recheck:
                    priority = -float(token['recent_volume'])
                    await self.queue.put((priority, token['mint']))
                logger.info(f"🔁 Re-queued {len(tokens_to_recheck)} tokens for Telegram status update.")
            
        except Exception as e:
            logger.error(f"🚨 Error during Telegram re-queue process: {e}", exc_info=True)

    async def _refresh_queue(self):
        """Refreshes the queue with tokens that have never had a socials check."""
        try:
            # This clear operation is the source of the race condition.
            # We will remove it and check attempts before putting items on the queue.
            # while not self.queue.empty():
            #     try: self.queue.get_nowait(); self.queue.task_done()
            #     except asyncio.QueueEmpty: break
            
            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND t.socials_score IS NULL
                    GROUP BY t.mint
                    ORDER BY volume DESC
                """)

            if rows:
                added_count = 0
                for row in rows:
                    mint = row["mint"]
                    # --- START: FIX ---
                    # Only add the token to the queue if it hasn't already reached max fetch attempts.
                    if self.fetch_attempts.get(mint, 0) < MAX_FETCH_ATTEMPTS:
                        priority = -float(row["volume"] or Decimal(0))
                        await self.queue.put((priority, mint))
                        added_count += 1
                    # --- END: FIX ---
                if added_count > 0:
                    logger.debug(f"🔄 Refreshed Socials queue with {added_count} new tokens.")
            return True

        except Exception as e:
            logger.error(f"🚨 Critical error in _refresh_queue: {e}", exc_info=True)
            return False

    async def _worker(self):
        logger.info("🔗 Socials worker started.")
        while not self.state.shutdown_event.is_set():
            try:
                if self.queue.empty():
                    logger.debug("Socials queue is empty. Attempting to refill...")
                    await self._refresh_queue()
                    if self.queue.empty():
                        await self._requeue_telegram_updates()
                    if self.queue.empty():
                        logger.debug("No new or re-queueable social tasks found. Waiting.")
                        await self.state.wait_or_interrupt(timeout=15)
                        continue

                priority, mint = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                try:
                    async with self.db_client.pool.acquire() as conn:
                        token_status = await conn.fetchrow("SELECT is_active FROM tokens WHERE mint = $1", mint)
                    if not token_status or not token_status['is_active']:
                        logger.debug(f"🚩 Token {mint} no longer active. Skipping Socials Check.")
                        self.queue.task_done()
                        continue

                    process_status = await self.process_token(mint)
                    
                    # --- START: REFINED ERROR HANDLING ---
                    permanent_failures = {
                        "NOT_FOUND", "Error InvalidURI", "NO_PRIMARY_URI",
                        "Error NotJSONContentType", "Error DecodeFailedStrict", 
                        "Error DecodeGeneral", "Error HTTP 404", "Error HTTP 403", "Error HTTP 401"
                    }
                    
                    is_permanent_failure = False
                    if isinstance(process_status, str):
                        for failure_type in permanent_failures:
                            if failure_type in process_status:
                                is_permanent_failure = True
                                break
                    
                    if process_status is True:
                        self.fetch_attempts.pop(mint, None)
                    elif is_permanent_failure:
                        logger.warning(f" socials Socials Check for {mint} failed with permanent error: '{process_status}'. No more retries.")
                        self.fetch_attempts[mint] = MAX_FETCH_ATTEMPTS
                    else: 
                        current_attempts = self.fetch_attempts.get(mint, 0) + 1
                        self.fetch_attempts[mint] = current_attempts
                        logger.warning(f" socials Socials Check for {mint} failed with transient error ('{process_status}'). Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")
                        if current_attempts < MAX_FETCH_ATTEMPTS:
                            await self.queue.put((priority, mint))
                        else:
                            await self.queue.put((DEPRIORITIZED_PRIORITY, mint))
                            logger.warning(f"🚩 Max socials check attempts ({MAX_FETCH_ATTEMPTS}) reached for {mint}. Deprioritizing.")
                    # --- END: REFINED ERROR HANDLING ---
                    
                    self.queue.task_done()

                except asyncio.TimeoutError:
                    continue
                except Exception as proc_err:
                    logger.error(f"🚨 Unexpected error processing socials item for {mint}: {proc_err}", exc_info=True)
                    if 'mint' in locals() and 'priority' in locals() :
                         await self.queue.put((priority, mint))
                    self.queue.task_done()
            
            except asyncio.CancelledError:
                logger.info("🛑 Socials Check worker task cancelled.")
                break
            except Exception as e:
                logger.error(f"🚨 Unexpected error in Socials Check worker main loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=10)
        logger.info("🛑 Socials check worker shutting down.")

    def start(self) -> list[asyncio.Task]:
        logger.info("Creating Socials Check background task...")
        return [
            asyncio.create_task(self._worker(), name="socialscheck_worker"),
        ]