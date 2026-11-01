import { apiFetchData } from './base'
import type {
  DeviationOptimizeJob,
  DeviationOptimizeJobResult,
  DeviationReportOptimizeType,
  DeviationReportUploadResult,
} from '@/types/quality'

const API_BASE = '/api/v1/quality/deviation-report'

/** 上传 Word 模板并解析为 HTML */
export async function uploadDeviationReport(file: File): Promise<DeviationReportUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetchData<DeviationReportUploadResult>(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  })
}

/** 提交 AI 优化任务，立即返回 job_id（LLM 在后台跑，不在请求里等） */
export async function startDeviationReportOptimize(
  text: string,
  optimizeType: DeviationReportOptimizeType,
): Promise<DeviationOptimizeJob> {
  return apiFetchData<DeviationOptimizeJob>(`${API_BASE}/ai/optimize`, {
    method: 'POST',
    body: JSON.stringify({ text, optimize_type: optimizeType }),
  })
}

/** 轮询 AI 优化任务状态 */
export async function fetchDeviationReportOptimizeJob(jobId: string): Promise<DeviationOptimizeJobResult> {
  return apiFetchData<DeviationOptimizeJobResult>(`${API_BASE}/ai/optimize/jobs/${encodeURIComponent(jobId)}`)
}