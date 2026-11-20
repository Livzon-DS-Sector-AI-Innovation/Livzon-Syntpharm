/** 文档翻译 —— 浏览器端请求（只读走 apiGet/apiFetchPaginated，上传走 apiUpload）。 */

import { apiFetchPaginated, apiGet, apiUpload } from '@/lib/api/client'
import type {
  DocxGlossaryImportResult,
  DocxGlossaryTerm,
  DocxPageQuery,
  DocxTaskQuery,
  DocxTranslationFileRecord,
  DocxTranslationJobState,
  DocxTranslationSubmitPayload,
  DocxTranslationSubmitResult,
  DocxTranslationTaskDetail,
  DocxTranslationTaskRecord,
} from '@/types/docx-translator'

const BASE = '/api/v1/registration/docx-translator'

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value))
  })
  return search.toString()
}

export async function fetchSubmitTranslationJob(
  payload: DocxTranslationSubmitPayload
): Promise<DocxTranslationSubmitResult> {
  const form = new FormData()
  payload.files.forEach(file => form.append('files', file, file.name))
  form.append('source_lang', payload.sourceLang)
  form.append('target_lang', payload.targetLang)
  form.append('mode', payload.mode)
  if (payload.batchSize) form.append('batch_size', String(payload.batchSize))
  return apiUpload<DocxTranslationSubmitResult>(`${BASE}/jobs`, form)
}

export async function fetchTranslationJobState(jobId: string): Promise<DocxTranslationJobState> {
  return apiGet<DocxTranslationJobState>(`${BASE}/jobs/${jobId}`)
}

export async function fetchTranslationJobStates(ids: string[]): Promise<DocxTranslationJobState[]> {
  if (!ids.length) return []
  const search = new URLSearchParams()
  ids.forEach(id => search.append('ids', id))
  const data = await apiGet<{ items: DocxTranslationJobState[] }>(`${BASE}/jobs?${search.toString()}`)
  return data.items ?? []
}

export function translationDownloadUrl(jobId: string, fileIndex: number): string {
  return `${BASE}/jobs/${jobId}/files/${fileIndex}`
}

export function fetchGlossaryTerms(
  params: DocxPageQuery
): Promise<{ items: DocxGlossaryTerm[]; total: number; page: number; page_size: number }> {
  const query = buildQuery({ keyword: params.keyword, page: params.page, page_size: params.pageSize })
  return apiFetchPaginated<DocxGlossaryTerm>(`${BASE}/glossary?${query}`)
}

export async function fetchGlossaryImport(file: File): Promise<DocxGlossaryImportResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  return apiUpload<DocxGlossaryImportResult>(`${BASE}/glossary/import`, form)
}

export function glossaryExportUrl(): string {
  return `${BASE}/glossary/export`
}

export function fetchTranslationTasks(
  params: DocxTaskQuery
): Promise<{ items: DocxTranslationTaskRecord[]; total: number; page: number; page_size: number }> {
  const query = buildQuery({
    keyword: params.keyword,
    status: params.status,
    mine: params.mine ? 'true' : undefined,
    page: params.page,
    page_size: params.pageSize,
  })
  return apiFetchPaginated<DocxTranslationTaskRecord>(`${BASE}/tasks?${query}`)
}

export function fetchTranslationTaskDetail(taskId: string): Promise<DocxTranslationTaskDetail> {
  return apiGet<DocxTranslationTaskDetail>(`${BASE}/tasks/${taskId}`)
}

export function translationFileDownloadUrl(fileId: string): string {
  return `${BASE}/files/${fileId}/download`
}

export type { DocxTranslationFileRecord }
