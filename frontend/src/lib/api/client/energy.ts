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