from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, UserPublic, Token
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.dependencies import get_current_user
from app.exceptions import (
    AppException,
    USER_ALREADY_EXISTS,
    INVALID_CREDENTIALS,
    SERVICE_UNAVAILABLE,
)

DB_UNAVAILABLE_MSG = "Server is temporarily busy. Please try again in a few minutes."

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        existing = db.query(User).filter(User.email == user.email).first()

        if existing:
            raise AppException(
                status_code=400,
                error_code=USER_ALREADY_EXISTS,
                message="Email already registered",
                details={"email": user.email},
            )

        hashed = hash_password(user.password)

        new_user = User(
            full_name=user.full_name.strip(),
            date_of_birth=user.date_of_birth,
            email=user.email,
            hashed_password=hashed,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user
    except AppException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise AppException(
            status_code=503,
            error_code=SERVICE_UNAVAILABLE,
            message=DB_UNAVAILABLE_MSG,
            details={},
        )


@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.email == user.email).first()

        if not db_user:
            raise AppException(
                status_code=401,
                error_code=INVALID_CREDENTIALS,
                message="Invalid credentials",
                details={},
            )

        if not verify_password(user.password, db_user.hashed_password):
            raise AppException(
                status_code=401,
                error_code=INVALID_CREDENTIALS,
                message="Invalid credentials",
                details={},
            )

        token = create_access_token(
            {
                "user_id": db_user.id,
                "email": db_user.email,
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer",
        }
    except AppException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise AppException(
            status_code=503,
            error_code=SERVICE_UNAVAILABLE,
            message=DB_UNAVAILABLE_MSG,
            details={},
        )


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user
