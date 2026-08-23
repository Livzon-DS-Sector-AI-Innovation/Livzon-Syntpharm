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
  submitEquipmentCheckApi,
  deleteInspectionPhotoApi,
  submitRouteCheckApi,
  analyzeInspectionPhotoApi,
  createScheduleApi, updateScheduleApi, deleteScheduleApi,
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
  return result as any
}

export async function updateInspectionRoute(id: string, data: UpdateInspectionRouteInput) {
  const result = await updateRouteApi(id, data, await authHeaders())
  revalidate()
  return result as any
}

export async function deleteInspectionRoute(id: string) {
  const result = await deleteRouteApi(id, await authHeaders())
  revalidate()
  return result as any
}

export async function setRouteLocations(routeId: string, locations: RouteLocationItem[]) {
  const result = await setRouteLocationsApi(routeId, locations, await authHeaders())
  revalidate()
  return result as any
}

export async function createInspectionTask(data: CreateInspectionTaskInput) {
  const result = await createTaskApi(data, await authHeaders())
  revalidate()
  return result as any
}

export async function startInspectionTask(id: string) {
  const result = await startTaskApi(id, await authHeaders())
  revalidate()
  return result as any
}

export async function completeInspectionTask(id: string) {
  const result = await completeTaskApi(id, await authHeaders())
  revalidate()
  return result as any
}

export async function closeInspectionTask(id: string, closureRemark?: string) {
  const result = await closeTaskApi(id, closureRemark, await authHeaders())
  revalidate()
  return result as any
}

export async function submitEquipmentCheck(taskId: string, equipmentId: string, data: EquipmentCheckResult) {
  const result = await submitEquipmentCheckApi(taskId, equipmentId, data, await authHeaders())
  revalidate()
  return result as any
}

export async function uploadInspectionPhoto(taskId: string, equipmentId: string, formData: FormData) {
  const result = await uploadInspectionPhotoApi(taskId, equipmentId, formData, await authHeaders())
  revalidate()
  return result as any
}

export async function deleteInspectionPhoto(taskId: string, photoId: string) {
  const result = await deleteInspectionPhotoApi(taskId, photoId, await authHeaders())
  revalidate()
  return result as any
}

export async function submitRouteCheck(taskId: string, data: RouteCheckSubmitInput) {
  const result = await submitRouteCheckApi(taskId, data, await authHeaders())
  revalidate()
  return result as any
}

export async function uploadTaskPhoto(taskId: string, formData: FormData) {
  const result = await uploadTaskPhotoApi(taskId, formData, await authHeaders())
  revalidate()
  return result as any
}

export async function analyzeInspectionPhoto(
  taskId: string,
  equipmentId: string,
  imageBase64: string,
  imageMimeType: string,
): Promise<InspectionAIItemResult[]> {
  const result = await analyzeInspectionPhotoApi(taskId, equipmentId, imageBase64, imageMimeType, await authHeaders())
  return result ?? []
}

export async function createSchedule(routeId: string, data: CreateInspectionScheduleInput) {
  const result = await createScheduleApi(routeId, data, await authHeaders())
  revalidate()
  return result as any
}

export async function updateSchedule(
  routeId: string, scheduleId: string, data: UpdateInspectionScheduleInput,
) {
  const result = await updateScheduleApi(routeId, scheduleId, data, await authHeaders())
  revalidate()
  return result as any
}

export async function deleteSchedule(routeId: string, scheduleId: string) {
  const result = await deleteScheduleApi(routeId, scheduleId, await authHeaders())
  revalidate()
  return result as any
}
