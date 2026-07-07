"""
标签接口模块
"""
import time
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models import Tag
from app.schemas.question import TagBrief

router = APIRouter(prefix="/api/tags", tags=["标签"])

_tags_cache: dict[str, tuple[list, float]] = {}
_CACHE_TTL = 300.0  # 5 分钟


@router.get("", response_model=list[TagBrief], summary="标签列表")
async def list_tags(
    type: str | None = Query(None, description="按类型筛选: knowledge/position/topic"),
    db: AsyncSession = Depends(get_session),
):
    cache_key = type or "__all__"
    cached = _tags_cache.get(cache_key)
    if cached is not None and time.monotonic() - cached[1] < _CACHE_TTL:
        return cached[0]
    stmt = select(Tag).order_by(Tag.type, Tag.id)
    if type:
        stmt = stmt.where(Tag.type == type)
    result = await db.execute(stmt)
    data = result.scalars().all()
    _tags_cache[cache_key] = (data, time.monotonic())
    return data


@router.get("/topic-stats", summary="知识点标签题目数统计")
async def topic_tag_stats(
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import func
    from app.models import question_tags, Question
    stmt = (
        select(Tag.id, Tag.name, func.count(question_tags.c.question_id).label("count"))
        .join(question_tags, Tag.id == question_tags.c.tag_id)
        .join(Question, Question.id == question_tags.c.question_id)
        .where(Tag.type == "topic", Question.status == "published")
        .group_by(Tag.id)
        .order_by(func.count(question_tags.c.question_id).desc())
    )
    rows = (await db.execute(stmt)).all()
    return [{"id": r.id, "name": r.name, "count": r.count} for r in rows]
