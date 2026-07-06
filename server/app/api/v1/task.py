from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.task import Task

router = APIRouter()


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_device_ids: List  # [1, 2, 3] or ["all"]
    config: Optional[dict] = None
    scheduled_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    target_device_ids: Optional[List]
    config: Optional[dict]
    status: str
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


@router.create("", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    db_task = Task(**task.model_dump(), created_by=user.get("sub"))
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.get("/list", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}/dispatch")
async def dispatch_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Task already dispatched")

    task.status = "dispatched"
    task.started_at = datetime.utcnow()
    db.commit()
    # TODO: Notify devices via WebSocket or message queue
    return {"status": "dispatched", "task_id": task_id}
