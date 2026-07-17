'use server'

import { generateExamQuestions as generateExamQuestionsApi, exportExam as exportExamApi } from '@/lib/api/server/ai'
import { ExamGenerateResponse, ExamExportData } from '@/types/hr'

interface ExamConfig {
  choice_count?: number
  true_false_count?: number
  qa_count?: number
}

export async function generateExamQuestions(file: File, _config?: ExamConfig): Promise<ExamGenerateResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return generateExamQuestionsApi(formData)
}

export async function exportExam(data: ExamExportData): Promise<Blob> {
  const res = await exportExamApi(data)
  return res.blob()
}
