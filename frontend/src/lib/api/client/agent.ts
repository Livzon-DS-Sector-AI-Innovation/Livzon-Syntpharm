/**
 * 智能体 - PPT 配音视频：浏览器端只读请求（用于列表翻页、渲染进度轮询、复用记录抽屉）。
 *
 * 只放 GET：所有写操作在 `src/actions/agent/ppt-video.ts`（Server Actions）。
 * 相对路径由 `src/proxy.ts` 转发到后端，禁止硬编码后端地址。
 */
import { apiGet, fetchApi } from '@/lib/api/client'
import type {
  JobState,
  PageImagesState,
  ProjectDetail,
  ProjectPage,
  ProjectSummary,
  SlideRegionsResponse,
  VersionManifest,
} from '@/types/agent/ppt-video'

const API = '/api/v1/agent'

export interface PptVideoQuery {
  keyword?: string
  status?: string
  language?: string
  page?: number
  page_size?: number
}

/**
 * 项目列表：`items` 在 data 内、`total` 在信封 meta 内，
 * 不能直接用 apiGet（会丢掉 meta.total），这里读原始信封。
 */
export async function fetchPptVideoProjects(params: PptVideoQuery = {}): Promise<ProjectPage> {
  const qs = new URLSearchParams()
  if (params.keyword) qs.set('keyword', params.keyword)
  if (params.status) qs.set('status', params.status)
  if (params.language) qs.set('language', params.language)
  qs.set('page', String(params.page ?? 1))
  qs.set('page_size', String(params.page_size ?? 20))

  const raw = await fetchApi<{
    code: number
    data: { items: ProjectSummary[] }
    meta?: { total?: number }
  }>(`${API}/ppt-videos?${qs.toString()}`)
  const items = raw.data?.items ?? []
  return { items, total: raw.meta?.total ?? items.length }
}

export async function fetchPptVideoJob(projectId: string): Promise<JobState | null> {
  return apiGet<JobState | null>(`${API}/ppt-videos/${projectId}/job`)
}

export async function fetchPptVideoDetail(projectId: string): Promise<ProjectDetail> {
  return apiGet<ProjectDetail>(`${API}/ppt-videos/${projectId}`)
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