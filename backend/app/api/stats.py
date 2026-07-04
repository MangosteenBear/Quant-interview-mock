"""
统计接口：按题型、难度聚合作答记录（设备维度）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models import AttemptLog, Question

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("", summary="做题统计")
async def get_stats(
    device_id: str = Query(..., description="设备 ID"),
    db: AsyncSession = Depends(get_session),
):
    # 每道题只取最近一次作答（去重）
    # 用子查询：per question_id, 取 max(id) 的那条记录
    latest_ids = (
        select(func.max(AttemptLog.id).label("id"))
        .where(AttemptLog.device_id == device_id)
        .group_by(AttemptLog.question_id)
        .subquery()
    )
    latest = (
        select(AttemptLog.question_id, AttemptLog.is_correct)
        .join(latest_ids, AttemptLog.id == latest_ids.c.id)
        .subquery()
    )

    # Join with Question to get type & difficulty
    rows = (await db.execute(
        select(
            Question.question_type,
            Question.difficulty,
            latest.c.is_correct,
            func.count().label("cnt"),
        )
        .join(latest, Question.id == latest.c.question_id)
        .group_by(Question.question_type, Question.difficulty, latest.c.is_correct)
    )).all()

    by_type: dict = {}
    by_diff: dict = {}

    for row in rows:
        qt, diff, correct, cnt = row.question_type, row.difficulty, row.is_correct, row.cnt

        # By type
        if qt not in by_type:
            by_type[qt] = {"total": 0, "correct": 0}
        by_type[qt]["total"] += cnt
        if correct is True:
            by_type[qt]["correct"] += cnt

        # By difficulty (skip None)
        if diff is not None:
            k = str(diff)
            if k not in by_diff:
                by_diff[k] = {"total": 0, "correct": 0}
            by_diff[k]["total"] += cnt
            if correct is True:
                by_diff[k]["correct"] += cnt

    return {"by_type": by_type, "by_diff": by_diff}
