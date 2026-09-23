import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import {
  ReportCreate,
  ReportUpdate,
  ReportItemsBatchSave,
  TemplateUpdate,
} from '@/types/material-report'

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

export async function getReports(params?: {
  template_id?: string
  status?: string
  start_date?: string
  end_date?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.template_id) searchParams.set('template_id', params.template_id)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  return apiFetch(`/api/v1/quality/material-report?${searchParams.toString()}`)
}

export async function getReportById(id: string) {
  return apiFetch(`/api/v1/quality/material-report/${id}`)
}

export async function createReport(data: ReportCreate) {
  return apiFetch('/api/v1/quality/material-report', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateReport(id: string, data: ReportUpdate) {
  return apiFetch(`/api/v1/quality/material-report/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteReport(id: string) {
  return apiFetch(`/api/v1/quality/material-report/${id}`, {
    method: 'DELETE',
  })
}

export async function saveReportItems(id: string, data: ReportItemsBatchSave) {
  return apiFetch(`/api/v1/quality/material-report/${id}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateReport(id: string): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/quality/material-report/${id}/generate`, {
    method: 'POST',
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`生成报告失败: ${response.status}`)
  }
  return response.blob()
}

export async function submitReport(id: string) {
  return apiFetch(`/api/v1/quality/material-report/${id}/submit`, {
    method: 'POST',
  })
}

export async function getReportStatistics() {
  return apiFetch('/api/v1/quality/material-report/statistics')
}

export async function getTemplates(params?: {
  is_active?: boolean
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active))
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  return apiFetch(`/api/v1/quality/material-report/template?${searchParams.toString()}`)
}

export async function getTemplateById(id: string) {
  return apiFetch(`/api/v1/quality/material-report/template/${id}`)
}

export async function uploadTemplate(
  file: File,
  templateName: string,
  templateDescription?: string,
  fieldMapping?: Record<string, unknown>,
  tableFields?: Record<string, unknown>
) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('template_name', templateName)
  if (templateDescription) {
    formData.append('template_description', templateDescription)
  }
  if (fieldMapping) {
    formData.append('field_mapping', JSON.stringify(fieldMapping))
  }
  if (tableFields) {
    formData.append('table_fields', JSON.stringify(tableFields))
  }
  return apiFetchFormData('/api/v1/quality/material-report/template', {
    method: 'POST',
    body: formData,
  })
}

export async function updateTemplate(id: string, data: TemplateUpdate) {
  return apiFetch(`/api/v1/quality/material-report/template/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTemplate(id: string) {
  return apiFetch(`/api/v1/quality/material-report/template/${id}`, {
    method: 'DELETE',
  })
}

export async function previewTemplate(id: string) {
  return apiFetch(`/api/v1/quality/material-report/template/${id}/preview`)
}

export async function uploadReportImage(
  reportId: string,
  file: File,
  fieldKey?: string,
  rowIndex?: number
) {
  const formData = new FormData()
  formData.append('file', file)
  if (fieldKey) {
    formData.append('field_key', fieldKey)
  }
  if (rowIndex !== undefined) {
    formData.append('row_index', String(rowIndex))
  }
  return apiFetchFormData(`/api/v1/quality/material-report/${reportId}/images`, {
    method: 'POST',
    body: formData,
  })
}

export async function getReportImages(reportId: string) {
  return apiFetch(`/api/v1/quality/material-report/${reportId}/images`)
}