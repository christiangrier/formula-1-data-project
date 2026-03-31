"""
F1 Analytics Dashboard — entry point.
"""

import streamlit as st

st.set_page_config(
    page_title="F1 Analytics | 2026",
    page_icon="🏁",
    layout="wide",
)

st.title("🏁 F1 Data Platform — Analytics Dashboard")
st.caption("Phase 3 Analytics | Stage 1 — DuckDB local stack")

st.markdown("""
Use the sidebar to navigate between analysis pages.

| Page | Description |
|------|-------------|
| 🏎️ Telemetry Comparison | Driver vs driver — speed, throttle, brake, DRS, track maps |

More pages coming as Phase 3 progresses.
""")

st.info(
    "**Data source:** Gold mart tables + `staging.stg_fastf1_telemetry` via local DuckDB.  "
    "All queries are read-only. Re-run ingestion to add new rounds.",
    icon="ℹ️",
)
