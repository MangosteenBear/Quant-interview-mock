"""
用户接口：当前用户信息、历史数据绑定
"""
from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import AttemptLog, Favorite, User
from app.schemas.auth import BindDeviceRequest, BindDeviceResponse, UserOut

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserOut, summary="当前用户信息")
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/me/bind-device", response_model=BindDeviceResponse, summary="绑定设备历史记录到账号")
async def bind_device(
    body: BindDeviceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    r1 = await db.execute(
        update(AttemptLog)
        .where(AttemptLog.device_id == body.device_id, AttemptLog.user_id.is_(None))
        .values(user_id=user.id)
    )
    r2 = await db.execute(
        update(Favorite)
        .where(Favorite.device_id == body.device_id, Favorite.user_id.is_(None))
        .values(user_id=user.id)
    )
    await db.commit()
    return BindDeviceResponse(
        migrated_attempts=r1.rowcount or 0,
        migrated_favorites=r2.rowcount or 0,
    )


# ---------- M3 学习闭环 ----------
from datetime import date, datetime, timedelta

from fastapi import HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import selectinload

from app.models import AttemptLog, Question
from app.api.deps import get_current_user_optional
from app.schemas.question import QuestionListItem


class UpdateMeRequest(BaseModel):
    nickname: str | None = None
    avatar_url: str | None = None


@router.patch("/me", response_model=UserOut, summary="更新个人资料")
async def update_me(
    body: UpdateMeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if body.nickname is not None:
        nickname = body.nickname.strip()
        if not 1 <= len(nickname) <= 20:
            raise HTTPException(400, "昵称长度需在 1-20 字之间")
        user.nickname = nickname
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    await db.commit()
    await db.refresh(user)
    return user


def _identity_filter(user, device_id: str | None):
    """登录用 user_id，匿名用 device_id"""
    if user:
        return AttemptLog.user_id == user.id
    if device_id:
        return AttemptLog.device_id == device_id
    raise HTTPException(401, "需登录或提供 device_id")


class StatsResponse(BaseModel):
    total_attempts: int
    attempted_questions: int
    correct_rate: float | None  # 仅统计可自动判分的题
    today_count: int
    streak_days: int
    by_type: dict[str, int]  # 各题型已做题数（去重）


@router.get("/me/stats", response_model=StatsResponse, summary="学习进度统计")
async def get_stats(
    device_id: str | None = Query(None),
    user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_session),
):
    ident = _identity_filter(user, device_id)

    total = (await db.execute(
        select(func.count()).select_from(AttemptLog).where(ident)
    )).scalar_one()

    attempted = (await db.execute(
        select(func.count(func.distinct(AttemptLog.question_id))).where(ident)
    )).scalar_one()

    judged, correct = (await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(func.cast(AttemptLog.is_correct, Integer)), 0),
        ).where(ident, AttemptLog.is_correct.is_not(None))
    )).one()

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_count = (await db.execute(
        select(func.count()).select_from(AttemptLog)
        .where(ident, AttemptLog.created_at >= today_start)
    )).scalar_one()

    # streak：取最近 366 个有作答的自然日，从今天/昨天往回数连续天数
    days = (await db.execute(
        select(func.date(AttemptLog.created_at).label("d"))
        .where(ident).group_by("d").order_by(func.date(AttemptLog.created_at).desc())
        .limit(366)
    )).scalars().all()
    day_set = {d if isinstance(d, date) else date.fromisoformat(str(d)) for d in days}
    streak = 0
    cursor = date.today()
    if cursor not in day_set:
        cursor -= timedelta(days=1)  # 今天还没做题，从昨天起算
    while cursor in day_set:
        streak += 1
        cursor -= timedelta(days=1)

    by_type_rows = (await db.execute(
        select(Question.question_type, func.count(func.distinct(AttemptLog.question_id)))
        .join(Question, Question.id == AttemptLog.question_id)
        .where(ident)
        .group_by(Question.question_type)
    )).all()

    return StatsResponse(
        total_attempts=total,
        attempted_questions=attempted,
        correct_rate=round(correct / judged, 4) if judged else None,
        today_count=today_count,
        streak_days=streak,
        by_type={t: c for t, c in by_type_rows},
    )


class WrongQuestionItem(BaseModel):
    question: QuestionListItem
    last_wrong_at: datetime
    wrong_count: int


@router.get("/me/wrong-questions", summary="错题本（每题以最近一次作答为准）")
async def wrong_questions(
    device_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_session),
):
    ident = _identity_filter(user, device_id)

    # 每题最近一次作答
    rn = func.row_number().over(
        partition_by=AttemptLog.question_id,
        order_by=[AttemptLog.created_at.desc(), AttemptLog.id.desc()],
    ).label("rn")
    latest = (
        select(AttemptLog.question_id, AttemptLog.is_correct, AttemptLog.created_at, rn)
        .where(ident)
        .subquery()
    )
    rows = (await db.execute(
        select(latest.c.question_id, latest.c.created_at)
        .where(latest.c.rn == 1, latest.c.is_correct == False)  # noqa: E712
        .order_by(latest.c.created_at.desc())
        .limit(limit)
    )).all()
    if not rows:
        return {"items": [], "total": 0}

    qids = [r[0] for r in rows]
    wrong_at = {r[0]: r[1] for r in rows}

    # 每题累计错误次数
    counts = dict((await db.execute(
        select(AttemptLog.question_id, func.count())
        .where(ident, AttemptLog.is_correct == False, AttemptLog.question_id.in_(qids))  # noqa: E712
        .group_by(AttemptLog.question_id)
    )).all())

    questions = (await db.execute(
        select(Question)
        .options(selectinload(Question.source), selectinload(Question.tags))
        .where(Question.id.in_(qids))
    )).scalars().all()
    qmap = {q.id: q for q in questions}

    items = [
        WrongQuestionItem(
            question=QuestionListItem.model_validate(qmap[qid], from_attributes=True),
            last_wrong_at=wrong_at[qid],
            wrong_count=counts.get(qid, 1),
        )
        for qid in qids if qid in qmap
    ]
    return {"items": items, "total": len(items)}
