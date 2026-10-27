import { apiFetch, apiFetchRaw, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'

export interface ExamJobState {
  status: 'running' | 'done' | 'failed'
  result: Record<string, unknown> | null
  error: string | null
}

/** 提交 AI 出题后台任务，返回 job_id（结果轮询 fetchExamJob）。 */
export async function submitExamJob(formData: FormData): Promise<string> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/hr/ai-exam/generate`, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`出题失败: ${res.status} ${text}`)
  }
  const json = (await res.json()) as { data?: { job_id?: string } }
  if (!json.data?.job_id) {
    throw new Error('出题任务提交失败：响应缺少 job_id')
  }
  return json.data.job_id
}

/** 轮询出题任务状态；任务不存在（服务重启）时抛错。 */
export async function fetchExamJob(jobId: string): Promise<ExamJobState> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/hr/jobs/${jobId}`, {
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`查询出题任务失败: ${res.status}`)
  }
  const json = (await res.json()) as { data?: ExamJobState }
  if (!json.data) {
    throw new Error('查询出题任务失败：响应缺少 data')
  }
  return json.data
}

export async function exportExam(data: unknown): Promise<Response> {
  return apiFetchRaw('/api/v1/hr/ai-exam/export', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function parseExperimentRecord(formData: FormData): Promise<unknown> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/ai/parse-experiment`, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(`解析失败: ${res.status} ${errorText}`)
  }
  const result = await res.json()
  return unwrapResponse(result)
}

export async function parseProcessParameters(content: string, type: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  return apiFetch('/api/v1/ai/parse-parameters', {
    method: 'POST',
    body: JSON.stringify({ content, parse_type: type }),
  })
}
