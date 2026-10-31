import { apiFetchData } from './base'
import type { DeviationOptimizeResult, DeviationReportOptimizeType, DeviationReportUploadResult } from '@/types/quality'

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

/** AI 优化选中文本，返回后端契约结构 */
export async function optimizeDeviationReportText(
  text: string,
  optimizeType: DeviationReportOptimizeType,
): Promise<DeviationOptimizeResult> {
  return apiFetchData<DeviationOptimizeResult>(`${API_BASE}/ai/optimize`, {
    method: 'POST',
    body: JSON.stringify({ text, optimize_type: optimizeType }),
  })
}