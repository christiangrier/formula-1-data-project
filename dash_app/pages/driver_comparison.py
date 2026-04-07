"""
Dashboard 2 — Driver Comparison
Full-width 50px header (driver selectors) + 3-col grid: 22% | 48% | 30%
• Header: driver A / driver B dropdowns
• Col 1 row 1: Avg Delta + Sectors
• Col 1 row 2: Best Lap + Consistency metric
• Col 2 (hero, both rows): Lap Time Comparison
• Col 3 row 1: Telemetry Averages
• Col 3 row 2: Consistency (box plot)
"""
import dash
from dash import html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
import numpy as np

from data.queries import (
    COMPOUND_COLORS,
    get_race_results,
    get_drivers_for_round,
    get_lap_times_for_drivers,
    get_sector_averages,
    get_telemetry_metrics,
)

dash.register_page(__name__, path="/driver-comparison", name="Driver Comparison")

# ── Design tokens ──────────────────────────────────────────────────────────────
BG_PANEL = "#1A1A1A"
BG_P2    = "#242424"
BORDER   = "#2E2E2E"
TEXT_PRI = "#F0F0F0"
TEXT_SEC = "#9A9A9A"

COLOR_A_DEFAULT = "#FF8000"
COLOR_B_DEFAULT = "#27F4D2"

_DOT_STYLE_BASE = {
    "width": "10px", "height": "10px", "borderRadius": "50%",
    "marginRight": "8px", "flexShrink": "0",
}


def _dot_style(color: str) -> dict:
    return {**_DOT_STYLE_BASE, "backgroundColor": color}


def _resolve_colors(season, round_num, driver_a, driver_b) -> tuple[str, str]:
    """Return (color_a, color_b) from team colors in the results data.
    If both drivers share a color, driver B is set to white."""
    try:
        results = get_race_results(season, round_num)
        color_map = results.set_index("abbreviation")["team_color"].to_dict()
        color_a = color_map.get(driver_a, COLOR_A_DEFAULT)
        color_b = color_map.get(driver_b, COLOR_B_DEFAULT)
        if color_a.lower() == color_b.lower():
            color_b = "#FFFFFF"
        return color_a, color_b
    except Exception:
        return COLOR_A_DEFAULT, COLOR_B_DEFAULT

HEADER_H  = "50px"
CONTENT_H = f"calc(100vh - 44px - {HEADER_H})"
ROW_H     = f"calc((100vh - 44px - {HEADER_H} - 24px) / 2)"

CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT_PRI, size=10),
    margin=dict(l=8, r=8, t=28, b=8),
)

_LEGEND = dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0)", font=dict(size=10))

GRAPH_CFG = {"displayModeBar": False, "responsive": True}

SECTOR_COLORS = ["#9B59B6", "#1DB954", "#FF9800"]


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


def _metric_card(label: str, value: str, sub: str = "", color: str = TEXT_PRI) -> html.Div:
    return html.Div(
        [
            html.Div(label, className="metric-label"),
            html.Div(value, style={"fontSize": "16px", "fontWeight": "500", "color": color}),
            html.Div(sub, style={"fontSize": "10px", "color": TEXT_SEC}) if sub else html.Div(),
        ],
        style={
            "backgroundColor": BG_P2,
            "borderRadius": "6px",
            "padding": "8px 10px",
            "flex": "1",
        },
    )


# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div(
    [
        dcc.Store(id="dc-driver-colors", data={"a": COLOR_A_DEFAULT, "b": COLOR_B_DEFAULT}),

        # ── Driver selector header ─────────────────────────────────────────
        html.Div(
            [
                html.Div(
                    [
                        html.Div(id="dc-dot-a", style=_dot_style(COLOR_A_DEFAULT)),
                        dcc.Dropdown(
                            id="dc-driver-a",
                            options=[],
                            value=None,
                            clearable=False,
                            style={"width": "150px", "fontSize": "12px"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
                html.Span("vs", style={"color": TEXT_SEC, "fontSize": "13px", "fontWeight": "500", "margin": "0 20px"}),
                html.Div(
                    [
                        html.Div(id="dc-dot-b", style=_dot_style(COLOR_B_DEFAULT)),
                        dcc.Dropdown(
                            id="dc-driver-b",
                            options=[],
                            value=None,
                            clearable=False,
                            style={"width": "150px", "fontSize": "12px"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
            style={
                "height": HEADER_H,
                "backgroundColor": BG_PANEL,
                "border": f"0.5px solid {BORDER}",
                "borderRadius": "8px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "padding": "0 20px",
                "marginBottom": "8px",
            },
        ),

        # ── 3-col grid ─────────────────────────────────────────────────────
        html.Div(
            [
                # col 2 (hero, both rows): lap time comparison — explicit column keeps it centred
                _panel(
                    [
                        _panel_title("Lap Time Comparison"),
                        dcc.Graph(
                            id="dc-laptime-chart",
                            config=GRAPH_CFG,
                            style={"height": "calc(100% - 22px)"},
                        ),
                    ],
                    style_extra={
                        "gridColumn": "2",
                        "gridRow": "1 / span 2",
                        "display": "flex",
                        "flexDirection": "column",
                    },
                ),

                # col 1 row 1: avg delta + sectors
                _panel(
                    [
                        _panel_title("Average Delta + Sectors"),
                        html.Div(id="dc-delta-content", style={"height": "calc(100% - 22px)", "overflow": "hidden"}),
                    ],
                    style_extra={
                        "gridColumn": "1",
                        "gridRow": "1",
                        "display": "flex",
                        "flexDirection": "column",
                    },
                ),

                # col 3 row 1: telemetry averages (metric cards, no chart)
                _panel(
                    [
                        _panel_title("Telemetry Averages"),
                        html.Div(id="dc-telemetry-content", style={"height": "calc(100% - 22px)", "overflow": "hidden"}),
                    ],
                    style_extra={
                        "gridColumn": "3",
                        "gridRow": "1",
                        "display": "flex",
                        "flexDirection": "column",
                    },
                ),

                # col 1 row 2: best lap + consistency metrics
                _panel(
                    [
                        _panel_title("Best Lap + Consistency"),
                        html.Div(id="dc-bestlap-content", style={"height": "calc(100% - 22px)", "overflow": "hidden"}),
                    ],
                    style_extra={
                        "gridColumn": "1",
                        "gridRow": "2",
                        "display": "flex",
                        "flexDirection": "column",
                    },
                ),

                # col 3 row 2: consistency box plot
                _panel(
                    [
                        _panel_title("Lap Time Distribution"),
                        dcc.Graph(
                            id="dc-consistency-chart",
                            config=GRAPH_CFG,
                            style={"height": "calc(100% - 22px)"},
                        ),
                    ],
                    style_extra={
                        "gridColumn": "3",
                        "gridRow": "2",
                        "display": "flex",
                        "flexDirection": "column",
                    },
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "20% 54% 26%",
                "gridTemplateRows": f"{ROW_H} {ROW_H}",
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
    Output("dc-driver-colors", "data"),
    Output("dc-dot-a", "style"),
    Output("dc-dot-b", "style"),
    Input("race-store", "data"),
    Input("dc-driver-a", "value"),
    Input("dc-driver-b", "value"),
)
def update_driver_colors(store, driver_a, driver_b):
    season, round_num = store.get("season"), store.get("round")
    if not all([season, round_num, driver_a, driver_b]):
        return (
            {"a": COLOR_A_DEFAULT, "b": COLOR_B_DEFAULT},
            _dot_style(COLOR_A_DEFAULT),
            _dot_style(COLOR_B_DEFAULT),
        )
    color_a, color_b = _resolve_colors(season, round_num, driver_a, driver_b)
    return (
        {"a": color_a, "b": color_b},
        _dot_style(color_a),
        _dot_style(color_b),
    )


@callback(
    Output("dc-driver-a", "options"),
    Output("dc-driver-a", "value"),
    Output("dc-driver-b", "options"),
    Output("dc-driver-b", "value"),
    Input("race-store", "data"),
    Input("dc-driver-a", "value"),
    State("dc-driver-b", "value"),
)
def update_driver_dropdowns(store, current_driver_a, current_driver_b):
    from dash import ctx

    season, round_num = store.get("season"), store.get("round")
    if not season or not round_num:
        return [], None, [], None

    drivers = get_drivers_for_round(season, round_num)
    if len(drivers) < 2:
        return [], None, [], None

    opts = [{"label": d, "value": d} for d in drivers]

    # When the race changes, reset both drivers
    if ctx.triggered_id == "race-store" or current_driver_a not in drivers:
        driver_a = drivers[0]
        b_opts   = [{"label": d, "value": d} for d in drivers if d != driver_a]
        driver_b = b_opts[0]["value"] if b_opts else None
    else:
        driver_a = current_driver_a
        b_opts   = [{"label": d, "value": d} for d in drivers if d != driver_a]
        # Preserve driver B if still valid and not the same as the new driver A
        if current_driver_b and current_driver_b in drivers and current_driver_b != driver_a:
            driver_b = current_driver_b
        else:
            driver_b = b_opts[0]["value"] if b_opts else None

    return opts, driver_a, b_opts, driver_b


@callback(
    Output("dc-laptime-chart", "figure"),
    Input("race-store", "data"),
    Input("dc-driver-colors", "data"),
    State("dc-driver-a", "value"),
    State("dc-driver-b", "value"),
)
def update_laptime_chart(store, colors, driver_a, driver_b):
    COLOR_A = (colors or {}).get("a", COLOR_A_DEFAULT)
    COLOR_B = (colors or {}).get("b", COLOR_B_DEFAULT)
    season, round_num = store.get("season"), store.get("round")
    if not all([season, round_num, driver_a, driver_b]):
        return go.Figure()

    laps_df = get_lap_times_for_drivers(season, round_num, driver_a, driver_b)
    if laps_df.empty:
        fig = go.Figure()
        fig.update_layout(**CHART_BASE, title="No lap data")
        return fig

    fig = go.Figure()

    for driver, color in [(driver_a, COLOR_A), (driver_b, COLOR_B)]:
        subset = laps_df[laps_df["abbreviation"] == driver].sort_values("lap_number")
        if subset.empty:
            continue

        # Fill between lines — add a filled trace first
        fig.add_trace(
            go.Scatter(
                x=subset["lap_number"],
                y=subset["lap_time_seconds"],
                mode="none",
                fill="tonexty" if driver == driver_b else None,
                fillcolor="rgba(255,255,255,0.04)",
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=subset["lap_number"],
                y=subset["lap_time_seconds"],
                mode="lines+markers",
                name=driver,
                line=dict(color=color, width=2),
                marker=dict(
                    color=[COMPOUND_COLORS.get(c, "#888888") for c in subset["compound"]],
                    size=6,
                    line=dict(color=color, width=1),
                ),
                hovertemplate=(
                    f"<b>{driver}</b><br>"
                    "Lap %{x}<br>"
                    "Time: %{y:.3f}s<br>"
                    "Compound: %{customdata}<extra></extra>"
                ),
                customdata=subset["compound"],
            )
        )

    fig.update_layout(
        **CHART_BASE,
        title=dict(text=f"Lap Times — {driver_a} vs {driver_b}", font=dict(size=12)),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1A1A1A",
            bordercolor="#2E2E2E",
            font=dict(color="#F0F0F0", size=10, family="Inter, sans-serif"),
        ),
        xaxis=dict(title="Lap", gridcolor="#2A2A2A", gridwidth=0.5, zeroline=False, color=TEXT_SEC),
        yaxis=dict(title="Lap Time (s)", gridcolor="#2A2A2A", gridwidth=0.5, zeroline=False, color=TEXT_SEC),
    )
    return fig


@callback(
    Output("dc-delta-content", "children"),
    Input("race-store", "data"),
    Input("dc-driver-colors", "data"),
    State("dc-driver-a", "value"),
    State("dc-driver-b", "value"),
)
def update_delta(store, colors, driver_a, driver_b):
    season, round_num = store.get("season"), store.get("round")
    if not all([season, round_num, driver_a, driver_b]):
        return html.Div("Select drivers", style={"color": TEXT_SEC, "fontSize": "11px"})

    sector_df = get_sector_averages(season, round_num, driver_a, driver_b)
    laps_df   = get_lap_times_for_drivers(season, round_num, driver_a, driver_b)

    if sector_df.empty or laps_df.empty:
        return html.Div("No data", style={"color": TEXT_SEC, "fontSize": "11px"})

    row_a = sector_df[sector_df["abbreviation"] == driver_a]
    row_b = sector_df[sector_df["abbreviation"] == driver_b]

    avg_a = laps_df[laps_df["abbreviation"] == driver_a]["lap_time_seconds"].median()
    avg_b = laps_df[laps_df["abbreviation"] == driver_b]["lap_time_seconds"].median()

    if row_a.empty or row_b.empty:
        return html.Div("No sector data", style={"color": TEXT_SEC, "fontSize": "11px"})

    delta = avg_a - avg_b
    delta_str = f"{delta:+.3f}s"
    delta_color = "#E8473F" if delta > 0 else "#1DB954"
    delta_label = f"{driver_a} {'slower' if delta > 0 else 'faster'} than {driver_b}"

    sector_deltas = []
    for i, (col, label, color) in enumerate(
        [("avg_s1", "S1", SECTOR_COLORS[0]), ("avg_s2", "S2", SECTOR_COLORS[1]), ("avg_s3", "S3", SECTOR_COLORS[2])]
    ):
        d = row_a[col].iloc[0] - row_b[col].iloc[0]
        sector_deltas.append(
            html.Div(
                [
                    html.Div(label, style={"fontSize": "9px", "color": TEXT_SEC, "textTransform": "uppercase"}),
                    html.Div(
                        f"{d:+.3f}s",
                        style={"fontSize": "13px", "fontWeight": "500", "color": "#E8473F" if d > 0 else "#1DB954"},
                    ),
                ],
                style={
                    "flex": "1",
                    "backgroundColor": BG_P2,
                    "borderRadius": "5px",
                    "padding": "6px 8px",
                    "borderTop": f"2px solid {color}",
                },
            )
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Div(delta_str, style={"fontSize": "28px", "fontWeight": "600", "color": delta_color, "textAlign": "center"}),
                    html.Div(delta_label, style={"fontSize": "10px", "color": TEXT_SEC, "textAlign": "center", "marginBottom": "10px"}),
                ],
            ),
            html.Div(sector_deltas, style={"display": "flex", "flexDirection": "column", "gap": "6px"}),
        ],
        style={"display": "flex", "flexDirection": "column", "justifyContent": "center", "height": "100%"},
    )


@callback(
    Output("dc-bestlap-content", "children"),
    Input("race-store", "data"),
    Input("dc-driver-colors", "data"),
    State("dc-driver-a", "value"),
    State("dc-driver-b", "value"),
)
def update_bestlap(store, colors, driver_a, driver_b):
    COLOR_A = (colors or {}).get("a", COLOR_A_DEFAULT)
    COLOR_B = (colors or {}).get("b", COLOR_B_DEFAULT)
    season, round_num = store.get("season"), store.get("round")
    if not all([season, round_num, driver_a, driver_b]):
        return html.Div()

    laps_df = get_lap_times_for_drivers(season, round_num, driver_a, driver_b)
    if laps_df.empty:
        return html.Div("No data", style={"color": TEXT_SEC, "fontSize": "11px"})

    cards = []
    for driver, color in [(driver_a, COLOR_A), (driver_b, COLOR_B)]:
        sub = laps_df[laps_df["abbreviation"] == driver]
        if sub.empty:
            continue
        best_row  = sub.loc[sub["lap_time_seconds"].idxmin()]
        best_time = f"{best_row['lap_time_seconds']:.3f}s"
        best_lap  = f"Lap {int(best_row['lap_number'])}"
        std_dev   = sub["lap_time_seconds"].std()
        cards.append(
            html.Div(
                [
                    html.Div(
                        style={
                            "width": "8px", "height": "8px", "borderRadius": "50%",
                            "backgroundColor": color, "marginBottom": "4px",
                        }
                    ),
                    html.Div(driver, style={"fontSize": "10px", "color": TEXT_SEC, "textTransform": "uppercase", "letterSpacing": "0.04em"}),
                    html.Div(best_time, style={"fontSize": "18px", "fontWeight": "500", "color": TEXT_PRI}),
                    html.Div(best_lap, style={"fontSize": "10px", "color": TEXT_SEC}),
                    html.Div(
                        f"σ {std_dev:.3f}s",
                        style={"fontSize": "11px", "color": TEXT_SEC, "marginTop": "6px"},
                        title="Lap time standard deviation",
                    ),
                ],
                style={
                    "flex": "1",
                    "backgroundColor": BG_P2,
                    "borderRadius": "6px",
                    "padding": "10px",
                    "borderTop": f"2px solid {color}",
                },
            )
        )

    return html.Div(cards, style={"display": "flex", "gap": "8px", "height": "100%", "alignItems": "stretch"})


@callback(
    Output("dc-telemetry-content", "children"),
    Input("race-store", "data"),
    Input("dc-driver-colors", "data"),
    State("dc-driver-a", "value"),
    State("dc-driver-b", "value"),
)
def update_telemetry_content(store, colors, driver_a, driver_b):
    COLOR_A = (colors or {}).get("a", COLOR_A_DEFAULT)
    COLOR_B = (colors or {}).get("b", COLOR_B_DEFAULT)
    season, round_num = store.get("season"), store.get("round")
    if not all([season, round_num, driver_a, driver_b]):
        return html.Div("Select drivers", style={"color": TEXT_SEC, "fontSize": "11px"})

    tel_df = get_telemetry_metrics(season, round_num, driver_a, driver_b)
    if tel_df.empty:
        return html.Div("No telemetry data", style={"color": TEXT_SEC, "fontSize": "11px"})

    row_a = tel_df[tel_df["abbreviation"] == driver_a]
    row_b = tel_df[tel_df["abbreviation"] == driver_b]
    if row_a.empty or row_b.empty:
        return html.Div("Incomplete data", style={"color": TEXT_SEC, "fontSize": "11px"})

    def _metric_row(label, val_a, val_b, fmt):
        return html.Div(
            [
                html.Div(label, className="metric-label"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(driver_a, style={"fontSize": "9px", "color": COLOR_A, "marginBottom": "2px"}),
                                html.Div(fmt(val_a), style={"fontSize": "16px", "fontWeight": "500", "color": TEXT_PRI}),
                            ],
                            style={
                                "flex": "1",
                                "backgroundColor": BG_P2,
                                "borderRadius": "5px",
                                "padding": "6px 8px",
                                "borderTop": f"2px solid {COLOR_A}",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(driver_b, style={"fontSize": "9px", "color": COLOR_B, "marginBottom": "2px"}),
                                html.Div(fmt(val_b), style={"fontSize": "16px", "fontWeight": "500", "color": TEXT_PRI}),
                            ],
                            style={
                                "flex": "1",
                                "backgroundColor": BG_P2,
                                "borderRadius": "5px",
                                "padding": "6px 8px",
                                "borderTop": f"2px solid {COLOR_B}",
                            },
                        ),
                    ],
                    style={"display": "flex", "gap": "6px"},
                ),
            ],
            style={"marginBottom": "8px"},
        )

    a_throttle  = row_a["full_throttle_pct"].iloc[0]
    b_throttle  = row_b["full_throttle_pct"].iloc[0]
    a_brake     = row_a["brake_pct"].iloc[0]
    b_brake     = row_b["brake_pct"].iloc[0]
    a_maxspeed  = row_a["max_speed"].iloc[0]
    b_maxspeed  = row_b["max_speed"].iloc[0]

    return html.Div(
        [
            _metric_row("Full Throttle",  a_throttle, b_throttle, lambda v: f"{v:.1f}%"),
            _metric_row("Brake",          a_brake,    b_brake,    lambda v: f"{v:.1f}%"),
            _metric_row("Max Speed",      a_maxspeed, b_maxspeed, lambda v: f"{v:.0f} km/h"),
        ],
        style={"height": "100%", "display": "flex", "flexDirection": "column", "justifyContent": "center"},
    )


@callback(
    Output("dc-consistency-chart", "figure"),
    Input("race-store", "data"),
    Input("dc-driver-colors", "data"),
    State("dc-driver-a", "value"),
    State("dc-driver-b", "value"),
)
def update_consistency_chart(store, colors, driver_a, driver_b):
    COLOR_A = (colors or {}).get("a", COLOR_A_DEFAULT)
    COLOR_B = (colors or {}).get("b", COLOR_B_DEFAULT)
    season, round_num = store.get("season"), store.get("round")
    fig = go.Figure()

    if not all([season, round_num, driver_a, driver_b]):
        fig.update_layout(**CHART_BASE)
        return fig

    laps_df = get_lap_times_for_drivers(season, round_num, driver_a, driver_b)
    if laps_df.empty:
        fig.update_layout(**CHART_BASE, title="No data")
        return fig

    for driver, color in [(driver_a, COLOR_A), (driver_b, COLOR_B)]:
        subset = laps_df[laps_df["abbreviation"] == driver]
        if subset.empty:
            continue
        fig.add_trace(
            go.Box(
                y=subset["lap_time_seconds"],
                name=driver,
                marker_color=color,
                boxpoints="outliers",
                line=dict(color=color),
                hovertemplate=f"<b>{driver}</b><br>%{{y:.3f}}s<extra></extra>",
            )
        )

    fig.update_layout(
        **CHART_BASE,
        title=dict(text="Lap Time Distribution", font=dict(size=12)),
        yaxis=dict(title="Lap Time (s)", gridcolor="#2A2A2A", gridwidth=0.5, zeroline=False, color=TEXT_SEC),
        xaxis=dict(gridcolor="#2A2A2A", gridwidth=0.5, zeroline=False, color=TEXT_SEC),
        showlegend=False,
    )
    return fig
