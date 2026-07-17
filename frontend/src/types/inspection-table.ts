/**
 * 原料检验数据表类型定义
 */

// 列配置
export interface ColumnConfig {
  key: string
  label: string
  type: 'text' | 'number' | 'date' | 'select'
  width?: number
  required?: boolean
  options?: { label: string; value: string }[]
}

// 数据表
export interface InspectionTable {
  id: string
  table_name: string
  table_description?: string
  columns_config: ColumnConfig[]
  is_active: boolean
  row_count?: number
  template_path?: string
  template_name?: string
  created_at: string
  updated_at?: string
}

// 数据行
export interface InspectionTableRow {
  id: number
  table_id: string
  row_data: Record<string, any>
  sort_order: number
  created_at: string
}

// 数据表详情（包含数据行）
export interface InspectionTableDetail extends InspectionTable {
  rows: InspectionTableRow[]
}

// 创建数据表请求
export interface CreateTableRequest {
  table_name: string
  table_description?: string
  columns_config: ColumnConfig[]
}

// 更新数据表请求
export interface UpdateTableRequest {
  table_name?: string
  table_description?: string
  columns_config?: ColumnConfig[]
  is_active?: boolean
}

// 列表项
export interface TableListItem {
  id: string
  table_name: string
  table_description?: string
  is_active: boolean
  row_count: number
  created_at: string
}
