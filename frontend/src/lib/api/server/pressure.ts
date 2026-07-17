import { apiFetch } from '@/lib/api/server/base'
import type {
  ApiResponse,
  AuditStats,
  BatchManualEntryRequest,
  BatchManualEntryResponse,
  CreateOcrRecordRequest,
  DashboardStats,
  DeleteMergedRowRequest,
  MergedPressureRow,
  NotificationListResponse,
  OcrSubmitResponse,
  OcrTask,
  PointMapping,
  PressureRecord,
  UpdateMergedRowRequest,
} from '@/types/pressure'

export async function getPressureDashboard(headers: Record<string, string>) {
  return apiFetch<ApiResponse<DashboardStats>>('/api/v1/production/pressure/dashboard', { headers })
}

export async function getPointMappings(
  headers: Record<string, string>,
  params: {
    area?: string
    keyword?: string
    page?: number
    page_size?: number
  } = {}
) {
  const searchParams = new URLSearchParams()
  if (params.area) searchParams.set('area', params.area)
  if (params.keyword) searchParams.set('keyword', params.keyword)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiFetch<ApiResponse<PointMapping[]>>(
    `/api/v1/production/pressure/point-mappings${qs ? `?${qs}` : ''}`,
    { headers }
  )
}

export async function getPointMapping(headers: Record<string, string>, id: string) {
  return apiFetch<ApiResponse<PointMapping>>(
    `/api/v1/production/pressure/point-mappings/${id}`,
    { headers }
  )
}

export async function createPointMapping(
  headers: Record<string, string>,
  data: { point_id: string; area: string; standard_pressure: number }
) {
  return apiFetch<ApiResponse<PointMapping>>(
    '/api/v1/production/pressure/point-mappings',
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function updatePointMapping(
  headers: Record<string, string>,
  id: string,
  data: { area?: string; standard_pressure?: number }
) {
  return apiFetch<ApiResponse<PointMapping>>(
    `/api/v1/production/pressure/point-mappings/${id}`,
    { method: 'PUT', headers, body: JSON.stringify(data) }
  )
}

export async function deletePointMapping(headers: Record<string, string>, id: string) {
  return apiFetch<ApiResponse<void>>(
    `/api/v1/production/pressure/point-mappings/${id}`,
    { method: 'DELETE', headers }
  )
}

export async function checkPointIdUnique(headers: Record<string, string>, pointId: string) {
  return apiFetch<ApiResponse<{ exists: boolean }>>(
    `/api/v1/production/pressure/point-mappings/check-unique?point_id=${encodeURIComponent(pointId)}`,
    { headers }
  )
}

export async function getPressureRecords(
  headers: Record<string, string>,
  params: {
    area?: string
    point_id?: string
    input_type?: string
    status?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  } = {}
) {
  const searchParams = new URLSearchParams()
  if (params.area) searchParams.set('area', params.area)
  if (params.point_id) searchParams.set('point_id', params.point_id)
  if (params.input_type) searchParams.set('input_type', params.input_type)
  if (params.status) searchParams.set('status', params.status)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiFetch<ApiResponse<PressureRecord[]>>(
    `/api/v1/production/pressure/records${qs ? `?${qs}` : ''}`,
    { headers }
  )
}

export async function getMergedPressureRecords(
  headers: Record<string, string>,
  params: {
    area?: string
    point_id?: string
    input_type?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  } = {}
) {
  const searchParams = new URLSearchParams()
  if (params.area) searchParams.set('area', params.area)
  if (params.point_id) searchParams.set('point_id', params.point_id)
  if (params.input_type) searchParams.set('input_type', params.input_type)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiFetch<ApiResponse<MergedPressureRow[]>>(
    `/api/v1/production/pressure/records/merged${qs ? `?${qs}` : ''}`,
    { headers }
  )
}

export async function createManualRecord(
  headers: Record<string, string>,
  data: { record_time: string; point_id: string; pressure_value: number; time_slot?: string; remark?: string }
) {
  return apiFetch<ApiResponse<{ id: string; success: boolean }>>(
    '/api/v1/production/pressure/records/manual',
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function createBatchManualRecord(
  headers: Record<string, string>,
  data: BatchManualEntryRequest
) {
  return apiFetch<ApiResponse<BatchManualEntryResponse>>(
    '/api/v1/production/pressure/records/manual/batch',
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function submitOcrRecords(
  headers: Record<string, string>,
  data: CreateOcrRecordRequest
) {
  return apiFetch<ApiResponse<OcrSubmitResponse>>(
    '/api/v1/production/pressure/records/ocr',
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function auditPressureRecord(
  headers: Record<string, string>,
  id: string,
  data: { status: string; reject_reason?: string }
) {
  return apiFetch<ApiResponse<{ success: boolean }>>(
    `/api/v1/production/pressure/records/${id}/audit`,
    { method: 'PATCH', headers, body: JSON.stringify(data) }
  )
}

export async function batchAuditPressureRecords(
  headers: Record<string, string>,
  data: { ids: string[]; status: string; reject_reason?: string }
) {
  return apiFetch<ApiResponse<{ success_count: number; fail_count: number }>>(
    '/api/v1/production/pressure/records/batch-audit',
    { method: 'PATCH', headers, body: JSON.stringify(data) }
  )
}

export async function deletePressureRecord(headers: Record<string, string>, id: string) {
  return apiFetch<ApiResponse<void>>(
    `/api/v1/production/pressure/records/${id}`,
    { method: 'DELETE', headers }
  )
}

export async function batchDeletePressureRecords(headers: Record<string, string>, ids: string[]) {
  return apiFetch<ApiResponse<{ success_count: number }>>(
    '/api/v1/production/pressure/records/batch-delete',
    { method: 'POST', headers, body: JSON.stringify({ ids }) }
  )
}

export async function updateMergedRow(
  headers: Record<string, string>,
  data: UpdateMergedRowRequest
) {
  return apiFetch<ApiResponse<{ success_count: number }>>(
    '/api/v1/production/pressure/records/merged/update',
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function deleteMergedRow(
  headers: Record<string, string>,
  data: DeleteMergedRowRequest
) {
  return apiFetch<ApiResponse<{ success_count: number }>>(
    '/api/v1/production/pressure/records/merged/delete',
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function batchDeleteMergedRows(
  headers: Record<string, string>,
  rows: DeleteMergedRowRequest[]
) {
  return apiFetch<ApiResponse<{ success_count: number }>>(
    '/api/v1/production/pressure/records/merged/batch-delete',
    { method: 'POST', headers, body: JSON.stringify({ rows }) }
  )
}

export async function exportByArea(
  headers: Record<string, string>,
  params: {
    area?: string
    start_date?: string
    end_date?: string
    point_id?: string
  } = {}
) {
  const searchParams = new URLSearchParams()
  if (params.area) searchParams.set('area', params.area)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  if (params.point_id) searchParams.set('point_id', params.point_id)
  const qs = searchParams.toString()
  return apiFetch<ApiResponse<any[]>>(
    `/api/v1/production/pressure/records/export/by-area${qs ? `?${qs}` : ''}`,
    { headers }
  )
}

export async function getAuditStats(headers: Record<string, string>) {
  return apiFetch<ApiResponse<AuditStats>>('/api/v1/production/pressure/audit/stats', { headers })
}

export async function getOcrTasks(
  headers: Record<string, string>,
  params: {
    status?: string
    page?: number
    page_size?: number
  } = {}
) {
  const searchParams = new URLSearchParams()
  if (params.status) searchParams.set('status', params.status)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiFetch<ApiResponse<OcrTask[]>>(
    `/api/v1/production/pressure/ocr-tasks${qs ? `?${qs}` : ''}`,
    { headers }
  )
}

export async function getOcrTask(headers: Record<string, string>, id: string) {
  return apiFetch<ApiResponse<OcrTask>>(`/api/v1/production/pressure/ocr-tasks/${id}`, { headers })
}

export async function createOcrTask(
  headers: Record<string, string>,
  data: { image_url: string }
) {
  return apiFetch<ApiResponse<OcrTask>>(
    '/api/v1/production/pressure/ocr-tasks',
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function submitOcrTaskResult(
  headers: Record<string, string>,
  taskId: string,
  data: { records: any[] }
) {
  return apiFetch<ApiResponse<OcrSubmitResponse>>(
    `/api/v1/production/pressure/ocr-tasks/${taskId}/submit`,
    { method: 'POST', headers, body: JSON.stringify(data) }
  )
}

export async function getNotifications(
  headers: Record<string, string>,
  params: {
    user_id?: string
    page?: number
    page_size?: number
  } = {}
) {
  const searchParams = new URLSearchParams()
  if (params.user_id) searchParams.set('user_id', params.user_id)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const qs = searchParams.toString()
  return apiFetch<ApiResponse<NotificationListResponse>>(
    `/api/v1/production/pressure/notifications${qs ? `?${qs}` : ''}`,
    { headers }
  )
}

export async function markNotificationRead(headers: Record<string, string>, id: string) {
  return apiFetch<ApiResponse<void>>(
    `/api/v1/production/pressure/notifications/${id}/read`,
    { method: 'PATCH', headers }
  )
}

export async function markAllNotificationsRead(headers: Record<string, string>, userId?: string) {
  const qs = userId ? `?user_id=${userId}` : ''
  return apiFetch<ApiResponse<void>>(
    `/api/v1/production/pressure/notifications/read-all${qs}`,
    { method: 'PATCH', headers }
  )
}