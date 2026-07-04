"""
题目接口模块
8 个端点中的 6 个：列表/详情/搜索/作答/收藏切换/收藏列表
"""
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_session, get_pagination
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


# ---------- 详情 ----------
@router.get("/{question_id}", response_model=QuestionDetail, summary="题目详情")
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
    return question


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
    from sqlalchemy import or_
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
    stmt = stmt.order_by(Question.id).offset(pagination["offset"]).limit(pagination["page_size"])
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
        correct_opts = [o for o in question.options if o.is_correct]
        correct_set = set(o.label for o in correct_opts)
        user_labels = set(body.answer.strip().upper().replace("，", ",").split(","))
        is_correct = user_labels == correct_set
        # 格式："正确答案 A：xxxx"（多选用 / 分隔）
        correct_answer = "  /  ".join(
            f"正确答案 {o.label}：{o.content_markdown}"
            for o in sorted(correct_opts, key=lambda x: x.label)
        )
    elif question.question_type == "fill":
        if question.solutions:
            # 优先用 version=1（短答案），无则用第一条
            short_sol = next((s for s in question.solutions if s.version == 1), None)
            ref_raw = (short_sol or question.solutions[0]).content_markdown.strip()
            correct_answer = ref_raw

            def normalize_blank(s: str) -> str:
                """去序号前缀(1./①)、strip、lower"""
                import re
                s = re.sub(r'^\d+\.\s*', '', s.strip())  # "1. answer" → "answer"
                s = re.sub(r'^[①②③④⑤⑥⑦⑧⑨]\s*', '', s)
                return s.strip().lower()

            def accepted_vals(ref_part: str):
                """将 'a lot (lots)' 展开为 ['a lot', 'lots']"""
                import re
                base = normalize_blank(ref_part)
                alts = [base]
                m = re.search(r'\(([^)]+)\)', base)
                if m:
                    # 括号内容作为备选
                    alts.append(m.group(1).strip().lower())
                    alts.append(re.sub(r'\s*\([^)]+\)', '', base).strip())
                return alts

            ref_parts = [p for p in ref_raw.split("|")]
            user_parts = [p.strip() for p in body.answer.strip().split("|")]

            def blank_match(user: str, ref: str) -> bool:
                u = normalize_blank(user)
                return u in accepted_vals(ref)

            if len(ref_parts) == 1:
                is_correct = blank_match(user_parts[0], ref_parts[0]) if user_parts else False
            else:
                is_correct = (len(user_parts) == len(ref_parts) and
                              all(blank_match(u, r) for u, r in zip(user_parts, ref_parts)))
        else:
            is_correct = False
    else:
        # 简答/证明：不自动判错，返回参考答案
        if question.solutions:
            correct_answer = question.solutions[0].content_markdown

    # 记录作答日志
    log = AttemptLog(
        device_id=body.device_id,
        question_id=question_id,
        answer=body.answer,
        is_correct=is_correct,
        duration_ms=body.duration_ms,
    )
    db.add(log)

    # 解析优先用 version=2（原题完整解析）
    explanation = None
    if question.solutions:
        full_sol = next((s for s in question.solutions if s.version == 2), None)
        explanation = (full_sol or question.solutions[0]).content_markdown

    # 填空题展示答案时去掉序号前缀，方便用户对照
    if question.question_type == "fill" and correct_answer:
        import re
        correct_answer = re.sub(r'(?m)^\d+\.\s*', '', correct_answer).strip()

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
