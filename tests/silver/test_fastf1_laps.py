import pandas as pd
import pytest
from ingestion.silver.fastf1_laps import clean_fastf1_laps

def make_row(**overrides) -> dict:
    base = {
        "time": 3_836_437_000_000,
        "driver": "NOR",
        "driver_number": "1",
        "lap_time": 96_458_000_000,
        "lap_number": 2.0,
        "stint": 1.0,
        "pit_out_time": None,
        "pit_in_time": None,
        "sector1_time": None,
        "sector2_time": 18_163_000_000,
        "sector3_time": 38_796_000_000,
        "sector1_session_time": None,
        "sector2_session_time": 3_797_998_000_000,
        "sector3_session_time": 3_836_692_000_000,
        "speed_i1": 229.0,
        "speed_i2": 291.0,
        "speed_fl": 304.0,
        "speed_st": 217.0,
        "is_personal_best": False,
        "compound": "MEDIUM",
        "tyre_life": 1.0,
        "fresh_tyre": True,
        "team": "McLaren",
        "lap_start_time": 3_739_743_000_000,
        "lap_start_date": None,
        "track_status": "1",
        "position": 6.0,
        "deleted": 0,
        "deleted_reason": "",
        "fast_f1_generated": False,
        "is_accurate": True,
        "season": 2026,
        "round": 1,
        "source": "fastf1",
        "ingested_at": "2026-03-22T03:06:37.399936+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestFiltering:

    def test_inaccurate_laps_filtered_out(self):
        row_accurate = make_row(is_accurate=True)
        row_inaccurate = make_row(is_accurate=False, lap_number=3.0)
        df = clean_fastf1_laps(make_df(row_accurate, row_inaccurate))
        assert len(df) == 1

    def test_lap_number_1_filtered_out(self):
        row_lap1 = make_row(lap_number=1.0)
        row_lap2 = make_row(lap_number=2.0)
        df = clean_fastf1_laps(make_df(row_lap1, row_lap2))
        assert len(df) == 1
        assert df["lap_number"].iloc[0] == 2

    def test_inaccurate_lap_1_filtered_out(self):
        row = make_row(is_accurate=False, lap_number=1.0)
        df = clean_fastf1_laps(make_df(row))
        assert len(df) == 0

    def test_accurate_lap_2_kept(self):
        row = make_row(is_accurate=True, lap_number=2.0)
        df = clean_fastf1_laps(make_df(row))
        assert len(df) == 1

    def test_all_laps_accurate_and_above_1_kept(self):
        rows = [make_row(lap_number=float(i)) for i in range(2, 7)]
        df = clean_fastf1_laps(make_df(*rows))
        assert len(df) == 5


class TestNanosecondConversions:

    def test_lap_time_converted_to_seconds(self):
        df = clean_fastf1_laps(make_df(make_row(lap_time=96_458_000_000)))
        assert "lap_time" not in df.columns
        assert "lap_time_seconds" in df.columns
        assert df["lap_time_seconds"].iloc[0] == pytest.approx(96.458)

    def test_time_converted_to_seconds(self):
        df = clean_fastf1_laps(make_df(make_row(time=3_836_437_000_000)))
        assert "time" not in df.columns
        assert "time_seconds" in df.columns
        assert df["time_seconds"].iloc[0] == pytest.approx(3836.437)

    def test_sector2_time_converted(self):
        df = clean_fastf1_laps(make_df(make_row(sector2_time=18_163_000_000)))
        assert "sector2_time" not in df.columns
        assert "sector2_time_seconds" in df.columns
        assert df["sector2_time_seconds"].iloc[0] == pytest.approx(18.163)

    def test_null_sector_time_stays_null(self):
        df = clean_fastf1_laps(make_df(make_row(sector1_time=None)))
        assert pd.isna(df["sector1_time_seconds"].iloc[0])

    def test_all_ns_columns_dropped(self):
        df = clean_fastf1_laps(make_df(make_row()))
        ns_cols = [
            "time", "lap_time", "pit_out_time", "pit_in_time",
            "sector1_time", "sector2_time", "sector3_time",
            "sector1_session_time", "sector2_session_time",
            "sector3_session_time", "lap_start_time",
        ]
        for col in ns_cols:
            assert col not in df.columns, f"{col} should have been dropped"


class TestTypeCasting:
 
    def test_lap_number_cast_to_nullable_int(self):
        df = clean_fastf1_laps(make_df(make_row(lap_number=2.0)))
        assert df["lap_number"].dtype == "Int64"
        assert df["lap_number"].iloc[0] == 2

    def test_stint_cast_to_nullable_int(self):
        df = clean_fastf1_laps(make_df(make_row(stint=1.0)))
        assert df["stint"].dtype == "Int64"

    def test_tyre_life_cast_to_nullable_int(self):
        df = clean_fastf1_laps(make_df(make_row(tyre_life=1.0)))
        assert df["tyre_life"].dtype == "Int64"

    def test_position_cast_to_nullable_int(self):
        df = clean_fastf1_laps(make_df(make_row(position=6.0)))
        assert df["position"].dtype == "Int64"
        assert df["position"].iloc[0] == 6

    def test_deleted_cast_to_boolean(self):
        df = clean_fastf1_laps(make_df(make_row(deleted=0)))
        assert df["deleted"].dtype == "boolean"

    def test_ingested_at_cast_to_utc_datetime(self):
        df = clean_fastf1_laps(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])
        assert str(df["ingested_at"].dt.tz) == "UTC"


class TestIdNormalisation:

    def test_driver_abbreviation_lowercased(self):
        df = clean_fastf1_laps(make_df(make_row(driver="NOR")))
        assert df["driver"].iloc[0] == "nor"

    def test_team_lowercased(self):
        df = clean_fastf1_laps(make_df(make_row(team="McLaren")))
        assert df["team"].iloc[0] == "mclaren"

    def test_team_spaces_replaced_with_underscore(self):
        df = clean_fastf1_laps(make_df(make_row(team="Red Bull Racing")))
        assert df["team"].iloc[0] == "red_bull_racing"


class TestNullHandling:

    def test_empty_deleted_reason_normalised_to_none(self):
        df = clean_fastf1_laps(make_df(make_row(deleted_reason="")))
        val = df["deleted_reason"].iloc[0]
        assert val is None or pd.isna(val)

    def test_empty_track_status_normalised_to_none(self):
        df = clean_fastf1_laps(make_df(make_row(track_status="")))
        val = df["track_status"].iloc[0]
        assert val is None or pd.isna(val)

    def test_compound_null_filled_with_unknown(self):
        df = clean_fastf1_laps(make_df(make_row(compound=None)))
        assert df["compound"].iloc[0] == "UNKNOWN"

    def test_compound_preserved_when_not_null(self):
        df = clean_fastf1_laps(make_df(make_row(compound="SOFT")))
        assert df["compound"].iloc[0] == "SOFT"


class TestDeduplication:

    def test_exact_duplicate_removed(self):
        row = make_row()
        df = clean_fastf1_laps(make_df(row, row))
        assert len(df) == 1

    def test_different_drivers_same_lap_not_deduped(self):
        row1 = make_row(driver="NOR", lap_number=2.0)
        row2 = make_row(driver="RUS", lap_number=2.0)
        df = clean_fastf1_laps(make_df(row1, row2))
        assert len(df) == 2

    def test_same_driver_different_laps_not_deduped(self):
        row1 = make_row(lap_number=2.0)
        row2 = make_row(lap_number=3.0)
        df = clean_fastf1_laps(make_df(row1, row2))
        assert len(df) == 2