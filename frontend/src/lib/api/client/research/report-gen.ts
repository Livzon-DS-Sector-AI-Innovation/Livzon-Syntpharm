/**
 * AI 报告生成的浏览器端只读接口
 *
 * 写操作走 Server Actions（`actions/research/report-gen.ts`）。
 * 文件下载是流式响应，按 AGENTS.md 的例外允许在客户端直接 fetch。
 */

import { apiGet } from '@/lib/api/client'
import {
  REPORT_GEN_METRIC_DEFAULT_WINDOW,
  type ReportGenDocumentVersionList,
  type ReportGenFeedbackList,
  type ReportGenJob,
  type ReportGenJobList,
  type ReportGenMetrics,
  type ReportGenOpinionDigestList,
  type ReportGenOpinionList,
  type ReportGenOutline,
  type ReportGenStepList,
} from '@/types/research/report-gen'

const API_BASE = '/api/v1/research/report-gen'

/** 配置页「Agent 运行情况」：切换时间窗时重取，只读聚合，不改任何配置。 */
export async function fetchReportGenMetrics(
  days: number = REPORT_GEN_METRIC_DEFAULT_WINDOW
): Promise<ReportGenMetrics | null> {
  return apiGet<ReportGenMetrics>(`${API_BASE}/settings/metrics?days=${days}`)
}

/** 某一版报告上提过的修改意见（只读）：写操作走 Server Action。 */
export async function fetchReportGenFeedback(jobId: string): Promise<ReportGenFeedbackList> {
  const result = await apiGet<ReportGenFeedbackList>(`${API_BASE}/jobs/${jobId}/feedback`)
  return result ?? { total: 0, open_count: 0, items: [] }
}

/** 全局意见库：跨报告归并后的历史意见，次数高的在前。 */
export async function fetchReportGenOpinions(params: {
  status?: 'active' | 'disabled'
  keyword?: string
  limit?: number
} = {}): Promise<ReportGenOpinionList> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.keyword) qs.set('keyword', params.keyword)
  if (params.limit) qs.set('limit', String(params.limit))
  const result = await apiGet<ReportGenOpinionList>(`${API_BASE}/opinion-library?${qs}`)
  return result ?? { total: 0, active_count: 0, items: [] }
}

/** 历史意见汇总快照：回答「这一版按哪份写作要求生成」。 */
export async function fetchReportGenOpinionDigests(limit = 20): Promise<ReportGenOpinionDigestList> {
  const result = await apiGet<ReportGenOpinionDigestList>(
    `${API_BASE}/opinion-library/digests?limit=${limit}`,
  )
  return result ?? { total: 0, items: [] }
}

export async function fetchReportGenJobs(
  params: { projectId?: string; reportId?: string; limit?: number } = {},
): Promise<ReportGenJobList> {
  const qs = new URLSearchParams()
  if (params.projectId) qs.set('project_id', params.projectId)
  if (params.reportId) qs.set('report_id', params.reportId)
  // 跨项目时后端默认只回 100 条，显式抬到上限，避免老任务的进度被截断成「未生成」
  if (params.limit) qs.set('limit', String(params.limit))
  const result = await apiGet<ReportGenJobList>(`${API_BASE}/jobs?${qs}`)
  return result ?? { items: [], active_count: 0 }
}

export async function fetchReportGenJob(jobId: string): Promise<ReportGenJob> {
  return apiGet<ReportGenJob>(`${API_BASE}/jobs/${jobId}`)
}

/**
 * 详情页审阅清单：母本可写位置（含未写空位）+ 写入记录 + 成品结构自检数字。
 * 生成中也能取：那时只有母本位置、还没有写入值，正好用来展示「准备写哪些地方」。
 */
export async function fetchReportGenOutline(jobId: string): Promise<ReportGenOutline> {
  return apiGet<ReportGenOutline>(`${API_BASE}/jobs/${jobId}/outline`)
}

/** 文档版本时间线：AI 初稿、在线编辑、人工上传都在这里，用于对照与回滚。 */
export async function fetchReportGenVersions(jobId: string): Promise<ReportGenDocumentVersionList> {
  const result = await apiGet<ReportGenDocumentVersionList>(`${API_BASE}/jobs/${jobId}/versions`)
  return result ?? { items: [], total: 0 }
}

export async function fetchReportGenSteps(
  jobId: string,
  afterSeq = 0,
  limit = 200,
): Promise<ReportGenStepList> {
  const qs = new URLSearchParams({ after_seq: String(afterSeq), limit: String(limit) })
  const result = await apiGet<ReportGenStepList>(`${API_BASE}/jobs/${jobId}/steps?${qs}`)
  return result ?? { items: [], last_seq: afterSeq }
}

function authHeaders(): Record<string, string> {
  if (typeof document === 'undefined') return {}
  const token = document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith('auth_token='))
  return token ? { Authorization: `Bearer ${token.slice('auth_token='.length)}` } : {}
}

function pickFileName(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8) {
    const decoded = decodeURIComponent(utf8[1])
    return decoded
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i)
  return plain ? plain[1] : fallback
}

/** 取成品 docx 的 Blob，用于在线预览。 */
export async function fetchReportGenDocumentBlob(jobId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/document`, {
    method: 'GET',
    headers: authHeaders(),
    credentials: 'include',
  })
  if (!response.ok) throw new Error(response.status === 404 ? '成品还未生成' : `加载失败（${response.status}）`)
  return response.blob()
}

/** 下载成品 docx；失败直接抛错，由调用方提示。 */
export async function downloadReportGenFile(jobId: string, fallbackName: string): Promise<string> {
  return downloadBlob(`${API_BASE}/jobs/${jobId}/document`, fallbackName)
}

/** 下载某一版 docx。 */
export async function downloadReportGenVersion(versionId: string, fallbackName: string): Promise<string> {
  return downloadBlob(`${API_BASE}/versions/${versionId}/document`, fallbackName)
}

async function downloadBlob(url: string, fallbackName: string): Promise<string> {
  const response = await fetch(url, {
    method: 'GET',
    headers: authHeaders(),
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(response.status === 404 ? '文件还未生成' : `下载失败（${response.status}）`)
  }
  const blob = await response.blob()
  const filename = pickFileName(response.headers.get('Content-Disposition'), fallbackName)
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
  return filename
}