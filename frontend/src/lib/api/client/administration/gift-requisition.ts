const API_BASE = '/api/v1'

export async function fetchGiftRequisitions(params?: { department?: string; item_name?: string; recipient?: string; page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.department) searchParams.set('department', params.department)
  if (params?.item_name) searchParams.set('item_name', params.item_name)
  if (params?.recipient) searchParams.set('recipient', params.recipient)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  const res = await fetch(`${API_BASE}/administration/gift-requisitions?${searchParams.toString()}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('获取领用记录失败')
  return res.json()
}

export async function createGiftRequisition(data: any) {
  const res = await fetch(`${API_BASE}/administration/gift-requisitions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建领用记录失败')
  return res.json()
}

export async function updateGiftRequisition(id: string, data: any) {
  const res = await fetch(`${API_BASE}/administration/gift-requisitions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新领用记录失败')
  return res.json()
}

export async function deleteGiftRequisition(id: string) {
  const res = await fetch(`${API_BASE}/administration/gift-requisitions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除领用记录失败')
  return res.json()
}