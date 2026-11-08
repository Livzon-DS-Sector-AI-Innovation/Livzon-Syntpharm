/**
 * AI 报告生成的浏览器端只读接口
 *
 * 写操作走 Server Actions（`actions/research/report-gen.ts`）。
 * 文件下载是流式响应，按 AGENTS.md 的例外允许在客户端直接 fetch。
 */

import { apiGet } from '@/lib/api/client'
import {
  REPORT_GEN_METRIC_DEFAULT_WINDOW,
  type ReportGenJob,
  type ReportGenJobList,
  type ReportGenMetrics,
  type ReportGenSlotList,
  type ReportGenStepList,
  type ReportGenStructureRunList,
} from '@/types/research/report-gen'

const API_BASE = '/api/v1/research/report-gen'

/** 配置页「Agent 运行情况」：切换时间窗时重取，只读聚合，不改任何配置。 */
export async function fetchReportGenMetrics(
  days: number = REPORT_GEN_METRIC_DEFAULT_WINDOW
): Promise<ReportGenMetrics | null> {
  return apiGet<ReportGenMetrics>(`${API_BASE}/settings/metrics?days=${days}`)
}

/**
 * 母本解析留痕（只读）：每次识别选了多少槽位，以及人工随后补了/否掉了多少。
 *
 * 统计是「解析当时的选择」对比「当前结构」，跨多次人工编辑会混在一起，只作趋势看。
 */
export async function fetchTemplateStructureRuns(
  templateId: string,
  limit = 10,
): Promise<ReportGenStructureRunList> {
  const result = await apiGet<ReportGenStructureRunList>(
    `${API_BASE}/templates/${templateId}/structure-runs?limit=${limit}`,
  )
  return result ?? { total: 0, items: [] }
}

export async function fetchReportGenJobs(params: { projectId?: string; reportId?: string } = {}): Promise<ReportGenJobList> {
  const qs = new URLSearchParams()
  if (params.projectId) qs.set('project_id', params.projectId)
  if (params.reportId) qs.set('report_id', params.reportId)
  const result = await apiGet<ReportGenJobList>(`${API_BASE}/jobs?${qs}`)
  return result ?? { items: [], active_count: 0 }
}

export async function fetchReportGenJob(jobId: string): Promise<ReportGenJob> {
  return apiGet<ReportGenJob>(`${API_BASE}/jobs/${jobId}`)
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

export async function fetchReportGenSlots(jobId: string): Promise<ReportGenSlotList> {
  const result = await apiGet<ReportGenSlotList>(`${API_BASE}/jobs/${jobId}/slots`)
  return result ?? { items: [], total: 0, filled: 0, gaps: 0 }
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

/** 取成品 docx 的 Blob，用于在线预览（预览组件自己渲染）。 */
export async function fetchReportGenDocumentBlob(jobId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/document`, {
    method: 'GET',
    headers: authHeaders(),
    credentials: 'include',
  })
  if (!response.ok) throw new Error(response.status === 404 ? '成品还未生成' : `加载失败（${response.status}）`)
  return response.blob()
}

/** 下载成品 docx 或槽位对照表；失败直接抛错，由调用方提示。 */
export async function downloadReportGenFile(
  jobId: string,
  kind: 'document' | 'comparison',
  fallbackName: string,
): Promise<string> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/${kind}`, {
    method: 'GET',
    headers: authHeaders(),
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(response.status === 404 ? '成品还未生成' : `下载失败（${response.status}）`)
  }
  const blob = await response.blob()
  const filename = pickFileName(response.headers.get('Content-Disposition'), fallbackName)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  return filename
}