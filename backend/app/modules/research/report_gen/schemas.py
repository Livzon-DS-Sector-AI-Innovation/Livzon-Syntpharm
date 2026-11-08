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


class ReportGenFeedbackSlotStat(BaseModel):
    """意见集中在哪些槽位：同一槽位反复被提，说明这里需要的不是改一次，而是改提示词或加示例。"""

    slot_key: str = Field(description="槽位标识")
    count: int = Field(description="窗口内该槽位被提意见的条数")


class ReportGenMetricsData(BaseModel):
    """配置页「Agent 运行情况」：窗口内**已终态**任务的聚合口径。

    比率类字段在样本为 0 时返回 ``None``，前端显示「—」而不是假的 0%，
    避免「刚上线没跑过任务」被误读成「成功率 0%」。
    评审意见部分按意见的提出时间落窗口，与任务窗口各算各的：意见是人对成品的判断，
    不依赖任务是否在窗口内开始。
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
    feedback_total: int = Field(0, description="窗口内提出的意见总数")
    feedback_open: int = Field(0, description="其中仍未落实的条数（下次生成会带上）")
    feedback_applied: int = Field(0, description="其中已被后续生成落实的条数")
    feedback_ignored: int = Field(0, description="其中被判不采纳的条数")
    feedback_adoption_rate: float | None = Field(
        None, description="applied ÷ (applied + ignored)：有人处置过的意见里被采纳的比例"
    )
    feedback_slot_top: list[ReportGenFeedbackSlotStat] = Field(
        default_factory=list, description="被提意见最多的槽位（最多 5 个，整篇意见不计入）"
    )
    agent_prompt_version: str = Field(description="正文生成提示词指纹（sha256 前 8 位）")
    structure_prompt_version: str = Field(description="结构识别提示词指纹（sha256 前 8 位）")
    generated_at: datetime = Field(description="本次统计时间，用于判断面板数据新鲜度")


class ReportGenStructureDiff(BaseModel):
    """解析结果与当前结构的差异：漏选=人工后补，多选=人工否掉。"""

    ai_slot_count: int = Field(description="解析当时模型选出的槽位数")
    current_slot_count: int = Field(description="当前结构里的槽位总数（含已停用）")
    kept_count: int = Field(description="AI 选中且当前仍启用的槽位数")
    missing_count: int = Field(description="漏选数：当前启用但 AI 当时没选（人工后补）")
    extra_count: int = Field(description="多选数：AI 当时选了但现在被停用或删除")
    missing_keys: list[str] = Field(default_factory=list, description="漏选槽位标识（最多 10 个）")
    extra_keys: list[str] = Field(default_factory=list, description="多选槽位标识（最多 10 个）")


class ReportGenStructureRunData(BaseModel):
    """一次母本结构解析的留痕。"""

    id: str
    source_key: str | None = Field(None, description="解析时的母本存储键，换版即变")
    prompt_version: str = Field(description="解析所用提示词指纹")
    model_name: str | None = Field(None, description="解析所用模型")
    candidate_count: int = Field(description="送模型的候选位置数")
    slot_count: int = Field(description="模型判定出的槽位数")
    duration_ms: int = Field(description="解析耗时（毫秒）")
    status: str = Field(description="ok / failed")
    error: str | None = Field(None, description="失败原因")
    created_at: datetime = Field(description="解析时间")
    diff: ReportGenStructureDiff = Field(description="与当前结构的差异")


class ReportGenStructureRunListData(BaseModel):
    total: int
    items: list[ReportGenStructureRunData]


class ReportGenFeedbackCreateRequest(BaseModel):
    """提一条评审意见：要么针对整篇，要么针对某个槽位。"""

    slot_key: str | None = Field(None, max_length=100, description="针对的槽位；留空=整篇意见")
    content: str = Field(..., min_length=1, max_length=1000, description="意见内容")


class ReportGenFeedbackUpdateRequest(BaseModel):
    """人工处置意见：不采纳标 ignored，需要重新打开标 open。"""

    status: Literal["open", "ignored"] = Field(description="open=重新待落实 / ignored=不采纳")


class ReportGenFeedbackData(BaseModel):
    id: str
    job_id: str
    slot_key: str | None = Field(None, description="针对的槽位；空=整篇意见")
    content: str
    status: str = Field(description="open / applied / ignored")
    applied_job_id: str | None = Field(None, description="落实该意见的重生成任务")
    created_at: datetime


class ReportGenFeedbackListData(BaseModel):
    total: int = 0
    open_count: int = Field(0, description="待落实条数：下次生成会被自动带上")
    items: list[ReportGenFeedbackData] = Field(default_factory=list)


class ReportGenExamplePromoteData(BaseModel):
    """把一条已落实意见沉淀成槽位示例的结果：下次同模板生成会把它当 few-shot 参照。"""

    feedback_id: str
    slot_key: str
    slot_label: str = ""
    value: str = Field(description="被采纳的槽位写法（来自落实该意见的那次生成）")
    source: str = Field(description="示例来源，沉淀路径固定为 feedback_promoted")
    created: bool = Field(description="true=新建示例 / false=覆盖了该槽位原有示例")


__all__ = [
    "ReportGenExamplePromoteData",
    "ReportGenFeedbackCreateRequest",
    "ReportGenFeedbackData",
    "ReportGenFeedbackListData",
    "ReportGenFeedbackSlotStat",
    "ReportGenFeedbackUpdateRequest",
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
    "ReportGenStructureDiff",
    "ReportGenStructureRunData",
    "ReportGenStructureRunListData",
]
