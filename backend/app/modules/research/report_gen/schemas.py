"""AI 报告生成的请求与响应模型。

响应统一用 ``DataResponse[T]``（``app/shared/schemas.py``）：``data`` 类型具体，
前端通过 OpenAPI 生成类型时能直接拿到字段，避免 ``response_model=dict``。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReportGenJobCreateRequest(BaseModel):
    """提交一次 AI 生成。"""

    report_id: uuid.UUID
    project_id: uuid.UUID
    deliverable_template_id: uuid.UUID = Field(..., description="Word 母本对应的交付物模板")
    doc_code: str | None = Field(None, max_length=100, description="受控编码")
    drug_name: str | None = Field(None, max_length=200, description="品种名称")
    supplement_text: str | None = Field(None, description="补充说明")


class ReportGenJobData(BaseModel):
    """任务详情：详情页头部与列表进度列都用它。"""

    id: uuid.UUID
    report_id: uuid.UUID
    project_id: uuid.UUID
    report_title: str | None = None
    template_file_name: str | None = None
    deliverable_template_id: uuid.UUID | None = None
    status: str
    progress: int
    current_step: str | None = None
    error_message: str | None = None
    doc_code: str | None = None
    drug_name: str | None = None
    supplement_text: str | None = None
    document_file_name: str | None = None
    slot_total: int
    slot_filled: int
    slot_gap: int
    rounds: int
    tool_mode: str | None = None
    model_config_name: str | None = None
    model_name: str | None = None
    structure_model_name: str | None = None
    fallback_model_name: str | None = None
    used_fallback: bool = False
    can_cancel: bool = False
    has_document: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class ReportGenJobListData(BaseModel):
    items: list[ReportGenJobData]
    active_count: int = 0


class ReportGenStepData(BaseModel):
    id: uuid.UUID
    seq: int
    kind: str
    title: str
    tool_name: str | None = None
    args_summary: dict[str, Any] | None = None
    result_summary: str | None = None
    status: str
    duration_ms: int | None = None
    created_at: datetime


class ReportGenStepListData(BaseModel):
    items: list[ReportGenStepData]
    last_seq: int = 0


class ReportGenSlotData(BaseModel):
    slot_key: str
    slot_label: str
    location: str | None = None
    state: str
    value: str | None = None
    source_name: str | None = None
    evidence: str | None = None
    confidence: float | None = None
    owner_hint: str | None = None


class ReportGenSlotListData(BaseModel):
    items: list[ReportGenSlotData]
    total: int = 0
    filled: int = 0
    gaps: int = 0


class ReportGenSlotUpdateRequest(BaseModel):
    """人工修正槽位：只改结果与对照表，不重新渲染成品（按需求确认的口径）。"""

    value: str | None = Field(None, description="新的填充值，留空表示标记缺口")
    evidence: str | None = Field(None, description="人工补充的依据")
    owner_hint: str | None = Field(None, max_length=100, description="缺口责任方")


class ReportGenModelTestRequest(BaseModel):
    """配置页的「测试连通」：只验证某一档能不能出字，不改任何配置。"""

    slot: Literal["main", "structure", "fallback"] = Field(description="要测试的模型档位")


class ReportGenModelTestData(BaseModel):
    ok: bool
    slot: str
    model: str | None = Field(None, description="实际使用的模型名；不含密钥与端点")
    latency_ms: int | None = Field(None, description="一次往返耗时（毫秒）")
    detail: str | None = Field(None, description="成功提示或失败原因摘要")


__all__ = [
    "ReportGenJobCreateRequest",
    "ReportGenJobData",
    "ReportGenJobListData",
    "ReportGenModelTestData",
    "ReportGenModelTestRequest",
    "ReportGenSlotData",
    "ReportGenSlotListData",
    "ReportGenSlotUpdateRequest",
    "ReportGenStepData",
    "ReportGenStepListData",
]
