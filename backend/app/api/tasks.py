"""研究任务 REST 接口（P0 冒烟版；M1 起扩展 plan/sources/claims 等）。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.events import emit_event
from app.models import ResearchTask, TaskStatus
from app.schemas.task import TaskCreate, TaskListOut, TaskOut

logger = logging.getLogger("app.api.tasks")
router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("", status_code=202, response_model=None)
def create_task(body: TaskCreate, db: Session = Depends(get_db)) -> dict:
    """创建研究任务并派发流水线（P0：mock 冒烟流水线）。"""
    settings = get_settings()
    if not settings.mock_pipeline:
        # 真实流水线在 M1 落地；此分支保证配置误开时不静默丢任务
        raise HTTPException(status_code=501, detail="real pipeline arrives in M1")

    task = ResearchTask(
        topic=body.topic.strip(),
        params=body.params,
        budget={
            "max_sources": settings.max_sources,
            "max_rounds": settings.max_rounds,
            "task_time_limit": settings.task_time_limit,
        },
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info("task created", extra={"task_id": task.id})

    emit_event(db, task.id, "task.created", {"message": "任务已创建", "topic": task.topic})
    db.commit()  # 事件先落库，再派发（worker 独立进程时也依赖数据已持久化）
    # 用任务对象派发而非 send_task 按名派发：
    # 1) 与实现解耦不如可测试性重要（eager 模式仅对象调用生效）；
    # 2) M1 起此处改为 Orchestrator 统一派发。
    from app.tasks.smoke import run_smoke_pipeline

    run_smoke_pipeline.apply_async(args=[task.id])
    return {"task_id": task.id, "status": task.status.value}


@router.get("", response_model=TaskListOut)
def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> TaskListOut:
    total = db.scalar(select(func.count()).select_from(ResearchTask)) or 0
    stmt = (
        select(ResearchTask)
        .order_by(ResearchTask.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = db.scalars(stmt).all()
    return TaskListOut(items=[TaskOut.model_validate(t) for t in items], total=total)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskOut:
    task = db.get(ResearchTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskOut.model_validate(task)


@router.post("/{task_id}/cancel", response_model=None)
def cancel_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    """取消：置状态即可，worker 在阶段边界检查点响应（设计文档 §7.3）。"""
    task = db.get(ResearchTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status in (TaskStatus.done, TaskStatus.failed, TaskStatus.cancelled):
        return {"task_id": task.id, "status": task.status.value}
    task.status = TaskStatus.cancelled
    emit_event(db, task.id, "warn", {"message": "任务已取消，将在当前阶段边界停止"}, level="warn")
    db.commit()
    return {"task_id": task.id, "status": task.status.value}
