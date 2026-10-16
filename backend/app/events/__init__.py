"""事件模块：event_log 落库 + Redis Pub/Sub 实时推送（设计文档 §6.2）。"""
from app.events.service import emit_event, task_channel

__all__ = ["emit_event", "task_channel"]
