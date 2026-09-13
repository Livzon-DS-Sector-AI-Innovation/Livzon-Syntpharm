export type { SummaryStats, RegulatoryDocument, SyncJob, DocumentListParams, PaginatedResponse, ApiResponse, SourceStatus, TrendItem, ClassificationStat, PriorityDocument, DashboardData, DocumentDetail } from '@/types/regulatory-tracker'

import type {
  SummaryStats,
  RegulatoryDocument,
  SyncJob,
  DocumentListParams,
  PaginatedResponse,
  ApiResponse,
  AIAnalysisResult,
  AIBatchAnalysisResult,
  DashboardData,
  DocumentDetail,
} from '@/types/regulatory-tracker'


// ====== AI 分析类型 ======
export type { AIAnalysisResult, AIBatchAnalysisResult }


// Mock AI 分析数据（未来替换为真实 API 调用）
const _MOCK_AI_ANALYSIS: Record<string, AIAnalysisResult> = {}


// ====== API 调用 ======
export async function fetchSummary(): Promise<SummaryStats> {
  const res = await fetch(`/api/v1/registration/regulatory-tracker/summary`, { credentials: 'include' })
  const json: ApiResponse<SummaryStats> = await res.json()
  return json.data
}

export async function fetchDocuments(
  params: DocumentListParams = {}
): Promise<PaginatedResponse<RegulatoryDocument>> {
  const searchParams = new URLSearchParams()
  
  if (params.keyword) searchParams.append('keyword', params.keyword)
  if (params.publishDateFrom) searchParams.append('publishDateFrom', params.publishDateFrom)
  if (params.publishDateTo) searchParams.append('publishDateTo', params.publishDateTo)
  if (params.statusText) searchParams.append('statusText', params.statusText)
  if (params.classification) searchParams.append('classification', params.classification)
  if (params.isNew !== undefined) searchParams.append('isNew', params.isNew.toString())
  if (params.page) searchParams.append('page', params.page.toString())
  if (params.pageSize) searchParams.append('pageSize', params.pageSize.toString())

  const url = `/api/v1/registration/regulatory-documents?${searchParams.toString()}`
  const res = await fetch(url, { credentials: 'include' })
  const json: ApiResponse<PaginatedResponse<RegulatoryDocument>> = await res.json()
  return json.data
}


export async function fetchSyncJobs(
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<SyncJob>> {
  const url = `/api/v1/sync-jobs?page=${page}&pageSize=${pageSize}`
  const res = await fetch(url, { credentials: 'include' })
  const json: ApiResponse<PaginatedResponse<SyncJob>> = await res.json()
  return json.data
}


// ====== AI 分析 API（当前为 mock，未来替换为真实接口） ======

/**
 * 单条文档 AI 分析
 * 当前返回基于规则引擎的 mock 结果，未来将调用后端 LLM 接口
 */

/**
 * 批量文档 AI 分析（化学原料药视角）
 * 当前返回基于规则引擎的 mock 结果，未来将调用后端 LLM 接口
 */

// ====== 新增类型和函数（来自 feature/ra-hcra-frontend） ======

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch(`/api/v1/registration/regulatory-tracker/dashboard`, { credentials: 'include' })
  const json = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '获取仪表盘数据失败')
  }
  return json.data
}

export async function fetchDocumentDetail(docId: string): Promise<DocumentDetail> {
  const res = await fetch(`/api/v1/registration/regulatory-documents/${docId}/detail`, { credentials: 'include' })
  const json = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '获取文档详情失败')
  }
  return json.data
}


export function getExportUrl(params?: DocumentListParams): string {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.publishDateFrom) searchParams.set('publishDateFrom', params.publishDateFrom)
  if (params?.publishDateTo) searchParams.set('publishDateTo', params.publishDateTo)
  if (params?.statusText) searchParams.set('statusText', params.statusText)
  if (params?.classification) searchParams.set('classification', params.classification)
  if (params?.isNew !== undefined) searchParams.set('isNew', String(params.isNew))
  if (params?.impactLevel) searchParams.set('impactLevel', params.impactLevel)
  if (params?.documentCategory) searchParams.set('documentCategory', params.documentCategory)
  if (params?.notificationRequired !== undefined) searchParams.set('notificationRequired', String(params.notificationRequired))
  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : ''
  return `/api/v1/registration/regulatory-documents/export${suffix}`
}