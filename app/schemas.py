from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, model_validator


# --------------------------------- INPUT ---------------------------------
class BingePreference(str, Enum):
    BINGE = "binge"
    SHORT_SERIES = "short_series"


class Mood(str, Enum):
    CHILL = "chill"
    HAPPY = "happy"
    FAMILIAR = "familiar"
    FOCUSED = "focused"
    ADRENALINE = "adrenaline"
    DARK = "dark"
    CURIOUS = "curious"


class EpisodeLengthPreference(str, Enum):
    SHORT = "short"      # 30 minutes maximum
    LONG = "long"        # 31 minutes minimum
    ANY = "any"


class WatchingContext(str, Enum):
    ALONE = "alone"
    PARTNER = "partner"
    FAMILY = "family"


class RecommendationInput(BaseModel):
    binge_preference: BingePreference = Field(
        BingePreference.BINGE,
        description="Whether the user prefers binge-worthy or single-season shows",
    )

    preferred_genres: List[str] = Field(
        default_factory=list,
        description="List of preferred genres (e.g. comedy, drama, sci-fi)",
    )

    mood: Mood = Field(
        Mood.CHILL,
        description="How the user wants to feel while watching (emotional intention)",
    )

    language_preference: Optional[str] = Field(
        None,
        description="Preferred language for the show (e.g. English, Spanish)",
    )

    episode_length_preference: EpisodeLengthPreference = Field(
        EpisodeLengthPreference.ANY,
        description="Preferred episode length",
    )

    watching_context: WatchingContext = Field(
        WatchingContext.ALONE,
        description="Context in which the show will be watched",
    )

    query: Optional[str] = Field(
        None,
        description="Optional natural language query for semantic candidate retrieval",
    )

    guest_family_safe: Optional[bool] = Field(
        None,
        description="For unauthenticated users only: True = apply family/general safety filter (under 18), False/None = adult (18+). Ignored when authenticated.",
    )


# --------------------------------- OUTPUT ---------------------------------
class RecommendationOutput(BaseModel):
    id: Optional[int] = Field(None, description="Show ID (shows.id) when from DB; for favorites add by show_id")
    title: str = Field(..., description="Title of the TV show")

    recommendation_reason: Optional[str] = Field(
        None,
        description="Short explanation of why this show was recommended",
    )

    genres: List[str] = Field(
        default_factory=list,
        description="Primary genres of the show",
    )

    short_summary: str = Field(
        ...,
        description="Brief summary of the TV show",
    )

    content_rating: Optional[str] = Field(
        None,
        description="Age or content classification (e.g. TV-14, TV-MA)",
    )

    average_episode_length: Optional[int] = Field(
        None,
        description="Average episode duration in minutes",
    )

    number_of_seasons: Optional[int] = Field(
        None,
        ge=1,
        description="Total number of seasons",
    )

    language: Optional[str] = Field(
        None,
        description="Original language of the TV show",
    )

    # -------- TMDB enrichment fields --------
    poster_url: Optional[str] = Field(
        None,
        description="Poster image URL from TMDB",
    )

    tmdb_rating: Optional[float] = Field(
        None,
        description="Rating from TMDB",
    )

    tmdb_overview: Optional[str] = Field(
        None,
        description="Overview from TMDB",
    )

    first_air_date: Optional[str] = Field(
        None,
        description="First air date from TMDB",
    )


# --------------------------------- FAVORITES (API: /watchlist) ---------------------------------
# Internal names remain watchlist_* for backwards compatibility; user-facing term is Favorites.


class SaveRequest(BaseModel):
    """Legacy: add/remove by title only. Not used by current API. TODO V2: remove if unused."""

    title: str = Field(..., description="Title of the show to save/remove")


class WatchlistAddRequest(BaseModel):
    """Add to favorites by show_id (preferred) or by title when show_id is missing (e.g. recommendations from static data)."""

    show_id: Optional[int] = Field(None, ge=1, description="ID of the show (shows.id) to add")
    title: Optional[str] = Field(None, description="Title of the show to add (used when show_id not provided)")
    poster_url: Optional[str] = Field(None, description="Optional poster URL when creating a show from title (fallback data)")

    @model_validator(mode="after")
    def at_least_one_identifier(self):
        if self.show_id is None and (self.title is None or not str(self.title).strip()):
            raise ValueError("Either show_id or title must be provided")
        return self


class WatchlistRemoveRequest(BaseModel):
    """Remove from favorites. Prefer show_id. title is legacy for pre-migration items. TODO V2: deprecate remove-by-title."""

    show_id: Optional[int] = Field(None, ge=1, description="ID of the show to remove (preferred)")
    title: Optional[str] = Field(None, description="Legacy: title of the show to remove (when show_id not set)")

    @model_validator(mode="after")
    def at_least_one_identifier(self):
        if self.show_id is None and (self.title is None or not str(self.title).strip()):
            raise ValueError("Either show_id or title must be provided")
        return self


class WatchlistItemOut(BaseModel):
    """Favorites entry. show_id null for legacy items; title from show relation or denormalized."""

    show_id: Optional[int] = Field(None, description="ID of the show (null for legacy items only)")
    title: str = Field(..., description="Show title (from show relation or denormalized)")
    poster_url: Optional[str] = Field(None, description="Poster URL when available from show")


class WatchlistResponse(BaseModel):
    watchlist: List[WatchlistItemOut] = Field(
        default_factory=list,
        description="List of favorites (internal key: watchlist for API compatibility)",
    )

# --------------------------------- AUTH ---------------------------------


from pydantic import EmailStr
from datetime import datetime


def _validate_date_of_birth(v: date) -> date:
    """Validate date_of_birth is in the past and age is 13-120."""
    today = date.today()
    if v >= today:
        raise ValueError("date_of_birth must be in the past")
    age = today.year - v.year
    if (today.month, today.day) < (v.month, v.day):
        age -= 1
    if age < 13:
        raise ValueError("User must be at least 13 years old")
    if age > 120:
        raise ValueError("Invalid date of birth")
    return v


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    date_of_birth: date = Field(..., description="User's date of birth (age 13-120)")
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)

    @model_validator(mode="after")
    def validate_dob(self):
        _validate_date_of_birth(self.date_of_birth)
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=72)


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    date_of_birth: date
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str

# ----------------------------------------------------
class WatchlistTitle(BaseModel):
    """Legacy: add/remove by title only. Not used by current API. TODO V2: remove if unused."""
    title: str

# --------------------------------- SEMANTIC SEARCH ---------------------------------


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return (max 50)")


class SemanticSearchResult(BaseModel):
    id: int
    title: str
    genres: List[str] = Field(default_factory=list)
    ai_match_reason: Optional[str] = None
    overview: str
    poster_url: Optional[str] = None
    vote_average: Optional[float] = None
    first_air_date: Optional[str] = None
    distance: float = Field(..., description="Cosine distance (lower is more similar)")


class MoreLikeThisRequest(BaseModel):
    show_id: int = Field(..., ge=1, description="Show id to find similar titles for")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return (max 50)")