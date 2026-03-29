"""
core/scorer.py
--------------
Scores a single skill based on the user's current proficiency and live market data.
Produces demand, gap, risk, reward, and ROI metrics used by the portfolio engine.
"""
from config import DEMAND_WEIGHT, EFFORT_WEIGHT, SALARY_WEIGHT


def score_skill(skill_name: str, current_level: int, market_data: dict) -> dict:
    """
    Score a skill for investment potential.

    Parameters
    ----------
    skill_name : str
        Human-readable skill identifier (e.g. "Python", "Kubernetes").
    current_level : int
        User's self-rated proficiency on a 1-10 scale.
    market_data : dict
        Dict returned by scrape_skill_demand() for this skill.
        Accepts either "market_demand_score" or "demand_score" (0-10).

    Returns
    -------
    dict
        {
            "skill_name"          : str,
            "current_level"       : int,
            "demand_score"        : float,
            "market_demand_score" : float,   # alias — required by charts
            "gap_score"           : float,
            "risk_score"          : float,
            "reward_score"        : float,
            "roi_ratio"           : float,
        }
    """
    if not (1 <= current_level <= 10):
        raise ValueError(
            f"current_level must be between 1 and 10, got {current_level!r}"
        )

    # Accept either key name from market data
    demand_score: float = float(
        market_data.get("market_demand_score")
        or market_data.get("demand_score")
        or 5.0
    )

    gap_score: float = (10 - current_level) * (demand_score / 10)

    risk_score: float = round(10 - demand_score + (current_level * 0.3), 2)

    reward_score: float = round(
        (demand_score * DEMAND_WEIGHT)
        + (gap_score * EFFORT_WEIGHT)
        + (current_level * SALARY_WEIGHT),
        2,
    )

    roi_ratio: float = round(reward_score / max(risk_score, 0.1), 2)

    return {
        "skill_name": skill_name,
        "current_level": current_level,
        "demand_score": demand_score,
        "market_demand_score": demand_score,   # charts expect this key
        "gap_score": round(gap_score, 2),
        "risk_score": risk_score,
        "reward_score": reward_score,
        "roi_ratio": roi_ratio,
    }