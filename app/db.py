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
)

# Defaults: use localhost for local development; in Docker set POSTGRES_HOST=db in compose.
_POSTGRES_HOST_DEFAULT = "localhost"
_POSTGRES_PORT_DEFAULT = "5432"


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
            f"Set DATABASE_URL or define {required_vars}. "
            "POSTGRES_HOST defaults to localhost; use 'db' when running in Docker.\n"
            "Tip: copy .env.example to .env and fill in the values."
        )

    host = (os.getenv("POSTGRES_HOST") or "").strip() or _POSTGRES_HOST_DEFAULT
    port = (os.getenv("POSTGRES_PORT") or "").strip() or _POSTGRES_PORT_DEFAULT

    return (
        f"postgresql://{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}"
        f"@{host}:{port}/{values['POSTGRES_DB']}"
    )


DATABASE_URL = _build_database_url()

engine = create_engine(DATABASE_URL, echo=True)


def _ensure_vector_extension(dbapi_connection, connection_record):
    """Ensure pgvector extension exists (for semantic search). Idempotent."""
    cur = dbapi_connection.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    finally:
        cur.close()


from sqlalchemy import event

event.listen(engine.pool, "connect", _ensure_vector_extension)

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
