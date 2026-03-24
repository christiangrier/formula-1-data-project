import pandas as pd
import pytest
from ingestion.silver.fastf1_weather import clean_fastf1_weather

def make_row(**overrides) -> dict:
    base = {
        "time": 13_466_000_000,
        "air_temp": 23.1,
        "humidity": 55.8,
        "pressure": 1013.7,
        "rainfall": False,
        "track_temp": 36.2,
        "wind_direction": 114,
        "wind_speed": 1.8,
        "season": 2026,
        "round": 1,
        "source": "fastf1",
        "ingested_at": "2026-03-22T03:06:38.002261+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestNanosecondConversion:

    def test_time_converted_to_time_seconds(self):
        df = clean_fastf1_weather(make_df(make_row(time=13_466_000_000)))
        assert "time" not in df.columns
        assert "time_seconds" in df.columns
        assert df["time_seconds"].iloc[0] == pytest.approx(13.466)

    def test_original_time_column_dropped(self):
        df = clean_fastf1_weather(make_df(make_row()))
        assert "time" not in df.columns


class TestTypeCasting:
 
    def test_ingested_at_cast_to_datetime(self):
        df = clean_fastf1_weather(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])
 
    def test_ingested_at_is_utc_aware(self):
        df = clean_fastf1_weather(make_df(make_row()))
        assert str(df["ingested_at"].dt.tz) == "UTC"
 
    def test_rainfall_stays_boolean(self):
        df = clean_fastf1_weather(make_df(make_row(rainfall=False)))
        assert df["rainfall"].dtype == bool or df["rainfall"].dtype == "boolean"
 
    def test_numeric_columns_stay_float(self):
        df = clean_fastf1_weather(make_df(make_row()))
        for col in ["air_temp", "humidity", "pressure", "track_temp", "wind_speed"]:
            assert pd.api.types.is_float_dtype(df[col]), f"{col} should be float"


class TestForwardFill:

    def test_null_air_temp_filled_from_previous_row(self):
        row1 = make_row(time=13_466_000_000, air_temp=23.1)
        row2 = make_row(time=73_482_000_000, air_temp=None)
        df = clean_fastf1_weather(make_df(row1, row2))
        assert df.iloc[1]["air_temp"] == pytest.approx(23.1)

    def test_null_track_temp_filled_from_previous_row(self):
        row1 = make_row(time=13_466_000_000, track_temp=36.2)
        row2 = make_row(time=73_482_000_000, track_temp=None)
        df = clean_fastf1_weather(make_df(row1, row2))
        assert df.iloc[1]["track_temp"] == pytest.approx(36.2)

    def test_ffill_does_not_bleed_across_rounds(self):
        row_round1 = make_row(round=1, time=13_466_000_000, air_temp=23.1)
        row_round2 = make_row(round=2, time=13_466_000_000, air_temp=None)
        df = clean_fastf1_weather(make_df(row_round1, row_round2))
        round2_temp = df[df["round"] == 2]["air_temp"].iloc[0]
        assert pd.isna(round2_temp)

    def test_ffill_does_not_bleed_across_seasons(self):
        row_2025 = make_row(season=2025, round=1, time=13_466_000_000, air_temp=30.0)
        row_2026 = make_row(season=2026, round=1, time=13_466_000_000, air_temp=None)
        df = clean_fastf1_weather(make_df(row_2025, row_2026))
        row_2026_temp = df[df["season"] == 2026]["air_temp"].iloc[0]
        assert pd.isna(row_2026_temp)

    def test_non_null_air_temp_not_overwritten(self):
        row1 = make_row(time=13_466_000_000, air_temp=23.1)
        row2 = make_row(time=73_482_000_000, air_temp=24.5)
        df = clean_fastf1_weather(make_df(row1, row2))
        assert df.iloc[1]["air_temp"] == pytest.approx(24.5)

    def test_leading_null_stays_null(self):
        row1 = make_row(time=13_466_000_000, air_temp=None)
        row2 = make_row(time=73_482_000_000, air_temp=23.1)
        df = clean_fastf1_weather(make_df(row1, row2))
        assert pd.isna(df.iloc[0]["air_temp"])


class TestDeduplication:

    def test_exact_duplicate_removed(self):
        row = make_row()
        df = clean_fastf1_weather(make_df(row, row))
        assert len(df) == 1

    def test_different_time_not_deduped(self):
        row1 = make_row(time=13_466_000_000)
        row2 = make_row(time=73_482_000_000)
        df = clean_fastf1_weather(make_df(row1, row2))
        assert len(df) == 2

    def test_same_time_different_rounds_not_deduped(self):
        row1 = make_row(round=1, time=13_466_000_000)
        row2 = make_row(round=2, time=13_466_000_000)
        df = clean_fastf1_weather(make_df(row1, row2))
        assert len(df) == 2


class TestOutputShape:

    def test_time_seconds_present(self):
        df = clean_fastf1_weather(make_df(make_row()))
        assert "time_seconds" in df.columns

    def test_original_time_dropped(self):
        df = clean_fastf1_weather(make_df(make_row()))
        assert "time" not in df.columns

    def test_output_has_one_fewer_column_than_input(self):
        input_df = make_df(make_row())
        input_col_count = len(input_df.columns)
        output_df = clean_fastf1_weather(input_df.copy())
        assert len(output_df.columns) == input_col_count