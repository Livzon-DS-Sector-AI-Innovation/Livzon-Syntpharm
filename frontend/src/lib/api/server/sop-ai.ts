import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function getConfigs() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/config`)
}

export async function getConfig(configKey: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/config/${configKey}`)
}

export async function updateConfig(configKey: string, data: { config_value: string; description?: string; operator?: string }) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/config/${configKey}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function singleCheck(data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/check/single`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function batchCheck(data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/check/batch`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getCheckRecords(params: Record<string, unknown> = {}) {
  const searchParams = new URLSearchParams()
  if (params.status) searchParams.set('status', String(params.status))
  if (params.file_code) searchParams.set('file_code', String(params.file_code))
  if (params.start_date) searchParams.set('start_date', String(params.start_date))
  if (params.end_date) searchParams.set('end_date', String(params.end_date))
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/records${query}`)
}

export async function getCheckRecordDetail(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/records/${id}`)
}

export async function exportCheckReport(id: string, format: string = 'excel', includeProblems: boolean = true) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/export/${id}?format=${format}&include_problems=${includeProblems}`)
}

export async function handleProblem(problemId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/problems/${problemId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function getScheduledJobs() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/jobs`)
}

export async function createScheduledJob(data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/jobs`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteScheduledJob(jobId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/jobs/${jobId}`, {
    method: 'DELETE',
  })
}