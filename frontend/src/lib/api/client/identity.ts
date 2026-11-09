import type { components } from '@/types/generated/schema'
import { apiGet } from '@/lib/api/client'

const API_BASE = '/api/v1'

/** 人员列表项：直接使用生成的 OpenAPI 契约（identity.personnel），不再手工维护字段子集。 */
export type PersonnelOption = components['schemas']['PersonnelItem']

/** 接口 data 字段：契约声明为可空，因此保留空数组兜底。 */
type PersonnelListData = components['schemas']['PersonnelListApiResponse']['data']

/** 人员分页结果：total 用于判断是否还有下一页（后端按姓名排序）。 */
export interface PersonnelPage {
  items: PersonnelOption[]
  total: number
}

export interface SearchPersonnelOptions {
  /** 仅返回已绑定飞书身份的账号（后端 feishu_bound_only，供需要发飞书通知的场景使用） */
  feishuBoundOnly?: boolean
}

/**
 * 分页获取系统用户（keyword 为空即返回全部未删除用户）。
 * 统一走 API 层，避免组件里裸 fetch 与手工解包信封。
 */
export async function searchPersonnel(
  keyword = '',
  offset = 0,
  limit = 50,
  options: SearchPersonnelOptions = {},
): Promise<PersonnelPage> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) })
  const kw = keyword.trim()
  if (kw) params.set('keyword', kw)
  if (options.feishuBoundOnly) params.set('feishu_bound_only', 'true')
  const data = await apiGet<PersonnelListData>(
    `${API_BASE}/identity/personnel?${params.toString()}`,
  )
  const items = data?.items ?? []
  return { items, total: data?.total ?? items.length }
}