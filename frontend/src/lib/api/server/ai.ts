import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'
import type { ExamGenerateResponse } from '@/types/hr'

export async function generateExamQuestions(formData: FormData): Promise<ExamGenerateResponse> {
  const url = `${API_BASE_URL}/api/v1/hr/ai-exam/generate`
  const res = await fetch(url, {
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
  const url = `${API_BASE_URL}/api/v1/hr/ai-exam/export`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`导出失败: ${res.status} ${text}`)
  }
  return res
}

export async function parseExperimentRecord(formData: FormData): Promise<unknown> {
  const url = `${API_BASE_URL}/api/v1/ai/parse-experiment`
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    cache: 'no-store',
  })
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`解析失败: ${response.status} ${errorText}`)
  }
  const result = await response.json()
  return result.data
}

export async function parseProcessParameters(content: string, type: 'lab_confirmation' | 'scale_up'): Promise<unknown> {
  return apiFetch(`${API_BASE_URL}/api/v1/ai/parse-parameters`, {
    method: 'POST',
    body: JSON.stringify({ content, parse_type: type }),
  })
}
