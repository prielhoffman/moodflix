"""
Shared constants and small helper utilities used across backend modules and scripts.
"""

from __future__ import annotations


# TMDB TV genre id -> normalized lowercase genre name.
TMDB_TV_GENRE_ID_TO_NAME: dict[int, str] = {
    10759: "action",
    16: "animation",
    35: "comedy",
    80: "crime",
    99: "documentary",
    18: "drama",
    10751: "family",
    10762: "kids",
    9648: "mystery",
    10763: "news",
    10764: "reality",
    10765: "sci-fi",
    10766: "soap",
    10767: "talk",
    10768: "war",
    37: "western",
}


def shorten_text(text: str | None, *, fallback: str, max_length: int = 220) -> str:
    """
    Return a trimmed, length-limited summary string.

    If text is missing/blank, return the provided fallback message.
    Behavior intentionally matches existing call sites:
    - trim whitespace
    - keep text as-is when <= max_length
    - otherwise truncate to max_length - 3 and append "..."
    """
    if text and text.strip():
        cleaned = text.strip()
        return cleaned if len(cleaned) <= max_length else cleaned[: max_length - 3].rstrip() + "..."
    return fallback
