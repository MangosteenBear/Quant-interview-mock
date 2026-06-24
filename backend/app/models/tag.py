"""
标签模型：Tag + QuestionTag 关联表
三类标签: knowledge(知识点) / position(岗位) / topic(题型主题)
题目与标签为多对多关系
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 多对多关联表
question_tags = Table(
    "question_tags",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """标签（知识点/岗位/题型主题）"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), comment="标签名称")
    type: Mapped[str] = mapped_column(
        String(20), comment="标签类型: knowledge/position/topic"
    )

    questions: Mapped[list["Question"]] = relationship(  # noqa: F821
        secondary=question_tags, back_populates="tags", lazy="selectin"
    )
