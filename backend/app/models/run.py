"""执行记录模型：stage_run / event_log（驱动前端时间线与 SSE 回放）。"""
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK
from app.models.enums import EventLevel, StageName, StageStatus


class StageRun(Base):
    """一次阶段执行（含重试，每次 attempt 一行）。"""

    __tablename__ = "stage_run"
    __table_args__ = (Index("ix_stage_run_task_stage", "task_id", "stage"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("research_task.id"), nullable=False, index=True
    )
    stage: Mapped[StageName] = mapped_column(nullable=False)
    status: Mapped[StageStatus] = mapped_column(default=StageStatus.running, nullable=False
    )
    attempt: Mapped[int] = mapped_column(default=1, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    llm_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    task = relationship("ResearchTask", back_populates="stage_runs")
    events: Mapped[list["EventLog"]] = relationship(back_populates="stage_run")


class EventLog(Base):
    """事件流：落库（回放）+ Redis Pub/Sub（实时推送）。"""

    __tablename__ = "event_log"
    # SSE 按 (task_id, id) 增量回放，id 即游标
    __table_args__ = (Index("ix_event_task_id", "task_id", "id"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("research_task.id"), nullable=False, index=True
    )
    stage_run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stage_run.id"), nullable=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    level: Mapped[EventLevel] = mapped_column(default=EventLevel.info)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    stage_run: Mapped[StageRun | None] = relationship(back_populates="events")
