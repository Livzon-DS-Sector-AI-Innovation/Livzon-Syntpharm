import type { 
  EnergyOverviewData, 
  CollectLogDetail,
  EnergyPlatform,
  AlertRule,
  AlertRecord,
  EnergyMonthlyRecord,
  EnergyWorkshop,
  MonthlySummary,
  SyncJobStatus,
  RuleQueryParams,
  RecordQueryParams,
  MonthlyRecordQueryParams,
  WorkshopQueryParams,
  PaginatedResponse
} from '@/types/energy'
import { apiGet, apiFetchPaginated, fetchApi } from '@/lib/api/client'

const API_BASE = '/api/v1'

// ═══════════════════════════════════════════════════════════
//  能源总览
// ═══════════════════════════════════════════════════════════

function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return ''
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) searchParams.set(k, String(v))
  })
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

export async function fetchEnergyOverviewClient(params: {
  energy_type?: string
  start_time: string
  end_time: string
}): Promise<EnergyOverviewData> {
  const query = buildQueryString(params)
  return apiGet<EnergyOverviewData>(`${API_BASE}/energy/overview${query}`)
}

export async function fetchCollectLogDetailClient(logId: string): Promise<CollectLogDetail> {
  return apiGet<CollectLogDetail>(`${API_BASE}/energy/collect/logs/${logId}/detail`)
}

export async function fetchPlatformsClient(): Promise<EnergyPlatform[]> {
  return apiGet<EnergyPlatform[]>(`${API_BASE}/energy/platforms`)
}

// ═══════════════════════════════════════════════════════════
//  预警规则
// ═══════════════════════════════════════════════════════════

export async function fetchAlertRules(params?: RuleQueryParams): Promise<PaginatedResponse<AlertRule>> {
  const query = buildQueryString(params as Record<string, unknown>)
  return apiFetchPaginated<AlertRule>(`${API_BASE}/energy/alerts/rules${query}`)
}

// ═══════════════════════════════════════════════════════════
//  预警记录
// ═══════════════════════════════════════════════════════════

export async function fetchAlertRecords(params?: RecordQueryParams): Promise<PaginatedResponse<AlertRecord>> {
  const query = buildQueryString(params as Record<string, unknown>)
  return apiFetchPaginated<AlertRecord>(`${API_BASE}/energy/alerts/records${query}`)
}

// ═══════════════════════════════════════════════════════════
//  月度记录
// ═══════════════════════════════════════════════════════════

export async function fetchMonthlyRecordsClient(params?: MonthlyRecordQueryParams): Promise<PaginatedResponse<EnergyMonthlyRecord>> {
  const query = buildQueryString(params as Record<string, unknown>)
  return apiFetchPaginated<EnergyMonthlyRecord>(`${API_BASE}/energy/monthly${query}`)
}

export async function fetchWorkshopsClient(params?: WorkshopQueryParams): Promise<EnergyWorkshop[]> {
  const query = buildQueryString(params as Record<string, unknown>)
  return apiGet<EnergyWorkshop[]>(`${API_BASE}/energy/workshops${query}`)
}

export async function fetchWorkshopsPageClient(params?: WorkshopQueryParams): Promise<PaginatedResponse<EnergyWorkshop>> {
  const query = buildQueryString(params as Record<string, unknown>)
  return apiFetchPaginated<EnergyWorkshop>(`${API_BASE}/energy/workshops${query}`)
}

export async function fetchMonthlySummaryClient(params?: MonthlyRecordQueryParams): Promise<MonthlySummary> {
  const query = buildQueryString(params as Record<string, unknown>)
  return apiGet<MonthlySummary>(`${API_BASE}/energy/monthly/summary${query}`)
}

// ═══════════════════════════════════════════════════════════
//  异步导入任务状态
// ═══════════════════════════════════════════════════════════

/**
 * 查异步导入任务状态。`/sync/bitable*` 只回受理句柄，计数必须靠这里轮询（`D-48`）。
 * 任务状态存在后端进程内（`D-11`），重启即丢，因此 404 是「状态不可查」而不是「任务失败」。
 */
export async function fetchSyncJobClient(jobId: string): Promise<SyncJobStatus> {
  return apiGet<SyncJobStatus>(`${API_BASE}/energy/jobs/${jobId}`)
}

// ═══════════════════════════════════════════════════════════
//  单耗目标管理
// ═══════════════════════════════════════════════════════════

export interface UnitConsumptionTarget {
  id: string
  workshop_id: string
  workshop_name?: string
  target_month: string
  target_unit_consumption: number
  created_at: string
}

export async function createTarget(data: {
  workshop_id: string
  target_month: string
  target_unit_consumption: number
}): Promise<UnitConsumptionTarget> {
  const result = await fetchApi<{ code: number; data: UnitConsumptionTarget; message?: string }>(`${API_BASE}/energy/targets`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
  return result.data
}

export async function updateTarget(
  targetId: string,
  data: { target_unit_consumption: number }
): Promise<UnitConsumptionTarget> {
  const result = await fetchApi<{ code: number; data: UnitConsumptionTarget; message?: string }>(`${API_BASE}/energy/targets/${targetId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
  return result.data
}

export async function getTarget(
  workshopId: string,
  targetMonth: string
): Promise<UnitConsumptionTarget | null> {
  try {
    const result = await fetchApi<{ code: number; data: UnitConsumptionTarget | null; message?: string }>(`${API_BASE}/energy/targets/${workshopId}/${targetMonth}`)
    return result.data
  } catch {
    return null
  }
}

// ═══════════════════════════════════════════════════════════
//  AI 分析（V2 - 支持单耗）
// ═══════════════════════════════════════════════════════════

export interface AISuggestion {
  status: string
  summary: string
  detailed_analysis: string
  recommendations: string[]
  confidence_level: 'high' | 'medium' | 'low'
}

export interface AIAnalysisResult {
  workshop_id: string
  workshop_name: string
  analysis_month: string
  total_energy_kwh: number
  production_items: { product_name: string; quantity: number; unit: string }[]
  actual_unit_consumption: number
  target_unit_consumption: number | null
  deviation_rate: number | null
  deviation_status: 'normal' | 'warning' | 'critical' | 'unknown'
  ai_suggestion: AISuggestion | null
}

/** 提交 AI 能耗分析后台任务，返回 job_id（结果轮询 fetchEnergyAiJob）。 */
export async function submitEnergyAnalysisJob(data: {
  workshop_id: string
  analysis_month: string
  production_items: { product_name: string; quantity: number; unit: string }[]
  include_ai_suggestion?: boolean
}): Promise<string> {
  const result = await fetchApi<{ code: number; data: { job_id: string }; message?: string }>(
    `${API_BASE}/energy/ai-analysis-v2`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  )
  return result.data.job_id
}

export interface EnergyAiJobState {
  status: 'running' | 'done' | 'failed'
  result: AIAnalysisResult | null
  error: string | null
}

/** 轮询 AI 能耗分析任务状态。 */
export async function fetchEnergyAiJob(jobId: string): Promise<EnergyAiJobState> {
  const result = await fetchApi<{ code: number; data: EnergyAiJobState; message?: string }>(
    `${API_BASE}/energy/ai-analysis-v2/jobs/${jobId}`,
  )
  return result.data
}