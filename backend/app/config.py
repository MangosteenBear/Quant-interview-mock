"""
应用配置模块
使用 pydantic-settings 管理环境变量，支持 .env 文件覆盖
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，可通过环境变量或 .env 文件覆盖"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用基础信息
    APP_NAME: str = "量化面试刷题题库平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库
    # 开发: sqlite+aiosqlite:///./quantquiz.db
    # 生产: postgresql+asyncpg://user:pass@host:5432/dbname
    DATABASE_URL: str = "sqlite+aiosqlite:///./quantquiz.db"

    # CORS 跨域（前端域名，生产环境需收紧）
    CORS_ORIGINS: list[str] = ["*"]

    # 分页默认值
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


# 全局单例
settings = Settings()
