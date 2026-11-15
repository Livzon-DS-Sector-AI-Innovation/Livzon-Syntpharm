/**
 * AI 报告生成的服务端写操作
 *
 * 全部经由 Server Actions 调用，客户端不直接 fetch 写接口。
 */

import { apiFetch, apiFetchData, getApiBaseUrl } from '@/lib/api/server/base'
import {
  REPORT_GEN_METRIC_DEFAULT_WINDOW,
  type ReportGenEditRequest,
  type ReportGenEditResult,
  type ReportGenFeedbackCreate,
  type ReportGenJob,
  type ReportGenJobCreate,
  type ReportGenMetrics,
  type ReportGenModelTest,
  type ReportGenModelTestRequest,
  type ReportGenRender,
} from '@/types/research/report-gen'

const API_BASE = '/api/v1/research/report-gen'

/** 详情页首屏数据：服务端取一次，避免客户端白屏。 */
export async function fetchReportGenJobServer(jobId: string): Promise<ReportGenJob> {
  return apiFetchData<ReportGenJob>(`${getApiBaseUrl()}${API_BASE}/jobs/${jobId}`)
}

export async function createReportGenJob(payload: ReportGenJobCreate) {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/jobs`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function cancelReportGenJob(jobId: string) {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/jobs/${jobId}/cancel`, { method: 'POST' })
}

/** 对某一版报告提一条修改意见：下次生成会自动带上未落实的条目。 */
export async function createReportGenFeedback(jobId: string, payload: ReportGenFeedbackCreate) {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/jobs/${jobId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** 处置意见：ignored 不再带入下一次生成，open 恢复带入。 */
export async function updateReportGenFeedback(feedbackId: string, status: 'open' | 'ignored') {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/feedback/${feedbackId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

/**
 * 停用 / 恢复一条意见库条目。
 * 停用是「这条要求不该再影响后续生成」，同类新意见也不会自动把它打开。
 */
export async function updateReportGenOpinion(opinionId: string, status: 'active' | 'disabled') {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/opinion-library/${opinionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

/**
 * 在线编辑保存：整批提交，后端要么全生效、要么逐条返回拒绝原因。
 * 不在这里重试——写 docx 与落版本不是幂等操作。
 */
export async function saveReportGenEdits(
  jobId: string,
  payload: ReportGenEditRequest,
): Promise<ReportGenEditResult> {
  return apiFetchData<ReportGenEditResult>(`${getApiBaseUrl()}${API_BASE}/jobs/${jobId}/edits`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** 回滚到指定版本：后端把旧文件再落一个新版本，历史版本不被改写。 */
export async function restoreReportGenVersion(
  jobId: string,
  versionId: string,
  baseVersionId?: string | null,
): Promise<ReportGenRender> {
  return apiFetchData<ReportGenRender>(`${getApiBaseUrl()}${API_BASE}/jobs/${jobId}/versions/${versionId}/restore`, {
    method: 'POST',
    body: JSON.stringify({ base_version_id: baseVersionId ?? null }),
  })
}

/** 配置页首屏指标：服务端取一次，避免面板白屏；失败由页面 try/catch 兜成空态。 */
export async function fetchReportGenMetricsServer(
  days: number = REPORT_GEN_METRIC_DEFAULT_WINDOW
): Promise<ReportGenMetrics> {
  return apiFetchData<ReportGenMetrics>(`${getApiBaseUrl()}${API_BASE}/settings/metrics?days=${days}`)
}

/** 单档位连通测试：只发一次极短对话，不写配置。 */
export async function testReportGenModel(payload: ReportGenModelTestRequest): Promise<ReportGenModelTest> {
  return apiFetchData<ReportGenModelTest>(`${getApiBaseUrl()}${API_BASE}/settings/test-model`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}