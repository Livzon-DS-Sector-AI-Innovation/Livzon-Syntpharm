/**
 * AI 报告生成的服务端写操作
 *
 * 全部经由 Server Actions 调用，客户端不直接 fetch 写接口。
 */

import { apiFetch, apiFetchData, getApiBaseUrl } from '@/lib/api/server/base'
import {
  REPORT_GEN_METRIC_DEFAULT_WINDOW,
  type ReportGenExampleUpdate,
  type ReportGenFeedbackCreate,
  type ReportGenJob,
  type ReportGenJobCreate,
  type ReportGenMetrics,
  type ReportGenModelTest,
  type ReportGenModelTestRequest,
  type ReportGenSlotUpdate,
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

export async function updateReportGenSlot(jobId: string, slotKey: string, payload: ReportGenSlotUpdate) {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/jobs/${jobId}/slots/${encodeURIComponent(slotKey)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
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

/** 把已落实的意见沉淀成槽位示例：后端取那次生成的实际写法，前端不传值。 */
export async function promoteReportGenFeedback(feedbackId: string) {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/feedback/${feedbackId}/promote`, { method: 'POST' })
}

/** 人工维护一条示例：改写法 / 补依据 / 停用。 */
export async function updateTemplateExample(exampleId: string, payload: ReportGenExampleUpdate) {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/examples/${exampleId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/** 软删除一条示例：不再参与注入，但保留记录可追。 */
export async function deleteTemplateExample(exampleId: string) {
  return apiFetch(`${getApiBaseUrl()}${API_BASE}/examples/${exampleId}`, { method: 'DELETE' })
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