import argparse
import sys
from pathlib import Path
from typing import Any

# Allow running this script directly: `python scripts/generate_embeddings.py`
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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


def build_embedding_text(show: Show) -> str:
    title = (show.title or "").strip()
    overview = (show.overview or "").strip()
    genres_str = _genres_to_string(show.genres)

    lines = [f"Title: {title or 'Unknown'}"]
    if genres_str:
        lines.append(f"Genres: {genres_str}")
    if overview:
        lines.append(f"Overview: {overview}")

    return "\n".join(lines)


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

