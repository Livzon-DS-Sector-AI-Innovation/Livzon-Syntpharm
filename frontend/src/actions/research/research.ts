'use server'

import { revalidatePath } from 'next/cache'
import { ResearchProjectCreate, ResearchProjectUpdate } from '@/types/research'
import type { EDBOOptimizeResponse } from '@/types/research'
import {
  createResearchProject as createResearchProjectApi,
  updateResearchProject as updateResearchProjectApi,
  deleteResearchProject as deleteResearchProjectApi,
  createPilotWorkflow as createPilotWorkflowApi,
  startPilotWorkflow as startPilotWorkflowApi,
  approvePilotWorkflowStep as approvePilotWorkflowStepApi,
  uploadPilotWorkflowDocument as uploadPilotWorkflowDocumentApi,
  deletePilotWorkflow as deletePilotWorkflowApi,
  fetchResearchProjects as fetchResearchProjectsApi,
  fetchRoutes as fetchRoutesApi,
  fetchPilotWorkflows as fetchPilotWorkflowsApi,
  fetchPilotWorkflow as fetchPilotWorkflowApi,
  analyzeICHFile as analyzeICHFileApi,
  deleteICHRecord as deleteICHRecordApi,
  runEDBOOptimize as runEDBOOptimizeApi,
  generateReactionScope as generateReactionScopeApi,
  fetchResearchProject as fetchResearchProjectApi,
  analyzeLiterature as analyzeLiteratureApi,
} from '@/lib/api/server/research'

export async function createResearchProject(data: ResearchProjectCreate) {
  const result = await createResearchProjectApi(data)
  revalidatePath('/research')
  return result
}

export async function updateResearchProject(projectId: string, data: ResearchProjectUpdate) {
  const result = await updateResearchProjectApi(projectId, data)
  revalidatePath('/research')
  return result
}

export async function deleteResearchProject(projectId: string) {
  await deleteResearchProjectApi(projectId)
  revalidatePath('/research')
}

// ===== Pilot Workflow Server Actions =====

export async function createPilotWorkflow(data: {
  product_name: string
  scale_up_ratio: number
  equipment_type: string
  equipment_volume: number
  project_id?: string
  input_context?: Record<string, unknown>
}) {
  const result = await createPilotWorkflowApi(data)
  revalidatePath('/research/pilot-workflow')
  return result
}

export async function startPilotWorkflow(workflowId: string) {
  const result = await startPilotWorkflowApi(workflowId)
  revalidatePath(`/research/pilot-workflow/${workflowId}`)
  revalidatePath('/research/pilot-workflow')
  return result
}

export async function approvePilotWorkflowStep(workflowId: string) {
  const result = await approvePilotWorkflowStepApi(workflowId)
  revalidatePath(`/research/pilot-workflow/${workflowId}`)
  revalidatePath('/research/pilot-workflow')
  return result
}

export async function uploadPilotWorkflowDocument(workflowId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const result = await uploadPilotWorkflowDocumentApi(workflowId, formData)
  revalidatePath(`/research/pilot-workflow/${workflowId}`)
  return result
}

export async function deletePilotWorkflow(workflowId: string) {
  await deletePilotWorkflowApi(workflowId)
  revalidatePath('/research/pilot-workflow')
}

// ─── Server-side fetch functions (for Server Components) ───

export async function fetchResearchProjects(params: any = {}): Promise<any> {
  return fetchResearchProjectsApi(params)
}

export async function fetchRoutes(params: any = {}): Promise<any> {
  return fetchRoutesApi(params)
}

export async function fetchPilotWorkflows(params: any = {}): Promise<any> {
  const json = await fetchPilotWorkflowsApi(params) as any
  return {
    items: json.data || [],
    total: json.meta?.total || 0,
    page: json.meta?.page || 1,
    page_size: json.meta?.page_size || 20,
  }
}

export async function fetchPilotWorkflow(workflowId: string): Promise<any> {
  const json = await fetchPilotWorkflowApi(workflowId) as any
  return json.data
}

// ICH Analysis Actions
export async function analyzeICHFile(file: File): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await analyzeICHFileApi(formData)
  revalidatePath('/research')
  return result
}

export async function deleteICHRecord(recordId: string): Promise<any> {
  const result = await deleteICHRecordApi(recordId)
  revalidatePath('/research')
  return result
}

// ── EDBO+ 贝叶斯优化 ──

export async function runEDBOOptimize(
  file: File,
  objectives: string[],
  objectiveModes: ('max' | 'min')[],
  batchSize: number,
  savePrediction: boolean = false
): Promise<EDBOOptimizeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('objectives', objectives.join(','))
  formData.append('objective_modes', objectiveModes.join(','))
  formData.append('batch_size', String(batchSize))
  formData.append('save_prediction', String(savePrediction))
  const result = await runEDBOOptimizeApi(formData)
  return result as EDBOOptimizeResponse
}

export async function generateReactionScope(
  components: Record<string, (string | number)[]>,
  objectives: string[] = [],
  batchSize: number = 5
): Promise<{
    csv_data: string;
    row_count: number;
    columns: string[];
    recommended_experiments?: string;
    optimization_completed?: boolean;
    optimization_error?: string;
  }> {
  const result = await generateReactionScopeApi({ components, objectives, batch_size: batchSize })
  return result
}

export async function fetchResearchProject(projectId: string): Promise<any> {
  return fetchResearchProjectApi(projectId)
}

// ─── Literature Analysis Actions ───

export async function analyzeLiterature(file: File): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await analyzeLiteratureApi(formData)
  revalidatePath('/research')
  return result
}