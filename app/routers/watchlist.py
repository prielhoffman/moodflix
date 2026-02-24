from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import WatchlistItem, User, Show
from app.schemas import WatchlistAddRequest, WatchlistRemoveRequest
from app.dependencies import get_current_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _serialize_item(item: WatchlistItem) -> dict:
    """Build watchlist entry: prefer show relation for title/poster_url, else denormalized title."""
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
    show = db.query(Show).filter(Show.id == payload.show_id).first()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")

    existing = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.show_id == payload.show_id,
        )
        .first()
    )
    if not existing:
        item = WatchlistItem(
            show_id=payload.show_id,
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
        title = (payload.title or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Either show_id or title must be provided")
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
