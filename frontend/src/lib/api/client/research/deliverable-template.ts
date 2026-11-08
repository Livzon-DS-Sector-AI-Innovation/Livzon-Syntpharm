/**
 * 交付物模板 —— 浏览器侧 API
 *
 * 只包含 Word 母本的上传、下载与版本历史，不涉及任何文档生成能力。
 * 两个 client fetch 例外（AGENTS.md 上传/下载例外）：
 * 1. 上传：multipart 大文件，Server Actions 受请求体大小限制；
 * 2. 下载：文件流必须由浏览器直接接收并触发保存。
 */
import { apiGet } from '@/lib/api/client'
import type { DocGenTemplateSlots } from '@/types/research/deliverable-template-slot'
import type { components } from '@/types/generated/schema'

const DOC_TEMPLATE_BASE = '/api/v1/research/doc-gen/deliverable-templates'

/** 上传兜底超时：数十 MB 正常在分钟级完成，超过即视为代理/后端异常 */
const UPLOAD_TIMEOUT_MS = 10 * 60 * 1000

/**
 * multipart 上传的统一封装（AGENTS.md 上传例外）。
 *
 * 必须带超时：请求体被代理层截断时后端会复位连接且不回响应，fetch 会永远 pending，
 * 调用方的 finally 不执行，按钮就会一直卡在「上传中」。
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
      throw new Error(`${fallback}：上传超时，请减少文件大小或分批上传`)
    }
    throw new Error(`${fallback}：${e instanceof Error ? e.message : '网络异常，请稍后重试'}`)
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { message?: string; detail?: unknown } | null
    const detail = typeof body?.detail === 'string' ? body.detail : ''
    throw new Error(body?.message || detail || `${fallback}: ${response.status}`)
  }
  return (await response.json()) as T
}

/**
 * 上传模板文件（docx/dotx/doc）到交付物模板，后端自动留档为一个新版本。
 *
 * changeNote 是该版本的变更备注（可空），用于版本历史里说明「这次改了什么」。
 */
export async function uploadDeliverableTemplateFile(
  templateId: string,
  file: File,
  changeNote?: string,
): Promise<components['schemas']['DocGenTemplateFileData']> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('change_note', changeNote ?? '')
  const result = await postMultipart<components['schemas']['DocGenTemplateFileResponse']>(
    `${DOC_TEMPLATE_BASE}/${templateId}/upload`,
    formData,
    '上传失败',
  )
  return result.data
}

/** 下载交付物模板文件 */
export async function downloadDeliverableTemplate(id: string): Promise<Blob> {
  const response = await fetch(`${DOC_TEMPLATE_BASE}/${id}/download`, { credentials: 'include' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: '下载失败' }))
    throw new Error(error.message || error.detail || `下载失败: ${response.status}`)
  }
  return response.blob()
}

/** 批量上传结果：字段派生自 OpenAPI 生成类型，后端有默认值故在此收窄为必填 */
type BatchUploadRaw = components['schemas']['DocGenBatchUploadResult']
export type DocGenBatchUploadResult = Required<Pick<BatchUploadRaw, 'created' | 'versioned' | 'skipped'>>

/** 批量上传 Word 模板文件：同名文件作为该模板的新版本挂载 */
export async function uploadDeliverableTemplates(files: File[]): Promise<DocGenBatchUploadResult> {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  const result = await postMultipart<components['schemas']['DocGenBatchUploadResponse']>(
    `${DOC_TEMPLATE_BASE}/batch-upload`,
    formData,
    '批量上传失败',
  )
  return {
    created: result.data.created ?? [],
    versioned: result.data.versioned ?? [],
    skipped: result.data.skipped ?? [],
  }
}

/** 模板的历史版本（含上传人与版本说明，用于版本历史展示） */
export type DocGenTemplateVersion = components['schemas']['DocGenTemplateVersionItem']

/** 拉取模板的版本历史（新版本在前） */
export async function fetchDeliverableTemplateVersions(templateId: string): Promise<DocGenTemplateVersion[]> {
  const data = await apiGet<NonNullable<components['schemas']['DocGenTemplateVersionListResponse']['data']>>(
    `${DOC_TEMPLATE_BASE}/${templateId}/versions`,
  )
  return data ?? []
}

/**
 * 拉取模板的槽位结构与母本候选位置。
 *
 * 只读母本取候选位、不触发模型识别，所以可以在抽屉打开时直接调用。
 */
export async function fetchDeliverableTemplateSlots(templateId: string): Promise<DocGenTemplateSlots> {
  const data = await apiGet<components['schemas']['DocGenTemplateSlotsData'] | null>(
    `${DOC_TEMPLATE_BASE}/${templateId}/slots`,
  )
  if (!data) {
    throw new Error('槽位结构返回为空，请稍后重试')
  }
  return data
}

/**
 * 下载指定历史版本的 Word 原件（供浏览器保存或在线预览）。
 *
 * 例外说明（AGENTS.md 下载例外）：文件流必须由浏览器直接接收，
 * Server Actions 无法返回二进制文件流，因此与模板下载同样直接 fetch。
 */
export async function downloadDeliverableTemplateVersion(templateId: string, versionId: string): Promise<Blob> {
  const response = await fetch(`${DOC_TEMPLATE_BASE}/${templateId}/versions/${versionId}/download`, {
    cache: 'no-store',
    credentials: 'include',
  })
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { message?: string; detail?: string } | null
    throw new Error(error?.message || error?.detail || `下载历史版本失败: ${response.status}`)
  }
  return response.blob()
}