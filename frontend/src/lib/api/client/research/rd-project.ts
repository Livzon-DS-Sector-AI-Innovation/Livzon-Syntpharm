

import {
  RdProject,
  RdMilestone,
  RdStageRecord,
  RdResearchTrack,
  RdResearchFinding,
  RdPilotStudy,
  RdProcessValidation,
  RdRegistrationFiling,
  RdStageDeliverable,
  RdExperimentLog,
  RdReport,
  RdInitiation,
  StageTransitionCheck,
  RdDeliverableTemplate,
} from '@/types/research/rd-project'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

const API_BASE = '/api/v1'

export async function fetchRdProjects(params: { page?: number; page_size?: number; stage?: string; status?: string; keyword?: string } = {}) {
  const qs = new URLSearchParams()
  if (params.stage) qs.set('stage', params.stage)
  if (params.status) qs.set('status', params.status)
  if (params.keyword) qs.set('keyword', params.keyword)
  qs.set('page', String(params.page || 1))
  qs.set('page_size', String(params.page_size || 20))
  return apiFetchPaginated<RdProject>(`${API_BASE}/research/rd-projects?${qs}`)
}

export async function fetchRdProject(id: string): Promise<RdProject> {
  return apiGet<RdProject>(`${API_BASE}/research/rd-projects/${id}`)
}

export async function fetchMilestones(projectId: string): Promise<RdMilestone[]> {
  const result = await apiGet<RdMilestone[]>(`${API_BASE}/research/projects/${projectId}/milestones`)
  return result || []
}

export async function fetchStages(projectId: string): Promise<RdStageRecord[]> {
  const result = await apiGet<RdStageRecord[]>(`${API_BASE}/research/projects/${projectId}/stages`)
  return result || []
}

export async function fetchTracks(projectId: string): Promise<RdResearchTrack[]> {
  const result = await apiGet<RdResearchTrack[]>(`${API_BASE}/research/projects/${projectId}/tracks`)
  return result || []
}

export async function fetchAllTracks(params: { projectId?: string; trackType?: string } = {}): Promise<any[]> {
  const qs = new URLSearchParams()
  if (params.projectId) qs.set('project_id', params.projectId)
  if (params.trackType) qs.set('track_type', params.trackType)
  const result = await apiGet<any[]>(`${API_BASE}/research/tracks?${qs}`)
  return result || []
}

export async function fetchFindings(trackId: string): Promise<RdResearchFinding[]> {
  const result = await apiGet<RdResearchFinding[]>(`${API_BASE}/research/tracks/${trackId}/findings`)
  return result || []
}

export async function fetchStageTransitionCheck(projectId: string, targetStage: string): Promise<StageTransitionCheck> {
  return apiGet<StageTransitionCheck>(`${API_BASE}/research/rd-projects/${projectId}/transition-check?target_stage=${targetStage}`)
}

export async function fetchPilotStudies(projectId: string): Promise<RdPilotStudy[]> {
  const result = await apiGet<RdPilotStudy[]>(`${API_BASE}/research/pilot-studies?project_id=${projectId}`)
  return result || []
}

export async function fetchValidations(projectId: string): Promise<RdProcessValidation[]> {
  const result = await apiGet<RdProcessValidation[]>(`${API_BASE}/research/process-validations?project_id=${projectId}`)
  return result || []
}

export async function fetchFilings(projectId: string): Promise<RdRegistrationFiling[]> {
  const result = await apiGet<RdRegistrationFiling[]>(`${API_BASE}/research/registration-filings?project_id=${projectId}`)
  return result || []
}

export async function fetchDeliverables(projectId: string, params: { stage?: string; deliverable_type?: string; status?: string } = {}): Promise<RdStageDeliverable[]> {
  const qs = new URLSearchParams()
  qs.set('project_id', projectId)
  if (params.stage) qs.set('stage', params.stage)
  if (params.deliverable_type) qs.set('deliverable_type', params.deliverable_type)
  if (params.status) qs.set('status', params.status)
  const result = await apiGet<RdStageDeliverable[]>(`${API_BASE}/research/rd-stage-deliverables?${qs}`)
  return result || []
}

export async function fetchExperimentLogs(projectId: string): Promise<RdExperimentLog[]> {
  const result = await apiGet<RdExperimentLog[]>(`${API_BASE}/research/experiment-logs?project_id=${projectId}`)
  return result || []
}

export async function fetchReports(projectId: string): Promise<RdReport[]> {
  const result = await apiGet<RdReport[]>(`${API_BASE}/research/reports?project_id=${projectId}`)
  return result || []
}


export async function fetchInitiations(projectId: string): Promise<RdInitiation[]> {
  const result = await apiGet<RdInitiation[]>(`${API_BASE}/research/initiations?project_id=${projectId}`)
  return result || []
}

export async function fetchTrackDetail(trackId: string): Promise<RdResearchTrack> {
  return apiGet<RdResearchTrack>(`${API_BASE}/research/tracks/${trackId}`)
}

export async function fetchConclusionVersions(trackId: string): Promise<any[]> {
  const result = await apiGet<any[]>(`${API_BASE}/research/tracks/${trackId}/conclusion-versions`)
  return result || []
}

export interface RdStatsOverview {
  projects: {
    total: number
    by_stage: Record<string, number>
    by_status: Record<string, number>
  }
  tracks: {
    total: number
    by_type: Record<string, number>
  }
  experiments: {
    total: number
  }
  deliverables: {
    total: number
    by_status: Record<string, number>
  }
}

export interface RdProjectProgress {
  id: string
  name: string
  current_stage: string | null
  status: string
  progress: number
  start_date: string | null
  target_filing_date: string | null
}

export async function fetchStatsOverview(): Promise<RdStatsOverview> {
  return apiGet<RdStatsOverview>(`${API_BASE}/research/stats/overview`)
}

export async function fetchProjectProgress(): Promise<RdProjectProgress[]> {
  return apiGet<RdProjectProgress[]>(`${API_BASE}/research/stats/project-progress`)
}

export async function fetchDeliverableTemplates(params: {
  stage?: string
  deliverable_type?: string
  is_active?: boolean
} = {}): Promise<RdDeliverableTemplate[]> {
  const qs = new URLSearchParams()
  if (params.stage) qs.set('stage', params.stage)
  if (params.deliverable_type) qs.set('deliverable_type', params.deliverable_type)
  if (params.is_active !== undefined) qs.set('is_active', String(params.is_active))
  const result = await apiGet<RdDeliverableTemplate[]>(`${API_BASE}/research/deliverable-templates?${qs}`)
  return result || []
}
