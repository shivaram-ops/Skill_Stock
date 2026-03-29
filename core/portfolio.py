"""
core/portfolio.py
-----------------
Builds a prioritised, hour-scaled Skill Investment Portfolio by combining:
  - the LLM's strategic recommendations  (llm_result)
  - live market demand data              (market_data)
  - scorer metrics for every skill       (core.scorer)
  - the user's weekly capacity           (user_profile)
"""

from __future__ import annotations

from typing import Any

from core.scorer import score_skill


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

def build_portfolio(
    user_profile: dict[str, Any],
    llm_result: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Assemble, score, sort and hour-scale a personalised skill portfolio.

    Parameters
    ----------
    user_profile : dict
        Keys expected:
            name            – str, the user's display name
            skills          – list[dict] with keys "name" (str) and "level" (int 1-10)
            hours_per_week  – int/float, total weekly learning capacity
            goal            – str, the user's stated career goal
    llm_result : dict
        JSON dict returned by call_llm(). Expected keys:
            portfolio             – list[dict], each item has at minimum:
                                      "skill"                     : str
                                      "action"                    : str  ("invest_more" | "maintain" | "reduce" | "exit")
                                      "recommended_hours_per_week": float
            top_recommendation    – str
            portfolio_health      – str | dict
            summary               – str
    market_data : dict
        Dict returned by get_market_data(). Keyed by skill name (case-sensitive),
        each value is a dict as returned by scrape_skill_demand().

    Returns
    -------
    dict
        {
            "user_name"           : str,
            "portfolio"           : list[dict],   # sorted by reward_score desc
            "top_recommendation"  : str,
            "portfolio_health"    : str | dict,
            "summary"             : str,
            "total_hours_per_week": float,
            "skills_to_invest"    : list[str],
            "skills_to_exit"      : list[str],
        }

    Raises
    ------
    KeyError
        If required keys are missing from user_profile or llm_result.
    """
    # ------------------------------------------------------------------ #
    # 1. Resolve current proficiency for every skill in the LLM portfolio #
    # ------------------------------------------------------------------ #
    # Build a fast lookup from the user's self-rated skill list
    user_level_map: dict[str, int] = {
        s["name"]: s["level"] for s in user_profile.get("skills", [])
    }

    portfolio: list[dict[str, Any]] = []

    for skill_entry in llm_result["portfolio"]:
        skill_name: str = skill_entry["skill"]

        # Fall back to level 5 (mid-range) if the user didn't rate this skill
        current_level: int = user_level_map.get(skill_name, 5)

        # Pull the matching market data slice (fall back to empty dict → defaults)
        skill_market: dict = market_data.get(skill_name, {})

        # ---------------------------------------------------------------- #
        # 2. Enrich each entry with scorer metrics                          #
        # ---------------------------------------------------------------- #
        scorer_result = score_skill(skill_name, current_level, skill_market)

        enriched = {**skill_entry, **scorer_result}
        portfolio.append(enriched)

    # ------------------------------------------------------------------ #
    # 3. Sort by reward_score descending (highest value opportunity first) #
    # ------------------------------------------------------------------ #
    portfolio.sort(key=lambda s: s["reward_score"], reverse=True)

    # ------------------------------------------------------------------ #
    # 4. Scale hours to fit the user's weekly capacity                    #
    # ------------------------------------------------------------------ #
    total_recommended_hours: float = sum(
        s.get("recommended_hours_per_week", 0) for s in portfolio
    )

    weekly_capacity: float = float(user_profile["hours_per_week"])

    if total_recommended_hours > weekly_capacity and total_recommended_hours > 0:
        scale_factor = weekly_capacity / total_recommended_hours
        for skill in portfolio:
            raw = skill.get("recommended_hours_per_week", 0)
            skill["recommended_hours_per_week"] = round(raw * scale_factor, 2)

        # Recalculate total after scaling (should equal capacity)
        total_recommended_hours = weekly_capacity

    # ------------------------------------------------------------------ #
    # 5. Add allocation_pct to each skill                                 #
    # ------------------------------------------------------------------ #
    denominator = total_recommended_hours if total_recommended_hours > 0 else 1.0
    for skill in portfolio:
        hours = skill.get("recommended_hours_per_week", 0)
        skill["allocation_pct"] = round((hours / denominator) * 100, 2)

    # ------------------------------------------------------------------ #
    # 6. Derive invest / exit lists                                       #
    # ------------------------------------------------------------------ #
    EXIT_ACTIONS = {"reduce", "exit"}

    skills_to_invest: list[str] = [
        s["skill"] for s in portfolio if s.get("action") == "invest_more"
    ]
    skills_to_exit: list[str] = [
        s["skill"] for s in portfolio if s.get("action") in EXIT_ACTIONS
    ]

    # ------------------------------------------------------------------ #
    # 7. Assemble and return the final portfolio dict                     #
    # ------------------------------------------------------------------ #
    return {
        "user_name": user_profile["name"],
        "portfolio": portfolio,
        "top_recommendation": llm_result["top_recommendation"],
        "portfolio_health": llm_result["portfolio_health"],
        "summary": llm_result["summary"],
        "total_hours_per_week": weekly_capacity,
        "skills_to_invest": skills_to_invest,
        "skills_to_exit": skills_to_exit,
    }