/**
 * 研发项目知识库 —— 浏览器侧 API
 *
 * 只读查询走统一 apiGet；上传走 client fetch（AGENTS.md 的上传例外）：
 * multipart 大文件经 Server Actions 会受请求体大小限制，且无法可靠转发多文件。
 * 删除与重新解析是写操作，按规范放在 actions/research/knowledge-base.ts。
 */
import { apiGet } from '@/lib/api/client'
import { saveBlob } from '@/lib/utils/download'
import type {
  KbChunkList,
  KbDocumentItem,
  KbLimits,
  KnowledgeBaseItem,
  KbUploadResult,
} from '@/types/research/knowledge-base'

const API_BASE = '/api/v1'
const KB_BASE = `${API_BASE}/research/knowledge-bases`

/** 上传兜底超时：知识库服务解析前要先收完文件，大文件走分钟级 */
const UPLOAD_TIMEOUT_MS = 15 * 60 * 1000

/**
 * multipart 上传封装。
 *
 * 必须带超时：请求体被代理层截断时后端会复位连接且不回响应，
 * fetch 会永远 pending，按钮就卡在「上传中」。
 */
async function postMultipart<T>(path: string, formData: FormData, fallback: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      method: 'POST',
      body: formData,
      credentials: 'include',
      cache: 'no-store',
      signal: AbortSignal.timeout(UPLOAD_TIMEOUT_MS),
    })
  } catch (e) {
    if (e instanceof Error && (e.name === 'TimeoutError' || e.name === 'AbortError')) {
      throw new Error(`${fallback}：上传超时，请减少文件数量或分批上传`)
    }
    throw new Error(`${fallback}：${e instanceof Error ? e.message : '网络异常，请稍后重试'}`)
  }
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, fallback))
  }
  return (await response.json()) as T
}

/** 上传限制（含「知识库服务是否已配置」，用于提前提示） */
export async function fetchKbLimits(): Promise<KbLimits> {
  return apiGet<KbLimits>(`${KB_BASE}/limits`)
}

/** 按项目取知识库（通常 0 或 1 条）：新建报告页据此判断项目是否已挂知识库 */
export async function fetchKnowledgeBasesByProject(projectId: string): Promise<KnowledgeBaseItem[]> {
  return apiGet<KnowledgeBaseItem[]>(`${KB_BASE}?project_id=${encodeURIComponent(projectId)}`)
}

/**
 * 文档列表（含解析进度）。
 *
 * refresh=true 时后端会回源 RAGFlow 对账，因此这里拿到的 progress 是实时的，
 * 前端只需按固定间隔轮询本接口即可。
 */
export async function fetchKbDocuments(kbId: string): Promise<KbDocumentItem[]> {
  return apiGet<KbDocumentItem[]>(`${KB_BASE}/${kbId}/documents?refresh=true`)
}

/** 上传资料到知识库并触发解析；返回成功/跳过清单与刷新后的文档列表 */
export async function uploadKbDocuments(kbId: string, files: File[]): Promise<KbUploadResult> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  return postMultipart<KbUploadResult>(`${KB_BASE}/${kbId}/documents`, formData, '上传资料失败')
}

/**
 * 取资料原件字节流（预览用）。
 *
 * 例外说明（AGENTS.md 下载例外）：预览需要二进制流交给 docx-preview / 图片 / PDF 渲染，
 * Server Actions 无法返回文件流，因此与下载一样由浏览器直接 fetch。
 */
export async function fetchKbDocumentBlob(
  kbId: string,
  documentRowId: string,
  options: KbFileUrlOptions = {},
): Promise<Blob> {
  const response = await fetch(documentFileUrl(kbId, documentRowId, { inline: true, ...options }), {
    cache: 'no-store',
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, '加载资料文件失败'))
  }
  return response.blob()
}

export interface KbFileUrlOptions {
  /** 以 inline 返回：浏览器内直接打开而不是下载 */
  inline?: boolean
  /** 让后端把 Office 文档转成 PDF（.doc/.xls/.xlsx/.ppt 等浏览器渲染不了的格式） */
  asPdf?: boolean
}

/** 资料原件地址（预览与下载共用） */
export function documentFileUrl(
  kbId: string,
  documentRowId: string,
  options: KbFileUrlOptions = {},
): string {
  const params = new URLSearchParams()
  if (options.inline) params.set('inline', 'true')
  if (options.asPdf) params.set('as_pdf', 'true')
  const query = params.toString()
  return `${KB_BASE}/${kbId}/documents/${documentRowId}/download${query ? `?${query}` : ''}`
}

/**
 * 切片配图地址（PDF 页图 / 图注配图）。
 *
 * 后端鉴权支持 auth_token Cookie，所以浏览器 `<img>` 直接引用即可，不用转 blob。
 */
export function kbImageUrl(kbId: string, imageId: string): string {
  return `${KB_BASE}/${kbId}/images/${encodeURIComponent(imageId)}`
}

/** 解析切片分页（「解析内容」预览用：docx/xls 等无法在浏览器直接渲染） */
export async function fetchKbDocumentChunks(
  kbId: string,
  documentRowId: string,
  page = 1,
  pageSize = 50,
): Promise<KbChunkList> {
  return apiGet<KbChunkList>(
    `${KB_BASE}/${kbId}/documents/${documentRowId}/chunks?page=${page}&page_size=${pageSize}`,
  )
}

/** 下载资料原件到本地 */
export async function downloadKbDocument(
  kbId: string,
  documentRowId: string,
  fileName: string,
): Promise<void> {
  const response = await fetch(documentFileUrl(kbId, documentRowId), {
    cache: 'no-store',
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, '下载失败'))
  }
  saveBlob(await response.blob(), fileName)
}

/** 后端出错时返回的是统一信封的 JSON，尽量取出可读原因 */
async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  const body = (await response.json().catch(() => null)) as { message?: string; detail?: unknown } | null
  const detail = typeof body?.detail === 'string' ? body.detail : ''
  return body?.message || detail || `${fallback}: ${response.status}`
}
