const API_BASE = '/api/v1'

export async function fetchGiftInventories(params?: { keyword?: string; status?: string; page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.status) searchParams.set('status', params.status)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  const res = await fetch(`${API_BASE}/administration/gift-inventories?${searchParams.toString()}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('获取库存列表失败')
  return res.json()
}

export async function createGiftInventory(data: any) {
  const res = await fetch(`${API_BASE}/administration/gift-inventories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建库存记录失败')
  return res.json()
}

export async function updateGiftInventory(id: string, data: any) {
  const res = await fetch(`${API_BASE}/administration/gift-inventories/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新库存记录失败')
  return res.json()
}

export async function deleteGiftInventory(id: string) {
  const res = await fetch(`${API_BASE}/administration/gift-inventories/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除库存记录失败')
  return res.json()
}