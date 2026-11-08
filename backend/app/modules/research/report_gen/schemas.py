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


class ReportGenMetricsData(BaseModel):
    """配置页「Agent 运行情况」：窗口内**已终态**任务的聚合口径。

    比率类字段在样本为 0 时返回 ``None``，前端显示「—」而不是假的 0%，
    避免「刚上线没跑过任务」被误读成「成功率 0%」。
    """

    window_days: int = Field(description="统计窗口天数")
    total: int = Field(0, description="窗口内终态任务数（completed + failed + cancelled）")
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    success_rate: float | None = Field(None, description="completed ÷ 终态任务数")
    avg_rounds: float | None = Field(None, description="仅统计 completed 的平均轮次")
    avg_duration_seconds: float | None = Field(None, description="仅统计 completed 的平均耗时（秒）")
    gap_rate: float | None = Field(None, description="Σslot_gap ÷ Σslot_total（仅 completed）")
    fallback_rate: float | None = Field(None, description="completed 中触发兜底降级的比例")
    agent_prompt_version: str = Field(description="正文生成提示词指纹（sha256 前 8 位）")
    structure_prompt_version: str = Field(description="结构识别提示词指纹（sha256 前 8 位）")
    generated_at: datetime = Field(description="本次统计时间，用于判断面板数据新鲜度")


__all__ = [
    "ReportGenJobCreateRequest",
    "ReportGenJobData",
    "ReportGenJobListData",
    "ReportGenMetricsData",
    "ReportGenModelTestData",
    "ReportGenModelTestRequest",
    "ReportGenSlotData",
    "ReportGenSlotListData",
    "ReportGenSlotUpdateRequest",
    "ReportGenStepData",
    "ReportGenStepListData",
]
