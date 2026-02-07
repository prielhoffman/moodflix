from dotenv import load_dotenv
load_dotenv()

import os
import requests


# Read API key from environment variables.
# IMPORTANT: TMDB is an optional enrichment layer — the app should run without it.
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Base URLs for TMDB API and images
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def search_tv_show(title: str) -> dict | None:
    # Best-effort enrichment:
    # - If TMDB is not configured, return None (do not crash the app).
    # - If TMDB is down / rate-limited, return None.
    if not TMDB_API_KEY:
        return None

    try:
        url = f"{BASE_URL}/search/tv"

        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "language": "en-US",
            "page": 1,
        }

        # Keep timeouts low so recommendations don't hang when TMDB is slow.
        # (connect timeout, read timeout)
        response = requests.get(url, params=params, timeout=(2, 5))

        # Rate limited / blocked: treat as optional enrichment
        if response.status_code == 429:
            return None

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            # Invalid / non-JSON response from TMDB (or intermediary)
            return None

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
