'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
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
import {
  getBatches as getBatchesApi,
  getBatch as getBatchApi,
  createBatch as createBatchApi,
  updateBatch as updateBatchApi,
  updateBatchStatus as updateBatchStatusApi,
  deleteBatch as deleteBatchApi,
  getBatchMaterials as getBatchMaterialsApi,
  addBatchMaterial as addBatchMaterialApi,
  updateBatchMaterial as updateBatchMaterialApi,
  deleteBatchMaterial as deleteBatchMaterialApi,
  getPlans as getPlansApi,
  getPlan as getPlanApi,
  createPlan as createPlanApi,
  updatePlan as updatePlanApi,
  deletePlan as deletePlanApi,
  getPlanTasks as getPlanTasksApi,
  createPlanTask as createPlanTaskApi,
  updatePlanTask as updatePlanTaskApi,
  deletePlanTask as deletePlanTaskApi,
  getProcessSpecs as getProcessSpecsApi,
  getProcessSpec as getProcessSpecApi,
  createProcessSpec as createProcessSpecApi,
  updateProcessSpec as updateProcessSpecApi,
  deleteProcessSpec as deleteProcessSpecApi,
  getProcessSteps as getProcessStepsApi,
  createProcessStep as createProcessStepApi,
  updateProcessStep as updateProcessStepApi,
  deleteProcessStep as deleteProcessStepApi,
  getProcessParameters as getProcessParametersApi,
  createProcessParameter as createProcessParameterApi,
  deleteProcessParameter as deleteProcessParameterApi,
  getProductionRecords as getProductionRecordsApi,
  createProductionRecord as createProductionRecordApi,
  updateProductionRecord as updateProductionRecordApi,
  deleteProductionRecord as deleteProductionRecordApi,
  getMaterialBalance as getMaterialBalanceApi,
  calculateMaterialBalance as calculateMaterialBalanceApi,
  uploadLabelVerificationVideo as uploadLabelVerificationVideoApi,
} from '@/lib/api/server/production'

// ============ Batch Actions ============

export async function getBatches(params: BatchQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return getBatchesApi(params, authHeaders)
}

export async function getBatch(id: string) {
  const authHeaders = await getAuthHeaders()
  return getBatchApi(id, authHeaders)
}

export async function createBatch(data: BatchFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await createBatchApi(data, authHeaders)
  revalidatePath('/production/batches')
  return response
}

export async function updateBatch(id: string, data: Partial<BatchFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await updateBatchApi(id, data, authHeaders)
  revalidatePath('/production/batches')
  return response
}

export async function updateBatchStatus(id: string, status: string) {
  const authHeaders = await getAuthHeaders()
  const response = await updateBatchStatusApi(id, status, authHeaders)
  revalidatePath('/production/batches')
  return response
}

export async function deleteBatch(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await deleteBatchApi(id, authHeaders)
  revalidatePath('/production/batches')
  return response
}

// ============ Batch Material Actions ============

export async function getBatchMaterials(batchId: string) {
  const authHeaders = await getAuthHeaders()
  return getBatchMaterialsApi(batchId, authHeaders)
}

export async function addBatchMaterial(batchId: string, data: BatchMaterialFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await addBatchMaterialApi(batchId, data, authHeaders)
  revalidatePath(`/production/batches/${batchId}`)
  return response
}

export async function updateBatchMaterial(id: string, data: Partial<BatchMaterialFormData>) {
  const authHeaders = await getAuthHeaders()
  return updateBatchMaterialApi(id, data, authHeaders)
}

export async function deleteBatchMaterial(id: string) {
  const authHeaders = await getAuthHeaders()
  return deleteBatchMaterialApi(id, authHeaders)
}

// ============ Production Plan Actions ============

export async function getPlans(params: PlanQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return getPlansApi(params, authHeaders)
}

export async function getPlan(id: string) {
  const authHeaders = await getAuthHeaders()
  return getPlanApi(id, authHeaders)
}

export async function createPlan(data: ProductionPlanFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await createPlanApi(data, authHeaders)
  revalidatePath('/production/plan')
  return response
}

export async function updatePlan(id: string, data: Partial<ProductionPlanFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await updatePlanApi(id, data, authHeaders)
  revalidatePath('/production/plan')
  return response
}

export async function deletePlan(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await deletePlanApi(id, authHeaders)
  revalidatePath('/production/plan')
  return response
}

// ============ Plan Task Actions ============

export async function getPlanTasks(planId: string) {
  const authHeaders = await getAuthHeaders()
  return getPlanTasksApi(planId, authHeaders)
}

export async function createPlanTask(data: PlanTaskFormData & { plan_id: string }) {
  const authHeaders = await getAuthHeaders()
  const response = await createPlanTaskApi(data, authHeaders)
  revalidatePath(`/production/plan/${data.plan_id}`)
  return response
}

export async function updatePlanTask(id: string, data: Partial<PlanTaskFormData>) {
  const authHeaders = await getAuthHeaders()
  return updatePlanTaskApi(id, data, authHeaders)
}

export async function deletePlanTask(id: string) {
  const authHeaders = await getAuthHeaders()
  return deletePlanTaskApi(id, authHeaders)
}

// ============ Process Spec Actions ============

export async function getProcessSpecs(params: ProcessSpecQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return getProcessSpecsApi(params, authHeaders)
}

export async function getProcessSpec(id: string) {
  const authHeaders = await getAuthHeaders()
  return getProcessSpecApi(id, authHeaders)
}

export async function createProcessSpec(data: ProcessSpecFormData) {
  const authHeaders = await getAuthHeaders()
  const response = await createProcessSpecApi(data, authHeaders)
  revalidatePath('/production/process')
  return response
}

export async function updateProcessSpec(id: string, data: Partial<ProcessSpecFormData>) {
  const authHeaders = await getAuthHeaders()
  const response = await updateProcessSpecApi(id, data, authHeaders)
  revalidatePath('/production/process')
  return response
}

export async function deleteProcessSpec(id: string) {
  const authHeaders = await getAuthHeaders()
  const response = await deleteProcessSpecApi(id, authHeaders)
  revalidatePath('/production/process')
  return response
}

// ============ Process Step Actions ============

export async function getProcessSteps(specId: string) {
  const authHeaders = await getAuthHeaders()
  return getProcessStepsApi(specId, authHeaders)
}

export async function createProcessStep(data: ProcessStepFormData & { spec_id: string }) {
  const authHeaders = await getAuthHeaders()
  const response = await createProcessStepApi(data, authHeaders)
  revalidatePath(`/production/process/${data.spec_id}`)
  return response
}

export async function updateProcessStep(id: string, data: Partial<ProcessStepFormData>) {
  const authHeaders = await getAuthHeaders()
  return updateProcessStepApi(id, data, authHeaders)
}

export async function deleteProcessStep(id: string) {
  const authHeaders = await getAuthHeaders()
  return deleteProcessStepApi(id, authHeaders)
}

// ============ Process Parameter Actions ============

export async function getProcessParameters(stepId: string) {
  const authHeaders = await getAuthHeaders()
  return getProcessParametersApi(stepId, authHeaders)
}

export async function createProcessParameter(data: ProcessParameterFormData & { step_id: string }) {
  const authHeaders = await getAuthHeaders()
  const response = await createProcessParameterApi(data, authHeaders)
  revalidatePath(`/production/process`)
  return response
}

export async function deleteProcessParameter(id: string) {
  const authHeaders = await getAuthHeaders()
  return deleteProcessParameterApi(id, authHeaders)
}

// ============ Production Record Actions ============

export async function getProductionRecords(batchId: string, page = 1, pageSize = 100) {
  const authHeaders = await getAuthHeaders()
  return getProductionRecordsApi(batchId, page, pageSize, authHeaders)
}

export async function createProductionRecord(data: ProductionRecordFormData & { batch_id: string }) {
  const authHeaders = await getAuthHeaders()
  const response = await createProductionRecordApi(data, authHeaders)
  revalidatePath(`/production/records`)
  return response
}

export async function updateProductionRecord(id: string, data: Partial<ProductionRecordFormData>) {
  const authHeaders = await getAuthHeaders()
  return updateProductionRecordApi(id, data, authHeaders)
}

export async function deleteProductionRecord(id: string) {
  const authHeaders = await getAuthHeaders()
  return deleteProductionRecordApi(id, authHeaders)
}

// ============ Material Balance Actions ============

export async function getMaterialBalance(batchId: string) {
  const authHeaders = await getAuthHeaders()
  return getMaterialBalanceApi(batchId, authHeaders)
}

export async function calculateMaterialBalance(batchId: string, minBalanceRate = 95.0) {
  const authHeaders = await getAuthHeaders()
  const response = await calculateMaterialBalanceApi(batchId, minBalanceRate, authHeaders)
  revalidatePath(`/production/balance`)
  return response
}

// Label Verification Video Upload
export async function uploadLabelVerificationVideo(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await uploadLabelVerificationVideoApi(formData)
  revalidatePath('/production/label-verification')
  return response
}