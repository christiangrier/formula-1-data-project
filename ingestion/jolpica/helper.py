import time
import requests
import logging

BASE_URL="https://api.jolpi.ca/ergast/f1"
SLEEP_TIME = 0.5
MAX_RETRY = 3

logger = logging.getLogger(__name__)

def logging_setup(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def _get_with_retry(url: str, params: dict = None) -> dict:
    for attempt in range(1, MAX_RETRY + 1):
        try:
            time.sleep(SLEEP_TIME)
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()


        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt}/{MAX_RETRY} failed for {url}: {e}")
            if attempt == MAX_RETRY:
                raise

def pagination_helper(endpoint: str, params: dict = None) -> list[dict]:
    if params is None:
        params = {}
    limit = 200
    offset = 0
    all_results = []
    
    while True:
        url = f"{BASE_URL}/{endpoint}.json"
        request_params = {**params, "limit": limit, "offset": offset}
        results = _get_with_retry(url, params=request_params)

        data = results["MRData"]
        total = int(data["total"])
        returned_limit = int(data["limit"])
        returned_offset = int(data["offset"])

        logger.info(f"{endpoint}: offset {returned_offset}/{total}")

        all_results.append(data)

        if returned_offset + returned_limit >= limit:
            break
        offset += limit

        logger.info(f"{endpoint}: complete ({len(all_results)} page(s), {total} total records)")

    return all_results


