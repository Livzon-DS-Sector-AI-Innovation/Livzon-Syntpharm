import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'

async function apiFetchFormData(url: string, body: FormData): Promise<any> {
  const res = await fetch(url, {
    method: 'POST',
    body,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.message || '上传失败')
  }
  return res.json()
}

async function apiFetchBlob(url: string, options?: RequestInit): Promise<Blob> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
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
  if (params?.department) searchParams.set('department', params.department)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees?${searchParams.toString()}`)
}

export async function createEmployeeApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEmployeeApi(id: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteEmployeeApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees/${id}`, {
    method: 'DELETE',
  })
}

export async function uploadEmployeesApi(formData: FormData) {
  return apiFetchFormData(`${API_BASE_URL}/api/v1/hr/employees/upload`, formData)
}

export async function syncFromFeishuApi() {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees/sync-from-feishu`, {
    method: 'POST',
  })
}

export async function syncToFeishuApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees/${id}/sync-to-feishu`, {
    method: 'POST',
  })
}

export async function fetchDepartmentsApi(params?: {
  keyword?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/departments?${searchParams.toString()}`)
}

export async function createDepartmentApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/departments`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDepartmentApi(id: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/departments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDepartmentApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/departments/${id}`, {
    method: 'DELETE',
  })
}

export async function fetchTeamsApi(params?: {
  department_id?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.department_id) searchParams.set('department_id', params.department_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/teams?${searchParams.toString()}`)
}

export async function createTeamApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/teams`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTeamApi(id: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/teams/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTeamApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/teams/${id}`, {
    method: 'DELETE',
  })
}

export async function fetchOffboardingRecordsApi(params?: {
  employee_id?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.employee_id) searchParams.set('employee_id', params.employee_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/offboarding-records?${searchParams.toString()}`)
}

export async function createOffboardingRecordApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/offboarding-records`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateOffboardingRecordApi(id: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/offboarding-records/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteOffboardingRecordApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/offboarding-records/${id}`, {
    method: 'DELETE',
  })
}

export async function createAnnualTrainingPlanApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/annual-training-plans`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAnnualTrainingPlanApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/annual-training-plans/${id}`, {
    method: 'DELETE',
  })
}

export async function deleteAnnualPlanItemApi(planId: string, itemId: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/annual-training-plans/${planId}/items/${itemId}`, {
    method: 'DELETE',
  })
}

export async function batchUpdatePlanItemsApi(planId: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/annual-training-plans/${planId}/items`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function fetchOnboardingRecordsApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.employee_id) searchParams.set('employee_id', params.employee_id)
  if (params?.department) searchParams.set('department', params.department)
  if (params?.position) searchParams.set('position', params.position)
  if (params?.is_employed) searchParams.set('is_employed', params.is_employed)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/onboarding-records?${searchParams.toString()}`)
}

export async function fetchDepartureRecordsApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.offboarding_type) searchParams.set('offboarding_type', params.offboarding_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/departure-records?${searchParams.toString()}`)
}

export async function fetchEmployeeByIdApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees/${id}`)
}

export async function fetchCandidateByIdApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/candidates/${id}`)
}

export async function fetchCandidatesApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.status) searchParams.set('status', params.status)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/candidates?${searchParams.toString()}`)
}

export async function fetchNewEmployeesApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/new/employees?${searchParams.toString()}`)
}

export async function fetchNewDepartmentsApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/new/departments?${searchParams.toString()}`)
}

export async function fetchNewOnboardingRecordsApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.position) searchParams.set('position', params.position)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/new/onboarding-records?${searchParams.toString()}`)
}

export async function fetchNewDepartureRecordsApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.offboarding_type) searchParams.set('offboarding_type', params.offboarding_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/new/departure-records?${searchParams.toString()}`)
}

export async function fetchNewOffboardingRecordsApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.offboarding_type) searchParams.set('offboarding_type', params.offboarding_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/new/offboarding-records?${searchParams.toString()}`)
}

export async function fetchAnnualTrainingPlanByIdApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/annual-training-plans/${id}`)
}

export async function fetchPlanItemsApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/annual-training-plans/${id}/items`)
}

export async function fetchTrainingRecordsApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.employee_id) searchParams.set('employee_id', params.employee_id)
  if (params?.training_type) searchParams.set('training_type', params.training_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-records?${searchParams.toString()}`)
}

export async function fetchTrainingPlansApi(params?: any) {
  const searchParams = new URLSearchParams()
  if (params?.year) searchParams.set('year', params.year)
  if (params?.department) searchParams.set('department', params.department)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-plans?${searchParams.toString()}`)
}

export async function fetchEmployeeByNumberApi(employeeNumber: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/employees/by-number/${employeeNumber}`)
}

export async function syncTrainingSpecialistsFeishuOpenIdsApi() {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-specialists/sync-feishu-openids`, {
    method: 'POST',
  })
}

export async function syncOnboardingFromFeishuApi() {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/onboarding-records/sync-from-feishu`, {
    method: 'POST',
  })
}

export async function syncDepartureFromFeishuApi() {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/departure-records/sync-from-feishu`, {
    method: 'POST',
  })
}

export async function createTrainingLedgerApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-ledgers`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTrainingLedgerApi(id: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-ledgers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingLedgerApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-ledgers/${id}`, {
    method: 'DELETE',
  })
}

export async function createTrainingLedgerPageApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-ledgers/pages`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function sendTrainingNotificationApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-notifications/send`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateTrainingSignInSheetApi(data: any) {
  return apiFetchBlob(`${API_BASE_URL}/api/v1/hr/training/sign-in-sheet/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateTrainingNotificationApi(data: any) {
  return apiFetchBlob(`${API_BASE_URL}/api/v1/hr/training/notification/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateTrainingEvaluationApi(data: any) {
  return apiFetchBlob(`${API_BASE_URL}/api/v1/hr/training/evaluation/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateOnboardingEvaluationApi(data: any) {
  return apiFetchBlob(`${API_BASE_URL}/api/v1/hr/onboarding/evaluation/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createOnboardingTrainingRecordApi(employeeNumber: string, data: any) {
  return apiFetchBlob(`${API_BASE_URL}/api/v1/hr/employees/${employeeNumber}/onboarding-training-record`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createDepartureRecordApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/departure-records`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function uploadAnnualTrainingPlanApi(formData: FormData) {
  return apiFetchFormData(`${API_BASE_URL}/api/v1/hr/annual-training-plans/upload`, formData)
}

export async function uploadTrainersApi(formData: FormData) {
  return apiFetchFormData(`${API_BASE_URL}/api/v1/hr/trainers/upload`, formData)
}

export async function uploadSopCatalogApi(formData: FormData) {
  return apiFetchFormData(`${API_BASE_URL}/api/v1/hr/sop-catalog/upload`, formData)
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
  if (params?.department) searchParams.set('department', params.department)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.date_from) searchParams.set('date_from', params.date_from)
  if (params?.date_to) searchParams.set('date_to', params.date_to)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions?${searchParams.toString()}`)
}

export async function createTrainingSessionApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTrainingSessionApi(id: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingSessionApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions/${id}`, {
    method: 'DELETE',
  })
}

export async function updateTrainingSessionStatusApi(id: string, status: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

export async function fetchTrainingSessionByIdApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions/${id}`)
}

export async function sendTrainingSessionSelectTasksApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions/${id}/send-select-tasks`, {
    method: 'POST',
  })
}

export async function fetchTrainingSessionSelectTasksApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-sessions/${id}/select-tasks`)
}

export async function fetchTrainingSelectTasks(sessionId?: string) {
  const url = sessionId
    ? `${API_BASE_URL}/api/v1/hr/training-sessions/${sessionId}/select-tasks`
    : `${API_BASE_URL}/api/v1/hr/training-select-tasks`
  return apiFetch(url)
}

export async function fetchTrainingSelectTask(token: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-select-tasks/${token}`)
}

export async function fetchSopCatalog(params?: any) {
  const sp = new URLSearchParams()
  if (params?.department) sp.set('department', params.department)
  if (params?.category) sp.set('category', params.category)
  if (params?.keyword) sp.set('keyword', params.keyword)
  if (params?.page) sp.set('page', String(params.page))
  if (params?.page_size) sp.set('page_size', String(params.page_size))
  const qs = sp.toString()
  return apiFetch(`${API_BASE_URL}/api/v1/hr/sop-catalog${qs ? `?${qs}` : ''}`)
}

export async function sendTrainingSelectTaskApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-select-tasks/send`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function savePrejobTemplateApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/prejob-training-templates`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function generatePrejobTrainingPlanApi(employeeId: string, params: any, factory: string, body: any) {
  return apiFetchBlob(
    `${API_BASE_URL}/api/v1/hr/employees/${employeeId}/prejob-training-plan?factory=${factory}`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    }
  )
}

export async function submitTrainingSelectTaskApi(token: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-select-tasks/${token}/submit`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createTrainingTeamApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-teams`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTrainingTeamApi(id: string, data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-teams/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingTeamApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-teams/${id}`, {
    method: 'DELETE',
  })
}

export async function upsertTrainingSpecialistApi(data: any) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-specialists`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteTrainingSpecialistApi(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/hr/training-specialists/${id}`, {
    method: 'DELETE',
  })
}