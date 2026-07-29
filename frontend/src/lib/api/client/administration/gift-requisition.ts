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





