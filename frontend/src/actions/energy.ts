'use server'
import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'

import { revalidatePath } from 'next/cache'
import {
  fetchEnergyDevices,
  fetchEnergyDeviceById,
  fetchEnergyData,
  fetchEnergyOverview,
  fetchCollectLogs,
  fetchAlertRules,
  fetchAlertRuleById,
  fetchAlertRecords,
  createEnergyDevice as createEnergyDeviceServer,
  updateEnergyDevice as updateEnergyDeviceServer,
  deleteEnergyDevice as deleteEnergyDeviceServer,
  triggerCollect as triggerCollectServer,
  createAlertRule as createAlertRuleServer,
  updateAlertRule as updateAlertRuleServer,
  deleteAlertRule as deleteAlertRuleServer,
  processAlertRecord as processAlertRecordServer,
} from '@/lib/api/server/energy'
import type {
  CreateDeviceInput,
  UpdateDeviceInput,
  DeviceQueryParams,
  DataQueryParams,
  StatisticsParams,
  LogQueryParams,
  CreateRuleInput,
  UpdateRuleInput,
  ProcessRecordInput,
  RuleQueryParams,
  RecordQueryParams,
} from '@/types/energy'

// 数据源配置 Server Actions
export async function getEnergyDevices(params: DeviceQueryParams = {}) {
  return fetchEnergyDevices(params)
}

export async function getEnergyDeviceById(id: string) {
  return fetchEnergyDeviceById(id)
}

export async function createEnergyDevice(data: CreateDeviceInput) {
  const result = await createEnergyDeviceServer(data)
  revalidatePath('/energy/devices')
  return result
}

export async function updateEnergyDevice(id: string, data: UpdateDeviceInput) {
  const result = await updateEnergyDeviceServer(id, data)
  revalidatePath('/energy/devices')
  return result
}

export async function deleteEnergyDevice(id: string) {
  await deleteEnergyDeviceServer(id)
  revalidatePath('/energy/devices')
}

// 能耗数据 Server Actions
export async function getEnergyData(params: DataQueryParams = {}) {
  return fetchEnergyData(params)
}

export async function getEnergyOverview(params: StatisticsParams = {}) {
  return fetchEnergyOverview(params)
}

// 数据采集 Server Actions
export async function triggerCollect(platformCode?: string) {
  const result = await triggerCollectServer(platformCode)
  revalidatePath('/energy/collect-logs')
  return result
}

export async function getCollectLogs(params: LogQueryParams = {}) {
  return fetchCollectLogs(params)
}

// 预警规则 Server Actions
export async function getAlertRules(params: RuleQueryParams = {}) {
  return fetchAlertRules(params)
}

export async function getAlertRuleById(id: string) {
  return fetchAlertRuleById(id)
}

export async function createAlertRule(data: CreateRuleInput) {
  const result = await createAlertRuleServer(data)
  revalidatePath('/energy/alerts')
  return result
}

export async function updateAlertRule(id: string, data: UpdateRuleInput) {
  const result = await updateAlertRuleServer(id, data)
  revalidatePath('/energy/alerts')
  return result
}

export async function deleteAlertRule(id: string) {
  await deleteAlertRuleServer(id)
  revalidatePath('/energy/alerts')
}

// 预警记录 Server Actions
export async function getAlertRecords(params: RecordQueryParams = {}) {
  return fetchAlertRecords(params)
}

export async function processAlertRecord(id: string, data: ProcessRecordInput) {
  const result = await processAlertRecordServer(id, data)
  revalidatePath('/energy/alerts')
  return result
}

// ─── Workshop Actions ───

export async function getWorkshops(params: Record<string, unknown> = {}) {
  'use server'
  const headers = await getAuthHeaders()
  return fetchWorkshops(params, headers)
}

import { getAuthHeaders } from "@/lib/auth"
import { fetchWorkshops, createWorkshop, updateWorkshop, deleteWorkshop, fetchMonthlyRecords } from "@/lib/api/server/energy"

export async function createWorkshopAction(data: Record<string, unknown>) {
  'use server'
  const headers = await getAuthHeaders()
  return createWorkshop(data, headers)
}

export async function updateWorkshopAction(id: string, data: Record<string, unknown>) {
  'use server'
  const headers = await getAuthHeaders()
  return updateWorkshop(id, data, headers)
}

export async function deleteWorkshopAction(id: string) {
  'use server'
  const headers = await getAuthHeaders()
  return deleteWorkshop(id, headers)
}

// ─── Monthly Records ───


export async function importFromBitable(params: Record<string, unknown>) {
  'use server'
  const headers = await getAuthHeaders()
  return apiFetch(`${API_BASE_URL}/api/v1/energy/import-from-bitable?app_token=${params.app_token || ""}&table_id=${params.table_id || ""}`, {
    method: 'POST',
    headers,
  })
}

export async function importFromFeishu(params: Record<string, unknown>) {
  'use server'
  const headers = await getAuthHeaders()
  return apiFetch(`${API_BASE_URL}/api/v1/energy/import-from-feishu?spreadsheet_token=${params.spreadsheet_token || ''}&sheet_id=${params.sheet_id || ''}`, {
    method: 'POST',
    headers,
  })
}

export async function deleteMonthlyRecordAction(id: string) {
  'use server'
  const headers = await getAuthHeaders()
  return apiFetch(`${API_BASE_URL}/api/v1/energy/monthly/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function getMonthlyRecords(params: Record<string, unknown> = {}) {
  'use server'
  const headers = await getAuthHeaders()
  return fetchMonthlyRecords(params, headers)
}
