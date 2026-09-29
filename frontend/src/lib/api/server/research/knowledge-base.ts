/**
 * 研发项目知识库 —— 服务端 API（Server Component / Server Action 使用）
 *
 * 写操作用 safeApiFetch：业务拒绝（项目已挂知识库、知识库服务未配置等）
 * 需要把后端的 message 原样带给用户，apiFetch 的错误体解析会拿到通用文案。
 */
import { apiFetch, getApiBaseUrl, safeApiFetch } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

type KnowledgeBaseItem = components['schemas']['KnowledgeBaseItem']
type KbDocumentItem = components['schemas']['KbDocumentItem']
type KbLimits = components['schemas']['KbLimits']
type KnowledgeBaseCreateRequest = components['schemas']['KnowledgeBaseCreateRequest']

const KB_BASE = '/api/v1/research/knowledge-bases'

/** 异步写操作的统一返回体解析：code >= 400 或空 data 都视为失败 */
async function unwrapWrite<T>(endpoint: string, options: RequestInit, fallback: string): Promise<T> {
  const result = await safeApiFetch<T>(endpoint, options)
  if (result.code >= 400 || result.data === undefined || result.data === null) {
    throw new Error(result.message || fallback)
  }
  return result.data
}

export async function fetchKnowledgeBases(projectId?: string): Promise<KnowledgeBaseItem[]> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
  const result = await apiFetch<components['schemas']['KnowledgeBaseListResponse']>(
    `${getApiBaseUrl()}${KB_BASE}${query}`,
  )
  return result.data ?? []
}

export async function fetchKbLimits(): Promise<KbLimits> {
  const result = await apiFetch<components['schemas']['KbLimitsResponse']>(`${getApiBaseUrl()}${KB_BASE}/limits`)
  if (!result.data) {
    throw new Error('读取知识库上传限制失败')
  }
  return result.data
}

export async function fetchKbDocuments(kbId: string): Promise<KbDocumentItem[]> {
  const result = await apiFetch<components['schemas']['KbDocumentListResponse']>(
    `${getApiBaseUrl()}${KB_BASE}/${kbId}/documents`,
  )
  return result.data ?? []
}

/** 为研发项目创建知识库（后端同步在 RAGFlow 建数据集） */
export async function createKnowledgeBase(payload: KnowledgeBaseCreateRequest): Promise<KnowledgeBaseItem> {
  return unwrapWrite<KnowledgeBaseItem>(
    `${KB_BASE}`,
    { method: 'POST', body: JSON.stringify(payload) },
    '创建知识库失败',
  )
}

/** 删除知识库（同时清理远端数据集与本地文档镜像） */
export async function deleteKnowledgeBase(kbId: string): Promise<void> {
  await unwrapWrite<Record<string, string>>(
    `${KB_BASE}/${kbId}`,
    { method: 'DELETE' },
    '删除知识库失败',
  )
}

/** 从知识库移除一份文档 */
export async function deleteKbDocument(kbId: string, documentRowId: string): Promise<KbDocumentItem[]> {
  return unwrapWrite<KbDocumentItem[]>(
    `${KB_BASE}/${kbId}/documents/${documentRowId}`,
    { method: 'DELETE' },
    '删除文档失败',
  )
}

/** 重新解析一份文档（清空旧切片后重跑） */
export async function reparseKbDocument(kbId: string, documentRowId: string): Promise<KbDocumentItem[]> {
  return unwrapWrite<KbDocumentItem[]>(
    `${KB_BASE}/${kbId}/documents/${documentRowId}/reparse`,
    { method: 'POST' },
    '重新解析失败',
  )
}
