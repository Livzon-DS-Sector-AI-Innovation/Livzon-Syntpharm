import type { EnergyOverviewData, CollectLogDetail } from '@/types/energy'
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
  return apiGet<CollectLogDetail>(`${API_BASE}/energy/collect-logs/${logId}`)
}

export async function fetchPlatformsClient(): Promise<any[]> {
  return apiGet<any[]>(`${API_BASE}/energy/platforms`)
}

// ═══════════════════════════════════════════════════════════
//  预警规则
// ═══════════════════════════════════════════════════════════

export async function fetchAlertRules(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const query = buildQueryString(params)
  return apiFetchPaginated<any>(`${API_BASE}/energy/alerts/rules${query}`)
}

// ═══════════════════════════════════════════════════════════
//  预警记录
// ═══════════════════════════════════════════════════════════

export async function fetchAlertRecords(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const query = buildQueryString(params)
  return apiFetchPaginated<any>(`${API_BASE}/energy/alerts/records${query}`)
}

// ═══════════════════════════════════════════════════════════
//  月度记录
// ═══════════════════════════════════════════════════════════

export async function fetchMonthlyRecordsClient(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const query = buildQueryString(params)
  return apiFetchPaginated<any>(`${API_BASE}/energy/monthly${query}`)
}

export async function fetchWorkshopsClient(params?: any): Promise<any[]> {
  const query = buildQueryString(params)
  return apiGet<any[]>(`${API_BASE}/energy/workshops${query}`)
}

export async function fetchMonthlySummaryClient(params?: any): Promise<any> {
  const query = buildQueryString(params)
  return apiGet<any>(`${API_BASE}/energy/monthly/summary${query}`)
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

export async function analyzeEnergyV2(data: {
  workshop_id: string
  analysis_month: string
  production_items: { product_name: string; quantity: number; unit: string }[]
  include_ai_suggestion?: boolean
}): Promise<AIAnalysisResult> {
  const result = await fetchApi<{ code: number; data: AIAnalysisResult; message?: string }>(`${API_BASE}/energy/ai-analysis-v2`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
  return result.data
}

// ═══════════════════════════════════════════════════════════
//  生产数据同步
// ═══════════════════════════════════════════════════════════

export interface ProductionOutputItem {
  product_name: string
  quantity: number
  unit: string
}

export async function fetchProductionOutput(params: {
  workshop_id: string
  month: string
}): Promise<{ items: ProductionOutputItem[] }> {
  const query = buildQueryString(params)
  return apiGet<{ items: ProductionOutputItem[] }>(`${API_BASE}/energy/production/output${query}`)
}
