import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { CreateTableRequest, UpdateTableRequest, RecognizeResult } from '@/types/inspection-table'

async function apiFetchFormData<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url.startsWith('http') ? url : `${getApiBaseUrl()}${url}`, {
    ...options,
    cache: 'no-store',
  })
  if (!response.ok) {
    const errorBody = await response.text().catch(() => '')
    let errorMessage = `请求失败: ${response.status} ${response.statusText}`
    try {
      const errorJson = JSON.parse(errorBody)
      if (errorJson.message) errorMessage = errorJson.message
      else if (errorJson.detail) errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail)
    } catch {}
    throw new Error(errorMessage)
  }
  const result = await response.json()
  return result.data ?? result
}

export async function getInspectionTables(params?: {
  is_active?: boolean
  keyword?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active))
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  return apiFetch(`/api/v1/quality/inspection-table?${searchParams.toString()}`)
}

export async function getInspectionTable(id: string) {
  return apiFetch(`/api/v1/quality/inspection-table/${id}`)
}

export async function createInspectionTable(data: CreateTableRequest) {
  return apiFetch(`/api/v1/quality/inspection-table`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateInspectionTable(id: string, data: UpdateTableRequest) {
  return apiFetch(`/api/v1/quality/inspection-table/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteInspectionTable(id: string) {
  return apiFetch(`/api/v1/quality/inspection-table/${id}`, {
    method: 'DELETE',
  })
}

export async function addTableRow(tableId: string, rowData: Record<string, unknown>) {
  return apiFetch(`/api/v1/quality/inspection-table/${tableId}/rows`, {
    method: 'POST',
    body: JSON.stringify({ row_data: rowData }),
  })
}

export async function updateTableRow(tableId: string, rowId: number, rowData: Record<string, unknown>) {
  return apiFetch(`/api/v1/quality/inspection-table/${tableId}/rows/${rowId}`, {
    method: 'PUT',
    body: JSON.stringify({ row_data: rowData }),
  })
}

export async function deleteTableRow(tableId: string, rowId: number) {
  return apiFetch(`/api/v1/quality/inspection-table/${tableId}/rows/${rowId}`, {
    method: 'DELETE',
  })
}

export async function batchSaveTableRows(tableId: string, rows: Record<string, any>[]) {
  return apiFetch(`/api/v1/quality/inspection-table/${tableId}/rows/batch`, {
    method: 'POST',
    body: JSON.stringify({ rows }),
  })
}

export async function recognizeImage(tableId: string, file: File): Promise<RecognizeResult> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetchFormData<RecognizeResult>(`/api/v1/quality/inspection-table/${tableId}/recognize/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function recognizeMultipleImagesV3(tableId: string, files: File[]): Promise<RecognizeResult> {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })
  return apiFetchFormData<RecognizeResult>(`/api/v1/quality/inspection-table/${tableId}/recognize/multiple`, {
    method: 'POST',
    body: formData,
  })
}

export async function uploadInspectionTemplate(tableId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetchFormData(`/api/v1/quality/inspection-table/${tableId}/template`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteInspectionTemplate(tableId: string) {
  return apiFetch(`/api/v1/quality/inspection-table/${tableId}/template`, {
    method: 'DELETE',
  })
}