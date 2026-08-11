import { apiFetch, apiFetchRaw, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'

async function fetchDeleteOrNull<T>(endpoint: string): Promise<T | null> {
  const res = await apiFetchRaw(endpoint, { method: 'DELETE' })
  if (res.status === 204) return null
  const json = await res.json()
  return unwrapResponse(json)
}
import type {
  InspectionStandard,
  InspectionStandardItem,
  InspectionStandardFormData,
  InspectionStandardItemFormData,
  StandardCopyData,
  ObsoleteData,
  ApprovalRecord,
  StandardQueryParams,
  CreateDeviationRequest,
  UpdateDeviationRequest,
  CreateCapaRequest,
  UpdateCapaRequest,
  CreateDepartmentContactRequest,
  UpdateDepartmentContactRequest,
} from '@/types/quality'
import type {
  SamplingOrder,
  SamplingOrderCreate,
  SamplingOrderUpdate,
  SamplingOrderListItem,
  SamplingOrderListResponse,
  SamplingOrderFilter,
  SamplingOrderItemCreate,
  SamplingApprovalRecord,
  SamplingApprovalCreate,
  SampleRetentionLedger,
  RetentionLedgerListResponse,
  RetentionLedgerFilter,
} from '@/types/sampling'
import type {
  IQCInspection,
  IQCInspectionCreate,
  IQCInspectionUpdate,
  IQCInspectionListItem,
  IQCInspectionListResponse,
  IQCInspectionFilter,
  IQCInspectionItemCreate,
  IQCApprovalRecord,
  IQCApprovalCreate,
} from '@/types/iqc'
import type {
  IPQCInspection,
  IPQCInspectionCreate,
  IPQCInspectionUpdate,
  IPQCInspectionListItem,
  IPQCInspectionListResponse,
  IPQCInspectionFilter,
  IPQCInspectionItemCreate,
  IPQCApprovalRecord,
  IPQCApprovalCreate,
} from '@/types/ipqc'
import type {
  FQCInspection,
  FQCInspectionCreate,
  FQCInspectionUpdate,
  FQCInspectionListItem,
  FQCInspectionListResponse,
  FQCInspectionFilter,
  FQCInspectionItemCreate,
  FQCApprovalRecord,
  FQCApprovalCreate,
} from '@/types/fqc'
import type {
  StabilityStudy,
  StabilityStudyCreate,
  StabilityStudyUpdate,
  StabilityStudyListItem,
  StabilityStudyListResponse,
  StabilityStudyFilter,
  StabilitySampleNode,
  StabilitySampleNodeUpdate,
  StabilityInspection,
  StabilityInspectionCreate,
  StabilityInspectionUpdate,
  StabilityInspectionListItem,
  StabilityInspectionListResponse,
  StabilityInspectionFilter,
  StabilityInspectionItemCreate,
  StabilityApprovalRecord,
  StabilityApprovalCreate,
  TrendData,
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

export async function getAiLogs(params: any = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.operate_type) searchParams.set('operate_type', params.operate_type)
  if (params.operator) searchParams.set('operator', params.operator)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  if (params.keyword) searchParams.set('keyword', params.keyword)
  const queryString = searchParams.toString()
  const endpoint = `/ai/logs${queryString ? `?${queryString}` : ''}`
  return apiFetch(`/api/v1${endpoint}`)
}

export async function getAiLogById(id: string) {
  return apiFetch(`/api/v1/ai/logs/${id}`)
}

// ============ Deviation Actions ============

export async function createDeviation(data: CreateDeviationRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviations`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDeviation(deviationId: string, data: UpdateDeviationRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviations/${deviationId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDeviation(deviationId: string) {
  return fetchDeleteOrNull(`/api/v1/quality/deviations/${deviationId}`)
}

// ============ CAPA Actions ============

export async function createCapa(data: CreateCapaRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCapa(capaId: string, data: UpdateCapaRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCapa(capaId: string) {
  return fetchDeleteOrNull(`/api/v1/quality/capas/${capaId}`)
}

// ============ Department Contact Actions ============

export async function createDepartmentContact(data: CreateDepartmentContactRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/department-contacts`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDepartmentContact(contactId: string, data: UpdateDepartmentContactRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/department-contacts/${contactId}`, {
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

// ============ Attachment Review Actions ============

export async function submitAttachmentReview(data: {
  deviation_id?: string | null
  capa_id?: string | null
  attachment_url: string
  content: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/attachment-reviews`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAttachmentReview(reviewId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/attachment-reviews/${reviewId}`, {
    method: 'DELETE',
  })
}

// ============ Additional CAPA Actions ============

export async function submitCapa(capaId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/submit`, {
    method: 'POST',
  })
}

export async function approveCapa(capaId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function resubmitCapa(capaId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/resubmit`, {
    method: 'POST',
  })
}

export async function addExecutionTrack(capaId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/execution-tracks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteExecutionTrack(capaId: string, trackId: string) {
  return fetchDeleteOrNull(`/api/v1/quality/capas/${capaId}/execution-tracks/${trackId}`)
}

export async function confirmExecution(capaId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/confirm-execution`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function submitEvaluation(capaId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/evaluate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function completeCapaPart(capaId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/complete-part`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function confirmDeptHead(capaId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/capas/${capaId}/confirm-dept-head`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ============ Additional Deviation Actions ============

export async function submitDeviation(deviationId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviations/${deviationId}/submit`, {
    method: 'POST',
  })
}

export async function submitInvestigation(deviationId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviations/${deviationId}/investigation`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function submitReview(deviationId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviations/${deviationId}/review`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function submitFinalCode(deviationId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviations/${deviationId}/final-code`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function resubmitDeviation(deviationId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviations/${deviationId}/resubmit`, {
    method: 'POST',
  })
}

// ============ AI Config Actions ============

export async function saveAIConfig(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/ai/config`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function resetAIConfig(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/ai/config`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function testAIConnection(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/ai/config/test`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ============ Deviation Automation Actions ============

export async function createDeviationTask(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generateDeviationReport(taskId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function submitDeviationApproval(taskId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}/submit`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDeviationTask(taskId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function updateDeviationTaskFields(taskId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}/fields`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDeviationTask(taskId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}`, {
    method: 'DELETE',
  })
}

export async function createDeviationTemplate(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/templates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDeviationTemplate(templateId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/templates/${templateId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDeviationTemplate(templateId: string | number) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/templates/${templateId}`, {
    method: 'DELETE',
  })
}

export async function createSopTemplate(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop/templates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createSopFromTemplate(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop/from-template`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateSopTemplate(templateId: string, data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop/templates/${templateId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteSopTemplate(templateId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop/templates/${templateId}`, {
    method: 'DELETE',
  })
}

export async function generateSop(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function uploadDeviationFile(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function triggerAIProcess(taskId: number) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}/ai-process`, {
    method: 'POST',
  })
}

export async function updateAIResult(taskId: number, aiResult: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}/update-ai-result`, {
    method: 'PUT',
    body: JSON.stringify({ ai_result: aiResult }),
  })
}

export async function generateStandard(taskId: number) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/tasks/${taskId}/generate-standard`, {
    method: 'POST',
  })
}

export async function updateDeviationTemplateStatus(id: number, isActive: boolean) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ is_active: isActive }),
  })
}

export async function uploadDeviationTemplate(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/templates/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteSopRule(id: number) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop-rules/${id}`, {
    method: 'DELETE',
  })
}

export async function updateSopRuleStatus(id: number | string, status: string | number) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop-rules/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

export async function createSopRule(data: unknown) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop-rules`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function uploadSopRule(formData: FormData, ruleId: number) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop-rules/${ruleId}/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function aiParseSopRule(ruleId: number) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/sop-rules/${ruleId}/ai-parse`, {
    method: 'POST',
  })
}

export async function uploadDeviationFileWithTask(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/deviation-automation/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function uploadLcExcel(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/lc-report/upload`, {
    method: 'POST',
    body: formData,
  })
}