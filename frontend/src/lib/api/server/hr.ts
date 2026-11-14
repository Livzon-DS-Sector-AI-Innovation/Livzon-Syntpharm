import { apiFetch, apiFetchRaw, getApiBaseUrl } from '@/lib/api/server/base'
import type { components, operations } from '@/types/generated/schema'
import type {
  CandidateListParams,
  EmployeeProfileDetailResponse,
  EmployeeProfileListResponse,
  OrgDepartmentTreeResponse,
  OrgSyncStatusResponse,
  OrgSyncTriggerResponse,
} from '@/types/hr'

type Schemas = components['schemas']
type OnboardingRecordListQuery = NonNullable<
  operations['list_onboarding_records_api_v1_hr_onboarding_records_get']['parameters']['query']
>
type DepartureRecordListQuery = NonNullable<
  operations['list_departure_records_api_v1_hr_departure_records_get']['parameters']['query']
>

async function apiFetchFormData(url: string, body: FormData): Promise<unknown> {
  return apiFetch(url, { method: 'POST', body })
}

async function apiFetchBlob(url: string, options?: RequestInit): Promise<Blob> {
  // apiFetchRaw 会带上 Authorization 头；裸 fetch 会绕过服务端鉴权。
  const res = await apiFetchRaw(url, options)
  return res.blob()
}

export async function fetchEmployeesApi(params?: {
  department?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', String(params.department))
  if (params?.status) searchParams.set('status', String(params.status))
  if (params?.keyword) searchParams.set('keyword', String(params.keyword))
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees?${searchParams.toString()}`)
}

export async function createEmployeeApi(
  data: Schemas['EmployeeCreate'],
): Promise<Schemas['DataResponse_EmployeeResponse_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEmployeeApi(
  id: string,
  data: Schemas['EmployeeUpdate'],
): Promise<Schemas['DataResponse_EmployeeResponse_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteEmployeeApi(id: string): Promise<Schemas['app__shared__schemas__MessageApiResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees/${id}`, {
    method: 'DELETE',
  })
}

export async function uploadEmployeesApi(formData: FormData) {
  return apiFetchFormData(`${getApiBaseUrl()}/api/v1/hr/employees/upload`, formData)
}

export async function syncFromFeishuApi(): Promise<Schemas['AsyncJobAcceptedResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees/sync-from-feishu`, {
    method: 'POST',
  })
}

export async function syncToFeishuApi(id: string): Promise<Schemas['DataResponse_EmployeeFeishuSyncResult_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees/${id}/sync-to-feishu`, {
    method: 'POST',
  })
}

export async function fetchOrgDepartmentsApi(): Promise<OrgDepartmentTreeResponse> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/org/departments`)
}

export async function fetchOrgSyncStatusApi(): Promise<OrgSyncStatusResponse> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/org/sync-status`)
}

export async function triggerOrgSyncApi(): Promise<OrgSyncTriggerResponse> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/org/sync`, {
    method: 'POST',
  })
}

export async function fetchDepartmentsApi(params?: {
  keyword?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', String(params.keyword))
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/departments?${searchParams.toString()}`)
}








export async function createAnnualTrainingPlanApi(data: Schemas['AnnualTrainingPlanCreate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/annual-training-plans`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAnnualTrainingPlanApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/annual-training-plans/${id}`, {
    method: 'DELETE',
  })
}

export async function deleteAnnualPlanItemApi(planId: string, itemId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/annual-training-plans/${planId}/items/${itemId}`, {
    method: 'DELETE',
  })
}

export async function batchUpdatePlanItemsApi(planId: string, data: Schemas['AnnualTrainingPlanItemBatchUpdate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/annual-training-plans/${planId}/items`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function fetchOnboardingRecordsApi(
  params?: OnboardingRecordListQuery,
): Promise<Schemas['OnboardingRecordListApiResponse']> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', String(params.department))
  if (params?.keyword) searchParams.set('keyword', String(params.keyword))
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/onboarding-records?${searchParams.toString()}`)
}

export async function createOnboardingRecordApi(
  data: Schemas['OnboardingRecordCreate'],
): Promise<Schemas['OnboardingRecordApiResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/onboarding-records`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateOnboardingRecordApi(
  id: string,
  data: Schemas['OnboardingRecordUpdate'],
): Promise<Schemas['OnboardingRecordApiResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/onboarding-records/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteOnboardingRecordApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/onboarding-records/${id}`, {
    method: 'DELETE',
  })
}

export async function fetchDepartureRecordsApi(
  params?: DepartureRecordListQuery,
): Promise<Schemas['DepartureRecordListApiResponse']> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/departure-records?${searchParams.toString()}`)
}

export async function createDepartureRecordApi(
  data: Schemas['DepartureRecordCreate'],
): Promise<Schemas['DepartureRecordApiResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/departure-records`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDepartureRecordApi(
  id: string,
  data: Schemas['DepartureRecordUpdate'],
): Promise<Schemas['DepartureRecordApiResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/departure-records/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDepartureRecordApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/departure-records/${id}`, {
    method: 'DELETE',
  })
}

export async function fetchEmployeeByIdApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees/${id}`)
}

export async function fetchCandidateByIdApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/candidates/${id}`)
}

export async function fetchCandidatesApi(params?: CandidateListParams) {
  const searchParams = new URLSearchParams()
  if (params?.position) searchParams.set('position', String(params.position))
  if (params?.education) searchParams.set('education', String(params.education))
  if (params?.recommendation_level) searchParams.set('recommendation_level', String(params.recommendation_level))
  if (params?.sync_status) searchParams.set('sync_status', String(params.sync_status))
  if (params?.keyword) searchParams.set('keyword', String(params.keyword))
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/candidates?${searchParams.toString()}`)
}

export async function fetchAnnualTrainingPlanByIdApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/annual-training-plans/${id}`)
}

export async function fetchPlanItemsApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/annual-training-plans/${id}/items`)
}

export async function fetchEmployeeByNumberApi(employeeNumber: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/employees/by-number/${employeeNumber}`)
}

export async function syncTrainingSpecialistsFeishuOpenIdsApi(): Promise<Schemas['AsyncJobAcceptedResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-specialists/sync-feishu-openids`, {
    method: 'POST',
  })
}

export async function createTrainingLedgerApi(
  data: Schemas['TrainingLedgerCreate'],
): Promise<Schemas['DataResponse_TrainingLedgerResponse_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-ledgers`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTrainingLedgerApi(
  id: string,
  data: Schemas['TrainingLedgerUpdate'],
): Promise<Schemas['DataResponse_TrainingLedgerResponse_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-ledgers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingLedgerApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-ledgers/${id}`, {
    method: 'DELETE',
  })
}

export async function createTrainingLedgerPageApi(
  data: Schemas['TrainingLedgerPageCreate'],
): Promise<Schemas['DataResponse_TrainingLedgerPageResponse_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-ledgers/pages`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function sendTrainingNotificationApi(data: Schemas['TrainingNotifyInput']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-notifications/send`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateTrainingSignInSheetApi(
  data: Schemas['TrainingSignInSheetInput'],
  factory: 'old' | 'new' = 'old',
): Promise<Blob> {
  return apiFetchBlob(`${getApiBaseUrl()}/api/v1/hr/training-sign-in-sheet?factory=${factory}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateTrainingNotificationApi(
  data: Schemas['TrainingNotificationInput'],
  factory: 'old' | 'new' = 'old',
): Promise<Blob> {
  return apiFetchBlob(`${getApiBaseUrl()}/api/v1/hr/training-notification?factory=${factory}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateTrainingEvaluationApi(
  data: Schemas['TrainingEvaluationInput'],
  factory: 'old' | 'new' = 'old',
): Promise<Blob> {
  return apiFetchBlob(`${getApiBaseUrl()}/api/v1/hr/training-evaluation?factory=${factory}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateOnboardingEvaluationApi(
  data: Schemas['OnboardingEvaluationInput'],
  factory: 'old' | 'new' = 'old',
): Promise<Blob> {
  return apiFetchBlob(`${getApiBaseUrl()}/api/v1/hr/onboarding-evaluation?factory=${factory}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createOnboardingTrainingRecordApi(employeeNumber: string, data: unknown) {
  return apiFetchBlob(`${getApiBaseUrl()}/api/v1/hr/employees/${employeeNumber}/onboarding-training-record`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function uploadAnnualTrainingPlanApi(formData: FormData) {
  return apiFetchFormData(`${getApiBaseUrl()}/api/v1/hr/annual-training-plans/upload`, formData)
}

export async function uploadTrainersApi(formData: FormData) {
  return apiFetchFormData(`${getApiBaseUrl()}/api/v1/hr/trainers/upload`, formData)
}

export async function uploadSopCatalogApi(formData: FormData) {
  return apiFetchFormData(`${getApiBaseUrl()}/api/v1/hr/sop-catalog/upload`, formData)
}

export async function fetchTrainingSessionsApi(params?: {
  department?: string
  keyword?: string
  status?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', String(params.department))
  if (params?.keyword) searchParams.set('keyword', String(params.keyword))
  if (params?.status) searchParams.set('status', String(params.status))
  if (params?.date_from) searchParams.set('date_from', String(params.date_from))
  if (params?.date_to) searchParams.set('date_to', String(params.date_to))
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions?${searchParams.toString()}`)
}

export async function createTrainingSessionApi(
  data: Schemas['TrainingSessionCreate'],
): Promise<Schemas['DataResponse_TrainingSessionResponse_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTrainingSessionApi(
  id: string,
  data: Schemas['TrainingSessionUpdate'],
): Promise<Schemas['DataResponse_TrainingSessionResponse_']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingSessionApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions/${id}`, {
    method: 'DELETE',
  })
}

export async function updateTrainingSessionStatusApi(id: string, status: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

export async function fetchTrainingSessionByIdApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions/${id}`)
}

export async function sendTrainingSessionSelectTasksApi(id: string): Promise<Schemas['AsyncJobAcceptedResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions/${id}/send-select-tasks`, {
    method: 'POST',
  })
}

export async function fetchTrainingSessionSelectTasksApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-sessions/${id}/select-tasks`)
}

export async function fetchTrainingSelectTasks(sessionId?: string) {
  const url = sessionId
    ? `${getApiBaseUrl()}/api/v1/hr/training-sessions/${sessionId}/select-tasks`
    : `${getApiBaseUrl()}/api/v1/hr/training-select-tasks`
  return apiFetch(url)
}

export async function fetchTrainingSelectTask(token: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-select-tasks/${token}`)
}

export async function fetchSopCatalog(params?: Record<string, unknown>) {
  const sp = new URLSearchParams()
  if (params?.department) sp.set('department', String(params.department))
  if (params?.category) sp.set('category', String(params.category))
  if (params?.keyword) sp.set('keyword', String(params.keyword))
  if (params?.page) sp.set('page', String(params.page))
  if (params?.page_size) sp.set('page_size', String(params.page_size))
  const qs = sp.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/sop-catalog${qs ? `?${qs}` : ''}`)
}

export async function sendTrainingSelectTaskApi(data: Schemas['TrainingSelectTaskCreate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-select-tasks/send`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function savePrejobTemplateApi(data: Schemas['PrejobTemplateCreate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/prejob-training-templates`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function generatePrejobTrainingPlanApi(
  employeeId: string,
  factory: string,
  body: Schemas['PrejobTemplateItem'][] | null,
): Promise<Blob> {
  return apiFetchBlob(
    `${getApiBaseUrl()}/api/v1/hr/employees/${employeeId}/prejob-training-plan?factory=${factory}`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    }
  )
}

export async function submitTrainingSelectTaskApi(token: string, data: Schemas['TrainingSelectTaskSubmit']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-select-tasks/${token}/submit`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createTrainingTeamApi(data: Schemas['TrainingTeamCreate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-teams`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTrainingTeamApi(id: string, data: Schemas['TrainingTeamUpdate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-teams/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingTeamApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-teams/${id}`, {
    method: 'DELETE',
  })
}

export async function upsertTrainingSpecialistApi(data: Schemas['TrainingSpecialistCreate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-specialists`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingSpecialistApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/training-specialists/${id}`, {
    method: 'DELETE',
  })
}

// ── 人员流动分析（后台任务）──

export async function submitTurnoverAnalysisJobApi(): Promise<Schemas['AsyncJobAcceptedResponse']> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/turnover-analysis`, {
    method: 'POST',
  })
}

// ── 员工档案（飞书通讯录只读镜像，ticket #198）──

export async function fetchEmployeeProfilesApi(params?: {
  department_id?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<EmployeeProfileListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department_id) searchParams.set('department_id', params.department_id)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/people?${searchParams.toString()}`)
}

export async function fetchEmployeeProfileDetailApi(identifier: string): Promise<EmployeeProfileDetailResponse> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/people/${encodeURIComponent(identifier)}`)
}

export async function fetchEmployeeDepartmentsApi(): Promise<OrgDepartmentTreeResponse> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/hr/people/departments`)
}
