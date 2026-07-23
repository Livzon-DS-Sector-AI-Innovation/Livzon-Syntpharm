/**
 * Registration module TypeScript types
 * 
 * NOTE: These types are hand-written because the backend doesn't export them via OpenAPI.
 * The backend routes use `response_model=dict` or return dicts via `success_response()`,
 * so these types don't appear in the generated schema.
 * 
 * To fix this properly, the backend needs to:
 * 1. Add `response_model` annotations to routes in `app/modules/registration/api/`
 * 2. Use typed response models instead of `success_response()` dicts
 * 3. Regenerate OpenAPI spec and frontend types
 * 
 * See AGENTS.md: "所有 API 相关的类型必须从 @/types/generated/schema 导入"
 */

export interface ProductInfo {
  product_name: string
  registration_number: string
}

export interface AuthorizationLetter {
  id: string
  api_company: string
  product_name: string
  registration_number: string
  preparation_unit: string
  preparation_name: string
  administration_route: string
  template_file_name?: string
  output_file_name: string
  remarks?: string
  created_at: string
  updated_at: string
}

export interface AuthorizationLetterListItem {
  id: string
  product_name: string
  registration_number: string
  preparation_unit: string
  preparation_name: string
  administration_route: string
  output_file_name: string
  created_at: string
}

export interface AuthorizationLetterCreateInput {
  product_name: string
  registration_number: string
  preparation_unit: string
  preparation_name: string
  administration_route: string
  remarks?: string
}

export interface AuthorizationLetterListResponse {
  code: number
  message: string
  data: AuthorizationLetterListItem[]
  meta?: {
    page: number
    page_size: number
    total: number
  }
}

export interface AuthorizationLetterResponse {
  code: number
  message: string
  data: AuthorizationLetter
}

export interface ProductListResponse {
  code: number
  message: string
  data: ProductInfo[]
}

export interface AuthorizationLetterListParams {
  product_name?: string
  preparation_unit?: string
  page?: number
  page_size?: number
}

// ── 发补回复 ──

export interface SupplementaryReply {
  id: string
  drug_name: string
  registration_number?: string
  acceptance_number?: string
  company_name?: string
  notice_file_name?: string
  template_file_name?: string
  output_file_name: string
  question_count: number
  remarks?: string
  created_at: string
  updated_at: string
}

export interface SupplementaryReplyListItem {
  id: string
  drug_name: string
  registration_number?: string
  acceptance_number?: string
  output_file_name: string
  question_count: number
  created_at: string
}

export interface SupplementaryReplyListResponse {
  code: number
  message: string
  data: SupplementaryReplyListItem[]
  meta?: {
    page: number
    page_size: number
    total: number
  }
}

export interface SupplementaryReplyResponse {
  code: number
  message: string
  data: SupplementaryReply
}

export interface SupplementaryReplyListParams {
  drug_name?: string
  page?: number
  page_size?: number
}

// ── 对照物质说明表 ──

export interface ReferenceStandard {
  id: string
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
  coa_file_name?: string
  output_file_name: string
  remarks?: string
  created_at: string
  updated_at: string
}

export interface ReferenceStandardListItem {
  id: string
  drug_name: string
  reference_substance_name?: string
  batch_number?: string
  manufacturer?: string
  output_file_name: string
  created_at: string
}

export interface ReferenceStandardListResponse {
  code: number
  message: string
  data: ReferenceStandardListItem[]
  meta?: {
    page: number
    page_size: number
    total: number
  }
}

export interface ReferenceStandardResponse {
  code: number
  message: string
  data: ReferenceStandard
}

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

export interface Holiday {
  id: string
  year: number
  date: string
  type: 'holiday' | 'makeup'
  description: string | null
  created_at: string
  updated_at: string
}

export interface ReviewNodeConfig {
  index: number
  name: string
  days: number
}

// ── Dashboard ──

export interface DashboardProjectItem {
  id: string
  product_name: string
  market: string
  registration_type: string | null
  status: string
  submitted_at: string | null
  accepted_at: string | null
  expected_completion_at: string | null
  owner: string | null
  latest_progress: string | null
}

export interface DashboardCertificateItem {
  id: string
  product_name: string
  certificate_no: string | null
  approved_at: string | null
  valid_until: string | null
  certificate_status: string
  file_path: string | null
}

export interface DashboardSummary {
  approved_product_count: number
  overseas_approval_count: number
  submitted_project_count: number
  active_project_count: number
  recent_projects: DashboardProjectItem[]
}
