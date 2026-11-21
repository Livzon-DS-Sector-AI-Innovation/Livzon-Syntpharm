import type { components, operations } from '@/types/generated/schema'
import type {
  MaintenancePlan as GeneratedMaintenancePlan,
  MaintenancePlanListResponse as GeneratedMaintenancePlanListResponse,
} from './generated-bridge'

export type CreateMaintenancePlanInput = components['schemas']['MaintenancePlanCreate']
export type UpdateMaintenancePlanInput = components['schemas']['MaintenancePlanUpdate']

// ==================== 维护计划 ====================
// 契约字段统一由 generated-bridge（OpenAPI 派生）维护，本文件只做别名，
// 避免同一个响应结构在两处并行加字段（如 responsible_person_name）。
export type MaintenancePlan = GeneratedMaintenancePlan
export type MaintenancePlanListResponse = GeneratedMaintenancePlanListResponse

/** 表单下拉用的取值集合（UI 类型，不是接口契约） */
export type MaintenancePlanType = '预防性维护' | '预测性维护'
/** 表单下拉用的取值集合（UI 类型，不是接口契约） */
export type MaintenancePlanStatus = '启用' | '停用' | '已完成'
/** 表单下拉用的取值集合（UI 类型，不是接口契约） */
export type FrequencyUnit = '天' | '周' | '月' | '年'

/** 列表查询参数：直接取生成契约，避免手写字段与后端漂移。 */
export type MaintenancePlanFilters = NonNullable<
  operations['list_maintenance_plans_api_v1_equipment_maintenance_plans__get']['parameters']['query']
>