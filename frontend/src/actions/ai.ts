'use server'

import { exportExam as exportExamApi, fetchExamJob, submitExamJob } from '@/lib/api/server/ai'
import type { ExamJobState } from '@/lib/api/server/ai'
import { ExamExportData } from '@/types/hr'

export async function submitExamJobAction(
  file: File,
  config: { choice_count: number; true_false_count: number; multi_choice_count?: number; fill_blank_count?: number },
): Promise<string> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('choice_count', String(config.choice_count))
  formData.append('true_false_count', String(config.true_false_count))
  formData.append('multi_choice_count', String(config.multi_choice_count ?? 0))
  formData.append('fill_blank_count', String(config.fill_blank_count ?? 0))
  return submitExamJob(formData)
}

export async function fetchExamJobAction(jobId: string): Promise<ExamJobState> {
  return fetchExamJob(jobId)
}

export async function exportExam(data: ExamExportData): Promise<Blob> {
  const res = await exportExamApi(data)
  return res.blob()
}
