"""
题目核心模型：Question + Option + Solution
对应 PRD §3.3 题目主表/选项表/解析表
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Question(Base):
    """题目主表"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stem_markdown: Mapped[str] = mapped_column(Text, comment="题干（Markdown，含 LaTeX 公式）")
    stem_latex_normalized: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="题干 LaTeX 归一化文本，用于去重与搜索索引"
    )
    question_type: Mapped[str] = mapped_column(
        String(20), comment="题型: choice(选择)/fill(填空)/short(简答)/proof(证明)"
    )
    difficulty: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="难度 1-5"
    )
    simhash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="64位 SimHash 去重指纹"
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True, comment="来源书目 ID"
    )
    book_page: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="原书页码")
    book_chapter: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="原书章节"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="published",
        comment="状态: pending/reviewing/published/rejected"
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="入库时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # 关联关系
    source: Mapped["Source | None"] = relationship(  # noqa: F821
        back_populates="questions", lazy="selectin"
    )
    options: Mapped[list["Option"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", lazy="selectin",
        order_by="Option.label"
    )
    solutions: Mapped[list["Solution"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", lazy="selectin"
    )
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="question_tags", back_populates="questions", lazy="selectin"
    )


class Option(Base):
    """选择题选项"""

    __tablename__ = "options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(10), comment="选项标签: A/B/C/D")
    content_markdown: Mapped[str] = mapped_column(Text, comment="选项内容（Markdown含LaTeX）")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否正确选项")

    question: Mapped["Question"] = relationship(back_populates="options")


class Solution(Base):
    """解析表（1题N版本，支持相同题干合并保留多来源解析）"""

    __tablename__ = "solutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    content_markdown: Mapped[str] = mapped_column(Text, comment="解析内容（Markdown含LaTeX）")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True, comment="解析来源（多版本时区分）"
    )
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")

    question: Mapped["Question"] = relationship(back_populates="solutions")
    source: Mapped["Source | None"] = relationship(  # noqa: F821
        back_populates="solutions", lazy="selectin"
    )
