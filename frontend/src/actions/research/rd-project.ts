'use server'

import { revalidatePath } from 'next/cache'
import type { components } from '@/types/generated/schema'
import { z } from 'zod'
import {
  RdInitiationCreateSchema,
  RdDeliverableTemplateCreateSchema,
  RdStageDeliverableCreateSchema,
  parse,
  formatZodError
} from '@/lib/validation/schemas'

import {
  RdProject,
  RdMilestone,
  RdStageRecord,
  RdResearchTrack,
  RdResearchFinding,
  RdPilotStudy,
  RdProcessValidation,
  RdRegistrationFiling,
  RdExperimentLog,
  RdReport,
  RdInitiation,
  StageTransitionResult,
} from '@/types/research/rd-project'

import {
  createRdProject as createRdProjectApi,
  updateRdProject as updateRdProjectApi,
  deleteRdProject as deleteRdProjectApi,
  createMilestone as createMilestoneApi,
  updateMilestone as updateMilestoneApi,
  createStage as createStageApi,
  updateStage as updateStageApi,
  createTrack as createTrackApi,
  updateTrack as updateTrackApi,
  createFinding as createFindingApi,
  updateFinding as updateFindingApi,
  doTransition as doTransitionApi,
  createProjectPilotStudy,
  updateProjectPilotStudy,
  createProjectValidation,
  updateProjectValidation,
  createProjectFiling,
  updateProjectFiling,
  createExperimentLog as createExperimentLogApi,
  updateExperimentLog as updateExperimentLogApi,
  createReport as createReportApi,
  updateReport as updateReportApi,
  createInitiation as createInitiationApi,
  updateInitiation as updateInitiationApi,
  createDeliverableTemplate as createDeliverableTemplateApi,
  updateDeliverableTemplate as updateDeliverableTemplateApi,
  deleteDeliverableTemplate as deleteDeliverableTemplateApi,
  createStageDeliverable as createStageDeliverableApi,
  updateStageDeliverable as updateStageDeliverableApi,
  deleteStageDeliverable as deleteStageDeliverableApi,
  publishConclusionVersion as publishConclusionVersionApi,
  generateReport as generateReportApi,
} from '@/lib/api/server/research'

type RdExperimentLogCreate = Omit<components['schemas']['RdExperimentLogCreate'], 'project_id'>
type RdExperimentLogUpdate = components['schemas']['RdExperimentLogUpdate']
type RdReportCreate = Omit<components['schemas']['RdReportCreate'], 'project_id'>
type RdReportUpdate = components['schemas']['RdReportUpdate']
type RdPilotStudyCreate = Omit<components['schemas']['RdPilotStudyCreate'], 'project_id'>
type RdPilotStudyUpdate = components['schemas']['RdPilotStudyUpdate']
type RdProcessValidationCreate = Omit<components['schemas']['RdProcessValidationCreate'], 'project_id'>
type RdProcessValidationUpdate = components['schemas']['RdProcessValidationUpdate']
type RdRegistrationFilingCreate = Omit<components['schemas']['RdRegistrationFilingCreate'], 'project_id'>
type RdRegistrationFilingUpdate = components['schemas']['RdRegistrationFilingUpdate']

// Projects
export async function createRdProject(data: Partial<RdProject>) {
  const result = await createRdProjectApi(data)
  revalidatePath('/research')
  return result
}

export async function updateRdProject(id: string, data: Partial<RdProject>) {
  const result = await updateRdProjectApi(id, data)
  revalidatePath('/research')
  return result
}

export async function deleteRdProject(id: string) {
  await deleteRdProjectApi(id)
  revalidatePath('/research')
}

// Milestones
export async function createMilestone(projectId: string, data: Partial<RdMilestone>) {
  const result = await createMilestoneApi(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updateMilestone(id: string, data: Partial<RdMilestone>) {
  const result = await updateMilestoneApi(id, data)
  revalidatePath('/research')
  return result
}

// Stages
export async function createStage(projectId: string, data: Partial<RdStageRecord>) {
  const result = await createStageApi(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updateStage(id: string, data: Partial<RdStageRecord>) {
  const result = await updateStageApi(id, data)
  revalidatePath('/research')
  return result
}

// Tracks
export async function createTrack(projectId: string, data: Partial<RdResearchTrack>) {
  const result = await createTrackApi(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updateTrack(id: string, data: Partial<RdResearchTrack>) {
  const result = await updateTrackApi(id, data)
  revalidatePath('/research')
  return result
}

// Findings
export async function createFinding(trackId: string, data: Partial<RdResearchFinding>) {
  const result = await createFindingApi(trackId, data)
  revalidatePath('/research')
  return result
}

export async function updateFinding(id: string, data: Partial<RdResearchFinding>) {
  const result = await updateFindingApi(id, data)
  revalidatePath('/research')
  return result
}

// Stage Transitions
export async function doTransition(projectId: string, targetStage: string, reviewNotes?: string): Promise<StageTransitionResult> {
  const result = await doTransitionApi(projectId, targetStage, reviewNotes)
  revalidatePath('/research')
  return result
}

// Pilot Studies
export async function createPilotStudy(projectId: string, data: RdPilotStudyCreate) {
  const result = await createProjectPilotStudy(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updatePilotStudy(id: string, data: RdPilotStudyUpdate) {
  const result = await updateProjectPilotStudy(id, data)
  revalidatePath('/research')
  return result
}

// Process Validations
export async function createValidation(projectId: string, data: RdProcessValidationCreate) {
  const result = await createProjectValidation(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updateValidation(id: string, data: RdProcessValidationUpdate) {
  const result = await updateProjectValidation(id, data)
  revalidatePath('/research')
  return result
}

// Registration Filings
export async function createFiling(projectId: string, data: RdRegistrationFilingCreate) {
  const result = await createProjectFiling(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updateFiling(id: string, data: RdRegistrationFilingUpdate) {
  const result = await updateProjectFiling(id, data)
  revalidatePath('/research')
  return result
}

// Experiment Logs
export async function createExperimentLog(projectId: string, data: RdExperimentLogCreate) {
  const result = await createExperimentLogApi(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updateExperimentLog(id: string, data: RdExperimentLogUpdate) {
  const result = await updateExperimentLogApi(id, data)
  revalidatePath('/research')
  return result
}

// Reports
export async function createReport(projectId: string, data: RdReportCreate) {
  const result = await createReportApi(projectId, data)
  revalidatePath('/research')
  return result
}

export async function updateReport(id: string, data: RdReportUpdate) {
  const result = await updateReportApi(id, data)
  revalidatePath('/research')
  return result
}

// Initiations
export async function createInitiation(projectId: string, data: unknown) {
  const validated = parse(RdInitiationCreateSchema, data)
  const result = await createInitiationApi(projectId, validated)
  revalidatePath('/research')
  return result
}

export async function updateInitiation(id: string, data: unknown) {
  const validated = parse(RdInitiationCreateSchema.partial(), data)
  const result = await updateInitiationApi(id, validated)
  revalidatePath('/research')
  return result
}

// Deliverable Templates
export async function createDeliverableTemplate(data: unknown) {
  const validated = parse(RdDeliverableTemplateCreateSchema, data)
  const result = await createDeliverableTemplateApi(validated)
  revalidatePath('/research')
  return result
}

export async function updateDeliverableTemplate(id: string, data: unknown) {
  const validated = parse(RdDeliverableTemplateCreateSchema.partial(), data)
  const result = await updateDeliverableTemplateApi(id, validated)
  revalidatePath('/research')
  return result
}

export async function deleteDeliverableTemplate(id: string) {
  await deleteDeliverableTemplateApi(id)
  revalidatePath('/research')
}

// Stage Deliverables
export async function createStageDeliverable(projectId: string, data: unknown) {
  const validated = parse(RdStageDeliverableCreateSchema, data)
  const result = await createStageDeliverableApi(projectId, validated)
  revalidatePath('/research')
  return result
}

export async function updateStageDeliverable(id: string, data: unknown) {
  const validated = parse(RdStageDeliverableCreateSchema.partial(), data)
  const result = await updateStageDeliverableApi(id, validated)
  revalidatePath('/research')
  return result
}

export async function deleteStageDeliverable(id: string) {
  await deleteStageDeliverableApi(id)
  revalidatePath('/research')
}

// Conclusion Versions
export async function publishConclusionVersion(trackId: string, data: {
  conclusion?: string
  confidence: string
  change_summary?: string
  evidence_refs?: Record<string, unknown>
}) {
  const result = await publishConclusionVersionApi(trackId, data)
  revalidatePath('/research')
  return result
}

// AI Report Generation
export async function generateReport(data: {
  project_id: string
  deliverable_type: string
  template_id?: string
  additional_context?: string
}): Promise<{ content: string; structure: Record<string, unknown> | null; data_sources: string[] }> {
  const result = await generateReportApi(data)
  revalidatePath('/research')
  return result as { content: string; structure: Record<string, unknown> | null; data_sources: string[] }
}