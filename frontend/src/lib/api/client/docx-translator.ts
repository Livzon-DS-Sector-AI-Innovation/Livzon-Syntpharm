/** 文档翻译 —— 浏览器端只读请求 + 文件上传（FormData 属项目允许的例外写法） */

import { ApiError } from '@/lib/api/client'
import type {
  DocxGlossaryImportResult,
  DocxGlossaryTermPage,
  DocxTranslationFilePage,
  DocxTranslationJobState,
  DocxTranslationTaskDetail,
  DocxTranslationTaskPage,
  DocxTranslationSubmitPayload,
  DocxTranslationSubmitResult,
} from '@/types/docx-translator'

const BASE = '/api/v1/registration/docx-translator'

interface Envelope<T> {
  code: number
  message?: string
  data?: T
  meta?: { page?: number; page_size?: number; total?: number } | null
}

async function readJson<T>(res: Response, fallback: string): Promise<T> {
  if (!res.ok) {
    let detail = fallback
    try {
      const body = (await res.json()) as { message?: string; detail?: string }
      detail = body.message || body.detail || fallback
    } catch {
      // 响应不是 JSON 时保留兜底文案
    }
    // 抛出 ApiError 才能让 usePollingJob 识别 404（任务状态已过期）并切到 unavailable 兜底态
    throw new ApiError(res.status, res.statusText, detail)
  }
  const body = (await res.json()) as Envelope<T>
  if (!body.data) throw new Error(fallback)
  return body.data
}

export async function submitTranslationJob(
  payload: DocxTranslationSubmitPayload
): Promise<DocxTranslationSubmitResult> {
  const form = new FormData()
  payload.files.forEach(file => form.append('files', file, file.name))
  form.append('source_lang', payload.sourceLang)
  form.append('target_lang', payload.targetLang)
  form.append('mode', payload.mode)
  if (payload.batchSize) form.append('batch_size', String(payload.batchSize))

  const res = await fetch(`${BASE}/jobs`, { method: 'POST', body: form })
  return readJson<DocxTranslationSubmitResult>(res, '提交翻译任务失败')
}

export async function fetchTranslationJobState(jobId: string): Promise<DocxTranslationJobState> {
  const res = await fetch(`${BASE}/jobs/${jobId}`, { cache: 'no-store' })
  return readJson<DocxTranslationJobState>(res, '查询翻译任务状态失败')
}

export function translationDownloadUrl(jobId: string, fileIndex: number): string {
  return `${BASE}/jobs/${jobId}/files/${fileIndex}`
}

export async function fetchGlossaryTerms(params: {
  keyword?: string
  page: number
  pageSize: number
}): Promise<DocxGlossaryTermPage> {
  const search = new URLSearchParams()
  if (params.keyword) search.set('keyword', params.keyword)
  search.set('page', String(params.page))
  search.set('page_size', String(params.pageSize))
  const res = await fetch(`${BASE}/glossary?${search.toString()}`, { cache: 'no-store' })
  const data = await readJson<{ items: DocxGlossaryTermPage['items']; total: number }>(res, '获取术语表失败')
  return { items: data.items, total: data.total }
}

export async function importGlossaryFile(file: File): Promise<DocxGlossaryImportResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  const res = await fetch(`${BASE}/glossary/import`, { method: 'POST', body: form })
  return readJson<DocxGlossaryImportResult>(res, '导入术语表失败')
}

export function glossaryExportUrl(): string {
  return `${BASE}/glossary/export`
}

export async function fetchTranslationFiles(params: {
  keyword?: string
  page: number
  pageSize: number
}): Promise<DocxTranslationFilePage> {
  const search = new URLSearchParams()
  if (params.keyword) search.set('keyword', params.keyword)
  search.set('page', String(params.page))
  search.set('page_size', String(params.pageSize))
  const res = await fetch(`${BASE}/files?${search.toString()}`, { cache: 'no-store' })
  const data = await readJson<DocxTranslationFilePage>(res, '获取翻译历史失败')
  return { items: data.items ?? [], total: data.total ?? 0 }
}

export function translationFileDownloadUrl(fileId: string): string {
  return `${BASE}/files/${fileId}/download`
}

export async function fetchTranslationTasks(params: {
  keyword?: string
  status?: 'running' | 'done' | 'failed'
  mine?: boolean
  page: number
  pageSize: number
}): Promise<DocxTranslationTaskPage> {
  const search = new URLSearchParams()
  if (params.keyword) search.set('keyword', params.keyword)
  if (params.status) search.set('status', params.status)
  if (params.mine) search.set('mine', 'true')
  search.set('page', String(params.page))
  search.set('page_size', String(params.pageSize))
  const res = await fetch(`${BASE}/tasks?${search.toString()}`, { cache: 'no-store' })
  const data = await readJson<DocxTranslationTaskPage>(res, '获取翻译历史失败')
  return { items: data.items ?? [], total: data.total ?? 0 }
}

export async function fetchTranslationTaskDetail(taskId: string): Promise<DocxTranslationTaskDetail> {
  const res = await fetch(`${BASE}/tasks/${taskId}`, { cache: 'no-store' })
  return readJson<DocxTranslationTaskDetail>(res, '获取任务详情失败')
}


export async function fetchTranslationJobStates(ids: string[]): Promise<DocxTranslationJobState[]> {
  if (!ids.length) return []
  const search = new URLSearchParams()
  ids.forEach(id => search.append('ids', id))
  const res = await fetch(`${BASE}/jobs?${search.toString()}`, { cache: 'no-store' })
  const data = await readJson<{ items: DocxTranslationJobState[] }>(res, '获取任务状态失败')
  return data.items ?? []
}
