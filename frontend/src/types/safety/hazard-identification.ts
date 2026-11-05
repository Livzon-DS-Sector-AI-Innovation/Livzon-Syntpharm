/**
 * Safety module domain model types (ViewModels).
 * API 契约字段一律从 OpenAPI 生成类型派生（@/types/generated/schema），禁止手写，
 * 避免后端新增字段后前端静默丢失。仅枚举展示类型、查询参数等前端私有结构手写。
 */

import type { components } from '@/types/generated/schema'

/** 危险源辨识台账记录（响应契约来自 OpenAPI） */
export type HazardIdentification = components['schemas']['HazardIdentificationResponse']

export interface HazardIdentificationFormData {
  hazard_id_no?: string  // 留空时后端自动生成 HI-YYYYMMDD-NNN
  department: string
  position: string
  production_step?: string  // 已取消输入
  regulation_id?: string  // 引用的安全操作规程 ID
  notes?: string
}

// ── 批量辨识 ──

export interface RegulationStageInfo {
  stage_name: string
  safety_count: number
  operation_count: number
}

export interface RegulationStagesResponse {
  regulation_id: string
  regulation_name?: string
  stages: RegulationStageInfo[]
}

export interface HazardIdentificationBatchCreateInput {
  regulation_id: string
  department: string
  position: string
  stage_names: string[]
  notes?: string
  auto_submit?: boolean
}

export interface HazardIdentificationBatchResponse {
  batch_id: string
  regulation_id: string
  regulation_name?: string
  records: HazardIdentification[]
  total_stages: number
  created_count: number
}

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

export interface HazardIdentificationStats {
  total_draft: number
  total_in_progress: number
  total_pending_review: number
  total_completed: number
}

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

export interface HazardLedgerExportRequest {
  natural_query?: string
  department?: string
  position?: string
  risk_level?: string
  date_from?: string
  date_to?: string
  keyword?: string
}

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
