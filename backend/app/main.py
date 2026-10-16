"""FastAPI 入口（P0-1.1，P0-3 挂载路由）。

路由：/api/research 任务 CRUD、/api/research/{id}/events SSE 事件流；
后续里程碑按 plan.md 扩展 plan/sources/claims/export 等。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import events as events_router
from app.api import tasks as tasks_router
from app.config import get_settings
from app.logging_setup import setup_logging

logger = logging.getLogger("app")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.environment)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("api startup", extra={"environment": settings.environment})
        yield
        logger.info("api shutdown")

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(tasks_router.router)
    app.include_router(events_router.router)

    @app.get("/health")
    def health() -> dict:
        """深度健康检查：DB 与 Redis 可达性。"""
        db_ok = redis_ok = False
        try:
            from sqlalchemy import text

            from app.db import get_engine

            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            logger.exception("health: db check failed")
        try:
            from app.redis_client import get_redis

            redis_ok = bool(get_redis().ping())
        except Exception:
            logger.exception("health: redis check failed")
        return {
            "status": "ok" if (db_ok and redis_ok) else "degraded",
            "environment": settings.environment,
            "db": db_ok,
            "redis": redis_ok,
        }

    return app


app = create_app()
