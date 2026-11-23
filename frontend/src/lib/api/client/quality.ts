import type { ModuleInfo } from '@/types'
import type { components } from '@/types/generated/schema'
import type {
  CapaListQuery,
  DepartmentContactListData,
  DepartmentLeaderData,
  DepartmentMemberOption,
  DeviationAttachmentCommentList,
  DeviationAttachmentCommentSummary,
  DeviationLedgerDetail,
  DeviationLedgerOption,
  DeviationLedgerOptionResult,
  DeviationLedgerStatistics,
  DeviationMemberOptionResult,
  DeviationNotifySettings,
} from '@/types/quality'

type CapaResponse = components['schemas']['CapaResponse']
type CapaApiResponse = components['schemas']['CapaApiResponse']

import { apiGet, apiFetchPaginated } from '@/lib/api/client'

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet(`/api/v1/quality`)
}

export async function fetchCapa(id: string): Promise<CapaApiResponse> {
  return apiGet<CapaApiResponse>(`/api/v1/quality/capas/${id}`)
}

/** CAPA 分页结果：形状由 apiFetchPaginated 统一决定，不在这里手写字段。 */
export type CapaListPage = Awaited<ReturnType<typeof apiFetchPaginated<CapaResponse>>>

export async function fetchCapas(params?: CapaListQuery): Promise<CapaListPage> {
  const query = params
    ? Object.entries(params)
        .filter(([_, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join('&')
    : ''
  return apiFetchPaginated<CapaResponse>(`/api/v1/quality/capas${query ? `?${query}` : ''}`)
}

export async function fetchDepartmentContacts(keyword?: string): Promise<DepartmentContactListData> {
  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : ''
  return apiGet<DepartmentContactListData>(`/api/v1/quality/department-contacts${query}`)
}

/**
 * 部门联系人配置：按部门名解析 HR 组织里的部门负责人（新增部门时自动带出）。
 *
 * 返回的 `dept_head_profile_id` 是 `hr.employee_profiles.id`，与
 * `DepartmentContact.dept_head_id`（`identity.users.id`）不是同一套 ID：
 * 提交时后端会统一归一，前端只管原样回填。
 */
export async function fetchDepartmentLeader(department: string): Promise<DepartmentLeaderData> {
  return apiGet<DepartmentLeaderData>(
    `/api/v1/quality/department-contacts/department-leader?department=${encodeURIComponent(department)}`,
    { cache: 'no-store' },
  )
}

/** 部门联系人配置：人员候选（客户端版，供模块配置页签使用） */
export async function fetchDepartmentMemberOptions(keyword?: string): Promise<DepartmentMemberOption[]> {
  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : ''
  const data = await apiGet<DeviationMemberOptionResult>(
    `/api/v1/quality/department-contacts/member-options${query}`,
  )
  return data.items
}

/** 部门联系人配置：组织部门候选（部门名与台账同源） */
export async function fetchLedgerDepartmentOptions(): Promise<DeviationLedgerOption[]> {
  const data = await apiGet<DeviationLedgerOptionResult>('/api/v1/quality/deviation/ledger/department-options')
  return data.items
}

/** 部门联系人配置：偏差台账部门分布（用于提示「有偏差但没配置联系人」） */
export async function fetchDeviationStatistics(): Promise<DeviationLedgerStatistics> {
  return apiGet<DeviationLedgerStatistics>('/api/v1/quality/deviation/ledger/statistics')
}

/** 部门联系人配置：通知设置 */
export async function fetchDeviationNotifyConfig(): Promise<DeviationNotifySettings> {
  return apiGet<DeviationNotifySettings>('/api/v1/quality/deviation/notify')
}

type InstrumentListData = components['schemas']['InstrumentListData']
type ReagentListData = components['schemas']['ReagentListResponse']

/** 质量看盘：仪器列表（含校准有效期与超期标记） */
export async function fetchQualityInstruments(): Promise<InstrumentListData['items']> {
  const data = await apiGet<InstrumentListData>(`/api/v1/quality/instrument?page=1&page_size=100`)
  return data.items
}

/** 质量看盘：试剂列表 */
export async function fetchQualityReagents(): Promise<ReagentListData['items']> {
  const data = await apiGet<ReagentListData>(`/api/v1/quality/reagent/list?page=1&page_size=100`)
  return data.items
}

// ============ 偏差台账（quality.deviation_ledger） ============

/** 台账只读详情：右侧抽屉按需拉取，只含主表字段 */
export async function fetchDeviationLedgerDetail(id: string): Promise<DeviationLedgerDetail> {
  return apiGet<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${encodeURIComponent(id)}`)
}

/** 某附件的批注列表（时间正序，含未处理条数） */
export async function fetchDeviationAttachmentComments(
  ledgerId: string,
  fileId: string
): Promise<DeviationAttachmentCommentList> {
  const base = `/api/v1/quality/deviation/ledger/${encodeURIComponent(ledgerId)}`
  return apiGet<DeviationAttachmentCommentList>(
    `${base}/attachments/${encodeURIComponent(fileId)}/comments`
  )
}

/** 详情页附件角标：按附件聚合未处理 / 全部批注数 */
export async function fetchDeviationAttachmentCommentSummary(
  ledgerId: string
): Promise<DeviationAttachmentCommentSummary> {
  const base = `/api/v1/quality/deviation/ledger/${encodeURIComponent(ledgerId)}`
  return apiGet<DeviationAttachmentCommentSummary>(`${base}/attachment-comments/summary`)
}

// ============ 试剂库存提醒（quality.reagent-reminder） ============

type ReagentReminderConfigData = components['schemas']['ReagentReminderConfigData']
type LowStockData = components['schemas']['LowStockData']

/** 库存提醒配置；未配置过时后端返回 data=null。 */
export async function fetchReagentReminderConfig(): Promise<ReagentReminderConfigData | null> {
  return apiGet<ReagentReminderConfigData | null>('/api/v1/quality/reagent-reminder/config')
}

/** 低于阈值的试剂预览（含每项提醒开关状态）。 */
export async function fetchReagentLowStock(threshold: number): Promise<LowStockData['items']> {
  const data = await apiGet<LowStockData>(
    `/api/v1/quality/reagent-reminder/low-stock?threshold=${threshold}`
  )
  return data.items ?? []
}
