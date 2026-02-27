#!/bin/sh
# Run migrations then start the backend. Used as Docker entrypoint.
set -e

cd /app

# Wait for DB to be ready and run migrations (retry for compose startup).
MAX_TRIES=30
i=1
while [ "$i" -le "$MAX_TRIES" ]; do
  if python -m alembic upgrade head 2>/dev/null; then
    break
  fi
  if [ "$i" -eq "$MAX_TRIES" ]; then
    echo "Alembic upgrade failed after $MAX_TRIES attempts. Is the database reachable?"
    exit 1
  fi
  echo "Waiting for database... attempt $i/$MAX_TRIES"
  sleep 2
  i=$((i + 1))
done

exec python -m uvicorn app.api:app --host 0.0.0.0 --port 8000
