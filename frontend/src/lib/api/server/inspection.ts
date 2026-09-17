import { apiFetch, getApiBaseUrl } from './base'
import type { components } from '@/types/generated/schema'

const BASE = `${getApiBaseUrl()}/api/v1/equipment/inspection`

export async function createRouteApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function updateRouteApi(id: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${id}`, { method: 'PUT', body: JSON.stringify(data), headers })
}

export async function deleteRouteApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${id}`, { method: 'DELETE', headers })
}

export async function setRouteLocationsApi(routeId: string, locations: any[], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${routeId}/locations`, {
    method: 'POST',
    body: JSON.stringify({ locations }),
    headers,
  })
}

export async function createTaskApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function startTaskApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${id}/start`, { method: 'PUT', headers })
}

export async function completeTaskApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${id}/complete`, { method: 'PUT', headers })
}

export async function closeTaskApi(id: string, closureRemark?: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${id}/close`, {
    method: 'PUT',
    body: JSON.stringify({ closure_remark: closureRemark }),
    headers,
  })
}

export async function submitEquipmentCheckApi(taskId: string, equipmentId: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${taskId}/equipments/${equipmentId}/check`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteInspectionPhotoApi(taskId: string, photoId: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${taskId}/photos/${photoId}`, { method: 'DELETE', headers })
}

export async function submitRouteCheckApi(taskId: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${taskId}/route-check`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function analyzeInspectionPhotoApi(taskId: string, equipmentId: string, imageBase64: string, imageMimeType: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${taskId}/equipments/${equipmentId}/ai-analyze`, {
    method: 'POST',
    body: JSON.stringify({ image_base64: imageBase64, image_mime_type: imageMimeType }),
    headers,
  })
}

export async function createScheduleApi(routeId: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${routeId}/schedules`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateScheduleApi(routeId: string, scheduleId: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${routeId}/schedules/${scheduleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteScheduleApi(routeId: string, scheduleId: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${routeId}/schedules/${scheduleId}`, { method: 'DELETE', headers })
}


// Typed versions
export async function createRouteApiTyped(data: components['schemas']['InspectionRouteCreate'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function updateRouteApiTyped(id: string, data: components['schemas']['InspectionRouteUpdate'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${id}`, { method: 'PUT', body: JSON.stringify(data), headers })
}

export async function createTaskApiTyped(data: components['schemas']['InspectionTaskCreate'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function submitEquipmentCheckApiTyped(taskId: string, equipmentId: string, data: components['schemas']['EquipmentCheckResult'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${taskId}/equipments/${equipmentId}/check`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function submitRouteCheckApiTyped(taskId: string, data: components['schemas']['RouteCheckSubmit'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/tasks/${taskId}/route-check`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function createScheduleApiTyped(routeId: string, data: components['schemas']['InspectionScheduleCreate'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${routeId}/schedules`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function updateScheduleApiTyped(routeId: string, scheduleId: string, data: components['schemas']['InspectionScheduleUpdate'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/routes/${routeId}/schedules/${scheduleId}`, { method: 'PUT', body: JSON.stringify(data), headers })
}
