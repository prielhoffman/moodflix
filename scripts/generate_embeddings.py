"""
Generate and store embeddings for shows in the same Postgres DB that FastAPI uses.
Run from project root: python -m scripts.generate_embeddings
Uses the same .env so the script connects to the same database.
Commits update shows.embedding for many rows.
"""
import argparse
from typing import Any

from app.db import SessionLocal
from app.embeddings import EMBED_DIM, embed_texts
from app.models import Show
from app.shared import TMDB_TV_GENRE_ID_TO_NAME


EXPECTED_DIM = EMBED_DIM


def _genres_to_string(genres: Any) -> str:
    if not genres:
        return ""
    if not isinstance(genres, list):
        return str(genres)

    out: list[str] = []
    for g in genres:
        if isinstance(g, int):
            name = TMDB_TV_GENRE_ID_TO_NAME.get(g)
            out.append(name or str(g))
        elif isinstance(g, str):
            if g.strip():
                out.append(g.strip())
        else:
            out.append(str(g))
    return ", ".join(out)


def _genres_to_list(genres: Any) -> list[str]:
    """Return lowercase genre names for descriptor inference."""
    if not genres or not isinstance(genres, list):
        return []
    out: list[str] = []
    for g in genres:
        if isinstance(g, int):
            name = TMDB_TV_GENRE_ID_TO_NAME.get(g)
            if name:
                out.append(name)
        elif isinstance(g, str) and g.strip():
            out.append(g.strip().lower())
    return out


def _infer_embedding_descriptors(overview: str | None, genres: list[str]) -> list[str]:
    """
    Infer setting/theme descriptors from overview + genres for embedding enrichment.
    Rule-based, cap at ~5-6 descriptors. Uses simple keyword checks.
    """
    if not overview:
        return []
    ov = overview.lower()
    genre_set = set(genres)
    descriptors: list[str] = []
    has_comedy = "comedy" in genre_set
    has_drama = "drama" in genre_set

    # Office / corporate workplace
    if any(k in ov for k in ("office", "company", "boss", "employee", "coworker", "coworkers", "job", "workplace")):
        if has_comedy:
            descriptors.extend(["workplace comedy", "office comedy", "coworkers"])
        else:
            descriptors.append("workplace")

    # Police / precinct
    if any(k in ov for k in ("police", "cop", "cops", "detective", "detectives", "precinct", "squad")):
        if has_comedy:
            descriptors.extend(["police workplace comedy", "police precinct", "coworkers"])
        else:
            descriptors.extend(["police precinct", "detectives"])

    # Hospital / medical
    if any(k in ov for k in ("hospital", "doctor", "doctors", "nurse", "nurses", "medical", "clinic")):
        descriptors.extend(["hospital workplace", "medical staff"])

    # School
    if any(k in ov for k in ("school", "teacher", "teachers", "principal", "students", "classroom")):
        descriptors.extend(["school staff", "teachers", "workplace"])

    # Newsroom / media
    if any(k in ov for k in ("newsroom", "reporter", "reporters", "journalist", "journalists", "anchor", "tv station")):
        descriptors.extend(["newsroom", "media workplace"])

    # Ensemble / team
    if any(k in ov for k in ("team", "staff", "crew", "department", "squad", "group of")):
        descriptors.append("ensemble cast")
        if has_comedy:
            descriptors.append("ensemble comedy")

    # Dedupe and cap
    seen: set[str] = set()
    out: list[str] = []
    for d in descriptors:
        if d not in seen and len(out) < 6:
            seen.add(d)
            out.append(d)
    return out


def build_embedding_text(show: Show) -> str:
    """Build a single text blob for embedding: title, genres, overview, themes."""
    title = (show.title or "").strip() or "Unknown"
    genres_str = _genres_to_string(show.genres)
    overview = (show.overview or "").strip()
    genre_names = _genres_to_list(show.genres)
    descriptors = _infer_embedding_descriptors(overview, genre_names)

    parts = [
        f"Title: {title}.",
        f"Genres: {genres_str}.",
        f"Overview: {overview}.",
    ]
    if descriptors:
        parts.append(f"Themes: {', '.join(descriptors)}.")
    return " ".join(parts)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate and store embeddings for shows in Postgres.")
    p.add_argument("--limit", type=int, default=None, help="Optional limit on number of shows to process")
    p.add_argument("--force", action="store_true", help="Regenerate embeddings even if already present")
    p.add_argument("--batch-size", type=int, default=100, help="Batch size for embedding generation")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    batch_size = max(1, int(args.batch_size))
    limit = int(args.limit) if args.limit is not None else None
    force = bool(args.force)

    db = SessionLocal()
    try:
        base_query = db.query(Show).order_by(Show.id.asc())
        if not force:
            base_query = base_query.filter(Show.embedding.is_(None))

        total = base_query.count()
        if limit is not None:
            total = min(total, limit)

        print(f"Found {total} shows to embed (force={force}, batch_size={batch_size}).")
        if total == 0:
            return 0

        processed = 0
        offset = 0

        while processed < total:
            remaining = total - processed
            this_batch = min(batch_size, remaining)

            if force:
                rows = base_query.offset(offset).limit(this_batch).all()
                offset += this_batch
            else:
                # No offset in non-force mode because the filtered set shrinks as we write embeddings.
                rows = base_query.limit(this_batch).all()

            if not rows:
                break

            texts = [build_embedding_text(s) for s in rows]
            vectors = embed_texts(texts)

            if len(vectors) != len(rows):
                raise RuntimeError("Embedding generator returned a different number of vectors than inputs")

            for show, vec in zip(rows, vectors):
                if len(vec) != EXPECTED_DIM:
                    raise RuntimeError(f"Embedding dim mismatch for show_id={show.id}: got {len(vec)} expected {EXPECTED_DIM}")
                show.embedding = vec

            db.commit()
            processed += len(rows)
            print(f"✅ Embedded {processed}/{total}")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

