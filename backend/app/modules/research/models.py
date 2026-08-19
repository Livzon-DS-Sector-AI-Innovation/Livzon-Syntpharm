"""Research ORM models."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (func, 
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class ResearchProject(BaseModel):
    """研发项目主表"""

    __tablename__ = "research_projects"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('立项', '研发中试', '验证', '注册', '商业化')",
            name="ck_research_projects_stage",
        ),
        CheckConstraint(
            "status IN ('进行中', '已暂停', '已完成', '已终止')",
            name="ck_research_projects_status",
        ),
        {"schema": "research"},
    )

    project_no: Mapped[str] = mapped_column(String(50), comment="项目编号")
    name: Mapped[str] = mapped_column(String(200), comment="项目名称")
    project_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="项目类型")
    stage: Mapped[str] = mapped_column(
        String(20),
        default="立项",
        comment="项目阶段：立项/研发中试/验证/注册/商业化",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="进行中",
        comment="项目状态：进行中/已暂停/已完成/已终止",
    )
    leader: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="项目负责人")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="开始日期")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="结束日期")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目描述")


class ICHAnalysisRecord(BaseModel):
    """ICH Q3C/Q3D 杂质识别分析记录"""

    __tablename__ = "ich_analysis_records"
    __table_args__ = {"schema": "research"}

    filename: Mapped[str] = mapped_column(String(500), comment="上传的文件名")
    route: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="给药途径: oral/parenteral/inhalation/cutaneous (deprecated)",
    )
    q3c_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="Q3C 溶剂残留分析结果")
    q3d_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="Q3D 元素杂质分析结果")
    llm_used: Mapped[bool] = mapped_column(default=False, comment="是否使用 LLM 增强识别")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RouteDevelopment(BaseModel):
    """打通路线开发记录"""

    __tablename__ = "route_developments"
    __table_args__ = {"schema": "research"}

    # Override id from BaseModel to use String (DB column is varchar)
    id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="主键ID")  # type: ignore[assignment]

    project_id: Mapped[str] = mapped_column(String(50), comment="所属研发项目ID")
    route_no: Mapped[str] = mapped_column(String(50), comment="路线编号")
    name: Mapped[str] = mapped_column(String(200), comment="路线名称")
    source: Mapped[str] = mapped_column(String(50), default="manual", comment="来源: manual/literature/llm")
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="来源引用")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[str] = mapped_column(
        String(20),
        default="planning",
        comment="状态: planning/in_progress/completed/failed",
    )
    current_module: Mapped[str] = mapped_column(
        String(20),
        default="research",
        comment="当前工作流阶段: research/trial/assessment/confirmation",
    )
    literature_sources: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="文献来源数据")
    candidate_routes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="候选路线列表")
    selected_route_ids: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="已选路线ID列表")
    experiment_plans: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="实验方案列表")
    assessment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="四维度评估结果")
    deliverables: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="交付物列表")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="开始日期")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="结束日期")


class RouteExperiment(BaseModel):
    """打通路线实验记录"""

    __tablename__ = "route_experiments"
    __table_args__ = {"schema": "research"}

    # Override id from BaseModel to use String (DB column is varchar)
    id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="主键ID")  # type: ignore[assignment]

    route_id: Mapped[str | None] = mapped_column(String(50), comment="所属路线ID")
    experiment_no: Mapped[str] = mapped_column(String(50), comment="实验编号")
    title: Mapped[str] = mapped_column(String(200), comment="实验标题")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实验描述")
    experiment_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="实验日期")
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="操作人")
    status: Mapped[str] = mapped_column(
        String(20),
        default="planned",
        comment="状态: planned/in_progress/completed/failed",
    )
    reaction_temp: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="反应温度")
    reaction_time: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="反应时间")
    yield_pct: Mapped[float | None] = mapped_column(nullable=True, comment="收率(%)")
    purity: Mapped[float | None] = mapped_column(nullable=True, comment="纯度(%)")
    impurities: Mapped[float | None] = mapped_column(nullable=True, comment="杂质(%)")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结果摘要")


class ProcessOptimization(BaseModel):
    """工艺优化记录"""

    __tablename__ = "process_optimizations"
    __table_args__ = {"schema": "research"}

    id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="主键ID")  # type: ignore[assignment]
    project_id: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="所属研发项目ID")
    optimization_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="优化任务编号")
    source_route_id: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="来源路线ID")
    source_route_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="来源路线名称")
    name: Mapped[str] = mapped_column(String(200), comment="优化任务名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[str] = mapped_column(
        String(20),
        default="planning",
        comment="状态: planning/in_progress/completed/failed",
    )
    current_module: Mapped[str] = mapped_column(
        String(20),
        default="doe",
        comment="当前工作流阶段: doe/impurity/crystal/quality/scaleup/report",
    )
    doe_experiment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="DOE实验数据")
    impurity_study: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="杂质研究数据")
    crystal_form_study: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="晶型研究数据")
    quality_standard_set: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="质量标准数据")
    scale_up_study: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="公斤级放大数据")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="开始日期")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="结束日期")

    
    # 研究项关联（新架构）
    impurity_track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_research_tracks.id"),
        nullable=True,
        comment="关联的杂质研究项ID"
    )
    crystal_track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_research_tracks.id"),
        nullable=True,
        comment="关联的晶型研究项ID"
    )

class PilotWorkflow(BaseModel):
    """中试研究实例"""

    __tablename__ = "pilot_workflows"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'waiting_approval', 'completed', 'failed')",
            name="ck_pilot_workflows_status",
        ),
        {"schema": "research"},
    )

    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="关联研发项目ID")
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="产品名称")
    scale_up_ratio: Mapped[float] = mapped_column(Float, nullable=False, comment="放大倍数")
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="设备类型")
    equipment_volume: Mapped[float] = mapped_column(Float, nullable=False, comment="设备容积(L)")
    input_document_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="上传文档路径")
    input_context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="额外上下文")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="状态")
    final_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="最终报告")


class PilotWorkflowStep(BaseModel):
    """工作流步骤执行记录"""

    __tablename__ = "pilot_workflow_steps"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'waiting_approval', 'completed', 'failed', 'skipped')",
            name="ck_pilot_workflow_steps_status",
        ),
        {"schema": "research"},
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="工作流ID")
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="步骤序号")
    step_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="步骤标识")
    step_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="步骤名称")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="状态")
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="输入数据")
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="输出数据")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="完成时间")


class BayesianProject(BaseModel):
    """贝叶斯优化项目表"""

    __tablename__ = "bayesian_projects"
    __table_args__ = {"schema": "research"}

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="项目名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目描述")
    status: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目状态")


class BayesianExperiment(BaseModel):
    """贝叶斯优化实验表"""

    __tablename__ = "bayesian_experiments"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="所属项目ID")
    batch_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="实验批次号")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="实验参数")
    results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="实验结果")
    is_suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否为建议的实验")
    status: Mapped[str] = mapped_column(String(50), nullable=False, comment="实验状态")


class BayesianObjective(BaseModel):
    """贝叶斯优化目标表"""

    __tablename__ = "bayesian_objectives"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="所属项目ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="目标名称")
    direction: Mapped[str] = mapped_column(String(20), nullable=False, comment="优化方向：maximize/minimize")
    weight: Mapped[float | None] = mapped_column(Float, nullable=True, comment="目标权重")
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True, comment="目标阈值")


class BayesianComponent(BaseModel):
    """贝叶斯优化组件表"""

    __tablename__ = "bayesian_components"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="所属项目ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="组件名称")
    lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True, comment="下界")
    upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True, comment="上界")
    interval: Mapped[float | None] = mapped_column(Float, nullable=True, comment="间隔")
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="单位")
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="排序顺序")
    component_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="组件类型")
    data_points: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="数据点数")
    categorical_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="分类值")


class ReactionScope(BaseModel):
    """反应范围表"""

    __tablename__ = "reaction_scopes"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="所属项目ID")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="范围名称")
    scope_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="范围数据")
    total_combinations: Mapped[int] = mapped_column(Integer, nullable=False, comment="总组合数")


# ===== Rd Project Models (from rd_project) =====


class RdProject(BaseModel):
    """研发项目主表"""

    __tablename__ = "rd_projects"
    __table_args__ = {"schema": "research"}

    name: Mapped[str] = mapped_column(String(200), comment="品种名称")
    api_name: Mapped[str] = mapped_column(String(200), comment="API全称")
    cas_number: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="CAS号")
    molecular_formula: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="分子式")
    molecular_weight: Mapped[float | None] = mapped_column(Float, nullable=True, comment="分子量")
    indication: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="适应症")
    project_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="generic/improved")
    status: Mapped[str] = mapped_column(String(50), default="initiation", comment="当前阶段状态")
    priority: Mapped[str] = mapped_column(String(20), default="normal", comment="low/normal/high/urgent")

    project_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="项目经理",
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="开始日期")
    target_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="目标申报日期")
    actual_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="实际申报日期")

    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="当前阶段")
    overall_progress: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总体进度%")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdMilestone(BaseModel):
    """里程碑/决策记录"""

    __tablename__ = "rd_milestones"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    title: Mapped[str] = mapped_column(String(200), comment="标题")
    milestone_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="gate_review/decision/achievement"
    )
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="关联阶段")
    status: Mapped[str] = mapped_column(String(50), default="planned", comment="planned/achieved/delayed/cancelled")
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="计划日期")
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="实际日期")
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="go/no_go/hold/conditional")
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True, comment="决策理由")


class RdStageRecord(BaseModel):
    """阶段记录"""

    __tablename__ = "rd_stage_records"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    stage: Mapped[str] = mapped_column(String(50), comment="initiation/route_dev/optimization/pilot/validation/filing")
    status: Mapped[str] = mapped_column(
        String(50),
        default="not_started",
        comment="not_started/in_progress/review/completed/transferred",
    )
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")

    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="上游输入摘要")
    input_references: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="关联的上游记录ID")
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="产出摘要")
    deliverables: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="产出物列表")

    gate_review_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="pending/approved/rejected/conditional"
    )
    gate_hard_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="硬条件检查结果")
    gate_soft_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="软条件检查结果")
    gate_review_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="评审备注")
    gate_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gate_reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RdResearchTrack(BaseModel):
    """研究项（跨阶段并行）"""

    __tablename__ = "rd_research_tracks"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    type: Mapped[str] = mapped_column(String(50), comment="impurity/crystal_form/stability/quality_standard/custom")
    name: Mapped[str] = mapped_column(String(200), comment="研究项名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[str] = mapped_column(String(50), default="active", comment="active/paused/completed/archived")
    priority: Mapped[str] = mapped_column(String(20), default="normal", comment="low/normal/high/urgent")

    current_conclusion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="当前结论")
    conclusion_version: Mapped[int] = mapped_column(Integer, default=0, comment="结论版本号")
    conclusion_confidence: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="preliminary/confirmed/final"
    )

    active_stages: Mapped[list[Any] | None] = mapped_column(ARRAY(String(50)), nullable=True, comment="活跃阶段列表")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="负责人",
    )


class RdResearchFinding(BaseModel):
    """研究发现"""

    __tablename__ = "rd_research_findings"
    __table_args__ = {"schema": "research"}

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_research_tracks.id"),
        comment="研究项ID",
    )
    stage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_stage_records.id"),
        nullable=True,
        comment="关联阶段记录",
    )

    finding_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="identification/classification/control_strategy/characterization",
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSON, comment="结构化数据")
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结论")
    confidence: Mapped[str] = mapped_column(String(50), default="preliminary", comment="preliminary/confirmed/final")

    # 实验条件（结构化）
    experiment_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="实验日期")
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="操作人")
    experiment_conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="实验条件（温度、溶剂、时间等）"
    )
    materials_used: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="使用物料")
    equipment_used: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="使用设备")
    # 图谱与检测
    spectra_refs: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="图谱引用（HPLC/NMR/XRD等）"
    )
    analytical_results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="检测结果")
    # 其他
    observations: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实验现象/观察")
    attachments: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="附件列表")
    filing_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="国内申报信息")
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdPilotStudy(BaseModel):
    """中试研究"""

    __tablename__ = "rd_pilot_studies"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    stage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_stage_records.id"),
        nullable=True,
        comment="关联阶段记录",
    )
    batch_no: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="批次号")
    batch_size: Mapped[float | None] = mapped_column(Float, nullable=True, comment="批次规模(kg)")
    status: Mapped[str] = mapped_column(String(50), default="draft", comment="draft/in_progress/completed")
    material_balance: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="物料衡算")
    equipment_selection: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="设备选型")
    engineering_calc: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="工程计算")
    ehs_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="EHS评估")
    scale_up_effect: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="放大效应")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdProcessValidation(BaseModel):
    """工艺验证"""

    __tablename__ = "rd_process_validations"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    stage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_stage_records.id"),
        nullable=True,
        comment="关联阶段记录",
    )
    status: Mapped[str] = mapped_column(String(50), default="draft", comment="draft/in_progress/completed")
    validation_protocol: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="验证方案")
    validation_batches: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="验证批次")
    statistical_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="统计分析")
    validation_conclusion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="验证结论")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdRegistrationFiling(BaseModel):
    """申报资料"""

    __tablename__ = "rd_registration_filings"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    stage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_stage_records.id"),
        nullable=True,
        comment="关联阶段记录",
    )
    status: Mapped[str] = mapped_column(String(50), default="draft", comment="draft/in_progress/completed")
    ctd_structure: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="CTD文档结构")
    filing_progress: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="申报进度")
    supplementary_docs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="补充资料")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdStageDeliverable(BaseModel):
    """阶段交付物"""

    __tablename__ = "rd_stage_deliverables"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    stage: Mapped[str] = mapped_column(String(50), comment="initiation/route_dev/optimization/pilot/validation/filing")
    deliverable_type: Mapped[str] = mapped_column(String(100), comment="交付物类型")
    title: Mapped[str] = mapped_column(String(500), comment="标题")
    status: Mapped[str] = mapped_column(String(50), default="draft", comment="draft/in_progress/completed/approved")
    version: Mapped[str] = mapped_column(String(50), default="v1.0", comment="版本号")
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="附件URL")
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="文件名")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小(字节)")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容(富文本)")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="负责人",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdExperimentLog(BaseModel):
    """实验记录"""

    __tablename__ = "rd_experiment_logs"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    stage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_stage_records.id"),
        nullable=True,
        comment="关联阶段记录",
    )
    title: Mapped[str] = mapped_column(String(300), comment="实验标题")
    experiment_type: Mapped[str] = mapped_column(
        String(50),
        comment="实验类型: reaction/crystallization/purification/analysis/stability/other",
    )
    experiment_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="实验日期")
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="操作人")
    status: Mapped[str] = mapped_column(String(50), default="planned", comment="planned/in_progress/completed/failed")
    objective: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实验目的")
    materials: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原辅料信息")
    equipment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="设备信息")
    procedure: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实验步骤")
    process_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="工艺参数")
    observations: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实验现象/观察")
    results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="实验结果")
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实验结论")
    issues: Mapped[str | None] = mapped_column(Text, nullable=True, comment="问题与讨论")
    next_steps: Mapped[str | None] = mapped_column(Text, nullable=True, comment="后续计划")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdReport(BaseModel):
    """研发报告"""

    __tablename__ = "rd_reports"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    title: Mapped[str] = mapped_column(String(500), comment="报告标题")
    report_type: Mapped[str] = mapped_column(String(50), comment="报告类型: summary/stage/annual/final/custom")
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="关联阶段")
    status: Mapped[str] = mapped_column(String(50), default="draft", comment="draft/in_progress/reviewed/approved")
    version: Mapped[str] = mapped_column(String(50), default="v1.0", comment="版本号")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="报告内容(富文本)")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="摘要")
    key_findings: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="关键发现")
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True, comment="建议与结论")
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="作者",
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="审核人",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdInitiation(BaseModel):
    """立项申请"""

    __tablename__ = "rd_initiations"
    __table_args__ = {"schema": "research"}

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research.rd_projects.id"), comment="项目ID"
    )
    # 立项申请信息
    project_background: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目背景")
    market_analysis: Mapped[str | None] = mapped_column(Text, nullable=True, comment="市场分析")
    technical_feasibility: Mapped[str | None] = mapped_column(Text, nullable=True, comment="技术可行性分析")
    resource_requirements: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="资源需求（人员、设备、预算）"
    )
    timeline_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="时间计划")
    risk_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="风险评估")
    expected_outcomes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="预期成果")
    applicant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="申请人",
    )
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="申请日期")
    # 评审信息
    review_status: Mapped[str] = mapped_column(
        String(50), default="pending", comment="评审状态: pending/approved/rejected"
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="评审人",
    )
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="评审日期")
    review_comments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="评审意见")
    review_score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="评审评分(1-10)")
    # 批准信息
    approval_status: Mapped[str] = mapped_column(
        String(50), default="pending", comment="批准状态: pending/approved/rejected"
    )
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="批准人",
    )
    approval_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="批准日期")
    approval_comments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="批准意见")
    # 其他
    attachments: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="附件列表")
    filing_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="国内申报信息")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class RdTrackConclusionVersion(BaseModel):
    """研究项结论版本历史"""

    __tablename__ = "rd_track_conclusion_versions"
    __table_args__ = {"schema": "research"}

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research.rd_research_tracks.id"),
        comment="研究项ID",
    )
    version: Mapped[int] = mapped_column(Integer, comment="版本号")
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结论文本")
    confidence: Mapped[str] = mapped_column(String(50), default="preliminary", comment="preliminary/confirmed/final")
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="变更说明")
    evidence_refs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="支撑证据引用")
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="作者",
    )


class RdDeliverableTemplate(BaseModel):
    """交付物模板"""

    __tablename__ = "rd_deliverable_templates"
    __table_args__ = {"schema": "research"}

    name: Mapped[str] = mapped_column(String(200), comment="模板名称")
    deliverable_type: Mapped[str] = mapped_column(String(50), comment="交付物类型")
    stage: Mapped[str] = mapped_column(String(50), comment="所属阶段")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模板描述")
    template_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模板内容")
    template_structure: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="模板结构定义")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    creator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="创建者",
    )


class RdReportTemplate(BaseModel):
    """研发报告模板"""

    __tablename__ = "rd_report_templates"
    __table_args__ = {"schema": "research"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), comment="模板名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模板描述")
    
    # 核心内容：Markdown 格式
    content_md: Mapped[str] = mapped_column(Text, comment="模板内容(Markdown)")
    
    # 元数据：存储 YAML frontmatter 解析后的结果，方便前端展示变量列表
    meta_info: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="模板元数据(info)")
    
    category: Mapped[str] = mapped_column(String(50), default="general", comment="分类：process_optimization, validation, etc.")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
