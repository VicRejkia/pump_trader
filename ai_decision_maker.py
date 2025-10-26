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
from datetime import datetime, timezone

class AIDecisionMaker:
    # --- PROMPT TEMPLATES AND CONFIG ---
    PROMPT_TEMPLATE_BASE = """
**CRITICAL: YOUR OUTPUT MUST FOLLOW THIS FORMAT EXACTLY.**
1.  **FIRST LINE ONLY:** `DECISION:CONFIDENCE` (e.g., `BUY:85`, `SELL:60`, `HOLD:70`). Replace DECISION with BUY, SELL, or HOLD. Replace CONFIDENCE with a number between 0 and 100. **DO NOT add any text, markdown, or greetings before this line.**
2.  **SECOND LINE ONLY:** `---` (three hyphens)
3.  **FOLLOWING LINES:** Your detailed reasoning and explanation.

**EXAMPLE OUTPUT:**
--- [START OF EXAMPLE] ---
SELL:70
---
1. The context is SELL/HOLD... [rest of reasoning]...

--- [END OF EXAMPLE] ---

Now, analyze the following data:
You are an expert Solana meme coin trading analyst AI. Your goal is to maximize profit while managing risk for a trading bot.
Analyze the provided comprehensive data and decide: {decision_options}. Output your decision, a confidence score (0-100), and a brief explanation using a reasoning chain.

**Current Decision Context:** {decision_context}
{context_specific_guidance}

**Past Trade History Summary:**
{trade_history_summary}
- **Interpretation:** Analyze the sequence and outcomes. Repeated 'Stop Loss' or negative profit sells suggest weakness. 'Take Profit' sells indicate past strength. 'Manual Override' sells mean external factors influenced the exit; consider if those factors might still apply. A history with only buys suggests the current hold needs careful evaluation.

**Key Decision Rules & Interpretation Guide:**
# ... (rest of the rules remain the same as previous refactoring) ...
- **Data Source:** Interpret '{source}' data correctly ({source_explanation}).
- **Risk Scores (Lower is Better):** Focus on TRENDS and STABILITY. Rapid worsening is a major red flag.
    - **Rugcheck Score:** <50 very low, <300 low, <600 moderate, <900 high. Significant *increases* are negative, especially in SELL/HOLD context.
    - **Social Score (0-100):** <10 excellent, <30 good, <50 moderate, <70 poor. Scores near/above {social_threshold} are high risk. Significant *increases* are negative, especially in SELL/HOLD context.
- **Market Cap (USD):** Reflects size/risk/reward. {market_cap_guidance}
- **Volatility:** Moderate ({min_volatility}+) preferred for opportunities. Low may mean stagnation. High increases risk.
- **DexScreener Inactivity:** If source is DexScreener, near-zero volume/liquidity is a strong SELL/HOLD signal.
- **Token Age:** Very young (< 15 mins) are riskier, especially for initial buys. Older tokens require stronger signals for entry/hold.
- **Creator:** 'Prolific/Suspicious' increases risk, especially for holds.
- **URI Status:** 'Missing'/'Invalid'/'Error' increases risk, especially for buys.
{context_specific_rules}
- **Past Situations (Context):** Learn from relevant past scenarios: {rag_context}

**Current Token Data ({name} - {mint}):**
# ... (rest of current data section remains the same) ...
**Metadata & Context:**
- Token Age: {token_age_minutes} minutes
- Creator Status: {creator_status}
- Metadata URI Status: {uri_status}

**Core Metrics:**
- Price (SOL): {price:.9f}
- Market Cap (USD): ${market_cap:,.0f}
- Volatility (Recent): {volatility:.3f}

**Risk Assessment:**
- Rugcheck: Latest: {rugcheck_latest}, Initial: {rugcheck_initial}, Trend(1h): {rugcheck_trend}, Stability: {rugcheck_stability}
- Social Score: Latest: {social_latest}, Initial: {social_initial}, Trend(1h): {social_score_trend}, Stability: {social_stability}, TG Members Trend(1h): {telegram_members_trend}, TG Online Ratio Trend(1h): {telegram_online_ratio_trend}

**Market Dynamics (Source: {source}):**
{market_dynamics_formatted}


**Reasoning Chain Steps:**
1. State the current decision context ({decision_context}).
2. Analyze the **Past Trade History Summary**, noting sequence, reasons, and outcomes. How does this history inform the current risk/potential?
3. Summarize current core metrics, risk scores (value, trend, stability), token age, creator, URI.
4. Evaluate market dynamics ({source}), focusing on signals relevant to {decision_context}. Check DexScreener inactivity if applicable.
5. Assess overall risk profile using rules. How has risk evolved (if SELL/HOLD)? How do token age and the detailed **past trade history** influence this?
6. Synthesize findings with insights from relevant past situations ({rag_context}).
7. Conclude with a clear decision ({decision_options}), confidence score (0-100), and concise explanation incorporating the analysis from step 2.

**Decision:**
"""

    PROMPT_CONFIG_BUY = {
        "decision_options": "BUY or HOLD",
        "context_specific_guidance": "- Focus on entry signals, risk assessment, momentum, and potential upside. Is this a good time to enter/re-enter?",
        "source_explanation": "PUMP = High-frequency Ticks, DEXSCREENER = Periodic Snapshots",
        "market_cap_guidance": f"Avoid buys below ${DEFAULT_MARKETCAP_THRESHOLD} unless very strong signals exist.",
        "context_specific_rules": "- Look for positive momentum (price, volume), improving risk scores, reasonable volatility, and consider token age.",
        "market_dynamics_template_pump": """- Price Change (1min): {pump_price_change_1m}
- Volume Velocity (1min): {pump_volume_velocity_1m}
- Tick Frequency (1min): {pump_tick_frequency_1m} trades/min""",
        "market_dynamics_template_dex": """- Price Change (5min snap): {dex_price_change_m5:.2f}%
- Volume (5min snap): ${dex_volume_m5:,.0f}
- Buys/Sells (5min snap): {dex_buys_m5} / {dex_sells_m5}
- Price Trend (15min): {dex_price_trend_15m}
- Volume Trend (15min): {dex_volume_trend_15m}
- Liquidity Trend (30min): {dex_liquidity_trend_30m}"""
    }

    PROMPT_CONFIG_SELL = {
        "decision_options": "SELL or HOLD",
        "context_specific_guidance": "- Focus on exit signals, risk changes (worsening scores, MC drops), profit-taking, stagnation, or negative momentum. Is it time to exit or continue holding?",
        "source_explanation": "PUMP = High-frequency Ticks, DEXSCREENER = Periodic Snapshots",
        "market_cap_guidance": f"Consider selling if MC drops significantly, especially below ${MIN_MARKETCAP_THRESHOLD}.",
        "context_specific_rules": "- Look for negative momentum, worsening risk scores, prolonged low volume/volatility, hitting profit/loss targets, or excessive token age without growth.",
        "market_dynamics_template_pump": """- Price Change (1min): {pump_price_change_1m}
- Volume Velocity (1min): {pump_volume_velocity_1m}
- Tick Frequency (1min): {pump_tick_frequency_1m} trades/min""",
        "market_dynamics_template_dex": """- Price Change (5min snap): {dex_price_change_m5:.2f}%
- Volume (5min snap): ${dex_volume_m5:,.0f}
- Buys/Sells (5min snap): {dex_buys_m5} / {dex_sells_m5}
- Price Trend (15min): {dex_price_trend_15m}
- Volume Trend (15min): {dex_volume_trend_15m}
- Liquidity Trend (30min): {dex_liquidity_trend_30m}"""
    }
    # --- END PROMPT TEMPLATES ---

    def __init__(self, model_name='llama3:latest', embedding_model='all-MiniLM-L6-v2'):
        self.model = model_name
        self.embedder = SentenceTransformer(embedding_model)
        try:
            # Consider making the path configurable
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db_aidm")
            # Consider versioning or parameterizing the collection name
            self.collection = self.chroma_client.get_or_create_collection(name="trading_decision_memory_v3")
            logger.info("ChromaDB client initialized for AI Decision Maker.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}", exc_info=True)
            raise
        logger.info("AI Decision Maker initialized with Ollama model: %s", self.model)

    def _embed_text(self, text: str) -> list:
        try:
            return self.embedder.encode(text).tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: {e}", exc_info=True)
            return []

    def add_decision_snapshot_to_memory(self, snapshot_data: dict, decision_info: dict):
        """
        Store a snapshot of the data used for a decision, the decision itself,
        and potentially the outcome (if available later).
        """
        # Format a concise summary string for embedding and document storage
        # Ensure key metrics are present and formatted reasonably
        mcap_usd = snapshot_data.get('market_cap', 0)
        volatility = snapshot_data.get('volatility', 0)
        rug_score = snapshot_data.get('rugcheck_latest', 'N/A') # Use renamed key
        rug_trend = snapshot_data.get('rugcheck_trend', 'N/A')
        social_score = snapshot_data.get('social_latest', 'N/A') # Use renamed key
        social_trend = snapshot_data.get('social_score_trend', 'N/A')
        token_age = snapshot_data.get('token_age_minutes', 'N/A')

        situation_summary = (
            f"Situation Snapshot at {snapshot_data.get('timestamp', datetime.now(timezone.utc).isoformat())} for {snapshot_data.get('mint', 'N/A')} ({snapshot_data.get('decision_context', 'N/A')} context):\n"
            f"Source: {snapshot_data.get('source', 'N/A')}, MCap (USD): ${mcap_usd:,.0f}, Volatility: {volatility:.3f}\n"
            f"Token Age: {token_age} mins, Creator: {'Prolific' if snapshot_data.get('is_prolific_creator') else 'Normal'}, URI: {snapshot_data.get('uri_status', 'N/A')}\n"
            f"Rug Score: {rug_score} (Trend: {rug_trend})\n"
            f"Social Score: {social_score} (Trend: {social_trend})\n"
            f"Market Dynamics Summary: {snapshot_data.get('market_dynamics_summary_str', 'N/A')}\n" # Use summary string
            f"Trade History: {snapshot_data.get('trade_history_summary', 'N/A')}\n"
            f"AI Decision: {decision_info.get('decision', 'N/A')} (Confidence: {decision_info.get('confidence', 'N/A')})\n"
            f"Reasoning Snippet: {decision_info.get('explanation', 'N/A')[:150]}...\n" # Keep snippet short
        )


        embedding = self._embed_text(situation_summary)
        if not embedding:
            logger.warning("Failed to create embedding for decision snapshot. Skipping memory add.")
            return

        snapshot_time_str = snapshot_data.get('timestamp', datetime.now(timezone.utc).isoformat())
        # Ensure timestamp is a valid string before using in ID
        if not isinstance(snapshot_time_str, str):
             snapshot_time_str = datetime.now(timezone.utc).isoformat()

        snapshot_id = f"{snapshot_time_str}_{snapshot_data.get('mint', 'unknown')}"

        # Prepare metadata: Ensure values are suitable types (str, int, float, bool)
        metadata_to_store = {
            "mint": snapshot_data.get('mint'),
            "timestamp": snapshot_time_str, # Store as string
            "decision_context": snapshot_data.get('decision_context'),
            "source": snapshot_data.get('source'),
            "market_cap": float(mcap_usd) if mcap_usd is not None else None,
            "volatility": float(volatility) if volatility is not None else None,
            "token_age_minutes": float(token_age) if token_age is not None else None, # Store age
            "is_prolific_creator": snapshot_data.get('is_prolific_creator'),
            "uri_status": snapshot_data.get('uri_status'),
            "rugcheck_score": str(rug_score), # Store scores as string for flexibility
            "social_score": str(social_score),
            "rugcheck_trend": rug_trend,
            "social_score_trend": social_trend,
            "decision": decision_info.get('decision'),
            "confidence": int(decision_info.get('confidence', 0)), # Store confidence as int
        }
        # Filter out None values before adding to ChromaDB
        metadata_to_store = {k: v for k, v in metadata_to_store.items() if v is not None}

        try:
            self.collection.add(
                documents=[situation_summary],
                embeddings=[embedding],
                ids=[snapshot_id],
                metadatas=[metadata_to_store]
            )
            logger.debug(f"Added decision snapshot to memory: ID {snapshot_id}")
        except Exception as e:
            logger.error(f"Failed to add decision snapshot to ChromaDB: {e}", exc_info=True)


    def retrieve_context(self, situation_query: str, top_k: int = 5) -> str:
        """Retrieve relevant past decision snapshots based on the current market situation."""
        if not situation_query:
            return "No situation query provided."

        query_embedding = self._embed_text(situation_query)
        if not query_embedding:
            logger.warning("Failed to create embedding for situation query. Cannot retrieve context.")
            return "Embedding failed for query."

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                # Optional: Add filtering based on metadata if needed in the future
                # where={"decision_context": decision_context_filter}
            )

            if not results or not results.get('documents') or not results['documents'][0]:
                return "No relevant past decision snapshots found."

            context_parts = ["--- Relevant Past Situations & Decisions ---"]
            for i, doc in enumerate(results['documents'][0]):
                 metadata = results['metadatas'][0][i] if (
                     results.get('metadatas') and
                     len(results['metadatas']) > 0 and
                     len(results['metadatas'][0]) > i
                 ) else {}

                 context_parts.append(f"Past Case {i+1}:")
                 # The document already contains a summary, just append it
                 context_parts.append(doc.strip())

                 # Add key metadata for quick reference in the prompt
                 if metadata:
                     mcap_display = f"${metadata.get('market_cap', 0):,.0f}" if metadata.get('market_cap') else "N/A"
                     outcome_info = f", Outcome Profit: {metadata.get('profit', 'N/A')}" if 'profit' in metadata else ""
                     context_parts.append(
                         f"  (Metadata: Decision={metadata.get('decision', '?')}, "
                         f"Conf={metadata.get('confidence', '?')}, "
                         f"Context={metadata.get('decision_context', '?')}, " # Show context of past decision
                         f"MCap={mcap_display}{outcome_info})"
                     )
                 context_parts.append("---")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error querying ChromaDB for context: {e}", exc_info=True)
            return "Error retrieving context from memory."

    def query_llm(self, prompt: str) -> str:
        """Query Ollama for decision."""
        # Limit log length to avoid flooding console
        log_prompt_snippet = prompt[:5000] + ('...' if len(prompt) > 5000 else '')
        logger.debug(f"Sending prompt to LLM (approx {len(prompt)} chars):\n{log_prompt_snippet}")
        try:
            response = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': prompt}])
            result = response['message']['content'].strip()
            # Limit log length for response too
            log_result_snippet = result[:5000] + ('...' if len(result) > 5000 else '')
            logger.debug(f"LLM Response received:\n{log_result_snippet}")
            return result
        except Exception as e:
            logger.error("Ollama query failed: %s", e, exc_info=True)
            # Provide a structured error response that parse_llm can handle
            return "Decision: HOLD\nConfidence Score: 0\nExplanation: AI decision unavailable due to LLM query error."


    def get_trade_advice(self, current_data: dict) -> dict:
        """Main entry: Get buy/sell advice based on comprehensive current data + RAG context."""
        required_keys = ['mint', 'source', 'price', 'market_cap', 'volatility', 'decision_context', 'token_age_minutes']
        if not all(k in current_data for k in required_keys):
             # Log the missing keys for easier debugging
             missing = [k for k in required_keys if k not in current_data]
             logger.error(f"Missing essential keys in current_data for AI advice: {missing}")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Incomplete essential data: Missing {missing}"}

        decision_context = current_data['decision_context']

        # --- Select Prompt Configuration ---
        if decision_context in ["INITIAL BUY", "REBUY"]:
            prompt_config = self.PROMPT_CONFIG_BUY
        elif decision_context == "SELL/HOLD":
            prompt_config = self.PROMPT_CONFIG_SELL
        else:
            logger.warning(f"Unknown decision context '{decision_context}'. Defaulting to SELL/HOLD prompt.")
            prompt_config = self.PROMPT_CONFIG_SELL
            decision_context = "SELL/HOLD" # Ensure context matches default prompt

        # --- Refine RAG Query ---
        # Construct query using available data, handling potential None values
        mcap_for_query = current_data.get('market_cap', 0)
        volatility_for_query = current_data.get('volatility', 0)
        rug_score_for_query = current_data.get('rugcheck_latest', 'N/A')
        rug_trend_for_query = current_data.get('rugcheck_trend', 'N/A')
        social_score_for_query = current_data.get('social_latest', 'N/A')
        social_trend_for_query = current_data.get('social_score_trend', 'N/A')
        age_for_query = current_data.get('token_age_minutes', 'N/A')
        creator_status_for_query = 'Prolific' if current_data.get('is_prolific_creator') else 'Normal'
        uri_status_for_query = current_data.get('uri_status', 'N/A')

        # Get relevant price momentum based on source for the query
        price_momentum_query_part = "N/A"
        if current_data['source'] == 'PUMP':
             price_momentum_query_part = current_data.get('pump_price_change_1m', 'N/A')
        elif current_data['source'] == 'DEXSCREENER':
             price_momentum_query_part = f"{current_data.get('dex_price_change_m5', 'N/A')}%"


        situation_query = (
            f"Analyze similar Solana meme coin situations: "
            f"Context={decision_context}, "
            f"Source={current_data['source']}, "
            f"MCap approx ${mcap_for_query:,.0f}, "
            f"Volatility level {volatility_for_query:.3f}, "
            f"Token Age: {age_for_query} mins. "
            f"Rugcheck score {rug_score_for_query} trending {rug_trend_for_query}, "
            f"Social score {social_score_for_query} trending {social_trend_for_query}. "
            f"Creator Status: {creator_status_for_query}. "
            f"URI Status: {uri_status_for_query}. "
            f"Price Momentum (recent): {price_momentum_query_part}"
        )
        rag_context = self.retrieve_context(situation_query)


        # --- Format Market Dynamics Based on Source ---
        market_dynamics_formatted = "Market dynamics data not available for this source or is missing."
        source = current_data['source']
        try:
            if source == 'PUMP':
                # Check if keys exist before formatting
                if all(k in current_data for k in ['pump_price_change_1m', 'pump_volume_velocity_1m', 'pump_tick_frequency_1m']):
                    market_dynamics_formatted = prompt_config['market_dynamics_template_pump'].format(
                        pump_price_change_1m=current_data.get('pump_price_change_1m', 'N/A'),
                        pump_volume_velocity_1m=current_data.get('pump_volume_velocity_1m', 'N/A'),
                        pump_tick_frequency_1m=current_data.get('pump_tick_frequency_1m', 'N/A')
                    )
                else:
                    logger.warning("Missing PUMP market dynamic keys in current_data.")
            elif source == 'DEXSCREENER':
                # Check if keys exist before formatting
                dex_keys = ['dex_price_change_m5', 'dex_volume_m5', 'dex_buys_m5', 'dex_sells_m5',
                            'dex_price_trend_15m', 'dex_volume_trend_15m', 'dex_liquidity_trend_30m']
                if all(k in current_data for k in dex_keys):
                    market_dynamics_formatted = prompt_config['market_dynamics_template_dex'].format(
                        dex_price_change_m5=current_data.get('dex_price_change_m5', 0.0),
                        dex_volume_m5=current_data.get('dex_volume_m5', 0.0),
                        dex_buys_m5=current_data.get('dex_buys_m5', 0),
                        dex_sells_m5=current_data.get('dex_sells_m5', 0),
                        dex_price_trend_15m=current_data.get('dex_price_trend_15m', 'N/A'),
                        dex_volume_trend_15m=current_data.get('dex_volume_trend_15m', 'N/A'),
                        dex_liquidity_trend_30m=current_data.get('dex_liquidity_trend_30m', 'N/A')
                    )
                else:
                     logger.warning("Missing DEXSCREENER market dynamic keys in current_data.")
        except KeyError as e:
             logger.error(f"KeyError during market dynamics formatting for source {source}: {e}. Data: {current_data}")
             market_dynamics_formatted = f"Error formatting market dynamics for {source}."


        # --- Prepare data for final prompt formatting ---
        # Use .get() with defaults for all potentially missing keys to prevent KeyErrors
        prompt_data = {
            'mint': current_data.get('mint', 'N/A'),
            'name': current_data.get('name', 'Unknown'),
            'symbol': current_data.get('symbol', 'N/A'),
            'source': source,
            'decision_context': decision_context,
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
            'social_latest': current_data.get('social_score_latest', 'N/A'),
            'social_initial': current_data.get('social_score_initial', 'N/A'), # Corrected key
            'social_score_trend': current_data.get('social_score_trend', 'N/A'),
            'social_stability': current_data.get('social_score_stability', 'N/A'), # Corrected key
            'telegram_members_trend': current_data.get('telegram_members_trend', 'N/A'),
            'telegram_online_ratio_trend': current_data.get('telegram_online_ratio_trend', 'N/A'),
            'trade_history_summary': current_data.get('trade_history_summary', 'N/A'),
            'rag_context': rag_context,
            'market_dynamics_formatted': market_dynamics_formatted,
            'social_threshold': DEFAULT_SOCIAL_SCORE_THRESHOLD,
            'min_volatility': MIN_VOLATILITY,
            'default_marketcap_threshold': DEFAULT_MARKETCAP_THRESHOLD,
            'min_marketcap_threshold': MIN_MARKETCAP_THRESHOLD,
            **prompt_config # Includes context-specific guidance strings etc.
        }

        # --- Generate Final Prompt ---
        try:
             final_prompt = self.PROMPT_TEMPLATE_BASE.format(**prompt_data)
        except KeyError as e:
             logger.error(f"CRITICAL: Missing key '{e}' required for prompt template. Data provided: {prompt_data.keys()}")
             return {"decision": "HOLD", "confidence": 0, "explanation": f"Internal Error: Prompt generation failed due to missing key '{e}'."}


        # --- Query LLM and Parse ---
        llm_response = self.query_llm(final_prompt)
        parsed_decision = self._parse_llm_response(llm_response)

        # --- Logging and Memory ---
        logger.info(
            "AI Advice for %s (%s): %s (Confidence: %d) - %s",
            current_data['mint'],
            decision_context, # Log context used
            parsed_decision['decision'],
            parsed_decision['confidence'],
            parsed_decision['explanation'][:200] + ('...' if len(parsed_decision['explanation']) > 200 else '') # Keep log concise
        )
        # Add snapshot to memory uses the original comprehensive current_data
        self.add_decision_snapshot_to_memory(current_data, parsed_decision)

        return parsed_decision

    def _parse_llm_response(self, llm_response: str) -> dict:
        """Parse LLM response to extract decision, confidence, and explanation."""
        decision = "HOLD" # Default
        confidence = 50 # Default
        explanation = llm_response # Default as fallback
        raw_response_upper = llm_response.upper() # For loose keyword checks

        # --- Decision Parsing ---
        # Attempt 1: Strict start-of-line match (most reliable if format holds)
        # Allows optional markdown bolding around label and value
        decision_match_strict = re.search(r"^\W*\*?\s*Decision\s*\*?\W*:\s*\**?(BUY|SELL|HOLD)\**?", llm_response, re.IGNORECASE | re.MULTILINE)
        if decision_match_strict:
            decision = decision_match_strict.group(1).upper()
            logger.debug(f"Parser: Found decision '{decision}' using strict regex.")
        else:
            # Attempt 2: More lenient search for "Decision: WORD" anywhere on a line (still prefers structure)
            decision_match_lenient = re.search(r"^.*?\W*Decision\W*:\s*\**?(BUY|SELL|HOLD)\**?", llm_response, re.IGNORECASE | re.MULTILINE)
            if decision_match_lenient:
                decision = decision_match_lenient.group(1).upper()
                logger.debug(f"Parser: Found decision '{decision}' using lenient line regex.")
            else:
                 # Attempt 3: Look for standalone keywords (BUY/SELL have priority over HOLD default)
                 # Check SELL first
                 if re.search(r"^\s*SELL\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or \
                    ( "SELL" in raw_response_upper and "BUY" not in raw_response_upper and "HOLD" not in raw_response_upper ): # Check if ONLY Sell keyword exists loosely
                     decision = "SELL"
                     logger.debug("Parser: Found decision 'SELL' using keyword fallback.")
                 # Check BUY next
                 elif re.search(r"^\s*BUY\s*$", llm_response, re.IGNORECASE | re.MULTILINE) or \
                      ( "BUY" in raw_response_upper and "SELL" not in raw_response_upper and "HOLD" not in raw_response_upper ): # Check if ONLY Buy keyword exists loosely
                     decision = "BUY"
                     logger.debug("Parser: Found decision 'BUY' using keyword fallback.")
                 # Check HOLD last (only if explicitly stated alone)
                 elif re.search(r"^\s*HOLD\s*$", llm_response, re.IGNORECASE | re.MULTILINE) :
                      decision = "HOLD"
                      logger.debug("Parser: Found decision 'HOLD' using keyword fallback.")
                 else:
                      logger.debug(f"Parser: No clear decision found via regex or keywords. Defaulting to {decision}.")


        # --- Confidence Parsing (Keep previous robust version) ---
        # Attempt 1: Strict start-of-line match
        conf_match_strict = re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1,3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
        if conf_match_strict:
            try:
                confidence = int(conf_match_strict.group(1))
                confidence = max(0, min(100, confidence))
                logger.debug(f"Parser: Found confidence '{confidence}' using strict regex.")
            except ValueError:
                 logger.warning("Parser: Found strict confidence pattern but failed to parse number.")
        else:
            # Attempt 2: More lenient search anywhere on a line
            conf_match_lenient = re.search(r"^.*?\W*Confidence(?:\s*Score)?\s*\*?\W*:\s*(\d{1,3})\%?", llm_response, re.IGNORECASE | re.MULTILINE)
            if conf_match_lenient:
                 try:
                     confidence = int(conf_match_lenient.group(1))
                     confidence = max(0, min(100, confidence))
                     logger.debug(f"Parser: Found confidence '{confidence}' using lenient line regex.")
                 except ValueError:
                      logger.warning("Parser: Found lenient confidence pattern but failed to parse number.")
            else:
                 # Attempt 3: Fallback search anywhere (less reliable)
                 conf_fallback_match = re.search(r"Confidence.*?[:\s](\d{1,3})", llm_response, re.IGNORECASE | re.DOTALL)
                 if conf_fallback_match:
                     try:
                         confidence = int(conf_fallback_match.group(1))
                         confidence = max(0, min(100, confidence))
                         logger.debug(f"Parser: Found confidence '{confidence}' using fallback anywhere regex.")
                     except ValueError:
                         logger.warning("Parser: Found fallback anywhere confidence pattern but failed to parse number.")
                 else:
                     logger.debug(f"Parser: No confidence score found via regex. Defaulting to {confidence}.")


        # --- Explanation Parsing (Keep previous robust version) ---
        explanation_match = re.search(
            r"^\W*\*?\s*(?:Explanation|Reasoning|Justification)\s*\*?\W*:\s*(.*)",
            llm_response,
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if explanation_match:
            explanation = explanation_match.group(1).strip()
            # Remove potential repetition of Decision/Confidence within the explanation block more robustly
            explanation = re.sub(r"^\W*\*?\s*Decision\s*\*?\W*:.*?\n?", "", explanation, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            explanation = re.sub(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:.*?\n?", "", explanation, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
            logger.debug("Parser: Found explanation using primary header regex.")
        else:
            # Fallback if specific header not found: Try splitting based on Decision/Confidence lines
            lines = llm_response.splitlines()
            start_index = 0
            found_marker = False
            # Find the *last* occurrence of Decision or Confidence header
            last_marker_index = -1
            for i, line in enumerate(lines):
                 if re.search(r"^\W*\*?\s*Decision\s*\*?\W*:", line, re.IGNORECASE) or \
                    re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:", line, re.IGNORECASE):
                     last_marker_index = i
                     found_marker = True

            if found_marker:
                start_index = last_marker_index + 1
                # If confidence follows decision, skip that too
                if start_index < len(lines) and re.search(r"^\W*\*?\s*Confidence(?:\s*Score)?\s*\*?\W*:", lines[start_index], re.IGNORECASE):
                    start_index += 1

                if start_index < len(lines):
                    explanation = "\n".join(lines[start_index:]).strip()
                    logger.debug("Parser: Found explanation using fallback split logic after last marker.")
                else:
                     logger.debug("Parser: Found marker lines, but no text followed for explanation.")
                     explanation = "" # Clear explanation if only headers were found
            else:
                 logger.debug("Parser: No explanation header found, keeping full response as explanation.")
                 # Keep full response as explanation

        explanation = re.sub(r'\n{3,}', '\n\n', explanation) # Reduce excessive newlines

        # --- Mismatch Check (Keep previous robust version) ---
        # Compare parsed decision with keywords in the *explanation* part, not the whole response
        explanation_upper = explanation.upper() if explanation else ""
        if decision == "BUY" and "HOLD" in explanation_upper and "SELL" not in explanation_upper:
             logger.warning(f"Parser Mismatch Check: Explanation contained 'HOLD', parsed decision is '{decision}'. Explanation Snippet:\n{explanation[:500]}...")
        elif decision == "HOLD" and "BUY" in explanation_upper and "SELL" not in explanation_upper:
             logger.warning(f"Parser Mismatch Check: Explanation contained 'BUY', parsed decision is '{decision}'. Explanation Snippet:\n{explanation[:500]}...")
        elif decision == "SELL" and ("BUY" in explanation_upper or "HOLD" in explanation_upper):
             logger.debug(f"Parser Info: Explanation contained 'BUY' or 'HOLD', parsed decision is '{decision}'. This might be part of the reasoning process. Explanation Snippet:\n{explanation[:500]}...")
        # Add more checks if needed

        return {"decision": decision, "confidence": confidence, "explanation": explanation}
    # --- END REFINED PARSER ---