"""
Matplotlib chart functions for the Streamlit dashboard.
All functions return a matplotlib Figure — Streamlit renders via st.pyplot(fig).
No Plotly anywhere in this module.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.gridspec import GridSpec

# ── Theme constants ───────────────────────────────────────────────────────────
BG_DARK   = "#0f1117"   # matches Streamlit dark background
BG_PANEL  = "#1a1a2e"
GRID_COL  = "#2a2a3e"
TEXT_COL  = "#e0e0e0"
ZERO_LINE = "#ffffff"

DRIVER_COLORS = ["#FF8000", "#27F4D2"]  # A = orange, B = teal


def _base_fig(figsize=(14, 5)) -> tuple:
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_COL)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.yaxis.label.set_color(TEXT_COL)
    ax.title.set_color(TEXT_COL)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
    ax.grid(True, color=GRID_COL, linewidth=0.5, linestyle="--", alpha=0.6)
    return fig, ax


def _style_ax(ax):
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_COL, labelsize=8)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.yaxis.label.set_color(TEXT_COL)
    ax.title.set_color(TEXT_COL)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
    ax.grid(True, color=GRID_COL, linewidth=0.5, linestyle="--", alpha=0.5)


# ── Track maps ────────────────────────────────────────────────────────────────

def track_map_speed(
    tel_a: pd.DataFrame, tel_b: pd.DataFrame,
    driver_a: str, driver_b: str,
    race_name: str, lap_a: int, lap_b: int,
) -> plt.Figure:
    """Side-by-side speed track maps for two drivers."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(BG_DARK)
    fig.suptitle(f"Speed Map — {race_name}", color=TEXT_COL, fontsize=13)

    cmap = cm.get_cmap("plasma")

    for ax, (driver, tel, lap) in zip(
        axes, [(driver_a, tel_a, lap_a), (driver_b, tel_b, lap_b)]
    ):
        ax.set_facecolor(BG_PANEL)
        values = tel["speed"].values.astype(float)
        norm   = Normalize(vmin=np.nanpercentile(values, 2),
                           vmax=np.nanpercentile(values, 98))

        points   = np.array([tel["x"], tel["y"]]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, cmap=cmap, norm=norm,
                            linewidth=3, capstyle="round")
        lc.set_array(values[:-1])
        ax.add_collection(lc)

        cb = fig.colorbar(lc, ax=ax, pad=0.02, fraction=0.03)
        cb.set_label("Speed (km/h)", color=TEXT_COL, fontsize=8)
        cb.ax.yaxis.set_tick_params(color=TEXT_COL, labelsize=7)
        plt.setp(cb.ax.yaxis.get_ticklabels(), color=TEXT_COL)

        ax.autoscale_view()
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{driver}  —  Lap {lap}", color=TEXT_COL, fontsize=11)

    plt.tight_layout()
    return fig


def track_map_delta(
    tel_a_interp: pd.DataFrame, tel_b_interp: pd.DataFrame,
    dist_grid: np.ndarray,
    driver_a: str, driver_b: str,
    race_name: str, lap_a: int, lap_b: int,
) -> plt.Figure:
    """Track map coloured by speed delta (A − B). Blue = A faster, Red = B faster."""
    speed_delta = tel_a_interp["speed"].values - tel_b_interp["speed"].values
    x_grid      = tel_a_interp["x"].values
    y_grid      = tel_a_interp["y"].values

    abs_max = np.percentile(np.abs(speed_delta), 95)
    norm    = Normalize(vmin=-abs_max, vmax=abs_max)
    cmap    = cm.get_cmap("RdBu")

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)

    points   = np.array([x_grid, y_grid]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap=cmap, norm=norm,
                        linewidth=4, capstyle="round")
    lc.set_array(speed_delta[:-1])
    ax.add_collection(lc)

    cb = fig.colorbar(lc, ax=ax, pad=0.02, fraction=0.03)
    cb.set_label(
        f"Speed delta (km/h)   +ve = {driver_a} faster   −ve = {driver_b} faster",
        color=TEXT_COL, fontsize=8,
    )
    cb.ax.yaxis.set_tick_params(color=TEXT_COL, labelsize=7)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=TEXT_COL)

    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        f"Speed Delta: {driver_a} (lap {lap_a}) vs {driver_b} (lap {lap_b})  |  {race_name}",
        color=TEXT_COL, fontsize=11,
    )
    plt.tight_layout()
    return fig


def track_map_braking(
    tel_a: pd.DataFrame, tel_b: pd.DataFrame,
    driver_a: str, driver_b: str,
    race_name: str, lap_a: int, lap_b: int,
) -> plt.Figure:
    """Side-by-side braking zone maps."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(BG_DARK)
    fig.suptitle(f"Braking Zones — {race_name}", color=TEXT_COL, fontsize=13)

    for ax, (driver, tel, lap) in zip(
        axes, [(driver_a, tel_a, lap_a), (driver_b, tel_b, lap_b)]
    ):
        ax.set_facecolor(BG_PANEL)
        ax.plot(tel["x"], tel["y"], color="#333333", linewidth=2, zorder=1)
        braking = tel[tel["brake"] == True]
        coasting = tel[tel["brake"] == False]
        ax.scatter(coasting["x"], coasting["y"],
                   color="#555555", s=2, zorder=2, label="No brake")
        ax.scatter(braking["x"], braking["y"],
                   color="#FF4444", s=6, zorder=3, label="Braking")
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{driver}  —  Lap {lap}", color=TEXT_COL, fontsize=11)
        legend = ax.legend(facecolor=BG_PANEL, labelcolor=TEXT_COL,
                           markerscale=3, loc="lower right", fontsize=8)

    plt.tight_layout()
    return fig


# ── Telemetry traces ──────────────────────────────────────────────────────────

def speed_trace(
    tel_a_interp: pd.DataFrame, tel_b_interp: pd.DataFrame,
    dist_grid: np.ndarray,
    driver_a: str, driver_b: str,
    race_name: str, lap_a: int, lap_b: int,
) -> plt.Figure:
    """Speed overlay + delta on a shared distance axis."""
    fig = plt.figure(figsize=(14, 7))
    fig.patch.set_facecolor(BG_DARK)
    gs = GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08, figure=fig)

    ax_speed = fig.add_subplot(gs[0])
    ax_delta = fig.add_subplot(gs[1], sharex=ax_speed)

    for ax in [ax_speed, ax_delta]:
        _style_ax(ax)

    # Speed overlay
    ax_speed.plot(dist_grid, tel_a_interp["speed"],
                  color=DRIVER_COLORS[0], linewidth=1.5,
                  label=f"{driver_a} (lap {lap_a})")
    ax_speed.plot(dist_grid, tel_b_interp["speed"],
                  color=DRIVER_COLORS[1], linewidth=1.5,
                  label=f"{driver_b} (lap {lap_b})")
    ax_speed.set_ylabel("Speed (km/h)", color=TEXT_COL)
    ax_speed.legend(facecolor=BG_PANEL, labelcolor=TEXT_COL, fontsize=9)
    ax_speed.set_title(
        f"Speed Trace — {driver_a} vs {driver_b}  |  {race_name}",
        color=TEXT_COL, fontsize=12,
    )
    plt.setp(ax_speed.get_xticklabels(), visible=False)

    # Delta
    speed_delta = tel_a_interp["speed"].values - tel_b_interp["speed"].values
    ax_delta.plot(dist_grid, speed_delta, color="#aaaaaa", linewidth=1.2)
    ax_delta.fill_between(dist_grid, speed_delta, 0,
                          where=speed_delta >= 0,
                          color=DRIVER_COLORS[0], alpha=0.4)
    ax_delta.fill_between(dist_grid, speed_delta, 0,
                          where=speed_delta < 0,
                          color=DRIVER_COLORS[1], alpha=0.4)
    ax_delta.axhline(0, color=ZERO_LINE, linewidth=0.8, linestyle="--", alpha=0.5)
    ax_delta.set_ylabel("Δ Speed (km/h)", color=TEXT_COL, fontsize=9)
    ax_delta.set_xlabel("Distance (m)", color=TEXT_COL)

    plt.tight_layout()
    return fig


def time_distance(
    tel_a_interp: pd.DataFrame, tel_b_interp: pd.DataFrame,
    dist_grid: np.ndarray,
    cum_time_a: np.ndarray, cum_time_b: np.ndarray,
    driver_a: str, driver_b: str,
    race_name: str, lap_a: int, lap_b: int,
) -> plt.Figure:
    """Cumulative lap time vs distance + time delta subplot."""
    time_delta = cum_time_a - cum_time_b

    fig = plt.figure(figsize=(14, 7))
    fig.patch.set_facecolor(BG_DARK)
    gs = GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08, figure=fig)

    ax_time  = fig.add_subplot(gs[0])
    ax_delta = fig.add_subplot(gs[1], sharex=ax_time)

    for ax in [ax_time, ax_delta]:
        _style_ax(ax)

    ax_time.plot(dist_grid, cum_time_a,
                 color=DRIVER_COLORS[0], linewidth=1.5,
                 label=f"{driver_a} (lap {lap_a})")
    ax_time.plot(dist_grid, cum_time_b,
                 color=DRIVER_COLORS[1], linewidth=1.5,
                 label=f"{driver_b} (lap {lap_b})")
    ax_time.set_ylabel("Elapsed time (s)", color=TEXT_COL)
    ax_time.legend(facecolor=BG_PANEL, labelcolor=TEXT_COL, fontsize=9)
    ax_time.set_title(
        f"Lap Time vs Distance — {driver_a} vs {driver_b}  |  {race_name}",
        color=TEXT_COL, fontsize=12,
    )
    plt.setp(ax_time.get_xticklabels(), visible=False)

    ax_delta.plot(dist_grid, time_delta, color="#aaaaaa", linewidth=1.2)
    ax_delta.fill_between(dist_grid, time_delta, 0,
                          where=time_delta >= 0,
                          color=DRIVER_COLORS[1], alpha=0.4,
                          label=f"{driver_b} ahead")
    ax_delta.fill_between(dist_grid, time_delta, 0,
                          where=time_delta < 0,
                          color=DRIVER_COLORS[0], alpha=0.4,
                          label=f"{driver_a} ahead")
    ax_delta.axhline(0, color=ZERO_LINE, linewidth=0.8, linestyle="--", alpha=0.5)
    ax_delta.set_ylabel(f"Δ time (s)\n+ve={driver_a} behind", color=TEXT_COL, fontsize=8)
    ax_delta.set_xlabel("Distance (m)", color=TEXT_COL)
    ax_delta.legend(facecolor=BG_PANEL, labelcolor=TEXT_COL, fontsize=8,
                    loc="upper left")

    plt.tight_layout()
    return fig


def four_panel_trace(
    tel_a_interp: pd.DataFrame, tel_b_interp: pd.DataFrame,
    dist_grid: np.ndarray,
    driver_a: str, driver_b: str,
    race_name: str, lap_a: int, lap_b: int,
) -> plt.Figure:
    """4-panel trace: Speed / Throttle / Brake / Gear on shared distance axis."""
    channels = [
        ("speed",    "Speed (km/h)"),
        ("throttle", "Throttle (%)"),
        ("brake",    "Brake"),
        ("n_gear",   "Gear"),
    ]

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    fig.patch.set_facecolor(BG_DARK)
    fig.suptitle(
        f"Driver Comparison — {driver_a} vs {driver_b}  |  {race_name}",
        color=TEXT_COL, fontsize=12,
    )

    for ax, (ch, ylabel) in zip(axes, channels):
        _style_ax(ax)
        ax.plot(dist_grid, tel_a_interp[ch].astype(float),
                color=DRIVER_COLORS[0], linewidth=1.2,
                label=f"{driver_a} (lap {lap_a})")
        ax.plot(dist_grid, tel_b_interp[ch].astype(float),
                color=DRIVER_COLORS[1], linewidth=1.2,
                label=f"{driver_b} (lap {lap_b})")
        ax.set_ylabel(ylabel, color=TEXT_COL, fontsize=9)

    axes[0].legend(facecolor=BG_PANEL, labelcolor=TEXT_COL,
                   fontsize=9, loc="upper right")
    axes[-1].set_xlabel("Distance (m)", color=TEXT_COL)

    plt.tight_layout()
    return fig


def drs_by_lap_chart(
    drs_df: pd.DataFrame,
    driver_a: str, driver_b: str,
    race_name: str,
) -> plt.Figure:
    """DRS open % per lap — grouped bar chart."""
    fig, ax = _base_fig(figsize=(14, 4))

    df_a = drs_df[drs_df["abbreviation"] == driver_a]
    df_b = drs_df[drs_df["abbreviation"] == driver_b]

    laps   = sorted(drs_df["lap_number"].unique())
    x      = np.arange(len(laps))
    width  = 0.35

    ax.bar(x - width / 2,
           [df_a[df_a["lap_number"] == l]["drs_open_pct"].values[0]
            if l in df_a["lap_number"].values else 0 for l in laps],
           width=width, color=DRIVER_COLORS[0], label=driver_a, alpha=0.85)
    ax.bar(x + width / 2,
           [df_b[df_b["lap_number"] == l]["drs_open_pct"].values[0]
            if l in df_b["lap_number"].values else 0 for l in laps],
           width=width, color=DRIVER_COLORS[1], label=driver_b, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels([str(l) for l in laps], fontsize=7, color=TEXT_COL)
    ax.set_xlabel("Lap", color=TEXT_COL)
    ax.set_ylabel("DRS open (%)", color=TEXT_COL)
    ax.set_title(f"DRS Open % per Lap — {race_name}", color=TEXT_COL, fontsize=11)
    ax.legend(facecolor=BG_PANEL, labelcolor=TEXT_COL, fontsize=9)

    plt.tight_layout()
    return fig


def throttle_breakdown_chart(
    throttle_df: pd.DataFrame,
    driver_a: str, driver_b: str,
    race_name: str,
) -> plt.Figure:
    """Stacked throttle band bar chart — full / partial / lift."""
    fig, ax = _base_fig(figsize=(7, 4))

    bands  = ["full_throttle_pct", "partial_throttle_pct", "lift_pct"]
    labels = ["Full throttle", "Partial throttle", "Lift"]
    colors = ["#00CC66", "#FFAA00", "#CC3333"]

    drivers = [driver_a, driver_b]
    x       = np.arange(len(drivers))
    bottoms = np.zeros(len(drivers))

    for band, label, color in zip(bands, labels, colors):
        vals = [
            throttle_df[throttle_df["abbreviation"] == d][band].values[0]
            if d in throttle_df["abbreviation"].values else 0
            for d in drivers
        ]
        ax.bar(x, vals, bottom=bottoms, color=color, label=label,
               alpha=0.9, width=0.5)
        for i, (v, b) in enumerate(zip(vals, bottoms)):
            if v > 3:
                ax.text(x[i], b + v / 2, f"{v:.1f}%",
                        ha="center", va="center",
                        color="white", fontsize=8, fontweight="bold")
        bottoms += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels(drivers, color=TEXT_COL, fontsize=10)
    ax.set_ylabel("%", color=TEXT_COL)
    ax.set_ylim(0, 105)
    ax.set_title(f"Throttle Application — {race_name}", color=TEXT_COL, fontsize=11)
    ax.legend(facecolor=BG_PANEL, labelcolor=TEXT_COL, fontsize=8,
              loc="lower right")

    plt.tight_layout()
    return fig
