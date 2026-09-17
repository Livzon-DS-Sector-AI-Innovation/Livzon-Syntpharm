/**
 * 研发报告 AI 文档生成 —— 浏览器侧 API
 *
 * 只读 GET（templates/limits/jobDetail/jobsForReport）走统一 fetchApi 封装。
 * 另有两个 AGENTS.md 允许的 client fetch 写操作例外（原因见各函数注释）：
 * 1. createDocGenJob：multipart 大文件上传，Server Actions 受请求体大小限制
 *    且无法可靠转发多文件，按上传例外处理；
 * 2. 文档/说明下载：文件流必须由浏览器直接接收并触发保存，
 *    Server Actions 无法返回文件流。
 */
import { apiGet } from '@/lib/api/client'
import type { components } from '@/types/generated/schema'

export type DocGenTemplateSummary = components['schemas']['DocGenTemplateSummary']
export type DocGenLimits = components['schemas']['DocGenLimits']
export type DocGenJobResponse = components['schemas']['DocGenJobResponse']
export type DocGenJobDetail = components['schemas']['DocGenJobDetail']
export type DocGenInputFileResponse = components['schemas']['DocGenInputFileResponse']
export type DocGenSlotValueResponse = components['schemas']['DocGenSlotValueResponse']
export type DocGenJobDetailResponse = components['schemas']['DocGenJobDetailResponse']
/** 结构化提取信息：单个填充项结果（键名为后端 slot_key） */
export type DocGenExtractedSlot = DocGenSlotValueResponse
/** 结构化提取信息响应体（后端返回 {"slots": [...]}） */
export type DocGenExtractedInfo = components['schemas']['DocGenExtractedInfoResponse']['data']
/** 资料角色：material=研究资料，literature=文献 */
export type DocGenFileRole = DocGenInputFileResponse['role']
/** 对话消息条目（assistant=盘点卡/追问，user=用户补充的原文） */
export type DocGenConversationMessage = components['schemas']['DocGenMessageResponse']
/** 会话与消息列表（任务未创建会话时后端返回 data=null） */
export type DocGenConversationData = components['schemas']['DocGenConversationData']

const API_BASE = '/api/v1'
const DOC_GEN_BASE = `${API_BASE}/research/doc-gen`

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

export async function fetchDocGenTemplates(): Promise<DocGenTemplateSummary[]> {
  const data = await apiGet<NonNullable<components['schemas']['DocGenTemplateListResponse']['data']>>(
    `${DOC_GEN_BASE}/templates`,
  )
  return data ?? []
}

export async function fetchDocGenLimits(): Promise<DocGenLimits> {
  return apiGet<components['schemas']['DocGenLimitsResponse']['data']>(`${DOC_GEN_BASE}/limits`)
}

export async function fetchDocGenJob(jobId: string): Promise<DocGenJobDetail> {
  return apiGet<components['schemas']['DocGenJobDetailResponse']['data']>(`${DOC_GEN_BASE}/jobs/${jobId}`)
}

/** 查询任务的结构化提取信息（仅填充项结果），用于前端预览与编辑 */
export async function fetchDocGenExtractedInfo(jobId: string): Promise<{ slots: DocGenExtractedSlot[] }> {
  const data = await apiGet<DocGenExtractedInfo>(`${DOC_GEN_BASE}/jobs/${jobId}/extracted-info`)
  return { slots: data?.slots ?? [] }
}

/**
 * 查询任务的对话会话与消息。
 *
 * 任务完成「解析 + 初抽」后后端会自动建会话，因此初抽未完成时返回 null；
 * 只读 GET，写操作（发消息/完成/跳过）一律走 Server Actions。
 */
export async function fetchDocGenConversation(jobId: string): Promise<DocGenConversationData | null> {
  const data = await apiGet<components['schemas']['DocGenConversationDataResponse']['data']>(
    `${DOC_GEN_BASE}/jobs/${jobId}/conversation`,
  )
  return data ?? null
}

/** 按项目一次取回全部生成任务（列表页用它避免逐报告请求） */
export async function fetchDocGenJobsByProject(projectId: string): Promise<DocGenJobResponse[]> {
  const data = await apiGet<NonNullable<components['schemas']['DocGenJobListResponse']['data']>>(
    `${DOC_GEN_BASE}/jobs?project_id=${encodeURIComponent(projectId)}`,
  )
  return data ?? []
}

export async function fetchDocGenJobsForReport(reportId: string): Promise<DocGenJobResponse[]> {
  const data = await apiGet<NonNullable<components['schemas']['DocGenJobListResponse']['data']>>(
    `${DOC_GEN_BASE}/reports/${reportId}/jobs`,
  )
  return data ?? []
}

export interface CreateDocGenJobInput {
  /** 交付物模板 ID（Word 母本 + 填充项配置） */
  templateId: string
  files: File[]
  /** 与 files 同序的角色标记，缺省按 material 处理 */
  fileRoles?: DocGenFileRole[]
  reportId?: string
  projectId?: string
  docCode: string
  docVersion: string
  drugName: string
  /** 人工补充说明：作为补充资料参与提取与成文 */
  supplementText?: string
  /** 报告标题（后端据此创建 RdReport 记录） */
  reportTitle?: string
  /** 报告类型（summary/stage/annual/final/custom） */
  reportType?: string
  /** 关联阶段 */
  reportStage?: string
  /** 报告摘要 */
  reportSummary?: string
}

/**
 * 创建文档生成任务（multipart/form-data 上传）。
 *
 * 例外说明（AGENTS.md 上传例外）：资料文件可达数十 MB，Server Actions 存在
 * 请求体大小限制且转发 multipart 不可靠，因此此处直接 fetch 后端相对路径，
 * 由 src/proxy.ts 转发并透传 cookies（auth_token）。
 */
export async function createDocGenJob(input: CreateDocGenJobInput): Promise<DocGenJobResponse> {
  const formData = new FormData()
  formData.append('deliverable_template_id', input.templateId)
  formData.append('doc_code', input.docCode)
  formData.append('doc_version', input.docVersion)
  formData.append('drug_name', input.drugName)
  if (input.reportId) formData.append('report_id', input.reportId)
  if (input.projectId) formData.append('project_id', input.projectId)
  if (input.supplementText) formData.append('supplement_text', input.supplementText)
  if (input.reportTitle) formData.append('report_title', input.reportTitle)
  if (input.reportType) formData.append('report_type', input.reportType)
  if (input.reportStage) formData.append('report_stage', input.reportStage)
  if (input.reportSummary) formData.append('report_summary', input.reportSummary)
  input.files.forEach((file, index) => {
    formData.append('files', file)
    formData.append('file_roles', input.fileRoles?.[index] ?? 'material')
  })

  // 不设置 Content-Type，交给浏览器自动生成 multipart boundary
  const body = await postMultipart<components['schemas']['DocGenJobDataResponse']>(
    `${DOC_GEN_BASE}/jobs`,
    formData,
    '创建生成任务失败',
  )
  return body.data
}

/**
 * 追加资料文件到已有任务（编辑模式保存时调用）。
 *
 * 例外说明（AGENTS.md 上传例外）：multipart 大文件上传，Server Actions 不可靠。
 */
export async function uploadJobFiles(
  jobId: string,
  files: File[],
  fileRoles: DocGenFileRole[] = [],
): Promise<DocGenJobDetailResponse> {
  const formData = new FormData()
  files.forEach((file, index) => {
    formData.append('files', file)
    formData.append('file_roles', fileRoles[index] ?? 'material')
  })
  const body = await postMultipart<components['schemas']['DocGenJobDetailResponse']>(
    `${DOC_GEN_BASE}/jobs/${jobId}/files`,
    formData,
    '上传资料文件失败',
  )
  return body
}

/** 触发浏览器保存 blob（沿用 hr.ts 的下载模式） */
async function saveBlob(res: Response, filename: string): Promise<void> {
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

/**
 * 下载文档初版（docx 文件流）。
 *
 * 例外说明（AGENTS.md 下载例外）：文件流响应必须由浏览器直接接收，
 * Server Actions 无法返回二进制文件流，因此直接 fetch 后走 blob 下载。
 */
export async function downloadDocGenDocument(jobId: string, filename: string): Promise<void> {
  const res = await fetch(`${DOC_GEN_BASE}/jobs/${jobId}/document`, { cache: 'no-store' })
  if (!res.ok) throw new Error('下载文档初版失败')
  await saveBlob(res, filename)
}

/** 下载生成说明（md 文件流），同为下载例外，原因同上 */
export async function downloadDocGenReport(jobId: string, filename: string): Promise<void> {
  const res = await fetch(`${DOC_GEN_BASE}/jobs/${jobId}/report`, { cache: 'no-store' })
  if (!res.ok) throw new Error('下载生成说明失败')
  await saveBlob(res, filename)
}

/**
 * 取文档初版字节流供在线预览（不触发下载）。
 *
 * 例外说明（AGENTS.md 下载例外）：预览需要二进制流交给 docx-preview 渲染，
 * Server Actions 无法返回文件流，因此与下载同样直接 fetch。
 */
export async function fetchDocGenDocumentBlob(jobId: string): Promise<Blob> {
  const res = await fetch(`${DOC_GEN_BASE}/jobs/${jobId}/document`, { cache: 'no-store' })
  if (!res.ok) throw new Error('加载文档预览失败')
  return res.blob()
}

/**
 * 下载任务的资料文件原件（供预览）。
 *
 * 例外说明：文件流必须由浏览器直接接收，Server Actions 无法返回二进制流。
 */
export async function fetchDocGenInputFileBlob(jobId: string, fileId: string): Promise<Blob> {
  const res = await fetch(`${DOC_GEN_BASE}/jobs/${jobId}/input-files/${fileId}/download`, {
    cache: 'no-store',
    credentials: 'include',
  })
  if (!res.ok) throw new Error('加载资料文件失败')
  return res.blob()
}

/**
 * 上传模板文件（docx/dotx/doc）到交付物模板，后端自动留档为一个新版本。
 *
 * 例外原因：multipart 文件上传，Server Actions 受请求体大小限制。
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
    `${DOC_GEN_BASE}/deliverable-templates/${templateId}/upload`,
    formData,
    '上传失败',
  )
  return result.data
}

/**
 * 下载交付物模板文件
 */
export async function downloadDeliverableTemplate(id: string): Promise<Blob> {
  const response = await fetch(`/api/v1/research/doc-gen/deliverable-templates/${id}/download`, {
    credentials: 'include',
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: '下载失败' }))
    throw new Error(error.message || error.detail || `下载失败: ${response.status}`)
  }
  return response.blob()
}

/**
 * 批量上传 Word 模板文件
 * 例外原因：multipart 文件上传，Server Actions 受请求体大小限制
 */
/** 批量上传结果：字段派生自 OpenAPI 生成类型，后端有默认值故在此收窄为必填 */
type BatchUploadRaw = components['schemas']['DocGenBatchUploadResult']
export type DocGenBatchUploadResult = Required<Pick<BatchUploadRaw, 'created' | 'versioned' | 'skipped'>>

export async function uploadDeliverableTemplates(files: File[]): Promise<DocGenBatchUploadResult> {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  const result = await postMultipart<{ data: BatchUploadRaw }>(
    `${DOC_GEN_BASE}/deliverable-templates/batch-upload`,
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
    `${DOC_GEN_BASE}/deliverable-templates/${templateId}/versions`,
  )
  return data ?? []
}

/**
 * 下载指定历史版本的 Word 原件（供浏览器保存或在线预览）。
 *
 * 例外说明（AGENTS.md 下载例外）：文件流必须由浏览器直接接收，
 * Server Actions 无法返回二进制文件流，因此与模板下载同样直接 fetch。
 */
export async function downloadDeliverableTemplateVersion(templateId: string, versionId: string): Promise<Blob> {
  const response = await fetch(
    `/api/v1/research/doc-gen/deliverable-templates/${templateId}/versions/${versionId}/download`,
    { cache: 'no-store', credentials: 'include' },
  )
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { message?: string; detail?: string } | null
    throw new Error(error?.message || error?.detail || `下载历史版本失败: ${response.status}`)
  }
  return response.blob()
}

/** 内置填充项配置（上传 Word 模板原件时选择）——类型来自 OpenAPI 生成结果 */
export type DocGenSlotProfile = components['schemas']['DocGenSlotProfile']

/** 可用于 AI 生成的交付物模板——类型来自 OpenAPI 生成结果 */
export type DocGenUsableTemplate = components['schemas']['DocGenUsableTemplate']

/** 拉取内置填充项配置清单 */
export async function fetchDocGenSlotProfiles(): Promise<DocGenSlotProfile[]> {
  const data = await apiGet<DocGenSlotProfile[]>('/api/v1/research/doc-gen/slot-profiles')
  return data ?? []
}

/** 拉取可用于 AI 生成的模板（必须有 Word 模板原件与合法填充项配置） */
export async function fetchUsableDocGenTemplates(): Promise<DocGenUsableTemplate[]> {
  const data = await apiGet<DocGenUsableTemplate[]>('/api/v1/research/doc-gen/templates')
  return data ?? []
}
