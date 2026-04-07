import logging
import os
from pathlib import Path
import fastf1
import pandas as pd
from dotenv import load_dotenv
from ingestion.bronze.fastf1.helper import rename_columns


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

ENDPOINTS = [
    "results",
    "laps",
    "weather_data"
]

logger = logging.getLogger(__name__)

def load_session(year: int, round_number: int) -> dict[str, pd.DataFrame]:

    cache_path = REPO_ROOT / os.getenv("FASTF1_CACHE_PATH", "dbt/data/fastf1_cache")
    cache_path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(cache_path)

    session = fastf1.get_session(year, round_number, "R")
    session.load(telemetry=False, weather=True, messages=False)

    results = {}
    for endpoint in ENDPOINTS:
        df = rename_columns(getattr(session, endpoint))
        df["season"] = year
        df["round"] = round_number
        results[endpoint] = df
    return results