"""Safety request and response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.modules.safety.schemas.enums import HazardLevel, HazardType
from app.modules.safety.schemas.person_ref import PersonRef


class RectificationReplyRequest(BaseModel):
    """整改回复请求（合并了原 complete_rectification 步骤）"""

    reply_content: str = Field(..., description="整改回复内容")
    rectification_photos: str | None = Field(None, description="整改后图片JSON数组")
    corrective_preventive_measures: str | None = Field(None, description="AI整改建议（兼容旧字段）")
    rectification_reply: str | None = Field(None, description="整改回复内容（新字段）")
    capa_measures: str | None = Field(None, description="纠正预防措施（人工填写）")
    actual_completion_date: datetime | None = Field(None, description="整改完成时间（默认当前时间）")
    rectification_progress_note: str | None = Field(None, description="整改进度说明")


class VerifyLevelRequest(BaseModel):
    """三级复核请求"""

    level: int = Field(..., ge=1, le=3, description="复核级别: 1/2/3")
    action: str = Field(..., description="approved | rejected")
    opinion: str | None = Field(None, description="复核意见")


class ConfirmCheckRequest(BaseModel):
    """确认检查请求"""

    role: str = Field(..., description="确认角色: inspector / safety_officer")


class HazardStatsResponse(BaseModel):
    """隐患统计（全局，不受分页/筛选影响）"""

    total: int = 0
    pending_review: int = 0
    pending: int = 0
    in_progress: int = 0
    replied: int = 0
    verifying: int = 0
    rejected: int = 0
    closed: int = 0
    overdue: int = 0


class HazardReportBase(BaseModel):
    """隐患报告基础模式"""

    hazard_no: str = Field(..., max_length=64, description="隐患编号")
    inspection_name: str | None = Field(None, max_length=255, description="检查名称")
    inspection_category: str | None = Field(None, max_length=64, description="检查类别（日常检查/专项检查…）")
    hazard_type: HazardType = Field(..., description="隐患分类（人/物/环/管）")
    hazard_level: HazardLevel = Field(HazardLevel.GENERAL, description="隐患等级")
    hazard_category: str | None = Field(None, max_length=64, description="隐患类别（字典表名称）")
    description: str = Field(..., description="隐患描述")
    discovered_by: uuid.UUID | None = Field(None, description="发现人")
    discovered_by_name: str | None = Field(None, max_length=100, description="检查人员姓名")
    inspector_department: str | None = Field(None, max_length=500, description="检查人员部门（Bitable 多选，逗号分隔）")
    discovered_at: datetime = Field(..., description="检查日期")
    department: str | None = Field(None, max_length=100, description="责任部门")
    major_hazard_basis: str | None = Field(None, description="隐患判定依据（AI）")
    key_defect: str | None = Field(None, description="隐患描述（AI）")
    defect_photos: str | None = Field(None, description="缺陷图片JSON数组")
    rectification_responsible_person: uuid.UUID | None = Field(None, description="整改责任人（FK → identity.users）")
    rectification_responsible_person_name: str | None = Field(None, max_length=100, description="整改责任人姓名")
    rectification_responsible_person_ids: list[str] | None = Field(None, description="整改负责人多选 UUID 列表")
    rectification_responsible_person_names: str | None = Field(
        None, max_length=500, description="整改负责人姓名快照（逗号分隔）"
    )
    rectification_progress_note: str | None = Field(None, description="整改进度说明（自定义文字）")
    corrective_preventive_measures: str | None = Field(None, description="AI整改建议")
    rectification_reply: str | None = Field(None, description="整改回复内容")
    capa_measures: str | None = Field(None, description="纠正预防措施（人工填写）")
    deadline: datetime | None = Field(None, description="目标完成日期")
    actual_completion_date: datetime | None = Field(None, description="整改完成时间")
    rectification_photos: str | None = Field(None, description="整改后图片JSON数组")
    check_id: uuid.UUID | None = Field(None, description="关联检查ID")
    notes: str | None = Field(None, description="备注")


class HazardReportCreate(HazardReportBase):
    """创建隐患报告"""

    hazard_no: str | None = Field(  # type: ignore[assignment]
        None, max_length=64, description="隐患编号（留空自动生成）"
    )
    hazard_type: HazardType | None = Field(None, description="隐患分类")  # type: ignore[assignment]
    hazard_level: HazardLevel | None = Field(None, description="隐患等级")  # type: ignore[assignment]
    hazard_category: str | None = Field(None, max_length=64, description="隐患类别（字典表名称）")
    description: str | None = Field(None, description="隐患描述")  # type: ignore[assignment]
    discovered_at: datetime | None = Field(None, description="发现时间")  # type: ignore[assignment]
    overall_status: str | None = Field(
        None, max_length=20, description="整体状态（draft=草稿，completed=正式登记）"
    )


class HazardReportUpdate(BaseModel):
    """更新隐患报告"""

    hazard_no: str | None = Field(None, max_length=64, description="隐患编号")
    inspection_name: str | None = Field(None, max_length=255, description="检查名称")
    inspection_category: str | None = Field(None, max_length=64, description="检查类别（日常检查/专项检查…）")
    hazard_type: HazardType | None = Field(None, description="隐患分类")
    hazard_level: HazardLevel | None = Field(None, description="隐患等级")
    hazard_category: str | None = Field(None, max_length=64, description="隐患类别（字典表名称）")
    description: str | None = Field(None, description="隐患描述")
    discovered_by: uuid.UUID | None = Field(None, description="发现人（FK → identity.users）")
    discovered_by_name: str | None = Field(None, max_length=100, description="检查人员姓名")
    discovered_at: datetime | None = Field(None, description="检查日期")
    department: str | None = Field(None, max_length=100, description="责任部门")
    inspector_department: str | None = Field(None, max_length=500, description="检查人员部门（Bitable 多选，逗号分隔）")
    major_hazard_basis: str | None = Field(None, description="隐患判定依据（AI）")
    key_defect: str | None = Field(None, description="隐患描述（AI）")
    defect_photos: str | None = Field(None, description="缺陷图片JSON数组")
    rectification_responsible_person: uuid.UUID | None = Field(None, description="整改责任人（FK → identity.users）")
    rectification_responsible_person_name: str | None = Field(None, max_length=100, description="整改责任人姓名")
    rectification_responsible_person_ids: list[str] | None = Field(None, description="整改负责人多选 UUID 列表")
    rectification_responsible_person_names: str | None = Field(
        None, max_length=500, description="整改负责人姓名快照（逗号分隔）"
    )
    rectification_progress_note: str | None = Field(None, description="整改进度说明")
    corrective_preventive_measures: str | None = Field(None, description="AI整改建议")
    rectification_reply: str | None = Field(None, description="整改回复内容")
    capa_measures: str | None = Field(None, description="纠正预防措施（人工填写）")
    deadline: datetime | None = Field(None, description="目标完成日期")
    actual_completion_date: datetime | None = Field(None, description="整改完成时间")
    rectification_photos: str | None = Field(None, description="整改后图片JSON数组")
    rectification_status: str | None = Field(None, max_length=32, description="整改进度")
    status: str | None = Field(None, max_length=32, description="状态")
    notes: str | None = Field(None, description="备注")
    # ── AI 流程字段 ──
    ai_node_progress: str | None = Field(None, max_length=50, description="AI流程节点进度")
    overall_status: str | None = Field(None, max_length=20, description="整体状态")
    ai_error_message: str | None = Field(None, description="AI错误信息")
    script1_review_status: str | None = Field(None, max_length=20, description="AI隐患识别审核状态")
    script2_review_status: str | None = Field(None, max_length=20, description="AI整改建议审核状态")


class HazardReportResponse(HazardReportBase):
    """隐患报告响应"""

    id: uuid.UUID
    rectification_status: str
    status: str
    closed_at: datetime | None = None
    # ── 三级复核 ──
    verify_level_1_status: str = "pending"
    verify_level_2_status: str = "pending"
    verify_level_3_status: str = "pending"
    # ── 审批人留痕（每级只保留最后一次）──
    verify_level_1_reviewer_id: uuid.UUID | None = None
    verify_level_1_reviewer_name: str | None = None
    verify_level_1_reviewed_at: datetime | None = None
    verify_level_2_reviewer_id: uuid.UUID | None = None
    verify_level_2_reviewer_name: str | None = None
    verify_level_2_reviewed_at: datetime | None = None
    verify_level_3_reviewer_id: uuid.UUID | None = None
    verify_level_3_reviewer_name: str | None = None
    verify_level_3_reviewed_at: datetime | None = None
    # ── AI 流程字段 ──
    ai_node_progress: str = "pending_input"
    overall_status: str = "draft"
    ai_error_message: str | None = None
    script1_review_status: str = "pending"
    script2_review_status: str = "pending"
    # ── AI 整改初审 ──
    ai_review_result: dict[str, Any] | None = None
    ai_review_status: str = "pending"
    ai_review_completed_at: datetime | None = None
    ai_generated: bool = False
    created_at: datetime
    updated_at: datetime
    # ── 飞书通知追踪 ──
    rectification_notified_at: datetime | None = None
    rectification_notify_status: str | None = None
    rectification_notify_error: str | None = None
    review_notified_at: datetime | None = None
    review_notified_level: int | None = None
    review_notify_status: str | None = None
    review_notify_error: str | None = None
    # ── 人员引用（读时解析：UUID 命中 → 系统用户；仅姓名 → 唯一命中兜底）──
    discovered_by_person: PersonRef | None = Field(None, description="检查人员/审批人（含头像）")
    rectification_responsible_persons: list[PersonRef] = Field(
        default_factory=list, description="整改负责人（顺序与 rectification_responsible_person_names 一致）"
    )

    class Config:
        from_attributes = True


class HazardReportRunAIRequest(BaseModel):
    """执行隐患AI工作流请求（AI从已有数据读取上下文）"""

    pass


class DepartmentLeaderResponse(BaseModel):
    """部门负责人查询响应"""

    department: str = Field(..., description="部门名称")
    leader_name: str | None = Field(None, description="负责人姓名")
    leader_id: str | None = Field(None, description="负责人 UUID")


class DepartmentSafetyOfficerResponse(BaseModel):
    """部门分管安全员查询响应"""

    department: str = Field(..., description="部门名称")
    safety_officer_name: str | None = Field(None, description="安全员姓名")
    safety_officer_id: str | None = Field(None, description="安全员 UUID")


# ============ API Response Wrappers ============


class HazardApiResponse(BaseModel):
    """Single hazard response wrapper"""

    code: int = 200
    message: str = "success"
    data: HazardReportResponse | None = None


class HazardListApiResponse(BaseModel):
    """Hazard list response wrapper"""

    code: int = 200
    message: str = "success"
    data: list[HazardReportResponse]
    meta: dict[str, Any] | None = None


class HazardStatsApiResponse(BaseModel):
    """Hazard statistics response wrapper"""

    code: int = 200
    message: str = "success"
    data: HazardStatsResponse


class DepartmentLeaderApiResponse(BaseModel):
    """Department leader response wrapper"""

    code: int = 200
    message: str = "success"
    data: DepartmentLeaderResponse | None = None


class DepartmentSafetyOfficerApiResponse(BaseModel):
    """Department safety officer response wrapper"""

    code: int = 200
    message: str = "success"
    data: DepartmentSafetyOfficerResponse | None = None


class HazardVerifyNotifyData(BaseModel):
    """复核通知发送结果"""

    level: int = Field(..., description="当前复核级别：1 部门负责人 / 2 分管领导 / 3 检查人员")
    level_label: str = Field(..., description="复核级别名称")


class HazardVerifyNotifyApiResponse(BaseModel):
    """复核通知响应包装"""

    code: int = 200
    message: str = "success"
    data: HazardVerifyNotifyData | None = None


class HazardRectificationNotifyData(BaseModel):
    """整改通知发送结果"""

    target: str = Field(..., description="整改责任人姓名，未知时为「未知」")


class HazardRectificationNotifyApiResponse(BaseModel):
    """整改通知响应包装"""

    code: int = 200
    message: str = "success"
    data: HazardRectificationNotifyData | None = None


class HazardAiRunData(BaseModel):
    """AI 工作流提交结果（后端异步执行，前端轮询隐患详情取最终结果）"""

    job_id: str = Field(..., description="后台任务 ID")
    hazard_id: str = Field(..., description="隐患 ID")
    script_number: int = Field(..., description="AI 工作流脚本编号")


class HazardAiRunApiResponse(BaseModel):
    """AI 工作流提交响应包装"""

    code: int = 200
    message: str = "success"
    data: HazardAiRunData | None = None


# ============ 隐患类别字典 ============


class HazardCategoryCreate(BaseModel):
    """新增隐患类别请求"""

    name: str = Field(..., min_length=1, max_length=64, description="类别名称")


class HazardCategoryResponse(BaseModel):
    """隐患类别项"""

    id: str | None = Field(None, description="字典记录 ID（内置类别为 None）")
    name: str = Field(..., description="类别名称")
    sort_order: int = Field(0, description="排序值，越小越前")
    is_builtin: bool = Field(False, description="是否内置类别（不可删除）")


class HazardCategoryListApiResponse(BaseModel):
    """隐患类别列表响应包装"""

    code: int = 200
    message: str = "success"
    data: list[HazardCategoryResponse]


class HazardCategoryApiResponse(BaseModel):
    """单个隐患类别响应包装"""

    code: int = 200
    message: str = "success"
    data: HazardCategoryResponse | None = None
