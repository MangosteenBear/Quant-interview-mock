"""
模型统一导出
确保所有模型在 Base.metadata 注册，供建表与关联解析
"""
from app.models.source import Source
from app.models.question import Question, Option, Solution
from app.models.tag import Tag, question_tags
from app.models.interaction import AttemptLog, Favorite

__all__ = [
    "Source",
    "Question",
    "Option",
    "Solution",
    "Tag",
    "question_tags",
    "AttemptLog",
    "Favorite",
]
