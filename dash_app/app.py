"""
F1 Analytics — Plotly Dash multi-page app.
Run: python dash_app/app.py  (from repo root)
     or: cd dash_app && python app.py
"""
import sys
from pathlib import Path

# Ensure dash_app/ is on the path so pages can import data.queries
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dash
from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc

from data.queries import get_seasons, get_rounds

# ── Design tokens ──────────────────────────────────────────────────────────────
BG_PAGE  = "#0F0F0F"
BG_PANEL = "#1A1A1A"
BORDER   = "#2E2E2E"
TEXT_PRI = "#F0F0F0"
TEXT_SEC = "#9A9A9A"
NAV_H    = "44px"

# ── Seed selectors from DB ─────────────────────────────────────────────────────
seasons = get_seasons()
_default_season = seasons[0] if seasons else None
_rounds_df = get_rounds(_default_season) if _default_season else None
_round_opts = (
    [{"label": r["race_name"], "value": r["round"]} for _, r in _rounds_df.iterrows()]
    if _rounds_df is not None and not _rounds_df.empty
    else []
)
_default_round = _round_opts[0]["value"] if _round_opts else None

# ── App init ───────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    use_pages=True,
    pages_folder=str(Path(__file__).resolve().parent / "pages"),
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap",
    ],
    suppress_callback_exceptions=True,
)
server = app.server  # expose for gunicorn if needed

# ── Shared navbar ──────────────────────────────────────────────────────────────
def _nav_link(label: str, href: str) -> html.A:
    return html.A(label, href=href, id=f"nav-{href.strip('/') or 'home'}", className="f1-nav-link")


navbar = html.Div(
    [
        # Brand
        html.Span(
            "F1 Analytics",
            style={
                "color": TEXT_PRI,
                "fontWeight": "600",
                "fontSize": "14px",
                "letterSpacing": "0.03em",
                "marginRight": "20px",
                "whiteSpace": "nowrap",
            },
        ),
        # Season selector
        html.Span("Season", style={"color": TEXT_SEC, "fontSize": "11px", "marginRight": "6px"}),
        dcc.Dropdown(
            id="season-dropdown",
            options=[{"label": str(s), "value": s} for s in seasons],
            value=_default_season,
            clearable=False,
            style={"width": "78px", "fontSize": "12px", "minHeight": "28px"},
        ),
        # Round selector
        html.Span(
            "Race",
            style={"color": TEXT_SEC, "fontSize": "11px", "margin": "0 6px 0 14px"},
        ),
        dcc.Dropdown(
            id="round-dropdown",
            options=_round_opts,
            value=_default_round,
            clearable=False,
            style={"width": "230px", "fontSize": "12px", "minHeight": "28px"},
        ),
        # Spacer
        html.Div(style={"flex": "1"}),
        # Nav tabs
        html.Div(
            [
                _nav_link("Race Overview", "/"),
                _nav_link("Driver Comparison", "/driver-comparison"),
                _nav_link("Team Strategy", "/team-strategy"),
            ],
            style={"display": "flex", "gap": "4px", "alignItems": "center"},
        ),
    ],
    style={
        "height": NAV_H,
        "backgroundColor": BG_PANEL,
        "borderBottom": f"0.5px solid {BORDER}",
        "display": "flex",
        "alignItems": "center",
        "padding": "0 16px",
        "gap": "8px",
        "fontFamily": "Inter, sans-serif",
        "position": "relative",
        "zIndex": "100",
    },
)

# ── Root layout ────────────────────────────────────────────────────────────────
app.layout = html.Div(
    [
        dcc.Location(id="url"),
        dcc.Store(id="race-store", data={"season": _default_season, "round": _default_round}),
        navbar,
        dash.page_container,
    ],
    style={
        "backgroundColor": BG_PAGE,
        "height": "100vh",
        "overflow": "hidden",
        "fontFamily": "Inter, sans-serif",
    },
)


# ── Shared callbacks ───────────────────────────────────────────────────────────
@callback(
    Output("round-dropdown", "options"),
    Output("round-dropdown", "value"),
    Input("season-dropdown", "value"),
)
def _update_rounds(season):
    if not season:
        return [], None
    df = get_rounds(season)
    opts = [{"label": r["race_name"], "value": r["round"]} for _, r in df.iterrows()]
    return opts, (opts[0]["value"] if opts else None)


@callback(
    Output("race-store", "data"),
    Input("season-dropdown", "value"),
    Input("round-dropdown", "value"),
)
def _update_store(season, round_num):
    return {"season": season, "round": round_num}


# Highlight active nav link based on current URL
@callback(
    Output("nav-home", "className"),
    Output("nav-driver-comparison", "className"),
    Output("nav-team-strategy", "className"),
    Input("url", "pathname"),
)
def _highlight_nav(pathname):
    active = "f1-nav-link f1-nav-link-active"
    normal = "f1-nav-link"
    return (
        active if pathname == "/" else normal,
        active if pathname == "/driver-comparison" else normal,
        active if pathname == "/team-strategy" else normal,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8050)
