'use client'

import type { CSSProperties } from 'react'
import { Tooltip } from 'antd'
import { UserAvatar } from '@/components/common/UserAvatar'
import { T } from '@/components/safety/sharedStyles'

/** 未绑定系统用户时统一的说明文案：同名多人无法消歧、或系统里查无此人 */
export const PERSON_PENDING_HINT =
  '系统内未匹配到唯一用户（同名多人或查无此人），请在此处选择实际人员完成绑定'

const badgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  flex: 'none',
  padding: '1px 6px',
  borderRadius: 4,
  fontSize: 11,
  fontWeight: 600,
  lineHeight: '16px',
  color: T.warning,
  background: T.yellow,
  whiteSpace: 'nowrap',
}

/** 「待确认」标记：姓名无法唯一解析（同名多人无法消歧，或系统查无此人） */
export function PersonPendingBadge({ text = '待确认' }: { text?: string }) {
  return (
    <Tooltip title={PERSON_PENDING_HINT}>
      <span style={badgeStyle}>{text}</span>
    </Tooltip>
  )
}

/**
 * 表格/详情里的人员单元：头像 + 姓名，姓名无法唯一解析 → 追加「待确认」标记。
 *
 * `src` 由后端读时解析提供（UUID 命中或姓名唯一命中）；未命中时 UserAvatar 走姓名首字色块。
 * `pending` 优先于 `bound` 判定：唯一匹配会返回 id 且 pending=false，只有同名多人无法消歧
 * 或查无此人时才保留待确认。
 */
export function PersonNameWithBadge({
  name,
  bound,
  pending,
  src,
  fontSize = 13,
  avatarSize = 20,
}: {
  name?: string | null
  bound?: string | null
  pending?: boolean
  src?: string | null
  fontSize?: number
  avatarSize?: number
}) {
  if (!name) return <span style={{ color: T.muted }}>-</span>
  const isPending = pending ?? !bound
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, maxWidth: '100%', fontSize }}>
      <UserAvatar name={name} src={src} size={avatarSize} />
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
      {isPending ? <PersonPendingBadge /> : null}
    </span>
  )
}