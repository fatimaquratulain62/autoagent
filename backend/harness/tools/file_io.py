"""File read/write tools."""
import os
import uuid
from pathlib import Path
from typing import ClassVar, Optional

import aiofiles
from pydantic import BaseModel, Field

from backend.harness.tools.base import BaseTool, register_tool
from models.schemas import get_settings

settings = get_settings()

# Will be set per-task when harness initializes
_current_task_id: Optional[str] = None
_current_session_id: Optional[str] = None


def set_task_context(task_id: str, session_id: Optional[str] = None):
    global _current_task_id, _current_session_id
    _current_task_id = task_id
    _current_session_id = session_id


def get_output_dir(task_id: str) -> Path:
    path = Path(settings.OUTPUT_DIR) / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── Read file ─────────────────────────────────────────────────────────────────

class ReadFileInput(BaseModel):
    path: str = Field(..., description="Path to the file to read (relative or absolute)")


class ReadFileTool(BaseTool):
    name: ClassVar[str] = "read_file"
    description: ClassVar[str] = (
        "Read the contents of an uploaded file. Supports text files, CSV, JSON, PDF. "
        "Provide the filename as given after upload."
    )
    input_schema: ClassVar[type[BaseModel]] = ReadFileInput

    def __init__(self, task_id_getter=None):
        self.task_id_getter = task_id_getter

    async def run(self, path: str) -> str:
        # Try uploaded files first
        upload_dirs = [
            Path(settings.OUTPUT_DIR) / "uploads",
            Path("/tmp/autoagent/uploads"),
        ]
        if _current_task_id:
            upload_dirs.insert(0, Path(settings.OUTPUT_DIR) / _current_task_id / "uploads")

        file_path = None
        for d in upload_dirs:
            candidate = d / Path(path).name
            if candidate.exists():
                file_path = candidate
                break

        if not file_path:
            # Try as absolute path
            p = Path(path)
            if p.exists():
                file_path = p

        if not file_path:
            return f"Error: File '{path}' not found. Available upload paths searched."

        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text[:20_000] or "No text extracted from PDF."
            except Exception as e:
                return f"Error reading PDF: {e}"

        # Text/CSV/JSON etc.
        async with aiofiles.open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = await f.read()

        if len(content) > 20_000:
            content = content[:20_000] + "\n[... file truncated ...]"

        return content


# ── Write file ────────────────────────────────────────────────────────────────

class WriteFileInput(BaseModel):
    filename: str = Field(..., description="Filename for the output (e.g. 'report.md', 'data.csv')")
    content: str = Field(..., description="Text content to write to the file")


class WriteFileTool(BaseTool):
    name: ClassVar[str] = "write_file"
    description: ClassVar[str] = (
        "Write text content to a file in the session's output directory. "
        "Use this to produce deliverables like reports, markdown tables, CSV data, etc. "
        "Returns a download URL for the created file."
    )
    input_schema: ClassVar[type[BaseModel]] = WriteFileInput

    async def run(self, filename: str, content: str) -> str:
        task_id = _current_task_id or "default"
        output_dir = get_output_dir(task_id)

        # Sanitize filename
        safe_name = Path(filename).name
        if not safe_name:
            safe_name = f"output_{uuid.uuid4().hex[:8]}.txt"

        file_path = output_dir / safe_name
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)

        size = file_path.stat().st_size
        download_url = f"/api/v1/tasks/{task_id}/files/{safe_name}"

        return (
            f"File written successfully!\n"
            f"Filename: {safe_name}\n"
            f"Size: {size:,} bytes\n"
            f"Download URL: {download_url}"
        )


register_tool(ReadFileTool())
register_tool(WriteFileTool())
