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

// ── 人员下拉（选人组件数据源）────────────────────────────────────────

/** 人员下拉项：系统账号口径，只含展示字段（不含手机号/邮箱/角色）。 */
export type UserLookupItem = components['schemas']['UserLookupItem']

export interface UserLookupPage {
  items: UserLookupItem[]
  total: number
}

/**
 * 分页获取启用账号（选人组件的唯一数据源）。
 *
 * 与 HR 公共目录的区别：这里只返回 `identity.users` 中 `status=active` 的账号，
 * 即「系统管理 → 用户管理」里能登录的人；未开号的 HR 员工不会被列出。
 */
export async function fetchUserLookup(params?: {
  keyword?: string
  offset?: number
  limit?: number
}): Promise<UserLookupPage> {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('offset', String(params?.offset ?? 0))
  searchParams.set('limit', String(params?.limit ?? 50))
  const data = await apiGet<components['schemas']['UserLookupListApiResponse']['data']>(
    `${API_BASE}/identity/users/lookup?${searchParams.toString()}`,
    { cache: 'no-store' },
  )
  return { items: data?.items ?? [], total: data?.total ?? 0 }
}