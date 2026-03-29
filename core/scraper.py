import requests
import re
import time
from datetime import datetime
from config import BRIGHT_DATA_API_KEY, BRIGHT_DATA_ENDPOINT


def scrape_skill_demand(skill: str) -> dict:
    """
    Scrapes real-time job market data for a given skill using the Bright Data API.

    Args:
        skill: The skill to search for on LinkedIn Jobs

    Returns:
        dict with skill, job_count, market_demand_score, and scraped_at timestamp.
        NOTE: key is 'market_demand_score' (0-10) to match chart/portfolio expectations.
    """
    try:
        headers = {
            "Authorization": f"Bearer {BRIGHT_DATA_API_KEY}",
            "Content-Type": "application/json",
        }

        body = {
            "url": f"https://www.linkedin.com/jobs/search/?keywords={skill}&location=Worldwide",
            "format": "raw_html",
        }

        response = requests.post(BRIGHT_DATA_ENDPOINT, headers=headers, json=body)
        response.raise_for_status()

        html_content = response.text

        # Extract job count using regex
        match = re.search(r"([\d,]+)\s+(?:results|jobs)", html_content)
        if match:
            job_count = int(match.group(1).replace(",", ""))
        else:
            job_count = 0

        market_demand_score = round(min(10.0, job_count / 50000 * 10), 2)

        return {
            "skill": skill,
            "job_count": job_count,
            "market_demand_score": market_demand_score,  # unified key name
            "demand_score": market_demand_score,          # kept for scorer.py compat
            "action": "maintain",                         # default; overridden by LLM
            "scraped_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "skill": skill,
            "job_count": 0,
            "market_demand_score": 5.0,
            "demand_score": 5.0,
            "action": "maintain",
            "error": str(e),
            "scraped_at": datetime.now().isoformat(),
        }


def get_market_data(skills: list) -> dict:
    """
    Fetches market data for a list of skills.

    Returns:
        dict mapping skill name → result dict (NO extra 'summary' key —
        that key broke downstream iteration over the dict).
    """
    results: dict = {}

    for i, skill in enumerate(skills):
        results[skill] = scrape_skill_demand(skill)
        if i < len(skills) - 1:
            time.sleep(1)

    return results          # clean: only skill keys, no 'summary' pollution


def get_trending_skills() -> list:
    """Returns a hardcoded list of 15 currently trending skills."""
    return [
        "Python", "Machine Learning", "React", "AWS", "LLMs",
        "Data Engineering", "TypeScript", "Kubernetes", "Rust",
        "Prompt Engineering", "RAG", "System Design", "SQL",
        "DevOps", "Computer Vision",
    ]