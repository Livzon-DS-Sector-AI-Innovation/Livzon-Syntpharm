import type { components } from '../generated/schema'

// Re-export request types from generated schema
export type CreateCategoryInput = components['schemas']['EquipmentCategoryCreate']
export type UpdateCategoryInput = components['schemas']['EquipmentCategoryUpdate']
export type CreateEquipmentInput = components['schemas']['EquipmentCreate']
export type UpdateEquipmentInput = components['schemas']['EquipmentUpdate']

export type CreateLocationInput = components['schemas']['LocationCreate']
export type UpdateLocationInput = components['schemas']['LocationUpdate']

// Import response types from bridge file
export type {
  EquipmentCategoryResponse,
  EquipmentCategoryTree,
  LocationResponse,
  LocationTree,
  EquipmentResponse,
  FailureCodeResponse,
  SparePartResponse,
  WorkOrderResponse,
  CalibrationPlanResponse,
  InspectionTemplateResponse,
  InspectionTemplateItemResponse,
  EquipmentFilters,
  EquipmentStatistics,
} from './generated-bridge'

// Legacy type aliases for backward compatibility
// These match the structure of the backend Pydantic models
export interface EquipmentCategory {
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
  children?: EquipmentCategory[]
}

export interface Location {
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
  children?: Location[]
}

export type EquipmentStatus = '在用' | '备用' | '维修中' | '停用' | '报废'
export type EquipmentImportance = '高' | '中' | '低'
export type EquipmentClass = 'A' | 'B' | 'C'

export interface Equipment {
  id: string
  asset_no: string
  equipment_tag: string | null
  equipment_class: EquipmentClass
  category_description: string | null
  name: string
  category_ids: string[]
  category_names?: string | null
  location_id: string | null
  location_text: string | null
  location_name?: string | null
  status: EquipmentStatus
  importance: EquipmentImportance
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
  category?: EquipmentCategory
  location?: Location
}

export interface EquipmentListResponse {
  items: Equipment[]
  total: number
  page: number
  page_size: number
}

export interface ImportResult {
  success: number
  failed: number
  errors: ImportRowError[]
  error?: string
  data?: any
  imported?: number
  skipped?: number
  warnings?: any[]
}

export interface ImportRowError {
  row: number
  field: string
  message: string
}
