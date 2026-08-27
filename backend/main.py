"""AutoAgent — FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.routers import files, scheduled, tasks
from memory.session_store import close_redis, get_redis
from models.database import create_tables
from models.schemas import get_settings

settings = get_settings()

# Configure logging
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    level=settings.LOG_LEVEL,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AutoAgent...")
    await create_tables()
    logger.info("Database tables ready")
    await get_redis()
    logger.info("Redis connected")
    import backend.harness.tools  # noqa — registers all tools
    logger.info("Tools registered")
    yield
    await close_redis()
    logger.info("AutoAgent shutdown complete")


app = FastAPI(
    title="AutoAgent",
    description="Autonomous AI Task Execution Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — wide open for local dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allows any origin including localhost:5173
    allow_credentials=False,       # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(tasks.router)
app.include_router(files.router)
app.include_router(scheduled.router)


# ── Health / ping ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/v1/ping")
async def ping():
    """
    Reachability check used by the frontend.
    Lives under /api/v1 so it goes through the Vite proxy just like every
    other API call — no separate proxy rule needed.
    """
    return {"status": "ok"}


# ── Models list ───────────────────────────────────────────────────────────────

@app.get("/api/v1/models")
async def list_models():
    """
    Available LLM providers and models.
    NOTE: gpt-oss-120b is Groq-hosted — use provider=groq for it.
    """
    return {
        "providers": {
            "groq": {
                "available": bool(settings.GROQ_API_KEY),
                "note": "Use provider=groq for ALL Groq-hosted models",
                "models": [
                    "gpt-oss-120b",
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "mixtral-8x7b-32768",
                    "gemma2-9b-it",
                ],
            },
            "openai": {
                "available": bool(settings.OPENAI_API_KEY),
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            },
            "anthropic": {
                "available": bool(settings.ANTHROPIC_API_KEY),
                "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
            },
        }
    }