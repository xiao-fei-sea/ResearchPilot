"""任务相关 Pydantic 模型（API 输入输出契约）。"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskStatus


class TaskCreate(BaseModel):
    topic: str = Field(min_length=2, description="研究主题")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="可选参数：depth/language/time_range/length（设计文档 §4.1）",
    )


class TaskCreated(BaseModel):
    task_id: int
    status: TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    status: TaskStatus
    params: dict[str, Any]
    budget: dict[str, Any]
    stats: dict[str, Any]
    created_at: datetime


class TaskListOut(BaseModel):
    items: list[TaskOut]
    total: int
