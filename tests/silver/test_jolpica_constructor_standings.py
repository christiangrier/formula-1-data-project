import pandas as pd
import pytest
from ingestion.silver.jolpica_constructor_standings import clean_constructor_standings

def make_row(**overrides) -> dict:
    base = {
        "season": 2026,
        "round": 2,
        "constructor_id": "mercedes",
        "constructor": "Mercedes",
        "constructor_country": "German",
        "position": 1,
        "points": 98.0,
        "wins": 2,
        "source": "jolpica",
        "ingested_at": "2026-03-18T21:45:45.373097+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestTypeCasting:

    def test_ingested_at_cast_to_datetime(self):
        df = clean_constructor_standings(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])

    def test_ingested_at_is_utc_aware(self):
        df = clean_constructor_standings(make_df(make_row()))
        assert str(df["ingested_at"].dt.tz) == "UTC"

    def test_points_stays_float(self):
        df = clean_constructor_standings(make_df(make_row(points=98.0)))
        assert df["points"].dtype == float

    def test_fractional_points_preserved(self):
        df = clean_constructor_standings(make_df(make_row(points=0.5)))
        assert df["points"].iloc[0] == 0.5

    def test_wins_stays_int(self):
        df = clean_constructor_standings(make_df(make_row(wins=2)))
        assert pd.api.types.is_integer_dtype(df["wins"])


class TestIdNormalisation:

    def test_constructor_id_lowercased(self):
        df = clean_constructor_standings(make_df(make_row(constructor_id="Mercedes")))
        assert df["constructor_id"].iloc[0] == "mercedes"

    def test_constructor_id_spaces_replaced_with_underscore(self):
        df = clean_constructor_standings(make_df(make_row(constructor_id="Red Bull")))
        assert df["constructor_id"].iloc[0] == "red_bull"

    def test_constructor_id_stripped_of_whitespace(self):
        df = clean_constructor_standings(make_df(make_row(constructor_id="  mercedes  ")))
        assert df["constructor_id"].iloc[0] == "mercedes"

    def test_constructor_display_name_not_normalised(self):
        """constructor (display name) must stay as-is — not lowercased."""
        df = clean_constructor_standings(make_df(make_row(constructor="Red Bull Racing")))
        assert df["constructor"].iloc[0] == "Red Bull Racing"

    def test_constructor_display_name_mixed_case_preserved(self):
        df = clean_constructor_standings(make_df(make_row(constructor="Mercedes")))
        assert df["constructor"].iloc[0] == "Mercedes"


class TestNullHandling:

    def test_constructor_country_null_filled_with_unknown(self):
        df = clean_constructor_standings(make_df(make_row(constructor_country=None)))
        assert df["constructor_country"].iloc[0] == "Unknown"

    def test_constructor_country_preserved_when_not_null(self):
        df = clean_constructor_standings(make_df(make_row(constructor_country="German")))
        assert df["constructor_country"].iloc[0] == "German"

    def test_constructor_null_filled_with_unknown_constructor(self):
        df = clean_constructor_standings(make_df(make_row(constructor=None)))
        assert df["constructor"].iloc[0] == "Unknown Constructor"


class TestDeduplication:

    def test_exact_duplicate_rows_removed(self):
        row = make_row()
        df = clean_constructor_standings(make_df(row, row))
        assert len(df) == 1

    def test_last_duplicate_kept(self):
        row1 = make_row(points=88.0)
        row2 = make_row(points=98.0)
        df = clean_constructor_standings(make_df(row1, row2))
        assert df["points"].iloc[0] == 98.0

    def test_different_constructors_same_round_not_deduped(self):
        row1 = make_row(constructor_id="mercedes", position=1)
        row2 = make_row(constructor_id="mclaren", position=2)
        df = clean_constructor_standings(make_df(row1, row2))
        assert len(df) == 2

    def test_same_constructor_different_rounds_not_deduped(self):
        row1 = make_row(round=1)
        row2 = make_row(round=2)
        df = clean_constructor_standings(make_df(row1, row2))
        assert len(df) == 2

    def test_same_constructor_different_seasons_not_deduped(self):
        row1 = make_row(season=2025)
        row2 = make_row(season=2026)
        df = clean_constructor_standings(make_df(row1, row2))
        assert len(df) == 2


class TestOutputShape:

    def test_no_columns_dropped(self):
        input_df = make_df(make_row())
        output_df = clean_constructor_standings(input_df)
        assert set(input_df.columns) == set(output_df.columns)

    def test_no_extra_columns_added(self):
        input_df = make_df(make_row())
        output_df = clean_constructor_standings(input_df)
        assert set(output_df.columns) == set(input_df.columns)