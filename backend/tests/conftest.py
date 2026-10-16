"""pytest 公共夹具：独立 SQLite + Celery eager + 隔离 Redis。

每个测试拿到干净的数据库与配置，互不影响本机开发环境。
"""
import pytest


@pytest.fixture()
def test_env(tmp_path, monkeypatch):
    # 1) 隔离配置：独立 sqlite 文件 + 不可达的 redis（发布失败会被 emit_event 容忍）
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6399/0")
    monkeypatch.setenv("MOCK_PIPELINE", "true")

    from app.config import get_settings

    get_settings.cache_clear()

    from app.db import reset_engine
    from app.redis_client import reset_redis

    reset_engine()
    reset_redis()

    # 2) Celery eager：任务在本进程内联执行，不经 broker
    from app.celery import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    # 3) 按模型建表（等价于 alembic upgrade head 的测试态）
    from app.db import get_engine
    from app.models import Base

    Base.metadata.create_all(get_engine())

    # 4) 模拟流水线不做真实 sleep，加速测试
    monkeypatch.setattr("app.tasks.smoke.time.sleep", lambda s: None)

    yield

    get_settings.cache_clear()
    reset_engine()
    reset_redis()


@pytest.fixture()
def client(test_env):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
