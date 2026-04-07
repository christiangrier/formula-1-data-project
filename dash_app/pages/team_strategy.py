"""
Dashboard 3 — Team Strategy
Grid: 40% | 60%, both columns span both rows.
• Col 1 (hero): Pit Stop Timeline — Gantt per team
• Col 2 (hero): Tyre Degradation Curves — per compound, with team dropdown
"""
import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import numpy as np
import pandas as pd

from data.queries import (
    COMPOUND_COLORS,
    get_race_results,
    get_pit_stops_for_race,
    get_tyre_strategy,
    get_tyre_degradation_all,
)

dash.register_page(__name__, path="/team-strategy", name="Team Strategy")

# ── Design tokens ──────────────────────────────────────────────────────────────
BG_PANEL = "#1A1A1A"
BG_P2    = "#242424"
BORDER   = "#2E2E2E"
TEXT_PRI = "#F0F0F0"
TEXT_SEC = "#9A9A9A"

CONTENT_H = "calc(100vh - 44px)"

CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT_PRI, size=10),
    margin=dict(l=8, r=8, t=28, b=8),
)

_LEGEND = dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0)", font=dict(size=9))

GRAPH_CFG = {"displayModeBar": False, "responsive": True}


def _panel(children, style_extra=None):
    s = {
        "backgroundColor": BG_PANEL,
        "border": f"0.5px solid {BORDER}",
        "borderRadius": "8px",
        "padding": "12px",
        "overflow": "hidden",
    }
    if style_extra:
        s.update(style_extra)
    return html.Div(children, style=s)


def _panel_title(text: str) -> html.Div:
    return html.Div(
        text,
        style={
            "fontSize": "10px",
            "textTransform": "uppercase",
            "letterSpacing": "0.04em",
            "color": TEXT_SEC,
            "marginBottom": "6px",
        },
    )


# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div(
    [
        html.Div(
            [
                # col 1: pit stop timeline (hero)
                _panel(
                    [
                        _panel_title("Pit Stop Timeline by Team"),
                        dcc.Graph(
                            id="ts-pitstop-chart",
                            config=GRAPH_CFG,
                            style={"height": "calc(100% - 22px)"},
                        ),
                    ],
                    style_extra={"display": "flex", "flexDirection": "column"},
                ),

                # col 2: tyre degradation (hero)
                _panel(
                    [
                        html.Div(
                            [
                                _panel_title("Tyre Degradation Curves"),
                                dcc.Dropdown(
                                    id="ts-team-dropdown",
                                    options=[],
                                    value=None,
                                    placeholder="All teams",
                                    clearable=True,
                                    style={"width": "200px", "fontSize": "12px"},
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "6px"},
                        ),
                        dcc.Graph(
                            id="ts-degradation-chart",
                            config=GRAPH_CFG,
                            style={"height": "calc(100% - 44px)"},
                        ),
                    ],
                    style_extra={"display": "flex", "flexDirection": "column"},
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "40% 60%",
                "gridTemplateRows": "1fr",
                "gap": "8px",
                "height": CONTENT_H,
                "overflow": "hidden",
            },
        ),
    ],
    style={"padding": "8px", "height": "calc(100vh - 44px)", "overflow": "hidden"},
)


# ── Callbacks ──────────────────────────────────────────────────────────────────
@callback(
    Output("ts-team-dropdown", "options"),
    Output("ts-team-dropdown", "value"),
    Input("race-store", "data"),
)
def update_team_dropdown(store):
    season, round_num = store.get("season"), store.get("round")
    if not season or not round_num:
        return [], None
    results_df = get_race_results(season, round_num)
    teams = sorted(results_df["team_name"].dropna().unique().tolist())
    opts  = [{"label": t, "value": t} for t in teams]
    return opts, None  # default = all teams


@callback(
    Output("ts-pitstop-chart", "figure"),
    Input("race-store", "data"),
)
def update_pitstop_chart(store):
    season, round_num = store.get("season"), store.get("round")
    if not season or not round_num:
        return go.Figure()

    strategy_df = get_tyre_strategy(season, round_num)
    results_df  = get_race_results(season, round_num)
    pit_df      = get_pit_stops_for_race(season, round_num)

    if strategy_df.empty:
        fig = go.Figure()
        fig.update_layout(**CHART_BASE, title="No data")
        return fig

    # Merge team info into strategy
    team_map = results_df.set_index("abbreviation")["team_name"].to_dict()
    color_map = results_df.set_index("abbreviation")["team_color"].to_dict()
    strategy_df = strategy_df.copy()
    strategy_df["team_name"]  = strategy_df["abbreviation"].map(team_map)
    strategy_df["team_color"] = strategy_df["abbreviation"].map(color_map)

    # Y-axis: one row per driver, grouped by team (drivers within same team adjacent)
    team_order = (
        results_df.dropna(subset=["finish_position"])
        .sort_values("finish_position")
        .groupby("team_name", sort=False)["abbreviation"]
        .first()
        .index.tolist()
    )
    # Flatten to driver list: within each team, sorted by finish position
    driver_order = []
    for team in team_order:
        team_drivers = (
            results_df[results_df["team_name"] == team]
            .sort_values("finish_position")["abbreviation"]
            .tolist()
        )
        driver_order.extend(team_drivers)
    # Plotly renders bottom-to-top
    driver_order_plot = list(reversed(driver_order))

    fig = go.Figure()

    known = set(COMPOUND_COLORS.keys())
    all_compounds = list(COMPOUND_COLORS.keys()) + [
        c for c in strategy_df["compound"].unique() if c not in known
    ]

    for compound in all_compounds:
        color = COMPOUND_COLORS.get(compound, "#888888")
        subset = strategy_df[strategy_df["compound"] == compound]
        if subset.empty:
            continue
        fig.add_trace(
            go.Bar(
                x=subset["visual_length"],
                y=subset["abbreviation"],
                base=subset["visual_start_lap"] - 1,
                orientation="h",
                name=compound,
                marker_color=color,
                marker_line_color="#111111",
                marker_line_width=0.8,
                customdata=subset["visual_length"],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"Compound: {compound}<br>"
                    "Start lap: %{base}<br>"
                    "Laps on tyre: %{customdata}<extra></extra>"
                ),
            )
        )

    # Pit stop duration markers
    if not pit_df.empty:
        fig.add_trace(
            go.Scatter(
                x=pit_df["lap_pitted"],
                y=pit_df["abbreviation"],
                mode="markers",
                marker=dict(symbol="diamond", size=8, color="white", line=dict(color="#111111", width=1)),
                name="Pit stop",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Pit lap: %{x}<br>"
                    "Duration: %{customdata:.2f}s<extra></extra>"
                ),
                customdata=pit_df["pit_stop_duration_seconds"],
            )
        )

    # Team separator lines (horizontal)
    team_boundaries = []
    prev_team = None
    for driver in driver_order:
        team = team_map.get(driver)
        if prev_team and team != prev_team:
            idx = driver_order.index(driver)
            team_boundaries.append(idx - 0.5)
        prev_team = team

    for boundary in team_boundaries:
        fig.add_hline(
            y=boundary,
            line=dict(color="#3A3A3A", width=0.8, dash="dot"),
            layer="below",
        )

    fig.update_layout(
        **CHART_BASE,
        barmode="stack",
        title=dict(text="Pit Stop Timeline", font=dict(size=12)),
        xaxis=dict(title="Lap", gridcolor="#2A2A2A", gridwidth=0.5, zeroline=False, color=TEXT_SEC),
        yaxis=dict(
            categoryorder="array",
            categoryarray=driver_order_plot,
            gridcolor="#2A2A2A",
            gridwidth=0.5,
            zeroline=False,
            color=TEXT_SEC,
            tickfont=dict(size=9),
        ),
        legend=dict(
            orientation="h",
            x=0,
            y=-0.06,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=9),
        ),
    )
    fig.update_layout(margin_b=40)
    return fig


@callback(
    Output("ts-degradation-chart", "figure"),
    Input("race-store", "data"),
    Input("ts-team-dropdown", "value"),
)
def update_degradation_chart(store, selected_team):
    season, round_num = store.get("season"), store.get("round")
    fig = go.Figure()

    if not season or not round_num:
        fig.update_layout(**CHART_BASE)
        return fig

    deg_df = get_tyre_degradation_all(season, round_num)
    if deg_df.empty:
        fig.update_layout(**CHART_BASE, title="No degradation data")
        return fig

    # Filter by team if selected
    if selected_team:
        deg_df = deg_df[deg_df["team_name"] == selected_team]
        if deg_df.empty:
            fig.update_layout(**CHART_BASE, title=f"No data for {selected_team}")
            return fig

    # Compute lap time delta from stint baseline (first lap of each driver+stint)
    deg_df = deg_df.copy()
    baseline = (
        deg_df.groupby(["abbreviation", "stint"])["lap_time_seconds"]
        .transform("first")
    )
    deg_df["delta"] = deg_df["lap_time_seconds"] - baseline

    # One trace per compound (aggregated across all drivers/stints)
    compounds = deg_df["compound"].dropna().unique()

    deg_threshold = 0.1  # highlight region above this degradation rate

    for compound in compounds:
        color = COMPOUND_COLORS.get(compound, "#888888")
        subset = deg_df[deg_df["compound"] == compound].copy()
        if subset.empty:
            continue

        # Aggregate: median delta per tyre_life across all drivers using this compound
        agg = (
            subset.groupby("tyre_life")["delta"]
            .agg(["median", "count"])
            .reset_index()
        )
        agg = agg[agg["count"] >= 1].sort_values("tyre_life")

        # Scatter of individual laps (low opacity)
        fig.add_trace(
            go.Scatter(
                x=subset["tyre_life"],
                y=subset["delta"],
                mode="markers",
                name=f"{compound} laps",
                marker=dict(color=color, size=4, opacity=0.3),
                showlegend=True,
                hovertemplate=(
                    f"<b>{compound}</b><br>"
                    "Tyre life: %{x} laps<br>"
                    "Delta: %{y:+.3f}s<extra></extra>"
                ),
            )
        )

        # Median trend line
        if len(agg) >= 2:
            fig.add_trace(
                go.Scatter(
                    x=agg["tyre_life"],
                    y=agg["median"],
                    mode="lines",
                    name=f"{compound} trend",
                    line=dict(color=color, width=2),
                    hovertemplate=(
                        f"<b>{compound} median</b><br>"
                        "Tyre life: %{x} laps<br>"
                        "Delta: %{y:+.3f}s<extra></extra>"
                    ),
                )
            )

            # OLS trendline to show deg rate
            x_vals = agg["tyre_life"].values.astype(float)
            y_vals = agg["median"].values.astype(float)
            coefs  = np.polyfit(x_vals, y_vals, 1)
            slope  = coefs[0]
            x_line = np.linspace(x_vals.min(), x_vals.max(), 50)
            y_line = np.polyval(coefs, x_line)
            fig.add_trace(
                go.Scatter(
                    x=x_line,
                    y=y_line,
                    mode="lines",
                    name=f"{compound} ({slope:+.3f}s/lap)",
                    line=dict(color=color, dash="dash", width=1.2),
                    hoverinfo="skip",
                )
            )

    # Threshold band
    x_range = [0, int(deg_df["tyre_life"].max()) + 1] if not deg_df.empty else [0, 50]
    fig.add_hrect(
        y0=deg_threshold,
        y1=deg_df["delta"].max() * 1.1 if not deg_df.empty else 1.0,
        fillcolor="rgba(232,71,63,0.07)",
        line_width=0,
        annotation_text=f">{deg_threshold}s deg",
        annotation_position="top right",
        annotation_font=dict(size=9, color="#E8473F"),
    )

    # Zero reference line
    fig.add_hline(y=0, line=dict(color="#3A3A3A", width=0.8, dash="dot"), layer="below")

    title_suffix = f" — {selected_team}" if selected_team else " — All Teams"
    fig.update_layout(
        **CHART_BASE,
        title=dict(text=f"Tyre Degradation{title_suffix}", font=dict(size=12)),
        xaxis=dict(
            title="Tyre Life (laps on tyre)",
            gridcolor="#2A2A2A",
            gridwidth=0.5,
            zeroline=False,
            color=TEXT_SEC,
        ),
        yaxis=dict(
            title="Lap Time Delta from Stint Start (s)",
            gridcolor="#2A2A2A",
            gridwidth=0.5,
            zeroline=False,
            color=TEXT_SEC,
        ),
    )
    return fig
