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







