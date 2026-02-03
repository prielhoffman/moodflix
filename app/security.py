"""
Security utilities for password hashing and JWT token management.

This module provides:
- Password hashing and verification using bcrypt
- JWT token creation and decoding
"""

import os
import warnings
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Production environment detection: check explicit ENV or APP_ENV variables
# Treat "production" or "prod" (case-insensitive) as production environment
_env_var = (os.getenv("ENV") or os.getenv("APP_ENV", "")).lower()
_is_production = _env_var in ("production", "prod")

# Warn only when in production AND using default SECRET_KEY
if _is_production and SECRET_KEY == "dev-secret-key-change-in-production":
    warnings.warn(
        "SECRET_KEY is using default value. Set SECRET_KEY in environment "
        "variables for production use.",
        UserWarning,
    )


def hash_password(plain: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        plain: Plain text password string

    Returns:
        Hashed password string
    """
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain: Plain text password to verify
        hashed: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing the data to encode in the token
               (typically includes user_id, email, etc.)
        expires_minutes: Optional expiration time in minutes.
                        Defaults to ACCESS_TOKEN_EXPIRE_MINUTES from env.

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_minutes is None:
        expires_minutes = ACCESS_TOKEN_EXPIRE_MINUTES

    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})

    # Encode and return token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary containing the decoded token payload (never None)

    Raises:
        JWTError: If token is invalid, expired, or cannot be decoded.
                  Always raises on failure; never returns None silently.
    """
    if not token:
        # Explicit check for empty/invalid token input
        raise JWTError("Invalid token: token cannot be empty")

    try:
        # Decode and verify token - jwt.decode raises JWTError on any failure
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Ensure we always return a dict (jwt.decode should never return None, but be explicit)
        if payload is None:
            raise JWTError("Invalid token: decoded payload is empty")
        
        return payload
    except JWTError as e:
        # Re-raise with user-friendly message, preserving original exception chain
        # Don't expose internal error details to users
        raise JWTError("Invalid or expired token") from e
