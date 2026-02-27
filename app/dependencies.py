from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_token
from app.exceptions import AppException, CREDENTIALS_INVALID


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        user_id: int | None = payload.get("user_id")
        if user_id is None:
            raise AppException(
                status_code=401,
                error_code=CREDENTIALS_INVALID,
                message="Could not validate credentials",
                details={},
            )
    except JWTError:
        raise AppException(
            status_code=401,
            error_code=CREDENTIALS_INVALID,
            message="Could not validate credentials",
            details={},
        ) from None

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise AppException(
            status_code=401,
            error_code=CREDENTIALS_INVALID,
            message="Could not validate credentials",
            details={},
        )

    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the current user if a valid token is provided, else None."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id: int | None = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None

    return db.query(User).filter(User.id == user_id).first()
