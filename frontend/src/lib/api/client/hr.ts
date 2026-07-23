import {
  EmployeeListResponse,
  EmployeeResponse,
  DepartmentListResponse,
  TeamListResponse,
  OffboardingRecordListResponse,
  OnboardingRecordListResponse,
  DepartureRecordListResponse,
  SyncStatusResponse,
  TrainingPlanListResponse,
  TrainingPlanResponse,
  TrainingPlanSopListResponse,
  TrainingPlanSopResponse,
  TrainingRecordListResponse,
  TrainingRecordResponse,
  TrainingAssessmentListResponse,
  TrainingAssessmentResponse,
  TrainingApprovalListResponse,
  TrainingApprovalResponse,
  TurnoverAnalysisResponse,
  TrainingLedgerListResponse,
  TrainingLedgerPageListResponse,
  AnnualTrainingPlanListResponse,
  AnnualTrainingPlanItemListResponse,
  SopCatalogListResponse,
  GenericDataResponse,
  GenericDataListResponse,
  PrejobTemplateResponse,
} from '@/types/hr'

const API_BASE = '/api/v1'

export async function fetchEmployees(
  params?: {
    department?: string
    status?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<EmployeeListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/employees?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取员工列表失败')
  return res.json()
}

export async function fetchEmployeeById(id: string): Promise<EmployeeResponse> {
  const res = await fetch(`${API_BASE}/hr/employees/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取员工详情失败')
  return res.json()
}

export async function fetchEmployeeByNumber(employeeNumber: string): Promise<EmployeeResponse> {
  const res = await fetch(`${API_BASE}/hr/employees/by-number/${employeeNumber}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取员工详情失败')
  return res.json()
}

export async function fetchDepartments(
  params?: {
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartmentListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))

  const res = await fetch(`${API_BASE}/hr/departments?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取部门列表失败')
  return res.json()
}

export async function fetchTeams(
  params?: {
    department_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TeamListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department_id) searchParams.set('department_id', params.department_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))

  const res = await fetch(`${API_BASE}/hr/teams?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取班组列表失败')
  return res.json()
}

export async function fetchOffboardingRecords(
  params?: {
    employee_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<OffboardingRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.employee_id) searchParams.set('employee_id', params.employee_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/offboarding-records?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取离职记录失败')
  return res.json()
}

export async function fetchOnboardingRecords(
  params?: {
    employee_id?: string
    department?: string
    position?: string
    is_employed?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<OnboardingRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.employee_id) searchParams.set('employee_id', params.employee_id)
  if (params?.department) searchParams.set('department', params.department)
  if (params?.position) searchParams.set('position', params.position)
  if (params?.is_employed) searchParams.set('is_employed', params.is_employed)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/onboarding-records?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取入职记录失败')
  return res.json()
}

export async function fetchDepartureRecords(
  params?: {
    department?: string
    offboarding_type?: string
    keyword?: string
    sort_by?: string
    sort_order?: string
    page?: number
    page_size?: number
  }
): Promise<DepartureRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.offboarding_type) searchParams.set('offboarding_type', params.offboarding_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.sort_by) searchParams.set('sort_by', params.sort_by)
  if (params?.sort_order) searchParams.set('sort_order', params.sort_order)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/departure-records?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取离职台账记录失败')
  return res.json()
}

// ─── Feishu Sync APIs ───

export async function fetchSyncStatus(): Promise<SyncStatusResponse> {
  const res = await fetch(`${API_BASE}/hr/employees/sync-status`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取同步状态失败')
  return res.json()
}

export async function fetchTrainingPlans(
  params?: {
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TrainingPlanListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/training-plans?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训计划列表失败')
  return res.json()
}

export async function fetchTrainingPlanById(id: string): Promise<TrainingPlanResponse> {
  const res = await fetch(`${API_BASE}/hr/training-plans/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训计划详情失败')
  return res.json()
}

export async function fetchTrainingPlanSops(
  params?: {
    plan_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TrainingPlanSopListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.plan_id) searchParams.set('plan_id', params.plan_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/training-plan-sops?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训计划SOP列表失败')
  return res.json()
}

export async function fetchTrainingPlanSopById(id: string): Promise<TrainingPlanSopResponse> {
  const res = await fetch(`${API_BASE}/hr/training-plan-sops/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训计划SOP详情失败')
  return res.json()
}

export async function fetchTrainingRecords(
  params?: {
    plan_id?: string
    employee_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TrainingRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.plan_id) searchParams.set('plan_id', params.plan_id)
  if (params?.employee_id) searchParams.set('employee_id', params.employee_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/training-records?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训记录列表失败')
  return res.json()
}

export async function fetchTrainingRecordById(id: string): Promise<TrainingRecordResponse> {
  const res = await fetch(`${API_BASE}/hr/training-records/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训记录详情失败')
  return res.json()
}

export async function fetchTrainingAssessments(
  params?: {
    record_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TrainingAssessmentListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.record_id) searchParams.set('record_id', params.record_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/training-assessments?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训考核列表失败')
  return res.json()
}

export async function fetchTrainingAssessmentById(id: string): Promise<TrainingAssessmentResponse> {
  const res = await fetch(`${API_BASE}/hr/training-assessments/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训考核详情失败')
  return res.json()
}

export async function fetchTrainingApprovals(
  params?: {
    record_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TrainingApprovalListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.record_id) searchParams.set('record_id', params.record_id)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  try {
    const res = await fetch(`${API_BASE}/hr/training-approvals?${searchParams.toString()}`, {
      cache: 'no-store',
    })
    if (!res.ok) throw new Error('获取培训审批列表失败')
    return res.json()
  } catch {
    return {
      code: 500,
      message: '服务暂不可用',
      data: [],
      meta: { page: params?.page || 1, page_size: params?.page_size || 20, total: 0 },
    }
  }
}

export async function fetchTrainingApprovalById(id: string): Promise<TrainingApprovalResponse> {
  const res = await fetch(`${API_BASE}/hr/training-approvals/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训审批详情失败')
  return res.json()
}

export { fetchTrainingPlanSops as fetchTrainingSops }

export async function fetchTurnoverAnalysis(): Promise<TurnoverAnalysisResponse> {
  const res = await fetch(`${API_BASE}/hr/turnover-analysis`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取人员流动分析失败')
  return res.json()
}

export async function fetchOnboardingTrainingRecord(
  employeeId: string,
  employeeName: string
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/hr/employees/${employeeId}/onboarding-training-record`,
    { cache: 'no-store' }
  )
  if (!res.ok) throw new Error('生成培训记录失败')
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `7.3新员工入职培训记录_${employeeName}.docx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export async function fetchPrejobTrainingPlan(
  employeeId: string,
  employeeName: string
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/hr/employees/${employeeId}/prejob-training-plan`,
    { cache: 'no-store' }
  )
  if (!res.ok) throw new Error('生成岗前培训计划失败')
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `7.4岗前培训计划_${employeeName}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export async function fetchOnboardingEvaluationByEmployeeId(
  employeeId: string,
  employeeName: string
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/hr/employees/${employeeId}/onboarding-evaluation`,
    { cache: 'no-store' }
  )
  if (!res.ok) throw new Error('生成员工上岗评估表失败')
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `员工上岗评估表_${employeeName}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

// ─── TrainingLedger APIs ───

export async function fetchTrainingLedgers(
  params?: {
    employee_number?: string
    date_from?: string
    date_to?: string
    page?: number
    page_size?: number
  }
): Promise<TrainingLedgerListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.employee_number) searchParams.set('employee_number', params.employee_number)
  if (params?.date_from) searchParams.set('date_from', params.date_from)
  if (params?.date_to) searchParams.set('date_to', params.date_to)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))

  const res = await fetch(`${API_BASE}/hr/training-ledgers?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训台账列表失败')
  return res.json()
}

// ─── TrainingLedgerPage APIs ───

export async function fetchTrainingLedgerPages(): Promise<TrainingLedgerPageListResponse> {
  const res = await fetch(`${API_BASE}/hr/training-ledgers/pages`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训台账页面列表失败')
  return res.json()
}

export async function exportTrainingLedger(employeeNumber: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/hr/training-ledgers/export?employee_number=${encodeURIComponent(employeeNumber)}`,
    { cache: 'no-store' }
  )
  if (!res.ok) throw new Error('导出培训台账失败')
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const disposition = res.headers.get('content-disposition')
  const filenameMatch = disposition?.match(/filename\*=utf-8''(.+)/)
  a.download = filenameMatch ? decodeURIComponent(filenameMatch[1]) : '培训台账.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

// ─── AnnualTrainingPlan APIs ───

export async function fetchAnnualTrainingPlans(
  params?: {
    year?: number
    department?: string
    page?: number
    page_size?: number
  }
): Promise<AnnualTrainingPlanListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.year) searchParams.set('year', String(params.year))
  if (params?.department) searchParams.set('department', params.department)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))

  const res = await fetch(`${API_BASE}/hr/annual-training-plans?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取年度培训计划列表失败')
  return res.json()
}

// ─── New Factory APIs ───

export async function fetchNewEmployees(
  params?: {
    department?: string
    status?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<EmployeeListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/new/employees?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取新厂员工列表失败')
  return res.json()
}

export async function fetchNewDepartments(
  params?: {
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartmentListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 100))

  const res = await fetch(`${API_BASE}/hr/new/departments?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取新厂部门列表失败')
  return res.json()
}

export async function fetchNewOnboardingRecords(
  params?: {
    department?: string
    position?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<OnboardingRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.position) searchParams.set('position', params.position)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/new/onboarding-records?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取新厂入职台账列表失败')
  return res.json()
}

export async function fetchNewDepartureRecords(
  params?: {
    department?: string
    offboarding_type?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartureRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.offboarding_type) searchParams.set('offboarding_type', params.offboarding_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/new/departure-records?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取新厂离职台账列表失败')
  return res.json()
}

export async function fetchNewOffboardingRecords(
  params?: {
    department?: string
    offboarding_type?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartureRecordListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.offboarding_type) searchParams.set('offboarding_type', params.offboarding_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`${API_BASE}/hr/new/offboarding-records?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取新厂离职管理列表失败')
  return res.json()
}

export async function fetchAnnualTrainingPlanById(id: string): Promise<TrainingPlanResponse> {
  const res = await fetch(`${API_BASE}/hr/annual-training-plans/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取年度培训计划详情失败')
  return res.json()
}

export async function fetchPlanItems(id: string): Promise<AnnualTrainingPlanItemListResponse> {
  const res = await fetch(`${API_BASE}/hr/annual-training-plans/${id}/items`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取年度计划明细失败')
  return res.json()
}

// ─── 招聘候选人（待后端实现）───

export async function fetchCandidates(params: Record<string, any> = {}): Promise<{ data: any[]; meta?: { total: number } }> {
  // TODO: backend candidate API not yet implemented
  return { data: [], meta: { total: 0 } }
}

// ─── SOP Catalog APIs ───

export async function fetchSopCatalog(params?: {
  department?: string; category?: string; keyword?: string; page?: number; page_size?: number
}): Promise<SopCatalogListResponse> {
  const sp = new URLSearchParams()
  if (params?.department) sp.set('department', params.department)
  if (params?.category) sp.set('category', params.category)
  if (params?.keyword) sp.set('keyword', params.keyword)
  sp.set('page', String(params?.page || 1))
  sp.set('page_size', String(params?.page_size || 50))
  const res = await fetch(`${API_BASE}/hr/sop-catalog?${sp.toString()}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('获取SOP目录失败')
  return res.json()
}

export async function fetchCandidateById(id: string): Promise<GenericDataResponse> {
  // TODO: backend candidate API not yet implemented
  return { code: 404, message: '招聘功能暂未实现', data: null }
}

// ─── Training Select Task APIs ───

export async function fetchTrainingSelectTaskResult(token: string): Promise<GenericDataResponse> {
  const res = await fetch(`${API_BASE}/hr/training-select-tasks/${token}/result`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取选择结果失败')
  return res.json()
}

export async function fetchTrainingSelectTasks(sessionId?: string): Promise<GenericDataListResponse> {
  const res = await fetch(`${API_BASE}/hr/training-select-tasks`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取选择任务列表失败')
  return res.json()
}

// ─── Prejob Template APIs ───

export async function fetchPrejobTemplate(
  department: string,
  factory: 'old' | 'new' = 'old'
): Promise<PrejobTemplateResponse> {
  const params = new URLSearchParams({ department, factory })
  const res = await fetch(
    `${API_BASE}/hr/prejob-training-templates?${params.toString()}`,
    { cache: 'no-store' }
  )
  if (!res.ok) throw new Error('获取岗前培训计划模板失败')
  return res.json()
}

// ─── Additional Training Select Task APIs ───

export async function fetchTrainingSelectTask(token: string): Promise<GenericDataResponse> {
  const res = await fetch(`${API_BASE}/hr/training-select-tasks/${token}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取选择任务失败')
  return res.json()
}

export async function fetchTrainingSessionSelectTasks(sessionId: string): Promise<GenericDataListResponse> {
  const res = await fetch(`${API_BASE}/hr/training-sessions/${sessionId}/select-tasks`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训会话选择任务失败')
  return res.json()
}

// ─── Training Team & Specialist APIs ───

export async function fetchTrainingTeams(factory?: string): Promise<GenericDataListResponse> {
  const res = await fetch(`${API_BASE}/hr/training-teams`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训团队列表失败')
  return res.json()
}

export async function fetchTrainingSpecialists(factory?: string): Promise<GenericDataListResponse> {
  const res = await fetch(`${API_BASE}/hr/training-specialists`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取培训专家列表失败')
  return res.json()
}
