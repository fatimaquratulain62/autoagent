#!/usr/bin/env bash
# Run backend locally (requires Python 3.11+ and a local Postgres + Redis)
set -e

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — please fill in your API keys"
  exit 1
fi

# Install deps
pip install -r requirements.txt

# Run migrations (needs Postgres running)
alembic upgrade head

# Start backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
