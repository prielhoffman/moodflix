from typing import List

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text


from app.db import get_db
from app.routers import auth


from app.schemas import (
    RecommendationInput,
    RecommendationOutput,
    SaveRequest,
    WatchlistResponse,
)
from app.logic import recommend_shows
from app.user_data import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
)

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="MoodFlix")
app.include_router(auth.router)


# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Health Check --------------------

@app.get("/health/db")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "connected"}


# -------------------- Recommendations --------------------


@app.post("/recommend", response_model=List[RecommendationOutput])
def recommend(input_data: RecommendationInput):
    """
    Receive user preferences and return TV show recommendations.
    """
    return recommend_shows(input_data)


# -------------------- Watchlist --------------------


@app.post("/watchlist/add", response_model=WatchlistResponse)
def add_watchlist_item(request: SaveRequest):
    """
    Add a show to the user's watchlist.
    """
    add_to_watchlist(request.title)

    return WatchlistResponse(watchlist=get_watchlist())


@app.post("/watchlist/remove", response_model=WatchlistResponse)
def remove_watchlist_item(request: SaveRequest):
    """
    Remove a show from the user's watchlist.
    """
    remove_from_watchlist(request.title)

    return WatchlistResponse(watchlist=get_watchlist())


@app.get("/watchlist", response_model=WatchlistResponse)
def get_watchlist_items():
    """
    Get all saved shows in the watchlist.
    """
    return WatchlistResponse(watchlist=get_watchlist())
