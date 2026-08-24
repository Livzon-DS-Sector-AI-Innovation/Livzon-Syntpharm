/**
 * Type bridge between hand-written equipment types and generated OpenAPI types
 * 
 * This file provides type aliases that map our hand-written domain types to
 * the closest equivalents in the generated OpenAPI schema.
 * 
 * For request types (Create/Update), we use generated types directly.
 * For response types, we define structural types that match the backend Pydantic models.
 * 
 * Migration strategy:
 * - Phase 1 (Expand): Use this bridge file alongside existing types
 * - Phase 2 (Migrate): Update components to use these types
 * - Phase 3 (Contract): Remove hand-written types, keep only generated types
 */

import type { components } from '../generated/schema'

// ============================================================================
// Request Types (from generated schema)
// ============================================================================

export type EquipmentCategoryCreate = components['schemas']['EquipmentCategoryCreate']
export type EquipmentCategoryUpdate = components['schemas']['EquipmentCategoryUpdate']
export type EquipmentCreate = components['schemas']['EquipmentCreate']
export type EquipmentUpdate = components['schemas']['EquipmentUpdate']
export type LocationCreate = components['schemas']['LocationCreate']
export type LocationUpdate = components['schemas']['LocationUpdate']
export type FailureCodeCreate = components['schemas']['FailureCodeCreate']
export type FailureCodeUpdate = components['schemas']['FailureCodeUpdate']
export type SparePartCreate = components['schemas']['SparePartCreate']
export type SparePartUpdate = components['schemas']['SparePartUpdate']
export type WorkOrderCreate = components['schemas']['WorkOrderCreate']
export type WorkOrderUpdate = components['schemas']['WorkOrderUpdate']
export type CalibrationPlanCreate = components['schemas']['CalibrationPlanCreate']
export type CalibrationPlanUpdate = components['schemas']['CalibrationPlanUpdate']
export type InspectionTemplateCreate = components['schemas']['InspectionTemplateCreate']
export type InspectionTemplateUpdate = components['schemas']['InspectionTemplateUpdate']
export type InspectionTemplateItemCreate = components['schemas']['InspectionTemplateItemCreate']
export type InspectionTemplateItemUpdate = components['schemas']['InspectionTemplateItemUpdate']

// ============================================================================
// Response Types (structural types matching backend Pydantic models)
// These should eventually be replaced with generated types once backend
// endpoints return proper response models instead of generic ApiResponse
// ============================================================================

/**
 * Equipment category response
 * Matches backend: EquipmentCategoryResponse
 */
export interface EquipmentCategoryResponse {
  id: string
  name: string
  code: string
  parent_id: string | null
  description: string | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/**
 * Equipment category tree node
 * Matches backend: EquipmentCategoryTree
 */
export interface EquipmentCategoryTree extends EquipmentCategoryResponse {
  children: EquipmentCategoryTree[]
}

/**
 * Location response
 * Matches backend: LocationResponse (if exists) or similar structure
 */
export interface LocationResponse {
  id: string
  name: string
  code: string
  parent_id: string | null
  description: string | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/**
 * Location tree node
 */
export interface LocationTree extends LocationResponse {
  children: LocationTree[]
}

/**
 * Equipment response
 * Matches backend: EquipmentResponse (if exists)
 */
export interface EquipmentResponse {
  id: string
  asset_no: string
  name: string
  equipment_tag: string | null
  equipment_class: string
  category_description: string | null
  category_ids: string[]
  location_id: string | null
  status: string
  importance: string
  model: string | null
  specification: string | null
  manufacturer: string | null
  supplier: string | null
  production_date: string | null
  commissioning_date: string | null
  description: string | null
  current_cost: number | null
  book_value: number | null
  warranty_expire_date: string | null
  depreciation_years: number | null
  technical_params: Record<string, unknown> | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  department_id: string | null
  department_name: string | null
  responsible_person_id: string | null
  responsible_person_name: string | null
  label_no: string | null
  scrap_status: string | null
  scrap_time: string | null
}

/**
 * Failure code response
 */
export interface FailureCodeResponse {
  id: string
  code: string
  name: string
  type: string
  description: string | null
  created_at: string
  updated_at: string
}

/**
 * Spare part response
 */
export interface SparePartResponse {
  id: string
  code: string
  name: string
  specification: string | null
  unit: string
  stock_quantity: number
  min_stock: number
  max_stock: number
  location: string | null
  equipment_ids: string[]
  created_at: string
  updated_at: string
}

/**
 * Work order response
 */
export interface WorkOrderResponse {
  id: string
  order_no: string
  equipment_id: string
  equipment_name: string
  fault_type: string
  fault_description: string
  priority: string
  status: string
  assignee_id: string | null
  assignee_name: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

/**
 * Calibration plan response
 */
export interface CalibrationPlanResponse {
  id: string
  equipment_id: string
  equipment_name: string
  plan_date: string
  actual_date: string | null
  status: string
  result: string | null
  created_at: string
  updated_at: string
}

/**
 * Inspection template response
 */
export interface InspectionTemplateResponse {
  id: string
  name: string
  description: string | null
  equipment_category_id: string | null
  items: InspectionTemplateItemResponse[]
  created_at: string
  updated_at: string
}

/**
 * Inspection template item response
 */
export interface InspectionTemplateItemResponse {
  id: string
  template_id: string
  name: string
  standard: string | null
  method: string | null
  sort_order: number
}

// ============================================================================
// List/Filter Types
// ============================================================================

/**
 * Paginated list response
 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/**
 * Equipment filters
 */
export interface EquipmentFilters {
  category_id?: string
  location_id?: string
  department_id?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
  is_active?: boolean
}

/**
 * Work order filters
 */
export interface WorkOrderFilters {
  status?: string
  priority?: string
  equipment_id?: string
  assignee_id?: string
  order_type?: string
  exclude_status?: string
  page?: number
  page_size?: number
  is_active?: boolean
}

/**
 * Spare part filters
 */
export interface SparePartFilters {
  category?: string
  keyword?: string
  equipment_id?: string
  page?: number
  page_size?: number
  is_active?: boolean
}

/**
 * Calibration plan filters
 */
export interface CalibrationPlanFilters {
  equipment_id?: string
  status?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
  is_active?: boolean
}

/**
 * Inspection template filters
 */
export interface InspectionTemplateFilters {
  equipment_category_id?: string
  keyword?: string
  is_active?: boolean
  page?: number
  page_size?: number
}

// ============================================================================
// Statistics Types
// ============================================================================

/**
 * Equipment statistics
 */
export interface EquipmentStatistics {
  total: number
  by_status: Record<string, number>
  by_category: Record<string, number>
  by_location: Record<string, number>
}

/**
 * Work order statistics
 */
export interface WorkOrderStatistics {
  total: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  by_priority: Record<string, number>
  overdue?: number
}
