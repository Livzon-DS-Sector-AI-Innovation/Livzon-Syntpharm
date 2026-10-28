'use client'

import { BoundaryResult } from '@/components/common/BoundaryResult'

interface NoAccessResultProps {
  title?: string
  subTitle?: string
}

/**
 * 无权限 / 未登录时的统一提示（**页面级**守卫用）。
 *
 * 以前文案写死为「只有管理员可以管理用户、LLM 模型配置与 Livzon Skill」，
 * 用在字典等页面就不通顺了 —— 现在按「权限不足」通用表达。
 *
 * 内部统一走 `BoundaryResult`，与模块级守卫（`ModuleNoAccess`）、404 / 错误页
 * 共用同一套外观与动作按钮，避免多处各写一套。
 */
export function NoAccessResult({ title, subTitle }: NoAccessResultProps = {}) {
  // 传了「请先登录」这类文案 → 按未登录处理（会多给一个「去登录」按钮）
  const kind = title?.includes('登录') ? 'unauthorized' : 'forbidden'
  return <BoundaryResult kind={kind} title={title} subTitle={subTitle} />
}
