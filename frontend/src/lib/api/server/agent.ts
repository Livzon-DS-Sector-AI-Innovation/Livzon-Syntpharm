/**
 * 智能体 - PPT 配音视频：Server Component / Server Action 取数。
 *
 * 约定：
 * - 一律走 `apiFetch`（内部处理 API_BASE_URL、cookie→Bearer、403 语义）；
 * - 信封类型直接取自 `@/types/generated/schema` 的 `DataResponse_*`，不手写 `Envelope`；
 * - 需要业务数据时用 `unwrapResponse`，不在调用点逐层取 `.data`；
 * - 上传用 FormData 透传，不要 JSON.stringify。
 */
import { apiFetch, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'
import type {
  AiConfigFormValue,
  AiConfigListResponse,
  EditableShapeList,
  ProjectDetail,
  ProjectPage,
  ProjectUpdatePayload,
  PptVideoListQuery,
  RevisionItem,
  ScriptRewritePayload,
  SlideUpdatePayload,
  VersionItem,
  VersionManifest,
  VoiceOption,
} from '@/types/agent/ppt-video'

type Schemas = components['schemas']

const API = '/api/v1/agent'

function buildQuery(params: PptVideoListQuery): string {
  const qs = new URLSearchParams()
  if (params.keyword) qs.set('keyword', params.keyword)
  if (params.status) qs.set('status', params.status)
  if (params.language) qs.set('language', params.language)
  qs.set('page', String(params.page ?? 1))
  qs.set('page_size', String(params.page_size ?? 20))
  return qs.toString()
}

export async function fetchPptVideoProjects(params: PptVideoListQuery = {}): Promise<ProjectPage> {
  const raw = await apiFetch<Schemas['DataResponse_ProjectListResponse_']>(
    `${getApiBaseUrl()}${API}/ppt-videos?${buildQuery(params)}`,
  )
  return { items: raw.data?.items ?? [], total: raw.meta?.total ?? raw.data?.items?.length ?? 0 }
}

export async function fetchPptVideoProject(projectId: string): Promise<ProjectDetail> {
  return apiFetch<Schemas['DataResponse_ProjectDetail_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}`,
  ).then(unwrapResponse)
}

export async function fetchVoiceCatalog(language?: 'zh' | 'en'): Promise<VoiceOption[]> {
  const suffix = language ? `?language=${language}` : ''
  const raw = await apiFetch<Schemas['DataResponse_VoiceCatalogResponse_']>(
    `${getApiBaseUrl()}${API}/voices${suffix}`,
  )
  return raw.data?.items ?? []
}

export async function fetchVersionManifest(versionId: string): Promise<VersionManifest> {
  return apiFetch<Schemas['DataResponse_ManifestResponse_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/versions/${versionId}/manifest`,
  ).then(unwrapResponse)
}

export async function fetchVersionList(projectId: string): Promise<VersionItem[]> {
  return apiFetch<Schemas['DataResponse_list_VersionItem__']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/versions`,
  ).then(unwrapResponse)
}

export async function updateProjectRequest(
  projectId: string,
  payload: ProjectUpdatePayload,
): Promise<Schemas['DataResponse_ProjectDetail_']> {
  return apiFetch<Schemas['DataResponse_ProjectDetail_']>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateSlideRequest(
  projectId: string,
  slideUid: string,
  payload: SlideUpdatePayload,
): Promise<Schemas['DataResponse_SlideItem_']> {
  return apiFetch<Schemas['DataResponse_SlideItem_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
}

export async function previewSlideRequest(
  projectId: string,
  slideUid: string,
): Promise<Schemas['DataResponse_PreviewResponse_']> {
  return apiFetch<Schemas['DataResponse_PreviewResponse_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/preview`,
    { method: 'POST' },
  )
}

/** 重新生成 AI 讲稿初稿：只填空页，202 返回最新详情 */
export async function regenerateScriptAiRequest(projectId: string): Promise<Schemas['DataResponse_ProjectDetail_']> {
  return apiFetch<Schemas['DataResponse_ProjectDetail_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/script-ai`,
    { method: 'POST' },
  )
}

export async function requestRenderRequest(projectId: string): Promise<Schemas['DataResponse_RenderAccepted_']> {
  return apiFetch<Schemas['DataResponse_RenderAccepted_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/render`,
    { method: 'POST' },
  )
}

/**
 * 页图重生成：后端返回 202 + job_id，前端拿它开始轮状态。
 * `apiFetch` 已把非 2xx 转成异常，这里只解信封。
 */
export async function regeneratePageImagesRequest(
  projectId: string,
): Promise<Schemas['DataResponse_PageImagesAccepted_']> {
  return apiFetch<Schemas['DataResponse_PageImagesAccepted_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/page-images`,
    { method: 'POST' },
  )
}

export async function deleteProjectRequest(projectId: string): Promise<Schemas['DataResponse_MessageResult_']> {
  return apiFetch<Schemas['DataResponse_MessageResult_']>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}`, {
    method: 'DELETE',
  })
}

// ── AI 配置 ────────────────────────────────────────────────────────────────
//
// 注意路径是 /ai-configs 而不是 /ppt-videos/ai-config：
// 后端 /ppt-videos/{project_id} 的 {project_id} 是 UUID，会把字面量路由吃掉。

export async function fetchAiConfigs(): Promise<AiConfigListResponse> {
  return apiFetch<Schemas['DataResponse_AiConfigListResponse_']>(`${getApiBaseUrl()}${API}/ai-configs`).then(
    unwrapResponse,
  )
}

export async function createAiConfigRequest(
  payload: AiConfigFormValue,
): Promise<Schemas['DataResponse_AiConfigListResponse_']> {
  return apiFetch<Schemas['DataResponse_AiConfigListResponse_']>(`${getApiBaseUrl()}${API}/ai-configs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateAiConfigRequest(
  configId: string,
  payload: Partial<AiConfigFormValue>,
): Promise<Schemas['DataResponse_AiConfigListResponse_']> {
  return apiFetch<Schemas['DataResponse_AiConfigListResponse_']>(`${getApiBaseUrl()}${API}/ai-configs/${configId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deleteAiConfigRequest(
  configId: string,
): Promise<Schemas['DataResponse_AiConfigListResponse_']> {
  return apiFetch<Schemas['DataResponse_AiConfigListResponse_']>(`${getApiBaseUrl()}${API}/ai-configs/${configId}`, {
    method: 'DELETE',
  })
}

/** 连通性测试：传 config_id 测已保存配置，或传表单值直接测 */
export async function testAiConfigRequest(
  payload: Partial<AiConfigFormValue> & { config_id?: string },
): Promise<Schemas['DataResponse_AiConfigTestResponse_']> {
  return apiFetch<Schemas['DataResponse_AiConfigTestResponse_']>(`${getApiBaseUrl()}${API}/ai-configs/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

/** 拉取某个 Key 可用的模型清单：编辑态传 config_id 复用已保存的 Key */
export async function discoverAiModelsRequest(payload: {
  config_id?: string
  api_base_url?: string
  api_key?: string
}): Promise<Schemas['DataResponse_AiModelsDiscoverResponse_']> {
  return apiFetch<Schemas['DataResponse_AiModelsDiscoverResponse_']>(`${getApiBaseUrl()}${API}/ai-configs/models`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateGlobalAiSettingsRequest(payload: {
  global_config_id?: string | null
  global_model_name?: string | null
  clear_global_config?: boolean
  global_guide?: string | null
  clear_global_guide?: boolean
}): Promise<Schemas['DataResponse_AiConfigListResponse_']> {
  return apiFetch<Schemas['DataResponse_AiConfigListResponse_']>(`${getApiBaseUrl()}${API}/ai-configs/global`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateProjectAiSettingsRequest(
  projectId: string,
  payload: {
    llm_config_id?: string | null
    llm_model_name?: string | null
    clear_config?: boolean
    script_guide?: string | null
    clear_guide?: boolean
  },
): Promise<Schemas['DataResponse_ProjectDetail_']> {
  return apiFetch<Schemas['DataResponse_ProjectDetail_']>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/ai`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

// ── 讲稿改写 / 修订 ────────────────────────────────────────────────────────

/** 提交改写：一律入队（202），返回 revision_id 供前端轮询 */
export async function rewriteScriptsRequest(
  projectId: string,
  payload: ScriptRewritePayload,
): Promise<Schemas['DataResponse_ScriptRewriteResult_']> {
  return apiFetch<Schemas['DataResponse_ScriptRewriteResult_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/script-rewrite`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
}

/** 手工重算单页讲稿覆盖度（页文本/讲稿在别处被改过时用） */
export async function recheckCoverageRequest(
  projectId: string,
  slideUid: string,
): Promise<Schemas['DataResponse_SlideItem_']> {
  return apiFetch<Schemas['DataResponse_SlideItem_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/recheck-coverage`,
    { method: 'POST' },
  )
}

export async function fetchScriptRevisions(projectId: string, limit = 30): Promise<RevisionItem[]> {
  const raw = await apiFetch<Schemas['DataResponse_RevisionListResponse_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/revisions?limit=${limit}`,
  )
  return raw.data?.items ?? []
}

export async function rollbackRevisionRequest(
  projectId: string,
  revisionId: string,
): Promise<Schemas['DataResponse_MessageResult_']> {
  return apiFetch<Schemas['DataResponse_MessageResult_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/revisions/${revisionId}/rollback`,
    { method: 'POST' },
  )
}

// ── 换源 ───────────────────────────────────────────────────────────────────

export async function previewSourceRequest(
  projectId: string,
  file: File,
): Promise<Schemas['DataResponse_SourceDiffSummary_']> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<Schemas['DataResponse_SourceDiffSummary_']>(`${getApiBaseUrl()}${API}/ppt-videos/${projectId}/source`, {
    method: 'POST',
    body: form,
  })
}

export async function applySourceRequest(
  projectId: string,
  autoRewrite = true,
): Promise<Schemas['DataResponse_SourceApplyResult_']> {
  return apiFetch<Schemas['DataResponse_SourceApplyResult_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/source/apply?auto_rewrite=${autoRewrite}`,
    { method: 'POST' },
  )
}

// ── 轻量页级编辑 ───────────────────────────────────────────────────────────

export async function fetchEditableShapes(projectId: string, slideUid: string): Promise<EditableShapeList> {
  return apiFetch<Schemas['DataResponse_EditableShapeList_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/shapes`,
  ).then(unwrapResponse)
}

export async function editSlideTextRequest(
  projectId: string,
  slideUid: string,
  shapeIndex: number,
  text: string,
): Promise<Schemas['DataResponse_SlideEditResult_']> {
  return apiFetch<Schemas['DataResponse_SlideEditResult_']>(
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
): Promise<Schemas['DataResponse_SlideEditResult_']> {
  const form = new FormData()
  form.append('shape_index', String(shapeIndex))
  form.append('file', file)
  return apiFetch<Schemas['DataResponse_SlideEditResult_']>(
    `${getApiBaseUrl()}${API}/ppt-videos/${projectId}/slides/${slideUid}/edit-image`,
    { method: 'POST', body: form },
  )
}