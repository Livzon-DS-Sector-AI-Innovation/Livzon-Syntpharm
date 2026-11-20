/**
 * 智能体 - PPT 配音视频：浏览器端只读请求（用于列表翻页、渲染进度轮询、复用记录抽屉）。
 *
 * 只放 GET：所有写操作在 `src/actions/agent/ppt-video.ts`（Server Actions）。
 * 相对路径由 `src/proxy.ts` 转发到后端，禁止硬编码后端地址。
 */
import { apiGet, apiGetWithMeta } from '@/lib/api/client'
import type { components } from '@/types/generated/schema'
import type {
  AiConfigListResponse,
  JobState,
  PageImagesState,
  ParseState,
  ProjectDetail,
  ProjectPage,
  PptVideoListQuery,
  RevisionItem,
  RevisionListResponse,
  SlideRegionsResponse,
  VersionManifest,
} from '@/types/agent/ppt-video'

type Schemas = components['schemas']

const API = '/api/v1/agent'

/**
 * 项目列表：`items` 在 data 内、`total` 在信封 meta 内，
 * 不能直接用 apiGet（会丢掉 meta.total），走 apiGetWithMeta 保留 meta。
 */
export async function fetchPptVideoProjects(params: PptVideoListQuery = {}): Promise<ProjectPage> {
  const qs = new URLSearchParams()
  if (params.keyword) qs.set('keyword', params.keyword)
  if (params.status) qs.set('status', params.status)
  if (params.language) qs.set('language', params.language)
  qs.set('page', String(params.page ?? 1))
  qs.set('page_size', String(params.page_size ?? 20))

  const { data, meta } = await apiGetWithMeta<Schemas['ProjectListResponse'], Schemas['PaginationMeta']>(
    `${API}/ppt-videos?${qs.toString()}`,
  )
  const items = data.items ?? []
  return { items, total: meta.total ?? items.length }
}

export async function fetchPptVideoJob(projectId: string): Promise<JobState | null> {
  return apiGet<JobState | null>(`${API}/ppt-videos/${projectId}/job`)
}

export async function fetchPptVideoDetail(projectId: string): Promise<ProjectDetail> {
  return apiGet<ProjectDetail>(`${API}/ppt-videos/${projectId}`)
}

/**
 * 解析进度：解析已改为队列任务，上传后靠这个接口轮询（比整份详情便宜）。
 */
export async function fetchPptVideoParseState(projectId: string): Promise<ParseState> {
  return apiGet<ParseState>(`${API}/ppt-videos/${projectId}/parse`)
}

/** 异步任务进度与产物（试听音频地址、换源预览差异）。 */
export async function fetchPptVideoJobById(projectId: string, jobId: string): Promise<JobState> {
  return apiGet<JobState>(`${API}/ppt-videos/${projectId}/jobs/${jobId}`)
}

const TERMINAL_JOB_STATUS = new Set(['succeeded', 'failed', 'canceled'])

/**
 * 等待异步任务到终态（试听合成、换源预览这类一次性任务）。
 *
 * 用轮询而不是 useEffect：调用点都是用户点击后的处理函数，轮询结束即给出结果，
 * 不会在组件里留下需要 effect 同步的状态。
 */
export async function waitForPptVideoJob(
  projectId: string,
  jobId: string,
  { intervalMs = 1000, timeoutMs = 120_000 }: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<JobState> {
  const deadline = Date.now() + timeoutMs
  for (;;) {
    const job = await fetchPptVideoJobById(projectId, jobId)
    if (TERMINAL_JOB_STATUS.has(job.status)) return job
    if (Date.now() > deadline) throw new Error('任务处理超时，请稍后刷新重试')
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
}

/** AI 配置清单（抽屉打开时取一次）。 */
export async function fetchAiConfigs(): Promise<AiConfigListResponse> {
  return apiGet<AiConfigListResponse>(`${API}/ai-configs`)
}

/** 讲稿修订记录（抽屉打开时取一次）。 */
export async function fetchScriptRevisionList(projectId: string, limit = 30): Promise<RevisionItem[]> {
  const data = await apiGet<RevisionListResponse | null>(`${API}/ppt-videos/${projectId}/revisions?limit=${limit}`)
  return data?.items ?? []
}

/**
 * 页图生成状态：单行查询，比整份详情便宜一个量级，
 * 左栏进度条 2 秒轮一次只在终态时才回拉详情。
 */
export async function fetchPageImagesStatus(projectId: string): Promise<PageImagesState> {
  return apiGet<PageImagesState>(`${API}/ppt-videos/${projectId}/page-images/status`)
}

export async function fetchVersionManifest(versionId: string): Promise<VersionManifest> {
  return apiGet<VersionManifest>(`${API}/ppt-videos/versions/${versionId}/manifest`)
}

/**
 * 单页可高亮区域清单：页面尺寸 + layout 元素坐标 + 服务端切好的句子。
 * 只在打开区域设置抽屉时取一次，比整份详情便宜。
 */
export async function fetchSlideRegions(projectId: string, slideUid: string): Promise<SlideRegionsResponse> {
  return apiGet<SlideRegionsResponse>(`${API}/ppt-videos/${projectId}/slides/${slideUid}/regions`)
}