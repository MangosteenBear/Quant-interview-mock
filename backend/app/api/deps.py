"""
FastAPI 依赖注入
"""
from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    """注入数据库会话"""
    yield session


def get_pagination(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
):
    """分页参数依赖"""
    return {"page": page, "page_size": page_size, "offset": (page - 1) * page_size}
