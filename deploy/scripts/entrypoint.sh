#!/usr/bin/env bash
# Backend entrypoint — runs migrations then starts the server.
set -e

echo "Running database migrations..."
uv run alembic upgrade head 2>&1 || {
    echo "WARNING: Migration failed (database may not be ready yet). Continuing..."
}

echo "Starting application..."
exec "$@"
