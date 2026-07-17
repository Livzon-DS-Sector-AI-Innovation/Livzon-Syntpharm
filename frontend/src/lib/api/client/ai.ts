import { ExamGenerateResponse, ExamExportData } from '@/types/hr'

const API_BASE = '/api/v1'

export async function generateExamQuestions(
  file: File,
  config?: { choice_count?: number; true_false_count?: number; multi_choice_count?: number; fill_blank_count?: number }
): Promise<ExamGenerateResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (config) {
    formData.append('choice_count', String(config.choice_count ?? 5))
    formData.append('true_false_count', String(config.true_false_count ?? 5))
    formData.append('multi_choice_count', String(config.multi_choice_count ?? 0))
    formData.append('fill_blank_count', String(config.fill_blank_count ?? 0))
  }

  const res = await fetch(`${API_BASE}/ai/exam/generate`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`出题失败: ${res.status} ${text}`)
  }

  return res.json()
}

export async function exportExam(data: ExamExportData): Promise<Blob> {
  const res = await fetch(`${API_BASE}/ai/exam/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`导出失败: ${res.status} ${text}`)
  }

  return res.blob()
}