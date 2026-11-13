import { apiFetch, apiFetchData, apiFetchRaw, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

type CapaApiResponse = components['schemas']['CapaApiResponse']
type CapaCreate = components['schemas']['CapaCreate']
type CapaUpdate = components['schemas']['CapaUpdate']

async function fetchDeleteOrNull<T>(endpoint: string): Promise<T | null> {
  const res = await apiFetchRaw(endpoint, { method: 'DELETE' })
  if (res.status === 204) return null
  const json = await res.json()
  return unwrapResponse(json)
}
import type {
  InspectionStandardFormData,
  StandardCopyData,
  ObsoleteData,
  StandardQueryParams,
  CreateDepartmentContactRequest,
  UpdateDepartmentContactRequest,
  UploadLcResponse,
  AiLogFilter,
  DepartmentContact,
  DepartmentContactListData,
  DepartmentMemberOption,
  DeviationAiAnalysisInput,
  DeviationAttachmentComment,
  DeviationAttachmentCommentCreateInput,
  DeviationAttachmentCommentUpdateInput,
  DeviationBatchResult,
  DeviationCrossDeptApproveInput,
  DeviationCrossDeptInvestigationInput,
  DeviationCrossDeptRejectInput,
  DeviationDeleteResult,
  DeviationFinalCodeInput,
  DeviationInvestigationDraftInput,
  DeviationInvestigationInput,
  DeviationInvestigationSubmitInput,
  DeviationJobState,
  DeviationLedgerBatchStatusInput,
  DeviationLedgerCreateInput,
  DeviationLedgerDetail,
  DeviationLedgerFilters,
  DeviationLedgerListResult,
  DeviationLedgerOption,
  DeviationLedgerOptionResult,
  DeviationLedgerStatistics,
  DeviationMemberOptionResult,
  DeviationLedgerUpdateInput,
  DeviationNotifySettings,
  DeviationNotifySettingsUpdate,
  DeviationNotifyTestResult,
  DeviationResubmitInput,
  DeviationReviewInput,
  WeeklyConfirmationInput,
  WeeklyConfirmationItem,
  WeeklyConfirmationListData,
} from '@/types/quality'
import type {
  SamplingOrderCreate,
  SamplingOrderUpdate,
  SamplingOrderFilter,
  SamplingApprovalCreate,
  RetentionLedgerFilter,
} from '@/types/sampling'
import type {
  IQCInspectionCreate,
  IQCInspectionUpdate,
  IQCInspectionFilter,
  IQCApprovalCreate,
} from '@/types/iqc'
import type {
  IPQCInspectionCreate,
  IPQCInspectionUpdate,
  IPQCInspectionFilter,
  IPQCApprovalCreate,
} from '@/types/ipqc'
import type {
  FQCInspectionCreate,
  FQCInspectionUpdate,
  FQCInspectionFilter,
  FQCApprovalCreate,
} from '@/types/fqc'
import type {
  StabilityStudyCreate,
  StabilityStudyUpdate,
  StabilityStudyFilter,
  StabilitySampleNodeUpdate,
  StabilityInspectionCreate,
  StabilityInspectionUpdate,
  StabilityInspectionFilter,
  StabilityApprovalCreate,
} from '@/types/stability'



// ============ InspectionStandard Actions ============

export async function getStandards(params: StandardQueryParams = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.status) searchParams.set('status', params.status)
  if (params.material_code) searchParams.set('material_code', params.material_code)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.material_category) searchParams.set('material_category', params.material_category)
  if (params.pharmacopeia) searchParams.set('pharmacopeia', params.pharmacopeia)
  if (params.version) searchParams.set('version', params.version)
  if (params.is_effective !== undefined) searchParams.set('is_effective', String(params.is_effective))
  const queryString = searchParams.toString()
  const endpoint = `/quality/standards${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getEffectiveStandards(params: { material_code?: string; material_category?: string } = {}) {
  const searchParams = new URLSearchParams()
  if (params.material_code) searchParams.set('material_code', params.material_code)
  if (params.material_category) searchParams.set('material_category', params.material_category)
  const queryString = searchParams.toString()
  const endpoint = `/quality/standards/effective${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getStandard(id: string) {
  return apiFetch(`/api/v1/quality/standards/${id}`)
}

export async function createStandard(data: InspectionStandardFormData) {
  return apiFetch(`/api/v1/quality/standards`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStandard(id: string, data: Partial<InspectionStandardFormData>) {
  return apiFetch(`/api/v1/quality/standards/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteStandard(id: string) {
  return apiFetch(`/api/v1/quality/standards/${id}`, {
    method: 'DELETE',
  })
}

export async function submitStandardForApproval(id: string) {
  return apiFetch(`/api/v1/quality/standards/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveStandard(id: string) {
  return apiFetch(`/api/v1/quality/standards/${id}/approve`, {
    method: 'POST',
  })
}

export async function rejectStandard(id: string, comments: string) {
  return apiFetch(`/api/v1/quality/standards/${id}/reject?comments=${encodeURIComponent(comments)}`, {
    method: 'POST',
  })
}

export async function obsoleteStandard(id: string, data: ObsoleteData) {
  return apiFetch(`/api/v1/quality/standards/${id}/obsolete`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function copyStandard(data: StandardCopyData) {
  return apiFetch(`/api/v1/quality/standards/copy`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getStandardItems(standardId: string) {
  return apiFetch(`/api/v1/quality/standards/${standardId}/items`)
}

export async function getApprovalRecords(standardId: string) {
  return apiFetch(`/api/v1/quality/standards/${standardId}/approvals`)
}

// ============ Sampling Order Actions ============

export async function getSamplingOrders(params: SamplingOrderFilter & { page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.order_no) searchParams.set('order_no', params.order_no)
  if (params.material_code) searchParams.set('material_code', params.material_code)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.sampling_source) searchParams.set('sampling_source', params.sampling_source)
  if (params.status) searchParams.set('status', params.status)
  if (params.sampling_result) searchParams.set('sampling_result', params.sampling_result)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const queryString = searchParams.toString()
  const endpoint = `/quality/sampling/orders${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getSamplingOrder(id: string) {
  return apiFetch(`/api/v1/quality/sampling/orders/${id}`)
}

export async function createSamplingOrder(data: SamplingOrderCreate) {
  return apiFetch(`/api/v1/quality/sampling/orders`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateSamplingOrder(id: string, data: SamplingOrderUpdate) {
  return apiFetch(`/api/v1/quality/sampling/orders/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteSamplingOrder(id: string) {
  return apiFetch(`/api/v1/quality/sampling/orders/${id}`, {
    method: 'DELETE',
  })
}

export async function submitSamplingOrderForApproval(id: string) {
  return apiFetch(`/api/v1/quality/sampling/orders/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveSamplingOrder(id: string, data: SamplingApprovalCreate) {
  return apiFetch(`/api/v1/quality/sampling/orders/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getSamplingApprovals(orderId: string) {
  return apiFetch(`/api/v1/quality/sampling/orders/${orderId}/approvals`)
}

// ============ Retention Ledger Actions ============

export async function getRetentionLedger(params: RetentionLedgerFilter & { page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.order_no) searchParams.set('order_no', params.order_no)
  if (params.sample_no) searchParams.set('sample_no', params.sample_no)
  if (params.material_code) searchParams.set('material_code', params.material_code)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.retention_status) searchParams.set('retention_status', params.retention_status)
  const queryString = searchParams.toString()
  const endpoint = `/quality/sampling/retention-ledger${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getRetentionByOrder(orderId: string) {
  return apiFetch(`/api/v1/quality/sampling/retention-ledger/order/${orderId}`)
}

// ============ IQC Inspection Actions ============

export async function getIQCInspections(params: IQCInspectionFilter & { page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.inspection_no) searchParams.set('inspection_no', params.inspection_no)
  if (params.material_code) searchParams.set('material_code', params.material_code)
  if (params.material_name) searchParams.set('material_name', params.material_name)
  if (params.material_category) searchParams.set('material_category', params.material_category)
  if (params.supplier_name) searchParams.set('supplier_name', params.supplier_name)
  if (params.status) searchParams.set('status', params.status)
  if (params.inspection_conclusion) searchParams.set('inspection_conclusion', params.inspection_conclusion)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const queryString = searchParams.toString()
  const endpoint = `/quality/iqc/inspections${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getIQCInspection(id: string) {
  return apiFetch(`/api/v1/quality/iqc/inspections/${id}`)
}

export async function createIQCInspection(data: IQCInspectionCreate) {
  return apiFetch(`/api/v1/quality/iqc/inspections`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateIQCInspection(id: string, data: IQCInspectionUpdate) {
  return apiFetch(`/api/v1/quality/iqc/inspections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteIQCInspection(id: string) {
  return apiFetch(`/api/v1/quality/iqc/inspections/${id}`, {
    method: 'DELETE',
  })
}

export async function submitIQCInspectionForApproval(id: string) {
  return apiFetch(`/api/v1/quality/iqc/inspections/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveIQCInspection(id: string, data: IQCApprovalCreate) {
  return apiFetch(`/api/v1/quality/iqc/inspections/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getIQCApprovals(inspectionId: string) {
  return apiFetch(`/api/v1/quality/iqc/inspections/${inspectionId}/approvals`)
}

// ============ IPQC Inspection Actions ============

export async function getIPQCInspections(params: IPQCInspectionFilter & { page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.inspection_no) searchParams.set('inspection_no', params.inspection_no)
  if (params.batch_no) searchParams.set('batch_no', params.batch_no)
  if (params.product_code) searchParams.set('product_code', params.product_code)
  if (params.product_name) searchParams.set('product_name', params.product_name)
  if (params.process_stage) searchParams.set('process_stage', params.process_stage)
  if (params.status) searchParams.set('status', params.status)
  if (params.inspection_conclusion) searchParams.set('inspection_conclusion', params.inspection_conclusion)
  if (params.batch_locked !== undefined) searchParams.set('batch_locked', String(params.batch_locked))
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const queryString = searchParams.toString()
  const endpoint = `/quality/ipqc/inspections${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getIPQCInspection(id: string) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${id}`)
}

export async function createIPQCInspection(data: IPQCInspectionCreate) {
  return apiFetch(`/api/v1/quality/ipqc/inspections`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateIPQCInspection(id: string, data: IPQCInspectionUpdate) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteIPQCInspection(id: string) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${id}`, {
    method: 'DELETE',
  })
}

export async function submitIPQCInspectionForApproval(id: string) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveIPQCInspection(id: string, data: IPQCApprovalCreate) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getIPQCApprovals(inspectionId: string) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${inspectionId}/approvals`)
}

export async function lockIPQCBatch(id: string, reason: string) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${id}/lock-batch?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
  })
}

export async function unlockIPQCBatch(id: string) {
  return apiFetch(`/api/v1/quality/ipqc/inspections/${id}/unlock-batch`, {
    method: 'POST',
  })
}

// ============ FQC Inspection Actions ============

export async function getFQCInspections(params: FQCInspectionFilter & { page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.inspection_no) searchParams.set('inspection_no', params.inspection_no)
  if (params.batch_no) searchParams.set('batch_no', params.batch_no)
  if (params.product_code) searchParams.set('product_code', params.product_code)
  if (params.product_name) searchParams.set('product_name', params.product_name)
  if (params.production_workshop) searchParams.set('production_workshop', params.production_workshop)
  if (params.status) searchParams.set('status', params.status)
  if (params.inspection_conclusion) searchParams.set('inspection_conclusion', params.inspection_conclusion)
  if (params.release_status) searchParams.set('release_status', params.release_status)
  if (params.batch_locked !== undefined) searchParams.set('batch_locked', String(params.batch_locked))
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const queryString = searchParams.toString()
  const endpoint = `/quality/fqc/inspections${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getFQCInspection(id: string) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}`)
}

export async function createFQCInspection(data: FQCInspectionCreate) {
  return apiFetch(`/api/v1/quality/fqc/inspections`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateFQCInspection(id: string, data: FQCInspectionUpdate) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteFQCInspection(id: string) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}`, {
    method: 'DELETE',
  })
}

export async function submitFQCInspectionForApproval(id: string) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveFQCInspection(id: string, data: FQCApprovalCreate) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getFQCApprovals(inspectionId: string) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${inspectionId}/approvals`)
}

export async function applyFQCReinspection(id: string, reason: string) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}/reinspection?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
  })
}

export async function releaseFQCInspection(id: string, releaseReason?: string) {
  const url = releaseReason
    ? `/quality/fqc/inspections/${id}/release?release_reason=${encodeURIComponent(releaseReason)}`
    : `/quality/fqc/inspections/${id}/release`
  return apiFetch(`/api/v1${url}`, {
    method: 'POST',
  })
}

export async function lockFQCBatch(id: string, reason: string) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}/lock-batch?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
  })
}

export async function unlockFQCBatch(id: string) {
  return apiFetch(`/api/v1/quality/fqc/inspections/${id}/unlock-batch`, {
    method: 'POST',
  })
}

// ============ Stability Study Actions ============

export async function getStabilityStudies(params: StabilityStudyFilter & { page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.study_no) searchParams.set('study_no', params.study_no)
  if (params.product_code) searchParams.set('product_code', params.product_code)
  if (params.product_name) searchParams.set('product_name', params.product_name)
  if (params.study_type) searchParams.set('study_type', params.study_type)
  if (params.status) searchParams.set('status', params.status)
  if (params.batch_no) searchParams.set('batch_no', params.batch_no)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const queryString = searchParams.toString()
  const endpoint = `/quality/stability/studies${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getStabilityStudy(id: string) {
  return apiFetch(`/api/v1/quality/stability/studies/${id}`)
}

export async function createStabilityStudy(data: StabilityStudyCreate) {
  return apiFetch(`/api/v1/quality/stability/studies`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStabilityStudy(id: string, data: StabilityStudyUpdate) {
  return apiFetch(`/api/v1/quality/stability/studies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteStabilityStudy(id: string) {
  return apiFetch(`/api/v1/quality/stability/studies/${id}`, {
    method: 'DELETE',
  })
}

export async function submitStabilityStudy(id: string) {
  return apiFetch(`/api/v1/quality/stability/studies/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveStabilityStudy(id: string, data: StabilityApprovalCreate) {
  return apiFetch(`/api/v1/quality/stability/studies/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getStabilityStudySampleNodes(studyId: string) {
  return apiFetch(`/api/v1/quality/stability/studies/${studyId}/sample-nodes`)
}

export async function updateStabilitySampleNode(id: string, data: StabilitySampleNodeUpdate) {
  return apiFetch(`/api/v1/quality/stability/sample-nodes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function getStabilityInspections(params: StabilityInspectionFilter & { page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.study_id) searchParams.set('study_id', params.study_id)
  if (params.study_no) searchParams.set('study_no', params.study_no)
  if (params.inspection_no) searchParams.set('inspection_no', params.inspection_no)
  if (params.batch_no) searchParams.set('batch_no', params.batch_no)
  if (params.status) searchParams.set('status', params.status)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const queryString = searchParams.toString()
  const endpoint = `/quality/stability/inspections${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getStabilityInspection(id: string) {
  return apiFetch(`/api/v1/quality/stability/inspections/${id}`)
}

export async function createStabilityInspection(data: StabilityInspectionCreate) {
  return apiFetch(`/api/v1/quality/stability/inspections`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStabilityInspection(id: string, data: StabilityInspectionUpdate) {
  return apiFetch(`/api/v1/quality/stability/inspections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function submitStabilityInspection(id: string) {
  return apiFetch(`/api/v1/quality/stability/inspections/${id}/submit`, {
    method: 'POST',
  })
}

export async function getStabilityTrendData(studyId: string) {
  return apiFetch(`/api/v1/quality/stability/studies/${studyId}/trend`)
}

// ============ AI 交互日志 Actions ============

export async function getAiLogs(params: AiLogFilter = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.operate_type) searchParams.set('operate_type', params.operate_type)
  if (params.operator) searchParams.set('operator', params.operator)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  if (params.keyword) searchParams.set('keyword', params.keyword)
  const queryString = searchParams.toString()
  const endpoint = `/quality/ai/logs${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getAiLogById(id: string) {
  return apiFetch(`/api/v1/quality/ai/logs/${id}`)
}

// ============ CAPA Actions ============

export async function createCapa(data: CapaCreate): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCapa(capaId: string, data: CapaUpdate): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCapa(capaId: string) {
  return fetchDeleteOrNull(`/api/v1/quality/capas/${capaId}`)
}

// ============ Department Contact Actions ============

export async function createDepartmentContact(data: CreateDepartmentContactRequest): Promise<DepartmentContact> {
  return apiFetchData<DepartmentContact>('/api/v1/quality/department-contacts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDepartmentContact(
  contactId: string,
  data: UpdateDepartmentContactRequest,
): Promise<DepartmentContact> {
  return apiFetchData<DepartmentContact>(`/api/v1/quality/department-contacts/${contactId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDepartmentContact(contactId: string) {
  return fetchDeleteOrNull(`/api/v1/quality/department-contacts/${contactId}`)
}

// ============ Label Verification Actions ============

export async function fetchLabelVerifications(params: { page: number; page_size: number }) {
  const searchParams = new URLSearchParams({
    page: params.page.toString(),
    page_size: params.page_size.toString(),
  })
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/label-verifications?${searchParams.toString()}`)
}

// ============ Additional CAPA Actions ============

export async function submitCapa(capaId: string): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/submit`, {
    method: 'POST',
  })
}

export async function approveCapa(capaId: string, data: unknown): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function resubmitCapa(capaId: string): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/resubmit`, {
    method: 'POST',
  })
}

export async function addExecutionTrack(capaId: string, data: unknown): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/execution-tracks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteExecutionTrack(capaId: string, trackId: string) {
  return fetchDeleteOrNull(`/api/v1/quality/capas/${capaId}/execution-tracks/${trackId}`)
}

export async function confirmExecution(capaId: string, data: unknown): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/confirm-execution`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function submitEvaluation(capaId: string, data: unknown): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/evaluate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function completeCapaPart(capaId: string, data: unknown): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/complete-part`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function confirmDeptHead(capaId: string, data: unknown): Promise<CapaApiResponse> {
  return apiFetch<CapaApiResponse>(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/confirm-dept-head`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function uploadLcExcel(formData: FormData): Promise<UploadLcResponse> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/lc-report/upload`, {
    method: 'POST',
    body: formData,
  })
}

// ============ 偏差台账 ============

/** 台账列表：状态 / 发生部门 / 发现日期区间筛选，按发现日期倒序 */
export async function fetchDeviationLedgerList(
  params: DeviationLedgerFilters = {},
): Promise<DeviationLedgerListResult> {
  const searchParams = new URLSearchParams()
  if (params.reason_category) searchParams.set('reason_category', params.reason_category)
  if (params.status) searchParams.set('status', params.status)
  if (params.department) searchParams.set('department', params.department)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  const queryString = searchParams.toString()
  return apiFetchData<DeviationLedgerListResult>(
    `/api/v1/quality/deviation/ledger${queryString ? `?${queryString}` : ''}`,
  )
}

/** 偏差看盘统计 */
export async function fetchDeviationLedgerStatistics(): Promise<DeviationLedgerStatistics> {
  return apiFetchData<DeviationLedgerStatistics>('/api/v1/quality/deviation/ledger/statistics')
}

/** 台账只读详情 */
export async function fetchDeviationLedgerDetail(id: string): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}`)
}

/** 发生部门候选（筛选栏，覆盖台账已有部门） */
export async function fetchDeviationDepartmentOptions(): Promise<DeviationLedgerOption[]> {
  const data = await apiFetchData<DeviationLedgerOptionResult>(
    '/api/v1/quality/deviation/ledger/department-options',
  )
  return data.items
}

/** 新建 / 编辑可用部门（来源部门联系人配置，保证节点负责人可解析） */
export async function fetchDeviationDepartmentContactOptions(): Promise<DeviationLedgerOption[]> {
  const data = await apiFetchData<DeviationLedgerOptionResult>(
    '/api/v1/quality/deviation/ledger/department-contact-options',
  )
  return data.items
}

/** 调查人候选 */
export async function fetchDeviationInvestigatorOptions(keyword?: string): Promise<DeviationLedgerOption[]> {
  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : ''
  const data = await apiFetchData<DeviationLedgerOptionResult>(
    `/api/v1/quality/deviation/ledger/investigator-options${query}`,
  )
  return data.items
}

/** 状态候选 */
export async function fetchDeviationStatusOptions(): Promise<DeviationLedgerOption[]> {
  const data = await apiFetchData<DeviationLedgerOptionResult>(
    '/api/v1/quality/deviation/ledger/status-options',
  )
  return data.items
}

/** 新建偏差 */
export async function fetchCreateDeviationLedger(data: DeviationLedgerCreateInput): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>('/api/v1/quality/deviation/ledger', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 修改基础信息（含调查人、跨部门审核配置） */
export async function fetchUpdateDeviationLedger(
  id: string,
  data: DeviationLedgerUpdateInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

/** 生成 AI 分析（生成后不落库，需再确认保存） */
export async function fetchStartDeviationAiAnalysis(id: string): Promise<DeviationJobState> {
  return apiFetchData<DeviationJobState>(`/api/v1/quality/deviation/ledger/${id}/ai-analysis`, {
    method: 'POST',
  })
}

/** 查询 AI 分析后台任务状态（客户端轮询用） */
export async function fetchDeviationJobStatus(jobId: string): Promise<DeviationJobState> {
  return apiFetchData<DeviationJobState>(`/api/v1/quality/deviation/ledger/jobs/${jobId}`)
}

/** 保存 AI 分析结果（只落库，不流转流程） */
export async function fetchCompleteDeviationAiAnalysis(
  id: string,
  data: DeviationAiAnalysisInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/complete-ai-analysis`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 提交调查报告 */
export async function fetchSubmitDeviationInvestigation(
  id: string,
  data: DeviationInvestigationInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/investigation`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 审核阶段追加调查记录（不推进流程） */
export async function fetchAppendDeviationInvestigationRecord(
  id: string,
  data: DeviationInvestigationInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/investigation-records`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 暂存调查记录草稿（按本人 + 部门覆盖，不推进流程） */
export async function fetchSaveDeviationInvestigationDraft(
  id: string,
  data: DeviationInvestigationDraftInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/investigation-drafts`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 清除本人的调查记录草稿（department 为空即主流程调查草稿） */
export async function fetchDeleteDeviationInvestigationDraft(
  id: string,
  department?: string | null,
): Promise<DeviationLedgerDetail> {
  const query = department ? `?department=${encodeURIComponent(department)}` : ''
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/investigation-drafts${query}`, {
    method: 'DELETE',
  })
}

/** 跨部门调查人提交本部门调查记录（完成该行「调查」节点） */
export async function fetchSubmitDeviationCrossDeptInvestigation(
  id: string,
  data: DeviationCrossDeptInvestigationInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/cross-dept-investigation`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 跨部门会签：逐行审批（任一审核人通过即该行通过，全部行通过后流转所属QA审核） */
export async function fetchApproveDeviationCrossDeptRow(
  id: string,
  data: DeviationCrossDeptApproveInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/cross-dept-review`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 跨部门会签：逐行退回（只重置该部门的调查与审核节点，流程仍停在跨部门环节） */
export async function fetchRejectDeviationCrossDeptRow(
  id: string,
  data: DeviationCrossDeptRejectInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/cross-dept-review/reject`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 调查记录已填写：直接提交审核（不新建记录） */
export async function fetchSubmitDeviationInvestigationForReview(
  id: string,
  data: DeviationInvestigationSubmitInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/investigation-submit`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 审核通过 / 退回 */
export async function fetchReviewDeviationLedger(
  id: string,
  data: DeviationReviewInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 退回后重新提交 */
export async function fetchResubmitDeviationLedger(
  id: string,
  data: DeviationResubmitInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/resubmit`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 提交最终编号并关闭 */
export async function fetchSubmitDeviationFinalCode(
  id: string,
  data: DeviationFinalCodeInput,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/final-code`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 上传附件 */
export async function fetchUploadDeviationAttachment(
  id: string,
  formData: FormData,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${id}/attachments`, {
    method: 'POST',
    body: formData,
  })
}

/** 删除附件 */
export async function fetchDeleteDeviationAttachment(
  id: string,
  fileId: string,
): Promise<DeviationLedgerDetail> {
  return apiFetchData<DeviationLedgerDetail>(
    `/api/v1/quality/deviation/ledger/${id}/attachments/${fileId}`,
    { method: 'DELETE' },
  )
}

/** 新增附件批注 */
export async function fetchCreateDeviationAttachmentComment(
  id: string,
  fileId: string,
  data: DeviationAttachmentCommentCreateInput,
): Promise<DeviationAttachmentComment> {
  return apiFetchData<DeviationAttachmentComment>(
    `/api/v1/quality/deviation/ledger/${id}/attachments/${fileId}/comments`,
    { method: 'POST', body: JSON.stringify(data) },
  )
}

/** 修改附件批注（正文或处理状态） */
export async function fetchUpdateDeviationAttachmentComment(
  id: string,
  fileId: string,
  commentId: string,
  data: DeviationAttachmentCommentUpdateInput,
): Promise<DeviationAttachmentComment> {
  return apiFetchData<DeviationAttachmentComment>(
    `/api/v1/quality/deviation/ledger/${id}/attachments/${fileId}/comments/${commentId}`,
    { method: 'PATCH', body: JSON.stringify(data) },
  )
}

/** 删除附件批注（软删除，仅作者/超管） */
export async function fetchDeleteDeviationAttachmentComment(
  id: string,
  fileId: string,
  commentId: string,
): Promise<DeviationDeleteResult | null> {
  return fetchDeleteOrNull<DeviationDeleteResult>(
    `/api/v1/quality/deviation/ledger/${id}/attachments/${fileId}/comments/${commentId}`,
  )
}

/** 批量更新状态 */
export async function fetchBatchUpdateDeviationStatus(
  data: DeviationLedgerBatchStatusInput,
): Promise<DeviationBatchResult> {
  return apiFetchData<DeviationBatchResult>('/api/v1/quality/deviation/ledger/batch-status', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

/** 删除偏差（任意状态软删除，数据仍可追溯） */
export async function fetchRemoveDeviationLedger(id: string): Promise<void> {
  await apiFetchRaw(`/api/v1/quality/deviation/ledger/${id}`, { method: 'DELETE' })
}

// ============ 偏差组织配置 ============

/** 部门联系人列表 */
export async function fetchDepartmentContacts(keyword?: string): Promise<DepartmentContactListData> {
  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : ''
  return apiFetchData<DepartmentContactListData>(`/api/v1/quality/department-contacts${query}`)
}

/** 配置页人员候选 */
export async function fetchDeviationMemberOptions(keyword?: string): Promise<DepartmentMemberOption[]> {
  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : ''
  const data = await apiFetchData<DeviationMemberOptionResult>(
    `/api/v1/quality/department-contacts/member-options${query}`,
  )
  return data.items
}

/** 通知设置 */
export async function fetchDeviationNotifySettings(): Promise<DeviationNotifySettings> {
  return apiFetchData<DeviationNotifySettings>('/api/v1/quality/deviation/notify')
}

/** 更新通知设置 */
export async function fetchUpdateDeviationNotifySettings(
  data: DeviationNotifySettingsUpdate,
): Promise<DeviationNotifySettings> {
  return apiFetchData<DeviationNotifySettings>('/api/v1/quality/deviation/notify', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

/** 发送偏差通知测试卡片（自检飞书链路与处理人绑定情况） */
export async function fetchSendDeviationNotifyTest(): Promise<DeviationNotifyTestResult> {
  return apiFetchData<DeviationNotifyTestResult>('/api/v1/quality/deviation/notify/test', {
    method: 'POST',
  })
}

/** 部门周确认列表 */
export async function getWeeklyConfirmations(weekKey?: string): Promise<WeeklyConfirmationListData> {
  const query = weekKey ? `?week_key=${encodeURIComponent(weekKey)}` : ''
  return apiFetchData<WeeklyConfirmationListData>(
    `/api/v1/quality/deviation/weekly-confirmations${query}`,
  )
}

/** 提交本部门周确认 */
export async function upsertWeeklyConfirmation(
  data: WeeklyConfirmationInput,
): Promise<WeeklyConfirmationItem> {
  return apiFetchData<WeeklyConfirmationItem>('/api/v1/quality/deviation/weekly-confirmations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
