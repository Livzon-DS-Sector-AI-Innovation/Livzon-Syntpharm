/**
 * Safety module domain model types (ViewModels).
 * API 契约字段一律从 OpenAPI 生成类型派生（@/types/generated/schema），禁止手写，
 * 避免后端新增字段后前端静默丢失。仅枚举展示类型、查询参数、统计等前端私有结构手写。
 */

// ============ HazardReport Types ============

import type { components } from "@/types/generated/schema"
import { HazardType, HazardLevel } from "./enums"

type HazardReportApi = components["schemas"]["HazardReportResponse"]

/** 隐患详情（响应契约来自 OpenAPI；枚举字段收窄为本地 enum 以便选项渲染） */
export interface HazardReport extends Omit<HazardReportApi, "hazard_type" | "hazard_level" | "hazard_category"> {
  hazard_type: HazardType
  hazard_level: HazardLevel
  /** 隐患类别：字典表名称（内置 7 类 + 用户新增），旧记录可能是英文枚举值 */
  hazard_category?: string
}

/** 表单载荷（创建契约来自 OpenAPI，overall_status 为平台内部草稿态） */
export type HazardReportFormData = Partial<components["schemas"]["HazardReportCreate"]> & {
  overall_status?: string
  /** 整改进度：走 PUT /hazards/{id} 人工维护（创建契约不含该字段） */
  rectification_status?: string
}

export interface HazardReportQueryParams {
  page?: number
  page_size?: number
  status?: string
  rectification_status?: string
  overall_status?: string
  hazard_type?: string
  hazard_level?: string
  hazard_category?: string
  inspection_category?: string
  department?: string
  keyword?: string
  /** "pending" 时只返回人员待匹配记录（有姓名、未绑定系统用户） */
  person_match?: 'pending'
}

/** 隐患统计（响应契约来自 OpenAPI 生成类型，禁止手写） */
export type HazardStats = components['schemas']['HazardStatsResponse']

export type RectificationReplyRequest = components["schemas"]["RectificationReplyRequest"]

/**
 * 分级审批请求：字段来自 OpenAPI 生成类型，仅把 action 收窄为字面量联合
 * （后端 schema 未用 Literal，生成类型是 string）。
 */
export type VerifyLevelRequest =
  Omit<components['schemas']['VerifyLevelRequest'], 'action'> & { action: 'approved' | 'rejected' }

/** 确认检查请求：字段来自 OpenAPI 生成类型，仅把 role 收窄为字面量联合。 */
export type ConfirmCheckRequest =
  Omit<components['schemas']['ConfirmCheckRequest'], 'role'> & { role: 'inspector' | 'safety_officer' }

