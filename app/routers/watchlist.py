from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import WatchlistItem, User
from app.dependencies import get_current_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("")
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    return [{"id": i.id, "title": i.title, "created_at": i.created_at} for i in items]


@router.post("/add")
def add_to_watchlist(
    title: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = title.strip()
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
    if existing:
        return {"message": "Already in watchlist", "id": existing.id}

    item = WatchlistItem(title=title, user_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)

    return {"message": "Added", "id": item.id}


@router.post("/remove")
def remove_from_watchlist(
    title: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = title.strip()
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

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    return {"message": "Removed"}
