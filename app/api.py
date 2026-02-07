from typing import List

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models import Show
from app.db import get_db
from app.routers import auth, watchlist
from app.routers import search
from app.schemas import RecommendationInput, RecommendationOutput
from app.logic import recommend_shows

app = FastAPI(title="MoodFlix")

app.include_router(auth.router)
app.include_router(watchlist.router)
app.include_router(search.router)

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
def recommend(input_data: RecommendationInput, db: Session = Depends(get_db)):
    """
    Receive user preferences and return TV show recommendations.
    """
    return recommend_shows(input_data, db=db)


@app.get("/debug/shows")
def debug_shows(db: Session = Depends(get_db)):
    return db.query(Show).limit(5).all()