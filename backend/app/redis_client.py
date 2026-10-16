"""Redis 连接（SSE 实时推送 / 去重指纹 / 缓存共用）。惰性单例，便于测试替换。"""
import redis

from app.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            # 短超时：Redis 不可用时发布/缓存操作快速失败，
            # 由调用方降级（事件已落库可回放，缓存未命中走 DB）
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


def reset_redis() -> None:
    """测试钩子。"""
    global _client
    _client = None
