import plotly.graph_objects as go
import plotly.express as px

# ── Shared design tokens ──────────────────────────────────────────────────────
_PALETTE = [
    "#4361ee", "#3a0ca3", "#7209b7", "#f72585",
    "#4cc9f0", "#06d6a0", "#ffd166", "#ef476f",
]

_ACTION_COLORS = {
    "invest_more": "#06d6a0",
    "maintain":    "#4361ee",
    "reduce":      "#ffd166",
    "exit":        "#ef476f",
}

_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=13),
)


# ── 1. Allocation donut ───────────────────────────────────────────────────────
def make_allocation_donut(portfolio: list) -> go.Figure:
    """
    Donut chart showing recommended_hours_per_week per skill.

    Args:
        portfolio: list of dicts, each containing at least:
                   'skill' (str) and 'recommended_hours_per_week' (float/int).

    Returns:
        plotly.graph_objects.Figure
    """
    labels = [item["skill"] for item in portfolio]
    values = [item["recommended_hours_per_week"] for item in portfolio]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            marker=dict(colors=_PALETTE[: len(labels)]),
            textinfo="label+percent",
            textposition="auto",
            hovertemplate="<b>%{label}</b><br>Hours/week: %{value}<br>Share: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Weekly time allocation", x=0.5, xanchor="center"),
        annotations=[
            dict(
                text="Hours/week",
                x=0.5,
                y=0.5,
                font=dict(family="Inter, sans-serif", size=13),
                showarrow=False,
            )
        ],
        showlegend=True,
    )

    return fig


# ── 2. Risk-reward bubble ─────────────────────────────────────────────────────
def make_risk_reward_bubble(portfolio: list) -> go.Figure:
    """
    Scatter/bubble chart: x=risk_score, y=reward_score,
    size=market_demand_score*5, color=action.

    Args:
        portfolio: list of dicts, each containing at least:
                   'skill', 'risk_score', 'reward_score',
                   'market_demand_score', 'action'.

    Returns:
        plotly.graph_objects.Figure
    """
    # Group by action so each action gets a single legend entry
    traces_by_action: dict[str, dict] = {}
    for item in portfolio:
        action = item["action"]
        if action not in traces_by_action:
            traces_by_action[action] = dict(
                x=[], y=[], sizes=[], texts=[], name=action,
                color=_ACTION_COLORS.get(action, "#4361ee"),
            )
        traces_by_action[action]["x"].append(item["risk_score"])
        traces_by_action[action]["y"].append(item["reward_score"])
        traces_by_action[action]["sizes"].append(item["market_demand_score"] * 5)
        traces_by_action[action]["texts"].append(item["skill"])

    fig = go.Figure()

    for action, grp in traces_by_action.items():
        fig.add_trace(
            go.Scatter(
                x=grp["x"],
                y=grp["y"],
                mode="markers+text",
                name=action.replace("_", " ").title(),
                text=grp["texts"],
                textposition="top center",
                marker=dict(
                    size=grp["sizes"],
                    color=grp["color"],
                    opacity=0.85,
                    line=dict(width=1, color="rgba(255,255,255,0.4)"),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Risk: %{x}<br>"
                    "Reward: %{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Quadrant guide lines
    line_style = dict(color="gray", width=1, dash="dash")
    fig.add_hline(y=5, line=dict(**line_style), opacity=0.3)
    fig.add_vline(x=5, line=dict(**line_style), opacity=0.3)

    # Quadrant labels
    _quad_labels = [
        dict(x=1.0,  y=10.5, text="High reward  low risk"),
        dict(x=7.5,  y=10.5, text="High reward  high risk"),
        dict(x=1.0,  y=0.3,  text="Low reward  low risk"),
        dict(x=7.5,  y=0.3,  text="Low reward  high risk"),
    ]
    annotations = [
        dict(
            x=q["x"], y=q["y"],
            text=q["text"],
            showarrow=False,
            font=dict(size=11, color="gray"),
            xref="x", yref="y",
        )
        for q in _quad_labels
    ]

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Risk vs reward matrix", x=0.5, xanchor="center"),
        xaxis=dict(title="Risk score",   range=[0, 11], showgrid=False),
        yaxis=dict(title="Reward score", range=[0, 11], showgrid=False),
        annotations=annotations,
        legend=dict(title="Action"),
    )

    return fig


# ── 3. Market demand horizontal bar ──────────────────────────────────────────
def make_demand_bar(portfolio: list) -> go.Figure:
    """
    Horizontal bar chart of market_demand_score per skill, colored by action,
    sorted ascending so the highest score appears on top.

    Args:
        portfolio: list of dicts, each containing at least:
                   'skill', 'market_demand_score', 'action'.

    Returns:
        plotly.graph_objects.Figure
    """
    # Sort ascending by demand score (Plotly renders bottom-to-top for 'h' bars)
    sorted_items = sorted(portfolio, key=lambda d: d["market_demand_score"])

    skills  = [item["skill"]               for item in sorted_items]
    scores  = [item["market_demand_score"] for item in sorted_items]
    colors  = [_ACTION_COLORS.get(item["action"], "#4361ee") for item in sorted_items]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=skills,
            orientation="h",
            marker=dict(color=colors),
            text=scores,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Demand score: %{x}<extra></extra>",
        )
    )

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Real-time market demand", x=0.5, xanchor="center"),
        xaxis=dict(title="Market demand score", range=[0, 11], showgrid=False),
        yaxis=dict(showgrid=False),
        showlegend=False,
    )

    return fig


# ── 4. Portfolio health gauge ─────────────────────────────────────────────────
def make_health_gauge(portfolio_health: str) -> go.Figure:
    """
    Gauge indicator for overall portfolio health.

    Args:
        portfolio_health: one of 'strong', 'balanced', or 'at_risk'.

    Returns:
        plotly.graph_objects.Figure
    """
    _health_map = {
        "strong":   85,
        "balanced": 60,
        "at_risk":  30,
    }
    value = _health_map.get(portfolio_health, 60)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title=dict(
                text="Portfolio health score",
                font=dict(family="Inter, sans-serif", size=13),
            ),
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color="#4361ee"),
                steps=[
                    dict(range=[0,  40], color="#ef476f"),   # red
                    dict(range=[40, 70], color="#ffd166"),   # yellow
                    dict(range=[70, 100], color="#06d6a0"),  # green
                ],
                threshold=dict(
                    line=dict(color="white", width=2),
                    thickness=0.75,
                    value=value,
                ),
            ),
        )
    )

    fig.update_layout(
        **_BASE_LAYOUT,
        margin=dict(t=80, b=30, l=30, r=30),
    )

    return fig