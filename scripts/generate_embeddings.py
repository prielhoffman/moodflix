import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

# Allow running this script directly: `python scripts/generate_embeddings.py`
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import SessionLocal
from app.models import Show


# OpenAI embedding model with 1536 dimensions (matches Vector(1536))
EMBEDDING_MODEL = "text-embedding-3-small"
EXPECTED_DIM = 1536


_TMDB_TV_GENRE_ID_TO_NAME: dict[int, str] = {
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


def _genres_to_string(genres: Any) -> str:
    if not genres:
        return ""
    if not isinstance(genres, list):
        return str(genres)

    out: list[str] = []
    for g in genres:
        if isinstance(g, int):
            name = _TMDB_TV_GENRE_ID_TO_NAME.get(g)
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


def create_embeddings_with_retries(
    client: OpenAI,
    *,
    inputs: list[str],
    max_retries: int = 6,
    base_delay_s: float = 1.0,
) -> list[list[float]]:
    """
    Create embeddings with basic backoff on rate limits / transient failures.
    Keeps dependencies minimal (no tenacity).
    """
    last_err: Exception | None = None

    for attempt in range(max_retries):
        try:
            resp = client.embeddings.create(model=EMBEDDING_MODEL, input=inputs)
            vectors = [item.embedding for item in resp.data]
            return vectors
        except Exception as e:
            last_err = e

            # Best-effort parsing of status codes across OpenAI SDK versions
            status = (
                getattr(e, "status_code", None)
                or getattr(e, "status", None)
                or getattr(getattr(e, "response", None), "status_code", None)
            )

            # Fail fast on obvious non-retryable HTTP errors
            if status in (400, 401, 403, 404, 409, 422):
                hint = ""
                if status in (401, 403):
                    hint = " Check OPENAI_API_KEY / permissions."
                elif status == 400:
                    hint = " Check model name and request payload."
                raise RuntimeError(f"OpenAI request failed (status={status}).{hint}") from e

            # Retry only on transient cases: rate limits, 5xx, and network/timeouts.
            cls_name = e.__class__.__name__.lower()
            msg = str(e).lower()
            network_like = any(
                k in cls_name
                for k in (
                    "timeout",
                    "connect",
                    "connection",
                    "api_connection",
                    "httpx",
                    "httpcore",
                )
            ) or any(
                k in msg
                for k in (
                    "timeout",
                    "timed out",
                    "connection",
                    "network",
                    "temporarily unavailable",
                    "server disconnected",
                )
            )

            retryable = status in (429, 500, 502, 503, 504) or (status is None and network_like)
            if not retryable:
                raise RuntimeError(f"OpenAI request failed (status={status}).") from e

            if attempt == max_retries - 1:
                break

            sleep_s = base_delay_s * (2 ** attempt)
            print(f"⚠️ OpenAI request failed (status={status}). retrying in {sleep_s:.1f}s... ({attempt+1}/{max_retries})")
            time.sleep(sleep_s)

    raise RuntimeError(f"OpenAI embeddings request failed after retries: {last_err}") from last_err


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate and store embeddings for shows in Postgres.")
    p.add_argument("--limit", type=int, default=None, help="Optional limit on number of shows to process")
    p.add_argument("--force", action="store_true", help="Regenerate embeddings even if already present")
    p.add_argument("--batch-size", type=int, default=100, help="Batch size for OpenAI embedding requests")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is missing. Set it in your environment to generate embeddings.")
        return 1

    batch_size = max(1, int(args.batch_size))
    limit = int(args.limit) if args.limit is not None else None
    force = bool(args.force)

    client = OpenAI(api_key=api_key)

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
            vectors = create_embeddings_with_retries(client, inputs=texts)

            if len(vectors) != len(rows):
                raise RuntimeError("OpenAI returned a different number of embeddings than inputs")

            for show, vec in zip(rows, vectors):
                if len(vec) != EXPECTED_DIM:
                    raise RuntimeError(f"Embedding dim mismatch for show_id={show.id}: got {len(vec)} expected {EXPECTED_DIM}")
                show.embedding = vec

            db.commit()
            processed += len(rows)
            print(f"✅ Embedded {processed}/{total}")

            # Small pacing delay to be polite with rate limits
            time.sleep(0.2)

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

