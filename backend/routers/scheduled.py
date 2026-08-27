"""Scheduled tasks router."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import ScheduledTask, get_db
from models.schemas import ScheduledTaskCreate, ScheduledTaskOut, ScheduledTaskUpdate

router = APIRouter(prefix="/api/v1/scheduled", tags=["scheduled"])


def _next_run_placeholder(cron: str) -> str:
    """Placeholder — in production use APScheduler or croniter."""
    return "Next run calculated by scheduler"


@router.post("", response_model=ScheduledTaskOut)
async def create_scheduled_task(
    payload: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_db),
):
    task = ScheduledTask(
        cron_expression=payload.cron_expression,
        task_description=payload.task_description,
        is_active=True,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return ScheduledTaskOut.model_validate(task)


@router.get("", response_model=list[ScheduledTaskOut])
async def list_scheduled_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScheduledTask).order_by(ScheduledTask.created_at.desc())
    )
    tasks = result.scalars().all()
    return [ScheduledTaskOut.model_validate(t) for t in tasks]


@router.patch("/{task_id}", response_model=ScheduledTaskOut)
async def update_scheduled_task(
    task_id: str,
    payload: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    if payload.is_active is not None:
        task.is_active = payload.is_active
    if payload.cron_expression:
        task.cron_expression = payload.cron_expression
    if payload.task_description:
        task.task_description = payload.task_description

    await db.commit()
    await db.refresh(task)
    return ScheduledTaskOut.model_validate(task)


@router.delete("/{task_id}")
async def delete_scheduled_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    await db.delete(task)
    await db.commit()
    return {"status": "deleted"}
