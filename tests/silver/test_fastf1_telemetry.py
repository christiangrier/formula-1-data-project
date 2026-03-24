import pandas as pd
import pytest
from ingestion.silver.fastf1_telemetry import clean_fastf1_telemetry

def make_row(**overrides) -> dict:
    base = {
        "date": "2026-03-08 04:03:26.366",
        "session_time": 3_739_743_000_000,
        "driver_ahead": "",
        "distance_to_driver_ahead": 0.0,
        "time": 0,
        "rpm": 12_500.0,
        "speed": 0.0,
        "n_gear": 1,
        "throttle": 24.0,
        "brake": True,
        "drs": 0,
        "source": "fastf1",
        "distance": 0.0,
        "relative_distance": 0.0,
        "status": "OnTrack",
        "x": -768.0,
        "y": -1740.0,
        "z": 88.0,
        "season": 2026,
        "round": 1,
        "driver": "NOR",
        "team": "McLaren",
        "lap_number": 1,
        "ingested_at": "2026-03-22T03:12:16.206831+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestNanosecondConversions:

    def test_session_time_converted_to_seconds(self):
        df = clean_fastf1_telemetry(make_df(make_row(session_time=3_739_743_000_000)))
        assert "session_time" not in df.columns
        assert "session_time_seconds" in df.columns
        assert df["session_time_seconds"].iloc[0] == pytest.approx(3739.743)

    def test_time_converted_to_lap_time_seconds(self):
        df = clean_fastf1_telemetry(make_df(make_row(time=46_000_000)))
        assert "time" not in df.columns
        assert "lap_time_seconds" in df.columns
        assert df["lap_time_seconds"].iloc[0] == pytest.approx(0.046)

    def test_time_zero_converts_to_zero_seconds(self):
        df = clean_fastf1_telemetry(make_df(make_row(time=0)))
        assert df["lap_time_seconds"].iloc[0] == pytest.approx(0.0)

    def test_original_session_time_dropped(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert "session_time" not in df.columns

    def test_original_time_dropped(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert "time" not in df.columns


class TestDateCasting:

    def test_date_cast_to_datetime(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_date_is_utc_aware(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert str(df["date"].dt.tz) == "UTC"

    def test_ingested_at_cast_to_utc_datetime(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])
        assert str(df["ingested_at"].dt.tz) == "UTC"


class TestIdNormalisation:

    def test_driver_abbreviation_lowercased(self):
        df = clean_fastf1_telemetry(make_df(make_row(driver="NOR")))
        assert df["driver"].iloc[0] == "nor"

    def test_team_lowercased(self):
        df = clean_fastf1_telemetry(make_df(make_row(team="McLaren")))
        assert df["team"].iloc[0] == "mclaren"

    def test_team_spaces_replaced_with_underscore(self):
        df = clean_fastf1_telemetry(make_df(make_row(team="Red Bull Racing")))
        assert df["team"].iloc[0] == "red_bull_racing"

    def test_driver_no_underscore_added(self):
        df = clean_fastf1_telemetry(make_df(make_row(driver="RUS")))
        assert df["driver"].iloc[0] == "rus"


class TestNullHandling:

    def test_empty_driver_ahead_normalised_to_none(self):
        df = clean_fastf1_telemetry(make_df(make_row(driver_ahead="")))
        val = df["driver_ahead"].iloc[0]
        assert val is None or pd.isna(val)

    def test_driver_ahead_value_preserved_when_not_empty(self):
        df = clean_fastf1_telemetry(make_df(make_row(driver_ahead="RUS")))
        assert df["driver_ahead"].iloc[0] == "RUS"

    def test_empty_status_normalised_to_none(self):
        df = clean_fastf1_telemetry(make_df(make_row(status="")))
        val = df["status"].iloc[0]
        assert val is None or pd.isna(val)

    def test_status_preserved_when_not_empty(self):
        df = clean_fastf1_telemetry(make_df(make_row(status="OnTrack")))
        assert df["status"].iloc[0] == "OnTrack"


class TestRowDropping:

    def test_null_distance_row_dropped(self):
        row_valid = make_row(driver="nor", lap_number=2)
        row_null = make_row(driver="rus", lap_number=2, distance=None)
        df = clean_fastf1_telemetry(make_df(row_valid, row_null))
        assert len(df) == 1
        assert df["driver"].iloc[0] == "nor"

    def test_valid_distance_zero_kept(self):
        row = make_row(distance=0.0)
        df = clean_fastf1_telemetry(make_df(row))
        assert len(df) == 1

    def test_all_valid_rows_kept(self):
        rows = [make_row(driver=f"d{i}", distance=float(i)) for i in range(5)]
        df = clean_fastf1_telemetry(make_df(*rows))
        assert len(df) == 5


class TestDeduplication:

    def test_exact_duplicate_removed(self):
        row = make_row()
        df = clean_fastf1_telemetry(make_df(row, row))
        assert len(df) == 1

    def test_different_date_not_deduped(self):
        row1 = make_row(date="2026-03-08 04:03:26.366")
        row2 = make_row(date="2026-03-08 04:03:26.412")
        df = clean_fastf1_telemetry(make_df(row1, row2))
        assert len(df) == 2

    def test_different_drivers_same_timestamp_not_deduped(self):
        row1 = make_row(driver="NOR", date="2026-03-08 04:03:26.366")
        row2 = make_row(driver="RUS", date="2026-03-08 04:03:26.366")
        df = clean_fastf1_telemetry(make_df(row1, row2))
        assert len(df) == 2

    def test_different_lap_numbers_not_deduped(self):
        row1 = make_row(lap_number=1)
        row2 = make_row(lap_number=2)
        df = clean_fastf1_telemetry(make_df(row1, row2))
        assert len(df) == 2


class TestOutputShape:

    def test_session_time_seconds_present(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert "session_time_seconds" in df.columns

    def test_lap_time_seconds_present(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert "lap_time_seconds" in df.columns

    def test_original_ns_columns_absent(self):
        df = clean_fastf1_telemetry(make_df(make_row()))
        assert "session_time" not in df.columns
        assert "time" not in df.columns