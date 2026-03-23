import datetime
import pandas as pd
import pytest
from ingestion.silver.jolpica_pit_stops import parse_duration_to_seconds, clean_pit_stops


def make_row(**overrides) -> dict:
    base = {
        "season": 2026,
        "round": 1,
        "race_name": "Australian Grand Prix",
        "circuit": "Albert Park Grand Prix Circuit",
        "date": "2026-03-08",
        "driver_id": "colapinto",
        "lap_pitted": "9",
        "stop_num": "1",
        "pit_in_time": "15:16:40",
        "pit_stop_duration": "27.733",
        "source": "jolpica",
        "ingested_at": "2026-03-18T21:57:00.363321+00:00",
    }
    base.update(overrides)
    return base

def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


class TestParseDurationToSeconds:
 
    def test_simple_seconds_parsed(self):
        assert parse_duration_to_seconds("27.733") == pytest.approx(27.733)

    def test_minutes_seconds_format_parsed(self):
        assert parse_duration_to_seconds("1:27.733") == pytest.approx(87.733)

    def test_two_minutes_parsed(self):
        assert parse_duration_to_seconds("2:05.000") == pytest.approx(125.0)

    def test_none_returns_none(self):
        assert parse_duration_to_seconds(None) is None

    def test_empty_string_returns_none(self):
        assert parse_duration_to_seconds("") is None

    def test_whitespace_string_returns_none(self):
        assert parse_duration_to_seconds("   ") is None

    def test_unparseable_string_returns_none(self):
        assert parse_duration_to_seconds("DNF") is None

    def test_integer_string_parsed(self):
        assert parse_duration_to_seconds("28") == pytest.approx(28.0)


class TestTypeCasting:

    def test_date_cast_to_date(self):
        df = clean_pit_stops(make_df(make_row()))
        assert isinstance(df["date"].iloc[0], datetime.date)

    def test_ingested_at_cast_to_datetime(self):
        df = clean_pit_stops(make_df(make_row()))
        assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"])

    def test_ingested_at_is_utc_aware(self):
        df = clean_pit_stops(make_df(make_row()))
        assert str(df["ingested_at"].dt.tz) == "UTC"

    def test_lap_pitted_cast_to_int(self):
        df = clean_pit_stops(make_df(make_row(lap_pitted="9")))
        assert df["lap_pitted"].dtype == "Int64"
        assert df["lap_pitted"].iloc[0] == 9

    def test_stop_num_cast_to_int(self):
        df = clean_pit_stops(make_df(make_row(stop_num="1")))
        assert df["stop_num"].dtype == "Int64"
        assert df["stop_num"].iloc[0] == 1

    def test_pit_in_time_cast_to_time(self):
        df = clean_pit_stops(make_df(make_row(pit_in_time="15:16:40")))
        assert isinstance(df["pit_in_time"].iloc[0], datetime.time)

    def test_pit_stop_duration_cast_to_float(self):
        df = clean_pit_stops(make_df(make_row(pit_stop_duration="27.733")))
        assert df["pit_stop_duration"].dtype == float
        assert df["pit_stop_duration"].iloc[0] == pytest.approx(27.733)

    def test_pit_stop_duration_minutes_format_converted(self):
        df = clean_pit_stops(make_df(make_row(pit_stop_duration="1:27.733")))
        assert df["pit_stop_duration"].iloc[0] == pytest.approx(87.733)


class TestIdNormalisation:

    def test_driver_id_lowercased(self):
        df = clean_pit_stops(make_df(make_row(driver_id="Colapinto")))
        assert df["driver_id"].iloc[0] == "colapinto"

    def test_driver_id_spaces_replaced_with_underscore(self):
        df = clean_pit_stops(make_df(make_row(driver_id="de vries")))
        assert df["driver_id"].iloc[0] == "de_vries"

    def test_driver_id_stripped_of_whitespace(self):
        df = clean_pit_stops(make_df(make_row(driver_id="  colapinto  ")))
        assert df["driver_id"].iloc[0] == "colapinto"


class TestRowDropping:

    def test_null_duration_row_dropped(self):
        row_valid = make_row()
        row_null = make_row(pit_stop_duration=None, driver_id="norris", stop_num="1")
        df = clean_pit_stops(make_df(row_valid, row_null))
        assert len(df) == 1
        assert df["driver_id"].iloc[0] == "colapinto"

    def test_unparseable_duration_row_dropped(self):
        row_valid = make_row()
        row_bad = make_row(pit_stop_duration="DNF", driver_id="norris", stop_num="1")
        df = clean_pit_stops(make_df(row_valid, row_bad))
        assert len(df) == 1

    def test_all_valid_rows_kept(self):
        rows = [make_row(driver_id=f"driver_{i}", stop_num="1") for i in range(5)]
        df = clean_pit_stops(make_df(*rows))
        assert len(df) == 5


class TestDeduplication:

    def test_exact_duplicate_rows_removed(self):
        row = make_row()
        df = clean_pit_stops(make_df(row, row))
        assert len(df) == 1

    def test_last_duplicate_kept(self):
        row1 = make_row(pit_stop_duration="27.733")
        row2 = make_row(pit_stop_duration="28.100")
        df = clean_pit_stops(make_df(row1, row2))
        assert df["pit_stop_duration"].iloc[0] == pytest.approx(28.100)

    def test_different_stop_numbers_not_deduped(self):
        row1 = make_row(stop_num="1", lap_pitted="9")
        row2 = make_row(stop_num="2", lap_pitted="30")
        df = clean_pit_stops(make_df(row1, row2))
        assert len(df) == 2

    def test_different_drivers_same_stop_not_deduped(self):
        row1 = make_row(driver_id="colapinto")
        row2 = make_row(driver_id="norris")
        df = clean_pit_stops(make_df(row1, row2))
        assert len(df) == 2

    def test_same_driver_different_rounds_not_deduped(self):
        row1 = make_row(round=1)
        row2 = make_row(round=2)
        df = clean_pit_stops(make_df(row1, row2))
        assert len(df) == 2


class TestOutputShape:

    def test_no_extra_columns_added(self):
        input_df = make_df(make_row())
        output_df = clean_pit_stops(input_df)
        assert set(output_df.columns) == set(input_df.columns)