from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

_engine_kwargs = {}
if settings.DATABASE_URL.startswith("postgresql"):
    if settings.SERVERLESS:
        # Vercel serverless：每次 invocation 独立进程，不能复用连接
        _engine_kwargs["poolclass"] = NullPool
    else:
        # 长驻进程（本地开发 / 服务器）：连接池复用，大幅降低延迟
        _engine_kwargs["pool_size"] = 5
        _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    **_engine_kwargs,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
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
    """开发环境建表；生产环境通过 Alembic 管理，此函数跳过"""
    if settings.DATABASE_URL.startswith("postgresql"):
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
