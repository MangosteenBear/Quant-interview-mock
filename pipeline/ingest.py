"""入库（A10）

将 dedup 产出的 questions_deduped.json 写入数据库。

设计要点：
- 使用同步 SQLAlchemy（pipeline 是 CLI 批处理，不需要 async）
- URL 自动适配：sqlite+aiosqlite:// → sqlite://（strip async driver）
- 幂等：simhash 相同视为已入库，跳过（UPDATE 不覆盖）
- 自动创建 Source 记录（若 source_file 对应的 source 不存在）

输入：questions_deduped.json
输出：写入数据库，返回入库摘要 dict
"""
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, relationship

from pipeline.logger import logger


# --------------------------------------------------------------------------- #
# 内联 ORM 模型（与 backend/app/models 保持结构一致，但独立声明避免跨包依赖）    #
# --------------------------------------------------------------------------- #

class _Base(DeclarativeBase):
    pass


class _Source(_Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_title = Column(String(500))
    author = Column(String(200), nullable=True)
    edition = Column(String(100), nullable=True)
    file_hash = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)


class _Question(_Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stem_markdown = Column(Text)
    stem_latex_normalized = Column(Text, nullable=True)
    question_type = Column(String(20))
    difficulty = Column(Integer, nullable=True)
    simhash = Column(String(64), nullable=True)
    source_id = Column(ForeignKey("sources.id"), nullable=True)
    book_page = Column(Integer, nullable=True)
    book_chapter = Column(String(200), nullable=True)
    status = Column(String(20), default="published")
    ingested_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class _Solution(_Base):
    __tablename__ = "solutions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(ForeignKey("questions.id", ondelete="CASCADE"))
    content_markdown = Column(Text)
    source_id = Column(ForeignKey("sources.id"), nullable=True)
    version = Column(Integer, default=1)


# --------------------------------------------------------------------------- #
# 辅助函数                                                                      #
# --------------------------------------------------------------------------- #

def _sync_url(db_url: str) -> str:
    """将异步 driver URL 转为同步：sqlite+aiosqlite:// → sqlite://"""
    return db_url.replace("sqlite+aiosqlite://", "sqlite://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )


def _guess_type(text: str) -> str:
    """粗粒度题型推断，后续人工校正。"""
    t = text[:200]
    if any(k in t for k in ("A.", "B.", "C.", "（A）", "（B）", "选择")):
        return "choice"
    if any(k in t for k in ("____", "___", "填空", "填入")):
        return "fill"
    if any(k in t for k in ("证明", "推导", "证")):
        return "proof"
    return "short"


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()[:16]


# --------------------------------------------------------------------------- #
# 主函数                                                                        #
# --------------------------------------------------------------------------- #

def ingest_questions(
    questions_path: str,
    db_url: str = "sqlite:///./quantquiz.db",
    source_title: str | None = None,
    source_file: str | None = None,
) -> dict[str, Any]:
    """
    批量入库，幂等（simhash 相同则跳过）。

    Args:
        questions_path: dedup 产出的 JSON 路径
        db_url:         数据库 URL（支持 sqlite 和 postgresql）
        source_title:   书名（若为 None 则用 questions_path 的文件名）
        source_file:    原始 PDF 路径（用于计算 file_hash）

    Returns:
        {"inserted": int, "skipped": int, "source_id": int}
    """
    url = _sync_url(db_url)
    engine = create_engine(url, future=True)
    _Base.metadata.create_all(engine)  # 幂等建表

    questions: list[dict] = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    title = source_title or Path(questions_path).stem
    fhash = _file_hash(source_file) if source_file else None

    with Session(engine) as session:
        # 找或建 Source 记录
        src = session.execute(
            select(_Source).where(_Source.book_title == title)
        ).scalar_one_or_none()
        if src is None:
            src = _Source(book_title=title, file_hash=fhash)
            session.add(src)
            session.flush()
            logger.info(f"新建 Source: '{title}' id={src.id}", extra={"stage": "ingest"})
        source_id = src.id

        inserted = 0
        skipped = 0

        for q in questions:
            sh = q.get("simhash")

            # simhash 碰撞检查（幂等）
            if sh:
                existing = session.execute(
                    select(_Question.id).where(_Question.simhash == sh)
                ).scalar_one_or_none()
                if existing is not None:
                    skipped += 1
                    continue

            raw_text = q.get("raw_text", "")
            pages_list = q.get("source_pages") or [None]
            first_page = pages_list[0] if pages_list else None

            new_q = _Question(
                stem_markdown=raw_text,
                question_type=_guess_type(raw_text),
                simhash=sh,
                source_id=source_id,
                book_page=first_page,
                status="published",
            )
            session.add(new_q)
            session.flush()

            ans = q.get("answer_text")
            if ans:
                session.add(_Solution(
                    question_id=new_q.id,
                    content_markdown=ans,
                    source_id=source_id,
                    version=1,
                ))

            inserted += 1

        session.commit()

    summary = {"inserted": inserted, "skipped": skipped, "source_id": source_id}
    logger.info(
        f"入库完成：新增={inserted}，跳过={skipped}，source_id={source_id}",
        extra={"stage": "ingest"},
    )
    return summary
