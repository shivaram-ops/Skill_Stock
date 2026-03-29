import json
import re

import requests

from config import (
    FEATHERLESS_API_KEY,
    FEATHERLESS_BASE_URL,
    MAX_TOKENS,
    MODEL_ID,
    TEMPERATURE,
)

_SYSTEM_PROMPT = """You are a career investment analyst. Treat skills exactly like financial assets. \
Analyze the user's skill portfolio against real-time market data. \
Return ONLY valid JSON, no explanation, no markdown. JSON schema:
{
  "portfolio": [
    {
      "skill": string,
      "current_level": int (1-10),
      "market_demand_score": float (0-10),
      "risk_score": float (0-10, higher = more risky/volatile),
      "reward_score": float (0-10, higher = better ROI),
      "recommended_hours_per_week": int,
      "action": one of ["invest_more", "maintain", "reduce", "exit"],
      "reason": string (one sentence)
    }
  ],
  "top_recommendation": string,
  "portfolio_health": one of ["strong", "balanced", "at_risk"],
  "summary": string (2-3 sentences plain English)
}"""

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def call_llm(user_profile: dict, market_data: dict) -> dict:
    """
    Call the Featherless AI chat-completions endpoint and return a parsed
    skill-portfolio recommendation dict.

    Args:
        user_profile: Mapping describing the user's current skills and goals.
        market_data:  Real-time market signals fetched via Bright Data.

    Returns:
        Parsed portfolio dict on success, or {"error": <message>} on failure.
    """
    user_prompt = (
        f"USER PROFILE:\n{json.dumps(user_profile)}\n\n"
        f"REAL-TIME MARKET DATA:\n{json.dumps(market_data)}\n\n"
        "Return the portfolio JSON."
    )

    payload = {
        "model": MODEL_ID,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {FEATHERLESS_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{FEATHERLESS_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()

        raw_content: str = response.json()["choices"][0]["message"]["content"]

        # Strip optional ```json ... ``` fences the model may add
        clean_content = _JSON_FENCE_RE.sub("", raw_content).strip()

        return json.loads(clean_content)

    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}