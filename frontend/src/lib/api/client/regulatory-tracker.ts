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

function generateMockAnalysis(doc: RegulatoryDocument): AIAnalysisResult {
  const title = doc.title || ''
  const classification = doc.classification || ''
  const isChemical = classification.includes('化学') || title.includes('化学') || title.includes('原料药') || title.includes('API')
  const isBio = classification.includes('生物') || title.includes('生物')
  const isBE = title.includes('生物等效性') || title.includes('BE')
  const isPharma = title.includes('药学') || title.includes('制剂') || title.includes('处方')
  const isQuality = title.includes('质量') || title.includes('稳定性') || title.includes('杂质')

  let impactLevel: 'high' | 'medium' | 'low' | 'none' = 'low'
  let impactScore = 30
  let impactSummary = '该法规对化学原料药业务影响较小，建议常规关注。'
  const keyChanges: string[] = []
  const impactAreas: string[] = []
  const complianceSuggestions: string[] = []
  let timelineUrgency: 'urgent' | 'normal' | 'long_term' = 'long_term'

  if (isChemical && isBE) {
    impactLevel = 'medium'
    impactScore = 55
    impactSummary = '该指导原则涉及化学药生物等效性研究要求，可能影响原料药供应商变更时的桥接研究策略。'
    keyChanges.push('明确生物等效性试验设计要求', '规定参比制剂选择标准')
    impactAreas.push('供应商变更评估', '工艺验证策略')
    complianceSuggestions.push('评估现有供应商变更是否触发 BE 研究', '更新变更控制流程')
    timelineUrgency = 'normal'
  } else if (isChemical && isPharma) {
    impactLevel = 'high'
    impactScore = 80
    impactSummary = '该指导原则直接涉及化学药药学研究要求，对原料药生产工艺和质量控制有重大影响。'
    keyChanges.push('更新原料药生产工艺验证要求', '强化关键质量属性控制', '提高杂质限度要求')
    impactAreas.push('生产工艺', '质量控制', '供应商管理', '注册申报')
    complianceSuggestions.push('对照新规逐项评估现有工艺合规性', '更新关键工艺参数控制策略', '准备补充申报资料')
    timelineUrgency = 'urgent'
  } else if (isQuality && (isChemical || !isBio)) {
    impactLevel = 'high'
    impactScore = 75
    impactSummary = '质量相关指导原则更新，直接影响原料药质量标准制定和控制策略。'
    keyChanges.push('调整杂质谱分析方法', '强化稳定性研究要求', '更新质量标准限度')
    impactAreas.push('质量标准', '稳定性研究', '分析方法')
    complianceSuggestions.push('审查现有质量标准是否符合新规', '评估是否需要进行补充稳定性研究')
    timelineUrgency = 'normal'
  } else if (isChemical) {
    impactLevel = 'medium'
    impactScore = 50
    impactSummary = '该指导原则涉及化学药领域，对原料药业务有中等程度影响，建议重点评估相关条款。'
    keyChanges.push('更新相关技术要求', '调整研究策略')
    impactAreas.push('注册申报', '合规评估')
    complianceSuggestions.push('组织技术团队研读新规重点条款', '评估对现有品种的潜在影响')
    timelineUrgency = 'normal'
  } else if (title.includes('中药')) {
    impactLevel = 'none'
    impactScore = 5
    impactSummary = '该指导原则仅针对中药领域，与化学原料药业务无直接关联。'
  } else {
    impactLevel = 'low'
    impactScore = 20
    impactSummary = '该指导原则主要涉及其他药品类型，对化学原料药影响有限，建议保持关注。'
  }

  return {
    documentId: doc.id,
    documentTitle: title,
    impactLevel,
    impactScore,
    impactSummary,
    keyChanges,
    impactAreas,
    complianceSuggestions,
    timelineUrgency,
    generatedAt: new Date().toISOString(),
  }
}

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