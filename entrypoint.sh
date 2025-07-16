#!/bin/sh
set -e

DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
MAX_TRIES=30
TRIES=0

>&2 echo "[Entrypoint] Waiting for postgres at $DB_HOST:$DB_PORT..."

until python -c "import socket; s=socket.socket(); s.connect(('${DB_HOST}', int('${DB_PORT}'))); s.close()" 2>/dev/null; do
  TRIES=$((TRIES+1))
  if [ "$TRIES" -ge "$MAX_TRIES" ]; then
    >&2 echo "[Entrypoint] ERROR: Could not connect to Postgres at $DB_HOST:$DB_PORT after $MAX_TRIES attempts."
    exit 1
  fi
  sleep 1
done

>&2 echo "[Entrypoint] Postgres is up - running migrations."
python migrate.py upgrade

>&2 echo "[Entrypoint] Starting main application."
exec python main.py
