"""Celery 应用实例（设计文档 §7.1）。

Worker 启动：celery -A app.celery worker --loglevel=info
backend/celery_app.py 是它的兼容出口，保持设计文档 §12 的引用方式可用。
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "researchpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.smoke"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    # 单任务硬超时兜底（编排器内有更细的预算控制）
    task_time_limit=settings.task_time_limit + 60,
    task_soft_time_limit=settings.task_time_limit,
    worker_prefetch_multiplier=1,  # 长任务公平分发
)

# P0 mock 模式：不依赖 Redis broker，任务在调用进程内联执行（演示/冒烟用）。
# M1 接入真实流水线时置 MOCK_PIPELINE=false，恢复经 broker 派发给 worker。
if settings.mock_pipeline:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
