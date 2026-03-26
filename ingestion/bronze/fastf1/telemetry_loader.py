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

    cache_path = REPO_ROOT / os.getenv("FASTF1_CACHE_PATH", "data/fastf1_cache")
    fastf1.Cache.enable_cache(str(cache_path))

    session = fastf1.get_session(year, round_number, "R")
    session.load(telemetry=True, weather=False, messages=False)

    all_telemetry = []
    drivers = session.laps["Driver"].unique()

    for driver in drivers:
        driver_laps = session.laps.pick_drivers(driver)

        for _, lap in driver_laps.iterlaps():
            try:
                telemetry = pd.DataFrame(lap.get_telemetry())
                telemetry = rename_columns(telemetry)

                telemetry["season"] = year
                telemetry["round"] = round_number
                telemetry["driver"] = lap["Driver"]
                telemetry["team"] = lap["Team"]
                telemetry["lap_number"] = int(lap["LapNumber"])

                all_telemetry.append(telemetry)

            except Exception as e:
                logger.warning(
                    f"Telemetry unavailable for driver={driver} lap={lap['LapNumber']}: {e}"
                )
                continue

    df = pd.concat(all_telemetry, ignore_index=True)

    logger.info(
        f"Telemetry loaded for year={year} and round={round_number} "
        f"rows={len(df)}"
    )

    return df
