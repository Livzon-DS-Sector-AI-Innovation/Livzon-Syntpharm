"""Research request and response schemas."""

import uuid
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ResearchProjectStage = Literal["立项", "研发中试", "验证", "注册", "商业化"]
ResearchProjectStatus = Literal["进行中", "已暂停", "已完成", "已终止"]


class ResearchProjectCreate(BaseModel):
    """创建研发项目请求"""

    project_no: str | None = Field(default=None, max_length=50, description="项目编号（可选，不填则自动生成）")
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    project_type: str | None = Field(default=None, max_length=100, description="项目类型")
    stage: ResearchProjectStage = Field(default="立项", description="项目阶段")
    status: ResearchProjectStatus = Field(default="进行中", description="项目状态")
    leader: str | None = Field(default=None, max_length=100, description="项目负责人")
    start_date: date | None = Field(default=None, description="开始日期")
    end_date: date | None = Field(default=None, description="结束日期")
    description: str | None = Field(default=None, description="项目描述")


class ResearchProjectUpdate(BaseModel):
    """更新研发项目请求"""

    project_no: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    project_type: str | None = Field(default=None, max_length=100)
    stage: ResearchProjectStage | None = None
    status: ResearchProjectStatus | None = None
    leader: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class ResearchProjectResponse(BaseModel):
    """研发项目响应"""

    id: uuid.UUID
    project_no: str
    name: str
    project_type: str | None
    stage: str
    status: str
    leader: str | None
    start_date: date | None
    end_date: date | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None

    model_config = {"from_attributes": True}


class EDBOOptimizeRequest(BaseModel):
    """EDBO+ 贝叶斯优化请求"""

    objectives: list[str] = Field(..., min_length=1, description="目标列名列表")
    objective_modes: list[Literal["max", "min"]] = Field(
        ..., min_length=1, description="目标方向（max/min），与 objectives 一一对应"
    )
    batch_size: int = Field(default=5, ge=1, le=100, description="建议实验数量")


class EDBOOptimizeResponse(BaseModel):
    """EDBO+ 贝叶斯优化响应"""

    csv_data: str = Field(..., description="结果 CSV 文本")
    row_count: int = Field(..., description="结果行数")
    prediction_data: str | None = Field(None, description="预测文件 CSV 文本（可选）")
    prediction_filename: str | None = Field(None, description="预测文件名（可选）")


# ===== Pilot Workflow Schemas =====

PilotWorkflowStatus = Literal["pending", "running", "waiting_approval", "completed", "failed"]
PilotWorkflowStepStatus = Literal["pending", "running", "waiting_approval", "completed", "failed", "skipped"]


class PilotWorkflowCreate(BaseModel):
    """创建中试研究"""

    project_id: uuid.UUID | None = Field(default=None, description="关联研发项目ID")
    product_name: str = Field(..., min_length=1, max_length=200, description="产品名称")
    scale_up_ratio: float = Field(..., gt=0, description="放大倍数")
    equipment_type: str = Field(..., min_length=1, max_length=100, description="设备类型")
    equipment_volume: float = Field(..., gt=0, description="设备容积(L)")
    input_context: dict[str, Any] | None = Field(default=None, description="额外上下文信息")


class PilotWorkflowStepResponse(BaseModel):
    """工作流步骤响应"""

    id: uuid.UUID
    workflow_id: uuid.UUID
    step_order: int
    step_code: str
    step_name: str
    status: str
    input_data: dict[str, Any] | None
    output_data: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PilotWorkflowResponse(BaseModel):
    """工作流响应"""

    id: uuid.UUID
    project_id: uuid.UUID | None
    product_name: str
    scale_up_ratio: float
    equipment_type: str
    equipment_volume: float
    input_document_path: str | None
    input_context: dict[str, Any] | None
    status: str
    final_report: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    steps: list[PilotWorkflowStepResponse] = []

    model_config = {"from_attributes": True}


class PilotWorkflowListResponse(BaseModel):
    """工作流列表响应"""

    id: uuid.UUID
    product_name: str
    scale_up_ratio: float
    equipment_type: str
    equipment_volume: float
    status: str
    created_at: datetime
    step_count: int = 0
    completed_step_count: int = 0

    model_config = {"from_attributes": True}


# Alias for backward compatibility
PilotWorkflowListItem = PilotWorkflowListResponse


# ===== Rd Project Schemas (from rd_project) =====


class RdProjectBase(BaseModel):
    name: str = Field(..., max_length=200, description="品种名称")
    api_name: str = Field(..., max_length=200, description="API全称")
    cas_number: str | None = Field(None, max_length=50, description="CAS号")
    molecular_formula: str | None = Field(None, max_length=200, description="分子式")
    molecular_weight: float | None = Field(None, description="分子量")
    indication: str | None = Field(None, max_length=500, description="适应症")
    project_type: str | None = Field(None, max_length=50, description="generic/improved")
    priority: str = Field("normal", max_length=20, description="low/normal/high/urgent")
    project_manager_id: UUID | None = Field(None, description="项目经理ID")
    start_date: date | None = Field(None, description="开始日期")
    target_filing_date: date | None = Field(None, description="目标申报日期")
    notes: str | None = Field(None, description="备注")
    current_stage: str | None = Field(None, max_length=50, description="起始阶段")


class RdProjectCreate(RdProjectBase):
    pass


class RdProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    api_name: str | None = Field(None, max_length=200)
    cas_number: str | None = Field(None, max_length=50)
    molecular_formula: str | None = Field(None, max_length=200)
    molecular_weight: float | None = None
    indication: str | None = Field(None, max_length=500)
    project_type: str | None = Field(None, max_length=50)
    priority: str | None = Field(None, max_length=20)
    project_manager_id: UUID | None = None
    start_date: date | None = None
    target_filing_date: date | None = None
    actual_filing_date: date | None = None
    current_stage: str | None = Field(None, max_length=50)
    overall_progress: float | None = None
    notes: str | None = None


class RdProjectResponse(RdProjectBase):
    id: UUID
    status: str
    current_stage: str | None
    overall_progress: float | None
    actual_filing_date: date | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    model_config = {"from_attributes": True}


# ===== Milestone Schemas =====


class RdMilestoneBase(BaseModel):
    title: str = Field(..., max_length=200, description="标题")
    milestone_type: str | None = Field(None, max_length=50, description="gate_review/decision/achievement")
    stage: str | None = Field(None, max_length=50, description="关联阶段")
    planned_date: date | None = Field(None, description="计划日期")
    decision: str | None = Field(None, max_length=50, description="go/no_go/hold/conditional")
    decision_rationale: str | None = Field(None, description="决策理由")


class RdMilestoneCreate(RdMilestoneBase):
    pass


class RdMilestoneUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    milestone_type: str | None = Field(None, max_length=50)
    stage: str | None = Field(None, max_length=50)
    status: str | None = Field(None, max_length=50)
    planned_date: date | None = None
    actual_date: date | None = None
    decision: str | None = Field(None, max_length=50)
    decision_rationale: str | None = None


class RdMilestoneResponse(RdMilestoneBase):
    id: UUID
    project_id: UUID
    status: str
    actual_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===== Stage Record Schemas =====


class RdStageRecordBase(BaseModel):
    stage: str = Field(
        ...,
        max_length=50,
        description="initiation/route_dev/optimization/pilot/validation/filing",
    )
    version: int = Field(1, description="版本号")
    input_summary: dict[str, Any] | None = Field(None, description="上游输入摘要")
    input_references: dict[str, Any] | None = Field(None, description="关联的上游记录ID")
    output_summary: dict[str, Any] | None = Field(None, description="产出摘要")
    deliverables: dict[str, Any] | None = Field(None, description="产出物列表")


class RdStageRecordCreate(RdStageRecordBase):
    pass


class RdStageRecordUpdate(BaseModel):
    status: str | None = Field(None, max_length=50)
    input_summary: dict[str, Any] | None = None
    input_references: dict[str, Any] | None = None
    output_summary: dict[str, Any] | None = None
    deliverables: dict[str, Any] | None = None
    gate_review_status: str | None = Field(None, max_length=50)
    gate_hard_conditions: dict[str, Any] | None = None
    gate_soft_conditions: dict[str, Any] | None = None
    gate_review_notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RdStageRecordResponse(RdStageRecordBase):
    id: UUID
    project_id: UUID
    status: str
    gate_review_status: str | None
    gate_reviewed_at: datetime | None
    gate_reviewed_by: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===== Research Track Schemas =====


class RdResearchTrackBase(BaseModel):
    type: str = Field(
        ...,
        max_length=50,
        description="impurity/crystal_form/stability/quality_standard/custom",
    )
    name: str = Field(..., max_length=200, description="研究项名称")
    description: str | None = Field(None, description="描述")
    priority: str = Field("normal", max_length=20, description="low/normal/high/urgent")
    owner_id: UUID | None = Field(None, description="负责人ID")


class RdResearchTrackCreate(RdResearchTrackBase):
    pass


class RdResearchTrackUpdate(BaseModel):
    type: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    status: str | None = Field(None, max_length=50)
    priority: str | None = Field(None, max_length=20)
    current_conclusion: str | None = None
    conclusion_version: int | None = None
    conclusion_confidence: str | None = Field(None, max_length=50)
    active_stages: list[str] | None = None
    owner_id: UUID | None = None


class RdResearchTrackResponse(RdResearchTrackBase):
    id: UUID
    project_id: UUID
    status: str
    current_conclusion: str | None
    conclusion_version: int
    conclusion_confidence: str | None
    active_stages: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===== Research Finding Schemas =====


class RdResearchFindingBase(BaseModel):
    finding_type: str | None = Field(
        None,
        max_length=50,
        description="identification/classification/control_strategy/characterization",
    )
    data: dict[str, Any] | None = Field(None, description="结构化数据")
    conclusion: str | None = Field(None, description="结论")
    confidence: str = Field("preliminary", max_length=50, description="preliminary/confirmed/final")
    experiment_date: date | None = None
    operator: str | None = None
    experiment_conditions: dict[str, Any] | None = None
    materials_used: dict[str, Any] | None = None
    equipment_used: dict[str, Any] | None = None
    spectra_refs: dict[str, Any] | None = None
    analytical_results: dict[str, Any] | None = None
    observations: str | None = None
    attachments: dict[str, Any] | None = None
    notes: str | None = None


class RdResearchFindingCreate(RdResearchFindingBase):
    stage_record_id: UUID | None = Field(None, description="关联阶段记录ID")


class RdResearchFindingUpdate(BaseModel):
    finding_type: str | None = Field(None, max_length=50)
    data: dict[str, Any] | None = None
    conclusion: str | None = None
    confidence: str | None = Field(None, max_length=50)
    experiment_date: date | None = None
    operator: str | None = None
    experiment_conditions: dict[str, Any] | None = None
    materials_used: dict[str, Any] | None = None
    equipment_used: dict[str, Any] | None = None
    spectra_refs: dict[str, Any] | None = None
    analytical_results: dict[str, Any] | None = None
    observations: str | None = None
    attachments: dict[str, Any] | None = None
    notes: str | None = None
    version: int | None = None


class RdResearchFindingResponse(RdResearchFindingBase):
    id: UUID
    track_id: UUID
    stage_record_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    model_config = {"from_attributes": True}


# Rebuild models to resolve forward references
RdProjectResponse.model_rebuild()
RdMilestoneResponse.model_rebuild()
RdStageRecordResponse.model_rebuild()
RdResearchTrackResponse.model_rebuild()
RdResearchFindingResponse.model_rebuild()


# ===== 中试研究 Schemas =====


class RdPilotStudyBase(BaseModel):
    project_id: UUID
    stage_record_id: UUID | None = None
    material_balance: dict[str, Any] | None = None
    equipment_selection: dict[str, Any] | None = None
    engineering_calc: dict[str, Any] | None = None
    ehs_assessment: dict[str, Any] | None = None
    scale_up_effect: dict[str, Any] | None = None
    batch_no: str | None = Field(None, max_length=100)
    batch_size: float | None = None
    status: str = Field("draft", max_length=50)
    notes: str | None = None


class RdPilotStudyCreate(RdPilotStudyBase):
    pass


class RdPilotStudyUpdate(BaseModel):
    material_balance: dict[str, Any] | None = None
    equipment_selection: dict[str, Any] | None = None
    engineering_calc: dict[str, Any] | None = None
    ehs_assessment: dict[str, Any] | None = None
    scale_up_effect: dict[str, Any] | None = None
    batch_no: str | None = Field(None, max_length=100)
    batch_size: float | None = None
    status: str | None = Field(None, max_length=50)
    notes: str | None = None


class RdPilotStudyResponse(RdPilotStudyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== 工艺验证 Schemas =====


class RdProcessValidationBase(BaseModel):
    project_id: UUID
    stage_record_id: UUID | None = None
    validation_protocol: dict[str, Any] | None = None
    validation_batches: dict[str, Any] | None = None
    statistical_analysis: dict[str, Any] | None = None
    validation_conclusion: str | None = None
    status: str = Field("draft", max_length=50)
    notes: str | None = None


class RdProcessValidationCreate(RdProcessValidationBase):
    pass


class RdProcessValidationUpdate(BaseModel):
    validation_protocol: dict[str, Any] | None = None
    validation_batches: dict[str, Any] | None = None
    statistical_analysis: dict[str, Any] | None = None
    validation_conclusion: str | None = None
    status: str | None = Field(None, max_length=50)
    notes: str | None = None


class RdProcessValidationResponse(RdProcessValidationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== 申报资料 Schemas =====


class RdRegistrationFilingBase(BaseModel):
    project_id: UUID
    stage_record_id: UUID | None = None
    ctd_structure: dict[str, Any] | None = None
    filing_progress: dict[str, Any] | None = None
    supplementary_docs: dict[str, Any] | None = None
    status: str = Field("draft", max_length=50)
    notes: str | None = None


class RdRegistrationFilingCreate(RdRegistrationFilingBase):
    pass


class RdRegistrationFilingUpdate(BaseModel):
    ctd_structure: dict[str, Any] | None = None
    filing_progress: dict[str, Any] | None = None
    supplementary_docs: dict[str, Any] | None = None
    status: str | None = Field(None, max_length=50)
    notes: str | None = None


class RdRegistrationFilingResponse(RdRegistrationFilingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== Stage Deliverable Schemas =====


class RdStageDeliverableBase(BaseModel):
    project_id: UUID = Field(..., description="项目ID")
    stage: str = Field(..., max_length=50, description="阶段")
    deliverable_type: str = Field(..., max_length=100, description="交付物类型")
    title: str = Field(..., max_length=500, description="标题")
    status: str = Field("draft", max_length=50, description="draft/in_progress/completed/approved")
    version: str = Field("v1.0", max_length=50, description="版本号")
    file_url: str | None = Field(None, max_length=1000, description="附件URL")
    file_name: str | None = Field(None, max_length=500, description="文件名")
    file_size: int | None = Field(None, description="文件大小(字节)")
    content: str | None = Field(None, description="内容(富文本)")
    owner_id: UUID | None = Field(None, description="负责人")


class RdStageDeliverableCreate(RdStageDeliverableBase):
    pass


class RdStageDeliverableUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    status: str | None = Field(None, max_length=50)
    version: str | None = Field(None, max_length=50)
    file_url: str | None = Field(None, max_length=1000)
    file_name: str | None = Field(None, max_length=500)
    file_size: int | None = None
    content: str | None = None
    owner_id: UUID | None = None


class RdStageDeliverableResponse(RdStageDeliverableBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None


# ===== 交付物类型配置 =====

DELIVERABLE_TYPES = {
    "initiation": [
        {"type": "literature_review", "label": "技术调研报告"},
        {"type": "development_plan", "label": "研发总方案"},
    ],
    "route_dev": [
        {"type": "route_confirmation", "label": "工艺路线确认报告"},
        {"type": "safety_assessment", "label": "工艺安全评估报告"},
        {"type": "impurity_analysis", "label": "理论杂质分析"},
    ],
    "optimization": [
        {"type": "optimization_plan", "label": "小试工艺优化方案"},
        {"type": "optimization_report", "label": "小试工艺优化报告"},
        {"type": "scale_up_summary", "label": "公斤级放大总结报告"},
    ],
    "pilot": [
        {"type": "pilot_plan", "label": "中试方案"},
        {"type": "pilot_report", "label": "中试报告"},
        {"type": "supplier_development", "label": "供应商开发报告"},
    ],
    "validation": [
        {"type": "validation_plan", "label": "工艺验证方案"},
        {"type": "validation_report", "label": "工艺验证报告"},
        {"type": "cleaning_procedure", "label": "清洁操作规程和记录"},
        {"type": "cleaning_validation", "label": "清洁验证总结报告"},
    ],
    "filing": [
        {"type": "structure_confirmation", "label": "原料药结构确证报告"},
        {"type": "crystal_form_study", "label": "晶型和粒度研究报告"},
        {"type": "impurity_study", "label": "杂质研究报告"},
    ],
}


# ===== 实验记录 Schemas =====


class RdExperimentLogBase(BaseModel):
    project_id: UUID
    stage_record_id: UUID | None = None
    title: str = Field(..., max_length=300)
    experiment_type: str = Field(..., max_length=50)
    experiment_date: date | None = None
    operator: str | None = Field(None, max_length=100)
    status: str = Field("planned", max_length=50)
    objective: str | None = None
    materials: dict[str, Any] | None = None
    equipment: dict[str, Any] | None = None
    procedure: str | None = None
    process_params: dict[str, Any] | None = None
    observations: str | None = None
    results: dict[str, Any] | None = None
    conclusion: str | None = None
    issues: str | None = None
    next_steps: str | None = None
    notes: str | None = None


class RdExperimentLogCreate(RdExperimentLogBase):
    pass


class RdExperimentLogUpdate(BaseModel):
    title: str | None = Field(None, max_length=300)
    experiment_type: str | None = Field(None, max_length=50)
    experiment_date: date | None = None
    operator: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=50)
    objective: str | None = None
    materials: dict[str, Any] | None = None
    equipment: dict[str, Any] | None = None
    procedure: str | None = None
    process_params: dict[str, Any] | None = None
    observations: str | None = None
    results: dict[str, Any] | None = None
    conclusion: str | None = None
    issues: str | None = None
    next_steps: str | None = None
    notes: str | None = None


class RdExperimentLogResponse(RdExperimentLogBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== 研发报告 Schemas =====


class RdReportBase(BaseModel):
    project_id: UUID
    title: str = Field(..., max_length=500)
    report_type: str = Field(..., max_length=50)
    stage: str | None = Field(None, max_length=50)
    status: str = Field("draft", max_length=50)
    version: str = Field("v1.0", max_length=50)
    content: str | None = None
    summary: str | None = None
    key_findings: dict[str, Any] | None = None
    recommendations: str | None = None
    author_id: UUID | None = None
    reviewer_id: UUID | None = None
    notes: str | None = None


class RdReportCreate(RdReportBase):
    pass


class RdReportUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    report_type: str | None = Field(None, max_length=50)
    stage: str | None = Field(None, max_length=50)
    status: str | None = Field(None, max_length=50)
    version: str | None = Field(None, max_length=50)
    content: str | None = None
    summary: str | None = None
    key_findings: dict[str, Any] | None = None
    recommendations: str | None = None
    reviewer_id: UUID | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None


class RdReportResponse(RdReportBase):
    id: UUID
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== 立项申请 Schemas =====


class RdInitiationBase(BaseModel):
    project_id: UUID
    project_background: str | None = None
    market_analysis: str | None = None
    technical_feasibility: str | None = None
    resource_requirements: dict[str, Any] | None = None
    timeline_plan: dict[str, Any] | None = None
    risk_assessment: dict[str, Any] | None = None
    expected_outcomes: str | None = None
    applicant_id: UUID | None = None
    application_date: date | None = None
    review_status: str = Field("pending", max_length=50)
    reviewer_id: UUID | None = None
    review_date: date | None = None
    review_comments: str | None = None
    review_score: int | None = None
    approval_status: str = Field("pending", max_length=50)
    approver_id: UUID | None = None
    approval_date: date | None = None
    approval_comments: str | None = None
    attachments: dict[str, Any] | None = None
    notes: str | None = None
    filing_content: str | None = Field(None, comment="国内申报信息")


class RdInitiationCreate(RdInitiationBase):
    pass


class RdInitiationUpdate(BaseModel):
    project_background: str | None = None
    market_analysis: str | None = None
    technical_feasibility: str | None = None
    resource_requirements: dict[str, Any] | None = None
    timeline_plan: dict[str, Any] | None = None
    risk_assessment: dict[str, Any] | None = None
    expected_outcomes: str | None = None
    review_status: str | None = Field(None, max_length=50)
    reviewer_id: UUID | None = None
    review_date: date | None = None
    review_comments: str | None = None
    review_score: int | None = None
    approval_status: str | None = Field(None, max_length=50)
    approver_id: UUID | None = None
    approval_date: date | None = None
    approval_comments: str | None = None
    attachments: dict[str, Any] | None = None
    notes: str | None = None


class RdInitiationResponse(RdInitiationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== Conclusion Version Schemas =====


class RdTrackConclusionVersionCreate(BaseModel):
    track_id: UUID
    conclusion: str | None = None
    confidence: str = Field("preliminary", max_length=50)
    change_summary: str | None = None
    evidence_refs: dict[str, Any] | None = None


class RdTrackConclusionVersionResponse(BaseModel):
    id: UUID
    track_id: UUID
    version: int
    conclusion: str | None
    confidence: str
    change_summary: str | None
    evidence_refs: dict[str, Any] | None
    author_id: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== 交付物模板 Schemas =====


class RdDeliverableTemplateBase(BaseModel):
    name: str = Field(..., max_length=200)
    deliverable_type: str = Field(..., max_length=50)
    stage: str = Field(..., max_length=50)
    description: str | None = None
    template_content: str | None = None
    template_structure: dict[str, Any] | None = None
    is_active: bool = True


class RdDeliverableTemplateCreate(RdDeliverableTemplateBase):
    pass


class RdDeliverableTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    template_content: str | None = None
    template_structure: dict[str, Any] | None = None
    is_active: bool | None = None


class RdDeliverableTemplateResponse(RdDeliverableTemplateBase):
    id: UUID
    creator_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ===== AI 报告生成 Schemas =====


class RdReportGenerateRequest(BaseModel):
    project_id: UUID
    deliverable_type: str
    template_id: UUID | None = None
    additional_context: str | None = None


class RdReportGenerateResponse(BaseModel):
    content: str
    structure: dict[str, Any] | None = None
    data_sources: list[str] = []


# ===== Report Templates =====

class RdReportTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    content_md: str
    category: str = "general"

class RdReportTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    content_md: str
    meta_info: dict | None = None
    category: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
