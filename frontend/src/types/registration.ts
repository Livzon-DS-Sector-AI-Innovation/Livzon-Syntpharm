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
  product_name?: string
  preparation_unit?: string
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
  created_at: string
  updated_at: string
}

/**
 * 注册项目（GET /api/v1/registration/projects/ 的返回项）。
 *
 * 手写原因：后端 `app/modules/registration/api/projects.py` 未声明 `response_model`，
 * 该端点在 OpenAPI 里的响应是泛化 object，无法生成具体类型。
 * 待后端补齐 `response_model` 后应改为 `components['schemas']['...']` 并删除本接口。
 */
export interface RegistrationProject {
  id: string
  product_name: string
  market: string
  registration_type: string | null
  status: string
  submitted_at: string | null
  accepted_at: string | null
  approved_at: string | null
  expected_completion_at: string | null
  owner: string | null
  latest_progress: string | null
  created_at: string
  updated_at: string
}

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
