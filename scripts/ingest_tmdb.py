import os
import requests
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Show


TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_PAGES = int(os.getenv("TMDB_PAGES", "2"))
TMDB_BASE = "https://api.themoviedb.org/3"


def parse_date(date_str: str | None):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def fetch_popular_tv(page: int):
    url = f"{TMDB_BASE}/tv/popular"
    params = {"api_key": TMDB_API_KEY, "page": page}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is missing. Put it in your .env file")

    db: Session = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        for page in range(1, TMDB_PAGES + 1):
            data = fetch_popular_tv(page)
            results = data.get("results", [])

            for item in results:
                tmdb_id = item.get("id")
                title = item.get("name")
                if not tmdb_id or not title:
                    continue

                exists = db.query(Show).filter(Show.tmdb_id == tmdb_id).first()
                if exists:
                    skipped += 1
                    continue

                poster_path = item.get("poster_path")
                poster_url = (
                    f"https://image.tmdb.org/t/p/w500{poster_path}"
                    if poster_path
                    else None
                )

                show = Show(
                    tmdb_id=tmdb_id,
                    title=title,
                    overview=item.get("overview"),
                    poster_url=poster_url,
                    genres=item.get("genre_ids"),  # ids for now
                    popularity=item.get("popularity"),
                    vote_average=item.get("vote_average"),
                    vote_count=item.get("vote_count"),
                    first_air_date=parse_date(item.get("first_air_date")),
                )

                db.add(show)
                inserted += 1

            db.commit()

        print(f"✅ Done. inserted={inserted} skipped={skipped}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
