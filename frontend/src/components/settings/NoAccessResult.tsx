'use client'

import { BoundaryResult } from '@/components/common/BoundaryResult'

interface NoAccessResultProps {
  title?: string
  subTitle?: string
  /** 缺少的权限码（如 `quality:admin:read`），会在提示里点明 */
  requiredPermission?: string
  /** 模块显示名（如「质量管理」），用于生成"找谁申请"的指引 */
  moduleLabel?: string
}

/**
 * 无权限 / 未登录时的统一提示（**页面级**守卫用）。
 *
 * 以前文案写死为「只有管理员可以管理用户、LLM 模型配置与 Livzon Skill」，
 * 用在字典等页面就不通顺了 —— 现在按「权限不足」通用表达。
 *
 * 委派式权限管理接入后新增两个可选参数：`requiredPermission` + `moduleLabel`，
 * 让提示能说清「缺哪个权限、该找谁申请」（模块负责人 / 模块管理员 / 系统管理员），
 * 否则用户只看到"权限不足"仍然不知道该找谁。
 *
 * 内部统一走 `BoundaryResult`，与模块级守卫（`ModuleNoAccess`）、404 / 错误页
 * 共用同一套外观与动作按钮，避免多处各写一套。
 */
export function NoAccessResult({
  title,
  subTitle,
  requiredPermission,
  moduleLabel,
}: NoAccessResultProps = {}) {
  // 传了「请先登录」这类文案 → 按未登录处理（会多给一个「去登录」按钮）
  const kind = title?.includes('登录') ? 'unauthorized' : 'forbidden'

  const details: string[] = []
  if (subTitle) details.push(subTitle)
  if (requiredPermission) details.push(`缺少权限：${requiredPermission}`)
  if (moduleLabel) {
    details.push(
      `可联系「${moduleLabel}」的模块负责人或模块代表申请；无人管理时联系系统管理员。`,
    )
  }

  return (
    <BoundaryResult
      kind={kind}
      title={title}
      subTitle={details.length > 0 ? details.join(' ') : undefined}
    />
  )
}
