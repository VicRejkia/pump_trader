# path: socials_processor.py

"""
Handles fetching, scoring, and storing social media links for tokens.
Now supports multiple, prioritized check types (Initial, Follow-up, Telegram).
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple
from urllib.parse import urlparse, urlsplit

import asyncpg
import httpx
from bs4 import BeautifulSoup

from bot_logger import logger
from connectors.telegram_monitor import check_telegram_channel
from database_handler import DatabaseClient
from state_manager import GlobalState
from utils import is_valid_telegram, is_valid_twitter

# --- Configuration for Retries ---
MAX_FETCH_ATTEMPTS = 3
DEPRIORITIZED_PRIORITY = float('inf')

class SocialsProcessor:
    def __init__(self, state: GlobalState, db_client: DatabaseClient, config_dict: dict):
        self.state = state
        self.db_client = db_client
        self.config = config_dict
        self.queue = self.state.get_socialscheck_queue()
        self.fetch_attempts = {}

        # --- Scoring values are loaded dynamically in _calculate_social_score ---

        # Shared HTTP client for website verification
        self._verify_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, limits=httpx.Limits(max_connections=5))

    async def _fetch_metadata(self, uri: str) -> dict | str | None:
        # ... (this method remains unchanged)
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
        # ... (this method remains unchanged)
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

    def _calculate_social_score(self, social_data: dict, token_name: str | None, token_symbol: str | None, verification_results: dict | None, telegram_results: dict | None) -> Tuple[int, list]:
        # ... (this method is mostly unchanged but now returns reasons for logging)
        total_penalty = 0
        reasons = []
        token_name = (token_name or "").lower()
        token_symbol = (token_symbol or "").lower()

        # Dynamically load config values to allow for live updates
        disallowed_domains = self.config['SOCIALS_DISALLOWED_WEBSITE_DOMAINS']

        website = social_data.get("website")
        if not website:
            penalty = self.config['SOCIALS_PENALTY_NO_WEBSITE']
            total_penalty += penalty
            reasons.append(f"No Website: +{penalty}")
        elif not isinstance(website, str):
            penalty = self.config['SOCIALS_PENALTY_INVALID_WEBSITE_TYPE']
            total_penalty += penalty
            reasons.append(f"Invalid Website Type: +{penalty}")
        else:
            try:
                parsed_domain_obj = urlparse(website)
                parsed_domain = parsed_domain_obj.netloc.lower().replace('www.', '')
                is_disallowed_website = False
                if parsed_domain:
                    if any(parsed_domain == d or parsed_domain.endswith('.' + d) for d in disallowed_domains):
                        penalty = self.config['SOCIALS_PENALTY_COMMON_PLATFORM_WEBSITE']
                        total_penalty += penalty
                        reasons.append(f"Disallowed Domain: +{penalty}")
                        is_disallowed_website = True
                else:
                    penalty = self.config['SOCIALS_PENALTY_WEBSITE_INVALID_URL']
                    total_penalty += penalty
                    reasons.append(f"Invalid URL: +{penalty}")
                    is_disallowed_website = True

                if not is_disallowed_website:
                    if verification_results and verification_results['error']:
                        error_str = verification_results['error']
                        if "Timeout" in error_str:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_TIMEOUT']
                            total_penalty += penalty
                            reasons.append(f"Website Timeout: +{penalty}")
                        elif "HTTP Error" in error_str:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_HTTP_ERROR']
                            total_penalty += penalty
                            reasons.append(f"HTTP Error: +{penalty}")
                        else:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_OTHER_ERROR']
                            total_penalty += penalty
                            reasons.append(f"Website Error: +{penalty}")
                    elif verification_results:
                        if not verification_results['uses_https']:
                            penalty = self.config['SOCIALS_PENALTY_NO_HTTPS']
                            total_penalty += penalty
                            reasons.append(f"No HTTPS: +{penalty}")
                        if not verification_results['mentions_token']:
                            penalty = self.config['SOCIALS_PENALTY_WEBSITE_NO_MENTION']
                            total_penalty += penalty
                            reasons.append(f"No Token Mention: +{penalty}")
                        if parsed_domain:
                            bonus = self.config['SOCIALS_BONUS_DOMAIN_MATCH']
                            if token_name and (token_name in parsed_domain):
                                total_penalty += bonus
                                reasons.append(f"Domain Match: {bonus}")
                            elif token_symbol and (token_symbol in parsed_domain):
                                total_penalty += bonus
                                reasons.append(f"Domain Match: {bonus}")
            except Exception as e:
                penalty = self.config['SOCIALS_PENALTY_WEBSITE_INVALID_URL']
                total_penalty += penalty
                reasons.append(f"URL Parse Error: +{penalty}")

        telegram = social_data.get("telegram") or social_data.get("tg")
        if not telegram:
            penalty = self.config['SOCIALS_PENALTY_NO_TELEGRAM']
            total_penalty += penalty
            reasons.append(f"No Telegram: +{penalty}")
        elif not isinstance(telegram, str) or not is_valid_telegram(telegram):
            penalty = self.config['SOCIALS_PENALTY_INVALID_TELEGRAM_URL']
            total_penalty += penalty
            reasons.append(f"Invalid TG URL: +{penalty}")
        elif telegram_results and telegram_results.get('valid'):
            members = telegram_results.get('members') or 0
            online = telegram_results.get('online') or 0
            if members > self.config['SOCIALS_THRESHOLD_TG_HIGH_MEMBERS']:
                bonus = self.config['SOCIALS_BONUS_TG_HIGH_MEMBERS']
                total_penalty += bonus
                reasons.append(f"High TG Members: {bonus}")
            if members > 0:
                online_ratio = online / members
                if online_ratio > self.config['SOCIALS_THRESHOLD_TG_HIGH_ONLINE_RATIO']:
                    bonus = self.config['SOCIALS_BONUS_TG_HIGH_ONLINE_RATIO']
                    total_penalty += bonus
                    reasons.append(f"High Online Ratio: {bonus}")

        twitter = social_data.get("twitter") or social_data.get("x")
        if not twitter:
            penalty = self.config['SOCIALS_PENALTY_NO_TWITTER']
            total_penalty += penalty
            reasons.append(f"No Twitter/X: +{penalty}")
        elif not isinstance(twitter, str) or not is_valid_twitter(twitter):
            penalty = self.config['SOCIALS_PENALTY_INVALID_TWITTER_URL']
            total_penalty += penalty
            reasons.append(f"Invalid Twitter URL: +{penalty}")

        valid_links = [link for link in [website, telegram, twitter] if isinstance(link, str) and link]
        if len(valid_links) > len(set(valid_links)):
            penalty = self.config['SOCIALS_PENALTY_DUPLICATE_LINKS']
            total_penalty += penalty
            reasons.append(f"Duplicate Links: +{penalty}")

        final_score = min(max(total_penalty, 0), 100)
        return final_score, reasons

    async def _update_token_socials(self, mint: str, website: str | None, telegram: str | None, twitter: str | None, score: int, score_type: str, details: dict | None):
        # ... (this method remains unchanged)
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

    async def _process_metadata_check(self, mint: str, is_initial_check: bool) -> str | bool:
        """
        Handles the full metadata check workflow: fetch URI, fetch metadata,
        verify socials, calculate score, and store results.
        """
        score_type = self.config['SOCIALS_SCORE_TYPE_INITIAL'] if is_initial_check else self.config['SOCIALS_SCORE_TYPE_FOLLOWUP']
        logger.debug(f"🔍 Processing '{score_type}' for token: {mint}")

        try:
            async with self.db_client.pool.acquire() as conn:
                token_info_row = await conn.fetchrow("SELECT uri, name, symbol FROM tokens WHERE mint = $1", mint)

            if not token_info_row: return "NOT_FOUND"

            primary_uri, token_name, token_symbol = token_info_row['uri'], token_info_row['name'], token_info_row['symbol']
            metadata = await self._fetch_metadata(primary_uri)
            metadata_source = primary_uri

            if isinstance(metadata, str) or metadata is None:
                metadata_fetch_error = metadata or "UNKNOWN_ERROR"
                logger.warning(f"Primary URI for {mint} failed ({metadata_fetch_error}). No fallback for metadata checks.")
                await self._update_token_socials(mint, None, None, None, self.config['SOCIALS_SCORE_FAILED_METADATA'], "METADATA_FETCH_FAILURE", {"error": metadata_fetch_error, "source": metadata_source})
                return metadata_fetch_error

            website = metadata.get("website") or metadata.get("homepage") or metadata.get("url") or metadata.get("external_url")
            telegram = metadata.get("telegram") or metadata.get("tg")
            twitter = metadata.get("twitter") or metadata.get("x")

            social_links = {"website": str(website) if website else None, "telegram": telegram, "twitter": str(twitter) if twitter else None}

            verification_results, telegram_results = None, None
            if social_links["website"]:
                verification_results = await self._verify_website_details(social_links["website"], token_name, token_symbol)
            if social_links["telegram"] and is_valid_telegram(social_links["telegram"]):
                telegram_results = await check_telegram_channel(social_links["telegram"])

            social_score, reasons = self._calculate_social_score(social_links, token_name, token_symbol, verification_results, telegram_results)
            details = {"metadata_source": metadata_source, "website_verification": verification_results, "telegram_stats": telegram_results, "reasons": reasons}

            display_name = token_name or token_symbol or mint
            logger.debug(f"📊 Socials Score for '{display_name}': {social_score} (Reasons: {', '.join(reasons)})")

            await self._update_token_socials(mint, social_links["website"], social_links["telegram"], social_links["twitter"], social_score, score_type, details)
            return True

        except Exception as e:
            logger.error(f"🚨 Unexpected error in _process_metadata_check for {mint}: {e}", exc_info=True)
            return "Error UnhandledProcess"

    async def _process_telegram_update(self, mint: str) -> str | bool:
        """
        Handles fetching the latest Telegram stats for a token and updating its record.
        This recalculates the main score based on the new Telegram data.
        """
        logger.debug(f"🔍 Processing 'TELEGRAM_UPDATE' for token: {mint}")
        try:
            async with self.db_client.pool.acquire() as conn:
                token_info = await conn.fetchrow("SELECT name, symbol, website, telegram, twitter FROM tokens WHERE mint = $1", mint)

            if not token_info or not token_info['telegram']:
                return "NO_TELEGRAM_LINK"

            telegram_url = token_info['telegram']
            telegram_results = await check_telegram_channel(telegram_url)

            if not telegram_results or not telegram_results.get('valid'):
                # Not a retryable error if the link is now invalid
                logger.warning(f"Telegram link {telegram_url} for {mint} is no longer valid.")
                return "TELEGRAM_INVALID"

            # Re-calculate score with EXISTING social links but NEW telegram data
            existing_socials = {"website": token_info['website'], "telegram": token_info['telegram'], "twitter": token_info['twitter']}

            # We don't re-verify the website here to keep this check lightweight
            # Pass None for verification_results to use only link presence/format checks
            new_score, reasons = self._calculate_social_score(existing_socials, token_info['name'], token_info['symbol'], None, telegram_results)

            details = {"source": "Telegram Update", "telegram_stats": telegram_results, "reasons": reasons}
            await self._update_token_socials(mint, None, None, None, new_score, self.config['SOCIALS_SCORE_TYPE_TELEGRAM'], details)

            return True
        except Exception as e:
            logger.error(f"🚨 Unexpected error in _process_telegram_update for {mint}: {e}", exc_info=True)
            return "Error UnhandledProcess"

    async def _refresh_initial_checks_queue(self):
        """Queues tokens that have never had a socials check (highest priority)."""
        try:
            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND t.socials_score IS NULL
                    GROUP BY t.mint ORDER BY volume DESC
                """)
            if rows:
                for row in rows:
                    if row["mint"] not in self.fetch_attempts:
                        priority = -float(row["volume"] or 0)  # High priority for active new tokens
                        await self.queue.put((priority, (row["mint"], 'INITIAL_METADATA')))
                logger.debug(f"🔄 Refreshed Socials queue with {len(rows)} initial checks.")
        except Exception as e:
            logger.error(f"🚨 Critical error in _refresh_initial_checks_queue: {e}", exc_info=True)

    async def _requeue_followup_metadata_checks(self):
        """Queues active tokens for a periodic re-check of their full metadata URI."""
        try:
            interval = self.config.get('SOCIALS_METADATA_UPDATE_INTERVAL_MINUTES', 60)
            # --- START FIX ---
            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS recent_volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND t.socials_score IS NOT NULL
                      AND t.socials_last_checked < NOW() - ($1 || ' minutes')::interval
                    GROUP BY t.mint ORDER BY recent_volume DESC;
                """, str(interval))

                if rows:
                    for row in rows:
                        if row["mint"] not in self.fetch_attempts:
                            # Lower priority based on volume + penalty for previous checks
                            check_count = await self.db_client.get_social_check_count(row["mint"], conn)
                            priority = -(float(row["recent_volume"] or 0) / (check_count + 1))
                            await self.queue.put((priority, (row["mint"], 'FOLLOWUP_METADATA')))
                    logger.info(f"🔁 Re-queued {len(rows)} tokens for follow-up metadata checks.")
            # --- END FIX ---
        except Exception as e:
            logger.error(f"🚨 Error in _requeue_followup_metadata_checks: {e}", exc_info=True)

    async def _requeue_telegram_updates(self):
        """Queues active tokens for a Telegram stats update."""
        try:
            interval = self.config.get('SOCIALS_TELEGRAM_UPDATE_INTERVAL_MINUTES', 15)
            async with self.db_client.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT t.mint, COALESCE(SUM(tr.sol_amount), 0) AS recent_volume
                    FROM tokens t
                    LEFT JOIN trades tr ON t.mint = tr.mint AND tr.timestamp >= NOW() - INTERVAL '1 hour'
                    WHERE t.is_active = TRUE AND t.telegram IS NOT NULL AND t.telegram != ''
                      AND t.socials_last_checked < NOW() - ($1 || ' minutes')::interval
                    GROUP BY t.mint ORDER BY recent_volume DESC;
                """, str(interval))
            if rows:
                for row in rows:
                     if row["mint"] not in self.fetch_attempts:
                        priority = -float(row['recent_volume'])
                        await self.queue.put((priority, (row['mint'], 'TELEGRAM_UPDATE')))
                logger.info(f"🔁 Re-queued {len(rows)} tokens for Telegram status update.")
        except Exception as e:
            logger.error(f"🚨 Error during Telegram re-queue process: {e}", exc_info=True)

    async def _worker(self):
        logger.info("🔗 Socials worker started.")
        while not self.state.shutdown_event.is_set():
            try:
                if self.queue.empty():
                    logger.debug("Socials queue is empty. Refilling...")
                    await self._refresh_initial_checks_queue()
                    await self._requeue_followup_metadata_checks()
                    await self._requeue_telegram_updates()
                    if self.queue.empty():
                        await self.state.wait_or_interrupt(timeout=15)
                        continue

                priority, (mint, check_type) = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                if self.fetch_attempts.get(mint, 0) >= MAX_FETCH_ATTEMPTS:
                    self.queue.task_done(); continue

                async with self.db_client.pool.acquire() as conn:
                    is_active = await conn.fetchval("SELECT is_active FROM tokens WHERE mint = $1", mint)
                if not is_active:
                    self.queue.task_done(); continue

                process_status = False
                if check_type in ['INITIAL_METADATA', 'FOLLOWUP_METADATA']:
                    process_status = await self._process_metadata_check(mint, is_initial_check=(check_type == 'INITIAL_METADATA'))
                elif check_type == 'TELEGRAM_UPDATE':
                    process_status = await self._process_telegram_update(mint)

                # --- Preserved Error Handling Logic ---
                permanent_failures = {"NOT_FOUND", "Error InvalidURI", "NO_PRIMARY_URI", "NO_TELEGRAM_LINK", "TELEGRAM_INVALID", "Error NotJSONContentType", "Error DecodeFailedStrict", "Error DecodeGeneral", "Error HTTP 404", "Error HTTP 403", "Error HTTP 401"}
                is_permanent_failure = isinstance(process_status, str) and any(pf in process_status for pf in permanent_failures)

                if process_status is True:
                    self.fetch_attempts.pop(mint, None)
                elif is_permanent_failure:
                    logger.warning(f" socials Socials Check for {mint} ('{check_type}') failed with permanent error: '{process_status}'. No more retries.")
                    self.fetch_attempts[mint] = MAX_FETCH_ATTEMPTS
                else:
                    current_attempts = self.fetch_attempts.get(mint, 0) + 1
                    self.fetch_attempts[mint] = current_attempts
                    logger.warning(f" socials Socials Check for {mint} ('{check_type}') failed with transient error ('{process_status}'). Attempt {current_attempts}/{MAX_FETCH_ATTEMPTS}.")
                    if current_attempts < MAX_FETCH_ATTEMPTS:
                        await self.queue.put((priority, (mint, check_type)))
                    else:
                        await self.queue.put((DEPRIORITIZED_PRIORITY, (mint, check_type)))
                        logger.warning(f"🚩 Max socials check attempts ({MAX_FETCH_ATTEMPTS}) reached for {mint}. Deprioritizing.")

                self.queue.task_done()

            except asyncio.TimeoutError: continue
            except asyncio.CancelledError: logger.info("🛑 Socials Check worker task cancelled."); break
            except Exception as e:
                logger.error(f"🚨 Unexpected error in Socials Check worker main loop: {e}", exc_info=True)
                await self.state.wait_or_interrupt(timeout=10)

        logger.info("🛑 Socials check worker shutting down.")

    def start(self) -> list[asyncio.Task]:
        logger.info("Creating Socials Check background task...")
        return [asyncio.create_task(self._worker(), name="socialscheck_worker")]
