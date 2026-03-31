"""
Telemetry Comparison — Driver vs Driver
"""

import sys
from pathlib import Path
import streamlit as st
import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
streamlit_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(streamlit_dir))

from utils.db import get_connection
from utils.telemetry import (
    get_seasons,
    get_rounds,
    get_drivers_for_round,
    get_best_lap,
    load_lap_telemetry,
    load_drs_by_lap,
    load_throttle_bands,
    build_shared_grid,
    interpolate_to_grid,
    cumulative_time,
)
from utils.charts import (
    track_map_speed,
    track_map_delta,
    track_map_braking,
    speed_trace,
    time_distance,
    four_panel_trace,
    drs_by_lap_chart,
    throttle_breakdown_chart,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Telemetry Comparison | F1 Analytics",
    page_icon="🏎️",
    layout="wide",
)

st.title("🏎️ Telemetry Comparison")
st.caption("Driver vs driver — lap-level telemetry from `staging.stg_fastf1_telemetry`")

# ── Sidebar controls ──────────────────────────────────────────────────────────
con = get_connection()

with st.sidebar:
    st.header("Selection")

    # Season
    seasons = get_seasons(con)
    season  = st.selectbox("Season", seasons, index=0)

    # Round
    rounds_df   = get_rounds(con, season)
    round_label = st.selectbox(
        "Race",
        rounds_df["race_name"].tolist(),
        index=0,
    )
    round_num = int(
        rounds_df[rounds_df["race_name"] == round_label]["round"].iloc[0]
    )

    # Drivers — populated dynamically from telemetry for this round
    drivers = get_drivers_for_round(con, season, round_num)

    if len(drivers) < 2:
        st.error("Not enough drivers with telemetry for this round.")
        st.stop()

    default_b = drivers[1] if len(drivers) > 1 else drivers[0]

    driver_a = st.selectbox("Driver A", drivers, index=0)
    driver_b = st.selectbox(
        "Driver B",
        [d for d in drivers if d != driver_a],
        index=0,
    )

    st.divider()
    st.caption("Lap selection")
    use_best = st.toggle("Use personal best lap", value=True)

    if not use_best:
        lap_a = st.number_input("Driver A lap", min_value=1, value=10, step=1)
        lap_b = st.number_input("Driver B lap", min_value=1, value=10, step=1)
    else:
        lap_a = None
        lap_b = None

# ── Resolve laps ──────────────────────────────────────────────────────────────
with st.spinner("Resolving laps..."):
    if use_best:
        lap_a = get_best_lap(con, season, round_num, driver_a)
        lap_b = get_best_lap(con, season, round_num, driver_b)

st.markdown(
    f"**{driver_a}** — Lap **{lap_a}** &nbsp;|&nbsp; "
    f"**{driver_b}** — Lap **{lap_b}** &nbsp;|&nbsp; "
    f"**{round_label}** &nbsp;({season} Round {round_num})"
)

# ── Load & interpolate telemetry ──────────────────────────────────────────────
with st.spinner("Loading telemetry..."):
    tel_a = load_lap_telemetry(con, season, round_num, driver_a, lap_a)
    tel_b = load_lap_telemetry(con, season, round_num, driver_b, lap_b)

if tel_a.empty or tel_b.empty:
    st.error("No telemetry found for one or both drivers on the selected lap.")
    st.stop()

dist_grid    = build_shared_grid(tel_a, tel_b)
tel_a_interp = interpolate_to_grid(tel_a, dist_grid)
tel_b_interp = interpolate_to_grid(tel_b, dist_grid)
cum_t_a      = cumulative_time(tel_a_interp)
cum_t_b      = cumulative_time(tel_b_interp)

# ── Section 1: Track Maps ─────────────────────────────────────────────────────
st.subheader("Track Maps")

with st.spinner("Rendering speed delta map..."):
    fig = track_map_delta(
        tel_a_interp, tel_b_interp, dist_grid,
        driver_a, driver_b, round_label, lap_a, lap_b,
    )
    st.pyplot(fig, use_container_width=True)

# Braking map full width below
with st.spinner("Rendering braking maps..."):
    fig = track_map_braking(
        tel_a, tel_b, driver_a, driver_b,
        round_label, lap_a, lap_b,
    )
    st.pyplot(fig, use_container_width=True)

# ── Section 2: Speed Trace ────────────────────────────────────────────────────
st.subheader("Speed Trace")

with st.spinner("Rendering speed trace..."):
    fig = speed_trace(
        tel_a_interp, tel_b_interp, dist_grid,
        driver_a, driver_b, round_label, lap_a, lap_b,
    )
    st.pyplot(fig, use_container_width=True)

# ── Section 3: Time vs Distance ───────────────────────────────────────────────
st.subheader("Lap Time vs Distance")

with st.spinner("Rendering time/distance chart..."):
    fig = time_distance(
        tel_a_interp, tel_b_interp, dist_grid,
        cum_t_a, cum_t_b,
        driver_a, driver_b, round_label, lap_a, lap_b,
    )
    st.pyplot(fig, use_container_width=True)

# ── Section 4: 4-Panel Trace ──────────────────────────────────────────────────
st.subheader("Full Channel Comparison")

with st.spinner("Rendering channel traces..."):
    fig = four_panel_trace(
        tel_a_interp, tel_b_interp, dist_grid,
        driver_a, driver_b, round_label, lap_a, lap_b,
    )
    st.pyplot(fig, use_container_width=True)

# ── Section 5: DRS & Throttle ─────────────────────────────────────────────────
st.subheader("DRS & Throttle")

with st.spinner("Loading throttle data..."):
    throttle_df = load_throttle_bands(con, season, round_num, driver_a, driver_b)
    fig = throttle_breakdown_chart(throttle_df, driver_a, driver_b, round_label)
    st.pyplot(fig, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"Source: `staging.stg_fastf1_telemetry` — {len(tel_a)} raw samples "
    f"({driver_a}), {len(tel_b)} ({driver_b}), interpolated to "
    f"{len(dist_grid)} points on shared distance grid."
)
