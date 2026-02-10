from dotenv import load_dotenv
load_dotenv()

import os
import logging
from threading import RLock
import requests
from cachetools import TTLCache


# Read API key from environment variables.
# IMPORTANT: TMDB is an optional enrichment layer — the app should run without it.
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Base URLs for TMDB API and images
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

logger = logging.getLogger(__name__)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


TMDB_CACHE_TTL_SECONDS = _int_env("TMDB_CACHE_TTL_SECONDS", 6 * 60 * 60)
TMDB_CACHE_MAX_SIZE = _int_env("TMDB_CACHE_MAX_SIZE", 1024)
TMDB_NEGATIVE_CACHE_TTL_SECONDS = _int_env("TMDB_NEGATIVE_CACHE_TTL_SECONDS", 2 * 60)

_CACHE_LOCK = RLock()
_POSITIVE_CACHE: TTLCache[str, dict] = TTLCache(
    maxsize=TMDB_CACHE_MAX_SIZE,
    ttl=TMDB_CACHE_TTL_SECONDS,
)
_NEGATIVE_CACHE: TTLCache[str, bool] = TTLCache(
    maxsize=TMDB_CACHE_MAX_SIZE,
    ttl=TMDB_NEGATIVE_CACHE_TTL_SECONDS,
)
_CACHE_HITS = 0
_CACHE_MISSES = 0


def _normalize_title(title: str) -> str:
    return " ".join((title or "").strip().lower().split())


def _cache_key_for_query(title: str, year: int | str | None = None) -> str:
    normalized_title = _normalize_title(title)
    normalized_year = str(year).strip() if year is not None else ""
    return f"query:{normalized_title}|year:{normalized_year}"


def _cache_key_for_tmdb_id(tmdb_id: int | None) -> str | None:
    if tmdb_id is None:
        return None
    try:
        return f"id:{int(tmdb_id)}"
    except (TypeError, ValueError):
        return None


def _search_tv_show_uncached(title: str, *, year: int | str | None = None) -> dict | None:
    url = f"{BASE_URL}/search/tv"

    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "en-US",
        "page": 1,
    }
    if year is not None:
        params["first_air_date_year"] = str(year).strip()

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


def _read_from_cache(keys: list[str]) -> tuple[dict | None, bool]:
    global _CACHE_HITS

    with _CACHE_LOCK:
        for key in keys:
            cached = _POSITIVE_CACHE.get(key)
            if cached is not None:
                _CACHE_HITS += 1
                return cached, True

        for key in keys:
            if _NEGATIVE_CACHE.get(key):
                _CACHE_HITS += 1
                return None, True

    return None, False


def _write_to_cache(keys: list[str], value: dict | None) -> None:
    with _CACHE_LOCK:
        if value is None:
            for key in keys:
                _NEGATIVE_CACHE[key] = True
            return
        for key in keys:
            _POSITIVE_CACHE[key] = value


def clear_tmdb_cache() -> None:
    global _CACHE_HITS, _CACHE_MISSES
    with _CACHE_LOCK:
        _POSITIVE_CACHE.clear()
        _NEGATIVE_CACHE.clear()
        _CACHE_HITS = 0
        _CACHE_MISSES = 0


def get_cache_counters() -> dict[str, int]:
    with _CACHE_LOCK:
        return {
            "hits": _CACHE_HITS,
            "misses": _CACHE_MISSES,
        }


def get_tv_details_cached(
    title: str,
    *,
    tmdb_id: int | None = None,
    year: int | str | None = None,
) -> dict | None:
    # Best-effort enrichment:
    # - If TMDB is not configured, return None (do not crash the app).
    # - If TMDB is down / rate-limited, return None.
    if not TMDB_API_KEY:
        return None

    query_key = _cache_key_for_query(title, year=year)
    id_key = _cache_key_for_tmdb_id(tmdb_id)
    keys = [query_key] + ([id_key] if id_key else [])

    cached, was_hit = _read_from_cache(keys)
    if was_hit:
        logger.debug("TMDB cache hit for key=%s", keys[0])
        return cached

    global _CACHE_MISSES
    with _CACHE_LOCK:
        _CACHE_MISSES += 1

    logger.debug("TMDB cache miss for key=%s", keys[0])
    try:
        fetched = _search_tv_show_uncached(title, year=year)
    except requests.RequestException:
        fetched = None

    _write_to_cache(keys, fetched)

    if fetched:
        fetched_id_key = _cache_key_for_tmdb_id(fetched.get("tmdb_id"))
        if fetched_id_key and fetched_id_key not in keys:
            _write_to_cache([fetched_id_key], fetched)

    return fetched


def search_tv_show(title: str) -> dict | None:
    return get_tv_details_cached(title)
