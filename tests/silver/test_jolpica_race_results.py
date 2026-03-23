import datetime
import pandas as pd
import pytest
from ingestion.silver.jolpica_race_results import clean_race_results

def make_row(**overrides) -> dict:
    base = {
        "season": 2026,
        "round": 1,
        "race_name": "Australian Grand Prix",
        "circuit": "Albert Park Grand Prix Circuit",
        "date": "2026-03-08",
        "driver_id": "russell",
        "driver_code": "RUS",
        "driver_name": "George Russell",
        "constructor": "Mercedes",
        "grid": 1,
        "position": 1,
        "points": 25.0,
        "status": "Finished",
        "fastest_lap_rank": 6.0,
        "source": "jolpica",
        "ingested_at": "2026-03-22T09:05:35.989350+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestTypeCasting:

    def test_date_cast_to_date(self):
        df = clean_race_results(make_df(make_row()))
        assert isinstance(df["date"].iloc[0], datetime.date)

    def test_ingested_at_cast_to_datetime(self):
        df = clean_race_results(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])

    def test_ingested_at_is_utc_aware(self):
        df = clean_race_results(make_df(make_row()))
        assert str(df["ingested_at"].dt.tz) == "UTC"

    def test_fastest_lap_rank_cast_to_int(self):
        df = clean_race_results(make_df(make_row(fastest_lap_rank=6.0)))
        assert df["fastest_lap_rank"].dtype == "Int64"
        assert df["fastest_lap_rank"].iloc[0] == 6

    def test_fastest_lap_rank_null_stays_null(self):
        df = clean_race_results(make_df(make_row(fastest_lap_rank=None)))
        assert pd.isna(df["fastest_lap_rank"].iloc[0])

    def test_fastest_lap_rank_is_nullable_int_not_float(self):
        """Ensure we're not silently keeping NaN as float after casting."""
        df = clean_race_results(make_df(
            make_row(fastest_lap_rank=1.0),
            make_row(fastest_lap_rank=None, driver_id="norris", round=2),
        ))
        assert df["fastest_lap_rank"].dtype == "Int64"


class TestIdNormalisation:

    def test_driver_id_lowercased(self):
        df = clean_race_results(make_df(make_row(driver_id="Russell")))
        assert df["driver_id"].iloc[0] == "russell"

    def test_driver_id_spaces_replaced_with_underscore(self):
        df = clean_race_results(make_df(make_row(driver_id="de vries")))
        assert df["driver_id"].iloc[0] == "de_vries"

    def test_driver_id_stripped_of_whitespace(self):
        df = clean_race_results(make_df(make_row(driver_id="  russell  ")))
        assert df["driver_id"].iloc[0] == "russell"

    def test_constructor_lowercased(self):
        df = clean_race_results(make_df(make_row(constructor="Mercedes")))
        assert df["constructor"].iloc[0] == "mercedes"

    def test_constructor_spaces_replaced_with_underscore(self):
        df = clean_race_results(make_df(make_row(constructor="Red Bull")))
        assert df["constructor"].iloc[0] == "red_bull"

    def test_constructor_stripped_of_whitespace(self):
        df = clean_race_results(make_df(make_row(constructor="  Mercedes  ")))
        assert df["constructor"].iloc[0] == "mercedes"


class TestNullHandling:

    def test_status_null_filled_with_unknown(self):
        df = clean_race_results(make_df(make_row(status=None)))
        assert df["status"].iloc[0] == "Unknown"

    def test_status_preserved_when_not_null(self):
        df = clean_race_results(make_df(make_row(status="Finished")))
        assert df["status"].iloc[0] == "Finished"

    def test_driver_code_null_filled_with_unk(self):
        df = clean_race_results(make_df(make_row(driver_code=None)))
        assert df["driver_code"].iloc[0] == "UNK"

    def test_driver_name_null_filled_with_unknown_driver(self):
        df = clean_race_results(make_df(make_row(driver_name=None)))
        assert df["driver_name"].iloc[0] == "Unknown Driver"


class TestDeduplication:
 
    def test_exact_duplicate_rows_removed(self):
        row = make_row()
        df = clean_race_results(make_df(row, row))
        assert len(df) == 1

    def test_last_duplicate_kept(self):
        row1 = make_row(points=25.0, status="Finished")
        row2 = make_row(points=25.0, status="Finished — updated")
        df = clean_race_results(make_df(row1, row2))
        assert df["status"].iloc[0] == "Finished — updated"

    def test_different_drivers_same_round_not_deduped(self):
        row1 = make_row(driver_id="russell", position=1)
        row2 = make_row(driver_id="norris", position=2)
        df = clean_race_results(make_df(row1, row2))
        assert len(df) == 2

    def test_same_driver_different_rounds_not_deduped(self):
        row1 = make_row(round=1)
        row2 = make_row(round=2)
        df = clean_race_results(make_df(row1, row2))
        assert len(df) == 2

    def test_same_driver_different_seasons_not_deduped(self):
        row1 = make_row(season=2025)
        row2 = make_row(season=2026)
        df = clean_race_results(make_df(row1, row2))
        assert len(df) == 2


class TestOutputShape:

    def test_no_columns_dropped(self):
        input_df = make_df(make_row())
        output_df = clean_race_results(input_df)
        assert set(input_df.columns) == set(output_df.columns)

    def test_no_extra_columns_added(self):
        input_df = make_df(make_row())
        output_df = clean_race_results(input_df)
        assert set(output_df.columns) == set(input_df.columns)