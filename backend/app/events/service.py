"""事件服务。

双通道设计（设计文档 §6.2）：
- 落库 event_log：断线重连时按 Last-Event-ID 回放；
- Redis Pub/Sub：在线客户端实时收到。

注意：先 flush 拿到 id 再发布（payload 自包含），事务最终回滚时
可能出现“幽灵事件”，前端以任务状态接口为准，可容忍。
"""
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import EventLog
from app.redis_client import get_redis

logger = logging.getLogger("app.events")


def task_channel(task_id: int) -> str:
    return f"research:{task_id}:events"


def emit_event(
    db: Session,
    task_id: int,
    type: str,
    payload: dict[str, Any] | None = None,
    level: str = "info",
    stage_run_id: int | None = None,
) -> int:
    """写一条事件并实时发布，返回事件 id（即 SSE 游标）。"""
    event = EventLog(
        task_id=task_id,
        stage_run_id=stage_run_id,
        type=type,
        level=level,
        payload=payload or {},
    )
    db.add(event)
    db.flush()  # 拿到自增 id，作为 SSE 游标

    message = {
        "id": event.id,
        "task_id": task_id,
        "type": type,
        "level": level,
        "stage_run_id": stage_run_id,
        "payload": payload or {},
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        get_redis().publish(task_channel(task_id), json.dumps(message, ensure_ascii=False))
    except Exception:  # 发布失败不影响主流程，事件已落库可回放
        logger.exception("publish event failed", extra={"task_id": task_id, "event_id": event.id})
    return event.id
