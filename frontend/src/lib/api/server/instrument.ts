import { apiFetch, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'
import type {
  Instrument,
  InstrumentListItem,
  InstrumentListResponse,
  InstrumentCreate,
  InstrumentUpdate,
  InstrumentFilter,
  CalibrationRule,
  CalibrationRuleCreate,
  CalibrationRuleUpdate,
  CalibrationRecord,
  CalibrationRecordListResponse,
  CalibrationRecordCreate,
  CalibrationRecordUpdate,
  CalibrationRecordFilter,
  ApprovalRecord,
  ApprovalCreate,
  AIRecognizedInstrumentInfo,
  UpcomingCalibrationResponse,
  ReminderResponse,
  RecordsForReminderResponse,
  ReminderConfig,
  ReminderConfigListResponse,
  ReminderConfigCreate,
  ReminderConfigUpdate,
  AutoTriggerResponse,
  FeishuUser,
  FeishuDepartment,
} from '@/types/instrument'

export async function getInstruments(params: InstrumentFilter = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.instrument_no) searchParams.set('instrument_no', params.instrument_no)
  if (params.instrument_name) searchParams.set('instrument_name', params.instrument_name)
  if (params.category) searchParams.set('category', params.category)
  if (params.is_active !== undefined) searchParams.set('is_active', String(params.is_active))
  if (params.status) searchParams.set('status', params.status)
  if (params.is_overdue !== undefined) searchParams.set('is_overdue', String(params.is_overdue))
  const queryString = searchParams.toString()
  return apiFetch<InstrumentListResponse>(`/api/v1/quality/instrument${queryString ? `?${queryString}` : ''}`)
}

export async function getInstrument(id: string) {
  return apiFetch<Instrument>(`/api/v1/quality/instrument/${id}`)
}

export async function createInstrument(data: InstrumentCreate) {
  return apiFetch<Instrument>('/api/v1/quality/instrument', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateInstrument(id: string, data: InstrumentUpdate) {
  return apiFetch<Instrument>(`/api/v1/quality/instrument/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteInstrument(id: string) {
  return apiFetch<null>(`/api/v1/quality/instrument/${id}`, {
    method: 'DELETE',
  })
}

export async function deactivateInstrument(id: string, reason: string) {
  return apiFetch<Instrument>(
    `/api/v1/quality/instrument/${id}/deactivate?reason=${encodeURIComponent(reason)}`,
    { method: 'POST' }
  )
}

export async function getOverdueInstruments() {
  return apiFetch<InstrumentListItem[]>('/api/v1/quality/instrument/overdue')
}

export async function getUpcomingCalibrations(days: number = 30) {
  return apiFetch<InstrumentListItem[]>(`/api/v1/quality/instrument/upcoming?days=${days}`)
}

export async function getCalibrationRules(instrumentId?: string) {
  const endpoint = instrumentId
    ? `/api/v1/quality/instrument/rules?instrument_id=${instrumentId}`
    : '/api/v1/quality/instrument/rules'
  return apiFetch<CalibrationRule[]>(endpoint)
}

export async function getCalibrationRule(id: string) {
  return apiFetch<CalibrationRule>(`/api/v1/quality/instrument/rules/${id}`)
}

export async function createCalibrationRule(data: CalibrationRuleCreate) {
  return apiFetch<CalibrationRule>('/api/v1/quality/instrument/rules', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCalibrationRule(id: string, data: CalibrationRuleUpdate) {
  return apiFetch<CalibrationRule>(`/api/v1/quality/instrument/rules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCalibrationRule(id: string) {
  return apiFetch<null>(`/api/v1/quality/instrument/rules/${id}`, {
    method: 'DELETE',
  })
}

export async function getCalibrationRecords(params: CalibrationRecordFilter = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.instrument_id) searchParams.set('instrument_id', params.instrument_id)
  if (params.rule_id) searchParams.set('rule_id', params.rule_id)
  if (params.calibration_no) searchParams.set('calibration_no', params.calibration_no)
  if (params.calibration_result) searchParams.set('calibration_result', params.calibration_result)
  if (params.status) searchParams.set('status', params.status)
  if (params.calibration_method) searchParams.set('calibration_method', params.calibration_method)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const queryString = searchParams.toString()
  return apiFetch<CalibrationRecordListResponse>(`/api/v1/quality/instrument/records${queryString ? `?${queryString}` : ''}`)
}

export async function getCalibrationRecord(id: string) {
  return apiFetch<CalibrationRecord>(`/api/v1/quality/instrument/records/${id}`)
}

export async function createCalibrationRecord(data: CalibrationRecordCreate) {
  return apiFetch<CalibrationRecord>('/api/v1/quality/instrument/records', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCalibrationRecord(id: string, data: CalibrationRecordUpdate) {
  return apiFetch<CalibrationRecord>(`/api/v1/quality/instrument/records/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCalibrationRecord(id: string) {
  return apiFetch<null>(`/api/v1/quality/instrument/records/${id}`, {
    method: 'DELETE',
  })
}

export async function submitCalibrationRecord(id: string) {
  return apiFetch<CalibrationRecord>(`/api/v1/quality/instrument/records/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveCalibrationRecordByAdmin(id: string) {
  return apiFetch<CalibrationRecord>(`/api/v1/quality/instrument/records/${id}/approve?approved=true&approval_type=admin`, {
    method: 'POST',
  })
}

export async function approveCalibrationRecordByQA(id: string) {
  return apiFetch<CalibrationRecord>(`/api/v1/quality/instrument/records/${id}/approve?approved=true&approval_type=qa`, {
    method: 'POST',
  })
}

export async function rejectCalibrationRecord(id: string, comments: string) {
  return apiFetch<CalibrationRecord>(
    `/api/v1/quality/instrument/records/${id}/approve?approved=false&comments=${encodeURIComponent(comments)}&approval_type=admin`,
    { method: 'POST' }
  )
}

export async function getInstrumentApprovals(instrumentId: string) {
  return apiFetch<ApprovalRecord[]>(`/api/v1/quality/instrument/${instrumentId}/approvals`)
}

export async function getCalibrationRecordApprovals(recordId: string) {
  return apiFetch<ApprovalRecord[]>(`/api/v1/quality/instrument/records/${recordId}/approvals`)
}

export async function approveInstrument(id: string, data: ApprovalCreate) {
  return apiFetch<ApprovalRecord>(`/api/v1/quality/instrument/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function approveCalibrationRecord(id: string, data: ApprovalCreate) {
  return apiFetch<ApprovalRecord>(`/api/v1/quality/instrument/records/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function recognizeInstrumentLabel(file: File): Promise<AIRecognizedInstrumentInfo> {
  const formData = new FormData()
  formData.append('file', file)
  const url = `${getApiBaseUrl()}/api/v1/quality/instrument/recognize`
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!response.ok) {
    const errorBody = await response.text().catch(() => '')
    throw new Error(`请求失败: ${response.status} ${errorBody}`)
  }
  const result = await response.json()
  return unwrapResponse(result)
}

export async function getUpcomingCalibrationRecords(days: number = 30): Promise<UpcomingCalibrationResponse> {
  return apiFetch<UpcomingCalibrationResponse>(`/api/v1/quality/instrument/record/upcoming?days=${days}`)
}

export async function getRecordsForReminder(days: number = 30): Promise<RecordsForReminderResponse> {
  return apiFetch<RecordsForReminderResponse>(`/api/v1/quality/instrument/record/for-reminder?days=${days}`)
}

export async function sendCalibrationReminder(
  chatId: string,
  receiveIdType: 'chat_id' | 'open_id' = 'chat_id',
  days: number = 30,
  feishuAppId?: string,
  feishuAppSecret?: string
): Promise<ReminderResponse> {
  const params = new URLSearchParams({
    chat_id: chatId,
    receive_id_type: receiveIdType,
    days: String(days),
  })
  if (feishuAppId) params.set('feishu_app_id', feishuAppId)
  if (feishuAppSecret) params.set('feishu_app_secret', feishuAppSecret)
  const result = await apiFetch<ReminderResponse>(`/api/v1/quality/instrument/record/remind?${params}`, {
    method: 'POST',
  })
  return result
}

export async function getReminderConfigs(): Promise<ReminderConfigListResponse> {
  return apiFetch<ReminderConfigListResponse>('/api/v1/quality/instrument/reminder-config')
}

export async function createReminderConfig(data: ReminderConfigCreate): Promise<ReminderConfig> {
  return apiFetch<ReminderConfig>('/api/v1/quality/instrument/reminder-config', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateReminderConfig(id: string, data: ReminderConfigUpdate): Promise<ReminderConfig> {
  return apiFetch<ReminderConfig>(`/api/v1/quality/instrument/reminder-config/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteReminderConfig(id: string): Promise<void> {
  await apiFetch(`/api/v1/quality/instrument/reminder-config/${id}`, {
    method: 'DELETE',
  })
}

export async function autoTriggerReminders(): Promise<AutoTriggerResponse> {
  return apiFetch<AutoTriggerResponse>('/api/v1/quality/instrument/reminder/auto-trigger', {
    method: 'POST',
  })
}

export async function resolveFeishuUser(mobile?: string, email?: string): Promise<string | null> {
  const result = await apiFetch<{ open_id: string | null }>('/api/v1/quality/instrument/feishu-contacts/resolve-user', {
    method: 'POST',
    body: JSON.stringify({ mobile, email }),
  })
  return result.open_id ?? null
}

export async function getFeishuContactUsers(departmentId: string = '0'): Promise<FeishuUser[]> {
  const result = await apiFetch<{ users: FeishuUser[] }>(`/api/v1/quality/instrument/feishu-contacts/users?department_id=${encodeURIComponent(departmentId)}`)
  return result.users ?? []
}

export async function getFeishuContactDepartments(parentDepartmentId: string = '0'): Promise<FeishuDepartment[]> {
  const result = await apiFetch<{ departments: FeishuDepartment[] }>(`/api/v1/quality/instrument/feishu-contacts/departments?parent_department_id=${encodeURIComponent(parentDepartmentId)}`)
  return result.departments ?? []
}