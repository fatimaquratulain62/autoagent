"""File upload router."""
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile
from loguru import logger

from models.schemas import get_settings

router = APIRouter(prefix="/api/v1/files", tags=["files"])
settings = get_settings()


@router.post("/upload")
async def upload_file(file: UploadFile, session_id: str = None):
    """Upload a file for use in agent tasks."""
    if not session_id:
        session_id = str(uuid.uuid4())

    upload_dir = Path(settings.OUTPUT_DIR) / "uploads" / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename).name if file.filename else f"file_{uuid.uuid4().hex[:8]}"
    file_path = upload_dir / safe_name

    content = await file.read()

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    logger.info(f"Uploaded file: {safe_name} ({len(content):,} bytes) for session {session_id}")

    return {
        "filename": safe_name,
        "session_id": session_id,
        "size_bytes": len(content),
        "path": str(file_path),
    }
