import type { EnergyOverviewData, CollectLogDetail, PaginatedResponse } from '@/types/energy'

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
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  })
  const res = await fetch(`/api/v1/energy/overview?${searchParams.toString()}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data
}

export async function fetchCollectLogDetailClient(logId: string): Promise<CollectLogDetail> {
  const res = await fetch(`/api/v1/energy/collect-logs/${logId}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data
}

export async function fetchPlatformsClient(): Promise<any[]> {
  const res = await fetch('/api/v1/energy/platforms', { credentials: 'include' })
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data
}
// ── 预警规则 ──

export async function fetchAlertRules(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const query = buildQueryString(params)
  // 浏览器端使用相对路径
  const fullUrl = `/api/v1/energy/alerts/rules${query}`
  const res = await fetch(fullUrl)
  const json = await res.json()
  return {
    items: json.data || [],
    total: json.meta?.total || 0,
    page: json.meta?.page || 1,
    page_size: json.meta?.page_size || 20,
  }
}

// ── 预警记录 ──

export async function fetchAlertRecords(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const query = buildQueryString(params)
  // 浏览器端使用相对路径
  const fullUrl = `/api/v1/energy/alerts/records${query}`
  const res = await fetch(fullUrl)
  const json = await res.json()
  return {
    items: json.data || [],
    total: json.meta?.total || 0,
    page: json.meta?.page || 1,
    page_size: json.meta?.page_size || 20,
  }
}

// ── 月度记录 ──

export async function fetchMonthlyRecordsClient(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const query = buildQueryString(params)
  const res = await fetch(`/api/v1/energy/monthly${query}`)
  const json = await res.json()
  return {
    items: json.data || [],
    total: json.meta?.total || 0,
    page: json.meta?.page || 1,
    page_size: json.meta?.page_size || 20,
  }
}

export async function fetchWorkshopsClient(params?: any): Promise<any[]> {
  const query = buildQueryString(params)
  const res = await fetch(`/api/v1/energy/workshops${query}`)
  const json = await res.json()
  return json.data || []
}

export async function fetchMonthlySummaryClient(params?: any): Promise<any> {
  const query = buildQueryString(params)
  const res = await fetch(`/api/v1/energy/monthly/summary${query}`)
  const json = await res.json()
  return json.data
}



// ── 单耗目标管理 ──

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
  const res = await fetch('/api/v1/energy/targets', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '创建目标失败')
  }
  return json.data
}

export async function updateTarget(

  targetId: string,
  data: { target_unit_consumption: number }
): Promise<UnitConsumptionTarget> {
  const res = await fetch(`/api/v1/energy/targets/${targetId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '更新目标失败')
  }
  return json.data
}

export async function getTarget(
  workshopId: string,
  targetMonth: string
): Promise<UnitConsumptionTarget | null> {
  const res = await fetch(`/api/v1/energy/targets/${workshopId}/${targetMonth}`)
  const json = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '查询目标失败')
  }
  return json.data
}

// ── AI 分析（V2 - 支持单耗） ──

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
  const res = await fetch('/api/v1/energy/ai-analysis-v2', {
    credentials: 'include',
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '分析失败')
  }
  return json.data
}
