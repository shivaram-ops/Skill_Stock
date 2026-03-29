"""
core/scraper.py
---------------
Scrapes live LinkedIn job counts for skills using Playwright connected
to a Bright Data remote browser over WebSocket CDP (wss:// URL).

Why Playwright instead of requests?
  LinkedIn blocks plain HTTP scrapers. Bright Data's Browser API spins up
  a real Chromium instance in the cloud, bypassing bot detection.
  We connect to it via the wss:// URL from your .env file.

Requirements:
  pip install playwright
  playwright install chromium   # only needed for local fallback
"""

import asyncio
import re
import time
from datetime import datetime

from playwright.async_api import async_playwright

from config import BRIGHTDATA_WS_URL


# ── Internal async scraper ────────────────────────────────────────────────────

async def _scrape_skill_async(skill: str) -> dict:
    """
    Open a remote Bright Data browser page, navigate to LinkedIn Jobs,
    extract the job count, and return a structured result dict.
    """
    async with async_playwright() as pw:
        # Connect to Bright Data's cloud browser over WebSocket
        browser = await pw.chromium.connect_over_cdp(BRIGHTDATA_WS_URL)
        try:
            page = await browser.new_page()

            url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={skill}&location=Worldwide"
            )
            await page.goto(url, timeout=120_000)

            # Wait for the job count element to appear
            try:
                await page.wait_for_selector(
                    ".results-context-header__job-count, "
                    ".jobs-search-results-list__subtitle",
                    timeout=15_000,
                )
            except Exception:
                pass  # Element may not appear; fall through to regex

            html = await page.content()

            # Try to extract job count
            match = re.search(r"([\d,]+)\s+(?:results|jobs)", html)
            job_count = int(match.group(1).replace(",", "")) if match else 0

        finally:
            await browser.close()

    market_demand_score = round(min(10.0, job_count / 50_000 * 10), 2)

    return {
        "skill": skill,
        "job_count": job_count,
        "market_demand_score": market_demand_score,
        "demand_score": market_demand_score,   # alias for scorer.py compat
        "action": "maintain",
        "scraped_at": datetime.now().isoformat(),
    }


async def _scrape_all_async(skills: list) -> dict:
    """Scrape all skills sequentially (1 s gap) to avoid rate limits."""
    results: dict = {}
    for i, skill in enumerate(skills):
        try:
            results[skill] = await _scrape_skill_async(skill)
        except Exception as e:
            results[skill] = {
                "skill": skill,
                "job_count": 0,
                "market_demand_score": 5.0,
                "demand_score": 5.0,
                "action": "maintain",
                "error": str(e),
                "scraped_at": datetime.now().isoformat(),
            }
        if i < len(skills) - 1:
            await asyncio.sleep(1)
    return results


# ── Public sync API (called by Gradio, which runs in a sync context) ──────────

def scrape_skill_demand(skill: str) -> dict:
    """
    Synchronous wrapper around the async Playwright scraper.
    Safe to call from Gradio event handlers.
    """
    return asyncio.run(_scrape_skill_async(skill))


def get_market_data(skills: list) -> dict:
    """
    Fetch market data for a list of skills via Playwright + Bright Data.

    Returns:
        dict mapping skill name -> result dict.
        Only skill keys — no extra 'summary' key — safe to iterate everywhere.
    """
    return asyncio.run(_scrape_all_async(skills))


def get_trending_skills() -> list:
    """Returns a hardcoded list of 15 currently trending skills."""
    return [
        "Python", "Machine Learning", "React", "AWS", "LLMs",
        "Data Engineering", "TypeScript", "Kubernetes", "Rust",
        "Prompt Engineering", "RAG", "System Design", "SQL",
        "DevOps", "Computer Vision",
    ]