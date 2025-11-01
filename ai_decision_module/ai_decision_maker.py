# ai_decision_maker.py
import ollama
import asyncio 
from sentence_transformers import SentenceTransformer
from bot_logger import logger
import json
import re
import yaml
import os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from database_handler import DatabaseClient 

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')

class AIDecisionMaker:
    """
    [REFACTORED]
    Manages communication with an LLM (via Ollama) to get trading advice.
    Uses PostgreSQL (with pgvector) for RAG memory, and runs all blocking
    operations in a thread pool to be fully asynchronous.
    """
    
    EMBEDDING_DIM = 384

    def __init__(self, config: Dict[str, Any], db_client: DatabaseClient):
        """
        Initializes the AIDecisionMaker.
        """
        self.config = config
        self.db_client = db_client 
        self.model = self.config.get('AI_MODEL_NAME', 'llama3:latest')
        self.prompts_dir = self.config.get('_AI_PROMPTS_DIR', 'ai_decision_module/prompts')
        self.prompts = self._load_prompts()
        
        # --- NEW: Verbose Logging Flag ---
        self.log_verbose = self.config.get('AI_LOG_VERBOSE', False)
        # --- END NEW ---
        
        embedding_model_name = self.config.get('_AI_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

        try:
            self.embedder = SentenceTransformer(embedding_model_name)
            logger.info(f"Sentence Transformer embedding model '{embedding_model_name}' loaded.")
        except Exception as e:
            logger.critical(f"Failed to load Sentence Transformer model '{embedding_model_name}': {e}", exc_info=True)
            raise
        
        logger.info(f"AI Decision Maker initialized with Ollama model: {self.model} and pgvector backend.")

    def _load_prompts(self) -> Dict[str, Any]:
        """Loads prompt templates and configurations from YAML files (Unchanged)."""
        loaded_prompts = {}
        try:
            base_path = os.path.join(self.prompts_dir, 'base.yaml')
            with open(base_path, 'r', encoding='utf-8') as f:
                base_config = yaml.safe_load(f)
                if not base_config: raise ValueError(f"{base_path} is empty or invalid")
                loaded_prompts['base'] = base_config

            for context_type in ['buy', 'sell']:
                specific_path = os.path.join(self.prompts_dir, f'{context_type}.yaml')
                with open(specific_path, 'r', encoding='utf-8') as f:
                    specific_config = yaml.safe_load(f)
                    if not specific_config: raise ValueError(f"{specific_path} is empty or invalid")
                    loaded_prompts[context_type] = {**base_config, **specific_config}

            logger.info(f"Successfully loaded prompt configurations from '{self.prompts_dir}'.")
            return loaded_prompts

        except FileNotFoundError as e:
            logger.critical(f"Prompt YAML file not found: {e}. Ensure '{self.prompts_dir}' contains base.yaml, buy.yaml, sell.yaml.", exc_info=True)
            raise
        except (yaml.YAMLError, Exception) as e:
            logger.critical(f"Error loading or parsing prompts: {e}", exc_info=True)
            raise

    async def embed_text(self, text: str) -> Optional[list]:
        """
        [REFACTORED] Generates sentence embeddings for the given text asynchronously.
        Wraps the blocking SentenceTransformer call in asyncio.to_thread().
        """
        if not text:
            logger.warning("Attempted to embed empty text.")
            return None
        try:
            if self.log_verbose: logger.debug("AI Worker: Embedding text... (STARTING BLOCKING CALL)")
            embedding = await asyncio.to_thread(self.embedder.encode, text)
            if self.log_verbose: logger.debug("AI Worker: Embedding text... (BLOCKING CALL COMPLETE)")
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: '{text[:100]}...'. Error: {e}", exc_info=True)
            return None

    async def add_decision_snapshot_to_memory(self, snapshot_data: dict, decision_info: dict):
        """
        [REFACTORED] Stores a snapshot of the market data, context, AI decision, and reasoning
        into the PostgreSQL `ai_decision_memory` table for future RAG retrieval.
        """
        # (Data assembly section is unchanged)
        mcap_usd = snapshot_data.get('market_cap', 0)
        volatility = snapshot_data.get('volatility', 0)
        rug_score = snapshot_data.get('rugcheck_latest', 'N/A')
        rug_trend = snapshot_data.get('rugcheck_trend', 'N/A')
        social_score = snapshot_data.get('social_latest', 'N/A')
        social_trend = snapshot_data.get('social_score_trend', 'N/A')
        token_age = snapshot_data.get('token_age_minutes', 'N/A')
        timestamp = snapshot_data.get('timestamp', datetime.now(timezone.utc).isoformat())
        mint = snapshot_data.get('mint', 'N/A')
        context = snapshot_data.get('decision_context', 'N/A')
        source = snapshot_data.get('source', 'N/A')
        creator_prolific = snapshot_data.get('is_prolific_creator', False)
        uri_status = snapshot_data.get('uri_status', 'N/A')
        market_summary = snapshot_data.get('market_dynamics_summary_str', 'N/A')
        trade_history = snapshot_data.get('trade_history_summary', 'N/A')
        explanation_snippet = "N/A"
        full_explanation = decision_info.get('explanation')
        placeholder_explanations = ["Explanation not found or invalid format.", "No explanation processed."]
        if full_explanation and full_explanation not in placeholder_explanations:
            explanation_snippet = full_explanation[:150] + ('...' if len(full_explanation) > 150 else '')
        else:
            full_explanation = None
        situation_summary = (
            f"Situation Snapshot at {timestamp} for {mint} ({context} context):\n"
            f"Source: {source}, MCap (USD): ${mcap_usd:,.0f}, Volatility: {volatility:.3f}\n"
            f"Token Age: {token_age} mins, Creator: {'Prolific' if creator_prolific else 'Normal'}, URI: {uri_status}\n"
            f"Rug Score: {rug_score} (Trend: {rug_trend})\n"
            f"Social Score: {social_score} (Trend: {social_trend})\n"
            f"Market Dynamics Summary: {market_summary}\n"
            f"Trade History: {trade_history}\n"
            f"AI Decision: {decision_info.get('decision', 'N/A')} (Confidence: {decision_info.get('confidence', 'N/A')})\n"
            f"Reasoning Snippet: {explanation_snippet}\n"
        )
        
        embedding = await self.embed_text(situation_summary)
        if not embedding:
            logger.warning(f"Failed to create embedding for decision snapshot (Mint: {mint}). Skipping memory add.")
            return

        snapshot_time_str = timestamp if isinstance(timestamp, str) else datetime.now(timezone.utc).isoformat()
        
        metadata_to_store = {
            "mint": mint, "timestamp": snapshot_time_str, "decision_context": context, "source": source,
            "market_cap": float(mcap_usd) if mcap_usd is not None and not np.isnan(mcap_usd) else None,
            "volatility": float(volatility) if volatility is not None and not np.isnan(volatility) else None,
            "token_age_minutes": float(token_age) if token_age is not None and not np.isnan(token_age) else None,
            "is_prolific_creator": bool(creator_prolific), "uri_status": str(uri_status),
            "rugcheck_score": str(rug_score), "social_score": str(social_score), "rugcheck_trend": str(rug_trend),
            "social_score_trend": str(social_trend), "decision": decision_info.get('decision'),
            "confidence": int(decision_info.get('confidence', 0)),
        }
        metadata_to_store = {k: v for k, v in metadata_to_store.items() if v is not None}
        metadata_json = json.dumps(metadata_to_store)

        query = """
            INSERT INTO ai_decision_memory (
                mint, evaluation_timestamp, decision_context, decision, confidence,
                explanation, situation_summary, embedding, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9
            );
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                await conn.execute(
                    query,
                    mint, datetime.fromisoformat(snapshot_time_str), context,
                    decision_info.get('decision'), int(decision_info.get('confidence', 0)),
                    full_explanation, situation_summary, 
                    str(embedding), # <-- This is the fix from last time
                    metadata_json
                )
            if self.log_verbose: logger.debug(f"Added decision snapshot to pgvector memory for {mint}")
        except Exception as e:
            logger.error(f"Failed to add decision snapshot to pgvector (Mint: {mint}): {e}", exc_info=True)

    async def retrieve_context(self, situation_query: str, top_k: int = 5) -> str:
        """
        [REFACTORED] Retrieves relevant past decision snapshots from pgvector based on semantic similarity
        to the current situation query.
        """
        if not situation_query:
            logger.warning("Retrieve context called with empty situation query.")
            return "No situation query provided for context retrieval."

        query_embedding = await self.embed_text(situation_query)
        if not query_embedding:
            logger.warning("Failed to create embedding for RAG query. Cannot retrieve context.")
            return "Embedding failed for query. Cannot retrieve context."

        query = """
            SELECT
                situation_summary,
                metadata,
                embedding <=> $1 AS distance
            FROM ai_decision_memory
            ORDER BY embedding <=> $1
            LIMIT $2;
        """
        
        try:
            async with self.db_client.pool.acquire() as conn:
                results = await conn.fetch(query, str(query_embedding), top_k) # <-- This is the fix from last time

            if not results:
                if self.log_verbose: logger.debug("No relevant past decision snapshots found in memory for query.")
                return "No relevant past decision snapshots found."

            context_parts = ["--- Relevant Past Situations & Decisions ---"]
            for i, record in enumerate(results):
                context_parts.append(f"Past Case {i+1} (Similarity Distance: {record['distance']:.4f}):")
                context_parts.append(record['situation_summary'].strip()) 
                metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                if metadata:
                    mcap_display = f"${metadata.get('market_cap', 0):,.0f}" if metadata.get('market_cap') else "N/A"
                    outcome_info = "" 
                    context_parts.append(
                        f"  (Metadata: Decision={metadata.get('decision', '?')}, "
                        f"Conf={metadata.get('confidence', '?')}, Context={metadata.get('decision_context', '?')}, "
                        f"MCap={mcap_display}{outcome_info})"
                    )
                context_parts.append("---")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error querying pgvector for RAG context: {e}", exc_info=True)
            return "Error retrieving context from memory."

    async def query_llm(self, prompt: str) -> str:
        """
        [REFACTORED] Sends the fully formatted prompt to the Ollama LLM asynchronously
        by wrapping the blocking 'ollama.chat' call in asyncio.to_thread().
        """
        if self.log_verbose: logger.debug(f"Sending prompt to LLM '{self.model}' (approx {len(prompt)} chars)")

        try:
            if self.log_verbose: logger.debug("AI Worker: Querying LLM... (STARTING BLOCKING CALL)")
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                options={'temperature': 0.1},
                messages=[{'role': 'user', 'content': prompt}]
            )
            if self.log_verbose: logger.debug("AI Worker: Querying LLM... (BLOCKING CALL COMPLETE)")
            
            result = response['message']['content'].strip()
            if self.log_verbose:
                log_result_snippet = result[:11] + ('...' if len(result) > 11 else '')
                logger.debug(f"LLM Response received:\n{log_result_snippet}")
            return result

        except Exception as e:
            logger.error(f"Ollama query failed using model '{self.model}': {e}", exc_info=True)
            return "HOLD:0\n---\nAI decision unavailable due to LLM query error."

    async def get_trade_advice(self, current_data: dict, include_explanation: bool = True) -> dict:
        """
        [REFACTORED] Orchestrates the process of getting trade advice from the LLM.
        This function is now fully asynchronous.
        """
        required_keys = ['mint', 'source', 'price', 'market_cap', 'volatility', 'decision_context', 'token_age_minutes']
        missing_keys = [k for k in required_keys if k not in current_data or current_data[k] is None]
        if missing_keys:
             logger.error(f"Missing essential keys for AI advice: {missing_keys}. Input data: {list(current_data.keys())}")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Incomplete essential data: Missing {missing_keys}"}

        decision_context = current_data['decision_context']
        if decision_context in ["INITIAL BUY", "REBUY"]:
            prompt_config = self.prompts['buy']
            if decision_context == "INITIAL BUY":
                specific_guidance_addon = "\n- This is the *first* potential buy. Assess initial risk carefully."
            else: # REBUY
                specific_guidance_addon = "\n- This is a *rebuy* opportunity. Check trade history for previous exit reason. Confirm trend reversal if needed."
            prompt_config['context_specific_guidance'] += specific_guidance_addon
        elif decision_context == "SELL/HOLD":
            prompt_config = self.prompts['sell']
        else:
            logger.warning(f"Unknown decision context '{decision_context}'. Defaulting to SELL/HOLD logic.")
            prompt_config = self.prompts['sell']
            decision_context = "SELL/HOLD"

        mcap_for_query = current_data.get('market_cap', 0)
        volatility_for_query = current_data.get('volatility', 0)
        rug_score_for_query = current_data.get('rugcheck_latest', 'N/A')
        rug_trend_for_query = current_data.get('rugcheck_trend', 'N/A')
        social_score_for_query = current_data.get('social_latest', 'N/A')
        social_trend_for_query = current_data.get('social_score_trend', 'N/A')
        age_for_query = current_data.get('token_age_minutes', 'N/A')
        creator_status_for_query = 'Prolific' if current_data.get('is_prolific_creator') else 'Normal'
        uri_status_for_query = current_data.get('uri_status', 'N/A')
        price_momentum_query_part = "N/A"
        if current_data['source'] == 'PUMP' and 'pump_price_change_1m' in current_data:
            price_momentum_query_part = current_data['pump_price_change_1m']
        elif current_data['source'] == 'DEXSCREENER' and 'dex_price_change_m5' in current_data:
            price_momentum_query_part = f"{current_data['dex_price_change_m5']}%"

        situation_query = (
            f"Analyze similar Solana meme coin situations: Context={decision_context}, "
            f"Source={current_data['source']}, MCap approx ${mcap_for_query:,.0f}, "
            f"Volatility level {volatility_for_query:.3f}, Token Age: {age_for_query} mins. "
            f"Rugcheck score {rug_score_for_query} trending {rug_trend_for_query}, "
            f"Social score {social_score_for_query} trending {social_trend_for_query}. "
            f"Creator Status: {creator_status_for_query}. URI Status: {uri_status_for_query}. "
            f"Price Momentum (recent): {price_momentum_query_part}"
        )
        if self.log_verbose: logger.debug(f"RAG Situation Query: {situation_query}")

        rag_context = await self.retrieve_context(situation_query)

        market_dynamics_formatted = "Market dynamics data not available or source unknown."
        source = current_data['source']
        try:
            if source == 'PUMP':
                pump_keys = re.findall(r'\{(\w+)\}', prompt_config['market_dynamics_template_pump'])
                if all(k in current_data for k in pump_keys):
                    market_dynamics_formatted = prompt_config['market_dynamics_template_pump'].format(**current_data)
                else:
                    logger.warning(f"Missing required PUMP market dynamics keys in current_data. Keys: {list(current_data.keys())}")
            elif source == 'DEXSCREENER':
                dex_keys = re.findall(r'\{(\w+)(?:[:\.].*)?\}', prompt_config['market_dynamics_template_dex'])
                if all(k in current_data for k in dex_keys):
                    market_dynamics_formatted = prompt_config['market_dynamics_template_dex'].format(**current_data)
                else:
                    logger.warning(f"Missing required DEXSCREENER market dynamics keys in current_data. Keys: {list(current_data.keys())}")
        except KeyError as e:
            logger.error(f"KeyError formatting market dynamics for {source}: Missing key '{e}'. Available data keys: {list(current_data.keys())}")
            market_dynamics_formatted = f"Error formatting market dynamics for {source} (KeyError: {e})."
        except Exception as e:
            logger.error(f"Unexpected error formatting market dynamics for {source}: {e}", exc_info=True)
            market_dynamics_formatted = f"Error formatting market dynamics for {source}."

        social_threshold = self.config.get('DEFAULT_SOCIAL_SCORE_THRESHOLD', 100)
        min_volatility_threshold = self.config.get('MIN_VOLATILITY', 0.1)
        default_mcap_threshold = self.config.get('DEFAULT_MARKETCAP_THRESHOLD', 14000)
        min_mcap_threshold = self.config.get('MIN_MARKETCAP_THRESHOLD', 4000)
        
        prompt_data = {
            'decision_context': decision_context,
            'trade_history_summary': current_data.get('trade_history_summary', 'N/A'),
            'social_threshold': social_threshold, 'min_volatility': min_volatility_threshold,
            'rag_context': rag_context, 'name': current_data.get('name', 'Unknown'),
            'mint': current_data.get('mint', 'N/A'),
            'token_age_minutes': current_data.get('token_age_minutes', 'N/A'),
            'creator_status': 'Prolific/Suspicious' if current_data.get('is_prolific_creator') else 'Normal/Unknown',
            'uri_status': current_data.get('uri_status', 'N/A'),
            'price': current_data.get('price', 0.0), 'market_cap': current_data.get('market_cap', 0.0),
            'volatility': current_data.get('volatility', 0.0),
            'rugcheck_latest': current_data.get('rugcheck_latest', 'N/A'),
            'rugcheck_initial': current_data.get('rugcheck_initial', 'N/A'),
            'rugcheck_trend': current_data.get('rugcheck_trend', 'N/A'),
            'rugcheck_stability': current_data.get('rugcheck_stability', 'N/A'),
            'social_latest': current_data.get('social_latest', 'N/A'),
            'social_initial': current_data.get('social_initial', 'N/A'),
            'social_score_trend': current_data.get('social_score_trend', 'N/A'),
            'social_stability': current_data.get('social_stability', 'N/A'),
            'telegram_members_trend': current_data.get('telegram_members_trend', 'N/A'),
            'telegram_online_ratio_trend': current_data.get('telegram_online_ratio_trend', 'N/A'),
            'source': source, 'market_dynamics_formatted': market_dynamics_formatted,
            'context_specific_guidance': prompt_config.get('context_specific_guidance', ''),
            'source_explanation': prompt_config.get('source_explanation', ''),
            'market_cap_guidance': prompt_config.get('market_cap_guidance', '').format(
                default_marketcap_threshold=default_mcap_threshold,
                min_marketcap_threshold=min_mcap_threshold
            ),
            'context_specific_rules': prompt_config.get('context_specific_rules', ''),
            'default_marketcap_threshold': default_mcap_threshold,
            'min_marketcap_threshold': min_mcap_threshold,
        }

        try:
            base_template_parts = self.prompts['base']
            final_prompt = f"{base_template_parts['task_definition']}\n\n" \
                           f"{base_template_parts['output_format_instructions']}\n\n" \
                           f"{base_template_parts['trade_history_section']}\n\n" \
                           f"{base_template_parts['key_decision_rules_section']}\n\n" \
                           f"{base_template_parts['current_token_data_header']}\n\n" \
                           f"{base_template_parts['metadata_context_section']}\n\n" \
                           f"{base_template_parts['core_metrics_section']}\n\n" \
                           f"{base_template_parts['risk_assessment_section']}\n\n" \
                           f"{base_template_parts['market_dynamics_header']}\n\n" \
                           f"{base_template_parts['final_reminder']}"
            final_prompt = final_prompt.format(**prompt_data)
        except KeyError as e:
             logger.critical(f"CRITICAL: Missing key '{e}' during prompt final formatting.")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed on key '{e}'."}
        except Exception as e:
             logger.critical(f"CRITICAL: Unexpected error during prompt final formatting: {e}", exc_info=True)
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed unexpectedly."}

        llm_response = await self.query_llm(final_prompt)

        parsed_decision = self._parse_llm_response_structured(llm_response, include_explanation)

        # This verbose log will now only show if AI_LOG_VERBOSE is True
        if self.log_verbose:
            log_explanation_snippet = parsed_decision['explanation'][:200] + ('...' if len(parsed_decision['explanation']) > 200 else '') if include_explanation and parsed_decision.get('explanation') else "(Explanation Skipped or Missing)"
            logger.debug(f"AI Advice for {current_data['mint']} ({decision_context}): {parsed_decision['decision']} "
                        f"(Confidence: {parsed_decision['confidence']}) - Reasoning: {log_explanation_snippet}")

        await self.add_decision_snapshot_to_memory(current_data, parsed_decision)

        return parsed_decision

    def _parse_llm_response_structured(self, llm_response: str, parse_explanation: bool = True) -> dict:
        """
        Parses the LLM response (Unchanged).
        """
        decision, confidence, explanation = "HOLD", 0, "No explanation processed." if not parse_explanation else "Explanation not found or invalid format."
        if not llm_response:
            logger.warning("LLM response parser received empty string.")
            return {"decision": decision, "confidence": confidence, "explanation": explanation}
        
        lines = llm_response.strip().split('\n', 2)
        strict_match = re.match(r"^\s*(BUY|SELL|HOLD)\s*:\s*(\d{1,3})\s*$", lines[0], re.IGNORECASE)

        if strict_match:
            decision = strict_match.group(1).upper()
            try:
                confidence = max(0, min(100, int(strict_match.group(2))))
                if self.log_verbose: logger.debug(f"Parser: Matched strict format '{decision}:{confidence}' on first line.")
                if parse_explanation:
                    if len(lines) > 2 and lines[1].strip() == '---':
                        explanation = lines[2].strip()
                        if self.log_verbose: logger.debug("Parser: Extracted explanation following strict format and separator.")
                    elif len(lines) == 2 and lines[1].strip() == '---':
                        explanation = "(No explanation text provided after separator)"
                        if self.log_verbose: logger.debug("Parser: Strict format OK, separator found, but no explanation text.")
                    elif len(lines) > 1:
                        explanation = "\n".join(lines[1:]).strip()
                        logger.warning("Parser: Strict format OK, but separator '---' missing. Taking rest as explanation.")
                    else: 
                        explanation = "(No explanation provided)"
                        if self.log_verbose: logger.debug("Parser: Strict format OK, but no subsequent lines for explanation.")
                return {"decision": decision, "confidence": confidence, "explanation": explanation}
            except ValueError:
                logger.warning(f"Parser: Matched strict format, but failed to parse confidence '{strict_match.group(2)}'. Falling back.")
        else:
            logger.warning(f"Parser: Strict format 'DECISION:CONFIDENCE' not found on line 1: '{lines[0]}'. Falling back.")

        fallback_result = self._parse_llm_response_fallback(llm_response)
        if not parse_explanation:
            fallback_result["explanation"] = "No explanation processed."
        return fallback_result

    def _parse_llm_response_fallback(self, llm_response: str) -> dict:
        """
        Fallback parser using regex (Unchanged).
        """
        decision, confidence, explanation = "HOLD", 50, llm_response
        response_upper = llm_response.upper()

        decision_match_strict_line = re.search(r"^\W*\*?\s*Decision\s*\*?\W*:\s*\**?(BUY|SELL|HOLD)\**?", llm_response, re.IGNORECASE | re.MULTILINE)
        if decision_match_strict_line:
            decision = decision_match_strict_line.group(1).upper()
            if self.log_verbose: logger.debug(f"Fallback Parser: Found decision '{decision}' via strict line search.")
        else:
            decision_match_lenient_line = re.search(r"^.*?\W*Decision\W*:\s*\**?(BUY|SELL|HOLD)\**?", llm_response, re.IGNORECASE | re.MULTILINE)
            if decision_match_lenient_line:
                decision = decision_match_lenient_line.group(1).upper()
                if self.log_verbose: logger.debug(f"Fallback Parser: Found decision '{decision}' via lenient line search.")
            elif re.search(r"^\s*SELL\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or ("SELL" in response_upper and "BUY" not in response_upper and "HOLD" not in response_upper):
                decision = "SELL"
                if self.log_verbose: logger.debug("Fallback Parser: Deduced 'SELL' via keyword dominance.")
            elif re.search(r"^\s*BUY\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or ("BUY" in response_upper and "SELL" not in response_upper and "HOLD" not in response_upper):
                decision = "BUY"
                if self.log_verbose: logger.debug("Fallback Parser: Deduced 'BUY' via keyword dominance.")
            elif re.search(r"^\s*HOLD\s*$", llm_response, re.IGNORECASE | re.MULTILINE):
                decision = "HOLD"
                if self.log_verbose: logger.debug("Fallback Parser: Found 'HOLD' on its own line.")
            else:
                 if self.log_verbose: logger.debug(f"Fallback Parser: No clear decision keyword found. Defaulting to '{decision}'.")

        conf_match_strict_line = re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1,3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
        if conf_match_strict_line:
            try: 
                confidence = max(0, min(100, int(conf_match_strict_line.group(1))))
                if self.log_verbose: logger.debug(f"Fallback Parser: Found confidence '{confidence}' via strict line search.")
            except ValueError: logger.warning(f"Fallback Parser: Strict confidence line found, but failed to parse number '{conf_match_strict_line.group(1)}'.")
        else:
            conf_match_lenient_line = re.search(r"^.*?\W*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1,3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
            if conf_match_lenient_line:
                 try: 
                     confidence = max(0, min(100, int(conf_match_lenient_line.group(1))))
                     if self.log_verbose: logger.debug(f"Fallback Parser: Found confidence '{confidence}' via lenient line search.")
                 except ValueError: logger.warning(f"Fallback Parser: Lenient confidence line found, but failed to parse number '{conf_match_lenient_line.group(1)}'.")
            else:
                 conf_fallback_anywhere = re.search(r"Confidence.*?[:\s](\d{1,3})", llm_response, re.IGNORECASE | re.DOTALL)
                 if conf_fallback_anywhere:
                     try: 
                         confidence = max(0, min(100, int(conf_fallback_anywhere.group(1))))
                         if self.log_verbose: logger.debug(f"Fallback Parser: Found confidence '{confidence}' via general fallback search.")
                     except ValueError: logger.warning(f"Fallback Parser: General confidence search found, but failed to parse number '{conf_fallback_anywhere.group(1)}'.")
                 else:
                     if self.log_verbose: logger.debug(f"Fallback Parser: No confidence value found. Defaulting to {confidence}.")

        explanation_match = re.search(r"^\W*\*?\s*(?:Explanation|Reasoning|Justification)\s*\*?\W*:\s*(.*)", llm_response, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if explanation_match:
            explanation_text = explanation_match.group(1).strip()
            explanation_text = re.sub(r"^\W*\*?\s*Decision\s*\*?\W*:.*?\n?", "", explanation_text, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            explanation_text = re.sub(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:.*?\n?", "", explanation_text, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            explanation = explanation_text
            if self.log_verbose: logger.debug("Fallback Parser: Found explanation using header keyword.")
        else:
            lines = llm_response.splitlines()
            start_index, last_marker_line_index, found_marker = 0, -1, False
            for i, line in enumerate(lines):
                 if re.search(r"^\W*\*?\s*Decision\s*\*?\W*:", line, re.IGNORECASE) or \
                    re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:", line, re.IGNORECASE):
                     last_marker_line_index = i; found_marker = True
            if found_marker:
                start_index = last_marker_line_index + 1
                if start_index < len(lines) and (re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:", lines[start_index], re.IGNORECASE)):
                    start_index += 1
                if start_index < len(lines):
                    explanation = "\n".join(lines[start_index:]).strip()
                    if self.log_verbose: logger.debug("Fallback Parser: Found explanation by splitting after last Decision/Confidence marker.")
                else:
                    explanation = "" 
                    if self.log_verbose: logger.debug("Fallback Parser: Decision/Confidence markers found, but no subsequent text for explanation.")

        explanation = re.sub(r'\n{3,}', '\n\n', explanation).strip()
        if not explanation: explanation = "(Explanation could not be extracted)"
        return {"decision": decision, "confidence": confidence, "explanation": explanation}