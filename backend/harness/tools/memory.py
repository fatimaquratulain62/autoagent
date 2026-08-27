"""Memory store/retrieve tools backed by Redis."""
from typing import ClassVar, Optional

from pydantic import BaseModel, Field

from backend.harness.tools.base import BaseTool, register_tool
from memory.session_store import memory_get, memory_set

_current_session_id: Optional[str] = None


def set_session(session_id: str):
    global _current_session_id
    _current_session_id = session_id


class MemoryStoreInput(BaseModel):
    key: str = Field(..., description="Key to store the value under")
    value: str = Field(..., description="Value to store (will be stored as text)")


class MemoryStoreTool(BaseTool):
    name: ClassVar[str] = "memory_store"
    description: ClassVar[str] = (
        "Store a value in session memory with a key. Use to save intermediate results "
        "you'll need later in the task, like URLs, data extracts, computed values, etc."
    )
    input_schema: ClassVar[type[BaseModel]] = MemoryStoreInput

    async def run(self, key: str, value: str) -> str:
        session_id = _current_session_id or "default"
        await memory_set(session_id, key, value)
        return f"Stored '{key}' = {value[:200]}{'...' if len(value) > 200 else ''}"


class MemoryRetrieveInput(BaseModel):
    key: str = Field(..., description="Key to retrieve the value for")


class MemoryRetrieveTool(BaseTool):
    name: ClassVar[str] = "memory_retrieve"
    description: ClassVar[str] = (
        "Retrieve a previously stored value by key from session memory."
    )
    input_schema: ClassVar[type[BaseModel]] = MemoryRetrieveInput

    async def run(self, key: str) -> str:
        session_id = _current_session_id or "default"
        value = await memory_get(session_id, key)
        if value is None:
            return f"No value found for key '{key}'"
        return f"Value for '{key}': {value}"


register_tool(MemoryStoreTool())
register_tool(MemoryRetrieveTool())
