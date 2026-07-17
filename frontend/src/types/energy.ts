// Energy module types
// API input types are aliased from generated schema for single-source-of-truth.
// UI-specific types (query params, response wrappers, display types) remain hand-written.

import type { components } from '@/types/generated/schema'

// ── API Input Types (from generated schema) ──

export type CreateDeviceInput = components['schemas']['EnergyDeviceConfigCreate']
export type UpdateDeviceInput = components['schemas']['EnergyDeviceConfigUpdate']
export type CreateRuleInput = components['schemas']['EnergyAlertRuleCreate']
export type UpdateRuleInput = components['schemas']['EnergyAlertRuleUpdate']
export type ProcessRecordInput = components['schemas']['AlertRecordProcessRequest']

// ── Enum / Literal Types (matching generated schema) ──

export type EnergyType = 'electricity' | 'water' | 'steam' | 'natural_gas'
export type MonitorLevel = 'normal' | 'important' | 'urgent'
export type AlertLevel = 'info' | 'warning' | 'critical' | 'emergency'
export type MonitorMetric = 'instant' | 'daily_total' | 'monthly_total'
export type ThresholdType = 'greater_than' | 'less_than' | 'equal'
export type NotifyFrequency = 'first' | 'every' | 'daily_summary'
export type EffectiveTimeType = 'all_day' | 'custom'
export type CollectStatus = 'success' | 'partial' | 'failed'
export type AlertRecordStatus = 'pending' | 'processed' | 'ignored'

// ── Response / Display Types (not in generated schema) ──

export interface EnergyDeviceConfig {
  id: string
  platform_code: string
  platform_device_code: string
  device_name: string
  energy_type: EnergyType
  api_endpoint: string
  workshop: string
  production_line?: string
  monitor_level: MonitorLevel
  unit: string
  collection_interval: number
  is_enabled: boolean
  remark?: string
  created_at: string
  updated_at: string
}

export interface DeviceQueryParams {
  keyword?: string
  energy_type?: EnergyType
  workshop?: string
  is_enabled?: boolean
  page?: number
  page_size?: number
}

export interface EnergyData {
  id: string
  config_id: string
  device_name: string
  energy_type: EnergyType
  workshop: string
  production_line?: string
  value: number
  unit: string
  collected_at: string
  created_at: string
}

export interface DataQueryParams {
  energy_type?: EnergyType
  workshop?: string
  device_id?: string
  start_time?: string
  end_time?: string
  page?: number
  page_size?: number
}

export interface EnergyStatistics {
  total_electricity: number
  total_water: number
  total_steam: number
  total_natural_gas: number
}

export interface EnergyOverviewData {
  summary: EnergyStatistics
  trend: TrendDataPoint[]
  distribution: DistributionDataPoint[]
}

export interface StatisticsParams {
  start_time?: string
  end_time?: string
  energy_type?: EnergyType
}

export interface CollectLog {
  id: string
  platform_code: string
  collect_time: string
  status: CollectStatus
  device_count: number
  success_count: number
  error_message: string | null
  created_at: string
}

export interface CollectLogDeviceDetail {
  device_name: string
  platform_device_code: string
  energy_type: string
  value: number
  unit: string
  data_timestamp: string
}

export interface CollectLogDetail {
  id: string
  platform_code: string
  collect_time: string
  status: CollectStatus
  device_count: number
  success_count: number
  error_message: string | null
  created_at: string
  devices: CollectLogDeviceDetail[]
  time_range_start: string | null
  time_range_end: string | null
}

export interface LogQueryParams {
  platform_code?: string
  status?: CollectStatus
  page?: number
  page_size?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface AlertRule {
  id: string
  rule_name: string
  rule_description?: string
  energy_type: EnergyType
  monitor_metric: MonitorMetric
  threshold_type: ThresholdType
  threshold_value: number
  unit: string
  alert_level: AlertLevel
  notify_method: string[]
  notify_users: string[]
  notify_frequency: NotifyFrequency
  effective_time: EffectiveTimeType
  custom_time_start?: string
  custom_time_end?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface RuleQueryParams {
  energy_type?: EnergyType
  alert_level?: AlertLevel
  is_enabled?: boolean
  page?: number
  page_size?: number
}

export interface AlertRecord {
  id: string
  rule_id: string
  rule_name: string
  config_id: string
  device_name: string
  energy_type: EnergyType
  alert_level: AlertLevel
  trigger_value: number
  threshold_value: number
  unit: string
  alert_time: string
  status: AlertRecordStatus
  processed_by?: string
  processed_at?: string
  process_note?: string
  created_at: string
}

export interface RecordQueryParams {
  energy_type?: EnergyType
  alert_level?: AlertLevel
  status?: AlertRecordStatus
  start_time?: string
  end_time?: string
  page?: number
  page_size?: number
}

export interface TrendDataPoint {
  time: string
  value: number
  type: string
}

export interface DistributionDataPoint {
  name: string
  value: number
}

export interface DeviceRankItem {
  device_name: string
  value: number
  unit: string
}

// ─── Workshop & Monthly ───

export type WorkshopCategory = 'workshop' | 'position' | 'support' | 'utility'

export interface EnergyWorkshop {
  id: string
  name: string
  code: string
  category: WorkshopCategory
  parent_id: string | null
  created_at: string
  updated_at: string
}

export interface MonthlyRecord {
  id: string
  workshop_id: string
  record_date: string
  date_range_end: string
  electricity: number
  water: number
  steam: number
  natural_gas: number
  unit: string
  created_at: string
  updated_at: string
}
