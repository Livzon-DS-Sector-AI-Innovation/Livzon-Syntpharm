'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders, getServerToken, getImpersonateToken } from '@/lib/auth'
import {
  CreateInspectionRouteInput, UpdateInspectionRouteInput,
  CreateInspectionTaskInput, EquipmentCheckResult,
  InspectionAIItemResult,
  RouteCheckSubmitInput, RouteLocationItem,
  CreateInspectionScheduleInput, UpdateInspectionScheduleInput,
} from '@/types/inspection'
import {
  createInspectionRouteApi,
  updateInspectionRouteApi,
  deleteInspectionRouteApi,
  setRouteLocationsApi,
  createInspectionTaskApi,
  startInspectionTaskApi,
  completeInspectionTaskApi,
  closeInspectionTaskApi,
  submitEquipmentCheckApi,
  uploadInspectionPhotoApi,
  deleteInspectionPhotoApi,
  submitRouteCheckApi,
  analyzeInspectionPhotoApi,
  createScheduleApi,
  updateScheduleApi,
  deleteScheduleApi,
  uploadTaskPhotoApi,
} from '@/lib/api/server/equipment'

type ActionResult<T> = { success: true; data: T | null } | { success: false; error: string }

async function wrapApiCall<T>(fn: () => Promise<T>): Promise<ActionResult<T>> {
  try {
    const data = await fn()
    return { success: true, data: data as T }
  } catch (err) {
    const msg = (err as Error).message || '请求失败'
    return { success: false, error: msg }
  }
}

async function uploadPhoto(taskId: string, formData: FormData): Promise<ActionResult<unknown>> {
  try {
    const token = await getServerToken()
    const impToken = await getImpersonateToken()
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
    if (impToken) headers['Cookie'] = `impersonate_token=${impToken}`
    const data = await uploadTaskPhotoApi(taskId, formData, headers)
    revalidatePath('/equipment/inspection')
    return { success: true as const, data }
  } catch (err) {
    return { success: false as const, error: (err as Error).message || '上传失败' }
  }
}

// ==================== 巡检线路 ====================
export async function createInspectionRoute(data: CreateInspectionRouteInput) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createInspectionRouteApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function updateInspectionRoute(id: string, data: UpdateInspectionRouteInput) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateInspectionRouteApi(id, data, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function deleteInspectionRoute(id: string) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteInspectionRouteApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function setRouteLocations(routeId: string, locations: RouteLocationItem[]) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => setRouteLocationsApi(routeId, locations, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

// ==================== 巡检任务 ====================
export async function createInspectionTask(data: CreateInspectionTaskInput) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createInspectionTaskApi(data, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function startInspectionTask(id: string) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => startInspectionTaskApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function completeInspectionTask(id: string) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => completeInspectionTaskApi(id, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function closeInspectionTask(id: string, closureRemark?: string) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => closeInspectionTaskApi(id, closureRemark, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

// ==================== 巡检执行 ====================
export async function submitEquipmentCheck(taskId: string, equipmentId: string, data: EquipmentCheckResult) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => submitEquipmentCheckApi(taskId, equipmentId, data, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

// ==================== 照片 ====================
export async function uploadInspectionPhoto(taskId: string, equipmentId: string, formData: FormData) {
  try {
    const token = await getServerToken()
    const impToken = await getImpersonateToken()
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
    if (impToken) headers['Cookie'] = `impersonate_token=${impToken}`
    const data = await uploadInspectionPhotoApi(taskId, equipmentId, formData, headers)
    revalidatePath('/equipment/inspection')
    return { success: true as const, data }
  } catch (err) {
    return { success: false as const, error: (err as Error).message || '上传失败' }
  }
}

export async function deleteInspectionPhoto(taskId: string, photoId: string) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteInspectionPhotoApi(taskId, photoId, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

// ==================== 线路巡检 ====================
export async function submitRouteCheck(taskId: string, data: RouteCheckSubmitInput) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => submitRouteCheckApi(taskId, data, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function uploadTaskPhoto(taskId: string, formData: FormData) {
  return uploadPhoto(taskId, formData)
}

// ==================== AI 分析 ====================
export async function analyzeInspectionPhoto(
  taskId: string,
  equipmentId: string,
  imageBase64: string,
  imageMimeType: string,
): Promise<ActionResult<InspectionAIItemResult[]>> {
  const authHeaders = await getAuthHeaders()
  return wrapApiCall<InspectionAIItemResult[]>(() =>
    analyzeInspectionPhotoApi(taskId, equipmentId, imageBase64, imageMimeType, authHeaders) as Promise<InspectionAIItemResult[]>
  )
}

// ==================== 路线定时任务 ====================
export async function createSchedule(routeId: string, data: CreateInspectionScheduleInput) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => createScheduleApi(routeId, data, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function updateSchedule(
  routeId: string, scheduleId: string, data: UpdateInspectionScheduleInput,
) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => updateScheduleApi(routeId, scheduleId, data, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}

export async function deleteSchedule(routeId: string, scheduleId: string) {
  const authHeaders = await getAuthHeaders()
  const result = await wrapApiCall(() => deleteScheduleApi(routeId, scheduleId, authHeaders))
  if (result.success) revalidatePath('/equipment/inspection')
  return result as any
}