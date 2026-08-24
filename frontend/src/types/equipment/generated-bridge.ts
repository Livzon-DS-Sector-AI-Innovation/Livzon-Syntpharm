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
  current_cost: number | null
  book_value: number | null
  warranty_expire_date: string | null
  depreciation_years: number | null
  technical_params: Record<string, unknown> | null
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
  current_cost: number | null
  book_value: number | null
  warranty_expire_date: string | null
  depreciation_years: number | null
  technical_params: Record<string, unknown> | null
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
  category_names?: string | null
  location_id: string | null
  location_text: string | null
  location_name?: string | null
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
  category?: EquipmentCategoryResponse
  location?: LocationResponse
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
  sort_order?: number
  is_active?: boolean
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
  category: string | null
  default_supplier: string | null
  unit_price: number | null
  is_active: boolean
  current_qty?: number
  min_qty?: number
  max_qty?: number
  location: string | null
  equipment_ids: string[]
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/**
 * Work order response
 */
export interface WorkOrderResponse {
  id: string
  work_order_no: string
  equipment_id: string
  equipment_name?: string
  asset_no?: string
  order_type: string
  priority: string
  status: string
  fault_symptom_id: string | null
  fault_cause_id: string | null
  fault_action_id: string | null
  fault_description: string | null
  reporter_id: string | null
  assignee_id: string | null
  assignee_name?: string
  verified_by: string | null
  reported_at: string
  assigned_at: string | null
  started_at: string | null
  completed_at: string | null
  verified_at: string | null
  verification_result: string | null
  verification_remark: string | null
  repair_detail: string | null
  actual_duration: number | null
  original_equipment_status: string | null
  maintenance_plan_id: string | null
  planned_start_date: string | null
  checklist_template_id: string | null
  check_result: string | null
  spare_parts_cost: number | null
  responsible_person_id?: string | null
  symptom_name?: string | null
  reporter_name?: string | null
  responsible_person_name?: string | null
  images?: Array<{id: string, url: string, file_name?: string}> | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/**
 * Calibration plan response
 */
export interface CalibrationPlanResponse {
  id: string
  equipment_id: string
  equipment_name?: string
  asset_no?: string
  calibration_type: string
  cycle_months: number
  last_calibration_date: string | null
  next_calibration_date: string | null
  responsible_person_id: string | null
  responsible_person_name?: string
  status: string
  remark: string | null
  plan_date?: string
  actual_date?: string
  result?: string
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/**
 * Inspection template response
 */
export interface InspectionTemplateResponse {
  id: string
  name: string
  description: string | null
  equipment_category_id: string | null
  equipment_category_name?: string | null
  is_active: boolean
  items_count: number
  items: InspectionTemplateItemResponse[]
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/**
 * Inspection template item response
 */
export interface InspectionTemplateItemResponse {
  id: string
  template_id: string
  item_name: string
  item_description: string | null
  expected_result: string | null
  check_method?: string | null
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
}

/**
 * Spare part filters
 */
export interface SparePartFilters {
  keyword?: string
  equipment_id?: string
  category?: string
  is_active?: boolean
  low_stock?: boolean
  page?: number
  page_size?: number
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

// ============================================================================
// Legacy Type Aliases (for backward compatibility during migration)
// These map old hand-written type names to the new bridge types
// ============================================================================

/** @deprecated Use EquipmentCategoryTree instead */
export type EquipmentCategory = EquipmentCategoryTree

/** @deprecated Use LocationTree instead */
export type Location = LocationTree

/** @deprecated Use EquipmentResponse instead */
export type Equipment = EquipmentResponse

/** @deprecated Use FailureCodeResponse instead */
export type FailureCode = FailureCodeResponse

/** @deprecated Use SparePartResponse instead */
export type SparePart = SparePartResponse

/** @deprecated Use WorkOrderResponse instead */
export type WorkOrder = WorkOrderResponse

/** @deprecated Use CalibrationPlanResponse instead */
export type CalibrationPlan = CalibrationPlanResponse

/** @deprecated Use InspectionTemplateResponse instead */
export type InspectionTemplate = InspectionTemplateResponse

/** @deprecated Use InspectionTemplateItemResponse instead */
export type InspectionTemplateItem = InspectionTemplateItemResponse

/**
 * Maintenance plan response
 */
export interface MaintenancePlanResponse {
  id: string
  equipment_id: string
  plan_name: string
  plan_type: string
  frequency: number
  frequency_unit: string
  last_maintenance_date: string | null
  next_maintenance_date: string | null
  responsible_person_id: string | null
  maintenance_content: string | null
  status: string
  remark: string | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

/**
 * Maintenance plan filters
 */
export interface MaintenancePlanFilters {
  equipment_id?: string
  status?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

/** @deprecated Use MaintenancePlanResponse instead */
export type MaintenancePlan = MaintenancePlanResponse

/**
 * Calibration record response
 */
export interface CalibrationRecordResponse {
  id: string
  calibration_plan_id: string
  equipment_id: string
  calibration_date: string
  calibration_type: string
  result: string
  certificate_no: string | null
  calibrated_by: string | null
  next_due_date: string
  remark: string | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  equipment_name?: string
  asset_no?: string
}

/** @deprecated Use CalibrationRecordResponse instead */
export type CalibrationRecord = CalibrationRecordResponse

/**
 * Material record response
 */
export interface MaterialRecordResponse {
  id: string
  work_order_id: string
  spare_part_id: string
  quantity: number
  remark: string | null
  created_at: string
  created_by: string | null
  spare_part_name?: string
  spare_part_code?: string
  spare_part_unit?: string
}

/** @deprecated Use MaterialRecordResponse instead */
export type MaterialRecord = MaterialRecordResponse

/**
 * Stock warning response
 */
export interface StockWarningResponse {
  spare_part_id: string
  code: string
  name: string
  current_qty: number
  min_qty: number
}

/** @deprecated Use StockWarningResponse instead */
export type StockWarning = StockWarningResponse

/**
 * Inspection record item
 */
export interface InspectionRecordItemResponse {
  item_id: string
  result: string
  actual_value?: string
  remark?: string
}

/** @deprecated Use InspectionRecordItemResponse instead */
export type InspectionRecordItem = InspectionRecordItemResponse
