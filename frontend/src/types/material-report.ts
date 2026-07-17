/**
 * 原料报告单类型定义
 */

// ============ 模板相关类型 ============

export interface TemplateColumnConfig {
  key: string
  label: string
  type: 'text' | 'number' | 'date' | 'select'
  width?: number
  required?: boolean
  options?: { label: string; value: string }[]
}

export interface TableFieldsConfig {
  columns: TemplateColumnConfig[]
}

export interface TemplateCreate {
  template_name: string
  template_description?: string
  field_mapping?: Record<string, any>
  table_fields?: TableFieldsConfig
}

export interface TemplateUpdate {
  template_name?: string
  template_description?: string
  field_mapping?: Record<string, any>
  table_fields?: TableFieldsConfig
  is_active?: boolean
}

export interface TemplateResponse {
  id: string
  template_name: string
  template_file_url: string
  template_description?: string
  field_mapping: Record<string, any>
  table_fields: TableFieldsConfig
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface TemplateListItem {
  id: string
  template_name: string
  template_description?: string
  is_active: boolean
  created_at: string
}

// ============ 报告单相关类型 ============

export interface ReportCreate {
  template_id?: string
  report_title: string
  report_date: string
  static_data?: Record<string, any>
}

export interface ReportUpdate {
  template_id?: string
  report_title?: string
  report_date?: string
  static_data?: Record<string, any>
  status?: string
}

export interface ReportItemData {
  row_index: number
  field_key: string
  field_value?: string
}

export interface ReportItemsBatchSave {
  items: ReportItemData[]
}

export interface ReportResponse {
  id: string
  report_no: string
  template_id?: string
  template_name?: string
  report_title: string
  report_date: string
  static_data?: Record<string, any>
  status: string
  generated_file_url?: string
  created_at: string
  updated_at?: string
}

export interface ReportDetailResponse extends ReportResponse {
  template?: TemplateResponse
  items: Record<string, any>[]
}

export interface ReportListItem {
  id: string
  report_no: string
  template_id?: string
  template_name?: string
  report_title: string
  report_date: string
  status: string
  created_at: string
}

export interface ReportStatistics {
  total_count: number
  draft_count: number
  completed_count: number
  approved_count: number
  by_template: Record<string, number>
}

// ============ 状态映射 ============

export const reportStatusLabels: Record<string, string> = {
  draft: '草稿',
  completed: '已完成',
  approved: '已审批',
  archived: '已归档',
}

export const reportStatusColors: Record<string, string> = {
  draft: 'default',
  completed: 'processing',
  approved: 'success',
  archived: 'warning',
}