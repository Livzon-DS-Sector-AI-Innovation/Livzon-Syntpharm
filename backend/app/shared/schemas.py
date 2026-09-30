from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None
    meta: dict[str, Any] | None = None


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class MessageApiResponse(BaseModel):
    """Message response wrapper"""

    code: int = 200
    message: str = "success"
    data: None = None


class DataApiResponse(BaseModel):
    """Generic data response wrapper"""

    code: int = 200
    message: str = "success"
    data: dict[str, Any] | None = None
