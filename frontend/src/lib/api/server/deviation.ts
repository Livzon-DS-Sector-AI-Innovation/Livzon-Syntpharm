import type { DeviationCreate, DeviationUpdate, InvestigationCreate, CorrectionCreate, ClosingCreate } from '@/types/deviation'

const API_BASE = (process.env.API_BASE_URL || 'http://dazah-backend-app-1:8000') + '/api/v1'

async function deviationFetch(endpoint: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    cache: 'no-store',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

async function deviationFetchUpload(endpoint: string, body: FormData) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body,
    cache: 'no-store',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// ============ 偏差流程 ============

export async function createDeviationFlow(data: Record<string, unknown>) {
  return deviationFetch('/quality/deviation-flow', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDeviationFlow(id: string, data: Record<string, unknown>) {
  return deviationFetch(`/quality/deviation-flow/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function submitDeviationFlow(id: string, targetStatus: string) {
  return deviationFetch(`/quality/deviation-flow/${id}/submit?target_status=${targetStatus}`, {
    method: 'POST',
  })
}

export async function uploadDeviationAttachment(deviationId: string, formData: FormData) {
  return deviationFetchUpload(`/quality/deviation-flow/${deviationId}/attachments`, formData)
}

// ============ 偏差设置（通用） ============

export async function saveDeviationSetting(url: string, method: string, values: Record<string, unknown>) {
  return deviationFetch(url, {
    method,
    body: JSON.stringify(values),
  })
}

export async function deleteDeviationSetting(url: string) {
  return deviationFetch(url, {
    method: 'DELETE',
  })
}

export async function toggleDeviationSetting(url: string) {
  return deviationFetch(url, {
    method: 'PUT',
  })
}

export async function setDefaultDeviationTemplate(templateId: string) {
  return deviationFetch(`/quality/deviation-settings/message-templates/${templateId}/set-default`, {
    method: 'PUT',
  })
}

// ============ 偏差 CRUD ============

export async function getDeviations(params?: {
  status?: string
  deviation_type?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.deviation_type) searchParams.set('deviation_type', params.deviation_type)
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  return deviationFetch(`/quality/deviation?${searchParams.toString()}`)
}

export async function getDeviationById(id: string) {
  return deviationFetch(`/quality/deviation/${id}`)
}

export async function createDeviation(data: DeviationCreate) {
  return deviationFetch('/quality/deviation', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDeviation(id: string, data: DeviationUpdate) {
  return deviationFetch(`/quality/deviation/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDeviation(id: string) {
  return deviationFetch(`/quality/deviation/${id}`, {
    method: 'DELETE',
  })
}

export async function submitDeviation(id: string) {
  return deviationFetch(`/quality/deviation/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveDeviation(id: string, data: { approved: boolean; comment?: string }) {
  return deviationFetch(`/quality/deviation/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function lockBatch(id: string, data: { reason: string }) {
  return deviationFetch(`/quality/deviation/${id}/lock-batch`, {
    method: 'POST',
    body: JSON.stringify({ deviation_id: id, ...data }),
  })
}

export async function unlockBatch(id: string) {
  return deviationFetch(`/quality/deviation/${id}/unlock-batch`, {
    method: 'POST',
  })
}

// ============ 偏差调查 ============

export async function getInvestigations(params?: { deviation_id?: string; page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.deviation_id) searchParams.set('deviation_id', params.deviation_id)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  return deviationFetch(`/quality/deviation/investigations/list?${searchParams.toString()}`)
}

export async function createInvestigation(data: InvestigationCreate) {
  return deviationFetch('/quality/deviation/investigations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateInvestigation(id: string, data: Partial<InvestigationCreate>) {
  return deviationFetch(`/quality/deviation/investigations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ============ 偏差整改 ============

export async function getCorrections(params?: { deviation_id?: string; status?: string; page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.deviation_id) searchParams.set('deviation_id', params.deviation_id)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  return deviationFetch(`/quality/deviation/corrections/list?${searchParams.toString()}`)
}

export async function createCorrection(data: CorrectionCreate) {
  return deviationFetch('/quality/deviation/corrections', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCorrection(id: string, data: Partial<CorrectionCreate>) {
  return deviationFetch(`/quality/deviation/corrections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ============ 偏差关闭 ============

export async function getClosings(params?: { deviation_id?: string; page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.deviation_id) searchParams.set('deviation_id', params.deviation_id)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  return deviationFetch(`/quality/deviation/closings/list?${searchParams.toString()}`)
}

export async function createClosing(data: ClosingCreate) {
  return deviationFetch('/quality/deviation/closings', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateClosing(id: string, data: Partial<ClosingCreate>) {
  return deviationFetch(`/quality/deviation/closings/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ============ 统计 ============

export async function getDeviationStatistics() {
  return deviationFetch('/quality/deviation/statistics')
}

// ============ AI辅助功能 ============

export async function aiGenerateDescription(params: {
  deviation_type?: string
  deviation_level?: string
  occurrence_date?: string
  discovering_department?: string
  product_name?: string
  production_batch?: string
  keywords: string
}) {
  const searchParams = new URLSearchParams()
  if (params.deviation_type) searchParams.set('deviation_type', params.deviation_type)
  if (params.deviation_level) searchParams.set('deviation_level', params.deviation_level)
  if (params.occurrence_date) searchParams.set('occurrence_date', params.occurrence_date)
  if (params.discovering_department) searchParams.set('discovering_department', params.discovering_department)
  if (params.product_name) searchParams.set('product_name', params.product_name)
  if (params.production_batch) searchParams.set('production_batch', params.production_batch)
  searchParams.set('keywords', params.keywords)
  return deviationFetch(`/quality/deviation/ai/generate-description?${searchParams.toString()}`, {
    method: 'POST',
  })
}

export async function aiAnalyzeImpact(params: {
  deviation_type?: string
  deviation_level?: string
  occurrence_date?: string
  discovering_department?: string
  product_name?: string
  production_batch?: string
  description?: string
}) {
  const searchParams = new URLSearchParams()
  if (params.deviation_type) searchParams.set('deviation_type', params.deviation_type)
  if (params.deviation_level) searchParams.set('deviation_level', params.deviation_level)
  if (params.occurrence_date) searchParams.set('occurrence_date', params.occurrence_date)
  if (params.discovering_department) searchParams.set('discovering_department', params.discovering_department)
  if (params.product_name) searchParams.set('product_name', params.product_name)
  if (params.production_batch) searchParams.set('production_batch', params.production_batch)
  if (params.description) searchParams.set('description', params.description)
  return deviationFetch(`/quality/deviation/ai/analyze-impact?${searchParams.toString()}`, {
    method: 'POST',
  })
}

export async function aiAnalyzeDirectCause(params: {
  deviation_type: string
  description?: string
  product_name?: string
  production_batch?: string
}) {
  const searchParams = new URLSearchParams()
  searchParams.set('deviation_type', params.deviation_type)
  if (params.description) searchParams.set('description', params.description)
  if (params.product_name) searchParams.set('product_name', params.product_name)
  if (params.production_batch) searchParams.set('production_batch', params.production_batch)
  return deviationFetch(`/quality/deviation/ai/analyze-direct-cause?${searchParams.toString()}`, {
    method: 'POST',
  })
}

export async function aiGenerateEmergencyMeasures(params: {
  deviation_type?: string
  deviation_level?: string
  occurrence_date?: string
  discovering_department?: string
  product_name?: string
  production_batch?: string
  description?: string
}) {
  const searchParams = new URLSearchParams()
  if (params.deviation_type) searchParams.set('deviation_type', params.deviation_type)
  if (params.deviation_level) searchParams.set('deviation_level', params.deviation_level)
  if (params.occurrence_date) searchParams.set('occurrence_date', params.occurrence_date)
  if (params.discovering_department) searchParams.set('discovering_department', params.discovering_department)
  if (params.product_name) searchParams.set('product_name', params.product_name)
  if (params.production_batch) searchParams.set('production_batch', params.production_batch)
  if (params.description) searchParams.set('description', params.description)
  return deviationFetch(`/quality/deviation/ai/generate-emergency-measures?${searchParams.toString()}`, {
    method: 'POST',
  })
}

export async function aiAnalyzeRootCause(params: {
  deviation_type: string
  description?: string
  direct_cause?: string
  root_cause?: string
  investigation_data?: string
}) {
  const searchParams = new URLSearchParams()
  searchParams.set('deviation_type', params.deviation_type)
  if (params.description) searchParams.set('description', params.description)
  if (params.direct_cause) searchParams.set('direct_cause', params.direct_cause)
  if (params.investigation_data) searchParams.set('investigation_data', params.investigation_data)
  return deviationFetch(`/quality/deviation/ai/analyze-root-cause?${searchParams.toString()}`, {
    method: 'POST',
  })
}

export async function aiGenerateCAPA(params: {
  deviation_type: string
  root_cause?: string
  deviation_level?: string
  department?: string
}) {
  const searchParams = new URLSearchParams()
  searchParams.set('deviation_type', params.deviation_type)
  if (params.root_cause) searchParams.set('root_cause', params.root_cause)
  if (params.deviation_level) searchParams.set('deviation_level', params.deviation_level)
  if (params.department) searchParams.set('department', params.department)
  return deviationFetch(`/quality/deviation/ai/generate-capa?${searchParams.toString()}`, {
    method: 'POST',
  })
}

export async function aiGeneratePrevention(params: {
  deviation_type: string
  root_cause?: string
  deviation_level?: string
  department?: string
}) {
  const searchParams = new URLSearchParams()
  searchParams.set('deviation_type', params.deviation_type)
  if (params.root_cause) searchParams.set('root_cause', params.root_cause)
  if (params.deviation_level) searchParams.set('deviation_level', params.deviation_level)
  if (params.department) searchParams.set('department', params.department)
  return deviationFetch(`/quality/deviation/ai/generate-prevention?${searchParams.toString()}`, {
    method: 'POST',
  })
}
