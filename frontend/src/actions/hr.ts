'use server'

import { z } from 'zod'
import { parse, NonEmptyStringSchema } from '@/lib/validation/schemas'

import { revalidatePath } from 'next/cache'
import {
  EmployeeCreateInput,
  EmployeeUpdateInput,
  EmployeeListResponse,
  DepartmentCreateInput,
  DepartmentUpdateInput,
  DepartmentListResponse,
  TeamCreateInput,
  TeamUpdateInput,
  TeamListResponse,
  OffboardingRecordCreateInput,
  OffboardingRecordUpdateInput,
  OffboardingRecordListResponse,
  TrainingSessionCreateInput,
  TrainingSessionUpdateInput,
  TrainingSessionListResponse,
  TrainingSessionResponse,
  SelectTask,
} from '@/types/hr'

import {
  fetchEmployeesApi,
  createEmployeeApi,
  updateEmployeeApi,
  deleteEmployeeApi,
  uploadEmployeesApi,
  syncFromFeishuApi,
  syncToFeishuApi,
  fetchDepartmentsApi,
  createDepartmentApi,
  updateDepartmentApi,
  deleteDepartmentApi,
  fetchTeamsApi,
  createTeamApi,
  updateTeamApi,
  deleteTeamApi,
  fetchOffboardingRecordsApi,
  createOffboardingRecordApi,
  updateOffboardingRecordApi,
  deleteOffboardingRecordApi,
  createAnnualTrainingPlanApi,
  deleteAnnualTrainingPlanApi,
  deleteAnnualPlanItemApi,
  batchUpdatePlanItemsApi,
  fetchOnboardingRecordsApi,
  fetchDepartureRecordsApi,
  fetchEmployeeByIdApi,
  fetchCandidateByIdApi,
  fetchCandidatesApi,
  fetchNewEmployeesApi,
  fetchNewDepartmentsApi,
  fetchNewOnboardingRecordsApi,
  fetchNewDepartureRecordsApi,
  fetchNewOffboardingRecordsApi,
  fetchAnnualTrainingPlanByIdApi,
  fetchPlanItemsApi,
  fetchTrainingRecordsApi,
  fetchTrainingPlansApi,
  fetchEmployeeByNumberApi,
  syncTrainingSpecialistsFeishuOpenIdsApi,
  syncOnboardingFromFeishuApi,
  syncDepartureFromFeishuApi,
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
} from '@/lib/api/server/hr'


// HR schemas
const TrainingSignInSheetSchema = z.object({
  training_id: z.string().uuid(),
  trainee_ids: z.array(z.string().uuid()),
})

const TrainingNotificationSchema = z.object({
  training_id: z.string().uuid(),
  notification_type: z.string(),
  recipients: z.array(z.string().uuid()),
})

const TrainingEvaluationSchema = z.object({
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

const DepartureRecordSchema = z.object({
  employee_id: z.string().uuid(),
  departure_date: z.string(),
  departure_reason: z.string().optional(),
  handover_notes: z.string().optional(),
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
  return fetchEmployeesApi(params)
}

export async function createEmployee(data: EmployeeCreateInput) {
  const res = await createEmployeeApi(data)
  revalidatePath('/hr/profile')
  return res
}

export async function updateEmployee(id: string, data: EmployeeUpdateInput) {
  const res = await updateEmployeeApi(id, data)
  revalidatePath('/hr/profile')
  return res
}

export async function deleteEmployee(id: string) {
  const res = await deleteEmployeeApi(id)
  revalidatePath('/hr/profile')
  return res
}

export async function uploadEmployeesAction(formData: FormData) {
  const res = await uploadEmployeesApi(formData)
  revalidatePath('/hr/profile')
  return res
}

// ─── Feishu Sync Actions ───

export async function syncFromFeishuAction() {
  const res = await syncFromFeishuApi()
  revalidatePath('/hr/profile')
  return res
}

export async function syncToFeishuAction(id: string) {
  const res = await syncToFeishuApi(id)
  revalidatePath('/hr/profile')
  return res
}

// ─── Department Actions ───

export async function fetchDepartmentsAction(
  params?: {
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartmentListResponse> {
  return fetchDepartmentsApi(params)
}

export async function createDepartment(data: DepartmentCreateInput) {
  const res = await createDepartmentApi(data)
  revalidatePath('/hr/departments')
  return res
}

export async function updateDepartment(id: string, data: DepartmentUpdateInput) {
  const res = await updateDepartmentApi(id, data)
  revalidatePath('/hr/departments')
  return res
}

export async function deleteDepartment(id: string) {
  const res = await deleteDepartmentApi(id)
  revalidatePath('/hr/departments')
  return res
}

// ─── Team Actions ───

export async function fetchTeamsAction(
  params?: {
    department_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TeamListResponse> {
  return fetchTeamsApi(params)
}

export async function createTeam(data: TeamCreateInput) {
  const res = await createTeamApi(data)
  revalidatePath('/hr/departments')
  return res
}

export async function updateTeam(id: string, data: TeamUpdateInput) {
  const res = await updateTeamApi(id, data)
  revalidatePath('/hr/departments')
  return res
}

export async function deleteTeam(id: string) {
  const res = await deleteTeamApi(id)
  revalidatePath('/hr/departments')
  return res
}

// ─── OffboardingRecord Actions ───

export async function fetchOffboardingRecordsAction(
  params?: {
    employee_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<OffboardingRecordListResponse> {
  return fetchOffboardingRecordsApi(params)
}

export async function createOffboardingRecord(data: OffboardingRecordCreateInput) {
  const res = await createOffboardingRecordApi(data)
  revalidatePath('/hr/offboarding')
  revalidatePath('/hr/profile')
  return res
}

export async function updateOffboardingRecord(id: string, data: OffboardingRecordUpdateInput) {
  const res = await updateOffboardingRecordApi(id, data)
  revalidatePath('/hr/offboarding')
  return res
}

export async function deleteOffboardingRecord(id: string) {
  const res = await deleteOffboardingRecordApi(id)
  revalidatePath('/hr/offboarding')
  return res
}

// ─── Annual Training Plan Actions ───

export async function createAnnualTrainingPlan(data: { year: number; department: string; status: string }) {
  const res = await createAnnualTrainingPlanApi(data)
  revalidatePath('/hr/training/annual-plan')
  return res
}

export async function deleteAnnualTrainingPlan(id: string) {
  const res = await deleteAnnualTrainingPlanApi(id)
  revalidatePath('/hr/training/annual-plan')
  return res
}

export async function deleteAnnualPlanItem(planId: string, itemId: string) {
  const res = await deleteAnnualPlanItemApi(planId, itemId)
  revalidatePath('/hr/training/annual-plan')
  return res
}

export async function batchUpdatePlanItems(planId: string, data: { items: unknown[] }) {
  const res = await batchUpdatePlanItemsApi(planId, data)
  revalidatePath('/hr/training/annual-plan')
  return res
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

export async function fetchDepartments(
  params?: {
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<DepartmentListResponse> {
  return fetchDepartmentsAction(params)
}

export async function fetchOffboardingRecords(
  params?: {
    employee_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<OffboardingRecordListResponse> {
  return fetchOffboardingRecordsAction(params)
}

export async function fetchTeams(
  params?: {
    department_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<TeamListResponse> {
  return fetchTeamsApi(params)
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
): Promise<any> {
  return fetchOnboardingRecordsApi(params)
}

export async function fetchDepartureRecords(
  params?: {
    department?: string
    offboarding_type?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<any> {
  return fetchDepartureRecordsApi(params)
}

export async function fetchEmployeeById(id: string): Promise<any> {
  return fetchEmployeeByIdApi(id)
}

export async function fetchCandidateById(id: string): Promise<any> {
  return fetchCandidateByIdApi(id)
}

export async function fetchCandidates(params: any = {}): Promise<any> {
  return fetchCandidatesApi(params).catch(() => ({ data: [], meta: { total: 0 } }))
}

export async function fetchNewEmployees(params: any = {}): Promise<EmployeeListResponse> {
  return fetchNewEmployeesApi(params)
}

export async function fetchNewDepartments(params: any = {}): Promise<DepartmentListResponse> {
  return fetchNewDepartmentsApi(params)
}

export async function fetchNewOnboardingRecords(params: any = {}): Promise<any> {
  return fetchNewOnboardingRecordsApi(params)
}

export async function fetchNewDepartureRecords(params: any = {}): Promise<any> {
  return fetchNewDepartureRecordsApi(params)
}

export async function fetchNewOffboardingRecords(params: any = {}): Promise<any> {
  return fetchNewOffboardingRecordsApi(params)
}

export async function fetchAnnualTrainingPlanById(id: string): Promise<any> {
  return fetchAnnualTrainingPlanByIdApi(id)
}

export async function fetchPlanItems(id: string): Promise<any> {
  return fetchPlanItemsApi(id)
}

export async function fetchTrainingRecords(params: any = {}): Promise<any> {
  return fetchTrainingRecordsApi(params)
}

export async function fetchTrainingPlans(params: any = {}): Promise<any> {
  return fetchTrainingPlansApi(params)
}

export async function fetchEmployeeByNumber(employeeNumber: string): Promise<any> {
  return fetchEmployeeByNumberApi(employeeNumber)
}

export async function syncTrainingSpecialistsFeishuOpenIds() {
  const res = await syncTrainingSpecialistsFeishuOpenIdsApi()
  revalidatePath('/hr/training/specialists')
  return res
}

// ─── 飞书同步 Actions (from lib/api/hr.ts) ───

export async function syncOnboardingFromFeishu() {
  const json = await syncOnboardingFromFeishuApi()
  revalidatePath('/hr/onboarding')
  return json
}

export async function syncDepartureFromFeishu() {
  const json = await syncDepartureFromFeishuApi()
  revalidatePath('/hr/departure')
  return json
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
  const validated = parse(OnboardingTrainingRecordSchema, data)
  const blob = await createOnboardingTrainingRecordApi(employeeNumber, data)
  revalidatePath('/hr')
  return blob
}

export async function createDepartureRecord(data: unknown) {
  const validated = parse(DepartureRecordSchema, data)
  const res = await createDepartureRecordApi(data)
  revalidatePath('/hr')
  return res
}

export async function uploadAnnualTrainingPlan(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await uploadAnnualTrainingPlanApi(fd)
  revalidatePath('/hr')
  return res
}

export async function uploadTrainers(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await uploadTrainersApi(fd)
  revalidatePath('/hr/training/trainers')
  return res
}

export async function uploadSopCatalog(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await uploadSopCatalogApi(fd)
  revalidatePath('/hr/training/sop-catalog')
  return res
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
  return fetchTrainingSessionsApi(params)
}

export async function createTrainingSession(data: TrainingSessionCreateInput) {
  const res = await createTrainingSessionApi(data)
  revalidatePath('/hr/training/records')
  return res
}

export async function updateTrainingSession(id: string, data: TrainingSessionUpdateInput) {
  const res = await updateTrainingSessionApi(id, data)
  revalidatePath('/hr/training/records')
  return res
}

export async function deleteTrainingSession(id: string) {
  const res = await deleteTrainingSessionApi(id)
  revalidatePath('/hr/training/records')
  return res
}

export async function updateTrainingSessionStatus(id: string, status: string) {
  const res = await updateTrainingSessionStatusApi(id, status)
  revalidatePath('/hr/training/records')
  return res
}

export async function fetchTrainingSessionByIdAction(id: string): Promise<TrainingSessionResponse> {
  return fetchTrainingSessionByIdApi(id)
}

export async function sendTrainingSessionSelectTasksAction(id: string): Promise<{ code: number; message: string; data: SelectTask[] }> {
  const res = await sendTrainingSessionSelectTasksApi(id)
  revalidatePath('/hr/training/records')
  return res
}

export async function fetchTrainingSessionSelectTasksAction(id: string): Promise<{ code: number; message: string; data: SelectTask[] }> {
  return fetchTrainingSessionSelectTasksApi(id)
}