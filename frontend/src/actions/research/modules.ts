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
  material_balance?: Record<string, any>
  equipment_selection?: Record<string, any>
  engineering_calc?: Record<string, any>
  ehs_assessment?: Record<string, any>
  scale_up_effect?: Record<string, any>
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
  material_balance?: Record<string, any>
  equipment_selection?: Record<string, any>
  engineering_calc?: Record<string, any>
  ehs_assessment?: Record<string, any>
  scale_up_effect?: Record<string, any>
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
  validation_protocol?: Record<string, any>
  validation_batches?: Record<string, any>
  statistical_analysis?: Record<string, any>
  validation_conclusion?: string
  notes?: string
}) {
  const result = await createValidationDirect(data)
  revalidatePath('/research/projects')
  return result
}

export async function updateValidation(id: string, data: {
  status?: string
  validation_protocol?: Record<string, any>
  validation_batches?: Record<string, any>
  statistical_analysis?: Record<string, any>
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
  ctd_structure?: Record<string, any>
  filing_progress?: Record<string, any>
  supplementary_docs?: Record<string, any>
  notes?: string
}) {
  const result = await createFilingDirect(data)
  revalidatePath('/research/projects')
  return result
}

export async function updateFiling(id: string, data: {
  status?: string
  ctd_structure?: Record<string, any>
  filing_progress?: Record<string, any>
  supplementary_docs?: Record<string, any>
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