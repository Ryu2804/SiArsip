from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    """Pagination info for list endpoints."""

    page: int
    size: int
    total: int


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "OK"
    data: T | None = None
    meta: Meta | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


def ok(data: T | None = None, message: str = "OK", meta: Meta | None = None) -> SuccessResponse[T]:
    return SuccessResponse(data=data, message=message, meta=meta)
