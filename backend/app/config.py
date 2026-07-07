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

    # 开发: sqlite+aiosqlite:///./quantquiz.db
    # 生产(Supabase Transaction Pooler): postgresql+asyncpg://postgres.[ref]:[pwd]@[host]:6543/postgres
    DATABASE_URL: str = "sqlite+aiosqlite:///./quantquiz.db"

    # 生产环境通过 CORS_ORIGINS 环境变量传入前端域名（逗号分隔）
    # 例: CORS_ORIGINS="https://quantquiz.vercel.app"
    CORS_ORIGINS: list[str] = ["*"]

    # True = Vercel serverless 模式（用 NullPool），False = 长驻进程（用连接池）
    SERVERLESS: bool = False

    # JWT（生产必须在 .env 覆盖 JWT_SECRET）
    JWT_SECRET: str = "dev-secret-change-me"
    ACCESS_TOKEN_DAYS: int = 7
    REFRESH_TOKEN_DAYS: int = 30

    # 短信 Provider: dev = 验证码写日志且随响应返回（内测）；tencent = 腾讯云短信（备案后接入）
    SMS_PROVIDER: str = "dev"

    # 分页默认值
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


# 全局单例
settings = Settings()
