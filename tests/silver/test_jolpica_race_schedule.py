import pandas as pd
import pytest
from ingestion.silver.jolpica_race_schedule import combine_date_time, clean_race_schedule

def make_row(**overrides) -> dict:
    base = {
        "season": 2026,
        "round": 1,
        "race_name": "Australian Grand Prix",
        "circuit": "Albert Park Grand Prix Circuit",
        "race_date": "2026-03-08",
        "race_start_time": "04:00:00Z",
        "fp1_date": "2026-03-06",
        "fp1_time": "01:30:00Z",
        "fp2_date": "2026-03-06",
        "fp2_time": "05:00:00Z",
        "fp3_date": "2026-03-07",
        "fp3_time": "01:30:00Z",
        "sprint_qualy_date": None,
        "sprint_qualy_time": None,
        "qualy_date": "2026-03-07",
        "qualy_time": "05:00:00Z",
        "source": "jolpica",
        "ingested_at": "2026-03-18T21:46:42.364626+00:00",
    }
    base.update(overrides)
    return base

def make_sprint_row(**overrides) -> dict:
    base = make_row(
        race_name="Chinese Grand Prix",
        circuit="Shanghai International Circuit",
        race_date="2026-03-22",
        race_start_time="07:00:00Z",
        fp1_date="2026-03-20",
        fp1_time="03:30:00Z",
        fp2_date=None,
        fp2_time=None,
        fp3_date=None,
        fp3_time=None,
        sprint_qualy_date="2026-03-21",
        sprint_qualy_time="03:30:00Z",
        qualy_date="2026-03-20",
        qualy_time="07:00:00Z",
        round=2,
    )
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestCombineDatetime:
 
    def test_valid_date_and_time_produces_utc_datetime(self):
        dates = pd.Series(["2026-03-08"])
        times = pd.Series(["04:00:00Z"])
        result = combine_date_time(dates, times)
        assert pd.api.types.is_datetime64_any_dtype(result)
        assert str(result.dt.tz) == "UTC"

    def test_correct_datetime_value(self):
        dates = pd.Series(["2026-03-08"])
        times = pd.Series(["04:00:00Z"])
        result = combine_date_time(dates, times)
        assert result.iloc[0] == pd.Timestamp("2026-03-08T04:00:00Z")

    def test_null_date_produces_nat(self):
        dates = pd.Series([None])
        times = pd.Series([None])
        result = combine_date_time(dates, times)
        assert pd.isna(result.iloc[0])


class TestColumnConsolidation:

    def test_original_date_columns_dropped(self):
        df = clean_race_schedule(make_df(make_row()))
        date_cols = [
            "race_date", "fp1_date", "fp2_date", "fp3_date",
            "sprint_qualy_date", "qualy_date",
        ]
        for col in date_cols:
            assert col not in df.columns, f"{col} should have been dropped"

    def test_original_time_columns_dropped(self):
        df = clean_race_schedule(make_df(make_row()))
        time_cols = [
            "race_start_time", "fp1_time", "fp2_time", "fp3_time",
            "sprint_qualy_time", "qualy_time",
        ]
        for col in time_cols:
            assert col not in df.columns, f"{col} should have been dropped"

    def test_combined_datetime_columns_present(self):
        df = clean_race_schedule(make_df(make_row()))
        expected = [
            "race_datetime", "fp1_datetime", "fp2_datetime",
            "fp3_datetime", "sprint_qualy_datetime", "qualy_datetime",
        ]
        for col in expected:
            assert col in df.columns, f"{col} should be present"

    def test_output_has_fewer_columns_than_input(self):
        input_df = make_df(make_row())
        input_col_count = len(input_df.columns)
        output_df = clean_race_schedule(input_df.copy())
        assert len(output_df.columns) == input_col_count - 6


class TestTypeCasting:

    def test_race_datetime_is_utc_aware(self):
        df = clean_race_schedule(make_df(make_row()))
        assert str(df["race_datetime"].dt.tz) == "UTC"

    def test_fp1_datetime_is_utc_aware(self):
        df = clean_race_schedule(make_df(make_row()))
        assert str(df["fp1_datetime"].dt.tz) == "UTC"

    def test_ingested_at_cast_to_datetime(self):
        df = clean_race_schedule(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])

    def test_ingested_at_is_utc_aware(self):
        df = clean_race_schedule(make_df(make_row()))
        assert str(df["ingested_at"].dt.tz) == "UTC"


class TestSprintWeekends:

    def test_sprint_qualy_datetime_null_for_non_sprint(self):
        df = clean_race_schedule(make_df(make_row()))
        assert pd.isna(df["sprint_qualy_datetime"].iloc[0])

    def test_sprint_qualy_datetime_populated_for_sprint_round(self):
        df = clean_race_schedule(make_df(make_sprint_row()))
        assert not pd.isna(df["sprint_qualy_datetime"].iloc[0])

    def test_fp2_datetime_null_for_sprint_round(self):
        df = clean_race_schedule(make_df(make_sprint_row()))
        assert pd.isna(df["fp2_datetime"].iloc[0])

    def test_non_sprint_and_sprint_rows_coexist(self):
        df = clean_race_schedule(make_df(make_row(), make_sprint_row()))
        assert len(df) == 2


class TestNullHandling:

    def test_race_name_null_filled(self):
        df = clean_race_schedule(make_df(make_row(race_name=None)))
        assert df["race_name"].iloc[0] == "Unknown Race"

    def test_circuit_null_filled(self):
        df = clean_race_schedule(make_df(make_row(circuit=None)))
        assert df["circuit"].iloc[0] == "Unknown Circuit"

    def test_race_name_preserved_when_not_null(self):
        df = clean_race_schedule(make_df(make_row(race_name="Australian Grand Prix")))
        assert df["race_name"].iloc[0] == "Australian Grand Prix"


class TestDeduplication:

    def test_exact_duplicate_rows_removed(self):
        row = make_row()
        df = clean_race_schedule(make_df(row, row))
        assert len(df) == 1

    def test_last_duplicate_kept(self):
        row1 = make_row(race_name="Old Name")
        row2 = make_row(race_name="Australian Grand Prix")
        df = clean_race_schedule(make_df(row1, row2))
        assert df["race_name"].iloc[0] == "Australian Grand Prix"

    def test_different_rounds_not_deduped(self):
        row1 = make_row(round=1)
        row2 = make_row(round=2)
        df = clean_race_schedule(make_df(row1, row2))
        assert len(df) == 2

    def test_same_round_different_seasons_not_deduped(self):
        row1 = make_row(season=2025)
        row2 = make_row(season=2026)
        df = clean_race_schedule(make_df(row1, row2))
        assert len(df) == 2