import { apiGet } from '@/lib/api/client'

const API_BASE = '/api/v1'

/** 人员搜索结果（identity.personnel 列表项的业务子集，仅取前端用到的字段） */
export interface PersonnelOption {
  id: string
  name: string
  username?: string
  department?: string
}

interface PersonnelListPayload {
  items?: PersonnelOption[]
}

/**
 * 按关键词搜索人员（部门/姓名/账号）。
 * 统一走 API 层，避免组件里裸 fetch 与手工解包信封。
 */
export async function searchPersonnel(keyword: string, limit = 50): Promise<PersonnelOption[]> {
  const params = new URLSearchParams({ keyword, limit: String(limit) })
  const data = await apiGet<PersonnelListPayload | PersonnelOption[]>(
    `${API_BASE}/identity/personnel?${params.toString()}`,
  )
  if (Array.isArray(data)) return data
  return data?.items ?? []
}