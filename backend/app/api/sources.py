"""
来源接口模块
"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models import Source
from app.schemas.question import SourceBrief

router = APIRouter(prefix="/api/sources", tags=["来源"])

_sources_cache: list | None = None
_sources_cache_at: float = 0.0
_CACHE_TTL = 300.0  # 5 分钟


@router.get("", response_model=list[SourceBrief], summary="来源书目列表")
async def list_sources(db: AsyncSession = Depends(get_session)):
    global _sources_cache, _sources_cache_at
    if _sources_cache is not None and time.monotonic() - _sources_cache_at < _CACHE_TTL:
        return _sources_cache
    result = await db.execute(select(Source).order_by(Source.id))
    _sources_cache = result.scalars().all()
    _sources_cache_at = time.monotonic()
    return _sources_cache
