"""偏差台账 Pydantic 模型（请求 / 视图 / 信封响应）。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from .deviation_ledger_constants import LEDGER_STATUSES


class CrossDeptReviewerItem(BaseModel):
    """跨部门审核行：部门 + 行内调查人 + 逐行审核状态。"""

    department: str
    investigator_ids: list[UUID] = Field(default_factory=list)
    investigator_names: list[str] = Field(default_factory=list)
    reviewer_names: list[str] = Field(default_factory=list, description="该行实际审核人（调查人为空时回退部门负责人）")
    review_state: str = Field("pending", description="行审核状态：pending / approved")
    approved_by: UUID | None = None
    approved_name: str | None = None
    approved_at: datetime | None = None
    opinion: str | None = Field(None, description="该行审核意见")
    can_approve: bool = Field(False, description="当前查看人可对该行执行通过操作")

    @field_validator("department")
    @classmethod
    def _strip_department(cls, value: str) -> str:
        return value.strip()


class CrossDeptStepSubItem(BaseModel):
    """步骤条跨部门环节的逐行子节点。"""

    department: str
    reviewer_names: list[str] = Field(default_factory=list)
    state: str = Field("pending", description="pending / approved")
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    opinion: str | None = None


class CrossDeptApproveRequest(BaseModel):
    """跨部门逐行审批请求体。"""

    department: str = Field(..., min_length=1, max_length=255, description="跨部门部门名（行标识）")
    opinion: str = Field("", max_length=2000, description="审核意见（可选）")

    @field_validator("department")
    @classmethod
    def _strip_department(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("跨部门部门不能为空")
        return cleaned


def _validated_cross_dept_rows(
    needs: bool | None,
    rows: list[CrossDeptReviewerItem] | None,
) -> list[CrossDeptReviewerItem] | None:
    """跨部门行公共校验：部门非空、行间不重复、开启开关至少一行。"""
    if rows is None:
        return rows
    departments = [row.department.strip() for row in rows]
    if any(not department for department in departments):
        raise ValueError("跨部门部门不能为空")
    if len(set(departments)) != len(departments):
        raise ValueError("跨部门部门不能重复")
    if needs and not rows:
        raise ValueError("开启跨部门审核时至少添加一个跨部门")
    return rows


class LedgerCreateRequest(BaseModel):
    """新建偏差请求体。

    发现人默认取当前登录人，可选择实际发现人；上报人取当前登录人。除「是否需要跨部门审核」外均必填。
    """

    title: str = Field(..., min_length=1, max_length=255, description="偏差标题")
    department: str = Field(..., min_length=1, max_length=255, description="所属部门")
    discovery_date: date = Field(..., description="发现日期")
    discovery_time: str = Field(..., description="发现时间 HH:MM")
    discovery_location: str = Field(..., min_length=1, max_length=255, description="发现地点")
    discoverer_id: UUID | None = Field(None, description="发现人（缺省为当前登录人）")
    affected_items: str = Field(..., min_length=1, description="受影响的产品/物料/设备/仪器")
    batch_number: str = Field(..., min_length=1, max_length=255, description="批号/位号/编号")
    handler_ids: list[UUID] = Field(..., min_length=1, description="调查人（可多人）")
    needs_cross_dept_review: bool = Field(False, description="是否需要跨部门审核")
    cross_dept_reviewers: list[CrossDeptReviewerItem] = Field(
        default_factory=list, description="跨部门调查配置（开启跨部门时填写）"
    )
    description: str = Field(..., min_length=1, description="偏差描述")

    @field_validator("title", "department", "discovery_location", "affected_items", "batch_number", "description")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("该字段不能为空")
        return cleaned

    @field_validator("discovery_time")
    @classmethod
    def _check_time(cls, value: str) -> str:
        cleaned = value.strip()
        try:
            hour, minute = cleaned.split(":")
            hour_num, minute_num = int(hour), int(minute)
        except (ValueError, AttributeError) as exc:
            raise ValueError("发现时间格式应为 HH:MM") from exc
        if not (0 <= hour_num <= 23 and 0 <= minute_num <= 59):
            raise ValueError("发现时间超出有效范围")
        return f"{hour_num:02d}:{minute_num:02d}"

    @field_validator("handler_ids")
    @classmethod
    def _check_handlers(cls, value: list[UUID]) -> list[UUID]:
        # 去重并保持顺序，避免前端重复添加同一个人
        seen: set[UUID] = set()
        result: list[UUID] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                result.append(item)
        if not result:
            raise ValueError("请至少选择一名调查人")
        return result

    @field_validator("cross_dept_reviewers")
    @classmethod
    def _check_cross_dept(
        cls,
        value: list[CrossDeptReviewerItem],
        info: ValidationInfo,
    ) -> list[CrossDeptReviewerItem]:
        return _validated_cross_dept_rows(info.data.get("needs_cross_dept_review"), value) or []


class StepHandlerPerson(BaseModel):
    """环节处理人 / 人名展示（含头像，前端统一「头像 + 姓名」）。"""

    id: UUID = Field(..., description="用户 ID")
    name: str = Field("-", description="姓名")
    avatar_url: str | None = Field(None, description="头像地址（飞书缩略图优先）")


class LedgerItem(BaseModel):
    """台账列表行。"""

    id: UUID
    code: str = Field(..., description="系统编号")
    final_code: str | None = Field(None, description="最终编号")
    display_code: str = Field(..., description="展示编号：最终编号优先")
    title: str
    department: str
    discovery_date: date
    status: str
    status_label: str = Field(..., description="状态中文标签")
    is_overdue: bool = Field(False, description="是否超期")
    overdue_days: int = Field(0, description="超期天数")
    current_handler: str | None = Field(None, description="当前处理人姓名或角色名")
    current_handlers: list[StepHandlerPerson] = Field(default_factory=list, description="当前处理人（含头像）")
    deviation_level: str | None = None
    level_label: str = Field("-", description="分级中文标签")
    reporter_name: str | None = None
    reporter: StepHandlerPerson | None = Field(None, description="上报人（含头像）")
    handler_names: list[str] = Field(default_factory=list, description="调查人姓名")
    handlers: list[StepHandlerPerson] = Field(default_factory=list, description="调查人（含头像）")
    returned_step: str | None = None
    returned_step_label: str | None = None
    created_at: datetime


class AttachmentItem(BaseModel):
    """附件元数据（二进制存 MinIO）。"""

    file_id: UUID
    file_name: str
    size: int = 0
    content_type: str | None = None
    uploaded_by: UUID | None = None
    uploaded_by_name: str | None = None
    uploaded_by_avatar: str | None = Field(None, description="上传人头像地址")
    uploaded_at: datetime | None = None


class AiAnalysisData(BaseModel):
    """AI 结构化分析结果。"""

    description: str = ""
    reason: str = ""
    risk_assessment: str = ""
    capa_suggestion: str = ""
    model: str | None = None
    generated_at: datetime | None = None


class CapaProposalItem(BaseModel):
    """CAPA 改进建议条目（内容简述 + 执行人 + 预计完成日期）。"""

    sequence: int = Field(0, ge=0, description="序号，请求方不传时由服务端按顺序回填")
    summary: str = Field(..., min_length=1, max_length=2000, description="CAPA 内容简述")
    executor: str | None = Field(None, max_length=255, description="执行人")
    expected_completion_date: date | None = Field(None, description="预计完成日期")

    @field_validator("summary")
    @classmethod
    def _strip_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("CAPA 内容简述不能为空")
        return cleaned

    @field_validator("executor")
    @classmethod
    def _strip_executor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class InvestigationRecordItem(BaseModel):
    """一条调查记录（结构化；旧记录仅 content，前端降级纯文本展示）。"""

    content: str = Field("", description="旧格式纯文本内容；新记录为空串")
    nonconformity_description: str = Field("", description="不符合事项描述")
    root_cause_analysis: str = Field("", description="根本原因分析")
    risk_assessment: str = Field("", description="风险评估")
    capa_proposals: list[CapaProposalItem] = Field(default_factory=list, description="改进建议（CAPA）")
    urgent_measures: str | None = Field(None, description="紧急处理措施（有值时黄色高亮展示）")
    attachments: list[AttachmentItem] = Field(default_factory=list, description="记录级附件（台账附件引用快照）")
    author_id: UUID | None = None
    author_name: str | None = None
    author_avatar: str | None = Field(None, description="作者头像地址")
    create_time: datetime | None = None


class ReviewOpinionItem(BaseModel):
    """一条审核意见（通过 / 退回 / 重提）。"""

    step: str
    step_label: str | None = None
    result: str
    author_id: UUID | None = None
    author_name: str | None = None
    author_avatar: str | None = Field(None, description="作者头像地址")
    content: str = ""
    create_time: datetime | None = None


class ReportVersionItem(BaseModel):
    """一版调查报告内容。"""

    content: str
    editor_id: UUID | None = None
    editor_name: str | None = None
    editor_avatar: str | None = Field(None, description="编辑人头像地址")
    edit_time: datetime | None = None
    change_summary: str | None = None


class LedgerStep(BaseModel):
    """步骤条单项。"""

    step: str
    label: str
    status: str
    role_label: str
    handlers: list[StepHandlerPerson] = Field(default_factory=list)
    applicable: bool = Field(True, description="本单是否需要经过该环节（步骤条仍展示，仅标注不适用）")
    skip_reason: str | None = Field(None, description="不适用原因（applicable 为 False 时）")
    auto_skip: bool = Field(False, description="该环节无处理人时由系统自动跳过")
    sub_items: list[CrossDeptStepSubItem] = Field(
        default_factory=list,
        description="跨部门环节逐行子节点（其余环节为空）",
    )


class LedgerDetail(LedgerItem):
    """偏差详情：主表 + 调查报告 + AI 分析 + 调查记录 + 审核全过程（无 CAPA）。"""

    discovery_time: str | None = None
    discovery_location: str
    discoverer_name: str | None = None
    discoverer: StepHandlerPerson | None = Field(None, description="发现人（含头像）")
    affected_items: str
    batch_number: str
    description: str
    needs_cross_dept_review: bool = False
    reason_category: str | None = None
    handler_ids: list[UUID] = Field(default_factory=list, description="调查人")
    cross_dept_reviewers: list[CrossDeptReviewerItem] = Field(default_factory=list)
    attachments: list[AttachmentItem] = Field(default_factory=list)
    ai_analysis: AiAnalysisData | None = None
    investigation_records: list[InvestigationRecordItem] = Field(default_factory=list)
    review_opinions: list[ReviewOpinionItem] = Field(default_factory=list)
    report_content: str | None = None
    report_versions: list[ReportVersionItem] = Field(default_factory=list)
    steps: list[LedgerStep] = Field(default_factory=list, description="8 环节步骤条")
    current_step: str | None = Field(None, description="当前环节（退回时为退回环节）")
    current_step_label: str | None = None
    status_updated_at: datetime | None = None
    can_operate: bool = Field(False, description="当前登录人是否可操作当前环节")
    allowed_actions: list[str] = Field(default_factory=list, description="当前登录人可执行的动作")
    editable: bool = Field(False, description="基础信息是否可编辑")
    can_edit_investigation: bool = Field(
        False,
        description="调查人/上报人可否新增调查记录、上传或删除调查文档（调查中与审核阶段均开放）",
    )
    can_edit_cross_dept: bool = Field(
        False,
        description="可否增删改跨部门行（基础信息可编辑；或待调查时由调查人+上报人动态添加审核节点）",
    )


class LedgerListData(BaseModel):
    """台账列表数据体。"""

    items: list[LedgerItem]
    total: int
    page: int
    page_size: int


class DistributionItem(BaseModel):
    """分布图单项。"""

    name: str
    count: int


class StatusDistributionItem(BaseModel):
    """状态分布项。"""

    status: str
    label: str
    count: int


class StepBreakdownItem(BaseModel):
    """环节分布项（步骤条各环节在办数量）。"""

    step: str
    label: str
    role_label: str
    status: str
    count: int = 0


class LedgerStatisticsData(BaseModel):
    """偏差看盘统计。"""

    total: int = 0
    pending: int = 0
    returned: int = 0
    closed: int = 0
    overdue: int = 0
    department_distribution: list[DistributionItem] = Field(default_factory=list)
    status_distribution: list[StatusDistributionItem] = Field(default_factory=list)
    step_breakdown: list[StepBreakdownItem] = Field(default_factory=list)


class OptionItem(BaseModel):
    """下拉候选。"""

    value: str
    label: str
    description: str | None = None


class OptionListData(BaseModel):
    """下拉候选集合。"""

    items: list[OptionItem]


class LedgerUpdateRequest(BaseModel):
    """基础信息修改（待 AI 分析 / 已退回可改全部；待调查仅可改跨部门两字段）。"""

    title: str | None = Field(None, min_length=1, max_length=255)
    department: str | None = Field(None, min_length=1, max_length=255)
    discovery_date: date | None = None
    discovery_time: str | None = None
    discovery_location: str | None = Field(None, min_length=1, max_length=255)
    affected_items: str | None = Field(None, min_length=1)
    batch_number: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    handler_ids: list[UUID] | None = Field(None, min_length=1)
    needs_cross_dept_review: bool | None = None
    cross_dept_reviewers: list[CrossDeptReviewerItem] | None = None

    @field_validator("title", "department", "discovery_location", "affected_items", "batch_number", "description")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("该字段不能为空")
        return cleaned

    @field_validator("cross_dept_reviewers")
    @classmethod
    def _check_cross_dept(
        cls,
        value: list[CrossDeptReviewerItem] | None,
        info: ValidationInfo,
    ) -> list[CrossDeptReviewerItem] | None:
        return _validated_cross_dept_rows(info.data.get("needs_cross_dept_review"), value)


class CompleteAiAnalysisRequest(BaseModel):
    """保存 AI 分析结果：只落库，不流转流程。"""

    ai_analysis: AiAnalysisData


class InvestigationRequest(BaseModel):
    """结构化调查记录（「提交调查」与「追加调查记录」共用）。"""

    nonconformity_description: str = Field(..., min_length=1, max_length=5000, description="不符合事项描述")
    root_cause_analysis: str = Field(..., min_length=1, max_length=5000, description="根本原因分析")
    risk_assessment: str = Field(..., min_length=1, max_length=5000, description="风险评估")
    capa_proposals: list[CapaProposalItem] = Field(..., min_length=1, description="改进建议（CAPA），至少一条")
    urgent_measures: str | None = Field(None, max_length=5000, description="紧急处理措施，勾选后必填")
    attachment_file_ids: list[UUID] = Field(default_factory=list, description="记录附件（已上传台账的 file_id）")

    @field_validator("nonconformity_description", "root_cause_analysis", "risk_assessment")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("该字段不能为空")
        return cleaned

    @field_validator("urgent_measures")
    @classmethod
    def _strip_urgent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("勾选有紧急处理措施时必须填写说明")
        return cleaned

    @field_validator("attachment_file_ids")
    @classmethod
    def _dedup_attachment_ids(cls, value: list[UUID]) -> list[UUID]:
        seen: set[UUID] = set()
        result: list[UUID] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result


class ReviewRequest(BaseModel):
    """审核操作。步骤缺省时按当前状态推导。"""

    step: str | None = Field(None, description="审核环节，缺省按当前状态推导")
    result: str = Field(..., description="approved / rejected")
    content: str = Field("", description="审核意见（退回时必填）")
    reason_category: str | None = Field(None, description="原因分类（QA 审核通过必填）")
    deviation_level: str | None = Field(None, description="偏差分级（QA 负责人通过前必填）")

    @field_validator("result")
    @classmethod
    def _check_result(cls, value: str) -> str:
        if value not in ("approved", "rejected"):
            raise ValueError("结论只能是 approved 或 rejected")
        return value

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        return value.strip()


class ResubmitRequest(BaseModel):
    """退回后重新提交。"""

    content: str = Field("", description="重新提交说明")


class FinalCodeRequest(BaseModel):
    """输入最终编号。"""

    final_code: str = Field(..., min_length=1, max_length=32, description="最终编号")
    content: str = Field("", description="备注")

    @field_validator("final_code")
    @classmethod
    def _strip_code(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("请输入最终编号")
        return cleaned


class ReportSaveRequest(BaseModel):
    """保存调查报告正文并追加版本。"""

    content: str = Field(..., description="报告正文")
    change_summary: str | None = Field(None, max_length=255, description="修改说明")
    append_version: bool = Field(True, description="是否追加版本")


class BatchStatusRequest(BaseModel):
    """批量更新状态。"""

    ids: list[UUID] = Field(..., min_length=1, max_length=200)
    status: str = Field(..., description="目标状态")

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: str) -> str:
        if value not in LEDGER_STATUSES:
            raise ValueError("非法状态")
        return value


class AttachmentListData(BaseModel):
    """附件列表。"""

    items: list[AttachmentItem] = Field(default_factory=list)


class AttachmentCommentCreateRequest(BaseModel):
    """新增文档批注。"""

    content: str = Field(..., min_length=1, max_length=2000, description="批注正文")
    page_no: int | None = Field(None, ge=1, description="页码（1 起），文档级批注留空")
    anchor_text: str | None = Field(None, max_length=500, description="选中文本锚点（预留）")

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("批注内容不能为空")
        return cleaned

    @field_validator("anchor_text")
    @classmethod
    def _strip_anchor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AttachmentCommentUpdateRequest(BaseModel):
    """修改批注内容或处理状态（两者至少一个）。"""

    content: str | None = Field(None, min_length=1, max_length=2000, description="批注正文")
    status: Literal["open", "resolved"] | None = Field(None, description="处理状态：open / resolved")

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("批注内容不能为空")
        return cleaned


class AttachmentCommentItem(BaseModel):
    """一条文档批注。"""

    id: UUID
    ledger_id: UUID
    file_id: UUID
    file_name: str
    page_no: int | None = Field(None, description="页码（1 起）")
    anchor_text: str | None = None
    content: str
    status: str = Field("open", description="open / resolved")
    author_id: UUID | None = None
    author_name: str | None = None
    author_avatar: str | None = Field(None, description="作者头像地址")
    resolved_by: UUID | None = None
    resolved_by_name: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AttachmentCommentListData(BaseModel):
    """某附件的批注列表。"""

    items: list[AttachmentCommentItem] = Field(default_factory=list)
    total: int = 0
    open_count: int = 0


class AttachmentCommentSummaryItem(BaseModel):
    """单个附件的批注计数（未处理 / 全部）。"""

    file_id: UUID
    open_count: int = 0
    total_count: int = 0


class AttachmentCommentSummaryData(BaseModel):
    """详情页附件角标用的批注汇总。"""

    items: list[AttachmentCommentSummaryItem] = Field(default_factory=list)


class BatchResultData(BaseModel):
    """批量操作结果。"""

    updated: int = 0


class DeleteResultData(BaseModel):
    """删除结果。"""

    id: UUID
    deleted: bool = True


# ============ 信封响应（code / data / message / meta） ============


class LedgerListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: LedgerListData
    meta: dict[str, Any] | None = None


class LedgerDetailApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: LedgerDetail
    meta: dict[str, Any] | None = None


class LedgerStatisticsApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: LedgerStatisticsData
    meta: dict[str, Any] | None = None


class LedgerOptionsApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: OptionListData
    meta: dict[str, Any] | None = None


class AttachmentListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AttachmentListData
    meta: dict[str, Any] | None = None


class AttachmentCommentApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AttachmentCommentItem
    meta: dict[str, Any] | None = None


class AttachmentCommentListApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AttachmentCommentListData
    meta: dict[str, Any] | None = None


class AttachmentCommentSummaryApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AttachmentCommentSummaryData
    meta: dict[str, Any] | None = None


class BatchResultApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: BatchResultData
    meta: dict[str, Any] | None = None


class DeleteResultApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DeleteResultData
    meta: dict[str, Any] | None = None


def status_options() -> list[OptionItem]:
    """把 12 态常量转成下拉候选。"""
    from .deviation_ledger_constants import status_label

    return [OptionItem(value=value, label=status_label(value)) for value in LEDGER_STATUSES]
