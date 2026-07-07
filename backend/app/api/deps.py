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


from fastapi import Header  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.models import User  # noqa: E402
from app.utils.security import decode_token  # noqa: E402


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """必须登录，Header: Authorization: Bearer <token>"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    user_id = decode_token(authorization[7:], expect_type="access")
    if user_id is None:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_current_user_optional(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """可选登录，匿名返回 None"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    user_id = decode_token(authorization[7:], expect_type="access")
    if user_id is None:
        return None
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
