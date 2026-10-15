"""FastAPI 入口（P0-1.1）。

P0 阶段只有 /health；随里程碑推进逐步挂载
/api/research、/api/research/{id}/events(SSE)、导出等路由（见 plan.md）。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
