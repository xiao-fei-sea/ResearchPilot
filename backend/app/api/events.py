"""SSE 事件流端点（设计文档 §6.2）。

- 优先订阅 Pub/Sub，再回放 event_log（游标去重），避免订阅空窗丢事件；
- 客户端断线重连带 Last-Event-ID 头，可从头补齐缺口；
- 收到 done / error 事件或超时后关闭连接；空闲期发心跳注释保活。
"""
import json
import logging
import time

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db, get_session_factory
from app.events import task_channel
from app.models import EventLog
from app.redis_client import get_redis

logger = logging.getLogger("app.api.events")

router = APIRouter(prefix="/api/research", tags=["events"])

HEARTBEAT_INTERVAL = 15.0  # 秒
MAX_STREAM_SECONDS = 1200  # 与任务时长上限（task_time_limit）对齐留裕量


def _format_sse(event_id: int, event_type: str, data: dict) -> str:
    return (
        f"id: {event_id}\n"
        f"event: {event_type}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


def _event_payload(row: EventLog) -> dict:
    return {
        "id": row.id,
        "task_id": row.task_id,
        "type": row.type,
        "level": row.level.value,
        "stage_run_id": row.stage_run_id,
        "payload": row.payload,
        "ts": row.ts.isoformat() if row.ts else None,
    }


def _stream(task_id: int, cursor: int):
    """生成器：回放 + 实时订阅（在线程池中运行）。"""
    redis_client = get_redis()
    try:
        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(task_channel(task_id))
    except Exception:
        # Redis 不可用：降级为仅回放（事件已落库，补发 cursor 之后的全部）
        logger.exception("pubsub unavailable, fallback to replay-only")
        pubsub = None
    try:
        # 1) 回放：补发 cursor 之后已落库的事件
        with get_session_factory()() as db:
            rows = db.scalars(
                select(EventLog)
                .where(EventLog.task_id == task_id, EventLog.id > cursor)
                .order_by(EventLog.id)
            ).all()
            for row in rows:
                cursor = max(cursor, row.id)
                yield _format_sse(row.id, row.type, _event_payload(row))
                if row.type in ("done", "error"):
                    return
            # 无实时通道时：任务未结束则保持短轮询回放（间隔 2s），直到出现终态
            if pubsub is None:
                while time.monotonic() < time.monotonic() + MAX_STREAM_SECONDS:
                    time.sleep(2)
                    db.expire_all()
                    rows = db.scalars(
                        select(EventLog)
                        .where(EventLog.task_id == task_id, EventLog.id > cursor)
                        .order_by(EventLog.id)
                    ).all()
                    for row in rows:
                        cursor = max(cursor, row.id)
                        yield _format_sse(row.id, row.type, _event_payload(row))
                        if row.type in ("done", "error"):
                            return

        # 2) 实时：Pub/Sub 推送，空闲发心跳
        deadline = time.monotonic() + MAX_STREAM_SECONDS
        last_beat = time.monotonic()
        while pubsub is not None and time.monotonic() < deadline:
            message = pubsub.get_message(timeout=1.0)
            if message is None:
                if time.monotonic() - last_beat > HEARTBEAT_INTERVAL:
                    last_beat = time.monotonic()
                    yield ": ping\n\n"
                continue
            data = json.loads(message["data"])
            if data["id"] <= cursor:
                continue  # 回放已覆盖
            cursor = data["id"]
            last_beat = time.monotonic()
            yield _format_sse(data["id"], data["type"], data)
            if data["type"] in ("done", "error"):
                return
        yield _format_sse(0, "warn", {"message": "stream timeout", "task_id": task_id})
    finally:
        if pubsub is not None:
            pubsub.close()


@router.get("/{task_id}/events")
def stream_events(
    task_id: int,
    last_event_id: int | None = Header(default=None, alias="Last-Event-ID"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    from app.models import ResearchTask

    if db.get(ResearchTask, task_id) is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="task not found")

    return StreamingResponse(
        _stream(task_id, last_event_id or 0),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
