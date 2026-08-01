import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type {
  StartCheckRequest,
  CheckConfig,
  HandleProblemRequest,
  QueryCheckRecordsRequest,
} from '@/types/doc-check'

export async function startCheckApi(data: StartCheckRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/check/single`, {
    method: 'POST',
    body: JSON.stringify({
      file_path: data.file_id,
      file_name: data.file_name || 'unknown',
      check_type: 'duplicate_check',
      operator: data.operator,
    }),
  })
}

export async function getCheckProgressApi(taskId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/records/${taskId}`)
}

export async function batchCheckApi(fileIds: string[], checkConfig: CheckConfig, operator?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/check/batch`, {
    method: 'POST',
    body: JSON.stringify({
      file_paths: fileIds,
      check_type: 'duplicate_check',
      operator,
    }),
  })
}

export async function getCheckRecordsApi(filter?: QueryCheckRecordsRequest) {
  const searchParams = new URLSearchParams()
  if (filter?.status) searchParams.set('status', filter.status)
  if (filter?.file_no) searchParams.set('file_code', filter.file_no)
  if (filter?.file_type) searchParams.set('file_type', filter.file_type)
  if (filter?.start_date) searchParams.set('start_date', filter.start_date)
  if (filter?.end_date) searchParams.set('end_date', filter.end_date)
  if (filter?.page) searchParams.set('page', String(filter.page))
  if (filter?.page_size) searchParams.set('page_size', String(filter.page_size))
  const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/records${query}`)
}

export async function getCheckRecordDetailApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/records/${id}`)
}

export async function handleProblemApi(problemId: string, data: HandleProblemRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/problems/${problemId}`, {
    method: 'PUT',
    body: JSON.stringify({
      handle_status: data.handle_status,
      ignore_reason: data.ignore_reason,
      operator: data.operator,
    }),
  })
}

export async function exportCheckReportApi(id: string, format: 'pdf' | 'excel' = 'pdf') {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/export/${id}?format=${format}`)
}

export async function getCheckConfigApi() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/config`)
}

export async function updateCheckConfigApi(key: string, value: string, operator?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/sop-ai/config/${key}`, {
    method: 'PUT',
    body: JSON.stringify({
      config_value: value,
      operator,
    }),
  })
}