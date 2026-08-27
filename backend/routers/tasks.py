"""Tasks API router — start, stream, status, cancel, history."""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.harness.loop import AgentHarness
from memory.session_store import subscribe_events
from models.database import AgentTurn, OutputFile, Task, TaskStatus, get_db
from models.schemas import (
    HarnessConfig,
    TaskCreate,
    TaskSummary,
    TurnOut,
    FileOut,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# Running task registry: task_id → asyncio.Task
_running_tasks: dict[str, asyncio.Task] = {}


# ── Start task ────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task = Task(
        description=payload.description,
        status="queued",
        config=payload.config.model_dump(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    task_id = str(task.id)

    # Launch in background
    async_task = asyncio.create_task(
        _run_task(task_id, payload.config),
        name=f"agent-{task_id}",
    )
    _running_tasks[task_id] = async_task

    # Remove from registry when done
    async_task.add_done_callback(lambda t: _running_tasks.pop(task_id, None))

    return {"task_id": task_id, "status": "queued"}


async def _run_task(task_id: str, config: HarnessConfig):
    """Background coroutine that runs the agent harness."""
    from models.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Task).where(Task.id == uuid.UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found in DB")
                return

            harness = AgentHarness(task=task, config=config, db=db)
            await harness.run()

        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled")
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")


# ── SSE stream ────────────────────────────────────────────────────────────────

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _make_evt(event_type: str, turn: int, **kwargs) -> str:
    payload = {
        "event_type": event_type,
        "turn": turn,
        "content": "",
        "tool_name": None,
        "tool_args": None,
        "tool_result": None,
        "duration_ms": 0,
        "token_usage": {},
        **kwargs,
    }
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/{task_id}/stream")
async def stream_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """
    Server-Sent Events stream of AgentEvents for a task.

    Flow:
    1. Replay any turns already in DB (handles browser reconnects mid-task)
    2. If task is already terminal → emit done/error and close
    3. Otherwise subscribe to Redis pub/sub for live events
    4. Send a heartbeat comment every 15s so proxies don't close the connection
    """

    async def event_generator():
        # ── 1. Replay existing DB turns (reconnect support) ───────────────────
        try:
            result = await db.execute(
                select(AgentTurn)
                .where(AgentTurn.task_id == uuid.UUID(task_id))
                .order_by(AgentTurn.turn_number)
            )
            existing_turns = result.scalars().all()
        except Exception as e:
            logger.error(f"DB error fetching turns for {task_id}: {e}")
            existing_turns = []

        for turn in existing_turns:
            if turn.thought:
                yield _make_evt("thought", turn.turn_number,
                                content=turn.thought,
                                duration_ms=turn.duration_ms or 0,
                                token_usage={"total_tokens": turn.tokens_used or 0})
            if turn.tool_name:
                yield _make_evt("tool_call", turn.turn_number,
                                content=f"Called {turn.tool_name}",
                                tool_name=turn.tool_name,
                                tool_args=turn.tool_args)
                if turn.tool_result:
                    yield _make_evt("tool_result", turn.turn_number,
                                    tool_name=turn.tool_name,
                                    tool_result=turn.tool_result)

        # ── 2. Check current task status ──────────────────────────────────────
        try:
            task_result = await db.execute(
                select(Task).where(Task.id == uuid.UUID(task_id))
            )
            task = task_result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"DB error fetching task {task_id}: {e}")
            task = None

        if task is None:
            yield _make_evt("error", 0, content=f"Task {task_id} not found.")
            return

        if task.status in TERMINAL_STATUSES:
            # Already finished — send final event and close
            if task.status == "completed":
                yield _make_evt("done", 0,
                                content=task.final_answer or "Task completed.")
            else:
                yield _make_evt("error", 0,
                                content=task.error_message or f"Task {task.status}.")
            return

        # ── 3. Live stream via Redis pub/sub ──────────────────────────────────
        # The harness publishes events as it runs. We subscribe and forward.
        # We also send SSE heartbeat comments every 15s so nginx/CloudFlare
        # don't close idle connections.
        heartbeat_interval = 15  # seconds

        async def _heartbeat(q: asyncio.Queue):
            """Push sentinel heartbeats into the queue periodically."""
            while True:
                await asyncio.sleep(heartbeat_interval)
                await q.put(None)  # None = heartbeat

        async def _subscriber(q: asyncio.Queue):
            """Pull Redis events into the queue."""
            try:
                async for event in subscribe_events(task_id):
                    await q.put(event)
                    if event.get("event_type") in ("done", "error"):
                        break
            except Exception as e:
                logger.warning(f"Redis subscriber error for {task_id}: {e}")
            finally:
                await q.put({"event_type": "__close__"})  # signal done

        q: asyncio.Queue = asyncio.Queue()
        heartbeat_task = asyncio.create_task(_heartbeat(q))
        sub_task = asyncio.create_task(_subscriber(q))

        try:
            # Safety timeout: max 30 min of streaming
            deadline = asyncio.get_event_loop().time() + 1800
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    yield _make_evt("error", 0, content="Stream timeout (30 min max).")
                    break
                try:
                    item = await asyncio.wait_for(q.get(), timeout=min(remaining, 20))
                except asyncio.TimeoutError:
                    # Shouldn't happen often since heartbeat fires every 15s,
                    # but re-check DB in case Redis missed the done event
                    try:
                        await db.refresh(task)
                        if task.status in TERMINAL_STATUSES:
                            if task.status == "completed":
                                yield _make_evt("done", 0, content=task.final_answer or "Done.")
                            else:
                                yield _make_evt("error", 0, content=task.error_message or task.status)
                            break
                    except Exception:
                        pass
                    yield ": heartbeat\n\n"
                    continue

                if item is None:
                    # Heartbeat tick
                    yield ": heartbeat\n\n"
                    continue

                if item.get("event_type") == "__close__":
                    # Subscriber finished; check DB for final state
                    try:
                        await db.refresh(task)
                    except Exception:
                        pass
                    if task.status == "completed":
                        yield _make_evt("done", 0, content=task.final_answer or "Done.")
                    elif task.status in TERMINAL_STATUSES:
                        yield _make_evt("error", 0, content=task.error_message or task.status)
                    break

                yield f"data: {json.dumps(item)}\n\n"

                if item.get("event_type") in ("done", "error"):
                    break

        except asyncio.CancelledError:
            logger.debug(f"SSE client disconnected for task {task_id}")
        finally:
            heartbeat_task.cancel()
            sub_task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/{task_id}/status")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    turn_count_result = await db.execute(
        select(func.count(AgentTurn.id)).where(AgentTurn.task_id == uuid.UUID(task_id))
    )
    turn_count = turn_count_result.scalar() or 0

    token_sum_result = await db.execute(
        select(func.sum(AgentTurn.tokens_used)).where(AgentTurn.task_id == uuid.UUID(task_id))
    )
    total_tokens = token_sum_result.scalar() or 0

    duration = None
    if task.completed_at and task.created_at:
        duration = (task.completed_at - task.created_at).total_seconds()

    return {
        "id": str(task.id),
        "description": task.description,
        "status": task.status,
        "turn_count": turn_count,
        "total_tokens": total_tokens,
        "duration_seconds": duration,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "final_answer": task.final_answer,
        "error_message": task.error_message,
    }


# ── Turns ─────────────────────────────────────────────────────────────────────

@router.get("/{task_id}/turns")
async def get_task_turns(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentTurn)
        .where(AgentTurn.task_id == uuid.UUID(task_id))
        .order_by(AgentTurn.turn_number)
    )
    turns = result.scalars().all()
    return [TurnOut.model_validate(t) for t in turns]


# ── Files ─────────────────────────────────────────────────────────────────────

@router.get("/{task_id}/files")
async def list_task_files(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OutputFile).where(OutputFile.task_id == uuid.UUID(task_id))
    )
    files = result.scalars().all()
    return [FileOut.model_validate(f) for f in files]


@router.get("/{task_id}/files/{filename}")
async def download_task_file(task_id: str, filename: str):
    from fastapi.responses import FileResponse
    from pathlib import Path
    from models.schemas import get_settings

    settings = get_settings()
    file_path = Path(settings.OUTPUT_DIR) / task_id / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    async_task = _running_tasks.get(task_id)
    if async_task and not async_task.done():
        async_task.cancel()
        return {"status": "cancellation requested"}

    # Update DB if task is still queued/running
    result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
    task = result.scalar_one_or_none()
    if task and task.status in ("queued", "running"):
        task.status = "cancelled"
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "cancelled"}

    return {"status": "not running"}


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task).order_by(Task.created_at.desc())

    if status:
        query = query.where(Task.status == status)
    if search:
        query = query.where(Task.description.ilike(f"%{search}%"))

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Get turn counts in batch
    task_ids = [t.id for t in tasks]
    turn_counts = {}
    if task_ids:
        count_result = await db.execute(
            select(AgentTurn.task_id, func.count(AgentTurn.id))
            .where(AgentTurn.task_id.in_(task_ids))
            .group_by(AgentTurn.task_id)
        )
        for row in count_result:
            turn_counts[row[0]] = row[1]

    items = []
    for t in tasks:
        duration = None
        if t.completed_at and t.created_at:
            duration = (t.completed_at - t.created_at).total_seconds()

        items.append({
            "id": str(t.id),
            "description": t.description[:200],
            "status": t.status,
            "turn_count": turn_counts.get(t.id, 0),
            "duration_seconds": duration,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })

    return {"items": items, "page": page, "page_size": page_size}


# ── Resume ────────────────────────────────────────────────────────────────────

@router.post("/{task_id}/resume")
async def resume_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Resume a stopped/failed task from where it left off."""
    result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "running":
        raise HTTPException(status_code=409, detail="Task is already running")

    # Reset status
    task.status = "queued"
    task.completed_at = None
    task.error_message = None
    await db.commit()

    config = HarnessConfig(**(task.config or {}))
    async_task = asyncio.create_task(
        _run_task(task_id, config),
        name=f"agent-{task_id}-resume",
    )
    _running_tasks[task_id] = async_task
    async_task.add_done_callback(lambda t: _running_tasks.pop(task_id, None))

    return {"task_id": task_id, "status": "resumed"}


# ── Debug endpoint ────────────────────────────────────────────────────────────

@router.get("/{task_id}/debug")
async def debug_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns full diagnostic info for a task.
    Hit this if a task shows 'not found' or produces no output.
    GET /api/v1/tasks/{id}/debug
    """
    result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in DB")

    turns_result = await db.execute(
        select(AgentTurn)
        .where(AgentTurn.task_id == uuid.UUID(task_id))
        .order_by(AgentTurn.turn_number)
    )
    turns = turns_result.scalars().all()

    return {
        "task": {
            "id": str(task.id),
            "status": task.status,
            "description": task.description,
            "config": task.config,
            "error_message": task.error_message,
            "final_answer": task.final_answer,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
        "turns": [
            {
                "turn_number": t.turn_number,
                "thought": t.thought,
                "tool_name": t.tool_name,
                "tool_args": t.tool_args,
                "tool_result": (t.tool_result or "")[:500],
                "tokens_used": t.tokens_used,
                "duration_ms": t.duration_ms,
            }
            for t in turns
        ],
        "is_running_in_memory": task_id in _running_tasks,
        "tip": (
            "If status=failed and error_message contains 'LLM error', "
            "check your GROQ_API_KEY and that the model name is correct. "
            "For gpt-oss-120b use provider=groq in the config."
        ),
    }