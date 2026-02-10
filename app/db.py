import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()
Base = declarative_base()

_REQUIRED_POSTGRES_ENV_VARS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
)


def _build_database_url() -> str:
    # Optional direct connection string support.
    direct_url = os.getenv("DATABASE_URL")
    if direct_url and direct_url.strip():
        return direct_url.strip()

    values: dict[str, str] = {}
    missing: list[str] = []

    for name in _REQUIRED_POSTGRES_ENV_VARS:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            missing.append(name)
        else:
            values[name] = raw.strip()

    if missing:
        missing_vars = ", ".join(sorted(missing))
        required_vars = ", ".join(_REQUIRED_POSTGRES_ENV_VARS)
        raise RuntimeError(
            "Database configuration is incomplete.\n"
            f"Missing required environment variables: {missing_vars}\n"
            f"Set DATABASE_URL or define all POSTGRES_* variables: {required_vars}\n"
            "Tip: copy .env.example to .env and fill in the values."
        )

    return (
        f"postgresql://{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}"
        f"@{values['POSTGRES_HOST']}:{values['POSTGRES_PORT']}/{values['POSTGRES_DB']}"
    )


DATABASE_URL = _build_database_url()

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
