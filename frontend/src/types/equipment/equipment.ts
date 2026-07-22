// 设备分类
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

export interface CreateCategoryInput {
  name: string
  code: string
  parent_id?: string
  description?: string
}

export interface UpdateCategoryInput {
  name?: string
  code?: string
  parent_id?: string
  description?: string
}

// 位置管理
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

export interface CreateLocationInput {
  name: string
  code: string
  parent_id?: string
  description?: string
}

export interface UpdateLocationInput {
  name?: string
  code?: string
  parent_id?: string
  description?: string
}

// 设备管理
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

export interface CreateEquipmentInput {
  name: string
  asset_no: string
  category_ids: string[]
  location_id: string
  status?: EquipmentStatus
  importance?: EquipmentImportance
  model?: string
  specification?: string
  manufacturer?: string
  supplier?: string
  production_date?: string
  commissioning_date?: string
  description?: string
  department_id?: string
  responsible_person_id?: string
}

export interface UpdateEquipmentInput {
  name?: string
  category_ids?: string[]
  location_id?: string
  status?: EquipmentStatus
  importance?: EquipmentImportance
  model?: string
  specification?: string
  manufacturer?: string
  supplier?: string
  production_date?: string
  commissioning_date?: string
  description?: string
  department_id?: string
  responsible_person_id?: string | null
}

// 列表和筛选
export interface EquipmentFilters {
  category_id?: string
  location_id?: string
  department_id?: string
  status?: EquipmentStatus
  keyword?: string
  page?: number
  page_size?: number
}

export interface EquipmentListResponse {
  items: Equipment[]
  total: number
  page: number
  page_size: number
}

// 统计
export interface EquipmentStatistics {
  total: number
  by_status: Record<EquipmentStatus, number>
  by_category: Record<string, number>
  by_location: Record<string, number>
}

// 导入结果
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
