const API_BASE = '/api/v1'

export interface Regulation {
  id: string
  title: string
  category: string
  version: string | null
  content: string
  file_name: string | null
  file_type: string | null
  file_data: string | null
  remarks: string | null
  created_at: string
  updated_at: string
}

export interface RegulationListResponse {
  code: number
  message: string
  data: Regulation[]
  meta?: {
    page: number
    page_size: number
    total: number
  }
}

export interface RegulationResponse {
  code: number
  message: string
  data: Regulation
}

export async function fetchRegulations(params?: { keyword?: string; page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))
  const res = await fetch(`${API_BASE}/administration/regulations?${searchParams.toString()}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('获取规章制度列表失败')
  return res.json() as Promise<RegulationListResponse>
}

export async function createRegulation(data: { title: string; category?: string; version?: string; content: string; file_name?: string; file_type?: string; file_data?: string; remarks?: string }) {
  const res = await fetch(`${API_BASE}/administration/regulations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('创建规章制度失败')
  return res.json() as Promise<RegulationResponse>
}

export async function updateRegulation(id: string, data: { title?: string; category?: string; version?: string; content?: string; file_name?: string; file_type?: string; file_data?: string; remarks?: string }) {
  const res = await fetch(`${API_BASE}/administration/regulations/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新规章制度失败')
  return res.json() as Promise<RegulationResponse>
}

export async function deleteRegulation(id: string) {
  const res = await fetch(`${API_BASE}/administration/regulations/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除规章制度失败')
  return res.json()
}

export async function extractRegulationText(data: { file_name?: string; file_type?: string; file_data?: string }) {
  const res = await fetch(`${API_BASE}/administration/regulations/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('提取文件内容失败')
  return res.json() as Promise<{ code: number; message: string; data: { text: string; source: string } }>
}