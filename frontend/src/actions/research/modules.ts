'use server'

import { revalidatePath } from 'next/cache'
import {
  createPilotStudyDirect,
  updatePilotStudyDirect,
  deletePilotStudyDirect,
  createValidationDirect,
  updateValidationDirect,
  deleteValidationDirect,
  createFilingDirect,
  updateFilingDirect,
  deleteFilingDirect,
  deleteExperimentLog,
  deleteReport,
  deleteInitiation,
  deleteTrack,
  deleteFinding,
} from '@/lib/api/server/research'

// ===== 中试研究 =====

export async function createPilotStudy(data: {
  project_id: string
  batch_no?: string
  batch_size?: number
  status?: string
  material_balance?: Record<string, unknown>
  equipment_selection?: Record<string, unknown>
  engineering_calc?: Record<string, unknown>
  ehs_assessment?: Record<string, unknown>
  scale_up_effect?: Record<string, unknown>
  notes?: string
}) {
  const result = await createPilotStudyDirect(data)
  revalidatePath('/research/projects')
  return result
}

export async function updatePilotStudy(id: string, data: {
  batch_no?: string
  batch_size?: number
  status?: string
  material_balance?: Record<string, unknown>
  equipment_selection?: Record<string, unknown>
  engineering_calc?: Record<string, unknown>
  ehs_assessment?: Record<string, unknown>
  scale_up_effect?: Record<string, unknown>
  notes?: string
}) {
  const result = await updatePilotStudyDirect(id, data)
  revalidatePath('/research/projects')
  return result
}

export async function deletePilotStudy(id: string) {
  await deletePilotStudyDirect(id)
  revalidatePath('/research/projects')
}

// ===== 工艺验证 =====

export async function createValidation(data: {
  project_id: string
  status?: string
  validation_protocol?: Record<string, unknown>
  validation_batches?: Record<string, unknown>
  statistical_analysis?: Record<string, unknown>
  validation_conclusion?: string
  notes?: string
}) {
  const result = await createValidationDirect(data)
  revalidatePath('/research/projects')
  return result
}

export async function updateValidation(id: string, data: {
  status?: string
  validation_protocol?: Record<string, unknown>
  validation_batches?: Record<string, unknown>
  statistical_analysis?: Record<string, unknown>
  validation_conclusion?: string
  notes?: string
}) {
  const result = await updateValidationDirect(id, data)
  revalidatePath('/research/projects')
  return result
}

export async function deleteValidation(id: string) {
  await deleteValidationDirect(id)
  revalidatePath('/research/projects')
}

// ===== 申报资料 =====

export async function createFiling(data: {
  project_id: string
  status?: string
  ctd_structure?: Record<string, unknown>
  filing_progress?: Record<string, unknown>
  supplementary_docs?: Record<string, unknown>
  notes?: string
}) {
  const result = await createFilingDirect(data)
  revalidatePath('/research/projects')
  return result
}

export async function updateFiling(id: string, data: {
  status?: string
  ctd_structure?: Record<string, unknown>
  filing_progress?: Record<string, unknown>
  supplementary_docs?: Record<string, unknown>
  notes?: string
}) {
  const result = await updateFilingDirect(id, data)
  revalidatePath('/research/projects')
  return result
}

export async function deleteFiling(id: string) {
  await deleteFilingDirect(id)
  revalidatePath('/research/projects')
}

export { deleteExperimentLog, deleteReport, deleteInitiation, deleteTrack, deleteFinding }