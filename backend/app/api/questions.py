"""
题目接口模块
8 个端点中的 6 个：列表/详情/搜索/作答/收藏切换/收藏列表
"""
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_session, get_current_user_optional, get_pagination
from app.models import Question, Option, Solution, AttemptLog, Favorite, QuestionReport, Tag, question_tags
from app.schemas.common import PageResponse
from app.schemas.question import (
    QuestionListItem,
    QuestionDetail,
    AttemptRequest,
    AttemptResponse,
    FavoriteRequest,
    FavoriteResponse,
    AdjacentResponse,
)
from app.utils.answer_match import judge_choice, judge_fill, format_fill_answer

router = APIRouter(prefix="/api/questions", tags=["题目"])


# ---------- 列表 ----------
@router.get("", response_model=PageResponse[QuestionListItem], summary="题目列表")
async def list_questions(
    source_id: int | None = Query(None, description="按来源书目筛选"),
    book_chapter: str | None = Query(None, description="按章节筛选"),
    question_type: str | None = Query(None, description="按题型筛选: choice/fill/short/proof"),
    difficulty: int | None = Query(None, ge=1, le=5, description="按难度筛选 1-5"),
    tag_name: str | None = Query(None, description="按知识点标签筛选"),
    status: str = Query("published", description="状态筛选，默认只看已发布"),
    db: AsyncSession = Depends(get_session),
    pagination: dict = Depends(get_pagination),
):
    # 构建查询条件
    conditions = []
    if source_id is not None:
        conditions.append(Question.source_id == source_id)
    if book_chapter is not None:
        conditions.append(Question.book_chapter == book_chapter)
    if question_type is not None:
        conditions.append(Question.question_type == question_type)
    if difficulty is not None:
        conditions.append(Question.difficulty == difficulty)
    if status:
        conditions.append(Question.status == status)

    def apply_tag_filter(stmt):
        if tag_name:
            # IDs directly tagged with this tag
            direct = (
                select(question_tags.c.question_id)
                .join(Tag, Tag.id == question_tags.c.tag_id)
                .where(Tag.name == tag_name)
            )
            # Also include variants whose parent is tagged
            stmt = stmt.where(
                (Question.id.in_(direct)) |
                (Question.parent_question_id.in_(direct))
            )
        return stmt

    # 查询总数
    count_stmt = select(func.count(Question.id))
    for cond in conditions:
        count_stmt = count_stmt.where(cond)
    count_stmt = apply_tag_filter(count_stmt)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 查询列表
    stmt = (
        select(Question)
        .options(selectinload(Question.source), selectinload(Question.tags))
    )
    for cond in conditions:
        stmt = stmt.where(cond)
    stmt = apply_tag_filter(stmt)
    stmt = stmt.order_by(Question.id).offset(pagination["offset"]).limit(pagination["page_size"])
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PageResponse(
        items=items,
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=math.ceil(total / pagination["page_size"]) if total > 0 else 0,
    )


# ---------- 每日一题 ----------
import hashlib
from datetime import date as _date


@router.get("/daily", summary="每日一题（全站当天同一道）")
async def daily_question(db: AsyncSession = Depends(get_session)):
    today = _date.today().isoformat()
    total = (await db.execute(
        select(func.count(Question.id)).where(Question.status == "published")
    )).scalar() or 0
    if total == 0:
        raise HTTPException(404, "题库为空")
    idx = int(hashlib.md5(today.encode()).hexdigest(), 16) % total
    qid = (await db.execute(
        select(Question.id).where(Question.status == "published")
        .order_by(Question.id).offset(idx).limit(1)
    )).scalar_one()
    return {"id": qid, "date": today}


# ---------- 随机一题 ----------
@router.get("/random", summary="随机抽一题（支持条件筛选）")
async def random_question(
    question_type: str | None = Query(None),
    difficulty: int | None = Query(None, ge=1, le=5),
    tag_name: str | None = Query(None),
    source_id: int | None = Query(None),
    exclude_id: int | None = Query(None, description="排除当前题，连续随机不重复"),
    mode: str = Query("random", description="random=全随机 smart=优先错题>未做>随机"),
    device_id: str | None = Query(None, description="smart 模式的匿名身份"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    stmt = select(Question.id).where(Question.status == "published")
    if question_type:
        stmt = stmt.where(Question.question_type == question_type)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    if source_id:
        stmt = stmt.where(Question.source_id == source_id)
    if exclude_id:
        stmt = stmt.where(Question.id != exclude_id)
    if tag_name:
        tagged = (
            select(question_tags.c.question_id)
            .join(Tag, Tag.id == question_tags.c.tag_id)
            .where(Tag.name == tag_name)
        )
        stmt = stmt.where(
            (Question.id.in_(tagged)) | (Question.parent_question_id.in_(tagged))
        )
    # smart 模式：错题 > 未做 > 全随机（三级回退，均在已筛选范围内）
    if mode == "smart" and (current_user or device_id):
        from app.models import AttemptLog, MasteredQuestion

        if current_user:
            ident = AttemptLog.user_id == current_user.id
            m_ident = MasteredQuestion.user_id == current_user.id
        else:
            ident = AttemptLog.device_id == device_id
            m_ident = MasteredQuestion.device_id == device_id

        rn = func.row_number().over(
            partition_by=AttemptLog.question_id,
            order_by=[AttemptLog.created_at.desc(), AttemptLog.id.desc()],
        ).label("rn")
        latest = (
            select(AttemptLog.question_id, AttemptLog.is_correct, rn)
            .where(ident).subquery()
        )
        wrong_ids = select(latest.c.question_id).where(
            latest.c.rn == 1, latest.c.is_correct == False,  # noqa: E712
        )
        mastered_ids = select(MasteredQuestion.question_id).where(m_ident)

        qid = (await db.execute(
            stmt.where(Question.id.in_(wrong_ids), Question.id.not_in(mastered_ids))
            .order_by(func.random()).limit(1)
        )).scalar_one_or_none()
        if qid is not None:
            return {"id": qid, "pick": "wrong"}

        attempted_ids = select(AttemptLog.question_id).where(ident)
        qid = (await db.execute(
            stmt.where(Question.id.not_in(attempted_ids))
            .order_by(func.random()).limit(1)
        )).scalar_one_or_none()
        if qid is not None:
            return {"id": qid, "pick": "unseen"}

    qid = (await db.execute(stmt.order_by(func.random()).limit(1))).scalar_one_or_none()
    if qid is None:
        raise HTTPException(404, "没有符合条件的题目")
    return {"id": qid, "pick": "random"}


# ---------- 详情 ----------
@router.get("/{question_id}", response_model=QuestionDetail, summary="题目详情（含前后题 ID）")
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Question)
        .options(
            selectinload(Question.source),
            selectinload(Question.options),
            selectinload(Question.solutions),
            selectinload(Question.tags),
        )
        .where(Question.id == question_id)
    )
    question = (await db.execute(stmt)).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail=f"题目 {question_id} 不存在")

    # 前后题 ID 一并返回，省去客户端额外请求
    prev_id = (await db.execute(
        select(Question.id).where(Question.status == "published", Question.id < question_id)
        .order_by(Question.id.desc()).limit(1)
    )).scalar_one_or_none()
    next_id = (await db.execute(
        select(Question.id).where(Question.status == "published", Question.id > question_id)
        .order_by(Question.id).limit(1)
    )).scalar_one_or_none()

    result = QuestionDetail.model_validate(question)
    result.adj_prev_id = prev_id
    result.adj_next_id = next_id
    return result


# ---------- 前后题 ----------
@router.get("/{question_id}/adjacent", response_model=AdjacentResponse, summary="前后题 ID")
async def get_adjacent(
    question_id: int,
    db: AsyncSession = Depends(get_session),
):
    prev_row = (await db.execute(
        select(Question.id).where(Question.status == "published", Question.id < question_id)
        .order_by(Question.id.desc()).limit(1)
    )).scalar_one_or_none()
    next_row = (await db.execute(
        select(Question.id).where(Question.status == "published", Question.id > question_id)
        .order_by(Question.id).limit(1)
    )).scalar_one_or_none()
    return AdjacentResponse(prev_id=prev_row, next_id=next_row)


# ---------- 搜索 ----------
@router.get("/search/all", response_model=PageResponse[QuestionListItem], summary="关键词搜索题目")
async def search_questions(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    db: AsyncSession = Depends(get_session),
    pagination: dict = Depends(get_pagination),
):
    # 按空格拆词，每词独立 LIKE AND 匹配（支持多词搜索）
    tokens = [t.strip() for t in q.split() if t.strip()]
    conditions = [Question.status == "published"]
    for token in tokens:
        pattern = f"%{token}%"
        # stem 或 solution 任意包含该词均可
        conditions.append(
            Question.stem_markdown.ilike(pattern) |
            Question.id.in_(
                select(Solution.question_id)
                .where(Solution.content_markdown.ilike(pattern))
            )
        )

    count_stmt = select(func.count(Question.id))
    for cond in conditions:
        count_stmt = count_stmt.where(cond)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Question)
        .options(selectinload(Question.source), selectinload(Question.tags))
    )
    for cond in conditions:
        stmt = stmt.where(cond)
    # PG 用 pg_trgm 相似度做相关性排序（GIN 索引已建）；SQLite 开发环境回退 id 排序
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.order_by(func.similarity(Question.stem_markdown, q).desc(), Question.id)
    else:
        stmt = stmt.order_by(Question.id)
    stmt = stmt.offset(pagination["offset"]).limit(pagination["page_size"])
    items = (await db.execute(stmt)).scalars().all()

    return PageResponse(
        items=items,
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=math.ceil(total / pagination["page_size"]) if total > 0 else 0,
    )


# ---------- 作答 ----------
@router.post("/{question_id}/attempt", response_model=AttemptResponse, summary="提交作答")
async def submit_attempt(
    question_id: int,
    body: AttemptRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    # 查题目与正确选项
    stmt = (
        select(Question)
        .options(selectinload(Question.options), selectinload(Question.solutions))
        .where(Question.id == question_id)
    )
    question = (await db.execute(stmt)).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail=f"题目 {question_id} 不存在")

    # 判定对错
    is_correct = None
    correct_answer = None

    if question.question_type == "choice":
        correct_opts = sorted(
            [o for o in question.options if o.is_correct], key=lambda x: x.label
        )
        correct_set = {o.label for o in correct_opts}
        is_correct = judge_choice(body.answer, correct_set)
        correct_answer = "  /  ".join(
            f"正确答案 {o.label}：{o.content_markdown}" for o in correct_opts
        )

    elif question.question_type == "fill":
        short_sol = next((s for s in question.solutions if s.version == 1), None)
        sol = short_sol or (question.solutions[0] if question.solutions else None)
        if sol:
            ref_raw = sol.content_markdown.strip()
            is_correct, _ = judge_fill(body.answer, ref_raw)
            correct_answer = format_fill_answer(ref_raw)
        else:
            is_correct = False

    else:
        # 简答/证明：不自动判错，展示参考答案
        if question.solutions:
            correct_answer = question.solutions[0].content_markdown

    # 解析优先用 version=2（原题完整解析）
    explanation = None
    if question.solutions:
        full_sol = next((s for s in question.solutions if s.version == 2), None)
        explanation = (full_sol or question.solutions[0]).content_markdown

    # 记录作答日志
    log = AttemptLog(
        device_id=body.device_id,
        user_id=current_user.id if current_user else None,
        question_id=question_id,
        answer=body.answer,
        is_correct=is_correct,
        duration_ms=body.duration_ms,
    )
    db.add(log)

    # 答错则清除「已掌握」标记，让题目回归错题本
    if is_correct is False:
        from app.models import MasteredQuestion as _MQ
        m_cond = (_MQ.user_id == current_user.id) if current_user else (_MQ.device_id == body.device_id)
        await db.execute(delete(_MQ).where(m_cond, _MQ.question_id == question_id))

    return AttemptResponse(
        is_correct=is_correct,
        correct_answer=correct_answer,
        explanation=explanation,
    )


# ---------- 举报题目 ----------
from pydantic import BaseModel as _BaseModel

class ReportRequest(_BaseModel):
    device_id: str
    reason: str  # wrong_answer / bad_options / garbled / other
    note: str | None = None


@router.post("/{question_id}/report", summary="举报题目问题")
async def report_question(
    question_id: int,
    body: ReportRequest,
    db: AsyncSession = Depends(get_session),
):
    q = (await db.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    if not q:
        raise HTTPException(404, "题目不存在")
    report = QuestionReport(
        device_id=body.device_id,
        question_id=question_id,
        reason=body.reason,
        note=body.note,
    )
    db.add(report)
    await db.commit()
    return {"ok": True}


# ---------- M5: 笔记 + 已掌握 ----------
from datetime import datetime as _dt

from app.models import MasteredQuestion, Note


class NoteRequest(_BaseModel):
    device_id: str
    content: str


def _note_ident(current_user, device_id: str):
    if current_user:
        return Note.user_id == current_user.id
    return Note.device_id == device_id


@router.get("/{question_id}/note", summary="获取本人对该题的笔记")
async def get_note(
    question_id: int,
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    note = (await db.execute(
        select(Note).where(_note_ident(current_user, device_id), Note.question_id == question_id)
    )).scalar_one_or_none()
    return {"content": note.content if note else None,
            "updated_at": note.updated_at if note else None}


@router.put("/{question_id}/note", summary="保存笔记（空内容即删除）")
async def save_note(
    question_id: int,
    body: NoteRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    content = body.content.strip()
    if len(content) > 5000:
        raise HTTPException(400, "笔记最长 5000 字")
    note = (await db.execute(
        select(Note).where(_note_ident(current_user, body.device_id), Note.question_id == question_id)
    )).scalar_one_or_none()

    if not content:
        if note:
            await db.delete(note)
            await db.commit()
        return {"saved": False, "deleted": True}

    if note:
        note.content = content
        note.updated_at = _dt.now()
    else:
        db.add(Note(
            device_id=body.device_id,
            user_id=current_user.id if current_user else None,
            question_id=question_id,
            content=content,
        ))
    await db.commit()
    return {"saved": True, "deleted": False}


class MasteredRequest(_BaseModel):
    device_id: str


@router.post("/{question_id}/mastered", summary="切换「已掌握」标记")
async def toggle_mastered(
    question_id: int,
    body: MasteredRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user_optional),
):
    if current_user:
        ident = MasteredQuestion.user_id == current_user.id
    else:
        ident = MasteredQuestion.device_id == body.device_id
    existing = (await db.execute(
        select(MasteredQuestion).where(ident, MasteredQuestion.question_id == question_id)
    )).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
        return {"mastered": False}
    db.add(MasteredQuestion(
        device_id=body.device_id,
        user_id=current_user.id if current_user else None,
        question_id=question_id,
    ))
    await db.commit()
    return {"mastered": True}
