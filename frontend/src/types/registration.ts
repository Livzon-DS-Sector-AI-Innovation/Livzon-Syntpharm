/**
 * Registration module TypeScript types
 *
 * 契约模型一律从 `@/types/generated/schema` 取（后端已声明具名 response_model）。
 * 仅以下前端专属类型保留手写：
 * - `*CreateInput`：表单入参
 * - `*ListParams`：查询参数
 * - `Drug` / `DrugNode` / `RegistrationProject` / `Holiday` / `DashboardSummary`：后端尚未导出契约
 */

import type { components, operations } from '@/types/generated/schema'

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


/** 契约模型，来自后端 OpenAPI（生成端点为 multipart，字段与 AuthorizationLetterCreate 一致） */
export type AuthorizationLetterCreateInput = Omit<
  components['schemas']['AuthorizationLetterResponse'],
  'id' | 'created_at' | 'updated_at' | 'created_by' | 'updated_by' | 'is_deleted' | 'api_company' | 'output_file_name' | 'output_file_key'
>

/** 契约模型，来自后端 OpenAPI */
export type AuthorizationLetterResponse = components['schemas']['DataResponse_AuthorizationLetterResponse_']


// ── 对照物质说明表 ──

/** 契约模型，来自后端 OpenAPI */
export type ReferenceStandard = components['schemas']['ReferenceStandardResponse']


/** 契约模型，来自后端 OpenAPI */
export type ReferenceStandardListItem = components['schemas']['ReferenceStandardListItem']


/** 契约模型，来自后端 OpenAPI */
export type ReferenceStandardResponse = components['schemas']['DataResponse_ReferenceStandardResponse_']


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



/** 契约模型，来自后端 OpenAPI；列表接口额外带 stage，故用交叉类型补可选字段 */
export type Drug = components['schemas']['DrugWithNodesResponse'] & {
  /** 当前阶段摘要（列表接口返回；详情接口无此字段） */
  stage?: NodeStageSummary
  nodes: DrugNode[]
}

/** 契约模型，来自后端 OpenAPI */
export type NodeStageSummary = components['schemas']['NodeStageSummary']

/** 契约模型，来自后端 OpenAPI */
export type DrugNode = components['schemas']['DrugNodeResponse']

/** 契约模型，来自后端 OpenAPI（后端恒返回该字段，故去掉可选性，值仍可能为 null） */
export type NodePrediction = Required<components['schemas']['NodePrediction']>

/** 契约模型，来自后端 OpenAPI */
export type NodeStatus = NodePrediction['status']

/** 契约模型，来自后端 OpenAPI（后端恒返回该字段，故去掉可选性，值仍可能为 null） */
export type DrugPrediction = Omit<
  Required<components['schemas']['DrugPredictionResponse']>,
  'nodes'
> & {
  nodes: NodePrediction[]
}

// ── 列表查询参数：直接取自生成契约，避免手写漂移（曾漏过 drug_id） ──
type Operations = operations

/** 授权书列表查询参数 */
export type AuthorizationLetterListParams = NonNullable<
  Operations['list_letters_api_v1_registration_authorization_letters_get']['parameters']['query']
>

/** 注册项目列表查询参数 */
export type RegistrationProjectListParams = NonNullable<
  Operations['list_projects_api_v1_registration_projects__get']['parameters']['query']
>

/** 对照物质说明表列表查询参数 */
export type ReferenceStandardListParams = NonNullable<
  Operations['get_api_v1_registration_reference_standards_get']['parameters']['query']
>

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

/** 契约模型，来自后端 OpenAPI */
export type Holiday = components['schemas']['HolidayResponse']

/** 契约模型，来自后端 OpenAPI */
export type ReviewNodeConfig = components['schemas']['ReviewNodeConfig']


// ── Dashboard ──

/** 契约模型，来自后端 OpenAPI */
export type DashboardProjectItem = components['schemas']['DashboardProjectItem']


/** 契约模型，来自后端 OpenAPI */
export type DashboardCertificateItem = components['schemas']['DashboardCertificateItem']


/** 契约模型，来自后端 OpenAPI（recent_projects 后端恒返回，故收紧为非可选） */
export type DashboardSummary = Omit<components['schemas']['DashboardSummaryResponse'], 'recent_projects'> & {
  recent_projects: DashboardProjectItem[]
}
