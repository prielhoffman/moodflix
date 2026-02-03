from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import WatchlistItem, User
from app.schemas import WatchlistTitle
from app.dependencies import get_current_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _serialize_watchlist(items):
    return [{"title": i.title} for i in items]


@router.get("")
def fetch_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    return {"watchlist": _serialize_watchlist(items)}


@router.post("/add")
def add_to_watchlist(
    payload: WatchlistTitle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    existing = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.title == title,
        )
        .first()
    )
    if not existing:
        item = WatchlistItem(title=title, user_id=current_user.id)
        db.add(item)
        db.commit()

    # Return updated list (matches frontend expectations)
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    return {"watchlist": _serialize_watchlist(items)}


@router.post("/remove")
def remove_from_watchlist(
    payload: WatchlistTitle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

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

    # Return updated list
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    return {"watchlist": _serialize_watchlist(items)}
