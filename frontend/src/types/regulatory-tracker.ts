/**
 * Regulatory Tracker module TypeScript types
 * 
 * These are ViewModel/display types not covered by the OpenAPI spec.
 * Per AGENTS.md: "允许手写前端 UI 类型，例如表单状态、筛选条件、表格状态、下拉选项、ViewModel/display 类型"
 * 
 * The backend doesn't export these types via OpenAPI because:
 * - Routes use `response_model=dict` or return dicts
 * - These types use camelCase (UI-oriented) while backend uses snake_case
 * - They represent display ViewModels, not raw API responses
 * 
 * API input types should use generated schema when available.
 */

export interface SummaryStats {
  totalCount: number
  todayNewCount: number
  unreadNewCount: number
  lastSyncTime: string | null
  lastSyncStatus: string | null
}

export interface RegulatoryDocument {
  id: string
  sourceId: string
  channelId: string
  documentId: string
  title: string
  publishDate: string | null
  statusText: string | null
  classification: string | null
  originalUrl: string | null
  isNew: boolean
  isRead: boolean
  firstFoundAt: string
  lastCheckedAt: string | null
  createdAt: string
  aiSummary: string | null
  aiKeyPoints: Record<string, unknown> | null
  aiRelevanceScore: number | null
  aiAnalyzedAt: string | null
  aiAnalysisStatus: string | null
  impact_level: string
  impact_score: number
  notification_required: boolean
  documentCategory: string | null
  documentCategoryName: string
  sourceName?: string
  detailText?: string
  relatedDocuments?: RegulatoryDocument[]
}

export interface SyncJob {
  id: string
  sourceId: string
  channelId: string
  jobType: string
  startedAt: string | null
  finishedAt: string | null
  status: string
  totalPages: number | null
  checkedCount: number
  newCount: number
  updatedCount: number
  errorMessage: string | null
  createdAt: string
}

export interface DocumentListParams {
  keyword?: string
  publishDateFrom?: string
  publishDateTo?: string
  statusText?: string
  classification?: string
  isNew?: boolean
  impactLevel?: string
  documentCategory?: string
  notificationRequired?: boolean
  firstFoundFrom?: string
  firstFoundTo?: string
  regulationType?: string
  sortBy?: string
  sortOrder?: string
  page?: number
  pageSize?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

// AI Analysis types
export interface AIAnalysisResult {
  documentId: string
  documentTitle: string
  impactLevel: 'high' | 'medium' | 'low' | 'none'
  impactScore: number
  impactSummary: string
  keyChanges: string[]
  impactAreas: string[]
  complianceSuggestions: string[]
  timelineUrgency: 'urgent' | 'normal' | 'long_term'
  generatedAt: string
}

export interface AIBatchAnalysisResult {
  totalAnalyzed: number
  highImpact: number
  mediumImpact: number
  lowImpact: number
  noneImpact: number
  topConcerns: Array<{
    title: string
    documentId: string
    impactLevel: 'high' | 'medium' | 'low' | 'none'
    reason: string
  }>
  overallAssessment: string
  generatedAt: string
}

// ====== Dashboard Types ======

export interface SourceStatus {
  sourceId: string
  sourceName: string
  enabled: boolean
  lastSyncAt: string | null
  lastSyncStatus: string | null
  documentCount: number
}

export interface TrendItem {
  date: string
  count: number
}

export interface PriorityDocument {
  id: string
  title: string
  publishDate: string | null
  impactLevel: 'high' | 'medium' | 'low' | 'none'
  impactScore: number
}

export interface DashboardData {
  summary: SummaryStats
  sourceStatuses: SourceStatus[]
  recentTrend: TrendItem[]
  priorityDocuments: PriorityDocument[]
}

export interface DocumentDetail extends RegulatoryDocument {
  sourceName: string
  detailText: string
  relatedDocuments: RegulatoryDocument[]
}
