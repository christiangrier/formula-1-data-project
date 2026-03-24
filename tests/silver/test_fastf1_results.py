import pandas as pd
import pytest
from ingestion.silver.fastf1_results import clean_fastf1_results
from ingestion.silver.helpers import nanoseconds_to_seconds

def make_row(**overrides) -> dict:
    base = {
        "driver_number": "63",
        "broadcast_name": "G RUSSELL",
        "abbreviation": "RUS",
        "driver_id": "russell",
        "team_name": "Mercedes",
        "team_color": "00D7B6",
        "team_id": "mercedes",
        "first_name": "George",
        "last_name": "Russell",
        "full_name": "George Russell",
        "headshot_url": "https://media.formula1.com/image.png",
        "country_code": "GBR",
        "position": 1.0,
        "classified_position": "1",
        "grid_position": 1.0,
        "q1": None,
        "q2": None,
        "q3": None,
        "time": 4986801000000,
        "status": "Finished",
        "points": 25.0,
        "laps": 58.0,
        "season": 2026,
        "round": 1,
        "source": "fastf1",
        "ingested_at": "2026-03-22T03:06:36.278058+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestNanosecondsToSeconds:

    def test_basic_conversion(self):
        s = pd.Series([1_000_000_000])
        assert nanoseconds_to_seconds(s).iloc[0] == pytest.approx(1.0)

    def test_large_value(self):
        s = pd.Series([4_986_801_000_000])
        assert nanoseconds_to_seconds(s).iloc[0] == pytest.approx(4986.801)

    def test_null_preserved_as_nan(self):
        s = pd.Series([None])
        assert pd.isna(nanoseconds_to_seconds(s).iloc[0])

    def test_zero_returns_zero(self):
        s = pd.Series([0])
        assert nanoseconds_to_seconds(s).iloc[0] == pytest.approx(0.0)


class TestColumnTransformations:

    def test_headshot_url_dropped(self):
        df = clean_fastf1_results(make_df(make_row()))
        assert "headshot_url" not in df.columns

    def test_time_converted_to_time_seconds(self):
        df = clean_fastf1_results(make_df(make_row(time=4_986_801_000_000)))
        assert "time" not in df.columns
        assert "time_seconds" in df.columns
        assert df["time_seconds"].iloc[0] == pytest.approx(4986.801)

    def test_q1_converted_to_q1_seconds(self):
        df = clean_fastf1_results(make_df(make_row(q1=90_000_000_000)))
        assert "q1" not in df.columns
        assert "q1_seconds" in df.columns
        assert df["q1_seconds"].iloc[0] == pytest.approx(90.0)

    def test_q1_null_stays_null(self):
        df = clean_fastf1_results(make_df(make_row(q1=None)))
        assert pd.isna(df["q1_seconds"].iloc[0])

    def test_q2_and_q3_converted(self):
        df = clean_fastf1_results(make_df(make_row(q2=91_000_000_000, q3=89_000_000_000)))
        assert "q2_seconds" in df.columns
        assert "q3_seconds" in df.columns


class TestTypeCasting:

    def test_ingested_at_cast_to_datetime(self):
        df = clean_fastf1_results(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])

    def test_ingested_at_is_utc_aware(self):
        df = clean_fastf1_results(make_df(make_row()))
        assert str(df["ingested_at"].dt.tz) == "UTC"

    def test_position_cast_to_nullable_int(self):
        df = clean_fastf1_results(make_df(make_row(position=1.0)))
        assert df["position"].dtype == "Int64"
        assert df["position"].iloc[0] == 1

    def test_position_null_stays_null(self):
        df = clean_fastf1_results(make_df(make_row(position=None)))
        assert pd.isna(df["position"].iloc[0])

    def test_grid_position_cast_to_nullable_int(self):
        df = clean_fastf1_results(make_df(make_row(grid_position=1.0)))
        assert df["grid_position"].dtype == "Int64"
        assert df["grid_position"].iloc[0] == 1

    def test_laps_cast_to_nullable_int(self):
        df = clean_fastf1_results(make_df(make_row(laps=58.0)))
        assert df["laps"].dtype == "Int64"
        assert df["laps"].iloc[0] == 58

    def test_points_stays_float(self):
        df = clean_fastf1_results(make_df(make_row(points=25.0)))
        assert df["points"].dtype == float


class TestIdNormalisation:

    def test_driver_id_lowercased(self):
        df = clean_fastf1_results(make_df(make_row(driver_id="Russell")))
        assert df["driver_id"].iloc[0] == "russell"

    def test_team_id_lowercased(self):
        df = clean_fastf1_results(make_df(make_row(team_id="Mercedes")))
        assert df["team_id"].iloc[0] == "mercedes"

    def test_team_id_spaces_replaced(self):
        df = clean_fastf1_results(make_df(make_row(team_id="Red Bull")))
        assert df["team_id"].iloc[0] == "red_bull"


class TestNullHandling:

    def test_empty_country_code_normalised_to_unknown(self):
        df = clean_fastf1_results(make_df(make_row(country_code="")))
        assert df["country_code"].iloc[0] == "Unknown"

    def test_country_code_null_filled_with_unknown(self):
        df = clean_fastf1_results(make_df(make_row(country_code=None)))
        assert df["country_code"].iloc[0] == "Unknown"

    def test_status_null_filled_with_unknown(self):
        df = clean_fastf1_results(make_df(make_row(status=None)))
        assert df["status"].iloc[0] == "Unknown"

    def test_classified_position_null_filled_with_unknown(self):
        df = clean_fastf1_results(make_df(make_row(classified_position=None)))
        assert df["classified_position"].iloc[0] == "Unknown"

    def test_classified_position_dnf_code_preserved(self):
        df = clean_fastf1_results(make_df(make_row(classified_position="R")))
        assert df["classified_position"].iloc[0] == "R"

    def test_full_name_null_filled(self):
        df = clean_fastf1_results(make_df(make_row(full_name=None)))
        assert df["full_name"].iloc[0] == "Unknown Driver"


class TestDeduplication:

    def test_exact_duplicate_rows_removed(self):
        row = make_row()
        df = clean_fastf1_results(make_df(row, row))
        assert len(df) == 1

    def test_last_duplicate_kept(self):
        row1 = make_row(status="Finished")
        row2 = make_row(status="Finished — updated")
        df = clean_fastf1_results(make_df(row1, row2))
        assert df["status"].iloc[0] == "Finished — updated"

    def test_different_drivers_not_deduped(self):
        row1 = make_row(driver_id="russell")
        row2 = make_row(driver_id="norris")
        df = clean_fastf1_results(make_df(row1, row2))
        assert len(df) == 2

    def test_same_driver_different_rounds_not_deduped(self):
        row1 = make_row(round=1)
        row2 = make_row(round=2)
        df = clean_fastf1_results(make_df(row1, row2))
        assert len(df) == 2


class TestOutputShape:

    def test_headshot_url_not_in_output(self):
        df = clean_fastf1_results(make_df(make_row()))
        assert "headshot_url" not in df.columns

    def test_original_time_columns_dropped(self):
        df = clean_fastf1_results(make_df(make_row()))
        for col in ["time", "q1", "q2", "q3"]:
            assert col not in df.columns

    def test_seconds_columns_present(self):
        df = clean_fastf1_results(make_df(make_row()))
        for col in ["time_seconds", "q1_seconds", "q2_seconds", "q3_seconds"]:
            assert col in df.columns