# ai_decision_maker.py
import ollama
import chromadb
from sentence_transformers import SentenceTransformer
from bot_logger import logger
# Assuming config values like thresholds are imported correctly
from config.config import (
    DEFAULT_SOCIAL_SCORE_THRESHOLD, DEFAULT_MARKETCAP_THRESHOLD,
    MIN_MARKETCAP_THRESHOLD, MIN_VOLATILITY
)
import json
import re
import yaml # For loading YAML prompts
import os # For path manipulation
from datetime import datetime, timezone
import numpy as np # For NaN check
import pandas as pd # For NaT check
from typing import Dict, Any, Optional # For type hinting

# Define the path to the prompts directory relative to this script
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')

class AIDecisionMaker:
    """
    Manages communication with an LLM (via Ollama) to get trading advice (BUY, SELL, HOLD)
    for Solana meme coins based on provided market data, risk scores, trade history,
    and context retrieved from a vector database (ChromaDB) using RAG.
    """

    def __init__(self, model_name: str = 'llama3:latest', embedding_model: str = 'all-MiniLM-L6-v2', prompts_dir: str = PROMPTS_DIR):
        """
        Initializes the AIDecisionMaker.

        Args:
            model_name (str): The name of the Ollama model to use (e.g., 'llama3:latest').
            embedding_model (str): The name of the Sentence Transformer model for embeddings.
            prompts_dir (str): The directory containing the YAML prompt configuration files.
        """
        self.model = model_name
        self.prompts_dir = prompts_dir
        self.prompts = self._load_prompts() # Load prompts from YAML files

        try:
            # Initialize Sentence Transformer model for creating embeddings
            self.embedder = SentenceTransformer(embedding_model)
            logger.info(f"Sentence Transformer embedding model '{embedding_model}' loaded.")
        except Exception as e:
            logger.critical(f"Failed to load Sentence Transformer model '{embedding_model}': {e}", exc_info=True)
            raise

        try:
            # Initialize ChromaDB client for RAG context memory
            # Uses a persistent client, storing data in "./chroma_db_aidm"
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db_aidm")
            # Get or create the collection (vector database table)
            # Increment version number if schema/data meaning changes significantly
            self.collection = self.chroma_client.get_or_create_collection(name="trading_decision_memory_v3")
            logger.info("ChromaDB client initialized for AI Decision Maker memory.")
        except Exception as e:
            logger.critical(f"Failed to initialize ChromaDB: {e}", exc_info=True)
            raise

        logger.info(f"AI Decision Maker initialized with Ollama model: {self.model}")

    def _load_prompts(self) -> Dict[str, Any]:
        """Loads prompt templates and configurations from YAML files."""
        loaded_prompts = {}
        try:
            # Load the base template
            with open(os.path.join(self.prompts_dir, 'base.yaml'), 'r', encoding='utf-8') as f:
                base_config = yaml.safe_load(f)
                if not base_config: raise ValueError("base.yaml is empty or invalid")
                loaded_prompts['base'] = base_config

            # Load context-specific configurations (BUY and SELL)
            for context_type in ['buy', 'sell']:
                with open(os.path.join(self.prompts_dir, f'{context_type}.yaml'), 'r', encoding='utf-8') as f:
                    specific_config = yaml.safe_load(f)
                    if not specific_config: raise ValueError(f"{context_type}.yaml is empty or invalid")
                    # Merge base config elements with specific config for convenient access
                    # Specific config keys will override base keys if they exist in both
                    loaded_prompts[context_type] = {**base_config, **specific_config}

            logger.info("Successfully loaded prompt configurations from YAML files.")
            return loaded_prompts

        except FileNotFoundError as e:
            logger.critical(f"Prompt YAML file not found: {e}. Ensure '{self.prompts_dir}' contains base.yaml, buy.yaml, sell.yaml.", exc_info=True)
            raise
        except yaml.YAMLError as e:
            logger.critical(f"Error parsing prompt YAML file: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.critical(f"Unexpected error loading prompts: {e}", exc_info=True)
            raise

    def _embed_text(self, text: str) -> Optional[list]:
        """
        Generates sentence embeddings for the given text.

        Args:
            text (str): The input text to embed.

        Returns:
            Optional[list]: A list representing the embedding, or None if embedding fails.
        """
        if not text:
            logger.warning("Attempted to embed empty text.")
            return None
        try:
            # Use the loaded Sentence Transformer model to encode the text
            embedding = self.embedder.encode(text)
            # Convert the numpy array to a list for ChromaDB compatibility
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: '{text[:100]}...'. Error: {e}", exc_info=True)
            return None

    def add_decision_snapshot_to_memory(self, snapshot_data: dict, decision_info: dict):
        """
        Stores a snapshot of the market data, context, AI decision, and reasoning
        into the ChromaDB vector store for future RAG retrieval.

        Args:
            snapshot_data (dict): The input data dictionary used for the decision.
                                  (Should match the structure prepared by `fetch_comprehensive_token_data`).
            decision_info (dict): The dictionary containing the AI's 'decision', 'confidence', and 'explanation'.
        """
        # Extract key metrics for the summary document
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

        # Include explanation snippet in the summary for embedding, if available and meaningful
        explanation_snippet = "N/A"
        full_explanation = decision_info.get('explanation')
        placeholder_explanations = ["Explanation not found or invalid format.", "No explanation processed."]
        if full_explanation and full_explanation not in placeholder_explanations:
            explanation_snippet = full_explanation[:150] + ('...' if len(full_explanation) > 150 else '')
        else:
            full_explanation = None # Don't store placeholder in metadata

        # Create a concise summary string - THIS is what gets embedded
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

        # Generate the embedding for the summary
        embedding = self._embed_text(situation_summary)
        if not embedding:
            logger.warning(f"Failed to create embedding for decision snapshot (Mint: {mint}). Skipping memory add.")
            return

        # Ensure timestamp is a string for ID generation
        snapshot_time_str = timestamp if isinstance(timestamp, str) else datetime.now(timezone.utc).isoformat()
        # Create a unique ID for the ChromaDB entry
        snapshot_id = f"{snapshot_time_str}_{mint}"

        # Prepare metadata to store alongside the embedding (includes potentially long explanation)
        # Ensure values are JSON serializable (float, int, str, bool, None)
        metadata_to_store = {
            "mint": mint,
            "timestamp": snapshot_time_str,
            "decision_context": context,
            "source": source,
            "market_cap": float(mcap_usd) if mcap_usd is not None and not np.isnan(mcap_usd) else None,
            "volatility": float(volatility) if volatility is not None and not np.isnan(volatility) else None,
            "token_age_minutes": float(token_age) if token_age is not None and not np.isnan(token_age) else None,
            "is_prolific_creator": bool(creator_prolific),
            "uri_status": str(uri_status),
            "rugcheck_score": str(rug_score), # Store scores as string if they can be 'N/A'
            "social_score": str(social_score),
            "rugcheck_trend": str(rug_trend),
            "social_score_trend": str(social_trend),
            "decision": decision_info.get('decision'),
            "confidence": int(decision_info.get('confidence', 0)),
            "explanation": full_explanation # Store the full explanation here
        }
        # Filter out keys with None values to keep metadata clean
        metadata_to_store = {k: v for k, v in metadata_to_store.items() if v is not None}

        try:
            # Add the data to the ChromaDB collection
            self.collection.add(
                documents=[situation_summary], # The embedded text
                embeddings=[embedding],        # The vector embedding
                ids=[snapshot_id],             # The unique ID
                metadatas=[metadata_to_store]  # Associated structured data
            )
            logger.debug(f"Added decision snapshot to memory: ID {snapshot_id}")
        except Exception as e:
            logger.error(f"Failed to add decision snapshot to ChromaDB (ID: {snapshot_id}): {e}", exc_info=True)

    def retrieve_context(self, situation_query: str, top_k: int = 5) -> str:
        """
        Retrieves relevant past decision snapshots from ChromaDB based on semantic similarity
        to the current situation query.

        Args:
            situation_query (str): A natural language description of the current trading situation.
            top_k (int): The maximum number of relevant past situations to retrieve.

        Returns:
            str: A formatted string containing the retrieved past situations, suitable for inclusion in the LLM prompt.
                 Returns an error/info message if retrieval fails or no context is found.
        """
        if not situation_query:
            logger.warning("Retrieve context called with empty situation query.")
            return "No situation query provided for context retrieval."

        # Generate embedding for the query
        query_embedding = self._embed_text(situation_query)
        if not query_embedding:
            logger.warning("Failed to create embedding for RAG query. Cannot retrieve context.")
            return "Embedding failed for query. Cannot retrieve context."

        try:
            # Query the ChromaDB collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            # Check if results are valid
            if not results or not results.get('documents') or not results['documents'][0]:
                logger.debug("No relevant past decision snapshots found in memory for query.")
                return "No relevant past decision snapshots found."

            # Format the retrieved documents and metadata for the prompt
            context_parts = ["--- Relevant Past Situations & Decisions ---"]
            doc_list = results['documents'][0]
            meta_list = results.get('metadatas', [[]])[0] # Handle case where metadata might be missing

            for i, doc in enumerate(doc_list):
                context_parts.append(f"Past Case {i+1}:")
                context_parts.append(doc.strip()) # doc is the summary string stored earlier

                # Add relevant metadata to provide more context
                if i < len(meta_list):
                    metadata = meta_list[i]
                    mcap_display = f"${metadata.get('market_cap', 0):,.0f}" if metadata.get('market_cap') else "N/A"
                    # Example: Add outcome if you store it later (e.g., via a feedback loop)
                    # outcome_info = f", Outcome Profit: {metadata.get('profit', 'N/A')}" if 'profit' in metadata else ""
                    outcome_info = "" # Placeholder for now
                    context_parts.append(
                        f"  (Metadata: Decision={metadata.get('decision', '?')}, "
                        f"Conf={metadata.get('confidence', '?')}, Context={metadata.get('decision_context', '?')}, "
                        f"MCap={mcap_display}{outcome_info})"
                    )
                context_parts.append("---")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error querying ChromaDB for RAG context: {e}", exc_info=True)
            return "Error retrieving context from memory."

    def query_llm(self, prompt: str) -> str:
        """
        Sends the fully formatted prompt to the Ollama LLM and returns the response.

        Args:
            prompt (str): The complete prompt string.

        Returns:
            str: The raw response string from the LLM, or a structured error message on failure.
        """
        # Log a snippet of the potentially very long prompt
        log_prompt_snippet = prompt[:11000] + ('...' if len(prompt) > 11000 else '')
        logger.debug(f"Sending prompt to LLM '{self.model}' (approx {len(prompt)} chars):\n{log_prompt_snippet}")

        try:
            # Use Ollama client library to interact with the LLM
            response = ollama.chat(
                model=self.model,
                # Low temperature for more deterministic, analytical responses
                options={'temperature': 0.1},
                messages=[{'role': 'user', 'content': prompt}]
            )
            result = response['message']['content'].strip()

            # Log a snippet of the response
            log_result_snippet = result[:11000] + ('...' if len(result) > 11000 else '')
            logger.debug(f"LLM Response received:\n{log_result_snippet}")
            return result

        except Exception as e:
            # Log the error and return a default structured response indicating failure
            logger.error(f"Ollama query failed using model '{self.model}': {e}", exc_info=True)
            return "HOLD:0\n---\nAI decision unavailable due to LLM query error."

    def get_trade_advice(self, current_data: dict, include_explanation: bool = True) -> dict:
        """
        Orchestrates the process of getting trade advice from the LLM.

        1. Validates input data.
        2. Selects the appropriate prompt configuration (BUY/SELL).
        3. Creates a query for RAG context retrieval.
        4. Retrieves relevant past situations using RAG.
        5. Formats market dynamics data based on the source (PUMP/DEXSCREENER).
        6. Assembles the final prompt using the base template and context-specific data.
        7. Queries the LLM.
        8. Parses the LLM response.
        9. Stores the decision snapshot in memory.
        10. Returns the parsed decision.

        Args:
            current_data (dict): A dictionary containing all necessary data points about the token
                                 (metadata, metrics, risk scores, history, etc.). This structure
                                 is expected to be generated by `fetch_comprehensive_token_data`.
            include_explanation (bool): Whether to parse and include the explanation part
                                        of the LLM response. Setting to False saves parsing time
                                        if only the decision/confidence is needed immediately.

        Returns:
            dict: A dictionary containing the 'decision' (str: BUY/SELL/HOLD),
                  'confidence' (int: 0-100), and 'explanation' (str).
                  Returns a default HOLD decision with error message on critical failures.
        """
        # 1. Validate required input data keys
        required_keys = ['mint', 'source', 'price', 'market_cap', 'volatility', 'decision_context', 'token_age_minutes']
        missing_keys = [k for k in required_keys if k not in current_data or current_data[k] is None]
        if missing_keys:
             logger.error(f"Missing essential keys for AI advice: {missing_keys}. Input data: {list(current_data.keys())}")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Incomplete essential data: Missing {missing_keys}"}

        # 2. Select prompt configuration based on decision context
        decision_context = current_data['decision_context']
        if decision_context in ["INITIAL BUY", "REBUY"]:
            prompt_config = self.prompts['buy']
            # Add slightly different guidance based on exact context
            if decision_context == "INITIAL BUY":
                specific_guidance_addon = "\n- This is the *first* potential buy. Assess initial risk carefully."
            else: # REBUY
                specific_guidance_addon = "\n- This is a *rebuy* opportunity. Check trade history for previous exit reason. Confirm trend reversal if needed."
            prompt_config['context_specific_guidance'] += specific_guidance_addon # Append to loaded guidance
        elif decision_context == "SELL/HOLD":
            prompt_config = self.prompts['sell']
        else:
            # Fallback for unknown contexts
            logger.warning(f"Unknown decision context '{decision_context}'. Defaulting to SELL/HOLD logic.")
            prompt_config = self.prompts['sell']
            decision_context = "SELL/HOLD" # Standardize context

        # 3. Create situation query string for RAG
        # This string describes the current situation to find similar past examples
        mcap_for_query = current_data.get('market_cap', 0)
        volatility_for_query = current_data.get('volatility', 0)
        rug_score_for_query = current_data.get('rugcheck_latest', 'N/A')
        rug_trend_for_query = current_data.get('rugcheck_trend', 'N/A')
        social_score_for_query = current_data.get('social_latest', 'N/A')
        social_trend_for_query = current_data.get('social_score_trend', 'N/A')
        age_for_query = current_data.get('token_age_minutes', 'N/A')
        creator_status_for_query = 'Prolific' if current_data.get('is_prolific_creator') else 'Normal'
        uri_status_for_query = current_data.get('uri_status', 'N/A')
        price_momentum_query_part = "N/A" # Extract recent price change for query
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
        logger.debug(f"RAG Situation Query: {situation_query}")

        # 4. Retrieve RAG context
        rag_context = self.retrieve_context(situation_query)

        # 5. Format market dynamics based on source
        market_dynamics_formatted = "Market dynamics data not available or source unknown."
        source = current_data['source']
        try:
            if source == 'PUMP':
                # Check if all keys needed for the PUMP template exist in current_data
                pump_keys = re.findall(r'\{(\w+)\}', prompt_config['market_dynamics_template_pump'])
                if all(k in current_data for k in pump_keys):
                    market_dynamics_formatted = prompt_config['market_dynamics_template_pump'].format(**current_data)
                else:
                    logger.warning(f"Missing required PUMP market dynamics keys in current_data. Keys: {list(current_data.keys())}")
            elif source == 'DEXSCREENER':
                # Check if all keys needed for the DEX template exist
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

        # 6. Assemble final prompt data dictionary
        # Map data from current_data to the placeholders defined in the YAML files
        prompt_data = {
            # --- Placeholders from base.yaml ---
            'decision_context': decision_context,
            'trade_history_summary': current_data.get('trade_history_summary', 'N/A'),
            'social_threshold': DEFAULT_SOCIAL_SCORE_THRESHOLD, # From config.py
            'min_volatility': MIN_VOLATILITY, # From config.py
            'rag_context': rag_context,
            'name': current_data.get('name', 'Unknown'),
            'mint': current_data.get('mint', 'N/A'),
            'token_age_minutes': current_data.get('token_age_minutes', 'N/A'),
            'creator_status': 'Prolific/Suspicious' if current_data.get('is_prolific_creator') else 'Normal/Unknown',
            'uri_status': current_data.get('uri_status', 'N/A'),
            'price': current_data.get('price', 0.0),
            'market_cap': current_data.get('market_cap', 0.0),
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
            'source': source,
            'market_dynamics_formatted': market_dynamics_formatted,
            # --- Placeholders filled from specific config (buy.yaml/sell.yaml) ---
            'context_specific_guidance': prompt_config.get('context_specific_guidance', ''),
            'source_explanation': prompt_config.get('source_explanation', ''),
            'market_cap_guidance': prompt_config.get('market_cap_guidance', '').format(
                default_marketcap_threshold=DEFAULT_MARKETCAP_THRESHOLD,
                min_marketcap_threshold=MIN_MARKETCAP_THRESHOLD
            ), # Format thresholds into guidance string
            'context_specific_rules': prompt_config.get('context_specific_rules', ''),
            # --- Thresholds needed within guidance text ---
            'default_marketcap_threshold': DEFAULT_MARKETCAP_THRESHOLD,
            'min_marketcap_threshold': MIN_MARKETCAP_THRESHOLD,
        }

        # Construct the final prompt string using the base template structure
        try:
            # Load template sections from the 'base' prompt config
            base_template_parts = self.prompts['base']
            # Assemble the prompt string section by section
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

            # Use .format() to insert the dynamic data into the assembled template string
            final_prompt = final_prompt.format(**prompt_data)

        except KeyError as e:
             logger.critical(f"CRITICAL: Missing key '{e}' during prompt final formatting. "
                             f"This likely indicates a mismatch between YAML placeholders and prompt_data dictionary. "
                             f"Available keys in prompt_data: {list(prompt_data.keys())}")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed on key '{e}'."}
        except Exception as e:
             logger.critical(f"CRITICAL: Unexpected error during prompt final formatting: {e}", exc_info=True)
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed unexpectedly."}

        # 7. Query the LLM
        llm_response = self.query_llm(final_prompt)

        # 8. Parse the LLM response
        parsed_decision = self._parse_llm_response_structured(llm_response, include_explanation)

        # Log the advice
        log_explanation_snippet = parsed_decision['explanation'][:200] + ('...' if len(parsed_decision['explanation']) > 200 else '') if include_explanation and parsed_decision.get('explanation') else "(Explanation Skipped or Missing)"
        logger.info(f"AI Advice for {current_data['mint']} ({decision_context}): {parsed_decision['decision']} "
                    f"(Confidence: {parsed_decision['confidence']}) - Reasoning: {log_explanation_snippet}")

        # 9. Store snapshot in memory (RAG)
        # Pass the original current_data and the final parsed_decision
        self.add_decision_snapshot_to_memory(current_data, parsed_decision)

        # 10. Return parsed decision
        return parsed_decision

    def _parse_llm_response_structured(self, llm_response: str, parse_explanation: bool = True) -> dict:
        """
        Parses the LLM response, expecting the strict format:
        DECISION:CONFIDENCE
        ---
        Explanation...

        Falls back to regex-based parsing if the strict format is not found.

        Args:
            llm_response (str): The raw response string from the LLM.
            parse_explanation (bool): Whether to attempt extracting the explanation text.

        Returns:
            dict: Dictionary with 'decision', 'confidence', and 'explanation'.
                  Provides default HOLD:0 on parsing failure.
        """
        # Default values
        decision = "HOLD"
        confidence = 0
        explanation = "No explanation processed." if not parse_explanation else "Explanation not found or invalid format."

        if not llm_response:
            logger.warning("LLM response parser received empty string.")
            return {"decision": decision, "confidence": confidence, "explanation": explanation}

        # Split into potential lines: Decision line, Separator line, Explanation part
        lines = llm_response.strip().split('\n', 2)

        # Try matching the strict format on the first line
        # Regex: ^\s* (optional whitespace) (BUY|SELL|HOLD) \s*:\s* (\d{1,3}) \s*$ (optional whitespace at end)
        strict_match = re.match(r"^\s*(BUY|SELL|HOLD)\s*:\s*(\d{1,3})\s*$", lines[0], re.IGNORECASE)

        if strict_match:
            decision = strict_match.group(1).upper()
            try:
                # Convert confidence, clamping between 0 and 100
                confidence = max(0, min(100, int(strict_match.group(2))))
                logger.debug(f"Parser: Matched strict format '{decision}:{confidence}' on first line.")

                # If strict match works, try to extract explanation based on separator
                if parse_explanation:
                    if len(lines) > 2 and lines[1].strip() == '---':
                        explanation = lines[2].strip()
                        logger.debug("Parser: Extracted explanation following strict format and separator.")
                    elif len(lines) == 2 and lines[1].strip() == '---':
                        explanation = "(No explanation text provided after separator)"
                        logger.debug("Parser: Strict format OK, separator found, but no explanation text.")
                    elif len(lines) > 1 and lines[1].strip() != '---':
                        # Strict format OK, but separator missing/wrong. Assume rest is explanation.
                        explanation = "\n".join(lines[1:]).strip()
                        logger.warning("Parser: Strict format OK, but separator '---' missing or incorrect on line 2. Taking rest of response as explanation.")
                    else: # Only one line matching strict format
                        explanation = "(No explanation provided)"
                        logger.debug("Parser: Strict format OK, but no subsequent lines for explanation.")
                # If we successfully parsed decision and confidence strictly, return immediately
                return {"decision": decision, "confidence": confidence, "explanation": explanation}

            except ValueError:
                # Should not happen with the regex, but handle just in case
                logger.warning(f"Parser: Matched strict format, but failed to parse confidence '{strict_match.group(2)}'. Falling back.")
                # Continue to fallback parser
        else:
            # Log the failed line for debugging
            logger.warning(f"Parser: Strict format 'DECISION:CONFIDENCE' not found on the first line: '{lines[0]}'. Falling back to regex.")

        # --- Fallback Parsing ---
        # If strict parsing failed, use the layered regex fallback
        logger.debug("Parser: Executing layered regex fallback parser.")
        fallback_result = self._parse_llm_response_fallback(llm_response)

        # Respect the include_explanation flag even in fallback
        if not parse_explanation:
            fallback_result["explanation"] = "No explanation processed."

        return fallback_result

    def _parse_llm_response_fallback(self, llm_response: str) -> dict:
        """
        Fallback parser using regex to find Decision, Confidence, and Explanation
        keywords and values anywhere in the response text. Less reliable than the
        structured parser but useful if the LLM deviates from the strict format.

        Args:
            llm_response (str): The raw response string from the LLM.

        Returns:
            dict: Dictionary with 'decision', 'confidence', and 'explanation'.
                  Uses defaults (HOLD:50) if parsing fails.
        """
        # Default values for fallback
        decision = "HOLD"
        confidence = 50 # Default confidence if not found
        explanation = llm_response # Default explanation is the full response

        response_upper = llm_response.upper() # For case-insensitive keyword search

        # --- Try to find Decision ---
        # 1. Look for "Decision: BUY/SELL/HOLD" at the start of a line (more reliable)
        decision_match_strict_line = re.search(r"^\W*\*?\s*Decision\s*\*?\W*:\s*\**?(BUY|SELL|HOLD)\**?", llm_response, re.IGNORECASE | re.MULTILINE)
        if decision_match_strict_line:
            decision = decision_match_strict_line.group(1).upper()
            logger.debug(f"Fallback Parser: Found decision '{decision}' via strict line search.")
        else:
            # 2. Look for "Decision: BUY/SELL/HOLD" anywhere on a line
            decision_match_lenient_line = re.search(r"^.*?\W*Decision\W*:\s*\**?(BUY|SELL|HOLD)\**?", llm_response, re.IGNORECASE | re.MULTILINE)
            if decision_match_lenient_line:
                decision = decision_match_lenient_line.group(1).upper()
                logger.debug(f"Fallback Parser: Found decision '{decision}' via lenient line search.")
            else:
                # 3. Look for BUY/SELL/HOLD as the only word on a line or as the dominant keyword
                if re.search(r"^\s*SELL\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or ("SELL" in response_upper and "BUY" not in response_upper and "HOLD" not in response_upper):
                    decision = "SELL"
                    logger.debug("Fallback Parser: Deduced 'SELL' via keyword dominance.")
                elif re.search(r"^\s*BUY\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or ("BUY" in response_upper and "SELL" not in response_upper and "HOLD" not in response_upper):
                    decision = "BUY"
                    logger.debug("Fallback Parser: Deduced 'BUY' via keyword dominance.")
                elif re.search(r"^\s*HOLD\s*$", llm_response, re.IGNORECASE | re.MULTILINE): # HOLD is often default, be more strict
                    decision = "HOLD"
                    logger.debug("Fallback Parser: Found 'HOLD' on its own line.")
                else:
                     logger.debug(f"Fallback Parser: No clear decision keyword found. Defaulting to '{decision}'.")

        # --- Try to find Confidence ---
        # 1. Look for "Confidence: 123" at the start of a line
        conf_match_strict_line = re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1,3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
        if conf_match_strict_line:
            try:
                confidence = max(0, min(100, int(conf_match_strict_line.group(1))))
                logger.debug(f"Fallback Parser: Found confidence '{confidence}' via strict line search.")
            except ValueError:
                logger.warning(f"Fallback Parser: Strict confidence line found, but failed to parse number '{conf_match_strict_line.group(1)}'.")
        else:
            # 2. Look for "Confidence: 123" anywhere on a line
            conf_match_lenient_line = re.search(r"^.*?\W*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1,3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
            if conf_match_lenient_line:
                 try:
                     confidence = max(0, min(100, int(conf_match_lenient_line.group(1))))
                     logger.debug(f"Fallback Parser: Found confidence '{confidence}' via lenient line search.")
                 except ValueError:
                     logger.warning(f"Fallback Parser: Lenient confidence line found, but failed to parse number '{conf_match_lenient_line.group(1)}'.")
            else:
                # 3. Look for "Confidence" followed by a number anywhere (less reliable)
                 conf_fallback_anywhere = re.search(r"Confidence.*?[:\s](\d{1,3})", llm_response, re.IGNORECASE | re.DOTALL)
                 if conf_fallback_anywhere:
                     try:
                         confidence = max(0, min(100, int(conf_fallback_anywhere.group(1))))
                         logger.debug(f"Fallback Parser: Found confidence '{confidence}' via general fallback search.")
                     except ValueError:
                         logger.warning(f"Fallback Parser: General confidence search found, but failed to parse number '{conf_fallback_anywhere.group(1)}'.")
                 else:
                     logger.debug(f"Fallback Parser: No confidence value found. Defaulting to {confidence}.")

        # --- Try to find Explanation ---
        # 1. Look for a header like "Explanation:", "Reasoning:", "Justification:" at the start of a line
        explanation_match = re.search(r"^\W*\*?\s*(?:Explanation|Reasoning|Justification)\s*\*?\W*:\s*(.*)", llm_response, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if explanation_match:
            explanation_text = explanation_match.group(1).strip()
            # Attempt to remove any Decision/Confidence lines that might have been included *after* the header
            explanation_text = re.sub(r"^\W*\*?\s*Decision\s*\*?\W*:.*?\n?", "", explanation_text, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            explanation_text = re.sub(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:.*?\n?", "", explanation_text, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            explanation = explanation_text
            logger.debug("Fallback Parser: Found explanation using header keyword.")
        else:
            # 2. If no header, assume explanation starts after the last Decision/Confidence line found
            lines = llm_response.splitlines()
            start_index = 0
            last_marker_line_index = -1
            found_marker = False
            for i, line in enumerate(lines):
                 # Check if the line contains a Decision or Confidence marker
                 if re.search(r"^\W*\*?\s*Decision\s*\*?\W*:", line, re.IGNORECASE) or \
                    re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:", line, re.IGNORECASE):
                     last_marker_line_index = i
                     found_marker = True

            if found_marker:
                start_index = last_marker_line_index + 1
                # Skip the next line too if it's *also* a marker (e.g., Confidence right after Decision)
                if start_index < len(lines) and (re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:", lines[start_index], re.IGNORECASE)):
                    start_index += 1

                # If there are lines remaining after the markers, join them as the explanation
                if start_index < len(lines):
                    explanation = "\n".join(lines[start_index:]).strip()
                    logger.debug("Fallback Parser: Found explanation by splitting after last Decision/Confidence marker.")
                else:
                    explanation = "" # Markers found, but nothing followed
                    logger.debug("Fallback Parser: Decision/Confidence markers found, but no subsequent text for explanation.")
            # else: No markers found, keep the full response as explanation (already the default)

        # Clean up excessive newlines in the extracted explanation
        explanation = re.sub(r'\n{3,}', '\n\n', explanation).strip()
        if not explanation: explanation = "(Explanation could not be extracted)"

        return {"decision": decision, "confidence": confidence, "explanation": explanation}