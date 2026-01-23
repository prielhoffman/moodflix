from typing import List

from fastapi import FastAPI

from app.schemas import RecommendationInput, RecommendationOutput
from app.logic import recommend_shows

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MoodFlix")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/recommend", response_model=List[RecommendationOutput])
def recommend(input_data: RecommendationInput):
    """
    Receive user preferences and return TV show recommendations.
    """
    return recommend_shows(input_data)
