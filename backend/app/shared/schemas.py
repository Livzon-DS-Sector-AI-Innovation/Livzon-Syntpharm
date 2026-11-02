from typing import Any, Literal, TypedDict

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


class DataResponse[T](BaseModel):
    """带具体 `data` 类型的响应信封。

    AGENTS.md:133 禁止 `response_model=ApiResponse` 与 `response_model=dict`，
    因为 `ApiResponse.data` 是 `Any`，OpenAPI 只能生成 `{type: object}`。
    这里用泛型把 `data` 固定为端点的真实返回类型，OpenAPI 会展开成
    `DataResponse_PersonnelResponse_` 这类具名 schema，前端可从生成的
    TypeScript 类型里直接拿到字段。

    用法：`response_model=DataResponse[PersonnelResponse]`，或以返回注解声明。
    """

    code: int = 200
    message: str = "success"
    data: T | None = None
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
    """Generic data response wrapper.

    `data` accepts a mapping **or a sequence** — some endpoints return a bare list
    (`DICT_OPTIONS`, `WORKSHOP_CHOICES`). It was `dict[str, Any] | None`, which the
    declared type could not describe, so those responses generated a misleading
    OpenAPI schema.

    This is a stop-gap, not the goal: `AGENTS.md:133` requires a concrete response
    model per endpoint, and `Any` inside `data` still gives the frontend
    `{type: object}` rather than real fields.
    """

    code: int = 200
    message: str = "success"
    data: dict[str, Any] | list[Any] | None = None


class AsyncJobAccepted(BaseModel):
    """异步任务的受理回执（提交端点立即返回，结果需轮询拿）。"""

    job_id: str
    status: Literal["running"] = "running"


class AsyncJobAcceptedResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AsyncJobAccepted


class AsyncJobState(BaseModel):
    """异步任务的当前状态（轮询端点返回）。

    404（任务不存在）不代表失败：状态存进程内，重启即丢（`D-11`）。
    """

    job_id: str
    status: Literal["running", "done", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = None


class AsyncJobStateResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AsyncJobState
