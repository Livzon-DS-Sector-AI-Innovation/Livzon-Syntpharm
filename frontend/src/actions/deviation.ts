/**
 * 偏差管理 Server Actions
 */
'use server'

import { revalidatePath } from 'next/cache'
import { DeviationCreate, DeviationUpdate, InvestigationCreate, CorrectionCreate, ClosingCreate } from '@/types/deviation'
import {
  createDeviationFlow as createDeviationFlowApi,
  updateDeviationFlow as updateDeviationFlowApi,
  submitDeviationFlow as submitDeviationFlowApi,
  uploadDeviationAttachment as uploadDeviationAttachmentApi,
  saveDeviationSetting as saveDeviationSettingApi,
  deleteDeviationSetting as deleteDeviationSettingApi,
  toggleDeviationSetting as toggleDeviationSettingApi,
  setDefaultDeviationTemplate as setDefaultDeviationTemplateApi,
  getDeviations as getDeviationsApi,
  getDeviationById as getDeviationByIdApi,
  createDeviation as createDeviationApi,
  updateDeviation as updateDeviationApi,
  deleteDeviation as deleteDeviationApi,
  submitDeviation as submitDeviationApi,
  approveDeviation as approveDeviationApi,
  lockBatch as lockBatchApi,
  unlockBatch as unlockBatchApi,
  getInvestigations as getInvestigationsApi,
  createInvestigation as createInvestigationApi,
  updateInvestigation as updateInvestigationApi,
  getCorrections as getCorrectionsApi,
  createCorrection as createCorrectionApi,
  updateCorrection as updateCorrectionApi,
  getClosings as getClosingsApi,
  createClosing as createClosingApi,
  updateClosing as updateClosingApi,
  getDeviationStatistics as getDeviationStatisticsApi,
  aiGenerateDescription as aiGenerateDescriptionApi,
  aiAnalyzeImpact as aiAnalyzeImpactApi,
  aiAnalyzeDirectCause as aiAnalyzeDirectCauseApi,
  aiGenerateEmergencyMeasures as aiGenerateEmergencyMeasuresApi,
  aiAnalyzeRootCause as aiAnalyzeRootCauseApi,
  aiGenerateCAPA as aiGenerateCAPAApi,
  aiGeneratePrevention as aiGeneratePreventionApi,
} from '@/lib/api/server/deviation'

// ============ 偏差流程 ============

export async function createDeviationFlow(data: Record<string, unknown>) {
  const result = await createDeviationFlowApi(data)
  revalidatePath('/quality/deviation-flow')
  return result as any
}

export async function updateDeviationFlow(id: string, data: Record<string, unknown>) {
  const result = await updateDeviationFlowApi(id, data)
  revalidatePath('/quality/deviation-flow')
  return result as any
}

export async function submitDeviationFlow(id: string, targetStatus: string) {
  const result = await submitDeviationFlowApi(id, targetStatus)
  revalidatePath('/quality/deviation-flow')
  return result as any
}

export async function uploadDeviationAttachment(deviationId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return uploadDeviationAttachmentApi(deviationId, formData)
}

// ============ 偏差设置 ============

export async function saveDeviationSetting(url: string, method: string, values: Record<string, unknown>) {
  const result = await saveDeviationSettingApi(url, method, values)
  revalidatePath('/quality/deviation-flow/settings')
  return result as any
}

export async function deleteDeviationSetting(url: string) {
  const result = await deleteDeviationSettingApi(url)
  revalidatePath('/quality/deviation-flow/settings')
  return result as any
}

export async function toggleDeviationSetting(url: string) {
  const result = await toggleDeviationSettingApi(url)
  revalidatePath('/quality/deviation-flow/settings')
  return result as any
}

export async function setDefaultDeviationTemplate(templateId: string) {
  const result = await setDefaultDeviationTemplateApi(templateId)
  revalidatePath('/quality/deviation-flow/settings')
  return result as any
}

export async function getDeviations(params?: {
  status?: string
  deviation_type?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}) {
  return getDeviationsApi(params)
}

export async function getDeviationById(id: string) {
  return getDeviationByIdApi(id)
}

export async function createDeviation(data: DeviationCreate) {
  const processedData = {
    ...data,
    occurrence_date: data.occurrence_date && typeof data.occurrence_date === 'object' && 'format' in data.occurrence_date
      ? (data.occurrence_date as { format: (fmt: string) => string }).format('YYYY-MM-DD')
      : data.occurrence_date,
  }
  const result = await createDeviationApi(processedData)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function updateDeviation(id: string, data: DeviationUpdate) {
  const processedData = {
    ...data,
    occurrence_date: data.occurrence_date && typeof data.occurrence_date === 'object' && 'format' in data.occurrence_date
      ? (data.occurrence_date as { format: (fmt: string) => string }).format('YYYY-MM-DD')
      : data.occurrence_date,
  }
  const result = await updateDeviationApi(id, processedData)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function deleteDeviation(id: string) {
  const result = await deleteDeviationApi(id)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function submitDeviation(id: string) {
  const result = await submitDeviationApi(id)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function approveDeviation(id: string, data: { approved: boolean; comment?: string }) {
  const result = await approveDeviationApi(id, data)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function lockBatch(id: string, data: { reason: string }) {
  const result = await lockBatchApi(id, data)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function unlockBatch(id: string) {
  const result = await unlockBatchApi(id)
  revalidatePath('/quality/deviation')
  return result as any
}

// ============ 偏差调查 ============

export async function getInvestigations(params?: { deviation_id?: string; page?: number; page_size?: number }) {
  return getInvestigationsApi(params)
}

export async function createInvestigation(data: InvestigationCreate) {
  const result = await createInvestigationApi(data)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function updateInvestigation(id: string, data: Partial<InvestigationCreate>) {
  const result = await updateInvestigationApi(id, data)
  revalidatePath('/quality/deviation')
  return result as any
}

// ============ 偏差整改 ============

export async function getCorrections(params?: { deviation_id?: string; status?: string; page?: number; page_size?: number }) {
  return getCorrectionsApi(params)
}

export async function createCorrection(data: CorrectionCreate) {
  const result = await createCorrectionApi(data)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function updateCorrection(id: string, data: Partial<CorrectionCreate>) {
  const result = await updateCorrectionApi(id, data)
  revalidatePath('/quality/deviation')
  return result as any
}

// ============ 偏差关闭 ============

export async function getClosings(params?: { deviation_id?: string; page?: number; page_size?: number }) {
  return getClosingsApi(params)
}

export async function createClosing(data: ClosingCreate) {
  const result = await createClosingApi(data)
  revalidatePath('/quality/deviation')
  return result as any
}

export async function updateClosing(id: string, data: Partial<ClosingCreate>) {
  const result = await updateClosingApi(id, data)
  revalidatePath('/quality/deviation')
  return result as any
}

// ============ 统计 ============

export async function getDeviationStatistics() {
  return getDeviationStatisticsApi()
}

// ============ AI辅助功能 ============

export async function aiGenerateDescription(params: {
  deviation_type?: string
  deviation_level?: string
  occurrence_date?: string
  discovering_department?: string
  product_name?: string
  production_batch?: string
  keywords: string
}) {
  return aiGenerateDescriptionApi(params)
}

export async function aiAnalyzeImpact(params: {
  deviation_type?: string
  deviation_level?: string
  occurrence_date?: string
  discovering_department?: string
  product_name?: string
  production_batch?: string
  description?: string
}) {
  return aiAnalyzeImpactApi(params)
}

export async function aiAnalyzeDirectCause(params: {
  deviation_type: string
  description?: string
  product_name?: string
  production_batch?: string
}) {
  return aiAnalyzeDirectCauseApi(params)
}

export async function aiGenerateEmergencyMeasures(params: {
  deviation_type?: string
  deviation_level?: string
  occurrence_date?: string
  discovering_department?: string
  product_name?: string
  production_batch?: string
  description?: string
}) {
  return aiGenerateEmergencyMeasuresApi(params)
}

export async function aiAnalyzeRootCause(params: {
  deviation_type: string
  description?: string
  direct_cause?: string
  root_cause?: string
  investigation_data?: string
}) {
  return aiAnalyzeRootCauseApi(params)
}

export async function aiGenerateCAPA(params: {
  deviation_type: string
  root_cause?: string
  deviation_level?: string
  department?: string
}) {
  return aiGenerateCAPAApi(params)
}

export async function aiGeneratePrevention(params: {
  deviation_type: string
  root_cause?: string
  deviation_level?: string
  department?: string
}) {
  return aiGeneratePreventionApi(params)
}
