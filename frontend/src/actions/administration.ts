'use server'

const API_BASE = process.env.API_BASE_URL || ''

export async function createGiftRequisition(data: any) {
  const res = await fetch(`${API_BASE}/api/v1/administration/gift-requisitions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建领用记录失败')
  return res.json()
}

export async function updateGiftRequisition(id: string, data: any) {
  const res = await fetch(`${API_BASE}/api/v1/administration/gift-requisitions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新领用记录失败')
  return res.json()
}

export async function deleteGiftRequisition(id: string) {
  const res = await fetch(`${API_BASE}/api/v1/administration/gift-requisitions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除领用记录失败')
  return res.json()
}

export async function createRegulation(data: any) {
  const res = await fetch(`${API_BASE}/api/v1/administration/regulations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建法规制度失败')
  return res.json()
}

export async function updateRegulation(id: string, data: any) {
  const res = await fetch(`${API_BASE}/api/v1/administration/regulations/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新法规制度失败')
  return res.json()
}

export async function deleteRegulation(id: string) {
  const res = await fetch(`${API_BASE}/api/v1/administration/regulations/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除法规制度失败')
  return res.json()
}


export async function extractRegulationText(data: { file_name?: string; file_type?: string; file_data?: string }) {
  const API_BASE = process.env.API_BASE_URL || ''
  const res = await fetch(`${API_BASE}/api/v1/administration/regulations/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('提取文件内容失败')
  return res.json() as Promise<{ code: number; message: string; data: { text: string; source: string } }>
}


export async function createGiftInventory(data: any) {
  const API_BASE = process.env.API_BASE_URL || ''
  const res = await fetch(`${API_BASE}/api/v1/administration/gift-inventories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建库存记录失败')
  return res.json()
}

export async function updateGiftInventory(id: string, data: any) {
  const API_BASE = process.env.API_BASE_URL || ''
  const res = await fetch(`${API_BASE}/api/v1/administration/gift-inventories/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新库存记录失败')
  return res.json()
}

export async function deleteGiftInventory(id: string) {
  const API_BASE = process.env.API_BASE_URL || ''
  const res = await fetch(`${API_BASE}/api/v1/administration/gift-inventories/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除库存记录失败')
  return res.json()
}

export async function createVehicle(data: any) {
  const API_BASE = process.env.API_BASE_URL || ''
  const res = await fetch(`${API_BASE}/api/v1/administration/vehicles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建车辆记录失败')
  return res.json()
}

export async function updateVehicle(id: string, data: any) {
  const API_BASE = process.env.API_BASE_URL || ''
  const res = await fetch(`${API_BASE}/api/v1/administration/vehicles/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新车辆记录失败')
  return res.json()
}

export async function deleteVehicle(id: string) {
  const API_BASE = process.env.API_BASE_URL || ''
  const res = await fetch(`${API_BASE}/api/v1/administration/vehicles/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除车辆记录失败')
  return res.json()
}
