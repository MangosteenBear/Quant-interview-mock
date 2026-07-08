"""
模考接口（轻量版）
choice/fill 题自动判分；start 抽题 → 前端顺序作答 → submit 出成绩报告
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user_optional, get_session
from app.models import AttemptLog, ExamSession, Question, Tag, question_tags
from app.utils.answer_match import format_fill_answer, judge_choice, judge_fill

router = APIRouter(prefix="/api/exam", tags=["模考"])

EXAM_TYPES = {"choice", "fill", "mixed"}


class ExamStartRequest(BaseModel):
    device_id: str
    count: int = Field(10, ge=5, le=50)
    question_type: str = "mixed"  # choice / fill / mixed
    tag_name: str | None = None
    difficulty: int | None = Field(None, ge=1, le=5)
    time_limit_sec: int | None = Field(None, ge=60, le=7200)


class ExamAnswer(BaseModel):
    question_id: int
    answer: str


class ExamSubmitRequest(BaseModel):
    device_id: str
    answers: list[ExamAnswer]
    duration_sec: int | None = None


@router.post("/start", summary="开始模考（随机抽题）")
async def start_exam(
    body: ExamStartRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    if body.question_type not in EXAM_TYPES:
        raise HTTPException(400, "题型仅支持 choice / fill / mixed")

    stmt = select(Question.id).where(Question.status == "published")
    if body.question_type == "mixed":
        stmt = stmt.where(Question.question_type.in_(["choice", "fill"]))
    else:
        stmt = stmt.where(Question.question_type == body.question_type)
    if body.difficulty:
        stmt = stmt.where(Question.difficulty == body.difficulty)
    if body.tag_name:
        tagged = (
            select(question_tags.c.question_id)
            .join(Tag, Tag.id == question_tags.c.tag_id)
            .where(Tag.name == body.tag_name)
        )
        stmt = stmt.where(
            (Question.id.in_(tagged)) | (Question.parent_question_id.in_(tagged))
        )

    qids = (await db.execute(
        stmt.order_by(func.random()).limit(body.count)
    )).scalars().all()
    if len(qids) < body.count:
        raise HTTPException(400, f"符合条件的题目不足 {body.count} 道（仅 {len(qids)} 道）")

    session = ExamSession(
        device_id=body.device_id,
        user_id=current_user.id if current_user else None,
        question_ids=json.dumps(list(qids)),
        time_limit_sec=body.time_limit_sec,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "id": session.id,
        "question_ids": list(qids),
        "time_limit_sec": body.time_limit_sec,
    }


@router.post("/{exam_id}/submit", summary="提交模考，返回成绩报告")
async def submit_exam(
    exam_id: int,
    body: ExamSubmitRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    session = (await db.execute(
        select(ExamSession).where(ExamSession.id == exam_id)
    )).scalar_one_or_none()
    if not session:
        raise HTTPException(404, "模考不存在")
    if session.device_id != body.device_id and not (
        current_user and session.user_id == current_user.id
    ):
        raise HTTPException(403, "无权提交该模考")
    if session.submitted_at:
        raise HTTPException(400, "该模考已提交")

    exam_qids = set(json.loads(session.question_ids))
    answer_map = {a.question_id: a.answer for a in body.answers if a.question_id in exam_qids}

    questions = (await db.execute(
        select(Question)
        .options(selectinload(Question.options), selectinload(Question.solutions))
        .where(Question.id.in_(exam_qids))
    )).scalars().all()

    details = []
    correct_count = 0
    for q in sorted(questions, key=lambda x: json.loads(session.question_ids).index(x.id)):
        user_answer = (answer_map.get(q.id) or "").strip()
        is_correct = False
        correct_answer = None

        if q.question_type == "choice":
            correct_labels = {o.label for o in q.options if o.is_correct}
            is_correct = bool(user_answer) and judge_choice(user_answer, correct_labels)
            correct_answer = "、".join(sorted(correct_labels))
        elif q.question_type == "fill":
            sol = next((s for s in q.solutions if s.version == 1), None) or (
                q.solutions[0] if q.solutions else None
            )
            if sol:
                ref_raw = sol.content_markdown.strip()
                if user_answer:
                    is_correct, _ = judge_fill(user_answer, ref_raw)
                correct_answer = format_fill_answer(ref_raw)

        if is_correct:
            correct_count += 1
        details.append({
            "question_id": q.id,
            "stem": q.stem_markdown[:120],
            "user_answer": user_answer or None,
            "is_correct": is_correct,
            "correct_answer": correct_answer,
        })
        # 模考作答同样计入做题记录（错题本/统计联动）
        db.add(AttemptLog(
            device_id=body.device_id,
            user_id=current_user.id if current_user else None,
            question_id=q.id,
            answer=user_answer or None,
            is_correct=is_correct,
        ))

    session.submitted_at = datetime.now()
    session.duration_sec = body.duration_sec
    session.score_correct = correct_count
    session.score_total = len(exam_qids)
    session.result_json = json.dumps(details, ensure_ascii=False)
    await db.commit()

    return {
        "id": session.id,
        "correct": correct_count,
        "total": len(exam_qids),
        "accuracy": round(correct_count / len(exam_qids), 4) if exam_qids else 0,
        "duration_sec": body.duration_sec,
        "details": details,
    }
