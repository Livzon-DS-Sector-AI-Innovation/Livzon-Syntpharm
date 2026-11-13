/**
 * Registration module TypeScript types
 *
 * 契约模型一律从 `@/types/generated/schema` 取（后端已声明具名 response_model）。
 * 仅以下前端专属类型保留手写：
 * - `*CreateInput`：表单入参
 * - `*ListParams`：查询参数
 * - `Drug` / `DrugNode` / `RegistrationProject` / `Holiday` / `DashboardSummary`：后端尚未导出契约
 */

import type { components } from '@/types/generated/schema'

/** 契约模型，来自后端 OpenAPI */
export type ProductInfo = components['schemas']['ProductInfo']


/** 契约模型，来自后端 OpenAPI */
export type AuthorizationLetter = components['schemas']['AuthorizationLetterResponse']


/** 契约模型，来自后端 OpenAPI */
export type AuthorizationLetterListItem = components['schemas']['AuthorizationLetterListItem']

/** 契约模型，来自后端 OpenAPI */
export type AuthorizationLetterTrail = components['schemas']['AuthorizationLetterTrailItem']

/** 契约模型，来自后端 OpenAPI */
export type AuthorizationLetterFilterOptions = components['schemas']['AuthorizationLetterFilterOptions']


export interface AuthorizationLetterCreateInput {
  product_name: string
  registration_number: string
  preparation_unit: string
  preparation_name: string
  administration_route: string
  remarks?: string
}

/** 契约模型，来自后端 OpenAPI */
export type AuthorizationLetterResponse = components['schemas']['DataResponse_AuthorizationLetterResponse_']


export interface AuthorizationLetterListParams {
  keyword?: string
  product_name?: string
  year?: number
  page?: number
  page_size?: number
}

// ── 发补回复 ──

/** 契约模型，来自后端 OpenAPI */
export type SupplementaryReply = components['schemas']['SupplementaryReplyResponse']


/** 契约模型，来自后端 OpenAPI */
export type SupplementaryReplyListItem = components['schemas']['SupplementaryReplyListItem']


/** 契约模型，来自后端 OpenAPI */
export type SupplementaryReplyResponse = components['schemas']['DataResponse_SupplementaryReplyResponse_']


export interface SupplementaryReplyListParams {
  drug_name?: string
  page?: number
  page_size?: number
}

// ── 对照物质说明表 ──

/** 契约模型，来自后端 OpenAPI */
export type ReferenceStandard = components['schemas']['ReferenceStandardResponse']


/** 契约模型，来自后端 OpenAPI */
export type ReferenceStandardListItem = components['schemas']['ReferenceStandardListItem']


/** 契约模型，来自后端 OpenAPI */
export type ReferenceStandardResponse = components['schemas']['DataResponse_ReferenceStandardResponse_']


export interface ReferenceStandardListParams {
  drug_name?: string
  page?: number
  page_size?: number
}

export interface ReferenceStandardCreateInput {
  drug_name: string
  reference_substance_name?: string
  batch_number?: string
  manufacturer?: string
  english_name?: string
  molecular_formula?: string
  molecular_weight?: string
  cas_number?: string
  content?: string
  moisture?: string
  rsd?: string
  expiration_date?: string
  storage_condition?: string
  remarks?: string
}

/** COA 解析结果（POST /api/v1/registration/reference-standards/parse-coa 的 data 字段） */
// COA 解析结果直接使用后端契约（GET/POST 已声明 response_model=CoaParseResult），
// 不再手写一份容易漂移的 metadata 结构。
export type ParseCOAResponse = components['schemas']['CoaParseResult']

// ── 药品与审评节点 ──



export interface Drug {
  id: string
  name: string
  type: '仿制药' | '创新药' | '原料药'
  acceptance_date: string
  acceptance_number?: string | null
  current_node: number
  created_at: string
  updated_at: string
  nodes: DrugNode[]
}

export interface DrugNode {
  id: string
  drug_id: string
  node_index: number
  actual_date: string | null
  skipped: boolean
  created_at: string
  updated_at: string
}

export type NodeStatus = 'completed' | 'in_progress' | 'pending' | 'skipped'

export interface NodePrediction {
  node_index: number
  node_name: string
  status: NodeStatus
  actual_date: string | null
  estimated_date: string | null
  estimated_range: [string, string] | null
  delta_days: number | null
}

export interface DrugPrediction {
  drug_id: string
  total_nodes: number
  completed_nodes: number
  current_node_index: number | null
  days_in_current_node: number | null
  estimated_approval_date: string | null
  nodes: NodePrediction[]
}

/** 契约模型，来自后端 OpenAPI（`projects.py` 已声明 `DataResponse[ProjectResponse]`） */
export type RegistrationProject = components['schemas']['ProjectResponse']

/** 契约模型，来自后端 OpenAPI */
export type ProjectProgressLog = components['schemas']['ProgressLogResponse']

/** 契约模型，来自后端 OpenAPI */
export type ProjectKpi = components['schemas']['ProjectKpiResponse']

/** 契约模型，来自后端 OpenAPI */
export type ProjectCreatePayload = components['schemas']['ProjectCreate']

/** 契约模型，来自后端 OpenAPI */
export type ProjectUpdatePayload = components['schemas']['ProjectUpdate']

/** 申报前阶段 key（与后端 PreStage 一致） */
export type PreStage = 'initiation' | 'data_preparation' | 'internal_review' | 'submission' | 'accepted'

export interface Holiday {
  id: string
  year: number
  date: string
  type: 'holiday' | 'makeup'
  description: string | null
  created_at: string
  updated_at: string
}

/** 契约模型，来自后端 OpenAPI */
export type ReviewNodeConfig = components['schemas']['ReviewNodeConfig']


// ── Dashboard ──

/** 契约模型，来自后端 OpenAPI */
export type DashboardProjectItem = components['schemas']['DashboardProjectItem']


/** 契约模型，来自后端 OpenAPI */
export type DashboardCertificateItem = components['schemas']['DashboardCertificateItem']


export interface DashboardSummary {
  approved_product_count: number
  overseas_approval_count: number
  submitted_project_count: number
  active_project_count: number
  recent_projects: DashboardProjectItem[]
}
