"""
数据库引擎与会话管理
SQLAlchemy 2.0 异步模式，开发用 SQLite (aiosqlite)，生产切 PostgreSQL (asyncpg)
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 异步引擎
# echo=False 关闭 SQL 日志（调试时可改 True）
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

# 异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有模型的基类"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖：注入异步数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """创建所有表（开发环境用，生产用 Alembic 迁移）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
