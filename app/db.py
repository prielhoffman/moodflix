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

# Defaults for local PostgreSQL (127.0.0.1:5432). In Docker set POSTGRES_HOST=db.
_POSTGRES_HOST_DEFAULT = "127.0.0.1"
_POSTGRES_PORT_DEFAULT = "5432"
# Fallbacks when running locally (no DATABASE_URL and vars unset)
_POSTGRES_USER_DEFAULT = "postgres"
_POSTGRES_PASSWORD_DEFAULT = ""
_POSTGRES_DB_DEFAULT = "moodflix"


def _build_database_url() -> str:
    # Optional direct connection string support.
    direct_url = os.getenv("DATABASE_URL")
    if direct_url and direct_url.strip():
        return direct_url.strip()

    host = (os.getenv("POSTGRES_HOST") or "").strip() or _POSTGRES_HOST_DEFAULT
    port = (os.getenv("POSTGRES_PORT") or "").strip() or _POSTGRES_PORT_DEFAULT
    is_local = host in ("127.0.0.1", "localhost", "::1")

    values: dict[str, str] = {}
    for name in _REQUIRED_POSTGRES_ENV_VARS:
        raw = os.getenv(name)
        if raw is not None and str(raw).strip():
            values[name] = str(raw).strip()

    # For local dev, allow defaults when vars are missing.
    if is_local:
        values.setdefault("POSTGRES_USER", _POSTGRES_USER_DEFAULT)
        values.setdefault("POSTGRES_PASSWORD", _POSTGRES_PASSWORD_DEFAULT)
        values.setdefault("POSTGRES_DB", _POSTGRES_DB_DEFAULT)

    missing = [n for n in _REQUIRED_POSTGRES_ENV_VARS if n not in values]
    if missing:
        missing_vars = ", ".join(sorted(missing))
        required_vars = ", ".join(_REQUIRED_POSTGRES_ENV_VARS)
        raise RuntimeError(
            "Database configuration is incomplete.\n"
            f"Missing required environment variables: {missing_vars}\n"
            f"Set DATABASE_URL or define {required_vars}. "
            "For local PostgreSQL, POSTGRES_HOST defaults to 127.0.0.1 and port to 5432; "
            "user/password/db default to postgres/<empty>/moodflix when host is local.\n"
            "Tip: copy .env.example to .env and fill in the values."
        )

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
