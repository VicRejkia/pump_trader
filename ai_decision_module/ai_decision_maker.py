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
        
        self.log_verbose = self.config.get('AI_LOG_VERBOSE', False)
        
        embedding_model_name = self.config.get('_AI_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

        try:
            self.embedder = SentenceTransformer(embedding_model_name)
            logger.info(f"🧠 Sentence Transformer embedding model '{embedding_model_name}' loaded.")
        except Exception as e:
            logger.critical(f"🧠 Failed to load Sentence Transformer model '{embedding_model_name}': {e}", exc_info=True)
            raise
        
        logger.info(f"🧠 AI Decision Maker initialized with Ollama model: {self.model} and pgvector backend.")

    def _load_prompts(self) -> Dict[str, Any]:
        """Loads prompt templates and configurations from YAML files with comment removal."""
        loaded_prompts = {}
        
        def remove_comments(content: str) -> str:
            """Remove comments from YAML content.
            
            Args:
                content: Raw YAML content as string
                
            Returns:
                YAML content with comments removed
            """
            lines = []
            for line in content.splitlines():
                line = line.split('#')[0]
                if line.strip():
                    lines.append(line)
            return '\n'.join(lines)
        
        try:
            base_path = os.path.join(self.prompts_dir, 'base.yaml')
            with open(base_path, 'r', encoding='utf-8') as f:
                content = remove_comments(f.read())
                base_config = yaml.safe_load(content)
                if not base_config: raise ValueError(f"{base_path} is empty or invalid")
                loaded_prompts['base'] = base_config

            for context_type in ['buy', 'sell', 'rebuy']: # <-- Add 'rebuy'
                specific_path = os.path.join(self.prompts_dir, f'{context_type}.yaml')
                if not os.path.exists(specific_path):
                    if context_type == 'rebuy':
                        logger.info(f"Optional prompt '{specific_path}' not found. Skipping.")
                        continue # It's okay if rebuy.yaml doesn't exist
                    else:
                         # Keep original error for required files
                         raise FileNotFoundError(f"{specific_path} is missing and required.")
                with open(specific_path, 'r', encoding='utf-8') as f:
                    content = remove_comments(f.read())
                    specific_config = yaml.safe_load(content)
                    if not specific_config: raise ValueError(f"{specific_path} is empty or invalid")
                    loaded_prompts[context_type] = {**base_config, **specific_config}

            logger.info(f"🧠 Successfully loaded prompt configurations from '{self.prompts_dir}'.")
            return loaded_prompts

        except FileNotFoundError as e:
            logger.critical(f"🧠 Prompt YAML file not found: {e}. Ensure '{self.prompts_dir}' contains base.yaml, buy.yaml, sell.yaml.", exc_info=True)
            raise
        except (yaml.YAMLError, Exception) as e:
            logger.critical(f"🧠 Error loading or parsing prompts: {e}", exc_info=True)
            raise

    def _set_log_verbose(self, verbose: bool):
        """Sets the verbosity of AI logging."""
        self.log_verbose = verbose
        logger.info(f"🧠 AI Decision Maker log verbosity set to: {self.log_verbose}")

    async def embed_text(self, text: str) -> Optional[list]:
        """
        [REFACTORED] Generates sentence embeddings for the given text asynchronously.
        Wraps the blocking SentenceTransformer call in asyncio.to_thread().
        """
        if not text:
            logger.warning("🧠 Attempted to embed empty text.")
            return None
        try:
            if self.log_verbose: logger.debug("🧠 AI Worker: Embedding text... (STARTING BLOCKING CALL)")
            embedding = await asyncio.to_thread(self.embedder.encode, text)
            if self.log_verbose: logger.debug("🧠 AI Worker: Embedding text... (BLOCKING CALL COMPLETE)")
            return embedding.tolist()
        except Exception as e:
            logger.error(f"🧠 Failed to embed text: '{text[:100]}...'. Error: {e}", exc_info=True)
            return None

    async def add_decision_snapshot_to_memory(self, snapshot_data: dict, decision_info: dict, raw_llm_response: Optional[str] = None):
        """
        [MODIFIED] Stores a snapshot of the market data, context, AI decision, and reasoning
        into the PostgreSQL `ai_decision_memory` table for future RAG retrieval.
        """
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
        
        # --- MODIFICATION START: Extract new fields ---
        creator_history = snapshot_data.get('creator_history_summary', 'N/A')
        max_price_sol = snapshot_data.get('max_price_sol', 'N/A')
        time_to_peak_minutes = snapshot_data.get('time_to_peak_minutes', 'N/A')
        drawdown_from_peak_pct = snapshot_data.get('drawdown_from_peak_pct', 'N/A')
        creator_rug_rate = snapshot_data.get('creator_rug_rate', 'N/A')

        uri_status = snapshot_data.get('uri_status', 'N/A')
        market_summary = snapshot_data.get('market_dynamics_summary_str', 'N/A')
        trade_history = snapshot_data.get('trade_history_summary', 'N/A')
        # Prioritize saving the raw response if provided.
        # The 'explanation' column will now store the RAW response for debugging.
        # The 'parsed_explanation' is still used for the summary snippet.
        parsed_explanation = decision_info.get('explanation')
        full_response_to_store = raw_llm_response if raw_llm_response else parsed_explanation # <-- Use raw_llm_response
        
        explanation_snippet = "N/A"
        placeholder_explanations = ["Explanation not found or invalid format.", "No explanation processed."]
        
        # Use the *parsed* explanation for the snippet
        if parsed_explanation and parsed_explanation not in placeholder_explanations:
            explanation_snippet = parsed_explanation[:150] + ('...' if len(parsed_explanation) > 150 else '')
        elif raw_llm_response:
             # Fallback for snippet if parsing failed but we have a raw response
            explanation_snippet = raw_llm_response.split('---', 1)[-1].strip()[:150] + '...'
        
        if not full_response_to_store or full_response_to_store in placeholder_explanations:
            full_response_to_store = None # Ensure we store NULL if it's empty/placeholder
            
        # --- [START OF FIX] ---
        # Helper function to safely format numeric values that might be None or "N/A"
        def safe_format(val, format_spec):
            if val is None or isinstance(val, str):
                return "N/A"
            try:
                return f"{float(val):{format_spec}}"
            except (ValueError, TypeError):
                return "N/A"

        # Apply safe formatting
        mcap_usd_str = safe_format(mcap_usd, ",.0f")
        volatility_str = safe_format(volatility, ".3f")
        drawdown_str = safe_format(drawdown_from_peak_pct, ".1f")
        max_price_str = safe_format(max_price_sol, ".9f")
        ttp_str = safe_format(time_to_peak_minutes, ".1f")
        # --- [END OF FIX] ---

        # --- MODIFICATION START ---
        # Update situation_summary to use new creator history
        situation_summary = (
            f"Situation Snapshot at {timestamp} for {mint} ({context} context):\n"
            f"Source: {source}, MCap (USD): ${mcap_usd_str}, Volatility: {volatility_str}\n"
            f"Token Age: {token_age} mins, URI: {uri_status}\n"
            f"Creator History: {creator_history} (Rug Rate: {creator_rug_rate})\n"
            f"Peak/Drawdown: Peak at {max_price_str} SOL ({ttp_str} mins). Current Drawdown: {drawdown_str}%.\n"
            f"Rug Score: {rug_score} (Trend: {rug_trend})\n"
            f"Social Score: {social_score} (Trend: {social_trend})\n"
            f"Market Dynamics Summary: {market_summary}\n"
            f"Trade History: {trade_history}\n"
            f"AI Decision: {decision_info.get('decision', 'N/A')} (Confidence: {decision_info.get('confidence', 'N/A')})\n"
            f"Reasoning Snippet: {explanation_snippet}\n"
        )
        # --- MODIFICATION END ---
        
        embedding = await self.embed_text(situation_summary)
        if not embedding:
            logger.warning(f"🧠 Failed to create embedding for decision snapshot (Mint: {mint}). Skipping memory add.")
            return

        snapshot_time_str = timestamp if isinstance(timestamp, str) else datetime.now(timezone.utc).isoformat()
        
        # --- MODIFICATION START: Update metadata_to_store ---
        metadata_to_store = {
            "mint": mint, "timestamp": snapshot_time_str, "decision_context": context, "source": source,
            "market_cap": float(mcap_usd) if mcap_usd is not None and not np.isnan(mcap_usd) and not isinstance(mcap_usd, str) else None,
            "volatility": float(volatility) if volatility is not None and not np.isnan(volatility) and not isinstance(volatility, str) else None,
            "token_age_minutes": float(token_age) if token_age is not None and not np.isnan(token_age) and not isinstance(token_age, str) else None,
            "creator_history_summary": str(creator_history),
            "uri_status": str(uri_status),
            "rugcheck_score": str(rug_score), "social_score": str(social_score), "rugcheck_trend": str(rug_trend),
            "social_score_trend": str(social_trend),
            
            # Add decision info (which now includes new fields)
            **decision_info, # Unpack decision, confidence, expected_return_1h_pct, etc.
            
            "model_name": self.model,

            # Add new computed metrics from snapshot_data
            "max_price_sol": snapshot_data.get('max_price_sol'),
            "max_mcap_sol": snapshot_data.get('max_mcap_sol'),
            "max_price_ts": snapshot_data.get('max_price_ts'),
            "time_to_peak_minutes": snapshot_data.get('time_to_peak_minutes'),
            "minutes_since_peak": snapshot_data.get('minutes_since_peak'),
            "drawdown_from_peak_pct": snapshot_data.get('drawdown_from_peak_pct'),
            "creator_total_launches": snapshot_data.get('creator_total_launches'),
            "creator_rug_count": snapshot_data.get('creator_rug_count'),
            "creator_rug_rate": snapshot_data.get('creator_rug_rate'),
            "creator_good_runs_count": snapshot_data.get('creator_good_runs_count'),
            "creator_avg_lifespan_minutes": snapshot_data.get('creator_avg_lifespan_minutes')
        }
        
        metadata_to_store = {k: v for k, v in metadata_to_store.items() if v is not None}
        metadata_json = json.dumps(metadata_to_store)

        query = """
            INSERT INTO ai_decision_memory (
                mint, evaluation_timestamp, decision_context, decision, confidence,
                model_name, explanation, situation_summary, embedding, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            );
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                await conn.execute(
                    query,
                    mint, datetime.fromisoformat(snapshot_time_str), context,
                    decision_info.get('decision'), int(decision_info.get('confidence', 0)),
                    self.model,
                    full_response_to_store, situation_summary, 
                    str(embedding), 
                    metadata_json
                )
            if self.log_verbose: logger.debug(f"🧠 Added decision snapshot to pgvector memory for {mint}")
        except Exception as e:
            logger.error(f"🧠 Failed to add decision snapshot to pgvector (Mint: {mint}): {e}", exc_info=True)

    async def retrieve_context(self, current_data: dict, top_k_actions: int = 5, top_k_market: int = 8) -> dict:
        """
        [REFACTORED V3 - CORRECTED] Retrieves relevant past contexts from pgvector.
        - Queries 'ai_decision_memory' for past actions.
        - Queries 'market_knowledge_base' using METADATA FILTERS for comparable market examples.
        - Fixes a SQL ambiguity error by casting parameter $3 to text.
        
        Args:
            current_data: The full data dictionary for the current token (used for filtering).
            top_k_actions: K for past actions.
            top_k_market: K for market examples.

        Returns:
            A dictionary containing formatted context strings.
        """
        default_return = {
            "actions": "No relevant past actions found in memory.",
            "market_examples": "No relevant market examples found in memory."
        }
        
        # --- MODIFICATION: Build situation query from current_data dict ---
        situation_query = (
            f"Analyze similar Solana meme coin situations: Context={current_data.get('decision_context', 'N/A')}, "
            f"Source={current_data.get('source', 'N/A')}, MCap approx ${current_data.get('market_cap', 0):,.0f}, "
            f"Volatility level {current_data.get('volatility', 0):.3f}, Token Age: {current_data.get('token_age_minutes', 'N/A')} mins. "
            f"Creator Rug Rate: {current_data.get('creator_rug_rate', 'N/A')}. "
            f"Drawdown: {current_data.get('drawdown_from_peak_pct', 0.0):.1f}%. "
            f"RSI: {current_data.get('latest_rsi', 'N/A')}."
        )
        # --- END MODIFICATION ---

        if not situation_query:
            logger.warning("🧠 Retrieve context called with empty situation query.")
            return default_return

        query_embedding = await self.embed_text(situation_query)
        if not query_embedding:
            logger.warning("🧠 Failed to create embedding for RAG query. Cannot retrieve context.")
            return default_return

        # Query 1: The bot's own past actions (pure vector search)
        query_actions = """
            SELECT
                situation_summary, metadata, embedding <=> $1 AS distance
            FROM ai_decision_memory
            ORDER BY embedding <=> $1
            LIMIT $2;
        """
        
        # --- [START OF FIX] ---
        # --- MODIFICATION: New Market Query with Metadata Filters ---
        query_market = """
            SELECT
                summary, metadata, embedding <=> $1 AS distance
            FROM market_knowledge_base
            WHERE
              -- Filter 1: Match the data source (PUMP or DEXSCREENER)
              -- [FIX] Cast $3 to text to resolve ambiguity when it is NULL
              ($3::text IS NULL OR (metadata->>'source') = $3::text)
              -- Filter 2: Match a market cap band (e.g., 0.5x to 2.0x current)
              AND ( (metadata->>'max_mcap_usd')::float BETWEEN $4 AND $5 )
            ORDER BY embedding <=> $1
            LIMIT $2;
        """
        # --- [END OF FIX] ---
        
        # Prepare filter parameters
        source_filter = current_data.get('source')
        current_mcap = current_data.get('market_cap', 0.0)
        # Define mcap bands (e.g., 0-10k, 10k-50k, 50k-250k, 250k+)
        if current_mcap < 10000:
            min_mcap, max_mcap = 0.0, 10000.0
        elif current_mcap < 50000:
            min_mcap, max_mcap = 10000.0, 50000.0
        elif current_mcap < 250000:
            min_mcap, max_mcap = 50000.0, 250000.0
        else:
            min_mcap, max_mcap = 250000.0, float('inf')

        try:
            results_actions, results_market = await asyncio.gather(
                self.db_client.pool.fetch(query_actions, str(query_embedding), top_k_actions),
                # Pass new filter params to the market query
                self.db_client.pool.fetch(query_market, str(query_embedding), top_k_market, source_filter, min_mcap, max_mcap)
            )

            # --- Process Past Actions (Unchanged) ---
            if not results_actions:
                if self.log_verbose: logger.debug("🧠 No relevant past actions found in 'ai_decision_memory'.")
            else:
                context_parts = ["--- Relevant Past Situations (Your Actions) ---"]
                for i, record in enumerate(results_actions):
                    context_parts.append(f"Past Case {i+1} (Similarity Distance: {record['distance']:.4f}):")
                    context_parts.append(record['situation_summary'].strip()) 
                    metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                    if metadata:
                        mcap_display = f"${metadata.get('market_cap', 0):,.0f}" if metadata.get('market_cap') else "N/A"
                        context_parts.append(
                            f"  (Metadata: Decision={metadata.get('decision', '?')}, "
                            f"Conf={metadata.get('confidence', '?')}, Context={metadata.get('decision_context', '?')}, "
                            f"MCap={mcap_display})"
                        )
                    context_parts.append("---")
                default_return["actions"] = "\n".join(context_parts)


            # --- Process Market Examples (Unchanged, but benefits from better query) ---
            if not results_market:
                if self.log_verbose: logger.debug(f"🧠 No relevant market examples found in 'market_knowledge_base' (with filters).")
            else:
                context_parts = ["--- Relevant Market Examples (Other Tokens) ---"]
                for i, record in enumerate(results_market):
                    context_parts.append(f"Market Example {i+1} (Similarity Distance: {record['distance']:.4f}):")
                    context_parts.append(record['summary'].strip()) 
                    metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                    if metadata:
                        context_parts.append(
                            f"  (Metadata: Outcome={metadata.get('reason', '?')}, "
                            f"Creator={metadata.get('creator', '?')}, "
                            f"MaxMCap={metadata.get('max_mcap', 'N/A')} SOL)"
                        )
                    context_parts.append("---")
                default_return["market_examples"] = "\n".join(context_parts)
            
            return default_return

        except Exception as e:
            logger.error(f"🧠 Error querying pgvector for RAG context: {e}", exc_info=True)
            return {
                "actions": "Error retrieving past actions from memory.",
                "market_examples": "Error retrieving market examples from memory."
            }

    async def query_llm(self, prompt: str) -> str:
        """
        [REFACTORED] Sends the fully formatted prompt to the Ollama LLM asynchronously
        by wrapping the blocking 'ollama.chat' call in asyncio.to_thread().
        """
        if self.log_verbose: logger.debug(f"🧠 Sending prompt to LLM '{self.model}' (approx {len(prompt)} chars)")

        try:
            if self.log_verbose: 
                logger.debug("🧠 AI Worker: Querying LLM... (STARTING BLOCKING CALL)")
                #logger.debug(f"🧠 LLM Prompt Preview:\n{prompt[:11000]}{'...' if len(prompt) > 11000 else ''}")
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                options={'temperature': 0.3},
                messages=[{'role': 'user', 'content': prompt}],
                format="json"  # <-- ENFORCE JSON OUTPUT
            )
            if self.log_verbose: logger.debug("🧠 AI Worker: Querying LLM... (BLOCKING CALL COMPLETE)")
            
            # The result is now a JSON string
            result = response['message']['content'].strip()
            
            if self.log_verbose:
                log_result_snippet = result[:11000] + ('...' if len(result) > 11000 else '')
                logger.debug(f"🧠 LLM JSON Response received:\n{log_result_snippet}")
            return result

        except Exception as e:
            logger.error(f"🧠 Ollama query failed using model '{self.model}': {e}", exc_info=True)
            # Return a fallback JSON error string
            return json.dumps({
                "decision": "HOLD",
                "confidence": 0,
                "expected_return_1h_pct": 0.0,
                "expected_return_6h_pct": 0.0,
                "suggested_size_pct": 0.0,
                "primary_risk": "INTERNAL_ERROR",
                "explanation": f"AI decision unavailable due to LLM query error: {e}"
            })

    async def get_trade_advice(self, current_data: dict, include_explanation: bool = True) -> dict:
        """
        [REFACTORED V7 - CORRECTED]
        Orchestrates the process of getting trade advice from the LLM.
        - Passes current_data to retrieve_context for filtered RAG.
        - Parses the new, richer JSON response.
        - [FIX] Sanitizes prompt_data to handle None values before formatting.
        """
        required_keys = ['mint', 'source', 'price', 'market_cap', 'volatility', 'decision_context', 'token_age_minutes']
        missing_keys = [k for k in required_keys if k not in current_data or current_data[k] is None]
        if missing_keys:
             logger.error(f"🧠 Missing essential keys for AI advice: {missing_keys}. Input data: {list(current_data.keys())}")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Incomplete essential data: Missing {missing_keys}"}

        # --- 1. Determine Context and Load Prompt Snippets ---
        decision_context = current_data['decision_context']

        if decision_context == "INITIAL BUY":
            context_key = 'buy'
        elif decision_context == "REBUY":
            context_key = 'rebuy'
        elif decision_context == "SELL/HOLD":
            context_key = 'sell'
        else:
            logger.warning(f"🧠 Unknown decision context '{decision_context}'. Defaulting to SELL/HOLD logic.")
            context_key = 'sell'
            decision_context = "SELL/HOLD" # Normalize

        if context_key == 'rebuy' and 'rebuy' not in self.prompts:
            logger.warning("🧠 'rebuy.yaml' not loaded. Falling back to 'buy.yaml' for REBUY context.")
            context_key = 'buy'
            
        prompt_config = self.prompts.get(context_key, self.prompts['sell']) # Fallback to 'sell'
        base_prompts = self.prompts.get('base')
        if not base_prompts:
            logger.critical("🧠 CRITICAL: 'base.yaml' prompt snippets not found. Cannot build prompt.")
            return {"decision": "HOLD", "confidence": 0, "explanation": "Internal Error: Base prompts missing."}

        # --- 2. Generate RAG Context ---
        if self.log_verbose: logger.debug(f"🧠 Generating RAG context for {current_data['mint']}...")
        rag_context = await self.retrieve_context(current_data) # Pass the full dict

        # --- 3. Format Dynamic Data Blocks ---
        market_dynamics_formatted = "Market dynamics data not available or source unknown."
        source = current_data['source']
        try:
            if source == 'PUMP':
                market_dynamics_formatted = prompt_config['market_dynamics_template_pump'].format(**current_data)
            elif source == 'DEXSCREENER':
                market_dynamics_formatted = prompt_config['market_dynamics_template_dex'].format(**current_data)
        except KeyError as e:
            logger.error(f"🧠 KeyError formatting market dynamics for {source}: Missing key '{e}'.")
            market_dynamics_formatted = f"Error formatting market dynamics for {source} (KeyError: {e})."
        
        # --- 4. Assemble Full Prompt Data ---
        prompt_data = {**current_data} 
        prompt_data.update({
            'rag_context_actions': rag_context['actions'],
            'rag_context_market': rag_context['market_examples'],
            'market_dynamics_formatted': market_dynamics_formatted,
            'source_explanation': prompt_config.get('source_explanation', ''),
            'market_cap_guidance': prompt_config.get('market_cap_guidance', '').format(
                default_marketcap_threshold=self.config.get('DEFAULT_MARKETCAP_THRESHOLD', 14000),
                min_marketcap_threshold=self.config.get('MIN_MARKETCAP_THRESHOLD', 4000)
            ),
            'context_specific_rules': prompt_config.get('context_specific_rules', ''),
            'default_marketcap_threshold': self.config.get('DEFAULT_MARKETCAP_THRESHOLD', 14000),
            'min_marketcap_threshold': self.config.get('MIN_MARKETCAP_THRESHOLD', 4000),
        })

        # --- [START OF FIX] ---
        # 4b. Sanitize None values that require numeric formatting in the prompt
        # We replace None with 0.0 or "N/A" depending on what the prompt expects.
        # For numeric formats (like :.9f), we MUST use a number (0.0).
        # For string formats, "N/A" is fine.
        
        # Keys that are formatted as numbers (e.g., :.9f, :.1f, :.2f)
        numeric_format_keys = [
            'price', 'market_cap', 'volatility', 'max_price_sol', 
            'time_to_peak_minutes', 'minutes_since_peak', 'drawdown_from_peak_pct',
            'dex_price_change_m5', 'dex_volume_m5'
        ]
        # Keys that are formatted as strings or integers (e.g., {})
        string_format_keys = [
            'latest_rsi', 'latest_ema_fast', 'latest_ema_slow',
            'token_age_minutes', # This one is formatted as {token_age_minutes}
            'pump_price_change_1m', 'pump_volume_velocity_1m', 'pump_tick_frequency_1m',
            'dex_buys_m5', 'dex_sells_m5', 'dex_price_trend_15m', 
            'dex_volume_trend_15m', 'dex_liquidity_trend_30m'
        ]

        for key in numeric_format_keys:
            if prompt_data.get(key) is None:
                prompt_data[key] = 0.0 # Use 0.0 for numeric formatting

        for key in string_format_keys:
            if prompt_data.get(key) is None:
                prompt_data[key] = "N/A" # Use "N/A" for string formatting

        # Ensure creator_history_summary is at least an empty string
        if prompt_data.get('creator_history_summary') is None:
            prompt_data['creator_history_summary'] = "N/A"
            
        # Ensure data completeness notes are present
        if prompt_data.get('data_completeness_notes') is None:
            prompt_data['data_completeness_notes'] = "N/A"

        # --- 5. Dynamically Build the Final Prompt (Context -> Data -> Rules -> JSON Format) ---
        try:
            prompt_sections = []
            
            # 1. Task Definition (from buy.yaml, etc.)
            prompt_sections.append(prompt_config['task_definition'].format(**prompt_data))
            
            # 2. Data Blocks (from base.yaml)
            prompt_sections.append(base_prompts['current_token_data_header'].format(**prompt_data))
            prompt_sections.append(base_prompts['metadata_context_section'].format(**prompt_data))
            
            # This section now contains the new peak/drawdown metrics
            prompt_sections.append(base_prompts['core_metrics_section'].format(**prompt_data)) 
            
            prompt_sections.append(base_prompts['risk_assessment_section'].format(**prompt_data))
            prompt_sections.append(base_prompts['market_dynamics_header'].format(**prompt_data))
            prompt_sections.append(base_prompts['trade_history_section'].format(**prompt_data))
            
            # 3. Rules & RAG Context (from base.yaml)
            prompt_sections.append(base_prompts['key_decision_rules_section'].format(**prompt_data))
            
            # 4. FINAL INSTRUCTION: The JSON format (from base.yaml)
            prompt_sections.append(base_prompts['json_output_format'].format(**prompt_data))
            
            final_prompt = "\n\n".join(prompt_sections)
            
            if self.log_verbose:
                logger.debug(f"🧠 Final dynamic prompt for {current_data['mint']}:\n{final_prompt}")
                
        except (KeyError, TypeError) as e: # Catch TypeError as well
             logger.critical(f"🧠 CRITICAL: Missing key or Type error '{e}' during prompt final formatting.")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed on key/type '{e}'."}
        except Exception as e:
             logger.critical(f"🧠 CRITICAL: Unexpected error during prompt final formatting: {e}", exc_info=True)
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed unexpectedly."}

        # --- 6. Query LLM and Process Response ---
        llm_response_string = await self.query_llm(final_prompt) # This is now a JSON string

        if self.log_verbose:
            logger.debug(f"🧠 LLM Raw JSON Response for {current_data['mint']} ({decision_context}): {llm_response_string}")

        # Parse the NEW, richer JSON response
        parsed_decision_rich = self._parse_llm_json_response(llm_response_string, include_explanation)

        if self.log_verbose:
            log_explanation_snippet = parsed_decision_rich['explanation'][:200] + ('...' if len(parsed_decision_rich['explanation']) > 200 else '') if include_explanation and parsed_decision_rich.get('explanation') else "(Explanation Skipped or Missing)"
            logger.debug(f"🧠 AI Advice for {current_data['mint']} ({decision_context}): {parsed_decision_rich['decision']} "
                        f"(Confidence: {parsed_decision_rich['confidence']}) - Risk: {parsed_decision_rich.get('primary_risk', 'N/A')} "
                        f"- Return(1h): {parsed_decision_rich.get('expected_return_1h_pct', 'N/A')}%")

        # Save the new decision (and its rich explanation) to RAG memory
        # We pass the full current_data (with all computed metrics)
        # and the full parsed_decision_rich (with all LLM outputs)
        await self.add_decision_snapshot_to_memory(current_data, parsed_decision_rich, raw_llm_response=llm_response_string)

        return parsed_decision_rich

    def _parse_llm_json_response(self, llm_response_string: str, parse_explanation: bool = True) -> dict:
        """
        Parses the simplified 3-key JSON response from the LLM.
        [MODIFIED] Now handles string-based confidence values (e.g., "Low", "High").
        """
        
        # Map for string-based confidence values to integers
        CONFIDENCE_STRING_MAP = {
            "very low": 10,
            "low": 25,
            "moderate": 50,
            "medium": 50,
            "average": 50,
            "reasonable": 60,
            "good": 75,
            "strong": 85,
            "high": 90,
            "very high": 95,
            "extreme": 100,
            "certain": 100,
            "none": 0,
            "zero": 0,
        }

        default_reasoning = "Explanation not found or invalid JSON format."
        default_output = {
            "decision": "HOLD", 
            "confidence": 0, 
            "expected_return_1h_pct": 0.0,
            "expected_return_6h_pct": 0.0,
            "suggested_size_pct": 0.0,
            "primary_risk": "UNKNOWN",
            "explanation": "No explanation processed." if not parse_explanation else default_reasoning
        }

        try:
            # --- FIX: Replaced re.sub with simple string methods ---
            llm_response_string = llm_response_string.strip()
            if llm_response_string.startswith("```json"):
                llm_response_string = llm_response_string[7:]
            if llm_response_string.endswith("```"):
                llm_response_string = llm_response_string[:-3]
            llm_response_string = llm_response_string.strip()
            # --- END FIX ---

            data = json.loads(llm_response_string)
            if not isinstance(data, dict):
                raise TypeError("LLM returned valid JSON, but it was not a dictionary.")

            # --- [ NEW SCHEMA PARSING ] ---
            decision = str(data.get("decision", "HOLD")).upper()
            
            # --- [ MODIFIED CONFIDENCE PARSING ] ---
            raw_confidence = data.get("confidence")
            confidence = 0 # Default

            if isinstance(raw_confidence, int):
                confidence = raw_confidence
            elif isinstance(raw_confidence, float):
                confidence = int(raw_confidence)
            elif isinstance(raw_confidence, str):
                confidence_str_low = raw_confidence.strip().lower()
                if confidence_str_low in CONFIDENCE_STRING_MAP:
                    confidence = CONFIDENCE_STRING_MAP[confidence_str_low]
                    logger.debug(f"🧠 Parser: Mapped confidence string '{raw_confidence}' to {confidence}.")
                else:
                    try:
                        # Try to cast string-as-number (e.g., "80")
                        confidence = int(float(confidence_str_low.strip('% '))) # Handle "80", "80.0", "80%", " 80 "
                    except (ValueError, TypeError):
                        logger.warning(f"🧠 Parser: Could not parse string confidence '{raw_confidence}'. Defaulting to 0.")
                        confidence = 0
            elif raw_confidence is None:
                 logger.warning(f"🧠 Parser: Confidence was 'null' in JSON response. Defaulting to 0.")
                 confidence = 0
            else:
                 logger.warning(f"🧠 Parser: Confidence was of an unexpected type '{type(raw_confidence)}'. Defaulting to 0.")
                 confidence = 0
            # --- [ END MODIFIED CONFIDENCE PARSING ] ---

            explanation = default_reasoning
            if parse_explanation:
                # Use the new 'explanation' key
                reasoning_str = data.get("explanation") # <-- KEY CHANGED
                if reasoning_str and isinstance(reasoning_str, str):
                    explanation = reasoning_str
                # Fallback for old key, just in case
                elif data.get("full_reasoning") and isinstance(data.get("full_reasoning"), str):
                    explanation = data.get("full_reasoning")
            
            # --- MODIFICATION: Parse new fields ---
            def parse_numeric_field(key: str, default_val: float = 0.0) -> float:
                val = data.get(key)
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    try:
                        return float(val.strip('% '))
                    except (ValueError, TypeError):
                        return default_val
                return default_val

            expected_return_1h_pct = parse_numeric_field("expected_return_1h_pct")
            expected_return_6h_pct = parse_numeric_field("expected_return_6h_pct")
            suggested_size_pct = parse_numeric_field("suggested_size_pct")
            
            primary_risk = str(data.get("primary_risk", "UNKNOWN")).upper()
            # --- END MODIFICATION ---

            # Ensure values are sane
            valid_decisions = ["BUY", "SELL", "HOLD", "AGGRESSIVE_BUY", "REBUY", "REDUCE"]
            if decision not in valid_decisions:
                logger.warning(f"🧠 Parser: LLM returned invalid decision '{decision}'. Defaulting to HOLD.")
                decision = "HOLD"

            # --- MODIFICATION: Return new rich dictionary ---
            return {
                "decision": decision, 
                "confidence": confidence, 
                "expected_return_1h_pct": expected_return_1h_pct,
                "expected_return_6h_pct": expected_return_6h_pct,
                "suggested_size_pct": max(0, min(100, suggested_size_pct)), # Clamp 0-100
                "primary_risk": primary_risk,
                "explanation": explanation
            }
            # --- END MODIFICATION ---

        except json.JSONDecodeError as e:
            logger.error(f"🧠 Parser: Failed to decode LLM JSON response. Error: {e}. Response: {llm_response_string[:500]}...")
            return default_output
        except (TypeError, ValueError) as e:
            logger.error(f"🧠 Parser: Error parsing fields from LLM JSON. Error: {e}. Data: {llm_response_string[:500]}...")
            return default_output
    
    # --- [ DELETE THE OLD PARSERS ] ---
    # def _parse_llm_response_structured(self, ...):
    # def _parse_llm_response_fallback(self, ...):

    def _parse_llm_response_structured(self, llm_response: str, parse_explanation: bool = True) -> dict:
        """
        Parses the LLM response (Unchanged).
        """
        decision, confidence, explanation = "HOLD", 0, "No explanation processed." if not parse_explanation else "Explanation not found or invalid format."
        if not llm_response:
            logger.warning("🧠 LLM response parser received empty string.")
            return {"decision": decision, "confidence": confidence, "explanation": explanation}
        
        lines = llm_response.strip().split('\n', 2)
        # This new regex is more robust. It ignores any combination of whitespace,
        # asterisks (*), or brackets ([]) around the core components.
        strict_match = re.match(
            r"^\s*[\*\[\]]*\s*(BUY|SELL|HOLD|REBUY)\s*[\*\[\]]*\s*:\s*[\*\[\]]*\s*(\d{1,3})\s*[\*\[\]]*\s*$",
            lines[0],
            re.IGNORECASE
        )

        if strict_match:
            decision = strict_match.group(1).upper()
            try:
                confidence = max(0, min(100, int(strict_match.group(2))))
                if self.log_verbose: logger.debug(f"🧠 Parser: Matched strict format '{decision}:{confidence}' on first line.")
                if parse_explanation:
                    if len(lines) > 2 and lines[1].strip() == '---':
                        explanation = lines[2].strip()
                        if self.log_verbose: logger.debug("🧠 Parser: Extracted explanation following strict format and separator.")
                    elif len(lines) == 2 and lines[1].strip() == '---':
                        explanation = "(No explanation text provided after separator)"
                        if self.log_verbose: logger.debug("🧠 Parser: Strict format OK, separator found, but no explanation text.")
                    elif len(lines) > 1:
                        explanation = "\n".join(lines[1:]).strip()
                        logger.warning("🧠 Parser: Strict format OK, but separator '---' missing. Taking rest as explanation.")
                    else: 
                        explanation = "(No explanation provided)"
                        if self.log_verbose: logger.debug("🧠 Parser: Strict format OK, but no subsequent lines for explanation.")
                return {"decision": decision, "confidence": confidence, "explanation": explanation}
            except ValueError:
                logger.warning(f"🧠 Parser: Matched strict format, but failed to parse confidence '{strict_match.group(2)}'. Falling back.")
        else:
            logger.warning(f"🧠 Parser: Strict format 'DECISION:CONFIDENCE' not found on line 1: '{lines[0]}'. Falling back.")

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
            if self.log_verbose: logger.debug(f"🧠 Fallback Parser: Found decision '{decision}' via strict line search.")
        else:
            decision_match_lenient_line = re.search(r"^.*?\W*Decision\W*:\s*\**?(BUY|SELL|HOLD)\**?", llm_response, re.IGNORECASE | re.MULTILINE)
            if decision_match_lenient_line:
                decision = decision_match_lenient_line.group(1).upper()
                if self.log_verbose: logger.debug(f"🧠 Fallback Parser: Found decision '{decision}' via lenient line search.")
            elif re.search(r"^\s*SELL\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or ("SELL" in response_upper and "BUY" not in response_upper and "HOLD" not in response_upper):
                decision = "SELL"
                if self.log_verbose: logger.debug("🧠 Fallback Parser: Deduced 'SELL' via keyword dominance.")
            elif re.search(r"^\s*BUY\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or ("BUY" in response_upper and "SELL" not in response_upper and "HOLD" not in response_upper):
                decision = "BUY"
                if self.log_verbose: logger.debug("🧠 Fallback Parser: Deduced 'BUY' via keyword dominance.")
            elif re.search(r"^\s*HOLD\s*$", llm_response, re.IGNORECASE | re.MULTILINE):
                decision = "HOLD"
                if self.log_verbose: logger.debug("🧠 Fallback Parser: Found 'HOLD' on its own line.")
            else:
                 if self.log_verbose: logger.debug(f"🧠 Fallback Parser: No clear decision keyword found. Defaulting to '{decision}'.")

        conf_match_strict_line = re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1,3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
        if conf_match_strict_line:
            try: 
                confidence = max(0, min(100, int(conf_match_strict_line.group(1))))
                if self.log_verbose: logger.debug(f"🧠 Fallback Parser: Found confidence '{confidence}' via strict line search.")
            except ValueError: logger.warning(f"🧠 Fallback Parser: Strict confidence line found, but failed to parse number '{conf_match_strict_line.group(1)}'.")
        else:
            conf_match_lenient_line = re.search(r"^.*?\W*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1.3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
            if conf_match_lenient_line:
                 try: 
                     confidence = max(0, min(100, int(conf_match_lenient_line.group(1))))
                     if self.log_verbose: logger.debug(f"🧠 Fallback Parser: Found confidence '{confidence}' via lenient line search.")
                 except ValueError: logger.warning(f"🧠 Fallback Parser: Lenient confidence line found, but failed to parse number '{conf_match_lenient_line.group(1)}'.")
            else:
                 conf_fallback_anywhere = re.search(r"Confidence.*?[:\s](\d{1,3})", llm_response, re.IGNORECASE | re.DOTALL)
                 if conf_fallback_anywhere:
                     try: 
                         confidence = max(0, min(100, int(conf_fallback_anywhere.group(1))))
                         if self.log_verbose: logger.debug(f"🧠 Fallback Parser: Found confidence '{confidence}' via general fallback search.")
                     except ValueError: logger.warning(f"🧠 Fallback Parser: General confidence search found, but failed to parse number '{conf_fallback_anywhere.group(1)}'.")
                 else:
                     if self.log_verbose: logger.debug(f"🧠 Fallback Parser: No confidence value found. Defaulting to {confidence}.")

        explanation_match = re.search(r"^\W*\*?\s*(?:Explanation|Reasoning|Justification)\s*\*?\W*:\s*(.*)", llm_response, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if explanation_match:
            explanation_text = explanation_match.group(1).strip()
            explanation_text = re.sub(r"^\W*\*?\s*Decision\s*\*?\W*:.*?\n?", "", explanation_text, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            explanation_text = re.sub(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:.*?\n?", "", explanation_text, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            explanation = explanation_text
            if self.log_verbose: logger.debug("🧠 Fallback Parser: Found explanation using header keyword.")
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
                    if self.log_verbose: logger.debug("🧠 Fallback Parser: Found explanation by splitting after last Decision/Confidence marker.")
                else:
                    explanation = "" 
                    if self.log_verbose: logger.debug("🧠 Fallback Parser: Decision/Confidence markers found, but no subsequent text for explanation.")

        explanation = re.sub(r'\n{3,}', '\n\n', explanation).strip()
        if not explanation: explanation = "(Explanation could not be extracted)"
        return {"decision": decision, "confidence": confidence, "explanation": explanation}