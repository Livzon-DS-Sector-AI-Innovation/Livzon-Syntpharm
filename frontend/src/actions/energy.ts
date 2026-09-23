'use server'

import { revalidatePath } from 'next/cache'
import {
  fetchEnergyDevices,
  fetchEnergyDeviceById,
  createEnergyDevice as apiCreateDevice,
  updateEnergyDevice as apiUpdateDevice,
  deleteEnergyDevice as apiDeleteDevice,
  fetchEnergyData,
  fetchEnergyOverview,
  triggerCollect as apiTriggerCollect,
  fetchCollectLogs,
  fetchAlertRules,
  fetchAlertRuleById,
  createAlertRule as apiCreateAlertRule,
  updateAlertRule as apiUpdateAlertRule,
  deleteAlertRule as apiDeleteAlertRule,
  fetchAlertRecords,
  processAlertRecord as apiProcessAlertRecord,
  fetchWorkshops,
  fetchWorkshopById,
  createWorkshop as apiCreateWorkshop,
  updateWorkshop as apiUpdateWorkshop,
  deleteWorkshop as apiDeleteWorkshop,
  fetchMonthlyRecords,
  fetchMonthlyRecordById,
  createMonthlyRecord as apiCreateMonthlyRecord,
  deleteMonthlyRecord as apiDeleteMonthlyRecord,
  importFromFeishu as apiImportFromFeishu,
  crossImportFromBitable as apiCrossImportFromBitable,
  syncBitableDailyData as apiSyncBitableDailyData,
  checkAlerts as apiCheckAlerts,
  fetchAlertDates as apiFetchAlertDates,
} from '@/lib/api/server/energy'
import type { components } from '@/types/generated/schema'
type CreateDeviceInput = components['schemas']['EnergyDeviceConfigCreate']
type UpdateDeviceInput = components['schemas']['EnergyDeviceConfigUpdate']
type CreateRuleInput = components['schemas']['EnergyAlertRuleCreate']
type UpdateRuleInput = components['schemas']['EnergyAlertRuleUpdate']
type CreateWorkshopInput = components['schemas']['EnergyWorkshopCreate']
type UpdateWorkshopInput = components['schemas']['EnergyWorkshopUpdate']
type CreateMonthlyRecordInput = components['schemas']['EnergyMonthlyRecordCreate']
type FeishuImportRequest = components['schemas']['FeishuEnergyImportRequest']
import type {
  DeviceQueryParams,
  RuleQueryParams,
  ProcessRecordInput,
  WorkshopQueryParams,
  EnergyOverviewData,
} from '@/types/energy'

// 数据源配置 Server Actions

export async function getEnergyDevices(params?: DeviceQueryParams) {
  return fetchEnergyDevices(params as Record<string, unknown>)
}

export async function getEnergyDeviceById(id: string) {
  return fetchEnergyDeviceById(id)
}

export async function createEnergyDevice(data: CreateDeviceInput) {
  const result = await apiCreateDevice(data)
  revalidatePath('/energy/devices')
  return result
}

export async function updateEnergyDevice(id: string, data: UpdateDeviceInput) {
  const result = await apiUpdateDevice(id, data)
  revalidatePath('/energy/devices')
  return result
}

export async function deleteEnergyDevice(id: string) {
  await apiDeleteDevice(id)
  revalidatePath('/energy/devices')
}

// 能耗数据 Server Actions

export async function getEnergyData(params: DeviceQueryParams) {
  return fetchEnergyData(params as Record<string, unknown>)
}

export async function getEnergyOverview(params?: Record<string, unknown>): Promise<EnergyOverviewData> {
  // TODO: add type to OpenAPI schema - energy overview query params not yet typed
  return fetchEnergyOverview(params || {})
}

export async function triggerCollect(platformCode?: string) {
  const result = await apiTriggerCollect(platformCode)
  revalidatePath('/energy/collect-logs')
  return result
}

// 采集日志 Server Actions

export async function getCollectLogs(params?: { page?: number; page_size?: number }) {
  return fetchCollectLogs(params)
}

// 预警规则 Server Actions

export async function getAlertRules(params?: RuleQueryParams) {
  return fetchAlertRules(params as Record<string, unknown>)
}

export async function getAlertRuleById(id: string) {
  return fetchAlertRuleById(id)
}

export async function createAlertRule(data: CreateRuleInput) {
  const result = await apiCreateAlertRule(data)
  revalidatePath('/energy/alert-rules')
  return result
}

export async function updateAlertRule(id: string, data: UpdateRuleInput) {
  const result = await apiUpdateAlertRule(id, data)
  revalidatePath('/energy/alert-rules')
  return result
}

export async function deleteAlertRule(id: string) {
  await apiDeleteAlertRule(id)
  revalidatePath('/energy/alert-rules')
}

// 预警记录 Server Actions

export async function getAlertRecords(params?: RuleQueryParams) {
  return fetchAlertRecords(params as Record<string, unknown>)
}

export async function processAlertRecord(id: string, data: ProcessRecordInput) {
  const result = await apiProcessAlertRecord(id, data)
  revalidatePath('/energy/alert-records')
  return result
}

// 车间管理 Server Actions

export async function getWorkshops(params?: WorkshopQueryParams) {
  return fetchWorkshops(params !== null && params !== void 0 ? params as Record<string, unknown> : undefined)
}

export async function getWorkshopById(id: string) {
  return fetchWorkshopById(id)
}

export async function createWorkshopAction(data: CreateWorkshopInput) {
  const result = await apiCreateWorkshop(data)
  revalidatePath('/energy/workshops')
  return result
}

export async function updateWorkshopAction(id: string, data: UpdateWorkshopInput) {
  const result = await apiUpdateWorkshop(id, data)
  revalidatePath('/energy/workshops')
  return result
}

export async function deleteWorkshopAction(id: string) {
  await apiDeleteWorkshop(id)
  revalidatePath('/energy/workshops')
}

// 月度记录 Server Actions

export async function getMonthlyRecords(params?: {
  workshop_id?: string
  energy_type?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}) {
  return fetchMonthlyRecords(params as Record<string, unknown> | undefined)
}

export async function getMonthlyRecordById(id: string) {
  return fetchMonthlyRecordById(id)
}

export async function createMonthlyRecordAction(data: CreateMonthlyRecordInput) {
  const result = await apiCreateMonthlyRecord(data)
  revalidatePath('/energy/monthly')
  return result
}

export async function deleteMonthlyRecordAction(id: string) {
  await apiDeleteMonthlyRecord(id)
  revalidatePath('/energy/monthly')
}

// ── 飞书导入 Server Action ──

export async function importFromFeishuAction(data: FeishuImportRequest) {
  const result = await apiImportFromFeishu(data)
  if (!data.dry_run) {
    revalidatePath('/energy/monthly')
  }
  return result
}

// ── 飞书多维表格交叉表导入 Server Action ──

export async function crossImportFromBitableAction(data: components['schemas']['BitableCrossImportRequest']) {
  const result = await apiCrossImportFromBitable(data as Record<string, unknown>)
  revalidatePath('/energy/monthly')
  return result
}

// ── 数据导入和预警检查 ──

export async function syncBitableDailyDataAction() {
  const result = await apiSyncBitableDailyData()
  revalidatePath('/energy/alerts')
  return result
}

export async function checkAlertsAction(checkDate: string) {
  const result = await apiCheckAlerts(checkDate)
  revalidatePath('/energy/alerts')
  return result
}

export async function fetchAlertDatesAction() {
  return apiFetchAlertDates()
}



