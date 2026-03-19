import logging
import os
from datetime import datetime, timezone
import s3fs
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger(__name__)

def df_write_to_s3_raw(df: pd.DataFrame, source: str, year: int, endpoint: str) -> str:
    df = df.copy()
    df["source"] = source
    df["ingested_at"] = datetime.now(timezone.utc).isoformat()
    bucket = os.getenv("S3_BUCKET_RAW")
    key = f"{source}/{year}/{endpoint}.parquet"
    s3_path = f"s3://{bucket}/{key}"

    fs = s3fs.S3FileSystem(
        key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret=os.getenv("AWS_SECRET_ACCESS_KEY"),
        client_kwargs={"region_name": os.getenv("AWS_REGION")},
    )

    with fs.open(s3_path, "wb") as f:
        df.to_parquet(f, index=False)

    return s3_path

