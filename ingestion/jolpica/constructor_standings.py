import logging
import pandas as pd
from ingestion.jolpica.helper import pagination_helper, logging_setup 

# logging_setup()
logger = logging.getLogger(__name__)

def get_constructor_standings(year: int) -> pd.DataFrame:
    logger.info(f"Getting constructor standing data for {year}")

    data = []
    pages = pagination_helper(f"{year}/constructorStandings")
    for page in pages:
        constructors = page["StandingsTable"]["StandingsLists"]
        for constructor in constructors:
            season = constructor["season"]
            round_no = constructor["round"]
 
            for standing in constructor["ConstructorStandings"]:
                constructor = standing["Constructor"]
 
                data.append({
                    "season": int(season),
                    "round": int(round_no),
                    "constructor_id": constructor["constructorId"],
                    "constructor": constructor["name"],
                    "constructor_country": constructor["nationality"],
                    "position": int(standing["position"]) if standing["position"].isdigit() else None,
                    "points": float(standing["points"]),
                    "wins": int(standing["wins"])
                })
 
    df = pd.DataFrame(data)
 
    logger.info(
        f"Constructor standings for {year}: {len(df)} rows across "
        f"{df['round'].nunique()} rounds"
    )
    return df