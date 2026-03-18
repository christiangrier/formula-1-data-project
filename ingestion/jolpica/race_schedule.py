import logging
import pandas as pd
from jolpica.helper import pagination_helper, logging_setup 

# logging_setup()
logger = logging.getLogger(__name__)

def _get_session(race: dict, key: str) -> tuple:
    session = race.get(key)
    if session is None:
        return None, None
    return session.get("date"), session.get("time")

def get_season_race_data(year: int) -> pd.DataFrame:
    logger.info(f"Getting race season data for {year}")

    data = []
    pages = pagination_helper(f"{year}/races")
    for page in pages:
        races = page["RaceTable"]["Races"]
        for race in races:
            season = race["season"]
            round_no = race["round"]
            race_name = race["raceName"]
            circuit = race["Circuit"]["circuitName"]
            race_date = race["date"]
            race_start_time = race["time"]

            fp2_date, fp2_time = _get_session(race, "SecondPractice")
            fp3_date, fp3_time = _get_session(race, "ThirdPractice")
            sprint_qualy_date, sprint_qualy_time = _get_session(race, "SprintQualifying")
            sprint_date, sprint_time = _get_session(race, "Sprint")
 
            # for result in race["PitStops"]:
            #     driver_stops = result
 
            data.append({
                "season": int(season),
                "round": int(round_no),
                "race_name": race_name,
                "circuit": circuit,
                "race_date": race_date,
                "race_start_time": race_start_time,
                "fp1_date": race.get("FirstPractice", {}).get("date"),
                "fp1_time": race.get("FirstPractice", {}).get("time"),
                "fp2_date": fp2_date,
                "fp2_time": fp2_time,
                "fp3_date": fp3_date,
                "fp3_time": fp3_time,
                "sprint_qualy_date": sprint_qualy_date,
                "sprint_qualy_time": sprint_qualy_time,
                "qualy_date": race["Qualifying"]["date"],
                "qualy_time": race["Qualifying"]["time"]
            })
 
    df = pd.DataFrame(data)
 
    logger.info(
        f"Race sessions for year: {year} {len(df)} rows across "
        f"{df['round'].nunique()} rounds"
    )
    return df