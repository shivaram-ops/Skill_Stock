import os
from dotenv import load_dotenv

load_dotenv()

# ── Featherless AI ────────────────────────────────────────────────────────────
FEATHERLESS_API_KEY: str = os.environ["FEATHERLESS_API_KEY"]
FEATHERLESS_BASE_URL: str = "https://api.featherless.ai/v1"
MODEL_ID: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"

# ── Bright Data (Playwright WebSocket CDP) ────────────────────────────────────
# The wss:// connection string from your Bright Data control panel.
# Format: wss://brd-customer-<id>-zone-<zone>:<pass>@brd.superproxy.io:9222
BRIGHTDATA_WS_URL: str = os.environ["BRIGHTDATA_WS_URL"]

# ── Portfolio scoring weights (must sum to 1.0) ───────────────────────────────
DEMAND_WEIGHT: float = 0.45
EFFORT_WEIGHT: float = 0.25
SALARY_WEIGHT: float = 0.30

# ── LLM generation settings ───────────────────────────────────────────────────
MAX_TOKENS: int = 1500
TEMPERATURE: float = 0.3