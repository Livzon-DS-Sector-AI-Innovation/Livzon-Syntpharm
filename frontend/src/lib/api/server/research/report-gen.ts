/**
 * AI 报告生成的服务端写操作
 *
 * 全部经由 Server Actions 调用，客户端不直接 fetch 写接口。
 */

import { apiFetch, apiFetchData, getApiBaseUrl } from '@/lib/api/server/base'
import {
  REPORT_GEN_METRIC_DEFAULT_WINDOW,
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