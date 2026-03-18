import logging
import pandas as pd
from jolpica.helper import pagination_helper, logging_setup 

# logging_setup()
logger = logging.getLogger(__name__)

def get_pit_stop_time_data(year: int, round: int) -> pd.DataFrame:
    logger.info(f"Getting pit stop timing data for {year} round: {round}")

    data = []
    pages = pagination_helper(f"{year}/{round}/pitstops")
    for page in pages:
        pitstops = page["RaceTable"]["Races"]
        for stops in pitstops:
            season = stops["season"]
            round_no = stops["round"]
            race_name = stops["raceName"]
            circuit = stops["Circuit"]["circuitName"]
            date = stops["date"]
 
            for result in stops["PitStops"]:
                driver_stops = result
 
                data.append({
                    "season": int(season),
                    "round": int(round_no),
                    "race_name": race_name,
                    "circuit": circuit,
                    "date": date,
                    "driver_id": driver_stops["driverId"],
                    "lap_pitted": driver_stops["lap"],
                    "stop_num": driver_stops["stop"],
                    "pit_in_time": driver_stops["time"],
                    "pit_stop_duration": driver_stops["duration"],
                })
 
    df = pd.DataFrame(data)
 
    logger.info(
        f"Pit stops for year: {year} session: {round} = {len(df)} rows across "
        f"{df['round'].nunique()} rounds"
    )
    return df