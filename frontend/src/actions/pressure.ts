'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import type {
  BatchManualEntryRequest,
  CreateOcrRecordRequest,
  DeleteMergedRowRequest,
  UpdateMergedRowRequest,
} from '@/types/pressure'
import {
  getPressureDashboard as apiGetPressureDashboard,
  getPointMappings as apiGetPointMappings,
  getPointMapping as apiGetPointMapping,
  createPointMapping as apiCreatePointMapping,
  updatePointMapping as apiUpdatePointMapping,
  deletePointMapping as apiDeletePointMapping,
  checkPointIdUnique as apiCheckPointIdUnique,
  getPressureRecords as apiGetPressureRecords,
  getMergedPressureRecords as apiGetMergedPressureRecords,
  createManualRecord as apiCreateManualRecord,
  createBatchManualRecord as apiCreateBatchManualRecord,
  submitOcrRecords as apiSubmitOcrRecords,
  auditPressureRecord as apiAuditPressureRecord,
  batchAuditPressureRecords as apiBatchAuditPressureRecords,
  deletePressureRecord as apiDeletePressureRecord,
  batchDeletePressureRecords as apiBatchDeletePressureRecords,
  updateMergedRow as apiUpdateMergedRow,
  deleteMergedRow as apiDeleteMergedRow,
  batchDeleteMergedRows as apiBatchDeleteMergedRows,
  exportByArea as apiExportByArea,
  getAuditStats as apiGetAuditStats,
  getOcrTasks as apiGetOcrTasks,
  getOcrTask as apiGetOcrTask,
  createOcrTask as apiCreateOcrTask,
  submitOcrTaskResult as apiSubmitOcrTaskResult,
  getNotifications as apiGetNotifications,
  markNotificationRead as apiMarkNotificationRead,
  markAllNotificationsRead as apiMarkAllNotificationsRead,
} from '@/lib/api/server/pressure'

export async function getPressureDashboard() {
  const headers = await getAuthHeaders()
  return apiGetPressureDashboard(headers)
}

export async function getPointMappings(params: {
  area?: string
  keyword?: string
  page?: number
  page_size?: number
} = {}) {
  const headers = await getAuthHeaders()
  return apiGetPointMappings(headers, params)
}

export async function getPointMapping(id: string) {
  const headers = await getAuthHeaders()
  return apiGetPointMapping(headers, id)
}

export async function createPointMapping(data: {
  point_id: string
  area: string
  standard_pressure: number
}) {
  const headers = await getAuthHeaders()
  const response = await apiCreatePointMapping(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function updatePointMapping(
  id: string,
  data: { area?: string; standard_pressure?: number }
) {
  const headers = await getAuthHeaders()
  const response = await apiUpdatePointMapping(headers, id, data)
  revalidatePath('/production/pressure')
  return response
}

export async function deletePointMapping(id: string) {
  const headers = await getAuthHeaders()
  const response = await apiDeletePointMapping(headers, id)
  revalidatePath('/production/pressure')
  return response
}

export async function checkPointIdUnique(pointId: string) {
  const headers = await getAuthHeaders()
  return apiCheckPointIdUnique(headers, pointId)
}

export async function getPressureRecords(params: {
  area?: string
  point_id?: string
  input_type?: string
  status?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
} = {}) {
  const headers = await getAuthHeaders()
  return apiGetPressureRecords(headers, params)
}

export async function getMergedPressureRecords(params: {
  area?: string
  point_id?: string
  input_type?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
} = {}) {
  const headers = await getAuthHeaders()
  return apiGetMergedPressureRecords(headers, params)
}

export async function createManualRecord(data: {
  record_time: string
  point_id: string
  pressure_value: number
  time_slot?: string
  remark?: string
}) {
  const headers = await getAuthHeaders()
  const response = await apiCreateManualRecord(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function createBatchManualRecord(data: BatchManualEntryRequest) {
  const headers = await getAuthHeaders()
  const response = await apiCreateBatchManualRecord(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function submitOcrRecords(data: CreateOcrRecordRequest) {
  const headers = await getAuthHeaders()
  const response = await apiSubmitOcrRecords(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function auditPressureRecord(
  id: string,
  data: { status: string; reject_reason?: string }
) {
  const headers = await getAuthHeaders()
  const response = await apiAuditPressureRecord(headers, id, data)
  revalidatePath('/production/pressure')
  return response
}

export async function batchAuditPressureRecords(data: {
  ids: string[]
  status: string
  reject_reason?: string
}) {
  const headers = await getAuthHeaders()
  const response = await apiBatchAuditPressureRecords(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function deletePressureRecord(id: string) {
  const headers = await getAuthHeaders()
  const response = await apiDeletePressureRecord(headers, id)
  revalidatePath('/production/pressure')
  return response
}

export async function batchDeletePressureRecords(ids: string[]) {
  const headers = await getAuthHeaders()
  const response = await apiBatchDeletePressureRecords(headers, ids)
  revalidatePath('/production/pressure')
  return response
}

export async function updateMergedRow(data: UpdateMergedRowRequest) {
  const headers = await getAuthHeaders()
  const response = await apiUpdateMergedRow(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function deleteMergedRow(data: DeleteMergedRowRequest) {
  const headers = await getAuthHeaders()
  const response = await apiDeleteMergedRow(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function batchDeleteMergedRows(rows: DeleteMergedRowRequest[]) {
  const headers = await getAuthHeaders()
  const response = await apiBatchDeleteMergedRows(headers, rows)
  revalidatePath('/production/pressure')
  return response
}

export async function exportByArea(params: {
  area?: string
  start_date?: string
  end_date?: string
  point_id?: string
} = {}) {
  const headers = await getAuthHeaders()
  return apiExportByArea(headers, params)
}

export async function getAuditStats() {
  const headers = await getAuthHeaders()
  return apiGetAuditStats(headers)
}

export async function getOcrTasks(params: {
  status?: string
  page?: number
  page_size?: number
} = {}) {
  const headers = await getAuthHeaders()
  return apiGetOcrTasks(headers, params)
}

export async function getOcrTask(id: string) {
  const headers = await getAuthHeaders()
  return apiGetOcrTask(headers, id)
}

export async function createOcrTask(data: { image_url: string }) {
  const headers = await getAuthHeaders()
  const response = await apiCreateOcrTask(headers, data)
  revalidatePath('/production/pressure')
  return response
}

export async function submitOcrTaskResult(
  taskId: string,
  data: { records: Record<string, unknown>[] }
) {
  const headers = await getAuthHeaders()
  const response = await apiSubmitOcrTaskResult(headers, taskId, data)
  revalidatePath('/production/pressure')
  return response
}

export async function getNotifications(params: {
  user_id?: string
  page?: number
  page_size?: number
} = {}) {
  const headers = await getAuthHeaders()
  return apiGetNotifications(headers, params)
}

export async function markNotificationRead(id: string) {
  const headers = await getAuthHeaders()
  const response = await apiMarkNotificationRead(headers, id)
  revalidatePath('/production/pressure')
  return response
}

export async function markAllNotificationsRead(userId?: string) {
  const headers = await getAuthHeaders()
  const response = await apiMarkAllNotificationsRead(headers, userId)
  revalidatePath('/production/pressure')
  return response
}