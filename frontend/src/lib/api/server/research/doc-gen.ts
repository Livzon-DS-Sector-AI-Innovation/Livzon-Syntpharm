/**
 * 研发报告 AI 文档生成 —— 服务端 API（Server Component / Server Action 使用）
 * 风格照同层 research.ts：通过 API_BASE_URL 访问后端，返回统一响应包裹中的 data。
 */
import { apiFetch, getApiBaseUrl, safeApiFetch } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

type DocGenJobResponse = components['schemas']['DocGenJobResponse']
type DocGenJobDetail = components['schemas']['DocGenJobDetail']
type DocGenTemplateSummary = components['schemas']['DocGenTemplateSummary']
type DocGenLimits = components['schemas']['DocGenLimits']
type DocGenConversationData = components['schemas']['DocGenConversationData']

const DOC_GEN_BASE = '/api/v1/research/doc-gen'

export async function fetchDocGenTemplates(): Promise<DocGenTemplateSummary[]> {
  const result = await apiFetch<components['schemas']['DocGenTemplateListResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/templates`,
  )
  return result.data ?? []
}

export async function fetchDocGenLimits(): Promise<DocGenLimits> {
  const result = await apiFetch<components['schemas']['DocGenLimitsResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/limits`,
  )
  return result.data
}

export async function fetchDocGenJob(jobId: string): Promise<DocGenJobDetail> {
  const result = await apiFetch<components['schemas']['DocGenJobDetailResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/jobs/${jobId}`,
  )
  return result.data
}

export async function fetchDocGenJobsForReport(reportId: string): Promise<DocGenJobResponse[]> {
  const result = await apiFetch<components['schemas']['DocGenJobListResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/reports/${reportId}/jobs`,
  )
  return result.data ?? []
}

export async function cancelDocGenJob(jobId: string): Promise<DocGenJobResponse> {
  const result = await apiFetch<components['schemas']['DocGenJobDataResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/jobs/${jobId}/cancel`,
    { method: 'POST' },
  )
  return result.data
}

/** 人工确认提取结果并续跑渲染；slots 只含被改过的填充项（key → 修正后的文本） */
export async function confirmDocGenJob(jobId: string, slots: Record<string, string>): Promise<DocGenJobResponse> {
  const result = await apiFetch<components['schemas']['DocGenJobDataResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/jobs/${jobId}/confirm`,
    { method: 'POST', body: JSON.stringify({ slots }) },
  )
  return result.data
}

/** 两步流程第一步：触发 AI 提取信息（对话模式停在草稿时由用户手动开始） */
export async function extractDocGenJob(jobId: string): Promise<DocGenJobResponse> {
  const result = await apiFetch<components['schemas']['DocGenJobDataResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/jobs/${jobId}/extract`,
    { method: 'POST' },
  )
  return result.data
}

/**
 * 对话补全写操作（发消息 / 完成 / 跳过）。
 *
 * 用 safeApiFetch 而不是 apiFetch：轮数上限、会话已结束等业务拒绝需要把后端的
 * message 原样抛给用户，apiFetch 在解析错误体时会拿到通用文案。
 */
async function postConversationAction(
  path: string,
  body?: Record<string, unknown>,
): Promise<DocGenConversationData> {
  const result = await safeApiFetch<DocGenConversationData>(
    `${DOC_GEN_BASE}${path}`,
    body ? { method: 'POST', body: JSON.stringify(body) } : { method: 'POST' },
  )
  if (result.code >= 400 || !result.data) {
    throw new Error(result.message || '操作失败，请稍后重试')
  }
  return result.data
}

/** 发送一条用户消息：模型抽值 → 校验 → 写入槽位，返回更新后的会话与全部消息 */
export async function sendDocGenMessage(jobId: string, content: string): Promise<DocGenConversationData> {
  return postConversationAction(`/jobs/${jobId}/messages`, { content })
}

/** 完成对话（保留已补值），随后到确认页逐项检查并确认生成 */
export async function completeDocGenConversation(jobId: string): Promise<DocGenConversationData> {
  return postConversationAction(`/jobs/${jobId}/conversation/complete`)
}

/** 跳过对话：与完成等效，仅语义不同（不计入轮数） */
export async function skipDocGenConversation(jobId: string): Promise<DocGenConversationData> {
  return postConversationAction(`/jobs/${jobId}/conversation/skip`)
}

/** 修改报告基本信息与补充说明 */
export async function updateDocGenJob(
  jobId: string,
  payload: {
    doc_code?: string | null
    doc_version?: string | null
    drug_name?: string | null
    supplement_text?: string | null
    template_code?: string | null
  },
): Promise<DocGenJobResponse> {
  const result = await apiFetch<components['schemas']['DocGenJobDataResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/jobs/${jobId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
  return result.data
}

type DocGenTemplateVersionRestoreData = components['schemas']['DocGenTemplateVersionRestoreData']

/**
 * 回滚交付物模板到指定历史版本。
 *
 * 后端不在旧记录上原地生效，而是以该版本内容新建 v(N+1) 并设为当前生效版本
 * （类似 git revert），因此历史版本不可改写、可再次回滚回来。
 */
export async function restoreDeliverableTemplateVersion(
  templateId: string,
  versionId: string,
): Promise<DocGenTemplateVersionRestoreData> {
  const result = await apiFetch<components['schemas']['DocGenTemplateVersionRestoreResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/deliverable-templates/${templateId}/versions/${versionId}/restore`,
    { method: 'POST' },
  )
  return result.data
}

/** 删除模板的一个历史版本；当前生效版本与唯一版本后端会拒绝并返回业务提示 */
export async function deleteDeliverableTemplateVersion(templateId: string, versionId: string): Promise<void> {
  await apiFetch<components['schemas']['DocGenOperationResponse']>(
    `${getApiBaseUrl()}${DOC_GEN_BASE}/deliverable-templates/${templateId}/versions/${versionId}`,
    { method: 'DELETE' },
  )
}
