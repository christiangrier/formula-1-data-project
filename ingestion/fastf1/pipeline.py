import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from ingestion.fastf1.session_loader import load_session
from ingestion.fastf1.telemetry_loader import get_driver_telemetry
from ingestion.jolpica.writer import df_write_to_s3_raw
from ingestion.jolpica.helper import logging_setup

logging_setup()

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

ENDPOINTS = {
    "results": "results",
    "laps": "laps",
    "weather_data": "weather",
}

def fastf1_pipeline(year: int, round_number: int) -> None:
    bucket = os.getenv("S3_BUCKET_RAW")
    try:
        session_data = load_session(year, round_number)
        for key, endpoint in ENDPOINTS.items():
            df = session_data[key]
            df_write_to_s3_raw(
                df=df,
                source="fastf1",
                year=year,
                endpoint=f"{round_number}/{endpoint}"
            )
    except Exception as e:
        logger.error(
            f"Session load failed for year={year} and round={round_number}: {e}"
        )
        return

    try:
        telemetry_df = get_driver_telemetry(year, round_number)
        df_write_to_s3_raw(
            df=telemetry_df,
            source="fastf1",
            year=year,
            endpoint=f"{round_number}/telemetry",
        )

    except Exception as e:
        logger.error(
            f"Telemetry load failed for year={year} and round={round_number}: {e}"
        )
        return

    logger.info(f"Round {round_number} complete")