/**
 * Safety module domain model types (ViewModels).
 * API 契约字段一律从 OpenAPI 生成类型派生（@/types/generated/schema），禁止手写，
 * 避免后端新增字段后前端静默丢失。仅枚举展示类型、查询参数等前端私有结构手写。
 */

import type { components } from '@/types/generated/schema'

/** 危险源辨识台账记录（响应契约来自 OpenAPI） */
export type HazardIdentification = components['schemas']['HazardIdentificationResponse']

/** 创建入参（请求契约来自 OpenAPI；留空 hazard_id_no 时后端自动生成 HI-YYYYMMDD-NNN） */
export type HazardIdentificationFormData = components['schemas']['HazardIdentificationCreate']

// ── 批量辨识 ──

/** 工艺阶段条目（响应契约来自 OpenAPI） */
export type RegulationStageInfo = components['schemas']['RegulationStageInfo']

/** 操规工艺阶段列表（响应契约来自 OpenAPI） */
export type RegulationStagesResponse = components['schemas']['RegulationStagesResponse']

/** 批量创建入参（请求契约来自 OpenAPI） */
export type HazardIdentificationBatchCreateInput = components['schemas']['HazardIdentificationBatchCreate']

/** 批量创建结果（响应契约来自 OpenAPI） */
export type HazardIdentificationBatchResponse = components['schemas']['HazardIdentificationBatchResponse']

export interface HazardIdentificationQueryParams {
  page?: number
  page_size?: number
  department?: string
  overall_status?: string
  ai_node_progress?: string
  keyword?: string
  position?: string
  risk_level?: string
  date_from?: string
  date_to?: string
  batch_id?: string
}

/** 工作台状态计数（响应契约来自 OpenAPI） */
export type HazardIdentificationStats = components['schemas']['HazardIdentificationStatsData']

/** 台账风险等级分布（响应契约来自 OpenAPI） */
export type HazardLedgerStats = components['schemas']['HazardIdentificationLedgerStatsData']

export const AI_NODE_PROGRESS_OPTIONS = [
  { value: 'pending_input', label: '待填写基础信息', color: 'default' },
  { value: 'pending_script1', label: '待解析附件', color: 'processing' },
  { value: 'pending_script2', label: '待危险源辨识', color: 'processing' },
  { value: 'pending_script3', label: '待固有风险评价', color: 'processing' },
  { value: 'pending_script4', label: '待控制措施', color: 'processing' },
  { value: 'pending_script5', label: '待残余风险评价', color: 'processing' },
  { value: 'pending_script6', label: '待建议措施', color: 'processing' },
  { value: 'pending_script7', label: '待措施后评价', color: 'processing' },
  { value: 'completed', label: '已完成', color: 'success' },
]

// ============ Hazard Identification Export Types ============

/** 台账 PDF 导出请求（请求契约来自 OpenAPI） */
export type HazardLedgerExportRequest = components['schemas']['HazardLedgerExportRequest']

export interface HazardLedgerExportParsedFilters {
  department?: string
  position?: string
  risk_level?: string
  date_from?: string
  date_to?: string
  keyword?: string
  explanation: string
}

export const OVERALL_STATUS_OPTIONS_HI = [
  { value: 'draft', label: '草稿', color: 'default' },
  { value: 'in_progress', label: '进行中', color: 'processing' },
  { value: 'completed', label: '已完成', color: 'success' },
  { value: 'cancelled', label: '已取消', color: 'error' },
]

export const REVIEW_STATUS_OPTIONS = [
  { value: 'pending', label: '待审核', color: 'default' },
  { value: 'approved', label: '已审核', color: 'success' },
  { value: 'rejected', label: '已驳回', color: 'error' },
]

export const RECOMMENDATION_PRIORITY_OPTIONS = [
  { value: '高', label: '高', color: 'red' },
  { value: '中', label: '中', color: 'orange' },
  { value: '低', label: '低', color: 'blue' },
]
