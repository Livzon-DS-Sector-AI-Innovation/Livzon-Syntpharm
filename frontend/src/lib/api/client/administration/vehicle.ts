const API_BASE = '/api/v1'

export async function fetchVehicles(params?: { keyword?: string; status?: string; page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.status) searchParams.set('status', params.status)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  const res = await fetch(`${API_BASE}/administration/vehicles?${searchParams.toString()}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('获取车辆列表失败')
  return res.json()
}
