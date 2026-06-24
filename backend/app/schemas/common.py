"""
通用 Schema：分页响应、统一错误响应
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """统一错误响应"""
    code: int
    message: str
    detail: str | None = None
