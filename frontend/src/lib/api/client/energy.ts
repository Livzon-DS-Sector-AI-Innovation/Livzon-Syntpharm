import type { EnergyOverviewData, CollectLogDetail, PaginatedResponse } from '@/types/energy'

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
  const res = await fetch('/api/v1/energy/platforms')
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
