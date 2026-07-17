import { apiFetch, apiFetchRaw, API_BASE_URL } from '@/lib/api/server/base'
import type {
  Reagent,
  ReagentListResponse,
  CreateReagentRequest,
  UpdateReagentRequest,
  AiRecognizeResponse,
} from '@/types/reagent-quality'

const BASE_PATH = `${API_BASE_URL}/api/v1`

export async function recognizeReagentLabel(formData: FormData) {
  return apiFetch<{ code: number; message: string; data: AiRecognizeResponse | null }>(`${BASE_PATH}/quality/reagent/recognize`, {
    method: 'POST',
    body: formData,
  })
}

export async function getNextIncomingLotNo(dateStr?: string) {
  const url = dateStr
    ? `${BASE_PATH}/quality/reagent/next-lot-no?date_str=${dateStr}`
    : `${BASE_PATH}/quality/reagent/next-lot-no`
  return apiFetch<{ code: number; message: string; data: { incoming_lot_no: string } | null }>(url)
}

export async function getReagentList(params: {
  keyword?: string
  category?: string
  status?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params.keyword) searchParams.set('keyword', params.keyword)
  if (params.category) searchParams.set('category', params.category)
  if (params.status) searchParams.set('status', params.status)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  return apiFetch<{ code: number; message: string; data: ReagentListResponse }>(`${BASE_PATH}/quality/reagent/list?${searchParams.toString()}`)
}

export async function getReagentDetail(reagentId: string) {
  return apiFetch<{ code: number; message: string; data: Reagent | null }>(`${BASE_PATH}/quality/reagent/${reagentId}`)
}

export async function createReagent(data: CreateReagentRequest) {
  return apiFetch<{ code: number; message: string; data: Reagent | null }>(`${BASE_PATH}/quality/reagent`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateReagent(reagentId: string, data: UpdateReagentRequest) {
  return apiFetch<{ code: number; message: string; data: Reagent | null }>(`${BASE_PATH}/quality/reagent/${reagentId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteReagent(reagentId: string) {
  return apiFetch<{ code: number; message: string; data: null }>(`${BASE_PATH}/quality/reagent/${reagentId}`, {
    method: 'DELETE',
  })
}

export async function exportReagentsExcel(params?: {
  keyword?: string
  category?: string
  status?: string
}) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.category) searchParams.set('category', params.category)
  if (params?.status) searchParams.set('status', params.status)
  return apiFetchRaw(`${BASE_PATH}/quality/reagent/export?${searchParams.toString()}`)
}

export async function saveReagentReminderConfig(data: Record<string, unknown>) {
  return apiFetch(`${BASE_PATH}/quality/reagent-reminder/config`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function triggerReagentReminderCheck() {
  return apiFetch(`${BASE_PATH}/quality/reagent-reminder/check`, {
    method: 'POST',
  })
}

export async function setReagentItemReminder(reagentName: string, isEnabled: boolean) {
  return apiFetch(`${BASE_PATH}/quality/reagent-reminder/item-reminder`, {
    method: 'POST',
    body: JSON.stringify({ reagent_name: reagentName, is_enabled: isEnabled }),
  })
}