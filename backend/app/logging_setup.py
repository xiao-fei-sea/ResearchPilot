"""结构化日志（设计文档 §10 可观测性）。

统一输出 JSON，一行一条；业务代码用 ``logger.info("...", extra={"task_id": ...})``
即可把 task_id / stage 等上下文字段带进日志，便于按任务检索。
"""
import json
import logging
from datetime import datetime, timedelta, timezone

# 日志时间统一用东八区
_CST = timezone(timedelta(hours=8))

# LogRecord 自带的属性不进 JSON，其余 extra 字段全保留
_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(_CST).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(environment: str = "dev") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if environment == "dev" else logging.INFO)
    # 三方库降噪
    for noisy in ("uvicorn.access", "celery.app.trace", "celery.worker.consumer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
