import {
  PilotWorkflow,
  PilotWorkflowFilters,
  PilotWorkflowListItem,
  PilotWorkflowListResponse,
} from '@/types/pilot-workflow'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

export async function fetchPilotWorkflows(
  filters: PilotWorkflowFilters = {}
): Promise<PilotWorkflowListResponse> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.keyword) params.set('keyword', filters.keyword)
  if (filters.page) params.set('page', String(filters.page))
  if (filters.page_size) params.set('page_size', String(filters.page_size))

  const qs = params.toString()
  const url = `/api/v1/research/pilot/workflow${qs ? `?${qs}` : ''}`
  return apiFetchPaginated<PilotWorkflowListItem>(url)
}

export async function fetchPilotWorkflow(
  workflowId: string
): Promise<PilotWorkflow> {
  const url = `/api/v1/research/pilot/workflow/${workflowId}`
  return apiGet<PilotWorkflow>(url)
}
