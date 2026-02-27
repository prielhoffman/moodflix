import logging
from typing import List

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_user_optional
from app.utils import compute_age
from app.routers import auth, watchlist
from app.routers import search
from app.schemas import RecommendationInput, RecommendationOutput
from app.logic import recommend_shows
from app.exceptions import (
    AppException,
    ErrorResponse,
    INTERNAL_ERROR,
)

logger = logging.getLogger(__name__)

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


# -------------------- Global Exception Handlers --------------------

def _error_json(response: ErrorResponse) -> dict:
    return response.model_dump()


@app.exception_handler(AppException)
def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    headers = {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_json(exc.to_response()),
        headers=headers,
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
        details = {k: v for k, v in detail.items() if k != "message"}
    else:
        message = str(detail) if detail else "Request failed"
        details = {}
    error_code = f"HTTP_{exc.status_code}"
    body = ErrorResponse(error_code=error_code, message=message, details=details)
    return JSONResponse(status_code=exc.status_code, content=_error_json(body))


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception: %s",
        exc,
        exc_info=True,
        extra={"path": request.url.path, "method": request.method},
    )
    body = ErrorResponse(
        error_code=INTERNAL_ERROR,
        message="An unexpected error occurred. Please try again later.",
        details={},
    )
    return JSONResponse(status_code=500, content=_error_json(body))


# -------------------- Health Check --------------------

@app.get("/health/db")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "connected"}

# -------------------- Recommendations --------------------

@app.post("/recommend", response_model=List[RecommendationOutput])
def recommend(
    input_data: RecommendationInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    Receive user preferences and return TV show recommendations.
    When authenticated, age is inferred from the user's date_of_birth for content filtering.
    When unauthenticated, age filtering is skipped (treated as adult).
    """
    age = compute_age(current_user.date_of_birth) if current_user else None
    try:
        return recommend_shows(input_data, db=db, age=age)
    except AppException:
        raise
    except Exception as e:
        logger.exception("Recommendation failed: %s", e)
        raise AppException(
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            message="Recommendations are temporarily unavailable. Please try again later.",
            details={},
        ) from e