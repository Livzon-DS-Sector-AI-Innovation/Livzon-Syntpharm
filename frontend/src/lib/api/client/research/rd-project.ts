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
  StageTransitionResult,
  RdDeliverableTemplate,
} from '@/types/research/rd-project'

const API_BASE = '/api/v1'

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    const message = json?.message || `请求失败: ${res.status}`
    throw new Error(message)
  }
  const json = await res.json()
  return json.data
}

async function apiFetchList<T>(url: string): Promise<T[]> {
  const res = await fetch(url)
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    const message = json?.message || `请求失败: ${res.status}`
    throw new Error(message)
  }
  const json = await res.json()
  return json.data || []
}

// RdProject
export async function fetchRdProjects(params: { page?: number; page_size?: number; stage?: string; status?: string; keyword?: string } = {}) {
  const qs = new URLSearchParams()
  if (params.stage) qs.set('stage', params.stage)
  if (params.status) qs.set('status', params.status)
  if (params.keyword) qs.set('keyword', params.keyword)
  qs.set('page', String(params.page || 1))
  qs.set('page_size', String(params.page_size || 20))
  const res = await fetch(`${API_BASE}/research/rd-projects?${qs}`)
  const json = await res.json()
  return { items: json.data || [], total: json.meta?.total || 0, page: json.meta?.page || 1, page_size: json.meta?.page_size || 20 }
}

export async function fetchRdProject(id: string): Promise<RdProject> {
  return apiFetch<RdProject>(`${API_BASE}/research/rd-projects/${id}`)
}

// Milestones
export async function fetchMilestones(projectId: string): Promise<RdMilestone[]> {
  return apiFetchList<RdMilestone>(`${API_BASE}/research/projects/${projectId}/milestones`)
}

// Stage Records
export async function fetchStages(projectId: string): Promise<RdStageRecord[]> {
  return apiFetchList<RdStageRecord>(`${API_BASE}/research/projects/${projectId}/stages`)
}

// Research Tracks
export async function fetchTracks(projectId: string): Promise<RdResearchTrack[]> {
  return apiFetchList<RdResearchTrack>(`${API_BASE}/research/projects/${projectId}/tracks`)
}

export async function fetchAllTracks(params: { projectId?: string; trackType?: string } = {}): Promise<any[]> {
  const qs = new URLSearchParams()
  if (params.projectId) qs.set('project_id', params.projectId)
  if (params.trackType) qs.set('track_type', params.trackType)
  const res = await fetch(`${API_BASE}/research/tracks?${qs}`)
  const json = await res.json()
  return json.data || []
}

// Research Findings
export async function fetchFindings(trackId: string): Promise<RdResearchFinding[]> {
  return apiFetchList<RdResearchFinding>(`${API_BASE}/research/tracks/${trackId}/findings`)
}

// Stage Transition
export async function fetchStageTransitionCheck(projectId: string, targetStage: string): Promise<StageTransitionCheck> {
  return apiFetch<StageTransitionCheck>(`${API_BASE}/research/rd-projects/${projectId}/transition-check?target_stage=${targetStage}`)
}

// ===== 中试研究 API =====

export async function fetchPilotStudies(projectId: string): Promise<RdPilotStudy[]> {
  return apiFetchList<RdPilotStudy>(`${API_BASE}/research/pilot-studies?project_id=${projectId}`)
}

// ===== 工艺验证 API =====

export async function fetchValidations(projectId: string): Promise<RdProcessValidation[]> {
  return apiFetchList<RdProcessValidation>(`${API_BASE}/research/process-validations?project_id=${projectId}`)
}

// ===== 申报资料 API =====

export async function fetchFilings(projectId: string): Promise<RdRegistrationFiling[]> {
  return apiFetchList<RdRegistrationFiling>(`${API_BASE}/research/registration-filings?project_id=${projectId}`)
}

// ===== 阶段交付物 API =====

export async function fetchDeliverables(projectId: string, params: { stage?: string; deliverable_type?: string; status?: string } = {}): Promise<RdStageDeliverable[]> {
  const qs = new URLSearchParams()
  qs.set('project_id', projectId)
  if (params.stage) qs.set('stage', params.stage)
  if (params.deliverable_type) qs.set('deliverable_type', params.deliverable_type)
  if (params.status) qs.set('status', params.status)
  return apiFetchList<RdStageDeliverable>(`${API_BASE}/research/rd-stage-deliverables?${qs}`)
}


// ===== 实验记录 API =====


export async function fetchExperimentLogs(projectId: string): Promise<RdExperimentLog[]> {
  return apiFetchList<RdExperimentLog>(`${API_BASE}/research/experiment-logs?project_id=${projectId}`)
}

// ===== 研发报告 API =====

export async function fetchReports(projectId: string): Promise<RdReport[]> {
  return apiFetchList<RdReport>(`${API_BASE}/research/reports?project_id=${projectId}`)
}

// ===== 立项申请 API =====

type RdInitiationCreate = Omit<RdInitiation, 'id' | 'created_at' | 'updated_at'>
type RdInitiationUpdate = Partial<Omit<RdInitiation, 'id' | 'project_id' | 'created_at' | 'updated_at'>>

export async function fetchInitiations(projectId: string): Promise<RdInitiation[]> {
  return apiFetchList<RdInitiation>(`${API_BASE}/research/initiations?project_id=${projectId}`)
}

// ===== 研究项详情 API =====

export async function fetchTrackDetail(trackId: string): Promise<RdResearchTrack> {
  return apiFetch<RdResearchTrack>(`${API_BASE}/research/tracks/${trackId}`)
}

export async function fetchConclusionVersions(trackId: string): Promise<any[]> {
  return apiFetchList<any>(`${API_BASE}/research/tracks/${trackId}/conclusion-versions`)
}

// ===== 统计报表 API =====

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
  return apiFetch<RdStatsOverview>(`${API_BASE}/research/stats/overview`)
}

export async function fetchProjectProgress(): Promise<RdProjectProgress[]> {
  return apiFetch<RdProjectProgress[]>(`${API_BASE}/research/stats/project-progress`)
}

// ===== 交付物模板 API =====

export async function fetchDeliverableTemplates(params: {
  stage?: string
  deliverable_type?: string
  is_active?: boolean
} = {}): Promise<RdDeliverableTemplate[]> {
  const qs = new URLSearchParams()
  if (params.stage) qs.set('stage', params.stage)
  if (params.deliverable_type) qs.set('deliverable_type', params.deliverable_type)
  if (params.is_active !== undefined) qs.set('is_active', String(params.is_active))
  return apiFetchList<RdDeliverableTemplate>(`${API_BASE}/research/deliverable-templates?${qs}`)
}

// ===== AI 报告生成 API =====

