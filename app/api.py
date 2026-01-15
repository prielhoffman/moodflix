from typing import List

from fastapi import FastAPI

from app.schemas import RecommendationInput, RecommendationOutput
from app.logic import recommend_shows

app = FastAPI(title="MoodFlix")


@app.post("/recommend", response_model=List[RecommendationOutput])
def recommend(input_data: RecommendationInput):
    """
    Receive user preferences and return TV show recommendations.
    """
    return recommend_shows(input_data)
