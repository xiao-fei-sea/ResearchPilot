"""兼容出口：保持设计文档 §12 中 `backend/celery_app.py` 的引用方式。"""
from app.celery import celery_app

__all__ = ["celery_app"]
