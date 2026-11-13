'use server'

import { z } from 'zod'
import {parse} from '@/lib/validation/schemas'

import { revalidatePath } from 'next/cache'
import {
  EmployeeCreateInput,
  EmployeeUpdateInput,
  EmployeeListResponse,
  DepartmentListResponse,
  TrainingSessionCreateInput,
  TrainingSessionUpdateInput,
  TrainingSessionListResponse,
  TrainingSessionResponse,
  SelectTask,
  Employee,
  OnboardingRecordListResponse,
  OnboardingRecordApiResponse,
  OnboardingRecordCreateInput,
  OnboardingRecordUpdateInput,
  DepartureRecordListResponse,
  DepartureRecordApiResponse,
  DepartureRecordCreateInput,
  DepartureRecordUpdateInput,
  DepartureRecordDeleteResponse,
  CandidateListParams,
  CandidateListResponse,
  Candidate,
  CandidateResponse,
  AnnualTrainingPlan,
  AnnualTrainingPlanListResponse,
  AnnualTrainingPlanItem,
  TrainingLedgerListResponse,
  TrainingSession,
  TrainingTeam,
  TrainingSpecialist,
  SyncFromFeishuResponse,
  SyncToFeishuResponse,
  DeleteResponse,
  PrejobTemplate,
  EmployeeResponse,
  TrainingPlanResponse,
  ImportCounts,
  SyncOpenIdsResult,
  OrgDepartmentTreeResponse,
  OrgSyncStatusResponse,
  OrgSyncTriggerResponse,
  EmployeeProfileListResponse,
  EmployeeProfileDetailResponse,
} from '@/types/hr'

import type { ApiResponse, MessageResponse } from '@/types/common'

import {
  fetchEmployeesApi,
  createEmployeeApi,
  updateEmployeeApi,
  deleteEmployeeApi,
  uploadEmployeesApi,
  syncFromFeishuApi,
  syncToFeishuApi,
  fetchDepartmentsApi,
  fetchOrgDepartmentsApi,
  fetchOrgSyncStatusApi,
  triggerOrgSyncApi,
  createAnnualTrainingPlanApi,
  deleteAnnualTrainingPlanApi,
  deleteAnnualPlanItemApi,
  batchUpdatePlanItemsApi,
  fetchOnboardingRecordsApi,
  fetchDepartureRecordsApi,
  fetchEmployeeByIdApi,
  fetchCandidateByIdApi,
  fetchCandidatesApi,
  fetchAnnualTrainingPlanByIdApi,
  fetchPlanItemsApi,
  fetchTrainingRecordsApi,
  fetchTrainingPlansApi,
  fetchEmployeeByNumberApi,
  syncTrainingSpecialistsFeishuOpenIdsApi,
  createOnboardingRecordApi,
  updateOnboardingRecordApi,
  deleteOnboardingRecordApi,
  createTrainingLedgerApi,
  updateTrainingLedgerApi,
  deleteTrainingLedgerApi,
  createTrainingLedgerPageApi,
  sendTrainingNotificationApi,
  generateTrainingSignInSheetApi,
  generateTrainingNotificationApi,
  generateTrainingEvaluationApi,
  generateOnboardingEvaluationApi,
  createOnboardingTrainingRecordApi,
  createDepartureRecordApi,
  updateDepartureRecordApi,
  deleteDepartureRecordApi,
  uploadAnnualTrainingPlanApi,
  uploadTrainersApi,
  uploadSopCatalogApi,
  fetchTrainingSessionsApi,
  createTrainingSessionApi,
  updateTrainingSessionApi,
  deleteTrainingSessionApi,
  updateTrainingSessionStatusApi,
  fetchTrainingSessionByIdApi,
  sendTrainingSessionSelectTasksApi,
  fetchTrainingSessionSelectTasksApi,
  sendTrainingSelectTaskApi,
  savePrejobTemplateApi,
  generatePrejobTrainingPlanApi,
  submitTrainingSelectTaskApi,
  createTrainingTeamApi,
  updateTrainingTeamApi,
  deleteTrainingTeamApi,
  upsertTrainingSpecialistApi,
  deleteTrainingSpecialistApi,
  fetchEmployeeProfilesApi,
  fetchEmployeeProfileDetailApi,
  fetchEmployeeDepartmentsApi,
} from '@/lib/api/server/hr'


// HR schemas
const _TrainingSignInSheetSchema = z.object({
  training_id: z.string().uuid(),
  trainee_ids: z.array(z.string().uuid()),
})

const _TrainingNotificationSchema = z.object({
  training_id: z.string().uuid(),
  notification_type: z.string(),
  recipients: z.array(z.string().uuid()),
})

const _TrainingEvaluationSchema = z.object({
  training_id: z.string().uuid(),
  employee_id: z.string().uuid(),
  score: z.number().optional(),
  comments: z.string().optional(),
})


// HR schemas for Zod validation


const OnboardingTrainingRecordSchema = z.object({
  training_name: z.string().min(1),
  training_date: z.string(),
  trainer: z.string().optional(),
  duration_hours: z.number().optional(),
})

export async function fetchEmployeesAction(
  params?: {
    department?: string
    status?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<EmployeeListResponse> {
  return fetchEmployeesApi(params) as Promise<EmployeeListResponse>
}

export async function createEmployee(data: EmployeeCreateInput) {
  const res = await createEmployeeApi(data)
  revalidatePath('/hr/profile')
  return res as Employee
}

export async function updateEmployee(id: string, data: EmployeeUpdateInput) {
  const res = await updateEmployeeApi(id, data)
  revalidatePath('/hr/profile')
  return res as Employee
}

export async function deleteEmployee(id: string) {
  const res = await deleteEmployeeApi(id)
  revalidatePath('/hr/profile')
  return res as DeleteResponse
}

export async function uploadEmployeesAction(formData: FormData) {
  const res = await uploadEmployeesApi(formData)
  revalidatePath('/hr/profile')
  return res as ApiResponse<ImportCounts>
}

// ─── Feishu Sync Actions ───

export async function syncFromFeishuAction() {
  const res = await syncFromFeishuApi()
  revalidatePath('/hr/profile')
  return res as SyncFromFeishuResponse
}

export async function syncToFeishuAction(id: string) {
  const res = await syncToFeishuApi(id)
  revalidatePath('/hr/profile')
  return res as SyncToFeishuResponse
}

// ─── Department Actions ───

export async function fetchDepartmentsAction(
  params?: {
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartmentListResponse> {
  return fetchDepartmentsApi(params) as Promise<DepartmentListResponse>
}




// ─── Annual Training Plan Actions ───

export async function createAnnualTrainingPlan(data: { year: number; department: string; status: string }) {
  const res = await createAnnualTrainingPlanApi(data)
  revalidatePath('/hr/training/annual-plan')
  return res as ApiResponse<AnnualTrainingPlan>
}

export async function deleteAnnualTrainingPlan(id: string) {
  const res = await deleteAnnualTrainingPlanApi(id)
  revalidatePath('/hr/training/annual-plan')
  return res as DeleteResponse
}

export async function deleteAnnualPlanItem(planId: string, itemId: string) {
  const res = await deleteAnnualPlanItemApi(planId, itemId)
  revalidatePath('/hr/training/annual-plan')
  return res as DeleteResponse
}

export async function batchUpdatePlanItems(planId: string, data: { items: unknown[] }) {
  const res = await batchUpdatePlanItemsApi(planId, data)
  revalidatePath('/hr/training/annual-plan')
  return res as AnnualTrainingPlanItem[]
}

// ─── STUB: Candidate/Recruitment Actions (not yet implemented) ───

export async function createCandidateAction(_formData: FormData) {
  throw new Error('createCandidateAction: 功能尚未实现')
  return { success: true, message: "功能尚未实现" }
}

export async function parseResumePreviewAction(_formData: FormData) {
  throw new Error('parseResumePreviewAction: 功能尚未实现')
  return { data: { gender: "", school: "", education: "", major: "", match_report: "", recommendation_level: "" } }
}

export async function syncCandidateToFeishuAction(_candidateId: string) {
  throw new Error('syncCandidateToFeishuAction: 功能尚未实现')
  return { success: true, message: "功能尚未实现" }
}

export async function updateCandidateAction(_candidateId: string, _data: unknown) {
  throw new Error('updateCandidateAction: 功能尚未实现')
  return { success: true, message: "功能尚未实现" }
}

export async function updateCandidateRecommendationLevelAction(_candidateId: string, _level: string) {
  throw new Error('updateCandidateRecommendationLevelAction: 功能尚未实现')
  return { success: true, message: "功能尚未实现" }
}

export async function syncCandidatesFromFeishuAction() {
  throw new Error('syncCandidatesFromFeishuAction: 功能尚未实现')
  return { success: true, message: "功能尚未实现" }
}

export async function deleteCandidateAction(_candidateId: string) {
  throw new Error('deleteCandidateAction: 功能尚未实现')
  return { success: true, message: "功能尚未实现" }
}

// ─── Server-side fetch functions (for Server Components) ───

export async function fetchEmployees(
  params?: {
    department?: string
    status?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<EmployeeListResponse> {
  return fetchEmployeesAction(params)
}

export async function fetchOrgDepartments(): Promise<OrgDepartmentTreeResponse> {
  return fetchOrgDepartmentsApi()
}

export async function fetchOrgSyncStatus(): Promise<OrgSyncStatusResponse> {
  return fetchOrgSyncStatusApi()
}

export async function triggerOrgSync(): Promise<OrgSyncTriggerResponse> {
  const result = await triggerOrgSyncApi()
  revalidatePath('/hr/departments')
  return result
}

export async function fetchDepartments(
  params?: {
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartmentListResponse> {
  return fetchDepartmentsAction(params)
}

export async function fetchOnboardingRecords(params?: {
  department?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<OnboardingRecordListResponse> {
  return fetchOnboardingRecordsApi(params) as Promise<OnboardingRecordListResponse>
}

// ─── 入职台账 Actions（2026 手工台账，ticket #199）──

export async function createOnboardingRecord(data: OnboardingRecordCreateInput) {
  const res = await createOnboardingRecordApi(data)
  revalidatePath('/hr/onboarding')
  return res as OnboardingRecordApiResponse
}

export async function updateOnboardingRecord(id: string, data: OnboardingRecordUpdateInput) {
  const res = await updateOnboardingRecordApi(id, data)
  revalidatePath('/hr/onboarding')
  return res as OnboardingRecordApiResponse
}

export async function deleteOnboardingRecord(id: string) {
  const res = await deleteOnboardingRecordApi(id)
  revalidatePath('/hr/onboarding')
  return res as DeleteResponse
}

export async function fetchDepartureRecords(
  params?: {
    department?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartureRecordListResponse> {
  return fetchDepartureRecordsApi(params) as Promise<DepartureRecordListResponse>
}

// ─── 离职台账 Actions（2026 手工台账，ticket #200）──

export async function createDepartureRecord(data: DepartureRecordCreateInput) {
  const res = await createDepartureRecordApi(data)
  revalidatePath('/hr/offboarding')
  return res as DepartureRecordApiResponse
}

export async function updateDepartureRecord(id: string, data: DepartureRecordUpdateInput) {
  const res = await updateDepartureRecordApi(id, data)
  revalidatePath('/hr/offboarding')
  return res as DepartureRecordApiResponse
}

export async function deleteDepartureRecord(id: string) {
  const res = await deleteDepartureRecordApi(id)
  revalidatePath('/hr/offboarding')
  return res as DepartureRecordDeleteResponse
}

export async function fetchEmployeeById(id: string): Promise<EmployeeResponse> {
  return fetchEmployeeByIdApi(id) as Promise<EmployeeResponse>
}

export async function fetchCandidateById(id: string): Promise<CandidateResponse> {
  return fetchCandidateByIdApi(id) as Promise<CandidateResponse>
}

export async function fetchCandidates(params: CandidateListParams = {}): Promise<CandidateListResponse> {
  return fetchCandidatesApi(params).catch(() => ({ code: 0, message: '', data: [] as Candidate[], meta: { page: 1, page_size: 20, total: 0 } }) as CandidateListResponse)
}

export async function fetchAnnualTrainingPlanById(id: string): Promise<TrainingPlanResponse> {
  return fetchAnnualTrainingPlanByIdApi(id) as Promise<TrainingPlanResponse>
}

export async function fetchPlanItems(id: string): Promise<ApiResponse<AnnualTrainingPlanItem[]>> {
  return fetchPlanItemsApi(id) as Promise<ApiResponse<AnnualTrainingPlanItem[]>>
}

export async function fetchTrainingRecords(params: Record<string, unknown> = {}): Promise<TrainingLedgerListResponse> {
  return fetchTrainingRecordsApi(params) as Promise<TrainingLedgerListResponse>
}

export async function fetchTrainingPlans(params: Record<string, unknown> = {}): Promise<AnnualTrainingPlanListResponse> {
  return fetchTrainingPlansApi(params) as Promise<AnnualTrainingPlanListResponse>
}

export async function fetchEmployeeByNumber(employeeNumber: string): Promise<EmployeeResponse> {
  return fetchEmployeeByNumberApi(employeeNumber) as Promise<EmployeeResponse>
}

export async function syncTrainingSpecialistsFeishuOpenIds() {
  const res = await syncTrainingSpecialistsFeishuOpenIdsApi()
  revalidatePath('/hr/training/specialists')
  return res as ApiResponse<SyncOpenIdsResult>
}

// ─── 培训台账 Actions ───

import type {
  TrainingLedgerCreateInput,
  TrainingLedgerUpdateInput,
} from '@/types/hr'

export async function createTrainingLedger(data: TrainingLedgerCreateInput) {
  const json = await createTrainingLedgerApi(data)
  revalidatePath('/hr/training-ledger')
  return json
}

export async function updateTrainingLedger(id: string, data: TrainingLedgerUpdateInput) {
  const json = await updateTrainingLedgerApi(id, data)
  revalidatePath('/hr/training-ledger')
  return json
}

export async function deleteTrainingLedger(id: string) {
  const json = await deleteTrainingLedgerApi(id)
  revalidatePath('/hr/training-ledger')
  return json
}

export async function createTrainingLedgerPage(data: { employee_number: string; employee_name: string; ledger_type?: string }) {
  const json = await createTrainingLedgerPageApi(data)
  revalidatePath('/hr/training-ledger')
  return json
}

// ─── 培训通知 Actions ───

import type { TrainingNotifyData } from '@/types/hr'

export async function sendTrainingNotification(data: TrainingNotifyData) {
  return sendTrainingNotificationApi(data)
}

// ─── Document Generation Actions (moved from client API) ───

export async function generateTrainingSignInSheet(data: unknown): Promise<Blob> {
  const blob = await generateTrainingSignInSheetApi(data)
  revalidatePath('/hr')
  return blob
}

export async function generateTrainingNotification(data: unknown): Promise<Blob> {
  const blob = await generateTrainingNotificationApi(data)
  revalidatePath('/hr')
  return blob
}

export async function generateTrainingEvaluation(data: unknown): Promise<Blob> {
  const blob = await generateTrainingEvaluationApi(data)
  revalidatePath('/hr')
  return blob
}

export async function generateOnboardingEvaluation(data: unknown): Promise<Blob> {
  const blob = await generateOnboardingEvaluationApi(data)
  revalidatePath('/hr')
  return blob
}

// ─── Additional HR Actions (moved from components) ───

export async function createOnboardingTrainingRecord(employeeNumber: string, data: unknown) {
  const _validated = parse(OnboardingTrainingRecordSchema, data)
  const blob = await createOnboardingTrainingRecordApi(employeeNumber, data)
  revalidatePath('/hr')
  return blob
}

export async function uploadAnnualTrainingPlan(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await uploadAnnualTrainingPlanApi(fd)
  revalidatePath('/hr')
  return res as MessageResponse
}

export async function uploadTrainers(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await uploadTrainersApi(fd)
  revalidatePath('/hr/training/trainers')
  return res as ApiResponse<ImportCounts>
}

export async function uploadSopCatalog(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await uploadSopCatalogApi(fd)
  revalidatePath('/hr/training/sop-catalog')
  return res as ApiResponse<ImportCounts>
}

// ─── TrainingSession Actions ───

export async function fetchTrainingSessionsAction(
  params?: {
    department?: string
    keyword?: string
    status?: string
    date_from?: string
    date_to?: string
    page?: number
    page_size?: number
  }
): Promise<TrainingSessionListResponse> {
  return fetchTrainingSessionsApi(params) as Promise<TrainingSessionListResponse>
}

export async function createTrainingSession(data: TrainingSessionCreateInput) {
  const res = await createTrainingSessionApi(data)
  revalidatePath('/hr/training/records')
  return res as ApiResponse<TrainingSession>
}

export async function updateTrainingSession(id: string, data: TrainingSessionUpdateInput) {
  const res = await updateTrainingSessionApi(id, data)
  revalidatePath('/hr/training/records')
  return res as ApiResponse<TrainingSession>
}

export async function deleteTrainingSession(id: string) {
  const res = await deleteTrainingSessionApi(id)
  revalidatePath('/hr/training/records')
  return res as DeleteResponse
}

export async function updateTrainingSessionStatus(id: string, status: string) {
  const res = await updateTrainingSessionStatusApi(id, status)
  revalidatePath('/hr/training/records')
  return res as ApiResponse<TrainingSession>
}

export async function fetchTrainingSessionByIdAction(id: string): Promise<TrainingSessionResponse> {
  return fetchTrainingSessionByIdApi(id) as Promise<TrainingSessionResponse>
}

export async function sendTrainingSessionSelectTasksAction(id: string): Promise<ApiResponse<SelectTask[]>> {
  const res = await sendTrainingSessionSelectTasksApi(id)
  revalidatePath('/hr/training/records')
  return res as ApiResponse<SelectTask[]>
}

export async function fetchTrainingSessionSelectTasksAction(id: string): Promise<ApiResponse<SelectTask[]>> {
  return fetchTrainingSessionSelectTasksApi(id) as Promise<ApiResponse<SelectTask[]>>
}

export async function sendTrainingSelectTaskAction(data: unknown) {
  const res = await sendTrainingSelectTaskApi(data)
  revalidatePath('/hr/training')
  return res as Record<string, unknown>
}

export async function savePrejobTemplateAction(department: string, factory: 'old' | 'new', items: unknown[]) {
  const res = await savePrejobTemplateApi({ department, factory, items })
  revalidatePath('/hr/training/prejob')
  return res as PrejobTemplate
}

export async function generatePrejobTrainingPlanAction(
  employeeId: string,
  employeeName: string,
  factory: 'old' | 'new' = 'old',
  items?: unknown[]
): Promise<Blob> {
  const blob = await generatePrejobTrainingPlanApi(employeeId, {}, factory, items || [])
  revalidatePath('/hr')
  return blob
}

export async function submitTrainingSelectTaskAction(
  token: string,
  data: { selectedNumbers: string[]; selectedNames: string[] }
) {
  const res = await submitTrainingSelectTaskApi(token, data)
  revalidatePath('/hr/training')
  return res as ApiResponse<Record<string, unknown>>
}

export async function createTrainingTeamAction(data: unknown) {
  const res = await createTrainingTeamApi(data)
  revalidatePath('/hr/training/team')
  return res as TrainingTeam
}

export async function updateTrainingTeamAction(id: string, data: unknown) {
  const res = await updateTrainingTeamApi(id, data)
  revalidatePath('/hr/training/team')
  return res as TrainingTeam
}

export async function deleteTrainingTeamAction(id: string) {
  const res = await deleteTrainingTeamApi(id)
  revalidatePath('/hr/training/team')
  return res as DeleteResponse
}

export async function upsertTrainingSpecialistAction(data: unknown) {
  const res = await upsertTrainingSpecialistApi(data)
  revalidatePath('/hr/training/specialists')
  return res as TrainingSpecialist
}

export async function deleteTrainingSpecialistAction(id: string) {
  const res = await deleteTrainingSpecialistApi(id)
  revalidatePath('/hr/training/specialists')
  return res as DeleteResponse
}

// ── 员工档案（飞书通讯录只读镜像，ticket #198）──

export async function fetchEmployeeProfilesAction(params?: {
  department_id?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<EmployeeProfileListResponse> {
  return fetchEmployeeProfilesApi(params)
}

export async function fetchEmployeeProfileDetailAction(
  identifier: string
): Promise<EmployeeProfileDetailResponse> {
  return fetchEmployeeProfileDetailApi(identifier)
}

export async function fetchEmployeeDepartmentsAction(): Promise<OrgDepartmentTreeResponse> {
  return fetchEmployeeDepartmentsApi()
}
