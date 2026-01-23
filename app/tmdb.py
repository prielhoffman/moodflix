from dotenv import load_dotenv
load_dotenv()

import os
import requests

# Read API key from environment variables
# This avoids hardcoding secrets in the codebase
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Fail fast if the API key is missing
# Prevents silent failures later during API calls
if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is not set in environment variables")


# Base URLs for TMDB API and images
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def search_tv_show(title: str) -> dict | None:
    try:
        url = f"{BASE_URL}/search/tv"

        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "language": "en-US",
            "page": 1,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            return None

        show = results[0]

        return {
            "tmdb_id": show.get("id"),
            "poster_url": (
                f"{IMAGE_BASE_URL}{show['poster_path']}"
                if show.get("poster_path")
                else None
            ),
            "overview": show.get("overview"),
            "rating": show.get("vote_average"),
            "first_air_date": show.get("first_air_date"),
        }

    except requests.RequestException:
        return None
