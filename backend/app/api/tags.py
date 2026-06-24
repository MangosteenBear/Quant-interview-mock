"""
标签接口模块
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models import Tag
from app.schemas.question import TagBrief

router = APIRouter(prefix="/api/tags", tags=["标签"])


@router.get("", response_model=list[TagBrief], summary="标签列表")
async def list_tags(
    type: str | None = Query(None, description="按类型筛选: knowledge/position/topic"),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Tag).order_by(Tag.type, Tag.id)
    if type:
        stmt = stmt.where(Tag.type == type)
    result = await db.execute(stmt)
    return result.scalars().all()
