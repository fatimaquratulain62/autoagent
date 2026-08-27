# AutoAgent — Complete Setup Guide

Step-by-step commands for every OS. Copy-paste from top to bottom.

---

## Prerequisites

You need these installed before anything else:

- **Python 3.11+** — `python --version` to check
- **Node.js 20+** — `node --version` to check
- **Git** — `git --version` to check
- **PostgreSQL 14+** — running locally, or use Docker
- **Redis 7+** — running locally, or use Docker

> **Easiest path:** Use the Docker route at the bottom — it handles Postgres and Redis for you.

---

## Option A — Local Dev (no Docker)

### 1. Clone the repo

```bash
git clone <your-repo-url> autoagent
cd autoagent
```

---

### 2. Create and activate a Python virtual environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of your terminal prompt. Every Python command from here runs inside the venv.

---

### 3. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verify it worked:
```bash
pip list | grep fastapi
# Should print: fastapi   0.115.x
```

---

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in at minimum:

```env
# Required — get free keys at these links:
GROQ_API_KEY=gsk_...          # https://console.groq.com
TAVILY_API_KEY=tvly-...       # https://app.tavily.com

# Optional — only if you want to use these providers:
OPENAI_API_KEY=sk-...         # https://platform.openai.com
ANTHROPIC_API_KEY=sk-ant-...  # https://console.anthropic.com

# Point at your local Postgres:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/autoagent

# Point at your local Redis:
REDIS_URL=redis://localhost:6379/0
```

---

### 5. Create the database

Make sure Postgres is running, then:

```bash
# Create the database (run once)
psql -U postgres -c "CREATE DATABASE autoagent;"

# Or on some systems:
createdb autoagent
```

---

### 6. Run database migrations

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, Initial schema
```

---

### 7. Start the backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO     Starting AutoAgent...
INFO     Database tables ready
INFO     Redis connected
INFO     Tools registered
INFO     Uvicorn running on http://0.0.0.0:8000
```

Test it:
```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}
```

Leave this terminal running. Open a new terminal for the frontend.

---

### 8. Install frontend dependencies

```bash
cd frontend
npm install
```

---

### 9. Start the frontend

```bash
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

---

### 10. Open the app

Go to **http://localhost:5173** in your browser.

---

## Option B — Docker Compose (recommended)

Handles Postgres and Redis automatically. Just needs Docker Desktop installed.

### 1. Clone the repo

```bash
git clone <your-repo-url> autoagent
cd autoagent
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your API keys (GROQ_API_KEY at minimum)
```

### 3. Start everything

```bash
docker compose up --build
```

First run takes ~2 minutes to build. Subsequent runs are instant.

To run in the background:
```bash
docker compose up --build -d
```

### 4. Run migrations (first time only)

```bash
docker compose exec backend alembic upgrade head
```

### 5. Open the app

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

---

## Day-to-day commands

### Activate the venv (must do this every new terminal session)

```bash
# macOS / Linux
source venv/bin/activate

# Windows CMD
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1
```

### Start backend (after activating venv)

```bash
uvicorn backend.main:app --reload --port 8000
```

### Start frontend (separate terminal)

```bash
cd frontend
npm run dev
```

### Stop everything

```bash
# Backend / frontend — Ctrl+C in each terminal

# Docker (if using)
docker compose down

# Docker + wipe volumes (resets database)
docker compose down -v
```

---

## Database commands

### Run migrations after pulling new code

```bash
# Local
alembic upgrade head

# Docker
docker compose exec backend alembic upgrade head
```

### Create a new migration (after changing models)

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

### Reset the database completely

```bash
# Local
alembic downgrade base
alembic upgrade head

# Docker
docker compose down -v
docker compose up -d postgres redis
docker compose exec backend alembic upgrade head
```

### Open Postgres shell

```bash
# Local
psql -U postgres -d autoagent

# Docker
docker compose exec postgres psql -U autoagent -d autoagent
```

---

## Dependency commands

### Add a new Python package

```bash
# Make sure venv is active first
pip install some-package
pip freeze > requirements.txt   # save it
```

### Update all Python packages

```bash
pip install --upgrade -r requirements.txt
```

### Add a new frontend package

```bash
cd frontend
npm install some-package
```

### Update all frontend packages

```bash
cd frontend
npm update
```

---

## Troubleshooting

### `ModuleNotFoundError` on backend start

You forgot to activate the venv:
```bash
source venv/bin/activate   # then retry
```

### `connection refused` on port 5432 (Postgres)

Postgres isn't running:
```bash
# macOS (Homebrew)
brew services start postgresql@16

# Ubuntu / Debian
sudo systemctl start postgresql

# Docker
docker compose up -d postgres
```

### `connection refused` on port 6379 (Redis)

Redis isn't running:
```bash
# macOS (Homebrew)
brew services start redis

# Ubuntu / Debian
sudo systemctl start redis

# Docker
docker compose up -d redis
```

### `alembic: command not found`

Venv isn't active:
```bash
source venv/bin/activate
alembic upgrade head
```

### Frontend shows "Failed to fetch" errors

Backend isn't running, or is on a different port. Check:
```bash
curl http://localhost:8000/health
```

If that fails, start the backend first (step 7 above).

### Port 8000 or 5173 already in use

```bash
# Find what's using the port
lsof -i :8000
lsof -i :5173

# Kill it (replace PID with the number from above)
kill -9 <PID>
```

### `GROQ_API_KEY not set` warning

Your `.env` file is missing or the key is blank. Open `.env`, add the key, then restart the backend. The backend reads `.env` on startup.

---

## Environment variable reference

All settings live in `.env`. Full list:

```env
# ── LLM Providers ─────────────────────────────────
GROQ_API_KEY=               # Required. Free at console.groq.com
OPENAI_API_KEY=             # Optional
ANTHROPIC_API_KEY=          # Optional

# ── Default model ──────────────────────────────────
DEFAULT_LLM_PROVIDER=groq
DEFAULT_MODEL=llama-3.3-70b-versatile

# ── Tool APIs ──────────────────────────────────────
TAVILY_API_KEY=             # Recommended. Free tier at app.tavily.com
                            # Without this, falls back to DuckDuckGo scraping

# ── Database ───────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/autoagent

# ── Redis ──────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── App ────────────────────────────────────────────
ENVIRONMENT=development     # or production
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR

# ── File storage ───────────────────────────────────
OUTPUT_DIR=/tmp/autoagent/outputs
MAX_FILE_SIZE_MB=50

# ── Harness limits ─────────────────────────────────
DEFAULT_MAX_TURNS=40
DEFAULT_TOKEN_BUDGET=100000
TOOL_TIMEOUT_SECONDS=30
```

---

## Quick-reference cheatsheet

```bash
# First-time setup
git clone <repo> autoagent && cd autoagent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
psql -U postgres -c "CREATE DATABASE autoagent;"
alembic upgrade head

# Every day
source venv/bin/activate                              # terminal 1
uvicorn backend.main:app --reload --port 8000         # terminal 1
cd frontend && npm run dev                            # terminal 2

# Docker alternative (replaces all of the above)
cp .env.example .env          # then edit .env
docker compose up --build
```