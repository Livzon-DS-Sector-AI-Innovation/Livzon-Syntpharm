import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'

const BASE = `${API_BASE_URL}/api/v1/registration/validation-audit`

async function uploadFetch(url: string, formData: FormData) {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`
  const response = await fetch(fullUrl, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!response.ok) {
    const json = await response.json().catch(() => ({}))
    throw new Error(json.message || `上传失败: ${response.status}`)
  }
  return response.json()
}

export async function fetchTasks(params?: {
  product_name?: string
  source_company?: string
  status?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.product_name) searchParams.set('product_name', params.product_name)
  if (params?.source_company) searchParams.set('source_company', params.source_company)
  if (params?.status) searchParams.set('status', params.status)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${BASE}/tasks?${searchParams.toString()}`)
}

export async function fetchTaskById(id: string) {
  return apiFetch(`${BASE}/tasks/${id}`)
}

export async function fetchFiles(taskId: string) {
  return apiFetch(`${BASE}/tasks/${taskId}/files`)
}

export async function fetchIssues(taskId: string, issueType?: string) {
  const params = new URLSearchParams()
  if (issueType) params.set('issue_type', issueType)
  return apiFetch(`${BASE}/tasks/${taskId}/issues?${params.toString()}`)
}

export async function fetchReport(taskId: string) {
  return apiFetch(`${BASE}/tasks/${taskId}/report`)
}

export async function createTask(data: any) {
  return apiFetch(`${BASE}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteTask(taskId: string) {
  return apiFetch(`${BASE}/tasks/${taskId}`, {
    method: 'DELETE',
  })
}

export async function uploadFiles(taskId: string, formData: FormData) {
  return uploadFetch(`${BASE}/tasks/${taskId}/files`, formData)
}

export async function parseFiles(taskId: string) {
  return apiFetch(`${BASE}/tasks/${taskId}/parse`, {
    method: 'POST',
  })
}

export async function runAudit(taskId: string) {
  return apiFetch(`${BASE}/tasks/${taskId}/audit`, {
    method: 'POST',
  })
}