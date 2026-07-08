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
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="登录用户，匿名为空"
    )
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
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="登录用户，匿名为空"
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="收藏时间"
    )


class QuestionReport(Base):
    """题目问题举报"""

    __tablename__ = "question_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), comment="匿名设备标识")
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="登录用户，匿名为空"
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(20), comment="原因: wrong_answer/bad_options/wrong_tag/garbled/other")
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="附加说明")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Note(Base):
    """题目个人笔记（匿名按设备，登录后跨设备）"""

    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint("device_id", "question_id", name="uq_note_device_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class MasteredQuestion(Base):
    """错题本「已掌握」标记（重新答错自动回归时删除）"""

    __tablename__ = "mastered_questions"
    __table_args__ = (
        UniqueConstraint("device_id", "question_id", name="uq_mastered_device_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class ExamSession(Base):
    """模考会话（轻量版：choice/fill 自动判分）"""

    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_ids: Mapped[str] = mapped_column(Text, comment="题目 ID 列表 JSON")
    time_limit_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_correct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="判分明细 JSON")
