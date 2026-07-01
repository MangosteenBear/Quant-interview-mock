"""
用户交互模型：AttemptLog(作答记录) + Favorite(收藏)
一期匿名模式，以 device_id 维度记录（无账号体系）
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AttemptLog(Base):
    """作答记录（匿名，设备维度）"""

    __tablename__ = "attempt_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), comment="匿名设备标识")
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用户作答内容")
    is_correct: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="是否正确（简答/证明可为 null）"
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="作答耗时(毫秒)")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="作答时间"
    )


class Favorite(Base):
    """收藏（匿名，设备维度）"""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("device_id", "question_id", name="uq_device_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), comment="匿名设备标识")
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="收藏时间"
    )


class QuestionReport(Base):
    """题目问题举报"""

    __tablename__ = "question_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), comment="匿名设备标识")
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(20), comment="原因: wrong_answer/bad_options/garbled/other")
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="附加说明")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
