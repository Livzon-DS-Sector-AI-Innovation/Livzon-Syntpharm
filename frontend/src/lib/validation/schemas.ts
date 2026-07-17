/**
 * 共享的 Zod schemas
 * 
 * 用于数据边界的运行时校验：
 * - Server Actions 的复杂输入
 * - Excel/CSV 文件导入
 * - LLM 结构化输出
 * - 环境变量校验
 */

import { z } from 'zod'

// ============================================
// 通用基础 schemas
// ============================================

/** UUID 字符串 */
export const UUIDSchema = z.string().uuid('必须是有效的 UUID')

/** 正整数 */
export const PositiveIntSchema = z.number().int('必须是整数').gt(0, '必须大于 0')

/** 非负整数 */
export const NonNegativeIntSchema = z.number().int('必须是整数').gte(0, '不能为负数')

/** 日期时间字符串 (ISO 8601) */
export const DateTimeStringSchema = z.string().datetime({ message: '必须是有效的日期时间格式' })

/** 日期字符串 (YYYY-MM-DD) */
export const DateStringSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, '必须是 YYYY-MM-DD 格式')

/** 非空字符串 */
export const NonEmptyStringSchema = z.string().min(1, '不能为空')

// ============================================
// 生产模块 schemas
// ============================================

/** 产品产出数据 */
export const ProductOutputSchema = z.object({
  product_id: UUIDSchema,
  workshop: NonEmptyStringSchema,
  product_name: NonEmptyStringSchema,
  batch_no: NonEmptyStringSchema,
  production_date: DateStringSchema,
  end_date: DateStringSchema.optional(),
  weight: PositiveIntSchema,
  unit: z.string().optional(),
  notes: z.string().optional(),
})

export type ProductOutput = z.infer<typeof ProductOutputSchema>

// ============================================
// 研发模块 schemas
// ============================================

/** 研发项目创建 */
export const RdProjectCreateSchema = z.object({
  name: NonEmptyStringSchema,
  api_name: NonEmptyStringSchema,
  cas_number: z.string().optional(),
  molecular_formula: z.string().optional(),
  molecular_weight: z.number().positive().optional(),
  project_type: z.string().optional(),
  status: z.enum(['initiation', 'active', 'completed', 'on_hold', 'terminated']),
  priority: z.enum(['low', 'normal', 'high', 'urgent']),
  project_manager_id: UUIDSchema.optional(),
  start_date: DateStringSchema.optional(),
  target_filing_date: DateStringSchema.optional(),
})

export type RdProjectCreate = z.infer<typeof RdProjectCreateSchema>

/** 研发项目更新 */
export const RdProjectUpdateSchema = RdProjectCreateSchema.partial()

export type RdProjectUpdate = z.infer<typeof RdProjectUpdateSchema>

/** 里程碑创建 */
export const RdMilestoneCreateSchema = z.object({
  project_id: UUIDSchema,
  title: NonEmptyStringSchema,
  milestone_type: z.enum(['gate_review', 'decision', 'achievement']).optional(),
  stage: z.string().optional(),
  planned_date: DateStringSchema.optional(),
  decision: z.enum(['go', 'no_go', 'hold', 'conditional']).optional(),
  decision_rationale: z.string().optional(),
})

export type RdMilestoneCreate = z.infer<typeof RdMilestoneCreateSchema>

/** 阶段记录创建 */
export const RdStageRecordCreateSchema = z.object({
  project_id: UUIDSchema,
  stage: NonEmptyStringSchema,
  version: z.number().int().positive(),
  status: z.string(),
  input_summary: z.record(z.string(), z.unknown()).optional(),
  output_summary: z.record(z.string(), z.unknown()).optional(),
  deliverables: z.record(z.string(), z.unknown()).optional(),
})

export type RdStageRecordCreate = z.infer<typeof RdStageRecordCreateSchema>

/** 研究轨道创建 */
export const RdResearchTrackCreateSchema = z.object({
  project_id: UUIDSchema,
  type: z.enum(['impurity', 'crystal_form', 'stability', 'quality_standard', 'custom']),
  name: NonEmptyStringSchema,
  description: z.string().optional(),
  status: z.enum(['active', 'paused', 'completed', 'closed']),
  priority: z.enum(['low', 'normal', 'high', 'urgent']),
  owner_id: UUIDSchema.optional(),
})

export type RdResearchTrackCreate = z.infer<typeof RdResearchTrackCreateSchema>

/** 研究结果创建 */
export const RdResearchFindingCreateSchema = z.object({
  track_id: UUIDSchema,
  stage_record_id: UUIDSchema.optional(),
  finding_type: z.enum(['identification', 'classification', 'control_strategy', 'characterization']).optional(),
  data: z.record(z.string(), z.unknown()).optional(),
  conclusion: z.string().optional(),
  confidence: z.enum(['preliminary', 'confirmed', 'final']),
  experiment_date: DateStringSchema.optional(),
  operator: z.string().optional(),
})

export type RdResearchFindingCreate = z.infer<typeof RdResearchFindingCreateSchema>

/** 立项申请创建 */
export const RdInitiationCreateSchema = z.object({
  project_id: UUIDSchema,
  project_background: z.string().optional(),
  market_analysis: z.string().optional(),
  technical_feasibility: z.string().optional(),
  resource_requirements: z.record(z.string(), z.unknown()).optional(),
  timeline_plan: z.record(z.string(), z.unknown()).optional(),
  risk_assessment: z.record(z.string(), z.unknown()).optional(),
  expected_outcomes: z.string().optional(),
})

export type RdInitiationCreate = z.infer<typeof RdInitiationCreateSchema>

/** 交付物模板创建 */
export const RdDeliverableTemplateCreateSchema = z.object({
  name: NonEmptyStringSchema,
  deliverable_type: NonEmptyStringSchema,
  stage: NonEmptyStringSchema,
  description: z.string().optional(),
  template_content: z.string().optional(),
  template_structure: z.record(z.string(), z.unknown()).optional(),
  is_active: z.boolean(),
})

export type RdDeliverableTemplateCreate = z.infer<typeof RdDeliverableTemplateCreateSchema>

/** 阶段交付物创建 */
export const RdStageDeliverableCreateSchema = z.object({
  project_id: UUIDSchema,
  stage: NonEmptyStringSchema,
  deliverable_type: NonEmptyStringSchema,
  title: NonEmptyStringSchema,
  content: z.string().optional(),
  status: z.enum(['draft', 'in_progress', 'completed', 'approved']),
})

export type RdStageDeliverableCreate = z.infer<typeof RdStageDeliverableCreateSchema>

// ============================================
// 工具函数
// ============================================

/**
 * 安全解析 Zod schema
 * 返回 { success: true, data } 或 { success: false, error }
 */
export function safeParse<T>(schema: z.ZodSchema<T>, data: unknown): 
  | { success: true; data: T }
  | { success: false; error: z.ZodError } {
  const result = schema.safeParse(data)
  if (result.success) {
    return { success: true, data: result.data }
  }
  return { success: false, error: result.error }
}

/**
 * 解析 Zod schema，失败时抛出错误
 */
export function parse<T>(schema: z.ZodSchema<T>, data: unknown): T {
  return schema.parse(data)
}

/**
 * 格式化 Zod 错误为可读的中文消息
 */
export function formatZodError(error: z.ZodError): string {
  return error.issues.map((issue: any) => {
    const path = issue.path.join('.')
    return `${path}: ${issue.message}`
  }).join('; ')
}

// ============================================
// 质量模块 - CAPA schemas
// ============================================

/** CAPA 审批 */
export const CapaApprovalSchema = z.object({
  step: z.enum(['qa_review', 'q_head_approval']),
  result: z.enum(['approved', 'rejected', 'returned']),
  opinion: z.string().optional(),
})

export type CapaApproval = z.infer<typeof CapaApprovalSchema>

/** CAPA 执行跟踪 */
export const CapaExecutionTrackSchema = z.object({
  execution_status: z.string(),
  qa_confirmer: z.string().optional(),
  qa_confirm_date: z.string().optional(),
})

export type CapaExecutionTrack = z.infer<typeof CapaExecutionTrackSchema>

/** CAPA 执行确认 */
export const CapaExecutionConfirmSchema = z.object({
  confirmed: z.boolean().optional(),
  notes: z.string().optional(),
})

export type CapaExecutionConfirm = z.infer<typeof CapaExecutionConfirmSchema>

/** CAPA 评估提交 */
export const CapaEvaluationSchema = z.object({
  evaluation_target: z.string(),
  evaluation_result: z.string(),
  evaluation_confirmer: z.string(),
  evaluation_confirm_date: z.string(),
  closure_date: z.string(),
})

export type CapaEvaluation = z.infer<typeof CapaEvaluationSchema>

/** CAPA 部分完成 */
export const CapaPartCompleteSchema = z.object({
  part_name: z.string(),
  completed: z.boolean(),
  notes: z.string().optional(),
})

export type CapaPartComplete = z.infer<typeof CapaPartCompleteSchema>

/** CAPA 部门主管确认 */
export const CapaDeptHeadConfirmSchema = z.object({
  confirmed: z.boolean(),
  comments: z.string().optional(),
})

export type CapaDeptHeadConfirm = z.infer<typeof CapaDeptHeadConfirmSchema>

// ============================================
// 质量模块 - 偏差 schemas
// ============================================

/** 偏差调查提交 */
export const DeviationInvestigationSchema = z.object({
  root_cause: z.string(),
  investigation_details: z.string().optional(),
  supporting_documents: z.array(z.string()).optional(),
})

export type DeviationInvestigation = z.infer<typeof DeviationInvestigationSchema>

/** 偏差审核提交 */
export const DeviationReviewSchema = z.object({
  review_result: z.enum(['approved', 'rejected', 'returned']),
  review_comments: z.string().optional(),
})

export type DeviationReview = z.infer<typeof DeviationReviewSchema>

/** 偏差最终代码提交 */
export const DeviationFinalCodeSchema = z.object({
  final_code: z.string(),
  description: z.string().optional(),
})

export type DeviationFinalCode = z.infer<typeof DeviationFinalCodeSchema>

/** 偏差自动化任务创建 */
export const DeviationTaskCreateSchema = z.object({
  task_name: z.string(),
  template_id: z.string().uuid().optional(),
  parameters: z.record(z.string(), z.unknown()).optional(),
})

export type DeviationTaskCreate = z.infer<typeof DeviationTaskCreateSchema>

/** 偏差报告生成 */
export const DeviationReportGenerateSchema = z.object({
  format: z.enum(['pdf', 'docx', 'html']).optional(),
  include_attachments: z.boolean().optional(),
})

export type DeviationReportGenerate = z.infer<typeof DeviationReportGenerateSchema>

/** 偏差审批提交 */
export const DeviationApprovalSchema = z.object({
  approved: z.boolean(),
  comments: z.string().optional(),
  approver_id: z.string().uuid(),
})

export type DeviationApproval = z.infer<typeof DeviationApprovalSchema>

/** 偏差任务更新 */
export const DeviationTaskUpdateSchema = z.object({
  status: z.enum(['draft', 'in_progress', 'completed', 'approved']).optional(),
  assigned_to: z.string().uuid().optional(),
  due_date: z.string().optional(),
})

export type DeviationTaskUpdate = z.infer<typeof DeviationTaskUpdateSchema>

/** 偏差任务字段更新 */
export const DeviationTaskFieldsUpdateSchema = z.object({
  fields: z.record(z.string(), z.unknown()),
})

export type DeviationTaskFieldsUpdate = z.infer<typeof DeviationTaskFieldsUpdateSchema>

/** 偏差模板创建 */
export const DeviationTemplateCreateSchema = z.object({
  template_name: z.string(),
  description: z.string().optional(),
  template_content: z.record(z.string(), z.unknown()),
})

export type DeviationTemplateCreate = z.infer<typeof DeviationTemplateCreateSchema>

// ============================================
// 质量模块 - AI 配置 schemas
// ============================================

/** AI 配置保存 */
export const AIConfigSaveSchema = z.object({
  provider: z.string(),
  api_key: z.string(),
  model: z.string(),
  temperature: z.number().min(0).max(2).optional(),
  max_tokens: z.number().int().positive().optional(),
})

export type AIConfigSave = z.infer<typeof AIConfigSaveSchema>

/** AI 连接测试 */
export const AIConfigTestSchema = z.object({
  provider: z.string(),
  api_key: z.string(),
  model: z.string(),
})

export type AIConfigTest = z.infer<typeof AIConfigTestSchema>

// ============================================
// 质量模块 - SOP schemas
// ============================================

/** SOP 模板创建 */
export const SopTemplateCreateSchema = z.object({
  template_name: z.string(),
  description: z.string().optional(),
  template_content: z.record(z.string(), z.unknown()),
})

export type SopTemplateCreate = z.infer<typeof SopTemplateCreateSchema>

/** SOP 从模板创建 */
export const SopFromTemplateCreateSchema = z.object({
  template_id: z.string().uuid(),
  parameters: z.record(z.string(), z.unknown()).optional(),
})

export type SopFromTemplateCreate = z.infer<typeof SopFromTemplateCreateSchema>

/** SOP 生成 */
export const SopGenerateSchema = z.object({
  content: z.string(),
  metadata: z.record(z.string(), z.unknown()).optional(),
})

export type SopGenerate = z.infer<typeof SopGenerateSchema>

/** SOP 规则创建 */
export const SopRuleCreateSchema = z.object({
  rule_name: z.string(),
  condition: z.record(z.string(), z.unknown()),
  action: z.record(z.string(), z.unknown()),
})

export type SopRuleCreate = z.infer<typeof SopRuleCreateSchema>
