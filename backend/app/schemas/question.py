"""
题目相关 Schema：请求体与响应模型
"""
from datetime import datetime

from pydantic import BaseModel, Field


# ---------- 嵌套子模型 ----------

class SourceBrief(BaseModel):
    """来源简要信息"""
    id: int
    book_title: str
    author: str | None = None

    model_config = {"from_attributes": True}


class TagBrief(BaseModel):
    """标签简要信息"""
    id: int
    name: str
    type: str

    model_config = {"from_attributes": True}


class OptionOut(BaseModel):
    """选项"""
    id: int
    label: str
    content_markdown: str
    is_correct: bool

    model_config = {"from_attributes": True}


class SolutionOut(BaseModel):
    """解析"""
    id: int
    content_markdown: str
    version: int

    model_config = {"from_attributes": True}


# ---------- 响应模型 ----------

class QuestionListItem(BaseModel):
    """题目列表项（精简）"""
    id: int
    stem_markdown: str
    question_type: str
    difficulty: int | None = None
    status: str
    book_chapter: str | None = None
    source: SourceBrief | None = None
    tags: list[TagBrief] = []

    model_config = {"from_attributes": True}


class QuestionDetail(BaseModel):
    """题目详情（完整，含选项/解析/标签）"""
    id: int
    stem_markdown: str
    question_type: str
    difficulty: int | None = None
    status: str
    book_page: int | None = None
    book_chapter: str | None = None
    source: SourceBrief | None = None
    options: list[OptionOut] = []
    solutions: list[SolutionOut] = []
    tags: list[TagBrief] = []
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------- 请求模型 ----------

class AttemptRequest(BaseModel):
    """提交作答"""
    device_id: str = Field(..., min_length=1, max_length=64)
    answer: str = Field(..., description="用户作答内容")
    duration_ms: int | None = Field(None, ge=0, description="作答耗时(毫秒)")


class AttemptResponse(BaseModel):
    """作答结果"""
    is_correct: bool | None = None
    correct_answer: str | None = None
    explanation: str | None = None


class FavoriteRequest(BaseModel):
    """切换收藏"""
    device_id: str = Field(..., min_length=1, max_length=64)
    question_id: int


class FavoriteResponse(BaseModel):
    """收藏操作结果"""
    favorited: bool
    question_id: int
