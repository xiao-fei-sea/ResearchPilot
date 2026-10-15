"""数据库连接层：engine + Session 工厂。

同步 SQLAlchemy（与 Celery worker 同风格，简单一致）；
FastAPI 侧通过 get_db 依赖注入，Celery 侧直接用 session_scope。
"""
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger("app.db")

_engine = None
_SessionLocal = None


def get_engine():
    """惰性创建全局 engine（延迟到首次使用，便于测试覆盖配置）。"""
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,   # 取连接前探活，避免 MySQL 长连接断开
            pool_recycle=3600,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
        logger.info("engine created", extra={"dialect": _engine.dialect.name})
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db():
    """FastAPI 依赖：请求级会话。"""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Session:
    """Celery/脚本用：代码块结束自动 commit，异常回滚。"""
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reset_engine() -> None:
    """测试钩子：清空全局单例，让下一次 get_engine 用新配置。"""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
