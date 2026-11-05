/**
 * Safety module domain model types (ViewModels).
 * API 契约字段一律从 OpenAPI 生成类型派生（@/types/generated/schema），禁止手写，
 * 避免后端新增字段后前端静默丢失。仅枚举展示类型、查询参数、统计等前端私有结构手写。
 */

// ============ HazardReport Types ============

import type { components } from "@/types/generated/schema"
import { HazardType, HazardLevel, HazardCategory } from "./enums"

type HazardReportApi = components["schemas"]["HazardReportResponse"]

/** 隐患详情（响应契约来自 OpenAPI；枚举字段收窄为本地 enum 以便选项渲染） */
export interface HazardReport extends Omit<HazardReportApi, "hazard_type" | "hazard_level" | "hazard_category"> {
  hazard_type: HazardType
  hazard_level: HazardLevel
  hazard_category?: HazardCategory
}

/** 表单载荷（创建契约来自 OpenAPI，overall_status 为平台内部草稿态） */
export type HazardReportFormData = Partial<components["schemas"]["HazardReportCreate"]> & {
  overall_status?: string
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

export interface VerifyLevelRequest {
  level: number
  action: 'approved' | 'rejected'
  opinion?: string
}

export interface ConfirmCheckRequest {
  role: 'inspector' | 'safety_officer'
}

