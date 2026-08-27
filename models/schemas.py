"""Pydantic schemas and application settings."""
import uuid
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Providers
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Default LLM
    DEFAULT_LLM_PROVIDER: str = "groq"
    DEFAULT_MODEL: str = "llama-3.3-70b-versatile"

    # Tool APIs
    TAVILY_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://autoagent:autoagent@localhost:5432/autoagent"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # App
    SECRET_KEY: str = "change_me"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # File storage
    OUTPUT_DIR: str = "/tmp/autoagent/outputs"
    MAX_FILE_SIZE_MB: int = 50

    # Harness limits
    DEFAULT_MAX_TURNS: int = 40
    DEFAULT_TOKEN_BUDGET: int = 100000
    TOOL_TIMEOUT_SECONDS: float = 30.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# ── Harness config ────────────────────────────────────────────────────────────

class HarnessConfig(BaseModel):
    max_turns: int = 40
    # Keep response tokens low so request + response fits inside
    # Groq free-tier TPM limit (8,000 for gpt-oss-120b).
    # Increase to 2048-4096 if you upgrade to Dev tier.
    max_tokens_per_turn: int = 1024
    total_token_budget: int = 100_000
    tool_timeout_seconds: float = 30.0
    retry_on_tool_error: bool = True
    max_tool_retries: int = 2
    enabled_tools: list[str] = Field(
        default=[
            "web_search", "browse_url", "run_python",
            "read_file", "write_file", "http_request",
            "memory_store", "memory_retrieve",
        ]
    )
    # Provider: "groq" | "openai" | "anthropic"
    # NOTE: gpt-oss-120b, llama-3.3-70b-versatile, mixtral-8x7b are ALL Groq-hosted.
    # Use provider="groq" for all of them.
    llm_provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"


# ── Agent events ──────────────────────────────────────────────────────────────

class AgentEvent(BaseModel):
    event_type: Literal["thought", "tool_call", "tool_result", "error", "done"]
    turn: int
    content: str = ""
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Optional[str] = None
    duration_ms: float = 0.0
    token_usage: dict = Field(default_factory=dict)


# ── Task schemas ──────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    description: str = Field(..., min_length=5, max_length=10_000)
    config: HarnessConfig = Field(default_factory=HarnessConfig)
    uploaded_file_paths: list[str] = Field(default_factory=list)


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskSummary(BaseModel):
    id: uuid.UUID
    description: str
    status: str
    turn_count: int = 0
    duration_seconds: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    final_answer: Optional[str] = None

    class Config:
        from_attributes = True


class TurnOut(BaseModel):
    id: uuid.UUID
    turn_number: int
    thought: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Optional[str] = None
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    download_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledTaskCreate(BaseModel):
    cron_expression: str
    task_description: str


class ScheduledTaskOut(BaseModel):
    id: uuid.UUID
    cron_expression: str
    task_description: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledTaskUpdate(BaseModel):
    is_active: Optional[bool] = None
    cron_expression: Optional[str] = None
    task_description: Optional[str] = None