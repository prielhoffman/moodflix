from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


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
    age: int = Field(..., ge=0, description="User age for content suitability")

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


# --------------------------------- OUTPUT ---------------------------------
class RecommendationOutput(BaseModel):
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


# --------------------------------- WATCHLIST ---------------------------------


class SaveRequest(BaseModel):
    title: str = Field(..., description="Title of the show to save/remove")


class WatchlistResponse(BaseModel):
    watchlist: List[str] = Field(
        default_factory=list,
        description="List of saved show titles",
    )
