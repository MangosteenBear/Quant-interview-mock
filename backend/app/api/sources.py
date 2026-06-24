"""
来源接口模块
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models import Source
from app.schemas.question import SourceBrief

router = APIRouter(prefix="/api/sources", tags=["来源"])


@router.get("", response_model=list[SourceBrief], summary="来源书目列表")
async def list_sources(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Source).order_by(Source.id))
    return result.scalars().all()
