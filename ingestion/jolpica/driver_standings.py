import logging
import pandas as pd
from jolpica.helper import pagination_helper, logging_setup 

# logging_setup()
logger = logging.getLogger(__name__)

def get_driver_standings(year: int) -> pd.DataFrame:
    logger.info(f"Getting driver standing data for {year}")

    data = []
    pages = pagination_helper(f"{year}/driverStandings")
    for page in pages:
        drivers = page["StandingsTable"]["StandingsLists"]
        for driver in drivers:
            season = driver["season"]
            round_no = driver["round"]
 
            for standing in driver["DriverStandings"]:
                driver = standing["Driver"]
                constructor = standing["Constructors"][0]
 
                data.append({
                    "season": int(season),
                    "round": int(round_no),
                    "driver_id": driver["driverId"],
                    "driver_code": driver.get("code", None),
                    "driver_name": f"{driver['givenName']} {driver['familyName']}",
                    "driver_dob": driver["dateOfBirth"],
                    "driver_country": driver["nationality"],
                    "constructor": constructor["name"],
                    "constructor_country": constructor["nationality"],
                    "position": int(standing["position"]) if standing["position"].isdigit() else None,
                    "points": float(standing["points"]),
                    "wins": int(standing["wins"])
                })
 
    df = pd.DataFrame(data)
 
    logger.info(
        f"Driver standings for {year}: {len(df)} rows across "
        f"{df['round'].nunique()} rounds"
    )
    return df