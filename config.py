import os
from dotenv import load_dotenv

load_dotenv()

# Featherless AI
FEATHERLESS_API_KEY: str = os.environ["FEATHERLESS_API_KEY"]
FEATHERLESS_BASE_URL: str = "https://api.featherless.ai/v1"
MODEL_ID: str = "meta-llama/Llama-4-Scout-17B-16E-Instruct"

# Bright Data
BRIGHT_DATA_API_KEY: str = os.environ["BRIGHT_DATA_API_KEY"]
BRIGHT_DATA_ENDPOINT: str = "https://api.brightdata.com/request"

# Portfolio scoring weights (must sum to 1.0)
DEMAND_WEIGHT: float = 0.45
EFFORT_WEIGHT: float = 0.25
SALARY_WEIGHT: float = 0.30

# LLM generation settings
MAX_TOKENS: int = 1500
TEMPERATURE: float = 0.3