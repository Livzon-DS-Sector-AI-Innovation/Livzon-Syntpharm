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

export async function createVehicle(data: any) {
  const res = await fetch(`${API_BASE}/administration/vehicles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建车辆失败')
  return res.json()
}

export async function updateVehicle(id: string, data: any) {
  const res = await fetch(`${API_BASE}/administration/vehicles/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新车辆失败')
  return res.json()
}

export async function deleteVehicle(id: string) {
  const res = await fetch(`${API_BASE}/administration/vehicles/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除车辆失败')
  return res.json()
}

export async function batchImportVehicles(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/administration/vehicles/batch-import`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`批量导入失败 (HTTP ${res.status}): ${text}`)
  }
  return res.json()
}