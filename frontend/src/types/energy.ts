import type { components } from '@/types/generated/schema'

// Type aliases for generated types
export type EnergyPlatform = components['schemas']['EnergyPlatformResponse']
export type MonthlySummary = components['schemas']['MonthlySummaryApiResponse']['data']
export type CreateDeviceInput = components['schemas']['EnergyDeviceConfigCreate']
export type UpdateDeviceInput = components['schemas']['EnergyDeviceConfigUpdate']
export type CreateRuleInput = components['schemas']['EnergyAlertRuleCreate']
export type UpdateRuleInput = components['schemas']['EnergyAlertRuleUpdate']
export type CreateWorkshopInput = components['schemas']['EnergyWorkshopCreate']
export type UpdateWorkshopInput = components['schemas']['EnergyWorkshopUpdate']
export type CreateMonthlyRecordInput = components['schemas']['EnergyMonthlyRecordCreate']
export type FeishuImportRequest = components['schemas']['FeishuEnergyImportRequest']

// Type aliases for response types (now available in generated schema)
export type EnergyDeviceConfig = components['schemas']['EnergyDeviceConfigResponse']
export type AlertRule = components['schemas']['EnergyAlertRuleResponse']
export type AlertRecord = components['schemas']['EnergyAlertRecordResponse']
export type EnergyWorkshop = components['schemas']['EnergyWorkshopResponse']
export type EnergyMonthlyRecord = components['schemas']['EnergyMonthlyRecordResponse']

// 处理预警记录输入
export type ProcessRecordInput = components['schemas']['AlertRecordProcessRequest']

// ── API 响应类型（唯一来源：@/types/generated/schema）──

export type EnergyData = components['schemas']['EnergyDataResponse']
export type EnergyStatistics = components['schemas']['EnergyOverviewSummary']
export type EnergyOverviewData = components['schemas']['EnergyOverviewApiResponse']['data']
export type TrendDataPoint = components['schemas']['EnergyOverviewTrendPoint']
export type CollectLog = components['schemas']['CollectLogResponse']
export type CollectLogDeviceDetail = components['schemas']['CollectLogDeviceDetail']
export type CollectLogDetail = components['schemas']['CollectLogDetailResponse']
export type FeishuImportResult = components['schemas']['FeishuEnergyImportResponse']

// ── UI 类型（用于入参、表单状态、组件 props、本地状态；非 API 契约）──

// 能源类型枚举
export type EnergyType = 'electricity' | 'water' | 'steam' | 'natural_gas'

// 监控级别
export type MonitorLevel = 'normal' | 'important' | 'urgent'

// 设备查询参数
export interface DeviceQueryParams {
  keyword?: string
  energy_type?: EnergyType
  workshop?: string
  is_enabled?: boolean
  page?: number
  page_size?: number
}

// 能耗数据查询参数
export interface DataQueryParams {
  energy_type?: EnergyType
  workshop?: string
  device_id?: string
  start_time?: string
  end_time?: string
  page?: number
  page_size?: number
}

// 统计查询参数
export interface StatisticsParams {
  start_time?: string
  end_time?: string
  energy_type?: EnergyType
}

// 采集状态
export type CollectStatus = 'success' | 'partial' | 'failed'

// 采集日志查询参数
export interface LogQueryParams {
  platform_code?: string
  status?: CollectStatus
  page?: number
  page_size?: number
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// 预警等级
export type AlertLevel = 'info' | 'warning' | 'critical' | 'emergency'

// 监控指标
export type MonitorMetric = 'instant' | 'daily_total' | 'monthly_total'

// 阈值类型
export type ThresholdType = 'greater_than' | 'less_than' | 'equal'

// 通知频率
export type NotifyFrequency = 'first' | 'every' | 'daily_summary'

// 生效时间类型
export type EffectiveTimeType = 'all_day' | 'custom'

// 预警规则查询参数
export interface RuleQueryParams {
  energy_type?: EnergyType
  alert_level?: AlertLevel
  is_enabled?: boolean
  page?: number
  page_size?: number
}

// 预警记录状态
export type AlertRecordStatus = 'pending' | 'processed' | 'ignored'

// 预警记录查询参数
export interface RecordQueryParams {
  energy_type?: EnergyType
  alert_level?: AlertLevel
  status?: AlertRecordStatus
  start_time?: string
  end_time?: string
  page?: number
  page_size?: number
}

// 分布数据点（图表输入，由总览 distribution 映射而来）
export interface DistributionDataPoint {
  name: string
  value: number
}

// ── 车间管理 ──

// 车间分类
export type WorkshopCategory = 'workshop' | 'position' | 'support' | 'utility'

// 车间查询参数
export interface WorkshopQueryParams {
  category?: WorkshopCategory
  is_active?: boolean
  page?: number
  page_size?: number
}

// 月度记录查询参数
export interface MonthlyRecordQueryParams {
  workshop_id?: string
  energy_type?: EnergyType
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}
