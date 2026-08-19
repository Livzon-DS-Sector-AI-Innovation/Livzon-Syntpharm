import { apiFetch, apiFetchRaw, unwrapResponse, getApiBaseUrl } from '@/lib/api/server/base'
import type { ExamGenerateResponse } from '@/types/hr'

export async function generateExamQuestions(formData: FormData): Promise<ExamGenerateResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/hr/ai-exam/generate`, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`出题失败: ${res.status} ${text}`)
  }
  return res.json()
}

export async function exportExam(data: unknown): Promise<Response> {
  return apiFetchRaw('/api/v1/hr/ai-exam/export', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function parseExperimentRecord(content: string, parseType: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  return apiFetch('/api/v1/research/ai/parse-experiment', {
    method: 'POST',
    body: JSON.stringify({ content, parse_type: parseType }),
  })
}

export async function parseProcessParameters(content: string, type: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  return apiFetch('/api/v1/research/ai/parse-parameters', {
    method: 'POST',
    body: JSON.stringify({ content, parse_type: type }),
  })
}
