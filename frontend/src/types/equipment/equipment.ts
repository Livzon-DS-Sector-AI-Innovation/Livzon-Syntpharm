import type { components } from '../generated/schema'
import type { Equipment } from './generated-bridge'

// Re-export request types from generated schema
export type CreateCategoryInput = components['schemas']['EquipmentCategoryCreate']
export type UpdateCategoryInput = components['schemas']['EquipmentCategoryUpdate']
export type CreateEquipmentInput = components['schemas']['EquipmentCreate']
export type UpdateEquipmentInput = components['schemas']['EquipmentUpdate']

export type CreateLocationInput = components['schemas']['LocationCreate']
export type UpdateLocationInput = components['schemas']['LocationUpdate']

// Re-export response types from bridge file (excluding legacy aliases that are defined in other files)
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
  PaginatedResponse,
  EquipmentFilters,
  EquipmentStatistics,
} from './generated-bridge'

// Enums and utility types not in the bridge
export type EquipmentStatus = '在用' | '备用' | '维修中' | '停用' | '报废'
export type EquipmentImportance = '高' | '中' | '低'
export type EquipmentClass = 'A' | 'B' | 'C'

// Legacy type aliases for backward compatibility
export type {
  EquipmentCategory,
  Location,
  Equipment,
} from './generated-bridge'

// List response wrapper
export interface EquipmentListResponse {
  items: Equipment[]
  total: number
  page: number
  page_size: number
}

// Import result types
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
