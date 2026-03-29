import gradio as gr
import json
import pandas as pd

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
# Helpers
# ---------------------------------------------------------------------------

def _parse_skills(skills_input: str) -> list[dict]:
    """Parse 'Python:8, SQL:6, React:4' → [{name, level}, ...]"""
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


def _empty_outputs():
    """Return a tuple of empty/placeholder values matching all portfolio outputs."""
    empty_df = pd.DataFrame(
        columns=["skill", "action", "recommended_hours_per_week",
                 "risk_score", "reward_score", "reason"]
    )
    return "", "", None, None, None, None, empty_df


def _normalize_to_list(raw_data) -> list[dict]:
    """
    Ensure market data is always a list of dicts for chart functions.

    get_market_data() returns a dict keyed by skill name.
    Iterating over a dict yields string keys → TypeError in charts.
    This function always returns a plain list of the value dicts.
    """
    if isinstance(raw_data, list):
        return [item for item in raw_data if isinstance(item, dict)]
    if isinstance(raw_data, dict):
        return [v for v in raw_data.values() if isinstance(v, dict)]
    return []


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def analyze_portfolio(name, skills_input, goal, hours, experience):
    """Main analysis function wired to the Analyze button."""

    # --- Validate inputs ---
    if not name or not name.strip():
        err = "Please enter your name."
        return (err,) + ("",) + (None,) * 4 + (pd.DataFrame(),)

    if not skills_input or not skills_input.strip():
        err = "Please enter at least one skill."
        return (err,) + ("",) + (None,) * 4 + (pd.DataFrame(),)

    # --- Parse skills ---
    skills = _parse_skills(skills_input)
    if not skills:
        err = "Could not parse skills. Use format: Python:8, SQL:6"
        return (err,) + ("",) + (None,) * 4 + (pd.DataFrame(),)

    # --- Build profile ---
    user_profile = {
        "name": name.strip(),
        "skills": skills,
        "hours_per_week": int(hours),
        "goal": goal.strip() if goal else "",
        "experience": experience or "0-2 years",
    }

    # --- Fetch market data ---
    skill_names = [s["name"] for s in user_profile["skills"]]
    try:
        market_data = get_market_data(skill_names)
    except Exception as exc:
        err = f"Market data fetch failed: {exc}"
        return (err,) + ("",) + (None,) * 4 + (pd.DataFrame(),)

    # --- Call LLM ---
    try:
        llm_result = call_llm(user_profile, market_data)
    except Exception as exc:
        err = f"LLM call failed: {exc}"
        return (err,) + ("",) + (None,) * 4 + (pd.DataFrame(),)

    if isinstance(llm_result, dict) and "error" in llm_result:
        err = f"LLM error: {llm_result['error']}"
        return (err,) + ("",) + (None,) * 4 + (pd.DataFrame(),)

    # --- Build portfolio ---
    try:
        portfolio = build_portfolio(user_profile, llm_result, market_data)
    except Exception as exc:
        err = f"Portfolio build failed: {exc}"
        return (err,) + ("",) + (None,) * 4 + (pd.DataFrame(),)

    portfolio_items = portfolio.get("portfolio", [])

    # --- Build charts ---
    donut_fig  = make_allocation_donut(portfolio_items)
    bubble_fig = make_risk_reward_bubble(portfolio_items)
    bar_fig    = make_demand_bar(portfolio_items)

    # FIX: make_health_gauge expects a string ("strong"|"balanced"|"at_risk"),
    # NOT the portfolio list. Pull it from the portfolio result dict.
    portfolio_health: str = portfolio.get("portfolio_health", "balanced")
    if not isinstance(portfolio_health, str):
        portfolio_health = "balanced"
    gauge_fig = make_health_gauge(portfolio_health)

    # --- Build dataframe ---
    df_cols = ["skill", "action", "recommended_hours_per_week",
               "risk_score", "reward_score", "reason"]
    if portfolio_items:
        # Only keep columns that actually exist to avoid KeyError
        available_cols = [c for c in df_cols if c in portfolio_items[0]]
        df = pd.DataFrame(portfolio_items)[available_cols]
    else:
        df = pd.DataFrame(columns=df_cols)

    top_recommendation = portfolio.get("top_recommendation", "—")
    summary            = portfolio.get("summary", "—")

    return top_recommendation, summary, donut_fig, bubble_fig, bar_fig, gauge_fig, df


def scrape_market(skills_text):
    """Scrape live market data for the given comma-separated skills."""
    if not skills_text or not skills_text.strip():
        return pd.DataFrame(), None

    skills_list = [s.strip() for s in skills_text.split(",") if s.strip()]
    if not skills_list:
        return pd.DataFrame(), None

    try:
        raw_data = get_market_data(skills_list)
    except Exception as exc:
        error_df = pd.DataFrame({"error": [str(exc)]})
        return error_df, None

    # FIX: normalize dict → list of dicts before building df and chart
    data_list = _normalize_to_list(raw_data)

    df = pd.DataFrame(data_list) if data_list else pd.DataFrame()
    bar_fig = make_demand_bar(data_list) if data_list else None

    return df, bar_fig


# ---------------------------------------------------------------------------
# Theme  (defined once, passed to launch() — Gradio 6.0 requirement)
# ---------------------------------------------------------------------------

theme = gr.themes.Base(
    primary_hue="slate",
    secondary_hue="zinc",
    neutral_hue="zinc",
    font=[gr.themes.GoogleFont("IBM Plex Mono"), "monospace"],
    font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "monospace"],
).set(
    body_background_fill="#0f1117",
    body_background_fill_dark="#0f1117",
    body_text_color="#d1d5db",
    body_text_color_dark="#d1d5db",
    block_background_fill="#1a1d27",
    block_background_fill_dark="#1a1d27",
    block_border_color="#2e3147",
    block_border_width="1px",
    block_label_text_color="#6b7280",
    block_label_text_size="sm",
    input_background_fill="#12141e",
    input_background_fill_dark="#12141e",
    input_border_color="#2e3147",
    input_border_color_focus="#4f6bff",
    button_primary_background_fill="#4f6bff",
    button_primary_background_fill_hover="#3d57e8",
    button_primary_text_color="#ffffff",
    button_secondary_background_fill="#1e2130",
    button_secondary_background_fill_hover="#252840",
    button_secondary_text_color="#9ca3af",
    slider_color="#4f6bff",
    table_even_background_fill="#1a1d27",
    table_odd_background_fill="#12141e",
    table_border_color="#2e3147",
)

CUSTOM_CSS = """
/* ── App shell ── */
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding: 0 !important;
}
#app-header {
    background: #1a1d27;
    border-bottom: 1px solid #2e3147;
    padding: 20px 32px;
    display: flex;
    align-items: baseline;
    gap: 14px;
}
#app-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 15px;
    font-weight: 600;
    color: #e5e7eb;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
#app-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4b5563;
    letter-spacing: 0.06em;
}
.tab-nav button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: #6b7280 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 12px 20px !important;
    background: transparent !important;
}
.tab-nav button.selected {
    color: #e5e7eb !important;
    border-bottom-color: #4f6bff !important;
}
.tab-nav button:hover:not(.selected) { color: #9ca3af !important; }
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4b5563;
    padding: 0 0 8px 0;
    border-bottom: 1px solid #1e2130;
    margin-bottom: 4px;
}
#top-rec textarea {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    color: #a5b4fc !important;
    background: #12141e !important;
    border-color: #312e81 !important;
}
.gradio-dataframe table {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
}
.gradio-dataframe th {
    background: #12141e !important;
    color: #6b7280 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-size: 10px !important;
}
.status-msg {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #ef4444;
    padding: 6px 0;
}
"""

# ---------------------------------------------------------------------------
# UI  — theme/css NOT passed to gr.Blocks (Gradio 6.0 moved them to launch())
# ---------------------------------------------------------------------------

with gr.Blocks(title="Skill Portfolio Engine") as app:

    gr.HTML("""
    <div id="app-header">
        <span id="app-title">Skill Portfolio Engine</span>
        <span id="app-subtitle">v1.0 · internal tool</span>
    </div>
    """)

    with gr.Tabs(elem_classes="tab-nav"):

        # ── Tab 1: My Profile ──────────────────────────────────────────────
        with gr.Tab("My Profile"):
            gr.HTML('<div class="section-label">Identity</div>')

            with gr.Row():
                name_input = gr.Textbox(
                    label="Your name", placeholder="e.g. Arjun", scale=1,
                )
                experience_input = gr.Radio(
                    label="Experience level",
                    choices=["Student", "0-2 years", "2-5 years", "5+ years"],
                    value="0-2 years",
                    scale=2,
                )

            gr.HTML('<div class="section-label" style="margin-top:16px">Skills & Goal</div>')

            skills_input = gr.Textbox(
                label="Your skills (comma separated with levels)",
                placeholder="Python:8, SQL:6, React:4, AWS:3",
                lines=2,
            )
            goal_input = gr.Textbox(
                label="Career goal",
                placeholder="e.g. Become a senior ML engineer in 2 years",
            )

            gr.HTML('<div class="section-label" style="margin-top:16px">Availability</div>')

            hours_input = gr.Slider(
                label="Hours available per week for learning",
                minimum=2, maximum=40, step=1, value=10,
            )

            analyze_btn = gr.Button("Analyze my portfolio", variant="primary", size="lg")

        # ── Tab 2: My Portfolio ────────────────────────────────────────────
        with gr.Tab("My Portfolio"):
            gr.HTML('<div class="section-label">Recommendations</div>')

            top_rec_output = gr.Textbox(
                label="Top recommendation", interactive=False, elem_id="top-rec",
            )
            summary_output = gr.Textbox(
                label="Portfolio summary", interactive=False, lines=3,
            )

            gr.HTML('<div class="section-label" style="margin-top:20px">Visualisations</div>')

            with gr.Row():
                donut_plot  = gr.Plot(label="Time Allocation")
                bubble_plot = gr.Plot(label="Risk / Reward")

            with gr.Row():
                bar_plot   = gr.Plot(label="Market Demand")
                gauge_plot = gr.Plot(label="Portfolio Health")

            gr.HTML('<div class="section-label" style="margin-top:20px">Full Portfolio Table</div>')

            portfolio_df = gr.Dataframe(
                headers=["skill", "action", "recommended_hours_per_week",
                         "risk_score", "reward_score", "reason"],
                interactive=False,
                wrap=True,
            )

        # ── Tab 3: Market Data ─────────────────────────────────────────────
        with gr.Tab("Market Data"):
            gr.HTML('<div class="section-label">Live Scrape</div>')

            market_skills_input = gr.Textbox(
                label="Skills to check (comma separated)",
                placeholder="Python, Rust, LLMs",
            )
            scrape_btn = gr.Button("Scrape live market data", variant="secondary")

            gr.HTML('<div class="section-label" style="margin-top:20px">Raw Results</div>')
            market_df = gr.Dataframe(interactive=False, wrap=True)

            gr.HTML('<div class="section-label" style="margin-top:20px">Demand Chart</div>')
            market_bar_plot = gr.Plot(label="Skill Demand (scraped)")

    # ── Event wiring ────────────────────────────────────────────────────────

    analyze_btn.click(
        fn=analyze_portfolio,
        inputs=[name_input, skills_input, goal_input, hours_input, experience_input],
        outputs=[
            top_rec_output, summary_output,
            donut_plot, bubble_plot, bar_plot, gauge_plot,
            portfolio_df,
        ],
    )

    scrape_btn.click(
        fn=scrape_market,
        inputs=[market_skills_input],
        outputs=[market_df, market_bar_plot],
    )

# ---------------------------------------------------------------------------
# Launch — theme and css go here in Gradio 6.0
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.launch(theme=theme, css=CUSTOM_CSS)