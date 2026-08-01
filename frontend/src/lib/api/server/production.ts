import { apiFetch, apiFetchRaw, getApiBaseUrl } from '@/lib/api/server/base'
import type {
  BatchFormData,
  BatchMaterialFormData,
  ProductionPlanFormData,
  PlanTaskFormData,
  ProcessSpecFormData,
  ProcessStepFormData,
  ProcessParameterFormData,
  ProductionRecordFormData,
  BatchQueryParams,
  PlanQueryParams,
  ProcessSpecQueryParams,
} from '@/types/production'

// ============ Batch Actions ============

export async function getBatches(
  params: BatchQueryParams,
  headers: Record<string, string>,
) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.status) searchParams.set('status', params.status)
  if (params.product_code) searchParams.set('product_code', params.product_code)
  if (params.batch_no) searchParams.set('batch_no', params.batch_no)
  const queryString = searchParams.toString()
  const endpoint = `/api/v1/production/batches${queryString ? `?${queryString}` : ''}`
  return apiFetch(`${getApiBaseUrl()}${endpoint}`, { headers })
}

export async function getBatch(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${id}`, { headers })
}

export async function createBatch(data: BatchFormData, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateBatch(id: string, data: Partial<BatchFormData>, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateBatchStatus(id: string, status: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
    headers,
  })
}

export async function deleteBatch(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Batch Material Actions ============

export async function getBatchMaterials(batchId: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${batchId}/materials`, { headers })
}

export async function addBatchMaterial(batchId: string, data: BatchMaterialFormData, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${batchId}/materials`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateBatchMaterial(id: string, data: Partial<BatchMaterialFormData>, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/materials/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteBatchMaterial(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/materials/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Production Plan Actions ============

export async function getPlans(
  params: PlanQueryParams,
  headers: Record<string, string>,
) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.status) searchParams.set('status', params.status)
  if (params.plan_month) searchParams.set('plan_month', params.plan_month)
  const queryString = searchParams.toString()
  const endpoint = `/api/v1/production/plans${queryString ? `?${queryString}` : ''}`
  return apiFetch(`${getApiBaseUrl()}${endpoint}`, { headers })
}

export async function getPlan(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/plans/${id}`, { headers })
}

export async function createPlan(data: ProductionPlanFormData, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/plans`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updatePlan(id: string, data: Partial<ProductionPlanFormData>, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/plans/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deletePlan(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/plans/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Plan Task Actions ============

export async function getPlanTasks(planId: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/plans/${planId}/tasks`, { headers })
}

export async function createPlanTask(data: PlanTaskFormData & { plan_id: string }, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updatePlanTask(id: string, data: Partial<PlanTaskFormData>, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/tasks/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deletePlanTask(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/tasks/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Process Spec Actions ============

export async function getProcessSpecs(
  params: ProcessSpecQueryParams,
  headers: Record<string, string>,
) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.status) searchParams.set('status', params.status)
  if (params.product_code) searchParams.set('product_code', params.product_code)
  const queryString = searchParams.toString()
  const endpoint = `/api/v1/production/process-specs${queryString ? `?${queryString}` : ''}`
  return apiFetch(`${getApiBaseUrl()}${endpoint}`, { headers })
}

export async function getProcessSpec(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/process-specs/${id}`, { headers })
}

export async function createProcessSpec(data: ProcessSpecFormData, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/process-specs`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateProcessSpec(id: string, data: Partial<ProcessSpecFormData>, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/process-specs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteProcessSpec(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/process-specs/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Process Step Actions ============

export async function getProcessSteps(specId: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/process-specs/${specId}/steps`, { headers })
}

export async function createProcessStep(data: ProcessStepFormData & { spec_id: string }, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/steps`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateProcessStep(id: string, data: Partial<ProcessStepFormData>, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/steps/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteProcessStep(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/steps/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Process Parameter Actions ============

export async function getProcessParameters(stepId: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/steps/${stepId}/parameters`, { headers })
}

export async function createProcessParameter(data: ProcessParameterFormData & { step_id: string }, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/parameters`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteProcessParameter(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/parameters/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Production Record Actions ============

export async function getProductionRecords(batchId: string, page: number, pageSize: number, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${batchId}/records?page=${page}&page_size=${pageSize}`, { headers })
}

export async function createProductionRecord(data: ProductionRecordFormData & { batch_id: string }, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/records`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateProductionRecord(id: string, data: Partial<ProductionRecordFormData>, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/records/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteProductionRecord(id: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/records/${id}`, {
    method: 'DELETE',
    headers,
  })
}

// ============ Material Balance Actions ============

export async function getMaterialBalance(batchId: string, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${batchId}/balance`, { headers })
}

export async function calculateMaterialBalance(batchId: string, minBalanceRate: number, headers: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/production/batches/${batchId}/balance/calculate?min_balance_rate=${minBalanceRate}`, {
    method: 'POST',
    headers,
  })
}

// ============ Label Verification Video Upload ============

export async function uploadLabelVerificationVideo(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/quality/label-verifications/upload-video`, {
    method: 'POST',
    body: formData,
  })
}