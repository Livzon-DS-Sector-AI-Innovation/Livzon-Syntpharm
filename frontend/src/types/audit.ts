import type { components } from '@/types/generated/schema'

/** 单条操作记录（对应后端 audit 模块 AuditLogItem）。 */
export type AuditLogItem = components['schemas']['AuditLogItem']

/** 操作记录分页数据（前端取的是信封内的 data，即 items/total/page/page_size）。 */
export type AuditLogListResponse = components['schemas']['AuditLogListData']

/** 操作记录查询参数（actions 与 lib/api/server 共用一份，避免两层各写一遍）。 */
export interface AuditLogQuery {
  page?: number
  page_size?: number
  user_id?: string
  action?: string
  resource_type?: string
  keyword?: string
}
