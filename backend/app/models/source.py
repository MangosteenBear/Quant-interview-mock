"""
来源表模型 - 数据溯源
每本 PDF 电子书对应一条 source 记录
"""
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    """题库数据来源（电子书/平台）"""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_title: Mapped[str] = mapped_column(String(500), comment="书名")
    author: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="作者")
    edition: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="版本/版次")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="PDF文件哈希，用于去重与溯源")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 关联关系
    questions: Mapped[list["Question"]] = relationship(  # noqa: F821
        back_populates="source", lazy="selectin"
    )
    solutions: Mapped[list["Solution"]] = relationship(  # noqa: F821
        back_populates="source", lazy="selectin"
    )
