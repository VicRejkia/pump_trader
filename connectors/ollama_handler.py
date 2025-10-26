# path: connectors/ollama_handler.py

import httpx
import json
import asyncio
import argparse
import os
import asyncpg
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from .env file at the project root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Construct the database URL from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?options=-c%20timezone%3Dutc"

# Ollama Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL_NAME = "llama3:latest" # Or your preferred model

class OllamaHandler:
    """Handles communication with a local Ollama LLM instance."""
    def __init__(self, model_name: str = OLLAMA_MODEL_NAME):
        self.model_name = model_name
        # Increased timeout for potentially long LLM generation times
        self.client = httpx.AsyncClient(timeout=120.0)

    async def _query_ollama(self, prompt: str) -> dict | None:
        """Sends a prompt to the Ollama API and gets a structured JSON response."""
        print("🤖 Querying Ollama LLM... (This may take a moment)")
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }
        try:
            response = await self.client.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            # The actual JSON content is nested inside the 'response' key
            response_text = response.json().get("response", "{}")
            return json.loads(response_text)
        except httpx.RequestError as e:
            print(f"❌ Connection to Ollama failed. Is Ollama running at {OLLAMA_API_URL}?")
            print(f"   Error: {e}")
            return None
        except (json.JSONDecodeError, httpx.HTTPStatusError) as e:
            print(f"❌ Ollama API request failed: {e}")
            return None

    async def analyze_meme_fundamentals(self, metadata: dict, rugcheck_data: dict) -> dict | None:
        """Analyzes a meme coin's narrative, security, and distribution using a risk scoring model."""
        # Use json.dumps to safely handle the rugcheck data within the f-string
        rugcheck_json_str = json.dumps(rugcheck_data, indent=2)

        prompt = f"""
        You are an expert Solana meme coin risk analyst. Your task is to evaluate a new token and assign risk scores based on its metadata and on-chain data. A score of 1 is very low risk, and 100 is maximum risk.

        **Token Metadata:**
        - Name: "{metadata.get('name')}"
        - Symbol: "{metadata.get('symbol')}"
        - Description: "{metadata.get('description')}"

        **On-Chain & Rugcheck Data:**
        ```json
        {rugcheck_json_str}
        ```

        **Your Analysis Instructions:**
        1.  **Narrative Risk:** Evaluate the name, symbol, and description. Generic, low-effort, or scam-sounding names (e.g., 'SafeEarn') increase the risk score. Creative and unique narratives have lower risk.
        2.  **Security Risk:** Analyze the technical safety.
            - Start with a low score.
            - **ADD 40 points** if `mintAuthority` is NOT `null`.
            - **ADD 40 points** if `freezeAuthority` is NOT `null`.
            - **ADD 50 points** if `lpLockedPct` in the `markets` section is less than 95.
            - The `rugged: false` field is a positive signal and should contribute to a lower score.
        3.  **Distribution Risk:** Analyze `topHolders`.
            - A high percentage (>25%) in the top holder is a major risk.
            - Significant concentration in the top 5 wallets also increases the risk score substantially.
            - Wallets owned by '1111...' are burn addresses; do not count them as a risk.
        4.  **Overall Risk:** Provide a holistic `overall_risk_score` based on a weighted assessment of the above factors.

        **Output Format:**
        Provide your response as a single, valid JSON object with the following structure:
        {{
        "narrative_risk_score": <integer, 1-100, risk from the name/idea>,
        "security_risk_score": <integer, 1-100, risk from authorities/LP>,
        "distribution_risk_score": <integer, 1-100, risk from holder concentration>,
        "overall_risk_score": <integer, 1-100, your final holistic risk assessment>,
        "summary": "<A one-sentence summary of your findings and final risk score>",
        "red_flags": ["<List any identified risks, like 'High holder concentration'>"],
        "green_flags": ["<List any positive signals, like 'Mint authority is renounced'>"]
        }}
        """
        return await self._query_ollama(prompt)

async def fetch_metadata_from_uri(uri: str) -> dict:
    """Fetches and parses the JSON metadata from a given URI."""
    if not uri or not uri.startswith('http'):
        return {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(uri)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"⚠️  Could not fetch metadata from URI ({uri}): {e}")
        return {}

async def main():
    """Main function to run the analysis from the command line."""
    parser = argparse.ArgumentParser(description="Analyze a meme coin's 'vibe' and fundamentals using an LLM.")
    parser.add_argument("mint", type=str, help="The mint address of the token to analyze.")
    args = parser.parse_args()

    print(f"🔎 Analyzing token: {args.mint}")

    db_conn = None
    try:
        # 1. Connect to the database
        print(f"🔌 Connecting to database '{DB_DATABASE}' on '{DB_HOST}'...")
        db_conn = await asyncpg.connect(dsn=DB_URL)
        print("✅ Database connected.")

        # 2. Fetch data from the database
        print("📊 Fetching token and rugcheck data...")
        token_query = "SELECT name, symbol, uri FROM tokens WHERE mint = $1"
        rugcheck_query = "SELECT full_data FROM rugcheck WHERE mint = $1 ORDER BY last_checked DESC LIMIT 1"

        token_record = await db_conn.fetchrow(token_query, args.mint)
        rugcheck_record = await db_conn.fetchrow(rugcheck_query, args.mint)

        if not token_record:
            print(f"❌ Error: Token with mint '{args.mint}' not found in the 'tokens' table.")
            return
        if not rugcheck_record:
            print(f"❌ Error: No rugcheck data found for mint '{args.mint}'.")
            return

        # 3. Prepare data for the LLM
        # The rugcheck data is stored as a JSON string, so we need to parse it
        rugcheck_data = json.loads(rugcheck_record['full_data'])

        # Fetch the description from the metadata URI
        metadata_from_uri = await fetch_metadata_from_uri(token_record['uri'])

        metadata = {
            "name": token_record['name'],
            "symbol": token_record['symbol'],
            "description": metadata_from_uri.get('description', '') # Get desc from fetched metadata
        }
        print("✅ Data fetched and prepared.")

        # 4. Run the analysis
        ollama_handler = OllamaHandler()
        analysis_result = await ollama_handler.analyze_meme_fundamentals(metadata, rugcheck_data)

        # 5. Print the result
        if analysis_result:
            print("\n--- LLM Analysis Result ---")
            print(json.dumps(analysis_result, indent=2))
            print("--- End of Analysis ---")
        else:
            print("❌ Analysis failed. Could not get a valid response from the LLM.")

    except asyncpg.exceptions.PostgresError as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        if db_conn:
            await db_conn.close()
            print("\n🔌 Database connection closed.")

if __name__ == "__main__":
    # This block allows the script to be executed directly
    # Example usage: python connectors/ollama_handler.py YOUR_MINT_ADDRESS_HERE
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAnalysis cancelled by user.")