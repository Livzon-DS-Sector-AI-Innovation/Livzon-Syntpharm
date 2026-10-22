import type { components } from '@/types/generated/schema'

/** 单条操作记录（对应后端 audit 模块 AuditLogItem）。 */
export type AuditLogItem = components['schemas']['AuditLogItem']

/** 操作记录分页数据（前端取的是信封内的 data，即 items/total/page/page_size）。 */
export type AuditLogListResponse = components['schemas']['AuditLogListData']
