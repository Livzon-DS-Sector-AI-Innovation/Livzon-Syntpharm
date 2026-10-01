from typing import Any, TypedDict

from pydantic import BaseModel, Field


class PaginationMeta(TypedDict):
    """Pagination envelope carried in ApiResponse.meta.

    Mirrors what app/core/response.py:paginated_response() emits, so the
    OpenAPI contract names these fields instead of leaving meta an opaque dict.

    Deliberately a TypedDict, not a BaseModel: a BaseModel would coerce meta
    into a model instance, and the ~73 module envelopes that declare
    `meta: dict[...]` would then fail `response_model` validation with
    "Input should be a valid dictionary". A TypedDict keeps meta a plain dict
    while still generating a named schema for the frontend.
    """

    page: int
    page_size: int
    total: int


class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None
    # Pagination only. Non-pagination metadata belongs in `data` so this stays
    # a type the frontend can rely on (AGENTS.md: API types come from the spec).
    meta: PaginationMeta | None = None


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
