"""Watchlist API. Add by show_id (preferred) or title; remove supports show_id (preferred) or title (legacy)."""

import hashlib
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.models import WatchlistItem, User, Show
from app.schemas import WatchlistAddRequest, WatchlistRemoveRequest
from app.dependencies import get_current_user
from app.exceptions import AppException, SHOW_NOT_FOUND, INVALID_REQUEST

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _serialize_item(item: WatchlistItem) -> dict:
    """Build watchlist entry: prefer show relation for title/poster_url, else denormalized title (legacy)."""
    title = item.title
    poster_url = None
    show_id = item.show_id
    if item.show is not None:
        title = title or item.show.title
        poster_url = item.show.poster_url
    return {
        "show_id": show_id,
        "title": title or "Unknown",
        "poster_url": poster_url,
    }


def _serialize_watchlist(items: list[WatchlistItem]) -> list[dict]:
    return [_serialize_item(i) for i in items]


def _synthetic_tmdb_id_for_title(title: str) -> int:
    """Deterministic negative integer for fallback shows (TMDB uses positive IDs)."""
    h = hashlib.sha256(title.strip().encode("utf-8")).hexdigest()[:8]
    return -(int(h, 16) % (2**31 - 1) + 1)


def _get_or_create_show_by_title(
    db: Session,
    title: str,
    poster_url: str | None = None,
) -> Show:
    """Create a minimal Show row when saving from fallback/static data (no row in shows yet)."""
    title_clean = title.strip()
    show = db.query(Show).filter(Show.title == title_clean).first()
    if show is not None:
        return show
    synthetic_tmdb_id = _synthetic_tmdb_id_for_title(title_clean)
    show = Show(
        tmdb_id=synthetic_tmdb_id,
        title=title_clean,
        overview=None,
        poster_url=poster_url or None,
        genres=None,
        popularity=None,
        vote_average=None,
        vote_count=None,
        first_air_date=None,
        content_rating=None,
        average_episode_length=None,
        number_of_seasons=None,
        original_language=None,
        embedding=None,
    )
    db.add(show)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        show = db.query(Show).filter(Show.title == title_clean).first()
        if show is None:
            raise
    return show


@router.get("", response_model=dict)
def fetch_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(WatchlistItem)
        .options(joinedload(WatchlistItem.show))
        .filter(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    return {"watchlist": _serialize_watchlist(items)}


@router.post("/add", response_model=dict)
def add_to_watchlist(
    payload: WatchlistAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request_payload = {"show_id": payload.show_id, "title": getattr(payload, "title", None)}
    logger.info(
        "watchlist/add: request payload=%s authenticated user_id=%s",
        request_payload,
        current_user.id,
    )

    try:
        show = None
        if payload.show_id is not None:
            show = db.query(Show).filter(Show.id == payload.show_id).first()
        elif payload.title is not None and str(payload.title).strip():
            show = db.query(Show).filter(Show.title == str(payload.title).strip()).first()

        if show is None:
            if payload.title is not None and str(payload.title).strip():
                show = _get_or_create_show_by_title(
                    db,
                    str(payload.title).strip(),
                    poster_url=getattr(payload, "poster_url", None) or None,
                )
                logger.info("watchlist/add: created fallback show title=%r id=%s", show.title, show.id)
            else:
                logger.warning("watchlist/add: show not found for payload=%s", request_payload)
                raise AppException(
                    status_code=404,
                    error_code=SHOW_NOT_FOUND,
                    message="Show not found. The show is not in the database. Seed the shows table or add by title.",
                    details={"show_id": payload.show_id, "title": getattr(payload, "title", None)},
                )

        existing = (
            db.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == current_user.id,
                WatchlistItem.show_id == show.id,
            )
            .first()
        )
        if not existing:
            item = WatchlistItem(
                show_id=show.id,
                title=show.title,
                user_id=current_user.id,
            )
            db.add(item)
            db.commit()

        items = (
            db.query(WatchlistItem)
            .options(joinedload(WatchlistItem.show))
            .filter(WatchlistItem.user_id == current_user.id)
            .order_by(WatchlistItem.created_at.desc())
            .all()
        )
        return {"watchlist": _serialize_watchlist(items)}
    except AppException:
        raise
    except IntegrityError:
        db.rollback()
        items = (
            db.query(WatchlistItem)
            .options(joinedload(WatchlistItem.show))
            .filter(WatchlistItem.user_id == current_user.id)
            .order_by(WatchlistItem.created_at.desc())
            .all()
        )
        return {"watchlist": _serialize_watchlist(items)}
    except Exception as e:
        logger.exception("watchlist/add: unexpected error payload=%s user_id=%s", request_payload, current_user.id)
        raise


@router.post("/remove", response_model=dict)
def remove_from_watchlist(
    payload: WatchlistRemoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.show_id is not None:
        item = (
            db.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == current_user.id,
                WatchlistItem.show_id == payload.show_id,
            )
            .first()
        )
    else:
        # Legacy: remove by title (for pre-migration items with show_id NULL)
        title = (payload.title or "").strip()
        if not title:
            raise AppException(
                status_code=400,
                error_code=INVALID_REQUEST,
                message="Either show_id or title must be provided",
                details={},
            )
        item = (
            db.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == current_user.id,
                WatchlistItem.title == title,
            )
            .first()
        )

    if item:
        db.delete(item)
        db.commit()

    items = (
        db.query(WatchlistItem)
        .options(joinedload(WatchlistItem.show))
        .filter(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    return {"watchlist": _serialize_watchlist(items)}
