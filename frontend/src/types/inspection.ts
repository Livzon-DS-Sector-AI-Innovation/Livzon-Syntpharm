import type { components } from '@/types/generated/schema'

// ==================== 巡检枚举 ====================
export type InspectionTaskStatus = '待执行' | '执行中' | '已完成' | '已关闭'
export type InspectionPlanType = '线路巡检' | '设备巡检'
export type InspectionOverallResult = '正常' | '异常'
export type CheckResult = '正常' | '异常' | '跳过'

// ==================== 巡检路线 ====================
export interface InspectionRoute {
  id: string
  name: string
  description: string | null
  is_active: boolean
  equipment_count: number
  location_count: number
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

export interface InspectionRouteDetail extends InspectionRoute {
  locations: RouteLocation[]
}

export type CreateInspectionRouteInput = components['schemas']['InspectionRouteCreate']

export type UpdateInspectionRouteInput = components['schemas']['InspectionRouteUpdate']

// ==================== 路线地点配置 ====================
export interface RouteLocation {
  id: string
  location_id: string
  location_name: string | null
  sort_order: number
  equipments: RouteLocationEquipment[]
}

export interface RouteLocationEquipment {
  id: string
  equipment_id: string
  sort_order: number
  equipment_name: string | null
  asset_no: string | null
  templates: RouteEquipmentTemplate[]
}

export interface RouteEquipmentTemplate {
  id: string
  template_id: string
  template_name: string | null
}

// 批量设置请求
export interface RouteLocationsBatch {
  locations: RouteLocationItem[]
}

export interface RouteLocationItem {
  location_id: string
  sort_order: number
  equipments: RouteLocationEquipmentItem[]
}

export interface RouteLocationEquipmentItem {
  equipment_id: string
  sort_order: number
  template_ids: string[]
}

// 保留旧类型兼容
export interface RouteEquipment {
  id: string
  equipment_id: string
  sort_order: number
  equipment_name?: string
  asset_no?: string
}

export interface RouteEquipmentItem {
  equipment_id: string
  sort_order: number
}

export interface InspectionRouteFilters {
  is_active?: boolean
  location_id?: string
  keyword?: string
  page?: number
  page_size?: number
}

export interface InspectionRouteListResponse {
  items: InspectionRoute[]
  total: number
  page: number
  page_size: number
}

// ==================== 巡检任务 ====================
export interface InspectionTask {
  id: string
  task_no: string
  route_id: string | null
  equipment_id: string | null
  equipment_ids: string[] | null
  template_ids: string[] | null
  equipment_templates: Record<string, string[]> | null
  plan_type: InspectionPlanType
  assigned_to: string | null
  planned_time: string
  status: InspectionTaskStatus
  overall_result: InspectionOverallResult | null
  started_at: string | null
  completed_at: string | null
  closed_at: string | null
  closure_remark: string | null
  route_summary?: string | null
  created_at: string
  updated_at: string
  route_name?: string
  equipment_name?: string
  asset_no?: string
  assignee_name?: string
  equipment_count?: number
  completed_count?: number
  completed_equipment_ids?: string[]
  photo_count?: number
}

export type CreateInspectionTaskInput = components['schemas']['InspectionTaskCreate']

export interface InspectionTaskFilters {
  status?: InspectionTaskStatus
  exclude_status?: InspectionTaskStatus
  route_id?: string
  assigned_to?: string
  equipment_id?: string
  planned_time_from?: string
  planned_time_to?: string
  page?: number
  page_size?: number
}

export interface InspectionTaskListResponse {
  items: InspectionTask[]
  total: number
  page: number
  page_size: number
}

// ==================== 巡检执行 ====================
export interface InspectionRecordItem {
  template_item_id: string
  result: CheckResult
  actual_value?: string
  remark?: string
}

export interface EquipmentCheckResult {
  records: InspectionRecordItem[]
}

export interface InspectionRecord {
  id: string
  task_id: string
  equipment_id: string | null
  equipment_name: string | null
  template_item_id: string
  result: string
  actual_value: string | null
  remark: string | null
  item_name?: string
  expected_result?: string
  created_at: string
  route_location_id?: string | null
}

// ==================== 线路巡检提交 ====================
export interface RouteCheckSubmitInput {
  overall_result: InspectionOverallResult
  route_summary?: string
}

// ==================== 巡检照片 ====================
export interface InspectionPhoto {
  id: string
  task_id: string
  equipment_id: string | null
  file_name: string
  file_size: number | null
  uploaded_at: string
}

// ==================== 历史记录 ====================
export interface InspectionTaskDetail extends InspectionTask {
  records: InspectionRecord[]
  photos: InspectionPhoto[]
}

export interface InspectionHistoryFilters {
  date_from?: string
  date_to?: string
  equipment_id?: string
  route_id?: string
  result?: InspectionOverallResult
  page?: number
  page_size?: number
}

export interface InspectionHistoryListResponse {
  items: InspectionTask[]
  total: number
  page: number
  page_size: number
}

// ==================== 定时任务 ====================
export interface InspectionRouteSchedule {
  id: string
  route_id: string
  cron_expression: string
  assigned_to: string | null
  assignee_name?: string | null
  is_active: boolean
  last_triggered_at: string | null
  next_trigger_at: string | null
  created_at: string
  updated_at: string
}

export type CreateInspectionScheduleInput = components['schemas']['InspectionScheduleCreate']

export type UpdateInspectionScheduleInput = components['schemas']['InspectionScheduleUpdate']

// ==================== AI 分析 ====================
export interface InspectionAIAnalyzeRequest {
  image_base64: string
  image_mime_type: string
}

export interface InspectionAIItemResult {
  template_item_id: string
  item_name: string
  expected_result: string | null
  result: CheckResult
  actual_value: string | null
  remark: string | null
}
