'use client'

import type { ComponentType } from 'react'
import {
  AuditOutlined,
  BranchesOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  NumberOutlined,
  ProfileOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import type { DeviationLedgerDetail } from '@/types/quality'

/**
 * 偏差详情页分区注册表：导航条、板块标题、锚点三处共用同一份元数据，
 * 避免「导航里有、页面上没有」或标题文案漂移。
 */

export type DeviationSectionKey =
  | 'basic-info'
  | 'ai-analysis'
  | 'investigation'
  | 'cross-dept-review'
  | 'review'
  | 'final-code'
  | 'review-timeline'
  | 'flow'

type SectionIcon = ComponentType<{ className?: string }>

/** 板块色调：全部为静态 Tailwind 类名，禁止模板拼接，否则 JIT 扫不到 */
export interface SectionTone {
  /** 板块左侧 3px 色条 */
  bar: string
  /** 标题区底色 */
  headerBg: string
  /** 图标块底色 + 图标颜色 */
  iconBox: string
  /** 导航条选中态：边框 + 底色（文字色需落在内层 span 上） */
  chipActive: string
  /** 导航条悬浮态边框（作用于 button） */
  chipHoverBorder: string
  /** 导航条悬浮态文字色（作用于内层 span，配合 group-hover） */
  chipHoverText: string
}

/**
 * 导航 chip 统一主色：chip 表达的是「当前位置」，与板块是否待办无关，
 * 因此两套 tone 共用同一组 chip 样式。
 */
const CHIP_ACTIVE = 'border-[#5645D4] bg-[#5645D4]'
const CHIP_HOVER_BORDER = 'hover:border-[#5645D4]'
const CHIP_HOVER_TEXT = 'group-hover:text-[#5645D4]'

/** 常态：中性灰，只做区域分隔，不抢注意力 */
export const SECTION_TONE: SectionTone = {
  bar: 'bg-[var(--color-hairline-strong)]',
  headerBg: 'bg-[var(--color-surface-soft)]',
  iconBox: 'bg-[#ECEEF1] text-[#6B7280]',
  chipActive: CHIP_ACTIVE,
  chipHoverBorder: CHIP_HOVER_BORDER,
  chipHoverText: CHIP_HOVER_TEXT,
}

/** 待办：主色紫，语义是「当前登录人需要在这里动手」 */
export const PENDING_TONE: SectionTone = {
  bar: 'bg-[#5645D4]',
  headerBg: 'bg-[#F6F4FE]',
  iconBox: 'bg-[#EBE8FB] text-[#5645D4]',
  chipActive: CHIP_ACTIVE,
  chipHoverBorder: CHIP_HOVER_BORDER,
  chipHoverText: CHIP_HOVER_TEXT,
}

export interface DeviationSectionMeta {
  key: DeviationSectionKey
  label: string
  subtitle: string
  icon: SectionIcon
  /** 待办时标题右侧的短标签；只读板块留空 */
  pendingLabel: string
  /** 是否出现在分区导航条（右栏审核流程只作为跳转目标，不参与滚动高亮） */
  inNav: boolean
}

const SECTION_LIST: DeviationSectionMeta[] = [
  {
    key: 'basic-info',
    label: '基本信息',
    subtitle: '编号、发生部门、发现信息与责任人',
    icon: ProfileOutlined,
    pendingLabel: '待补全',
    inNav: true,
  },
  {
    key: 'ai-analysis',
    label: 'AI 智能分析',
    subtitle: '结构化建议，需人工核对后保存',
    icon: RobotOutlined,
    pendingLabel: '待分析',
    inNav: true,
  },
  {
    key: 'investigation',
    label: '调查记录',
    subtitle: '调查报告与附件，提交后进入审核',
    icon: FileSearchOutlined,
    pendingLabel: '待补充',
    inNav: true,
  },
  {
    key: 'cross-dept-review',
    label: '跨部门会签',
    subtitle: '各部门调查与负责人审核进度',
    icon: TeamOutlined,
    pendingLabel: '待会签',
    inNav: true,
  },
  {
    key: 'review',
    label: '审核流转',
    subtitle: '通过、退回与重新提交',
    icon: AuditOutlined,
    pendingLabel: '待审核',
    inNav: true,
  },
  {
    key: 'final-code',
    label: '最终编号与归档',
    subtitle: '填写归档编号后偏差关闭',
    icon: NumberOutlined,
    pendingLabel: '待填写',
    inNav: true,
  },
  {
    key: 'review-timeline',
    label: '审核记录',
    subtitle: '历次审核意见、结果与操作人',
    icon: HistoryOutlined,
    pendingLabel: '',
    inNav: true,
  },
  {
    key: 'flow',
    label: '审核流程',
    subtitle: '环节、责任角色与当前处理人',
    icon: BranchesOutlined,
    pendingLabel: '',
    inNav: true,
  },
]

export const DEVIATION_SECTIONS: readonly DeviationSectionMeta[] = SECTION_LIST

export const SECTION_BY_KEY: Record<DeviationSectionKey, DeviationSectionMeta> = SECTION_LIST.reduce(
  (acc, item) => {
    acc[item.key] = item
    return acc
  },
  {} as Record<DeviationSectionKey, DeviationSectionMeta>,
)

/** 参与滚动高亮的板块（右栏审核流程与左栏板块位置重叠，不参与计算） */
export const SCROLLSPY_SECTION_KEYS: readonly string[] = SECTION_LIST.filter(
  (item) => item.inNav && item.key !== 'flow',
).map((item) => item.key)

/**
 * 板块可见性与各卡片内部的 `return null` 条件同源：
 * 导航条与卡片都调用这里，保证「导航里点得到就一定渲染得出来」。
 */
export function isSectionVisible(key: DeviationSectionKey, ledger: DeviationLedgerDetail): boolean {
  const actions = ledger.allowed_actions ?? []
  switch (key) {
    case 'cross-dept-review': {
      const rows = ledger.cross_dept_reviewers ?? []
      const isCrossStep = ledger.current_step === 'cross_dept_head_review'
      return rows.length > 0 && (isCrossStep || rows.some((row) => row.review_state === 'approved'))
    }
    case 'review':
      return (
        actions.includes('approve') ||
        actions.includes('reject') ||
        (actions.includes('resubmit') && ledger.status === 'returned')
      )
    case 'final-code':
      return actions.includes('final_code') || Boolean(ledger.final_code)
    default:
      return true
  }
}

/**
 * 当前登录人是否需要在某个板块动手（决定标题区是否切主色 + 待办标签）。
 *
 * 全部取后端下发的 per-user 字段，与各卡片内按钮的显隐条件保持同源：
 * - 基本信息：与「保存」按钮同源（可编辑基础信息，或仅可增删改跨部门行）
 * - AI 分析 / 调查记录：allowed_actions + can_edit_investigation
 * - 跨部门会签：逐行的 can_approve（审核）/ can_investigate（本部门调查）
 * - 审核流转：approve / reject / resubmit（退回后）
 * - 最终编号：allowed_actions 含 final_code
 * - 审核记录 / 审核流程：只读区，恒为 false
 *
 * 注意：不使用 can_operate —— 它在调查环节同样为 true，会误亮「审核流转」。
 */
export function isSectionActionable(key: DeviationSectionKey, ledger: DeviationLedgerDetail): boolean {
  // 已关闭 / 已取消 = 归档只读：不再提示任何待办。
  // 后端在 closed 单上仍可能返回 can_edit_investigation=true（历史数据沿用处理人标记），
  // 若不加这道闸，「调查记录」会在归档单上误亮「待补充」。
  if (ledger.status === 'closed' || ledger.status === 'cancelled') return false

  const actions = ledger.allowed_actions ?? []
  switch (key) {
    case 'basic-info':
      return ledger.editable || ledger.can_edit_cross_dept
    case 'ai-analysis':
      return actions.includes('analyze')
    case 'investigation':
      return actions.includes('investigate') || ledger.can_edit_investigation === true
    case 'cross-dept-review':
      return (ledger.cross_dept_reviewers ?? []).some((row) => row.can_approve || row.can_investigate)
    case 'review':
      return (
        actions.includes('approve') ||
        actions.includes('reject') ||
        (actions.includes('resubmit') && ledger.status === 'returned')
      )
    case 'final-code':
      return actions.includes('final_code')
    default:
      return false
  }
}

/** 当前单据下真正会渲染的板块（按页面顺序） */
export function visibleSections(ledger: DeviationLedgerDetail): DeviationSectionMeta[] {
  return SECTION_LIST.filter((item) => isSectionVisible(item.key, ledger))
}

/** 当前登录人待办的板块（供导航条小圆点等使用） */
export function actionableSectionKeys(ledger: DeviationLedgerDetail): DeviationSectionKey[] {
  return SECTION_LIST.filter((item) => isSectionVisible(item.key, ledger) && isSectionActionable(item.key, ledger)).map(
    (item) => item.key,
  )
}