'use server'

import { revalidatePath } from 'next/cache'
import { getServerToken } from '@/lib/auth'
import type {
  CreateInspectionRouteInput, UpdateInspectionRouteInput,
  CreateInspectionTaskInput, EquipmentCheckResult,
  InspectionAIItemResult,
  RouteCheckSubmitInput, RouteLocationItem,
  CreateInspectionScheduleInput, UpdateInspectionScheduleInput,
} from '@/types/inspection'
import {
  createRouteApi, updateRouteApi, deleteRouteApi,
  setRouteLocationsApi,
  createTaskApi, startTaskApi, completeTaskApi, closeTaskApi,
  submitEquipmentCheckApiTyped,
  deleteInspectionPhotoApi,
  submitRouteCheckApiTyped,
  analyzeInspectionPhotoApi,
  getInspectionAIJobApi,
  createScheduleApiTyped, updateScheduleApiTyped, deleteScheduleApi,
} from '@/lib/api/server/inspection'
import {
  uploadInspectionPhotoApi,
  uploadTaskPhotoApi,
} from '@/lib/api/server/equipment'

async function authHeaders(): Promise<Record<string, string>> {
  return { Authorization: `Bearer ${await getServerToken()}` }
}

function revalidate() {
  revalidatePath('/equipment/inspection')
}

export async function createInspectionRoute(data: CreateInspectionRouteInput) {
  const result = await createRouteApi(data, await authHeaders())
  revalidate()
  return result
}

export async function updateInspectionRoute(id: string, data: UpdateInspectionRouteInput) {
  const result = await updateRouteApi(id, data, await authHeaders())
  revalidate()
  return result
}

export async function deleteInspectionRoute(id: string) {
  const result = await deleteRouteApi(id, await authHeaders())
  revalidate()
  return result
}

export async function setRouteLocations(routeId: string, locations: RouteLocationItem[]) {
  const result = await setRouteLocationsApi(routeId, locations, await authHeaders())
  revalidate()
  return result
}

export async function createInspectionTask(data: CreateInspectionTaskInput) {
  const result = await createTaskApi(data, await authHeaders())
  revalidate()
  return result
}

export async function startInspectionTask(id: string) {
  const result = await startTaskApi(id, await authHeaders())
  revalidate()
  return result
}

export async function completeInspectionTask(id: string) {
  const result = await completeTaskApi(id, await authHeaders())
  revalidate()
  return result
}

export async function closeInspectionTask(id: string, closureRemark?: string) {
  const result = await closeTaskApi(id, closureRemark, await authHeaders())
  revalidate()
  return result
}

export async function submitEquipmentCheck(taskId: string, equipmentId: string, data: EquipmentCheckResult) {
  const result = await submitEquipmentCheckApiTyped(taskId, equipmentId, data, await authHeaders())
  revalidate()
  return result
}

export async function uploadInspectionPhoto(taskId: string, equipmentId: string, formData: FormData) {
  const result = await uploadInspectionPhotoApi(taskId, equipmentId, formData, await authHeaders())
  revalidate()
  return result
}

export async function deleteInspectionPhoto(taskId: string, photoId: string) {
  const result = await deleteInspectionPhotoApi(taskId, photoId, await authHeaders())
  revalidate()
  return result
}

export async function submitRouteCheck(taskId: string, data: RouteCheckSubmitInput) {
  const result = await submitRouteCheckApiTyped(taskId, data, await authHeaders())
  revalidate()
  return result
}

export async function uploadTaskPhoto(taskId: string, formData: FormData) {
  const result = await uploadTaskPhotoApi(taskId, formData, await authHeaders())
  revalidate()
  return result
}

const AI_ANALYZE_POLL_INTERVAL_MS = 1500
const AI_ANALYZE_TIMEOUT_MS = 180_000

interface AIJobState {
  status?: 'running' | 'done' | 'failed'
  result?: { items?: InspectionAIItemResult[] } | null
  error?: string | null
}

/**
 * 提交巡检照片 AI 分析任务并等待结果。
 *
 * 后端已改为「提交任务 + 轮询状态」（视觉模型调用 >5s，不再占用 HTTP 请求），
 * 轮询放在这里完成，调用方仍然拿到最终检查项结果，无需改造组件。
 */
export async function analyzeInspectionPhoto(
  taskId: string,
  equipmentId: string,
  imageBase64: string,
  imageMimeType: string,
): Promise<InspectionAIItemResult[]> {
  const headers = await authHeaders()
  const accepted = await analyzeInspectionPhotoApi(taskId, equipmentId, imageBase64, imageMimeType, headers)
  const jobId = (accepted as { data?: { job_id?: string } } | null)?.data?.job_id
  if (!jobId) throw new Error('AI 分析任务提交失败')

  const deadline = Date.now() + AI_ANALYZE_TIMEOUT_MS
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, AI_ANALYZE_POLL_INTERVAL_MS))
    const state = await getInspectionAIJobApi(taskId, equipmentId, jobId, headers)
    const job = (state as { data?: AIJobState } | null)?.data
    if (job?.status === 'done') return job.result?.items ?? []
    if (job?.status === 'failed') throw new Error(job.error || 'AI 分析失败')
  }
  throw new Error('AI 分析超时，请稍后重试')
}

export async function createSchedule(routeId: string, data: CreateInspectionScheduleInput) {
  const result = await createScheduleApiTyped(routeId, data, await authHeaders())
  revalidate()
  return result
}

export async function updateSchedule(
  routeId: string, scheduleId: string, data: UpdateInspectionScheduleInput,
) {
  const result = await updateScheduleApiTyped(routeId, scheduleId, data, await authHeaders())
  revalidate()
  return result
}

export async function deleteSchedule(routeId: string, scheduleId: string) {
  const result = await deleteScheduleApi(routeId, scheduleId, await authHeaders())
  revalidate()
  return result
}
