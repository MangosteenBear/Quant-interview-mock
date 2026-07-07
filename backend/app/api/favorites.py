"""
收藏接口模块
"""
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_session, get_pagination, get_current_user_optional
from app.models import Favorite, Question
from app.schemas.common import PageResponse
from app.schemas.question import QuestionListItem, FavoriteRequest, FavoriteResponse

router = APIRouter(prefix="/api/favorites", tags=["收藏"])


@router.post("", response_model=FavoriteResponse, summary="切换收藏（已收藏则取消，未收藏则添加）")
async def toggle_favorite(
    body: FavoriteRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    # 确认题目存在
    exists = (await db.execute(
        select(Question.id).where(Question.id == body.question_id)
    )).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail=f"题目 {body.question_id} 不存在")

    # 查是否已收藏
    existing = (await db.execute(
        select(Favorite).where(
            Favorite.device_id == body.device_id,
            Favorite.question_id == body.question_id,
        )
    )).scalar_one_or_none()

    if existing:
        # 已收藏 → 取消
        await db.delete(existing)
        return FavoriteResponse(favorited=False, question_id=body.question_id)
    else:
        # 未收藏 → 添加
        fav = Favorite(device_id=body.device_id, question_id=body.question_id, user_id=current_user.id if current_user else None)
        db.add(fav)
        return FavoriteResponse(favorited=True, question_id=body.question_id)


@router.get("", response_model=PageResponse[QuestionListItem], summary="收藏列表")
async def list_favorites(
    device_id: str = Query(..., description="设备标识"),
    db: AsyncSession = Depends(get_session),
    pagination: dict = Depends(get_pagination),
):
    # 查该设备收藏的题目
    count_stmt = (
        select(func.count())
        .select_from(Favorite)
        .join(Question, Favorite.question_id == Question.id)
        .where(Favorite.device_id == device_id, Question.status == "published")
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Question)
        .join(Favorite, Favorite.question_id == Question.id)
        .options(selectinload(Question.source), selectinload(Question.tags))
        .where(Favorite.device_id == device_id, Question.status == "published")
        .order_by(Favorite.created_at.desc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
    )
    items = (await db.execute(stmt)).scalars().all()

    return PageResponse(
        items=items,
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=math.ceil(total / pagination["page_size"]) if total > 0 else 0,
    )
