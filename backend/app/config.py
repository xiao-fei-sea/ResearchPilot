"""全局配置（P0-1.4）。

所有可变项集中在这里，读取优先级：环境变量 > .env 文件 > 代码默认值。
设计文档 §11/§12：DB/Redis/LLM/搜索/预算全部配置化，不硬编码。
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- 基础 ---
    app_name: str = "ResearchPilot"
    environment: str = "dev"  # dev / prod
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- 数据层 ---
    database_url: str = (
        "mysql+pymysql://researchpilot:researchpilot@localhost:3306/researchpilot?charset=utf8mb4"
    )
    redis_url: str = "redis://localhost:6379/0"

    # --- LLM（OpenAI 兼容接口，分级用模型，见设计文档 §9.1）---
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_strong_model: str = ""
    llm_small_model: str = ""

    # --- 搜索（适配层可插拔，见设计文档 §3.3）---
    search_provider: str = "tavily"  # tavily / serper / searxng
    tavily_api_key: str = ""
    serper_api_key: str = ""
    searxng_base_url: str = ""

    # --- 预算（设计文档 §7.2，触顶行为见 orchestrator）---
    max_sources: int = 60
    max_rounds: int = 2
    task_time_limit: int = 900  # 任务总时长上限（秒）


@lru_cache
def get_settings() -> Settings:
    """进程内单例；测试中可用 get_settings.cache_clear() 重置。"""
    return Settings()
