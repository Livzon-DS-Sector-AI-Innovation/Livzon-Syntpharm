/**
 * 交付物模板槽位结构 —— 前端类型与展示常量。
 *
 * 数据结构一律取自 OpenAPI 生成类型（AGENTS.md 规则），这里只做别名收窄
 * 和「界面要用的选项/差异标记」这类纯前端常量。
 */
import type { components } from '@/types/generated/schema'

export type DocGenSlot = components['schemas']['DocGenSlotItem']
export type DocGenSlotAnchor = components['schemas']['DocGenSlotAnchorData']
export type DocGenSlotCandidate = components['schemas']['DocGenSlotCandidateItem']
export type DocGenTemplateSlots = components['schemas']['DocGenTemplateSlotsData']
export type DocGenSlotsSaveResult = components['schemas']['DocGenTemplateSlotsSaveData']
export type DocGenSlotsReparseResult = components['schemas']['DocGenTemplateSlotsReparseData']

/** 与后端 structure._VALUE_TYPES 保持一致 */
export const SLOT_VALUE_TYPE_OPTIONS = [
  { value: 'text', label: '短文本' },
  { value: 'long_text', label: '长文本' },
  { value: 'number', label: '数字' },
  { value: 'date', label: '日期' },
  { value: 'list', label: '列表' },
] as const

/** 重解析后的行标记：AI 新增 / 保留人工修改 */
export type SlotDiffStatus = 'added' | 'kept' | null

/**
 * 槽位的结构标识，用于判断两个槽位是否指向同一位置。
 *
 * 刚从前端「新增行」出来的槽位只有 candidate_id（保存后后端才补 anchor），
 * 因此这里按 anchor → candidate_id → slot_key 逐级回退，避免多个新行都撞成 'unknown'。
 */
export function slotAnchorKey(slot: Pick<DocGenSlot, 'anchor' | 'candidate_id' | 'slot_key'>): string {
  const anchor = slot.anchor
  if (anchor) {
    if (anchor.kind === 'paragraph') return `paragraph:${anchor.index ?? 0}`
    if (anchor.kind === 'table_cell') {
      return `table_cell:${anchor.table_index ?? 0}:${anchor.row ?? 0}:${anchor.col ?? 0}:${anchor.para_index ?? 0}`
    }
    if (anchor.kind) return anchor.kind
  }
  if (slot.candidate_id) return `candidate:${slot.candidate_id}`
  return slot.slot_key ? `slot:${slot.slot_key}` : 'unknown'
}