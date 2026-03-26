import logging
import pandas as pd
from ingestion.bronze.jolpica.helper import pagination_helper, logging_setup 

# logging_setup()
logger = logging.getLogger(__name__)

def get_race_results(year: int) -> pd.DataFrame:
    logger.info(f"Getting race result data for {year}")

    data = []
    pages = pagination_helper(f"{year}/results")
    for page in pages:
        races = page["RaceTable"]["Races"]
        for race in races:
            season = race["season"]
            round_no = race["round"]
            race_name = race["raceName"]
            circuit = race["Circuit"]["circuitName"]
            date = race["date"]
 
            for result in race["Results"]:
                driver = result["Driver"]
                constructor = result["Constructor"]
 
                fastest_lap_rank = (
                    result.get("FastestLap", {}).get("rank", None)
                )
 
                data.append({
                    "season": int(season),
                    "round": int(round_no),
                    "race_name": race_name,
                    "circuit": circuit,
                    "date": date,
                    "driver_id": driver["driverId"],
                    "driver_code": driver.get("code", None),
                    "driver_name": f"{driver['givenName']} {driver['familyName']}",
                    "constructor": constructor["name"],
                    "grid": int(result["grid"]),
                    "position": int(result["position"]) if result["position"].isdigit() else None,
                    "points": float(result["points"]),
                    "status": result["status"],
                    "fastest_lap_rank": int(fastest_lap_rank) if fastest_lap_rank else None,
                })
 
    df = pd.DataFrame(data)
 
    logger.info(
        f"Race results {year}: {len(df)} rows across "
        f"{df['round'].nunique()} rounds"
    )
    return df