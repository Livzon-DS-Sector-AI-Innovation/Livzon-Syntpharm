import type { components } from '@/types/generated/schema'
import { apiGet } from '@/lib/api/client'

const API_BASE = '/api/v1'

/** 人员列表项：直接使用生成的 OpenAPI 契约（identity.personnel），不再手工维护字段子集。 */
export type PersonnelOption = components['schemas']['PersonnelItem']

/** 接口 data 字段：契约声明为可空，因此保留空数组兜底。 */
type PersonnelListData = components['schemas']['PersonnelListApiResponse']['data']

/**
 * 按关键词搜索人员（部门/姓名/账号）。
 * 统一走 API 层，避免组件里裸 fetch 与手工解包信封。
 */
export async function searchPersonnel(keyword: string, limit = 50): Promise<PersonnelOption[]> {
  const params = new URLSearchParams({ keyword, limit: String(limit) })
  const data = await apiGet<PersonnelListData>(
    `${API_BASE}/identity/personnel?${params.toString()}`,
  )
  return data?.items ?? []
}
