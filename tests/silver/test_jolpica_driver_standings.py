import datetime
import pandas as pd
import pytest
from ingestion.silver.jolpica_driver_standings import clean_driver_standings

def make_row(**overrides) -> dict:
    base = {
        "season": 2026,
        "round": 2,
        "driver_id": "russell",
        "driver_code": "RUS",
        "driver_name": "George Russell",
        "driver_dob": "1998-02-15",
        "driver_country": "British",
        "constructor": "Mercedes",
        "constructor_country": "German",
        "position": 1,
        "points": 51.0,
        "wins": 1,
        "source": "jolpica",
        "ingested_at": "2026-03-18T21:45:04.180898+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestTypeCasting:

    def test_driver_dob_cast_to_date(self):
        df = clean_driver_standings(make_df(make_row()))
        assert isinstance(df["driver_dob"].iloc[0], datetime.date)

    def test_ingested_at_cast_to_datetime(self):
        df = clean_driver_standings(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])

    def test_ingested_at_is_utc_aware(self):
        df = clean_driver_standings(make_df(make_row()))
        assert str(df["ingested_at"].dt.tz) == "UTC"

    def test_points_stays_float(self):
        df = clean_driver_standings(make_df(make_row(points=51.0)))
        assert df["points"].dtype == float

    def test_fractional_points_preserved(self):
        df = clean_driver_standings(make_df(make_row(points=0.5)))
        assert df["points"].iloc[0] == 0.5

    def test_wins_stays_int(self):
        df = clean_driver_standings(make_df(make_row(wins=1)))
        assert pd.api.types.is_integer_dtype(df["wins"])


class TestIdNormalisation:

    def test_driver_id_lowercased(self):
        df = clean_driver_standings(make_df(make_row(driver_id="Russell")))
        assert df["driver_id"].iloc[0] == "russell"

    def test_driver_id_spaces_replaced_with_underscore(self):
        df = clean_driver_standings(make_df(make_row(driver_id="de vries")))
        assert df["driver_id"].iloc[0] == "de_vries"

    def test_driver_id_stripped_of_whitespace(self):
        df = clean_driver_standings(make_df(make_row(driver_id="  russell  ")))
        assert df["driver_id"].iloc[0] == "russell"

    def test_constructor_lowercased(self):
        df = clean_driver_standings(make_df(make_row(constructor="Mercedes")))
        assert df["constructor"].iloc[0] == "mercedes"

    def test_constructor_spaces_replaced_with_underscore(self):
        df = clean_driver_standings(make_df(make_row(constructor="Red Bull")))
        assert df["constructor"].iloc[0] == "red_bull"


class TestNullHandling:

    def test_driver_country_null_filled_with_unknown(self):
        df = clean_driver_standings(make_df(make_row(driver_country=None)))
        assert df["driver_country"].iloc[0] == "Unknown"

    def test_driver_country_preserved_when_not_null(self):
        df = clean_driver_standings(make_df(make_row(driver_country="British")))
        assert df["driver_country"].iloc[0] == "British"

    def test_constructor_country_null_filled_with_unknown(self):
        df = clean_driver_standings(make_df(make_row(constructor_country=None)))
        assert df["constructor_country"].iloc[0] == "Unknown"

    def test_driver_code_null_filled_with_unk(self):
        df = clean_driver_standings(make_df(make_row(driver_code=None)))
        assert df["driver_code"].iloc[0] == "UNK"

    def test_driver_name_null_filled_with_unknown_driver(self):
        df = clean_driver_standings(make_df(make_row(driver_name=None)))
        assert df["driver_name"].iloc[0] == "Unknown Driver"


class TestDeduplication:

    def test_exact_duplicate_rows_removed(self):
        row = make_row()
        df = clean_driver_standings(make_df(row, row))
        assert len(df) == 1

    def test_last_duplicate_kept(self):
        row1 = make_row(points=44.0)
        row2 = make_row(points=51.0)
        df = clean_driver_standings(make_df(row1, row2))
        assert df["points"].iloc[0] == 51.0

    def test_different_drivers_same_round_not_deduped(self):
        row1 = make_row(driver_id="russell", position=1)
        row2 = make_row(driver_id="norris", position=2)
        df = clean_driver_standings(make_df(row1, row2))
        assert len(df) == 2

    def test_same_driver_different_rounds_not_deduped(self):
        row1 = make_row(round=1)
        row2 = make_row(round=2)
        df = clean_driver_standings(make_df(row1, row2))
        assert len(df) == 2

    def test_same_driver_different_seasons_not_deduped(self):
        row1 = make_row(season=2025)
        row2 = make_row(season=2026)
        df = clean_driver_standings(make_df(row1, row2))
        assert len(df) == 2


class TestOutputShape:

    def test_no_columns_dropped(self):
        input_df = make_df(make_row())
        output_df = clean_driver_standings(input_df)
        assert set(input_df.columns) == set(output_df.columns)

    def test_no_extra_columns_added(self):
        input_df = make_df(make_row())
        output_df = clean_driver_standings(input_df)
        assert set(output_df.columns) == set(input_df.columns)