"""
Dashboard 1 — Race Overview
Grid: 35% | 40% | 25%, 2 equal rows
• Col 1 (hero, both rows): Tyre Strategies
• Col 2 (hero, both rows): Position Changes
• Col 3 row 1: Track Conditions
• Col 3 row 2: Pace Distribution
"""
import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go

from data.queries import (
    COMPOUND_COLORS,
    get_race_results,
    get_tyre_strategy,
    get_race_pace,
    get_position_by_lap,
    get_weather,
)

dash.register_page(__name__, path="/", name="Race Overview")

# ── Design tokens ──────────────────────────────────────────────────────────────
BG_PANEL = "#1A1A1A"
BG_P2    = "#242424"
BORDER   = "#2E2E2E"
TEXT_PRI = "#F0F0F0"
TEXT_SEC = "#9A9A9A"

CONTENT_H = "calc(100vh - 44px)"
ROW_H     = "calc(50vh - 22px)"

CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT_PRI, size=10),
    margin=dict(l=8, r=8, t=28, b=8),
)

_LEGEND = dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0)", font=dict(size=9))

GRAPH_CFG = {"displayModeBar": False, "responsive": True}

COMPOUND_LABEL = {"SOFT": "S", "MEDIUM": "M", "HARD": "H", "INTER": "I", "WET": "W"}


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
        # col 1: tyre strategies (hero, both rows)
        _panel(
            [
                _panel_title("Tyre Strategies"),
                dcc.Graph(
                    id="ro-tyre-chart",
                    config=GRAPH_CFG,
                    style={"height": "calc(100% - 22px)"},
                ),
            ],
            style_extra={
                "gridRow": "1 / span 2",
                "display": "flex",
                "flexDirection": "column",
            },
        ),
        # col 2: position changes (hero, both rows)
        _panel(
            [
                _panel_title("Position Changes"),
                dcc.Graph(
                    id="ro-position-chart",
                    config=GRAPH_CFG,
                    style={"height": "calc(100% - 22px)"},
                ),
            ],
            style_extra={
                "gridRow": "1 / span 2",
                "display": "flex",
                "flexDirection": "column",
            },
        ),
        # col 3: wrapper spanning both rows — track conditions (25%) + pace (75%)
        html.Div(
            [
                _panel(
                    [
                        _panel_title("Track Conditions"),
                        html.Div(id="ro-conditions-content", style={"height": "calc(100% - 22px)"}),
                    ],
                    style_extra={"display": "flex", "flexDirection": "column", "flex": "1"},
                ),
                _panel(
                    [
                        _panel_title("Pace Distribution"),
                        dcc.Graph(
                            id="ro-pace-chart",
                            config=GRAPH_CFG,
                            style={"height": "calc(100% - 22px)"},
                        ),
                    ],
                    style_extra={"display": "flex", "flexDirection": "column", "flex": "3"},
                ),
            ],
            style={
                "gridRow": "1 / span 2",
                "display": "flex",
                "flexDirection": "column",
                "gap": "8px",
            },
        ),
    ],
    style={
        "display": "grid",
        "gridTemplateColumns": "35% 40% 25%",
        "gridTemplateRows": f"{ROW_H} {ROW_H}",
        "gap": "8px",
        "padding": "8px",
        "height": CONTENT_H,
        "overflow": "hidden",
    },
)


# ── Callbacks ──────────────────────────────────────────────────────────────────
@callback(
    Output("ro-tyre-chart", "figure"),
    Input("race-store", "data"),
)
def update_tyre_chart(store):
    season, round_num = store.get("season"), store.get("round")
    if not season or not round_num:
        return go.Figure()

    strategy_df = get_tyre_strategy(season, round_num)
    results_df  = get_race_results(season, round_num)

    if strategy_df.empty:
        fig = go.Figure()
        fig.update_layout(**CHART_BASE, title="No data")
        return fig

    # Driver order: P1 at top (Plotly renders categoryarray bottom-to-top)
    driver_order = (
        results_df.dropna(subset=["finish_position"])
        .sort_values("finish_position", ascending=False)["abbreviation"]
        .tolist()
    )
    extra = [d for d in strategy_df["abbreviation"].unique() if d not in driver_order]
    driver_order = extra + driver_order

    fig = go.Figure()

    # One bar trace per compound for shared legend
    known = set(COMPOUND_COLORS.keys())
    all_compounds = list(COMPOUND_COLORS.keys()) + [
        c for c in strategy_df["compound"].unique() if c not in known
    ]

    for compound in all_compounds:
        color = COMPOUND_COLORS.get(compound, "#888888")
        subset = strategy_df[strategy_df["compound"] == compound]
        if subset.empty:
            continue
        label = COMPOUND_LABEL.get(compound, compound[0] if compound else "?")
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
                text=[label if v >= 3 else "" for v in subset["visual_length"]],
                textposition="inside",
                insidetextanchor="middle",
                constraintext="inside",
                textfont=dict(size=9, color="#0F0F0F", family="Inter, sans-serif"),
                customdata=subset["visual_length"],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"Compound: {compound}<br>"
                    "Start lap: %{base}<br>"
                    "Laps on tyre: %{customdata}<extra></extra>"
                ),
            )
        )

    # Pit stop markers
    pit_rows = strategy_df[strategy_df["lap_pitted"].notna()].copy()
    if not pit_rows.empty:
        fig.add_trace(
            go.Scatter(
                x=pit_rows["lap_pitted"],
                y=pit_rows["abbreviation"],
                mode="markers",
                marker=dict(symbol="diamond", size=8, color="white", line=dict(color="#0F0F0F", width=1)),
                name="Pit stop",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Pit lap: %{x}<br>"
                    "Duration: %{customdata:.2f}s<extra></extra>"
                ),
                customdata=pit_rows["pit_stop_duration_seconds"],
            )
        )

    fig.update_layout(
        **CHART_BASE,
        legend=dict(
            orientation="h",
            x=0,
            y=-0.06,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=9),
        ),
        barmode="stack",
        title=dict(text="Tyre Strategies", font=dict(size=12)),
        xaxis=dict(
            title="Lap", gridcolor="#2A2A2A", gridwidth=0.5, zeroline=False, color=TEXT_SEC,
        ),
        yaxis=dict(
            categoryorder="array",
            categoryarray=driver_order,
            gridcolor="#2A2A2A",
            gridwidth=0.5,
            zeroline=False,
            color=TEXT_SEC,
            tickfont=dict(size=9),
        ),
    )
    fig.update_layout(margin_b=40)
    return fig


@callback(
    Output("ro-position-chart", "figure"),
    Input("race-store", "data"),
)
def update_position_chart(store):
    season, round_num = store.get("season"), store.get("round")
    if not season or not round_num:
        return go.Figure()

    position_df = get_position_by_lap(season, round_num)

    if position_df.empty:
        fig = go.Figure()
        fig.update_layout(**CHART_BASE, title="No data")
        return fig

    fig = go.Figure()
    for driver, group in position_df.groupby("abbreviation"):
        color = group["team_color"].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=group["lap_number"],
                y=group["track_position"],
                mode="lines",
                name=str(driver),
                line=dict(color=color, width=1.8, shape="spline"),
                hovertemplate=(
                    f"<b>{driver}</b><br>"
                    "Lap %{x}<br>"
                    "P%{y}<extra></extra>"
                ),
            )
        )

    max_pos = int(position_df["track_position"].max()) if not position_df.empty else 20

    fig.update_layout(
        **CHART_BASE,
        title=dict(text="Position Changes", font=dict(size=12)),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#1A1A1A",
            bordercolor="#2E2E2E",
            font=dict(color="#F0F0F0", size=10, family="Inter, sans-serif"),
        ),
        xaxis=dict(title="Lap", gridcolor="#2A2A2A", gridwidth=0.5, zeroline=False, color=TEXT_SEC),
        yaxis=dict(
            autorange="reversed",
            dtick=1,
            range=[max_pos + 0.5, 0.5],
            gridcolor="#2A2A2A",
            gridwidth=0.5,
            zeroline=False,
            color=TEXT_SEC,
            tickfont=dict(size=9),
            title="Position",
        ),
        legend=dict(x=1.01, y=0.99, bgcolor="rgba(0,0,0,0)", font=dict(size=9), orientation="v"),
    )
    return fig


@callback(
    Output("ro-conditions-content", "children"),
    Input("race-store", "data"),
)
def update_conditions(store):
    season, round_num = store.get("season"), store.get("round")
    if not season or not round_num:
        return html.Div("No data", style={"color": TEXT_SEC, "fontSize": "12px"})

    weather_df = get_weather(season, round_num)

    if weather_df.empty:
        return html.Div("No weather data", style={"color": TEXT_SEC, "fontSize": "12px"})

    last = weather_df.iloc[-1]
    surface = "Wet" if last.get("rainfall") else "Dry"
    air_temp   = f"{last['air_temp']:.1f}°C"   if last["air_temp"]   is not None else "—"
    track_temp = f"{last['track_temp']:.1f}°C" if last["track_temp"] is not None else "—"
    humidity   = f"{last['humidity']:.0f}%"     if last["humidity"]   is not None else "—"

    air_series   = weather_df["air_temp"].dropna()
    track_series = weather_df["track_temp"].dropna()

    def _range_label(series):
        if len(series) < 2:
            return ""
        return f"Session: {series.min():.1f} – {series.max():.1f}°C"

    def metric_card(label, value, sub="", color=TEXT_PRI):
        return html.Div(
            [
                html.Div(label, className="metric-label"),
                html.Div(value, style={"fontSize": "15px", "fontWeight": "500", "color": color, "lineHeight": "1.2"}),
                html.Div(sub, style={"fontSize": "9px", "color": TEXT_SEC, "marginTop": "2px"}) if sub else None,
            ],
            style={
                "backgroundColor": BG_P2,
                "borderRadius": "6px",
                "padding": "6px 8px",
                "flex": "1",
                "overflow": "hidden",
            },
        )

    grid = html.Div(
        [
            html.Div(
                [
                    metric_card("Air Temp",   air_temp,   sub=_range_label(air_series)),
                    metric_card("Track Temp", track_temp, sub=_range_label(track_series)),
                ],
                style={"display": "flex", "gap": "6px", "marginBottom": "6px"},
            ),
            html.Div(
                [
                    metric_card("Humidity", humidity),
                    metric_card(
                        "Surface", surface,
                        color="#1DB954" if surface == "Dry" else "#4fc3f7",
                    ),
                ],
                style={"display": "flex", "gap": "6px"},
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "justifyContent": "center", "height": "100%"},
    )
    return grid


@callback(
    Output("ro-pace-chart", "figure"),
    Input("race-store", "data"),
)
def update_pace_chart(store):
    season, round_num = store.get("season"), store.get("round")
    if not season or not round_num:
        return go.Figure()

    pace_df = get_race_pace(season, round_num)

    if pace_df.empty:
        fig = go.Figure()
        fig.update_layout(**CHART_BASE, title="No data")
        return fig

    medians = (
        pace_df.groupby("abbreviation")["lap_time_seconds"]
        .median()
        .reset_index()
    )
    color_map = (
        pace_df[["abbreviation", "team_color"]]
        .drop_duplicates()
        .set_index("abbreviation")["team_color"]
        .to_dict()
    )

    # Order by finishing position; Plotly renders categoryarray bottom-to-top
    # so we reverse it to get P1 at the top.
    results_df = get_race_results(season, round_num)
    finish_order = (
        results_df.dropna(subset=["finish_position"])
        .sort_values("finish_position")["abbreviation"]
        .tolist()
    )
    # Keep only drivers present in pace data, preserve finish order
    finish_order = [d for d in finish_order if d in medians["abbreviation"].values]
    category_array = list(reversed(finish_order))

    medians["finish_position"] = medians["abbreviation"].map(
        results_df.set_index("abbreviation")["finish_position"].to_dict()
    )
    medians = medians.sort_values("finish_position")

    x_min = medians["lap_time_seconds"].min()
    x_max = medians["lap_time_seconds"].max()
    x_pad = (x_max - x_min) * 0.15

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=medians["lap_time_seconds"],
            y=medians["abbreviation"],
            orientation="h",
            marker_color=[color_map.get(d, "#888888") for d in medians["abbreviation"]],
            text=[f"{v:.3f}s" for v in medians["lap_time_seconds"]],
            textposition="outside",
            textfont=dict(size=9, color=TEXT_SEC),
            hovertemplate="<b>%{y}</b><br>Median: %{x:.3f}s<extra></extra>",
        )
    )

    fig.update_layout(
        **CHART_BASE,
        title=dict(text="Pace Distribution (Median Green-Flag Lap)", font=dict(size=12)),
        xaxis=dict(
            range=[x_min - x_pad * 0.5, x_max + x_pad],
            title="Median Lap (s)",
            gridcolor="#2A2A2A",
            gridwidth=0.5,
            zeroline=False,
            color=TEXT_SEC,
            tickfont=dict(size=9),
        ),
        yaxis=dict(
            categoryorder="array",
            categoryarray=category_array,
            gridcolor="#2A2A2A",
            gridwidth=0.5,
            zeroline=False,
            color=TEXT_SEC,
            tickfont=dict(size=9),
        ),
        showlegend=False,
    )
    return fig
