/**
 * RD Project module TypeScript types
 * 
 * These are domain model types (response/view models) not covered by OpenAPI spec.
 * API input types (Create/Update) should use @/types/generated/schema.
 * Per AGENTS.md: "允许手写前端 UI 类型，例如表单状态、筛选条件、表格状态、下拉选项、ViewModel/display 类型"
 */

// RdProject 类型定义（对齐后端 RdProject 模型）

export type RdProjectStage = 'initiation' | 'route_dev' | 'optimization' | 'pilot' | 'validation' | 'filing'
export type RdProjectStatus = 'initiation' | 'active' | 'completed' | 'on_hold' | 'terminated'
export type RdProjectPriority = 'low' | 'normal' | 'high' | 'urgent'
export type RdMilestoneType = 'gate_review' | 'decision' | 'achievement'
export type RdMilestoneDecision = 'go' | 'no_go' | 'hold' | 'conditional'
export type RdTrackType = 'impurity' | 'crystal_form' | 'stability' | 'quality_standard' | 'custom'
export type RdTrackStatus = 'active' | 'paused' | 'completed' | 'closed'
export type RdFindingType = 'identification' | 'classification' | 'control_strategy' | 'characterization'
export type RdFindingConfidence = 'preliminary' | 'confirmed' | 'final'

export interface RdProject {
  id: string
  name: string
  api_name: string
  cas_number: string | null
  molecular_formula: string | null
  molecular_weight: number | null
  indication: string | null
  project_type: string | null
  status: RdProjectStatus
  priority: RdProjectPriority
  project_manager_id: string | null
  start_date: string | null
  target_filing_date: string | null
  actual_filing_date: string | null
  current_stage: RdProjectStage | null
  overall_progress: number | null
  notes: string | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

export interface RdMilestone {
  id: string
  project_id: string
  title: string
  milestone_type: RdMilestoneType | null
  stage: string | null
  status: string
  planned_date: string | null
  actual_date: string | null
  decision: RdMilestoneDecision | null
  decision_rationale: string | null
  created_at: string
  updated_at: string
}

export interface RdStageRecord {
  id: string
  project_id: string
  stage: string
  version: number
  status: string
  input_summary: Record<string, unknown> | null
  input_references: Record<string, unknown> | null
  output_summary: Record<string, unknown> | null
  deliverables: Record<string, unknown> | null
  gate_review_status: string | null
  gate_reviewed_at: string | null
  gate_reviewed_by: string | null
  gate_hard_conditions: Record<string, unknown> | null
  gate_soft_conditions: Record<string, unknown> | null
  gate_review_notes: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface RdResearchTrack {
  id: string
  project_id: string
  type: RdTrackType
  name: string
  description: string | null
  status: RdTrackStatus
  priority: RdProjectPriority
  owner_id: string | null
  current_conclusion: string | null
  conclusion_version: number
  conclusion_confidence: RdFindingConfidence | null
  active_stages: string[] | null
  created_at: string
  updated_at: string
  // Extended fields (from detail API)
  findings?: RdResearchFinding[]
  conclusion_history?: RdTrackConclusionVersion[]
}

export interface RdResearchFinding {
  id: string
  track_id: string
  stage_record_id: string | null
  finding_type: RdFindingType | null
  data: Record<string, unknown> | null
  conclusion: string | null
  confidence: RdFindingConfidence
  experiment_date: string | null
  operator: string | null
  experiment_conditions: Record<string, unknown> | null
  materials_used: Record<string, unknown> | null
  equipment_used: Record<string, unknown> | null
  spectra_refs: Record<string, unknown> | null
  analytical_results: Record<string, unknown> | null
  observations: string | null
  attachments: Record<string, unknown> | null
  notes: string | null
  version: number
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

export interface RdTrackConclusionVersion {
  id: string
  track_id: string
  version: number
  conclusion: string | null
  confidence: RdFindingConfidence
  change_summary: string | null
  evidence_refs: Record<string, unknown> | null
  author_id: string | null
  created_at: string
}

export interface StageTransitionCheck {
  allowed: boolean
  current_stage: string
  target_stage: string
  hard_conditions: Record<string, boolean>
  soft_conditions: Record<string, boolean>
  hard_all_passed: boolean
  soft_all_passed: boolean
}

export interface StageTransitionResult {
  success: boolean
  project_id: string
  previous_stage: string
  new_stage: string
  check_result: StageTransitionCheck
}

export const STAGE_LABELS: Record<RdProjectStage, string> = {
  initiation: '立项',
  route_dev: '打通路线',
  optimization: '工艺优化',
  pilot: '中试研究',
  validation: '工艺验证',
  filing: '申报资料',
}

export const STAGE_ORDER: RdProjectStage[] = ['initiation', 'route_dev', 'optimization', 'pilot', 'validation', 'filing']

export const TRACK_TYPE_LABELS: Record<RdTrackType, string> = {
  impurity: '杂质研究',
  crystal_form: '晶型研究',
  stability: '稳定性考察',
  quality_standard: '质量标准',
  custom: '其他',
}

// ===== 中试研究类型 =====

export interface RdPilotStudy {
  id: string
  project_id: string
  stage_record_id: string | null
  material_balance: Record<string, unknown> | null
  equipment_selection: Record<string, unknown> | null
  engineering_calc: Record<string, unknown> | null
  ehs_assessment: Record<string, unknown> | null
  scale_up_effect: Record<string, unknown> | null
  batch_no: string | null
  batch_size: number | null
  status: string
  notes: string | null
  created_at: string
  updated_at: string
}

// ===== 工艺验证类型 =====

export interface RdProcessValidation {
  id: string
  project_id: string
  stage_record_id: string | null
  validation_protocol: Record<string, unknown> | null
  validation_batches: Record<string, unknown> | null
  statistical_analysis: Record<string, unknown> | null
  validation_conclusion: string | null
  status: string
  notes: string | null
  created_at: string
  updated_at: string
}

// ===== 申报资料类型 =====

export interface RdRegistrationFiling {
  id: string
  project_id: string
  stage_record_id: string | null
  ctd_structure: Record<string, unknown> | null
  filing_progress: Record<string, unknown> | null
  supplementary_docs: Record<string, unknown> | null
  status: string
  notes: string | null
  created_at: string
  updated_at: string
}

// ===== 阶段交付物类型 =====

export type RdDeliverableStatus = 'draft' | 'in_progress' | 'completed' | 'approved'

export interface RdStageDeliverable {
  id: string
  project_id: string
  stage: RdProjectStage
  deliverable_type: string
  title: string
  status: RdDeliverableStatus
  version: string
  file_url: string | null
  file_name: string | null
  file_size: number | null
  content: string | null
  owner_id: string | null
  created_by: string | null
  created_at: string
  updated_at: string
}

// 18 种交付物类型配置（与后端 DELIVERABLE_TYPES 同步）
export const DELIVERABLE_TYPES: Record<RdProjectStage, { type: string; label: string }[]> = {
  initiation: [
    { type: 'literature_review', label: '技术调研报告' },
    { type: 'development_plan', label: '研发总方案' },
  ],
  route_dev: [
    { type: 'route_confirmation', label: '工艺路线确认报告' },
    { type: 'safety_assessment', label: '工艺安全评估报告' },
    { type: 'impurity_analysis', label: '理论杂质分析' },
  ],
  optimization: [
    { type: 'optimization_plan', label: '小试工艺优化方案' },
    { type: 'optimization_report', label: '小试工艺优化报告' },
    { type: 'scale_up_summary', label: '公斤级放大总结报告' },
  ],
  pilot: [
    { type: 'pilot_plan', label: '中试方案' },
    { type: 'pilot_report', label: '中试报告' },
    { type: 'supplier_development', label: '供应商开发报告' },
  ],
  validation: [
    { type: 'validation_plan', label: '工艺验证方案' },
    { type: 'validation_report', label: '工艺验证报告' },
    { type: 'cleaning_procedure', label: '清洁操作规程和记录' },
    { type: 'cleaning_validation', label: '清洁验证总结报告' },
  ],
  filing: [
    { type: 'structure_confirmation', label: '原料药结构确证报告' },
    { type: 'crystal_form_study', label: '晶型和粒度研究报告' },
    { type: 'impurity_study', label: '杂质研究报告' },
  ],
}

export const DELIVERABLE_STATUS_LABELS: Record<RdDeliverableStatus, string> = {
  draft: '草稿',
  in_progress: '编写中',
  completed: '已完成',
  approved: '已批准',
}

// ===== 实验记录类型 =====

export type RdExperimentType = 'reaction' | 'crystallization' | 'purification' | 'analysis' | 'stability' | 'other'
export type RdExperimentStatus = 'planned' | 'in_progress' | 'completed' | 'failed'

export interface RdExperimentLog {
  id: string
  project_id: string
  stage_record_id: string | null
  title: string
  experiment_type: RdExperimentType
  experiment_date: string | null
  operator: string | null
  status: RdExperimentStatus
  objective: string | null
  materials: Record<string, unknown> | null
  equipment: Record<string, unknown> | null
  procedure: string | null
  process_params: Record<string, unknown> | null
  observations: string | null
  results: Record<string, unknown> | null
  conclusion: string | null
  issues: string | null
  next_steps: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export const EXPERIMENT_TYPE_LABELS: Record<RdExperimentType, string> = {
  reaction: '反应实验',
  crystallization: '结晶实验',
  purification: '纯化实验',
  analysis: '分析检测',
  stability: '稳定性实验',
  other: '其他',
}

export const EXPERIMENT_STATUS_LABELS: Record<RdExperimentStatus, string> = {
  planned: '计划中',
  in_progress: '进行中',
  completed: '已完成',
  failed: '失败',
}

// ===== 研发报告类型 =====

export type RdReportType = 'summary' | 'stage' | 'annual' | 'final' | 'custom'
export type RdReportStatus = 'draft' | 'in_progress' | 'reviewed' | 'approved'

export interface RdReport {
  id: string
  project_id: string
  title: string
  report_type: RdReportType
  stage: string | null
  status: RdReportStatus
  version: string
  content: string | null
  summary: string | null
  key_findings: Record<string, unknown> | null
  recommendations: string | null
  author_id: string | null
  reviewer_id: string | null
  reviewed_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export const REPORT_TYPE_LABELS: Record<RdReportType, string> = {
  summary: '研发总结报告',
  stage: '阶段报告',
  annual: '年度报告',
  final: '结题报告',
  custom: '自定义报告',
}

export const REPORT_STATUS_LABELS: Record<RdReportStatus, string> = {
  draft: '草稿',
  in_progress: '编写中',
  reviewed: '已审核',
  approved: '已批准',
}

// ===== 立项申请类型 =====

export type RdReviewStatus = 'pending' | 'approved' | 'rejected'
export type RdApprovalStatus = 'pending' | 'approved' | 'rejected'

export interface RdInitiation {
  id: string
  project_id: string
  project_background: string | null
  market_analysis: string | null
  technical_feasibility: string | null
  resource_requirements: Record<string, unknown> | null
  timeline_plan: Record<string, unknown> | null
  risk_assessment: Record<string, unknown> | null
  expected_outcomes: string | null
  applicant_id: string | null
  application_date: string | null
  review_status: RdReviewStatus
  reviewer_id: string | null
  review_date: string | null
  review_comments: string | null
  review_score: number | null
  approval_status: RdApprovalStatus
  approver_id: string | null
  approval_date: string | null
  approval_comments: string | null
  attachments: Record<string, unknown> | null
  notes: string | null
  created_at: string
  updated_at: string
}

export const REVIEW_STATUS_LABELS: Record<RdReviewStatus, string> = {
  pending: '待评审',
  approved: '已通过',
  rejected: '已驳回',
}

export const APPROVAL_STATUS_LABELS: Record<RdApprovalStatus, string> = {
  pending: '待批准',
  approved: '已批准',
  rejected: '已驳回',
}

// ===== 交付物模板类型 =====

export interface RdDeliverableTemplate {
  id: string
  name: string
  deliverable_type: string
  stage: string
  description: string | null
  template_content: string | null
  template_structure: Record<string, unknown> | null
  is_active: boolean
  creator_id: string | null
  created_at: string
  updated_at: string
}

// ===== AI 报告生成类型 =====

export interface RdReportGenerateRequest {
  project_id: string
  deliverable_type: string
  template_id?: string
  additional_context?: string
}

export interface RdReportGenerateResponse {
  content: string
  structure: Record<string, unknown> | null
  data_sources: string[]
}
