"""
Telemetry data helpers — loading, interpolation, and derived metrics.
All heavy aggregation is done query-side in DuckDB.
"""

import numpy as np
import pandas as pd
import duckdb
import streamlit as st


# ── Query helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_seasons(_con: duckdb.DuckDBPyConnection) -> list[int]:
    return (
        _con.execute(
            "SELECT DISTINCT season FROM gold.mart_race_results ORDER BY season DESC"
        )
        .df()["season"]
        .tolist()
    )


@st.cache_data(ttl=300)
def get_rounds(_con: duckdb.DuckDBPyConnection, season: int) -> pd.DataFrame:
    """Returns round number and race name for a given season."""
    return _con.execute(f"""
        SELECT DISTINCT round, race_name
        FROM gold.mart_race_results
        WHERE season = {season}
        ORDER BY round
    """).df()


@st.cache_data(ttl=300)
def get_drivers_for_round(
    _con: duckdb.DuckDBPyConnection, season: int, round_num: int
) -> list[str]:
    """Distinct driver abbreviations that have telemetry for the given round."""
    return (
        _con.execute(f"""
            SELECT DISTINCT abbreviation
            FROM staging.stg_fastf1_telemetry
            WHERE season = {season}
              AND round  = {round_num}
            ORDER BY abbreviation
        """)
        .df()["abbreviation"]
        .tolist()
    )


@st.cache_data(ttl=300)
def get_best_lap(
    _con: duckdb.DuckDBPyConnection, season: int, round_num: int, driver: str
) -> int:
    """Return the personal best lap number for a driver in a round."""
    # result = _con.execute(f"""
    #     SELECT lap_number
    #     FROM gold.mart_lap_times
    #     WHERE season         = {season}
    #       AND round          = {round_num}
    #       AND abbreviation   = '{driver}'
    #       AND is_accurate    = TRUE
    #       AND is_personal_best = TRUE
    #     LIMIT 1
    # """).df()
    # if not result.empty:
    #     return int(result["lap_number"].iloc[0])
    # Fallback: lap with minimum lap_time_seconds
    result = _con.execute(f"""
        SELECT lap_number
        FROM gold.mart_lap_times
        WHERE season       = {season}
          AND round        = {round_num}
          AND abbreviation = '{driver}'
        ORDER BY lap_time_seconds ASC
        LIMIT 1
    """).df()
    if not result.empty:
        return int(result["lap_number"].iloc[0])
    # Final fallback: lowest lap number with telemetry
    result = _con.execute(f"""
        SELECT MIN(lap_number) AS lap_number
        FROM staging.stg_fastf1_telemetry
        WHERE season       = {season}
          AND round        = {round_num}
          AND abbreviation = '{driver}'
    """).df()
    return int(result["lap_number"].iloc[0])


@st.cache_data(ttl=300)
def load_lap_telemetry(
    _con: duckdb.DuckDBPyConnection,
    season: int,
    round_num: int,
    driver: str,
    lap: int,
) -> pd.DataFrame:
    """Load raw telemetry for a single driver lap (~2–3K rows)."""
    return _con.execute(f"""
        SELECT
            abbreviation, team, lap_number,
            distance, speed, throttle, brake, drs,
            rpm, n_gear, x, y, z,
            driver_ahead, distance_to_driver_ahead,
            track_status
        FROM staging.stg_fastf1_telemetry
        WHERE season       = {season}
          AND round        = {round_num}
          AND abbreviation = '{driver}'
          AND lap_number   = {lap}
        ORDER BY distance
    """).df()


@st.cache_data(ttl=300)
def load_drs_by_lap(
    _con: duckdb.DuckDBPyConnection,
    season: int,
    round_num: int,
    driver_a: str,
    driver_b: str,
) -> pd.DataFrame:
    """DRS open % per lap — aggregated query."""
    return _con.execute(f"""
        SELECT
            abbreviation,
            lap_number,
            ROUND(
                100.0 * SUM(CASE WHEN drs >= 8 THEN 1 ELSE 0 END) / COUNT(*), 1
            ) AS drs_open_pct
        FROM staging.stg_fastf1_telemetry
        WHERE season       = {season}
          AND round        = {round_num}
          AND abbreviation IN ('{driver_a}', '{driver_b}')
        GROUP BY abbreviation, lap_number
        ORDER BY abbreviation, lap_number
    """).df()


@st.cache_data(ttl=300)
def load_throttle_bands(
    _con: duckdb.DuckDBPyConnection,
    season: int,
    round_num: int,
    driver_a: str,
    driver_b: str,
) -> pd.DataFrame:
    """Full-throttle / partial / lift breakdown per driver."""
    return _con.execute(f"""
        SELECT
            abbreviation,
            ROUND(100.0 * SUM(CASE WHEN throttle >= 98 THEN 1 ELSE 0 END) / COUNT(*), 1)
                AS full_throttle_pct,
            ROUND(100.0 * SUM(CASE WHEN throttle >= 20 AND throttle < 98 THEN 1 ELSE 0 END) / COUNT(*), 1)
                AS partial_throttle_pct,
            ROUND(100.0 * SUM(CASE WHEN throttle < 20 THEN 1 ELSE 0 END) / COUNT(*), 1)
                AS lift_pct
        FROM staging.stg_fastf1_telemetry
        WHERE season       = {season}
          AND round        = {round_num}
          AND abbreviation IN ('{driver_a}', '{driver_b}')
        GROUP BY abbreviation
    """).df()


# ── Interpolation ─────────────────────────────────────────────────────────────

N_GRID = 500


def build_shared_grid(tel_a: pd.DataFrame, tel_b: pd.DataFrame) -> np.ndarray:
    dist_min = max(tel_a["distance"].min(), tel_b["distance"].min())
    dist_max = min(tel_a["distance"].max(), tel_b["distance"].max())
    return np.linspace(dist_min, dist_max, N_GRID)


def interpolate_to_grid(tel: pd.DataFrame, dist_grid: np.ndarray) -> pd.DataFrame:
    """
    Resample a single-lap telemetry DataFrame onto a fixed distance grid.
    Numeric channels: linear interpolation.
    Boolean channels: interpolate as float, threshold at 0.5.
    DRS: nearest-neighbour (discrete state).
    """
    numeric = ["speed", "throttle", "rpm", "n_gear", "distance_to_driver_ahead",
               "x", "y", "z"]
    result = {"distance": dist_grid}

    src_dist = tel["distance"].values

    for ch in numeric:
        if ch in tel.columns:
            result[ch] = np.interp(dist_grid, src_dist, tel[ch].astype(float))

    if "brake" in tel.columns:
        interp = np.interp(dist_grid, src_dist, tel["brake"].astype(float))
        result["brake"] = interp >= 0.5

    if "drs" in tel.columns:
        idx = np.clip(np.searchsorted(src_dist, dist_grid, side="left"),
                      0, len(tel) - 1)
        result["drs"] = tel["drs"].values[idx]

    result["abbreviation"] = tel["abbreviation"].iloc[0]
    result["team"]         = tel["team"].iloc[0]
    result["lap_number"]   = tel["lap_number"].iloc[0]

    return pd.DataFrame(result)


# ── Derived metrics ───────────────────────────────────────────────────────────

def cumulative_time(tel_interp: pd.DataFrame) -> np.ndarray:
    """
    Reconstruct elapsed time from speed and distance.
    dt = dd / v  integrated along the lap.
    Ground truth lap time lives in mart_lap_times — this is for shape/comparison.
    """
    speed_ms = tel_interp["speed"].values / 3.6
    speed_ms = np.where(speed_ms < 1.0, 1.0, speed_ms)
    dist     = tel_interp["distance"].values
    dd       = np.diff(dist, prepend=dist[0])
    return np.cumsum(dd / speed_ms)
