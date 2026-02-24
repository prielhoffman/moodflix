"""
Standardized error handling: schema, custom exception, and error codes.

All API errors return: {"error_code": "...", "message": "...", "details": {...}}.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Consistent error response body for every API error."""

    error_code: str = Field(..., description="Machine-readable code for clients")
    message: str = Field(..., description="Human-readable message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Optional extra context")


# ---------- Error codes (use these when raising AppException) ----------
# Auth
USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
CREDENTIALS_INVALID = "CREDENTIALS_INVALID"  # e.g. invalid/missing token

# Watchlist
SHOW_NOT_FOUND = "SHOW_NOT_FOUND"
INVALID_REQUEST = "INVALID_REQUEST"
SHOW_NO_EMBEDDING = "SHOW_NO_EMBEDDING"

# Recommendations / external
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"  # DB or TMDB timeout / failure

# Search
QUERY_REQUIRED = "QUERY_REQUIRED"
EMBEDDING_ERROR = "EMBEDDING_ERROR"
SEARCH_FAILED = "SEARCH_FAILED"

# Generic
INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    """
    Custom exception that carries a consistent error payload.
    Raised by routes and converted to JSON by the global handler.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
        )
