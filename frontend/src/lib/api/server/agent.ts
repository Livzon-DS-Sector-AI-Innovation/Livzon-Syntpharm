/**
 * 智能体 - PPT 配音视频：Server Component / Server Action 取数。
 *
 * 约定：
 * - 一律走 `apiFetch`（内部处理 API_BASE_URL、cookie→Bearer、403 语义）；
 * - 列表接口的 total 在信封 meta 里、items 在 data 里，不能直接用 apiFetchPaginated；
 * - 上传用 FormData 透传，不要 JSON.stringify。
 */
import { apiFetch, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'
import type {
  AiConfigFormValue,
  AiConfigListResponse,
  AiConfigTestResponse,
  EditableShapeList,
  ProjectDetail,
  ProjectPage,
  ProjectSummary,
  RevisionItem,
  ScriptRewritePayload,
  ScriptRewriteResult,
  SlideEditResult,
  SourceApplyResult,
  SourceDiffSummary,
  VersionItem,
  VersionManifest,
  VoiceOption,
} from '@/types/agent/ppt-video'

interface Envelope<T> {
  code: number
  data: T
  message?: string
  meta?: { total?: number; page?: number; page_size?: number }
}

const API = '/api/v1/agent'

export interface ProjectQuery {
  keyword?: string
  status?: string
  language?: string
  page?: number
  page_size?: number
}

function buildQuery(params: ProjectQuery): string {
  const qs = new URLSearchParams()
  if (params.keyword) qs.set('keyword', params.keyword)
  if (params.status) qs.set('status', params.status)
  if (params.language) qs.set('language', params.language)
  qs.set('page', String(params.page ?? 1))
  qs.set('page_size', String(params.page_size ?? 20))
  return qs.toString()
}

export async function fetchPptVideoProjects(params: ProjectQuery = {}): Promise<ProjectPage> {
  const raw = await apiFetch<Envelope<{ items: ProjectSummary[] }>>(
    `${getApiBaseUrl()}${API}/ppt-videos?${buildQuery(params)}`,
  )
  return { items: raw.data?.items ?? [], total: raw.meta?.total ?? raw.data?.items?.length ?? 0 }
}

export async function fetchPptVideoProject(projectId: string): Promise<ProjectDetail> {
  return apiFetch<Envelope<ProjectDetail>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}`).then(unwrapResponse)
}

export async function fetchVoiceCatalog(language?: 'zh' | 'en'): Promise<VoiceOption[]> {
  const suffix = language ? `?language=${language}` : ''
  const raw = await apiFetch<Envelope<{ items: VoiceOption[] }>>(`${getApiBaseUrl()}${API}/voices${suffix}`)
  return raw.data?.items ?? []
}

export async function fetchVersionManifest(versionId: string): Promise<VersionManifest> {
  return apiFetch<Envelope<VersionManifest>>(
    `${getApiBaseUrl()}${API}/ppt-videos/versions/${versionId}/manifest`,
  ).then(unwrapResponse)
}

export async function fetchVersionList(projectId: string): Promise<VersionItem[]> {
  return apiFetch<Envelope<VersionItem[]>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/versions`).then(
    unwrapResponse,
  )
}

/** 上传 PPT + 可选讲稿：formData 直接透传，由后端做格式与大小校验 */
export async function createPptVideoProjectRequest(formData: FormData): Promise<Envelope<ProjectDetail>> {
  return apiFetch<Envelope<ProjectDetail>>(`${getApiBaseUrl()}${API}/ppt-videos`, {
    method: 'POST',
    body: formData,
  })
}

export async function updateProjectRequest(
  projectId: string,
  payload: Record<string, unknown>,
): Promise<Envelope<ProjectDetail>> {
  return apiFetch<Envelope<ProjectDetail>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateSlideRequest(
  projectId: string,
  slideUid: string,
  payload: Record<string, unknown>,
): Promise<Envelope<unknown>> {
  return apiFetch<Envelope<unknown>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function previewSlideRequest(
  projectId: string,
  slideUid: string,
): Promise<Envelope<{ audio_url: string; duration_ms: number; audio_sha256: string; slide_no: number }>> {
  return apiFetch(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/preview`, {
    method: 'POST',
  })
}

/** 重新生成 AI 讲稿初稿：只填空页，202 返回最新详情 */
export async function regenerateScriptAiRequest(projectId: string): Promise<Envelope<ProjectDetail>> {
  return apiFetch<Envelope<ProjectDetail>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/script-ai`, {
    method: 'POST',
  })
}

export async function requestRenderRequest(projectId: string): Promise<Envelope<{ job_id: string }>> {
  return apiFetch(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/render`, { method: 'POST' })
}

export async function deleteProjectRequest(projectId: string): Promise<Envelope<{ message: string }>> {
  return apiFetch(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}`, { method: 'DELETE' })
}

// ── AI 配置 ────────────────────────────────────────────────────────────────
//
// 注意路径是 /ai-configs 而不是 /ppt-videos/ai-config：
// 后端 /ppt-videos/{project_id} 的 {project_id} 是 UUID，会把字面量路由吃掉。

export async function fetchAiConfigs(): Promise<AiConfigListResponse> {
  return apiFetch<Envelope<AiConfigListResponse>>(`${getApiBaseUrl()}${API}/ai-configs`).then(unwrapResponse)
}

export async function createAiConfigRequest(payload: AiConfigFormValue): Promise<Envelope<AiConfigListResponse>> {
  return apiFetch<Envelope<AiConfigListResponse>>(`${getApiBaseUrl()}${API}/ai-configs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateAiConfigRequest(
  configId: string,
  payload: Partial<AiConfigFormValue>,
): Promise<Envelope<AiConfigListResponse>> {
  return apiFetch<Envelope<AiConfigListResponse>>(`${getApiBaseUrl()}${API}/ai-configs/${configId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deleteAiConfigRequest(configId: string): Promise<Envelope<AiConfigListResponse>> {
  return apiFetch<Envelope<AiConfigListResponse>>(`${getApiBaseUrl()}${API}/ai-configs/${configId}`, {
    method: 'DELETE',
  })
}

/** 连通性测试：传 config_id 测已保存配置，或传表单值直接测 */
export async function testAiConfigRequest(
  payload: AiConfigFormValue & { config_id?: string },
): Promise<Envelope<AiConfigTestResponse>> {
  return apiFetch<Envelope<AiConfigTestResponse>>(`${getApiBaseUrl()}${API}/ai-configs/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateGlobalAiSettingsRequest(payload: {
  global_config_id?: string | null
  clear_global_config?: boolean
  global_guide?: string | null
  clear_global_guide?: boolean
}): Promise<Envelope<AiConfigListResponse>> {
  return apiFetch<Envelope<AiConfigListResponse>>(`${getApiBaseUrl()}${API}/ai-configs/global`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateProjectAiSettingsRequest(
  projectId: string,
  payload: {
    llm_config_id?: string | null
    clear_config?: boolean
    script_guide?: string | null
    clear_guide?: boolean
  },
): Promise<Envelope<ProjectDetail>> {
  return apiFetch<Envelope<ProjectDetail>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/ai`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

// ── 讲稿改写 / 修订 ────────────────────────────────────────────────────────

export async function rewriteScriptsRequest(
  projectId: string,
  payload: ScriptRewritePayload,
): Promise<Envelope<ScriptRewriteResult>> {
  return apiFetch<Envelope<ScriptRewriteResult>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/script-rewrite`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function fetchScriptRevisions(projectId: string, limit = 30): Promise<RevisionItem[]> {
  const raw = await apiFetch<Envelope<{ items: RevisionItem[] }>>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/revisions?limit=${limit}`,
  )
  return raw.data?.items ?? []
}

export async function rollbackRevisionRequest(
  projectId: string,
  revisionId: string,
): Promise<Envelope<{ message: string }>> {
  return apiFetch(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/revisions/${revisionId}/rollback`, {
    method: 'POST',
  })
}

// ── 换源 ───────────────────────────────────────────────────────────────────

export async function previewSourceRequest(projectId: string, file: File): Promise<Envelope<SourceDiffSummary>> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<Envelope<SourceDiffSummary>>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/source`, {
    method: 'POST',
    body: form,
  })
}

export async function applySourceRequest(
  projectId: string,
  autoRewrite = true,
): Promise<Envelope<SourceApplyResult>> {
  return apiFetch<Envelope<SourceApplyResult>>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/source/apply?auto_rewrite=${autoRewrite}`,
    { method: 'POST' },
  )
}

// ── 轻量页级编辑 ───────────────────────────────────────────────────────────

export async function fetchEditableShapes(projectId: string, slideUid: string): Promise<EditableShapeList> {
  return apiFetch<Envelope<EditableShapeList>>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/shapes`,
  ).then(unwrapResponse)
}

export async function editSlideTextRequest(
  projectId: string,
  slideUid: string,
  shapeIndex: number,
  text: string,
): Promise<Envelope<SlideEditResult>> {
  return apiFetch<Envelope<SlideEditResult>>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/edit-text`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shape_index: shapeIndex, text }),
    },
  )
}

export async function editSlideImageRequest(
  projectId: string,
  slideUid: string,
  shapeIndex: number,
  file: File,
): Promise<Envelope<SlideEditResult>> {
  const form = new FormData()
  form.append('shape_index', String(shapeIndex))
  form.append('file', file)
  return apiFetch<Envelope<SlideEditResult>>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/edit-image`,
    { method: 'POST', body: form },
  )
}