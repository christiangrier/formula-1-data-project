import logging
import os
import re
from pathlib import Path
import fastf1
import pandas as pd
from dotenv import load_dotenv
from ingestion.bronze.fastf1.helper import rename_columns

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

def get_driver_telemetry(year: int, round_number: int) -> pd.DataFrame:

    cache_path = REPO_ROOT / os.getenv("FASTF1_CACHE_PATH", "dbt/data/fastf1_cache")
    cache_path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_path))

    session = fastf1.get_session(year, round_number, "R")
    session.load(telemetry=True, weather=False, messages=False)

    all_telemetry = []
    drivers = session.laps["Driver"].unique()

    for driver in drivers:
        driver_laps = session.laps.pick_drivers(driver)

        try:
            telemetry = driver_laps.get_telemetry()
        except Exception as e:
            logger.warning(f"Telemetry unavailable for driver={driver}: {e}")
            continue

        if telemetry.empty:
            continue

        telemetry = telemetry.reset_index(drop=True)
        telemetry = rename_columns(telemetry)

        telemetry = telemetry.sort_values("session_time").reset_index(drop=True)

        laps_sorted = (
            driver_laps[["LapNumber", "LapStartTime"]]
            .dropna(subset=["LapStartTime"])
            .reset_index(drop=True)
            .sort_values("LapStartTime")
        )

        if laps_sorted.empty:
            logger.warning(f"No valid lap start times for driver={driver}, skipping")
            continue

        telemetry = pd.merge_asof(
            telemetry,
            laps_sorted,
            left_on="session_time",
            right_on="LapStartTime",
            direction="backward",
        ).rename(columns={"LapNumber": "lap_number"})

        telemetry["season"] = year
        telemetry["round"] = round_number
        telemetry["driver"] = driver
        telemetry["team"] = driver_laps["Team"].iloc[0]
        telemetry["lap_number"] = telemetry["lap_number"].astype("Int64")
        telemetry = telemetry.drop(columns=["LapStartTime"])
        cols = [c for c in telemetry.columns if c != "lap_number"] + ["lap_number"]
        telemetry = telemetry[cols]

        all_telemetry.append(telemetry)

    df = pd.concat(all_telemetry, ignore_index=True)

    logger.info(
        f"Telemetry loaded for year={year} and round={round_number} rows={len(df)}"
    )

    return df
