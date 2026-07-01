"""管理后台 API — 题库增删改查与分类管理"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pathlib import Path
from sqlalchemy import func, select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Any

from app.api.deps import get_session
from app.models import Question, Solution, Source, Tag, QuestionReport
from app.database import Base

router = APIRouter(prefix="/admin", tags=["管理后台"])


# ── Pydantic Schemas ──────────────────────────────────────────

class QuestionPatch(BaseModel):
    stem_markdown: str | None = None
    question_type: str | None = None
    difficulty: int | None = None
    status: str | None = None
    book_chapter: str | None = None
    book_page: int | None = None
    tag_ids: list[int] | None = None


class SolutionPatch(BaseModel):
    content_markdown: str


class TagCreate(BaseModel):
    name: str
    type: str = "topic"


# ── 统计概览 ────────────────────────────────────────────────

@router.get("/api/stats")
async def admin_stats(db: AsyncSession = Depends(get_session)):
    total_q = (await db.execute(select(func.count(Question.id)))).scalar() or 0
    by_source = (await db.execute(
        select(Source.book_title, func.count(Question.id))
        .join(Question, Question.source_id == Source.id)
        .group_by(Source.id)
    )).all()
    by_status = (await db.execute(
        select(Question.status, func.count(Question.id)).group_by(Question.status)
    )).all()
    by_type = (await db.execute(
        select(Question.question_type, func.count(Question.id)).group_by(Question.question_type)
    )).all()
    no_answer = (await db.execute(
        select(func.count(Question.id))
        .outerjoin(Solution, Solution.question_id == Question.id)
        .where(Solution.id == None)
    )).scalar() or 0

    report_count = (await db.execute(select(func.count(QuestionReport.id)))).scalar() or 0

    return {
        "total_questions": total_q,
        "no_answer_count": no_answer,
        "report_count": report_count,
        "by_source": [{"title": r[0], "count": r[1]} for r in by_source],
        "by_status": dict(by_status),
        "by_type": dict(by_type),
    }


# ── 题目列表（管理视图，不过滤 status）────────────────────────

@router.get("/api/questions")
async def admin_list_questions(
    source_id: int | None = Query(None),
    status: str | None = Query(None),
    question_type: str | None = Query(None),
    q: str | None = Query(None, description="全文搜索"),
    has_answer: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Question)
        .options(
            selectinload(Question.source),
            selectinload(Question.solutions),
            selectinload(Question.tags),
        )
    )
    if source_id is not None:
        stmt = stmt.where(Question.source_id == source_id)
    if status:
        stmt = stmt.where(Question.status == status)
    if question_type:
        stmt = stmt.where(Question.question_type == question_type)
    if q:
        stmt = stmt.where(Question.stem_markdown.ilike(f"%{q}%"))
    if has_answer is True:
        stmt = stmt.join(Solution, Solution.question_id == Question.id)
    elif has_answer is False:
        stmt = stmt.outerjoin(Solution, Solution.question_id == Question.id).where(Solution.id == None)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Question.id).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    items = []
    for q_obj in rows:
        sol = q_obj.solutions[0].content_markdown[:120] if q_obj.solutions else None
        items.append({
            "id": q_obj.id,
            "stem": q_obj.stem_markdown[:150],
            "type": q_obj.question_type,
            "difficulty": q_obj.difficulty,
            "status": q_obj.status,
            "chapter": q_obj.book_chapter,
            "page": q_obj.book_page,
            "source": q_obj.source.book_title if q_obj.source else None,
            "tags": [{"id": t.id, "name": t.name} for t in q_obj.tags],
            "answer_preview": sol,
            "has_answer": bool(q_obj.solutions),
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ── 题目详情 ────────────────────────────────────────────────

@router.get("/api/questions/{question_id}")
async def admin_get_question(question_id: int, db: AsyncSession = Depends(get_session)):
    q_obj = (await db.execute(
        select(Question)
        .options(
            selectinload(Question.source),
            selectinload(Question.solutions),
            selectinload(Question.tags),
        )
        .where(Question.id == question_id)
    )).scalar_one_or_none()
    if not q_obj:
        raise HTTPException(404, "题目不存在")
    return {
        "id": q_obj.id,
        "stem_markdown": q_obj.stem_markdown,
        "question_type": q_obj.question_type,
        "difficulty": q_obj.difficulty,
        "status": q_obj.status,
        "book_chapter": q_obj.book_chapter,
        "book_page": q_obj.book_page,
        "source": q_obj.source.book_title if q_obj.source else None,
        "source_id": q_obj.source_id,
        "tags": [{"id": t.id, "name": t.name, "type": t.type} for t in q_obj.tags],
        "solutions": [
            {"id": s.id, "content_markdown": s.content_markdown, "version": s.version}
            for s in q_obj.solutions
        ],
    }


# ── 题目编辑 ────────────────────────────────────────────────

@router.patch("/api/questions/{question_id}")
async def admin_patch_question(
    question_id: int,
    patch: QuestionPatch,
    db: AsyncSession = Depends(get_session),
):
    q_obj = (await db.execute(
        select(Question)
        .options(selectinload(Question.tags))
        .where(Question.id == question_id)
    )).scalar_one_or_none()
    if not q_obj:
        raise HTTPException(404, "题目不存在")

    for field in ("stem_markdown", "question_type", "difficulty", "status", "book_chapter", "book_page"):
        val = getattr(patch, field)
        if val is not None:
            setattr(q_obj, field, val)

    if patch.tag_ids is not None:
        tags = (await db.execute(select(Tag).where(Tag.id.in_(patch.tag_ids)))).scalars().all()
        q_obj.tags = list(tags)

    await db.commit()
    return {"ok": True, "id": question_id}


# ── 答案编辑 ────────────────────────────────────────────────

@router.put("/api/questions/{question_id}/solution")
async def admin_upsert_solution(
    question_id: int,
    body: SolutionPatch,
    db: AsyncSession = Depends(get_session),
):
    existing = (await db.execute(
        select(Solution).where(Solution.question_id == question_id).limit(1)
    )).scalar_one_or_none()
    if existing:
        existing.content_markdown = body.content_markdown
    else:
        db.add(Solution(question_id=question_id, content_markdown=body.content_markdown, version=1))
    await db.commit()
    return {"ok": True}


# ── 批量状态更新 ────────────────────────────────────────────

class BatchStatusUpdate(BaseModel):
    ids: list[int]
    status: str


@router.patch("/api/questions/batch-status")
async def admin_batch_status(body: BatchStatusUpdate, db: AsyncSession = Depends(get_session)):
    allowed = {"published", "pending", "reviewing", "rejected"}
    if body.status not in allowed:
        raise HTTPException(400, f"状态必须是 {allowed} 之一")
    if not body.ids:
        raise HTTPException(400, "ids 不能为空")
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(Question)
        .where(Question.id.in_(body.ids))
        .values(status=body.status)
    )
    await db.commit()
    return {"ok": True, "updated": len(body.ids)}


# ── 题目删除 ────────────────────────────────────────────────

@router.delete("/api/questions/{question_id}")
async def admin_delete_question(question_id: int, db: AsyncSession = Depends(get_session)):
    result = await db.execute(delete(Question).where(Question.id == question_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "题目不存在")
    return {"ok": True}


# ── 标签管理 ────────────────────────────────────────────────

@router.get("/api/tags")
async def admin_list_tags(db: AsyncSession = Depends(get_session)):
    tags = (await db.execute(select(Tag).order_by(Tag.type, Tag.name))).scalars().all()
    return [{"id": t.id, "name": t.name, "type": t.type} for t in tags]


@router.post("/api/tags")
async def admin_create_tag(body: TagCreate, db: AsyncSession = Depends(get_session)):
    tag = Tag(name=body.name, type=body.type)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {"id": tag.id, "name": tag.name, "type": tag.type}


@router.delete("/api/tags/{tag_id}")
async def admin_delete_tag(tag_id: int, db: AsyncSession = Depends(get_session)):
    await db.execute(delete(Tag).where(Tag.id == tag_id))
    await db.commit()
    return {"ok": True}


# ── 举报列表 ────────────────────────────────────────────────

@router.get("/api/reports")
async def admin_list_reports(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(
        select(QuestionReport, Question.stem_markdown)
        .join(Question, Question.id == QuestionReport.question_id)
        .order_by(QuestionReport.created_at.desc())
        .limit(200)
    )).all()
    return [
        {
            "id": r.QuestionReport.id,
            "question_id": r.QuestionReport.question_id,
            "stem": r.stem_markdown[:80],
            "reason": r.QuestionReport.reason,
            "note": r.QuestionReport.note,
            "created_at": r.QuestionReport.created_at,
        }
        for r in rows
    ]


@router.delete("/api/reports/{report_id}")
async def admin_delete_report(report_id: int, db: AsyncSession = Depends(get_session)):
    await db.execute(delete(QuestionReport).where(QuestionReport.id == report_id))
    await db.commit()
    return {"ok": True}


# ── 来源列表 ────────────────────────────────────────────────

@router.get("/api/sources")
async def admin_list_sources(db: AsyncSession = Depends(get_session)):
    sources = (await db.execute(select(Source))).scalars().all()
    result = []
    for s in sources:
        cnt = (await db.execute(
            select(func.count(Question.id)).where(Question.source_id == s.id)
        )).scalar() or 0
        result.append({"id": s.id, "title": s.book_title, "author": s.author, "count": cnt})
    return result


# ── 管理面板 HTML ────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_panel():
    html_path = Path(__file__).parent.parent.parent / "admin" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Admin panel not found</h1>", status_code=404)
