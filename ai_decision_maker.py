# ai_decision_maker.py
import ollama
import chromadb
from sentence_transformers import SentenceTransformer
from bot_logger import logger
from config.config import *  # Import your config for thresholds

class AIDecisionMaker:
    def __init__(self, model_name='llama3.2:latest', embedding_model='all-MiniLM-L6-v2'):
        self.model = model_name
        self.embedder = SentenceTransformer(embedding_model)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")  # Local DB storage
        self.collection = self.chroma_client.get_or_create_collection(name="trading_memory")
        logger.info("AI Decision Maker initialized with Ollama model: %s", self.model)

    def _embed_text(self, text: str) -> list:
        return self.embedder.encode(text).tolist()

    def add_to_memory(self, trade_data: dict):
        """Store past trade/market data as episodic memory for RAG."""
        # Serialize data to text for embedding
        memory_text = f"Trade on {trade_data['mint']}: Reason={trade_data.get('reason', 'N/A')}, Profit={trade_data.get('profit', 0)}, MarketCap={trade_data.get('market_cap', 0)}, Volatility={trade_data.get('volatility', 0)}"
        embedding = self._embed_text(memory_text)
        self.collection.add(
            documents=[memory_text],
            embeddings=[embedding],
            ids=[str(trade_data['timestamp'])],  # Unique ID, e.g., timestamp
            metadatas=[trade_data]  # Store full dict for retrieval
        )
        logger.debug("Added to memory: %s", memory_text)

    def retrieve_context(self, query: str, top_k: int = 3) -> str:
        """Hybrid retrieval: Simple semantic search (add BM25 later if needed)."""
        query_embedding = self._embed_text(query)
        results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
        if not results['documents']:
            return "No relevant past data."
        context = "\n".join([doc for sublist in results['documents'] for doc in sublist])
        return f"Past trades context: {context}"

    def query_llm(self, prompt: str) -> str:
        """Query Ollama for decision."""
        try:
            response = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content'].strip()
        except Exception as e:
            logger.error("Ollama query failed: %s", e)
            return "AI decision unavailable."

    def get_trade_advice(self, current_data: dict) -> dict:
        """Main entry: Get buy/sell advice based on current data + RAG context."""
        # Build query from your bot's data (e.g., from trade_processor or trading_logic)
        query = f"Token: {current_data['mint']}, Name: {current_data.get('name', 'Unknown')}, Price: {current_data['price']}, Market Cap: {current_data['market_cap']}, Volatility: {current_data['volatility']}, Rugcheck: {current_data['rugcheck_score']}, Social Score: {current_data['social_score']}, Volume: {current_data['volume']}, DexScreener Trends: {current_data.get('dex_trends', 'N/A')}"

        # Retrieve RAG context (past similar trades)
        rag_context = self.retrieve_context(query)

        # Updated prompt with correct scoring interpretation and inactivity handling
        prompt = f"""
        You are a meme coin trading agent on Solana. Analyze this data and decide: BUY, SELL, or HOLD.
        Key rules:
        - Rugcheck score: Lower is better (1 = low risk, safe; high like >901 or >10000 = high risk, avoid). Tokens above {DEFAULT_RUGCHECK_SCORE_THRESHOLD} are usually ignored.
        - Social score: Lower is better (1 = low risk/good socials; 100+ = high risk/bad socials). Tokens above {DEFAULT_SOCIAL_SCORE_THRESHOLD} are usually ignored.
        - For migrated tokens (source=DexScreener), check for inactivity: If volume=0 or low activity for >{INACTIVITY_PERIOD} minutes, consider SELL or HOLD to avoid dead tokens.
        - Volatility: Prefer >{MIN_VOLATILITY} for opportunities, but not too high.
        - Market Cap: Avoid if below {DEFAULT_MARKETCAP_THRESHOLD} USD unless strong signals.
        - Use reasoning chain: 1) Summarize metrics with correct risk interpretation. 2) Compare to thresholds (e.g., Rugcheck low=good). 3) Factor in past trades: {rag_context}. 4) Check for zero/low activity in migrated tokens. 5) Output decision (BUY/SELL/HOLD) with confidence (0-100) and brief explanation.
        Current data: {query}
        """
        
        llm_response = self.query_llm(prompt)
        
        # Parse response (simple for now; improve with regex/JSON mode if model supports)
        decision = "HOLD"  # Default
        confidence = 50
        explanation = llm_response  # Use full response as explanation
        
        if "BUY" in llm_response.upper():
            decision = "BUY"
        elif "SELL" in llm_response.upper():
            decision = "SELL"
        
        # Extract confidence if mentioned (basic parse; improve as needed)
        import re
        conf_match = re.search(r'confidence (\d+)%?', llm_response, re.IGNORECASE)
        if conf_match:
            confidence = int(conf_match.group(1))
        
        logger.info("AI Advice: %s (Confidence: %d) - %s", decision, confidence, explanation)
        return {"decision": decision, "confidence": confidence, "explanation": explanation}