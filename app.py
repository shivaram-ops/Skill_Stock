"""
app.py  —  Skill Portfolio Engine (Streamlit UI)
Run with:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from core.llm import call_llm
from core.scraper import get_market_data, get_trending_skills
from core.portfolio import build_portfolio
from ui.charts import (
    make_allocation_donut,
    make_risk_reward_bubble,
    make_demand_bar,
    make_health_gauge,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Skill Portfolio Engine",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace !important;
    background-color: #0f1117;
    color: #d1d5db;
}

/* Header */
.app-header {
    background: #1a1d27;
    border-bottom: 1px solid #2e3147;
    padding: 20px 32px;
    margin: -1rem -1rem 2rem -1rem;
    display: flex;
    align-items: baseline;
    gap: 14px;
}
.app-title {
    font-size: 15px;
    font-weight: 600;
    color: #e5e7eb;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.app-subtitle {
    font-size: 11px;
    color: #4b5563;
    letter-spacing: 0.06em;
}

/* Section labels */
.section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4b5563;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2130;
    margin-bottom: 12px;
    margin-top: 24px;
}

/* Streamlit elements */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #12141e !important;
    border-color: #2e3147 !important;
    color: #d1d5db !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
.stSlider > div { color: #d1d5db; }
.stRadio > div { color: #d1d5db; }
.stButton > button {
    background: #4f6bff;
    color: white;
    border: none;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    padding: 10px 24px;
    border-radius: 6px;
    width: 100%;
}
.stButton > button:hover { background: #3d57e8; }

/* Top recommendation box */
.rec-box {
    background: #12141e;
    border: 1px solid #312e81;
    border-radius: 8px;
    padding: 16px 20px;
    color: #a5b4fc;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    margin-bottom: 12px;
}

/* Error box */
.err-box {
    background: #1a0a0a;
    border: 1px solid #7f1d1d;
    border-radius: 8px;
    padding: 12px 16px;
    color: #ef4444;
    font-size: 12px;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="app-header">
    <span class="app-title">Skill Portfolio Engine</span>
    <span class="app-subtitle">v1.0 · internal tool</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_skills(skills_input: str) -> list[dict]:
    skills = []
    for item in skills_input.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            parts = item.rsplit(":", 1)
            name = parts[0].strip()
            try:
                level = int(float(parts[1].strip()))
            except ValueError:
                level = 5
        else:
            name = item
            level = 5
        if name:
            skills.append({"name": name, "level": level})
    return skills


def _normalize_to_list(raw_data) -> list[dict]:
    if isinstance(raw_data, list):
        return [item for item in raw_data if isinstance(item, dict)]
    if isinstance(raw_data, dict):
        return [v for v in raw_data.values() if isinstance(v, dict)]
    return []

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs(["My Profile", "My Portfolio", "Market Data"])

# ===========================================================================
# TAB 1 — My Profile
# ===========================================================================

with tab1:
    st.markdown('<div class="section-label">Identity</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        name_input = st.text_input("Your name", placeholder="e.g. Arjun")
    with col2:
        experience_input = st.radio(
            "Experience level",
            ["Student", "0-2 years", "2-5 years", "5+ years"],
            index=1,
            horizontal=True,
        )

    st.markdown('<div class="section-label">Skills & Goal</div>', unsafe_allow_html=True)

    skills_input = st.text_area(
        "Your skills (comma separated with levels)",
        placeholder="Python:8, SQL:6, React:4, AWS:3",
        height=80,
    )
    goal_input = st.text_input(
        "Career goal",
        placeholder="e.g. Become a senior ML engineer in 2 years",
    )

    st.markdown('<div class="section-label">Availability</div>', unsafe_allow_html=True)

    hours_input = st.slider("Hours available per week for learning", 2, 40, 10)

    analyze_clicked = st.button("Analyze my portfolio", type="primary")

    if analyze_clicked:
        # Validate
        if not name_input.strip():
            st.error("Please enter your name.")
        elif not skills_input.strip():
            st.error("Please enter at least one skill.")
        else:
            skills = _parse_skills(skills_input)
            if not skills:
                st.error("Could not parse skills. Use format: Python:8, SQL:6")
            else:
                user_profile = {
                    "name": name_input.strip(),
                    "skills": skills,
                    "hours_per_week": int(hours_input),
                    "goal": goal_input.strip(),
                    "experience": experience_input,
                }

                skill_names = [s["name"] for s in skills]

                with st.spinner("Fetching market data..."):
                    try:
                        market_data = get_market_data(skill_names)
                    except Exception as e:
                        st.error(f"Market data fetch failed: {e}")
                        st.stop()

                with st.spinner("Analyzing with LLM..."):
                    try:
                        llm_result = call_llm(user_profile, market_data)
                    except Exception as e:
                        st.error(f"LLM call failed: {e}")
                        st.stop()

                    if isinstance(llm_result, dict) and "error" in llm_result:
                        st.error(f"LLM error: {llm_result['error']}")
                        st.stop()

                with st.spinner("Building portfolio..."):
                    try:
                        portfolio = build_portfolio(user_profile, llm_result, market_data)
                    except Exception as e:
                        st.error(f"Portfolio build failed: {e}")
                        st.stop()

                # Store results in session state so Tab 2 can read them
                st.session_state["portfolio"] = portfolio
                st.session_state["portfolio_items"] = portfolio.get("portfolio", [])
                st.success("Done! Switch to the 'My Portfolio' tab to see your results.")

# ===========================================================================
# TAB 2 — My Portfolio
# ===========================================================================

with tab2:
    if "portfolio" not in st.session_state:
        st.info("Fill in your profile on the 'My Profile' tab and click Analyze.")
    else:
        portfolio       = st.session_state["portfolio"]
        portfolio_items = st.session_state["portfolio_items"]

        st.markdown('<div class="section-label">Recommendations</div>', unsafe_allow_html=True)

        top_rec = portfolio.get("top_recommendation", "—")
        summary = portfolio.get("summary", "—")

        st.markdown(f'<div class="rec-box"><b>Top recommendation</b><br>{top_rec}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="rec-box"><b>Portfolio summary</b><br>{summary}</div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="section-label">Visualisations</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_allocation_donut(portfolio_items),
                            use_container_width=True)
        with col2:
            st.plotly_chart(make_risk_reward_bubble(portfolio_items),
                            use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(make_demand_bar(portfolio_items),
                            use_container_width=True)
        with col4:
            portfolio_health = portfolio.get("portfolio_health", "balanced")
            if not isinstance(portfolio_health, str):
                portfolio_health = "balanced"
            st.plotly_chart(make_health_gauge(portfolio_health),
                            use_container_width=True)

        st.markdown('<div class="section-label">Full Portfolio Table</div>',
                    unsafe_allow_html=True)

        df_cols = ["skill", "action", "recommended_hours_per_week",
                   "risk_score", "reward_score", "reason"]
        if portfolio_items:
            available_cols = [c for c in df_cols if c in portfolio_items[0]]
            df = pd.DataFrame(portfolio_items)[available_cols]
        else:
            df = pd.DataFrame(columns=df_cols)

        st.dataframe(df, use_container_width=True)

# ===========================================================================
# TAB 3 — Market Data
# ===========================================================================

with tab3:
    st.markdown('<div class="section-label">Live Scrape</div>', unsafe_allow_html=True)

    market_skills_input = st.text_input(
        "Skills to check (comma separated)",
        placeholder="Python, Rust, LLMs",
    )
    scrape_clicked = st.button("Scrape live market data")

    if scrape_clicked:
        if not market_skills_input.strip():
            st.error("Please enter at least one skill.")
        else:
            skills_list = [s.strip() for s in market_skills_input.split(",") if s.strip()]
            with st.spinner("Scraping..."):
                try:
                    raw_data = get_market_data(skills_list)
                except Exception as e:
                    st.error(f"Scrape failed: {e}")
                    st.stop()

            data_list = _normalize_to_list(raw_data)

            st.markdown('<div class="section-label">Raw Results</div>',
                        unsafe_allow_html=True)
            if data_list:
                st.dataframe(pd.DataFrame(data_list), use_container_width=True)
            else:
                st.warning("No data returned.")

            st.markdown('<div class="section-label">Demand Chart</div>',
                        unsafe_allow_html=True)
            if data_list:
                st.plotly_chart(make_demand_bar(data_list), use_container_width=True)