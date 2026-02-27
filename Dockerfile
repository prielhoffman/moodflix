# Backend: FastAPI + SQLAlchemy + pgvector (Python). No extra system deps for psycopg[binary]/pgvector.
FROM python:3.12-slim

WORKDIR /app

# 1) Dependencies only — this layer is cached until requirements.txt changes.
COPY requirements.txt .
# BuildKit cache mount: pip reuses downloads across builds; the cache is in the mount, not in the image.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 2) Application code — changes here do not invalidate the dependency layer.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts

RUN chmod +x /app/scripts/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
