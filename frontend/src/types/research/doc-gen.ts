/**
 * 研发报告 AI 文档生成 —— UI 层类型与中文文案映射。
 * API 契约类型一律从 @/types/generated/schema 派生，不得手写。
 */
import type { components } from '@/types/generated/schema'

/** 资料角色：material=研究资料，literature=文献 */
export type DocGenFileRole = components['schemas']['DocGenInputFileResponse']['role']

/** 面板内单个待上传文件的表单状态（UI 类型） */
export interface DocGenFormItem {
  file: File
  role: DocGenFileRole
}

export const DOC_GEN_STATUS_LABELS: Record<string, string> = {
  draft: '待提取',
  pending: '排队中',
  parsing: '解析资料',
  extracting: '抽取内容',
  awaiting_review: '待确认',
  confirmed: '已确认',
  composing: 'AI 报告生成',
  rendering: '渲染文档',
  completed: '已生成',
  ready: '已生成', // 旧版完成态（兼容存量任务展示）
  failed: '生成失败',
  cancelled: '已取消',
}

export const DOC_GEN_STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  pending: 'default',
  parsing: 'processing',
  extracting: 'processing',
  awaiting_review: 'warning',
  confirmed: 'processing',
  composing: 'processing',
  rendering: 'processing',
  completed: 'success',
  ready: 'success', // 旧版完成态
  failed: 'error',
  cancelled: 'warning',
}

/** 草稿：对话模式下任务已建、等待用户手动触发 AI 提取 */
export const DOC_GEN_DRAFT_STATUS = 'draft'

/** 完成态（含旧版 ready），用于「已生成」视图判定 */
export const DOC_GEN_COMPLETED_STATUSES: ReadonlySet<string> = new Set(['completed', 'ready'])

export function isDocGenCompleted(status: string): boolean {
  return DOC_GEN_COMPLETED_STATUSES.has(status)
}

/** 等待人工确认：既不轮询也不占用 worker，由人决定何时继续 */
export const DOC_GEN_REVIEW_STATUS = 'awaiting_review'

/** 填充项状态中文文案（state ∈ ok|ai_draft|pending|conflict|manual_only|ai_failed|layout_overflow|anchor_unresolved|needs_verify） */
export const DOC_GEN_SLOT_STATE_LABELS: Record<string, string> = {
  ok: '已填充',
  ai_draft: 'AI草稿',
  pending: '待补充',
  conflict: '来源冲突',
  manual_only: '需人工填写',
  ai_failed: 'AI抽取失败',
  layout_overflow: '版式待处理',
  anchor_unresolved: '未能定位',
  needs_verify: '需人工核对',
}

/** 终态：不再轮询 */
export const DOC_GEN_TERMINAL_STATUSES: ReadonlySet<string> = new Set(['completed', 'ready', 'failed', 'cancelled'])

export function isDocGenTerminal(status: string): boolean {
  return DOC_GEN_TERMINAL_STATUSES.has(status)
}

/**
 * 任务统计视图（后端 stats 为宽松字典，此处仅做 UI 解读，不属于 API 契约类型）。
 * 口径：substantive=实质内容（有依据写入）；pending=待补充；manual=需人工填写。
 * 后端另有 written（会把占位符也算进去），仅作技术排查用，不面向使用者展示。
 */
export interface DocGenStatsView {
  substantive: number
  pending: number
  manual: number
  drafts: number
  conflicts: number
  /** 值已写入但需人工核对（依据仅模糊匹配命中，或模型置信度偏低） */
  needsVerify: number
  /** 已写入且模型置信度介于中/高阈值之间的槽位数（信息性，供抽查） */
  lowConfidence: number
  unresolved: number
  occupied: number
  overflow: number
  warnings: string[]
}

export function parseDocGenStats(stats: Record<string, unknown> | null | undefined): DocGenStatsView {
  const num = (key: string): number => {
    const value = stats?.[key]
    return typeof value === 'number' && Number.isFinite(value) ? value : 0
  }
  const rawWarnings = stats?.warnings
  return {
    substantive: num('substantive'),
    pending: num('pending'),
    manual: num('manual'),
    drafts: num('drafts'),
    conflicts: num('conflicts'),
    needsVerify: num('needs_verify'),
    lowConfidence: num('low_confidence'),
    unresolved: num('unresolved'),
    occupied: num('occupied'),
    overflow: num('overflow'),
    warnings: Array.isArray(rawWarnings) ? rawWarnings.filter((w): w is string => typeof w === 'string') : [],
  }
}
