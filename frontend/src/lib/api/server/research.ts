import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { OptimizationCreate, OptimizationUpdate, ProcessOptimization, RouteCreate, RouteUpdate, RouteDevelopment } from '@/types/research'
import type { components } from '@/types/generated/schema'

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

async function uploadFetch<T>(url: string, formData: FormData): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${getApiBaseUrl()}${url}`
  const response = await fetch(fullUrl, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!response.ok) {
    const errorBody = await response.text().catch(() => '')
    let errorMessage = `上传失败: ${response.status} ${response.statusText}`
    try {
      const errorJson = JSON.parse(errorBody)
      if (errorJson.message) errorMessage = errorJson.message
    } catch {}
    throw new Error(errorMessage)
  }
  const result = await response.json()
  return result.data ?? result
}

// ===== deliverables.ts =====

export async function createDeliverable(data: {
  project_id: string
  stage: string
  deliverable_type: string
  title: string
  status?: string
  version?: string
  content?: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-stage-deliverables`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDeliverable(id: string, data: {
  title?: string
  status?: string
  version?: string
  content?: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-stage-deliverables/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDeliverable(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/rd-stage-deliverables/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    const errorBody = await response.text().catch(() => '')
    throw new Error(`请求失败: ${response.status} ${response.statusText} - ${errorBody}`)
  }
}

export async function uploadDeliverableFile(deliverableId: string, formData: FormData) {
  return uploadFetch(`${getApiBaseUrl()}/api/v1/research/rd-stage-deliverables/${deliverableId}/upload`, formData)
}

// ===== modules.ts - Pilot Studies =====

export async function createPilotStudyDirect(data: {
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
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-pilot-studies`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updatePilotStudyDirect(id: string, data: {
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
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-pilot-studies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deletePilotStudyDirect(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/rd-pilot-studies/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    const errorBody = await response.text().catch(() => '')
    throw new Error(`请求失败: ${response.status} ${response.statusText} - ${errorBody}`)
  }
}

// ===== modules.ts - Process Validations =====

export async function createValidationDirect(data: {
  project_id: string
  status?: string
  validation_protocol?: Record<string, any>
  validation_batches?: Record<string, any>
  statistical_analysis?: Record<string, any>
  validation_conclusion?: string
  notes?: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-process-validations`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateValidationDirect(id: string, data: {
  status?: string
  validation_protocol?: Record<string, any>
  validation_batches?: Record<string, any>
  statistical_analysis?: Record<string, any>
  validation_conclusion?: string
  notes?: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-process-validations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteValidationDirect(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/rd-process-validations/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== modules.ts - Registration Filings =====

export async function createFilingDirect(data: {
  project_id: string
  status?: string
  ctd_structure?: Record<string, any>
  filing_progress?: Record<string, any>
  supplementary_docs?: Record<string, any>
  notes?: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-registration-filings`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateFilingDirect(id: string, data: {
  status?: string
  ctd_structure?: Record<string, any>
  filing_progress?: Record<string, any>
  supplementary_docs?: Record<string, any>
  notes?: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-registration-filings/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteFilingDirect(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/rd-registration-filings/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== modules.ts - Deletes =====

export async function deleteExperimentLog(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/experiment-logs/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

export async function deleteReport(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/reports/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

export async function deleteInitiation(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/initiations/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

export async function deleteTrack(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/projects/tracks/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

export async function deleteFinding(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/findings/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== process-optimization.ts =====

export async function createOptimization(data: OptimizationCreate) {
  return apiFetch<ProcessOptimization>(`${getApiBaseUrl()}/api/v1/research/optimizations`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateOptimization(id: string, data: OptimizationUpdate) {
  return apiFetch<ProcessOptimization>(`${getApiBaseUrl()}/api/v1/research/optimizations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteOptimization(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/optimizations/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== route-development.ts =====

export async function createRoute(data: RouteCreate) {
  return apiFetch<RouteDevelopment>(`${getApiBaseUrl()}/api/v1/research/routes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateRoute(id: string, data: RouteUpdate) {
  return apiFetch<RouteDevelopment>(`${getApiBaseUrl()}/api/v1/research/routes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteRoute(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/routes/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== rd-project.ts - Projects =====

export async function createRdProject(data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateRdProject(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteRdProject(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/rd-projects/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== rd-project.ts - Milestones =====

export async function createMilestone(projectId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/milestones`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateMilestone(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/milestones/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Stages =====

export async function createStage(projectId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/stages`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStage(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/stages/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Tracks =====

export async function createTrack(projectId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/tracks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTrack(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/tracks/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Findings =====

export async function createFinding(trackId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/tracks/${trackId}/findings`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateFinding(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/findings/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Stage Transitions =====

export async function doTransition(projectId: string, targetStage: string, reviewNotes?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/stage-transitions`, {
    method: 'POST',
    body: JSON.stringify({ target_stage: targetStage, review_notes: reviewNotes }),
  })
}

// ===== rd-project.ts - Pilot Studies (nested) =====

export async function createProjectPilotStudy(projectId: string, data: RdPilotStudyCreate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/pilot-studies`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProjectPilotStudy(id: string, data: RdPilotStudyUpdate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/pilot-studies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Process Validations (nested) =====

export async function createProjectValidation(projectId: string, data: RdProcessValidationCreate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/process-validations`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProjectValidation(id: string, data: RdProcessValidationUpdate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/process-validations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Registration Filings (nested) =====

export async function createProjectFiling(projectId: string, data: RdRegistrationFilingCreate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/registration-filings`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProjectFiling(id: string, data: RdRegistrationFilingUpdate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/registration-filings/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Experiment Logs =====

export async function createExperimentLog(projectId: string, data: RdExperimentLogCreate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/experiment-logs`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateExperimentLog(id: string, data: RdExperimentLogUpdate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/experiment-logs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Reports =====

export async function createReport(projectId: string, data: RdReportCreate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/reports`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateReport(id: string, data: RdReportUpdate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/reports/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Initiations =====

export async function createInitiation(projectId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/initiations`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateInitiation(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/initiations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - Deliverable Templates =====

export async function createDeliverableTemplate(data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/deliverable-templates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDeliverableTemplate(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/deliverable-templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDeliverableTemplate(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/deliverable-templates/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== rd-project.ts - Stage Deliverables =====

export async function createStageDeliverable(projectId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}/stage-deliverables`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStageDeliverable(id: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/stage-deliverables/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteStageDeliverable(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/stage-deliverables/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== rd-project.ts - Conclusion Versions =====

export async function publishConclusionVersion(trackId: string, data: {
  conclusion?: string
  confidence: string
  change_summary?: string
  evidence_refs?: Record<string, unknown>
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/tracks/${trackId}/conclusion-versions`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ===== rd-project.ts - AI Report Generation =====

export async function generateReport(data: {
  project_id: string
  deliverable_type: string
  template_id?: string
  additional_context?: string
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/generate-report`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ===== research.ts - Projects =====

export async function createResearchProject(data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateResearchProject(projectId: string, data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteResearchProject(projectId: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== research.ts - Pilot Workflow =====

export async function createPilotWorkflow(data: any) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/pilot/workflow`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function startPilotWorkflow(workflowId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/pilot/workflow/${workflowId}/start`, {
    method: 'POST',
  })
}

export async function approvePilotWorkflowStep(workflowId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/pilot/workflow/${workflowId}/approve`, {
    method: 'POST',
  })
}

export async function uploadPilotWorkflowDocument(workflowId: string, formData: FormData) {
  return uploadFetch(`${getApiBaseUrl()}/api/v1/research/pilot/workflow/${workflowId}/upload`, formData)
}

export async function deletePilotWorkflow(workflowId: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/pilot/workflow/${workflowId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
}

// ===== research.ts - Fetch functions =====

export async function fetchResearchProjects(params: any = {}) {
  const searchParams = new URLSearchParams()
  if (params.keyword) searchParams.set('keyword', params.keyword)
  if (params.status) searchParams.set('status', params.status)
  searchParams.set('page', String(params.page || 1))
  searchParams.set('page_size', String(params.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects?${searchParams.toString()}`)
}

export async function fetchRoutes(params: any = {}) {
  const searchParams = new URLSearchParams()
  if (params.project_id) searchParams.set('project_id', params.project_id)
  if (params.status) searchParams.set('status', params.status)
  if (params.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params.page || 1))
  searchParams.set('page_size', String(params.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/routes?${searchParams.toString()}`)
}

export async function fetchPilotWorkflows(params: any = {}) {
  const searchParams = new URLSearchParams()
  if (params.status) searchParams.set('status', params.status)
  if (params.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params.page || 1))
  searchParams.set('page_size', String(params.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/pilot/workflow?${searchParams.toString()}`)
}

export async function fetchPilotWorkflow(workflowId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/pilot/workflow/${workflowId}`)
}

export async function fetchResearchProject(projectId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/projects/${projectId}`)
}

// ===== research.ts - ICH =====

export async function analyzeICHFile(formData: FormData) {
  return uploadFetch(`${getApiBaseUrl()}/api/v1/research/ich/analyze?use_llm=true`, formData)
}

export async function deleteICHRecord(recordId: string) {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/research/ich/records/${recordId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new Error('删除失败')
  }
  return response.json()
}

// ===== research.ts - EDBO =====

export async function runEDBOOptimize(formData: FormData) {
  return uploadFetch(`${getApiBaseUrl()}/api/v1/research/edbo/optimize`, formData)
}

export async function generateReactionScope(data: {
  components: Record<string, (string | number)[]>
  objectives: string[]
  batch_size: number
}) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/edbo/generate-scope`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ===== research.ts - Literature =====

export async function analyzeLiterature(formData: FormData) {
  return uploadFetch(`${getApiBaseUrl()}/api/v1/research/literature/analyze`, formData)
}